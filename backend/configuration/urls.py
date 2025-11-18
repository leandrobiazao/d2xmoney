"""
URLs for configuration app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvestmentTypeViewSet, InvestmentSubTypeViewSet

router = DefaultRouter()
router.register(r'investment-types', InvestmentTypeViewSet, basename='investment-type')
router.register(r'investment-subtypes', InvestmentSubTypeViewSet, basename='investment-subtype')

urlpatterns = [
    path('', include(router.urls)),
]


