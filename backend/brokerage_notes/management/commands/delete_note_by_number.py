"""
Management command to delete a brokerage note by note_number and note_date.
"""
from django.core.management.base import BaseCommand
from brokerage_notes.models import BrokerageNote
from brokerage_notes.services import BrokerageNoteHistoryService
from portfolio_operations.services import PortfolioService


class Command(BaseCommand):
    help = 'Delete a brokerage note by note_number and note_date (and optionally user_id)'

    def add_arguments(self, parser):
        parser.add_argument(
            'note_number',
            type=str,
            help='Note number to delete (e.g., 57836478)'
        )
        parser.add_argument(
            'note_date',
            type=str,
            help='Note date in DD/MM/YYYY format (e.g., 07/11/2022)'
        )
        parser.add_argument(
            '--user-id',
            type=str,
            default=None,
            help='Optional: User ID to filter by (if not provided, deletes for all users)'
        )
        parser.add_argument(
            '--refresh-portfolio',
            action='store_true',
            help='Refresh portfolio after deletion'
        )

    def handle(self, *args, **options):
        note_number = options['note_number']
        note_date = options['note_date']
        user_id = options.get('user_id')
        refresh_portfolio = options.get('refresh_portfolio', False)

        self.stdout.write(f'Searching for note: number={note_number}, date={note_date}' + 
                         (f', user_id={user_id}' if user_id else ' (all users)'))

        # Find notes matching criteria
        query = BrokerageNote.objects.filter(
            note_number=note_number,
            note_date=note_date
        )
        
        if user_id:
            query = query.filter(user_id=user_id)

        notes = list(query)
        
        if not notes:
            self.stdout.write(self.style.WARNING(f'No notes found matching number={note_number}, date={note_date}'))
            if user_id:
                self.stdout.write(self.style.WARNING(f'Try without --user-id to search all users'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {len(notes)} note(s) to delete:'))

        deleted_count = 0
        for note in notes:
            self.stdout.write(f'  - Note ID: {note.id}')
            self.stdout.write(f'    User ID: {note.user_id}')
            self.stdout.write(f'    File: {note.file_name}')
            self.stdout.write(f'    Operations: {note.operations_count}')
            
            try:
                # Delete using the service method
                BrokerageNoteHistoryService.delete_note(str(note.id))
                deleted_count += 1
                self.stdout.write(self.style.SUCCESS(f'    ✓ Deleted successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Error deleting: {e}'))

        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully deleted {deleted_count} note(s)'))
            
            if refresh_portfolio:
                self.stdout.write('Refreshing portfolio...')
                try:
                    PortfolioService.refresh_portfolio_from_brokerage_notes()
                    self.stdout.write(self.style.SUCCESS('Portfolio refreshed successfully'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Warning: Failed to refresh portfolio: {e}'))
        else:
            self.stdout.write(self.style.ERROR('No notes were deleted'))






