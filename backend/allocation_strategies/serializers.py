"""
Serializers for allocation_strategies app.
"""
from rest_framework import serializers
from .models import (
    UserAllocationStrategy,
    InvestmentTypeAllocation,
    SubTypeAllocation,
    StockAllocation
)
from configuration.serializers import InvestmentTypeSerializer, InvestmentSubTypeSerializer
from stocks.serializers import StockSerializer


class StockAllocationSerializer(serializers.ModelSerializer):
    """Serializer for StockAllocation."""
    stock = StockSerializer(read_only=True)
    
    class Meta:
        model = StockAllocation
        fields = ['id', 'stock', 'target_percentage', 'display_order']
        read_only_fields = ['id']


class SubTypeAllocationSerializer(serializers.ModelSerializer):
    """Serializer for SubTypeAllocation."""
    sub_type = InvestmentSubTypeSerializer(read_only=True)
    stock_allocations = StockAllocationSerializer(many=True, read_only=True)
    
    class Meta:
        model = SubTypeAllocation
        fields = [
            'id', 'sub_type', 'custom_name', 'target_percentage',
            'display_order', 'stock_allocations'
        ]
        read_only_fields = ['id']


class InvestmentTypeAllocationSerializer(serializers.ModelSerializer):
    """Serializer for InvestmentTypeAllocation."""
    investment_type = InvestmentTypeSerializer(read_only=True)
    sub_type_allocations = SubTypeAllocationSerializer(many=True, read_only=True)
    
    class Meta:
        model = InvestmentTypeAllocation
        fields = [
            'id', 'investment_type', 'target_percentage',
            'display_order', 'sub_type_allocations'
        ]
        read_only_fields = ['id']


class UserAllocationStrategySerializer(serializers.ModelSerializer):
    """Serializer for UserAllocationStrategy."""
    type_allocations = InvestmentTypeAllocationSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = UserAllocationStrategy
        fields = [
            'id', 'user', 'user_name', 'total_portfolio_value',
            'created_at', 'updated_at', 'type_allocations'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


