from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile, BlockedUser, UserPreference

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_deactivated')
    fieldsets = UserAdmin.fieldsets + (
        ('ConnectBook Info', {'fields': ('date_of_birth', 'gender', 'is_verified', 'is_deactivated')}),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'work', 'profile_visibility', 'updated_at')

@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'sound_enabled', 'email_notifications')
