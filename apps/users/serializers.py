from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Role, User


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'label_uz', 'label_ru')


class UserShortSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    chief_id = serializers.UUIDField(read_only=True, allow_null=True)
    direction_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'father_name',
            'position_uz', 'position_ru', 'phone_number', 'email',
            'role', 'status', 'enabled', 'avatar_url', 'telegram_id',
            'chief_id', 'direction_id',
        )

    def get_avatar_url(self, obj: User):
        if obj.avatar:
            request = self.context.get('request')
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None


class UserMeSerializer(UserShortSerializer):
    direction_id = serializers.UUIDField(read_only=True, allow_null=True)
    organisation_id = serializers.SerializerMethodField()
    chief_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta(UserShortSerializer.Meta):
        fields = UserShortSerializer.Meta.fields + (
            'direction_id', 'organisation_id', 'chief_id', 'office_number', 'company_car',
        )

    def get_organisation_id(self, obj: User):
        if obj.direction and obj.direction.organisation_id:
            return str(obj.direction.organisation_id)
        return None


class UserAdminSerializer(UserShortSerializer):
    direction_id = serializers.UUIDField(read_only=True)
    chief_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta(UserShortSerializer.Meta):
        fields = UserShortSerializer.Meta.fields + (
            'direction_id', 'chief_id', 'office_number',
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True,
    )
    direction_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    chief_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'password',
            'first_name', 'last_name', 'father_name',
            'position_uz', 'position_ru',
            'phone_number', 'email', 'office_number',
            'role_id', 'direction_id', 'chief_id',
            'status', 'enabled',
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        direction_id = validated_data.pop('direction_id', None)
        chief_id = validated_data.pop('chief_id', None)
        if direction_id:
            validated_data['direction_id'] = direction_id
        if chief_id:
            validated_data['chief_id'] = chief_id
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', required=False,
    )
    direction_id = serializers.UUIDField(required=False, allow_null=True)
    chief_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'father_name',
            'position_uz', 'position_ru',
            'phone_number', 'email', 'office_number',
            'role_id', 'direction_id', 'chief_id',
            'status', 'enabled',
        )


class UserSelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'father_name',
            'phone_number', 'email', 'office_number', 'avatar',
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class UserStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in User._meta.get_field('status').choices])
