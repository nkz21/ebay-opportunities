"""Wrapper Redis pour la deduplication."""

import logging
from typing import Any

import redis.asyncio as redis

from utils.settings import settings

log = logging.getLogger(__name__)

DB_KEYS = "ebay:seen"


class RedisCache:
    """Cache Redis pour deduplication des annonces."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.REDIS_URL
        self._client: redis.Redis | None = None
        self._ttl = 2_592_000  # 30 jours

    async def connect(self) -> None:
        """Connexion au client Redis."""
        if self._client and self._client.is_connected:
            return
        self._client = redis.from_url(self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.close()

    async def __aenter__(self) -> "RedisCache":
        await self.connect()
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.close()

    @property
    def _ready(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def is_seen(self, item_id: str) -> bool:
        """Renvoie True si l'annonce a deja ete vue."""
        if not self._ready:
            return False
        assert self._client is not None
        seen = await self._client.sismember(DB_KEYS, item_id)
        return bool(seen)

    async def mark_seen(self, item_ids: list[str]) -> None:
        """Marque les annonces comme vues."""
        if not item_ids:
            return
        if not self._ready:
            return
        assert self._client is not None
        pipe = self._client.pipeline()
        pipe.sadd(DB_KEYS, *item_ids)
        pipe.expire(DB_KEYS, self._ttl)
        await pipe.execute()

    async def count_seen(self) -> int:
        """Nombre d'annonces deja vues."""
        if not self._ready:
            return 0
        assert self._client is not None
        return await self._client.scard(DB_KEYS)
