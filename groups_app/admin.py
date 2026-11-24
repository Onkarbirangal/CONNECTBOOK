from django.contrib import admin
from .models import Group, GroupMembership, GroupJoinRequest

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'privacy', 'creator', 'created_at')

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'role', 'joined_at')

@admin.register(GroupJoinRequest)
class GroupJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'status', 'created_at')
