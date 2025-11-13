"""
Service for managing user data using Django ORM.
"""
import re
import uuid
from typing import List, Dict, Optional
from .models import User


class UserJsonStorageService:
    """Service for managing user data using Django ORM."""
    
    @staticmethod
    def get_users_file_path():
        """Legacy method - kept for backward compatibility."""
        # This method is no longer used but kept for compatibility
        pass
    
    @staticmethod
    def load_users() -> List[Dict]:
        """Load all users from database."""
        users = User.objects.all()
        return [UserJsonStorageService._user_to_dict(user) for user in users]
    
    @staticmethod
    def save_users(users: List[Dict]) -> None:
        """Save users list to database."""
        for user_data in users:
            User.objects.update_or_create(
                id=user_data.get('id'),
                defaults={
                    'name': user_data.get('name', ''),
                    'cpf': user_data.get('cpf', ''),
                    'account_provider': user_data.get('account_provider', ''),
                    'account_number': user_data.get('account_number', ''),
                    'picture': user_data.get('picture'),
                }
            )
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        try:
            user = User.objects.get(id=user_id)
            return UserJsonStorageService._user_to_dict(user)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def user_exists(user_id: str) -> bool:
        """Check if user exists."""
        return User.objects.filter(id=user_id).exists()
    
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
        users = User.objects.all()
        
        for user in users:
            if exclude_user_id and str(user.id) == exclude_user_id:
                continue
            user_cpf = user.cpf or ''
            if UserJsonStorageService.normalize_cpf(user_cpf) == normalized_cpf:
                return UserJsonStorageService._user_to_dict(user)
        
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
        queryset = User.objects.filter(account_number=account_number)
        if exclude_user_id:
            queryset = queryset.exclude(id=exclude_user_id)
        
        try:
            user = queryset.first()
            if user:
                return UserJsonStorageService._user_to_dict(user)
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def _user_to_dict(user: User) -> Dict:
        """Convert User model instance to dictionary."""
        return {
            'id': str(user.id),
            'name': user.name,
            'cpf': user.cpf,
            'account_provider': user.account_provider,
            'account_number': user.account_number,
            'picture': user.picture,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }
