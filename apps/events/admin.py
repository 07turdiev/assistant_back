from django.contrib import admin

from .models import Event, EventParticipant, PreEvent, Visitor


class VisitorInline(admin.TabularInline):
    model = Visitor
    extra = 0


class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 0
    raw_id_fields = ('user',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'start_time', 'end_time', 'sphere', 'type', 'is_important')
    list_filter = ('type', 'sphere', 'is_important', 'is_private')
    search_fields = ('title', 'description', 'address')
    raw_id_fields = ('direction', 'speaker', 'created_by', 'updated_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = [VisitorInline, EventParticipantInline]


@admin.register(PreEvent)
class PreEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'start_time', 'end_time')
    search_fields = ('title', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'organisation_name', 'event')
    search_fields = ('full_name', 'organisation_name')
    raw_id_fields = ('event',)
