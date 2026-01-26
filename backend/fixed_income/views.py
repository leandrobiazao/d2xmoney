"""
Views for fixed income app.
"""
import os
import tempfile
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import FixedIncomePosition, TesouroDiretoPosition
from .serializers import FixedIncomePositionSerializer, FixedIncomePositionListSerializer, TesouroDiretoPositionSerializer
from .services import PortfolioExcelImportService


class FixedIncomePositionViewSet(viewsets.ModelViewSet):
    """ViewSet for FixedIncomePosition."""
    
    queryset = FixedIncomePosition.objects.all()
    serializer_class = FixedIncomePositionSerializer
    
    def get_queryset(self):
        """Filter by user_id if provided. Exclude liquidated positions (position_value=0 and quantity=0)."""
        from django.db.models import Q
        from decimal import Decimal
        
        queryset = FixedIncomePosition.objects.select_related('investment_type', 'investment_sub_type').all()
        user_id = self.request.query_params.get('user_id', None)
        investment_type = self.request.query_params.get('investment_type', None)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if investment_type:
            queryset = queryset.filter(investment_type__code=investment_type)
        
        # Debug: Check liquidated positions before filtering
        all_positions = queryset.all()
        liquidated_before_filter = [
            pos for pos in all_positions 
            if pos.position_value == Decimal('0.00') and pos.quantity == Decimal('0.00')
        ]
        if liquidated_before_filter:
            print(f"DEBUG FILTER: Found {len(liquidated_before_filter)} liquidated positions before filter:")
            for pos in liquidated_before_filter[:5]:  # Show first 5
                print(f"  - {pos.asset_code}: quantity={pos.quantity}, position_value={pos.position_value}")
        
        # Exclude liquidated positions: position_value = 0 AND quantity = 0
        # Keep positions where position_value > 0 OR quantity > 0
        # Use __gte=0.01 to handle potential precision issues, or check for exact 0
        queryset = queryset.exclude(
            Q(position_value=Decimal('0.00')) & Q(quantity=Decimal('0.00'))
        )
        
        # Debug: Verify filtering worked
        after_filter = queryset.all()
        liquidated_after_filter = [
            pos for pos in after_filter 
            if pos.position_value == Decimal('0.00') and pos.quantity == Decimal('0.00')
        ]
        if liquidated_after_filter:
            print(f"DEBUG FILTER WARNING: {len(liquidated_after_filter)} liquidated positions still in queryset after filter!")
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Use list serializer for list action."""
        if self.action == 'list':
            return FixedIncomePositionListSerializer
        return FixedIncomePositionSerializer
    
    @action(detail=False, methods=['post'], url_path='import-excel')
    def import_excel(self, request):
        """Import positions from Excel file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"portfolio_import_{user_id}_{file.name}")
        
        try:
            with open(temp_file_path, 'wb+') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
            
            # Import from Excel
            results = PortfolioExcelImportService.import_from_excel(temp_file_path, user_id)
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return Response(results, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            import traceback
            error_details = traceback.format_exc()
            return Response(
                {'error': f'Import failed: {str(e)}', 'details': error_details},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TesouroDiretoPositionViewSet(viewsets.ModelViewSet):
    """ViewSet for TesouroDiretoPosition."""
    
    queryset = TesouroDiretoPosition.objects.all()
    serializer_class = TesouroDiretoPositionSerializer
    
    def get_queryset(self):
        """Filter by user_id if provided."""
        queryset = TesouroDiretoPosition.objects.all()
        user_id = self.request.query_params.get('user_id', None)
        
        if user_id:
            queryset = queryset.filter(fixed_income_position__user_id=user_id)
        
        return queryset.order_by('vencimento')


# InvestmentFundViewSet removed - InvestmentFund model was removed

