"""
JSON file storage service for brokerage notes history.
"""
import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings


class BrokerageNoteHistoryService:
    """Service for managing brokerage note history in JSON file storage."""
    
    @staticmethod
    def get_history_file_path() -> Path:
        """Get the path to the brokerage notes JSON file."""
        data_dir = Path(settings.DATA_DIR)
        return data_dir / 'brokerage_notes.json'
    
    @staticmethod
    def load_history() -> List[Dict]:
        """Load all notes from JSON file."""
        file_path = BrokerageNoteHistoryService.get_history_file_path()
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading brokerage notes: {e}")
            return []
    
    @staticmethod
    def save_history(notes: List[Dict]) -> None:
        """Save notes list to JSON file."""
        file_path = BrokerageNoteHistoryService.get_history_file_path()
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving brokerage notes: {e}")
            raise
    
    @staticmethod
    def get_note_by_id(note_id: str) -> Optional[Dict]:
        """Get note by ID."""
        notes = BrokerageNoteHistoryService.load_history()
        return next((n for n in notes if n.get('id') == note_id), None)
    
    @staticmethod
    def get_notes_by_user(user_id: str) -> List[Dict]:
        """Get all notes for a user."""
        notes = BrokerageNoteHistoryService.load_history()
        return [n for n in notes if n.get('user_id') == user_id]
    
    @staticmethod
    def find_duplicate_note(user_id: str, note_number: str, note_date: str) -> Optional[Dict]:
        """Find duplicate note by user_id, note_number, and note_date."""
        notes = BrokerageNoteHistoryService.load_history()
        for note in notes:
            if (note.get('user_id') == user_id and 
                note.get('note_number') == note_number and 
                note.get('note_date') == note_date):
                return note
        return None
    
    @staticmethod
    def add_note(note_data: Dict) -> str:
        """Add new note and return ID."""
        note_id = BrokerageNoteHistoryService.generate_note_id()
        note_data['id'] = note_id
        
        notes = BrokerageNoteHistoryService.load_history()
        notes.append(note_data)
        BrokerageNoteHistoryService.save_history(notes)
        
        return note_id
    
    @staticmethod
    def update_note(note_id: str, note_data: Dict) -> None:
        """Update note."""
        notes = BrokerageNoteHistoryService.load_history()
        notes = [n if n.get('id') != note_id else {**n, **note_data} for n in notes]
        BrokerageNoteHistoryService.save_history(notes)
    
    @staticmethod
    def delete_note(note_id: str) -> None:
        """Delete note from history."""
        notes = BrokerageNoteHistoryService.load_history()
        notes = [n for n in notes if n.get('id') != note_id]
        BrokerageNoteHistoryService.save_history(notes)
    
    @staticmethod
    def generate_note_id() -> str:
        """Generate unique UUID for note."""
        return str(uuid.uuid4())

