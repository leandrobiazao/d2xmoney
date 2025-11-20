"""
Serializers for fixed income app.
"""
from decimal import Decimal
from rest_framework import serializers
from .models import FixedIncomePosition, TesouroDiretoPosition


class FixedIncomePositionSerializer(serializers.ModelSerializer):
    """Serializer for FixedIncomePosition."""
    
    investment_type_name = serializers.CharField(source='investment_type.name', read_only=True)
    investment_sub_type_name = serializers.CharField(source='investment_sub_type.name', read_only=True)
    
    def update(self, instance, validated_data):
        """Override update to calculate yields when applied_value changes."""
        # Only calculate yields if they're not explicitly provided in the update
        if 'gross_yield' not in validated_data or 'net_yield' not in validated_data:
            # Calculate yields if applied_value, position_value, or net_value are being updated
            applied_value = validated_data.get('applied_value', instance.applied_value)
            position_value = validated_data.get('position_value', instance.position_value)
            net_value = validated_data.get('net_value', instance.net_value)
            
            # Ensure Decimal types
            applied_value = Decimal(str(applied_value)) if applied_value else Decimal('0.00')
            position_value = Decimal(str(position_value)) if position_value else Decimal('0.00')
            net_value = Decimal(str(net_value)) if net_value else Decimal('0.00')
            
            # Calculate Rendimento Bruto = Position Value - Applied Value
            if 'gross_yield' not in validated_data:
                validated_data['gross_yield'] = position_value - applied_value
            
            # Calculate Rendimento Líquido = Net Value - Applied Value
            if 'net_yield' not in validated_data:
                validated_data['net_yield'] = net_value - applied_value
        
        return super().update(instance, validated_data)
    
    class Meta:
        model = FixedIncomePosition
        fields = [
            'id',
            'user_id',
            'asset_name',
            'asset_code',
            'application_date',
            'grace_period_end',
            'maturity_date',
            'price_date',
            'rate',
            'price',
            'quantity',
            'available_quantity',
            'guarantee_quantity',
            'applied_value',
            'position_value',
            'net_value',
            'gross_yield',
            'net_yield',
            'income_tax',
            'iof',
            'rating',
            'liquidity',
            'interest',
            'investment_type',
            'investment_type_name',
            'investment_sub_type',
            'investment_sub_type_name',
            'source',
            'import_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'import_date']


class TesouroDiretoPositionSerializer(serializers.ModelSerializer):
    """Serializer for TesouroDiretoPosition."""
    
    fixed_income_position = FixedIncomePositionSerializer(read_only=True)
    
    class Meta:
        model = TesouroDiretoPosition
        fields = [
            'id',
            'fixed_income_position',
            'titulo_name',
            'vencimento',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FixedIncomePositionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    
    investment_type_name = serializers.CharField(source='investment_type.name', read_only=True)
    investment_sub_type_name = serializers.CharField(source='investment_sub_type.name', read_only=True, allow_null=True)
    
    class Meta:
        model = FixedIncomePosition
        fields = [
            'id',
            'asset_name',
            'asset_code',
            'application_date',
            'maturity_date',
            'rate',
            'quantity',
            'available_quantity',
            'applied_value',
            'position_value',
            'net_value',
            'investment_type_name',
            'investment_sub_type_name',
            'investment_type',
            'investment_sub_type',
        ]


