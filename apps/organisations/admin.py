from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import District, Organisation, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'name_ru')
    search_fields = ('name_uz', 'name_ru')


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'name_ru', 'region')
    list_filter = ('region',)
    search_fields = ('name_uz', 'name_ru')


@admin.register(Organisation)
class OrganisationAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'phone_number', 'district')
    list_display_links = ('indented_title',)
    search_fields = ('name_uz', 'name_ru', 'phone_number')
    list_filter = ('district',)
