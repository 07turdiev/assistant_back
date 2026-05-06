from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import ProtectedError

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

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError as e:
            protected_count = len(e.protected_objects) if hasattr(e, 'protected_objects') else 0
            return Response(
                {
                    'detail': (
                        "Yo'nalishni o'chirib bo'lmaydi: unga biriktirilgan "
                        f"{protected_count} ta yozuv mavjud. Avval foydalanuvchilarni "
                        "boshqa yo'nalishga o'tkazing."
                    ),
                    'protected_count': protected_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'])
    def tree(self, request):
        roots = Direction.objects.filter(parent__isnull=True)
        return Response(DirectionTreeSerializer(roots, many=True).data)
