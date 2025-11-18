"""
Serializers for stocks app.
"""
from rest_framework import serializers
from .models import Stock
from configuration.serializers import InvestmentTypeSerializer


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock."""
    investment_type = InvestmentTypeSerializer(read_only=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'ticker', 'name', 'cnpj', 'investment_type',
            'financial_market', 'stock_class', 'current_price', 'last_updated', 'is_active'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def to_internal_value(self, data):
        """Handle investment_type_id in input."""
        if 'investment_type_id' in data:
            data = data.copy()
            data['investment_type'] = data.pop('investment_type_id')
        return super().to_internal_value(data)

