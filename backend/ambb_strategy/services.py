"""
Service for AMBB strategy implementation.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from users.models import User
from portfolio_operations.models import PortfolioPosition
from stocks.models import Stock
from clubedovalor.services import ClubeDoValorService


class AMBBStrategyService:
    """Service for implementing AMBB programmable strategy."""
    
    MAX_STOCKS = 20
    RANK_THRESHOLD = 30
    
    @staticmethod
    def generate_rebalancing_recommendations(user: User) -> Dict:
        """
        Generate AMBB rebalancing recommendations based on programmable rules.
        
        Rules:
        1. Select up to 20 stocks from current AMBB recommendations
        2. Recommend to sell stocks not in newest AMBB table AND over rank 30
        3. Stocks in portfolio AND under rank 30 in current AMBB can be used to balance
        4. Stocks completely needed to be replaced by lowest ranking stock not in portfolio
        5. Equal value balancing using market values
        
        Returns:
        {
            'stocks_to_sell': [...],
            'stocks_to_buy': [...],
            'stocks_to_balance': [...],
            'stocks_to_replace': [...]
        }
        """
        # Get current AMBB recommendations
        current_stocks = ClubeDoValorService.get_current_stocks()
        current_ambb_tickers = {stock['codigo']: stock for stock in current_stocks}
        
        # Get user's portfolio positions
        positions = PortfolioPosition.objects.filter(user_id=str(user.id))
        portfolio_tickers = {pos.ticker: pos for pos in positions if pos.quantidade > 0}
        
        # Get stock prices from catalog
        portfolio_stocks = {}
        for ticker in portfolio_tickers.keys():
            try:
                stock = Stock.objects.get(ticker=ticker, is_active=True)
                portfolio_stocks[ticker] = {
                    'stock': stock,
                    'position': portfolio_tickers[ticker],
                    'current_value': Decimal(str(portfolio_tickers[ticker].valor_total_investido))
                }
            except Stock.DoesNotExist:
                pass
        
        # Rule 1: Select up to 20 stocks from current AMBB
        top_20_ambb = current_stocks[:AMBBStrategyService.MAX_STOCKS]
        target_tickers = {stock['codigo']: stock for stock in top_20_ambb}
        
        # Rule 2: Identify stocks to sell (not in AMBB AND over rank 30)
        stocks_to_sell = []
        for ticker, stock_data in portfolio_stocks.items():
            if ticker not in current_ambb_tickers:
                # Check if we have historical rank > 30
                # For now, if not in current AMBB, recommend sell
                stocks_to_sell.append({
                    'ticker': ticker,
                    'name': stock_data['stock'].name,
                    'current_value': float(stock_data['current_value']),
                    'quantity': stock_data['position'].quantidade,
                    'reason': 'Not in current AMBB recommendations'
                })
        
        # Rule 3: Stocks in portfolio AND under rank 30 can be used to balance
        stocks_to_balance = []
        for stock_data in current_stocks:
            ticker = stock_data['codigo']
            ranking = stock_data.get('ranking', 999)
            if ticker in portfolio_stocks and ranking <= AMBBStrategyService.RANK_THRESHOLD:
                stocks_to_balance.append({
                    'ticker': ticker,
                    'name': stock_data['nome'],
                    'ranking': ranking,
                    'current_value': float(portfolio_stocks[ticker]['current_value']),
                    'quantity': portfolio_stocks[ticker]['position'].quantidade
                })
        
        # Rule 4: Stocks to replace and buy
        stocks_to_buy = []
        stocks_to_replace = []
        
        # Calculate target equal value per stock
        total_target_value = sum(
            float(portfolio_stocks[ticker]['current_value'])
            for ticker in portfolio_stocks.keys()
            if ticker in target_tickers
        )
        target_value_per_stock = (
            total_target_value / len(target_tickers)
            if target_tickers else 0
        )
        
        # Identify stocks needed
        for stock_data in top_20_ambb:
            ticker = stock_data['codigo']
            ranking = stock_data.get('ranking', 999)
            
            if ticker not in portfolio_stocks:
                # Need to buy this stock
                try:
                    stock = Stock.objects.get(ticker=ticker, is_active=True)
                    current_price = stock.current_price
                    target_quantity = int(target_value_per_stock / current_price) if current_price > 0 else 0
                    
                    stocks_to_buy.append({
                        'ticker': ticker,
                        'name': stock_data['nome'],
                        'ranking': ranking,
                        'target_value': target_value_per_stock,
                        'target_quantity': target_quantity,
                        'current_price': float(current_price)
                    })
                except Stock.DoesNotExist:
                    pass
        
        # Rule 5: Equal value balancing
        # Rebalance existing positions to equal values
        for ticker, stock_data in portfolio_stocks.items():
            if ticker in target_tickers:
                current_value = float(stock_data['current_value'])
                difference = target_value_per_stock - current_value
                
                if abs(difference) > 0.01:  # Significant difference
                    stock = stock_data['stock']
                    quantity_diff = int(difference / stock.current_price) if stock.current_price > 0 else 0
                    
                    stocks_to_balance.append({
                        'ticker': ticker,
                        'name': stock.name,
                        'current_value': current_value,
                        'target_value': target_value_per_stock,
                        'difference': difference,
                        'quantity_to_adjust': quantity_diff
                    })
        
        return {
            'stocks_to_sell': stocks_to_sell,
            'stocks_to_buy': stocks_to_buy,
            'stocks_to_balance': stocks_to_balance,
            'stocks_to_replace': stocks_to_replace,
            'target_stocks_count': len(target_tickers),
            'current_portfolio_count': len(portfolio_stocks)
        }


