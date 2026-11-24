"""
ASGI config for connectbook project.
Exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'connectbook.settings')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing
import notifications.routing
import streaming.routing

# Combined websocket url patterns
websocket_urlpatterns = (
    chat.routing.websocket_urlpatterns +
    notifications.routing.websocket_urlpatterns +
    streaming.routing.websocket_urlpatterns
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
