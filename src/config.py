from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    host: str
    port: int
    database_url: str
    stripe_api_key: str
    stripe_webhook_secret: str
    stripe_price_id: str
    app_base_url: str
    subscription_amount_cents: int


DEFAULTS = {
    "APP_NAME": "PulseBoard",
    "APP_ENV": "development",
    "HOST": "0.0.0.0",
    "PORT": "8000",
    "DATABASE_URL": "./data/pulseboard.db",
    "STRIPE_API_KEY": "",
    "STRIPE_WEBHOOK_SECRET": "",
    "STRIPE_PRICE_ID": "price_pulseboard_pro_monthly",
    "APP_BASE_URL": "http://127.0.0.1:8000",
    "SUBSCRIPTION_AMOUNT_CENTS": "1900",
}


def _read_env_file(env_path: str = ".env") -> dict[str, str]:
    path = Path(env_path)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_settings() -> Settings:
    env_values = {**DEFAULTS, **_read_env_file()}
    return Settings(
        app_name=env_values["APP_NAME"],
        app_env=env_values["APP_ENV"],
        host=env_values["HOST"],
        port=int(env_values["PORT"]),
        database_url=env_values["DATABASE_URL"],
        stripe_api_key=env_values["STRIPE_API_KEY"],
        stripe_webhook_secret=env_values["STRIPE_WEBHOOK_SECRET"],
        stripe_price_id=env_values["STRIPE_PRICE_ID"],
        app_base_url=env_values["APP_BASE_URL"],
        subscription_amount_cents=int(env_values["SUBSCRIPTION_AMOUNT_CENTS"]),
    )


settings = load_settings()
