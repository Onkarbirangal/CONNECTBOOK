"""
ConnectBook Django Settings
Tagline: Connect with Friends. Share Your World.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-connectbook-default-dev-secret-key-3.12')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')


allowed_hosts_str = os.getenv(
    'ALLOWED_HOSTS',
    '127.0.0.1,localhost,testserver'
)

ALLOWED_HOSTS = [
    host.strip()
    for host in allowed_hosts_str.split(',')
    if host.strip()
]

# Automatically allow Render hostname
render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')

if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)


# Application definition
INSTALLED_APPS = [
    # Daphne must be listed before django.contrib.staticfiles
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'channels',

    # ConnectBook apps
    'accounts.apps.AccountsConfig',
    'social.apps.SocialConfig',
    'friends.apps.FriendsConfig',
    'stories.apps.StoriesConfig',
    'chat.apps.ChatConfig',
    'groups_app.apps.GroupsAppConfig',
    'pages_app.apps.PagesAppConfig',
    'events_app.apps.EventsAppConfig',
    'marketplace.apps.MarketplaceConfig',
    'streaming.apps.StreamingConfig',
    'notifications.apps.NotificationsConfig',
    'admin_dashboard.apps.AdminDashboardConfig',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'connectbook.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                # ConnectBook custom context processors
                'accounts.context_processors.user_profile_context',
                'notifications.context_processors.notification_badge_processor',
                'chat.context_processors.unread_messages_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'connectbook.wsgi.application'
ASGI_APPLICATION = 'connectbook.asgi.application'

# Database: SQLite ONLY as per strict project specification
# Database: Local SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
        },
    }
}
# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Channels & WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Local filesystem storage only)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'social:feed'
LOGOUT_REDIRECT_URL = 'accounts:login'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
# Media Limits (50MB max upload)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Email configuration (Console backend for local development)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = 'ConnectBook <noreply@connectbook.local>'

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'https://connectbook-navy.vercel.app'
    ).split(',')
    if origin.strip()
]

# Production Security
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True