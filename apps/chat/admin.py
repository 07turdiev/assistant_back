from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'message_short', 'viewed', 'created_at')
    list_filter = ('viewed',)
    search_fields = ('message', 'sender__username', 'receiver__username')
    raw_id_fields = ('sender', 'receiver', 'created_by', 'updated_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def message_short(self, obj):
        return (obj.message or '')[:60]
    message_short.short_description = 'Message'
