"""
Views for allocation_strategies app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from users.models import User
from .models import UserAllocationStrategy
from .serializers import UserAllocationStrategySerializer
from .services import AllocationStrategyService


class UserAllocationStrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for UserAllocationStrategy."""
    queryset = UserAllocationStrategy.objects.all()
    serializer_class = UserAllocationStrategySerializer
    
    def get_queryset(self):
        queryset = UserAllocationStrategy.objects.all()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset.order_by('user__name')
    
    @action(detail=False, methods=['post'])
    def create_strategy(self, request):
        """Create or update allocation strategy for a user."""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        type_allocations = request.data.get('type_allocations', [])
        total_portfolio_value = request.data.get('total_portfolio_value')
        
        try:
            strategy = AllocationStrategyService.create_or_update_strategy(
                user=user,
                type_allocations=type_allocations,
                total_portfolio_value=total_portfolio_value
            )
            serializer = self.get_serializer(strategy)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def current_vs_target(self, request):
        """Get current vs target allocation comparison."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        current = AllocationStrategyService.get_current_allocation(user)
        
        try:
            strategy = UserAllocationStrategy.objects.get(user=user)
            serializer = self.get_serializer(strategy)
            target = serializer.data
        except UserAllocationStrategy.DoesNotExist:
            target = None
        
        return Response({
            'current': current,
            'target': target
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def pie_chart_data(self, request):
        """Get pie chart data for allocation visualization."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        data = AllocationStrategyService.get_pie_chart_data(user)
        return Response(data, status=status.HTTP_200_OK)
