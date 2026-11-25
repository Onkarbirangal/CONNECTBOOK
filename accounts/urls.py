from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/avatar/update/', views.update_avatar_view, name='update_avatar'),
    path('profile/cover/update/', views.update_cover_view, name='update_cover'),
    path('profile/toggle-lock/', views.toggle_profile_lock_view, name='toggle_profile_lock'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/privacy/', views.privacy_settings_view, name='privacy_settings'),
    path('settings/security/', views.security_settings_view, name='security_settings'),
    path('settings/your-information/', views.your_information_view, name='your_information'),
    path('profile/<str:username>/follow/', views.toggle_follow_view, name='toggle_follow'),
    path('profile/<str:username>/followers/', views.followers_list_view, name='followers_list'),
    path('profile/<str:username>/following/', views.following_list_view, name='following_list'),
    path('deactivate/', views.deactivate_account_view, name='deactivate'),
    path('block/<int:user_id>/', views.toggle_block_user_view, name='toggle_block'),
    path('restrict/<int:user_id>/', views.toggle_restrict_user_view, name='toggle_restrict'),
    path('mute/<int:user_id>/', views.toggle_mute_user_view, name='toggle_mute'),
    path('session/<int:session_id>/terminate/', views.terminate_session_view, name='terminate_session'),
    path('cancel-deletion/', views.cancel_deletion_view, name='cancel_deletion'),
    path('api/toggle-theme/', views.api_toggle_theme, name='api_toggle_theme'),
    path('forgot-password/', views.ConnectBookPasswordResetView.as_view(), name='forgot_password'),
    path('password-reset/done/', views.ConnectBookPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.ConnectBookPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.ConnectBookPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
