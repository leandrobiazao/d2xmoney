"""
URL configuration for portfolio_operations app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Portfolio endpoints
    path('api/portfolio/', views.PortfolioListView.as_view(), name='portfolio-list'),
    path('api/portfolio/refresh/', views.PortfolioRefreshView.as_view(), name='portfolio-refresh'),
]
