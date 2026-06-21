"""Event views — production EventController bilan mos URL'lar."""
from datetime import datetime

from django.db.models import Q
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.attachments.models import Attachment
from apps.attachments.services import remove_attachment
from apps.core.permissions import HasRole, IsAdminRole
from apps.users.enums import RoleName
from apps.users.models import User

from .booking import assert_no_conflict, conflict_message, find_conflict
from .models import Event, Hall, HallBooking, Sphere
from .serializers import (
    EventDetailSerializer,
    EventForwardSerializer,
    EventInputSerializer,
    EventListSerializer,
    HallBookingCreateSerializer,
    HallBookingSerializer,
    HallSerializer,
    SphereSerializer,
)
from .services import EventService, calendar_for_vice, calendar_user_ids


CREATE_ROLES = (
    RoleName.VAZIR,
    RoleName.ORINBOSAR,
    RoleName.YORDAMCHI,
    RoleName.BOSHLIQ,
    RoleName.ADMIN,
    RoleName.SUPER_ADMIN,
)


def _parse_files(request) -> list:
    """Multipart `files[]` yoki `files` field — list olish."""
    files = request.FILES.getlist('files') or request.FILES.getlist('files[]')
    return files


def _parse_month(month_str: str) -> tuple:
    """`'5-2026'` formatidan (year, month) ni qaytaradi."""
    try:
        m, y = month_str.split('-')
        return int(y), int(m)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Noto'g'ri month format (kutilgan: M-yyyy): {month_str}") from exc


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related('on_behalf_of', 'direction', 'created_by').prefetch_related(
        'participants', 'visitors', 'files', 'protocols',
    )
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('list', 'all', 'by_period', 'today'):
            return EventListSerializer
        return EventDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), HasRole.with_roles(*CREATE_ROLES)()]
        return [IsAuthenticated()]

    # --------- LIST: month / by-period ---------

    @action(detail=False, methods=['get'], url_path='all')
    def all(self, request):
        """`GET /api/events/all/?month=M-yyyy[&vice_id=]` — oylik kalendar."""
        month_str = request.query_params.get('month')
        if not month_str:
            return Response({'success': False, 'message': "month parametri kerak (M-yyyy)"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            year, month = _parse_month(month_str)
        except ValueError as e:
            return Response({'success': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        qs = self._calendar_qs(request).filter(date__year=year, date__month=month)
        ser = EventListSerializer(qs, many=True, context={'request': request})
        return Response(ser.data)

    @action(detail=False, methods=['get'], url_path='all/by-period')
    def by_period(self, request):
        """`GET /api/events/all/by-period/?start_date=&end_date=[&vice_id=]`."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response({'success': False, 'message': "start_date va end_date kerak"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            start_date = datetime.fromisoformat(start).date()
            end_date = datetime.fromisoformat(end).date()
        except ValueError:
            return Response({'success': False, 'message': "Sana formati noto'g'ri (YYYY-MM-DD)"},
                            status=status.HTTP_400_BAD_REQUEST)

        qs = self._calendar_qs(request).filter(date__gte=start_date, date__lte=end_date)
        ser = EventListSerializer(qs, many=True, context={'request': request})
        return Response(ser.data)

    def _calendar_qs(self, request):
        """Kalendar uchun qaysi foydalanuvchilar tadbirlarini qaytarish kerakligi.

        - Agar `vice_id` berilgan va joriy user PREMIER_MINISTER bo'lsa: vice tadbirlari
        - Aks holda: o'zi va chief/yordamchilar (calendar_user_ids logikasi)
        """
        user = request.user
        vice_id = request.query_params.get('vice_id')
        if vice_id and user.role and user.role.name == RoleName.VAZIR:
            user_ids = calendar_for_vice(vice_id)
        else:
            user_ids = calendar_user_ids(user)

        return self.queryset.filter(
            Q(created_by_id__in=user_ids)
            | Q(on_behalf_of_id__in=user_ids)
            | Q(participants__id__in=user_ids)
        ).distinct()

    # --------- INFO ---------

    @action(detail=True, methods=['get'], url_path='info')
    def info(self, request, pk=None):
        """`GET /api/events/{id}/info/` — production'da locale-aware ko'rinish.

        Hozirgi MVP'da oddiy detail bilan bir xil — DRF i18n middleware
        til'ni `Accept-Language` header orqali aniqlaydi.
        """
        event = self.get_object()
        return Response(EventDetailSerializer(event, context={'request': request}).data)

    # --------- DELEGATSIYA (boshliq → quyi xodimlar) ---------

    @action(detail=True, methods=['post'], url_path='forward')
    def forward(self, request, pk=None):
        """`POST /api/events/{id}/forward/` — boshliq tadbirni o'z xodimlariga yo'naltiradi."""
        event = self.get_object()
        ser = EventForwardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        added = EventService.forward_to_subordinates(
            event,
            user=request.user,
            subordinate_ids=ser.validated_data.get('subordinate_ids'),
            direction_ids=ser.validated_data.get('direction_ids'),
        )
        return Response({'success': True, 'added': added,
                         'message': f'{added} ta xodim qo\'shildi'})

    # --------- CREATE / UPDATE / DELETE ---------

    def create(self, request, *args, **kwargs):
        # `dto` field'da JSON, `files[]` da fayllar — multipart konvensiya
        dto_data = self._parse_dto_payload(request)
        ser = EventInputSerializer(data=dto_data)
        ser.is_valid(raise_exception=True)
        files = _parse_files(request)

        event = EventService.create(
            validated_data=ser.validated_data,
            files=files,
            user=request.user,
        )
        return Response(
            EventDetailSerializer(event, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        event = self.get_object()
        dto_data = self._parse_dto_payload(request)
        ser = EventInputSerializer(data=dto_data)
        ser.is_valid(raise_exception=True)
        files = _parse_files(request)

        event = EventService.update(
            event,
            validated_data=ser.validated_data,
            files=files,
            user=request.user,
        )
        return Response(EventDetailSerializer(event, context={'request': request}).data)

    def partial_update(self, request, *args, **kwargs):
        # PATCH faqat protokol fayl yuklashga ishlatiladi (production konvensiya)
        return self.upload_protocols(request, pk=kwargs.get('pk'))

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        EventService.delete(event, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --------- PROTOCOLS ---------

    @action(detail=True, methods=['patch', 'post'], url_path='protocols',
            parser_classes=[MultiPartParser, FormParser])
    def upload_protocols(self, request, pk=None):
        event = self.get_object()
        files = _parse_files(request)
        if not files:
            return Response({'success': False, 'message': "Fayl yuborilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)
        count = EventService.upload_protocols(event, files, request.user)
        return Response({'success': True, 'message': f'{count} ta protokol biriktirildi'})

    @action(detail=True, methods=['delete'], url_path=r'protocols/(?P<protocol_id>[0-9a-f-]+)')
    def delete_protocol(self, request, pk=None, protocol_id=None):
        event = self.get_object()
        if event.created_by_id != request.user.id and not request.user.is_superuser:
            return Response({'success': False, 'message': "Faqat yaratuvchi o'chirishi mumkin"},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            att = Attachment.objects.get(pk=protocol_id, protocol_event=event)
        except Attachment.DoesNotExist as exc:
            raise Http404 from exc
        remove_attachment(att)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --------- HELPERS ---------

    def _parse_dto_payload(self, request) -> dict:
        """Multipart yoki pure JSON request'dan EventDto data olish.

        Production konvensiya: multipart `dto` (JSON string) + `files[]`.
        Yangi tizim ham shuni qo'llab-quvvatlaydi, ammo qulay bo'lishi uchun
        flat multipart fields ham (axios FormData append) qabul qilinadi.
        """
        # 1) `dto` fielda JSON string
        if 'dto' in request.data:
            import json
            raw = request.data['dto']
            if isinstance(raw, str):
                return json.loads(raw)
            return raw

        # 2) Pure JSON yoki flat multipart — axios FormData ko'rinishi
        # `participant_ids[]` ko'rinishidagi list field'larni yig'ish
        data = {}
        for key in request.data:
            if key.endswith('[]'):
                data[key[:-2]] = request.data.getlist(key)
            else:
                data[key] = request.data[key]

        # `participant_ids` agar string sifatida kelsa (JSON encoded)
        for list_field in ('participant_ids', 'notify_time_list', 'file_ids', 'deleted_file_ids'):
            if list_field in data and isinstance(data[list_field], str):
                import json as _j
                try:
                    data[list_field] = _j.loads(data[list_field])
                except (_j.JSONDecodeError, ValueError):
                    pass
        if 'visitors' in data and isinstance(data['visitors'], str):
            import json as _j
            try:
                data['visitors'] = _j.loads(data['visitors'])
            except (_j.JSONDecodeError, ValueError):
                pass

        return data


class HallViewSet(viewsets.ModelViewSet):
    """Yig'ilish zallari — admin paneldan boshqariladi (ko'rish — barcha auth user)."""
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]


class SphereViewSet(viewsets.ModelViewSet):
    """Tadbir sohalari — admin paneldan boshqariladi (ko'rish — barcha auth user)."""
    queryset = Sphere.objects.all()
    serializer_class = SphereSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]


class HallBookingViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Zal bandligi — ko'rish, alohida band qilish, bekor qilish, tekshirish.

    - GET  /api/hall-bookings/?hall=&start_date=&end_date=  — bandlik ro'yxati
    - POST /api/hall-bookings/                              — bo'lim nomidan band qilish
    - POST /api/hall-bookings/check/                        — bandlikni tekshirish (jonli)
    - DELETE /api/hall-bookings/{id}/                       — bekor qilish (alohida bron)
    """
    queryset = HallBooking.objects.select_related('hall', 'direction', 'event', 'created_by').all()
    serializer_class = HallBookingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        hall = self.request.query_params.get('hall')
        start = self.request.query_params.get('start_date')
        end = self.request.query_params.get('end_date')
        if hall:
            qs = qs.filter(hall_id=hall)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def create(self, request):
        ser = HallBookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d['end_time'] <= d['start_time']:
            raise ValidationError({'end_time': "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak"})
        assert_no_conflict(
            hall_id=d['hall_id'], date=d['date'],
            start_time=d['start_time'], end_time=d['end_time'],
        )
        booking = HallBooking.objects.create(
            hall_id=d['hall_id'], date=d['date'],
            start_time=d['start_time'], end_time=d['end_time'],
            direction_id=d.get('direction_id'),
            title=d.get('title') or '',
        )
        return Response(HallBookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        booking = self.get_object()
        if booking.event_id:
            return Response(
                {'detail': "Bu bron tadbirga bog'langan — tadbir orqali o'zgartiring."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role = getattr(getattr(request.user, 'role', None), 'name', None)
        is_admin = request.user.is_superuser or role in ('SUPER_ADMIN', 'ADMIN')
        if booking.created_by_id != request.user.id and not is_admin:
            return Response(
                {'detail': 'Faqat band qilgan shaxs yoki admin bekor qila oladi.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        booking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='check')
    def check(self, request):
        """Bandlikni tekshirish (jonli UI uchun). `exclude_event_id` — tadbirni tahrirlashda."""
        ser = HallBookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        exclude_booking_id = None
        exclude_event = request.data.get('exclude_event_id')
        if exclude_event:
            exclude_booking_id = (
                HallBooking.objects.filter(event_id=exclude_event)
                .values_list('pk', flat=True).first()
            )
        conflict = find_conflict(
            hall_id=d['hall_id'], date=d['date'],
            start_time=d['start_time'], end_time=d['end_time'],
            exclude_booking_id=exclude_booking_id,
        )
        if conflict:
            return Response({'available': False, 'message': conflict_message(conflict)})
        return Response({'available': True})
