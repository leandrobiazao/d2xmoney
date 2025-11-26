from rest_framework import serializers
from .models import FIIProfile

class FIIProfileSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source='stock.ticker', read_only=True)
    stock_id = serializers.IntegerField(source='stock.id', read_only=True)
    
    class Meta:
        model = FIIProfile
        fields = [
            'id', 'stock_id', 'ticker', 'segment', 'target_audience', 
            'administrator', 'last_yield', 'dividend_yield', 'base_date',
            'payment_date', 'average_yield_12m_value', 'average_yield_12m_percentage',
            'equity_per_share', 'price_to_vp', 'trades_per_month',
            'ifix_participation', 'shareholders_count', 'equity', 'base_share_price'
        ]
