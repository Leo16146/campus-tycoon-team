"""P0 technical spike: private game links on Streamlit Community Cloud.

Throwaway prototype for specs/campus-week.md, not part of the final app.
The database stores only SHA-256 hashes of the tokens.
"""
import hashlib
import os
import re
import secrets
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import streamlit as st


DATABASE = Path(os.environ.get("SPIKE_DB", Path(__file__).with_name("spike.sqlite3")))
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def initialize():
    with closing(sqlite3.connect(DATABASE)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS spike_games (
            token_hash TEXT PRIMARY KEY, counter INTEGER NOT NULL)""")


def create_game():
    token = secrets.token_urlsafe(32)
    with closing(sqlite3.connect(DATABASE)) as conn, conn:
        conn.execute("INSERT INTO spike_games VALUES (?, 0)", (token_hash(token),))
    return token


def load_counter(token):
    if not TOKEN_PATTERN.fullmatch(token):
        return None
    with closing(sqlite3.connect(DATABASE)) as conn:
        row = conn.execute("SELECT counter FROM spike_games WHERE token_hash = ?",
                           (token_hash(token),)).fetchone()
    return None if row is None else row[0]


def add_one(token):
    with closing(sqlite3.connect(DATABASE)) as conn, conn:
        conn.execute("UPDATE spike_games SET counter = counter + 1 WHERE token_hash = ?",
                     (token_hash(token),))


def start_game():
    st.query_params["game"] = create_game()


def back_to_start():
    st.query_params.clear()


st.set_page_config(page_title="P0 token spike")
initialize()
st.title("P0 token spike")
st.caption(f"Python {sys.version.split()[0]} · Streamlit {st.__version__}")

if "game" not in st.query_params:
    st.subheader("Start page")
    st.write("No game link in the URL.")
    st.button("Create game link", on_click=start_game)
else:
    token = st.query_params["game"]
    counter = load_counter(token)
    if counter is None:
        st.error("This game link is not valid or the game is no longer available.")
        st.button("Back to start", on_click=back_to_start)
    else:
        st.subheader("Game")
        st.metric("Counter", counter)
        st.caption(f"Game fingerprint: {token_hash(token)[:8]}")
        st.button("Add one", on_click=add_one, args=(token,))
