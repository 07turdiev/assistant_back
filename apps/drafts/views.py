"""Draft REST API.

Endpoints:
- GET    /api/drafts/events/                    — joriy foydalanuvchining qoralamalari
- GET    /api/drafts/events/{id}/               — bitta qoralama
- PATCH  /api/drafts/events/{id}/               — tahrirlash
- POST   /api/drafts/events/{id}/publish/       — joylash → Event yaratiladi
- POST   /api/drafts/events/{id}/reject/        — rad etish
- DELETE /api/drafts/events/{id}/               — o'chirish (faqat created_by yoki assigned_to)

Reports uchun ham xuddi shu URL'lar (/api/drafts/reports/...).
"""
from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.events.serializers import EventDetailSerializer
from apps.reports.serializers import ReportSerializer

from .enums import DraftStatus
from .models import EventDraft, ReportDraft
from .serializers import (
    EventDraftSerializer,
    EventDraftUpdateSerializer,
    RejectSerializer,
    ReportDraftSerializer,
    ReportDraftUpdateSerializer,
)
from .services import publish_event_draft, publish_report_draft, reject_draft


class _DraftViewSetBase(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Faqat shu foydalanuvchiga tegishli qoralamalar (created_by yoki assigned_to)."""
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post', 'delete']
    # Subclass'lar to'ldiradi — update'dan keyin to'liq javob qaytarish uchun
    read_serializer_class = None

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset_model.objects.select_related(
            'created_by', 'assigned_to', 'target_direction',
        )
        # SUPER_ADMIN, ADMIN va Django superuser hammasini ko'radi (debug/yordam uchun)
        role_name = getattr(getattr(user, 'role', None), 'name', None)
        if user.is_superuser or role_name in ('SUPER_ADMIN', 'ADMIN'):
            return qs.distinct()
        # Qolganlar — faqat o'zlari yaratgan yoki o'zlariga tayinlangan qoralamalar
        return qs.filter(Q(created_by=user) | Q(assigned_to=user)).distinct()

    def update(self, request, *args, **kwargs):
        # UpdateSerializer'da `id` va boshqa read-only field'lar yo'q. Frontend
        # javobni to'g'ridan-to'g'ri draft state'iga yozadi va keyingi publish/reject
        # chaqiruvlarida `draft.id` ishlatadi — shuning uchun read serializer bilan
        # to'liq holatni qaytaramiz.
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        self.perform_update(write_serializer)
        instance.refresh_from_db()
        return Response(
            self.read_serializer_class(instance, context={'request': request}).data
        )


class EventDraftViewSet(_DraftViewSetBase):
    queryset_model = EventDraft
    queryset = EventDraft.objects.all()
    read_serializer_class = EventDraftSerializer

    def get_serializer_class(self):
        if self.action in ('partial_update', 'update'):
            return EventDraftUpdateSerializer
        return EventDraftSerializer

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        draft = self.get_object()
        try:
            event = publish_event_draft(draft)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Joylangach — yaratilgan Event'ni qaytaramiz
        return Response(
            {
                'draft': EventDraftSerializer(draft, context={'request': request}).data,
                'event': EventDetailSerializer(event, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        draft = self.get_object()
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reject_draft(draft, reason=serializer.validated_data.get('reason', ''))
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EventDraftSerializer(draft, context={'request': request}).data)


class ReportDraftViewSet(_DraftViewSetBase):
    queryset_model = ReportDraft
    queryset = ReportDraft.objects.all()
    read_serializer_class = ReportDraftSerializer

    def get_serializer_class(self):
        if self.action in ('partial_update', 'update'):
            return ReportDraftUpdateSerializer
        return ReportDraftSerializer

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        draft = self.get_object()
        try:
            report = publish_report_draft(draft)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'draft': ReportDraftSerializer(draft, context={'request': request}).data,
                'report': ReportSerializer(report, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        draft = self.get_object()
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reject_draft(draft, reason=serializer.validated_data.get('reason', ''))
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReportDraftSerializer(draft, context={'request': request}).data)
