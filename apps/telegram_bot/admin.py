from django.contrib import admin

from .models import TelegramState


@admin.register(TelegramState)
class TelegramStateAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'tg_state', 'pending_username', 'created_at')
    list_filter = ('tg_state',)
    search_fields = ('telegram_id', 'pending_username')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')
