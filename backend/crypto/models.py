"""
Django models for crypto app.
"""
from django.db import models
from configuration.models import InvestmentType, InvestmentSubType


class CryptoCurrency(models.Model):
    """Crypto currency model for master catalog of cryptocurrencies."""
    
    symbol = models.CharField(max_length=20, unique=True, db_index=True)  # e.g., "BTC", "ETH"
    name = models.CharField(max_length=255)  # e.g., "Bitcoin", "Ethereum"
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crypto_currencies'
    )
    investment_subtype = models.ForeignKey(
        InvestmentSubType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crypto_currencies'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crypto_currencies'
        ordering = ['symbol']
        verbose_name = 'Crypto Currency'
        verbose_name_plural = 'Crypto Currencies'

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class CryptoOperation(models.Model):
    """Crypto operation model for tracking buy/sell operations."""
    
    OPERATION_TYPE_CHOICES = [
        ('BUY', 'Compra'),
        ('SELL', 'Venda'),
    ]
    
    user_id = models.CharField(max_length=100, db_index=True)
    crypto_currency = models.ForeignKey(
        CryptoCurrency,
        on_delete=models.PROTECT,
        related_name='operations'
    )
    operation_type = models.CharField(
        max_length=10,
        choices=OPERATION_TYPE_CHOICES
    )
    quantity = models.DecimalField(max_digits=30, decimal_places=18)  # Crypto quantities need high precision
    price = models.DecimalField(max_digits=20, decimal_places=2)  # Price per unit
    operation_date = models.DateField()
    broker = models.CharField(max_length=255, null=True, blank=True)  # Broker name
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crypto_operations'
        ordering = ['-operation_date', '-created_at']
        indexes = [
            models.Index(fields=['user_id', 'operation_date']),
            models.Index(fields=['crypto_currency', 'operation_date']),
        ]

    def __str__(self):
        return f"{self.operation_type} {self.quantity} {self.crypto_currency.symbol} on {self.operation_date}"

    @property
    def total_value(self):
        """Calculate total value of the operation."""
        return self.quantity * self.price


class CryptoPosition(models.Model):
    """Crypto position model for tracking current positions."""
    
    user_id = models.CharField(max_length=100, db_index=True)
    crypto_currency = models.ForeignKey(
        CryptoCurrency,
        on_delete=models.PROTECT,
        related_name='positions'
    )
    quantity = models.DecimalField(max_digits=30, decimal_places=18, default=0)  # Crypto quantities need high precision
    average_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    broker = models.CharField(max_length=255, null=True, blank=True)  # Broker name
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crypto_positions'
        ordering = ['crypto_currency__symbol']
        unique_together = [['user_id', 'crypto_currency']]
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['crypto_currency']),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.quantity} {self.crypto_currency.symbol} @ {self.average_price}"

    @property
    def total_invested(self):
        """Calculate total invested value."""
        return self.quantity * self.average_price
