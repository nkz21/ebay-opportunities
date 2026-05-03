"""Notifier Discord pour les opportunites eBay."""

import aiohttp
import logging
from typing import TYPE_CHECKING

from utils.settings import settings

if TYPE_CHECKING:
    from scrapers.ebay_scraper import Listing

log = logging.getLogger(__name__)

COLOUR_OPPORTUNIT_Y = 0x2ECC71
COLOUR_LOW_PRICE = 0xFFD700


class DiscordNotifier:
    """Envoie des notifications Discord via webhook."""

    @staticmethod
    async def send(item: "Listing") -> None:
        webhook_url = settings.DISCORD_WEBHOOK_URL
        if not webhook_url:
            log.debug("Discord: pas de webhook configuré")
            return

        colour = COLOUR_OPPORTUNIT_Y if item.score >= 0.9 else COLOUR_LOW_PRICE
        embed = {
            "title": item.title,
            "url": item.url,
            "color": colour,
            "fields": [
                {"name": "Prix", "value": item.raw_price, "inline": True},
                {"name": "Discount", "value": f"{item.score:.1%}", "inline": True},
                {"name": "Vendeur", "value": item.seller_name or "N/A", "inline": True},
                {"name": "URL", "value": item.url, "inline": False},
            ],
            "thumbnail": {"url": "https://ir.ebaystatic.com/cr/v/c1/M7.png"},
            "footer": {"icon_url": "https://ir.ebaystatic.com/pictures/aw/about/logo_138x27.gif", "text": "eBay Opportunities Bot"},
        }
        payload = {"embeds": [embed]}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 204:
                        log.warning("Discord webhook error: %d", resp.status)
                    else:
                        log.info("Discord: embed envoyé pour %s", item.title[:30])
            except Exception as e:
                log.exception("Discord webhook error: %s", e)
