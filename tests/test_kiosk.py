import sqlite3
from contextlib import closing

import pytest

import db
from logic import demand, sales_for_product


@pytest.fixture
def kiosk(tmp_path):
    path = tmp_path / "kiosk.sqlite3"
    db.initialize(path)
    return path, db.create_game(path, "exam_week")


def test_first_day_and_resume(kiosk):
    path, token = kiosk
    game, products, history = db.load(path, token)
    assert (game["day"], game["cash"]) == (1, 10000)
    assert [(p["name"], p["stock"], p["price"]) for p in products] == [
        ("Kaffee", 0, 400), ("Wasser", 0, 100), ("Müsliriegel", 0, 200)]
    assert not history
    db.buy(path, token, 1, "Kaffee", 10)
    with pytest.raises(ValueError, match="cash"):
        db.buy(path, token, 1, "Kaffee", 41)
    game, products, history = db.load(path, token)
    assert (game["day"], game["cash"]) == (1, 8000)
    assert [p["stock"] for p in products] == [10, 0, 0]
    assert not history
    db.trade(path, token, 1)
    with pytest.raises(ValueError, match="game has changed"):
        db.trade(path, token, 1)
    db.initialize(path)
    game, products, history = db.load(path, token)
    assert (game["day"], game["cash"]) == (2, 12000)
    assert [(p["stock"], p["price"]) for p in products] == [(0, 400), (0, 100), (0, 200)]
    assert [tuple(row) for row in history] == [
        (1, "Kaffee", 10, 4000, 2000, 2000),
        (1, "Wasser", 0, 0, 0, 0),
        (1, "Müsliriegel", 0, 0, 0, 0)]


def test_spend_exact_remaining_cash(kiosk):
    # Spec test 18a.
    path, token = kiosk
    db.buy(path, token, 1, "Kaffee", 10)
    db.buy(path, token, 1, "Kaffee", 40)
    game, products, _ = db.load(path, token)
    assert game["cash"] == 0
    assert products[0]["stock"] == 50


def test_unaffordable_purchase(kiosk):
    # Spec test 15: 51 coffee cost €102.00.
    path, token = kiosk
    before = db.load(path, token)
    with pytest.raises(ValueError, match="cash"):
        db.buy(path, token, 1, "Kaffee", 51)
    assert db.load(path, token) == before


def test_stock_ties_up_cash(kiosk):
    # Spec test 18: after 45 coffee only €10.00 remain, 21 water would cost €10.50.
    path, token = kiosk
    db.buy(path, token, 1, "Kaffee", 45)
    with pytest.raises(ValueError, match="cash"):
        db.buy(path, token, 1, "Wasser", 21)
    game, products, _ = db.load(path, token)
    assert game["cash"] == 1000
    assert [p["stock"] for p in products] == [45, 0, 0]


@pytest.mark.parametrize("quantity", [0, -1, 1.5])
def test_invalid_purchase(kiosk, quantity):
    # Spec test 16.
    path, token = kiosk
    before = db.load(path, token)
    with pytest.raises(ValueError, match="quantity"):
        db.buy(path, token, 1, "Kaffee", quantity)
    assert db.load(path, token) == before


@pytest.mark.parametrize(("price", "expected"), [(400, 10), (401, 5), (800, 5), (801, 0)])
def test_demand_boundaries(price, expected):
    assert demand(price, 400) == expected


@pytest.mark.parametrize("stock", [0, 3])
def test_limited_stock(stock):
    product = dict(stock=stock, price=400, reference=400, cost=200)
    assert sales_for_product(product) == (stock, stock * 400, stock * 200, stock * 200)


def test_mixed_sales(kiosk):
    path, token = kiosk
    db.buy(path, token, 1, "Kaffee", 12)
    db.buy(path, token, 1, "Wasser", 4)
    db.trade(path, token, 1)
    game, products, history = db.load(path, token)
    assert (game["day"], game["cash"]) == (2, 11800)
    assert [p["stock"] for p in products] == [2, 0, 0]
    assert [sum(row[key] for row in history)
            for key in ("sold", "revenue", "expense", "profit")] == [14, 4400, 2200, 2200]


def test_interrupted_trade_rolls_back(kiosk):
    # Spec test 13.
    path, token = kiosk
    db.buy(path, token, 1, "Kaffee", 10)
    before = db.load(path, token)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("""CREATE TRIGGER interrupt_trade BEFORE UPDATE ON games
                        BEGIN SELECT RAISE(ABORT, 'Testabbruch'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="Testabbruch"):
        db.trade(path, token, 1)
    assert db.load(path, token) == before


@pytest.mark.parametrize("text", ["0", "-0.01", "4.001", "abc", "NaN", ""])
def test_rejected_price_preserves_saved_game(kiosk, text):
    # Spec test 17.
    path, token = kiosk
    db.set_price(path, token, 1, "Kaffee", "4.01")
    before = db.load(path, token)
    with pytest.raises(ValueError):
        db.set_price(path, token, 1, "Kaffee", text)
    assert db.load(path, token) == before


@pytest.mark.parametrize(("action", "message"), [
    (lambda path, token: db.buy(path, token, 1, "Kaffee", 1), "game has changed"),
    (lambda path, token: db.set_price(path, token, 1, "Kaffee", "5.00"), "game has changed"),
    (lambda path, token: db.buy(path, token, 2, "Tee", 1), "not in the kiosk catalogue"),
    (lambda path, token: db.set_price(path, token, 2, "Tee", "5.00"), "not in the kiosk catalogue"),
])
def test_stale_day_or_unknown_product_is_rejected(kiosk, action, message):
    # The game is on day 2: day 1 is stale, "Tee" is not a product.
    path, token = kiosk
    db.buy(path, token, 1, "Kaffee", 3)
    db.trade(path, token, 1)
    before = db.load(path, token)
    with pytest.raises(ValueError, match=message):
        action(path, token)
    assert db.load(path, token) == before


def test_completed_run_rejects_actions(kiosk):
    # Spec test 12.
    path, token = kiosk
    for day in range(1, 6):
        db.trade(path, token, day)
    finished = db.load(path, token)
    with pytest.raises(ValueError, match="complete"):
        db.buy(path, token, 6, "Wasser", 1)
    with pytest.raises(ValueError, match="complete"):
        db.trade(path, token, 6)
    with pytest.raises(ValueError, match="complete"):
        db.set_price(path, token, 6, "Wasser", "1.01")
    assert db.load(path, token) == finished
