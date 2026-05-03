"""Notifier Telegram pour les opportunites eBay."""

import aiohttp
import logging
from typing import TYPE_CHECKING

from utils.settings import settings

if TYPE_CHECKING:
    from scrapers.ebay_scraper import Listing

log = logging.getLogger(__name__)

T_G = "Opportunité eBay"


class TelegramNotifier:
    """Envoie des notifications Telegram."""

    @staticmethod
    async def send(item: "Listing") -> None:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if not (token and chat_id):
            log.debug("Telegram: pas de token/ID configuré")
            return

        msg = (
            f"<b>{T_G} détectée !</b>\n"
            f"📦 <b>{item.title}</b>\n"
            f"💶 Prix: {item.raw_price}\n"
            f"🏷 Catégorie: {item.category_name}\n"
            f"⚡ Score: {item.score:.2f}\n"
            f"🔗 <a href='{item.url}'>Voir l'annonce</a>"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if resp.status != 200 or not data.get("ok"):
                    log.warning("Telegram error: %s", data)
                else:
                    log.info("Telegram: message envoyé pour %s", item.title[:30])

    @staticmethod
    async def test() -> None:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if not (token and chat_id):
            print("Telegram: pas de token/ID configuré")
            return
        msg = "Test de connexion au notifier Telegram eBay-Bot."
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        print("Telegram: test OK")
                    else:
                        print("Telegram: erreur", data)
            except Exception as e:
                print("Telegram: connexion échouée:", e)
