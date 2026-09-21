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
    RANK_THRESHOLD = 20  # MDIV keep/sell cutoff (never complete-sell rank <= 20)
    EQUAL_WEIGHT_DIVISOR = 10  # Buy/top-up target = RV Reais meta / 10
    SALES_LIMIT = Decimal('19000.00')  # 19,000 Reais per month
    MDIV_BUY_RANK_LIMIT = 10  # New names and equal-weight top-up
    MDIV_BUY_STRATEGY = 'MDIV'

    @staticmethod
    def _filter_reais_stocks_from_strategy(
        strategy_stocks: List[Dict],
        acoes_reais_type: InvestmentType,
    ) -> tuple:
        """
        Filter Clube do Valor strategy rows to active Ações em Reais catalog entries.
        Returns (filtered list, ticker -> stock_data map).
        """
        from stocks.services import StockService

        reais_stocks: List[Dict] = []
        ticker_map: Dict[str, Dict] = {}
        for stock_data in strategy_stocks:
            ticker = stock_data['codigo']
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                if stock.investment_type == acoes_reais_type:
                    reais_stocks.append(stock_data)
                    ticker_map[ticker] = stock_data
            except Stock.DoesNotExist:
                try:
                    fetched_stock = StockService.fetch_and_create_stock(
                        ticker, 'RENDA_VARIAVEL_REAIS'
                    )
                    if fetched_stock and fetched_stock.investment_type == acoes_reais_type:
                        reais_stocks.append(stock_data)
                        ticker_map[ticker] = stock_data
                except Exception as e:
                    print(f"Could not fetch {ticker} from yFinance: {e}")
        return reais_stocks, ticker_map

    @staticmethod
    def _apply_rank_priority_buy_cap(
        buy_budget: Decimal,
        strategic: Decimal,
        stocks_to_balance: List[Dict],
        formatted_buys: List[Dict],
    ) -> None:
        """
        When recommended buys exceed buy_budget, water-fill so ending position values
        among MDIV names that still need a buy are as even as possible (whole shares),
        capped at the strategic 1/10 target. Empty or small holdings get more of the
        cash; names already close to target get little. Total spend never exceeds buy_budget.
        """
        purchases = []
        for i, item in enumerate(stocks_to_balance):
            orig_qty = int(item.get('quantity_to_adjust') or 0)
            if orig_qty <= 0:
                continue
            price = Decimal(str(item.get('current_price', 0)))
            if price <= 0:
                continue
            cv = Decimal(str(item.get('current_value', 0)))
            headroom = max(Decimal('0'), strategic - cv)
            requested = min(Decimal(str(orig_qty)) * price, headroom)
            if requested <= 0:
                continue
            purchases.append({
                'index': i,
                'ticker': item.get('ticker', ''),
                'ranking': int(item.get('ranking', 999)),
                'price': price,
                'headroom': headroom,
                'requested': requested,
                'cv': cv,
                'end': cv,
                'qty': 0,
                'spent': Decimal('0'),
            })

        remaining = buy_budget
        while remaining > Decimal('0.01') and purchases:
            candidates = []
            for p in purchases:
                next_spent = p['spent'] + p['price']
                if remaining < p['price']:
                    continue
                if next_spent > p['requested'] or next_spent > p['headroom']:
                    continue
                candidates.append(p)
            if not candidates:
                break
            chosen = min(candidates, key=lambda p: (p['end'], p['ranking'], p['ticker']))
            chosen['qty'] += 1
            chosen['spent'] += chosen['price']
            chosen['end'] += chosen['price']
            remaining -= chosen['price']

        formatted_by_ticker = {fb['ticker']: fb for fb in formatted_buys}
        for p in purchases:
            item = stocks_to_balance[p['index']]
            cv = p['cv']
            item['target_value'] = float(strategic)
            item['difference'] = float(strategic - cv)
            item['quantity_to_adjust'] = p['qty']
            ticker = p['ticker']
            if ticker in formatted_by_ticker:
                formatted_by_ticker[ticker]['target_value'] = float(strategic)
                formatted_by_ticker[ticker]['target_quantity'] = p['qty']
    
    @staticmethod
    def generate_rebalancing_recommendations(user: User, remaining_monthly_limit: Decimal = None) -> Dict:
        """
        Generate MDIV rebalancing recommendations for "Ações em Reais" stocks only.
        
        Rules:
        1. Filter to only "Ações em Reais" investment type stocks
        2. Target: Maximum 20 stocks total in final allocation
        3. Keep existing portfolio stocks if they are in MDIV ranking AND rank <= 20
        4. Sell priority:
           - First: Stocks NOT in MDIV ranking (includes leftover AMBB 2.0 names)
           - Second: Stocks with MDIV rank > 20 (sell highest rank/worst first)
        5. Sales limit: Maximum 19,000 Reais per month (including partial sales from rebalancing)
        6. Buy: MDIV ranks 1-10 not already in portfolio
           - Prioritize lower MDIV rankings (best first)
           - Maximum 20 stocks total in final portfolio
        7. Equal nominal slice for MDIV ranks 1-10: target per name =
           («Meta» para Renda Variável em Reais no cartão de alocação = tipo % × valor total carteira)
           divided by EQUAL_WEIGHT_DIVISOR (10).
        8. MDIV ranks 11-20 already held: keep, no additional buys, no complete sell.
        9. Buy-budget cap: water-fill so MDIV 1-10 ending weights are as even as possible
           (not equal ticket sizes). Names already near the 1/10 slot get smaller buys.
        
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
        
        # MDIV ranking drives keep, sell, and buy
        mdiv_stocks_raw = ClubeDoValorService.get_current_stocks(
            AMBBStrategyService.MDIV_BUY_STRATEGY
        ) or []
        mdiv_reais_stocks, current_mdiv_tickers = AMBBStrategyService._filter_reais_stocks_from_strategy(
            mdiv_stocks_raw, acoes_reais_type
        )
        
        # Get user's portfolio positions
        positions = PortfolioPosition.objects.filter(user_id=str(user.id))
        portfolio_tickers = {pos.ticker: pos for pos in positions if pos.quantidade > 0}
        
        # Refresh current prices from yfinance for all tickers involved (portfolio + MDIV candidates)
        # so recommended quantities use up-to-date prices
        all_tickers = (
            set(portfolio_tickers.keys())
            | {s['codigo'] for s in mdiv_reais_stocks}
        )
        from stocks.services import StockService
        StockService.refresh_prices_for_tickers(all_tickers, 'B3')
        
        # Filter portfolio stocks to only "Ações em Reais" type
        portfolio_stocks = {}
        for ticker in portfolio_tickers.keys():
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                if stock.investment_type == acoes_reais_type:
                    position = portfolio_tickers[ticker]
                    # Use current market value (quantity × current_price) for rebalancing
                    # Fall back to valor_total_investido if current_price is not available
                    if stock.current_price and stock.current_price > 0:
                        current_value = Decimal(str(position.quantidade)) * stock.current_price
                    else:
                        current_value = Decimal(str(position.valor_total_investido))
                    
                    portfolio_stocks[ticker] = {
                        'stock': stock,
                        'position': position,
                        'current_value': current_value,
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
        
        # Identify stocks to keep (in MDIV with rank <= 20)
        stocks_to_keep = {}
        for ticker, stock_data in portfolio_stocks.items():
            if ticker in current_mdiv_tickers:
                ranking = current_mdiv_tickers[ticker].get('ranking', 999)
                if ranking <= AMBBStrategyService.RANK_THRESHOLD:
                    stocks_to_keep[ticker] = {
                        'stock_data': stock_data,
                        'ranking': ranking,
                        'mdiv_data': current_mdiv_tickers[ticker]
                    }
        
        # Sell bad stocks (not in MDIV or ranking > 20) completely first, then partially if limit allows.
        # Remaining limit may trim MDIV ranks 1-10 that are above the equal-weight target.
        
        # Use ALL remaining monthly limit to sell bad stocks completely
        # We prioritize selling bad stocks completely over rebalancing good stocks
        # If remaining_monthly_limit is None, use the full limit (19,000)
        if remaining_monthly_limit is None:
            remaining_monthly_limit = AMBBStrategyService.SALES_LIMIT
        remaining_limit_for_complete_sales = remaining_monthly_limit
        
        # Identify stocks to sell (prioritized)
        # Keep stocks with MDIV ranking <= 20
        # Sell stocks not in MDIV, then MDIV ranking > 20 (worst first)
        stocks_to_sell_list = []
        
        # Priority 1: Stocks NOT in MDIV ranking (no ranking = worst, sell first)
        stocks_not_in_ranking = []
        for ticker, stock_data in portfolio_stocks.items():
            if ticker not in current_mdiv_tickers and ticker not in stocks_to_keep:
                stocks_not_in_ranking.append({
                    'ticker': ticker,
                    'name': stock_data['stock'].name,
                    'current_value': stock_data['current_value'],
                    'quantity': stock_data['position'].quantidade,
                    'current_price': float(stock_data['current_price']),
                    'ranking': 9999,
                    'priority': 1,
                    'reason': 'Not in MDIV ranking'
                })
        
        # Priority 2: Stocks with MDIV rank > 20 (sort by highest rank/worst first)
        rank_over_threshold = []
        for ticker, stock_data in portfolio_stocks.items():
            if ticker in stocks_to_keep:
                continue
            
            if ticker in current_mdiv_tickers:
                ranking = current_mdiv_tickers[ticker].get('ranking', 999)
                if ranking > AMBBStrategyService.RANK_THRESHOLD:
                    rank_over_threshold.append({
                        'ticker': ticker,
                        'name': stock_data['stock'].name,
                        'current_value': stock_data['current_value'],
                        'quantity': stock_data['position'].quantidade,
                        'current_price': float(stock_data['current_price']),
                        'ranking': ranking,
                        'priority': 2,
                        'reason': f'Rank {ranking} > {AMBBStrategyService.RANK_THRESHOLD}'
                    })
        
        rank_over_threshold.sort(key=lambda x: x['ranking'], reverse=True)
        stocks_to_sell_list = stocks_not_in_ranking + rank_over_threshold
        
        # Apply ALL available limit to sell bad stocks COMPLETELY first
        # Priority order:
        # 1. First: Stocks NOT in MDIV ranking (priority 1, ranking 9999)
        # 2. Second: Stocks with MDIV ranking > 20, worst rank first (priority 2)
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
        
        # Get MDIV buy candidates sorted by ranking (lower = better)
        all_mdiv_buy_sorted = sorted(mdiv_reais_stocks, key=lambda x: x.get('ranking', 999))

        # Identify stocks to buy:
        # 1. Must be in MDIV ranking with rank <= MDIV_BUY_RANK_LIMIT (top 10)
        # 2. Must NOT already be in the portfolio
        # 3. Prioritize lower MDIV rankings first
        # 4. Maximum 20 stocks total in final portfolio
        stocks_to_buy = []
        available_slots = AMBBStrategyService.MAX_STOCKS - len(final_stock_tickers)

        # Only recommend buying if we have available slots
        if available_slots > 0:
            for stock_data in all_mdiv_buy_sorted:
                if len(stocks_to_buy) >= available_slots:
                    break  # We've filled all available slots

                ticker = stock_data['codigo']
                ranking = stock_data.get('ranking', 999)

                if ticker in portfolio_stocks:
                    continue  # Already in portfolio, skip

                if ranking > AMBBStrategyService.MDIV_BUY_RANK_LIMIT:
                    continue  # Only MDIV top 10

                try:
                    stock = Stock.objects.get(ticker=ticker, is_active=True)

                    if stock.investment_type != acoes_reais_type:
                        continue

                    final_stock_tickers.add(ticker)
                    stocks_to_buy.append({
                        'ticker': ticker,
                        'name': stock_data['nome'],
                        'ranking': ranking,
                        'current_price': float(stock.current_price) if stock.current_price > 0 else 0,
                        'buy_source': AMBBStrategyService.MDIV_BUY_STRATEGY,
                    })

                except Stock.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"Error processing MDIV buy candidate {ticker} (ranking {ranking}): {e}")
                    continue
        
        # Matches allocation panel «Meta» (getTargetTypeValue) for Renda Variável em Reais —
        # same as acoes_reais_target_total (= total portfolio × type target %).
        divisor = Decimal(AMBBStrategyService.EQUAL_WEIGHT_DIVISOR)
        final_stock_count = len(final_stock_tickers)
        if acoes_reais_target_total > Decimal('0'):
            target_value_per_stock = acoes_reais_target_total / divisor
        else:
            target_value_per_stock = Decimal('0')
        
        # Generate balance actions for stocks to keep and new buys
        stocks_to_balance = []
        # Tracks limit remaining after complete sales (updated by partial bad/good sells)
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
            eligible_for_top_up = stock_ranking <= AMBBStrategyService.MDIV_BUY_RANK_LIMIT

            if not eligible_for_top_up:
                # MDIV ranks 11-20: hold as-is (no buy, no complete sell)
                stocks_to_balance.append({
                    'ticker': ticker,
                    'name': stock.name,
                    'ranking': stock_ranking,
                    'current_value': float(current_value),
                    'target_value': float(current_value),
                    'difference': 0.0,
                    'quantity_to_adjust': 0,
                    'current_price': float(current_price)
                })
                continue
            
            if difference < Decimal('0'):  # Need to sell (current value > target)
                # Partial sell for ranks 1-10 is applied after bad-stock sales (see good_above_target pass)
                quantity_diff = 0
            elif difference > Decimal('0.01'):  # Need to buy
                quantity_diff = int(difference / current_price)
            else:
                quantity_diff = 0
            
            final_difference = target_value_per_stock - current_value
            
            stocks_to_balance.append({
                'ticker': ticker,
                'name': stock.name,
                'ranking': stock_ranking,
                'current_value': float(current_value),
                'target_value': float(target_value_per_stock),
                'difference': float(final_difference),
                'quantity_to_adjust': quantity_diff,
                'current_price': float(current_price)
            })
        
        # For stocks that couldn't be sold COMPLETELY due to 19K limit - try to sell them PARTIALLY
        # These stocks are bad (not in MDIV or ranking > 20) and should be sold, even if partially
        # IMPORTANT: Process in the SAME order as complete sales:
        # 1. First: stocks not in ranking (priority 1)
        # 2. Second: stocks with highest ranking (priority 2, worst first)
        
        for sell_item in stocks_to_sell_list:
            if sell_item not in final_stocks_to_sell:
                # Exit name that did not fit as a complete sale — use leftover limit
                # even if current value is below the 1/10 strategic slot.
                ticker = sell_item['ticker']
                if ticker in portfolio_stocks:
                    stock_data = portfolio_stocks[ticker]
                    current_value = stock_data['current_value']
                    stock = stock_data['stock']
                    current_price = stock.current_price if stock.current_price > 0 else Decimal('1')
                    quantity_diff = 0

                    if remaining_limit_after_complete_sales > Decimal('0.01') and current_price > 0:
                        max_sale_value = min(remaining_limit_after_complete_sales, current_value)
                        quantity_to_sell = int(max_sale_value / current_price)
                        if quantity_to_sell > 0:
                            partial_sale_value = Decimal(str(quantity_to_sell)) * current_price
                            quantity_diff = -quantity_to_sell
                            remaining_limit_after_complete_sales -= partial_sale_value

                    ranking = sell_item.get('ranking', 999)
                    if ticker in current_mdiv_tickers:
                        ranking = current_mdiv_tickers[ticker].get('ranking', ranking)

                    stocks_to_balance.append({
                        'ticker': ticker,
                        'name': stock.name,
                        'ranking': ranking,
                        'current_value': float(current_value),
                        'target_value': 0.0,
                        'difference': float(-current_value),
                        'quantity_to_adjust': quantity_diff,
                        'current_price': float(current_price)
                    })
        
        # Use remaining sales limit to trim MDIV ranks 1-10 above equal-weight target.
        good_above_target = [
            item for item in stocks_to_balance
            if item.get('ticker') in stocks_to_keep
            and int(item.get('ranking', 999)) <= AMBBStrategyService.MDIV_BUY_RANK_LIMIT
            and Decimal(str(item.get('difference', 0))) < Decimal('-0.01')
            and int(item.get('quantity_to_adjust') or 0) == 0
        ]
        good_above_target.sort(key=lambda x: (int(x.get('ranking', 999)), x.get('ticker', '')))
        for item in good_above_target:
            if remaining_limit_after_complete_sales <= Decimal('0.01'):
                break
            current_price = Decimal(str(item.get('current_price', 0)))
            if current_price <= 0:
                continue
            current_value = Decimal(str(item.get('current_value', 0)))
            over_target = max(Decimal('0'), current_value - target_value_per_stock)
            if over_target <= Decimal('0.01'):
                continue
            qty_needed = int(over_target / current_price)
            if qty_needed <= 0:
                continue
            sale_value_needed = Decimal(str(qty_needed)) * current_price
            max_sale_value = min(sale_value_needed, remaining_limit_after_complete_sales, current_value)
            qty_to_sell = int(max_sale_value / current_price)
            if qty_to_sell <= 0:
                continue
            item['quantity_to_adjust'] = -qty_to_sell
            remaining_limit_after_complete_sales -= Decimal(str(qty_to_sell)) * current_price
        
        # For new stocks to buy (MDIV ranks 1-10 only)
        for buy_item in stocks_to_buy:
            ranking = buy_item.get('ranking', 999)
            if ranking > AMBBStrategyService.MDIV_BUY_RANK_LIMIT:
                continue
            
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
            in_mdiv = ticker in current_mdiv_tickers
            in_stocks_to_keep = ticker in stocks_to_keep
            in_stocks_to_sell_list = any(s['ticker'] == ticker for s in stocks_to_sell_list)
            in_final_stocks_to_sell = any(s['ticker'] == ticker for s in final_stocks_to_sell)
            ranking = current_mdiv_tickers.get(ticker, {}).get('ranking', None) if in_mdiv else None
            current_value = portfolio_stocks.get(ticker, {}).get('current_value', Decimal('0')) if in_portfolio else Decimal('0')
            
            target_stocks_info.append({
                'ticker': ticker,
                'in_portfolio': in_portfolio,
                'in_mdiv': in_mdiv,
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
            'top_10_mdiv_rankings': [
                {
                    'ticker': s['codigo'],
                    'ranking': s.get('ranking', 999),
                    'in_portfolio': s['codigo'] in portfolio_stocks,
                    'in_catalog': Stock.objects.filter(ticker=s['codigo'], is_active=True).exists()
                }
                for s in sorted(mdiv_reais_stocks, key=lambda x: x.get('ranking', 999))[:10]
            ],
            'mdiv_buy_rank_limit': AMBBStrategyService.MDIV_BUY_RANK_LIMIT,
            'top_mdiv_buy_candidates': [
                {
                    'ticker': s['codigo'],
                    'ranking': s.get('ranking', 999),
                    'in_portfolio': s['codigo'] in portfolio_stocks,
                    'in_catalog': Stock.objects.filter(ticker=s['codigo'], is_active=True).exists(),
                    'eligible_for_buy': s.get('ranking', 999) <= AMBBStrategyService.MDIV_BUY_RANK_LIMIT
                    and s['codigo'] not in portfolio_stocks,
                }
                for s in all_mdiv_buy_sorted[:10]
            ],
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
        
        # Cap buy recommendations by type-level buy budget (so total buys <= target - value_after_sales)
        current_acoes_reais_value = sum(
            portfolio_stocks[ticker]['current_value']
            for ticker in portfolio_stocks
        )
        value_after_sales = current_acoes_reais_value - total_all_sales
        buy_budget = max(Decimal('0'), acoes_reais_target_total - value_after_sales)
        
        # Sum buy exposure only once: stocks_to_balance already includes new names and rebalance buys.
        # (formatted_buys mirrors new stocks — adding both double-counted and inflated buy_budget scaling.)
        total_recommended_buys = Decimal('0')
        for balance_item in stocks_to_balance:
            qty = balance_item.get('quantity_to_adjust', 0) or 0
            if qty > 0:
                price = Decimal(str(balance_item['current_price'])) if balance_item.get('current_price') else Decimal('0')
                total_recommended_buys += Decimal(str(qty)) * price
        
        if buy_budget <= 0:
            # Zero out all buys
            formatted_buys.clear()
            for balance_item in stocks_to_balance:
                cv = balance_item.get('current_value', 0)
                qty = balance_item.get('quantity_to_adjust', 0) or 0
                is_new = cv is None or (isinstance(cv, (int, float)) and cv <= 0.01)
                if is_new or qty > 0:
                    balance_item['quantity_to_adjust'] = 0
                    if is_new:
                        balance_item['target_value'] = 0.0
                        balance_item['difference'] = 0.0
        elif total_recommended_buys > buy_budget and buy_budget > 0:
            # Scale quantities only; Valor Alvo / Dif. stay strategic. Water-fill toward even ending weights.
            AMBBStrategyService._apply_rank_priority_buy_cap(
                buy_budget,
                target_value_per_stock,
                stocks_to_balance,
                formatted_buys,
            )
        
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


