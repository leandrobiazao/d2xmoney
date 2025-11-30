"""
Django REST Framework views for ticker mappings.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import TickerMappingService, TickerDiscoveryService


class TickerMappingListView(APIView):
    """List all ticker mappings or create/update a mapping."""
    
    def get(self, request):
        """Get all ticker mappings."""
        mappings = TickerMappingService.load_mappings()
        return Response(mappings, status=status.HTTP_200_OK)
    
    def put(self, request):
        """Sync ticker mappings from JSON file to database."""
        from django.conf import settings
        from pathlib import Path
        import json
        
        data_dir = Path(settings.DATA_DIR)
        json_file = data_dir / 'ticker.json'
        
        if not json_file.exists():
            return Response(
                {'error': f'JSON file not found: {json_file}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_mappings = json.load(f)
            
            # Sync to database
            TickerMappingService.save_mappings(json_mappings)
            
            # Check for missing entries
            db_mappings = TickerMappingService.load_mappings()
            missing = []
            for company_name, ticker in json_mappings.items():
                normalized_name = TickerMappingService.normalize_company_name(company_name)
                if normalized_name not in db_mappings:
                    missing.append(company_name)
            
            return Response({
                'success': True,
                'message': f'Synced {len(json_mappings)} mappings from JSON to database',
                'synced': len(json_mappings),
                'in_database': len(db_mappings),
                'missing': len(missing),
                'missing_entries': missing[:10]  # Return first 10 missing
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in PUT handler: {str(e)}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Error syncing mappings: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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


class TickerDiscoveryView(APIView):
    """Discover ticker for a company name."""
    
    def post(self, request):
        """Discover ticker for a company name."""
        company_name = request.data.get('company_name')
        
        if not company_name:
            return Response(
                {'error': 'Company name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # First check if mapping already exists
            existing_ticker = TickerMappingService.get_ticker(company_name)
            if existing_ticker:
                return Response({
                    'ticker': existing_ticker,
                    'found': True,
                    'source': 'database'
                }, status=status.HTTP_200_OK)
            
            # Try to discover
            ticker, found = TickerDiscoveryService.discover_ticker(company_name)
            
            if found and ticker:
                # Save the discovery
                TickerMappingService.set_ticker(company_name, ticker)
                
                return Response({
                    'ticker': ticker,
                    'found': True,
                    'source': 'discovery'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'ticker': None,
                    'found': False
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in discovery handler: {str(e)}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Error discovering ticker: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
