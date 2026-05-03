from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'reply', 'reply_at', 'seen', 'created_at')
    list_filter = ('reply', 'seen')
    search_fields = ('description', 'sender__username', 'receiver__username')
    raw_id_fields = ('sender', 'receiver', 'created_by', 'updated_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')
