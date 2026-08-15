# PocketBudget

PocketBudget is a personal budgeting app designed for a SideStore-installed iPhone build and a private backend. The phone app shows accounts, spending, budgets, and investment holdings. The backend owns every Plaid secret and encrypted bank access token.

## Current MVP

- Native SwiftUI iOS app.
- Manual GitHub Actions build that produces an unsigned `.ipa` for SideStore.
- FastAPI backend with SQLite storage.
- Plaid Sandbox-ready bank linking through a server-hosted Plaid Link page.
- Transaction sync through Plaid Transactions Sync.
- Budget categories for `Necessities`, `Fun`, `Girlfriend`, `Savings`, `Income`, and `Uncategorized`.
- Merchant rules foundation for custom category routing.
- Plaid Investments holdings sync foundation for brokerage accounts, including Robinhood if Plaid supports the linked account and the Plaid product is enabled.

## Repository Layout

```text
.
├── .github/workflows/ios-testing-build.yml  # unsigned SideStore IPA build
├── .github/workflows/server-tests.yml       # backend unit tests
├── ios/PocketBudget                         # SwiftUI client
├── server                                   # FastAPI backend
├── docs                                     # architecture and build notes
└── project.yml                              # XcodeGen project definition
```

## Backend Setup

```bash
cd server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_key.py
cp .env.example .env
```

Edit `.env`:

- `APP_API_TOKEN`: long random token used by the iPhone app.
- `PUBLIC_BASE_URL`: HTTPS URL your phone can reach.
- `DATA_ENCRYPTION_KEY`: output from `scripts/generate_key.py`.
- `PLAID_CLIENT_ID` / `PLAID_SECRET`: Plaid Sandbox credentials first.
- `PLAID_REDIRECT_URI`: `https://your-domain/link/oauth-return`, registered in Plaid.

Run it:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Linux Mint, install `python3.12-venv` and `python3-pip` first if `venv` or `pip` is missing.

## iPhone Setup

1. Open the app.
2. Go to Settings.
3. Set the backend URL, for example `https://budget.example.com`.
4. Paste `APP_API_TOKEN`.
5. Tap `Connect Bank Account`.

The iPhone never stores Plaid secrets. It stores only your backend URL and backend API token.

## Cloud IPA Build

The iOS build mirrors the Noop fork approach:

- No Apple signing secrets.
- No Plaid secrets.
- `xcodebuild` runs on a GitHub-hosted macOS runner.
- The workflow packages `Payload/PocketBudget.app` into an unsigned `.ipa`.
- SideStore re-signs the IPA for your phone.

To use it:

1. Push this repo to GitHub as a public repo if you want GitHub-hosted macOS Actions without private-repo minute usage.
2. Run `iOS testing build` from the Actions tab.
3. Download `PocketBudget-ios-unsigned-v0.1.0.ipa` from the `ios-testing-latest` prerelease.
4. Install with SideStore.

## Security Notes

- Do not put Plaid secrets in the app.
- Do not commit `.env`, SQLite databases, or generated encryption keys.
- Serve the backend over HTTPS before linking real accounts.
- Use Plaid Sandbox until the whole flow works end to end.
- Treat `APP_API_TOKEN` like a password.

## Next Work

- Add rule management UI for merchant-to-budget routing.
- Add recurring bill detection.
- Add monthly budget history.
- Add Robinhood brokerage support through Plaid Investments where available.
- Add optional read-only Robinhood Crypto API integration.
- Add server deployment config for the machine that already runs SideStore.
