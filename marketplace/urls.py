from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.listing_list_view, name='listing_list'),
    path('create/', views.create_listing_view, name='create_listing'),
    path('<int:pk>/', views.listing_detail_view, name='listing_detail'),
    path('<int:pk>/edit/', views.edit_listing_view, name='edit_listing'),
    path('<int:pk>/delete/', views.delete_listing_view, name='delete_listing'),
    path('<int:pk>/toggle-status/', views.toggle_status_view, name='toggle_status'),
    path('<int:pk>/save/', views.toggle_save_listing_view, name='toggle_save'),
    path('<int:pk>/inquire/', views.send_inquiry_view, name='send_inquiry'),
    path('dashboard/', views.seller_dashboard_view, name='seller_dashboard'),
]
