from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsAdminRole

from .models import District, Organisation, Region
from .serializers import (
    DistrictSerializer,
    OrganisationSerializer,
    OrganisationTreeSerializer,
    RegionSerializer,
)


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]


class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.select_related('region').all()
    serializer_class = DistrictSerializer
    filterset_fields = ('region',)
    search_fields = ('name_uz', 'name_ru')
    filter_backends = (filters.SearchFilter,)
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        region_id = self.request.query_params.get('region_id')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]


class OrganisationViewSet(viewsets.ModelViewSet):
    queryset = Organisation.objects.select_related('district', 'parent').all()
    serializer_class = OrganisationSerializer
    search_fields = ('name_uz', 'name_ru', 'phone_number')
    filter_backends = (filters.SearchFilter,)

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'tree'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    @action(detail=False, methods=['get'])
    def tree(self, request):
        roots = Organisation.objects.filter(parent__isnull=True)
        return Response(OrganisationTreeSerializer(roots, many=True).data)
