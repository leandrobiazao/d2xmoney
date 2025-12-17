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
from .models import FixedIncomePosition, TesouroDiretoPosition, InvestmentFund
from .serializers import FixedIncomePositionSerializer, FixedIncomePositionListSerializer, TesouroDiretoPositionSerializer, InvestmentFundSerializer
from .services import PortfolioExcelImportService


class FixedIncomePositionViewSet(viewsets.ModelViewSet):
    """ViewSet for FixedIncomePosition."""
    
    queryset = FixedIncomePosition.objects.all()
    serializer_class = FixedIncomePositionSerializer
    
    def get_queryset(self):
        """Filter by user_id if provided."""
        queryset = FixedIncomePosition.objects.select_related('investment_type', 'investment_sub_type').all()
        user_id = self.request.query_params.get('user_id', None)
        investment_type = self.request.query_params.get('investment_type', None)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if investment_type:
            queryset = queryset.filter(investment_type__code=investment_type)
        
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


class InvestmentFundViewSet(viewsets.ModelViewSet):
    """ViewSet for Investment Funds."""
    
    queryset = InvestmentFund.objects.all()
    serializer_class = InvestmentFundSerializer
    
    def get_queryset(self):
        """Filter by user_id and fund_type if provided."""
        queryset = InvestmentFund.objects.all()
        user_id = self.request.query_params.get('user_id', None)
        fund_type = self.request.query_params.get('fund_type', None)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if fund_type:
            queryset = queryset.filter(fund_type=fund_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Get summary of investment funds by type for a user."""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        funds = InvestmentFund.objects.filter(user_id=user_id)
        
        # Group by fund type
        summary = {}
        total_position = 0
        
        for fund in funds:
            fund_type = fund.get_fund_type_display()
            if fund_type not in summary:
                summary[fund_type] = {
                    'count': 0,
                    'total_position': 0,
                    'total_net_value': 0,
                    'total_applied': 0,
                }
            
            summary[fund_type]['count'] += 1
            summary[fund_type]['total_position'] += float(fund.position_value)
            summary[fund_type]['total_net_value'] += float(fund.net_value)
            summary[fund_type]['total_applied'] += float(fund.applied_value)
            total_position += float(fund.position_value)
        
        # Calculate allocation percentages
        for fund_type in summary:
            if total_position > 0:
                summary[fund_type]['allocation_percent'] = (summary[fund_type]['total_position'] / total_position) * 100
            else:
                summary[fund_type]['allocation_percent'] = 0
        
        return Response({
            'summary': summary,
            'total_position': total_position,
            'total_funds': funds.count(),
        }, status=status.HTTP_200_OK)


