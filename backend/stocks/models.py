"""
Django models for stocks app.
"""
from django.db import models
from configuration.models import InvestmentType


class Stock(models.Model):
    """Stock model for master catalog of stocks."""
    
    FINANCIAL_MARKET_CHOICES = [
        ('B3', 'B3'),
        ('Nasdaq', 'Nasdaq'),
        ('NYExchange', 'NYSE'),
    ]
    
    STOCK_CLASS_CHOICES = [
        ('ON', 'ON'),
        ('PN', 'PN'),
        ('ETF', 'ETF'),
        ('BDR', 'BDR'),
    ]
    
    ticker = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, null=True, blank=True)
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stocks'
    )
    financial_market = models.CharField(
        max_length=20,
        choices=FINANCIAL_MARKET_CHOICES,
        default='B3'
    )
    stock_class = models.CharField(
        max_length=10,
        choices=STOCK_CLASS_CHOICES,
        default='ON'
    )
    current_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'stock_catalog'
        ordering = ['ticker']

    def __str__(self):
        return f"{self.ticker} - {self.name}"
