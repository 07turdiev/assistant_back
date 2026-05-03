"""Reports DRF endpointlari — production ReportController bilan biznes mantiq mos."""
from django.db.models import Q
from django.http import Http404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasRole
from apps.users.enums import RoleName

from .enums import ReportKind
from .models import Report
from .serializers import (
    ReplyInputSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)
from .services import ReportService

ALLOWED_CREATE_ROLES = (
    RoleName.PREMIER_MINISTER,
    RoleName.HEAD,
    RoleName.ASSISTANT,
    RoleName.ASSISTANT_PREMIER,
)


class ReportViewSet(viewsets.GenericViewSet):
    """Hisobotlar ViewSet.

    Frontend kutgan endpointlar:
    - POST /api/reports/  body {description}
    - POST /api/reports/reply/  body {report_id, reply?, notify_time?}
    - GET  /api/reports/tasks/active/
    - GET  /api/reports/tasks/inactive/?page=&page_size=&search=
    - GET  /api/reports/tasks/count/
    - GET  /api/reports/requests/active/
    - GET  /api/reports/requests/inactive/?page=&page_size=&search=
    - GET  /api/reports/requests/count/
    - GET  /api/reports/{id}/
    - PUT  /api/reports/{id}/  (sender tahrirlay oladi)
    - DELETE /api/reports/{id}/  (sender o'chira oladi)
    """

    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.SearchFilter,)
    search_fields = ('description',)

    def get_permissions(self):
        if self.action in ('create', 'reply'):
            return [IsAuthenticated(), HasRole.with_roles(*ALLOWED_CREATE_ROLES)()]
        return [IsAuthenticated()]

    # --------- Helpers ---------

    def _is_task_owner(self, user) -> bool:
        return bool(user.role and user.role.name in (RoleName.PREMIER_MINISTER, RoleName.HEAD))

    def _is_request_owner(self, user) -> bool:
        return bool(user.role and user.role.name in (RoleName.ASSISTANT, RoleName.ASSISTANT_PREMIER))

    def _tasks_qs(self, user, *, active: bool):
        """User'ning task'lari — sender YOKI receiver, lekin sender Premier/Head bo'lishi shart.

        Bir HEAD bir vaqtda Premier'dan task oladi va o'z yordamchilariga yuboradi —
        bitta "Tasks" sahifa ikkalasini ko'rsatadi.
        """
        task_sender_roles = (RoleName.PREMIER_MINISTER, RoleName.HEAD)
        qs = Report.objects.filter(
            Q(sender=user) | Q(receiver=user),
            sender__role__name__in=task_sender_roles,
        )
        if active:
            qs = qs.filter(reply__isnull=True)
        else:
            qs = qs.exclude(reply__isnull=True)
        return qs.select_related('sender', 'receiver', 'sender__role', 'receiver__role')

    def _requests_qs(self, user, *, active: bool):
        """Request'lar — sender YOKI receiver, sender Assistant/AssistantPremier bo'lishi shart."""
        request_sender_roles = (RoleName.ASSISTANT, RoleName.ASSISTANT_PREMIER)
        qs = Report.objects.filter(
            Q(sender=user) | Q(receiver=user),
            sender__role__name__in=request_sender_roles,
        )
        if active:
            qs = qs.filter(reply__isnull=True)
        else:
            qs = qs.exclude(reply__isnull=True)
        return qs.select_related('sender', 'receiver', 'sender__role', 'receiver__role')

    # --------- CREATE / REPLY ---------

    def create(self, request):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reports = ReportService.create(
            description=ser.validated_data['description'],
            sender=request.user,
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

    # --------- REQUESTS ---------

    @action(detail=False, methods=['get'], url_path='requests/active')
    def requests_active(self, request):
        qs = self._requests_qs(request.user, active=True)
        return Response(ReportSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='requests/inactive')
    def requests_inactive(self, request):
        qs = self._requests_qs(request.user, active=False)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(description__icontains=search)
        page = self.paginate_queryset(qs)
        ser = ReportSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=['get'], url_path='requests/count')
    def requests_count(self, request):
        return Response({'count': self._requests_qs(request.user, active=True).count()})

    # --------- DETAIL / UPDATE / DELETE ---------

    def retrieve(self, request, pk=None):
        try:
            r = Report.objects.select_related(
                'sender', 'receiver', 'sender__role', 'receiver__role'
            ).get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        # Faqat ishtirokchilar (sender / receiver / superuser)
        if r.sender_id != request.user.id and r.receiver_id != request.user.id \
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
