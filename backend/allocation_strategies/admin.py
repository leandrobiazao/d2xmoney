"""
Django admin for allocation_strategies app.
"""
from django.contrib import admin
from .models import UserAllocationStrategy, InvestmentTypeAllocation, SubTypeAllocation, StockAllocation


@admin.register(UserAllocationStrategy)
class UserAllocationStrategyAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_portfolio_value', 'created_at', 'updated_at')
    search_fields = ('user__name', 'user__cpf')
    ordering = ('user__name',)


@admin.register(InvestmentTypeAllocation)
class InvestmentTypeAllocationAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'investment_type', 'target_percentage', 'display_order')
    list_filter = ('investment_type',)
    search_fields = ('strategy__user__name', 'investment_type__name')
    ordering = ('strategy', 'display_order')


@admin.register(SubTypeAllocation)
class SubTypeAllocationAdmin(admin.ModelAdmin):
    list_display = ('type_allocation', 'sub_type', 'custom_name', 'target_percentage', 'display_order')
    list_filter = ('type_allocation__investment_type',)
    search_fields = ('custom_name', 'sub_type__name')
    ordering = ('type_allocation', 'display_order')


@admin.register(StockAllocation)
class StockAllocationAdmin(admin.ModelAdmin):
    list_display = ('sub_type_allocation', 'stock', 'target_percentage', 'display_order')
    list_filter = ('stock__investment_type', 'stock__financial_market')
    search_fields = ('stock__ticker', 'stock__name')
    ordering = ('sub_type_allocation', 'display_order')
