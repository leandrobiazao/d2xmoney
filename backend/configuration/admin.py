"""
Django admin for configuration app.
"""
from django.contrib import admin
from .models import InvestmentType, InvestmentSubType


@admin.register(InvestmentType)
class InvestmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('display_order', 'name')


@admin.register(InvestmentSubType)
class InvestmentSubTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'investment_type', 'code', 'display_order', 'is_predefined', 'is_active')
    list_filter = ('investment_type', 'is_predefined', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('investment_type', 'display_order', 'name')
