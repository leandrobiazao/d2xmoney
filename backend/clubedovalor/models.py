"""
Models for Clube do Valor app.
"""
import uuid
from django.db import models


class StockSnapshot(models.Model):
    """Stock snapshot model for storing monthly snapshots of stock recommendations."""
    STRATEGY_CHOICES = [
        ('AMBB1', 'AMBB 1.0 - Ações mais baratas da bolsa'),
        ('AMBB2', 'AMBB 2.0 - Ações mais baratas da bolsa'),
        ('MDIV', 'Máquina de Dividendos'),
        ('MOMM', 'Momentum Melhores'),
        ('MOMP', 'Momentum Piores'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.CharField(max_length=50)  # ISO 8601 format string
    strategy_type = models.CharField(max_length=10, choices=STRATEGY_CHOICES, default='AMBB1', db_index=True)
    is_current = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_snapshots'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['strategy_type', 'is_current']),
            models.Index(fields=['strategy_type', '-timestamp']),
        ]

    def __str__(self):
        return f"Snapshot {self.timestamp} ({self.strategy_type}) (Current: {self.is_current})"


class Stock(models.Model):
    """Stock model for storing individual stock data within a snapshot.
    
    Supports multiple strategies:
    - AMBB1: Uses ebit field
    - AMBB2: Uses value_idx, cfy, btm, mktcap fields
    - MDIV: Uses dividend_yield_36m, liquidez_media_3m fields
    - MOMM: Uses momentum_6m, id_ratio, volume_mm, capitalizacao_mm, subsetor, segmento fields (Momentum Melhores)
    - MOMP: Uses momentum_6m, id_ratio, volume_mm, capitalizacao_mm, subsetor, segmento fields (Momentum Piores)
    """
    snapshot = models.ForeignKey(StockSnapshot, on_delete=models.CASCADE, related_name='stocks')
    ranking = models.IntegerField()
    codigo = models.CharField(max_length=20, db_index=True)
    nome = models.CharField(max_length=255)
    setor = models.CharField(max_length=255)
    observacao = models.TextField(blank=True, default='')
    
    # AMBB1 & AMBB2 fields
    earning_yield = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ev = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    liquidez = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cotacao_atual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # AMBB1 specific
    ebit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # AMBB2 specific
    value_idx = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cfy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # Cash Flow Yield
    btm = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Book to Market
    mktcap = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Market Cap
    
    # MDIV specific
    dividend_yield_36m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # 36-month average annual weighted
    liquidez_media_3m = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Average 3-month liquidity
    
    # MOM specific
    momentum_6m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # 6 months Momentum (%)
    id_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # ID ratio
    volume_mm = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Volume (MM)
    capitalizacao_mm = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Capitalização (MM)
    subsetor = models.CharField(max_length=255, blank=True, default='')  # Subsetor
    segmento = models.CharField(max_length=255, blank=True, default='')  # Segmento

    class Meta:
        db_table = 'stocks'
        ordering = ['ranking']
        unique_together = [['snapshot', 'codigo']]

    def __str__(self):
        return f"{self.codigo} - {self.nome} (Rank: {self.ranking})"
