"""Fetches Jumia listing pages and turns product cards into Product records.

Jumia renders listings server side as <article class="prd ..."> cards. If Jumia
changes its markup, this is the only file that should need updating.
"""
import re
import time
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NG,en;q=0.9",
}


@dataclass
class Product:
    key: str
    name: str
    url: str
    price: float | None
    old_price: float | None
    discount: int | None
    items_left: int | None = None
    flash_sale: bool = False

    @property
    def effective_discount(self):
        if self.discount is not None:
            return self.discount
        if self.price and self.old_price and self.old_price > self.price:
            return round(100 * (1 - self.price / self.old_price))
        return 0


def parse_naira(text):
    """'₦ 1,234,500 - ₦ 1,300,000' -> 1234500.0 (the lowest price in a range)."""
    if not text:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    return float(m.group().replace(",", "")) if m else None


def _text(el):
    return el.get_text(" ", strip=True) if el else ""


def parse_listing(html, base_url, flash_sale=False):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for card in soup.select("article.prd"):
        link = card.select_one("a.core") or card.find("a", href=True)
        if not link or not link.get("href"):
            continue
        url = urljoin(base_url, link["href"])
        name = _text(card.select_one(".name")) or link.get("data-gtm-name", "")
        price = parse_naira(_text(card.select_one(".prc"))) or parse_naira(link.get("data-gtm-price"))
        old_price = parse_naira(_text(card.select_one(".old")))
        dsct = re.search(r"(\d+)\s*%", _text(card.select_one(".bdg._dsct")))
        left = re.search(r"(\d+)\s+items?\s+left", _text(card), re.I)
        key = link.get("data-gtm-id") or link.get("data-id") or url.split("?")[0]
        products.append(
            Product(
                key=key,
                name=name,
                url=url,
                price=price,
                old_price=old_price,
                discount=int(dsct.group(1)) if dsct else None,
                items_left=int(left.group(1)) if left else None,
                flash_sale=flash_sale or "flash" in " ".join(card.get("class", [])).lower(),
            )
        )
    return products


class JumiaClient:
    def __init__(self, base_url, delay_seconds=2.0):
        self.base_url = base_url.rstrip("/")
        self.delay = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, url):
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        time.sleep(self.delay)  # be polite: one request at a time with a gap
        return r.text

    def search(self, query, pages=1, sort=None):
        products = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/catalog/?q={quote_plus(query)}&page={page}"
            if sort:
                url += f"&sort={sort}"
            found = parse_listing(self._get(url), self.base_url)
            products += found
            if not found:
                break
        return products

    def listing(self, path, pages=1, flash_sale=False):
        products = []
        for page in range(1, pages + 1):
            url = urljoin(self.base_url + "/", path.lstrip("/"))
            url += ("&" if "?" in url else "?") + f"page={page}"
            found = parse_listing(self._get(url), self.base_url, flash_sale=flash_sale)
            products += found
            if not found:
                break
        return products
