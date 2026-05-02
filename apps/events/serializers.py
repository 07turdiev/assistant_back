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

from .models import Event, EventParticipant, PreEvent, Visitor


class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = ('id', 'full_name', 'organisation_name', 'position')


class EventListSerializer(serializers.ModelSerializer):
    """Kalendar/list uchun yengilroq variant."""
    speaker = UserShortSerializer(read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'date', 'start_time', 'end_time', 'address',
            'sphere', 'type', 'is_important', 'is_private',
            'serial_number', 'speaker', 'created_by',
        )


class EventDetailSerializer(serializers.ModelSerializer):
    """To'liq ma'lumot — `GET /api/events/{id}/` va `/info/{id}` uchun."""
    speaker = UserShortSerializer(read_only=True)
    participants = UserShortSerializer(many=True, read_only=True)
    visitors = VisitorSerializer(many=True, read_only=True)
    files = AttachmentSerializer(many=True, read_only=True)
    protocols = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'description', 'date', 'start_time', 'end_time',
            'address', 'serial_number', 'sphere', 'type',
            'is_important', 'is_private', 'conclusion',
            'direction', 'speaker', 'participants', 'visitors',
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
    speaker_id = serializers.UUIDField()
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False,
    )
    visitors = VisitorSerializer(many=True, required=False, default=list)
    pre_event_id = serializers.UUIDField(required=False, allow_null=True)
    direction_id = serializers.UUIDField(required=False, allow_null=True)
    serial_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    conclusion = serializers.CharField(required=False, allow_blank=True, default='')

    # Tahrirda
    file_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    deleted_file_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class EventParticipantSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = EventParticipant
        fields = ('id', 'user', 'is_present', 'comment')


class PreEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreEvent
        fields = ('id', 'title', 'description', 'date', 'start_time', 'end_time',
                  'created_at', 'created_by')
        read_only_fields = ('id', 'created_at', 'created_by')
