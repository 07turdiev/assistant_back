# Generated migration for changing Event.direction on_delete behavior

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('directions', '0001_initial'),
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='direction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='directions.direction'),
        ),
    ]
