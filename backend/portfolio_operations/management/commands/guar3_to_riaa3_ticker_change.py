"""
Django management command to create the GUAR3 → RIAA3 ticker change event (Guararapes → Riachuelo).
Data efetiva na B3: 05/02/2026.
Cria apenas o evento corporativo TICKER_CHANGE. Com --apply migra posições e operações para RIAA3.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = 'Cria o evento de mudança de ticker GUAR3 → RIAA3 (Guararapes → Riachuelo, 05/02/2026)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplicar o ajuste automaticamente (atualiza posições e operações para RIAA3)',
        )

    def handle(self, *args, **options):
        previous_ticker = 'GUAR3'
        new_ticker = 'RIAA3'
        ex_date = '2026-02-05'
        description = (
            'Mudança de ticker e nome: Guararapes → Riachuelo. '
            'A Guararapes (GUAR3) passou a adotar o nome de pregão Riachuelo e o ticker RIAA3 na B3 em 05/02/2026, '
            'reforçando a identidade da marca Riachuelo.'
        )

        self.stdout.write(f'Criando evento de mudança de ticker {previous_ticker} → {new_ticker}...')

        existing = CorporateEvent.objects.filter(
            event_type='TICKER_CHANGE',
            previous_ticker=previous_ticker,
            ticker=new_ticker,
        ).first()

        if existing:
            self.stdout.write(
                self.style.WARNING(f'Evento já existe: ID {existing.id} - {previous_ticker} → {new_ticker}')
            )
            event = existing
        else:
            with transaction.atomic():
                event = CorporateEvent.objects.create(
                    previous_ticker=previous_ticker,
                    ticker=new_ticker,
                    event_type='TICKER_CHANGE',
                    asset_type='STOCK',
                    ex_date=ex_date,
                    ratio='',
                    description=description,
                    applied=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Evento criado: ID {event.id} - {previous_ticker} → {new_ticker}')
                )

        if options['apply']:
            self.stdout.write('Aplicando mudança de ticker (posições e operações)...')
            try:
                result = PortfolioService.apply_ticker_change(event)
                if result.get('success'):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Aplicado: {result.get('message', '')} "
                            f"(posições: {result.get('positions_updated', 0)}, "
                            f"operações: {result.get('operations_updated', 0)})"
                        )
                    )
                    event.applied = True
                    event.save()
                else:
                    self.stdout.write(self.style.WARNING(result.get('message', 'Não aplicado')))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao aplicar: {e}'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Evento criado e não aplicado. Para aplicar: '
                    'Configuração → Eventos Corporativos → Aplicar neste evento, '
                    'ou execute: python manage.py guar3_to_riaa3_ticker_change --apply'
                )
            )
