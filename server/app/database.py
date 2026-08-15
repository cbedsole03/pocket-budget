from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .categorizer import DEFAULT_BUDGETS


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def migrate(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  icon_system_name TEXT NOT NULL,
                  color_hex TEXT NOT NULL,
                  monthly_limit_cents INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS category_rules (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  match_type TEXT NOT NULL,
                  pattern TEXT NOT NULL,
                  category_id TEXT NOT NULL REFERENCES budgets(id)
                );

                CREATE TABLE IF NOT EXISTS plaid_items (
                  item_id TEXT PRIMARY KEY,
                  institution_name TEXT,
                  encrypted_access_token TEXT NOT NULL,
                  cursor TEXT,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS accounts (
                  account_id TEXT PRIMARY KEY,
                  item_id TEXT NOT NULL REFERENCES plaid_items(item_id),
                  name TEXT NOT NULL,
                  type TEXT NOT NULL,
                  subtype TEXT,
                  balance_cents INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS transactions (
                  transaction_id TEXT PRIMARY KEY,
                  account_id TEXT NOT NULL,
                  date TEXT NOT NULL,
                  name TEXT NOT NULL,
                  merchant_name TEXT,
                  amount_cents INTEGER NOT NULL,
                  pending INTEGER NOT NULL DEFAULT 0,
                  category_id TEXT,
                  category_name TEXT,
                  pfc_primary TEXT,
                  pfc_detailed TEXT,
                  removed INTEGER NOT NULL DEFAULT 0,
                  raw_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS holdings (
                  security_id TEXT PRIMARY KEY,
                  account_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  ticker_symbol TEXT,
                  quantity REAL NOT NULL,
                  value_cents INTEGER NOT NULL
                );
                """
            )
            for budget in DEFAULT_BUDGETS:
                db.execute(
                    """
                    INSERT OR IGNORE INTO budgets
                    (id, name, icon_system_name, color_hex, monthly_limit_cents)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        budget.id,
                        budget.name,
                        budget.icon_system_name,
                        budget.color_hex,
                        budget.monthly_limit_cents,
                    ),
                )

    def budgets(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT id, name, icon_system_name, color_hex, monthly_limit_cents
                FROM budgets
                ORDER BY
                  CASE id
                    WHEN 'necessities' THEN 1
                    WHEN 'fun' THEN 2
                    WHEN 'girlfriend' THEN 3
                    WHEN 'savings' THEN 4
                    WHEN 'income' THEN 5
                    ELSE 99
                  END,
                  name
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def update_budget(self, budget_id: str, monthly_limit_cents: int) -> dict[str, Any] | None:
        with self.connect() as db:
            db.execute(
                "UPDATE budgets SET monthly_limit_cents = ? WHERE id = ?",
                (monthly_limit_cents, budget_id),
            )
            row = db.execute(
                """
                SELECT id, name, icon_system_name, color_hex, monthly_limit_cents
                FROM budgets
                WHERE id = ?
                """,
                (budget_id,),
            ).fetchone()
            return dict(row) if row else None

    def category_rules(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT match_type, pattern, category_id FROM category_rules").fetchall()
            return [dict(row) for row in rows]

    def upsert_item(self, item_id: str, institution_name: str | None, encrypted_access_token: str) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO plaid_items (item_id, institution_name, encrypted_access_token)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                  institution_name = excluded.institution_name,
                  encrypted_access_token = excluded.encrypted_access_token
                """,
                (item_id, institution_name, encrypted_access_token),
            )

    def items(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT item_id, institution_name, encrypted_access_token, cursor
                FROM plaid_items
                ORDER BY created_at
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def update_cursor(self, item_id: str, cursor: str | None) -> None:
        with self.connect() as db:
            db.execute("UPDATE plaid_items SET cursor = ? WHERE item_id = ?", (cursor, item_id))

    def upsert_account(self, item_id: str, account: dict[str, Any]) -> None:
        balances = account.get("balances") or {}
        current = balances.get("current") or balances.get("available") or 0
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO accounts (account_id, item_id, name, type, subtype, balance_cents)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                  name = excluded.name,
                  type = excluded.type,
                  subtype = excluded.subtype,
                  balance_cents = excluded.balance_cents
                """,
                (
                    account["account_id"],
                    item_id,
                    account.get("name") or "Account",
                    account.get("type") or "unknown",
                    account.get("subtype"),
                    int(round(float(current) * 100)),
                ),
            )

    def upsert_transaction(self, transaction: dict[str, Any], category_id: str, category_name: str) -> None:
        pfc = transaction.get("personal_finance_category") or {}
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO transactions (
                  transaction_id, account_id, date, name, merchant_name, amount_cents,
                  pending, category_id, category_name, pfc_primary, pfc_detailed, removed, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(transaction_id) DO UPDATE SET
                  account_id = excluded.account_id,
                  date = excluded.date,
                  name = excluded.name,
                  merchant_name = excluded.merchant_name,
                  amount_cents = excluded.amount_cents,
                  pending = excluded.pending,
                  category_id = excluded.category_id,
                  category_name = excluded.category_name,
                  pfc_primary = excluded.pfc_primary,
                  pfc_detailed = excluded.pfc_detailed,
                  removed = 0,
                  raw_json = excluded.raw_json
                """,
                (
                    transaction["transaction_id"],
                    transaction["account_id"],
                    transaction.get("date") or "",
                    transaction.get("name") or "Transaction",
                    transaction.get("merchant_name"),
                    int(round(float(transaction.get("amount", 0)) * 100)),
                    1 if transaction.get("pending") else 0,
                    category_id,
                    category_name,
                    pfc.get("primary"),
                    pfc.get("detailed"),
                    json.dumps(transaction),
                ),
            )

    def mark_transaction_removed(self, transaction_id: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE transactions SET removed = 1 WHERE transaction_id = ?",
                (transaction_id,),
            )

    def accounts(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT account_id AS id, name, type, subtype, balance_cents
                FROM accounts
                ORDER BY name
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def transactions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT
                  t.transaction_id AS id,
                  t.date,
                  t.name,
                  t.merchant_name,
                  t.amount_cents,
                  t.category_id,
                  t.category_name,
                  t.pending,
                  a.name AS account_name
                FROM transactions t
                LEFT JOIN accounts a ON a.account_id = t.account_id
                WHERE t.removed = 0
                ORDER BY t.date DESC, t.transaction_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) | {"pending": bool(row["pending"])} for row in rows]

    def monthly_spend_by_budget(self, month_prefix: str) -> dict[str, int]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT category_id, SUM(amount_cents) AS spent
                FROM transactions
                WHERE removed = 0
                  AND pending = 0
                  AND amount_cents > 0
                  AND date LIKE ?
                GROUP BY category_id
                """,
                (f"{month_prefix}%",),
            ).fetchall()
            return {row["category_id"] or "uncategorized": int(row["spent"] or 0) for row in rows}

    def upsert_holding(self, account_id: str, holding: dict[str, Any], security: dict[str, Any]) -> None:
        value = holding.get("institution_value") or 0
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO holdings (security_id, account_id, name, ticker_symbol, quantity, value_cents)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(security_id) DO UPDATE SET
                  account_id = excluded.account_id,
                  name = excluded.name,
                  ticker_symbol = excluded.ticker_symbol,
                  quantity = excluded.quantity,
                  value_cents = excluded.value_cents
                """,
                (
                    holding["security_id"],
                    account_id,
                    security.get("name") or security.get("ticker_symbol") or "Holding",
                    security.get("ticker_symbol"),
                    float(holding.get("quantity") or 0),
                    int(round(float(value) * 100)),
                ),
            )

    def holdings(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT
                  security_id AS id,
                  name,
                  ticker_symbol,
                  quantity,
                  value_cents
                FROM holdings
                ORDER BY value_cents DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

