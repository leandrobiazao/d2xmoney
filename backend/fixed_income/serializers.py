"""
Serializers for fixed income app.
"""
from rest_framework import serializers
from .models import FixedIncomePosition, TesouroDiretoPosition


class FixedIncomePositionSerializer(serializers.ModelSerializer):
    """Serializer for FixedIncomePosition."""
    
    investment_type_name = serializers.CharField(source='investment_type.name', read_only=True)
    investment_sub_type_name = serializers.CharField(source='investment_sub_type.name', read_only=True)
    
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
            'applied_value',
            'position_value',
            'net_value',
            'investment_type_name',
        ]


