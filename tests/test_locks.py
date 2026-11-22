"""Temporary database locks: a clear message, no partial changes, success once released."""
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db


APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "locks.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    monkeypatch.setattr(db, "LOCK_TIMEOUT", 0.05)  # keep the tests fast
    db.initialize(path)
    return path


@contextmanager
def locked(path, mode="IMMEDIATE"):
    """Hold a lock from a second connection, like another user in the middle of a write."""
    with closing(sqlite3.connect(path, isolation_level=None)) as other:
        other.execute(f"BEGIN {mode}")
        try:
            yield
        finally:
            other.execute("ROLLBACK")


def all_rows(path):
    with closing(sqlite3.connect(path)) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("games", "products", "sales")}


def test_locked_purchase_changes_nothing_and_succeeds_once_afterwards(path):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with locked(path):
        with pytest.raises(db.DatabaseBusy, match="try again"):
            db.buy(path, token, 1, "Kaffee", 10)
    assert all_rows(path) == before
    db.buy(path, token, 1, "Kaffee", 10)
    game, products, _ = db.load(path, token)
    assert (game["cash"], products[0]["stock"]) == (8000, 10)


def test_locked_trade_changes_nothing_and_settles_once_afterwards(path):
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 10)
    before = all_rows(path)
    with locked(path):
        with pytest.raises(db.DatabaseBusy):
            db.trade(path, token, 1)
    assert all_rows(path) == before
    db.trade(path, token, 1)
    game, _, history = db.load(path, token)
    assert (game["day"], game["cash"], len(history)) == (2, 12000, 3)
    with pytest.raises(ValueError, match="game has changed"):
        db.trade(path, token, 1)


@pytest.mark.parametrize("action", [
    lambda path, token: db.set_price(path, token, 1, "Kaffee", "5.00"),
    lambda path, token: db.delete_game(path, token),
    lambda path, token: db.create_game(path, "heatwave"),
])
def test_other_writes_report_the_lock(path, action):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with locked(path):
        with pytest.raises(db.DatabaseBusy):
            action(path, token)
    assert all_rows(path) == before


def test_page_load_does_not_wait_for_a_writer(path):
    # Once the tables exist, initialize() only reads.
    with locked(path):
        db.initialize(path)


def test_creating_the_tables_reports_the_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "LOCK_TIMEOUT", 0.05)
    fresh = tmp_path / "fresh.sqlite3"
    with locked(fresh):
        with pytest.raises(db.DatabaseBusy):
            db.initialize(fresh)
    db.initialize(fresh)
    assert all_rows(fresh) == {"games": [], "products": [], "sales": []}


def test_reading_waits_only_for_an_exclusive_lock(path):
    token = db.create_game(path, "exam_week")
    with locked(path, "IMMEDIATE"):
        assert db.load(path, token)[0]["day"] == 1
    with locked(path, "EXCLUSIVE"):
        with pytest.raises(db.DatabaseBusy):
            db.load(path, token)


def test_other_database_errors_are_not_hidden(path):
    token = db.create_game(path, "exam_week")
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("DROP TABLE sales")
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        db.trade(path, token, 1)


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


def test_app_shows_the_lock_and_buys_once_after_release(path):
    token = db.create_game(path, "exam_week")
    page = AppTest.from_file(str(APP), default_timeout=10)
    page.query_params["game"] = token
    page.run()
    page.number_input[0].set_value(10).run()
    with locked(path):
        click(page, "Buy")
    assert "busy right now" in page.error[0].value
    game, products, _ = db.load(path, token)
    assert (game["cash"], products[0]["stock"]) == (10000, 0)
    click(page, "Buy")
    assert page.success[0].value == "Purchased 10 × Coffee."
    game, products, _ = db.load(path, token)
    assert (game["cash"], products[0]["stock"]) == (8000, 10)


def test_app_page_load_offers_try_again(path):
    token = db.create_game(path, "exam_week")
    page = AppTest.from_file(str(APP), default_timeout=10)
    page.query_params["game"] = token
    with locked(path, "EXCLUSIVE"):
        page.run()
        assert not page.exception
        assert "busy right now" in page.warning[0].value
        assert [b.label for b in page.button] == ["Try again"]
    click(page, "Try again")
    assert page.metric[0].value == "€100.00"
    assert not page.warning


def test_app_reports_a_lock_while_loading_the_game(path, monkeypatch):
    # initialize() succeeded, but the game itself cannot be read yet.
    token = db.create_game(path, "exam_week")

    def busy_load(*args):
        raise db.DatabaseBusy(db.BUSY)

    monkeypatch.setattr(db, "load", busy_load)
    page = AppTest.from_file(str(APP), default_timeout=10)
    page.query_params["game"] = token
    page.run()
    assert not page.exception
    assert "busy right now" in page.warning[0].value
    assert [b.label for b in page.button] == ["Try again"]
    assert not page.error


def test_app_does_not_retry_a_busy_purchase(path, monkeypatch):
    token = db.create_game(path, "exam_week")
    calls = []

    def busy_buy(*args):
        calls.append(args)
        raise db.DatabaseBusy(db.BUSY)

    page = AppTest.from_file(str(APP), default_timeout=10)
    page.query_params["game"] = token
    page.run()
    monkeypatch.setattr(db, "buy", busy_buy)
    click(page, "Buy")
    assert len(calls) == 1
    assert "busy right now" in page.error[0].value
    assert db.load(path, token)[0]["cash"] == 10000
