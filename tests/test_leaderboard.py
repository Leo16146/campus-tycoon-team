"""Optional scenario leaderboard (specs/daily-plan-and-leaderboard.md, tests L1–L16)."""
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
PREMIUM = {"Kaffee": "8.00", "Wasser": "2.00", "Müsliriegel": "4.00"}
REFERENCE = {"Kaffee": "4.00", "Wasser": "1.00", "Müsliriegel": "2.00"}
# Test 23 of campus-week.md, "Premium except Open Day": ends at €319.00.
WINNING_PLAN = [(PREMIUM, (5, 5, 5)), (PREMIUM, (10, 5, 5)), (PREMIUM, (10, 5, 5)),
                (REFERENCE, (14, 14, 14)), (PREMIUM, (5, 5, 5))]
EMPTY_PLAN = [(REFERENCE, (0, 0, 0))] * 5  # never buys anything: €0.00


@pytest.fixture
def path(tmp_path, monkeypatch):
    path = tmp_path / "leaderboard.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    monkeypatch.setattr(db, "LOCK_TIMEOUT", 0.05)
    db.initialize(path)
    return path


def play(path, scenario, plan):
    token = db.create_game(path, scenario)
    for day, (prices, quantities) in enumerate(plan, start=1):
        db.apply_plan(path, token, day, dict(zip(PRODUCTS, quantities)), dict(prices))
        db.trade(path, token, day)
    return token


def rows(path):
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT entry_id, game_id, nickname, score FROM leaderboard "
                            "ORDER BY entry_id").fetchall()


def all_rows(path):
    with closing(sqlite3.connect(path)) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in ("games", "products", "sales", "leaderboard")}


def board(path, scenario):
    return [(e["rank"], e["nickname"], e["score"]) for e in db.leaderboard(path, scenario)]


def open_app(token=None):
    page = AppTest.from_file(str(APP), default_timeout=60)
    if token is not None:
        page.query_params["game"] = token
    return page.run()


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


@pytest.fixture
def l6(path):
    """Exam Week: Ana €319.00 (first), Ben €0.00, Cleo €319.00 (last). Heatwave: Dan €0.00."""
    games = {"Ana": play(path, "exam_week", WINNING_PLAN),
             "Ben": play(path, "exam_week", EMPTY_PLAN),
             "Cleo": play(path, "exam_week", WINNING_PLAN),
             "Dan": play(path, "heatwave", EMPTY_PLAN)}
    for nickname, token in games.items():
        db.publish_result(path, token, nickname)
    return games


def test_l1_unfinished_game_cannot_be_published(path):
    token = db.create_game(path, "exam_week")
    for day in (1, 2):
        db.trade(path, token, day)
    with pytest.raises(ValueError, match="Finish all five trading days"):
        db.publish_result(path, token, "Ana")
    assert rows(path) == []


def test_l2_score_comes_from_the_saved_game(path):
    token = play(path, "exam_week", WINNING_PLAN)
    db.publish_result(path, token, "Ana")
    assert [(r[2], r[3]) for r in rows(path)] == [("Ana", 31900)]


def test_l3_one_entry_per_game(path):
    token = play(path, "exam_week", WINNING_PLAN)
    db.publish_result(path, token, "Ana")
    with pytest.raises(ValueError, match="already on the leaderboard"):
        db.publish_result(path, token, "Ana again")
    assert len(rows(path)) == 1


@pytest.mark.parametrize("nickname", ["", "ab", "x" * 21, "Leo!", "<b>Leo</b>"])
def test_l4_invalid_nicknames_are_rejected(path, nickname):
    token = play(path, "exam_week", EMPTY_PLAN)
    with pytest.raises(ValueError, match="Use 3–20 letters"):
        db.publish_result(path, token, nickname)
    assert rows(path) == []


def test_l5_nicknames_are_trimmed(path):
    first = play(path, "exam_week", EMPTY_PLAN)
    second = play(path, "exam_week", EMPTY_PLAN)
    db.publish_result(path, first, "  Leo  ")
    db.publish_result(path, second, "Team 4_a-b")
    assert [r[2] for r in rows(path)] == ["Leo", "Team 4_a-b"]


def test_l6_separate_boards_and_shared_ranks(path, l6):
    assert board(path, "exam_week") == [(1, "Ana", 31900), (1, "Cleo", 31900), (3, "Ben", 0)]
    assert board(path, "heatwave") == [(1, "Dan", 0)]


def test_l7_withdraw_and_publish_again(path, l6):
    db.withdraw_result(path, l6["Ana"])
    assert board(path, "exam_week") == [(1, "Cleo", 31900), (2, "Ben", 0)]
    db.publish_result(path, l6["Ana"], "Ana")
    assert board(path, "exam_week") == [(1, "Cleo", 31900), (1, "Ana", 31900), (3, "Ben", 0)]


def test_l8_deleting_a_game_removes_its_entry(path, l6):
    before = [r for r in rows(path) if r[2] != "Ana"]
    db.delete_game(path, l6["Ana"])
    assert rows(path) == before
    assert board(path, "exam_week") == [(1, "Cleo", 31900), (2, "Ben", 0)]


def test_l9_pages_show_ranks_but_never_tokens(path, l6):
    start = open_app()
    tables = [t.value for t in start.table]
    assert [t.columns.tolist() for t in tables] == [["Rank", "Nickname", "Overall gain / loss"]] * 2
    assert tables[0].values.tolist() == [[1, "Ana", "€319.00"], [1, "Cleo", "€319.00"],
                                         [3, "Ben", "€0.00"]]
    assert tables[1].values.tolist() == [[1, "Dan", "€0.00"]]
    final = open_app(l6["Cleo"])
    assert final.success[0].value == "Your rank: 1 of 3 (as Cleo)"
    assert any(c.value.startswith("The leaderboard is stored temporarily") for c in final.caption)
    for page in (start, final):
        texts = ([e.value for e in page.markdown] + [e.value for e in page.caption]
                 + [str(t.value.values.tolist()) for t in page.table])
        assert not any(token in text for token in l6.values() for text in texts)


def test_l10_unknown_or_invalid_tokens_change_nothing(path, l6, tmp_path):
    before = rows(path)
    for token in ("A" * 43, "abc"):
        with pytest.raises(ValueError, match="not valid"):
            db.publish_result(path, token, "Eve")
        with pytest.raises(ValueError, match="not valid"):
            db.withdraw_result(path, token)
    assert rows(path) == before


def test_l11_start_page_shows_the_best_ten(path):
    # Buying k coffee at the reference price sells all k over days 1–2: score 2 × k euros.
    for k in range(12):
        token = play(path, "exam_week", [(REFERENCE, (k, 0, 0))] + EMPTY_PLAN[:4])
        db.publish_result(path, token, f"Player {k:02d}")
    table = open_app().table[0].value
    assert len(table) == 10
    assert table["Nickname"].tolist() == [f"Player {k:02d}" for k in range(11, 1, -1)]
    assert table["Overall gain / loss"].tolist()[:2] == ["€22.00", "€20.00"]


def test_l12_existing_p4_database_gets_the_new_table(path):
    token = play(path, "exam_week", WINNING_PLAN)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("DROP TABLE leaderboard")  # the schema before E2
    with closing(sqlite3.connect(path)) as conn:
        before = {t: conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("games", "products", "sales")}
    db.initialize(path)
    with closing(sqlite3.connect(path)) as conn:
        after = {t: conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("games", "products", "sales")}
        assert conn.execute("SELECT COUNT(*) FROM leaderboard").fetchone() == (0,)
    assert after == before
    db.publish_result(path, token, "Ana")
    assert board(path, "exam_week") == [(1, "Ana", 31900)]


def locked(path):
    other = sqlite3.connect(path, isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    return other


def test_l13_publishing_while_locked(path):
    token = play(path, "exam_week", WINNING_PLAN)
    other = locked(path)
    with pytest.raises(db.DatabaseBusy):
        db.publish_result(path, token, "Ana")
    other.execute("ROLLBACK")
    other.close()
    assert rows(path) == []
    db.publish_result(path, token, "Ana")
    assert len(rows(path)) == 1


def test_l14_empty_boards(path):
    page = open_app()
    assert [c.value for c in page.caption].count("No results published yet.") == 2
    assert not page.table


def test_l15_withdrawing_while_locked(path):
    token = play(path, "exam_week", WINNING_PLAN)
    db.publish_result(path, token, "Ana")
    other = locked(path)
    with pytest.raises(db.DatabaseBusy):
        db.withdraw_result(path, token)
    other.execute("ROLLBACK")
    other.close()
    assert len(rows(path)) == 1
    db.withdraw_result(path, token)
    assert rows(path) == []


def test_l16_failed_delete_keeps_game_and_entry(path):
    token = play(path, "exam_week", WINNING_PLAN)
    db.publish_result(path, token, "Ana")
    before = all_rows(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("""CREATE TRIGGER stop_delete BEFORE DELETE ON games
                        BEGIN SELECT RAISE(ABORT, 'Testabbruch'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="Testabbruch"):
        db.delete_game(path, token)
    assert all_rows(path) == before


def test_publish_and_remove_through_the_app(path):
    token = play(path, "exam_week", WINNING_PLAN)
    page = open_app(token)
    page.text_input(key="nickname").set_value("ab").run()
    click(page, "Publish my result")
    assert page.error[0].value == "Use 3–20 letters, digits, spaces, _ or -."
    assert rows(path) == []
    page.text_input(key="nickname").set_value("Ana").run()
    click(page, "Publish my result")
    assert "Your result is on the leaderboard." in [s.value for s in page.success]
    assert "Your rank: 1 of 1 (as Ana)" in [s.value for s in page.success]
    click(page, "Remove my result")
    assert rows(path) == []
    assert [b.label for b in page.button][0] == "Publish my result"


def test_busy_leaderboard_does_not_hide_the_rest_of_the_final_screen(path, monkeypatch):
    token = play(path, "exam_week", WINNING_PLAN)

    def busy(*args, **kwargs):
        raise db.DatabaseBusy(db.BUSY)

    monkeypatch.setattr(db, "my_entry", busy)
    monkeypatch.setattr(db, "leaderboard", busy)
    page = open_app(token)
    assert not page.exception
    captions = [c.value for c in page.caption]
    assert "Your leaderboard entry could not be loaded right now. Please reload the page in a moment." in captions
    assert "The leaderboard is busy right now. Please reload the page in a moment." in captions
    assert [b.label for b in page.button][-2:] == ["Delete this game", "Start another game"]
    assert page.expander[0].label == "Day 5"
