"""Local storage for a single kiosk."""
import sqlite3
from contextlib import closing

from logic import STARTING_CASH, price_in_cents, purchase_cost, sales_for_product


CATALOG = [("Kaffee", 200, 400), ("Wasser", 50, 100), ("Müsliriegel", 100, 200)]


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(path):
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS game (
            id INTEGER PRIMARY KEY, day INTEGER NOT NULL, cash INTEGER NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY, cost INTEGER NOT NULL, reference INTEGER NOT NULL,
            price INTEGER NOT NULL, stock INTEGER NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sales (
            day INTEGER NOT NULL, name TEXT NOT NULL, sold INTEGER NOT NULL,
            revenue INTEGER NOT NULL, expense INTEGER NOT NULL, profit INTEGER NOT NULL,
            PRIMARY KEY (day, name))""")
        if conn.execute("SELECT id FROM game WHERE id = 1").fetchone() is None:
            conn.execute("INSERT INTO game VALUES (1, 1, ?)", (STARTING_CASH,))
            for name, cost, reference in CATALOG:
                conn.execute("INSERT INTO products VALUES (?, ?, ?, ?, 0)",
                             (name, cost, reference, reference))


def load(path):
    with closing(connect(path)) as conn:
        conn.execute("BEGIN")
        game = conn.execute("SELECT day, cash FROM game WHERE id = 1").fetchone()
        products = conn.execute("SELECT * FROM products ORDER BY rowid").fetchall()
        history = conn.execute("SELECT * FROM sales ORDER BY day, rowid").fetchall()
        return game, products, history


def current_game(conn, expected_day):
    game = conn.execute("SELECT day, cash FROM game WHERE id = 1").fetchone()
    if game["day"] != expected_day:
        raise ValueError("The game has changed. Check the current trading day.")
    if game["day"] > 5:
        raise ValueError("All five trading days are complete.")
    return game


def buy(path, day, name, quantity):
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game = current_game(conn, day)
        product = conn.execute("SELECT cost FROM products WHERE name = ?", (name,)).fetchone()
        if product is None:
            raise ValueError("This product is not in the kiosk catalogue.")
        total = purchase_cost(quantity, product["cost"], game["cash"])
        conn.execute("UPDATE game SET cash = cash - ? WHERE id = 1", (total,))
        conn.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (quantity, name))


def set_price(path, day, name, text):
    price = price_in_cents(text)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        current_game(conn, day)
        changed = conn.execute("UPDATE products SET price = ? WHERE name = ?", (price, name))
        if changed.rowcount != 1:
            raise ValueError("This product is not in the kiosk catalogue.")


def trade(path, day):
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        current_game(conn, day)
        total_revenue = 0
        for product in conn.execute("SELECT * FROM products ORDER BY rowid").fetchall():
            sold, revenue, expense, profit = sales_for_product(product)
            name = product["name"]
            conn.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)",
                         (day, name, sold, revenue, expense, profit))
            conn.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (sold, name))
            total_revenue += revenue
        conn.execute("UPDATE game SET cash = cash + ?, day = day + 1 WHERE id = 1",
                     (total_revenue,))


def reset_game(path):
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM sales")
        conn.execute("UPDATE products SET stock = 0, price = reference")
        conn.execute("UPDATE game SET day = 1, cash = ? WHERE id = 1", (STARTING_CASH,))
