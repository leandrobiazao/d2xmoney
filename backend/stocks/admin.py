"""
Django admin for stocks app.
"""
from django.contrib import admin
from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'name', 'investment_type', 'financial_market', 'stock_class', 'current_price', 'is_active')
    list_filter = ('investment_type', 'financial_market', 'stock_class', 'is_active')
    search_fields = ('ticker', 'name', 'cnpj')
    ordering = ('ticker',)
