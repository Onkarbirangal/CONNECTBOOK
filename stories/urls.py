from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    path('create/', views.create_story_view, name='create_story'),
    path('new/', views.create_story_view, name='create'),
    path('archive/', views.story_archive_view, name='story_archive'),
    path('highlights/create/', views.create_highlight_view, name='create_highlight'),
    path('api/user/<int:user_id>/', views.user_stories_api, name='user_stories_api'),
    path('api/highlight/<int:highlight_id>/', views.highlight_stories_api, name='highlight_stories_api'),
    path('<int:story_id>/view/', views.view_story_api, name='view_story_api'),
    path('<int:story_id>/react/', views.react_story_api, name='react_story_api'),
    path('<int:story_id>/reply/', views.reply_story_api, name='reply_story_api'),
    path('<int:story_id>/delete/', views.delete_story_view, name='delete_story'),
]
