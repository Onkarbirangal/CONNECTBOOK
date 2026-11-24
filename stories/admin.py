from django.contrib import admin
from .models import Story, StoryView

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'media_type', 'created_at', 'expires_at')

@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('story', 'viewer', 'viewed_at')
