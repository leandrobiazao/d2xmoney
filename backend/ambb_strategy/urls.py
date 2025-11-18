"""
URLs for ambb_strategy app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AMBBStrategyViewSet

router = DefaultRouter()
router.register(r'ambb-strategy', AMBBStrategyViewSet, basename='ambb-strategy')

urlpatterns = [
    path('', include(router.urls)),
]


