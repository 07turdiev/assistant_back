from rest_framework import serializers

from apps.organisations.models import Organisation

from .models import Direction


class DirectionSerializer(serializers.ModelSerializer):
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(), source='organisation', write_only=True,
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Direction.objects.all(), source='parent', write_only=True,
        required=False, allow_null=True,
    )

    class Meta:
        model = Direction
        fields = (
            'id', 'name_uz', 'name_ru', 'organisation', 'organisation_id',
            'parent', 'parent_id',
        )
        read_only_fields = ('organisation', 'parent')


class DirectionTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Direction
        fields = ('id', 'name_uz', 'name_ru', 'organisation', 'children')

    def get_children(self, obj):
        return DirectionTreeSerializer(obj.get_children(), many=True).data
