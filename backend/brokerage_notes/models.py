"""
Django models for brokerage_notes app.
"""
import uuid
from django.db import models


class BrokerageNote(models.Model):
    """Brokerage note model for storing brokerage note information."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100)  # Store as string to match existing UUID format
    file_name = models.CharField(max_length=255)
    original_file_path = models.CharField(max_length=500, null=True, blank=True)
    note_date = models.CharField(max_length=20)  # Stored as DD/MM/YYYY string
    note_number = models.CharField(max_length=100)
    processed_at = models.DateTimeField(null=True, blank=True)
    operations_count = models.IntegerField(default=0)
    operations = models.JSONField(default=list)  # Store operations as JSON
    status = models.CharField(max_length=20, default='success', choices=[
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed')
    ])
    error_message = models.TextField(null=True, blank=True)
    
    # Resumo dos Negócios (Business Summary)
    debentures = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendas_a_vista = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    compras_a_vista = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_das_operacoes = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Resumo Financeiro (Financial Summary)
    clearing = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_liquido_operacoes = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxa_liquidacao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxa_registro = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_cblc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bolsa = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    emolumentos = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxa_transferencia_ativos = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_bovespa = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Custos Operacionais (Operational Costs)
    taxa_operacional = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    execucao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    taxa_custodia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    impostos = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    irrf_operacoes = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    irrf_base = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    outros_custos = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_custos_despesas = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    liquido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    liquido_data = models.CharField(max_length=20, null=True, blank=True)  # Date for "Líquido para"

    class Meta:
        db_table = 'brokerage_notes'
        ordering = ['-note_date', '-note_number']
        unique_together = [['user_id', 'note_number', 'note_date']]

    def __str__(self):
        return f"Note {self.note_number} - {self.note_date}"


class Operation(models.Model):
    """Operation model for storing individual operations from brokerage notes."""
    id = models.CharField(primary_key=True, max_length=100)  # Uses existing operation IDs
    note = models.ForeignKey(BrokerageNote, on_delete=models.CASCADE, related_name='operation_set')
    tipo_operacao = models.CharField(max_length=1)  # C or V
    tipo_mercado = models.CharField(max_length=50, null=True, blank=True)
    ordem = models.IntegerField(default=0)
    titulo = models.CharField(max_length=20)
    qtd_total = models.IntegerField(default=0, null=True, blank=True)
    preco_medio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantidade = models.IntegerField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    valor_operacao = models.DecimalField(max_digits=12, decimal_places=2)
    dc = models.CharField(max_length=1, null=True, blank=True)
    nota_tipo = models.CharField(max_length=50, null=True, blank=True)
    corretora = models.CharField(max_length=100, null=True, blank=True)
    nota_number = models.CharField(max_length=100, null=True, blank=True)  # Note number from operation
    data = models.CharField(max_length=20)  # Stored as DD/MM/YYYY string
    client_id = models.CharField(max_length=100, null=True, blank=True)
    # Store additional fields as JSON for flexibility
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        db_table = 'operations'
        ordering = ['data', 'ordem']

    def __str__(self):
        return f"{self.titulo} - {self.tipo_operacao} - {self.quantidade}"
