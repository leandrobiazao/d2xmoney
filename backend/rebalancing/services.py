"""
Service for rebalancing recommendations.
"""
from typing import List, Dict
from datetime import date
from decimal import Decimal
from django.db import transaction
from users.models import User
from allocation_strategies.models import UserAllocationStrategy
from allocation_strategies.services import AllocationStrategyService
from ambb_strategy.services import AMBBStrategyService
from portfolio_operations.models import PortfolioPosition
from configuration.models import InvestmentType
from .models import RebalancingRecommendation, RebalancingAction
from stocks.models import Stock
from django.db.models import Sum, Q


class RebalancingService:
    """Service for generating rebalancing recommendations."""
    
    @staticmethod
    @transaction.atomic
    def generate_monthly_recommendations(user: User) -> RebalancingRecommendation:
        """
        Generate monthly rebalancing recommendations combining:
        - Investment type allocation rebalancing
        - AMBB strategy recommendations
        - Fixed income rebalancing
        """
        try:
            strategy = UserAllocationStrategy.objects.get(user=user)
        except UserAllocationStrategy.DoesNotExist:
            raise ValueError("User does not have an allocation strategy")
        
        # Create recommendation
        recommendation = RebalancingRecommendation.objects.create(
            user=user,
            strategy=strategy,
            recommendation_date=date.today(),
            status='pending'
        )
        
        # Get current vs target allocation
        current_allocation = AllocationStrategyService.get_current_allocation(user)
        
        # Calculate total sales already executed this month from brokerage notes (Operations)
        # This is important to respect the 19K monthly limit
        # IMPORTANT: Use Operation model (brokerage notes) instead of RebalancingRecommendation
        # to match what is shown in the UI
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        # Get "Ações em Reais" investment type
        acoes_reais_type = None
        try:
            acoes_reais_type = InvestmentType.objects.get(code='ACOES_REAIS', is_active=True)
        except InvestmentType.DoesNotExist:
            try:
                acoes_reais_type = InvestmentType.objects.filter(
                    Q(code__icontains='ACOES') | Q(name__icontains='Ações em Reais'),
                    is_active=True
                ).first()
            except:
                pass
        
        # Build query for operations in current month
        # Data is stored as DD/MM/YYYY string, so we need to filter by month/year
        month_str = f"/{current_month:02d}/{current_year}"
        
        # Get all sell operations (tipo_operacao = 'V') for this user in current month
        from brokerage_notes.models import Operation
        operations = Operation.objects.filter(
            note__user_id=str(user.id),
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
        previous_sales_this_month = operations.aggregate(
            total=Sum('valor_operacao')
        )['total'] or Decimal('0')
        
        # Calculate remaining sales limit for this month
        remaining_monthly_limit = Decimal('19000.00') - previous_sales_this_month
        
        # Generate actions for investment type rebalancing
        type_allocations = strategy.type_allocations.all()
        for type_alloc in type_allocations:
            target_percentage = type_alloc.target_percentage
            investment_type_name = type_alloc.investment_type.name
            
            # Find current percentage
            current_percentage = Decimal('0')
            for type_data in current_allocation['investment_types']:
                if type_data['investment_type_id'] == type_alloc.investment_type.id:
                    current_percentage = type_data['current_percentage']
                    break
            
            # Calculate difference
            total_value = current_allocation['total_value']
            target_value = total_value * target_percentage / 100
            current_value = total_value * current_percentage / 100
            difference = target_value - current_value
            
            if abs(difference) > Decimal('1.00'):  # Significant difference
                RebalancingAction.objects.create(
                    recommendation=recommendation,
                    action_type='rebalance',
                    current_value=current_value,
                    target_value=target_value,
                    difference=difference,
                    display_order=type_alloc.display_order
                )
        
        # Generate AMBB strategy recommendations for "Ações em Reais"
        # Pass the remaining monthly limit to consider previous sales this month
        ambb_recommendations = AMBBStrategyService.generate_rebalancing_recommendations(
            user, 
            remaining_monthly_limit=remaining_monthly_limit
        )
        
        # Update recommendation with sales limit info
        # Use total_all_sales_value which includes both complete and partial sales
        total_all_sales = ambb_recommendations.get('total_all_sales_value', ambb_recommendations.get('total_sales_value', 0))
        recommendation.total_sales_value = Decimal(str(total_all_sales))
        recommendation.save()
        
        action_order = type_allocations.count() + 1
        
        # Add sell actions (respecting 19K limit)
        for stock_data in ambb_recommendations.get('stocks_to_sell', []):
            try:
                stock = Stock.objects.get(ticker=stock_data['ticker'], is_active=True)
                # Use ranking as display_order if available, otherwise use action_order
                ranking = stock_data.get('ranking', None)
                display_order_value = ranking if ranking is not None else action_order
                
                RebalancingAction.objects.create(
                    recommendation=recommendation,
                    action_type='sell',
                    stock=stock,
                    current_value=Decimal(str(stock_data['current_value'])),
                    target_value=Decimal('0'),
                    difference=-Decimal(str(stock_data['current_value'])),
                    quantity_to_sell=stock_data.get('quantity', 0),
                    display_order=display_order_value,
                    reason=stock_data.get('reason', 'Not in AMBB 2.0 or Rank > 30')
                )
                action_order += 1
            except Stock.DoesNotExist:
                pass
        
        # Track which stocks are already in balance actions to avoid duplicates
        stocks_in_balance = set()
        balance_actions_data = []
        
        # First, collect all balance actions (includes both stocks to keep and new buys)
        for stock_data in ambb_recommendations.get('stocks_to_balance', []):
            ticker = stock_data.get('ticker')
            if ticker:
                stocks_in_balance.add(ticker)
                balance_actions_data.append(stock_data)
        
        # Add buy actions only for stocks NOT in balance list (shouldn't happen, but safety check)
        for stock_data in ambb_recommendations.get('stocks_to_buy', []):
            ticker = stock_data.get('ticker')
            if ticker and ticker not in stocks_in_balance:
                try:
                    stock = Stock.objects.get(ticker=ticker, is_active=True)
                    RebalancingAction.objects.create(
                        recommendation=recommendation,
                        action_type='buy',
                        stock=stock,
                        current_value=Decimal('0'),
                        target_value=Decimal(str(stock_data['target_value'])),
                        difference=Decimal(str(stock_data['target_value'])),
                        quantity_to_buy=stock_data.get('target_quantity', 0),
                        display_order=stock_data.get('ranking', 999)  # Use ranking from AMBB 2.0
                    )
                    action_order += 1
                except Stock.DoesNotExist:
                    pass
        
        # Add balance actions (this includes both stocks to keep and new buys)
        # Use a set to track processed tickers to avoid duplicates
        processed_tickers = set()
        for stock_data in balance_actions_data:
            ticker = stock_data.get('ticker')
            if not ticker or ticker in processed_tickers:
                continue  # Skip duplicates
            processed_tickers.add(ticker)
            
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                quantity_to_adjust = stock_data.get('quantity_to_adjust', 0)
                # Get ranking from stock_data (AMBB 2.0 ranking) - this is the source of truth
                ranking = stock_data.get('ranking', 999)
                
                # Determine action type: 'buy' if current_value is 0, otherwise 'rebalance'
                current_value = Decimal(str(stock_data.get('current_value', 0)))
                # Use <= 0.01 to handle floating point precision issues
                action_type = 'buy' if current_value <= Decimal('0.01') else 'rebalance'
                
                # NEVER create 'buy' actions for stocks with ranking > 30
                # This is a hard limit - we should never buy stocks above rank 30
                # If ranking > 30 and it's trying to be a 'buy' action, skip it entirely
                # If ranking > 30 and it's a 'rebalance' action, allow it (stock already in portfolio)
                if ranking > 30 and action_type == 'buy':
                    # This is trying to be a buy action for a stock with ranking > 30 - skip it
                    continue
                
                # Also, if ranking > 30 and we need to buy more (quantity_to_adjust > 0),
                # we should NOT recommend buying more - only allow rebalancing (selling)
                if ranking > 30 and quantity_to_adjust > 0:
                    # Don't recommend buying more of a stock with ranking > 30
                    # Set quantity_to_adjust to 0 (no buy recommendation)
                    quantity_to_adjust = 0
                    # If there's no current value and we can't buy, skip this action entirely
                    if current_value <= Decimal('0.01'):
                        continue
                    # Otherwise, it becomes a rebalance action with no buy
                    action_type = 'rebalance'
                
                RebalancingAction.objects.create(
                    recommendation=recommendation,
                    action_type=action_type,
                    stock=stock,
                    current_value=current_value,
                    target_value=Decimal(str(stock_data.get('target_value', 0))),
                    difference=Decimal(str(stock_data.get('difference', 0))),
                    quantity_to_buy=quantity_to_adjust if quantity_to_adjust > 0 else None,
                    quantity_to_sell=-quantity_to_adjust if quantity_to_adjust < 0 else None,
                    display_order=ranking  # Use ranking as display_order for sorting
                )
                action_order += 1
            except Stock.DoesNotExist:
                pass
        
        # Generate recommendations for BERK34 (Ações em Dólares)
        try:
            acoes_dolares_type = InvestmentType.objects.get(
                code__in=['ACOES_DOLARES', 'AÇÕES_EM_DÓLARES'],
                is_active=True
            )
        except InvestmentType.DoesNotExist:
            # Try alternative names
            try:
                acoes_dolares_type = InvestmentType.objects.get(
                    name__icontains='Ações em Dólares',
                    is_active=True
                )
            except InvestmentType.DoesNotExist:
                acoes_dolares_type = None
        
        if acoes_dolares_type:
            # Find the type allocation for Ações em Dólares
            acoes_dolares_alloc = None
            for type_alloc in type_allocations:
                if type_alloc.investment_type.id == acoes_dolares_type.id:
                    acoes_dolares_alloc = type_alloc
                    break
            
            if acoes_dolares_alloc:
                # Get target value for Ações em Dólares
                target_percentage = acoes_dolares_alloc.target_percentage
                total_value = current_allocation['total_value']
                target_value = total_value * target_percentage / 100
                
                # Get current BERK34 position
                try:
                    berk34_stock = Stock.objects.get(ticker='BERK34', is_active=True)
                    berk34_position = PortfolioPosition.objects.filter(
                        user_id=str(user.id),
                        ticker='BERK34'
                    ).first()
                    
                    current_value = Decimal('0')
                    current_quantity = 0
                    
                    if berk34_position:
                        # Use valor_total_investido as current value (or could use current_price * quantity)
                        current_value = Decimal(str(berk34_position.valor_total_investido))
                        current_quantity = berk34_position.quantidade
                    
                    difference = target_value - current_value
                    
                    # Only create action if difference is significant
                    if abs(difference) > Decimal('1.00'):
                        # Get current price for BERK34
                        current_price = berk34_stock.current_price or Decimal('0')
                        
                        if current_price == 0:
                            # Price not available - create action without quantity
                            action_type = 'buy' if current_value == 0 else 'rebalance'
                            RebalancingAction.objects.create(
                                recommendation=recommendation,
                                action_type=action_type,
                                stock=berk34_stock,
                                current_value=current_value,
                                target_value=target_value,
                                difference=difference,
                                display_order=action_order
                            )
                        else:
                            # Calculate quantity to buy/sell based on current price
                            if difference > 0:
                                # Need to buy more
                                quantity_to_buy = int(difference / current_price)
                                action_type = 'buy' if current_value == 0 else 'rebalance'
                                RebalancingAction.objects.create(
                                    recommendation=recommendation,
                                    action_type=action_type,
                                    stock=berk34_stock,
                                    current_value=current_value,
                                    target_value=target_value,
                                    difference=difference,
                                    quantity_to_buy=quantity_to_buy,
                                    display_order=action_order
                                )
                            else:
                                # Need to sell some
                                quantity_to_sell = int(abs(difference) / current_price)
                                RebalancingAction.objects.create(
                                    recommendation=recommendation,
                                    action_type='rebalance',
                                    stock=berk34_stock,
                                    current_value=current_value,
                                    target_value=target_value,
                                    difference=difference,
                                    quantity_to_sell=quantity_to_sell,
                                    display_order=action_order
                                )
                        action_order += 1
                except Stock.DoesNotExist:
                    pass
        
        return recommendation


