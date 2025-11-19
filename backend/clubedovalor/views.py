"""
Django REST Framework views for Clube do Valor stock recommendations.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .services import ClubeDoValorService


class ClubeDoValorListView(APIView):
    """Get current month's stock list."""
    
    def get(self, request):
        """Get current month's stocks."""
        stocks = ClubeDoValorService.get_current_stocks()
        current_data = ClubeDoValorService.load_ambb_data()
        current_info = current_data.get('current', {})
        
        return Response({
            'timestamp': current_info.get('timestamp', ''),
            'stocks': stocks,
            'count': len(stocks)
        }, status=status.HTTP_200_OK)


class ClubeDoValorHistoryView(APIView):
    """Get all historical snapshots."""
    
    def get(self, request):
        """Get all historical snapshots."""
        snapshots = ClubeDoValorService.get_historical_snapshots()
        return Response({
            'snapshots': snapshots,
            'count': len(snapshots)
        }, status=status.HTTP_200_OK)


class ClubeDoValorRefreshView(APIView):
    """Manually trigger fetch from Google Sheets and create new snapshot."""
    permission_classes = [AllowAny]
    authentication_classes = []  # Disable authentication to bypass CSRF
    
    def post(self, request):
        """Fetch from Google Sheets and create new snapshot."""
        try:
            # Use provided URL or default to the fixed URL
            sheets_url = request.data.get('sheets_url', None)
            
            result = ClubeDoValorService.refresh_from_google_sheets(sheets_url=sheets_url)
            return Response({
                'success': True,
                'message': 'Data refreshed successfully from Google Sheets',
                'timestamp': result['timestamp'],
                'stocks_count': result['count']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_details = str(e)
            traceback_str = traceback.format_exc()
            print(f"Error refreshing from Google Sheets: {error_details}")
            print(f"Traceback: {traceback_str}")
            
            # Provide more helpful error message for 404 errors
            if '404' in error_details or 'Not Found' in error_details:
                error_message = (
                    'Failed to access Google Sheets. This usually means:\n'
                    '1. The sheet is not published to the web (File > Share > Publish to web)\n'
                    '2. The URL is incorrect or incomplete\n'
                    '3. The sheet has been moved or deleted\n\n'
                    f'Error: {error_details}'
                )
            else:
                error_message = f'Failed to refresh from Google Sheets: {error_details}'
            
            return Response({
                'error': 'Failed to refresh from Google Sheets',
                'details': error_message
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClubeDoValorStockDetailView(APIView):
    """Delete a stock and auto-reorder rankings."""
    
    def delete(self, request, codigo):
        """Delete a stock by codigo."""
        deleted = ClubeDoValorService.delete_stock(codigo)
        
        if deleted:
            return Response({
                'success': True,
                'message': f'Stock {codigo} deleted successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Stock not found'
            }, status=status.HTTP_404_NOT_FOUND)

