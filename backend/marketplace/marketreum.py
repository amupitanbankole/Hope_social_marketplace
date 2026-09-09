import os
from decimal import Decimal, InvalidOperation
from typing import Any

import requests


class MarketreumClient:
    """Small adapter for importing Marketreum catalog data.

    Marketreum's public API reference was not discoverable from the supplied
    repository or public web search, so endpoint paths and authentication are
    configurable through environment variables. The adapter accepts common
    JSON response shapes and normalizes them for the HopeSocial catalog.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("MARKETREUM_API_URL", "")).strip().rstrip("/")
        self.api_key = (api_key or os.environ.get("MARKETREUM_API_KEY", "")).strip()
        self.auth_header = os.environ.get("MARKETREUM_AUTH_HEADER", "Authorization").strip()
        self.auth_scheme = os.environ.get("MARKETREUM_AUTH_SCHEME", "Bearer").strip()
        self.services_path = os.environ.get("MARKETREUM_SERVICES_PATH", "/services").strip()
        self.products_path = os.environ.get("MARKETREUM_PRODUCTS_PATH", "/products").strip()
        self.timeout = int(os.environ.get("MARKETREUM_TIMEOUT", "20"))

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            if self.auth_scheme:
                headers[self.auth_header] = f"{self.auth_scheme} {self.api_key}"
            else:
                headers[self.auth_header] = self.api_key
        return headers

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.base_url:
            raise ValueError("MARKETREUM_API_URL is not configured")
        response = requests.get(
            self._url(path),
            headers=self._headers(),
            params=params or {},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _unwrap(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
                if isinstance(value, dict):
                    nested = MarketreumClient._unwrap(value, keys)
                    if nested:
                        return nested
            data = payload.get("data")
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return MarketreumClient._unwrap(data, keys)
        return []

    def get_services(self) -> list[dict[str, Any]]:
        payload = self._request(self.services_path)
        return self._unwrap(payload, ("services", "results", "items"))

    def get_products(self) -> list[dict[str, Any]]:
        payload = self._request(self.products_path)
        return self._unwrap(payload, ("products", "results", "items"))

    @staticmethod
    def _first(item: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return default

    @staticmethod
    def _decimal(value: Any, default: str = "0.00") -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(default)

    def normalize(self, item: dict[str, Any], listing_type: str, margin_pct: Decimal) -> dict[str, Any]:
        external_id = self._first(item, "id", "service", "service_id", "product_id", "sku", "code", default="")
        name = self._first(item, "name", "title", "product_name", "service_name", default="Marketreum item")
        category = str(self._first(item, "category", "category_name", "type", default="General"))
        platform = str(self._first(item, "platform", "network", "channel", default="Social Marketplace"))
        description = str(self._first(item, "description", "short_description", "details", default=""))
        image_url = str(self._first(item, "image", "image_url", "thumbnail", "photo", default=""))
        external_url = str(self._first(item, "url", "link", "product_url", "service_url", default=""))
        raw_rate = self._first(item, "rate_per_1k", "rate", "price", "amount", "cost", default="0")
        provider_rate = self._decimal(raw_rate)
        selling_rate = (provider_rate * (Decimal("1.00") + margin_pct / Decimal("100"))).quantize(Decimal("0.01"))

        min_order = int(self._first(item, "min_order", "min", "minimum_quantity", default=1) or 1)
        max_order = int(self._first(item, "max_order", "max", "maximum_quantity", default=100000) or 100000)
        is_active = bool(self._first(item, "is_active", "active", "enabled", "status", default=True) not in (False, 0, "0", "false", "False", "inactive", "disabled"))

        return {
            "external_id": str(external_id),
            "name": str(name),
            "category": category[:100],
            "platform": platform[:50],
            "description": description,
            "image_url": image_url,
            "external_url": external_url,
            "provider_rate": provider_rate,
            "rate_per_1k": selling_rate,
            "min_order": max(1, min_order),
            "max_order": max(min_order, max_order),
            "listing_type": "product" if listing_type == "product" else "service",
            "is_active": is_active,
        }
