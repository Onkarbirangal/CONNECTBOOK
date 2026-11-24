from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('me/', views.CurrentUserAPIView.as_view(), name='current_user'),
    path('posts/', views.PostListCreateAPIView.as_view(), name='posts_list_create'),
    path('posts/<int:pk>/', views.PostDetailAPIView.as_view(), name='post_detail'),
    path('posts/<int:post_id>/comments/', views.PostCommentListCreateAPIView.as_view(), name='post_comments'),
    path('stories/', views.ActiveStoriesAPIView.as_view(), name='active_stories'),
    path('conversations/<int:conversation_id>/messages/', views.ConversationMessagesAPIView.as_view(), name='conversation_messages'),
    path('groups/', views.GroupListCreateAPIView.as_view(), name='groups_list_create'),
    path('notifications/', views.NotificationListAPIView.as_view(), name='notifications_list'),
]
