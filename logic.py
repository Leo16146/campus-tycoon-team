"""Campus Kiosk trading rules. All amounts are in cents."""


import re

STARTING_CASH = 10000

# Scenario keys are stored with each game. Never redefine an existing key.
# Daily events per scenario follow in P2 (specs/campus-week.md).
SCENARIOS = {"exam_week": "Exam Week", "heatwave": "Heatwave"}


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


def demand(price, reference):
    if price <= 0:
        raise ValueError("The selling price must be positive.")
    if price <= reference:
        return 10
    if price <= 2 * reference:
        return 5
    return 0


def sales_for_product(product):
    sold = min(product["stock"], demand(product["price"], product["reference"]))
    revenue = sold * product["price"]
    expense = sold * product["cost"]
    return sold, revenue, expense, revenue - expense
