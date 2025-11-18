"""
Service for managing stock catalog.
"""
from typing import List, Dict, Optional
from datetime import datetime
import requests
from django.db import models as django_models
from django.utils import timezone
from .models import Stock
from configuration.models import InvestmentType


class StockService:
    """Service for managing stock catalog."""
    
    @staticmethod
    def get_stock_by_ticker(ticker: str) -> Optional[Stock]:
        """Get stock by ticker."""
        try:
            return Stock.objects.get(ticker=ticker, is_active=True)
        except Stock.DoesNotExist:
            return None
    
    @staticmethod
    def search_stocks(query: str, limit: int = 50) -> List[Stock]:
        """Search stocks by ticker or name."""
        queryset = Stock.objects.filter(is_active=True)
        if query:
            queryset = queryset.filter(
                django_models.Q(ticker__icontains=query) |
                django_models.Q(name__icontains=query)
            )
        return list(queryset[:limit])
    
    @staticmethod
    def update_stock_price(ticker: str, price: float) -> Optional[Stock]:
        """Update stock price."""
        try:
            stock = Stock.objects.get(ticker=ticker)
            stock.current_price = price
            stock.last_updated = timezone.now()
            stock.save()
            return stock
        except Stock.DoesNotExist:
            return None
    
    @staticmethod
    def fetch_price_from_google_finance(ticker: str, market: str = 'B3') -> Optional[float]:
        """
        Fetch stock price from Google Finance.
        
        Note: Google Finance API is not officially available.
        This is a placeholder that would need to be implemented with
        an actual finance API (e.g., Alpha Vantage, Yahoo Finance, etc.)
        """
        # Placeholder implementation
        # In production, use a proper finance API
        try:
            # Example: Using yfinance or similar library
            # import yfinance as yf
            # stock = yf.Ticker(f"{ticker}.SA" if market == 'B3' else ticker)
            # data = stock.history(period="1d")
            # if not data.empty:
            #     return float(data['Close'].iloc[-1])
            return None
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
    
    @staticmethod
    def update_prices_daily():
        """Update prices for all active stocks."""
        stocks = Stock.objects.filter(is_active=True)
        updated = 0
        errors = []
        
        for stock in stocks:
            try:
                price = StockService.fetch_price_from_google_finance(
                    stock.ticker,
                    stock.financial_market
                )
                if price:
                    stock.current_price = price
                    stock.last_updated = timezone.now()
                    stock.save()
                    updated += 1
            except Exception as e:
                errors.append(f"{stock.ticker}: {str(e)}")
        
        return {
            'updated': updated,
            'total': stocks.count(),
            'errors': errors
        }

