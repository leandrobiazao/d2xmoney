"""
Serializers for configuration app.
"""
from rest_framework import serializers
from .models import InvestmentType, InvestmentSubType


class InvestmentSubTypeSerializer(serializers.ModelSerializer):
    """Serializer for InvestmentSubType."""
    
    class Meta:
        model = InvestmentSubType
        fields = ['id', 'name', 'code', 'display_order', 'is_predefined', 'is_active']
        read_only_fields = ['id']


class InvestmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for InvestmentType."""
    sub_types = InvestmentSubTypeSerializer(many=True, read_only=True)
    
    class Meta:
        model = InvestmentType
        fields = ['id', 'name', 'code', 'display_order', 'is_active', 'sub_types']
        read_only_fields = ['id']


class InvestmentSubTypeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating InvestmentSubType."""
    
    class Meta:
        model = InvestmentSubType
        fields = ['id', 'investment_type', 'name', 'code', 'display_order', 'is_predefined', 'is_active']
        read_only_fields = ['id']


