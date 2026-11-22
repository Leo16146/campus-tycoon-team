"""Daily result summary and product-specific plan errors."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db


APP = Path(__file__).resolve().parents[1] / "app.py"
# AppTest runs use a 60 s timeout: the first run in a fresh environment imports
# pandas and pyarrow and took about 16 s in a clean clone.
PRODUCTS = ["Kaffee", "Wasser", "Müsliriegel"]
PREMIUM = {"Kaffee": "8.00", "Wasser": "2.00", "Müsliriegel": "4.00"}
REFERENCE = {"Kaffee": "4.00", "Wasser": "1.00", "Müsliriegel": "2.00"}


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "polish.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    return path


def open_app(token):
    page = AppTest.from_file(str(APP), default_timeout=60)
    page.query_params["game"] = token
    return page.run()


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


def summaries(page):
    return [i.value for i in page.info if i.value.startswith("Day ")]


def play_day(path, token, day, prices, quantities):
    db.apply_plan(path, token, day, dict(zip(PRODUCTS, quantities)), dict(prices))
    db.trade(path, token, day)


# --- Daily result summary -----------------------------------------------------

def test_no_summary_before_the_first_trading_day(path):
    page = open_app(db.create_game(path, "exam_week"))
    assert summaries(page) == []


def test_summary_appears_right_after_trading(path):
    # Test 23, day 1: 5/5/5 at premium prices -> 15 units, €70.00 revenue, €52.50
    # gross profit; the baseline earns €35.00 on Exam Week day 1.
    token = db.create_game(path, "exam_week")
    page = open_app(token)
    for name, quantity in zip(PRODUCTS, (5, 5, 5)):
        page.number_input(key=f"buy_{name}").set_value(quantity).run()
        page.text_input(key=f"price_{name}").set_value(PREMIUM[name]).run()
    click(page, "Apply purchases and prices")
    click(page, "Start trading day")
    assert page.success[0].value == "Day 1 complete."
    assert summaries(page) == ["Day 1 result: 15 units sold · revenue €70.00 · "
                               "gross profit €52.50 · baseline gross profit €35.00"]


def test_summary_shows_a_day_below_the_baseline(path):
    # Premium prices on Open Day sell nothing; the baseline earns €49.00 that day.
    token = db.create_game(path, "exam_week")
    play_day(path, token, 1, PREMIUM, (5, 5, 5))
    play_day(path, token, 2, PREMIUM, (10, 5, 5))
    play_day(path, token, 3, PREMIUM, (10, 5, 5))
    play_day(path, token, 4, PREMIUM, (0, 0, 0))
    page = open_app(token)
    assert summaries(page) == ["Day 4 result: 0 units sold · revenue €0.00 · "
                               "gross profit €0.00 · baseline gross profit €49.00"]


def test_summary_on_the_final_screen_and_only_for_its_own_game(path):
    a = db.create_game(path, "heatwave")
    b = db.create_game(path, "heatwave")
    for day in range(1, 5):
        db.trade(path, a, day)
    # Heatwave day 5 (Cool change): 12 coffee at €4.00 -> €48.00 revenue, €24.00 gross
    # profit; the baseline earns €39.00 that day.
    play_day(path, a, 5, REFERENCE, (12, 0, 0))
    play_day(path, b, 1, REFERENCE, (0, 16, 0))
    page_a, page_b = open_app(a), open_app(b)
    assert page_a.metric[1].value == "Complete"
    assert summaries(page_a) == ["Day 5 result: 12 units sold · revenue €48.00 · "
                                 "gross profit €24.00 · baseline gross profit €39.00"]
    # B: 16 water at €1.00 on Warm morning -> €16.00 revenue, €8.00 gross profit.
    assert summaries(page_b) == ["Day 1 result: 16 units sold · revenue €16.00 · "
                                 "gross profit €8.00 · baseline gross profit €38.00"]


# --- Product-specific errors --------------------------------------------------

@pytest.mark.parametrize(("prices", "quantities", "message"), [
    (dict(REFERENCE, Kaffee="abc"), (1, 0, 0), "Coffee: Use a decimal point and at most two decimals, e.g. 4.50 (no comma, no € symbol)."),
    (dict(REFERENCE, Kaffee="4,00"), (1, 0, 0), "Coffee: Use a decimal point and at most two decimals, e.g. 4.50 (no comma, no € symbol)."),
    (dict(REFERENCE, Kaffee="€4.00"), (1, 0, 0), "Coffee: Use a decimal point and at most two decimals, e.g. 4.50 (no comma, no € symbol)."),
    (dict(REFERENCE, Wasser="0"), (0, 0, 0), "Water: The selling price must be positive."),
    (dict(REFERENCE, Kaffee="", Wasser="x"), (0, 0, 0), "Coffee: "),
    (REFERENCE, (0, 0, -1), "Granola bar: Enter a whole number of 0 or more to buy."),
])
def test_plan_errors_name_the_product(path, prices, quantities, message):
    token = db.create_game(path, "exam_week")
    before = db.load(path, token)
    with pytest.raises(ValueError) as error:
        db.apply_plan(path, token, 1, dict(zip(PRODUCTS, quantities)), prices)
    assert str(error.value).startswith(message)
    assert db.load(path, token) == before


def test_the_app_shows_which_price_is_invalid(path):
    token = db.create_game(path, "exam_week")
    page = open_app(token)
    page.text_input(key="price_Müsliriegel").set_value("2.001").run()
    click(page, "Apply purchases and prices")
    assert page.error[0].value == "Granola bar: Use a decimal point and at most two decimals, e.g. 4.50 (no comma, no € symbol)."
    # The field itself explains the format before anything goes wrong.
    assert page.text_input(key="price_Müsliriegel").help == (
        "Use a decimal point, e.g. 4.50. No comma, no € symbol.")
