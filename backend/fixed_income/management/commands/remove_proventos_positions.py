"""
Management command to remove proventos, dividendos, and distribuições positions.
"""
from django.core.management.base import BaseCommand
from fixed_income.models import FixedIncomePosition


class Command(BaseCommand):
    help = 'Remove FixedIncomePosition entries that are proventos, dividendos, or distribuições'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            help='Remove positions only for a specific user_id',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        dry_run = options.get('dry_run', False)
        
        excluded_keywords = [
            'proventos', 'dividendos', 'distribuições', 'distribuicoes',
            'rendimentos', 'juros', 'amortização', 'amortizacao',
            'resgate', 'liquidação', 'liquidacao'
        ]
        
        queryset = FixedIncomePosition.objects.all()
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Find positions with excluded keywords in asset_name
        positions_to_delete = []
        for pos in queryset:
            asset_name_lower = (pos.asset_name or '').lower()
            if any(keyword in asset_name_lower for keyword in excluded_keywords):
                positions_to_delete.append(pos)
        
        if dry_run:
            self.stdout.write(f'Would delete {len(positions_to_delete)} position(s):')
            for pos in positions_to_delete:
                self.stdout.write(f'  - {pos.asset_name} (ID: {pos.id}, User: {pos.user_id})')
        else:
            count = len(positions_to_delete)
            for pos in positions_to_delete:
                pos.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully removed {count} position(s)'))

