"""
URL configuration for clubedovalor app.
"""
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    path('api/clubedovalor/', views.ClubeDoValorListView.as_view(), name='clubedovalor-list'),
    path('api/clubedovalor/history/', views.ClubeDoValorHistoryView.as_view(), name='clubedovalor-history'),
    path('api/clubedovalor/refresh/', csrf_exempt(views.ClubeDoValorRefreshView.as_view()), name='clubedovalor-refresh'),
    path('api/clubedovalor/stocks/<str:codigo>/', views.ClubeDoValorStockDetailView.as_view(), name='clubedovalor-stock-detail'),
]

