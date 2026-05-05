"""Emergency admin (faqat superuser uchun) — qoralamalarni ko'rish va o'chirish."""
from django.contrib import admin

from .models import EventDraft, ReportDraft


class _DraftAdminBase(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_by', 'assigned_to', 'created_at')
    list_filter = ('status', 'source', 'is_important')
    search_fields = ('title', 'description', 'raw_transcript')
    readonly_fields = ('id', 'created_at', 'updated_at', 'parsed_json', 'raw_transcript', 'source')
    date_hierarchy = 'created_at'


@admin.register(EventDraft)
class EventDraftAdmin(_DraftAdminBase):
    list_display = _DraftAdminBase.list_display + ('date', 'start_time', 'is_private')
    filter_horizontal = ('suggested_participants',)


@admin.register(ReportDraft)
class ReportDraftAdmin(_DraftAdminBase):
    filter_horizontal = ('suggested_participants',)
