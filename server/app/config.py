from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_api_token: str = ""
    app_name: str = "PocketBudget"
    public_base_url: str = "http://127.0.0.1:8000"
    database_path: str = "data/pocket_budget.sqlite3"
    data_encryption_key: str = ""

    plaid_env: str = "sandbox"
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_products: str = "transactions,investments"
    plaid_country_codes: str = "US"
    plaid_redirect_uri: str = ""

    @property
    def plaid_products_list(self) -> list[str]:
        return [part.strip() for part in self.plaid_products.split(",") if part.strip()]

    @property
    def plaid_country_codes_list(self) -> list[str]:
        return [part.strip() for part in self.plaid_country_codes.split(",") if part.strip()]

    @property
    def plaid_is_configured(self) -> bool:
        return bool(self.plaid_client_id and self.plaid_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()

