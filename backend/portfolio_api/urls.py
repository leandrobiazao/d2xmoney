"""
URL configuration for portfolio_api project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Existing apps already include 'api/' in their URL patterns
    path('', include('users.urls')),
    path('', include('brokerage_notes.urls')),
    path('', include('ticker_mappings.urls')),
    path('', include('portfolio_operations.urls')),
    path('', include('clubedovalor.urls')),
    # New apps use router patterns without 'api/' prefix
    path('api/configuration/', include('configuration.urls')),
    path('api/stocks/', include('stocks.urls')),
    path('api/allocation-strategies/', include('allocation_strategies.urls')),
    path('api/ambb-strategy/', include('ambb_strategy.urls')),
    path('api/rebalancing/', include('rebalancing.urls')),
    path('api/fixed-income/', include('fixed_income.urls')),
    path('api/crypto/', include('crypto.urls')),
    path('', include('fiis.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

