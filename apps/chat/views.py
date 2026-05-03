"""Chat DRF endpointlari — production ChatController bilan biznes mantiq mos."""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatMessage
from .serializers import (
    ChatMessageSerializer,
    ChatSendSerializer,
    MarkReadSerializer,
)
from .services import ChatService


class ChatViewSet(viewsets.GenericViewSet):
    """
    - POST /api/chat/ (multipart: receiver_id, message?, files[]?) — yangi xabar
    - GET  /api/chat/?receiver_id=&page=&page_size= — partner bilan tarix
    - GET  /api/chat/count/ — o'qilmaganlar soni + sender bo'yicha guruh
    - POST /api/chat/mark-read/ — bir nechta xabarlarni read qilish
    """

    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def list(self, request):
        receiver_id = request.query_params.get('receiver_id')
        if not receiver_id:
            return Response(
                {'success': False, 'message': "receiver_id parametri kerak"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ChatService.history_qs(request.user, receiver_id)

        # Tarix ochilganda partner'dan kelgan o'qilmaganlarni avtomatik o'qildi qilamiz
        ChatService.mark_thread_read(request.user, receiver_id)

        page = self.paginate_queryset(qs)
        ser = ChatMessageSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    def create(self, request):
        ser = ChatSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        files = request.FILES.getlist('files') or request.FILES.getlist('files[]')
        msg = ChatService.send(
            sender=request.user,
            receiver_id=ser.validated_data['receiver_id'],
            message=ser.validated_data.get('message', ''),
            files=files,
        )
        return Response(
            ChatMessageSerializer(msg, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def count(self, request):
        total = ChatService.unread_count_total(request.user)
        by_sender = ChatService.unread_count_by_sender(request.user)
        return Response({'count': total, 'by_sender': by_sender})

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        ser = MarkReadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated = ChatService.mark_read(request.user, ser.validated_data['message_ids'])
        return Response({'success': True, 'updated': updated})
