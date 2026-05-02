from django.contrib import admin

from .models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'content_type', 'size', 'path', 'created_at')
    list_filter = ('content_type', 'path')
    search_fields = ('file_name', 'random_name')
    readonly_fields = ('id', 'random_name', 'created_at', 'updated_at', 'created_by', 'updated_by')
