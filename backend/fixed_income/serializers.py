"""
Serializers for fixed income app.
"""
from decimal import Decimal
from rest_framework import serializers
from .models import FixedIncomePosition, TesouroDiretoPosition, InvestmentFund
from configuration.serializers import InvestmentTypeSerializer, InvestmentSubTypeSerializer


class FixedIncomePositionSerializer(serializers.ModelSerializer):
    """Serializer for FixedIncomePosition."""
    
    investment_type = InvestmentTypeSerializer(read_only=True)
    investment_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    investment_type_name = serializers.CharField(source='investment_type.name', read_only=True)
    investment_sub_type = InvestmentSubTypeSerializer(read_only=True)
    investment_sub_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    investment_sub_type_name = serializers.CharField(source='investment_sub_type.name', read_only=True)
    
    def update(self, instance, validated_data):
        """Override update to calculate yields when applied_value changes and handle investment type/subtype updates."""
        # Handle investment_type_id and investment_sub_type_id updates
        investment_type_id = validated_data.pop('investment_type_id', None)
        investment_sub_type_id = validated_data.pop('investment_sub_type_id', None)
        
        # Handle investment_type_id
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
                    if instance.investment_type_id is not None:
                        instance.investment_type = None
                        investment_type_changed = True
            except InvestmentType.DoesNotExist:
                pass
        
        # Handle investment_sub_type_id
        investment_sub_type_changed = False
        if investment_sub_type_id is not None:
            from configuration.models import InvestmentSubType
            try:
                if investment_sub_type_id:
                    investment_sub_type = InvestmentSubType.objects.get(id=investment_sub_type_id)
                    if instance.investment_sub_type_id != investment_sub_type_id:
                        instance.investment_sub_type = investment_sub_type
                        investment_sub_type_changed = True
                else:
                    if instance.investment_sub_type_id is not None:
                        instance.investment_sub_type = None
                        investment_sub_type_changed = True
            except InvestmentSubType.DoesNotExist:
                pass
        
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
        
        # Call parent update to save all other fields
        instance = super().update(instance, validated_data)
        
        # Explicitly save the instance to persist investment_type and investment_sub_type changes
        update_fields = []
        if investment_type_changed:
            update_fields.append('investment_type')
        if investment_sub_type_changed:
            update_fields.append('investment_sub_type')
        
        if update_fields:
            instance.save(update_fields=update_fields)
            # Reload instance from database with related objects
            instance = FixedIncomePosition.objects.select_related('investment_type', 'investment_sub_type').get(pk=instance.pk)
        
        return instance
    
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
            'investment_type_id',
            'investment_type_name',
            'investment_sub_type',
            'investment_sub_type_id',
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


class InvestmentFundSerializer(serializers.ModelSerializer):
    """Serializer for Investment Fund model."""
    
    fund_type_display = serializers.CharField(source='get_fund_type_display', read_only=True)
    allocation_percent = serializers.SerializerMethodField()
    investment_type = serializers.PrimaryKeyRelatedField(read_only=True)
    investment_sub_type = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = InvestmentFund
        fields = [
            'id',
            'user_id',
            'fund_name',
            'fund_cnpj',
            'fund_type',
            'fund_type_display',
            'investment_type',
            'investment_sub_type',
            'quota_date',
            'quota_value',
            'quota_quantity',
            'in_quotation',
            'position_value',
            'net_value',
            'applied_value',
            'gross_return_percent',
            'net_return_percent',
            'source',
            'import_date',
            'created_at',
            'updated_at',
            'allocation_percent',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'import_date', 'allocation_percent']
    
    def get_allocation_percent(self, obj):
        """Calculate allocation percentage (can be enhanced with total portfolio value)."""
        # This is a placeholder - in a real scenario, you'd pass total portfolio value
        return None


