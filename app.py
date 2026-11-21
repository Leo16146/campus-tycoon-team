import os
from pathlib import Path

import streamlit as st

import db
from logic import demand, final_result, sales_for_product


DATABASE = Path(os.environ.get("CAMPUS_TYCOON_DB", Path(__file__).with_name("kiosk.sqlite3")))


# Saved games use the original product names as SQLite keys.
PRODUCT_LABELS = {"Kaffee": "Coffee", "Wasser": "Water", "Müsliriegel": "Granola bar"}


def euros(cents):
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}€{whole:,}.{fraction:02d}"


def sales_summary_row(label, sales):
    return {
        "Product": label,
        "Units sold": sum(row["sold"] for row in sales),
        "Revenue": euros(sum(row["revenue"] for row in sales)),
        "Gross profit": euros(sum(row["profit"] for row in sales)),
    }


def buy_selected(day, name, quantity):
    try:
        db.buy(DATABASE, day, name, quantity)
        st.session_state.notice = ("success", f"Purchased {quantity} × {PRODUCT_LABELS[name]}.")
    except ValueError as error:
        st.session_state.notice = ("error", str(error))


def save_price(day, name):
    key = f"price_{name}"
    try:
        db.set_price(DATABASE, day, name, st.session_state[key])
        st.session_state.notice = ("success", f"Selling price saved for {PRODUCT_LABELS[name]}.")
    except ValueError as error:
        st.session_state.notice = ("error", str(error))


def trade_day(day):
    try:
        db.trade(DATABASE, day)
        st.session_state.notice = ("success", f"Day {day} complete.")
    except ValueError as error:
        st.session_state.notice = ("error", str(error))


def start_new_game():
    db.reset_game(DATABASE)
    for key in ("confirm_restart", "product", "quantity"):
        st.session_state.pop(key, None)
    st.session_state.notice = ("success", "New game started.")


st.set_page_config(page_title="Campus Kiosk")
db.initialize(DATABASE)
game, products, history = db.load(DATABASE)
day = game["day"]
st.title("Campus Kiosk")
left, right = st.columns(2)
left.metric("Cash", euros(game["cash"]))
right.metric("Trading day", f"{day} of 5" if day <= 5 else "Complete")
st.progress((day - 1) / 5, text=f"{day - 1} of 5 days completed")

st.subheader("Inventory")
st.table([{"Product": PRODUCT_LABELS[p["name"]], "Stock": p["stock"], "Unit cost": euros(p["cost"]),
           "Reference price": euros(p["reference"]), "Selling price": euros(p["price"])}
          for p in products])

if "notice" in st.session_state:
    kind, message = st.session_state.pop("notice")
    if kind == "success":
        st.success(message)
    else:
        st.error(message)

if day <= 5:
    st.subheader("Buy stock")
    by_name = {p["name"]: p for p in products}
    name = st.selectbox("Product", list(by_name), format_func=PRODUCT_LABELS.__getitem__, key="product")
    quantity = st.number_input("Quantity", min_value=1, step=1, value=1, key="quantity")
    st.write(f"Purchase total: **{euros(quantity * by_name[name]['cost'])}**")
    st.button("Buy", on_click=buy_selected, args=(day, name, quantity))
    st.subheader("Selling prices")
    st.caption("Enter a price in euros and press Enter to save it.")
    for product in products:
        name = product["name"]
        key = f"price_{name}"
        whole, fraction = divmod(product["price"], 100)
        st.session_state[key] = f"{whole}.{fraction:02d}"
        st.text_input(f"{PRODUCT_LABELS[name]} (€)", key=key, max_chars=21,
                      on_change=save_price, args=(day, name))
        daily_demand = demand(product["price"], product["reference"])
        expected_units = sales_for_product(product)[0]
        st.caption(f"Demand: {daily_demand} · In stock: {product['stock']} · Expected sales: {expected_units}")
    st.subheader("Trading")
    st.write("Daily demand is 10 units per product at or below its reference price. "
             "Above that price, demand falls to 5 units, or to 0 if the price exceeds "
             "twice the reference price. Sales are limited to the stock on hand.")
    st.button("Start trading day", type="primary", on_click=trade_day, args=(day,))

else:
    stock_value, result = final_result(game["cash"], products)
    st.subheader("Final results")
    cash_col, stock_col, result_col = st.columns(3)
    cash_col.metric("Final cash", euros(game["cash"]))
    stock_col.metric("Remaining stock at cost", euros(stock_value))
    result_col.metric("Overall gain / loss", euros(result))
    st.caption("Final cash + remaining stock at purchase cost − €100.00 starting cash.")
    st.subheader("Sales by product")
    summary = []
    for product in products:
        name = product["name"]
        sales = [row for row in history if row["name"] == name]
        summary.append(sales_summary_row(PRODUCT_LABELS[name], sales))
    summary.append(sales_summary_row("Total", history))
    st.table(summary)

if history:
    st.subheader("Daily results")
    for completed_day in range(day - 1, 0, -1):
        lines = [row for row in history if row["day"] == completed_day]
        totals = {key: sum(row[key] for row in lines)
                  for key in ("sold", "revenue", "expense", "profit")}
        with st.expander(f"Day {completed_day}", expanded=completed_day == day - 1):
            report = [dict(row, label=PRODUCT_LABELS[row["name"]]) for row in lines]
            report.append({"label": "Total", **totals})
            st.table([{"Product": row["label"], "Units sold": row["sold"],
                       "Revenue": euros(row["revenue"]), "Cost of goods sold": euros(row["expense"]),
                       "Gross profit": euros(row["profit"])}
                      for row in report])

st.divider()
if st.session_state.get("confirm_restart"):
    st.warning("Replace your current game? Your stock and daily results will be cleared. "
               "You will start day 1 with €100.00.")
    cancel, confirm = st.columns(2)
    if cancel.button("Cancel"):
        st.session_state.confirm_restart = False
        st.rerun()
    confirm.button("Start new game", on_click=start_new_game)
else:
    if st.button("New game"):
        st.session_state.confirm_restart = True
        st.rerun()
