"""
Serializers for stocks app.
"""
from rest_framework import serializers
from .models import Stock
from configuration.serializers import InvestmentTypeSerializer, InvestmentSubTypeSerializer


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock."""
    investment_type = InvestmentTypeSerializer(read_only=True)
    investment_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    investment_subtype = InvestmentSubTypeSerializer(read_only=True)
    investment_subtype_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'ticker', 'name', 'cnpj', 'investment_type', 'investment_type_id',
            'investment_subtype', 'investment_subtype_id',
            'financial_market', 'stock_class', 'current_price', 'last_updated', 'is_active'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def update(self, instance, validated_data):
        """Handle investment_type_id and investment_subtype_id updates."""
        investment_type_id = validated_data.pop('investment_type_id', None)
        investment_subtype_id = validated_data.pop('investment_subtype_id', None)
        
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
        
        # Handle investment_subtype_id by converting it to investment_subtype object
        investment_subtype_changed = False
        if investment_subtype_id is not None:
            from configuration.models import InvestmentSubType
            try:
                if investment_subtype_id:
                    investment_subtype = InvestmentSubType.objects.get(id=investment_subtype_id)
                    if instance.investment_subtype_id != investment_subtype_id:
                        instance.investment_subtype = investment_subtype
                        investment_subtype_changed = True
                else:
                    # Set to None to clear the relationship
                    if instance.investment_subtype_id is not None:
                        instance.investment_subtype = None
                        investment_subtype_changed = True
            except InvestmentSubType.DoesNotExist:
                # If investment subtype doesn't exist, skip the update
                pass
        
        # Call parent update to save all other fields
        instance = super().update(instance, validated_data)
        
        # Explicitly save the instance to persist investment_type and investment_subtype changes
        # This is necessary because they are read_only and won't be saved by parent update
        update_fields = []
        if investment_type_changed:
            update_fields.append('investment_type')
        if investment_subtype_changed:
            update_fields.append('investment_subtype')
        
        if update_fields:
            instance.save(update_fields=update_fields)
            # Reload instance from database with related objects to ensure they're available for serialization
            instance = Stock.objects.select_related('investment_type', 'investment_subtype').get(pk=instance.pk)
        
        return instance

