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
        # #region agent log
        import json as json_module
        try:
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A', 'location': 'services.py:20', 'message': 'load_users() entry', 'data': {}}, ensure_ascii=False) + '\n')
        except Exception as log_err:
            print(f"DEBUG LOG ERROR: {log_err}")
        print("DEBUG: load_users() called")
        # #endregion
        # #region agent log
        try:
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A', 'location': 'services.py:22', 'message': 'Before User.objects.all()', 'data': {'User_model': str(User)}}, ensure_ascii=False) + '\n')
        except Exception as log_err:
            print(f"DEBUG LOG ERROR: {log_err}")
        # #endregion
        users = User.objects.all()
        # #region agent log
        with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A', 'location': 'services.py:23', 'message': 'After User.objects.all()', 'data': {'queryset_type': str(type(users)), 'queryset_count': users.count() if hasattr(users, 'count') else 'unknown'}}, ensure_ascii=False) + '\n')
        # #endregion
        result = []
        for idx, user in enumerate(users):
            # #region agent log
            with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'C', 'location': 'services.py:26', 'message': 'Before _user_to_dict()', 'data': {'user_idx': idx, 'user_id': str(user.id) if hasattr(user, 'id') else 'no_id', 'user_created_at': str(user.created_at) if hasattr(user, 'created_at') else 'no_attr', 'user_updated_at': str(user.updated_at) if hasattr(user, 'updated_at') else 'no_attr'}}, ensure_ascii=False) + '\n')
            # #endregion
            try:
                user_dict = UserJsonStorageService._user_to_dict(user)
                # #region agent log
                with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'C', 'location': 'services.py:30', 'message': 'After _user_to_dict()', 'data': {'user_idx': idx, 'user_dict_keys': list(user_dict.keys()) if isinstance(user_dict, dict) else 'not_dict'}}, ensure_ascii=False) + '\n')
                # #endregion
                result.append(user_dict)
            except Exception as e:
                # #region agent log
                with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'C', 'location': 'services.py:33', 'message': 'Exception in _user_to_dict()', 'data': {'user_idx': idx, 'error': str(e), 'error_type': type(e).__name__}}, ensure_ascii=False) + '\n')
                # #endregion
                raise
        # #region agent log
        with open('c:\\app\\d2xmoney\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({'sessionId': 'debug-session', 'runId': 'run1', 'hypothesisId': 'A,B,C', 'location': 'services.py:37', 'message': 'load_users() returning', 'data': {'result_count': len(result)}}, ensure_ascii=False) + '\n')
        # #endregion
        return result
    
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
