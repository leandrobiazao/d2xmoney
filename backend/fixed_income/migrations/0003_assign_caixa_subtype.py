# Generated migration to assign CAIXA subtype to Caixa positions

from django.db import migrations


def assign_caixa_subtype_forward(apps, schema_editor):
    """Assign CAIXA subtype to Caixa positions."""
    FixedIncomePosition = apps.get_model('fixed_income', 'FixedIncomePosition')
    InvestmentType = apps.get_model('configuration', 'InvestmentType')
    InvestmentSubType = apps.get_model('configuration', 'InvestmentSubType')
    
    # Get RENDA_FIXA type
    renda_fixa_type = InvestmentType.objects.filter(code='RENDA_FIXA').first()
    if not renda_fixa_type:
        print("RENDA_FIXA type not found, skipping Caixa subtype assignment")
        return
    
    # Get or create CAIXA subtype
    caixa_subtype, created = InvestmentSubType.objects.get_or_create(
        investment_type=renda_fixa_type,
        code='CAIXA',
        defaults={
            'name': 'Caixa',
            'display_order': 1,
            'is_predefined': False,
            'is_active': True
        }
    )
    
    if created:
        print(f"Created CAIXA subtype (ID: {caixa_subtype.id})")
    else:
        print(f"Found existing CAIXA subtype (ID: {caixa_subtype.id})")
    
    # Update all Caixa positions to have the CAIXA subtype
    caixa_positions = FixedIncomePosition.objects.filter(
        asset_code__startswith='CAIXA_',
        investment_sub_type__isnull=True
    )
    
    updated_count = caixa_positions.update(
        investment_sub_type=caixa_subtype
    )
    
    print(f"Updated {updated_count} Caixa positions to use CAIXA subtype")


def assign_caixa_subtype_reverse(apps, schema_editor):
    """Reverse migration - set investment_sub_type to None for Caixa positions."""
    FixedIncomePosition = apps.get_model('fixed_income', 'FixedIncomePosition')
    InvestmentSubType = apps.get_model('configuration', 'InvestmentSubType')
    
    # Get CAIXA subtype
    caixa_subtype = InvestmentSubType.objects.filter(code='CAIXA').first()
    if caixa_subtype:
        FixedIncomePosition.objects.filter(
            asset_code__startswith='CAIXA_',
            investment_sub_type=caixa_subtype
        ).update(investment_sub_type=None)


class Migration(migrations.Migration):

    dependencies = [
        ('fixed_income', '0002_assign_tesouro_direto_subtype'),
        ('configuration', '0004_ensure_subtypes_exist'),
    ]

    operations = [
        migrations.RunPython(assign_caixa_subtype_forward, assign_caixa_subtype_reverse),
    ]

