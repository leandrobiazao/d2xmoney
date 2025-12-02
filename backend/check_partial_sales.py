"""
Script to check partial sales calculation for a user's recommendation.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio_api.settings')
django.setup()

from users.models import User
from rebalancing.models import RebalancingRecommendation, RebalancingAction
from decimal import Decimal

# List all users first
print("Available users:")
for u in User.objects.all():
    print(f"  - {u.name} (ID: {u.id})")

# Get Aurelio user (try different variations)
user = None
for name_variant in ['Aurelio', 'aurelio', 'Aurélio', 'AURELIO']:
    try:
        user = User.objects.get(name=name_variant)
        break
    except User.DoesNotExist:
        continue

if not user:
    # Get first user with a recommendation
    recommendation = RebalancingRecommendation.objects.first()
    if recommendation:
        user = recommendation.user
        print(f"\nUsing user: {user.name} (has recommendation)")
    else:
        print("\nNo users with recommendations found")
        sys.exit(1)

# Get the most recent recommendation
recommendation = RebalancingRecommendation.objects.filter(user=user).order_by('-created_at').first()

if not recommendation:
    print("No recommendation found for Aurelio")
    sys.exit(1)

print(f"\n=== Recommendation ID: {recommendation.id} ===")
print(f"Created at: {recommendation.created_at}")
print(f"Total partial sales value (from serializer): R$ {recommendation.total_partial_sales_value if hasattr(recommendation, 'total_partial_sales_value') else 'N/A'}\n")

# Get all rebalance actions with quantity_to_sell > 0
rebalance_actions_with_sell = RebalancingAction.objects.filter(
    recommendation=recommendation,
    action_type='rebalance',
    quantity_to_sell__isnull=False
).exclude(quantity_to_sell=0)

print(f"=== Rebalance Actions with quantity_to_sell > 0 ({rebalance_actions_with_sell.count()} total) ===\n")

total_calculated = Decimal('0')
for action in rebalance_actions_with_sell:
    ticker = action.stock.ticker if action.stock else 'N/A'
    quantity = action.quantity_to_sell
    current_price = action.stock.current_price if action.stock and action.stock.current_price else Decimal('0')
    sale_value = Decimal(str(quantity)) * current_price if current_price > 0 else Decimal('0')
    total_calculated += sale_value
    
    print(f"Ticker: {ticker}")
    print(f"  Ranking: {action.display_order}")
    print(f"  Quantity to sell: {quantity}")
    print(f"  Current price: R$ {current_price}")
    print(f"  Sale value: R$ {sale_value}")
    print(f"  Current value: R$ {action.current_value}")
    print(f"  Target value: R$ {action.target_value}")
    print(f"  Difference: R$ {action.difference}")
    print()

print(f"=== Total Calculated: R$ {total_calculated} ===\n")

# Also check all rebalance actions for "Ações em Reais"
from configuration.models import InvestmentType
acoes_reais_type = InvestmentType.objects.filter(code='RENDA_VARIAVEL_REAIS').first()

if acoes_reais_type:
    all_rebalance_actions = RebalancingAction.objects.filter(
        recommendation=recommendation,
        action_type='rebalance',
        stock__isnull=False
    ).select_related('stock')
    
    print(f"=== All Rebalance Actions for Ações em Reais ({all_rebalance_actions.count()} total) ===\n")
    for action in all_rebalance_actions.order_by('display_order'):
        ticker = action.stock.ticker if action.stock else 'N/A'
        print(f"Ticker: {ticker}, Ranking: {action.display_order}")
        print(f"  quantity_to_sell: {action.quantity_to_sell}")
        print(f"  quantity_to_buy: {action.quantity_to_buy}")
        print(f"  Current value: R$ {action.current_value}")
        print(f"  Difference: R$ {action.difference}")
        print()

