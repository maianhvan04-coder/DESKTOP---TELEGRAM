from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from desktop_telegram.core.paths import get_env_file


ENV_FILE = get_env_file()
load_dotenv(ENV_FILE)


@dataclass
class Settings:
    app_name: str
    mongodb_uri: str
    telegram_api_id: int | None
    telegram_api_hash: str | None
    crawl_hour: int
    crawl_minute: int

    @property
    def has_telegram_credentials(self) -> bool:
        return bool(self.telegram_api_id and self.telegram_api_hash and self.telegram_api_hash.strip())


def _to_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value.strip())


settings = Settings(
    app_name=os.getenv("APP_NAME", "Telegram Desktop Tool"),
    mongodb_uri=os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/telegram-desktop"),
    telegram_api_id=_to_int(os.getenv("TELEGRAM_API_ID")),
    telegram_api_hash=(os.getenv("TELEGRAM_API_HASH") or "").strip() or None,
    crawl_hour=int(os.getenv("CRAWL_HOUR", "1")),
    crawl_minute=int(os.getenv("CRAWL_MINUTE", "0")),
)