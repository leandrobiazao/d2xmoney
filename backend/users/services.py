"""
JSON file storage service for users.
"""
import json
import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings


class UserJsonStorageService:
    """Service for managing user data in JSON file storage."""
    
    @staticmethod
    def get_users_file_path() -> Path:
        """Get the path to the users JSON file."""
        data_dir = Path(settings.DATA_DIR)
        return data_dir / 'users.json'
    
    @staticmethod
    def load_users() -> List[Dict]:
        """Load all users from JSON file."""
        file_path = UserJsonStorageService.get_users_file_path()
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading users: {e}")
            return []
    
    @staticmethod
    def save_users(users: List[Dict]) -> None:
        """Save users list to JSON file."""
        file_path = UserJsonStorageService.get_users_file_path()
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving users: {e}")
            raise
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        users = UserJsonStorageService.load_users()
        return next((u for u in users if u.get('id') == user_id), None)
    
    @staticmethod
    def user_exists(user_id: str) -> bool:
        """Check if user exists."""
        return UserJsonStorageService.get_user_by_id(user_id) is not None
    
    @staticmethod
    def generate_user_id() -> str:
        """Generate unique UUID for user."""
        return str(uuid.uuid4())
    
    @staticmethod
    def normalize_cpf(cpf: str) -> str:
        """Normalize CPF by removing formatting (dots and dashes)."""
        return re.sub(r'[^\d]', '', cpf)
    
    @staticmethod
    def get_user_by_cpf(cpf: str, exclude_user_id: Optional[str] = None) -> Optional[Dict]:
        """Get user by CPF (normalized comparison).
        
        Args:
            cpf: CPF to search for (can be formatted or unformatted)
            exclude_user_id: Optional user ID to exclude from search (for updates)
        
        Returns:
            User dict if found, None otherwise
        """
        normalized_cpf = UserJsonStorageService.normalize_cpf(cpf)
        users = UserJsonStorageService.load_users()
        
        for user in users:
            if exclude_user_id and user.get('id') == exclude_user_id:
                continue
            user_cpf = user.get('cpf', '')
            if UserJsonStorageService.normalize_cpf(user_cpf) == normalized_cpf:
                return user
        
        return None
    
    @staticmethod
    def get_user_by_account_number(account_number: str, exclude_user_id: Optional[str] = None) -> Optional[Dict]:
        """Get user by account number.
        
        Args:
            account_number: Account number to search for
            exclude_user_id: Optional user ID to exclude from search (for updates)
        
        Returns:
            User dict if found, None otherwise
        """
        users = UserJsonStorageService.load_users()
        
        for user in users:
            if exclude_user_id and user.get('id') == exclude_user_id:
                continue
            if user.get('account_number') == account_number:
                return user
        
        return None

