from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .categorizer import category_for_transaction
from .config import Settings, get_settings
from .database import Database
from .plaid_client import PlaidClient
from .security import TokenCipher


settings = get_settings()
db = Database(settings.database_path)
db.migrate()
plaid = PlaidClient(settings)

app = FastAPI(title="PocketBudget API", version="0.1.0")


@dataclass
class LinkSession:
    session_id: str
    link_token: str
    return_url: str
    expires_at: datetime


link_sessions: dict[str, LinkSession] = {}


class LinkSessionRequest(BaseModel):
    return_url: str = Field(default="pocketbudget://plaid/connected")


class LinkSessionResponse(BaseModel):
    link_url: str
    expires_at: str


class BudgetUpdate(BaseModel):
    monthly_limit_cents: int = Field(ge=0)


class PublicTokenExchange(BaseModel):
    public_token: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def cipher() -> TokenCipher:
    try:
        return TokenCipher(settings.data_encryption_key)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def require_auth(request: Request) -> None:
    if not settings.app_api_token:
        return

    expected = f"Bearer {settings.app_api_token}"
    actual = request.headers.get("authorization", "")
    if not secrets.compare_digest(actual, expected):
        raise HTTPException(status_code=401, detail="Invalid API token.")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "plaid_configured": settings.plaid_is_configured,
        "auth_required": bool(settings.app_api_token),
    }


@app.get("/api/summary", dependencies=[Depends(require_auth)])
async def summary() -> dict[str, Any]:
    now = datetime.now(UTC)
    month = now.strftime("%Y-%m")
    spend = db.monthly_spend_by_budget(month)

    budgets = []
    for budget in db.budgets():
        budget_id = budget["id"]
        budgets.append(
            {
                **budget,
                "spent_cents": spend.get(budget_id, 0),
            }
        )

    holdings = db.holdings()
    return {
        "month": month,
        "accounts": db.accounts(),
        "budgets": budgets,
        "recent_transactions": db.transactions(limit=8),
        "investments": {
            "total_value_cents": sum(item["value_cents"] for item in holdings),
            "holdings": holdings,
        },
    }


@app.get("/api/transactions", dependencies=[Depends(require_auth)])
async def transactions(limit: int = 100) -> list[dict[str, Any]]:
    return db.transactions(limit=min(max(limit, 1), 500))


@app.put("/api/budgets/{budget_id}", dependencies=[Depends(require_auth)])
async def update_budget(budget_id: str, payload: BudgetUpdate) -> dict[str, Any]:
    budget = db.update_budget(budget_id, payload.monthly_limit_cents)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget category not found.")
    budget["spent_cents"] = db.monthly_spend_by_budget(datetime.now(UTC).strftime("%Y-%m")).get(
        budget_id,
        0,
    )
    return budget


@app.post("/api/sync", dependencies=[Depends(require_auth)])
async def sync() -> dict[str, Any]:
    items = db.items()
    for item in items:
        await sync_item(item)
    return {}


@app.post("/api/link/session", dependencies=[Depends(require_auth)])
async def create_link_session(payload: LinkSessionRequest) -> LinkSessionResponse:
    if not settings.plaid_is_configured:
        raise HTTPException(status_code=503, detail="Plaid credentials are not configured.")

    cipher()
    data = await plaid.create_link_token()
    session_id = secrets.token_urlsafe(24)
    expires_at = datetime.now(UTC) + timedelta(minutes=25)
    link_sessions[session_id] = LinkSession(
        session_id=session_id,
        link_token=data["link_token"],
        return_url=payload.return_url,
        expires_at=expires_at,
    )

    return LinkSessionResponse(
        link_url=f"{settings.public_base_url.rstrip('/')}/link/session/{session_id}",
        expires_at=expires_at.isoformat(),
    )


@app.get("/link/session/{session_id}", response_class=HTMLResponse)
async def link_session_page(session_id: str) -> HTMLResponse:
    session = current_link_session(session_id)
    return HTMLResponse(
        plaid_link_html(
            session_id=session.session_id,
            link_token=session.link_token,
            return_url=session.return_url,
            oauth_return=False,
        )
    )


@app.get("/link/oauth-return", response_class=HTMLResponse)
async def link_oauth_return() -> HTMLResponse:
    return HTMLResponse(plaid_link_html(session_id="", link_token="", return_url="", oauth_return=True))


@app.post("/link/session/{session_id}/exchange")
async def exchange_public_token(session_id: str, payload: PublicTokenExchange) -> dict[str, Any]:
    session = current_link_session(session_id)
    data = await plaid.exchange_public_token(payload.public_token)

    institution = payload.metadata.get("institution") or {}
    db.upsert_item(
        item_id=data["item_id"],
        institution_name=institution.get("name"),
        encrypted_access_token=cipher().encrypt(data["access_token"]),
    )

    item = next((row for row in db.items() if row["item_id"] == data["item_id"]), None)
    if item:
        await sync_item(item)

    link_sessions.pop(session.session_id, None)
    return {"ok": True}


def current_link_session(session_id: str) -> LinkSession:
    session = link_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Link session not found or expired.")
    if session.expires_at < datetime.now(UTC):
        link_sessions.pop(session_id, None)
        raise HTTPException(status_code=410, detail="Link session expired.")
    return session


async def sync_item(item: dict[str, Any]) -> None:
    access_token = cipher().decrypt(item["encrypted_access_token"])
    cursor = item.get("cursor")
    rules = db.category_rules()
    budgets_by_id = {budget["id"]: budget for budget in db.budgets()}

    while True:
        try:
            data = await plaid.transactions_sync(access_token, cursor)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {400, 429}:
                return
            raise

        for account in data.get("accounts", []):
            db.upsert_account(item["item_id"], account)

        for transaction in data.get("added", []) + data.get("modified", []):
            category_id = category_for_transaction(transaction, rules)
            category_name = budgets_by_id.get(category_id, budgets_by_id["uncategorized"])["name"]
            db.upsert_transaction(transaction, category_id, category_name)

        for removed in data.get("removed", []):
            db.mark_transaction_removed(removed["transaction_id"])

        cursor = data.get("next_cursor")
        if not data.get("has_more"):
            break

    db.update_cursor(item["item_id"], cursor)
    await sync_investments(access_token)


async def sync_investments(access_token: str) -> None:
    try:
        data = await plaid.investments_holdings_get(access_token)
    except httpx.HTTPStatusError:
        return

    securities = {item["security_id"]: item for item in data.get("securities", [])}
    for account in data.get("accounts", []):
        db.upsert_account(data.get("item", {}).get("item_id", "investment-item"), account)

    for holding in data.get("holdings", []):
        security = securities.get(holding.get("security_id"), {})
        db.upsert_holding(holding["account_id"], holding, security)


def plaid_link_html(
    session_id: str,
    link_token: str,
    return_url: str,
    oauth_return: bool,
) -> str:
    payload = {
        "sessionId": session_id,
        "linkToken": link_token,
        "returnUrl": return_url,
        "oauthReturn": oauth_return,
    }
    config_json = json.dumps(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PocketBudget Bank Link</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f8fafc;
      color: #0f172a;
      display: grid;
      min-height: 100vh;
      place-items: center;
    }}
    main {{
      width: min(92vw, 420px);
      background: white;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 12px 30px rgb(15 23 42 / 0.08);
    }}
    h1 {{ font-size: 22px; margin: 0 0 8px; }}
    p {{ color: #475569; line-height: 1.5; }}
    button {{
      width: 100%;
      border: 0;
      border-radius: 8px;
      padding: 13px 16px;
      font: inherit;
      font-weight: 700;
      color: white;
      background: #2563eb;
    }}
    #error {{ color: #b91c1c; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <main>
    <h1>Connect your bank</h1>
    <p id="status">Opening Plaid Link...</p>
    <p id="error"></p>
    <button id="open" type="button">Open Plaid Link</button>
  </main>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    const serverConfig = {config_json};
    const statusEl = document.getElementById("status");
    const errorEl = document.getElementById("error");
    const button = document.getElementById("open");

    function readConfig() {{
      if (!serverConfig.oauthReturn) {{
        localStorage.setItem("pb_session_id", serverConfig.sessionId);
        localStorage.setItem("pb_link_token", serverConfig.linkToken);
        localStorage.setItem("pb_return_url", serverConfig.returnUrl);
        return serverConfig;
      }}
      return {{
        sessionId: localStorage.getItem("pb_session_id"),
        linkToken: localStorage.getItem("pb_link_token"),
        returnUrl: localStorage.getItem("pb_return_url"),
        oauthReturn: true
      }};
    }}

    async function exchange(sessionId, publicToken, metadata) {{
      const response = await fetch(`/link/session/${{sessionId}}/exchange`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ public_token: publicToken, metadata }})
      }});
      if (!response.ok) {{
        throw new Error(await response.text());
      }}
    }}

    function openPlaid() {{
      const cfg = readConfig();
      if (!cfg.sessionId || !cfg.linkToken) {{
        errorEl.textContent = "Bank link session is missing. Start again from the app.";
        return;
      }}

      const plaidConfig = {{
        token: cfg.linkToken,
        onSuccess: async function(publicToken, metadata) {{
          try {{
            statusEl.textContent = "Saving connection...";
            await exchange(cfg.sessionId, publicToken, metadata);
            localStorage.removeItem("pb_session_id");
            localStorage.removeItem("pb_link_token");
            localStorage.removeItem("pb_return_url");
            window.location.href = cfg.returnUrl || "pocketbudget://plaid/connected";
          }} catch (error) {{
            errorEl.textContent = String(error);
          }}
        }},
        onExit: function(error) {{
          if (error) {{
            errorEl.textContent = error.display_message || error.error_message || String(error);
          }}
        }}
      }};

      if (cfg.oauthReturn) {{
        plaidConfig.receivedRedirectUri = window.location.href;
      }}

      const handler = Plaid.create(plaidConfig);
      handler.open();
    }}

    button.addEventListener("click", openPlaid);
    window.addEventListener("load", openPlaid);
  </script>
</body>
</html>"""
