"""
Views for configuration app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import os
from .models import InvestmentType, InvestmentSubType
from .serializers import InvestmentTypeSerializer, InvestmentSubTypeSerializer, InvestmentSubTypeCreateSerializer
from .services import ConfigurationService


class InvestmentTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for InvestmentType."""
    queryset = InvestmentType.objects.all()
    serializer_class = InvestmentTypeSerializer
    
    def get_queryset(self):
        queryset = InvestmentType.objects.all()
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('display_order', 'name')


class InvestmentSubTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for InvestmentSubType."""
    queryset = InvestmentSubType.objects.all()
    serializer_class = InvestmentSubTypeSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvestmentSubTypeCreateSerializer
        return InvestmentSubTypeSerializer
    
    def get_queryset(self):
        queryset = InvestmentSubType.objects.all()
        investment_type_id = self.request.query_params.get('investment_type_id')
        if investment_type_id:
            queryset = queryset.filter(investment_type_id=investment_type_id)
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('investment_type', 'display_order', 'name')
    
    @action(detail=False, methods=['post'])
    def import_excel(self, request):
        """Import sub-types from Excel file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        investment_type_code = request.data.get('investment_type_code')
        if not investment_type_code:
            return Response(
                {'error': 'investment_type_code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        sheet_name = request.data.get('sheet_name')
        
        # Save uploaded file temporarily
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.name)
        with open(temp_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        try:
            result = ConfigurationService.import_sub_types_from_excel(
                temp_path,
                investment_type_code,
                sheet_name
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
