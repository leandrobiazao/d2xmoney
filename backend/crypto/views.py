"""
Views for crypto app.
"""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import CryptoCurrency, CryptoOperation, CryptoPosition
from .serializers import CryptoCurrencySerializer, CryptoOperationSerializer, CryptoPositionSerializer
from .services import CryptoService


class CryptoCurrencyViewSet(viewsets.ModelViewSet):
    """ViewSet for CryptoCurrency."""
    queryset = CryptoCurrency.objects.all()
    serializer_class = CryptoCurrencySerializer
    
    def get_queryset(self):
        queryset = CryptoCurrency.objects.select_related('investment_type', 'investment_subtype').all()
        search = self.request.query_params.get('search')
        investment_type_id = self.request.query_params.get('investment_type_id')
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        if search:
            queryset = queryset.filter(
                models.Q(symbol__icontains=search) |
                models.Q(name__icontains=search)
            )
        if investment_type_id:
            queryset = queryset.filter(investment_type_id=investment_type_id)
        
        return queryset.order_by('symbol')


class CryptoOperationViewSet(viewsets.ModelViewSet):
    """ViewSet for CryptoOperation."""
    queryset = CryptoOperation.objects.all()
    serializer_class = CryptoOperationSerializer
    
    def get_queryset(self):
        queryset = CryptoOperation.objects.select_related('crypto_currency', 'crypto_currency__investment_type').all()
        user_id = self.request.query_params.get('user_id')
        crypto_currency_id = self.request.query_params.get('crypto_currency_id')
        operation_type = self.request.query_params.get('operation_type')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if crypto_currency_id:
            queryset = queryset.filter(crypto_currency_id=crypto_currency_id)
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)
        
        return queryset.order_by('-operation_date', '-created_at')
    
    @action(detail=True, methods=['delete'])
    def delete_and_recalculate(self, request, pk=None):
        """Delete operation and recalculate positions."""
        operation = self.get_object()
        user_id = operation.user_id
        
        operation.delete()
        
        # Recalculate positions after deletion
        CryptoService.recalculate_user_positions(user_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class CryptoPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for CryptoPosition (read-only, positions are calculated from operations)."""
    queryset = CryptoPosition.objects.all()
    serializer_class = CryptoPositionSerializer
    
    def get_queryset(self):
        queryset = CryptoPosition.objects.select_related('crypto_currency', 'crypto_currency__investment_type').all()
        user_id = self.request.query_params.get('user_id')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset.order_by('crypto_currency__symbol')
    
    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        """Recalculate positions for a user from operations."""
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        CryptoService.recalculate_user_positions(user_id)
        
        # Return updated positions
        positions = CryptoPosition.objects.filter(user_id=user_id).select_related(
            'crypto_currency', 'crypto_currency__investment_type'
        )
        serializer = self.get_serializer(positions, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class CryptoPriceViewSet(viewsets.ViewSet):
    """ViewSet for fetching crypto prices from yfinance."""
    
    @action(detail=False, methods=['get'])
    def btc_brl(self, request):
        """Get current BTC price in BRL."""
        from django.utils import timezone
        price = CryptoService.fetch_btc_brl_price()
        
        if price is None:
            return Response(
                {'error': 'Failed to fetch BTC price'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'symbol': 'BTC',
            'currency': 'BRL',
            'price': float(price),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def price(self, request):
        """Get current crypto price.
        
        Query parameters:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH') - required
            currency: Currency code (default 'BRL')
        """
        from django.utils import timezone
        symbol = request.query_params.get('symbol')
        currency = request.query_params.get('currency', 'BRL')
        
        if not symbol:
            return Response(
                {'error': 'symbol parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        price = CryptoService.fetch_crypto_price(symbol.upper(), currency.upper())
        
        if price is None:
            return Response(
                {'error': f'Failed to fetch {symbol}-{currency} price'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'symbol': symbol.upper(),
            'currency': currency.upper(),
            'price': float(price),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


class CryptoPriceViewSet(viewsets.ViewSet):
    """ViewSet for fetching crypto prices from yfinance."""
    
    @action(detail=False, methods=['get'])
    def btc_brl(self, request):
        """Get current BTC price in BRL."""
        price = CryptoService.fetch_btc_brl_price()
        
        if price is None:
            return Response(
                {'error': 'Failed to fetch BTC price'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'symbol': 'BTC',
            'currency': 'BRL',
            'price': float(price),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def price(self, request):
        """Get current crypto price.
        
        Query parameters:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH') - required
            currency: Currency code (default 'BRL')
        """
        symbol = request.query_params.get('symbol')
        currency = request.query_params.get('currency', 'BRL')
        
        if not symbol:
            return Response(
                {'error': 'symbol parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        price = CryptoService.fetch_crypto_price(symbol.upper(), currency.upper())
        
        if price is None:
            return Response(
                {'error': f'Failed to fetch {symbol}-{currency} price'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'symbol': symbol.upper(),
            'currency': currency.upper(),
            'price': float(price),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
