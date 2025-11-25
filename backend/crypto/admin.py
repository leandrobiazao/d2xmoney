from django.contrib import admin
from .models import CryptoCurrency, CryptoOperation, CryptoPosition


@admin.register(CryptoCurrency)
class CryptoCurrencyAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'investment_type', 'investment_subtype', 'is_active', 'created_at']
    list_filter = ['is_active', 'investment_type', 'investment_subtype']
    search_fields = ['symbol', 'name']
    ordering = ['symbol']


@admin.register(CryptoOperation)
class CryptoOperationAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'crypto_currency', 'operation_type', 'quantity', 'price', 'operation_date', 'broker']
    list_filter = ['operation_type', 'operation_date', 'crypto_currency']
    search_fields = ['user_id', 'crypto_currency__symbol', 'crypto_currency__name', 'broker']
    ordering = ['-operation_date', '-created_at']
    date_hierarchy = 'operation_date'


@admin.register(CryptoPosition)
class CryptoPositionAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'crypto_currency', 'quantity', 'average_price', 'broker', 'updated_at']
    list_filter = ['crypto_currency', 'broker']
    search_fields = ['user_id', 'crypto_currency__symbol', 'crypto_currency__name', 'broker']
    ordering = ['user_id', 'crypto_currency__symbol']
