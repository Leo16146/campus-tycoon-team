import sqlite3
from contextlib import closing

import pytest

import db
from logic import demand, sales_for_product


@pytest.fixture
def kiosk(tmp_path):
    path = tmp_path / "kiosk.sqlite3"
    db.initialize(path)
    return path


def test_first_day_and_resume(kiosk):
    game, products, history = db.load(kiosk)
    assert tuple(game) == (1, 10000)
    assert [(p["name"], p["stock"], p["price"]) for p in products] == [
        ("Kaffee", 0, 400), ("Wasser", 0, 100), ("Müsliriegel", 0, 200)]
    assert not history
    db.buy(kiosk, 1, "Kaffee", 10)
    with pytest.raises(ValueError, match="cash"):
        db.buy(kiosk, 1, "Kaffee", 41)
    game, products, history = db.load(kiosk)
    assert tuple(game) == (1, 8000)
    assert [p["stock"] for p in products] == [10, 0, 0]
    assert not history
    db.trade(kiosk, 1)
    with pytest.raises(ValueError, match="game has changed"):
        db.trade(kiosk, 1)
    db.initialize(kiosk)
    game, products, history = db.load(kiosk)
    assert tuple(game) == (2, 12000)
    assert [(p["stock"], p["price"]) for p in products] == [(0, 400), (0, 100), (0, 200)]
    assert [tuple(row) for row in history] == [
        (1, "Kaffee", 10, 4000, 2000, 2000),
        (1, "Wasser", 0, 0, 0, 0),
        (1, "Müsliriegel", 0, 0, 0, 0)]


def test_spend_exact_remaining_cash(kiosk):
    db.buy(kiosk, 1, "Kaffee", 10)
    db.buy(kiosk, 1, "Kaffee", 40)
    game, products, _ = db.load(kiosk)
    assert game["cash"] == 0
    assert products[0]["stock"] == 50


@pytest.mark.parametrize("quantity", [0, -1, 1.5])
def test_invalid_purchase(kiosk, quantity):
    before = db.load(kiosk)
    with pytest.raises(ValueError, match="quantity"):
        db.buy(kiosk, 1, "Kaffee", quantity)
    assert db.load(kiosk) == before


@pytest.mark.parametrize(("price", "expected"), [(400, 10), (401, 5), (800, 5), (801, 0)])
def test_demand_boundaries(price, expected):
    assert demand(price, 400) == expected


@pytest.mark.parametrize("stock", [0, 3])
def test_limited_stock(stock):
    product = dict(stock=stock, price=400, reference=400, cost=200)
    assert sales_for_product(product) == (stock, stock * 400, stock * 200, stock * 200)


def test_mixed_sales(kiosk):
    db.buy(kiosk, 1, "Kaffee", 12)
    db.buy(kiosk, 1, "Wasser", 4)
    db.trade(kiosk, 1)
    game, products, history = db.load(kiosk)
    assert tuple(game) == (2, 11800)
    assert [p["stock"] for p in products] == [2, 0, 0]
    assert [sum(row[key] for row in history)
            for key in ("sold", "revenue", "expense", "profit")] == [14, 4400, 2200, 2200]


def test_interrupted_trade_rolls_back(kiosk):
    db.buy(kiosk, 1, "Kaffee", 10)
    before = db.load(kiosk)
    with closing(sqlite3.connect(kiosk)) as conn:
        conn.execute("""CREATE TRIGGER interrupt_trade BEFORE UPDATE ON game
                        BEGIN SELECT RAISE(ABORT, 'Testabbruch'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="Testabbruch"):
        db.trade(kiosk, 1)
    assert db.load(kiosk) == before


@pytest.mark.parametrize("text", ["0", "-0.01", "4.001", "abc", "NaN", ""])
def test_rejected_price_preserves_saved_game(kiosk, text):
    db.set_price(kiosk, 1, "Kaffee", "4.01")
    before = db.load(kiosk)
    with pytest.raises(ValueError):
        db.set_price(kiosk, 1, "Kaffee", text)
    assert db.load(kiosk) == before


def test_completed_run_rejects_actions(kiosk):
    for day in range(1, 6):
        db.trade(kiosk, day)
    finished = db.load(kiosk)
    with pytest.raises(ValueError, match="complete"):
        db.buy(kiosk, 6, "Wasser", 1)
    with pytest.raises(ValueError, match="complete"):
        db.trade(kiosk, 6)
    with pytest.raises(ValueError, match="complete"):
        db.set_price(kiosk, 6, "Wasser", "1.01")
    assert db.load(kiosk) == finished
