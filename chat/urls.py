from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.inbox_view, name='inbox'),
    path('messenger/', views.inbox_view, name='messenger'),
    path('<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('direct/<int:user_id>/', views.direct_chat_view, name='direct'),
    path('<int:conversation_id>/send/', views.send_message_http, name='send_http'),
    path('<int:conversation_id>/messages/', views.get_messages_api, name='get_messages'),
    path('<int:conversation_id>/toggle-mute/', views.toggle_mute_conversation_view, name='toggle_mute'),
    path('<int:conversation_id>/toggle-archive/', views.toggle_archive_conversation_view, name='toggle_archive'),
    path('messages/<int:message_id>/react/', views.react_message_view, name='react_message'),
    path('messages/<int:message_id>/edit/', views.edit_message_view, name='edit_message'),
    path('messages/<int:message_id>/delete/', views.delete_message_view, name='delete_message'),
    # V4 Calling routes
    path('call/start/<int:user_id>/<str:call_type>/', views.start_call_view, name='start_call'),
    path('call/<str:room_name>/', views.call_room_view, name='call_room'),
    path('call/<str:room_name>/end/', views.end_call_http_view, name='end_call_http'),
]
