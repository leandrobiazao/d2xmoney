"""
URLs for allocation_strategies app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserAllocationStrategyViewSet

router = DefaultRouter()
router.register(r'allocation-strategies', UserAllocationStrategyViewSet, basename='allocation-strategy')

urlpatterns = [
    path('', include(router.urls)),
]


