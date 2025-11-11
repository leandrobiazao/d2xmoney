"""
URL configuration for portfolio_operations app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # New portfolio endpoints
    path('api/portfolio/', views.PortfolioListView.as_view(), name='portfolio-list'),
    path('api/portfolio/refresh/', views.PortfolioRefreshView.as_view(), name='portfolio-refresh'),
    
    # Legacy endpoints (kept for backward compatibility during migration)
    path('api/portfolio-operations/', views.PortfolioOperationsListView.as_view(), name='operations-list'),
    path('api/portfolio-operations/<str:operation_id>/', views.PortfolioOperationsDetailView.as_view(), name='operation-detail'),
    path('api/portfolio-operations/client/<str:client_id>/', views.PortfolioOperationsClientView.as_view(), name='client-operations'),
]
