"""Reports DRF endpointlari — production ReportController bilan biznes mantiq mos."""
from django.db.models import Q
from django.http import Http404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import ReportKind
from .models import Report
from .serializers import (
    ReplyInputSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)
from .services import ReportService


class ReportViewSet(viewsets.GenericViewSet):
    """Hisobotlar ViewSet.

    Frontend kutgan endpointlar:
    - POST /api/reports/  body {description, kind?}  (kind=TASK|ANNOUNCEMENT)
    - POST /api/reports/reply/  body {report_id, reply?, notify_time?}  (faqat TASK)
    - GET  /api/reports/tasks/active/
    - GET  /api/reports/tasks/inactive/?page=&page_size=&search=
    - GET  /api/reports/tasks/count/
    - GET  /api/reports/announcements/?page=&page_size=&search=   (hammaga ko'rinadi)
    - GET  /api/reports/announcements/count/
    - GET  /api/reports/{id}/
    - PUT  /api/reports/{id}/  (sender tahrirlay oladi)
    - DELETE /api/reports/{id}/  (sender o'chira oladi)
    """

    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.SearchFilter,)
    search_fields = ('description',)

    # --------- Helpers ---------

    def _visible_user_ids(self, user) -> set:
        """User va uning barcha quyi turuvchilari (rekursiv) ID'lari.

        Vazir → barcha xodimlar; bo'lim boshlig'i → o'zi va bo'lim ichidagilar; va h.k.
        """
        from apps.events.services import calendar_user_ids
        return set(calendar_user_ids(user))

    def _tasks_qs(self, user, *, active: bool):
        """User'ning topshiriqlari — o'zi YOKI quyi turuvchilari ishtirok etgan tasklar.

        Vazirga butun tashkilot bo'yicha topshiriqlar ko'rinadi.
        """
        visible = self._visible_user_ids(user)
        qs = Report.objects.filter(
            Q(sender_id__in=visible) | Q(receiver_id__in=visible),
            kind=ReportKind.TASK,
        )
        if active:
            qs = qs.filter(reply__isnull=True)
        else:
            qs = qs.exclude(reply__isnull=True)
        return qs.select_related('sender', 'receiver', 'sender__role', 'receiver__role')

    def _announcements_qs(self):
        """Umumiy e'lonlar — hammaga ko'rinadi (kind=ANNOUNCEMENT, javobsiz)."""
        return Report.objects.filter(kind=ReportKind.ANNOUNCEMENT).select_related(
            'sender', 'sender__role',
        )

    # --------- CREATE / REPLY ---------

    def create(self, request):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reports = ReportService.create(
            description=ser.validated_data['description'],
            sender=request.user,
            kind=ser.validated_data.get('kind', ReportKind.TASK),
        )
        return Response(
            ReportSerializer(reports, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'])
    def reply(self, request):
        ser = ReplyInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            report = Report.objects.get(pk=ser.validated_data['report_id'])
        except Report.DoesNotExist as exc:
            raise Http404 from exc

        report = ReportService.reply(
            report=report,
            user=request.user,
            reply=ser.validated_data.get('reply') or None,
            notify_time=ser.validated_data.get('notify_time'),
        )
        return Response(ReportSerializer(report).data)

    # --------- TASKS ---------

    @action(detail=False, methods=['get'], url_path='tasks/active')
    def tasks_active(self, request):
        qs = self._tasks_qs(request.user, active=True)
        return Response(ReportSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='tasks/inactive')
    def tasks_inactive(self, request):
        qs = self._tasks_qs(request.user, active=False)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(description__icontains=search)
        page = self.paginate_queryset(qs)
        ser = ReportSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=['get'], url_path='tasks/count')
    def tasks_count(self, request):
        return Response({'count': self._tasks_qs(request.user, active=True).count()})

    # --------- ANNOUNCEMENTS (umumiy e'lonlar) ---------

    @action(detail=False, methods=['get'], url_path='announcements')
    def announcements(self, request):
        """Barcha umumiy e'lonlar — hammaga ko'rinadi, sahifalangan."""
        qs = self._announcements_qs()
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(description__icontains=search)
        page = self.paginate_queryset(qs)
        ser = ReportSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=['get'], url_path='announcements/count')
    def announcements_count(self, request):
        return Response({'count': self._announcements_qs().count()})

    # --------- DETAIL / UPDATE / DELETE ---------

    def retrieve(self, request, pk=None):
        try:
            r = Report.objects.select_related(
                'sender', 'receiver', 'sender__role', 'receiver__role'
            ).get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        # E'lon — hammaga ochiq; topshiriq — faqat ishtirokchilar (sender/receiver/superuser)
        if r.kind != ReportKind.ANNOUNCEMENT \
                and r.sender_id != request.user.id and r.receiver_id != request.user.id \
                and not request.user.is_superuser:
            return Response({'success': False, 'message': 'Ruxsat yo\'q'},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(ReportSerializer(r).data)

    def update(self, request, pk=None):
        try:
            r = Report.objects.get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        if r.sender_id != request.user.id and not request.user.is_superuser:
            return Response({'success': False, 'message': "Faqat yuboruvchi tahrirlay oladi"},
                            status=status.HTTP_403_FORBIDDEN)
        description = request.data.get('description')
        if description:
            r.description = description
            r.save(update_fields=['description', 'updated_at', 'updated_by'])
        return Response(ReportSerializer(r).data)

    def destroy(self, request, pk=None):
        try:
            r = Report.objects.get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        if r.sender_id != request.user.id and not request.user.is_superuser:
            return Response({'success': False, 'message': "Faqat yuboruvchi o'chira oladi"},
                            status=status.HTTP_403_FORBIDDEN)
        r.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
