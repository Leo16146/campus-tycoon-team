"""SQLite storage for separate games. Each game is opened with its private token."""
import hashlib
import re
import secrets
import sqlite3
from contextlib import closing

from logic import (CATALOG, SCENARIOS, STARTING_CASH, price_in_cents, purchase_cost,
                   sales_for_product, todays_event)


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
INVALID_LINK = ("This game link is not valid or the game is no longer available. "
                "Games are stored temporarily and may be removed.")
RETIRED_SCENARIO = "This game uses a scenario that is no longer available."
SOLO_SCHEMA = "This database uses the solo schema. Set CAMPUS_TYCOON_DB to a new file."


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_token(token):
    """Reject malformed tokens before the database is opened."""
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        raise ValueError(INVALID_LINK)


def initialize(path):
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "game" in tables and "games" not in tables:
            raise ValueError(SOLO_SCHEMA)
        conn.execute("""CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
            scenario TEXT NOT NULL, day INTEGER NOT NULL, cash INTEGER NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            game_id INTEGER NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL,
            cost INTEGER NOT NULL, reference INTEGER NOT NULL,
            price INTEGER NOT NULL, stock INTEGER NOT NULL,
            PRIMARY KEY (game_id, name))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sales (
            game_id INTEGER NOT NULL, day INTEGER NOT NULL, name TEXT NOT NULL,
            sold INTEGER NOT NULL, revenue INTEGER NOT NULL,
            expense INTEGER NOT NULL, profit INTEGER NOT NULL,
            PRIMARY KEY (game_id, day, name))""")


def create_game(path, scenario):
    """Create a game and return its token. Only the token's hash is stored."""
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario.")
    token = secrets.token_urlsafe(32)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game_id = conn.execute(
            "INSERT INTO games (token_hash, scenario, day, cash) VALUES (?, ?, 1, ?)",
            (token_hash(token), scenario, STARTING_CASH)).lastrowid
        for position, (name, cost, reference) in enumerate(CATALOG):
            conn.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, 0)",
                         (game_id, position, name, cost, reference, reference))
    return token


def authorized_game(conn, token):
    """Find the game that belongs to this token. Its id never comes from the browser."""
    game = conn.execute("SELECT * FROM games WHERE token_hash = ?",
                        (token_hash(token),)).fetchone()
    if game is None:
        raise ValueError(INVALID_LINK)
    return game


def playable_game(conn, token):
    game = authorized_game(conn, token)
    if game["scenario"] not in SCENARIOS:
        raise ValueError(RETIRED_SCENARIO)
    return game


def load(path, token):
    check_token(token)
    with closing(connect(path)) as conn:
        conn.execute("BEGIN")
        game = playable_game(conn, token)
        products = conn.execute(
            """SELECT name, cost, reference, price, stock FROM products
               WHERE game_id = ? ORDER BY position""", (game["id"],)).fetchall()
        history = conn.execute(
            """SELECT day, name, sold, revenue, expense, profit FROM sales
               WHERE game_id = ? ORDER BY day, rowid""", (game["id"],)).fetchall()
        state = {"scenario": game["scenario"], "day": game["day"], "cash": game["cash"]}
        return state, products, history


def current_game(conn, token, expected_day):
    game = playable_game(conn, token)
    if game["day"] != expected_day:
        raise ValueError("The game has changed. Check the current trading day.")
    if game["day"] > 5:
        raise ValueError("All five trading days are complete.")
    return game


def buy(path, token, day, name, quantity):
    check_token(token)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game = current_game(conn, token, day)
        product = conn.execute("SELECT cost FROM products WHERE game_id = ? AND name = ?",
                               (game["id"], name)).fetchone()
        if product is None:
            raise ValueError("This product is not in the kiosk catalogue.")
        total = purchase_cost(quantity, product["cost"], game["cash"])
        conn.execute("UPDATE games SET cash = cash - ? WHERE id = ?", (total, game["id"]))
        conn.execute("UPDATE products SET stock = stock + ? WHERE game_id = ? AND name = ?",
                     (quantity, game["id"], name))


def set_price(path, token, day, name, text):
    check_token(token)
    price = price_in_cents(text)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game = current_game(conn, token, day)
        changed = conn.execute("UPDATE products SET price = ? WHERE game_id = ? AND name = ?",
                               (price, game["id"], name))
        if changed.rowcount != 1:
            raise ValueError("This product is not in the kiosk catalogue.")


def trade(path, token, day):
    check_token(token)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game = current_game(conn, token, day)
        _, tiers = todays_event(game["scenario"], day)
        total_revenue = 0
        products = conn.execute("SELECT * FROM products WHERE game_id = ? ORDER BY position",
                                (game["id"],)).fetchall()
        for product in products:
            name = product["name"]
            sold, revenue, expense, profit = sales_for_product(product, tiers[name])
            conn.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (game["id"], day, name, sold, revenue, expense, profit))
            conn.execute("UPDATE products SET stock = stock - ? WHERE game_id = ? AND name = ?",
                         (sold, game["id"], name))
            total_revenue += revenue
        conn.execute("UPDATE games SET cash = cash + ?, day = day + 1 WHERE id = ?",
                     (total_revenue, game["id"]))


def delete_game(path, token):
    """Delete this game only. Afterwards its link no longer works."""
    check_token(token)
    with closing(connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        game = authorized_game(conn, token)
        conn.execute("DELETE FROM sales WHERE game_id = ?", (game["id"],))
        conn.execute("DELETE FROM products WHERE game_id = ?", (game["id"],))
        conn.execute("DELETE FROM games WHERE id = ?", (game["id"],))
