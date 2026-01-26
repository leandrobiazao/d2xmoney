"""
Django management command to add a single ticker mapping.
Usage: python manage.py add_ticker "WIZ CO ON NM" "WIZC3"
"""
from django.core.management.base import BaseCommand
from ticker_mappings.services import TickerMappingService


class Command(BaseCommand):
    help = 'Add a single ticker mapping'

    def add_arguments(self, parser):
        parser.add_argument('company_name', type=str, help='Company name (e.g., "WIZ CO ON NM")')
        parser.add_argument('ticker', type=str, help='Ticker symbol (e.g., "WIZC3")')

    def handle(self, *args, **options):
        company_name = options['company_name']
        ticker = options['ticker']
        
        self.stdout.write(f'Adding mapping: "{company_name}" -> "{ticker}"')
        
        try:
            # Check if mapping already exists
            existing_ticker = TickerMappingService.get_ticker(company_name)
            if existing_ticker:
                if existing_ticker == ticker.upper():
                    self.stdout.write(self.style.SUCCESS(f'✓ Mapping already exists: "{company_name}" -> "{existing_ticker}"'))
                    return
                else:
                    self.stdout.write(self.style.WARNING(f'⚠ Mapping exists with different ticker: "{company_name}" -> "{existing_ticker}"'))
                    self.stdout.write(f'Will update to: "{ticker.upper()}"')
            
            TickerMappingService.set_ticker(company_name, ticker)
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully added mapping: "{company_name}" -> "{ticker.upper()}"'))
            
            # Verify it was saved
            saved_ticker = TickerMappingService.get_ticker(company_name)
            if saved_ticker == ticker.upper():
                self.stdout.write(self.style.SUCCESS(f'✅ Verified: Mapping is correctly stored in database'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Warning: Mapping verification failed. Expected: {ticker.upper()}, Got: {saved_ticker}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error adding mapping: {e}'))
            import traceback
            traceback.print_exc()
            raise








