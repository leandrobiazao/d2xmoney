"""
URL configuration for ticker_mappings app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/ticker-mappings/', views.TickerMappingListView.as_view(), name='ticker-mapping-list'),
    path('api/ticker-mappings/<str:nome>/', views.TickerMappingDetailView.as_view(), name='ticker-mapping-detail'),
]
