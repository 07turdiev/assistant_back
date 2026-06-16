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

from .models import Event, EventParticipant, Visitor


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ('id', 'full_name', 'organisation_name', 'position')


class EventListSerializer(serializers.ModelSerializer):
    """Kalendar/list uchun yengilroq variant."""
    speaker = UserShortSerializer(read_only=True)
    on_behalf_of = UserShortSerializer(read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'date', 'start_time', 'end_time', 'address',
            'sphere', 'type', 'is_important', 'is_private',
            'serial_number', 'speaker', 'on_behalf_of', 'created_by',
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
    speaker = UserShortSerializer(read_only=True)
    on_behalf_of = UserShortSerializer(read_only=True)
    participants = UserShortSerializer(many=True, read_only=True)
    participant_directions = EventDirectionSerializer(many=True, read_only=True)
    visitors = VisitorSerializer(many=True, read_only=True)
    files = AttachmentSerializer(many=True, read_only=True)
    protocols = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'description', 'date', 'start_time', 'end_time',
            'address', 'serial_number', 'sphere', 'type',
            'is_important', 'is_private', 'conclusion',
            'direction', 'speaker', 'on_behalf_of', 'participants', 'participant_directions', 'visitors',
            'notify_time', 'files', 'protocols',
            'created_at', 'updated_at', 'created_by',
        )


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
    sphere = serializers.CharField()
    type = serializers.CharField()
    notify_time_list = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, default=list,
    )
    # Ma'ruzachi ixtiyoriy (berilmasa — yaratuvchi)
    speaker_id = serializers.UUIDField(required=False, allow_null=True)
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
    """Boshliq tadbirni o'z quyi xodimlariga yo'naltirishi (delegatsiya)."""
    subordinate_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False,
    )


class EventParticipantSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = EventParticipant
        fields = ('id', 'user', 'is_present', 'comment')


