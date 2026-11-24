from django.urls import path
from . import views

app_name = 'events_app'

urlpatterns = [
    path('', views.event_list_view, name='event_list'),
    path('create/', views.create_event_view, name='create_event'),
    path('<int:pk>/', views.event_detail_view, name='event_detail'),
    path('<int:pk>/edit/', views.edit_event_view, name='edit_event'),
    path('<int:pk>/delete/', views.delete_event_view, name='delete_event'),
    path('<int:pk>/rsvp/', views.event_rsvp_view, name='event_rsvp'),
]
