from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    host: str
    port: int
    database_url: str


DEFAULTS = {
    "APP_NAME": "PulseBoard",
    "APP_ENV": "development",
    "HOST": "0.0.0.0",
    "PORT": "8000",
    "DATABASE_URL": "./data/pulseboard.db",
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
    )


settings = load_settings()
