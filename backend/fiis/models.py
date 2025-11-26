from django.db import models
from stocks.models import Stock


class FIIProfile(models.Model):
    """
    Profile model for Fundos Imobiliários (FIIs), extending the base Stock model.
    """
    stock = models.OneToOneField(
        Stock,
        on_delete=models.CASCADE,
        related_name='fii_profile'
    )
    segment = models.CharField(max_length=100, help_text="e.g., Tijolo:Shoppings")
    target_audience = models.CharField(max_length=100, help_text="e.g., Investidor Qualificado")
    administrator = models.CharField(max_length=255)
    
    # Financial Data
    last_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    base_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    
    # Additional Data
    average_yield_12m_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Rend. Méd. 12m (R$)"
    )
    average_yield_12m_percentage = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Rend. Méd. 12m (%)"
    )
    equity_per_share = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Patrimônio/Cota"
    )
    price_to_vp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Cotação/VP"
    )
    trades_per_month = models.IntegerField(
        null=True, blank=True,
        verbose_name="Nº negócios/mês"
    )
    ifix_participation = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Partic. IFIX"
    )
    shareholders_count = models.IntegerField(
        null=True, blank=True,
        verbose_name="Número Cotistas"
    )
    equity = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
        verbose_name="Patrimônio"
    )
    base_share_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Cota base"
    )

    class Meta:
        db_table = 'fii_profiles'
        verbose_name = 'FII Profile'
        verbose_name_plural = 'FII Profiles'

    def __str__(self):
        return f"Profile for {self.stock.ticker}"
