#!/usr/bin/env python
"""
Simple script to add a ticker mapping directly.
Usage: python add_ticker_mapping.py "WIZ CO ON NM" "WIZC3"
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio_api.settings')
django.setup()

from ticker_mappings.services import TickerMappingService

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python add_ticker_mapping.py <company_name> <ticker>")
        print('Example: python add_ticker_mapping.py "WIZ CO ON NM" "WIZC3"')
        sys.exit(1)
    
    company_name = sys.argv[1]
    ticker = sys.argv[2]
    
    print(f'Adding mapping: "{company_name}" -> "{ticker}"')
    
    try:
        TickerMappingService.set_ticker(company_name, ticker)
        print(f'✅ Successfully added mapping: "{company_name}" -> "{ticker}"')
        
        # Verify it was saved
        saved_ticker = TickerMappingService.get_ticker(company_name)
        if saved_ticker == ticker.upper():
            print(f'✅ Verified: Mapping is correctly stored in database')
        else:
            print(f'⚠️ Warning: Mapping verification failed. Expected: {ticker.upper()}, Got: {saved_ticker}')
    except Exception as e:
        print(f'❌ Error adding mapping: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)








