import json
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import httpx
from app.services.import_engine.base import ProductSourceProvider
from app.services.import_engine.ssrf import safe_fetch_url
from app.core.logging import get_logger

logger = get_logger(__name__)


class GenericWebProvider(ProductSourceProvider):
    def can_handle(self, url: str) -> bool:
        return safe_fetch_url(url) is not None

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    async def fetch_product(self, url: str) -> Dict[str, Any]:
        safe_url = safe_fetch_url(url)
        if not safe_url:
            raise ValueError(f"URL failed safety check: {url}")

        async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers={"User-Agent": "VelnioBot/1.0"}) as client:
            response = await client.get(safe_url)
            response.raise_for_status()
            html = response.text

        return {
            "url": url,
            "html": html,
            "content_type": response.headers.get("content-type", ""),
            "status_code": response.status_code,
        }

    async def extract_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        html = raw_data.get("html", "")
        url = raw_data.get("url", "")

        result = {
            "source_url": url,
            "name": None,
            "description": None,
            "price": None,
            "currency": "USD",
            "images": [],
            "source_domain": urlparse(url).netloc if url else None,
        }

        json_ld = self._extract_json_ld(html)
        if json_ld:
            result.update(self._parse_json_ld(json_ld))

        og_data = self._extract_opengraph(html)
        if og_data:
            if not result["name"] and og_data.get("og:title"):
                result["name"] = og_data["og:title"]
            if not result["description"] and og_data.get("og:description"):
                result["description"] = og_data["og:description"]
            if og_data.get("og:image"):
                result["images"].append(og_data["og:image"])

        meta = self._extract_meta(html)
        if not result["name"] and meta.get("title"):
            result["name"] = meta["title"]
        if not result["description"] and meta.get("description"):
            result["description"] = meta["description"]

        return result

    def _extract_json_ld(self, html: str) -> Optional[Dict]:
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    return data
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            return item
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _parse_json_ld(self, data: Dict) -> Dict[str, Any]:
        result = {}
        if data.get("name"):
            result["name"] = data["name"]
        if data.get("description"):
            result["description"] = data["description"]
        offers = data.get("offers", {})
        if isinstance(offers, dict):
            if offers.get("price"):
                try:
                    result["price"] = float(offers["price"])
                except (ValueError, TypeError):
                    pass
            if offers.get("priceCurrency"):
                result["currency"] = offers["priceCurrency"]
        images = data.get("image", [])
        if isinstance(images, str):
            images = [images]
        if isinstance(images, list):
            result["images"] = images[:5]
        return result

    def _extract_opengraph(self, html: str) -> Dict[str, str]:
        og_data = {}
        pattern = r'<meta[^>]*property=["\']og:(\w+)["\'][^>]*content=["\']([^"\']+)["\']'
        matches = re.findall(pattern, html, re.IGNORECASE)
        for key, value in matches:
            og_data[f"og:{key}"] = value
        return og_data

    def _extract_meta(self, html: str) -> Dict[str, str]:
        meta = {}
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        if title_match:
            meta["title"] = title_match.group(1).strip()
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if desc_match:
            meta["description"] = desc_match.group(1).strip()
        return meta
