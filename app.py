import os
from pathlib import Path

import streamlit as st

import db
from logic import (CATALOG, SCENARIOS, baseline_results, demand, final_result, price_in_cents,
                   sales_for_product, todays_event)


DATABASE = Path(os.environ.get("CAMPUS_TYCOON_DB", Path(__file__).with_name("campus_week.sqlite3")))


# Saved games use the original product names as SQLite keys.
PRODUCT_LABELS = {"Kaffee": "Coffee", "Wasser": "Water", "Müsliriegel": "Granola bar"}

BUSY_LOADING = "The game is busy right now and could not be loaded. Please try again in a moment."

# Errors that are shown to the player as a message instead of a crash.
USER_ERRORS = (ValueError, db.DatabaseBusy)

# Input fields of today's plan: purchases and selling prices per product.
NAMES = [name for name, _, _ in CATALOG]
DRAFT_KEYS = tuple(f"buy_{name}" for name in NAMES) + tuple(f"price_{name}" for name in NAMES)

# Session values that belong to one game and must not carry over to another link.
GAME_SESSION_KEYS = ("confirm_delete", "notices", "draft_of") + DRAFT_KEYS

HOW_TO_PLAY = (
    "**How to play**\n\n"
    "- **Goal:** end the five trading days with the highest possible overall gain.\n"
    "- **Each day:** check today's event, buy stock, set selling prices, start the trading day.\n"
    "- **Score:** final cash + remaining stock at unit cost − €100.00, compared with a "
    "simple baseline strategy.")


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


def price_text(cents):
    whole, fraction = divmod(cents, 100)
    return f"{whole}.{fraction:02d}"


def parsed_price(text):
    """Price in cents, or None if the text is not a valid price."""
    try:
        return price_in_cents(text)
    except ValueError:
        return None


def notify(kind, message):
    """Queue a message (success, info, warning or error) for the next page run."""
    st.session_state.setdefault("notices", []).append((kind, message))


def show_notices():
    show = {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}
    for kind, message in st.session_state.pop("notices", []):
        show[kind](message)


def draft_changed(saved_prices):
    """True if the plan fields differ from the saved game.

    A purchase above 0, an invalid price or a price with another amount counts as a
    change; "4" and "4.00" are the same price. Fields without a value are untouched.
    """
    for name in NAMES:
        if st.session_state.get(f"buy_{name}", 0) > 0:
            return True
        text = st.session_state.get(f"price_{name}")
        if text is not None and parsed_price(text) != saved_prices[name]:
            return True
    return False


def clear_draft():
    for key in DRAFT_KEYS:
        st.session_state.pop(key, None)


def fill_draft(products):
    """Give fields that have no value yet the saved values. An emptied field stays empty."""
    for product in products:
        name = product["name"]
        if f"buy_{name}" not in st.session_state:
            st.session_state[f"buy_{name}"] = 0
        if f"price_{name}" not in st.session_state:
            st.session_state[f"price_{name}"] = price_text(product["price"])


def follow_saved_state(token, seen):
    """Discard a plan that was made for an older saved state, for example after
    another window finished the day or applied its own plan. A message appears
    only if the plan differed from the state it was made for."""
    owner = (db.token_hash(token), seen)
    previous = st.session_state.get("draft_of")
    if previous is not None and previous != owner:
        old_day, _, old_products = previous[1]
        if draft_changed({name: price for name, _, price in old_products}):
            if old_day != seen[0]:
                notify("warning", "Your plan was discarded because the trading day changed.")
            else:
                notify("warning", "Your plan was discarded because the game was changed "
                                  "in another window.")
        clear_draft()
    st.session_state.draft_of = owner


def preview_text(product, quantity, text, tiers):
    cost = euros(quantity * product["cost"])
    price = parsed_price(text)
    if price is None:
        return f"Invalid price · In stock: {product['stock']} · Cost: {cost}"
    planned = dict(product, stock=product["stock"] + quantity, price=price)
    daily_demand = demand(price, product["reference"], tiers)
    expected_units = sales_for_product(planned, tiers)[0]
    return (f"Demand: {daily_demand} · In stock: {product['stock']} · "
            f"Expected sales: {expected_units} · Cost: {cost}")


def plan_message(quantities):
    bought = [f"{quantity} × {PRODUCT_LABELS[name]}" for name, quantity in quantities.items() if quantity]
    return (f"Bought {', '.join(bought)}. " if bought else "") + "Prices saved."


def start_game(scenario):
    try:
        st.query_params["game"] = db.create_game(DATABASE, scenario)
    except USER_ERRORS as error:
        notify("error", str(error))


def leave_game():
    st.query_params.clear()


def forget_other_game(token):
    """Clear inputs from a previous game when the link changes."""
    active = db.token_hash(token)
    if st.session_state.get("active_game") != active:
        for key in GAME_SESSION_KEYS:
            st.session_state.pop(key, None)
        st.session_state.active_game = active


def apply_plan(token, day, saved_prices, seen):
    """Apply all purchases and prices together. After a rejection the inputs stay."""
    if not draft_changed(saved_prices):
        notify("info", "Nothing to apply.")
        return
    quantities = {name: st.session_state[f"buy_{name}"] for name in NAMES}
    prices = {name: st.session_state[f"price_{name}"] for name in NAMES}
    try:
        db.apply_plan(DATABASE, token, day, quantities, prices, seen)
    except USER_ERRORS as error:
        notify("error", str(error))
        return
    notify("success", plan_message(quantities))
    clear_draft()


def trade_day(token, day, saved_prices, seen):
    if draft_changed(saved_prices):
        notify("error", "Apply or discard your changes before trading.")
        return
    try:
        db.trade(DATABASE, token, day, seen)
    except USER_ERRORS as error:
        notify("error", str(error))
        return
    notify("success", f"Day {day} complete.")
    clear_draft()


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
        notify("error", str(error))
        return
    notify("success", "Game deleted.")
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
    show_notices()
    with st.container(border=True):
        st.markdown(HOW_TO_PLAY)
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
saved_prices = {p["name"]: p["price"] for p in products}
seen = db.snapshot(game, products)
follow_saved_state(token, seen)
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

show_notices()

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
    st.subheader("Plan today")
    st.caption("Enter purchases and selling prices for all products, check the preview, "
               "then apply them together. Nothing is saved before you apply.")
    fill_draft(products)
    total = 0
    for product in products:
        name = product["name"]
        buy_col, price_col = st.columns(2)
        quantity = buy_col.number_input(f"Buy {PRODUCT_LABELS[name]}", min_value=0, step=1,
                                        key=f"buy_{name}")
        text = price_col.text_input(f"{PRODUCT_LABELS[name]} selling price (€)", max_chars=21,
                                    key=f"price_{name}")
        st.caption(preview_text(product, quantity, text, tiers[name]))
        total += quantity * product["cost"]
    st.write(f"Total purchase cost: **{euros(total)}** · "
             f"Cash after purchases: **{euros(game['cash'] - total)}**")
    if total > game["cash"]:
        st.warning("The total purchase cost is more than your cash.")
    changed = draft_changed(saved_prices)
    apply_col, discard_col = st.columns(2)
    apply_col.button("Apply purchases and prices", on_click=apply_plan,
                     args=(token, day, saved_prices, seen))
    discard_col.button("Discard changes", on_click=clear_draft, disabled=not changed)
    st.subheader("Trading")
    st.write("Today's demand depends on the event shown above and on each selling price. "
             "Sales are limited to the stock on hand. Unsold stock stays in the inventory.")
    st.button("Start trading day", type="primary", on_click=trade_day,
              args=(token, day, saved_prices, seen), disabled=changed)
    if changed:
        st.caption("Apply or discard your changes before trading.")

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
