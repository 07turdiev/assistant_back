from rest_framework import serializers

from apps.users.serializers import UserShortSerializer

from .models import Report


class DirectionMiniSerializer(serializers.Serializer):
    """E'lon auditoriyasini ko'rsatish uchun yengil bo'lim ma'lumoti."""
    id = serializers.UUIDField(read_only=True)
    name_uz = serializers.CharField(read_only=True)
    name_ru = serializers.CharField(read_only=True)


class ReportSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    target_directions = DirectionMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'kind', 'description',
            'sender', 'target_directions',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    description = serializers.CharField()
    # E'lon auditoriyasi: bo'sh = HAMMAGA, aks holda shu bo'limlarga (va ichidagilarga)
    target_direction_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
