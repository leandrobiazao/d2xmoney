"""
Django REST Framework serializers for brokerage notes.
"""
from rest_framework import serializers


class BrokerageNoteSerializer(serializers.Serializer):
    """Serializer for BrokerageNote model."""
    
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.CharField(required=True)
    file_name = serializers.CharField(required=True)
    original_file_path = serializers.CharField(allow_blank=True, required=False)
    processed_at = serializers.DateTimeField(read_only=True)
    note_date = serializers.CharField(required=True)
    note_number = serializers.CharField(required=True)
    operations_count = serializers.IntegerField(read_only=True)
    operations = serializers.ListField(required=True)
    status = serializers.ChoiceField(
        choices=['success', 'partial', 'failed'],
        required=True
    )
    error_message = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    
    def validate_note_number(self, value):
        """Validate that note_number is provided and not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Número da nota é obrigatório.")
        return value.strip()
    
    def validate_note_date(self, value):
        """Validate note_date format (DD/MM/YYYY)."""
        if not value:
            raise serializers.ValidationError("Data da nota é obrigatória.")
        # Basic format validation - should be DD/MM/YYYY
        import re
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', value):
            raise serializers.ValidationError("Formato de data inválido. Use DD/MM/YYYY.")
        return value

