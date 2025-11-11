"""
Django REST Framework views for portfolio summaries.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import PortfolioService


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


# Legacy views for backward compatibility (deprecated)
class PortfolioOperationsListView(APIView):
    """Legacy endpoint - use /api/portfolio/ instead."""
    
    def get(self, request):
        """Legacy endpoint - redirects to new portfolio endpoint."""
        client_id = request.query_params.get('client_id')
        if client_id:
            ticker_summaries = PortfolioService.get_user_portfolio(client_id)
            return Response(ticker_summaries, status=status.HTTP_200_OK)
        return Response(
            {'error': 'client_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def post(self, request):
        """Legacy endpoint - not supported, use /api/portfolio/refresh/ instead."""
        return Response({
            'error': 'This endpoint is deprecated. Use /api/portfolio/refresh/ instead.'
        }, status=status.HTTP_410_GONE)


class PortfolioOperationsDetailView(APIView):
    """Legacy endpoint - not supported."""
    
    def get(self, request, operation_id):
        return Response({
            'error': 'This endpoint is deprecated. Portfolio operations are now aggregated in /api/portfolio/'
        }, status=status.HTTP_410_GONE)
    
    def put(self, request, operation_id):
        return Response({
            'error': 'This endpoint is deprecated. Portfolio operations are now aggregated in /api/portfolio/'
        }, status=status.HTTP_410_GONE)
    
    def delete(self, request, operation_id):
        return Response({
            'error': 'This endpoint is deprecated. Delete brokerage notes to update portfolio.'
        }, status=status.HTTP_410_GONE)


class PortfolioOperationsClientView(APIView):
    """Legacy endpoint - not supported."""
    
    def delete(self, request, client_id):
        return Response({
            'error': 'This endpoint is deprecated. Delete brokerage notes to update portfolio.'
        }, status=status.HTTP_410_GONE)
