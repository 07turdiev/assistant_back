"""ChatMessage soft-delete maydonlari — faqat SUPER_ADMIN o'chira oladi."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chat_deleted',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
