from rest_framework import serializers

from apps.users.serializers import UserShortSerializer

from .enums import ReportKind
from .models import Report


class DirectionMiniSerializer(serializers.Serializer):
    """E'lon auditoriyasini ko'rsatish uchun yengil bo'lim ma'lumoti."""
    id = serializers.UUIDField(read_only=True)
    name_uz = serializers.CharField(read_only=True)
    name_ru = serializers.CharField(read_only=True)


class ReportSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    receiver = UserShortSerializer(read_only=True)
    target_directions = DirectionMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'kind', 'description',
            'sender', 'receiver', 'target_directions',
            'reply', 'reply_at', 'notify_time', 'seen',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'kind', 'sender', 'receiver', 'target_directions',
                            'reply', 'reply_at', 'notify_time', 'seen', 'created_at', 'updated_at')


class ReportCreateSerializer(serializers.Serializer):
    description = serializers.CharField()
    # TASK (topshiriq) yoki ANNOUNCEMENT (e'lon). Berilmasa — topshiriq.
    kind = serializers.ChoiceField(
        choices=[ReportKind.TASK, ReportKind.ANNOUNCEMENT],
        default=ReportKind.TASK,
        required=False,
    )
    # E'lon auditoriyasi: bo'sh = HAMMAGA, aks holda shu bo'limlarga (va ichidagilarga)
    target_direction_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )


class ReplyInputSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    reply = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notify_time = serializers.IntegerField(required=False, allow_null=True, min_value=1)
