"""
Service for managing stock catalog.
"""
from typing import List, Dict, Optional
from datetime import datetime
import time
import requests
import yfinance as yf
from django.db import models as django_models
from django.db import transaction
from django.db.utils import OperationalError
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
        Fetch stock price from Google Finance via yfinance library.
        
        For Brazilian stocks (B3 market), appends .SA suffix to ticker.
        Example: BERK34 -> BERK34.SA
        
        Uses stock.info as primary source (more reliable for current prices),
        with stock.history() as fallback.
        
        Args:
            ticker: Stock ticker symbol
            market: Financial market (default 'B3' for Brazilian stocks)
        
        Returns:
            Current stock price as float, or None if fetch fails
        """
        try:
            # For Brazilian stocks on B3, append .SA suffix
            yfinance_ticker = f"{ticker}.SA" if market == 'B3' else ticker
            
            stock = yf.Ticker(yfinance_ticker)
            
            # Try to get price from stock.info first (more reliable for current price)
            try:
                info = stock.info
                # Try different price fields in order of preference
                price_fields = ['regularMarketPrice', 'currentPrice', 'previousClose', 'regularMarketPreviousClose']
                for field in price_fields:
                    if field in info and info[field] is not None:
                        price = float(info[field])
                        if price > 0:
                            return price
            except:
                pass  # If info fails, try history as fallback
            
            # Fallback: Fetch last day's data from history
            data = stock.history(period="1d")
            
            if not data.empty and 'Close' in data.columns:
                # Return the last closing price
                price = float(data['Close'].iloc[-1])
                return price
            
            return None
        except Exception as e:
            print(f"Error fetching price for {ticker} (market: {market}): {e}")
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
    
    @staticmethod
    def fetch_stock_info_from_yfinance(ticker: str, market: str = 'B3') -> Optional[Dict]:
        """
        Fetch stock information from yFinance.
        
        Args:
            ticker: Stock ticker symbol
            market: Financial market (default 'B3' for Brazilian stocks)
        
        Returns:
            Dict with stock info: {name, cnpj, price, financial_market, stock_class} or None
        """
        try:
            # For Brazilian stocks on B3, append .SA suffix
            yfinance_ticker = f"{ticker}.SA" if market == 'B3' else ticker
            
            stock_info = yf.Ticker(yfinance_ticker)
            info = stock_info.info
            
            if not info or 'symbol' not in info:
                return None
            
            # Extract stock information
            name = info.get('longName') or info.get('shortName') or ticker
            price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
            
            # Determine stock class from ticker
            stock_class = 'ON'
            if ticker.endswith('3'):
                stock_class = 'ON'
            elif ticker.endswith('4'):
                stock_class = 'PN'
            elif 'ETF' in name.upper() or 'FUNDO' in name.upper():
                stock_class = 'ETF'
            elif ticker.endswith('34') or 'BDR' in name.upper():
                stock_class = 'BDR'
            
            return {
                'name': name,
                'cnpj': None,  # yFinance doesn't provide CNPJ
                'price': float(price) if price else 0.0,
                'financial_market': market,
                'stock_class': stock_class
            }
        except Exception as e:
            print(f"Error fetching stock info for {ticker} (market: {market}): {e}")
            return None
    
    @staticmethod
    def sync_portfolio_stocks_to_catalog(user_id: Optional[str] = None) -> Dict:
        """
        Sync stocks from portfolio positions to the stock catalog.
        Fetches missing stocks from yFinance and adds them to the catalog.
        
        Args:
            user_id: Optional user_id to sync stocks for specific user only
        
        Returns:
            Dict with sync results: {created, updated, errors, total_processed}
        """
        from portfolio_operations.models import PortfolioPosition
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': [],
            'total_processed': 0
        }
        
        # Get all unique tickers from portfolio positions
        if user_id:
            positions = PortfolioPosition.objects.filter(user_id=user_id)
        else:
            positions = PortfolioPosition.objects.all()
        
        tickers = positions.values_list('ticker', flat=True).distinct()
        results['total_processed'] = len(tickers)
        
        for ticker in tickers:
            try:
                # Check if stock already exists in catalog
                stock = StockService.get_stock_by_ticker(ticker)
                
                if stock:
                    # Stock exists, just update price if needed
                    price = StockService.fetch_price_from_google_finance(
                        ticker,
                        stock.financial_market
                    )
                    if price:
                        stock.current_price = price
                        stock.last_updated = timezone.now()
                        stock.save()
                        results['updated'] += 1
                else:
                    # Stock doesn't exist, fetch info from yFinance and create
                    # Try B3 first (most common for Brazilian stocks)
                    stock_info = StockService.fetch_stock_info_from_yfinance(ticker, 'B3')
                    
                    # If B3 fails, try other markets
                    if not stock_info:
                        for market in ['Nasdaq', 'NYExchange']:
                            stock_info = StockService.fetch_stock_info_from_yfinance(ticker, market)
                            if stock_info:
                                break
                    
                    if stock_info:
                        # Create new stock in catalog
                        stock = Stock.objects.create(
                            ticker=ticker,
                            name=stock_info['name'],
                            cnpj=stock_info.get('cnpj'),
                            financial_market=stock_info['financial_market'],
                            stock_class=stock_info['stock_class'],
                            current_price=stock_info['price'],
                            is_active=True
                        )
                        results['created'] += 1
                    else:
                        # Couldn't fetch info, create with minimal data
                        stock = Stock.objects.create(
                            ticker=ticker,
                            name=ticker,  # Use ticker as name if we can't fetch
                            financial_market='B3',  # Default to B3
                            stock_class='ON',  # Default to ON
                            current_price=0.0,
                            is_active=True
                        )
                        results['created'] += 1
                        results['errors'].append(f"{ticker}: Could not fetch info from yFinance, created with minimal data")
            except Exception as e:
                error_msg = f"{ticker}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"Error syncing stock {ticker}: {e}")
        
        return results
    
    @staticmethod
    def fetch_and_create_stock(ticker: str, investment_type_code: str = 'RENDA_VARIAVEL_REAIS') -> Optional[Stock]:
        """
        Fetch stock information from yFinance and create it in the catalog.
        Uses retry logic to handle SQLite database locking.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'BRSR6')
            investment_type_code: Investment type code (default 'RENDA_VARIAVEL_REAIS')
        
        Returns:
            Created Stock object or None if creation fails
        """
        # Check if stock already exists
        existing_stock = StockService.get_stock_by_ticker(ticker)
        if existing_stock:
            return existing_stock
        
        # Try to fetch from yFinance (B3 market first)
        stock_info = StockService.fetch_stock_info_from_yfinance(ticker, 'B3')
        
        # If B3 fails, try other markets
        if not stock_info:
            for market in ['Nasdaq', 'NYExchange']:
                stock_info = StockService.fetch_stock_info_from_yfinance(ticker, market)
                if stock_info:
                    break
        
        # Get investment type
        investment_type = None
        try:
            investment_type = InvestmentType.objects.get(code=investment_type_code, is_active=True)
        except InvestmentType.DoesNotExist:
            # Try alternative names for backward compatibility
            from django.db.models import Q
            try:
                investment_type = InvestmentType.objects.get(
                    Q(name__icontains='Renda Variável em Reais') | 
                    Q(name__icontains='Ações em Reais'), 
                    is_active=True
                )
            except InvestmentType.DoesNotExist:
                pass
        
        # Create stock with retry logic for SQLite locking
        max_retries = 5
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    if stock_info:
                        # Create stock with fetched info
                        stock = Stock.objects.create(
                            ticker=ticker,
                            name=stock_info['name'],
                            cnpj=stock_info.get('cnpj'),
                            financial_market=stock_info['financial_market'],
                            stock_class=stock_info['stock_class'],
                            current_price=stock_info['price'],
                            investment_type=investment_type,
                            is_active=True
                        )
                    else:
                        # Create with minimal data if yFinance fetch fails
                        stock = Stock.objects.create(
                            ticker=ticker,
                            name=ticker,  # Use ticker as name
                            financial_market='B3',  # Default to B3
                            stock_class='ON',  # Default to ON
                            current_price=0.0,
                            investment_type=investment_type,
                            is_active=True
                        )
                    return stock
            except OperationalError as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    # Re-raise if it's not a lock error or we've exhausted retries
                    raise
            except Exception as e:
                # For other errors, log and return None
                print(f"Error creating stock {ticker}: {e}")
                return None
        
        return None

