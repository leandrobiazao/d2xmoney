"""
Service for managing brokerage note history using Django ORM.
"""
import uuid
import time
from datetime import datetime
from typing import List, Dict, Optional
from django.db import transaction
from django.db.utils import OperationalError
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
            # Load all notes (don't use only() to ensure all fields including financial summary are loaded)
            notes = BrokerageNote.objects.all()
            
            result = []
            for note in notes:
                # Use _note_to_dict to ensure all fields are included
                note_dict = BrokerageNoteHistoryService._note_to_dict(note)
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
            # Get the full note object (don't use only() to ensure all fields are loaded)
            # This ensures financial summary fields are included
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
            print(f"DEBUG: Duplicate note found: id={note.id}, user_id={user_id}, note_number={note_number}, note_date={note_date}")
            return BrokerageNoteHistoryService._note_to_dict(note)
        except BrokerageNote.DoesNotExist:
            print(f"DEBUG: No duplicate note found for user_id={user_id}, note_number={note_number}, note_date={note_date}")
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
        import uuid
        
        # Use atomic transaction to ensure deletion is committed
        with transaction.atomic():
            try:
                # Try to convert to UUID if it's a string
                try:
                    note_uuid = uuid.UUID(str(note_id))
                except (ValueError, AttributeError):
                    # If it's not a valid UUID, try to find by string representation
                    note_uuid = note_id
                
                # Use Django ORM to delete - this ensures proper transaction handling
                # and respects the database constraints
                try:
                    note = BrokerageNote.objects.get(id=note_uuid)
                except BrokerageNote.DoesNotExist:
                    # Try as string if UUID lookup failed
                    try:
                        note = BrokerageNote.objects.get(id=str(note_id))
                    except BrokerageNote.DoesNotExist:
                        raise ValueError(f"Note with id {note_id} not found")
                
                # Log before deletion for debugging
                print(f"DEBUG: Deleting note {note_id} (user_id={note.user_id}, note_number={note.note_number}, note_date={note.note_date})")
                
                # Delete the note - this will cascade delete operations due to CASCADE on_delete
                note.delete()
                
                print(f"DEBUG: Note {note_id} deleted successfully")
                
            except Exception as e:
                print(f"DEBUG: Error deleting note with Django ORM: {e}")
                # If Django ORM fails, fall back to raw SQL (for edge cases)
                from django.db import connection
                note_id_str = str(note_id).replace('-', '')
                
                with connection.cursor() as cursor:
                    # Check if note exists first (try both with and without hyphens)
                    cursor.execute("SELECT id, user_id, note_number, note_date FROM brokerage_notes WHERE id = %s OR id = %s", [note_id_str, str(note_id)])
                    row = cursor.fetchone()
                    if not row:
                        raise ValueError(f"Note with id {note_id} not found")
                    
                    print(f"DEBUG: Deleting note {note_id} using raw SQL (user_id={row[1]}, note_number={row[2]}, note_date={row[3]})")
                    
                    # First delete operations (cascade) - try both formats
                    cursor.execute("DELETE FROM operations WHERE note_id = %s OR note_id = %s", [note_id_str, str(note_id)])
                    # Then delete the note - try both formats
                    cursor.execute("DELETE FROM brokerage_notes WHERE id = %s OR id = %s", [note_id_str, str(note_id)])
                    
                    print(f"DEBUG: Note {note_id} deleted successfully using raw SQL")
    
    @staticmethod
    def generate_note_id() -> str:
        """Generate unique UUID for note."""
        return str(uuid.uuid4())
    
    @staticmethod
    def _save_note_data(note_data: Dict) -> BrokerageNote:
        """Save note data to database with retry logic for SQLite locking."""
        note_id = note_data.get('id')
        processed_at = None
        if note_data.get('processed_at'):
            processed_at = BrokerageNoteHistoryService._parse_datetime(note_data['processed_at'])
        
        max_retries = 5
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
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
                            # Resumo dos Negócios
                            'debentures': note_data.get('debentures'),
                            'vendas_a_vista': note_data.get('vendas_a_vista'),
                            'compras_a_vista': note_data.get('compras_a_vista'),
                            'valor_das_operacoes': note_data.get('valor_das_operacoes'),
                            # Resumo Financeiro
                            'valor_liquido_operacoes': note_data.get('valor_liquido_operacoes'),
                            'taxa_liquidacao': note_data.get('taxa_liquidacao'),
                            'taxa_registro': note_data.get('taxa_registro'),
                            'total_cblc': note_data.get('total_cblc'),
                            'emolumentos': note_data.get('emolumentos'),
                            'taxa_transferencia_ativos': note_data.get('taxa_transferencia_ativos'),
                            'total_bovespa': note_data.get('total_bovespa'),
                            # Custos Operacionais
                            'taxa_operacional': note_data.get('taxa_operacional'),
                            'execucao': note_data.get('execucao'),
                            'taxa_custodia': note_data.get('taxa_custodia'),
                            'impostos': note_data.get('impostos'),
                            'irrf_operacoes': note_data.get('irrf_operacoes'),
                            'irrf_base': note_data.get('irrf_base'),
                            'outros_custos': note_data.get('outros_custos'),
                            'total_custos_despesas': note_data.get('total_custos_despesas'),
                            'liquido': note_data.get('liquido'),
                            'liquido_data': note_data.get('liquido_data'),
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
            except OperationalError as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    # Re-raise if it's not a lock error or we've exhausted retries
                    raise
    
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
        
        # Add financial summary fields (Resumo dos Negócios)
        try:
            result['debentures'] = float(note.debentures) if note.debentures is not None else None
        except (AttributeError, ValueError, TypeError):
            result['debentures'] = None
        
        try:
            result['vendas_a_vista'] = float(note.vendas_a_vista) if note.vendas_a_vista is not None else None
        except (AttributeError, ValueError, TypeError):
            result['vendas_a_vista'] = None
        
        try:
            result['compras_a_vista'] = float(note.compras_a_vista) if note.compras_a_vista is not None else None
        except (AttributeError, ValueError, TypeError):
            result['compras_a_vista'] = None
        
        try:
            result['valor_das_operacoes'] = float(note.valor_das_operacoes) if note.valor_das_operacoes is not None else None
        except (AttributeError, ValueError, TypeError):
            result['valor_das_operacoes'] = None
        
        # Add financial summary fields (Resumo Financeiro)
        try:
            result['valor_liquido_operacoes'] = float(note.valor_liquido_operacoes) if note.valor_liquido_operacoes is not None else None
        except (AttributeError, ValueError, TypeError):
            result['valor_liquido_operacoes'] = None
        
        try:
            result['taxa_liquidacao'] = float(note.taxa_liquidacao) if note.taxa_liquidacao is not None else None
        except (AttributeError, ValueError, TypeError):
            result['taxa_liquidacao'] = None
        
        try:
            result['taxa_registro'] = float(note.taxa_registro) if note.taxa_registro is not None else None
        except (AttributeError, ValueError, TypeError):
            result['taxa_registro'] = None
        
        try:
            result['total_cblc'] = float(note.total_cblc) if note.total_cblc is not None else None
        except (AttributeError, ValueError, TypeError):
            result['total_cblc'] = None
        
        try:
            result['emolumentos'] = float(note.emolumentos) if note.emolumentos is not None else None
        except (AttributeError, ValueError, TypeError):
            result['emolumentos'] = None
        
        try:
            result['taxa_transferencia_ativos'] = float(note.taxa_transferencia_ativos) if note.taxa_transferencia_ativos is not None else None
        except (AttributeError, ValueError, TypeError):
            result['taxa_transferencia_ativos'] = None
        
        try:
            result['total_bovespa'] = float(note.total_bovespa) if note.total_bovespa is not None else None
        except (AttributeError, ValueError, TypeError):
            result['total_bovespa'] = None
        
        # Add operational costs (Custos Operacionais)
        try:
            result['taxa_operacional'] = float(note.taxa_operacional) if note.taxa_operacional is not None else None
        except (AttributeError, ValueError, TypeError):
            result['taxa_operacional'] = None
        
        try:
            result['execucao'] = float(note.execucao) if note.execucao is not None else None
        except (AttributeError, ValueError, TypeError):
            result['execucao'] = None
        
        try:
            result['taxa_custodia'] = float(note.taxa_custodia) if note.taxa_custodia is not None else None
        except (AttributeError, ValueError, TypeError):
            result['taxa_custodia'] = None
        
        try:
            result['impostos'] = float(note.impostos) if note.impostos is not None else None
        except (AttributeError, ValueError, TypeError):
            result['impostos'] = None
        
        try:
            result['irrf_operacoes'] = float(note.irrf_operacoes) if note.irrf_operacoes is not None else None
        except (AttributeError, ValueError, TypeError):
            result['irrf_operacoes'] = None
        
        try:
            result['irrf_base'] = float(note.irrf_base) if note.irrf_base is not None else None
        except (AttributeError, ValueError, TypeError):
            result['irrf_base'] = None
        
        try:
            result['outros_custos'] = float(note.outros_custos) if note.outros_custos is not None else None
        except (AttributeError, ValueError, TypeError):
            result['outros_custos'] = None
        
        try:
            if note.total_custos_despesas is not None:
                # Handle both Decimal and float/int types
                from decimal import Decimal
                if isinstance(note.total_custos_despesas, Decimal):
                    result['total_custos_despesas'] = float(note.total_custos_despesas)
                else:
                    result['total_custos_despesas'] = float(note.total_custos_despesas)
            else:
                result['total_custos_despesas'] = None
        except (AttributeError, ValueError, TypeError) as e:
            # Log the error for debugging
            import traceback
            print(f"Warning: Error converting total_custos_despesas: {e}")
            print(traceback.format_exc())
            result['total_custos_despesas'] = None
        
        try:
            result['liquido'] = float(note.liquido) if note.liquido is not None else None
        except (AttributeError, ValueError, TypeError):
            result['liquido'] = None
        
        try:
            result['liquido_data'] = note.liquido_data
        except (AttributeError, ValueError, TypeError):
            result['liquido_data'] = None
        
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
