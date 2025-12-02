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
    note_number = serializers.CharField(required=True, allow_blank=True)
    operations_count = serializers.IntegerField(read_only=True)
    operations = serializers.ListField(required=True)
    status = serializers.ChoiceField(
        choices=['success', 'partial', 'failed'],
        required=True
    )
    error_message = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    
    # Resumo dos Negócios (Business Summary)
    debentures = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    vendas_a_vista = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    compras_a_vista = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    valor_das_operacoes = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    
    # Resumo Financeiro (Financial Summary)
    valor_liquido_operacoes = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    taxa_liquidacao = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    taxa_registro = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    total_cblc = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    emolumentos = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    taxa_transferencia_ativos = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    total_bovespa = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    
    # Custos Operacionais (Operational Costs)
    taxa_operacional = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    execucao = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    taxa_custodia = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    impostos = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    irrf_operacoes = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    irrf_base = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    outros_custos = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    total_custos_despesas = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    liquido = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False)
    liquido_data = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=False)
    
    def validate_note_number(self, value):
        """Validate note_number - allow empty string but normalize it."""
        if value is None:
            return ''
        value = value.strip()
        # If empty, use 'N/A' as default for display purposes
        if not value:
            return 'N/A'
        return value
    
    def validate_note_date(self, value):
        """Validate note_date format (DD/MM/YYYY)."""
        if not value:
            raise serializers.ValidationError("Data da nota é obrigatória.")
        # Basic format validation - should be DD/MM/YYYY
        import re
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', value):
            raise serializers.ValidationError("Formato de data inválido. Use DD/MM/YYYY.")
        return value

