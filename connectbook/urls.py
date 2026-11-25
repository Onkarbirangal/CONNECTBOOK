"""
ConnectBook URL Configuration
Tagline: Connect with Friends. Share Your World.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('admin_dashboard.urls')),
    path('dashboard/', RedirectView.as_view(url='/admin-panel/', permanent=False)),
    path('accounts/', include('accounts.urls')),
    path('settings/privacy/', accounts_views.privacy_settings_view, name='privacy_settings_root'),
    path('settings/security/', accounts_views.security_settings_view, name='security_settings_root'),
    path('settings/your-information/', accounts_views.your_information_view, name='your_information_root'),
    path('accounts/reset/<uidb64>/<token>/', accounts_views.ConnectBookPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/password-reset/confirm/<uidb64>/<token>/', accounts_views.ConnectBookPasswordResetConfirmView.as_view()),
    path('friends/', include('friends.urls')),
    path('stories/', include('stories.urls')),
    path('chat/', include('chat.urls')),
    path('groups/', include('groups_app.urls')),
    path('pages/', include('pages_app.urls')),
    path('events/', include('events_app.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('live/', include('streaming.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/', include('api.urls')),
    path('', include('social.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
