"""
Django management command to refresh portfolio.json from brokerage notes.
This command rebuilds the entire portfolio.json file from all operations in brokerage_notes.json.
"""
from django.core.management.base import BaseCommand
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = 'Refresh portfolio.json from all brokerage notes'

    def handle(self, *args, **options):
        self.stdout.write('Refreshing portfolio from brokerage notes...')
        
        try:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            portfolio = PortfolioService.load_portfolio()
            
            users_count = len(portfolio)
            total_positions = sum(len(tickers) for tickers in portfolio.values())
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Portfolio refreshed successfully!\n'
                    f'   Users: {users_count}\n'
                    f'   Total ticker positions: {total_positions}'
                )
            )
            
            # Show summary per user
            for user_id, ticker_summaries in portfolio.items():
                positions_with_quantity = [t for t in ticker_summaries if t['quantidade'] > 0]
                positions_zero = [t for t in ticker_summaries if t['quantidade'] == 0]
                total_realized = sum(t['lucroRealizado'] for t in ticker_summaries)
                
                self.stdout.write(
                    f'\n  User: {user_id[:8]}...\n'
                    f'    Active positions: {len(positions_with_quantity)}\n'
                    f'    Zero quantity positions: {len(positions_zero)}\n'
                    f'    Total realized profit: R$ {total_realized:.2f}'
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error refreshing portfolio: {e}')
            )
            raise

