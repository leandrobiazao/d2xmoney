"""
Serializers for stocks app.
"""
from rest_framework import serializers
from .models import Stock
from configuration.serializers import InvestmentTypeSerializer


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock."""
    investment_type = InvestmentTypeSerializer(read_only=True)
    investment_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'ticker', 'name', 'cnpj', 'investment_type', 'investment_type_id',
            'financial_market', 'stock_class', 'current_price', 'last_updated', 'is_active'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def update(self, instance, validated_data):
        """Handle investment_type_id update."""
        investment_type_id = validated_data.pop('investment_type_id', None)
        
        # Handle investment_type_id by converting it to investment_type object
        # Since investment_type is read_only, we need to set it directly on the instance
        investment_type_changed = False
        if investment_type_id is not None:
            from configuration.models import InvestmentType
            try:
                if investment_type_id:
                    investment_type = InvestmentType.objects.get(id=investment_type_id)
                    if instance.investment_type_id != investment_type_id:
                        instance.investment_type = investment_type
                        investment_type_changed = True
                else:
                    # Set to None to clear the relationship
                    if instance.investment_type_id is not None:
                        instance.investment_type = None
                        investment_type_changed = True
            except InvestmentType.DoesNotExist:
                # If investment type doesn't exist, skip the update
                pass
        
        # Call parent update to save all other fields
        instance = super().update(instance, validated_data)
        
        # Explicitly save the instance to persist investment_type changes
        # This is necessary because investment_type is read_only and won't be saved by parent update
        if investment_type_changed:
            instance.save(update_fields=['investment_type'])
            # Reload instance from database with related investment_type to ensure it's available for serialization
            instance = Stock.objects.select_related('investment_type').get(pk=instance.pk)
        
        return instance

