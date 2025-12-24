"""
Data migration to merge duplicate investment funds before changing unique constraint.
Merges funds with same user_id and fund_name but different quota_date.
"""
from django.db import migrations
from decimal import Decimal


def merge_duplicate_funds(apps, schema_editor):
    """Merge duplicate funds by user_id and fund_name."""
    InvestmentFund = apps.get_model('fixed_income', 'InvestmentFund')
    
    # Group funds by user_id and fund_name
    from collections import defaultdict
    fund_groups = defaultdict(list)
    
    for fund in InvestmentFund.objects.all():
        key = (fund.user_id, fund.fund_name)
        fund_groups[key].append(fund)
    
    # Merge duplicates
    merged_count = 0
    for (user_id, fund_name), funds in fund_groups.items():
        if len(funds) > 1:
            # Keep the first one and merge others into it
            keep_fund = funds[0]
            
            for fund in funds[1:]:
                # Sum quantities and values
                keep_fund.quota_quantity = (keep_fund.quota_quantity or Decimal('0')) + (fund.quota_quantity or Decimal('0'))
                keep_fund.in_quotation = (keep_fund.in_quotation or Decimal('0')) + (fund.in_quotation or Decimal('0'))
                keep_fund.position_value = (keep_fund.position_value or Decimal('0')) + (fund.position_value or Decimal('0'))
                keep_fund.net_value = (keep_fund.net_value or Decimal('0')) + (fund.net_value or Decimal('0'))
                keep_fund.applied_value = (keep_fund.applied_value or Decimal('0')) + (fund.applied_value or Decimal('0'))
                
                # Use the most recent quota_date and quota_value
                if fund.quota_date and (not keep_fund.quota_date or fund.quota_date > keep_fund.quota_date):
                    keep_fund.quota_date = fund.quota_date
                    keep_fund.quota_value = fund.quota_value
                
                # Delete the duplicate
                fund.delete()
                merged_count += 1
            
            # Recalculate returns
            if keep_fund.applied_value > 0 and keep_fund.net_value > 0:
                keep_fund.net_return_percent = ((keep_fund.net_value - keep_fund.applied_value) / keep_fund.applied_value) * 100
            
            keep_fund.save()
    
    print(f"Merged {merged_count} duplicate fund(s)")


def reverse_merge(apps, schema_editor):
    """Reverse migration - cannot reverse merge operation."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fixed_income', '0005_add_investment_type_to_funds'),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_funds, reverse_merge),
    ]

