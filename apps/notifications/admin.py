from django.contrib import admin

from .models import Notification, WebPushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'user_id', 'is_important', 'seen', 'created_at')
    list_filter = ('notification_type', 'is_important', 'seen')
    search_fields = ('title',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_agent', 'last_used_at', 'created_at')
    search_fields = ('user__username', 'endpoint', 'user_agent')
    raw_id_fields = ('user',)
    readonly_fields = ('id', 'endpoint', 'p256dh', 'auth', 'created_at', 'updated_at',
                       'created_by', 'updated_by', 'last_used_at')
