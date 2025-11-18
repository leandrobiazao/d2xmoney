"""
Views for ambb_strategy app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import User
from .services import AMBBStrategyService


class AMBBStrategyViewSet(viewsets.ViewSet):
    """ViewSet for AMBB strategy."""
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get AMBB rebalancing recommendations for a user."""
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
        
        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(user)
        return Response(recommendations, status=status.HTTP_200_OK)
