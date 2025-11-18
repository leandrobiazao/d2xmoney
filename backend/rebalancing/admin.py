"""
Django admin for rebalancing app.
"""
from django.contrib import admin
from .models import RebalancingRecommendation, RebalancingAction


@admin.register(RebalancingRecommendation)
class RebalancingRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'recommendation_date', 'status', 'created_at')
    list_filter = ('status', 'recommendation_date')
    search_fields = ('user__name', 'user__cpf')
    ordering = ('-recommendation_date', '-created_at')


@admin.register(RebalancingAction)
class RebalancingActionAdmin(admin.ModelAdmin):
    list_display = ('recommendation', 'action_type', 'stock', 'current_value', 'target_value', 'difference')
    list_filter = ('action_type', 'recommendation__status')
    search_fields = ('stock__ticker', 'stock__name', 'recommendation__user__name')
    ordering = ('recommendation', 'display_order')
