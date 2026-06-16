from rest_framework import serializers

from apps.organisations.models import Organisation
from apps.users.models import User
from apps.users.serializers import UserShortSerializer

from .models import Direction


class DirectionSerializer(serializers.ModelSerializer):
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(), source='organisation',
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Direction.objects.all(), source='parent',
        required=False, allow_null=True,
    )
    # Ma'sul shaxs (boshliq) va nazoratchi o'rinbosar — o'qishda nested, yozishda *_id
    head = UserShortSerializer(read_only=True)
    head_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='head',
        required=False, allow_null=True, write_only=True,
    )
    supervisor = UserShortSerializer(read_only=True)
    supervisor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='supervisor',
        required=False, allow_null=True, write_only=True,
    )

    class Meta:
        model = Direction
        fields = (
            'id', 'name_uz', 'name_ru', 'kind', 'organisation', 'organisation_id',
            'parent', 'parent_id', 'head', 'head_id', 'supervisor', 'supervisor_id',
        )
        read_only_fields = ('organisation', 'parent', 'head', 'supervisor')


class DirectionTreeSerializer(serializers.ModelSerializer):
    head = UserShortSerializer(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Direction
        fields = ('id', 'name_uz', 'name_ru', 'kind', 'organisation', 'head', 'children')

    def get_children(self, obj):
        return DirectionTreeSerializer(obj.get_children(), many=True).data
