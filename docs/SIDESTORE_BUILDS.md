# SideStore Builds

The GitHub workflow is `.github/workflows/ios-testing-build.yml`.

It deliberately produces an unsigned IPA:

```text
Payload/PocketBudget.app -> PocketBudget-ios-unsigned-vX.Y.Z.ipa
```

SideStore handles the final signing step for your Apple ID and device.

## Why Unsigned

Unsigned cloud builds avoid:

- Apple Developer Program signing setup.
- Certificates in GitHub secrets.
- Provisioning profile management.

That is good for a personal testing build. It is not the same as App Store or TestFlight distribution.

## Running The Workflow

1. Push the repo to GitHub.
2. Open Actions.
3. Run `iOS testing build`.
4. Open the `ios-testing-latest` prerelease.
5. Download the IPA.
6. Install with SideStore.

## Backend URL

The app must reach the backend from your phone. Use HTTPS for real Plaid accounts. A local-only URL like `http://127.0.0.1:8000` only works from the computer running the server, not from the phone.

