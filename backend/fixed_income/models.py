"""
Django models for fixed_income app.
"""
from django.db import models
from configuration.models import InvestmentType, InvestmentSubType


class FixedIncomePosition(models.Model):
    """Fixed Income Position model for tracking CDB and other fixed income investments."""
    
    # Basic identification
    user_id = models.CharField(max_length=100, db_index=True)
    asset_name = models.CharField(max_length=255)  # e.g., "CDB BANCO MASTER S/A - DEZ/2026"
    asset_code = models.CharField(max_length=100, db_index=True)  # e.g., "CDB PRE DU CDB1202HZPT"
    
    # Dates
    application_date = models.DateField()  # Data de aplicação
    grace_period_end = models.DateField(null=True, blank=True)  # Carência
    maturity_date = models.DateField()  # Vencimento
    price_date = models.DateField(null=True, blank=True)  # Data do preço
    
    # Financial metrics
    rate = models.CharField(max_length=20, null=True, blank=True)  # e.g., "+9,00%"
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Preço
    quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Quantidade
    available_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Disponível
    guarantee_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Garantia
    
    # Values
    applied_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Valor aplicado
    position_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Posição
    net_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Valor líquido
    gross_yield = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Rendimento bruto
    net_yield = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Rendimento líquido
    
    # Taxes
    income_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # IR
    iof = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # IOF
    
    # Attributes
    rating = models.CharField(max_length=100, null=True, blank=True)  # e.g., "CC Fitch"
    liquidity = models.CharField(max_length=100, null=True, blank=True)  # e.g., "Sem Liquidez"
    interest = models.CharField(max_length=100, null=True, blank=True)  # Juros
    
    # Investment type relationships
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='fixed_income_positions'
    )
    investment_sub_type = models.ForeignKey(
        InvestmentSubType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='fixed_income_positions'
    )
    
    # Metadata
    source = models.CharField(max_length=50, default='Manual Entry')  # e.g., "Excel Import", "Manual Entry"
    import_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fixed_income_positions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'asset_code']),
            models.Index(fields=['user_id', 'investment_type']),
            models.Index(fields=['maturity_date']),
        ]
        unique_together = [['user_id', 'asset_code', 'application_date']]
    
    def __str__(self):
        return f"{self.user_id} - {self.asset_name}"


class TesouroDiretoPosition(models.Model):
    """Tesouro Direto Position model for Brazilian government bonds."""
    
    # Link to fixed income position (can share common fields)
    fixed_income_position = models.OneToOneField(
        FixedIncomePosition,
        on_delete=models.CASCADE,
        related_name='tesouro_direto',
        null=True,
        blank=True
    )
    
    # Tesouro-specific fields
    titulo_name = models.CharField(max_length=255)  # e.g., "Tesouro IPCA+ 2029"
    vencimento = models.DateField()  # Maturity date - critical for interest rate determination
    
    # Additional Tesouro-specific fields can be added here
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tesouro_direto_positions'
        ordering = ['vencimento']
        indexes = [
            models.Index(fields=['titulo_name', 'vencimento']),
        ]
    
    def __str__(self):
        return f"{self.titulo_name} - {self.vencimento}"


class InvestmentFund(models.Model):
    """
    Investment Fund model for tracking Fundos de Investimento (RF, Multimercado, etc.).
    """
    
    FUND_TYPE_CHOICES = [
        ('RF_POS', 'Renda Fixa Pós-Fixado'),
        ('RF_PRE', 'Renda Fixa Prefixado'),
        ('RF_IPCA', 'Renda Fixa IPCA+'),
        ('MULTI', 'Multimercado'),
        ('ACOES', 'Ações'),
        ('CAMBIO', 'Câmbio'),
        ('OTHER', 'Outros'),
    ]
    
    # Fund-specific fields
    fund_name = models.CharField(max_length=255)  # e.g., "Trend Cash CIC de Classes RF Simples RL"
    fund_cnpj = models.CharField(max_length=20, null=True, blank=True)  # CNPJ do fundo
    fund_type = models.CharField(max_length=20, choices=FUND_TYPE_CHOICES, default='RF_POS')
    
    # Quota information
    quota_date = models.DateField(null=True, blank=True)  # Data da cota
    quota_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)  # Valor da cota
    quota_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Quantidade de cotas
    
    # Values
    in_quotation = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Em cotização
    position_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Posição
    net_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Valor líquido
    applied_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Valor aplicado
    
    # Returns
    gross_return_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Rentabilidade bruta %
    net_return_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Rentabilidade líquida %
    
    # User and metadata
    user_id = models.CharField(max_length=100, db_index=True)
    
    # Link to investment type and subtype (for allocation strategy)
    investment_type = models.ForeignKey(
        InvestmentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='investment_funds',
        help_text='Tipo de investimento configurado (ex: Renda Fixa)'
    )
    investment_sub_type = models.ForeignKey(
        InvestmentSubType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='investment_funds',
        help_text='Subtipo de investimento configurado'
    )
    
    source = models.CharField(max_length=50, default='Excel Import')  # e.g., "Excel Import", "Manual Entry"
    import_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investment_funds'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'fund_name']),
            models.Index(fields=['user_id', 'fund_type']),
            models.Index(fields=['quota_date']),
        ]
        unique_together = [['user_id', 'fund_name', 'quota_date']]
    
    def __str__(self):
        return f"{self.user_id} - {self.fund_name}"
    
    def calculate_allocation_percent(self, total_portfolio_value):
        """Calculate allocation percentage of this fund in the portfolio."""
        if total_portfolio_value > 0:
            return (float(self.position_value) / float(total_portfolio_value)) * 100
        return 0.0


