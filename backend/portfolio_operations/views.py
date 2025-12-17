"""
Django REST Framework views for portfolio summaries.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .services import PortfolioService
from .models import CorporateEvent
from .serializers import CorporateEventSerializer
from stocks.services import StockService


class PortfolioListView(APIView):
    """Get portfolio for a user or refresh portfolio."""
    
    def get(self, request):
        """Get portfolio for a user."""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticker_summaries = PortfolioService.get_user_portfolio(user_id)
        return Response(ticker_summaries, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Manually trigger portfolio refresh from brokerage notes."""
        try:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            return Response({
                'success': True,
                'message': 'Portfolio refreshed successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to refresh portfolio',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PortfolioRefreshView(APIView):
    """Refresh portfolio from brokerage notes."""
    
    def post(self, request):
        """Refresh portfolio from all brokerage notes."""
        try:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
            portfolio = PortfolioService.load_portfolio()
            return Response({
                'success': True,
                'message': 'Portfolio refreshed successfully',
                'users_count': len(portfolio),
                'total_positions': sum(len(tickers) for tickers in portfolio.values())
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to refresh portfolio',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PortfolioPricesView(APIView):
    """Fetch current prices for multiple tickers."""
    
    def post(self, request):
        """
        Fetch current stock prices for a list of tickers.
        
        Request body:
        {
            "tickers": ["BERK34", "PETR4", ...],
            "market": "B3"  // Optional, defaults to "B3"
        }
        
        Returns:
        {
            "prices": {
                "BERK34": 132.07,
                "PETR4": 28.50,
                ...
            }
        }
        """
        try:
            tickers = request.data.get('tickers', [])
            market = request.data.get('market', 'B3')
            
            if not tickers or not isinstance(tickers, list):
                return Response({
                    'error': 'tickers parameter is required and must be a list'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            prices = {}
            for ticker in tickers:
                if not isinstance(ticker, str):
                    continue
                
                # Fetch price using StockService
                price = StockService.fetch_price_from_google_finance(ticker, market)
                if price is not None:
                    prices[ticker] = price
            
            return Response({
                'prices': prices
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to fetch prices',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CorporateEventListView(APIView):
    """List all corporate events or create a new one."""
    
    def get(self, request):
        """Get all corporate events."""
        events = CorporateEvent.objects.all()
        serializer = CorporateEventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new corporate event."""
        serializer = CorporateEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CorporateEventDetailView(APIView):
    """Get, update, or delete a specific corporate event."""
    
    def get(self, request, event_id):
        """Get a specific corporate event."""
        try:
            event = CorporateEvent.objects.get(pk=event_id)
            serializer = CorporateEventSerializer(event)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CorporateEvent.DoesNotExist:
            return Response(
                {'error': 'Corporate event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, event_id):
        """Update a corporate event."""
        try:
            event = CorporateEvent.objects.get(pk=event_id)
            serializer = CorporateEventSerializer(event, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CorporateEvent.DoesNotExist:
            return Response(
                {'error': 'Corporate event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, event_id):
        """Delete a corporate event."""
        try:
            event = CorporateEvent.objects.get(pk=event_id)
            event.delete()
            return Response(
                {'success': True, 'message': 'Corporate event deleted successfully'},
                status=status.HTTP_200_OK
            )
        except CorporateEvent.DoesNotExist:
            return Response(
                {'error': 'Corporate event not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CorporateEventApplyView(APIView):
    """Apply a corporate event adjustment to portfolio positions."""
    
    def post(self, request, event_id):
        """Apply corporate event adjustment to portfolio."""
        try:
            event = CorporateEvent.objects.get(pk=event_id)
            user_id = request.data.get('user_id')  # Optional: if None, applies to all users
            
            with transaction.atomic():
                # Handle ticker changes differently
                if event.event_type == 'TICKER_CHANGE':
                    result = PortfolioService.apply_ticker_change(event)
                    event.applied = True
                    event.save()
                    
                    # After applying ticker change, refresh portfolio to consolidate
                    PortfolioService.refresh_portfolio_from_brokerage_notes()
                    
                    return Response({
                        'success': True,
                        'message': result['message'],
                        'positions_updated': result['positions_updated'],
                        'operations_updated': result['operations_updated'],
                        'event': CorporateEventSerializer(event).data
                    }, status=status.HTTP_200_OK)
                elif event.event_type == 'FUND_CONVERSION':
                    # Handle fund conversion (extinction/liquidation with conversion)
                    result = PortfolioService.apply_fund_conversion(event, user_id=user_id)
                    event.applied = True
                    event.save()
                    
                    # Refresh portfolio to ensure consistency
                    PortfolioService.refresh_portfolio_from_brokerage_notes()
                    
                    return Response({
                        'success': True,
                        'message': result['message'],
                        'positions_created': result.get('positions_created', 0),
                        'positions_updated': result.get('positions_updated', 0),
                        'operations_updated': result.get('operations_updated', 0),
                        'event': CorporateEventSerializer(event).data
                    }, status=status.HTTP_200_OK)
                else:
                    # Handle other event types (GROUPING, SPLIT, BONUS)
                    PortfolioService.apply_corporate_event(event, user_id=user_id)
                    event.applied = True
                    event.save()
                    
                    return Response({
                        'success': True,
                        'message': f'Corporate event {event.ticker} applied successfully',
                        'event': CorporateEventSerializer(event).data
                    }, status=status.HTTP_200_OK)
            
        except CorporateEvent.DoesNotExist:
            return Response(
                {'error': 'Corporate event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response({
                'error': 'Invalid event configuration',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to apply corporate event',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
