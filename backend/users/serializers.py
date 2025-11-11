"""
Django REST Framework serializers for users.
"""
import re
from rest_framework import serializers
from django.core.files.uploadedfile import InMemoryUploadedFile
from .services import UserJsonStorageService


def validate_cpf_checksum(cpf: str) -> bool:
    """Validate Brazilian CPF checksum algorithm."""
    # Remove formatting
    cpf_digits = re.sub(r'[^\d]', '', cpf)
    
    if len(cpf_digits) != 11:
        return False
    
    # Check if all digits are the same (invalid CPF)
    if len(set(cpf_digits)) == 1:
        return False
    
    # Calculate first check digit
    sum_val = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    remainder = sum_val % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cpf_digits[9]) != first_digit:
        return False
    
    # Calculate second check digit
    sum_val = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    remainder = sum_val % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cpf_digits[10]) == second_digit


class UserSerializer(serializers.Serializer):
    """Serializer for User model."""
    
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=200, required=True)
    cpf = serializers.CharField(max_length=14, required=True)
    account_provider = serializers.CharField(max_length=100, required=True)
    account_number = serializers.CharField(max_length=50, required=True)
    picture = serializers.ImageField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def validate_cpf(self, value: str) -> str:
        """Validate CPF format, checksum, and uniqueness."""
        # Remove formatting
        cpf_digits = re.sub(r'[^\d]', '', value)
        
        # Check length
        if len(cpf_digits) != 11:
            raise serializers.ValidationError("CPF must have 11 digits")
        
        # Format as XXX.XXX.XXX-XX
        formatted_cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
        
        # Validate checksum
        if not validate_cpf_checksum(cpf_digits):
            raise serializers.ValidationError("Invalid CPF checksum")
        
        # Check uniqueness
        # Get exclude_user_id from context if available (for updates)
        exclude_user_id = None
        if hasattr(self, 'context') and self.context:
            exclude_user_id = self.context.get('exclude_user_id')
        elif hasattr(self, 'instance') and self.instance:
            # If instance exists, it's an update - exclude current user
            exclude_user_id = self.instance.get('id') if isinstance(self.instance, dict) else None
        
        existing_user = UserJsonStorageService.get_user_by_cpf(formatted_cpf, exclude_user_id=exclude_user_id)
        if existing_user:
            raise serializers.ValidationError("CPF já cadastrado")
        
        return formatted_cpf
    
    def validate_account_number(self, value: str) -> str:
        """Validate account number format and uniqueness."""
        if not re.match(r'^[A-Za-z0-9\-]+$', value):
            raise serializers.ValidationError("Account number must be alphanumeric")
        
        # Check uniqueness
        # Get exclude_user_id from context if available (for updates)
        exclude_user_id = None
        if hasattr(self, 'context') and self.context:
            exclude_user_id = self.context.get('exclude_user_id')
        elif hasattr(self, 'instance') and self.instance:
            # If instance exists, it's an update - exclude current user
            exclude_user_id = self.instance.get('id') if isinstance(self.instance, dict) else None
        
        existing_user = UserJsonStorageService.get_user_by_account_number(value, exclude_user_id=exclude_user_id)
        if existing_user:
            raise serializers.ValidationError("Número da conta já cadastrado")
        
        return value
    
    def validate_picture(self, value: InMemoryUploadedFile) -> InMemoryUploadedFile:
        """Validate picture file."""
        if value is None:
            return value
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError("File size exceeds 5MB")
        
        return value

