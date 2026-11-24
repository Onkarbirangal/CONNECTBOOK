from django.urls import path
from . import views

app_name = 'streaming'

urlpatterns = [
    path('', views.stream_list_view, name='stream_list'),
    path('schedule/', views.schedule_stream_view, name='schedule_stream'),
    path('create/', views.schedule_stream_view, name='create_stream'),
    path('<int:pk>/', views.stream_room_view, name='stream_room'),
    path('<int:pk>/dashboard/', views.stream_dashboard_view, name='stream_dashboard'),
    path('<int:pk>/status/', views.toggle_stream_status_view, name='toggle_status'),
    path('<int:pk>/chat/<int:message_id>/delete/', views.delete_stream_chat_view, name='delete_chat'),
]
