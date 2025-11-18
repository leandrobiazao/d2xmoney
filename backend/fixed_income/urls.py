"""
URLs for fixed income app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FixedIncomePositionViewSet, TesouroDiretoPositionViewSet

router = DefaultRouter()
router.register(r'positions', FixedIncomePositionViewSet, basename='fixed-income-position')
router.register(r'tesouro-direto', TesouroDiretoPositionViewSet, basename='tesouro-direto-position')

urlpatterns = [
    path('', include(router.urls)),
]


