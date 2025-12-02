"""
URL configuration for portfolio_operations app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Portfolio endpoints
    path('api/portfolio/', views.PortfolioListView.as_view(), name='portfolio-list'),
    path('api/portfolio/refresh/', views.PortfolioRefreshView.as_view(), name='portfolio-refresh'),
    path('api/portfolio/prices/', views.PortfolioPricesView.as_view(), name='portfolio-prices'),
    
    # Corporate events endpoints
    path('api/corporate-events/', views.CorporateEventListView.as_view(), name='corporate-event-list'),
    path('api/corporate-events/<int:event_id>/', views.CorporateEventDetailView.as_view(), name='corporate-event-detail'),
    path('api/corporate-events/<int:event_id>/apply/', views.CorporateEventApplyView.as_view(), name='corporate-event-apply'),
]
