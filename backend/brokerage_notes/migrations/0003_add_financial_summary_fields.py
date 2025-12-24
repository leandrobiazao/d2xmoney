# Generated migration for adding financial summary fields to BrokerageNote model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brokerage_notes', '0002_add_status_fields'),
    ]

    operations = [
        # Resumo dos Negócios (Business Summary)
        migrations.AddField(
            model_name='brokeragenote',
            name='debentures',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='vendas_a_vista',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='compras_a_vista',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='valor_das_operacoes',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        
        # Resumo Financeiro (Financial Summary)
        migrations.AddField(
            model_name='brokeragenote',
            name='clearing',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='valor_liquido_operacoes',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='taxa_liquidacao',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='taxa_registro',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='total_cblc',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='bolsa',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='emolumentos',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='taxa_transferencia_ativos',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='total_bovespa',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        
        # Custos Operacionais (Operational Costs)
        migrations.AddField(
            model_name='brokeragenote',
            name='taxa_operacional',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='execucao',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='taxa_custodia',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='impostos',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='irrf_operacoes',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='irrf_base',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='outros_custos',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='total_custos_despesas',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='liquido',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='liquido_data',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]







