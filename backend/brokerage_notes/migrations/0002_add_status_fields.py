# Generated migration to add status and error_message fields to BrokerageNote model

from django.db import migrations, models


def set_default_status(apps, schema_editor):
    """Set default status='success' for all existing notes."""
    BrokerageNote = apps.get_model('brokerage_notes', 'BrokerageNote')
    BrokerageNote.objects.all().update(status='success')


class Migration(migrations.Migration):

    dependencies = [
        ('brokerage_notes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='brokeragenote',
            name='status',
            field=models.CharField(
                choices=[('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
                default='success',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='brokeragenote',
            name='error_message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(set_default_status, migrations.RunPython.noop),
    ]

