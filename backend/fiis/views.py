from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import FIIProfile
from .serializers import FIIProfileSerializer
from stocks.models import Stock

class FIIProfileListView(APIView):
    """List all FII profiles or create a new one."""
    authentication_classes = []
    
    def get(self, request):
        profiles = FIIProfile.objects.select_related('stock').all()
        serializer = FIIProfileSerializer(profiles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new FII profile and associated Stock."""
        ticker = request.data.get('ticker', '').upper().strip()
        name = request.data.get('name', '').strip()
        
        if not ticker or not name:
            return Response(
                {'error': 'Ticker and name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if FIIProfile already exists
        if FIIProfile.objects.filter(stock__ticker=ticker).exists():
            return Response(
                {'error': f'FII profile with ticker {ticker} already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Check if Stock already exists
                stock = Stock.objects.filter(ticker=ticker).first()
                
                if stock:
                    # Stock exists but no profile - create profile only
                    # Update stock if name provided and different
                    if stock.name != name:
                        stock.name = name
                        stock.save()
                    # Ensure stock_class is FII
                    if stock.stock_class != 'FII':
                        stock.stock_class = 'FII'
                        stock.save()
                else:
                    # Create Stock first
                    stock = Stock.objects.create(
                        ticker=ticker,
                        name=name,
                        stock_class='FII',
                        financial_market='B3',
                        is_active=True
                    )
                
                # Create FIIProfile
                profile_data = {
                    'stock': stock,
                    'segment': request.data.get('segment', ''),
                    'target_audience': request.data.get('target_audience', ''),
                    'administrator': request.data.get('administrator', ''),
                }
                
                # Handle optional decimal fields
                decimal_fields = [
                    'last_yield', 'dividend_yield', 'average_yield_12m_value',
                    'average_yield_12m_percentage', 'equity_per_share', 'price_to_vp',
                    'ifix_participation', 'equity', 'base_share_price'
                ]
                for field in decimal_fields:
                    value = request.data.get(field)
                    if value is not None and value != '':
                        profile_data[field] = value
                
                # Handle optional integer fields
                integer_fields = ['trades_per_month', 'shareholders_count']
                for field in integer_fields:
                    value = request.data.get(field)
                    if value is not None and value != '':
                        profile_data[field] = value
                
                # Handle optional date fields
                date_fields = ['base_date', 'payment_date']
                for field in date_fields:
                    value = request.data.get(field)
                    if value:
                        profile_data[field] = value
                
                profile = FIIProfile.objects.create(**profile_data)
                
                serializer = FIIProfileSerializer(profile)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Error creating FII: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FIIProfileDetailView(APIView):
    """Get a specific FII profile by ticker."""
    authentication_classes = []
    
    def get(self, request, ticker):
        try:
            profile = FIIProfile.objects.select_related('stock').get(stock__ticker=ticker)
            serializer = FIIProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FIIProfile.DoesNotExist:
            return Response(
                {'error': 'FII profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
