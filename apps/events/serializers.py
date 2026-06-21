"""Event serializerlar.

Production EventDto bilan moslik:
- title, date (string), startTime (string HH:mm), endTime (string HH:mm), address
- description, isPrivate, isImportant
- sphere (string enum), type (string enum)
- notifyTimeList: List<Integer>
- speakerId: UUID
- participants: List<UUID>
- visitors: List<VisitorDto {fullName, organisationName, position}>
- preEventId: UUID (optional)
- fileIds: List<UUID> (saqlanadigan eski fayllar — tahrirda)
- deletedFileIds: List<UUID> (o'chiriladigan fayllar — tahrirda)
"""
from rest_framework import serializers

from apps.attachments.serializers import AttachmentSerializer
from apps.users.serializers import UserShortSerializer

from .models import Event, EventParticipant, Hall, HallBooking, Sphere, Visitor


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ('id', 'full_name', 'organisation_name', 'position')


class HallMiniSerializer(serializers.Serializer):
    """Hona — yengil ko'rinish (tadbir/bron ichida)."""
    id = serializers.IntegerField(read_only=True)
    floor = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class LocationMiniSerializer(serializers.Serializer):
    """Viloyat/tuman — yengil ko'rinish."""
    id = serializers.IntegerField(read_only=True)
    name_uz = serializers.CharField(read_only=True)
    name_ru = serializers.CharField(read_only=True)


class EventListSerializer(serializers.ModelSerializer):
    """Kalendar/list uchun yengilroq variant."""
    on_behalf_of = UserShortSerializer(read_only=True)
    hall = HallMiniSerializer(read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'date', 'start_time', 'end_time', 'address',
            'sphere', 'type', 'is_important', 'is_private',
            'serial_number', 'on_behalf_of', 'created_by', 'hall',
        )


class EventDirectionSerializer(serializers.Serializer):
    """Tadbir yo'naltirilgan bo'lim (ma'sul shaxsi bilan) — ko'rsatish uchun."""
    id = serializers.UUIDField(read_only=True)
    name_uz = serializers.CharField(read_only=True)
    name_ru = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)
    head = UserShortSerializer(read_only=True)


class EventDetailSerializer(serializers.ModelSerializer):
    """To'liq ma'lumot — `GET /api/events/{id}/` va `/info/{id}` uchun."""
    on_behalf_of = UserShortSerializer(read_only=True)
    participants = UserShortSerializer(many=True, read_only=True)
    participant_directions = EventDirectionSerializer(many=True, read_only=True)
    visitors = VisitorSerializer(many=True, read_only=True)
    files = AttachmentSerializer(many=True, read_only=True)
    protocols = AttachmentSerializer(many=True, read_only=True)
    hall = HallMiniSerializer(read_only=True)
    region = LocationMiniSerializer(read_only=True)
    district = LocationMiniSerializer(read_only=True)
    # Joriy foydalanuvchi tadbirni tahrirlay/o'chira oladimi (muallif, rahbar yoki yordamchi)
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'description', 'date', 'start_time', 'end_time',
            'address', 'serial_number', 'sphere', 'type',
            'is_important', 'is_private', 'conclusion',
            'direction', 'on_behalf_of', 'participants', 'participant_directions', 'visitors',
            'hall', 'region', 'district', 'can_manage',
            'notify_time', 'files', 'protocols',
            'created_at', 'updated_at', 'created_by',
        )

    def get_can_manage(self, obj) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser or obj.created_by_id == user.id:
            return True
        from apps.users.delegation import can_act_as
        return can_act_as(user, obj.on_behalf_of_id) or can_act_as(user, obj.created_by_id)


class EventInputSerializer(serializers.Serializer):
    """Production EventDto'ga to'liq mos input formati.

    - `notify_time_list` — JAR'dagi `notifyTimeList` (DRF camel-to-snake convention)
    - frontend axios `notify_time_list` yuborishi shart, yoki front'da `snake_case` ga aylantirilsin
    """
    title = serializers.CharField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    address = serializers.CharField(required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_private = serializers.BooleanField(required=False, default=False)
    is_important = serializers.BooleanField(required=False, default=False)
    sphere = serializers.CharField(required=False, allow_blank=True, default='')
    type = serializers.CharField()
    notify_time_list = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, default=list,
    )
    # Manzil — ikki rejim: vazirlik honasi (hall_id) yoki tashqi hudud (region/district)
    hall_id = serializers.IntegerField(required=False, allow_null=True)
    region_id = serializers.IntegerField(required=False, allow_null=True)
    district_id = serializers.IntegerField(required=False, allow_null=True)
    # Qatnashchilar ikki manbadan: to'g'ridan-to'g'ri odamlar (boshliq tanlasa)
    # va bo'limlar (yuqori rollar tanlaydi → boshliqlar qatnashchi bo'ladi)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
    participant_direction_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
    visitors = VisitorSerializer(many=True, required=False, default=list)
    direction_id = serializers.UUIDField(required=False, allow_null=True)
    serial_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    conclusion = serializers.CharField(required=False, allow_blank=True, default='')

    # Tahrirda
    file_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    deleted_file_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)

    def validate(self, attrs):
        if not (attrs.get('participant_ids') or attrs.get('participant_direction_ids')):
            raise serializers.ValidationError(
                "Kamida bitta bo'lim yoki xodim tanlanishi kerak",
            )
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError(
                {'end_time': "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak"},
            )
        return attrs


class EventForwardSerializer(serializers.Serializer):
    """Boshliq tadbirni o'z quyi xodimlari yoki quyi bo'limlariga yo'naltirishi (delegatsiya)."""
    subordinate_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
    # Quyi bo'limlar — har birining boshlig'i qatnashchi bo'lib qo'shiladi (u yana yo'naltira oladi)
    direction_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )

    def validate(self, attrs):
        if not (attrs.get('subordinate_ids') or attrs.get('direction_ids')):
            raise serializers.ValidationError("Xodim yoki bo'lim tanlang")
        return attrs


class EventParticipantSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = EventParticipant
        fields = ('id', 'user', 'is_present', 'comment')


class HallSerializer(serializers.ModelSerializer):
    """Yig'ilish zali — etaj + nom (admin paneldan boshqariladi)."""

    class Meta:
        model = Hall
        fields = ('id', 'floor', 'name')


class SphereSerializer(serializers.ModelSerializer):
    """Tadbir sohasi — nom (admin paneldan boshqariladi)."""

    class Meta:
        model = Sphere
        fields = ('id', 'name')


class HallBookingSerializer(serializers.ModelSerializer):
    """Zal bandligi — kalendar/ro'yxat uchun (kim, qachon, qaysi zal band qilgan)."""
    hall = HallMiniSerializer(read_only=True)
    event_title = serializers.SerializerMethodField()
    direction_name = serializers.SerializerMethodField()
    booked_by = serializers.SerializerMethodField()

    class Meta:
        model = HallBooking
        fields = (
            'id', 'hall', 'date', 'start_time', 'end_time',
            'title', 'event', 'event_title', 'direction_name', 'booked_by', 'created_at',
        )
        read_only_fields = fields

    def get_event_title(self, obj) -> str:
        return obj.event.title if obj.event_id and obj.event else ''

    def get_direction_name(self, obj) -> str:
        return obj.direction.name_uz if obj.direction_id and obj.direction else ''

    def get_booked_by(self, obj) -> str:
        u = obj.created_by
        return ' '.join(filter(None, [u.last_name, u.first_name])) if u else ''


class HallBookingCreateSerializer(serializers.Serializer):
    """Alohida zal band qilish (bo'lim nomidan) yoki bandlikni tekshirish."""
    hall_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    direction_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default='')


