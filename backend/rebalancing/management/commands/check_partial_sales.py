"""
Management command to check partial sales calculation.
"""
from django.core.management.base import BaseCommand
from users.models import User
from rebalancing.models import RebalancingRecommendation, RebalancingAction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Check partial sales calculation for a user'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='User name (default: first user with recommendation)')

    def handle(self, *args, **options):
        user_name = options.get('user')
        
        if user_name:
            try:
                user = User.objects.get(name=user_name)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{user_name}' not found"))
                return
        else:
            # Get first user with a recommendation
            recommendation = RebalancingRecommendation.objects.first()
            if not recommendation:
                self.stdout.write(self.style.ERROR("No recommendations found"))
                return
            user = recommendation.user
            self.stdout.write(f"Using user: {user.name}")

        # Get the most recent recommendation
        recommendation = RebalancingRecommendation.objects.filter(user=user).order_by('-created_at').first()

        if not recommendation:
            self.stdout.write(self.style.ERROR(f"No recommendation found for {user.name}"))
            return

        self.stdout.write(f"\n=== Recommendation ID: {recommendation.id} ===")
        self.stdout.write(f"Created at: {recommendation.created_at}\n")

        # Get all rebalance actions with quantity_to_sell > 0
        rebalance_actions_with_sell = RebalancingAction.objects.filter(
            recommendation=recommendation,
            action_type='rebalance',
            quantity_to_sell__isnull=False
        ).exclude(quantity_to_sell=0).select_related('stock')

        self.stdout.write(f"=== Rebalance Actions with quantity_to_sell > 0 ({rebalance_actions_with_sell.count()} total) ===\n")

        total_calculated = Decimal('0')
        for action in rebalance_actions_with_sell:
            ticker = action.stock.ticker if action.stock else 'N/A'
            subtype_name = action.subtype_name or (action.investment_subtype.name if action.investment_subtype else 'N/A')
            quantity = action.quantity_to_sell
            current_price = action.stock.current_price if action.stock and action.stock.current_price else Decimal('0')
            sale_value = Decimal(str(quantity)) * current_price if current_price > 0 else Decimal('0')
            total_calculated += sale_value
            
            self.stdout.write(f"Ticker: {ticker}")
            self.stdout.write(f"  Subtype: {subtype_name}")
            self.stdout.write(f"  Ranking: {action.display_order}")
            self.stdout.write(f"  Quantity to sell: {quantity}")
            self.stdout.write(f"  Current price: R$ {current_price}")
            self.stdout.write(f"  Sale value: R$ {sale_value}")
            self.stdout.write(f"  Current value: R$ {action.current_value}")
            self.stdout.write(f"  Target value: R$ {action.target_value}")
            self.stdout.write(f"  Difference: R$ {action.difference}")
            self.stdout.write("")

        self.stdout.write(f"=== Total Calculated: R$ {total_calculated} ===\n")

        # Also show all rebalance actions for comparison
        all_rebalance_actions = RebalancingAction.objects.filter(
            recommendation=recommendation,
            action_type='rebalance',
            stock__isnull=False
        ).select_related('stock').order_by('display_order')

        self.stdout.write(f"=== All Rebalance Actions ({all_rebalance_actions.count()} total) ===\n")
        for action in all_rebalance_actions[:20]:  # Show first 20
            ticker = action.stock.ticker if action.stock else 'N/A'
            self.stdout.write(f"{ticker} (Rank {action.display_order}): qty_sell={action.quantity_to_sell}, qty_buy={action.quantity_to_buy}, diff=R$ {action.difference}")

