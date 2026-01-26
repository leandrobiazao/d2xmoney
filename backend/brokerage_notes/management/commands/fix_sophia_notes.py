"""
Management command to fix Sophia's notes that have wrong user_id.
"""
from django.core.management.base import BaseCommand
from brokerage_notes.models import BrokerageNote


class Command(BaseCommand):
    help = 'Fix Sophia notes that have wrong user_id assigned'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # User IDs from database
        sophia_id = '8535f27e-7323-4c9a-b543-5ada9ec8e1c2'
        aurelio_id = 'a1a974df-a8e1-4206-86ef-efb8302d96db'
        
        # Find all notes with Sophia in filename but wrong user_id
        wrong_notes = BrokerageNote.objects.filter(
            file_name__icontains='Sophia'
        ).filter(
            user_id=aurelio_id
        )
        
        count = wrong_notes.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No notes found that need fixing!'))
            return
        
        self.stdout.write(f'Found {count} note(s) with Sophia in filename but wrong user_id:')
        self.stdout.write('')
        
        for note in wrong_notes:
            self.stdout.write(f'  - {note.file_name}')
            self.stdout.write(f'    Current user_id: {note.user_id} (Aurelio)')
            self.stdout.write(f'    Should be: {sophia_id} (Sophia)')
            self.stdout.write(f'    Note ID: {note.id}')
            self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN: No changes made. Run without --dry-run to apply changes.'))
        else:
            # Update all wrong notes
            updated = wrong_notes.update(user_id=sophia_id)
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {updated} note(s)!'))
            self.stdout.write('All Sophia notes now have the correct user_id.')








