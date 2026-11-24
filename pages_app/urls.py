from django.urls import path
from . import views

app_name = 'pages_app'

urlpatterns = [
    path('', views.page_list_view, name='page_list'),
    path('create/', views.create_page_view, name='create_page'),
    path('<slug:slug>/', views.page_detail_view, name='page_detail'),
    path('<slug:slug>/edit/', views.edit_page_view, name='edit_page'),
    path('<slug:slug>/delete/', views.delete_page_view, name='delete_page'),
    path('<slug:slug>/follow/', views.toggle_follow_page_view, name='toggle_follow'),
    path('<slug:slug>/analytics/', views.page_analytics_view, name='page_analytics'),
]
