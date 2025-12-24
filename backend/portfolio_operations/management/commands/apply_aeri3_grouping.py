"""
Django management command to create and apply the AERI3 grouping event (20:1 reverse split).
Event date: May 14, 2024
Approval: April 11, 2024
Ratio: 20:1 (every 20 old shares become 1 new share)
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = 'Cria e aplica o evento de grupamento AERI3 (20:1) de 14/05/2024'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplicar o ajuste automaticamente após criar o evento',
        )
        parser.add_argument(
            '--user-id',
            type=str,
            default=None,
            help='ID do usuário para aplicar apenas a esse usuário (opcional)',
        )

    def handle(self, *args, **options):
        ticker = 'AERI3'
        ex_date = '2024-05-14'
        ratio = '20:1'
        description = (
            'Grupamento de ações da Aeris na proporção de 20 para 1. '
            'Aprovação: Assembleia Geral em 11/04/2024. '
            'Data ex-grupamento: 14/05/2024. '
            'Cada lote de 20 ações ordinárias existentes foi agrupado em uma única ação.'
        )

        self.stdout.write(f'Criando evento corporativo para {ticker}...')

        # Check if event already exists
        existing_event = CorporateEvent.objects.filter(
            ticker=ticker,
            ex_date=ex_date,
            event_type='GROUPING'
        ).first()

        if existing_event:
            self.stdout.write(
                self.style.WARNING(
                    f'Evento já existe: ID {existing_event.id} - {existing_event}'
                )
            )
            event = existing_event
        else:
            # Create the event
            with transaction.atomic():
                event = CorporateEvent.objects.create(
                    ticker=ticker,
                    event_type='GROUPING',
                    asset_type='STOCK',
                    ex_date=ex_date,
                    ratio=ratio,
                    description=description,
                    applied=False
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Evento criado com sucesso: ID {event.id}'
                    )
                )

        # Apply the adjustment if requested
        if options['apply']:
            self.stdout.write('Aplicando ajuste ao portfólio...')
            try:
                user_id = options.get('user_id')
                result = PortfolioService.apply_corporate_event(event, user_id=user_id)
                
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Ajuste aplicado: {result['message']}"
                        )
                    )
                    if 'positions_adjusted' in result:
                        self.stdout.write(
                            f"Posições ajustadas: {result['positions_adjusted']}"
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(result.get('message', 'Ajuste não aplicado'))
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Erro ao aplicar ajuste: {str(e)}')
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Evento criado mas não aplicado. Use --apply para aplicar o ajuste.'
                )
            )
            self.stdout.write(
                f'Para aplicar manualmente, use a interface web ou execute: '
                f'python manage.py apply_aeri3_grouping --apply'
            )





