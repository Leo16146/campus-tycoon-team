import sqlite3


def test_sqlite_query():
    connection = sqlite3.connect(":memory:")
    try:
        row = connection.execute("SELECT 2 + 3").fetchone()
        assert row == (5,)
    finally:
        connection.close()
