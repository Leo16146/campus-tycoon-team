from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_sales_by_product_uses_actual_daily_prices(tmp_path, monkeypatch):
    import db

    path = tmp_path / "summary.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    db.buy(path, 1, "Kaffee", 15)
    db.buy(path, 1, "Wasser", 2)
    db.trade(path, 1)
    db.set_price(path, 2, "Kaffee", "4.01")
    for day in range(2, 6):
        db.trade(path, day)

    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert not page.exception
    table = page.table[1].value
    assert table.columns.tolist() == ["Product", "Units sold", "Revenue", "Gross profit"]
    assert table.values.tolist() == [
        ["Coffee", 15, "€60.05", "€30.05"],
        ["Water", 2, "€2.00", "€1.00"],
        ["Granola bar", 0, "€0.00", "€0.00"],
        ["Total", 17, "€62.05", "€31.05"],
    ]


def test_clicks_and_new_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(tmp_path / "ui.sqlite3"))
    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert page.selectbox[0].options == ["Coffee", "Water", "Granola bar"]
    page.number_input[0].set_value(10).run()
    assert "€20.00" in page.markdown[0].value
    page.button[0].click().run()
    assert page.metric[0].value == "€80.00"
    page.number_input[0].set_value(41).run()
    assert "€82.00" in page.markdown[0].value
    page.button[0].click().run()
    assert "cash" in page.error[0].value
    page.button[1].click().run()
    page.run()
    for view in (page, AppTest.from_file(str(APP), default_timeout=10).run()):
        assert not view.exception
        assert view.metric[0].value == "€120.00"
        assert view.metric[1].value == "2 of 5"
        assert view.expander[0].label == "Day 1"
        assert view.table[-1].value["Product"].tolist() == ["Coffee", "Water", "Granola bar", "Total"]
        assert len(view.expander) == 1
        assert view.table[-1].value.iloc[-1].tolist() == [
            "Total", 10, "€40.00", "€20.00", "€20.00"]


def test_new_game_requires_confirmation_and_persists(tmp_path, monkeypatch):
    import db

    path = tmp_path / "restart.sqlite3"
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(path))
    db.initialize(path)
    fresh = db.load(path)
    for day in range(1, 5):
        db.trade(path, day)
    db.buy(path, 5, "Kaffee", 12)
    db.buy(path, 5, "Wasser", 4)
    db.trade(path, 5)
    finished = db.load(path)

    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert [m.value for m in page.metric[-3:]] == ["€118.00", "€4.00", "€22.00"]
    assert [b.label for b in page.button] == ["New game"]

    def click(label):
        next(button for button in page.button if button.label == label).click().run()
        assert not page.exception

    click("New game")
    assert db.load(path) == finished
    click("Cancel")
    assert db.load(path) == finished
    click("New game")
    click("Start new game")
    assert db.load(path) == fresh
    reopened = AppTest.from_file(str(APP), default_timeout=10).run()
    assert reopened.metric[0].value == "€100.00"
    assert reopened.metric[1].value == "1 of 5"
    assert not reopened.expander


def test_edited_price_persists_and_changes_sales(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DB", str(tmp_path / "prices.sqlite3"))
    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert page.caption[1].value == "Demand: 10 · In stock: 0 · Expected sales: 0"
    page.number_input[0].set_value(10).run()
    page.button[0].click().run()
    assert page.caption[1].value == "Demand: 10 · In stock: 10 · Expected sales: 10"
    page.text_input[0].set_value("4.01").run()
    assert page.caption[1].value == "Demand: 5 · In stock: 10 · Expected sales: 5"
    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert page.text_input[0].value == "4.01"
    page.text_input[0].set_value("-2").run()
    assert page.error and page.text_input[0].value == "4.01"
    page.button[1].click().run()
    page = AppTest.from_file(str(APP), default_timeout=10).run()
    assert not page.exception
    assert page.metric[0].value == "€100.05"
    assert page.text_input[0].value == "4.01"
    assert page.table[0].value["Stock"].tolist() == [5, 0, 0]
    assert len(page.expander) == 1
    assert page.table[-1].value.iloc[-1].tolist() == [
        "Total", 5, "€20.05", "€10.00", "€10.05"]
