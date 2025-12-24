"""
Management command to remove all investment funds.
"""
from django.core.management.base import BaseCommand
from fixed_income.models import InvestmentFund


class Command(BaseCommand):
    help = 'Remove all investment funds from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            help='Remove funds only for a specific user_id',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        
        if user_id:
            funds = InvestmentFund.objects.filter(user_id=user_id)
            count = funds.count()
            funds.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully removed {count} fund(s) for user {user_id}'))
        else:
            count = InvestmentFund.objects.count()
            InvestmentFund.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully removed all {count} fund(s) from the database'))

