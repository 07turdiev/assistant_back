from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin

from .models import Direction


@admin.register(Direction)
class DirectionAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'organisation')
    list_display_links = ('indented_title',)
    search_fields = ('name_uz', 'name_ru')
    list_filter = ('organisation',)
