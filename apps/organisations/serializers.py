from rest_framework import serializers

from .models import District, Organisation, Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ('id', 'name_uz', 'name_ru')


class DistrictSerializer(serializers.ModelSerializer):
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), source='region', write_only=True,
    )

    class Meta:
        model = District
        fields = ('id', 'name_uz', 'name_ru', 'region', 'region_id')
        read_only_fields = ('region',)


class OrganisationSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), source='district', write_only=True, required=False, allow_null=True,
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(), source='parent', write_only=True,
        required=False, allow_null=True,
    )

    class Meta:
        model = Organisation
        fields = (
            'id', 'name_uz', 'name_ru', 'address_uz', 'address_ru',
            'phone_number', 'lat', 'lng', 'district', 'district_id',
            'parent', 'parent_id',
        )
        read_only_fields = ('district', 'parent')


class OrganisationTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = (
            'id', 'name_uz', 'name_ru', 'address_uz', 'address_ru',
            'phone_number', 'lat', 'lng', 'district', 'children',
        )

    def get_children(self, obj):
        return OrganisationTreeSerializer(obj.get_children(), many=True).data
