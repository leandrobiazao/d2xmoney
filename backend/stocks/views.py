"""
Views for stocks app.
"""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Stock
from .serializers import StockSerializer
from .services import StockService


class StockViewSet(viewsets.ModelViewSet):
    """ViewSet for Stock."""
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    
    def get_queryset(self):
        queryset = Stock.objects.select_related('investment_type').all()
        search = self.request.query_params.get('search')
        investment_type_id = self.request.query_params.get('investment_type_id')
        financial_market = self.request.query_params.get('financial_market')
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        if search:
            queryset = queryset.filter(
                models.Q(ticker__icontains=search) |
                models.Q(name__icontains=search)
            )
        if investment_type_id:
            queryset = queryset.filter(investment_type_id=investment_type_id)
        if financial_market:
            queryset = queryset.filter(financial_market=financial_market)
        
        return queryset.order_by('ticker')
    
    @action(detail=False, methods=['post'])
    def update_prices(self, request):
        """Update prices for all active stocks."""
        result = StockService.update_prices_daily()
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """Update price for a specific stock."""
        stock = self.get_object()
        price = request.data.get('price')
        if price is None:
            return Response(
                {'error': 'price is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            price = float(price)
            updated_stock = StockService.update_stock_price(stock.ticker, price)
            if updated_stock:
                serializer = self.get_serializer(updated_stock)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                {'error': 'Stock not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid price value'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def sync_from_portfolio(self, request):
        """Sync stocks from portfolio positions to catalog."""
        user_id = request.data.get('user_id')
        results = StockService.sync_portfolio_stocks_to_catalog(user_id=user_id)
        return Response(results, status=status.HTTP_200_OK)