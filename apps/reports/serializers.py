from rest_framework import serializers

from apps.users.serializers import UserShortSerializer

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    receiver = UserShortSerializer(read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'description',
            'sender', 'receiver',
            'reply', 'reply_at', 'notify_time', 'seen',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'sender', 'receiver', 'reply', 'reply_at',
                            'notify_time', 'seen', 'created_at', 'updated_at')


class ReportCreateSerializer(serializers.Serializer):
    description = serializers.CharField()


class ReplyInputSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    reply = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notify_time = serializers.IntegerField(required=False, allow_null=True, min_value=1)
