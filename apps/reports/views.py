"""Reports DRF endpointlari — faqat umumiy e'lonlar (Topshiriq moduli olib tashlandi)."""
from django.db.models import Count, Q
from django.http import Http404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import ReportKind
from .models import Report
from .serializers import ReportCreateSerializer, ReportSerializer
from .services import ReportService


class ReportViewSet(viewsets.GenericViewSet):
    """E'lonlar ViewSet (Topshiriq moduli olib tashlandi).

    Endpointlar:
    - POST   /api/reports/                  body {description, target_direction_ids?}
    - GET    /api/reports/announcements/     (auditoriya bo'yicha ko'rinadi, sahifalangan)
    - GET    /api/reports/announcements/count/
    - GET    /api/reports/{id}/
    - PUT    /api/reports/{id}/              (yuboruvchi tahrirlaydi)
    - DELETE /api/reports/{id}/              (yuboruvchi o'chiradi)
    """

    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.SearchFilter,)
    search_fields = ('description',)

    # --------- Helpers ---------

    def _announcements_qs(self, user):
        """Umumiy e'lonlar — auditoriya bo'yicha ko'rinadi.

        - Hammaga (target_directions bo'sh) — har kim ko'radi
        - Yo'naltirilgan — faqat o'sha bo'lim (yoki uning ichidagi) xodimlari ko'radi
        - Yuboruvchi o'z e'lonini doim ko'radi; admin/superadmin — hammasini
        """
        qs = (
            Report.objects.filter(kind=ReportKind.ANNOUNCEMENT)
            .select_related('sender', 'sender__role')
            .prefetch_related('target_directions')
        )
        is_admin = user.is_superuser or (user.role and user.role.name in ('SUPER_ADMIN', 'ADMIN'))
        if is_admin:
            return qs

        qs = qs.annotate(n_targets=Count('target_directions'))
        # hammaga + o'zi yuborgan (rahbar) + o'zi yaratgan (yordamchi nomidan)
        visible = Q(n_targets=0) | Q(sender_id=user.id) | Q(created_by_id=user.id)
        if user.direction_id:
            from apps.directions.models import Direction
            my_dir = Direction.objects.filter(pk=user.direction_id).first()
            if my_dir:
                ancestor_ids = list(
                    my_dir.get_ancestors(include_self=True).values_list('id', flat=True)
                )
                visible |= Q(target_directions__id__in=ancestor_ids)
        return qs.filter(visible).distinct()

    # --------- CREATE ---------

    def create(self, request):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reports = ReportService.create(
            description=ser.validated_data['description'],
            sender=request.user,
            target_direction_ids=ser.validated_data.get('target_direction_ids') or None,
        )
        return Response(
            ReportSerializer(reports, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    # --------- ANNOUNCEMENTS (umumiy e'lonlar) ---------

    @action(detail=False, methods=['get'], url_path='announcements')
    def announcements(self, request):
        qs = self._announcements_qs(request.user)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(description__icontains=search)
        page = self.paginate_queryset(qs)
        ser = ReportSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=False, methods=['get'], url_path='announcements/count')
    def announcements_count(self, request):
        return Response({'count': self._announcements_qs(request.user).count()})

    # --------- DETAIL / UPDATE / DELETE ---------

    def retrieve(self, request, pk=None):
        try:
            r = Report.objects.select_related('sender', 'sender__role').get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        # E'lon — hammaga ochiq; eski yozuvlar — faqat yuboruvchi/superuser
        if r.kind != ReportKind.ANNOUNCEMENT \
                and r.sender_id != request.user.id and not request.user.is_superuser:
            return Response({'success': False, 'message': 'Ruxsat yo\'q'},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(ReportSerializer(r, context={'request': request}).data)

    def update(self, request, pk=None):
        try:
            r = Report.objects.get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        if not self._can_manage(request.user, r):
            return Response({'success': False, 'message': "Faqat muallif yoki uning yordamchisi tahrirlay oladi"},
                            status=status.HTTP_403_FORBIDDEN)
        description = request.data.get('description')
        if description:
            r.description = description
            r.save(update_fields=['description', 'updated_at', 'updated_by'])
        return Response(ReportSerializer(r, context={'request': request}).data)

    def destroy(self, request, pk=None):
        try:
            r = Report.objects.get(pk=pk)
        except Report.DoesNotExist as exc:
            raise Http404 from exc
        if not self._can_manage(request.user, r):
            return Response({'success': False, 'message': "Faqat muallif yoki uning yordamchisi o'chira oladi"},
                            status=status.HTTP_403_FORBIDDEN)
        r.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _can_manage(user, report) -> bool:
        """E'lonni tahrirlash/o'chirish ruxsati: rahbar (sender), uning yordamchisi,
        asl yaratuvchi yoki superuser."""
        from apps.users.delegation import can_act_as
        return (
            user.is_superuser
            or can_act_as(user, report.sender_id)
            or report.created_by_id == user.id
        )
