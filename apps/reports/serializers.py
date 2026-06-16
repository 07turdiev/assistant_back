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
    # Joriy foydalanuvchi shu e'lonni tahrirlash/o'chirish huquqiga egami
    # (muallif-rahbar, uning yordamchisi, asl yaratuvchi yoki superuser).
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'kind', 'description',
            'sender', 'target_directions', 'can_manage',
            'created_at', 'updated_at',
        )
        read_only_fields = fields

    def get_can_manage(self, obj) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        from apps.users.delegation import can_act_as
        return can_act_as(user, obj.sender_id) or obj.created_by_id == user.id


class ReportCreateSerializer(serializers.Serializer):
    description = serializers.CharField()
    # E'lon auditoriyasi: bo'sh = HAMMAGA, aks holda shu bo'limlarga (va ichidagilarga)
    target_direction_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
