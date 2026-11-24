from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.overview_view, name='overview'),
    path('users/', views.users_management_view, name='users'),
    path('users/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),
    path('moderation/', views.moderation_queue_view, name='moderation'),
    path('moderation/bulk-resolve/', views.bulk_resolve_reports_view, name='bulk_resolve_reports'),
    path('reports/<int:report_id>/resolve/', views.resolve_report_view, name='resolve_report'),
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('privacy-security/', views.privacy_security_view, name='privacy_security'),
    path('privacy-security/deletion-request/<int:request_id>/<str:action>/', views.handle_deletion_request_view, name='handle_deletion_request'),
    path('sensitive-access/log/', views.log_sensitive_access_view, name='log_sensitive_access'),
    # V4 Moderation Routes
    path('media/', views.media_moderation_view, name='media_moderation'),
    path('media/video/<int:video_id>/delete/', views.delete_video_admin_view, name='admin_delete_video'),
    path('media/reel/<int:reel_id>/delete/', views.delete_reel_admin_view, name='admin_delete_reel'),
    path('streams/', views.streams_moderation_view, name='streams_moderation'),
    path('streams/<int:stream_id>/end/', views.force_end_stream_admin_view, name='admin_force_end_stream'),
]
