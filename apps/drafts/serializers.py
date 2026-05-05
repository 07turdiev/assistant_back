"""Draft serializerlar.

Endpoint dizayn:
- GET /api/drafts/events/ — joriy foydalanuvchi assigned_to bo'lgan EventDraft list
- GET /api/drafts/events/{id}/ — bitta draft
- PATCH /api/drafts/events/{id}/ — qoralamani tahrir qilish
- POST /api/drafts/events/{id}/publish/ — joylash → Event yaratiladi
- POST /api/drafts/events/{id}/reject/ — rad etish

Xuddi shu reports uchun ham.
"""
from rest_framework import serializers

from apps.users.serializers import UserShortSerializer

from .models import EventDraft, ReportDraft


def _enabled_users_qs():
    """Lazy User queryset — import siklini chetlab o'tadi."""
    from apps.users.models import User
    return User.objects.filter(enabled=True)


class _DraftBaseSerializer(serializers.ModelSerializer):
    created_by = UserShortSerializer(read_only=True)
    assigned_to = UserShortSerializer(read_only=True)
    suggested_participants = UserShortSerializer(many=True, read_only=True)
    voice_file_url = serializers.SerializerMethodField()
    target_direction_name = serializers.SerializerMethodField()

    def get_voice_file_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.voice_file and request:
            return request.build_absolute_uri(obj.voice_file.url)
        return None

    def get_target_direction_name(self, obj) -> str | None:
        return obj.target_direction.name_uz if obj.target_direction else None


# --------- EVENT DRAFT ---------

class EventDraftSerializer(_DraftBaseSerializer):
    speaker = UserShortSerializer(read_only=True)

    class Meta:
        model = EventDraft
        fields = (
            'id', 'title', 'description', 'status',
            'date', 'start_time', 'end_time', 'duration_minutes',
            'location', 'is_important', 'is_private',
            'sphere', 'event_type',
            'speaker', 'assigned_to', 'target_direction', 'target_direction_name',
            'suggested_participants', 'unresolved_participant_names',
            'notify_minutes_before',
            'source', 'raw_transcript', 'voice_file_url',
            'created_by', 'created_at', 'updated_at',
            'published_at', 'published_event',
            'rejected_reason',
        )
        read_only_fields = (
            'id', 'status', 'source', 'raw_transcript',
            'created_by', 'created_at', 'updated_at',
            'published_at', 'published_event', 'rejected_reason',
            'suggested_participants', 'voice_file_url', 'target_direction_name',
            'speaker', 'assigned_to',
        )


class EventDraftUpdateSerializer(serializers.ModelSerializer):
    """PATCH uchun — tahrirlash mumkin bo'lgan maydonlar.

    Foydalanuvchi qoralamada hammasini tuzata oladi: sana, vaqt, qatnashchilar, manzil va h.k.
    """
    class Meta:
        model = EventDraft
        fields = (
            'title', 'description',
            'date', 'start_time', 'end_time', 'duration_minutes',
            'location', 'is_important', 'is_private',
            'sphere', 'event_type',
            'speaker', 'assigned_to', 'suggested_participants',
            'notify_minutes_before',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users_qs = _enabled_users_qs()
        if 'speaker' in self.fields:
            self.fields['speaker'].queryset = users_qs
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = users_qs
        if 'suggested_participants' in self.fields:
            self.fields['suggested_participants'].child_relation.queryset = users_qs


# --------- REPORT DRAFT ---------

class ReportDraftSerializer(_DraftBaseSerializer):
    class Meta:
        model = ReportDraft
        fields = (
            'id', 'title', 'description', 'status',
            'is_important', 'deadline_text',
            'assigned_to', 'target_direction', 'target_direction_name',
            'suggested_participants', 'unresolved_participant_names',
            'notify_minutes_before',
            'source', 'raw_transcript', 'voice_file_url',
            'created_by', 'created_at', 'updated_at',
            'published_at', 'published_report',
            'rejected_reason',
        )
        read_only_fields = (
            'id', 'status', 'source', 'raw_transcript',
            'created_by', 'created_at', 'updated_at',
            'published_at', 'published_report', 'rejected_reason',
            'suggested_participants', 'voice_file_url', 'target_direction_name',
            'assigned_to',
        )


class ReportDraftUpdateSerializer(serializers.ModelSerializer):
    """PATCH uchun."""
    class Meta:
        model = ReportDraft
        fields = (
            'title', 'description',
            'is_important', 'deadline_text',
            'assigned_to', 'suggested_participants',
            'notify_minutes_before',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users_qs = _enabled_users_qs()
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = users_qs
        if 'suggested_participants' in self.fields:
            self.fields['suggested_participants'].child_relation.queryset = users_qs


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
