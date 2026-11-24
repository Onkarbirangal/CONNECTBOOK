from django.contrib import admin
from .models import Event, EventRSVP


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'start_time', 'venue', 'privacy', 'created_at')
    search_fields = ('title', 'description', 'organizer__username', 'venue')
    list_filter = ('privacy', 'start_time')


@admin.register(EventRSVP)
class EventRSVPAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'status', 'created_at')
    list_filter = ('status',)
