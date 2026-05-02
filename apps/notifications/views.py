"""Notifications + WebPush DRF endpointlari."""
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, WebPushSubscription
from .serializers import (
    NotificationBulkSerializer,
    NotificationSerializer,
    WebPushSubscribeSerializer,
    WebPushSubscriptionSerializer,
)
from .services import NotificationService


class NotificationViewSet(viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user_id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def all(self, request):
        """`GET /api/notifications/all/` — barcha bildirishnomalar (sahifali)."""
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        ser = NotificationSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    def list(self, request):
        return self.all(request)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """`GET /api/notifications/count/` — o'qilmagan bildirishnomalar soni."""
        unread = self.get_queryset().filter(seen=False).count()
        return Response({'count': unread})

    @action(detail=True, methods=['delete'])
    def destroy_one(self, request, pk=None):
        deleted, _ = self.get_queryset().filter(pk=pk).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk=None):
        return self.destroy_one(request, pk)

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ser = NotificationBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        deleted, _ = self.get_queryset().filter(pk__in=ser.validated_data['ids']).delete()
        return Response({'success': True, 'deleted': deleted})

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        ser = NotificationBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated = self.get_queryset().filter(pk__in=ser.validated_data['ids']).update(seen=True)
        return Response({'success': True, 'updated': updated})


# --- WebPush ---

class VapidPublicKeyView(APIView):
    """`GET /api/webpush/vapid-public-key/` — frontend subscribe paytida ishlatadi.

    DIQQAT: bu endpoint public — frontend hali login qilmagan bo'lsa ham ola oladi.
    Lekin `subscribe` faqat auth foydalanuvchilar uchun.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'public_key': settings.VAPID_PUBLIC_KEY})


class WebPushSubscriptionViewSet(viewsets.GenericViewSet):
    serializer_class = WebPushSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebPushSubscription.objects.filter(user=self.request.user)

    def list(self, request):
        """`GET /api/webpush/subscriptions/` — joriy user'ning qurilmalari."""
        qs = self.get_queryset()
        return Response(WebPushSubscriptionSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        ser = WebPushSubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Bir xil endpoint bo'yicha — avvalgisini yangilaymiz (boshqa user bo'lsa ham qayta yozish)
        sub, created = WebPushSubscription.objects.update_or_create(
            endpoint=data['endpoint'],
            defaults={
                'user': request.user,
                'p256dh': data['keys']['p256dh'],
                'auth': data['keys']['auth'],
                'user_agent': data.get('user_agent', ''),
            },
        )
        return Response(
            WebPushSubscriptionSerializer(sub).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        deleted, _ = self.get_queryset().filter(pk=pk).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def test(self, request):
        """`POST /api/webpush/test/` — joriy user'ga test push."""
        sent = NotificationService.send_test_to_user(request.user)
        return Response({'success': True, 'sent': sent})
