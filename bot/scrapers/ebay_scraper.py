"""Scraper eBay.fr pour la catégorie Télévision & Caméscope."""

import aiohttp
import random
import asyncio
import logging
from dataclasses import dataclass, asdict
from utils.settings import settings

log = logging.getLogger(__name__)

CAT_TV = "175711"
CAT_PHOTO = "625"

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWeb" +
            "Kit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Ap" +
            "pleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" +
            " (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.8",
    },
]

FILTER_NEW_OPEN = "LH_ItemCondition=1000\|1500"


@dataclass(frozen=True)
class Listing:
    id: str
    title: str
    raw_price: str
    url: str
    category_id: str
    category_name: str
    seller_name: str | None  # à enrichir plus tard
    _score_value: float = 0.0

    @property
    def score(self) -> float:
        """Score d'opportunité élevé = meilleure affaire."""
        return self._score_value

    @property
    def as_dict(self) -> dict:
        return asdict(self)


class eBayScraper:
    """Scraper asynchrone pour eBay France."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            proxy = settings.PROXY_URL or None
            conn = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(
                connector=conn,
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @staticmethod
    def _build_url(keyword: str, cat: str) -> str:
        params = [
            "_nkw=" + keyword,
            "_sop=10",  # Argentina length not specified
            "LH_BIN=1",
            FILTER_NEW_OPEN,
            f"LH_CAT={cat}",
            "_oaa=1",
        ]
        return "https://www.ebay.fr/sch/i.html?" + "&".join(params)

    async def search_ebay(self, keyword: str) -> list[Listing]:
        """Recherche eBay pour un mot-clée donnée."""
        listings: list[Listing] = []
        cats = [(CAT_TV, "Tele"), (CAT_PHOTO, "Camera")]

        for cat_id, cat_name in cats:
            url = self._build_url(keyword, cat_id)
            headers = random.choice(HEADERS_POOL)
            result = await self._fetch_page(url, headers)
            if result:
                items = self._parse_page(html=result, cat_id=cat_id, cat_name=cat_name)
                listings.extend(items)
                log.info("Cat %s: %d annonces (keyword: %s)", cat_id, len(items), keyword)
            await asyncio.sleep(random.uniform(2, 4))

        return listings

    async def _fetch_page(self, url: str, headers: dict) -> str | None:
        session = await self._get_session()
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status == 200:
                        return await resp.text(encoding="utf-8")
                    log.warning("Status: %d (attempt %d)", resp.status, attempt + 1)
            except Exception as e:
                log.exception("Fetch error (attempt %d): %s", attempt + 1, e)
            await asyncio.sleep(3 * (attempt + 1))
        return None

    def _parse_page(self, *, html: str, cat_id: str, cat_name: str) -> list[Listing]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        items: list[Listing] = []
        for li in soup.select("ul.sr-results > li.s-item"):
            title_el = li.select_one("div.s-item__title span")
            link_el = li.select_one("a.s-item__link")
            price_el = li.select_one("span.s-item__price")
            if not (title_el and link_el and price_el):
                continue
            title = title_el.text.strip()
            raw_price = price_el.text.strip()
            url = link_el.get("href", "")
            item_id = self._extract_item_id(url)
            if not item_id:
                continue
            if self._is_bad_listing(title):
                continue
            items.append(
                Listing(
                    id=item_id,
                    title=title,
                    raw_price=raw_price,
                    url=url.split("?")[0],
                    category_id=cat_id,
                    category_name=cat_name,
                    seller_name=None,
                )
            )
        return items

    @staticmethod
    def _extract_item_id(url: str) -> str | None:
        try:
            p = url.split("/")
            for part in p:
                if part.isdigit():
                    return part
        except Exception:
            pass
        return None

    @staticmethod
    def _is_bad_listing(title: str) -> bool:
        t = title.lower()
        if any(x in t for x in ["for parts", "broken", "repair"]):
            return True
        if any(x in t for x in ["wall mount", "stand", "cover", "case", "manual"]):
            return True
        if len(title) < 10:
            return True
        return False
