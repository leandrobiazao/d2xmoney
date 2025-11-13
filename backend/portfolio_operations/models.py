"""
Django models for portfolio_operations app.
"""
from django.db import models


class PortfolioPosition(models.Model):
    """Portfolio position model for storing aggregated portfolio summaries."""
    user_id = models.CharField(max_length=100, db_index=True)  # Store as string to match existing UUID format
    ticker = models.CharField(max_length=20, db_index=True)
    quantidade = models.IntegerField(default=0)
    preco_medio = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    valor_total_investido = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    lucro_realizado = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'portfolio_positions'
        unique_together = [['user_id', 'ticker']]
        ordering = ['ticker']

    def __str__(self):
        return f"{self.user_id} - {self.ticker}: {self.quantidade}"
