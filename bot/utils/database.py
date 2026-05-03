"""Wrapper PostgreSQL asynchrone pour le bot."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import asyncpg

from analyzers.opportunity import MarketStats
from utils.settings import settings

if TYPE_CHECKING:
    from scrapers.ebay_scraper import Listing


def _extract_price(raw: str) -> float | None:
    m = re.search(r"(\\d+[,.]?\\d*)", raw)
    return float(m.group(1).replace(",", ".")) if m else None


@dataclass
class _DBItem:
    item_id: str
    title: str
    raw_price: str
    numeric_price: float | None
    url: str
    category_id: str
    category_name: str
    total_price: float | None


class Database:
    """Wrapper asynchrone PostgreSQL."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or settings.POSTGRES_URL
        self._pool: asyncpg.Pool | None = None

    @property
    def _ready(self) -> bool:
        return (self._pool is not None) and not (self._pool and self._pool.is_closed())

    async def connect(self) -> None:
        """Connexion avec pool."""
        if self._pool and not self._pool.is_closed():
            return
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=2,
            max_size=8,
            command_timeout=10,
        )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def __aenter__(self) -> "Database":
        await self.connect()
        return self

    async def __aexit__(self, *_args: Any) -> None:
        await self.close()

    async def bulk_insert_listings(self, items: list["Listing"]) -> int:
        if not items:
            return 0
        if not self._ready:
            return 0
        assert self._pool is not None
        records: list[tuple] = []
        for it in items:
            price = _extract_price(it.raw_price)
            total = price
            records.append((it.id, it.title, it.raw_price, price, it.url, it.category_id, it.category_name, total))
        async with self._pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO listings (item_id, title, raw_price, numeric_price, url, category_id, category_name, total_price) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (item_id) DO NOTHING",
                records,
            )
        return len(records)

    async def get_market_stats(self, cat_id: str) -> MarketStats | None:
        if not self._ready:
            return None
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT numeric_price FROM listings WHERE category_id = $1 AND numeric_price IS NOT NULL AND numeric_price > 0 LIMIT 200",
                cat_id,
            )
        if not rows:
            return None
        prices = [r["numeric_price"] for r in rows]
        return MarketStats(
            avg_price=sum(prices) / len(prices),
            min_price=min(prices),
            max_price=max(prices),
            sample_size=len(prices),
        )

    async def get_latest_listings(self, *, category_id: str | None = None, limit: int = 10) -> list[_DBItem]:
        if not self._ready:
            return []
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            if category_id:
                rows = await conn.fetch(
                    "SELECT item_id,title,raw_price,numeric_price,url,category_id,category_name,total_price FROM listings WHERE category_id = $1 ORDER BY created_at DESC LIMIT $2",
                    category_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    "SELECT item_id,title,raw_price,numeric_price,url,category_id,category_name,total_price FROM listings ORDER BY created_at DESC LIMIT $1",
                    limit,
                )
        return [_DBItem(**dict(r)) for r in rows]
