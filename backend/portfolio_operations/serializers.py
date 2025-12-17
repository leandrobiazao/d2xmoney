"""
Django REST Framework serializers for portfolio_operations app.
"""
from rest_framework import serializers
from .models import CorporateEvent


class CorporateEventSerializer(serializers.ModelSerializer):
    """Serializer for CorporateEvent model."""
    
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    asset_type_display = serializers.CharField(source='get_asset_type_display', read_only=True)
    
    class Meta:
        model = CorporateEvent
        fields = [
            'id',
            'ticker',
            'previous_ticker',
            'event_type',
            'event_type_display',
            'asset_type',
            'asset_type_display',
            'ex_date',
            'ratio',
            'description',
            'applied',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate event data based on event type."""
        event_type = data.get('event_type')
        
        # For TICKER_CHANGE, previous_ticker is required and ratio is not used
        if event_type == 'TICKER_CHANGE':
            if not data.get('previous_ticker'):
                raise serializers.ValidationError({
                    'previous_ticker': 'previous_ticker is required for TICKER_CHANGE events'
                })
            # Ratio is not needed for ticker changes
            data['ratio'] = ''
        # For FUND_CONVERSION, both previous_ticker and ratio are required
        elif event_type == 'FUND_CONVERSION':
            if not data.get('previous_ticker'):
                raise serializers.ValidationError({
                    'previous_ticker': 'previous_ticker is required for FUND_CONVERSION events (fundo extinto)'
                })
            if not data.get('ratio'):
                raise serializers.ValidationError({
                    'ratio': 'ratio is required for FUND_CONVERSION events (ex: 3:2 para 3 novas cotas para cada 2 antigas)'
                })
            # Validate ratio format
            self.validate_ratio(data['ratio'])
        else:
            # For other event types (GROUPING, SPLIT, BONUS, SUBSCRIPTION), ratio is required
            if not data.get('ratio'):
                raise serializers.ValidationError({
                    'ratio': 'ratio is required for this event type'
                })
            # Validate ratio format
            self.validate_ratio(data['ratio'])
            # previous_ticker should not be provided for these event types
            if data.get('previous_ticker'):
                data['previous_ticker'] = None
        
        return data
    
    def validate_ratio(self, value):
        """Validate ratio format (e.g., '20:1', '1:5')."""
        if not value:  # Allow empty ratio for TICKER_CHANGE
            return value
        
        try:
            parts = value.split(':')
            if len(parts) != 2:
                raise serializers.ValidationError("Ratio must be in format 'X:Y' (e.g., '20:1', '1:5')")
            numerator = float(parts[0])
            denominator = float(parts[1])
            if numerator <= 0 or denominator <= 0:
                raise serializers.ValidationError("Both numerator and denominator must be positive numbers")
            return value
        except ValueError:
            raise serializers.ValidationError("Ratio must contain valid numbers separated by ':'")

