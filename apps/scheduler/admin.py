from django.contrib import admin

from .models import ScheduledTask


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'event_id', 'run_at', 'executed', 'executed_at', 'error_short')
    list_filter = ('kind', 'executed')
    search_fields = ('event_id', 'user_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'executed_at', 'locked_until')
    ordering = ('-run_at',)

    def error_short(self, obj):
        return (obj.error or '')[:40]
    error_short.short_description = 'Error'
