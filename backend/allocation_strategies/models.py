"""
Django models for allocation_strategies app.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from users.models import User
from configuration.models import InvestmentType, InvestmentSubType
from stocks.models import Stock


class UserAllocationStrategy(models.Model):
    """User allocation strategy model linking user to their allocation strategy."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='allocation_strategy'
    )
    total_portfolio_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_allocation_strategies'
        ordering = ['user__name']

    def __str__(self):
        return f"Strategy for {self.user.name}"


class InvestmentTypeAllocation(models.Model):
    """Allocation percentage for each investment type."""
    strategy = models.ForeignKey(
        UserAllocationStrategy,
        on_delete=models.CASCADE,
        related_name='type_allocations'
    )
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'investment_type_allocations'
        ordering = ['strategy', 'display_order']
        unique_together = [['strategy', 'investment_type']]

    def __str__(self):
        return f"{self.strategy.user.name} - {self.investment_type.name}: {self.target_percentage}%"


class SubTypeAllocation(models.Model):
    """Sub-allocation within investment type."""
    type_allocation = models.ForeignKey(
        InvestmentTypeAllocation,
        on_delete=models.CASCADE,
        related_name='sub_type_allocations'
    )
    sub_type = models.ForeignKey(
        InvestmentSubType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocations'
    )
    custom_name = models.CharField(max_length=255, null=True, blank=True)
    target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'sub_type_allocations'
        ordering = ['type_allocation', 'display_order']

    def __str__(self):
        name = self.sub_type.name if self.sub_type else self.custom_name
        return f"{self.type_allocation} - {name}: {self.target_percentage}%"


class StockAllocation(models.Model):
    """Specific stock allocations (for Ações strategies)."""
    sub_type_allocation = models.ForeignKey(
        SubTypeAllocation,
        on_delete=models.CASCADE,
        related_name='stock_allocations'
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'stock_allocations'
        ordering = ['sub_type_allocation', 'display_order']
        unique_together = [['sub_type_allocation', 'stock']]

    def __str__(self):
        return f"{self.sub_type_allocation} - {self.stock.ticker}: {self.target_percentage}%"


class FIIAllocation(models.Model):
    """FII allocations linking directly to InvestmentTypeAllocation (bypassing subtypes)."""
    type_allocation = models.ForeignKey(
        InvestmentTypeAllocation,
        on_delete=models.CASCADE,
        related_name='fii_allocations'
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='fii_allocations'
    )
    target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    display_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'fii_allocations'
        ordering = ['type_allocation', 'display_order']
        unique_together = [['type_allocation', 'stock']]

    def __str__(self):
        return f"{self.type_allocation} - {self.stock.ticker}: {self.target_percentage}%"
