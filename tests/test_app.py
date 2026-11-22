import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db


APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "ui.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    return path


def open_app(token=None):
    page = AppTest.from_file(str(APP), default_timeout=10)
    if token is not None:
        page.query_params["game"] = token
    return page.run()


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


def labels(page):
    return [button.label for button in page.button]


def test_start_page_without_game_link(path):
    # Spec test 14c.
    other = db.create_game(path, "exam_week")
    db.buy(path, other, 1, "Kaffee", 7)
    page = open_app()
    assert not page.exception
    assert page.radio[0].options == ["Exam Week", "Heatwave"]
    assert labels(page) == ["Start game"]
    assert not page.metric and not page.table
    assert len(db.load(path, other)[1]) == 3


@pytest.mark.parametrize("token", ["", "abc", "A" * 43])
def test_empty_or_unknown_link_is_rejected(path, token):
    # Spec tests 9 and 14d: an empty ?game= is an invalid link, not the start page.
    page = open_app(token)
    assert not page.exception
    assert "not valid" in page.error[0].value
    assert labels(page) == ["Start a new game"]
    assert not page.radio and not page.metric
    click(page, "Start a new game")
    assert "game" not in page.query_params
    assert labels(page) == ["Start game"]


@pytest.mark.parametrize("token", ["", "abc", "!" * 43])
def test_malformed_link_never_opens_the_database(tmp_path, monkeypatch, token):
    # Spec test 9: the app checks the format before db.initialize() opens the file.
    missing = tmp_path / "never-created.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(missing))
    page = open_app(token)
    assert not page.exception
    assert "not valid" in page.error[0].value
    assert labels(page) == ["Start a new game"]
    assert not missing.exists()


def test_start_another_game_keeps_the_current_game(path):
    # "Start another game" leaves the game without changing it.
    page = open_app()
    click(page, "Start game")
    a = page.query_params["game"]
    page.number_input[0].set_value(3).run()
    click(page, "Buy")
    a_before = db.load(path, a)
    assert "Bookmark its link" in page.caption[-1].value
    click(page, "Start another game")
    assert "game" not in page.query_params
    assert labels(page) == ["Start game"]
    assert db.load(path, a) == a_before
    click(page, "Start game")
    b = page.query_params["game"]
    assert b != a
    assert page.metric[0].value == "€100.00"
    reopened = open_app(a)
    assert reopened.metric[0].value == "€94.00"
    assert reopened.table[0].value["Stock"].tolist() == [3, 0, 0]
    assert db.load(path, a) == a_before


def test_retired_scenario_shows_a_message(path):
    # Spec test 14b.
    token = db.create_game(path, "exam_week")
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE games SET scenario = 'retired_week'")
    page = open_app(token)
    assert not page.exception
    assert "no longer available" in page.error[0].value
    assert labels(page) == ["Start a new game"]


def test_clicks_and_new_session(path):
    # Spec tests 1, 7 and 8: start a game, play day 1, reopen the link in a new session.
    page = open_app()
    page.radio[0].set_value("heatwave").run()
    click(page, "Start game")
    token = page.query_params["game"]
    assert len(token) == 43
    assert page.caption[0].value == "Scenario: Heatwave"
    assert page.selectbox[0].options == ["Coffee", "Water", "Granola bar"]
    page.number_input[0].set_value(10).run()
    assert "€20.00" in page.markdown[0].value
    click(page, "Buy")
    assert page.metric[0].value == "€80.00"
    page.number_input[0].set_value(41).run()
    assert "€82.00" in page.markdown[0].value
    click(page, "Buy")
    assert "cash" in page.error[0].value
    click(page, "Start trading day")
    page.run()
    for view in (page, open_app(token)):
        assert not view.exception
        assert view.metric[0].value == "€120.00"
        assert view.metric[1].value == "2 of 5"
        assert view.expander[0].label == "Day 1"
        assert len(view.expander) == 1
        assert view.table[-1].value["Product"].tolist() == ["Coffee", "Water", "Granola bar", "Total"]
        assert view.table[-1].value.iloc[-1].tolist() == [
            "Total", 10, "€40.00", "€20.00", "€20.00"]


def test_two_windows_trade_the_same_day_once(path):
    # Spec test 7.
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 10)
    first, second = open_app(token), open_app(token)
    click(first, "Start trading day")
    click(second, "Start trading day")
    assert "game has changed" in second.error[0].value
    game, _, history = db.load(path, token)
    assert (game["day"], game["cash"]) == (2, 12000)
    assert len(history) == 3


def test_switching_links_clears_inputs_of_the_previous_game(path):
    # Spec test 11.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "exam_week")
    page = open_app(a)
    page.number_input[0].set_value(7).run()
    click(page, "Delete this game")
    assert page.warning
    page.query_params["game"] = b
    page.run()
    assert not page.exception
    assert page.number_input[0].value == 1
    assert not page.warning
    assert labels(page)[-2:] == ["Delete this game", "Start another game"]
    assert db.load(path, a)[0]["day"] == 1


def test_delete_requires_confirmation(path):
    # Spec tests 4, 5 and 10.
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "exam_week")
    db.buy(path, b, 1, "Wasser", 3)
    a_before, b_before = db.load(path, a), db.load(path, b)
    page = open_app(a)
    click(page, "Delete this game")
    assert "Delete this game?" in page.warning[0].value
    click(page, "Cancel")
    assert db.load(path, a) == a_before
    click(page, "Delete this game")
    click(page, "Delete game")
    assert "game" not in page.query_params
    assert page.success[0].value == "Game deleted."
    assert labels(page) == ["Start game"]
    assert db.load(path, b) == b_before
    reopened = open_app(a)
    assert "not valid" in reopened.error[0].value
    assert labels(reopened) == ["Start a new game"]


def test_sales_by_product_uses_actual_daily_prices(path):
    # Spec test 22e (solo demand rule until P2).
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 15)
    db.buy(path, token, 1, "Wasser", 2)
    db.trade(path, token, 1)
    db.set_price(path, token, 2, "Kaffee", "4.01")
    for day in range(2, 6):
        db.trade(path, token, day)

    page = open_app(token)
    assert not page.exception
    table = page.table[1].value
    assert table.columns.tolist() == ["Product", "Units sold", "Revenue", "Gross profit"]
    assert table.values.tolist() == [
        ["Coffee", 15, "€60.05", "€30.05"],
        ["Water", 2, "€2.00", "€1.00"],
        ["Granola bar", 0, "€0.00", "€0.00"],
        ["Total", 17, "€62.05", "€31.05"],
    ]


def test_final_result_values_remaining_stock_at_cost(path):
    # Spec test 22f: two unsold coffees count €4.00.
    token = db.create_game(path, "exam_week")
    for day in range(1, 5):
        db.trade(path, token, day)
    db.buy(path, token, 5, "Kaffee", 12)
    db.buy(path, token, 5, "Wasser", 4)
    db.trade(path, token, 5)
    page = open_app(token)
    assert not page.exception
    # Looked up by label: the baseline comparison adds three more metrics below.
    values = {m.label: m.value for m in page.metric}
    assert [values[label] for label in ("Final cash", "Remaining stock at cost",
                                        "Overall gain / loss")] == ["€118.00", "€4.00", "€22.00"]
    assert labels(page) == ["Delete this game", "Start another game"]


def test_edited_price_persists_and_changes_sales(path):
    token = db.create_game(path, "exam_week")
    page = open_app(token)
    assert page.caption[2].value == "Demand: 10 · In stock: 0 · Expected sales: 0"
    page.number_input[0].set_value(10).run()
    click(page, "Buy")
    assert page.caption[2].value == "Demand: 10 · In stock: 10 · Expected sales: 10"
    page.text_input[0].set_value("4.01").run()
    assert page.caption[2].value == "Demand: 5 · In stock: 10 · Expected sales: 5"
    page = open_app(token)
    assert page.text_input[0].value == "4.01"
    page.text_input[0].set_value("-2").run()
    assert page.error and page.text_input[0].value == "4.01"
    click(page, "Start trading day")
    page = open_app(token)
    assert not page.exception
    assert page.metric[0].value == "€100.05"
    assert page.text_input[0].value == "4.01"
    assert page.table[0].value["Stock"].tolist() == [5, 0, 0]
    assert len(page.expander) == 1
    assert page.table[-1].value.iloc[-1].tolist() == [
        "Total", 5, "€20.05", "€10.00", "€10.05"]
