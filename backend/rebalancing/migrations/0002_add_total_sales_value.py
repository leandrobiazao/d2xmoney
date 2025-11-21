# Generated manually for adding total_sales_value field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rebalancing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rebalancingrecommendation',
            name='total_sales_value',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Total value of sales for Ações em Reais (capped at 19,000 Reais)',
                max_digits=15
            ),
        ),
    ]

