from django.contrib import admin
from .models import Post, PostMedia, Reaction, Comment, CommentReaction, SavedPost, Hashtag, Report, AuditLog

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'privacy', 'group', 'created_at')
    list_filter = ('privacy', 'created_at')
    search_fields = ('content', 'author__username')
    inlines = [PostMediaInline]

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction_type', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'parent', 'created_at')

@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'saved_at')

@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'target_type', 'target_id', 'reason', 'status', 'created_at')
    list_filter = ('status', 'target_type', 'reason')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'target_repr')
