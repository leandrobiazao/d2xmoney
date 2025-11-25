"""
Service for managing crypto operations and positions.
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import yfinance as yf
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from .models import CryptoCurrency, CryptoOperation, CryptoPosition


class CryptoService:
    """Service for managing crypto operations and positions."""
    
    @staticmethod
    @transaction.atomic
    def update_position_from_operation(operation: CryptoOperation) -> CryptoPosition:
        """Update or create position based on operation."""
        user_id = operation.user_id
        crypto_currency = operation.crypto_currency
        
        # Get or create position
        position, created = CryptoPosition.objects.get_or_create(
            user_id=user_id,
            crypto_currency=crypto_currency,
            defaults={
                'quantity': Decimal('0'),
                'average_price': Decimal('0'),
                'broker': operation.broker
            }
        )
        
        if operation.operation_type == 'BUY':
            # Add to position
            total_quantity = position.quantity + operation.quantity
            total_invested = (position.quantity * position.average_price) + (operation.quantity * operation.price)
            
            if total_quantity > 0:
                position.average_price = total_invested / total_quantity
            else:
                position.average_price = Decimal('0')
            
            position.quantity = total_quantity
            
            # Update broker if provided
            if operation.broker:
                position.broker = operation.broker
                
        elif operation.operation_type == 'SELL':
            # Subtract from position
            if position.quantity < operation.quantity:
                raise ValueError(f"Insufficient quantity to sell. Available: {position.quantity}, Requested: {operation.quantity}")
            
            position.quantity = position.quantity - operation.quantity
            
            # If position is empty, reset average price
            if position.quantity == 0:
                position.average_price = Decimal('0')
        
        position.save()
        return position
    
    @staticmethod
    @transaction.atomic
    def recalculate_user_positions(user_id: str) -> List[CryptoPosition]:
        """Recalculate all positions for a user from operations."""
        # Get all operations for user, ordered by date
        operations = CryptoOperation.objects.filter(
            user_id=user_id
        ).order_by('operation_date', 'created_at')
        
        # Delete all existing positions for user
        CryptoPosition.objects.filter(user_id=user_id).delete()
        
        # Recalculate positions from operations
        positions_dict = {}
        
        for operation in operations:
            crypto_id = operation.crypto_currency_id
            
            if crypto_id not in positions_dict:
                positions_dict[crypto_id] = {
                    'quantity': Decimal('0'),
                    'total_invested': Decimal('0'),
                    'broker': operation.broker or None,
                    'crypto_currency': operation.crypto_currency
                }
            
            position_data = positions_dict[crypto_id]
            
            if operation.operation_type == 'BUY':
                # Add to position
                position_data['quantity'] += operation.quantity
                position_data['total_invested'] += operation.quantity * operation.price
                if operation.broker:
                    position_data['broker'] = operation.broker
                    
            elif operation.operation_type == 'SELL':
                # Subtract from position
                if position_data['quantity'] < operation.quantity:
                    # Skip this operation or handle error
                    continue
                
                # Calculate cost basis for sold quantity
                if position_data['quantity'] > 0:
                    avg_price = position_data['total_invested'] / position_data['quantity']
                    cost_basis = operation.quantity * avg_price
                    position_data['total_invested'] -= cost_basis
                else:
                    position_data['total_invested'] = Decimal('0')
                
                position_data['quantity'] -= operation.quantity
        
        # Create positions
        positions = []
        for crypto_id, position_data in positions_dict.items():
            if position_data['quantity'] > 0:
                avg_price = position_data['total_invested'] / position_data['quantity'] if position_data['quantity'] > 0 else Decimal('0')
                
                position = CryptoPosition.objects.create(
                    user_id=user_id,
                    crypto_currency=position_data['crypto_currency'],
                    quantity=position_data['quantity'],
                    average_price=avg_price,
                    broker=position_data['broker']
                )
                positions.append(position)
        
        return positions
    
    @staticmethod
    def get_user_positions_summary(user_id: str) -> Dict:
        """Get summary of user's crypto positions."""
        positions = CryptoPosition.objects.filter(
            user_id=user_id,
            quantity__gt=0
        ).select_related('crypto_currency')
        
        total_invested = Decimal('0')
        position_list = []
        
        for position in positions:
            invested = position.quantity * position.average_price
            total_invested += invested
            
            position_list.append({
                'crypto_currency': position.crypto_currency.symbol,
                'quantity': float(position.quantity),
                'average_price': float(position.average_price),
                'total_invested': float(invested),
                'broker': position.broker
            })
        
        return {
            'total_positions': len(position_list),
            'total_invested': float(total_invested),
            'positions': position_list
        }
    
    @staticmethod
    def fetch_crypto_price(symbol: str, currency: str = 'BRL') -> Optional[Decimal]:
        """
        Fetch cryptocurrency price from yfinance.
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            currency: Currency code (default 'BRL' for Brazilian Real)
        
        Returns:
            Current price as Decimal, or None if fetch fails
        
        Examples:
            BTC in BRL: fetch_crypto_price('BTC', 'BRL')
            BTC in USD: fetch_crypto_price('BTC', 'USD')
        
        Note: For BRL, we fetch BTC-USD and convert using USD-BRL exchange rate,
        as yfinance doesn't directly support BTC-BRL.
        """
        try:
            if currency.upper() == 'BRL':
                # For BRL, we need to fetch BTC-USD and convert using USD-BRL exchange rate
                # yfinance format: BTC-USD for Bitcoin in USD, USDBRL=X for USD to BRL exchange rate
                crypto_symbol = f"{symbol}-USD"
                crypto = yf.Ticker(crypto_symbol)
                crypto_data = crypto.history(period="1d")
                
                if crypto_data.empty or 'Close' not in crypto_data.columns:
                    return None
                
                btc_usd_price = Decimal(str(crypto_data['Close'].iloc[-1]))
                
                # Fetch USD-BRL exchange rate
                usdbrl = yf.Ticker("USDBRL=X")
                usdbrl_data = usdbrl.history(period="1d")
                
                if usdbrl_data.empty or 'Close' not in usdbrl_data.columns:
                    return None
                
                usd_brl_rate = Decimal(str(usdbrl_data['Close'].iloc[-1]))
                
                # Convert to BRL: BTC price in BRL = BTC price in USD * USD-BRL rate
                btc_brl_price = btc_usd_price * usd_brl_rate
                
                return btc_brl_price
            else:
                # For other currencies (USD, EUR, etc.), use direct format: SYMBOL-CURRENCY
                ticker_symbol = f"{symbol}-{currency}"
                crypto = yf.Ticker(ticker_symbol)
                data = crypto.history(period="1d")
                
                if not data.empty and 'Close' in data.columns:
                    price = Decimal(str(data['Close'].iloc[-1]))
                    return price
            
            return None
        except Exception as e:
            print(f"Error fetching price for {symbol}-{currency}: {e}")
            return None
    
    @staticmethod
    def fetch_btc_brl_price() -> Optional[Decimal]:
        """Convenience method to fetch BTC price in BRL."""
        return CryptoService.fetch_crypto_price('BTC', 'BRL')
    
    @staticmethod
    def update_crypto_price(symbol: str, currency: str = 'BRL') -> Optional[Decimal]:
        """
        Fetch and update crypto currency price in the database.
        
        Note: This requires a current_price field in CryptoCurrency model.
        If the field doesn't exist, this will only return the price without storing it.
        
        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            currency: Currency code (default 'BRL')
        
        Returns:
            Updated price as Decimal, or None if fetch fails
        """
        price = CryptoService.fetch_crypto_price(symbol, currency)
        
        if price is not None:
            try:
                crypto_currency = CryptoCurrency.objects.get(symbol=symbol, is_active=True)
                # Note: If current_price field doesn't exist, this will fail
                # We'll need to add this field to the model if we want to store prices
                if hasattr(crypto_currency, 'current_price'):
                    crypto_currency.current_price = price
                    if hasattr(crypto_currency, 'last_updated'):
                        crypto_currency.last_updated = timezone.now()
                    crypto_currency.save()
            except CryptoCurrency.DoesNotExist:
                print(f"CryptoCurrency with symbol {symbol} not found")
            except Exception as e:
                print(f"Error updating price for {symbol}: {e}")
        
        return price

