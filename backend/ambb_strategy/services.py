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
                # Filter: must be "Ações em Reais" type AND NOT a FII (stock_class != 'FII')
                if stock.investment_type == acoes_reais_type and stock.stock_class != 'FII':
                    ambb_reais_stocks.append(stock_data)
                    current_ambb_tickers[ticker] = stock_data
            except Stock.DoesNotExist:
                # Stock not in catalog - try to fetch from yFinance
                try:
                    fetched_stock = StockService.fetch_and_create_stock(ticker, 'RENDA_VARIAVEL_REAIS')
                    if fetched_stock and fetched_stock.investment_type == acoes_reais_type and fetched_stock.stock_class != 'FII':
                        ambb_reais_stocks.append(stock_data)
                        current_ambb_tickers[ticker] = stock_data
                except Exception as e:
                    # Failed to fetch - skip this stock
                    print(f"Could not fetch {ticker} from yFinance: {e}")
                    pass
        
        # Get user's portfolio positions
        positions = PortfolioPosition.objects.filter(user_id=str(user.id))
        portfolio_tickers = {pos.ticker: pos for pos in positions if pos.quantidade > 0}
        
        # Filter portfolio stocks to only "Ações em Reais" type (exclude FIIs)
        portfolio_stocks = {}
        for ticker in portfolio_tickers.keys():
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                # Filter: must be "Ações em Reais" type AND NOT a FII (stock_class != 'FII')
                if stock.investment_type == acoes_reais_type and stock.stock_class != 'FII':
                    position = portfolio_tickers[ticker]
                    # Calculate current value using current price (same as AllocationStrategyService)
                    # Fetch current price, fallback to average price if fetch fails
                    current_price = None
                    try:
                        current_price = StockService.fetch_price_from_google_finance(ticker, 'B3')
                    except:
                        pass
                    
                    # Use current price if available, otherwise use average price as fallback
                    price = Decimal(str(current_price)) if current_price else position.preco_medio
                    position_current_value = Decimal(str(position.quantidade)) * price
                    
                    portfolio_stocks[ticker] = {
                        'stock': stock,
                        'position': position,
                        'current_value': position_current_value,
                        'current_price': price  # Use the calculated price (current or average)
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
        
        # NEW LOGIC: Track if we stopped selling due to limit
        # This ensures strict priority even when moving from complete sales to partial sales
        stopped_due_to_limit = False
        
        for sell_item in stocks_to_sell_list:
            # Check if we can sell this stock completely
            # IMPORTANT: Check if the stock's value fits in the REMAINING limit, not total
            # We compare against remaining_limit_after_complete_sales which is updated as we go
            if not stopped_due_to_limit and sell_item['current_value'] <= remaining_limit_after_complete_sales:
                # Can sell this stock completely - it fits in the remaining limit
                final_stocks_to_sell.append(sell_item)
                total_sales_value += sell_item['current_value']
                remaining_limit_after_complete_sales -= sell_item['current_value']
            else:
                # Can't sell this one completely - will try to sell partially later
                sales_limit_reached = True
                stopped_due_to_limit = True
                # Stop processing complete sales to respect priority
                # If we skip this high-priority stock to sell a lower-priority one completely,
                # we are violating the ranking priority.
                # The remaining limit will be used for partial sales later in strict priority order
                # break is not needed here if we use the stopped_due_to_limit flag, 
                # but we can break to save iterations since we won't add any more to complete sales
                break
        
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
        # Use a single shared limit for all partial sales (both stocks_to_keep and stocks_to_sell_list)
        # This ensures the total partial sales never exceed the remaining limit
        shared_remaining_limit = remaining_limit_after_complete_sales
        
        # CRITICAL: Process bad stocks (from stocks_to_sell_list) FIRST, before good stocks (from stocks_to_keep)
        # This ensures bad stocks like CPFE3 (ranking 50) are sold before good stocks like JHSF3 (ranking 18)
        # even if the good stock has a larger absolute difference
        
        # For stocks that couldn't be sold COMPLETELY due to 19K limit - try to sell them PARTIALLY
        # These stocks are bad (not in ranking or ranking > 30) and should be sold, even if partially
        # Use the remaining limit after complete sales (remaining_limit_after_complete_sales) to sell as much as possible
        # IMPORTANT: Sort by largest absolute difference (most over target) first, not by ranking
        # This ensures stocks with the largest difference between current and target are prioritized
        
        # Calculate difference for each stock in stocks_to_sell_list that wasn't sold completely
        stocks_for_partial_sale = []
        for sell_item in stocks_to_sell_list:
            if sell_item not in final_stocks_to_sell:
                # This stock couldn't be sold completely due to limit - try to sell PARTIALLY
                ticker = sell_item['ticker']
                if ticker in portfolio_stocks:
                    stock_data = portfolio_stocks[ticker]
                    current_value = stock_data['current_value']
                    difference = target_value_per_stock - current_value
                    
                    # Add to list for sorting by absolute difference
                    stocks_for_partial_sale.append({
                        'sell_item': sell_item,
                        'ticker': ticker,
                        'stock_data': stock_data,
                        'current_value': current_value,
                        'difference': difference,
                        'target_value': target_value_per_stock
                    })
        
        # Sort by LARGEST absolute difference first (most over target first)
        # This prioritizes stocks with the largest difference between current and target value
        stocks_for_partial_sale.sort(key=lambda x: abs(x['difference']), reverse=True)
        
        # Process bad stocks partial sales FIRST (from stocks_to_sell_list)
        # These are bad stocks (ranking > 30) that couldn't be sold completely
        # CRITICAL: Process these BEFORE good stocks (stocks_needing_sale) to prioritize bad stocks
        # CRITICAL: Only process while we have remaining limit, stop once limit is exhausted
        for stock_info in stocks_for_partial_sale:
            # Check if we still have limit available - if not, skip remaining stocks
            if shared_remaining_limit <= 0:
                # No more limit available - add remaining stocks without selling
                sell_item = stock_info['sell_item']
                ticker = stock_info['ticker']
                stock_data = stock_info['stock_data']
                current_value = stock_info['current_value']
                difference = stock_info['difference']
                target_value = stock_info['target_value']
                stock = stock_data['stock']
                current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
                
                ranking = sell_item.get('ranking', 999)
                if ranking == 999:
                    for ambb_stock in ambb_reais_stocks:
                        if ambb_stock.get('codigo') == ticker:
                            ranking = ambb_stock.get('ranking', 999)
                            break
                
                final_difference = target_value_per_stock - current_value
                stocks_to_balance.append({
                    'ticker': ticker,
                    'name': stock.name,
                    'ranking': ranking,
                    'current_value': float(current_value),
                    'target_value': float(target_value_per_stock),
                    'difference': float(final_difference),
                    'quantity_to_adjust': 0,  # Can't sell - no limit left
                    'current_price': float(current_price)
                })
                continue
            
            sell_item = stock_info['sell_item']
            ticker = stock_info['ticker']
            stock_data = stock_info['stock_data']
            current_value = stock_info['current_value']
            difference = stock_info['difference']
            target_value = stock_info['target_value']
            
            stock = stock_data['stock']
            current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
            
            # Calculate quantity adjustment
            quantity_diff = 0
            
            # CRITICAL FIX: Stocks in stocks_to_sell_list are bad stocks (ranking > 30 or not in ranking)
            # They should be sold regardless of whether they're over or under target
            # NEW: Priority is now by largest absolute difference (most over target first), not by ranking
            # We should sell as much as possible with the remaining limit, prioritizing by difference
            
            # Try to sell PARTIALLY using shared remaining limit
            # Use shared_remaining_limit (which tracks the limit after complete sales)
            # STOPS processing partial sales if we hit the limit
            # NEW: Process in order of largest absolute difference (already sorted above)
            # Once we find a stock we can't sell completely, we sell it partially and STOP
            # We don't continue to lower priority stocks even if they fit the remaining limit
            
            # Calculate how much we can sell with remaining limit
            # IMPORTANT: Only sell PARTIALLY if the remaining limit is LESS than current_value
            # If remaining limit >= current_value, it should have been sold completely already
            if shared_remaining_limit < current_value:
                # True partial sale: sell only what fits in the remaining limit
                max_sale_value = shared_remaining_limit
                quantity_to_sell = int(max_sale_value / current_price)
                if quantity_to_sell > 0:
                    partial_sale_value = quantity_to_sell * current_price
                    quantity_diff = -quantity_to_sell
                    # CRITICAL: Subtract the ACTUAL sale value, not the current_value
                    shared_remaining_limit -= partial_sale_value
                    # Note: total_partial_sales_value is calculated at the end from stocks_to_balance
                else:
                    # Can't sell even 1 share with remaining limit - mark for future sale
                    quantity_diff = 0  # No partial sale possible now
                
                # CRITICAL: Since we used the remaining limit for this high-priority stock (largest difference),
                # we must STOP processing further sales to respect priority.
                # Even if there's a tiny bit of limit left (e.g. due to share price rounding),
                # we stop here.
                shared_remaining_limit = Decimal('0')
            else:
                # This shouldn't happen - if limit >= current_value, should have been sold completely
                # But if it did, don't sell partially (keep quantity_diff = 0)
                quantity_diff = 0
            
            # For stocks in stocks_to_sell_list, we always want to sell (not buy)
            # The difference might be positive (under target) or negative (over target)
            # But since it's a bad stock (ranking > 30), we should sell it, not buy more
            # The quantity_diff is already set above based on the remaining limit
            
            # Get ranking from sell_item (already has the correct ranking from stocks_to_sell_list)
            # Fallback to AMBB 2.0 if not available
            ranking = sell_item.get('ranking', 999)
            if ranking == 999:
                # Try to get from AMBB 2.0 as fallback
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
        
        # For stocks to keep - include ALL stocks that will be in final portfolio
        # Even if they don't need adjustment, they should appear in the balance list
        # But if they need to sell (partial), we must respect the remaining sales limit
        # Collect stocks that need selling first, then sort by largest absolute difference
        stocks_needing_sale = []
        stocks_needing_buy = []
        stocks_at_target = []
        
        for ticker in stocks_to_keep.keys():
            stock_data = portfolio_stocks[ticker]
            current_value = stock_data['current_value']
            difference = target_value_per_stock - current_value
            
            stock = stock_data['stock']
            current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
            
            # Get ranking for this stock
            stock_ranking = stocks_to_keep[ticker]['ranking']
            
            if difference < Decimal('0'):  # Need to sell (current value > target)
                # Collect stocks that need selling, will sort by largest absolute difference
                stocks_needing_sale.append({
                    'ticker': ticker,
                    'stock_data': stock_data,
                    'stock': stock,
                    'current_price': current_price,
                    'current_value': current_value,
                    'difference': difference,
                    'ranking': stock_ranking
                })
            elif difference > Decimal('0.01'):  # Need to buy
                stocks_needing_buy.append({
                    'ticker': ticker,
                    'stock_data': stock_data,
                    'stock': stock,
                    'current_price': current_price,
                    'current_value': current_value,
                    'difference': difference,
                    'ranking': stock_ranking
                })
            else:  # At target (difference is small)
                stocks_at_target.append({
                    'ticker': ticker,
                    'stock_data': stock_data,
                    'stock': stock,
                    'current_price': current_price,
                    'current_value': current_value,
                    'difference': difference,
                    'ranking': stock_ranking
                })
        
        # IMPORTANT: Bad stocks (from stocks_to_sell_list) should be sold BEFORE good stocks (from stocks_to_keep)
        # Even if a good stock has a larger absolute difference, bad stocks take priority
        # So we process stocks_for_partial_sale FIRST, then stocks_needing_sale
        
        # Sort stocks needing sale by LARGEST absolute difference first (most over target first)
        # This prioritizes stocks that are most over-allocated for selling
        stocks_needing_sale.sort(key=lambda x: abs(x['difference']), reverse=True)
        
        # Process bad stocks first (from stocks_to_sell_list - stocks_for_partial_sale)
        # These are handled in the stocks_for_partial_sale section below
        
        # Process good stocks needing sale (from stocks_to_keep): prioritize by largest absolute difference
        # CRITICAL: Only process AFTER bad stocks have been handled, and only while we have remaining limit
        for stock_info in stocks_needing_sale:
            # Check if we still have limit available - if not, skip remaining stocks
            if shared_remaining_limit <= 0:
                # No more limit available - add remaining stocks without selling
                ticker = stock_info['ticker']
                stock_data = stock_info['stock_data']
                stock = stock_info['stock']
                current_price = stock_info['current_price']
                current_value = stock_info['current_value']
                stock_ranking = stock_info['ranking']
                
                final_difference = target_value_per_stock - current_value
                stocks_to_balance.append({
                    'ticker': ticker,
                    'name': stock.name,
                    'ranking': stock_ranking,
                    'current_value': float(current_value),
                    'target_value': float(target_value_per_stock),
                    'difference': float(final_difference),
                    'quantity_to_adjust': 0,  # Can't sell - no limit left
                    'current_price': float(current_price)
                })
                continue
            
            ticker = stock_info['ticker']
            stock_data = stock_info['stock_data']
            stock = stock_info['stock']
            current_price = stock_info['current_price']
            current_value = stock_info['current_value']
            difference = stock_info['difference']
            stock_ranking = stock_info['ranking']
            
            # Calculate quantity adjustment
            quantity_diff = 0
            
            # For stocks with good ranking (<= 30) that are over target:
            # Use shared remaining limit to sell partially, prioritizing by largest absolute difference
            over_allocation = abs(difference)  # Amount over target
            
            # Calculate how much we can sell with remaining limit
            # Only sell PARTIALLY if the remaining limit is LESS than the over-allocation amount
            if shared_remaining_limit < over_allocation:
                # True partial sale: sell only what fits in the remaining limit
                max_sale_value = shared_remaining_limit
                quantity_to_sell = int(max_sale_value / current_price)
                if quantity_to_sell > 0:
                    partial_sale_value = quantity_to_sell * current_price
                    quantity_diff = -quantity_to_sell
                    # CRITICAL: Subtract the ACTUAL sale value, not the over_allocation
                    shared_remaining_limit -= partial_sale_value
                else:
                    quantity_diff = 0
                # Stop after using the limit for highest priority stock (largest difference)
                # Set to 0 to prevent further processing
                shared_remaining_limit = Decimal('0')
            else:
                # Can sell the full over-allocation
                quantity_to_sell = int(over_allocation / current_price)
                if quantity_to_sell > 0:
                    # Calculate actual sale value
                    actual_sale_value = quantity_to_sell * current_price
                    quantity_diff = -quantity_to_sell
                    # CRITICAL: Subtract the ACTUAL sale value, not the over_allocation
                    shared_remaining_limit -= actual_sale_value
                else:
                    quantity_diff = 0
            
            # CRITICAL: Always recalculate difference as target - current to ensure correct sign
            final_difference = target_value_per_stock - current_value
            
            stocks_to_balance.append({
                'ticker': ticker,
                'name': stock.name,
                'ranking': stock_ranking,
                'current_value': float(current_value),
                'target_value': float(target_value_per_stock),
                'difference': float(final_difference),  # Always target - current
                'quantity_to_adjust': quantity_diff,
                'current_price': float(current_price)
            })
        
        # Process stocks needing buy
        for stock_info in stocks_needing_buy:
            ticker = stock_info['ticker']
            stock_data = stock_info['stock_data']
            stock = stock_info['stock']
            current_price = stock_info['current_price']
            current_value = stock_info['current_value']
            difference = stock_info['difference']
            stock_ranking = stock_info['ranking']
            
            # Calculate quantity adjustment
            quantity_diff = 0
            
            # NEVER recommend buying more of stocks with ranking > 30
            # Stocks in stocks_to_keep should have ranking <= 30, but double-check
            if stock_ranking <= AMBBStrategyService.RANK_THRESHOLD:
                quantity_diff = int(difference / current_price)
            else:
                # Ranking > 30: don't recommend buying more
                quantity_diff = 0
            
            # CRITICAL: Always recalculate difference as target - current to ensure correct sign
            final_difference = target_value_per_stock - current_value
            
            stocks_to_balance.append({
                'ticker': ticker,
                'name': stock.name,
                'ranking': stock_ranking,
                'current_value': float(current_value),
                'target_value': float(target_value_per_stock),
                'difference': float(final_difference),  # Always target - current
                'quantity_to_adjust': quantity_diff,
                'current_price': float(current_price)
            })
        
        # Process stocks at target (no adjustment needed)
        for stock_info in stocks_at_target:
            ticker = stock_info['ticker']
            stock_data = stock_info['stock_data']
            stock = stock_info['stock']
            current_price = stock_info['current_price']
            current_value = stock_info['current_value']
            stock_ranking = stock_info['ranking']
            
            # CRITICAL: Always recalculate difference as target - current to ensure correct sign
            final_difference = target_value_per_stock - current_value
            
            stocks_to_balance.append({
                'ticker': ticker,
                'name': stock.name,
                'ranking': stock_ranking,
                'current_value': float(current_value),
                'target_value': float(target_value_per_stock),
                'difference': float(final_difference),  # Always target - current
                'quantity_to_adjust': 0,  # No adjustment needed
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
        
        # Verification of final recommendations
        verification_buy_value = Decimal('0')
        verification_sell_value = Decimal('0')
        
        # Calculate sell value from complete sales
        for sell in formatted_sells:
             # formatted_sells has 'current_value' which is likely cost basis in this system context,
             # but we want to check against "actual price" (market value).
             # Let's try to find the stock's current price from portfolio_stocks if possible
             ticker = sell['ticker']
             if ticker in portfolio_stocks:
                 stock_data = portfolio_stocks[ticker]
                 current_price = Decimal(str(stock_data['current_price']))
                 quantity = Decimal(str(sell['quantity']))
                 verification_sell_value += quantity * current_price
             else:
                 # Fallback if not found (should not happen)
                 verification_sell_value += Decimal(str(sell['current_value']))

        # Calculate buy/sell values from balance actions
        for balance in stocks_to_balance:
            qty = balance.get('quantity_to_adjust', 0)
            price = Decimal(str(balance['current_price']))
            if qty < 0:
                verification_sell_value += abs(qty) * price
            elif qty > 0:
                verification_buy_value += qty * price
                
        # Calculate buy value from new stocks
        for buy in formatted_buys:
            qty = buy['target_quantity']
            price = Decimal(str(buy['current_price']))
            verification_buy_value += qty * price
            
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
            'debug_info': debug_info,
            'verification': {
                'total_buy_value': float(verification_buy_value),
                'total_sell_value': float(verification_sell_value),
                'net_change': float(verification_buy_value - verification_sell_value)
            }
        }


