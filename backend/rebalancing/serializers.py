"""
Serializers for rebalancing app.
"""
from rest_framework import serializers
from .models import RebalancingRecommendation, RebalancingAction
from stocks.serializers import StockSerializer


class RebalancingActionSerializer(serializers.ModelSerializer):
    """Serializer for RebalancingAction."""
    stock = StockSerializer(read_only=True)
    
    class Meta:
        model = RebalancingAction
        fields = [
            'id', 'action_type', 'stock', 'current_value', 'target_value',
            'difference', 'quantity_to_buy', 'quantity_to_sell', 'display_order', 'reason'
        ]
        read_only_fields = ['id']


class RebalancingRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for RebalancingRecommendation."""
    actions = RebalancingActionSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    sales_limit_remaining = serializers.SerializerMethodField()
    sales_limit_reached = serializers.SerializerMethodField()
    previous_sales_this_month = serializers.SerializerMethodField()
    total_complete_sales_value = serializers.SerializerMethodField()
    total_partial_sales_value = serializers.SerializerMethodField()
    partial_sales_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RebalancingRecommendation
        fields = [
            'id', 'user', 'user_name', 'strategy', 'recommendation_date',
            'status', 'total_sales_value', 'sales_limit_remaining', 'sales_limit_reached',
            'previous_sales_this_month', 'total_complete_sales_value', 
            'total_partial_sales_value', 'partial_sales_count',
            'created_at', 'updated_at', 'actions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_sales_value']
    
    def get_sales_limit_remaining(self, obj):
        """Calculate remaining sales limit (19,000 - previous_sales_this_month - total_sales_value)."""
        from decimal import Decimal
        
        limit = Decimal('19000.00')
        
        # Get previous sales this month from brokerage notes (Operations)
        # Use the same method as get_previous_sales_this_month to ensure consistency
        previous_sales = Decimal(str(self.get_previous_sales_this_month(obj)))
        
        # Remaining = limit - previous sales (from brokerage notes) - current recommendation sales
        remaining = limit - previous_sales - obj.total_sales_value
        return float(max(remaining, Decimal('0')))
    
    def get_sales_limit_reached(self, obj):
        """Check if sales limit (19,000) has been reached."""
        from decimal import Decimal
        limit = Decimal('19000.00')
        return obj.total_sales_value >= limit
    
    def get_previous_sales_this_month(self, obj):
        """Calculate total sales already executed this month from brokerage notes (Operations)."""
        from decimal import Decimal
        from datetime import date
        from django.db.models import Sum, Q
        from brokerage_notes.models import Operation
        from stocks.models import Stock
        from configuration.models import InvestmentType
        
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        # Get "Ações em Reais" investment type
        acoes_reais_type = None
        try:
            acoes_reais_type = InvestmentType.objects.get(code='ACOES_REAIS', is_active=True)
        except InvestmentType.DoesNotExist:
            # Try alternative codes/names
            try:
                acoes_reais_type = InvestmentType.objects.filter(
                    Q(code__icontains='ACOES') | Q(name__icontains='Ações em Reais'),
                    is_active=True
                ).first()
            except:
                pass
        
        # Build query for operations in current month
        # Data is stored as DD/MM/YYYY string, so we need to filter by month/year
        # We'll filter operations where data ends with /MM/YYYY format
        month_str = f"/{current_month:02d}/{current_year}"
        
        # Get all sell operations (tipo_operacao = 'V') for this user in current month
        operations = Operation.objects.filter(
            note__user_id=str(obj.user.id),
            tipo_operacao='V',  # V = Venda (Sell)
            data__endswith=month_str
        )
        
        # If we have the investment type, filter by stocks of type "Ações em Reais"
        if acoes_reais_type:
            # Get all tickers that belong to "Ações em Reais"
            acoes_reais_tickers = Stock.objects.filter(
                investment_type=acoes_reais_type,
                is_active=True
            ).values_list('ticker', flat=True)
            
            # Filter operations to only include "Ações em Reais" stocks
            operations = operations.filter(titulo__in=acoes_reais_tickers)
        
        # Sum the valor_operacao (operation value) for all sell operations
        total_sales = operations.aggregate(
            total=Sum('valor_operacao')
        )['total'] or Decimal('0')
        
        return float(total_sales)
    
    def get_total_complete_sales_value(self, obj):
        """Calculate total value of complete sales (sell actions only)."""
        from decimal import Decimal
        total = Decimal('0')
        # Only count actions with action_type='sell' (complete sales)
        # These are actions where the entire position is being sold
        for action in obj.actions.filter(action_type='sell'):
            total += action.current_value
        return float(total)
    
    def get_total_partial_sales_value(self, obj):
        """Calculate total value of partial sales (rebalance actions with quantity_to_sell)."""
        from decimal import Decimal
        total = Decimal('0')
        for action in obj.actions.filter(action_type='rebalance'):
            if action.quantity_to_sell and action.quantity_to_sell > 0:
                # Calculate value: quantity_to_sell * current_price
                # We need to get the current price from the stock
                if action.stock and action.stock.current_price:
                    price = Decimal(str(action.stock.current_price))
                    quantity = Decimal(str(abs(action.quantity_to_sell)))  # Use abs to ensure positive
                    total += price * quantity
                elif action.current_value > 0:
                    # Fallback: estimate from current_value
                    # If we have current_value, we can estimate the price per share
                    # This is a rough estimate but better than nothing
                    if action.stock and hasattr(action.stock, 'current_price') and action.stock.current_price:
                        price = Decimal(str(action.stock.current_price))
                        quantity = Decimal(str(abs(action.quantity_to_sell)))
                        total += price * quantity
        return float(total)
    
    def get_partial_sales_count(self, obj):
        """Count number of stocks with partial sales."""
        return obj.actions.filter(
            action_type='rebalance',
            quantity_to_sell__isnull=False
        ).exclude(quantity_to_sell=0).count()


