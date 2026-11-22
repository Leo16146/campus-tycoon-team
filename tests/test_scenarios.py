"""Scenarios, demand tiers and settlement with events (specs/campus-week.md, P2)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db
from logic import EVENTS, NORMAL, SCENARIOS, demand, sales_for_product, todays_event


APP = Path(__file__).resolve().parents[1] / "app.py"
# AppTest runs use a 60 s timeout: the first run in a fresh environment imports
# pandas and pyarrow and took about 16 s in a clean clone.
PRODUCTS = ["Kaffee", "Wasser", "Müsliriegel"]


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "scenarios.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    return path


def state(path, token):
    game, products, history = db.load(path, token)
    return game["day"], game["cash"], [p["stock"] for p in products], history


def day_lines(history, day):
    return [(row["name"], row["sold"], row["revenue"], row["expense"], row["profit"])
            for row in history if row["day"] == day]


def test_every_scenario_defines_five_days_for_all_products():
    assert set(EVENTS) == set(SCENARIOS)
    for days in EVENTS.values():
        assert len(days) == 5
        for _, tiers in days:
            assert list(tiers) == PRODUCTS


# Copied by hand from the scenario tables in specs/campus-week.md:
# day, event, coffee, water, granola bar.
SPEC_TABLES = {
    "exam_week": [
        (1, "Normal day", (10, 5), (10, 5), (10, 5)),
        (2, "Revision rush", (20, 10), (10, 5), (10, 5)),
        (3, "Exam day", (20, 10), (10, 5), (10, 5)),
        (4, "Open Day", (14, 0), (14, 0), (14, 0)),
        (5, "Normal day", (10, 5), (10, 5), (10, 5)),
    ],
    "heatwave": [
        (1, "Warm morning", (10, 5), (16, 8), (10, 5)),
        (2, "Heatwave", (6, 3), (24, 12), (8, 4)),
        (3, "Heatwave", (6, 3), (24, 12), (8, 4)),
        (4, "Sports day", (8, 4), (30, 3), (12, 2)),
        (5, "Cool change", (12, 6), (10, 5), (10, 5)),
    ],
}


@pytest.mark.parametrize("scenario", list(SPEC_TABLES))
def test_events_match_the_spec_tables(scenario):
    for day, name, coffee, water, bar in SPEC_TABLES[scenario]:
        assert todays_event(scenario, day) == (
            name, {"Kaffee": coffee, "Wasser": water, "Müsliriegel": bar})


@pytest.mark.parametrize("day", [0, 6])
def test_there_is_no_event_outside_the_five_days(day):
    with pytest.raises(ValueError, match="no event"):
        todays_event("exam_week", day)


@pytest.mark.parametrize(("tiers", "reference", "prices", "expected"), [
    (NORMAL, 400, [400, 401, 800, 801], [10, 5, 5, 0]),       # spec test 19
    ((20, 10), 400, [400, 401, 800, 801], [20, 10, 10, 0]),   # spec test 20
    ((30, 3), 100, [100, 101, 200, 201], [30, 3, 3, 0]),      # spec test 21
    ((14, 0), 400, [400, 401, 800, 801], [14, 0, 0, 0]),      # Open Day
])
def test_demand_per_price_tier(tiers, reference, prices, expected):
    assert [demand(price, reference, tiers) for price in prices] == expected


def test_scarce_stock_can_favour_the_high_price():
    # Spec test 21a: water on Sports day (30, 3) with only 3 units in stock.
    water = dict(stock=3, cost=50, reference=100)
    assert sales_for_product(dict(water, price=100), (30, 3)) == (3, 300, 150, 150)
    assert sales_for_product(dict(water, price=200), (30, 3)) == (3, 600, 150, 450)


def test_revision_rush_sells_all_twelve_coffees(path):
    # Spec test 22a.
    token = db.create_game(path, "exam_week")
    db.trade(path, token, 1)
    db.buy(path, token, 2, "Kaffee", 12)
    db.trade(path, token, 2)
    day, cash, stock, history = state(path, token)
    assert (day, cash, stock) == (3, 12400, [0, 0, 0])
    assert day_lines(history, 2)[0] == ("Kaffee", 12, 4800, 2400, 2400)


def test_price_above_twice_the_reference_sells_nothing(path):
    # Spec test 22b: €8.01 sells nothing even on Revision rush.
    token = db.create_game(path, "exam_week")
    db.trade(path, token, 1)
    db.buy(path, token, 2, "Kaffee", 12)
    db.set_price(path, token, 2, "Kaffee", "8.01")
    db.trade(path, token, 2)
    day, cash, stock, history = state(path, token)
    assert (day, cash, stock) == (3, 7600, [12, 0, 0])
    assert day_lines(history, 2)[0] == ("Kaffee", 0, 0, 0, 0)


def test_leftover_stock_sells_on_the_next_day(path):
    # Spec test 22c.
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 12)
    db.trade(path, token, 1)
    assert state(path, token)[:3] == (2, 11600, [2, 0, 0])
    db.trade(path, token, 2)
    day, cash, stock, history = state(path, token)
    assert (day, cash, stock) == (3, 12400, [0, 0, 0])
    assert day_lines(history, 1)[0] == ("Kaffee", 10, 4000, 2000, 2000)
    assert day_lines(history, 2)[0] == ("Kaffee", 2, 800, 400, 400)


def test_sports_day_mixed_price_tiers(path):
    # Spec test 22d.
    token = db.create_game(path, "heatwave")
    for day in range(1, 4):
        db.trade(path, token, day)
    db.set_price(path, token, 4, "Kaffee", "8.00")
    db.buy(path, token, 4, "Kaffee", 4)
    db.buy(path, token, 4, "Wasser", 30)
    db.buy(path, token, 4, "Müsliriegel", 12)
    db.trade(path, token, 4)
    day, cash, stock, history = state(path, token)
    lines = day_lines(history, 4)
    assert lines == [("Kaffee", 4, 3200, 800, 2400),
                     ("Wasser", 30, 3000, 1500, 1500),
                     ("Müsliriegel", 12, 2400, 1200, 1200)]
    assert [sum(line[i] for line in lines) for i in range(1, 5)] == [46, 8600, 3500, 5100]
    assert (day, cash, stock) == (5, 10000 - 3500 + 8600, [0, 0, 0])


def test_same_actions_differ_by_scenario(path):
    # Both games sell 10 water at €1.00 on day 2, but demand differs: 10 vs 24.
    exam = db.create_game(path, "exam_week")
    heat = db.create_game(path, "heatwave")
    for token in (exam, heat):
        db.trade(path, token, 1)
        db.buy(path, token, 2, "Wasser", 30)
        db.trade(path, token, 2)
    assert day_lines(state(path, exam)[3], 2)[1] == ("Wasser", 10, 1000, 500, 500)
    assert day_lines(state(path, heat)[3], 2)[1] == ("Wasser", 24, 2400, 1200, 1200)


def open_app(token):
    page = AppTest.from_file(str(APP), default_timeout=60)
    page.query_params["game"] = token
    return page.run()


def event_heading(page):
    return next(h.value for h in page.subheader if h.value.startswith("Today's event"))


def coffee_caption(page):
    return next(c.value for c in page.caption if c.value.startswith("Demand:"))


def test_open_day_is_shown_and_expected_sales_follow_it(path):
    # Spec test 29.
    token = db.create_game(path, "exam_week")
    for day in range(1, 4):
        db.trade(path, token, day)
    db.buy(path, token, 4, "Kaffee", 14)
    db.set_price(path, token, 4, "Kaffee", "8.00")
    page = open_app(token)
    assert not page.exception
    assert event_heading(page) == "Today's event: Open Day"
    event = page.table[1].value
    assert event["Product"].tolist() == ["Coffee", "Water", "Granola bar"]
    assert event["Demand at or below reference price"].tolist() == [14, 14, 14]
    assert event.columns.tolist() == [
        "Product", "Demand at or below reference price",
        "Demand above reference price, up to and including twice it"]
    assert event["Demand above reference price, up to and including twice it"].tolist() == [0, 0, 0]
    assert any(i.value.startswith("Above twice the reference price, demand is 0.") for i in page.info)
    assert coffee_caption(page) == "Demand: 0 · In stock: 14 · Expected sales: 0 · Cost: €0.00"


def test_expected_sales_match_the_settlement(path):
    # Expected sales use today's event and the stock; the settlement uses the same rule.
    token = db.create_game(path, "exam_week")
    db.trade(path, token, 1)
    db.buy(path, token, 2, "Kaffee", 12)
    page = open_app(token)
    assert event_heading(page) == "Today's event: Revision rush"
    assert coffee_caption(page) == "Demand: 20 · In stock: 12 · Expected sales: 12 · Cost: €0.00"
    next(b for b in page.button if b.label == "Start trading day").click().run()
    assert not page.exception
    assert day_lines(state(path, token)[3], 2)[0][1] == 12
    assert event_heading(page) == "Today's event: Exam day"


def test_finished_game_shows_no_event(path):
    token = db.create_game(path, "heatwave")
    for day in range(1, 6):
        db.trade(path, token, day)
    page = open_app(token)
    assert not page.exception
    assert not any(s.value.startswith("Today's event") for s in page.subheader)
    assert page.metric[1].value == "Complete"
