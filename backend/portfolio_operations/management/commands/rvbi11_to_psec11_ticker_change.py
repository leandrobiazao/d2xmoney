"""
Create RVBI11 -> PSEC11 ticker change corporate event (Patria Securities rebrand).
Effective from market open on 2025-10-24.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = "Create RVBI11 -> PSEC11 ticker change event and refresh portfolio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh portfolio after creating or updating the event",
        )

    def handle(self, *args, **options):
        previous_ticker = "RVBI11"
        new_ticker = "PSEC11"
        ex_date = "2025-10-24"
        description = (
            "Patria Securities FII: RVBI11 changed name and ticker to PSEC11 "
            "(Patria Securities Fundo de Investimento Imobiliario). "
            "Effective from market open on 24/10/2025."
        )

        existing = CorporateEvent.objects.filter(
            event_type="TICKER_CHANGE",
            previous_ticker=previous_ticker,
            ticker=new_ticker,
        ).first()

        if existing:
            self.stdout.write(
                self.style.WARNING(f"Event already exists: ID {existing.id}")
            )
            event = existing
            updated = False
            if not event.applied:
                event.applied = True
                updated = True
            if event.ex_date.isoformat() != ex_date:
                event.ex_date = ex_date
                updated = True
            if event.description != description:
                event.description = description
                updated = True
            if updated:
                event.save()
        else:
            with transaction.atomic():
                event = CorporateEvent.objects.create(
                    previous_ticker=previous_ticker,
                    ticker=new_ticker,
                    event_type="TICKER_CHANGE",
                    asset_type="FII",
                    ex_date=ex_date,
                    ratio="",
                    description=description,
                    applied=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Event created: ID {event.id} - {previous_ticker} -> {new_ticker}"
                    )
                )

        if options["refresh"]:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            self.stdout.write(self.style.SUCCESS("Portfolio refreshed."))
