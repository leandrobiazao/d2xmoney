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
