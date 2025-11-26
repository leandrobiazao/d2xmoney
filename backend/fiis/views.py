from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FIIProfile
from .serializers import FIIProfileSerializer

class FIIProfileListView(APIView):
    """List all FII profiles."""
    authentication_classes = []
    
    def get(self, request):
        profiles = FIIProfile.objects.select_related('stock').all()
        serializer = FIIProfileSerializer(profiles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FIIProfileDetailView(APIView):
    """Get a specific FII profile by ticker."""
    authentication_classes = []
    
    def get(self, request, ticker):
        try:
            profile = FIIProfile.objects.select_related('stock').get(stock__ticker=ticker)
            serializer = FIIProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FIIProfile.DoesNotExist:
            return Response(
                {'error': 'FII profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
