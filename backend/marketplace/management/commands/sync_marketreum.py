import os

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from marketplace.models import Provider, Service
from marketplace.marketreum import MarketreumClient


PLATFORM_ALIASES = {
    "instagram": "Instagram",
    "ig": "Instagram",
    "facebook": "Facebook",
    "fb": "Facebook",
    "tiktok": "TikTok",
    "tt": "TikTok",
    "twitter": "Twitter/X",
    "twitter/x": "Twitter/X",
    "x": "Twitter/X",
    "telegram": "Telegram",
    "discord": "Discord",
    "youtube": "YouTube",
    "yt": "YouTube",
    "linkedin": "LinkedIn",
    "pinterest": "Pinterest",
    "snapchat": "Snapchat",
}


def normalize_platform(value: str, name: str, category: str) -> str:
    haystack = f"{value} {name} {category}".lower()
    for alias, label in PLATFORM_ALIASES.items():
        if alias in haystack:
            return label
    return value.strip()[:50] or "Social Marketplace"


class Command(BaseCommand):
    help = "Import Marketreum products and services into the HopeSocial marketplace catalog"

    def add_arguments(self, parser):
        parser.add_argument(
            "--margin",
            type=float,
            default=None,
            help="Override the Marketreum selling markup percentage",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Deactivate previously imported Marketreum items that are no longer returned",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        api_url = os.environ.get("MARKETREUM_API_URL", "").strip()
        api_key = os.environ.get("MARKETREUM_API_KEY", "").strip()

        if not api_url:
            self.stdout.write(self.style.ERROR("MARKETREUM_API_URL is not configured."))
            return
        if not api_key:
            self.stdout.write(self.style.ERROR("MARKETREUM_API_KEY is not configured."))
            return

        provider, _ = Provider.objects.update_or_create(
            name=os.environ.get("MARKETREUM_PROVIDER_NAME", "Marketreum"),
            defaults={
                "api_url": api_url,
                "api_key": api_key,
                "margin_percentage": Decimal(str(options["margin"] if options["margin"] is not None else os.environ.get("MARKETREUM_MARGIN_PERCENTAGE", "30"))),
                "is_active": True,
            },
        )

        margin = provider.margin_percentage
        client = MarketreumClient(api_url, api_key)

        try:
            remote_services = client.get_services()
            self.stdout.write(f"Fetched {len(remote_services)} Marketreum services.")
        except Exception as exc:
            remote_services = []
            self.stdout.write(self.style.WARNING(f"Could not fetch Marketreum services: {exc}"))

        try:
            remote_products = client.get_products()
            self.stdout.write(f"Fetched {len(remote_products)} Marketreum products.")
        except Exception as exc:
            remote_products = []
            self.stdout.write(self.style.WARNING(f"Could not fetch Marketreum products: {exc}"))

        imported_keys = set()
        imported = 0
        updated = 0

        for listing_type, items in (("service", remote_services), ("product", remote_products)):
            for item in items:
                normalized = client.normalize(item, listing_type, margin)
                external_id = normalized["external_id"]
                if not external_id:
                    self.stdout.write(self.style.WARNING("Skipped Marketreum item without an external id."))
                    continue

                normalized["platform"] = normalize_platform(
                    normalized["platform"], normalized["name"], normalized["category"]
                )

                provider_key = f"{listing_type}:{external_id}"
                imported_keys.add(provider_key)

                existing = Service.objects.filter(
                    provider=provider,
                    provider_service_id=external_id,
                    listing_type=listing_type,
                ).first()

                service, created = Service.objects.update_or_create(
                    provider=provider,
                    provider_service_id=external_id,
                    listing_type=listing_type,
                    defaults={
                        "platform": normalized["platform"],
                        "category": normalized["category"],
                        "name": normalized["name"],
                        "provider_rate": normalized["provider_rate"],
                        "rate_per_1k": normalized["rate_per_1k"],
                        "min_order": normalized["min_order"],
                        "max_order": normalized["max_order"],
                        "description": normalized["description"],
                        "external_url": normalized["external_url"],
                        "image_url": normalized["image_url"],
                        "is_active": normalized["is_active"],
                    },
                )

                imported += 1
                if created or existing is None:
                    self.stdout.write(f"  + {listing_type}: {service.name}")
                else:
                    updated += 1

        if options["deactivate_missing"]:
            queryset = Service.objects.filter(provider=provider)
            to_deactivate = []
            for service in queryset.only("id", "provider_service_id", "listing_type"):
                key = f"{service.listing_type}:{service.provider_service_id}"
                if key not in imported_keys:
                    to_deactivate.append(service.id)
            if to_deactivate:
                Service.objects.filter(id__in=to_deactivate).update(is_active=False)
                self.stdout.write(self.style.WARNING(f"Deactivated {len(to_deactivate)} stale Marketreum items."))

        self.stdout.write(
            self.style.SUCCESS(
                f"Marketreum sync complete: {imported} items processed, {updated} existing items updated."
            )
        )
