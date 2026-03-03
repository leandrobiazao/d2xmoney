# Generated manually for ETF Renda Fixa allocation feature

from django.db import migrations


def add_etf_renda_fixa_subtype_forward(apps, schema_editor):
    """Ensure ETF Renda Fixa subtype exists under Renda Fixa."""
    InvestmentType = apps.get_model('configuration', 'InvestmentType')
    InvestmentSubType = apps.get_model('configuration', 'InvestmentSubType')

    renda_fixa = InvestmentType.objects.filter(code='RENDA_FIXA').first()
    if not renda_fixa:
        return

    InvestmentSubType.objects.get_or_create(
        investment_type=renda_fixa,
        code='ETF_RENDA_FIXA',
        defaults={
            'name': 'ETF Renda Fixa',
            'display_order': 40,
            'is_predefined': True,
            'is_active': True,
        }
    )


def add_etf_renda_fixa_subtype_reverse(apps, schema_editor):
    """Reverse: do not delete (preserve data)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0004_ensure_subtypes_exist'),
    ]

    operations = [
        migrations.RunPython(add_etf_renda_fixa_subtype_forward, add_etf_renda_fixa_subtype_reverse),
    ]
