from __future__ import annotations

from typing import Any

import httpx

from .config import Settings


PLAID_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._base_url = PLAID_BASE_URLS.get(settings.plaid_env, PLAID_BASE_URLS["sandbox"])

    async def create_link_token(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "client_name": self._settings.app_name,
            "country_codes": self._settings.plaid_country_codes_list,
            "language": "en",
            "products": self._settings.plaid_products_list,
            "user": {"client_user_id": "primary-user"},
        }
        if self._settings.plaid_redirect_uri:
            payload["redirect_uri"] = self._settings.plaid_redirect_uri
        return await self._post("link/token/create", payload)

    async def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        return await self._post("item/public_token/exchange", {"public_token": public_token})

    async def transactions_sync(self, access_token: str, cursor: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "access_token": access_token,
            "count": 500,
        }
        if cursor:
            payload["cursor"] = cursor
        return await self._post("transactions/sync", payload)

    async def accounts_get(self, access_token: str) -> dict[str, Any]:
        return await self._post("accounts/get", {"access_token": access_token})

    async def investments_holdings_get(self, access_token: str) -> dict[str, Any]:
        return await self._post("investments/holdings/get", {"access_token": access_token})

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        full_payload = {
            "client_id": self._settings.plaid_client_id,
            "secret": self._settings.plaid_secret,
            **payload,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/{path}", json=full_payload)
            response.raise_for_status()
            return response.json()

