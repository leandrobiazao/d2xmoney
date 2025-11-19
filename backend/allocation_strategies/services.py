"""
Service for managing allocation strategies.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from users.models import User
from portfolio_operations.models import PortfolioPosition
from .models import (
    UserAllocationStrategy,
    InvestmentTypeAllocation,
    SubTypeAllocation,
    StockAllocation
)
from configuration.models import InvestmentType, InvestmentSubType
from stocks.models import Stock


class AllocationStrategyService:
    """Service for managing allocation strategies."""
    
    @staticmethod
    def validate_percentage_sum(percentages: List[Decimal], expected_sum: Decimal = Decimal('100')) -> bool:
        """Validate that percentages sum to expected_sum."""
        total = sum(percentages)
        return abs(total - expected_sum) < Decimal('0.01')  # Allow small rounding differences
    
    @staticmethod
    @transaction.atomic
    def create_or_update_strategy(
        user: User,
        type_allocations: List[Dict],
        total_portfolio_value: Optional[Decimal] = None
    ) -> UserAllocationStrategy:
        """
        Create or update user allocation strategy.
        
        Args:
            user: User instance
            type_allocations: List of dicts with structure:
                {
                    'investment_type_id': int,
                    'target_percentage': Decimal,
                    'display_order': int,
                    'sub_type_allocations': [
                        {
                            'sub_type_id': int (optional),
                            'custom_name': str (optional),
                            'target_percentage': Decimal,
                            'display_order': int,
                            'stock_allocations': [
                                {
                                    'stock_id': int,
                                    'target_percentage': Decimal,
                                    'display_order': int
                                }
                            ]
                        }
                    ]
                }
            total_portfolio_value: Optional total portfolio value
        """
        # Validate investment type allocations sum to 100%
        type_percentages = [Decimal(str(ta['target_percentage'])) for ta in type_allocations]
        if not AllocationStrategyService.validate_percentage_sum(type_percentages):
            raise ValidationError("Investment type allocations must sum to 100%")
        
        # Get or create strategy
        strategy, created = UserAllocationStrategy.objects.get_or_create(
            user=user,
            defaults={'total_portfolio_value': total_portfolio_value}
        )
        if not created and total_portfolio_value is not None:
            strategy.total_portfolio_value = total_portfolio_value
            strategy.save()
        
        # Clear existing allocations
        InvestmentTypeAllocation.objects.filter(strategy=strategy).delete()
        
        # Create new allocations
        for type_alloc_data in type_allocations:
            investment_type = InvestmentType.objects.get(
                id=type_alloc_data['investment_type_id']
            )
            
            type_allocation = InvestmentTypeAllocation.objects.create(
                strategy=strategy,
                investment_type=investment_type,
                target_percentage=Decimal(str(type_alloc_data['target_percentage'])),
                display_order=type_alloc_data.get('display_order', 0)
            )
            
            # Validate and create sub-type allocations
            sub_type_allocations = type_alloc_data.get('sub_type_allocations', [])
            if sub_type_allocations:
                sub_percentages = [
                    Decimal(str(sta['target_percentage']))
                    for sta in sub_type_allocations
                ]
                if not AllocationStrategyService.validate_percentage_sum(sub_percentages):
                    raise ValidationError(
                        f"Sub-type allocations for {investment_type.name} must sum to 100%"
                    )
                
                for sub_alloc_data in sub_type_allocations:
                    sub_type_allocation = SubTypeAllocation.objects.create(
                        type_allocation=type_allocation,
                        sub_type_id=sub_alloc_data.get('sub_type_id'),
                        custom_name=sub_alloc_data.get('custom_name'),
                        target_percentage=Decimal(str(sub_alloc_data['target_percentage'])),
                        display_order=sub_alloc_data.get('display_order', 0)
                    )
                    
                    # Create stock allocations if provided
                    stock_allocations = sub_alloc_data.get('stock_allocations', [])
                    if stock_allocations:
                        stock_percentages = [
                            Decimal(str(sa['target_percentage']))
                            for sa in stock_allocations
                        ]
                        if not AllocationStrategyService.validate_percentage_sum(stock_percentages):
                            raise ValidationError(
                                f"Stock allocations must sum to 100%"
                            )
                        
                        for stock_alloc_data in stock_allocations:
                            StockAllocation.objects.create(
                                sub_type_allocation=sub_type_allocation,
                                stock_id=stock_alloc_data['stock_id'],
                                target_percentage=Decimal(str(stock_alloc_data['target_percentage'])),
                                display_order=stock_alloc_data.get('display_order', 0)
                            )
        
        return strategy
    
    @staticmethod
    def get_current_allocation(user: User) -> Dict:
        """
        Calculate current allocation based on portfolio positions.
        
        Returns dict with structure:
        {
            'investment_types': [
                {
                    'investment_type_id': int,
                    'investment_type_name': str,
                    'current_value': Decimal,
                    'current_percentage': Decimal,
                    'sub_types': [...]
                }
            ],
            'total_value': Decimal,
            'unallocated_cash': Decimal
        }
        """
        # Get user's portfolio positions
        positions = PortfolioPosition.objects.filter(user_id=str(user.id))
        
        # Get user's allocation strategy
        try:
            strategy = UserAllocationStrategy.objects.get(user=user)
        except UserAllocationStrategy.DoesNotExist:
            return {
                'investment_types': [],
                'total_value': Decimal('0'),
                'unallocated_cash': Decimal('0')
            }
        
        # Calculate total portfolio value
        total_value = sum(
            Decimal(str(pos.valor_total_investido))
            for pos in positions
        )
        
        # Group positions by investment type (via stock)
        type_values = {}
        for position in positions:
            try:
                stock = Stock.objects.get(ticker=position.ticker, is_active=True)
                investment_type = stock.investment_type
                if investment_type:
                    type_id = investment_type.id
                    if type_id not in type_values:
                        type_values[type_id] = {
                            'investment_type_id': type_id,
                            'investment_type_name': investment_type.name,
                            'current_value': Decimal('0'),
                            'sub_types': {}
                        }
                    type_values[type_id]['current_value'] += Decimal(str(position.valor_total_investido))
            except Stock.DoesNotExist:
                # Stock not in catalog - treat as unallocated
                pass
        
        # Calculate percentages
        investment_types = []
        for type_id, type_data in type_values.items():
            percentage = (
                (type_data['current_value'] / total_value * 100)
                if total_value > 0 else Decimal('0')
            )
            type_data['current_percentage'] = percentage
            investment_types.append(type_data)
        
        # Unallocated cash goes to Renda Fixa
        unallocated_cash = Decimal('0')  # Could be calculated from cash positions
        
        return {
            'investment_types': investment_types,
            'total_value': total_value,
            'unallocated_cash': unallocated_cash
        }
    
    @staticmethod
    def get_pie_chart_data(user: User) -> Dict:
        """
        Get data formatted for pie chart visualization.
        
        Returns:
        {
            'target': {
                'labels': [str],
                'data': [Decimal],
                'colors': [str]
            },
            'current': {
                'labels': [str],
                'data': [Decimal],
                'colors': [str]
            }
        }
        """
        try:
            strategy = UserAllocationStrategy.objects.get(user=user)
        except UserAllocationStrategy.DoesNotExist:
            return {
                'target': {'labels': [], 'data': [], 'colors': []},
                'current': {'labels': [], 'data': [], 'colors': []}
            }
        
        # Get target allocations
        target_allocations = InvestmentTypeAllocation.objects.filter(
            strategy=strategy
        ).order_by('display_order')
        
        target_labels = []
        target_data = []
        target_colors = [
            '#0071e3', '#86868b', '#1d1d1f', '#e5e5e7',
            '#0077ed', '#d2d2d7', '#f5f5f7', '#ffffff'
        ]
        
        for i, alloc in enumerate(target_allocations):
            target_labels.append(alloc.investment_type.name)
            target_data.append(float(alloc.target_percentage))
        
        # Get current allocations
        current_allocation = AllocationStrategyService.get_current_allocation(user)
        current_labels = []
        current_data = []
        
        for type_data in current_allocation['investment_types']:
            current_labels.append(type_data['investment_type_name'])
            current_data.append(float(type_data['current_percentage']))
        
        return {
            'target': {
                'labels': target_labels,
                'data': target_data,
                'colors': target_colors[:len(target_labels)]
            },
            'current': {
                'labels': current_labels,
                'data': current_data,
                'colors': target_colors[:len(current_labels)]
            }
        }
    
    @staticmethod
    @transaction.atomic
    def create_default_strategy(user: User) -> UserAllocationStrategy:
        """
        Create a default empty allocation strategy for a new user.
        This creates the strategy object but without any allocations,
        allowing the user to configure it later.
        
        Args:
            user: User instance
        
        Returns:
            UserAllocationStrategy instance
        """
        # Create strategy if it doesn't exist
        strategy, created = UserAllocationStrategy.objects.get_or_create(
            user=user,
            defaults={'total_portfolio_value': None}
        )
        
        return strategy


