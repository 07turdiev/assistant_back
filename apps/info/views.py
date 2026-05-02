"""Lookup endpointlari — frontend tushuvchi ro'yxatlar uchun."""
from django.utils.translation import get_language
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organisations.models import District, Region
from apps.users.enums import RoleName, UserStatus
from apps.users.models import Role
from apps.users.serializers import RoleSerializer

from .enums import REPLY_CHOICES, EventType, Sphere


def _localized(label_uz: str, label_ru: str) -> str:
    return label_ru if get_language() == 'ru' else label_uz


def _choices_to_payload(choices):
    """`TextChoices` ni [{value, label}] ga o'giradi (joriy tilda)."""
    return [{'value': c[0], 'label': c[1]} for c in choices]


class SpheresView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_choices_to_payload(Sphere.choices))


class TypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_choices_to_payload(EventType.choices))


class _RepliesBase(APIView):
    permission_classes = [IsAuthenticated]
    reply_for: str = ''

    def get(self, request):
        items = []
        for value, meta in REPLY_CHOICES:
            if self.reply_for and meta['reply_for'] not in (self.reply_for, 'BOTH'):
                continue
            items.append({
                'value': value,
                'label': _localized(meta['label_uz'], meta['label_ru']),
                'color': meta['color'],
            })
        return Response(items)


class TaskRepliesView(_RepliesBase):
    reply_for = 'TASK'


class RequestRepliesView(_RepliesBase):
    reply_for = 'REQUEST'


class RolesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # `[{value, label}]` formatida (frontend lookup store'i shu formatda kutadi)
        items = [
            {'value': str(r.id), 'label': _localized(r.label_uz, r.label_ru)}
            for r in Role.objects.all()
        ]
        return Response(items)


class RolesFullView(APIView):
    """Admin sahifa ehtiyojlari uchun: ID + ikki tildagi nom."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(RoleSerializer(Role.objects.all(), many=True).data)


class StatusesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_choices_to_payload(UserStatus.choices))


class RoleNamesView(APIView):
    """Backend RoleName enum (frontend rol guard'lari uchun)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{'value': c[0], 'label': c[1]} for c in RoleName.choices])


class RegionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = [
            {'id': r.id, 'name': _localized(r.name_uz, r.name_ru), 'name_uz': r.name_uz, 'name_ru': r.name_ru}
            for r in Region.objects.all()
        ]
        return Response(items)


class DistrictsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = District.objects.select_related('region').all()
        region_id = request.query_params.get('region_id')
        if region_id:
            qs = qs.filter(region_id=region_id)
        items = [
            {
                'id': d.id,
                'name': _localized(d.name_uz, d.name_ru),
                'name_uz': d.name_uz,
                'name_ru': d.name_ru,
                'region_id': d.region_id,
            }
            for d in qs
        ]
        return Response(items)
