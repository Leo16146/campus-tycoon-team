"""CSV export of the daily results (specs/campus-week.md, test 32)."""
from pathlib import Path

import pytest
import streamlit
from streamlit.testing.v1 import AppTest

import db
from logic import history_csv


APP = Path(__file__).resolve().parents[1] / "app.py"
# AppTest runs use a 60 s timeout: the first run in a fresh environment imports
# pandas and pyarrow and took about 16 s in a clean clone.


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "csv.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    return path


def test_csv_lists_each_product_per_day_in_euros(path):
    # Exam Week day 1: 12 coffee at €4.00 -> 10 sold; day 2 (demand 20) sells the last 2.
    token = db.create_game(path, "exam_week")
    db.buy(path, token, 1, "Kaffee", 12)
    db.trade(path, token, 1)
    db.trade(path, token, 2)
    lines = history_csv(db.load(path, token)[2]).splitlines()
    assert lines == [
        "Day,Product,Units sold,Revenue (EUR),Cost of goods sold (EUR),Gross profit (EUR)",
        "1,Coffee,10,40.00,20.00,20.00",
        "1,Water,0,0.00,0.00,0.00",
        "1,Granola bar,0,0.00,0.00,0.00",
        "2,Coffee,2,8.00,4.00,4.00",
        "2,Water,0,0.00,0.00,0.00",
        "2,Granola bar,0,0.00,0.00,0.00",
    ]


def test_app_offers_only_its_own_game_without_the_token(path, monkeypatch):
    a = db.create_game(path, "heatwave")
    b = db.create_game(path, "heatwave")
    db.buy(path, a, 1, "Wasser", 16)
    db.trade(path, a, 1)
    db.buy(path, b, 1, "Kaffee", 3)
    db.trade(path, b, 1)
    calls = []

    def fake_download_button(label, data, file_name, mime, **kwargs):
        calls.append({"label": label, "data": data, "file_name": file_name, "mime": mime})
        return False

    monkeypatch.setattr(streamlit, "download_button", fake_download_button)
    page = AppTest.from_file(str(APP), default_timeout=60)
    page.query_params["game"] = a
    page.run()
    assert not page.exception
    assert len(calls) == 1
    call = calls[0]
    assert call["file_name"] == "campus-week-heatwave.csv"
    assert call["mime"] == "text/csv"
    # Game A sold 16 water at €1.00 on Warm morning; game B's coffee is not included.
    assert call["data"].splitlines()[1:] == ["1,Coffee,0,0.00,0.00,0.00",
                                             "1,Water,16,16.00,8.00,8.00",
                                             "1,Granola bar,0,0.00,0.00,0.00"]
    for token in (a, b):
        assert token not in call["data"] and token not in call["file_name"]


def test_no_download_before_the_first_trading_day(path, monkeypatch):
    calls = []
    monkeypatch.setattr(streamlit, "download_button", lambda *args, **kwargs: calls.append(1))
    page = AppTest.from_file(str(APP), default_timeout=60)
    page.query_params["game"] = db.create_game(path, "exam_week")
    page.run()
    assert not page.exception
    assert calls == []
