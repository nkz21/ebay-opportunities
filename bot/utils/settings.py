"""Configuration centralisee du bot."""

import os
from typing import Any


class _Config:
    """Configuration lazy avec validation."""

    POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@postgres:5432/ebay")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))
    METRICS_PORT = 9877
    METRICS_HOST = "0.0.0.0"
    PROXY_URL = os.getenv("PROXY_URL", "")

    # Notifications
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

    _db_confirmed: bool = False
    _cache_confirmed: bool = False

    def database_confirmed(self) -> None:
        self._db_confirmed = True

    def cache_confirmed(self) -> None:
        self._cache_confirmed = True

    @property
    def categories(self) -> list[str]:
        return ["smart tv 4k", "tv oled", "tv qled", "appareil photo reflex", "appareil photo mirrorless"]


settings = _Config()
