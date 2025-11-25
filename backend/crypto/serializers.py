"""
Serializers for crypto app.
"""
from rest_framework import serializers
from .models import CryptoCurrency, CryptoOperation, CryptoPosition
from configuration.serializers import InvestmentTypeSerializer, InvestmentSubTypeSerializer


class CryptoCurrencySerializer(serializers.ModelSerializer):
    """Serializer for CryptoCurrency."""
    investment_type = InvestmentTypeSerializer(read_only=True)
    investment_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    investment_subtype = InvestmentSubTypeSerializer(read_only=True)
    investment_subtype_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CryptoCurrency
        fields = [
            'id', 'symbol', 'name', 'investment_type', 'investment_type_id',
            'investment_subtype', 'investment_subtype_id', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        """Handle investment_type_id and investment_subtype_id updates."""
        investment_type_id = validated_data.pop('investment_type_id', None)
        investment_subtype_id = validated_data.pop('investment_subtype_id', None)
        
        # Handle investment_type_id
        if investment_type_id is not None:
            from configuration.models import InvestmentType
            try:
                if investment_type_id:
                    investment_type = InvestmentType.objects.get(id=investment_type_id)
                    instance.investment_type = investment_type
                else:
                    instance.investment_type = None
            except InvestmentType.DoesNotExist:
                pass
        
        # Handle investment_subtype_id
        if investment_subtype_id is not None:
            from configuration.models import InvestmentSubType
            try:
                if investment_subtype_id:
                    investment_subtype = InvestmentSubType.objects.get(id=investment_subtype_id)
                    instance.investment_subtype = investment_subtype
                else:
                    instance.investment_subtype = None
            except InvestmentSubType.DoesNotExist:
                pass
        
        # Call parent update
        instance = super().update(instance, validated_data)
        
        # Reload to ensure relationships are loaded
        from .models import CryptoCurrency
        instance = CryptoCurrency.objects.select_related('investment_type', 'investment_subtype').get(pk=instance.pk)
        
        return instance


class CryptoOperationSerializer(serializers.ModelSerializer):
    """Serializer for CryptoOperation."""
    crypto_currency = CryptoCurrencySerializer(read_only=True)
    crypto_currency_id = serializers.IntegerField(write_only=True)
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    
    class Meta:
        model = CryptoOperation
        fields = [
            'id', 'user_id', 'crypto_currency', 'crypto_currency_id',
            'operation_type', 'quantity', 'price', 'operation_date',
            'broker', 'notes', 'total_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create crypto operation and update position."""
        crypto_currency_id = validated_data.pop('crypto_currency_id')
        from .models import CryptoCurrency
        
        crypto_currency = CryptoCurrency.objects.get(id=crypto_currency_id)
        validated_data['crypto_currency'] = crypto_currency
        
        operation = CryptoOperation.objects.create(**validated_data)
        
        # Update position after operation (import here to avoid circular import)
        from .services import CryptoService
        CryptoService.update_position_from_operation(operation)
        
        return operation
    
    def update(self, instance, validated_data):
        """Update crypto operation and recalculate position."""
        # Update operation
        if 'crypto_currency_id' in validated_data:
            crypto_currency_id = validated_data.pop('crypto_currency_id')
            from .models import CryptoCurrency
            instance.crypto_currency = CryptoCurrency.objects.get(id=crypto_currency_id)
        
        user_id = instance.user_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Recalculate positions after update (import here to avoid circular import)
        from .services import CryptoService
        CryptoService.recalculate_user_positions(user_id)
        
        return instance


class CryptoPositionSerializer(serializers.ModelSerializer):
    """Serializer for CryptoPosition."""
    crypto_currency = CryptoCurrencySerializer(read_only=True)
    crypto_currency_id = serializers.IntegerField(write_only=True, required=False)
    total_invested = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    
    class Meta:
        model = CryptoPosition
        fields = [
            'id', 'user_id', 'crypto_currency', 'crypto_currency_id',
            'quantity', 'average_price', 'broker', 'total_invested',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

