"""Chat DRF endpointlari — production ChatController bilan biznes mantiq mos."""
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasRole

from .models import ChatMessage
from .serializers import (
    ChatMessageSerializer,
    ChatSendSerializer,
    MarkReadSerializer,
)
from .services import ChatService


SuperAdminOnly = HasRole.with_roles('SUPER_ADMIN')


class ChatViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    - POST   /api/chat/ (multipart: receiver_id, message?, files[]?) — yangi xabar
    - GET    /api/chat/?receiver_id=&page=&page_size= — partner bilan tarix
    - GET    /api/chat/count/ — o'qilmaganlar soni + sender bo'yicha guruh
    - POST   /api/chat/mark-read/ — bir nechta xabarlarni read qilish
    - DELETE /api/chat/<id>/ — habar o'chirish (SUPER_ADMIN, soft delete)
    - GET    /api/chat/admin/threads/ — barcha suhbat juftliklari (SUPER_ADMIN)
    - GET    /api/chat/admin/conversation/?user_a=&user_b=&page= — ikki user orasidagi suhbat (SUPER_ADMIN)
    """

    serializer_class = ChatMessageSerializer
    queryset = ChatMessage.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_permissions(self):
        # destroy / admin endpointlar — faqat SUPER_ADMIN
        if self.action in ('destroy', 'admin_threads', 'admin_conversation'):
            return [IsAuthenticated(), SuperAdminOnly()]
        return [IsAuthenticated()]

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

    def destroy(self, request, pk=None):
        msg = get_object_or_404(ChatMessage, pk=pk)
        ChatService.soft_delete(message=msg, by_user=request.user)
        return Response(
            ChatMessageSerializer(msg, context={'request': request}).data,
            status=status.HTTP_200_OK,
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

    @action(detail=False, methods=['get'], url_path='admin/threads')
    def admin_threads(self, request):
        """Tizimdagi barcha suhbat juftliklari — SUPER_ADMIN."""
        from apps.users.serializers import UserShortSerializer

        search = request.query_params.get('search', '').strip()
        threads = ChatService.admin_threads(search=search)

        # User obyektlarini bir martada yuklab, har bir thread'ga biriktirib qaytaramiz
        user_ids = set()
        for t in threads:
            user_ids.add(t['user_a_id'])
            user_ids.add(t['user_b_id'])
        from apps.users.models import User
        users_map = {
            str(u.id): u for u in User.objects.filter(id__in=user_ids)
        }
        result = []
        for t in threads:
            ua = users_map.get(t['user_a_id'])
            ub = users_map.get(t['user_b_id'])
            if not ua or not ub:
                continue
            result.append({
                'user_a': UserShortSerializer(ua, context={'request': request}).data,
                'user_b': UserShortSerializer(ub, context={'request': request}).data,
                'last_message_at': t['last_message_at'],
                'total': t['total'],
            })
        return Response(result)

    @action(detail=False, methods=['get'], url_path='admin/conversation')
    def admin_conversation(self, request):
        """Ikki foydalanuvchi orasidagi to'liq suhbat — SUPER_ADMIN."""
        user_a = request.query_params.get('user_a')
        user_b = request.query_params.get('user_b')
        if not (user_a and user_b):
            return Response(
                {'detail': "user_a va user_b parametrlari kerak"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ChatService.admin_conversation_qs(user_a, user_b)
        page = self.paginate_queryset(qs)
        ser = ChatMessageSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)
