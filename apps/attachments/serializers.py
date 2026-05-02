from rest_framework import serializers

from .models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.CharField(read_only=True)

    class Meta:
        model = Attachment
        fields = ('id', 'file_name', 'content_type', 'size', 'path', 'url', 'created_at')
