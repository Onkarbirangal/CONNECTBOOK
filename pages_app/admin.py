from django.contrib import admin
from .models import Page, PageFollow


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'owner', 'is_verified', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    list_filter = ('category', 'is_verified')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PageFollow)
class PageFollowAdmin(admin.ModelAdmin):
    list_display = ('page', 'user', 'created_at')
    search_fields = ('page__name', 'user__username')
