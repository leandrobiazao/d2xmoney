"""
URLs for crypto app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CryptoCurrencyViewSet, 
    CryptoOperationViewSet, 
    CryptoPositionViewSet,
    CryptoPriceViewSet
)

router = DefaultRouter()
router.register(r'currencies', CryptoCurrencyViewSet, basename='crypto-currency')
router.register(r'operations', CryptoOperationViewSet, basename='crypto-operation')
router.register(r'positions', CryptoPositionViewSet, basename='crypto-position')
router.register(r'prices', CryptoPriceViewSet, basename='crypto-price')

urlpatterns = [
    path('', include(router.urls)),
]

