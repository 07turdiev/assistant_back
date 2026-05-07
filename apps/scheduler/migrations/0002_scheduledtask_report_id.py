"""Add report_id field to ScheduledTask for report follow-up reminders."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledtask',
            name='report_id',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
