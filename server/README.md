# PocketBudget Server

The server keeps the finance integration safe. It exchanges Plaid public tokens, encrypts Plaid access tokens, syncs transactions, applies category rules, and serves the iPhone app's API.

## Run Locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_key.py
cp .env.example .env
uvicorn app.main:app --reload
```

On Linux Mint, install `python3.12-venv` and `python3-pip` first if Python reports that `ensurepip` or `pip` is unavailable.

## API Shape

- `GET /health`
- `GET /api/summary`
- `GET /api/transactions`
- `PUT /api/budgets/{budget_id}`
- `POST /api/sync`
- `POST /api/link/session`
- `GET /link/session/{session_id}`
- `GET /link/oauth-return`

All `/api/*` routes require `Authorization: Bearer $APP_API_TOKEN` when `APP_API_TOKEN` is set.

## Plaid Flow

1. The app calls `POST /api/link/session`.
2. The server creates a short-lived Plaid `link_token`.
3. The app opens `/link/session/{session_id}` with `ASWebAuthenticationSession`.
4. The web page opens Plaid Link.
5. The web page posts the Plaid `public_token` to the server.
6. The server exchanges it for an `access_token`, encrypts it, stores it in SQLite, and syncs transactions.

This avoids embedding Plaid secrets or long-lived Plaid tokens in the iOS app.

## Tests

The current dependency-free tests cover category decisions:

```bash
python -m unittest discover -s tests
```
