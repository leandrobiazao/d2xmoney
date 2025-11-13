"""
Models for Clube do Valor app.
"""
import uuid
from django.db import models


class StockSnapshot(models.Model):
    """Stock snapshot model for storing monthly snapshots of stock recommendations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.CharField(max_length=50)  # ISO 8601 format string
    is_current = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_snapshots'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Snapshot {self.timestamp} (Current: {self.is_current})"


class Stock(models.Model):
    """Stock model for storing individual stock data within a snapshot."""
    snapshot = models.ForeignKey(StockSnapshot, on_delete=models.CASCADE, related_name='stocks')
    ranking = models.IntegerField()
    codigo = models.CharField(max_length=20, db_index=True)
    earning_yield = models.DecimalField(max_digits=6, decimal_places=2)
    nome = models.CharField(max_length=255)
    setor = models.CharField(max_length=255)
    ev = models.DecimalField(max_digits=15, decimal_places=2)
    ebit = models.DecimalField(max_digits=15, decimal_places=2)
    liquidez = models.DecimalField(max_digits=12, decimal_places=2)
    cotacao_atual = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'stocks'
        ordering = ['ranking']
        unique_together = [['snapshot', 'codigo']]

    def __str__(self):
        return f"{self.codigo} - {self.nome} (Rank: {self.ranking})"
