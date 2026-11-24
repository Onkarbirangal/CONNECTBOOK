from django.urls import path
from . import views

app_name = 'friends'

urlpatterns = [
    path('', views.friends_list_view, name='list'),
    path('suggestions/', views.friend_suggestions_view, name='suggestions'),
    path('request/<int:user_id>/send/', views.send_friend_request, name='send_request'),
    path('request/<int:request_id>/accept/', views.accept_friend_request, name='accept_request'),
    path('request/<int:request_id>/reject/', views.reject_friend_request, name='reject_request'),
    path('request/<int:user_id>/cancel/', views.cancel_friend_request, name='cancel_request'),
    path('remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
]
