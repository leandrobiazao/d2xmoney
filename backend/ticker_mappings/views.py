"""
Django REST Framework views for ticker mappings.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import TickerMappingService


class TickerMappingListView(APIView):
    """List all ticker mappings or create/update a mapping."""
    
    def get(self, request):
        """Get all ticker mappings."""
        mappings = TickerMappingService.load_mappings()
        return Response(mappings, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create or update a ticker mapping."""
        nome = request.data.get('nome')
        ticker = request.data.get('ticker')
        
        if not nome or not ticker:
            return Response(
                {'error': 'Nome e ticker são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            TickerMappingService.set_ticker(nome, ticker)
            
            return Response({
                'success': True,
                'message': f'Mapeamento salvo: {nome.strip().upper()} -> {ticker.strip().upper()}',
                'nome': nome.strip().upper(),
                'ticker': ticker.strip().upper(),
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in POST handler: {str(e)}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Erro ao salvar mapeamento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TickerMappingDetailView(APIView):
    """Get, update, or delete a specific ticker mapping."""
    
    def get(self, request, nome):
        """Get ticker for a company name."""
        # URL decode the nome parameter
        from urllib.parse import unquote
        nome_decoded = unquote(nome)
        print(f"DEBUG: GET request for nome: '{nome}' (decoded: '{nome_decoded}')")
        
        ticker = TickerMappingService.get_ticker(nome_decoded)
        if ticker:
            return Response({
                'nome': nome_decoded.strip().upper(),
                'ticker': ticker
            }, status=status.HTTP_200_OK)
        else:
            # Try with the original nome as well
            ticker_original = TickerMappingService.get_ticker(nome)
            if ticker_original:
                return Response({
                    'nome': nome.strip().upper(),
                    'ticker': ticker_original
                }, status=status.HTTP_200_OK)
            else:
                print(f"DEBUG: Mapping not found for '{nome}' or '{nome_decoded}'")
                return Response(
                    {'error': 'Mapeamento não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
    
    def delete(self, request, nome):
        """Delete a ticker mapping."""
        deleted = TickerMappingService.delete_mapping(nome)
        if deleted:
            return Response({
                'success': True,
                'message': f'Mapeamento removido: {nome.strip().upper()}'
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Mapeamento não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
