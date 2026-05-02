from rest_framework import serializers

from .models import Notification, WebPushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            'id', 'user_id', 'title', 'notification_type',
            'event_id', 'pre_event_id',
            'date', 'start_time', 'end_time',
            'is_important', 'seen', 'created_at',
        )
        read_only_fields = fields


class NotificationBulkSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class WebPushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebPushSubscription
        fields = ('id', 'endpoint', 'user_agent', 'last_used_at', 'created_at')
        read_only_fields = ('id', 'last_used_at', 'created_at')


class WebPushKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField()
    auth = serializers.CharField()


class WebPushSubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    keys = WebPushKeysSerializer()
    user_agent = serializers.CharField(required=False, allow_blank=True, default='')
