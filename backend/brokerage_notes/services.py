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
        notes = BrokerageNote.objects.all()
        return [BrokerageNoteHistoryService._note_to_dict(note) for note in notes]
    
    @staticmethod
    def save_history(notes: List[Dict]) -> None:
        """Save notes list to database."""
        for note_data in notes:
            BrokerageNoteHistoryService._save_note_data(note_data)
    
    @staticmethod
    def get_note_by_id(note_id: str) -> Optional[Dict]:
        """Get note by ID."""
        try:
            note = BrokerageNote.objects.get(id=note_id)
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
        try:
            note = BrokerageNote.objects.get(id=note_id)
            note.delete()  # This will cascade delete operations
        except BrokerageNote.DoesNotExist:
            pass
    
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
        return {
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
