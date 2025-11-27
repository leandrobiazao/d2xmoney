"""
Management command to remove duplicate Tesouro Direto positions.
Duplicates are identified by having the same user_id and asset_code.
For each duplicate set, keeps the most recent position and deletes the others.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from fixed_income.models import FixedIncomePosition, TesouroDiretoPosition
from configuration.models import InvestmentSubType


class Command(BaseCommand):
    help = 'Remove duplicate Tesouro Direto positions (same user_id and asset_code)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='Filter by specific user_id',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id_filter = options.get('user_id')

        self.stdout.write('=' * 60)
        self.stdout.write('Removing Duplicate Tesouro Direto Positions')
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE] - No changes will be made\n'))
        
        # Get Tesouro Direto sub-type to filter only Tesouro positions
        try:
            tesouro_subtype = InvestmentSubType.objects.get(code='TESOURO_DIRETO')
        except InvestmentSubType.DoesNotExist:
            self.stdout.write(self.style.ERROR('TESOURO_DIRETO sub-type not found in database'))
            return

        # Find all Tesouro Direto positions
        queryset = FixedIncomePosition.objects.filter(
            investment_sub_type=tesouro_subtype
        )
        
        if user_id_filter:
            queryset = queryset.filter(user_id=user_id_filter)
            self.stdout.write(f'Filtering by user_id: {user_id_filter}\n')

        # Find duplicates: positions with same user_id and asset_code
        duplicates = (
            queryset
            .values('user_id', 'asset_code')
            .annotate(count=Count('id'), latest_created=Max('created_at'))
            .filter(count__gt=1)
            .order_by('user_id', 'asset_code')
        )

        if not duplicates.exists():
            self.stdout.write(self.style.SUCCESS('\n[OK] No duplicates found!'))
            return

        total_duplicate_sets = duplicates.count()
        total_to_delete = 0
        deleted_count = 0

        self.stdout.write(f'\n[INFO] Found {total_duplicate_sets} duplicate set(s)\n')

        for dup in duplicates:
            user_id = dup['user_id']
            asset_code = dup['asset_code']
            count = dup['count']
            latest_created = dup['latest_created']
            
            # Get all positions with this user_id and asset_code
            positions = queryset.filter(
                user_id=user_id,
                asset_code=asset_code
            ).order_by('-created_at')

            # The first one is the most recent (keep this one)
            position_to_keep = positions.first()
            positions_to_delete = list(positions[1:])  # All others are duplicates

            self.stdout.write(f'\n[DUPLICATE SET] {asset_code}')
            self.stdout.write(f'   User: {user_id}')
            self.stdout.write(f'   Total positions: {count}')
            self.stdout.write(f'   Keeping (most recent): ID {position_to_keep.id}')
            self.stdout.write(f'     Created: {position_to_keep.created_at}')
            self.stdout.write(f'     Application Date: {position_to_keep.application_date}')
            
            for pos in positions_to_delete:
                total_to_delete += 1
                self.stdout.write(f'   [DELETE] ID {pos.id}')
                self.stdout.write(f'     Created: {pos.created_at}')
                self.stdout.write(f'     Application Date: {pos.application_date}')
                
                # Check if it has a TesouroDiretoPosition
                if hasattr(pos, 'tesouro_direto'):
                    tesouro_pos = pos.tesouro_direto
                    self.stdout.write(f'     Tesouro: {tesouro_pos.titulo_name} - {tesouro_pos.vencimento}')
                
                if not dry_run:
                    # Delete the duplicate position
                    # TesouroDiretoPosition will be deleted automatically via CASCADE
                    pos.delete()
                    deleted_count += 1
                    self.stdout.write(f'     [DELETED]')
                else:
                    self.stdout.write(f'     [WOULD DELETE - dry-run]')

        if dry_run:
            self.stdout.write(f'\n\n[SUMMARY - DRY RUN]:')
            self.stdout.write(f'   Duplicate sets found: {total_duplicate_sets}')
            self.stdout.write(f'   Positions that would be deleted: {total_to_delete}')
            self.stdout.write(self.style.WARNING('\n[WARNING] Run without --dry-run to actually delete duplicates'))
        else:
            self.stdout.write(f'\n\n[SUMMARY]:')
            self.stdout.write(f'   Duplicate sets processed: {total_duplicate_sets}')
            self.stdout.write(f'   Positions deleted: {deleted_count}')
            self.stdout.write(self.style.SUCCESS(f'\n[SUCCESS] Successfully removed {deleted_count} duplicate position(s)!'))

