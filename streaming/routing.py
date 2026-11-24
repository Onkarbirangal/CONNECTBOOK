from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/live/<int:stream_id>/', consumers.LiveStreamConsumer.as_asgi()),
]
