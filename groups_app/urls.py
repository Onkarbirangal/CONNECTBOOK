from django.urls import path
from . import views

app_name = 'groups_app'

urlpatterns = [
    path('', views.group_list_view, name='list'),
    path('create/', views.create_group_view, name='create'),
    path('<slug:slug>/', views.group_detail_view, name='detail'),
    path('<slug:slug>/join/', views.join_group_view, name='join'),
    path('<slug:slug>/leave/', views.leave_group_view, name='leave'),
    path('<slug:slug>/announcements/create/', views.create_announcement_view, name='create_announcement'),
    path('<slug:slug>/rules/create/', views.create_rule_view, name='create_rule'),
]
