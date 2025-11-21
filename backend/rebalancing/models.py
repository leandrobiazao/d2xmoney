"""
Django models for rebalancing app.
"""
from django.db import models
from users.models import User
from allocation_strategies.models import UserAllocationStrategy
from stocks.models import Stock


class RebalancingRecommendation(models.Model):
    """Monthly rebalancing recommendations."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('applied', 'Applied'),
        ('dismissed', 'Dismissed'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rebalancing_recommendations'
    )
    strategy = models.ForeignKey(
        UserAllocationStrategy,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    recommendation_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    total_sales_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.0,
        help_text="Total value of sales for Ações em Reais (capped at 19,000 Reais)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rebalancing_recommendations'
        ordering = ['-recommendation_date', '-created_at']

    def __str__(self):
        return f"Recommendation for {self.user.name} - {self.recommendation_date}"


class RebalancingAction(models.Model):
    """Individual actions within a recommendation."""
    
    ACTION_TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('rebalance', 'Rebalance'),
    ]
    
    recommendation = models.ForeignKey(
        RebalancingRecommendation,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPE_CHOICES
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rebalancing_actions'
    )
    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    target_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    difference = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    quantity_to_buy = models.IntegerField(null=True, blank=True)
    quantity_to_sell = models.IntegerField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    reason = models.CharField(max_length=255, null=True, blank=True, help_text='Reason for this action (e.g., "Not in AMBB 2.0" or "Rank X > 30")')

    class Meta:
        db_table = 'rebalancing_actions'
        ordering = ['recommendation', 'display_order']

    def __str__(self):
        stock_name = self.stock.ticker if self.stock else "N/A"
        return f"{self.action_type} - {stock_name}: {self.difference}"
