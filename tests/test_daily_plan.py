"""Daily plan and "How to play" (specs/daily-plan-and-leaderboard.md, tests U1–U23)."""
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import db


APP = Path(__file__).resolve().parents[1] / "app.py"
# AppTest runs use a 60 s timeout: the first run in a fresh environment imports
# pandas and pyarrow and took about 16 s in a clean clone.
PRODUCTS = ["Kaffee", "Wasser", "Müsliriegel"]
REFERENCE = {"Kaffee": "4.00", "Wasser": "1.00", "Müsliriegel": "2.00"}


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "plan.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    monkeypatch.setattr(db, "LOCK_TIMEOUT", 0.05)
    db.initialize(path)
    return path


def all_rows(path):
    with closing(sqlite3.connect(path)) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("games", "products", "sales")}


def saved(path, token):
    game, products, _ = db.load(path, token)
    return (game["day"], game["cash"], [p["stock"] for p in products],
            [p["price"] for p in products])


def open_app(token=None):
    page = AppTest.from_file(str(APP), default_timeout=60)
    if token is not None:
        page.query_params["game"] = token
    return page.run()


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


def button(page, label):
    return next(b for b in page.button if b.label == label)


def plan(page, name, buy=None, price=None):
    if buy is not None:
        page.number_input(key=f"buy_{name}").set_value(buy).run()
    if price is not None:
        page.text_input(key=f"price_{name}").set_value(price).run()


def fields(page):
    return ([page.number_input(key=f"buy_{n}").value for n in PRODUCTS],
            [page.text_input(key=f"price_{n}").value for n in PRODUCTS])


def captions(page):
    return [c.value for c in page.caption if "In stock:" in c.value]


def total_line(page):
    return next(m.value for m in page.markdown if m.value.startswith("Total purchase cost"))


def new_game(path, scenario="exam_week"):
    token = db.create_game(path, scenario)
    return token, open_app(token)


def full_plan(quantities, prices=REFERENCE):
    return dict(zip(PRODUCTS, quantities)), dict(prices)


# --- Start page ---------------------------------------------------------------

def test_u1_how_to_play_on_the_start_page(path):
    page = open_app()
    text = next(m.value for m in page.markdown if m.value.startswith("**How to play**"))
    assert "**Goal:** end the five trading days with the highest possible overall gain." in text
    assert ("**Each day:** check today's event, buy stock, set selling prices, "
            "start the trading day.") in text
    assert "final cash + remaining stock at unit cost − €100.00" in text
    assert "baseline strategy" in text


# --- Preview, apply, reject ---------------------------------------------------

def test_u2_preview_without_saving(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=10, price="8.00")
    assert captions(page)[0] == "Demand: 5 · In stock: 0 · Expected sales: 5 · Cost: €20.00"
    assert total_line(page) == ("Total purchase cost: **€20.00** · "
                                "Cash after purchases: **€80.00**")
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])


def test_u3_u4_apply_resets_purchases_and_does_not_buy_twice(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=10, price="8.00")
    click(page, "Apply purchases and prices")
    assert page.success[0].value == "Bought 10 × Coffee. Prices saved."
    assert saved(path, token) == (1, 8000, [10, 0, 0], [800, 100, 200])
    assert fields(page) == ([0, 0, 0], ["8.00", "1.00", "2.00"])
    click(page, "Apply purchases and prices")
    assert "Nothing to apply." in [i.value for i in page.info]
    assert saved(path, token) == (1, 8000, [10, 0, 0], [800, 100, 200])


def test_u5_invalid_price_saves_nothing_and_keeps_inputs(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=10, price="abc")
    plan(page, "Wasser", buy=5)
    assert captions(page)[0].startswith("Invalid price")
    click(page, "Apply purchases and prices")
    assert page.error
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])
    assert fields(page) == ([10, 5, 0], ["abc", "1.00", "2.00"])


def test_u6_total_above_cash_saves_nothing(path):
    # 40 coffee (€80.00) and 41 water (€20.50) are each affordable, together not.
    token, page = new_game(path)
    plan(page, "Kaffee", buy=40)
    plan(page, "Wasser", buy=41)
    assert "**€100.50**" in total_line(page)
    assert page.warning[0].value == "The total purchase cost is more than your cash."
    click(page, "Apply purchases and prices")
    assert "Not enough cash" in page.error[0].value
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])


def test_u7_exact_cash_is_accepted(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=40)
    plan(page, "Wasser", buy=40)
    click(page, "Apply purchases and prices")
    assert saved(path, token) == (1, 0, [40, 40, 0], [400, 100, 200])


@pytest.mark.parametrize("quantity", [-1, 1.5])
def test_u8_invalid_quantities_are_rejected(path, quantity):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with pytest.raises(ValueError, match="whole number"):
        db.apply_plan(path, token, 1, *full_plan([quantity, 0, 0]))
    assert all_rows(path) == before


# --- Unapplied changes --------------------------------------------------------

def test_u9_trading_is_blocked_until_the_plan_is_applied(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=5)
    assert button(page, "Start trading day").disabled
    assert "Apply or discard your changes before trading." in [c.value for c in page.caption]
    click(page, "Apply purchases and prices")
    assert not button(page, "Start trading day").disabled


def test_u10_typed_price_survives_other_inputs(path):
    token, page = new_game(path)
    plan(page, "Kaffee", price="8.00")
    plan(page, "Wasser", buy=3)
    assert page.text_input(key="price_Kaffee").value == "8.00"
    assert button(page, "Start trading day").disabled
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])


def test_u11_switching_links_shows_the_other_games_own_values(path):
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "exam_week")
    db.set_price(path, b, 1, "Wasser", "1.50")
    page = open_app(a)
    plan(page, "Kaffee", buy=6, price="7.00")
    page.query_params["game"] = b
    page.run()
    assert fields(page) == ([0, 0, 0], ["4.00", "1.50", "2.00"])
    assert not button(page, "Start trading day").disabled


def test_u12_stale_day_and_finished_game_are_rejected(path):
    token = db.create_game(path, "exam_week")
    db.trade(path, token, 1)
    before = all_rows(path)
    with pytest.raises(ValueError, match="game has changed"):
        db.apply_plan(path, token, 1, *full_plan([1, 0, 0]))
    assert all_rows(path) == before
    for day in range(2, 6):
        db.trade(path, token, day)
    finished = all_rows(path)
    with pytest.raises(ValueError, match="complete"):
        db.apply_plan(path, token, 6, *full_plan([1, 0, 0]))
    assert all_rows(path) == finished


def test_u13_locked_database_saves_nothing_then_applies_once(path):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with closing(sqlite3.connect(path, isolation_level=None)) as other:
        other.execute("BEGIN IMMEDIATE")
        with pytest.raises(db.DatabaseBusy):
            db.apply_plan(path, token, 1, *full_plan([10, 0, 0]))
        other.execute("ROLLBACK")
    assert all_rows(path) == before
    db.apply_plan(path, token, 1, *full_plan([10, 0, 0]))
    assert saved(path, token) == (1, 8000, [10, 0, 0], [400, 100, 200])


# --- Full game through the new interface --------------------------------------

def test_u14_premium_except_open_day_through_the_ui(path):
    premium = {"Kaffee": "8.00", "Wasser": "2.00", "Müsliriegel": "4.00"}
    days = [(premium, [5, 5, 5]), (premium, [10, 5, 5]), (premium, [10, 5, 5]),
            (REFERENCE, [14, 14, 14]), (premium, [5, 5, 5])]
    token, page = new_game(path)
    cash_after = []
    for prices, quantities in days:
        for name, quantity in zip(PRODUCTS, quantities):
            plan(page, name, buy=quantity, price=prices[name])
        click(page, "Apply purchases and prices")
        click(page, "Start trading day")
        cash_after.append(db.load(path, token)[0]["cash"])
    assert cash_after == [15250, 23500, 31750, 36650, 41900]
    values = {m.label: m.value for m in page.metric}
    assert values["Your overall gain / loss"] == "€319.00"
    assert values["Difference (you − baseline)"] == "+€90.00"


# --- Review precisions --------------------------------------------------------

def test_u15_emptied_price_stays_empty_and_blocks(path):
    token, page = new_game(path)
    plan(page, "Kaffee", price="")
    plan(page, "Wasser", buy=3)
    assert page.text_input(key="price_Kaffee").value == ""
    assert captions(page)[0].startswith("Invalid price")
    assert button(page, "Start trading day").disabled
    click(page, "Apply purchases and prices")
    assert page.error
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])
    assert fields(page) == ([0, 3, 0], ["", "1.00", "2.00"])


def test_u16_invalid_or_unknown_token_changes_nothing(path, tmp_path):
    missing = tmp_path / "never-created.sqlite3"
    with pytest.raises(ValueError, match="not valid"):
        db.apply_plan(missing, "abc", 1, *full_plan([1, 0, 0]))
    assert not missing.exists()
    db.create_game(path, "exam_week")
    before = all_rows(path)
    with pytest.raises(ValueError, match="not valid"):
        db.apply_plan(path, "A" * 43, 1, *full_plan([1, 0, 0]))
    assert all_rows(path) == before


def test_u17_applying_in_a_leaves_b_unchanged(path):
    a = db.create_game(path, "exam_week")
    b = db.create_game(path, "heatwave")
    db.buy(path, b, 1, "Müsliriegel", 7)
    db.set_price(path, b, 1, "Kaffee", "6.00")
    with closing(sqlite3.connect(path)) as conn:
        b_id = conn.execute("SELECT id FROM games WHERE scenario = 'heatwave'").fetchone()[0]

    def rows_of_b():
        with closing(sqlite3.connect(path)) as conn:
            return (conn.execute("SELECT * FROM games WHERE id = ?", (b_id,)).fetchall(),
                    conn.execute("SELECT * FROM products WHERE game_id = ?", (b_id,)).fetchall())

    b_before = rows_of_b()
    db.apply_plan(path, a, 1, {"Kaffee": 3, "Wasser": 2, "Müsliriegel": 0},
                  {"Kaffee": "5.00", "Wasser": "1.50", "Müsliriegel": "2.00"})
    assert saved(path, a) == (1, 9300, [3, 2, 0], [500, 150, 200])
    assert rows_of_b() == b_before


def test_u18_failure_on_the_second_product_rolls_everything_back(path):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("""CREATE TRIGGER stop_water BEFORE UPDATE ON products
                        WHEN NEW.name = 'Wasser' BEGIN SELECT RAISE(ABORT, 'Testabbruch'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="Testabbruch"):
        db.apply_plan(path, token, 1, {"Kaffee": 3, "Wasser": 2, "Müsliriegel": 0},
                      {"Kaffee": "5.00", "Wasser": "1.50", "Müsliriegel": "2.00"})
    assert all_rows(path) == before


@pytest.mark.parametrize(("quantities", "prices"), [
    ({"Kaffee": 1, "Wasser": 0}, REFERENCE),
    ({"Kaffee": 1, "Wasser": 0, "Müsliriegel": 0, "Tee": 1}, REFERENCE),
    ({"Kaffee": 1, "Tee": 0, "Müsliriegel": 0}, REFERENCE),
    ({"Kaffee": 1, "Wasser": 0, "Müsliriegel": 0}, {"Kaffee": "4.00", "Wasser": "1.00"}),
    ({"Kaffee": 1, "Wasser": 0, "Müsliriegel": 0}, dict(REFERENCE, Tee="3.00")),
])
def test_u19_plan_must_match_the_catalogue(path, quantities, prices):
    token = db.create_game(path, "exam_week")
    before = all_rows(path)
    with pytest.raises(ValueError, match="does not match the kiosk catalogue"):
        db.apply_plan(path, token, 1, quantities, prices)
    assert all_rows(path) == before


def test_u20_day_finished_in_another_window_discards_the_plan(path):
    token, window_b = new_game(path)
    plan(window_b, "Kaffee", buy=5, price="8.00")
    window_a = open_app(token)
    click(window_a, "Start trading day")
    window_b.run()
    assert window_b.metric[1].value == "2 of 5"
    assert fields(window_b) == ([0, 0, 0], ["4.00", "1.00", "2.00"])
    assert window_b.warning[0].value == "Your plan was discarded because the trading day changed."
    assert saved(path, token) == (2, 10000, [0, 0, 0], [400, 100, 200])


def test_u21_applying_a_plan_for_a_finished_day_is_rejected(path):
    token, window_b = new_game(path)
    plan(window_b, "Kaffee", buy=5, price="8.00")
    db.trade(path, token, 1)
    click(window_b, "Apply purchases and prices")
    assert "game has changed" in window_b.error[0].value
    assert window_b.warning[0].value == "Your plan was discarded because the trading day changed."
    assert window_b.metric[1].value == "2 of 5"
    assert saved(path, token) == (2, 10000, [0, 0, 0], [400, 100, 200])


@pytest.mark.parametrize("text", ["4", "4.0", "4.00"])
def test_u22_prices_are_compared_as_amounts(path, text):
    token, page = new_game(path)
    plan(page, "Kaffee", price=text)
    assert not button(page, "Start trading day").disabled
    assert button(page, "Discard changes").disabled
    click(page, "Apply purchases and prices")
    assert "Nothing to apply." in [i.value for i in page.info]
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])


def test_u23_discard_restores_the_saved_plan(path):
    token, page = new_game(path)
    plan(page, "Kaffee", buy=5)
    plan(page, "Wasser", price="9.99")
    assert not button(page, "Discard changes").disabled
    click(page, "Discard changes")
    assert fields(page) == ([0, 0, 0], ["4.00", "1.00", "2.00"])
    assert saved(path, token) == (1, 10000, [0, 0, 0], [400, 100, 200])
    assert not button(page, "Start trading day").disabled
    assert button(page, "Discard changes").disabled
