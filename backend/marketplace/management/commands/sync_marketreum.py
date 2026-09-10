import os

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from marketplace.models import Provider, Service
from marketplace.marketreum import MarketreumClient


class Command(BaseCommand):
    help = "Import the Marketreum service catalog into the HopeSocial marketplace"

    def add_arguments(self, parser):
        parser.add_argument(
            "--margin",
            type=float,
            default=None,
            help="Override the selling markup percentage",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Deactivate previously imported Marketreum services that are no longer returned",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        api_url = (
            os.environ.get("MARKETREUM_API_URL")
            or MarketreumClient.DEFAULT_API_URL
        ).strip()
        api_key = os.environ.get("MARKETREUM_API_KEY", "").strip()

        if not api_key:
            self.stdout.write(self.style.ERROR("MARKETREUM_API_KEY is not configured."))
            return

        margin_value = (
            options["margin"]
            if options["margin"] is not None
            else os.environ.get("MARKETREUM_MARGIN_PERCENTAGE", "30")
        )
        margin = Decimal(str(margin_value))

        provider, _ = Provider.objects.update_or_create(
            name=os.environ.get("MARKETREUM_PROVIDER_NAME", "Marketreum"),
            defaults={
                "api_url": api_url,
                "api_key": api_key,
                "margin_percentage": margin,
                "is_active": True,
            },
        )

        client = MarketreumClient(api_url, api_key)

        try:
            remote_services = client.get_services()
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Marketreum service sync failed: {exc}"))
            return

        self.stdout.write(f"Fetched {len(remote_services)} services from Marketreum.")

        imported_ids: set[str] = set()
        created = 0
        updated = 0

        for item in remote_services:
            normalized = client.normalize(item, margin)
            external_id = normalized.pop("external_id")
            if not external_id:
                self.stdout.write(
                    self.style.WARNING("Skipped Marketreum record without a service ID.")
                )
                continue

            imported_ids.add(external_id)

            # Existing HopeSocial marketplace structure is retained. Every
            # Marketreum catalog record is a provider service because the
            # documented API exposes a `services` action, not a products action.
            defaults = {
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
                "listing_type": "service",
                "badge": normalized["service_type"],
            }

            service, was_created = Service.objects.update_or_create(
                provider=provider,
                provider_service_id=external_id,
                listing_type="service",
                defaults=defaults,
            )

            if was_created:
                created += 1
                self.stdout.write(f"  + {service.platform} / {service.category} / {service.name}")
            else:
                updated += 1

        if options["deactivate_missing"]:
            stale = Service.objects.filter(provider=provider).exclude(
                provider_service_id__in=imported_ids
            )
            stale_count = stale.update(is_active=False)
            if stale_count:
                self.stdout.write(
                    self.style.WARNING(f"Deactivated {stale_count} stale Marketreum services.")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Marketreum sync complete: {created} created, {updated} updated, "
                f"{len(imported_ids)} active catalog records processed."
            )
        )
