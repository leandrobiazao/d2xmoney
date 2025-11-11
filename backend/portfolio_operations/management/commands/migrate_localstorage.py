"""
Django management command to migrate operations from localStorage to backend JSON file.

This command reads operations from the backend/data/brokerage_notes.json file
(which contains operations extracted from brokerage notes) and migrates them
to the portfolio_operations.json file.

Usage:
    python manage.py migrate_localstorage [--client-id CLIENT_ID]
"""
import json
from django.core.management.base import BaseCommand
from portfolio_operations.services import PortfolioOperationsService
from brokerage_notes.services import BrokerageNoteHistoryService


class Command(BaseCommand):
    help = 'Migrate operations from brokerage notes to portfolio operations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=str,
            help='Migrate operations for a specific client ID only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )

    def handle(self, *args, **options):
        client_id = options.get('client_id')
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('🔄 Starting migration from brokerage notes to portfolio operations...')
        
        # Load all brokerage notes
        notes = BrokerageNoteHistoryService.load_history()
        
        if not notes:
            self.stdout.write(self.style.WARNING('No brokerage notes found.'))
            return
        
        # Extract all operations from notes
        all_operations = []
        for note in notes:
            note_client_id = note.get('user_id')
            
            # Filter by client_id if specified
            if client_id and note_client_id != client_id:
                continue
            
            operations = note.get('operations', [])
            for op in operations:
                # Ensure clientId is set
                op['clientId'] = note_client_id
                all_operations.append(op)
        
        if not all_operations:
            self.stdout.write(self.style.WARNING('No operations found to migrate.'))
            return
        
        self.stdout.write(f'📊 Found {len(all_operations)} operations to migrate')
        
        if client_id:
            self.stdout.write(f'   Filtered by client_id: {client_id}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
            
            # Show statistics
            by_client = {}
            by_ticker = {}
            for op in all_operations:
                cid = op.get('clientId', 'unknown')
                ticker = op.get('titulo', 'unknown')
                
                by_client[cid] = by_client.get(cid, 0) + 1
                by_ticker[ticker] = by_ticker.get(ticker, 0) + 1
            
            self.stdout.write('Operations by client:')
            for cid, count in sorted(by_client.items()):
                self.stdout.write(f'  {cid}: {count} operations')
            
            self.stdout.write('\nOperations by ticker (top 10):')
            for ticker, count in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)[:10]:
                self.stdout.write(f'  {ticker}: {count} operations')
            
            return
        
        # Migrate operations
        self.stdout.write('\n💾 Migrating operations...')
        added_operations = PortfolioOperationsService.add_operations(all_operations)
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Migration complete!'
        ))
        self.stdout.write(f'   Added: {len(added_operations)} operations')
        self.stdout.write(f'   Skipped (duplicates): {len(all_operations) - len(added_operations)} operations')
        
        # Show current totals
        if client_id:
            current_ops = PortfolioOperationsService.get_operations_by_client(client_id)
            self.stdout.write(f'\n📊 Current operations for client {client_id}: {len(current_ops)}')
        else:
            all_current = PortfolioOperationsService.load_operations()
            self.stdout.write(f'\n📊 Total operations in system: {len(all_current)}')

