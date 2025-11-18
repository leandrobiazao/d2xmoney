"""
Serializers for rebalancing app.
"""
from rest_framework import serializers
from .models import RebalancingRecommendation, RebalancingAction
from stocks.serializers import StockSerializer


class RebalancingActionSerializer(serializers.ModelSerializer):
    """Serializer for RebalancingAction."""
    stock = StockSerializer(read_only=True)
    
    class Meta:
        model = RebalancingAction
        fields = [
            'id', 'action_type', 'stock', 'current_value', 'target_value',
            'difference', 'quantity_to_buy', 'quantity_to_sell', 'display_order'
        ]
        read_only_fields = ['id']


class RebalancingRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for RebalancingRecommendation."""
    actions = RebalancingActionSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = RebalancingRecommendation
        fields = [
            'id', 'user', 'user_name', 'strategy', 'recommendation_date',
            'status', 'created_at', 'updated_at', 'actions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


