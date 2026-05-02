from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsAdminRole

from .models import Direction
from .serializers import DirectionSerializer, DirectionTreeSerializer


class DirectionViewSet(viewsets.ModelViewSet):
    queryset = Direction.objects.select_related('organisation', 'parent').all()
    serializer_class = DirectionSerializer
    search_fields = ('name_uz', 'name_ru')
    filter_backends = (filters.SearchFilter,)

    def get_queryset(self):
        qs = super().get_queryset()
        parent_id = self.request.query_params.get('parent_id')
        if parent_id == 'null':
            qs = qs.filter(parent__isnull=True)
        elif parent_id:
            qs = qs.filter(parent_id=parent_id)
        return qs

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'tree'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    @action(detail=False, methods=['get'])
    def tree(self, request):
        roots = Direction.objects.filter(parent__isnull=True)
        return Response(DirectionTreeSerializer(roots, many=True).data)
