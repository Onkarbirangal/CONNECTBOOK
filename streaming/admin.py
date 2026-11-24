from django.contrib import admin
from .models import LiveStream


@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'host', 'status', 'scheduled_start', 'viewer_count', 'created_at')
    search_fields = ('title', 'host__username')
    list_filter = ('status', 'scheduled_start')
