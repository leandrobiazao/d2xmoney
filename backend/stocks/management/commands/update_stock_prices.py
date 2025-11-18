"""
Management command to update stock prices daily.
"""
from django.core.management.base import BaseCommand
from stocks.services import StockService


class Command(BaseCommand):
    help = 'Update stock prices from Google Finance API'

    def handle(self, *args, **options):
        self.stdout.write('Starting stock price update...')
        result = StockService.update_prices_daily()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {result["updated"]} out of {result["total"]} stocks'
            )
        )
        
        if result['errors']:
            self.stdout.write(
                self.style.WARNING(f'Errors encountered: {len(result["errors"])}')
            )
            for error in result['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))


