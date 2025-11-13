"""
Django models for ticker_mappings app.
"""
from django.db import models


class TickerMapping(models.Model):
    """Ticker mapping model for storing company name to ticker mappings."""
    company_name = models.CharField(max_length=255, unique=True, db_index=True)
    ticker = models.CharField(max_length=20)

    class Meta:
        db_table = 'ticker_mappings'
        ordering = ['company_name']

    def __str__(self):
        return f"{self.company_name} -> {self.ticker}"
