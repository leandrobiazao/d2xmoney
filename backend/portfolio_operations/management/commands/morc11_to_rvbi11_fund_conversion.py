"""
Create MORC11 -> RVBI11 fund conversion corporate event (VBI Reits consolidation).

MORC11 was extinguished and merged into RVBI11. Cotistas received 1.12026315
RVBI11 shares per MORC11 share on 2024-03-27 (remaining R$ 3.07/cota paid in cash
on 2024-04-10).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from brokerage_notes.services import BrokerageNoteHistoryService
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService

FAKE_RVBI_BUY_OP_ID = "op-rvbi-open-64459174"


class Command(BaseCommand):
    help = "Create MORC11 -> RVBI11 fund conversion event and refresh portfolio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh portfolio after creating or updating the event",
        )
        parser.add_argument(
            "--remove-fake-rvbi-buy",
            action="store_true",
            help=(
                "Remove the synthetic RVBI11 buy added to fix a short position; "
                "RVBI shares should come from the MORC11 conversion instead"
            ),
        )

    def handle(self, *args, **options):
        previous_ticker = "MORC11"
        new_ticker = "RVBI11"
        ex_date = "2024-03-27"
        ratio = "1.12026315:1"
        description = (
            "VBI Reits consolidation: MORC11 (More Cidades) was extinguished and "
            "merged into RVBI11 (VBI Reits Multiestrategia). Trading suspended "
            "2024-02-02. RVBI11 delivery: 1.12026315 shares per MORC11 share on "
            "2024-03-27; remaining R$ 3.07 per cota paid in cash on 2024-04-10."
        )

        existing = CorporateEvent.objects.filter(
            event_type="FUND_CONVERSION",
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
                    previous_ticker=previous_ticker,
                    ticker=new_ticker,
                    event_type="FUND_CONVERSION",
                    asset_type="FII",
                    ex_date=ex_date,
                    ratio=ratio,
                    description=description,
                    applied=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Event created: ID {event.id} - {previous_ticker} -> {new_ticker}"
                    )
                )

        if options["remove_fake_rvbi_buy"]:
            self._remove_fake_rvbi_buy()

        if options["refresh"]:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            self.stdout.write(self.style.SUCCESS("Portfolio refreshed."))

    def _remove_fake_rvbi_buy(self) -> None:
        note_data = None
        for note in BrokerageNoteHistoryService.load_history():
            ops = note.get("operations") or []
            if any(op.get("id") == FAKE_RVBI_BUY_OP_ID for op in ops):
                note_data = note
                break

        if not note_data:
            self.stdout.write(
                self.style.WARNING(
                    f"Synthetic RVBI buy {FAKE_RVBI_BUY_OP_ID} not found; skipping"
                )
            )
            return

        before = len(note_data["operations"])
        note_data["operations"] = [
            op
            for op in note_data["operations"]
            if op.get("id") != FAKE_RVBI_BUY_OP_ID
        ]
        note_data["operations_count"] = len(note_data["operations"])
        BrokerageNoteHistoryService._save_note_data(note_data)
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed synthetic RVBI buy from {note_data.get('file_name')} "
                f"({before} -> {note_data['operations_count']} operations)"
            )
        )
