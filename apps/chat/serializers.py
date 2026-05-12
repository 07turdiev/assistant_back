from rest_framework import serializers

from apps.attachments.serializers import AttachmentSerializer
from apps.users.serializers import UserShortSerializer

from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    receiver = UserShortSerializer(read_only=True)
    files = AttachmentSerializer(many=True, read_only=True)
    deleted_by = UserShortSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            'id', 'message', 'viewed',
            'sender', 'receiver', 'files',
            'created_at',
            'is_deleted', 'deleted_at', 'deleted_by',
        )


class ChatSendSerializer(serializers.Serializer):
    """Multipart yoki JSON: `receiver_id` + `message` + `files[]`."""
    receiver_id = serializers.UUIDField()
    message = serializers.CharField(required=False, allow_blank=True, default='')


class MarkReadSerializer(serializers.Serializer):
    message_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
