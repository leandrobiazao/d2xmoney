# Generated manually to add reason field to RebalancingAction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rebalancing', '0002_add_total_sales_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='rebalancingaction',
            name='reason',
            field=models.CharField(blank=True, max_length=255, null=True, help_text='Reason for this action (e.g., "Not in AMBB 2.0" or "Rank X > 30")'),
        ),
    ]

