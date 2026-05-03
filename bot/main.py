"""Scheduler principal du bot eBay Opportunities."""

import asyncio
import time
import logging
from pathlib import Path
from contextlib import AsyncExitStack

from scrapers.ebay_scraper import eBayScraper
from analyzers.opportunity import OpportunityAnalyzer
from notifiers.telegram import TelegramNotifier
from notifiers.discord import DiscordNotifier
from utils.settings import settings
from utils.database import Database
from utils.cache import RedisCache
from metrics_server import start_server

log = logging.getLogger(__name__)


class Metrics:
    """Conteneur de métriques Prometheus."""

    def __init__(self) -> None:
        self.scrapes_total = 0
        self.listings_found_total = 0
        self.listings_stored_total = 0
        self.opportunities_total = 0
        self.last_scrape_timestamp = 0.0
        self.last_scrape_duration_s = 0.0
        self.redis_connections = 0
        self.db_connections = 0
        self.errors_total = 0

    def inc_scrapes(self) -> None:
        self.scrapes_total += 1
        self.last_scrape_timestamp = time.time()

    def inc_listings_found(self, count: int) -> None:
        self.listings_found_total += count

    def inc_listings_stored(self, count: int) -> None:
        self.listings_stored_total += count

    def inc_opportunities(self, count: int) -> None:
        self.opportunities_total += count

    def set_scrape_duration(self, duration: float) -> None:
        self.last_scrape_duration_s = duration

    def inc_errors(self, count: int) -> None:
        self.errors_total += count

    def render(self) -> str:
        """Rend les métriques au format Prometheus."""
        lines = [
            "# HELP ebay_scrapes_total Nombre total de scans effectues",
            "# TYPE ebay_scrapes_total counter",
            f"ebay_scrapes_total {self.scrapes_total}",
            "# HELP ebay_listings_found Nombre d'annonces trouvees par scan",
            "# TYPE ebay_listings_found counter",
            f"ebay_listings_found_total {self.listings_found_total}",
            "# HELP ebay_listings_stored Nombre d'annonces stockees en base",
            "# TYPE ebay_listings_stored counter",
            f"ebay_listings_stored_total {self.listings_stored_total}",
            "# HELP ebay_opportunities_total Nombre total d'opportunites detectees",
            "# TYPE ebay_opportunities_total counter",
            f"ebay_opportunities_total {self.opportunities_total}",
            "# HELP ebay_scrape_duration_seconds Duree d'un scan",
            "# TYPE ebay_scrape_duration_seconds gauge",
            f"ebay_scrape_duration_seconds {self.last_scrape_duration_s:.3f}",
            "# HELP ebay_last_scrape_timestamp Timestamp du dernier scan",
            "# TYPE ebay_last_scrape_timestamp gauge",
            f"ebay_last_scrape_timestamp {self.last_scrape_timestamp}",
            "# HELP ebay_redis_connections Connexions Redis actives",
            "# TYPE ebay_redis_connections gauge",
            f"ebay_redis_connections {self.redis_connections}",
            "# HELP ebay_db_connections Connexions PostgreSQL actives",
            "# TYPE ebay_db_connections gauge",
            f"ebay_db_connections {self.db_connections}",
            "# HELP ebay_errors_total Nombre total d'erreurs",
            "# TYPE ebay_errors_total counter",
            f"ebay_errors_total {self.errors_total}",
        ]
        return "\n".join(lines) + "\n"


class Bot:
    """Bot principal eBay Opportunities."""

    def __init__(self) -> None:
        self.metrics = Metrics()
        self.scraper = eBayScraper()
        self.analyzer = OpportunityAnalyzer()
        self.telegram = TelegramNotifier()
        self.discord = DiscordNotifier()

    async def connect(self) -> AsyncExitStack:
        """Connexion aux services externes."""
        stack = AsyncExitStack()
        self.db = await stack.enter_async_context(Database(settings.POSTGRES_URL))
        self.cache = await stack.enter_async_context(RedisCache(settings.REDIS_URL))
        settings.database_confirmed()
        settings.cache_confirmed()
        log.info("Connexions etablies (PostgreSQL + Redis)")
        start_server(
            port=settings.METRICS_PORT,
            host=settings.METRICS_HOST,
            metrics=self.metrics,
        )
        return stack

    async def run_loop(self) -> None:
        """Boucle principale de scan."""
        while True:
            start = time.time()
            try:
                await self._run_scan()
            except Exception as exc:
                log.exception("Scan failed: %s", exc)
                self.metrics.inc_errors(1)
            self.metrics.set_scrape_duration(time.time() - start)
            await asyncio.sleep(settings.SCAN_INTERVAL)

    async def _run_scan(self) -> None:
        """Un cycle de scan complet."""
        self.metrics.inc_scrapes()
        log.info("Debut du scan")

        all_listings = await asyncio.gather(
            *(self.scraper.search_ebay(keyword) for keyword in settings.CATEGORIES),
        )

        raw_items = [item for batch in all_listings for item in batch]
        log.info("Annonces recues: %d", len(raw_items))

        new_items = []
        for item in raw_items:
            if not await self.cache.is_seen(item.id):
                new_items.append(item)
        log.info("Nouvelles annonces (apres deduplication): %d", len(new_items))

        if not new_items:
            log.info("Aucune nouvelle annonce")
            return

        stored = await self.db.bulk_insert_listings(new_items)
        self.metrics.inc_listings_found(len(raw_items))
        self.metrics.inc_listings_stored(stored)
        log.info("Stockees en base: %d", stored)

        new_cache_keys = [item.id for item in new_items]
        await self.cache.mark_seen(new_cache_keys)

        opportunity_items = await self.analyzer.eval_items(new_items)
        if opportunity_items:
            self.metrics.inc_opportunities(len(opportunity_items))
            log.info("Opportunites detectees: %d", len(opportunity_items))
            await asyncio.gather(
                *(self._notify(item) for item in opportunity_items),
            )

    async def _notify(self, item) -> None:
        """Envoie la notification Telegram + Discord."""
        try:
            await self.telegram.send(item)
        except Exception as e:
            log.warning("Telegram notification failed: %s", e)
        try:
            await self.discord.send(item)
        except Exception as e:
            log.warning("Discord notification failed: %s", e)


async def main() -> None:
    """Point d'entree du bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    bot = Bot()
    async with await bot.connect():
        await bot.run_loop()


if __name__ == "__main__":
    asyncio.run(main())
