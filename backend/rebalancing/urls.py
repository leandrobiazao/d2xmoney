"""
URLs for rebalancing app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RebalancingRecommendationViewSet

router = DefaultRouter()
router.register(r'recommendations', RebalancingRecommendationViewSet, basename='rebalancing-recommendation')

urlpatterns = [
    path('', include(router.urls)),
]


