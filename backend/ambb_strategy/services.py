"""
Service for AMBB strategy implementation.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from users.models import User
from portfolio_operations.models import PortfolioPosition
from stocks.models import Stock
from clubedovalor.services import ClubeDoValorService
from configuration.models import InvestmentType
from allocation_strategies.models import UserAllocationStrategy


class AMBBStrategyService:
    """Service for implementing AMBB programmable strategy."""
    
    MAX_STOCKS = 20
    RANK_THRESHOLD = 30
    SALES_LIMIT = Decimal('19000.00')  # 19,000 Reais per month
    
    @staticmethod
    def generate_rebalancing_recommendations(user: User, remaining_monthly_limit: Decimal = None) -> Dict:
        """
        Generate AMBB rebalancing recommendations for "Ações em Reais" stocks only.
        
        Rules:
        1. Filter to only "Ações em Reais" investment type stocks
        2. Target: Maximum 20 stocks total in final allocation
        3. Keep existing portfolio stocks if they are in AMBB 2.0 ranking AND rank <= 30
        4. Sell priority:
           - First: Stocks NOT in AMBB 2.0 ranking
           - Second: Stocks with rank > 30 (sell highest rank/worst first)
        5. Sales limit: Maximum 19,000 Reais per month (including partial sales from rebalancing)
        6. Buy: AMBB 2.0 stocks not in portfolio with ranking <= 30 (NEVER buy ranking > 30)
           - Prioritize lower rankings (better stocks first)
           - Maximum 20 stocks total in final portfolio
        7. Equal value distribution among final selected stocks
        8. Priority: Balance existing portfolio stocks over selling bad stocks completely
        
        Returns:
        {
            'stocks_to_sell': [...],
            'stocks_to_buy': [...],
            'stocks_to_balance': [...],
            'total_sales_value': Decimal,
            'total_partial_sales_value': Decimal,
            'total_all_sales_value': Decimal,
            'sales_limit_reached': bool
        }
        """
        # Get "Renda Variável em Reais" investment type
        # Try different possible codes/names
        acoes_reais_type = None
        possible_codes = ['RENDA_VARIAVEL_REAIS', 'RENDA_VARIAVEL_EM_REAIS']
        possible_names = ['Renda Variável em Reais', 'Renda Variavel em Reais']
        
        for code in possible_codes:
            try:
                acoes_reais_type = InvestmentType.objects.get(code=code, is_active=True)
                break
            except InvestmentType.DoesNotExist:
                continue
        
        if not acoes_reais_type:
            from django.db.models import Q
            for name in possible_names:
                try:
                    acoes_reais_type = InvestmentType.objects.filter(
                        Q(name__icontains=name), 
                        is_active=True
                    ).first()
                    if acoes_reais_type:
                        break
                except InvestmentType.DoesNotExist:
                    continue
        
        if not acoes_reais_type:
            # If not found, return empty recommendations
            return {
                'stocks_to_sell': [],
                'stocks_to_buy': [],
                'stocks_to_balance': [],
                'total_sales_value': Decimal('0'),
                'sales_limit_reached': False,
                'error': 'Renda Variável em Reais investment type not found'
            }
        
        # Get current AMBB 2.0 recommendations
        current_stocks = ClubeDoValorService.get_current_stocks('AMBB2')
        if not current_stocks:
            current_stocks = ClubeDoValorService.get_current_stocks()
        
        # Filter AMBB stocks to only "Ações em Reais" type
        # Auto-fetch missing stocks from yFinance
        from stocks.services import StockService
        
        ambb_reais_stocks = []
        current_ambb_tickers = {}
        for stock_data in current_stocks:
            ticker = stock_data['codigo']
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                if stock.investment_type == acoes_reais_type:
                    ambb_reais_stocks.append(stock_data)
                    current_ambb_tickers[ticker] = stock_data
            except Stock.DoesNotExist:
                # Stock not in catalog - try to fetch from yFinance
                try:
                    fetched_stock = StockService.fetch_and_create_stock(ticker, 'RENDA_VARIAVEL_REAIS')
                    if fetched_stock and fetched_stock.investment_type == acoes_reais_type:
                        ambb_reais_stocks.append(stock_data)
                        current_ambb_tickers[ticker] = stock_data
                except Exception as e:
                    # Failed to fetch - skip this stock
                    print(f"Could not fetch {ticker} from yFinance: {e}")
                    pass
        
        # Get user's portfolio positions
        positions = PortfolioPosition.objects.filter(user_id=str(user.id))
        portfolio_tickers = {pos.ticker: pos for pos in positions if pos.quantidade > 0}
        
        # Filter portfolio stocks to only "Ações em Reais" type
        portfolio_stocks = {}
        for ticker in portfolio_tickers.keys():
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                if stock.investment_type == acoes_reais_type:
                    portfolio_stocks[ticker] = {
                        'stock': stock,
                        'position': portfolio_tickers[ticker],
                        'current_value': Decimal(str(portfolio_tickers[ticker].valor_total_investido)),
                        'current_price': stock.current_price
                    }
            except Stock.DoesNotExist:
                pass
        
        # Get allocation strategy to calculate target values
        try:
            strategy = UserAllocationStrategy.objects.get(user=user)
            acoes_reais_allocation = strategy.type_allocations.filter(
                investment_type=acoes_reais_type
            ).first()
        except UserAllocationStrategy.DoesNotExist:
            acoes_reais_allocation = None
        
        # Calculate total portfolio value (Ações em Reais + Ações em Dólares + Renda Fixa)
        from fixed_income.models import FixedIncomePosition
        from allocation_strategies.services import AllocationStrategyService
        
        current_allocation = AllocationStrategyService.get_current_allocation(user)
        total_portfolio_value = current_allocation['total_value']
        
        # Calculate "Ações em Reais" target total
        if acoes_reais_allocation:
            acoes_reais_target_percentage = acoes_reais_allocation.target_percentage
            acoes_reais_target_total = total_portfolio_value * (acoes_reais_target_percentage / 100)
        else:
            # Default to 30% if not configured
            acoes_reais_target_total = total_portfolio_value * Decimal('0.30')
        
        # Identify stocks to keep (in AMBB 2.0 with rank <= 30)
        stocks_to_keep = {}
        for ticker, stock_data in portfolio_stocks.items():
            if ticker in current_ambb_tickers:
                ranking = current_ambb_tickers[ticker].get('ranking', 999)
                if ranking <= AMBBStrategyService.RANK_THRESHOLD:
                    stocks_to_keep[ticker] = {
                        'stock_data': stock_data,
                        'ranking': ranking,
                        'ambb_data': current_ambb_tickers[ticker]
                    }
        
        # NEW PRIORITY: Sell bad stocks (ranking > 30) COMPLETELY FIRST, then partially if limit allows
        # Strategy: Use ALL available limit to sell bad stocks completely first
        # NO reserve for rebalancing good stocks - they will be kept without selling
        
        # Use ALL remaining monthly limit to sell bad stocks completely
        # We prioritize selling bad stocks completely over rebalancing good stocks
        # If remaining_monthly_limit is None, use the full limit (19,000)
        if remaining_monthly_limit is None:
            remaining_monthly_limit = AMBBStrategyService.SALES_LIMIT
        remaining_limit_for_complete_sales = remaining_monthly_limit
        
        # Identify stocks to sell (prioritized)
        # CRITICAL: Only sell stocks that should NOT be kept
        # Keep stocks with ranking <= 30 (better stocks)
        # Sell stocks with ranking > 30 (worse stocks), ordered by highest ranking first
        stocks_to_sell_list = []
        
        # Priority 1: Stocks NOT in AMBB ranking (no ranking = worst, sell first)
        stocks_not_in_ranking = []
        for ticker, stock_data in portfolio_stocks.items():
            # Only add to sell list if NOT in stocks_to_keep
            if ticker not in current_ambb_tickers and ticker not in stocks_to_keep:
                stocks_not_in_ranking.append({
                    'ticker': ticker,
                    'name': stock_data['stock'].name,
                    'current_value': stock_data['current_value'],
                    'quantity': stock_data['position'].quantidade,
                    'current_price': float(stock_data['current_price']),
                    'ranking': 9999,  # Assign very high ranking to stocks not in AMBB (worst)
                    'priority': 1,
                    'reason': 'Not in AMBB 2.0 ranking'
                })
        
        # Priority 2: Stocks with rank > 30 ONLY (sort by highest rank/worst first)
        # IMPORTANT: Only include stocks that are NOT in stocks_to_keep
        # stocks_to_keep contains stocks with ranking <= 30, so we should never sell those
        # CRITICAL: Also check if stock is in stocks_to_keep - if it is, it shouldn't be here
        rank_over_30 = []
        for ticker, stock_data in portfolio_stocks.items():
            # Skip if already in stocks_to_keep (these are good stocks with ranking <= 30)
            if ticker in stocks_to_keep:
                continue
            
            # Only consider stocks in AMBB that are NOT in stocks_to_keep
            if ticker in current_ambb_tickers:
                ranking = current_ambb_tickers[ticker].get('ranking', 999)
                # Double-check: only add if ranking > 30 (should already be excluded by stocks_to_keep check)
                if ranking > AMBBStrategyService.RANK_THRESHOLD:
                    rank_over_30.append({
                        'ticker': ticker,
                        'name': stock_data['stock'].name,
                        'current_value': stock_data['current_value'],
                        'quantity': stock_data['position'].quantidade,
                        'current_price': float(stock_data['current_price']),
                        'ranking': ranking,
                        'priority': 2,
                        'reason': f'Rank {ranking} > 30'
                    })
        
        # Sort stocks with rank > 30 by highest ranking (worst first)
        rank_over_30.sort(key=lambda x: x['ranking'], reverse=True)
        
        # Combine lists: FIRST stocks not in ranking, THEN stocks with ranking > 30
        # This ensures correct order: outside ranking first, then highest ranking first
        stocks_to_sell_list = stocks_not_in_ranking + rank_over_30
        
        # Apply ALL available limit to sell bad stocks COMPLETELY first
        # Priority order:
        # 1. First: Stocks NOT in AMBB ranking (priority 1, ranking 9999)
        # 2. Second: Stocks with ranking > 30, ordered by highest ranking (worst) first (priority 2)
        # Process in this exact order, respecting the limit
        total_sales_value = Decimal('0')
        final_stocks_to_sell = []
        sales_limit_reached = False
        remaining_limit_after_complete_sales = remaining_limit_for_complete_sales
        
        for sell_item in stocks_to_sell_list:
            # Check if we can sell this stock completely
            # IMPORTANT: Check if the stock's value fits in the REMAINING limit, not total
            # We compare against remaining_limit_after_complete_sales which is updated as we go
            if sell_item['current_value'] <= remaining_limit_after_complete_sales:
                # Can sell this stock completely - it fits in the remaining limit
                final_stocks_to_sell.append(sell_item)
                total_sales_value += sell_item['current_value']
                remaining_limit_after_complete_sales -= sell_item['current_value']
            else:
                # Can't sell this one completely - will try to sell partially later
                sales_limit_reached = True
                # Continue processing - don't break, as we want to try selling others completely
                # The remaining limit will be used for partial sales later
                # IMPORTANT: Don't add to final_stocks_to_sell, but it will be processed for partial sale later
        
        # Determine final stock selection (max 20)
        # Stocks to keep (these are the ones we want to keep)
        final_stock_tickers = set(stocks_to_keep.keys())
        
        # Stocks that couldn't be sold due to limit (we have to keep them, but they count toward the 20 limit)
        stocks_kept_due_to_limit = set()
        for sell_item in stocks_to_sell_list:
            if sell_item not in final_stocks_to_sell:
                # This stock couldn't be sold due to limit - we have to keep it
                ticker = sell_item['ticker']
                final_stock_tickers.add(ticker)
                stocks_kept_due_to_limit.add(ticker)
        
        # Get ALL AMBB 2.0 stocks sorted by ranking (lower = better)
        # Sort from lowest ranking (best) to highest ranking (worst)
        all_ambb_sorted = sorted(ambb_reais_stocks, key=lambda x: x.get('ranking', 999))
        
        # Identify stocks to buy:
        # 1. Must be in AMBB 2.0 ranking
        # 2. Must NOT be in current portfolio (or in stocks to keep)
        # 3. Must have ranking <= 30 (RANK_THRESHOLD) - NEVER buy stocks with ranking > 30
        # 4. Prioritize lower rankings (better stocks first)
        # 5. Maximum 20 stocks total in final portfolio
        stocks_to_buy = []
        available_slots = AMBBStrategyService.MAX_STOCKS - len(final_stock_tickers)
        
        # Only recommend buying if we have available slots
        if available_slots > 0:
            for stock_data in all_ambb_sorted:
                if len(stocks_to_buy) >= available_slots:
                    break  # We've filled all available slots
                
                ticker = stock_data['codigo']
                ranking = stock_data.get('ranking', 999)
                
                # Skip if already in current portfolio (we already own it)
                # Check portfolio_stocks directly, not final_stock_tickers
                # because final_stock_tickers includes stocks we want to keep
                if ticker in portfolio_stocks:
                    continue  # Already in portfolio, skip
                
                # NEVER recommend stocks with ranking > 30
                # This is a hard limit - we should never buy stocks above rank 30
                if ranking > AMBBStrategyService.RANK_THRESHOLD:
                    continue  # Skip stocks with ranking > 30
                
                # Try to get stock from catalog
                try:
                    stock = Stock.objects.get(ticker=ticker, is_active=True)
                    
                    # Verify investment type matches
                    if stock.investment_type != acoes_reais_type:
                        # Stock exists but wrong investment type - skip it
                        continue
                    
                    # All checks passed - recommend buying
                    final_stock_tickers.add(ticker)
                    stocks_to_buy.append({
                        'ticker': ticker,
                        'name': stock_data['nome'],
                        'ranking': ranking,
                        'current_price': float(stock.current_price) if stock.current_price > 0 else 0
                    })
                    
                except Stock.DoesNotExist:
                    # Stock not in catalog - skip it
                    # This means the ticker from AMBB 2.0 is not in our stock catalog
                    continue
                except Exception as e:
                    # Log any other errors but continue
                    print(f"Error processing stock {ticker} (ranking {ranking}): {e}")
                    continue
        
        # Calculate target value per stock (equal distribution)
        final_stock_count = len(final_stock_tickers)
        if final_stock_count > 0:
            target_value_per_stock = acoes_reais_target_total / final_stock_count
        else:
            target_value_per_stock = Decimal('0')
        
        # Generate balance actions for stocks to keep and new buys
        # IMPORTANT: Good stocks (ranking <= 30) should NOT be sold partially
        # They should be kept without selling, even if above target
        stocks_to_balance = []
        # remaining_sales_limit is now only for partial sales of bad stocks (ranking > 30)
        # This is the limit that remains after selling bad stocks completely
        remaining_sales_limit = remaining_limit_after_complete_sales
        
        # For stocks to keep - include ALL stocks that will be in final portfolio
        # Even if they don't need adjustment, they should appear in the balance list
        # But if they need to sell (partial), we must respect the remaining sales limit
        for ticker in stocks_to_keep.keys():
            stock_data = portfolio_stocks[ticker]
            current_value = stock_data['current_value']
            difference = target_value_per_stock - current_value
            
            stock = stock_data['stock']
            current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
            
            # Calculate quantity adjustment
            quantity_diff = 0
            partial_sale_value = Decimal('0')
            
            # Get ranking for this stock
            stock_ranking = stocks_to_keep[ticker]['ranking']
            
            if difference < Decimal('0'):  # Need to sell (current value > target)
                # CRITICAL: For stocks with good ranking (<= 30), DO NOT sell partially
                # Priority is to keep good stocks and sell bad stocks (ranking > 30) first
                # Only if we have exhausted selling bad stocks and still have limit, then consider rebalancing good stocks
                # For now, keep good stocks without selling - prioritize selling bad stocks
                quantity_diff = 0
                # Don't use remaining_sales_limit for good stocks - save it for bad stocks
                
                # IMPORTANT: Don't recalculate difference - it should always be target - current
                # The difference shows the gap between target and current, not after partial sale
            elif difference > Decimal('0.01'):  # Need to buy
                # NEVER recommend buying more of stocks with ranking > 30
                # Stocks in stocks_to_keep should have ranking <= 30, but double-check
                if stock_ranking <= AMBBStrategyService.RANK_THRESHOLD:
                    quantity_diff = int(difference / current_price)
                else:
                    # Ranking > 30: don't recommend buying more
                    quantity_diff = 0
                    # Keep the original difference (positive) to show it's still below target
                    # Don't zero it out - the difference should reflect the actual gap
                    # difference remains as is (positive, showing need to buy, but we won't recommend it)
            
            # Include ALL stocks to keep, even if difference is small
            # This ensures all 20 stocks appear in the balance list
            # CRITICAL: Always recalculate difference as target - current to ensure correct sign
            # Never use a recalculated difference that might have wrong sign
            # The difference should always reflect: target_value - current_value
            final_difference = target_value_per_stock - current_value
            
            stocks_to_balance.append({
                'ticker': ticker,
                'name': stock.name,
                'ranking': stocks_to_keep[ticker]['ranking'],
                'current_value': float(current_value),
                'target_value': float(target_value_per_stock),
                'difference': float(final_difference),  # Always target - current
                'quantity_to_adjust': quantity_diff,  # Will be 0 if no adjustment needed
                'current_price': float(current_price)
            })
        
        # For stocks that couldn't be sold COMPLETELY due to 19K limit - try to sell them PARTIALLY
        # These stocks are bad (not in ranking or ranking > 30) and should be sold, even if partially
        # Use the remaining limit after complete sales (remaining_limit_after_complete_sales) to sell as much as possible
        # IMPORTANT: Process in the SAME order as complete sales:
        # 1. First: stocks not in ranking (priority 1)
        # 2. Second: stocks with highest ranking (priority 2, worst first)
        
        for sell_item in stocks_to_sell_list:
            if sell_item not in final_stocks_to_sell:
                # This stock couldn't be sold completely due to limit - try to sell PARTIALLY
                ticker = sell_item['ticker']
                if ticker in portfolio_stocks:
                    stock_data = portfolio_stocks[ticker]
                    current_value = stock_data['current_value']
                    difference = target_value_per_stock - current_value
                    
                    stock = stock_data['stock']
                    current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
                    
                    # Calculate quantity adjustment
                    quantity_diff = 0
                    
                    if difference < Decimal('0'):  # Need to sell (but we already couldn't sell completely)
                        # These are bad stocks (ranking > 30) that couldn't be sold completely
                        # Try to sell PARTIALLY using remaining sales limit
                        # Use remaining_limit_after_complete_sales (which tracks the limit after complete sales)
                        if remaining_limit_after_complete_sales > 0:
                            # Calculate how much we can sell with remaining limit
                            # IMPORTANT: Only sell PARTIALLY if the remaining limit is LESS than current_value
                            # If remaining limit >= current_value, it should have been sold completely already
                            if remaining_limit_after_complete_sales < current_value:
                                # True partial sale: sell only what fits in the remaining limit
                                max_sale_value = remaining_limit_after_complete_sales
                                quantity_to_sell = int(max_sale_value / current_price)
                                if quantity_to_sell > 0:
                                    partial_sale_value = quantity_to_sell * current_price
                                    quantity_diff = -quantity_to_sell
                                    remaining_limit_after_complete_sales -= partial_sale_value
                                    # Note: total_partial_sales_value is calculated at the end from stocks_to_balance
                                else:
                                    # Can't sell even 1 share with remaining limit - mark for future sale
                                    # Set quantity_diff to a small negative value to indicate need to sell
                                    quantity_diff = 0  # No partial sale possible now
                            else:
                                # This shouldn't happen - if limit >= current_value, should have been sold completely
                                # But if it did, don't sell partially (keep quantity_diff = 0)
                                quantity_diff = 0
                        else:
                            # No remaining limit - can't sell now, but should still show as needing to sell
                            # For stocks with ranking > 30 and negative difference, we want to sell but can't due to limit
                            # Calculate how much we WOULD sell if we had limit (for display purposes)
                            # This helps the user understand these stocks need to be sold
                            if current_price > 0:
                                # Calculate quantity based on the difference (how much over target)
                                quantity_to_sell_if_possible = int(abs(difference) / current_price)
                                # Set a small negative value to indicate need to sell, even if we can't now
                                # This will show as "Vender X" in the UI, indicating the stock should be sold
                                quantity_diff = -quantity_to_sell_if_possible if quantity_to_sell_if_possible > 0 else 0
                            else:
                                quantity_diff = 0
                        # Difference remains as target - current (negative, showing need to sell)
                        # The negative difference and quantity_diff will show the need to sell
                    elif difference > Decimal('0.01'):  # Need to buy
                        # NEVER recommend buying more of stocks with ranking > 30
                        # If ranking > 30, we should not buy more, only sell if needed
                        if ranking <= AMBBStrategyService.RANK_THRESHOLD:
                            quantity_diff = int(difference / current_price)
                        else:
                            # Ranking > 30: don't recommend buying more
                            quantity_diff = 0
                            # Keep the original difference (positive) to show it's still below target
                            # Don't zero it out - the difference should reflect the actual gap
                            # difference remains as is (positive, showing need to buy, but we won't recommend it)
                    
                    # Get ranking from AMBB 2.0 if available, otherwise use a high number
                    ranking = 999
                    for ambb_stock in ambb_reais_stocks:
                        if ambb_stock.get('codigo') == ticker:
                            ranking = ambb_stock.get('ranking', 999)
                            break
                    
                    # CRITICAL: Always recalculate difference as target - current to ensure correct sign
                    final_difference = target_value_per_stock - current_value
                    
                    stocks_to_balance.append({
                        'ticker': ticker,
                        'name': stock.name,
                        'ranking': ranking,
                        'current_value': float(current_value),
                        'target_value': float(target_value_per_stock),
                        'difference': float(final_difference),  # Always target - current
                        'quantity_to_adjust': quantity_diff,
                        'current_price': float(current_price)
                    })
        
        # For new stocks to buy
        # Double-check: NEVER add stocks with ranking > 30 to balance list
        for buy_item in stocks_to_buy:
            ranking = buy_item.get('ranking', 999)
            # Safety check: skip if ranking > 30 (shouldn't happen due to earlier check, but just in case)
            if ranking > AMBBStrategyService.RANK_THRESHOLD:
                continue  # Skip stocks with ranking > 30
            
            stocks_to_balance.append({
                'ticker': buy_item['ticker'],
                'name': buy_item['name'],
                'ranking': ranking,
                'current_value': 0.0,
                'target_value': float(target_value_per_stock),
                'difference': float(target_value_per_stock),
                'quantity_to_adjust': int(target_value_per_stock / Decimal(str(buy_item['current_price']))) if buy_item['current_price'] > 0 else 0,
                'current_price': buy_item['current_price']
            })
        
        # Format sell list for response
        formatted_sells = []
        for sell_item in final_stocks_to_sell:
            formatted_sells.append({
                'ticker': sell_item['ticker'],
                'name': sell_item['name'],
                'current_value': float(sell_item['current_value']),
                'quantity': sell_item['quantity'],
                'reason': sell_item['reason'],
                'priority': sell_item['priority'],
                'ranking': sell_item.get('ranking', None)  # Add ranking to response
            })
        
        # Format buy list for response
        formatted_buys = []
        for buy_item in stocks_to_buy:
            target_quantity = int(target_value_per_stock / Decimal(str(buy_item['current_price']))) if buy_item['current_price'] > 0 else 0
            formatted_buys.append({
                'ticker': buy_item['ticker'],
                'name': buy_item['name'],
                'ranking': buy_item['ranking'],
                'target_value': float(target_value_per_stock),
                'target_quantity': target_quantity,
                'current_price': buy_item['current_price']
            })
        
        # Debug info: show why top rankings weren't recommended
        # Also track which stocks should be sold but weren't
        stocks_should_sell_but_didnt = []
        for sell_item in stocks_to_sell_list:
            if sell_item not in final_stocks_to_sell:
                # This stock should be sold but wasn't
                stocks_should_sell_but_didnt.append({
                    'ticker': sell_item['ticker'],
                    'ranking': sell_item.get('ranking', 999),
                    'current_value': float(sell_item['current_value']),
                    'reason': sell_item.get('reason', 'Unknown'),
                    'would_need_limit': float(sell_item['current_value']),
                    'remaining_limit': float(remaining_limit_after_complete_sales),
                    'total_sales_so_far': float(total_sales_value)
                })
        
        # Track specific stocks we're looking for
        target_tickers = ['VAMO3', 'LAVV3', 'IGTI11', 'KEPL3']
        target_stocks_info = []
        for ticker in target_tickers:
            in_portfolio = ticker in portfolio_stocks
            in_ambb = ticker in current_ambb_tickers
            in_stocks_to_keep = ticker in stocks_to_keep
            in_stocks_to_sell_list = any(s['ticker'] == ticker for s in stocks_to_sell_list)
            in_final_stocks_to_sell = any(s['ticker'] == ticker for s in final_stocks_to_sell)
            ranking = current_ambb_tickers.get(ticker, {}).get('ranking', None) if in_ambb else None
            current_value = portfolio_stocks.get(ticker, {}).get('current_value', Decimal('0')) if in_portfolio else Decimal('0')
            
            target_stocks_info.append({
                'ticker': ticker,
                'in_portfolio': in_portfolio,
                'in_ambb': in_ambb,
                'ranking': ranking,
                'in_stocks_to_keep': in_stocks_to_keep,
                'in_stocks_to_sell_list': in_stocks_to_sell_list,
                'in_final_stocks_to_sell': in_final_stocks_to_sell,
                'current_value': float(current_value)
            })
        
        debug_info = {
            'available_slots': available_slots,
            'final_stock_tickers_count': len(final_stock_tickers),
            'stocks_to_keep_count': len(stocks_to_keep),
            'stocks_kept_due_to_limit_count': len(stocks_kept_due_to_limit),
            'stocks_to_balance_count': len(stocks_to_balance),
            'final_stock_tickers': list(final_stock_tickers),
            'stocks_to_buy_count': len(stocks_to_buy),
            'stocks_to_sell_list_count': len(stocks_to_sell_list),
            'final_stocks_to_sell_count': len(final_stocks_to_sell),
            'remaining_limit_for_complete_sales': float(remaining_limit_for_complete_sales),
            'remaining_limit_after_complete_sales': float(remaining_limit_after_complete_sales),
            'total_sales_value': float(total_sales_value),
            'stocks_should_sell_but_didnt': stocks_should_sell_but_didnt,
            'target_stocks_info': target_stocks_info,
            'stocks_to_sell_list_details': [
                {
                    'ticker': s['ticker'],
                    'ranking': s.get('ranking', 999),
                    'current_value': float(s['current_value']),
                    'priority': s.get('priority', 0),
                    'in_final_sell': s in final_stocks_to_sell
                }
                for s in stocks_to_sell_list
            ],
            'top_10_ambb_rankings': [
                {
                    'ticker': s['codigo'],
                    'ranking': s.get('ranking', 999),
                    'in_portfolio': s['codigo'] in portfolio_stocks,
                    'in_catalog': Stock.objects.filter(ticker=s['codigo'], is_active=True).exists()
                }
                for s in all_ambb_sorted[:10]
            ]
        }
        
        # Calculate total sales including partial sales from rebalancing
        total_partial_sales = Decimal('0')
        for balance_item in stocks_to_balance:
            quantity_to_adjust = balance_item.get('quantity_to_adjust', 0)
            if quantity_to_adjust < 0:  # Negative means selling
                quantity_to_sell = abs(quantity_to_adjust)
                current_price = Decimal(str(balance_item['current_price']))
                sale_value = quantity_to_sell * current_price
                total_partial_sales += sale_value
        
        total_all_sales = total_sales_value + total_partial_sales
        
        return {
            'stocks_to_sell': formatted_sells,
            'stocks_to_buy': formatted_buys,
            'stocks_to_balance': stocks_to_balance,
            'total_sales_value': float(total_sales_value),  # Complete sales only
            'total_partial_sales_value': float(total_partial_sales),  # Partial sales from rebalancing
            'total_all_sales_value': float(total_all_sales),  # Total of all sales (complete + partial)
            'sales_limit_reached': total_all_sales >= AMBBStrategyService.SALES_LIMIT,
            'target_stocks_count': final_stock_count,
            'current_portfolio_count': len(portfolio_stocks),
            'target_value_per_stock': float(target_value_per_stock),
            'debug_info': debug_info
        }


