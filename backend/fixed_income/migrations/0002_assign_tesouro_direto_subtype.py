# Generated migration to assign TESOURO_DIRETO subtype to specific Tesouro positions

from django.db import migrations


def assign_tesouro_direto_subtype_forward(apps, schema_editor):
    """Assign TESOURO_DIRETO subtype to specific Tesouro positions."""
    FixedIncomePosition = apps.get_model('fixed_income', 'FixedIncomePosition')
    InvestmentType = apps.get_model('configuration', 'InvestmentType')
    InvestmentSubType = apps.get_model('configuration', 'InvestmentSubType')
    
    # Get RENDA_FIXA investment type
    renda_fixa_type = InvestmentType.objects.filter(code='RENDA_FIXA').first()
    if not renda_fixa_type:
        print("RENDA_FIXA investment type not found, skipping migration")
        return
    
    # Get or create TESOURO_DIRETO subtype
    tesouro_subtype, _ = InvestmentSubType.objects.get_or_create(
        investment_type=renda_fixa_type,
        code='TESOURO_DIRETO',
        defaults={
            'name': 'Tesouro Direto',
            'display_order': 10,
            'is_predefined': True,
            'is_active': True
        }
    )
    
    # List of specific asset codes to update
    tesouro_asset_codes = [
        'TESOURO_NTNB_PRINC_20290515',
        'TESOURO_LFT_20290301',
        'TESOURO_LTN_20270101'
    ]
    
    # Also match any asset codes that start with TESOURO_ and contain NTNB, LFT, or LTN
    # This covers variations like TESOURO_NTNB_PRINC_20290515, TESOURO_LFT_20290301, etc.
    updated_count = 0
    
    # Update specific asset codes
    for asset_code in tesouro_asset_codes:
        count = FixedIncomePosition.objects.filter(
            asset_code=asset_code
        ).update(
            investment_type=renda_fixa_type,
            investment_sub_type=tesouro_subtype
        )
        updated_count += count
        if count > 0:
            print(f"Updated {count} positions with asset_code: {asset_code}")
    
    # Also update any positions with asset_code starting with TESOURO_ and containing NTNB, LFT, or LTN
    # that don't already have the TESOURO_DIRETO subtype
    tesouro_positions = FixedIncomePosition.objects.filter(
        asset_code__startswith='TESOURO_',
        investment_type=renda_fixa_type
    ).exclude(
        investment_sub_type=tesouro_subtype
    )
    
    # Filter to only NTNB, LFT, or LTN positions
    tesouro_positions = tesouro_positions.filter(
        asset_code__iregex=r'TESOURO_(NTNB|LFT|LTN)'
    )
    
    additional_count = tesouro_positions.update(
        investment_sub_type=tesouro_subtype
    )
    updated_count += additional_count
    
    if additional_count > 0:
        print(f"Updated {additional_count} additional Tesouro positions to TESOURO_DIRETO subtype")
    
    print(f"Total positions updated: {updated_count}")


def assign_tesouro_direto_subtype_reverse(apps, schema_editor):
    """Reverse migration - set investment_sub_type to None for affected positions."""
    FixedIncomePosition = apps.get_model('fixed_income', 'FixedIncomePosition')
    InvestmentSubType = apps.get_model('configuration', 'InvestmentSubType')
    
    tesouro_subtype = InvestmentSubType.objects.filter(code='TESOURO_DIRETO').first()
    if tesouro_subtype:
        tesouro_asset_codes = [
            'TESOURO_NTNB_PRINC_20290515',
            'TESOURO_LFT_20290301',
            'TESOURO_LTN_20270101'
        ]
        
        for asset_code in tesouro_asset_codes:
            FixedIncomePosition.objects.filter(
                asset_code=asset_code,
                investment_sub_type=tesouro_subtype
            ).update(investment_sub_type=None)
        
        FixedIncomePosition.objects.filter(
            asset_code__startswith='TESOURO_',
            asset_code__iregex=r'TESOURO_(NTNB|LFT|LTN)',
            investment_sub_type=tesouro_subtype
        ).update(investment_sub_type=None)


class Migration(migrations.Migration):

    dependencies = [
        ('fixed_income', '0001_initial'),
        ('configuration', '0004_ensure_subtypes_exist'),
    ]

    operations = [
        migrations.RunPython(
            assign_tesouro_direto_subtype_forward,
            assign_tesouro_direto_subtype_reverse
        ),
    ]

