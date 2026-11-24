from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q
from social.models import Post, Comment, Reaction
from stories.models import Story
from chat.models import Conversation, Message
from groups_app.models import Group
from notifications.models import Notification
from .serializers import (
    UserSummarySerializer, PostSerializer, CommentSerializer,
    StorySerializer, MessageSerializer, GroupSerializer, NotificationSerializer
)

User = get_user_model()


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSummarySerializer(request.user)
        return Response(serializer.data)


class PostListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(privacy='public').select_related('author', 'author__profile').prefetch_related('media_files')[:30]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user and not self.request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        instance.delete()


class PostCommentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).select_related('author', 'author__profile')

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        serializer.save(author=self.request.user, post_id=post_id)


class ActiveStoriesAPIView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        return Story.objects.filter(expires_at__gt=timezone.now()).select_related('author', 'author__profile')


class ConversationMessagesAPIView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conv_id = self.kwargs['conversation_id']
        return Message.objects.filter(conversation_id=conv_id, is_deleted=False).select_related('sender', 'sender__profile')

    def perform_create(self, serializer):
        conv_id = self.kwargs['conversation_id']
        serializer.save(sender=self.request.user, conversation_id=conv_id)


class GroupListCreateAPIView(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        from groups_app.models import GroupMembership
        group = serializer.save(creator=self.request.user)
        GroupMembership.objects.create(group=group, user=self.request.user, role='admin')


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related('actor', 'actor__profile')
