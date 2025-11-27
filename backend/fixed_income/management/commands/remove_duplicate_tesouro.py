"""
Management command to remove duplicate Tesouro Direto positions.
Duplicates are identified by:
1. Same user_id and asset_code, OR
2. Same user_id, titulo_name, and vencimento (through TesouroDiretoPosition)
For each duplicate set, keeps the most recent position and deletes the others.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from fixed_income.models import FixedIncomePosition, TesouroDiretoPosition
from configuration.models import InvestmentSubType


class Command(BaseCommand):
    help = 'Remove duplicate Tesouro Direto positions (by asset_code or titulo_name+vencimento)'

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

        # Find duplicates by asset_code (same user_id and asset_code)
        duplicates_by_code = (
            queryset
            .values('user_id', 'asset_code')
            .annotate(count=Count('id'), latest_created=Max('created_at'))
            .filter(count__gt=1)
            .order_by('user_id', 'asset_code')
        )

        # Also find duplicates by titulo_name and vencimento (through TesouroDiretoPosition)
        # This catches cases where asset_code might differ but it's the same bond
        tesouro_positions = TesouroDiretoPosition.objects.filter(
            fixed_income_position__investment_sub_type=tesouro_subtype
        )
        
        if user_id_filter:
            tesouro_positions = tesouro_positions.filter(fixed_income_position__user_id=user_id_filter)
        
        duplicates_by_titulo = (
            tesouro_positions
            .values('fixed_income_position__user_id', 'titulo_name', 'vencimento')
            .annotate(count=Count('id'), latest_created=Max('fixed_income_position__created_at'))
            .filter(count__gt=1)
            .order_by('fixed_income_position__user_id', 'titulo_name', 'vencimento')
        )

        if not duplicates_by_code.exists() and not duplicates_by_titulo.exists():
            self.stdout.write(self.style.SUCCESS('\n[OK] No duplicates found!'))
            return

        total_duplicate_sets = 0
        total_to_delete = 0
        deleted_count = 0
        processed_positions = set()  # Track positions we've already processed

        # Process duplicates by asset_code
        if duplicates_by_code.exists():
            total_duplicate_sets += duplicates_by_code.count()
            self.stdout.write(f'\n[INFO] Found {duplicates_by_code.count()} duplicate set(s) by asset_code\n')

            for dup in duplicates_by_code:
                user_id = dup['user_id']
                asset_code = dup['asset_code']
                count = dup['count']
                
                # Get all positions with this user_id and asset_code
                positions = queryset.filter(
                    user_id=user_id,
                    asset_code=asset_code
                ).order_by('-created_at')

                # The first one is the most recent (keep this one)
                position_to_keep = positions.first()
                positions_to_delete = list(positions[1:])  # All others are duplicates

                self.stdout.write(f'\n[DUPLICATE SET BY ASSET_CODE] {asset_code}')
                self.stdout.write(f'   User: {user_id}')
                self.stdout.write(f'   Total positions: {count}')
                self.stdout.write(f'   Keeping (most recent): ID {position_to_keep.id}')
                self.stdout.write(f'     Created: {position_to_keep.created_at}')
                self.stdout.write(f'     Application Date: {position_to_keep.application_date}')
                
                # Mark all positions in this set as processed
                processed_positions.add(position_to_keep.id)
                
                for pos in positions_to_delete:
                    if pos.id in processed_positions:
                        continue  # Skip if already processed
                    processed_positions.add(pos.id)
                    total_to_delete += 1
                    self.stdout.write(f'   [DELETE] ID {pos.id}')
                    self.stdout.write(f'     Created: {pos.created_at}')
                    self.stdout.write(f'     Application Date: {pos.application_date}')
                    
                    # Check if it has a TesouroDiretoPosition
                    try:
                        tesouro_pos = pos.tesouro_direto
                        self.stdout.write(f'     Tesouro: {tesouro_pos.titulo_name} - {tesouro_pos.vencimento}')
                    except TesouroDiretoPosition.DoesNotExist:
                        pass
                    
                    if not dry_run:
                        # Delete the duplicate position
                        # TesouroDiretoPosition will be deleted automatically via CASCADE
                        pos.delete()
                        deleted_count += 1
                        self.stdout.write(f'     [DELETED]')
                    else:
                        self.stdout.write(f'     [WOULD DELETE - dry-run]')

        # Process duplicates by titulo_name and vencimento
        if duplicates_by_titulo.exists():
            total_duplicate_sets += duplicates_by_titulo.count()
            self.stdout.write(f'\n[INFO] Found {duplicates_by_titulo.count()} duplicate set(s) by titulo_name and vencimento\n')

            for dup in duplicates_by_titulo:
                user_id = dup['fixed_income_position__user_id']
                titulo_name = dup['titulo_name']
                vencimento = dup['vencimento']
                count = dup['count']
                
                # Get all TesouroDiretoPosition with this titulo_name and vencimento for this user
                tesouro_dups = TesouroDiretoPosition.objects.filter(
                    fixed_income_position__user_id=user_id,
                    fixed_income_position__investment_sub_type=tesouro_subtype,
                    titulo_name=titulo_name,
                    vencimento=vencimento
                ).select_related('fixed_income_position').order_by('-fixed_income_position__created_at')

                # The first one is the most recent (keep this one)
                tesouro_to_keep = tesouro_dups.first()
                tesouro_to_delete = list(tesouro_dups[1:])

                self.stdout.write(f'\n[DUPLICATE SET BY TITULO] {titulo_name} - {vencimento}')
                self.stdout.write(f'   User: {user_id}')
                self.stdout.write(f'   Total positions: {count}')
                self.stdout.write(f'   Keeping (most recent): ID {tesouro_to_keep.fixed_income_position.id}')
                self.stdout.write(f'     Created: {tesouro_to_keep.fixed_income_position.created_at}')
                self.stdout.write(f'     Asset Code: {tesouro_to_keep.fixed_income_position.asset_code}')
                
                # Mark position as processed
                processed_positions.add(tesouro_to_keep.fixed_income_position.id)
                
                for tesouro_pos in tesouro_to_delete:
                    pos = tesouro_pos.fixed_income_position
                    if pos.id in processed_positions:
                        continue  # Skip if already processed
                    processed_positions.add(pos.id)
                    total_to_delete += 1
                    self.stdout.write(f'   [DELETE] ID {pos.id}')
                    self.stdout.write(f'     Created: {pos.created_at}')
                    self.stdout.write(f'     Asset Code: {pos.asset_code}')
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

