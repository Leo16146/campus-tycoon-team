"""Baseline strategy and final comparison (specs/campus-week.md, tests 23–28, 30–31)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db
from logic import NORMAL, baseline_restock, baseline_results, final_result


APP = Path(__file__).resolve().parents[1] / "app.py"
# AppTest runs use a 60 s timeout: the first run in a fresh environment imports
# pandas and pyarrow and took about 16 s in a clean clone.
PRODUCTS = ["Kaffee", "Wasser", "Müsliriegel"]
PREMIUM = ("8.00", "2.00", "4.00")
REFERENCE = ("4.00", "1.00", "2.00")

# Test 23, "Premium except Open Day": prices and purchases (coffee, water, bars) per day.
PREMIUM_EXCEPT_OPEN_DAY = [
    (PREMIUM, (5, 5, 5)),
    (PREMIUM, (10, 5, 5)),
    (PREMIUM, (10, 5, 5)),
    (REFERENCE, (14, 14, 14)),
    (PREMIUM, (5, 5, 5)),
]
# Test 24: premium on Open Day too, so nothing is bought that day.
ALWAYS_PREMIUM = PREMIUM_EXCEPT_OPEN_DAY[:3] + [(PREMIUM, (0, 0, 0))] + PREMIUM_EXCEPT_OPEN_DAY[4:]


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "baseline.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    return path


def play(path, scenario, plan):
    """Play a game through db and return its token and the cash after each day."""
    token = db.create_game(path, scenario)
    cash_after = []
    for day, (prices, purchases) in enumerate(plan, start=1):
        for name, price, quantity in zip(PRODUCTS, prices, purchases):
            db.set_price(path, token, day, name, price)
            if quantity:
                db.buy(path, token, day, name, quantity)
        db.trade(path, token, day)
        cash_after.append(db.load(path, token)[0]["cash"])
    return token, cash_after


def overall(path, token):
    game, products, _ = db.load(path, token)
    return final_result(game["cash"], products)[1]


def daily_profit(path, token):
    history = db.load(path, token)[2]
    return [sum(row["profit"] for row in history if row["day"] == day) for day in range(1, 6)]


def test_premium_except_open_day(path):
    # Spec test 23.
    token, cash_after = play(path, "exam_week", PREMIUM_EXCEPT_OPEN_DAY)
    assert daily_profit(path, token) == [5250, 8250, 8250, 4900, 5250]
    assert cash_after == [15250, 23500, 31750, 36650, 41900]
    assert overall(path, token) == 31900


def test_always_premium(path):
    # Spec test 24.
    token, cash_after = play(path, "exam_week", ALWAYS_PREMIUM)
    assert daily_profit(path, token)[3] == 0
    assert cash_after[3:] == [31750, 37000]
    assert overall(path, token) == 27000


def test_baseline_exam_week():
    # Spec test 25.
    days, result = baseline_results("exam_week")
    assert days == [(3500, 13500), (5500, 19000), (5500, 24500), (4900, 29400), (3500, 32900)]
    assert result == 22900


def test_baseline_heatwave():
    # Spec test 26.
    days, result = baseline_results("heatwave")
    assert days == [(3800, 13800), (3200, 17000), (3200, 20200), (4300, 24500), (3900, 28400)]
    assert result == 18400


@pytest.mark.parametrize("scenario", ["exam_week", "heatwave"])
def test_baseline_is_deterministic(scenario):
    # Spec test 27.
    assert baseline_results(scenario) == baseline_results(scenario)


def test_baseline_buys_only_what_it_can_afford():
    # Spec test 28: €5.00 and demand 10/10/10 buy 2 coffee, 2 water, 0 bars.
    empty = {name: 0 for name in PRODUCTS}
    tiers = {name: NORMAL for name in PRODUCTS}
    stock, cash, bought = baseline_restock(empty, 500, tiers)
    assert bought == {"Kaffee": 2, "Wasser": 2, "Müsliriegel": 0}
    assert stock == bought
    assert cash == 0


def test_baseline_restock_counts_existing_stock():
    stock, cash, bought = baseline_restock(
        {"Kaffee": 4, "Wasser": 12, "Müsliriegel": 0}, 10000,
        {"Kaffee": (20, 10), "Wasser": NORMAL, "Müsliriegel": NORMAL})
    assert bought == {"Kaffee": 16, "Wasser": 0, "Müsliriegel": 10}
    assert stock == {"Kaffee": 20, "Wasser": 12, "Müsliriegel": 10}
    assert cash == 10000 - 16 * 200 - 10 * 100


def open_app(token):
    page = AppTest.from_file(str(APP), default_timeout=60)
    page.query_params["game"] = token
    return page.run()


def metrics(page):
    return {m.label: m.value for m in page.metric}


def comparison_rows(page):
    table = page.table[2].value
    assert table.columns.tolist() == [
        "Day", "Your gross profit", "Baseline gross profit", "Difference"]
    return table.values.tolist()


def test_final_comparison_above_the_baseline(path):
    # Spec test 30.
    token, _ = play(path, "exam_week", PREMIUM_EXCEPT_OPEN_DAY)
    page = open_app(token)
    assert not page.exception
    values = metrics(page)
    assert values["Overall gain / loss"] == "€319.00"
    assert values["Baseline overall gain / loss"] == "€229.00"
    assert values["Difference (you − baseline)"] == "+€90.00"
    assert comparison_rows(page) == [
        [1, "€52.50", "€35.00", "+€17.50"],
        [2, "€82.50", "€55.00", "+€27.50"],
        [3, "€82.50", "€55.00", "+€27.50"],
        [4, "€49.00", "€49.00", "€0.00"],
        [5, "€52.50", "€35.00", "+€17.50"],
    ]
    caption = next(c.value for c in page.caption if c.value.startswith("Baseline strategy"))
    assert "not the best possible strategy" in caption


def test_final_comparison_below_the_baseline(path):
    # A game that never buys anything ends €229.00 below the baseline.
    token, _ = play(path, "exam_week", [(REFERENCE, (0, 0, 0))] * 5)
    page = open_app(token)
    assert not page.exception
    values = metrics(page)
    assert values["Overall gain / loss"] == "€0.00"
    assert values["Baseline overall gain / loss"] == "€229.00"
    assert values["Difference (you − baseline)"] == "-€229.00"
    assert comparison_rows(page)[3] == [4, "€0.00", "€49.00", "-€49.00"]


def test_report_shows_only_its_own_game(path):
    # Spec test 31: A (Exam Week, premium) and B (Heatwave, nothing bought) are both finished.
    a, _ = play(path, "exam_week", PREMIUM_EXCEPT_OPEN_DAY)
    b, _ = play(path, "heatwave", [(REFERENCE, (0, 0, 0))] * 5)
    page_a, page_b = open_app(a), open_app(b)
    assert metrics(page_a)["Overall gain / loss"] == "€319.00"
    assert metrics(page_a)["Baseline overall gain / loss"] == "€229.00"
    assert page_a.table[1].value.values.tolist()[-1] == ["Total", 112, "€458.00", "€319.00"]
    assert metrics(page_b)["Overall gain / loss"] == "€0.00"
    assert metrics(page_b)["Baseline overall gain / loss"] == "€184.00"
    assert page_b.table[1].value.values.tolist()[-1] == ["Total", 0, "€0.00", "€0.00"]
    assert [row[1] for row in comparison_rows(page_b)] == ["€0.00"] * 5
