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
from configuration.models import InvestmentType, InvestmentSubType
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
        
        # Get "Renda Variável em Reais" investment type
        acoes_reais_type = None
        try:
            acoes_reais_type = InvestmentType.objects.get(code='RENDA_VARIAVEL_REAIS', is_active=True)
        except InvestmentType.DoesNotExist:
            try:
                acoes_reais_type = InvestmentType.objects.filter(
                    Q(code__icontains='RENDA_VARIAVEL') | Q(name__icontains='Renda Variável em Reais'),
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
            
            # For "Renda Variável em Dólares", ensure current_value includes ALL subtypes (BDRs + Bitcoin + others)
            # The target_value should be based on the type percentage, not subtype percentage
            if type_alloc.investment_type.code == 'RENDA_VARIAVEL_DOLARES' or 'Dólares' in investment_type_name:
                # Calculate current value by summing ALL subtypes (BDRs + Bitcoin + others)
                # Find current subtype data for this investment type
                for type_data in current_allocation['investment_types']:
                    if type_data['investment_type_id'] == type_alloc.investment_type.id:
                        # Sum all subtype current values
                        current_subtype_data = {
                            st['sub_type_id']: st for st in type_data.get('sub_types', [])
                        }
                        
                        # Sum all subtype current values
                        current_value = Decimal('0')
                        for subtype_data in current_subtype_data.values():
                            subtype_current_value = Decimal(str(subtype_data.get('current_value', 0)))
                            current_value += subtype_current_value
                        break
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
            
            # Generate subtype rebalancing recommendations
            # Get subtype allocations for this investment type
            subtype_allocations = type_alloc.sub_type_allocations.all()
            if subtype_allocations.exists():
                # Find current subtype data for this investment type
                current_subtype_data = {}
                for type_data in current_allocation['investment_types']:
                    if type_data['investment_type_id'] == type_alloc.investment_type.id:
                        current_subtype_data = {
                            st['sub_type_id']: st for st in type_data.get('sub_types', [])
                        }
                        break
                
                # Generate rebalancing actions for each subtype
                for subtype_alloc in subtype_allocations:
                    subtype = subtype_alloc.sub_type
                    subtype_id = subtype.id if subtype else None
                    subtype_name = subtype.name if subtype else subtype_alloc.custom_name
                    
                    # Check if this is a crypto subtype - if so, create individual actions for each crypto position
                    is_crypto_subtype = False
                    if subtype_name:
                        name_lower = subtype_name.lower()
                        is_crypto_subtype = 'bitcoin' in name_lower or 'crypto' in name_lower or 'cripto' in name_lower
                    
                    if is_crypto_subtype and type_alloc.investment_type.code == 'RENDA_VARIAVEL_DOLARES':
                        # For crypto subtypes, create individual actions for each crypto position
                        try:
                            from crypto.models import CryptoPosition, CryptoCurrency
                            from crypto.services import CryptoService
                            
                            # Get all crypto positions for this user with this subtype
                            crypto_positions = CryptoPosition.objects.filter(
                                user_id=str(user.id),
                                quantity__gt=0,
                                crypto_currency__investment_subtype=subtype,
                                crypto_currency__investment_type=type_alloc.investment_type,
                                crypto_currency__is_active=True
                            ).select_related('crypto_currency').order_by('crypto_currency__symbol')
                            
                            # Calculate target value for subtype (as percentage of total portfolio directly, not relative to type)
                            subtype_target_percentage = subtype_alloc.target_percentage
                            subtype_total_target_value = total_value * (subtype_target_percentage / 100)
                            
                            # Calculate total current value for all cryptos of this subtype
                            subtype_total_current_value = Decimal('0')
                            crypto_actions_data = []
                            
                            for crypto_position in crypto_positions:
                                crypto_currency = crypto_position.crypto_currency
                                
                                # Calculate current value: quantity * current_price (if available) or average_price
                                current_price = None
                                if crypto_currency.symbol:
                                    try:
                                        current_price = CryptoService.fetch_crypto_price(crypto_currency.symbol, 'BRL')
                                    except:
                                        pass
                                
                                position_current_value = Decimal(str(crypto_position.quantity)) * (
                                    Decimal(str(current_price)) if current_price else Decimal(str(crypto_position.average_price))
                                )
                                
                                subtype_total_current_value += position_current_value
                                crypto_actions_data.append({
                                    'crypto_currency': crypto_currency,
                                    'current_value': position_current_value,
                                    'quantity': crypto_position.quantity,
                                    'current_price': current_price
                                })
                            
                            # If we have crypto positions, distribute target value proportionally
                            if crypto_actions_data and subtype_total_current_value > 0:
                                crypto_index = 0
                                for crypto_data in crypto_actions_data:
                                    crypto_currency = crypto_data['crypto_currency']
                                    
                                    # Distribute target value proportionally based on current value
                                    proportion = crypto_data['current_value'] / subtype_total_current_value
                                    crypto_target_value = subtype_total_target_value * proportion
                                    crypto_difference = crypto_target_value - crypto_data['current_value']
                                    
                                    # Calculate quantity to buy/sell if we have current price
                                    quantity_to_adjust = None
                                    if crypto_data['current_price']:
                                        try:
                                            price = Decimal(str(crypto_data['current_price']))
                                            if price > 0:
                                                quantity_to_adjust = crypto_difference / price
                                        except:
                                            pass
                                    # If no current price but we have current_value and quantity, estimate price
                                    elif crypto_data['current_value'] > 0 and crypto_position.quantity > 0:
                                        try:
                                            # Estimate price from current value and quantity
                                            estimated_price = Decimal(str(crypto_data['current_value'])) / Decimal(str(crypto_position.quantity))
                                            if estimated_price > 0:
                                                quantity_to_adjust = crypto_difference / estimated_price
                                        except:
                                            pass
                                    
                                    # Only create action if difference is significant (at least R$ 100)
                                    if abs(crypto_difference) > Decimal('100.00'):
                                        RebalancingAction.objects.create(
                                            recommendation=recommendation,
                                            action_type='rebalance',
                                            investment_subtype=subtype,
                                            subtype_name=crypto_currency.symbol,  # Store crypto symbol in subtype_name for identification
                                            current_value=crypto_data['current_value'],
                                            target_value=crypto_target_value,
                                            difference=crypto_difference,
                                            # For crypto, store as integer but frontend will handle decimal display
                                            # Store rounded to 6 decimal places as integer (multiply by 1e6)
                                            quantity_to_buy=int(quantity_to_adjust * Decimal('1000000')) if quantity_to_adjust and quantity_to_adjust > 0 else None,
                                            quantity_to_sell=int(abs(quantity_to_adjust) * Decimal('1000000')) if quantity_to_adjust and quantity_to_adjust < 0 else None,
                                            display_order=type_alloc.display_order * 1000 + subtype_alloc.display_order * 100 + crypto_index
                                        )
                                    crypto_index += 1
                        except Exception as e:
                            import traceback
                            print(f"Error creating individual crypto actions: {e}")
                            traceback.print_exc()
                            # Fall back to aggregated action if error occurs
                            pass
                    else:
                        # For non-crypto subtypes or when crypto logic fails, create aggregated action as before
                        # Calculate target value for subtype (as percentage of total portfolio directly, not relative to type)
                        subtype_target_percentage = subtype_alloc.target_percentage
                        subtype_target_value = total_value * (subtype_target_percentage / 100)
                        
                        # Find current value for this subtype
                        subtype_current_value = Decimal('0')
                        # Try matching by ID first
                        if subtype_id is not None and subtype_id in current_subtype_data:
                            subtype_current_value = Decimal(str(current_subtype_data[subtype_id].get('current_value', 0)))
                        else:
                            # For custom subtypes or None subtype_id, try to match by name (case-insensitive)
                            for sub_id, sub_data in current_subtype_data.items():
                                current_name = sub_data.get('sub_type_name', '').strip().lower()
                                target_name = subtype_name.strip().lower() if subtype_name else ''
                                if current_name == target_name or current_name.startswith(target_name) or target_name.startswith(current_name):
                                    subtype_current_value = Decimal(str(sub_data.get('current_value', 0)))
                                    break
                        
                        subtype_difference = subtype_target_value - subtype_current_value
                        
                        # Only create action if difference is significant (at least 1% of subtype target or R$ 100)
                        threshold = max(subtype_target_value * Decimal('0.01'), Decimal('100.00'))
                        if abs(subtype_difference) > threshold:
                            RebalancingAction.objects.create(
                                recommendation=recommendation,
                                action_type='rebalance',
                                investment_subtype=subtype,
                                subtype_name=subtype_name if not subtype else None,
                                current_value=subtype_current_value,
                                target_value=subtype_target_value,
                                difference=subtype_difference,
                                display_order=type_alloc.display_order * 1000 + subtype_alloc.display_order
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
        
        # Generate recommendations for BERK34 (Renda Variável em Dólares)
        try:
            acoes_dolares_type = InvestmentType.objects.get(
                code='RENDA_VARIAVEL_DOLARES',
                is_active=True
            )
        except InvestmentType.DoesNotExist:
            # Try alternative names
            try:
                acoes_dolares_type = InvestmentType.objects.filter(
                    Q(code__icontains='RENDA_VARIAVEL') | Q(name__icontains='Renda Variável em Dólares'),
                    is_active=True
                ).first()
            except:
                acoes_dolares_type = None
        
        if acoes_dolares_type:
            # Find the type allocation for Ações em Dólares
            acoes_dolares_alloc = None
            for type_alloc in type_allocations:
                if type_alloc.investment_type.id == acoes_dolares_type.id:
                    acoes_dolares_alloc = type_alloc
                    break
            
            if acoes_dolares_alloc:
                # Get target value for BERK34 using BDRs subtype allocation (15% of type, not 50% of type)
                # Find BDRs subtype allocation
                bdr_subtype = InvestmentSubType.objects.filter(
                    investment_type=acoes_dolares_type,
                    name__icontains='BDR',
                    is_active=True
                ).first()
                
                if bdr_subtype:
                    # Find the BDRs subtype allocation
                    bdr_subtype_alloc = acoes_dolares_alloc.sub_type_allocations.filter(
                        sub_type=bdr_subtype
                    ).first()
                    
                    if bdr_subtype_alloc:
                        # Calculate target value based on BDRs subtype allocation
                        # Subtype target_percentage is a direct percentage of total portfolio, not relative to parent type
                        bdr_subtype_percentage = bdr_subtype_alloc.target_percentage
                        total_value = current_allocation['total_value']
                        # Target value = total_value * subtype_percentage / 100 (direct percentage of total portfolio)
                        target_value = total_value * (bdr_subtype_percentage / 100)
                        
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
                                        investment_subtype=bdr_subtype,  # Link to BDRs subtype
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
                                            investment_subtype=bdr_subtype,  # Link to BDRs subtype
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
                                            investment_subtype=bdr_subtype,  # Link to BDRs subtype
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


