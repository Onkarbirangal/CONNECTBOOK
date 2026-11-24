import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f'notify_{self.user.id}'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Client may send ping or mark-as-read acknowledgement
        pass

    async def user_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event.get('id'),
            'title': event.get('title'),
            'message': event.get('message'),
            'target_url': event.get('target_url', ''),
            'actor_name': event.get('actor_name', ''),
            'actor_avatar': event.get('actor_avatar', ''),
            'created_at': event.get('created_at', 'Just now'),
            'unread_count': event.get('unread_count', 1),
        }))
