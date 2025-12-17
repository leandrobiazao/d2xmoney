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


class CorporateEvent(models.Model):
    """
    Corporate event model for tracking events that affect stock/FII quantities and prices.
    Examples: groupings (reverse splits), splits, bonuses, etc.
    """
    EVENT_TYPE_CHOICES = [
        ('GROUPING', 'Grupamento (Reverse Split)'),
        ('SPLIT', 'Desdobramento (Split)'),
        ('BONUS', 'Bonificação'),
        ('SUBSCRIPTION', 'Subscrição'),
        ('TICKER_CHANGE', 'Mudança de Ticker/Nome'),
        ('FUND_CONVERSION', 'Extinção/Conversão de Fundo'),
    ]
    
    ASSET_TYPE_CHOICES = [
        ('STOCK', 'Ação'),
        ('FII', 'Fundo Imobiliário (FII)'),
    ]
    
    ticker = models.CharField(max_length=20, db_index=True, help_text="Ticker da ação ou FII (novo ticker para TICKER_CHANGE/FUND_CONVERSION)")
    previous_ticker = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Ticker anterior (usado para TICKER_CHANGE e FUND_CONVERSION - fundo extinto)"
    )
    event_type = models.CharField(
        max_length=20, 
        choices=EVENT_TYPE_CHOICES,
        help_text="Tipo de evento corporativo"
    )
    asset_type = models.CharField(
        max_length=10,
        choices=ASSET_TYPE_CHOICES,
        default='STOCK',
        help_text="Tipo de ativo (Ação ou FII)"
    )
    ex_date = models.DateField(help_text="Data ex-evento (data a partir da qual o evento é efetivo)")
    ratio = models.CharField(
        max_length=20,
        blank=True,
        help_text="Proporção do evento, ex: '20:1' para grupamento, '1:5' para split, '3:2' para conversão (novas:antigas)"
    )
    description = models.TextField(blank=True, help_text="Descrição detalhada do evento")
    applied = models.BooleanField(
        default=False,
        help_text="Indica se o ajuste já foi aplicado ao portfólio"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'corporate_events'
        ordering = ['-ex_date', 'ticker']
        indexes = [
            models.Index(fields=['ticker', 'ex_date']),
            models.Index(fields=['asset_type']),
        ]
    
    def __str__(self):
        return f"{self.ticker} - {self.get_event_type_display()} - {self.ex_date}"
    
    def parse_ratio(self):
        """Parse ratio string (e.g., '20:1') into numerator and denominator."""
        try:
            parts = self.ratio.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid ratio format: {self.ratio}")
            numerator = float(parts[0])
            denominator = float(parts[1])
            return numerator, denominator
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid ratio format '{self.ratio}': {e}")