# Architecture

PocketBudget is split into a thin iOS client and a private backend.

## iOS Client

The app is SwiftUI and has four tabs:

- Dashboard: accounts, budget progress, recent spending.
- Spending: transaction list.
- Budgets: edit monthly category limits.
- Settings: backend URL, API token, bank connect, manual sync.

The app stores:

- Backend URL in `UserDefaults`.
- Backend API token in Keychain.

The app does not store:

- Plaid client secret.
- Plaid access tokens.
- Bank credentials.

## Backend

The backend is FastAPI with SQLite. It owns:

- Plaid `client_id` and `secret`.
- Plaid `access_token`s encrypted with Fernet.
- Transaction sync cursors.
- Accounts, transactions, holdings, budgets, and category rules.

## Bank Linking

For SideStore builds, the backend hosts the Plaid Link page. This avoids depending on native iOS Universal Links for the first MVP.

The bank OAuth redirect, when required by an institution, lands on:

```text
https://your-domain/link/oauth-return
```

That URL must be registered in the Plaid dashboard.

## Budgeting

Plaid transactions are normalized into cents. Positive amounts are spending. Negative amounts are income. The categorizer applies:

1. Explicit merchant rules.
2. Plaid personal finance category mapping.
3. `Uncategorized` fallback.

Default categories are:

- Necessities
- Fun
- Girlfriend
- Savings
- Income
- Uncategorized

## Robinhood

The first realistic Robinhood path is Plaid Investments. If Robinhood links through Plaid and the Plaid Investments product is enabled, holdings are stored in the `holdings` table and shown in the investment summary.

The official Robinhood Crypto API is a separate future integration. It should start read-only.

