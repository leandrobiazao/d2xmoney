"""
Service for managing ticker mappings using Django ORM.
"""
import re
import time
import requests
import yfinance as yf
from typing import Dict, Optional, Tuple
from django.db import transaction
from django.db.utils import OperationalError
from .models import TickerMapping


class TickerMappingService:
    """Service for managing ticker mappings using Django ORM."""
    
    @staticmethod
    def get_mappings_file_path():
        """Legacy method - kept for backward compatibility."""
        # This method is no longer used but kept for compatibility
        pass
    
    @staticmethod
    def normalize_company_name(nome: str) -> str:
        """Normalize company name: remove @ and #, replace multiple spaces with single space, then strip and upper."""
        # Remove @ and # characters, normalize spaces, then uppercase
        cleaned = re.sub(r'[@#]', '', nome)
        return re.sub(r'\s+', ' ', cleaned.strip()).upper()
    
    @staticmethod
    def load_mappings() -> Dict[str, str]:
        """Load all ticker mappings from database."""
        mappings = TickerMapping.objects.all()
        return {mapping.company_name: mapping.ticker for mapping in mappings}
    
    @staticmethod
    def save_mappings(mappings: Dict[str, str]) -> None:
        """Save ticker mappings to database."""
        for company_name, ticker in mappings.items():
            normalized_name = TickerMappingService.normalize_company_name(company_name)
            TickerMapping.objects.update_or_create(
                company_name=normalized_name,
                defaults={'ticker': ticker.strip().upper()}
            )
    
    @staticmethod
    def get_ticker(nome: str) -> Optional[str]:
        """Get ticker for a company name."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        try:
            mapping = TickerMapping.objects.get(company_name=nome_normalizado)
            return mapping.ticker
        except TickerMapping.DoesNotExist:
            return None
    
    @staticmethod
    def set_ticker(nome: str, ticker: str) -> None:
        """Set ticker mapping for a company name with retry logic for SQLite locking."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        ticker_upper = ticker.strip().upper()
        
        max_retries = 5
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    TickerMapping.objects.update_or_create(
                        company_name=nome_normalizado,
                        defaults={'ticker': ticker_upper}
                    )
                    return
            except OperationalError as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    # Re-raise if it's not a lock error or we've exhausted retries
                    raise
    
    @staticmethod
    def has_mapping(nome: str) -> bool:
        """Check if a mapping exists for a company name."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        return TickerMapping.objects.filter(company_name=nome_normalizado).exists()
    
    @staticmethod
    def delete_mapping(nome: str) -> bool:
        """Delete a ticker mapping."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        deleted_count = TickerMapping.objects.filter(company_name=nome_normalizado).delete()[0]
        return deleted_count > 0


class TickerDiscoveryService:
    """Service for discovering tickers from company names."""
    
    @staticmethod
    def discover_ticker(company_name: str) -> Tuple[Optional[str], bool]:
        """
        Discover ticker for a company name using Yahoo Finance API.
        
        Returns:
            Tuple[Optional[str], bool]: (ticker, found)
            - ticker: The discovered ticker symbol (e.g., 'PETR4') or None
            - found: True if a valid ticker was found and verified
        """
        normalized_name = TickerMappingService.normalize_company_name(company_name)
        
        # Clean up company name for search
        # Remove common suffixes that might confuse the search
        search_term = normalized_name
        suffixes_to_remove = [
            ' S.A.', ' S/A', ' LTDA', ' PN', ' ON', ' PNB', ' PNA', 
            ' UNT', ' NM', ' N1', ' N2', ' EJ', ' ED', ' EDJ', ' ATZ'
        ]
        for suffix in suffixes_to_remove:
            search_term = search_term.replace(suffix, '')
            
        # Try searching with the original name first, then cleaned name if different
        search_attempts = [normalized_name]
        if search_term != normalized_name:
            search_attempts.append(search_term)
            
        for term in search_attempts:
            try:
                # Yahoo Finance Search API
                url = "https://query2.finance.yahoo.com/v1/finance/search"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                params = {
                    'q': term,
                    'quotesCount': 5,
                    'newsCount': 0,
                    'enableFuzzyQuery': True,
                    'quotesQueryId': 'tss_match_eq_us'
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'quotes' in data and data['quotes']:
                        # Look for Brazilian stocks (.SA)
                        for quote in data['quotes']:
                            symbol = quote.get('symbol', '')
                            # Prefer .SA stocks
                            if symbol.endswith('.SA'):
                                ticker = symbol.replace('.SA', '')
                                # Verify if it looks like a valid stock ticker (4 letters + number)
                                if re.match(r'^[A-Z]{4}\d{1,2}$', ticker):
                                    # Verify with yfinance
                                    if TickerDiscoveryService._verify_ticker(ticker):
                                        return ticker, True
                                    
                        # If no .SA found, check if any symbol looks like a Brazilian ticker but missing suffix
                        for quote in data['quotes']:
                            symbol = quote.get('symbol', '')
                            if re.match(r'^[A-Z]{4}\d{1,2}$', symbol):
                                # Try appending .SA and verify
                                if TickerDiscoveryService._verify_ticker(symbol):
                                    return symbol, True
            except Exception as e:
                print(f"Error searching for ticker for {term}: {e}")
                continue
                
        return None, False
    
    @staticmethod
    def _verify_ticker(ticker: str) -> bool:
        """Verify if a ticker is valid on B3 using yfinance."""
        try:
            # Append .SA for verification
            ticker_sa = f"{ticker}.SA"
            stock = yf.Ticker(ticker_sa)
            
            # Try to get info - lightweight check
            # If it has a current price or history, it's likely valid
            history = stock.history(period="1d")
            return not history.empty
        except Exception:
            return False
