"""
Create the BLAU3 share bonus corporate event (3 new shares for every 10 held).
Board approval: 29/12/2025. Record date (data-com): 05/01/2026.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = "Create BLAU3 bonificacao event (3:10, ex-date 2026-01-05) and refresh portfolio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh portfolio after creating or updating the event",
        )

    def handle(self, *args, **options):
        ticker = "BLAU3"
        ex_date = "2026-01-05"
        ratio = "3:10"
        description = (
            "Blau Farmaceutica: bonificacao de acoes na proporcao de 3 novas acoes "
            "para cada 10 possuidas, via capitalizacao de reservas de lucros (R$ 400 mi). "
            "Aprovacao do conselho em 29/12/2025. Data-com 05/01/2026, "
            "negociacao ex-bonificacao a partir de 06/01/2026, "
            "incorporacao das acoes em 08/01/2026."
        )

        self.stdout.write(f"Creating corporate event for {ticker} bonificacao...")

        existing = CorporateEvent.objects.filter(
            ticker=ticker,
            event_type="BONUS",
            ex_date=ex_date,
        ).first()

        if existing:
            self.stdout.write(
                self.style.WARNING(f"Event already exists: ID {existing.id} - {existing}")
            )
            event = existing
            updated = False
            if existing.ratio != ratio:
                existing.ratio = ratio
                updated = True
            if existing.description != description:
                existing.description = description
                updated = True
            if not existing.applied:
                existing.applied = True
                updated = True
            if updated:
                existing.save()
                self.stdout.write(self.style.SUCCESS("Updated existing event."))
        else:
            with transaction.atomic():
                event = CorporateEvent.objects.create(
                    ticker=ticker,
                    event_type="BONUS",
                    asset_type="STOCK",
                    ex_date=ex_date,
                    ratio=ratio,
                    description=description,
                    applied=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Event created: ID {event.id} - {ticker} BONUS {ratio}")
                )

        if options["refresh"]:
            self.stdout.write("Refreshing portfolio from brokerage notes...")
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            self.stdout.write(self.style.SUCCESS("Portfolio refreshed."))
        else:
            self.stdout.write(
                "Run with --refresh to rebuild portfolio with the new event."
            )
