"""Separate games and token authorization (specs/campus-week.md, tests 1–14d)."""
import hashlib
import sqlite3
from contextlib import closing

import pytest

import db


@pytest.fixture
def path(tmp_path):
    path = tmp_path / "games.sqlite3"
    db.initialize(path)
    return path


def all_rows(path):
    """Every row of every table, to prove that nothing changed."""
    with closing(sqlite3.connect(path)) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("games", "products", "sales")}


def test_new_game_stores_only_the_token_hash(path):
    # Spec test 1.
    token = db.create_game(path, "exam_week")
    assert len(token) == 43
    rows = all_rows(path)
    assert [(row[1], row[2], row[3], row[4]) for row in rows["games"]] == [
        (hashlib.sha256(token.encode()).hexdigest(), "exam_week", 1, 10000)]
    assert [(row[2], row[5], row[6]) for row in rows["products"]] == [
        ("Kaffee", 400, 0), ("Wasser", 100, 0), ("Müsliriegel", 200, 0)]
    assert rows["sales"] == []
    assert token.encode() not in path.read_bytes()


def test_purchase_changes_only_its_own_game(path):
    # Spec test 2.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "exam_week")
    db.buy(path, a, 1, "Kaffee", 3)
    game_a, products_a, _ = db.load(path, a)
    game_b, products_b, _ = db.load(path, b)
    assert game_a["cash"] == 9400
    assert [p["stock"] for p in products_a] == [3, 0, 0]
    assert game_b["cash"] == 10000
    assert [p["stock"] for p in products_b] == [0, 0, 0]


def test_price_change_changes_only_its_own_game(path):
    # Spec test 3.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "heatwave")
    db.set_price(path, a, 1, "Kaffee", "8.00")
    assert db.load(path, a)[1][0]["price"] == 800
    assert db.load(path, b)[1][0]["price"] == 400


def test_trade_and_history_stay_within_their_own_game(path):
    # Trading A leaves every row of B unchanged; each game loads only its own sales.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "heatwave")
    db.buy(path, a, 1, "Kaffee", 6)
    db.buy(path, b, 1, "Wasser", 8)
    db.set_price(path, b, 1, "Wasser", "1.50")
    db.trade(path, b, 1)
    b_before = db.load(path, b)
    with closing(sqlite3.connect(path)) as conn:
        b_id = conn.execute("SELECT id FROM games WHERE token_hash = ?",
                            (hashlib.sha256(b.encode()).hexdigest(),)).fetchone()[0]
        b_rows = [conn.execute(f"SELECT * FROM {table} WHERE {column} = ? ORDER BY rowid",
                               (b_id,)).fetchall()
                  for table, column in (("games", "id"), ("products", "game_id"),
                                        ("sales", "game_id"))]
    db.trade(path, a, 1)
    db.buy(path, a, 2, "Müsliriegel", 4)
    db.trade(path, a, 2)
    assert db.load(path, b) == b_before
    with closing(sqlite3.connect(path)) as conn:
        assert b_rows == [conn.execute(f"SELECT * FROM {table} WHERE {column} = ? ORDER BY rowid",
                                       (b_id,)).fetchall()
                          for table, column in (("games", "id"), ("products", "game_id"),
                                                ("sales", "game_id"))]
    history_a = db.load(path, a)[2]
    assert [(row["day"], row["name"], row["sold"], row["revenue"]) for row in history_a] == [
        (1, "Kaffee", 6, 2400), (1, "Wasser", 0, 0), (1, "Müsliriegel", 0, 0),
        (2, "Kaffee", 0, 0), (2, "Wasser", 0, 0), (2, "Müsliriegel", 4, 800)]
    history_b = b_before[2]
    assert [(row["day"], row["name"], row["sold"], row["revenue"]) for row in history_b] == [
        (1, "Kaffee", 0, 0), (1, "Wasser", 5, 750), (1, "Müsliriegel", 0, 0)]


def test_delete_removes_only_its_own_game(path):
    # Spec test 4.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "exam_week")
    for token in (a, b):
        db.buy(path, token, 1, "Kaffee", 2)
        db.trade(path, token, 1)
    b_before = db.load(path, b)
    db.delete_game(path, a)
    with pytest.raises(ValueError, match="not valid"):
        db.load(path, a)
    assert db.load(path, b) == b_before
    rows = all_rows(path)
    assert len(rows["games"]) == 1
    assert {row[0] for row in rows["products"] + rows["sales"]} == {rows["games"][0][0]}


def test_second_trade_of_the_same_day_is_rejected(path):
    # Spec test 6.
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 4)
    db.trade(path, token, 1)
    with pytest.raises(ValueError, match="game has changed"):
        db.trade(path, token, 1)
    game, _, history = db.load(path, token)
    assert game["day"] == 2
    assert game["cash"] == 10000 - 800 + 1600
    assert len(history) == 3


@pytest.mark.parametrize("token", ["", "abc", "!" * 43, None])
def test_malformed_token_never_opens_the_database(tmp_path, token):
    # Spec test 9: the format check happens before any database access.
    missing = tmp_path / "never-created.sqlite3"
    for action in (lambda: db.load(missing, token),
                   lambda: db.buy(missing, token, 1, "Kaffee", 1),
                   lambda: db.set_price(missing, token, 1, "Kaffee", "5.00"),
                   lambda: db.trade(missing, token, 1),
                   lambda: db.delete_game(missing, token)):
        with pytest.raises(ValueError, match="not valid"):
            action()
    assert not missing.exists()


def test_unknown_token_changes_nothing(path):
    # Spec tests 9 and 10: a well-formed but unknown or deleted token.
    b = db.create_game(path, "exam_week")
    db.buy(path, b, 1, "Kaffee", 1)
    deleted = db.create_game(path, "exam_week")
    db.delete_game(path, deleted)
    before = all_rows(path)
    for token in ("A" * 43, deleted, b[:-1] + ("A" if b[-1] != "A" else "B")):
        for action in (lambda: db.load(path, token),
                       lambda: db.buy(path, token, 1, "Kaffee", 1),
                       lambda: db.set_price(path, token, 1, "Kaffee", "5.00"),
                       lambda: db.trade(path, token, 1),
                       lambda: db.delete_game(path, token)):
            with pytest.raises(ValueError, match="not valid") as error:
                action()
            assert b not in str(error.value)
    assert all_rows(path) == before


def test_solo_schema_is_left_untouched(tmp_path):
    # Spec test 14.
    path = tmp_path / "solo.sqlite3"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE game (id INTEGER PRIMARY KEY, day INTEGER, cash INTEGER)")
        conn.execute("INSERT INTO game VALUES (1, 2, 12000)")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="solo schema"):
        db.initialize(path)
    assert path.read_bytes() == before
    with closing(sqlite3.connect(path)) as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master")]
        assert tables == ["game"]
        assert conn.execute("SELECT * FROM game").fetchall() == [(1, 2, 12000)]


def test_unknown_scenario_creates_nothing(path):
    # Spec test 14a.
    with pytest.raises(ValueError, match="Unknown scenario"):
        db.create_game(path, "summer_break")
    assert all_rows(path) == {"games": [], "products": [], "sales": []}


def test_retired_scenario_is_reported_and_left_unchanged(path):
    # Spec test 14b.
    token = db.create_game(path, "exam_week")
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE games SET scenario = 'retired_week'")
    before = all_rows(path)
    for action in (lambda: db.load(path, token),
                   lambda: db.buy(path, token, 1, "Kaffee", 1),
                   lambda: db.trade(path, token, 1)):
        with pytest.raises(ValueError, match="no longer available"):
            action()
    assert all_rows(path) == before
