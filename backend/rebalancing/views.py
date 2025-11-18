"""
Views for rebalancing app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import User
from .models import RebalancingRecommendation
from .serializers import RebalancingRecommendationSerializer
from .services import RebalancingService


class RebalancingRecommendationViewSet(viewsets.ModelViewSet):
    """ViewSet for RebalancingRecommendation."""
    queryset = RebalancingRecommendation.objects.all()
    serializer_class = RebalancingRecommendationSerializer
    
    def get_queryset(self):
        queryset = RebalancingRecommendation.objects.all()
        user_id = self.request.query_params.get('user_id')
        status_filter = self.request.query_params.get('status')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-recommendation_date', '-created_at')
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate monthly rebalancing recommendations for a user."""
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
        
        try:
            recommendation = RebalancingService.generate_monthly_recommendations(user)
            serializer = self.get_serializer(recommendation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Mark recommendation as applied."""
        recommendation = self.get_object()
        recommendation.status = 'applied'
        recommendation.save()
        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Mark recommendation as dismissed."""
        recommendation = self.get_object()
        recommendation.status = 'dismissed'
        recommendation.save()
        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)
