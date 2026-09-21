"""
Create XPSF11 1:10 split (desdobramento) corporate event.

Approved 2022-05-04, record date 2022-05-05, ex-date 2022-05-06.
Each pre-split cota became 10 post-split cotas; invested value unchanged.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = "Create XPSF11 1:10 split event and refresh portfolio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh portfolio after creating or updating the event",
        )

    def handle(self, *args, **options):
        ticker = "XPSF11"
        ex_date = "2022-05-06"
        # System convention: new:old (10 new shares per 1 old share)
        ratio = "10:1"
        description = (
            "XPSF11 desdobramento 1:10. Approved 2022-05-04, record date 2022-05-05, "
            "ex-date 2022-05-06. Each cota was split into 10 cotas; total invested "
            "value unchanged (price divided by 10)."
        )

        existing = CorporateEvent.objects.filter(
            event_type="SPLIT",
            ticker=ticker,
            ex_date=ex_date,
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
            if event.ratio != ratio:
                event.ratio = ratio
                updated = True
            if event.description != description:
                event.description = description
                updated = True
            if event.asset_type != "FII":
                event.asset_type = "FII"
                updated = True
            if updated:
                event.save()
        else:
            with transaction.atomic():
                event = CorporateEvent.objects.create(
                    ticker=ticker,
                    event_type="SPLIT",
                    asset_type="FII",
                    ex_date=ex_date,
                    ratio=ratio,
                    description=description,
                    applied=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Event created: ID {event.id} - {ticker} split {ratio}"
                    )
                )

        if options["refresh"]:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            self.stdout.write(self.style.SUCCESS("Portfolio refreshed."))
