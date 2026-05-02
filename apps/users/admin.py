"""Minimal Django admin (emergency tools). Vue dashboard kundalik ish uchun."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'label_uz', 'label_ru')
    search_fields = ('name', 'label_uz')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('last_name', 'first_name')
    list_display = ('username', 'last_name', 'first_name', 'role', 'enabled', 'status', 'is_superuser')
    list_filter = ('role', 'enabled', 'status', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'phone_number', 'email')
    raw_id_fields = ('chief', 'direction', 'created_by', 'updated_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'father_name', 'phone_number', 'email', 'office_number')}),
        ('Position', {'fields': ('position_uz', 'position_ru', 'role', 'direction', 'chief')}),
        ('Status', {'fields': ('enabled', 'status', 'is_active')}),
        ('Telegram', {'fields': ('telegram_id',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Audit', {'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )
