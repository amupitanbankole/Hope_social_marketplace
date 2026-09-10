import os
from decimal import Decimal, InvalidOperation
from typing import Any

import requests


class MarketreumClient:
    """Client for the Marketerum/Marketreum REST API v2.

    The documented API exposes a single POST endpoint. Authentication and the
    requested operation are sent as form data:
        key=<API key>&action=services

    The service catalog is the source of truth for the social marketplace.
    """

    DEFAULT_API_URL = "https://marketerum.com/api/v2"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (
            base_url
            or os.environ.get("MARKETREUM_API_URL")
            or self.DEFAULT_API_URL
        ).strip().rstrip("/")
        self.api_key = (api_key or os.environ.get("MARKETREUM_API_KEY", "")).strip()
        self.timeout = int(os.environ.get("MARKETREUM_TIMEOUT", "20"))

    def _post(self, action: str, **payload: Any) -> Any:
        if not self.base_url:
            raise ValueError("MARKETREUM_API_URL is not configured")
        if not self.api_key:
            raise ValueError("MARKETREUM_API_KEY is not configured")

        data = {"key": self.api_key, "action": action}
        data.update({key: value for key, value in payload.items() if value is not None})

        response = requests.post(
            self.base_url,
            data=data,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()

        if isinstance(result, dict) and result.get("error"):
            raise ValueError(str(result["error"]))
        return result

    @staticmethod
    def _unwrap_services(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("services", "results", "items", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def get_services(self) -> list[dict[str, Any]]:
        return self._unwrap_services(self._post("services"))

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

    @staticmethod
    def _bool(value: Any, default: bool = True) -> bool:
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip().lower() not in {
                "0", "false", "inactive", "disabled", "off", "no"
            }
        return bool(value)

    @staticmethod
    def detect_platform(name: str, category: str) -> str:
        """Map Marketerum category/service names to the marketplace buttons."""
        haystack = f"{name} {category}".lower()
        aliases = (
            (("instagram", "ig"), "Instagram"),
            (("facebook", "fb"), "Facebook"),
            (("tiktok", "tik tok", "tt"), "TikTok"),
            (("twitter", "twitter/x", " x "), "Twitter/X"),
            (("telegram",), "Telegram"),
            (("discord",), "Discord"),
            (("youtube", "youtube", "yt"), "YouTube"),
            (("linkedin", "linked in"), "LinkedIn"),
            (("pinterest",), "Pinterest"),
            (("snapchat",), "Snapchat"),
        )
        for aliases_for_platform, label in aliases:
            if any(alias in haystack for alias in aliases_for_platform):
                return label
        return "Social Marketplace"

    def normalize(
        self,
        item: dict[str, Any],
        margin_pct: Decimal,
    ) -> dict[str, Any]:
        """Normalize one documented Marketreum service for the Service model."""
        external_id = self._first(
            item, "service", "service_id", "id", "code", default=""
        )
        name = self._first(item, "name", "service_name", "title", default="Marketreum service")
        category = str(self._first(item, "category", default="General"))
        service_type = str(self._first(item, "type", default="Default"))
        platform = self.detect_platform(str(name), category)

        provider_rate = self._decimal(self._first(item, "rate", "price", default="0"))
        selling_rate = (
            provider_rate * (Decimal("1.00") + margin_pct / Decimal("100"))
        ).quantize(Decimal("0.01"))

        min_order = int(self._first(item, "min", "minimum", default=1) or 1)
        max_order = int(self._first(item, "max", "maximum", default=100000) or 100000)
        min_order = max(1, min_order)
        max_order = max(min_order, max_order)

        refill = self._bool(self._first(item, "refill", default=False), default=False)
        cancel = self._bool(self._first(item, "cancel", default=False), default=False)

        description = (
            f"{service_type} service. "
            f"Minimum order: {min_order:,}; maximum order: {max_order:,}. "
            f"Refill: {'available' if refill else 'not available'}; "
            f"Cancellation: {'available' if cancel else 'not available'}."
        )

        return {
            "external_id": str(external_id),
            "name": str(name),
            "category": category[:100],
            "platform": platform[:50],
            "description": description,
            "external_url": "",
            "image_url": "",
            "provider_rate": provider_rate,
            "rate_per_1k": selling_rate,
            "min_order": min_order,
            "max_order": max_order,
            "listing_type": "service",
            "is_active": self._bool(self._first(item, "active", "enabled", default=True)),
            "refill": refill,
            "cancel": cancel,
            "service_type": service_type[:100],
        }

    def place_order(
        self,
        service_id: str | int,
        link: str,
        quantity: int | None = None,
        runs: int | None = None,
        interval: int | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Place a Marketreum order using the documented add operation."""
        payload: dict[str, Any] = {
            "service": service_id,
            "link": link,
            "quantity": quantity,
            "runs": runs,
            "interval": interval,
        }
        payload.update(extra)
        result = self._post("add", **payload)
        if isinstance(result, dict) and result.get("order") is not None:
            return {"success": True, "order_id": result["order"], "raw": result}
        return {
            "success": False,
            "error": result.get("error", "Marketreum did not return an order ID")
            if isinstance(result, dict)
            else "Invalid Marketreum response",
            "raw": result,
        }

    def get_order_status(self, order_id: str | int) -> dict[str, Any]:
        result = self._post("status", order=order_id)
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    def get_balance(self) -> dict[str, Any]:
        result = self._post("balance")
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    def create_refill(self, order_id: str | int) -> dict[str, Any]:
        result = self._post("refill", order=order_id)
        return result if isinstance(result, dict) else {"error": "Invalid response"}

    def cancel_orders(self, order_ids: list[str | int]) -> Any:
        return self._post("cancel", orders=",".join(str(item) for item in order_ids))
