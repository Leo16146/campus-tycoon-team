"""SQLite storage for separate games. Each game is opened with its private token."""
import hashlib
import re
import secrets
import sqlite3
from contextlib import closing, contextmanager

from logic import (CATALOG, SCENARIOS, STARTING_CASH, price_in_cents, purchase_cost,
                   sales_for_product, todays_event)


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
INVALID_LINK = ("This game link is not valid or the game is no longer available. "
                "Games are stored temporarily and may be removed.")
RETIRED_SCENARIO = "This game uses a scenario that is no longer available."
SOLO_SCHEMA = "This database uses the solo schema. Set CAMPUS_TYCOON_DB to a new file."
BUSY = "The game is busy right now. Nothing was changed. Please try again in a moment."
LOCK_TIMEOUT = 5  # seconds SQLite waits for another connection to release its lock


class DatabaseBusy(Exception):
    """Another connection holds the lock; the action did not run and can be tried again."""


def connect(path):
    connection = sqlite3.connect(path, timeout=LOCK_TIMEOUT)
    connection.row_factory = sqlite3.Row
    return connection


def is_lock_error(error):
    return getattr(error, "sqlite_errorname", "").startswith(("SQLITE_BUSY", "SQLITE_LOCKED"))


@contextmanager
def transaction(path, write=True):
    """Run the block as one transaction: commit at the end, roll back on any error.

    A write transaction takes the write lock at the start. If the lock is not
    free within LOCK_TIMEOUT, DatabaseBusy is raised and nothing is changed.
    Other database errors are not hidden.
    """
    with closing(connect(path)) as conn:
        try:
            with conn:
                conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield conn
        except sqlite3.OperationalError as error:
            if is_lock_error(error):
                raise DatabaseBusy(BUSY) from error
            raise


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_token(token):
    """Reject malformed tokens before the database is opened."""
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        raise ValueError(INVALID_LINK)


def table_names(conn):
    return {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}


def initialize(path):
    """Create the tables if they are missing. Once they exist, this only reads,
    so a page load does not wait for another player's write."""
    with transaction(path, write=False) as conn:
        tables = table_names(conn)
    if "game" in tables and "games" not in tables:
        raise ValueError(SOLO_SCHEMA)
    if {"games", "products", "sales"} <= tables:
        return
    with transaction(path) as conn:
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
    with transaction(path) as conn:
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
    with transaction(path, write=False) as conn:
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
    with transaction(path) as conn:
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
    with transaction(path) as conn:
        game = current_game(conn, token, day)
        changed = conn.execute("UPDATE products SET price = ? WHERE game_id = ? AND name = ?",
                               (price, game["id"], name))
        if changed.rowcount != 1:
            raise ValueError("This product is not in the kiosk catalogue.")


def checked_plan(quantities, prices):
    """Validate a daily plan: whole quantities of 0 or more and valid prices for
    exactly the catalogue products. Returns the prices in cents."""
    names = {name for name, _, _ in CATALOG}
    if set(quantities) != names or set(prices) != names:
        raise ValueError("The plan does not match the kiosk catalogue.")
    for quantity in quantities.values():
        if type(quantity) is not int or quantity < 0:
            raise ValueError("Enter a whole number of 0 or more for each purchase.")
    return {name: price_in_cents(text) for name, text in prices.items()}


def apply_plan(path, token, day, quantities, prices):
    """Buy all planned stock and save all prices together, or change nothing."""
    check_token(token)
    with transaction(path) as conn:
        game = current_game(conn, token, day)
        cents = checked_plan(quantities, prices)
        products = conn.execute("SELECT name, cost FROM products WHERE game_id = ? ORDER BY position",
                                (game["id"],)).fetchall()
        total = sum(quantities[p["name"]] * p["cost"] for p in products)
        if total > game["cash"]:
            raise ValueError("Not enough cash for this purchase.")
        conn.execute("UPDATE games SET cash = cash - ? WHERE id = ?", (total, game["id"]))
        for product in products:
            name = product["name"]
            conn.execute("""UPDATE products SET stock = stock + ?, price = ?
                            WHERE game_id = ? AND name = ?""",
                         (quantities[name], cents[name], game["id"], name))


def trade(path, token, day):
    check_token(token)
    with transaction(path) as conn:
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
    with transaction(path) as conn:
        game = authorized_game(conn, token)
        conn.execute("DELETE FROM sales WHERE game_id = ?", (game["id"],))
        conn.execute("DELETE FROM products WHERE game_id = ?", (game["id"],))
        conn.execute("DELETE FROM games WHERE id = ?", (game["id"],))
