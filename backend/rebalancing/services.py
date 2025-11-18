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
from .models import RebalancingRecommendation, RebalancingAction
from stocks.models import Stock


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
        
        # Generate AMBB strategy recommendations
        ambb_recommendations = AMBBStrategyService.generate_rebalancing_recommendations(user)
        
        action_order = type_allocations.count() + 1
        
        # Add sell actions
        for stock_data in ambb_recommendations['stocks_to_sell']:
            try:
                stock = Stock.objects.get(ticker=stock_data['ticker'], is_active=True)
                RebalancingAction.objects.create(
                    recommendation=recommendation,
                    action_type='sell',
                    stock=stock,
                    current_value=Decimal(str(stock_data['current_value'])),
                    target_value=Decimal('0'),
                    difference=-Decimal(str(stock_data['current_value'])),
                    quantity_to_sell=stock_data['quantity'],
                    display_order=action_order
                )
                action_order += 1
            except Stock.DoesNotExist:
                pass
        
        # Add buy actions
        for stock_data in ambb_recommendations['stocks_to_buy']:
            try:
                stock = Stock.objects.get(ticker=stock_data['ticker'], is_active=True)
                RebalancingAction.objects.create(
                    recommendation=recommendation,
                    action_type='buy',
                    stock=stock,
                    current_value=Decimal('0'),
                    target_value=Decimal(str(stock_data['target_value'])),
                    difference=Decimal(str(stock_data['target_value'])),
                    quantity_to_buy=stock_data['target_quantity'],
                    display_order=action_order
                )
                action_order += 1
            except Stock.DoesNotExist:
                pass
        
        # Add balance actions
        for stock_data in ambb_recommendations['stocks_to_balance']:
            if 'difference' in stock_data:
                try:
                    stock = Stock.objects.get(ticker=stock_data['ticker'], is_active=True)
                    RebalancingAction.objects.create(
                        recommendation=recommendation,
                        action_type='rebalance',
                        stock=stock,
                        current_value=Decimal(str(stock_data['current_value'])),
                        target_value=Decimal(str(stock_data['target_value'])),
                        difference=Decimal(str(stock_data['difference'])),
                        quantity_to_buy=stock_data.get('quantity_to_adjust', 0) if stock_data.get('quantity_to_adjust', 0) > 0 else None,
                        quantity_to_sell=-stock_data.get('quantity_to_adjust', 0) if stock_data.get('quantity_to_adjust', 0) < 0 else None,
                        display_order=action_order
                    )
                    action_order += 1
                except Stock.DoesNotExist:
                    pass
        
        return recommendation


