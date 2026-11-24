from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_list_view, name='list'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('api/unread-count/', views.unread_count_api, name='unread_count_api'),
    path('<int:notif_id>/delete/', views.delete_notification, name='delete'),
]
