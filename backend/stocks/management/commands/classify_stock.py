"""
Classify a stock in the catalog (investment type, subtype, stock_class).

Example:
  python manage.py classify_stock XFIX11 --stock-class ETF --type-code FIIS --subtype-code ETF_FII
"""
from django.core.management.base import BaseCommand, CommandError

from configuration.models import InvestmentSubType, InvestmentType
from stocks.models import Stock


class Command(BaseCommand):
    help = 'Set investment type, subtype, and stock_class for a ticker'

    def add_arguments(self, parser):
        parser.add_argument('ticker', type=str, help='Ticker symbol (e.g. XFIX11)')
        parser.add_argument(
            '--stock-class',
            type=str,
            choices=['ON', 'PN', 'ETF', 'BDR', 'FII'],
            help='Stock class (e.g. ETF for ETF de FIIs)',
        )
        parser.add_argument(
            '--type-code',
            type=str,
            help='Investment type code (e.g. FIIS)',
        )
        parser.add_argument(
            '--subtype-code',
            type=str,
            help='Investment subtype code under that type (e.g. ETF_FII)',
        )
        parser.add_argument(
            '--ensure-subtype',
            action='store_true',
            help='Create subtype under type if missing (uses --subtype-name)',
        )
        parser.add_argument(
            '--subtype-name',
            type=str,
            default='ETF Imobiliário',
            help='Display name when --ensure-subtype creates the subtype',
        )

    def handle(self, *args, **options):
        ticker = options['ticker'].strip().upper()
        try:
            stock = Stock.objects.select_related('investment_type', 'investment_subtype').get(
                ticker=ticker
            )
        except Stock.DoesNotExist:
            raise CommandError(f'Stock {ticker} not found in catalog')

        if options['type_code']:
            try:
                inv_type = InvestmentType.objects.get(code=options['type_code'])
            except InvestmentType.DoesNotExist:
                raise CommandError(f'Investment type code {options["type_code"]!r} not found')
            stock.investment_type = inv_type

            if options['subtype_code']:
                subtype = InvestmentSubType.objects.filter(
                    investment_type=inv_type,
                    code=options['subtype_code'],
                ).first()
                if not subtype and options['ensure_subtype']:
                    subtype = InvestmentSubType.objects.create(
                        investment_type=inv_type,
                        code=options['subtype_code'],
                        name=options['subtype_name'],
                        display_order=5,
                        is_predefined=True,
                        is_active=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created subtype {subtype.code} ({subtype.name}) under {inv_type.name}'
                        )
                    )
                if not subtype:
                    raise CommandError(
                        f'Subtype {options["subtype_code"]!r} not found for {inv_type.name}. '
                        'Use --ensure-subtype to create it.'
                    )
                stock.investment_subtype = subtype

        if options['stock_class']:
            stock.stock_class = options['stock_class']

        stock.save()
        self.stdout.write(
            self.style.SUCCESS(
                f'{ticker}: class={stock.stock_class}, '
                f'type={stock.investment_type.name if stock.investment_type else "-"}, '
                f'subtype={stock.investment_subtype.name if stock.investment_subtype else "-"}'
            )
        )
