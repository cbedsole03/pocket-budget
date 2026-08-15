from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DefaultBudget:
    id: str
    name: str
    icon_system_name: str
    color_hex: str
    monthly_limit_cents: int


DEFAULT_BUDGETS = [
    DefaultBudget("necessities", "Necessities", "house.fill", "#2563EB", 180_000),
    DefaultBudget("fun", "Fun", "sparkles", "#7C3AED", 40_000),
    DefaultBudget("girlfriend", "Girlfriend", "heart.fill", "#DB2777", 30_000),
    DefaultBudget("savings", "Savings", "chart.line.uptrend.xyaxis", "#059669", 50_000),
    DefaultBudget("income", "Income", "banknote.fill", "#16A34A", 0),
    DefaultBudget("uncategorized", "Uncategorized", "questionmark.circle", "#64748B", 0),
]


PFC_PRIMARY_TO_BUDGET = {
    "BANK_FEES": "necessities",
    "FOOD_AND_DRINK": "fun",
    "GENERAL_MERCHANDISE": "fun",
    "GENERAL_SERVICES": "necessities",
    "GOVERNMENT_AND_NON_PROFIT": "necessities",
    "HOME_IMPROVEMENT": "necessities",
    "INCOME": "income",
    "LOAN_PAYMENTS": "necessities",
    "MEDICAL": "necessities",
    "PERSONAL_CARE": "necessities",
    "RENT_AND_UTILITIES": "necessities",
    "TRANSPORTATION": "necessities",
    "TRAVEL": "fun",
}


def normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def plaid_primary(transaction: dict[str, Any]) -> str | None:
    category = transaction.get("personal_finance_category") or {}
    return category.get("primary") or transaction.get("pfc_primary")


def amount_cents(transaction: dict[str, Any]) -> int:
    amount = transaction.get("amount", 0)
    return int(round(float(amount) * 100))


def category_for_transaction(
    transaction: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
) -> str:
    """Return the app's budget category id for a Plaid transaction-like dict."""
    if amount_cents(transaction) < 0:
        return "income"

    merchant = normalize(transaction.get("merchant_name"))
    name = normalize(transaction.get("name"))
    haystack = f"{merchant} {name}".strip()

    for rule in rules or []:
        pattern = normalize(rule.get("pattern"))
        category_id = rule.get("category_id")
        if not pattern or not category_id:
            continue
        if rule.get("match_type") == "merchant_contains" and pattern in haystack:
            return category_id

    primary = plaid_primary(transaction)
    if primary in PFC_PRIMARY_TO_BUDGET:
        return PFC_PRIMARY_TO_BUDGET[primary]

    return "uncategorized"

