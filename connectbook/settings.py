
"""
ConnectBook Django Settings
Tagline: Connect with Friends. Share Your World.

Environment:
- Local: SQLite
- Production: Render + SQLite Persistent Disk
- Server: Daphne / ASGI
- Static: WhiteNoise
- Media: Persistent Disk
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# ==========================================================
# BASE CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ==========================================================
# SECURITY SETTINGS
# ==========================================================

DEBUG = os.getenv("DEBUG", "True").lower() in (
    "true", "1", "yes"
)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = (
            "django-insecure-local-development-only"
        )
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is missing!"
        )


# ==========================================================
# ALLOWED HOSTS
# ==========================================================

allowed_hosts_str = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,testserver"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in allowed_hosts_str.split(",")
    if host.strip()
]

# Automatically allow Render hostname
render_hostname = os.getenv(
    "RENDER_EXTERNAL_HOSTNAME"
)

if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)


# ==========================================================
# APPLICATION DEFINITION
# ==========================================================

INSTALLED_APPS = [

    # Daphne
    "daphne",

    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third Party
    "rest_framework",
    "channels",

    # ConnectBook Applications
    "accounts.apps.AccountsConfig",
    "social.apps.SocialConfig",
    "friends.apps.FriendsConfig",
    "stories.apps.StoriesConfig",
    "chat.apps.ChatConfig",
    "groups_app.apps.GroupsAppConfig",
    "pages_app.apps.PagesAppConfig",
    "events_app.apps.EventsAppConfig",
    "marketplace.apps.MarketplaceConfig",
    "streaming.apps.StreamingConfig",
    "notifications.apps.NotificationsConfig",
    "admin_dashboard.apps.AdminDashboardConfig",
    "api.apps.ApiConfig",
]


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [

    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================================
# URL CONFIGURATION
# ==========================================================

ROOT_URLCONF = "connectbook.urls"

WSGI_APPLICATION = "connectbook.wsgi.application"

ASGI_APPLICATION = "connectbook.asgi.application"


# ==========================================================
# TEMPLATES
# ==========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates"
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [

                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",

                # Custom Context Processors
                "accounts.context_processors.user_profile_context",
                "notifications.context_processors.notification_badge_processor",
                "chat.context_processors.unread_messages_processor",
            ],
        },
    },
]


# ==========================================================
# DATABASE CONFIGURATION
# Local: SQLite
# Render: SQLite Persistent Disk
# ==========================================================

if os.getenv("RENDER") == "true" and Path("/var/data").exists():

    DATABASE_NAME = Path("/var/data/db.sqlite3")

else:

    DATABASE_NAME = BASE_DIR / "db.sqlite3"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",

        "NAME": DATABASE_NAME,

        "OPTIONS": {
            "timeout": 20,
        },
    }
}


# ==========================================================
# CUSTOM USER MODEL
# ==========================================================

AUTH_USER_MODEL = "accounts.CustomUser"


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),

        "OPTIONS": {
            "min_length": 8
        },
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==========================================================
# CHANNELS & WEBSOCKETS
# ==========================================================

CHANNEL_LAYERS = {

    "default": {

        "BACKEND": (
            "channels.layers.InMemoryChannelLayer"
        ),

    },

}


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ==========================================================
# STATIC FILE CONFIGURATION
# ==========================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = (
    [BASE_DIR / "static"]
    if (BASE_DIR / "static").is_dir()
    else []
)

STATIC_ROOT = BASE_DIR / "staticfiles"


# WhiteNoise Storage
STORAGES = {

    "default": {

        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),

    },

    "staticfiles": {

        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),

    },

}


# ==========================================================
# MEDIA FILE CONFIGURATION
# Local: media/
# Render: Persistent Disk
# ==========================================================

MEDIA_URL = "/media/"

if os.getenv("RENDER") == "true" and Path("/var/data").exists():

    MEDIA_ROOT = Path("/var/data/media")

else:

    MEDIA_ROOT = BASE_DIR / "media"


# ==========================================================
# DEFAULT PRIMARY KEY
# ==========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# AUTHENTICATION URLS
# ==========================================================

LOGIN_URL = "accounts:login"

LOGIN_REDIRECT_URL = "social:feed"

LOGOUT_REDIRECT_URL = "accounts:login"


# ==========================================================
# REST FRAMEWORK
# ==========================================================

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": [

        "rest_framework.authentication.SessionAuthentication",

    ],

    "DEFAULT_PERMISSION_CLASSES": [

        "rest_framework.permissions.IsAuthenticated",

    ],

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),

    "PAGE_SIZE": 10,

}


# ==========================================================
# MEDIA UPLOAD LIMITS
# 50 MB
# ==========================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800

FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800


# ==========================================================
# EMAIL CONFIGURATION
# ==========================================================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)

DEFAULT_FROM_EMAIL = (
    "ConnectBook <noreply@connectbook.local>"
)


# ==========================================================
# CSRF CONFIGURATION
# ==========================================================

csrf_origins_str = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://connectbook-3wej.onrender.com"
)

CSRF_TRUSTED_ORIGINS = [

    origin.strip()
    for origin in csrf_origins_str.split(",")
    if origin.strip()

]

# Automatically add Render HTTPS origin
if render_hostname:

    render_origin = f"https://{render_hostname}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:

        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ==========================================================
# PRODUCTION SECURITY
# ==========================================================

if not DEBUG:

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"


# ==========================================================
# END OF CONNECTBOOK SETTINGS
# ==========================================================
