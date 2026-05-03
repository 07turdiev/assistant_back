"""User views: /me, admin CRUD."""
import secrets
import string

from django.contrib.auth import update_session_auth_hash
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasRole, IsAdminRole

from .enums import RoleName
from .models import User
from .serializers import (
    ChangePasswordSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
    UserCreateSerializer,
    UserMeSerializer,
    UserSelfUpdateSerializer,
    UserShortSerializer,
    UserStatusSerializer,
)


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + '!@#$%'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class UserViewSet(viewsets.ModelViewSet):
    """
    Public list: /api/users/ (Auth foydalanuvchilar uchun)
    Admin CRUD: POST/PUT/DELETE — IsAdminRole
    Misc actions: /me/, /vice/, /reset-password/, /status/, /clear-telegram/
    """

    queryset = User.objects.select_related('role', 'direction').all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ('role', 'direction', 'enabled', 'status')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number', 'email')
    ordering_fields = ('username', 'last_name', 'created_at')
    ordering = ('last_name', 'first_name')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserAdminUpdateSerializer
        if self.action in ('list', 'retrieve'):
            return UserAdminSerializer if self._is_admin() else UserShortSerializer
        return UserShortSerializer

    def get_permissions(self):
        write_actions = {'create', 'update', 'partial_update', 'destroy', 'reset_password',
                         'change_status', 'clear_telegram'}
        if self.action in write_actions:
            return [IsAuthenticated(), IsAdminRole()]
        if self.action == 'vice':
            return [IsAuthenticated(), HasRole.with_roles('PREMIER_MINISTER', 'SUPER_ADMIN')()]
        return [IsAuthenticated()]

    def _is_admin(self) -> bool:
        user = self.request.user
        role = getattr(user, 'role', None)
        return bool(role and role.name in ('SUPER_ADMIN', 'ADMIN'))

    # ---- /me/ ----

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def me(self, request):
        if request.method == 'GET':
            return Response(UserMeSerializer(request.user, context={'request': request}).data)

        serializer = UserSelfUpdateSerializer(
            request.user, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserMeSerializer(request.user, context={'request': request}).data)

    @action(detail=False, methods=['patch'], url_path='me/password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'success': False, 'message': 'Eski parol noto\'g\'ri'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        update_session_auth_hash(request, user)
        return Response({'success': True, 'message': 'Parol o\'zgartirildi'})

    # ---- /vice/ ----

    @action(detail=False, methods=['get'])
    def vice(self, request):
        qs = self.queryset.filter(role__name=RoleName.VICE_MINISTER)
        page = self.paginate_queryset(qs)
        ser = UserShortSerializer(page or qs, many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    # ---- /chatters/ ----

    @action(detail=False, methods=['get'])
    def chatters(self, request):
        qs = self.queryset.exclude(id=request.user.id).filter(enabled=True)
        return Response(UserShortSerializer(qs, many=True, context={'request': request}).data)

    # ---- /participants/ ----

    @action(detail=False, methods=['get'])
    def participants(self, request):
        """Tadbir/topshiriq qatnashchilari. Filterlar:
        - direction_id — yo'nalish bo'yicha (joriy va bola yo'nalishlar uchun cascade)
        - organisation_id — tashkilot bo'yicha
        - chief_id — bevosita yordamchilar (subordinates)
        - search — F.I.Sh., username, email bo'yicha
        """
        from django.db.models import Q
        from apps.directions.models import Direction

        qs = self.queryset.filter(enabled=True)

        direction_id = request.query_params.get('direction_id')
        organisation_id = request.query_params.get('organisation_id')
        chief_id = request.query_params.get('chief_id')
        search = (request.query_params.get('search') or '').strip()

        if direction_id:
            # Yo'nalish va uning barcha bola yo'nalishlari (MPTT cascade)
            try:
                direction = Direction.objects.get(pk=direction_id)
                descendants = direction.get_descendants(include_self=True)
                qs = qs.filter(direction__in=descendants)
            except Direction.DoesNotExist:
                qs = qs.none()
        if organisation_id:
            qs = qs.filter(direction__organisation_id=organisation_id)
        if chief_id:
            qs = qs.filter(chief_id=chief_id)
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(father_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
            )

        return Response(UserShortSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def subordinates(self, request, pk=None):
        """Foydalanuvchining bevosita yordamchilari (chief_id = this user)."""
        qs = self.queryset.filter(chief_id=pk, enabled=True)
        return Response(UserShortSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='full')
    def full_info(self, request, pk=None):
        """Foydalanuvchining to'liq ma'lumotlari (Detail page'lar uchun).

        Production'dagi `/api/user/full-info/{id}` ga ekvivalent.
        """
        user = self.get_object()
        return Response(UserShortSerializer(user, context={'request': request}).data)

    # ---- Admin actions ----

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        user = self.get_object()
        ser = UserStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user.status = ser.validated_data['status']
        user.save(update_fields=['status'])
        return Response({'success': True, 'message': 'Holat yangilandi'})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('new_password') or _generate_password()
        user.set_password(new_password)
        user.save(update_fields=['password'])

        payload = {'success': True, 'message': 'Parol yangilandi'}
        # Agar admin parolni ko'rsatishni xohlasa (yoki email yuborish kerak bo'lsa):
        if not request.data.get('new_password'):
            payload['generated_password'] = new_password
        return Response(payload)

    @action(detail=True, methods=['post'], url_path='clear-telegram')
    def clear_telegram(self, request, pk=None):
        user = self.get_object()
        user.telegram_id = None
        user.save(update_fields=['telegram_id'])
        return Response({'success': True, 'message': 'Telegram bog\'lanish tozalandi'})
