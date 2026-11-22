import os
from pathlib import Path

import streamlit as st

import db
from logic import (SCENARIOS, baseline_results, demand, final_result, sales_for_product,
                   todays_event)


DATABASE = Path(os.environ.get("CAMPUS_TYCOON_DB", Path(__file__).with_name("campus_week.sqlite3")))


# Saved games use the original product names as SQLite keys.
PRODUCT_LABELS = {"Kaffee": "Coffee", "Wasser": "Water", "Müsliriegel": "Granola bar"}

BUSY_LOADING = "The game is busy right now and could not be loaded. Please try again in a moment."

# Errors that are shown to the player as a message instead of a crash.
USER_ERRORS = (ValueError, db.DatabaseBusy)

# Session values that belong to one game and must not carry over to another link.
GAME_SESSION_KEYS = ("product", "quantity", "confirm_delete", "notice")


def euros(cents):
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}€{whole:,}.{fraction:02d}"


def signed_euros(cents):
    """Show a difference with an explicit sign, for example +€90.00 or -€229.00."""
    return ("+" if cents > 0 else "") + euros(cents)


def daily_gross_profit(history, day):
    return sum(row["profit"] for row in history if row["day"] == day)


def sales_summary_row(label, sales):
    return {
        "Product": label,
        "Units sold": sum(row["sold"] for row in sales),
        "Revenue": euros(sum(row["revenue"] for row in sales)),
        "Gross profit": euros(sum(row["profit"] for row in sales)),
    }


def show_notice():
    if "notice" in st.session_state:
        kind, message = st.session_state.pop("notice")
        if kind == "success":
            st.success(message)
        else:
            st.error(message)


def start_game(scenario):
    try:
        st.query_params["game"] = db.create_game(DATABASE, scenario)
    except USER_ERRORS as error:
        st.session_state.notice = ("error", str(error))


def leave_game():
    st.query_params.clear()


def forget_other_game(token):
    """Clear inputs from a previous game when the link changes."""
    active = db.token_hash(token)
    if st.session_state.get("active_game") != active:
        for key in GAME_SESSION_KEYS:
            st.session_state.pop(key, None)
        st.session_state.active_game = active


def buy_selected(token, day, name, quantity):
    try:
        db.buy(DATABASE, token, day, name, quantity)
        st.session_state.notice = ("success", f"Purchased {quantity} × {PRODUCT_LABELS[name]}.")
    except USER_ERRORS as error:
        st.session_state.notice = ("error", str(error))


def save_price(token, day, name):
    key = f"price_{name}"
    try:
        db.set_price(DATABASE, token, day, name, st.session_state[key])
        st.session_state.notice = ("success", f"Selling price saved for {PRODUCT_LABELS[name]}.")
    except USER_ERRORS as error:
        st.session_state.notice = ("error", str(error))


def trade_day(token, day):
    try:
        db.trade(DATABASE, token, day)
        st.session_state.notice = ("success", f"Day {day} complete.")
    except USER_ERRORS as error:
        st.session_state.notice = ("error", str(error))


def ask_delete():
    st.session_state.confirm_delete = True


def cancel_delete():
    st.session_state.confirm_delete = False


def delete_current_game(token):
    """Leave the game only if it was deleted; otherwise keep its link in the URL."""
    st.session_state.confirm_delete = False
    try:
        db.delete_game(DATABASE, token)
    except USER_ERRORS as error:
        st.session_state.notice = ("error", str(error))
        return
    st.session_state.notice = ("success", "Game deleted.")
    st.query_params.clear()


def stop_when_busy():
    st.warning(BUSY_LOADING)
    st.button("Try again")
    st.stop()


def stop_with_link_error(message):
    st.error(message)
    st.button("Start a new game", on_click=leave_game)
    st.stop()


st.set_page_config(page_title="Campus Kiosk")
st.title("Campus Kiosk")

# A malformed link is rejected before the database is opened.
if "game" in st.query_params:
    try:
        db.check_token(st.query_params["game"])
    except ValueError as error:
        stop_with_link_error(str(error))

try:
    db.initialize(DATABASE)
except db.DatabaseBusy:
    stop_when_busy()
except ValueError as error:
    st.error(str(error))
    st.stop()

if "game" not in st.query_params:
    show_notice()
    st.subheader("Start a private game")
    st.write("Each game has its own private link. Anyone with the link can play or delete the game.")
    scenario = st.radio("Scenario", list(SCENARIOS), format_func=SCENARIOS.__getitem__, key="scenario")
    st.button("Start game", type="primary", on_click=start_game, args=(scenario,))
    st.stop()

token = st.query_params["game"]
forget_other_game(token)
try:
    game, products, history = db.load(DATABASE, token)
except db.DatabaseBusy:
    stop_when_busy()
except ValueError as error:
    stop_with_link_error(str(error))

day = game["day"]
st.caption(f"Scenario: {SCENARIOS[game['scenario']]}")
st.info("Bookmark this page to continue later. Games are stored temporarily on the server "
        "and may be removed, for example after a restart.")
left, right = st.columns(2)
left.metric("Cash", euros(game["cash"]))
right.metric("Trading day", f"{day} of 5" if day <= 5 else "Complete")
st.progress((day - 1) / 5, text=f"{day - 1} of 5 days completed")

st.subheader("Inventory")
st.table([{"Product": PRODUCT_LABELS[p["name"]], "Stock": p["stock"], "Unit cost": euros(p["cost"]),
           "Reference price": euros(p["reference"]), "Selling price": euros(p["price"])}
          for p in products])

show_notice()

if day <= 5:
    event_name, tiers = todays_event(game["scenario"], day)
    st.subheader(f"Today's event: {event_name}")
    st.table([{"Product": PRODUCT_LABELS[p["name"]],
               "Demand at or below reference price": tiers[p["name"]][0],
               "Demand above reference price, up to and including twice it": tiers[p["name"]][1]}
              for p in products])
    st.info("Above twice the reference price, demand is 0. "
            "At twice the reference price, each unit earns three times as much gross profit "
            "as at the reference price. Sales are limited to the stock on hand.")
    st.subheader("Buy stock")
    by_name = {p["name"]: p for p in products}
    name = st.selectbox("Product", list(by_name), format_func=PRODUCT_LABELS.__getitem__, key="product")
    quantity = st.number_input("Quantity", min_value=1, step=1, value=1, key="quantity")
    st.write(f"Purchase total: **{euros(quantity * by_name[name]['cost'])}**")
    st.button("Buy", on_click=buy_selected, args=(token, day, name, quantity))
    st.subheader("Selling prices")
    st.caption("Enter a price in euros and press Enter to save it.")
    for product in products:
        name = product["name"]
        key = f"price_{name}"
        whole, fraction = divmod(product["price"], 100)
        st.session_state[key] = f"{whole}.{fraction:02d}"
        st.text_input(f"{PRODUCT_LABELS[name]} (€)", key=key, max_chars=21,
                      on_change=save_price, args=(token, day, name))
        daily_demand = demand(product["price"], product["reference"], tiers[name])
        expected_units = sales_for_product(product, tiers[name])[0]
        st.caption(f"Demand: {daily_demand} · In stock: {product['stock']} · Expected sales: {expected_units}")
    st.subheader("Trading")
    st.write("Today's demand depends on the event shown above and on each selling price. "
             "Sales are limited to the stock on hand. Unsold stock stays in the inventory.")
    st.button("Start trading day", type="primary", on_click=trade_day, args=(token, day))

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

    baseline_days, baseline_result = baseline_results(game["scenario"])
    st.subheader("Comparison with the baseline strategy")
    you_col, baseline_col, difference_col = st.columns(3)
    you_col.metric("Your overall gain / loss", euros(result))
    baseline_col.metric("Baseline overall gain / loss", euros(baseline_result))
    difference_col.metric("Difference (you − baseline)", signed_euros(result - baseline_result))
    st.caption("Baseline strategy: a simple reference that keeps every selling price at the "
               "reference price and restocks each day to the demand at that price. "
               "It is not the best possible strategy.")
    comparison = []
    for number, (baseline_profit, _) in enumerate(baseline_days, start=1):
        yours = daily_gross_profit(history, number)
        comparison.append({"Day": number, "Your gross profit": euros(yours),
                           "Baseline gross profit": euros(baseline_profit),
                           "Difference": signed_euros(yours - baseline_profit)})
    st.table(comparison)

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
if st.session_state.get("confirm_delete"):
    st.warning("Delete this game? Its stock and daily results will be removed "
               "and this link will stop working.")
    cancel, confirm = st.columns(2)
    cancel.button("Cancel", on_click=cancel_delete)
    confirm.button("Delete game", on_click=delete_current_game, args=(token,))
else:
    delete_col, other_col = st.columns(2)
    delete_col.button("Delete this game", on_click=ask_delete)
    other_col.button("Start another game", on_click=leave_game)
    st.caption("Your current game is kept. Bookmark its link before leaving.")
