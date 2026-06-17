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
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        # Cache-bust: foydalanuvchi avatarini yangilaganda URL o'zgaradi,
        # shu sababli brauzer eski rasmni cache'dan ko'rsatmaydi.
        if obj.updated_at:
            sep = '&' if '?' in url else '?'
            url = f'{url}{sep}v={int(obj.updated_at.timestamp())}'
        return request.build_absolute_uri(url) if request else url


class UserMeSerializer(UserShortSerializer):
    direction_id = serializers.UUIDField(read_only=True, allow_null=True)
    organisation_id = serializers.SerializerMethodField()
    chief_id = serializers.UUIDField(read_only=True, allow_null=True)
    # Yordamchi bo'lsa — rahbarining qisqa ma'lumoti ("[rahbar] nomidan" banneri uchun)
    chief = serializers.SerializerMethodField()

    class Meta(UserShortSerializer.Meta):
        fields = UserShortSerializer.Meta.fields + (
            'direction_id', 'organisation_id', 'chief_id', 'chief', 'office_number', 'company_car',
        )

    def get_organisation_id(self, obj: User):
        if obj.direction and obj.direction.organisation_id:
            return str(obj.direction.organisation_id)
        return None

    def get_chief(self, obj: User):
        from apps.users.enums import RoleName
        c = getattr(obj, 'chief', None)
        if not (obj.role and obj.role.name == RoleName.YORDAMCHI and c):
            return None
        role = getattr(c, 'role', None)
        return {
            'id': str(c.id),
            'first_name': c.first_name,
            'last_name': c.last_name,
            'father_name': c.father_name or '',
            'position_uz': c.position_uz or '',
            'position_ru': c.position_ru or '',
            'role_label_uz': role.label_uz if role else '',
            'role_label_ru': role.label_ru if role else '',
        }


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

    def to_internal_value(self, data):
        cleaned = dict(data)
        for key in ('direction_id', 'chief_id'):
            if key in cleaned and cleaned[key] in ('', None):
                cleaned[key] = None
        if cleaned.get('email') == '':
            cleaned['email'] = None
        return super().to_internal_value(cleaned)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'password',
            'first_name', 'last_name', 'father_name',
            'position_uz', 'position_ru',
            'phone_number', 'email', 'office_number',
            'role_id', 'direction_id', 'chief_id',
            'status', 'enabled', 'company_car',
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

    def to_internal_value(self, data):
        # Bo'sh stringlarni null'ga o'giramiz (UUIDField/email tekshiruvini buzmasligi uchun)
        cleaned = dict(data)
        for key in ('direction_id', 'chief_id'):
            if key in cleaned and cleaned[key] in ('', None):
                cleaned[key] = None
        if cleaned.get('email') == '':
            cleaned['email'] = None
        return super().to_internal_value(cleaned)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'father_name',
            'position_uz', 'position_ru',
            'phone_number', 'email', 'office_number',
            'role_id', 'direction_id', 'chief_id',
            'status', 'enabled', 'company_car',
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
