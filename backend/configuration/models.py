"""
Django models for configuration app.
"""
from django.db import models


class InvestmentType(models.Model):
    """Investment type model for base investment categories."""
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'investment_types'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class InvestmentSubType(models.Model):
    """Investment sub-type model for sub-categories within investment types."""
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.CASCADE,
        related_name='sub_types'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, db_index=True)
    display_order = models.IntegerField(default=0)
    is_predefined = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'investment_sub_types'
        ordering = ['investment_type', 'display_order', 'name']
        unique_together = [['investment_type', 'code']]

    def __str__(self):
        return f"{self.investment_type.name} - {self.name}"
