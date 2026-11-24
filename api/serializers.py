from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from social.models import Post, PostMedia, Reaction, Comment
from stories.models import Story
from chat.models import Message, Conversation
from groups_app.models import Group
from notifications.models import Notification

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.CharField(source='get_avatar_url', read_only=True)
    cover_url = serializers.CharField(source='get_cover_url', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['bio', 'city', 'work', 'education', 'website', 'avatar_url', 'cover_url']


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'display_name', 'profile']


class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'media_type', 'order']


class PostSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    media_files = PostMediaSerializer(many=True, read_only=True)
    total_reactions = serializers.IntegerField(read_only=True)
    total_comments = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'privacy', 'group',
            'created_at', 'media_files', 'total_reactions', 'total_comments'
        ]
        read_only_fields = ['author', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'parent', 'content', 'created_at']
        read_only_fields = ['author', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'author', 'media_type', 'media_file', 'text_content', 'background_color', 'created_at', 'expires_at']
        read_only_fields = ['author', 'created_at', 'expires_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'attachment', 'created_at', 'is_read']
        read_only_fields = ['sender', 'created_at']


class GroupSerializer(serializers.ModelSerializer):
    creator = UserSummarySerializer(read_only=True)
    members_count = serializers.IntegerField(source='memberships.count', read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'slug', 'description', 'privacy', 'creator', 'created_at', 'members_count']
        read_only_fields = ['creator', 'slug', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'actor', 'notification_type', 'title', 'message', 'target_url', 'is_read', 'created_at']
