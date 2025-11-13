"""
Service for managing brokerage note history using Django ORM.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from .models import BrokerageNote, Operation


class BrokerageNoteHistoryService:
    """Service for managing brokerage note history using Django ORM."""
    
    @staticmethod
    def get_history_file_path():
        """Legacy method - kept for backward compatibility."""
        # This method is no longer used but kept for compatibility
        pass
    
    @staticmethod
    def load_history() -> List[Dict]:
        """Load all notes from database."""
        try:
            # First, check if status and error_message columns exist in the database
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA table_info(brokerage_notes)")
                columns = [row[1] for row in cursor.fetchall()]
                has_status = 'status' in columns
                has_error_message = 'error_message' in columns
            
            # Build list of fields to select (only those that exist in database)
            fields_to_select = [
                'id', 'user_id', 'file_name', 'original_file_path',
                'note_date', 'note_number', 'processed_at',
                'operations_count', 'operations'
            ]
            if has_status:
                fields_to_select.append('status')
            if has_error_message:
                fields_to_select.append('error_message')
            
            # Use only() to select only existing fields
            notes = BrokerageNote.objects.all().only(*fields_to_select)
            
            result = []
            for note in notes:
                note_dict = {
                    'id': str(note.id),
                    'user_id': note.user_id,
                    'file_name': note.file_name,
                    'original_file_path': note.original_file_path,
                    'note_date': note.note_date,
                    'note_number': note.note_number,
                    'processed_at': note.processed_at.isoformat() if note.processed_at else None,
                    'operations_count': note.operations_count,
                    'operations': note.operations or [],
                }
                
                # Add status and error_message - only access if column exists
                # If column doesn't exist, use defaults without trying to access
                if has_status and 'status' in fields_to_select:
                    # Only access if it was selected
                    note_dict['status'] = getattr(note, 'status', 'success')
                else:
                    note_dict['status'] = 'success'
                
                if has_error_message and 'error_message' in fields_to_select:
                    # Only access if it was selected
                    note_dict['error_message'] = getattr(note, 'error_message', None)
                else:
                    note_dict['error_message'] = None
                
                result.append(note_dict)
            
            return result
        except Exception as e:
            # Final fallback: return empty list with error message
            import traceback
            error_msg = str(e)
            print(f"ERROR: Could not load notes: {error_msg}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            # Return empty list instead of raising - allows UI to load
            return []
    
    @staticmethod
    def save_history(notes: List[Dict]) -> None:
        """Save notes list to database."""
        for note_data in notes:
            BrokerageNoteHistoryService._save_note_data(note_data)
    
    @staticmethod
    def get_note_by_id(note_id: str) -> Optional[Dict]:
        """Get note by ID."""
        try:
            # Check if status and error_message columns exist
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA table_info(brokerage_notes)")
                columns = [row[1] for row in cursor.fetchall()]
                has_status = 'status' in columns
                has_error_message = 'error_message' in columns
            
            # Build list of fields to select (only those that exist in database)
            fields_to_select = [
                'id', 'user_id', 'file_name', 'original_file_path',
                'note_date', 'note_number', 'processed_at',
                'operations_count', 'operations'
            ]
            if has_status:
                fields_to_select.append('status')
            if has_error_message:
                fields_to_select.append('error_message')
            
            # Use only() to select only existing fields
            note = BrokerageNote.objects.only(*fields_to_select).get(id=note_id)
            return BrokerageNoteHistoryService._note_to_dict(note)
        except BrokerageNote.DoesNotExist:
            return None
    
    @staticmethod
    def get_notes_by_user(user_id: str) -> List[Dict]:
        """Get all notes for a user."""
        notes = BrokerageNote.objects.filter(user_id=user_id)
        return [BrokerageNoteHistoryService._note_to_dict(note) for note in notes]
    
    @staticmethod
    def find_duplicate_note(user_id: str, note_number: str, note_date: str) -> Optional[Dict]:
        """Find duplicate note by user_id, note_number, and note_date."""
        try:
            note = BrokerageNote.objects.get(
                user_id=user_id,
                note_number=note_number,
                note_date=note_date
            )
            return BrokerageNoteHistoryService._note_to_dict(note)
        except BrokerageNote.DoesNotExist:
            return None
    
    @staticmethod
    def add_note(note_data: Dict) -> str:
        """Add new note and return ID."""
        note_id = note_data.get('id') or BrokerageNoteHistoryService.generate_note_id()
        note_data['id'] = note_id
        
        BrokerageNoteHistoryService._save_note_data(note_data)
        
        return note_id
    
    @staticmethod
    def update_note(note_id: str, note_data: Dict) -> None:
        """Update note."""
        try:
            note = BrokerageNote.objects.get(id=note_id)
            # Update note fields
            for field in ['user_id', 'file_name', 'original_file_path', 'note_date', 
                         'note_number', 'operations_count', 'operations']:
                if field in note_data:
                    setattr(note, field, note_data[field])
            
            if 'processed_at' in note_data:
                note.processed_at = BrokerageNoteHistoryService._parse_datetime(note_data['processed_at'])
            
            note.save()
            
            # Update operations if provided
            if 'operations' in note_data:
                # Delete existing operations
                Operation.objects.filter(note=note).delete()
                # Create new operations
                for op_data in note_data['operations']:
                    BrokerageNoteHistoryService._create_operation(note, op_data)
        except BrokerageNote.DoesNotExist:
            raise ValueError(f"Note with id {note_id} not found")
    
    @staticmethod
    def delete_note(note_id: str) -> None:
        """Delete note from history."""
        from django.db import connection
        import uuid
        
        # Convert note_id to string and handle UUID format (with or without hyphens)
        note_id_str = str(note_id).replace('-', '')  # Remove hyphens to match database format
        
        # Use raw SQL to delete directly, avoiding any field access issues
        # Django's SQLite backend uses %s placeholders
        with connection.cursor() as cursor:
            # Check if note exists first (try both with and without hyphens)
            cursor.execute("SELECT id FROM brokerage_notes WHERE id = %s OR id = %s", [note_id_str, str(note_id)])
            if not cursor.fetchone():
                raise ValueError(f"Note with id {note_id} not found")
            
            # First delete operations (cascade) - try both formats
            cursor.execute("DELETE FROM operations WHERE note_id = %s OR note_id = %s", [note_id_str, str(note_id)])
            # Then delete the note - try both formats
            cursor.execute("DELETE FROM brokerage_notes WHERE id = %s OR id = %s", [note_id_str, str(note_id)])
    
    @staticmethod
    def generate_note_id() -> str:
        """Generate unique UUID for note."""
        return str(uuid.uuid4())
    
    @staticmethod
    def _save_note_data(note_data: Dict) -> BrokerageNote:
        """Save note data to database."""
        note_id = note_data.get('id')
        processed_at = None
        if note_data.get('processed_at'):
            processed_at = BrokerageNoteHistoryService._parse_datetime(note_data['processed_at'])
        
        note, created = BrokerageNote.objects.update_or_create(
            id=note_id,
            defaults={
                'user_id': note_data.get('user_id', ''),
                'file_name': note_data.get('file_name', ''),
                'original_file_path': note_data.get('original_file_path'),
                'note_date': note_data.get('note_date', ''),
                'note_number': note_data.get('note_number', ''),
                'processed_at': processed_at,
                'operations_count': note_data.get('operations_count', 0),
                'operations': note_data.get('operations', []),
                'status': note_data.get('status', 'success'),
                'error_message': note_data.get('error_message'),
            }
        )
        
        # Save operations
        operations = note_data.get('operations', [])
        if operations:
            # Delete existing operations for this note
            Operation.objects.filter(note=note).delete()
            # Create new operations
            for op_data in operations:
                BrokerageNoteHistoryService._create_operation(note, op_data)
        
        return note
    
    @staticmethod
    def _create_operation(note: BrokerageNote, op_data: Dict) -> Operation:
        """Create an operation from data."""
        op_id = op_data.get('id', f"op-{note.id}-{op_data.get('ordem', 0)}")
        
        operation, created = Operation.objects.update_or_create(
            id=op_id,
            defaults={
                'note': note,
                'tipo_operacao': op_data.get('tipoOperacao', ''),
                'tipo_mercado': op_data.get('tipoMercado'),
                'ordem': op_data.get('ordem', 0),
                'titulo': op_data.get('titulo', ''),
                'qtd_total': op_data.get('qtdTotal'),
                'preco_medio': BrokerageNoteHistoryService._parse_decimal(op_data.get('precoMedio')),
                'quantidade': op_data.get('quantidade', 0),
                'preco': BrokerageNoteHistoryService._parse_decimal(op_data.get('preco', 0)),
                'valor_operacao': BrokerageNoteHistoryService._parse_decimal(op_data.get('valorOperacao', 0)),
                'dc': op_data.get('dc'),
                'nota_tipo': op_data.get('notaTipo'),
                'corretora': op_data.get('corretora'),
                'nota_number': op_data.get('nota'),
                'data': op_data.get('data', ''),
                'client_id': op_data.get('clientId'),
                'extra_data': {k: v for k, v in op_data.items() 
                             if k not in ['id', 'tipoOperacao', 'tipoMercado', 'ordem',
                                         'titulo', 'qtdTotal', 'precoMedio', 'quantidade',
                                         'preco', 'valorOperacao', 'dc', 'notaTipo',
                                         'corretora', 'nota', 'data', 'clientId']},
            }
        )
        return operation
    
    @staticmethod
    def _note_to_dict(note: BrokerageNote) -> Dict:
        """Convert BrokerageNote model instance to dictionary."""
        result = {
            'id': str(note.id),
            'user_id': note.user_id,
            'file_name': note.file_name,
            'original_file_path': note.original_file_path,
            'note_date': note.note_date,
            'note_number': note.note_number,
            'processed_at': note.processed_at.isoformat() if note.processed_at else None,
            'operations_count': note.operations_count,
            'operations': note.operations or [],
        }
        
        # Add status and error_message if they exist (for backward compatibility)
        # Handle both AttributeError (field doesn't exist on model) and database column errors
        try:
            # Try to access the field - this will work if migration has been run
            result['status'] = getattr(note, 'status', 'success')
        except Exception:
            # If any error occurs (including database column errors), use default
            result['status'] = 'success'
        
        try:
            result['error_message'] = getattr(note, 'error_message', None)
        except Exception:
            result['error_message'] = None
        
        return result
    
    @staticmethod
    def _parse_datetime(dt_str):
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            if isinstance(dt_str, str):
                if 'T' in dt_str:
                    dt_str_clean = dt_str.replace('Z', '').split('.')[0]
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            return datetime.strptime(dt_str_clean, fmt)
                        except ValueError:
                            continue
            return None
        except Exception:
            return None
    
    @staticmethod
    def _parse_decimal(value):
        """Parse value to Decimal-compatible format."""
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0
