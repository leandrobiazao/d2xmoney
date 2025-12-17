"""
Service for managing allocation strategies.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from users.models import User
from portfolio_operations.models import PortfolioPosition
from fixed_income.models import FixedIncomePosition
from crypto.models import CryptoPosition
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
                # Subtypes should sum to the parent type's target_percentage, not 100%
                expected_sum = Decimal(str(type_alloc_data['target_percentage']))
                if not AllocationStrategyService.validate_percentage_sum(sub_percentages, expected_sum):
                    raise ValidationError(
                        f"Sub-type allocations for {investment_type.name} must sum to {expected_sum}% (same as the parent type allocation)"
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
        
        # Calculate total portfolio value from stock positions using current prices
        # For stocks, we need to fetch current prices and multiply by quantity
        from stocks.services import StockService
        stock_total_value = Decimal('0')
        stock_position_current_values = {}  # Cache: ticker -> current_value for grouping later
        
        for pos in positions:
            if pos.quantidade > 0:
                # Try to get price from Stock catalog first (if recently updated)
                current_price = None
                try:
                    from django.utils import timezone
                    from datetime import timedelta
                    
                    stock = Stock.objects.filter(ticker=pos.ticker, is_active=True).first()
                    if stock and stock.current_price and stock.current_price > 0:
                        # Use cached price if updated within last 1 hour (reduced from 4 hours for more accuracy)
                        time_threshold = timezone.now() - timedelta(hours=1)
                        if stock.last_updated and stock.last_updated >= time_threshold:
                            current_price = float(stock.current_price)
                except Exception as e:
                    print(f"Error getting cached price for {pos.ticker}: {e}")
                
                # If no cached price available, fetch from API
                if current_price is None:
                    try:
                        current_price = StockService.fetch_price_from_google_finance(pos.ticker, 'B3')
                        # Update Stock catalog with new price if fetch succeeded
                        if current_price is not None:
                            try:
                                stock = Stock.objects.filter(ticker=pos.ticker, is_active=True).first()
                                if stock:
                                    StockService.update_stock_price(pos.ticker, current_price)
                            except Exception as e:
                                print(f"Error updating stock price for {pos.ticker}: {e}")
                        else:
                            print(f"Warning: Could not fetch current price for {pos.ticker}, using average price")
                    except Exception as e:
                        print(f"Error fetching current price for {pos.ticker}: {e}")
                
                # Use current price if available, otherwise use average price as fallback
                price = Decimal(str(current_price)) if current_price else pos.preco_medio
                position_current_value = Decimal(str(pos.quantidade)) * price
                stock_total_value += position_current_value
                
                # Store position current value for later grouping by type/subtype
                stock_position_current_values[pos.ticker] = position_current_value
        
        # Get CAIXA positions (cash) - these are part of RENDA_FIXA
        caixa_positions = FixedIncomePosition.objects.filter(
            user_id=str(user.id),
            asset_code__startswith='CAIXA_'
        )
        caixa_total_value = sum(
            Decimal(str(pos.net_value)) if pos.net_value > 0 else Decimal(str(pos.position_value))
            for pos in caixa_positions
        )
        
        # Get all Renda Fixa positions (including CAIXA)
        renda_fixa_type = None
        try:
            renda_fixa_type = InvestmentType.objects.get(code='RENDA_FIXA', is_active=True)
        except InvestmentType.DoesNotExist:
            # Try alternative names
            try:
                renda_fixa_type = InvestmentType.objects.get(name__icontains='Renda Fixa', is_active=True)
            except InvestmentType.DoesNotExist:
                pass
        
        renda_fixa_positions = FixedIncomePosition.objects.filter(
            user_id=str(user.id),
            investment_type=renda_fixa_type
        ) if renda_fixa_type else FixedIncomePosition.objects.none()
        
        renda_fixa_total_value = sum(
            Decimal(str(pos.net_value)) if pos.net_value > 0 else Decimal(str(pos.position_value))
            for pos in renda_fixa_positions
        )
        
        # Get crypto positions for "Renda Variável em Dólares" type
        # Only include crypto with investment_type = "Renda Variável em Dólares" and investment_subtype = Crypto/Bitcoin
        renda_var_dolares_type = None
        try:
            renda_var_dolares_type = InvestmentType.objects.get(code='RENDA_VARIAVEL_DOLARES', is_active=True)
        except InvestmentType.DoesNotExist:
            try:
                renda_var_dolares_type = InvestmentType.objects.filter(
                    name__icontains='Renda Variável em Dólares',
                    is_active=True
                ).first()
            except:
                pass
        
        # Filter crypto positions by investment_type and investment_subtype
        if renda_var_dolares_type:
            crypto_positions = CryptoPosition.objects.filter(
                user_id=str(user.id),
                quantity__gt=0,
                crypto_currency__investment_type=renda_var_dolares_type,
                crypto_currency__is_active=True
            ).select_related('crypto_currency', 'crypto_currency__investment_type', 'crypto_currency__investment_subtype')
        else:
            crypto_positions = CryptoPosition.objects.none()
        
        # Calculate crypto value using current prices (if available) or average price
        crypto_total_value = Decimal('0')
        if crypto_positions.exists():
            from crypto.services import CryptoService
            for crypto_pos in crypto_positions:
                crypto_currency = crypto_pos.crypto_currency
                # Try to get current price, fallback to average price
                current_price = None
                if crypto_currency and crypto_currency.symbol:
                    try:
                        current_price = CryptoService.fetch_crypto_price(crypto_currency.symbol, 'BRL')
                    except:
                        pass
                
                price = current_price if current_price else Decimal(str(crypto_pos.average_price))
                crypto_total_value += Decimal(str(crypto_pos.quantity)) * price
        
        # Get Investment Funds (Fundos de Investimento) - part of RENDA_FIXA
        from fixed_income.models import InvestmentFund
        investment_funds = InvestmentFund.objects.filter(user_id=str(user.id))
        
        investment_funds_total_value = sum(
            Decimal(str(fund.position_value)) if fund.position_value > 0 else Decimal(str(fund.net_value))
            for fund in investment_funds
        )
        
        # Total portfolio value = stocks + fixed income (including CAIXA) + crypto + investment funds
        total_value = stock_total_value + renda_fixa_total_value + crypto_total_value + investment_funds_total_value
        
        # Group positions by investment type and subtype (via stock)
        type_values = {}
        for position in positions:
            try:
                stock = Stock.objects.select_related('investment_type', 'investment_subtype').get(
                    ticker=position.ticker, 
                    is_active=True
                )
                investment_type = stock.investment_type
                investment_subtype = stock.investment_subtype
                
                if investment_type:
                    type_id = investment_type.id
                    if type_id not in type_values:
                        type_values[type_id] = {
                            'investment_type_id': type_id,
                            'investment_type_name': investment_type.name,
                            'current_value': Decimal('0'),
                            'sub_types': {}
                        }
                    
                    # Group by subtype within the investment type
                    subtype_id = investment_subtype.id if investment_subtype else None
                    subtype_name = investment_subtype.name if investment_subtype else 'Não categorizado'
                    
                    if subtype_id not in type_values[type_id]['sub_types']:
                        type_values[type_id]['sub_types'][subtype_id] = {
                            'sub_type_id': subtype_id,
                            'sub_type_name': subtype_name,
                            'current_value': Decimal('0')
                        }
                    
                    # Use current value (quantity * current price), not invested value
                    position_current_value = stock_position_current_values.get(
                        position.ticker,
                        Decimal(str(position.valor_total_investido))  # Fallback if not cached
                    )
                    type_values[type_id]['sub_types'][subtype_id]['current_value'] += position_current_value
                    type_values[type_id]['current_value'] += position_current_value
            except Stock.DoesNotExist:
                # Stock not in catalog - treat as unallocated
                pass
        
        # Add RENDA_FIXA from FixedIncomePosition (including CAIXA)
        # Group by subtype within RENDA_FIXA
        if renda_fixa_type:
            type_id = renda_fixa_type.id
            if type_id not in type_values:
                type_values[type_id] = {
                    'investment_type_id': type_id,
                    'investment_type_name': renda_fixa_type.name,
                    'current_value': Decimal('0'),
                    'sub_types': {}
                }
            
            # Group fixed income positions by subtype
            # Track which Caixa positions have been processed (those with subtype assigned)
            caixa_processed_value = Decimal('0')
            
            for fi_position in renda_fixa_positions:
                subtype = fi_position.investment_sub_type
                subtype_id = subtype.id if subtype else None
                subtype_name = subtype.name if subtype else 'Não categorizado'
                
                # Track Caixa positions that have subtype assigned
                if fi_position.asset_code.startswith('CAIXA_'):
                    caixa_processed_value += Decimal(str(fi_position.net_value)) if fi_position.net_value > 0 else Decimal(str(fi_position.position_value))
                
                if subtype_id not in type_values[type_id]['sub_types']:
                    type_values[type_id]['sub_types'][subtype_id] = {
                        'sub_type_id': subtype_id,
                        'sub_type_name': subtype_name,
                        'current_value': Decimal('0')
                    }
                
                position_value = Decimal(str(fi_position.net_value)) if fi_position.net_value > 0 else Decimal(str(fi_position.position_value))
                type_values[type_id]['sub_types'][subtype_id]['current_value'] += position_value
            
            # Also add CAIXA positions that don't have a subtype assigned (legacy data)
            # Only add if there are Caixa positions that weren't processed above (no subtype)
            remaining_caixa_value = caixa_total_value - caixa_processed_value
            if remaining_caixa_value > 0:
                caixa_subtype_id = None  # CAIXA without subtype assigned
                caixa_subtype_name = 'Caixa'
                
                if caixa_subtype_id not in type_values[type_id]['sub_types']:
                    type_values[type_id]['sub_types'][caixa_subtype_id] = {
                        'sub_type_id': caixa_subtype_id,
                        'sub_type_name': caixa_subtype_name,
                        'current_value': Decimal('0')
                    }
                type_values[type_id]['sub_types'][caixa_subtype_id]['current_value'] += remaining_caixa_value
            
            type_values[type_id]['current_value'] += renda_fixa_total_value
            
            # Add Investment Funds to RENDA_FIXA, grouped by subtype
            for fund in investment_funds:
                if fund.investment_type and fund.investment_type.id == type_id:
                    subtype = fund.investment_sub_type
                    subtype_id = subtype.id if subtype else None
                    subtype_name = subtype.name if subtype else 'Fundos de Investimento'
                    
                    if subtype_id not in type_values[type_id]['sub_types']:
                        type_values[type_id]['sub_types'][subtype_id] = {
                            'sub_type_id': subtype_id,
                            'sub_type_name': subtype_name,
                            'current_value': Decimal('0')
                        }
                    
                    fund_value = Decimal(str(fund.position_value)) if fund.position_value > 0 else Decimal(str(fund.net_value))
                    type_values[type_id]['sub_types'][subtype_id]['current_value'] += fund_value
                    type_values[type_id]['current_value'] += fund_value
        
        # Add crypto positions to "Renda Variável em Dólares"
        if renda_var_dolares_type and crypto_positions.exists():
            type_id = renda_var_dolares_type.id
            if type_id not in type_values:
                type_values[type_id] = {
                    'investment_type_id': type_id,
                    'investment_type_name': renda_var_dolares_type.name,
                    'current_value': Decimal('0'),
                    'sub_types': {}
                }
            
            # Group crypto positions by subtype
            for crypto_position in crypto_positions:
                crypto_currency = crypto_position.crypto_currency
                subtype = crypto_currency.investment_subtype
                subtype_id = subtype.id if subtype else None
                subtype_name = subtype.name if subtype else 'Não categorizado'
                
                # Calculate current value: quantity * current_price (if available) or average_price
                from crypto.services import CryptoService
                current_price = None
                if crypto_currency.symbol:
                    current_price = CryptoService.fetch_crypto_price(crypto_currency.symbol, 'BRL')
                
                position_value = Decimal(str(crypto_position.quantity)) * (
                    current_price if current_price else Decimal(str(crypto_position.average_price))
                )
                
                if subtype_id not in type_values[type_id]['sub_types']:
                    type_values[type_id]['sub_types'][subtype_id] = {
                        'sub_type_id': subtype_id,
                        'sub_type_name': subtype_name,
                        'current_value': Decimal('0')
                    }
                
                type_values[type_id]['sub_types'][subtype_id]['current_value'] += position_value
                type_values[type_id]['current_value'] += position_value
        
        # Calculate percentages for types and subtypes
        investment_types = []
        for type_id, type_data in type_values.items():
            percentage = (
                (type_data['current_value'] / total_value * 100)
                if total_value > 0 else Decimal('0')
            )
            # Round to 1 decimal place to avoid floating-point precision issues
            type_data['current_percentage'] = percentage.quantize(Decimal('0.1'))
            
            # Calculate percentages for subtypes within this type
            sub_types_list = []
            for subtype_id, subtype_data in type_data['sub_types'].items():
                subtype_percentage = (
                    (subtype_data['current_value'] / type_data['current_value'] * 100)
                    if type_data['current_value'] > 0 else Decimal('0')
                )
                # Round to 1 decimal place to avoid floating-point precision issues
                subtype_data['current_percentage'] = subtype_percentage.quantize(Decimal('0.1'))
                sub_types_list.append(subtype_data)
            
            type_data['sub_types'] = sub_types_list
            investment_types.append(type_data)
        
        # CAIXA is part of RENDA_FIXA, not unallocated
        unallocated_cash = Decimal('0')
        
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


