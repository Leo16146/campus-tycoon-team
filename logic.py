"""Campus Kiosk trading rules. All amounts are in cents."""


import re

STARTING_CASH = 10000

# Product name (SQLite key), unit cost and reference price in cents, in purchase order.
CATALOG = [("Kaffee", 200, 400), ("Wasser", 50, 100), ("Müsliriegel", 100, 200)]

TRADING_DAYS = 5

# Scenario keys are stored with each game. Never redefine an existing key.
SCENARIOS = {"exam_week": "Exam Week", "heatwave": "Heatwave"}

# Demand per product as (at or below the reference price, up to twice the reference price).
# Above twice the reference price demand is always 0. The solo rule is (10, 5).
NORMAL = (10, 5)
EVENTS = {
    "exam_week": [
        ("Normal day", {"Kaffee": NORMAL, "Wasser": NORMAL, "Müsliriegel": NORMAL}),
        ("Revision rush", {"Kaffee": (20, 10), "Wasser": NORMAL, "Müsliriegel": NORMAL}),
        ("Exam day", {"Kaffee": (20, 10), "Wasser": NORMAL, "Müsliriegel": NORMAL}),
        ("Open Day", {"Kaffee": (14, 0), "Wasser": (14, 0), "Müsliriegel": (14, 0)}),
        ("Normal day", {"Kaffee": NORMAL, "Wasser": NORMAL, "Müsliriegel": NORMAL}),
    ],
    "heatwave": [
        ("Warm morning", {"Kaffee": NORMAL, "Wasser": (16, 8), "Müsliriegel": NORMAL}),
        ("Heatwave", {"Kaffee": (6, 3), "Wasser": (24, 12), "Müsliriegel": (8, 4)}),
        ("Heatwave", {"Kaffee": (6, 3), "Wasser": (24, 12), "Müsliriegel": (8, 4)}),
        ("Sports day", {"Kaffee": (8, 4), "Wasser": (30, 3), "Müsliriegel": (12, 2)}),
        ("Cool change", {"Kaffee": (12, 6), "Wasser": NORMAL, "Müsliriegel": NORMAL}),
    ],
}


def price_in_cents(text):
    text = text.strip()
    if not re.fullmatch(r"[0-9]+(?:[.][0-9]{1,2})?", text):
        raise ValueError("Enter a positive euro amount with at most two decimal places.")
    whole, _, fraction = text.partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0"))
    if cents < 1:
        raise ValueError("The selling price must be positive.")
    if cents > 2**63 - 1:
        raise ValueError("This price is too large to save.")
    return cents


def final_result(cash, products):
    stock_value = sum(p["stock"] * p["cost"] for p in products)
    return stock_value, cash + stock_value - STARTING_CASH


def purchase_cost(quantity, unit_cost, cash):
    if type(quantity) is not int or quantity < 1:
        raise ValueError("Enter a positive whole number for the quantity.")
    cost = quantity * unit_cost
    if cost > cash:
        raise ValueError("Not enough cash for this purchase.")
    return cost


def todays_event(scenario, day):
    """Return the event name and the demand tiers per product for trading days 1 to 5."""
    if not 1 <= day <= TRADING_DAYS:
        raise ValueError("There is no event after the fifth trading day.")
    return EVENTS[scenario][day - 1]


def demand(price, reference, tiers):
    at_reference, up_to_double = tiers
    if price <= 0:
        raise ValueError("The selling price must be positive.")
    if price <= reference:
        return at_reference
    if price <= 2 * reference:
        return up_to_double
    return 0


def sales_for_product(product, tiers):
    sold = min(product["stock"], demand(product["price"], product["reference"], tiers))
    revenue = sold * product["price"]
    expense = sold * product["cost"]
    return sold, revenue, expense, revenue - expense


def baseline_restock(stock, cash, tiers):
    """Buy up to today's demand at the reference price, in catalogue order, as cash allows.

    Returns the new stock, the remaining cash and the units bought per product.
    """
    stock = dict(stock)
    bought = {}
    for name, cost, _ in CATALOG:
        wanted = max(0, tiers[name][0] - stock[name])
        bought[name] = min(wanted, cash // cost)
        stock[name] += bought[name]
        cash -= bought[name] * cost
    return stock, cash, bought


def baseline_results(scenario):
    """Play the baseline strategy: reference prices, restocked every day.

    Uses the same events and sales rules as a player. Returns a list of
    (gross profit, cash after trading) per day and the overall gain / loss.
    """
    stock = {name: 0 for name, _, _ in CATALOG}
    cash = STARTING_CASH
    days = []
    for _, tiers in EVENTS[scenario]:
        stock, cash, _ = baseline_restock(stock, cash, tiers)
        gross_profit = 0
        for name, cost, reference in CATALOG:
            product = {"stock": stock[name], "price": reference, "reference": reference, "cost": cost}
            sold, revenue, _, profit = sales_for_product(product, tiers[name])
            stock[name] -= sold
            cash += revenue
            gross_profit += profit
        days.append((gross_profit, cash))
    remaining = [{"stock": stock[name], "cost": cost} for name, cost, _ in CATALOG]
    return days, final_result(cash, remaining)[1]
