"""Analyseur de scoring des annonces eBay."""

import re
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scrapers.ebay_scraper import Listing

log = logging.getLogger(__name__)

OPPORTUNITY_THRESHOLD = 0.75
MIN_MARKET_SAMPLES = 5


@dataclass
class MarketStats:
    avg_price: float
    min_price: float
    max_price: float
    sample_size: int


class OpportunityAnalyzer:
    """Analyseur de scoring pour les annonces eBay."""

    @staticmethod
    def _extract_price(raw: str) -> float | None:
        m = re.search(r"([\d,.]+)", raw.replace("\xa0", ""))
        if not m:
            return None
        return float(m.group(1).replace(",", "."))

    @classmethod
    def score_item(cls, item: "Listing", market: MarketStats | None) -> tuple[float, MarketStats | None]:
        price = cls._extract_price(item.raw_price)
        if price is None or market is None:
            return 0.0, market

        if price < market.min_price:
            price_ratio = price / max(market.avg_price, 1.0)
            base_score = 1.0 - price_ratio
            bonus_seller = 0.15
            total = min(1.0, base_score + bonus_seller)
            return total, market

        rel_to_avg = price / max(market.avg_price, 1.0)
        if rel_to_avg <= 1.0:
            score = (1.0 - rel_to_avg) * 0.4 + 0.4
        else:
            score = max(0.0, 0.5 - (rel_to_avg - 1.0) * 0.5)
        return score, market

    async def eval_items(self, items: list["Listing"]) -> list["Listing"]: 
        if not items:
            return []
        try:
            from utils.database import Database
            from utils.settings import settings
        except ImportError:
            log.warning("Base indisponible pour analyse prix moyen du marche")
            return [i for i in items if self._extract_price(i.raw_price) < 500.0]

        opp_items: list["Listing"] = []
        db: Database | None = None
        try:
            db = Database(settings.POSTGRES_URL)
            await db.connect()
            for item in items:
                price = self._extract_price(item.raw_price)
                if price is None:
                    continue
                stats = await db.get_market_stats(item.category_id)
                if stats:
                    score, stats_resolved = self.score_item(item, stats)
                    item._score_value = score
                    log.info(
                        "[SCORE] %.2f - %s | Prix: %.1f  Moyenne: %.1f",
                        score,
                        item.title[:40],
                        price,
                        stats_resolved.avg_price,
                    )
                else:
                    price_ratio = price / 600.0
                    score = 1.0 / price_ratio if price_ratio > 0 else 0.0
                    item._score_value = score
                    log.info(
                        "[SCORE] %.2f (fallback) - %s | Prix: %.1f",
                        score,
                        item.title[:40],
                        price,
                    )
                if score >= OPPORTUNITY_THRESHOLD:
                    opp_items.append(item)
        except Exception as e:
            log.exception("Analyse prix moyen impossible: %s", e)
            for item in items:
                price = self._extract_price(item.raw_price)
                if price and price < 200.0:
                    item._score_value = 0.8
                    opp_items.append(item)
        finally:
            if db:
                await db.close()
        return opp_items
