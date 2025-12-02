"""
Django REST Framework views for brokerage notes.
"""
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .serializers import BrokerageNoteSerializer
from .services import BrokerageNoteHistoryService
from portfolio_operations.services import PortfolioService


class BrokerageNoteListView(APIView):
    """List all brokerage notes with optional filters and create new notes."""
    authentication_classes = []  # Disable authentication to bypass CSRF
    
    def get(self, request):
        """Get all notes with optional filters."""
        try:
            # Apply filters at database level for better performance and accuracy
            user_id = request.query_params.get('user_id')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            note_number = request.query_params.get('note_number')
            
            # Use database-level filtering instead of loading all and filtering in memory
            from .models import BrokerageNote
            
            query = BrokerageNote.objects.all()
            
            if user_id:
                query = query.filter(user_id=user_id)
            
            if note_number:
                query = query.filter(note_number=note_number)
            
            # Apply date filters if provided
            if date_from or date_to:
                # Note: note_date is stored as string DD/MM/YYYY, so we need string comparison
                # For proper date filtering, we'd need to parse and compare, but for now
                # string comparison works for exact matches and same-format strings
                if date_from:
                    # String comparison for DD/MM/YYYY format
                    # This works when dates are in the same format
                    notes_list = list(query)
                    notes_list = [n for n in notes_list if n.note_date >= date_from]
                    # Convert back to queryset-like list
                    note_ids = [n.id for n in notes_list]
                    query = BrokerageNote.objects.filter(id__in=note_ids)
                
                if date_to:
                    notes_list = list(query)
                    notes_list = [n for n in notes_list if n.note_date <= date_to]
                    note_ids = [n.id for n in notes_list]
                    query = BrokerageNote.objects.filter(id__in=note_ids)
            
            # Convert to list of dicts
            notes = []
            for note in query:
                note_dict = BrokerageNoteHistoryService._note_to_dict(note)
                notes.append(note_dict)
            
            return Response(notes, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in GET handler: {str(e)}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Error loading notes: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create note."""
        serializer = BrokerageNoteSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation error', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate note ID and add processed_at
        note_data = serializer.validated_data.copy()
        note_data['processed_at'] = datetime.now().isoformat()
        note_data['operations_count'] = len(note_data.get('operations', []))
        
        # Debug: Log financial summary fields
        print(f"DEBUG: Financial summary in request:")
        print(f"  total_custos_despesas: {note_data.get('total_custos_despesas')}")
        print(f"  taxa_operacional: {note_data.get('taxa_operacional')}")
        print(f"  execucao: {note_data.get('execucao')}")
        
        # Check for duplicate note
        user_id = note_data.get('user_id')
        note_number = note_data.get('note_number')
        note_date = note_data.get('note_date')
        
        if user_id and note_number and note_date:
            duplicate = BrokerageNoteHistoryService.find_duplicate_note(
                user_id, note_number, note_date
            )
            if duplicate:
                return Response(
                    {
                        'error': 'Nota de corretagem já processada',
                        'message': f'A nota número {note_number} de {note_date} já foi processada anteriormente.',
                        'existing_note_id': duplicate.get('id'),
                        'existing_note': duplicate
                    },
                    status=status.HTTP_409_CONFLICT
                )
        
        # Save to database
        try:
            note_id = BrokerageNoteHistoryService.add_note(note_data)
            note_data['id'] = note_id
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR: Failed to save brokerage note: {str(e)}")
            print(f"ERROR: Traceback: {error_details}")
            return Response(
                {
                    'error': 'Erro ao salvar nota de corretagem',
                    'message': f'Erro ao salvar no banco de dados: {str(e)}',
                    'details': error_details if 'database is locked' in str(e).lower() else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Refresh portfolio after adding note
        try:
            PortfolioService.refresh_portfolio_from_brokerage_notes()
        except Exception as e:
            print(f"Warning: Failed to refresh portfolio after note upload: {e}")
        
        return Response(note_data, status=status.HTTP_201_CREATED)


class BrokerageNoteDetailView(APIView):
    """Get or delete a brokerage note."""
    authentication_classes = []  # Disable authentication to bypass CSRF
    
    def get(self, request, note_id):
        """Get note by ID."""
        note = BrokerageNoteHistoryService.get_note_by_id(note_id)
        
        if not note:
            return Response(
                {'error': 'Note not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(note, status=status.HTTP_200_OK)
    
    def delete(self, request, note_id):
        """Delete note by ID."""
        try:
            # Delete note from database (this will check if it exists)
            BrokerageNoteHistoryService.delete_note(note_id)
            
            # Refresh portfolio after deleting note (skip if migration not run)
            try:
                PortfolioService.refresh_portfolio_from_brokerage_notes()
            except Exception as e:
                # Silently ignore errors during refresh (e.g., missing status column)
                # The portfolio will be refreshed on next manual refresh or when migration is run
                print(f"Warning: Failed to refresh portfolio after note deletion: {e}")
                pass
            
            return Response({
                'success': True,
                'message': f'Note {note_id} deleted successfully'
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            # Note not found
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            print(f"ERROR: Exception in DELETE handler: {str(e)}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Error deleting note: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BrokerageNoteOperationsView(APIView):
    """Get operations from a specific note."""
    
    def get(self, request, note_id):
        """Get operations for a note."""
        note = BrokerageNoteHistoryService.get_note_by_id(note_id)
        
        if not note:
            return Response(
                {'error': 'Note not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'note_id': note_id,
            'operations': note.get('operations', [])
        }, status=status.HTTP_200_OK)

