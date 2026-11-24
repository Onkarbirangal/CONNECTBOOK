import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class LiveStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.room_group_name = f'live_stream_{self.stream_id}'
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            # Allow anonymous read-only if desired, but ConnectBook authenticated is preferred
            pass

        # Check if user is blocked from this stream
        is_blocked = await self.check_blocked(self.stream_id, self.user)
        if is_blocked:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Increment viewer count
        viewers = await self.increment_viewers(self.stream_id, self.user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'viewer_count_update',
                'viewer_count': viewers
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            # Decrement viewer count
            viewers = await self.decrement_viewers(self.stream_id, self.user)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'viewer_count_update',
                    'viewer_count': viewers
                }
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'chat':
                message = data.get('message', '').strip()
                if not message or not self.user or self.user.is_anonymous:
                    return

                msg_obj = await self.save_chat_message(self.stream_id, self.user, message)
                if msg_obj:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'stream_chat_message',
                            'id': msg_obj['id'],
                            'sender_name': self.user.get_display_name(),
                            'sender_avatar': msg_obj['avatar'],
                            'message': message,
                            'created_at': msg_obj['created_at'],
                        }
                    )
            elif action == 'reaction':
                reaction = data.get('reaction', '❤️')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'stream_reaction',
                        'reaction': reaction,
                        'user_name': self.user.get_display_name() if self.user and not self.user.is_anonymous else 'Viewer'
                    }
                )
            elif action == 'delete_message':
                msg_id = data.get('message_id')
                if await self.delete_chat_message(self.stream_id, self.user, msg_id):
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'stream_message_deleted',
                            'message_id': msg_id
                        }
                    )
        except Exception:
            pass

    async def viewer_count_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'viewers',
            'viewer_count': event['viewer_count']
        }))

    async def stream_chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'id': event['id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'message': event['message'],
            'created_at': event['created_at'],
        }))

    async def stream_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'reaction': event['reaction'],
            'user_name': event['user_name']
        }))

    async def stream_message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'deleted',
            'message_id': event['message_id']
        }))

    @database_sync_to_async
    def check_blocked(self, stream_id, user):
        if not user or user.is_anonymous:
            return False
        from streaming.models import LiveStreamBlockedUser
        return LiveStreamBlockedUser.objects.filter(stream_id=stream_id, user=user).exists()

    @database_sync_to_async
    def increment_viewers(self, stream_id, user):
        from streaming.models import LiveStream, LiveStreamViewer
        stream = LiveStream.objects.filter(id=stream_id).first()
        if not stream:
            return 0
        if stream.status == 'live':
            stream.viewer_count += 1
            if stream.viewer_count > stream.peak_viewers:
                stream.peak_viewers = stream.viewer_count
            stream.save(update_fields=['viewer_count', 'peak_viewers'])
            if user and not user.is_anonymous:
                LiveStreamViewer.objects.get_or_create(stream=stream, user=user)
        return stream.viewer_count

    @database_sync_to_async
    def decrement_viewers(self, stream_id, user):
        from streaming.models import LiveStream
        stream = LiveStream.objects.filter(id=stream_id).first()
        if not stream:
            return 0
        if stream.status == 'live' and stream.viewer_count > 0:
            stream.viewer_count -= 1
            stream.save(update_fields=['viewer_count'])
        return stream.viewer_count

    @database_sync_to_async
    def save_chat_message(self, stream_id, user, message):
        from streaming.models import LiveStream, LiveStreamChatMessage
        stream = LiveStream.objects.filter(id=stream_id).first()
        if not stream:
            return None
        msg = LiveStreamChatMessage.objects.create(stream=stream, sender=user, message=message[:500])
        avatar = user.profile.get_avatar_url() if hasattr(user, 'profile') else '/static/images/default-avatar.svg'
        return {
            'id': msg.id,
            'avatar': avatar,
            'created_at': msg.created_at.strftime('%I:%M %p')
        }

    @database_sync_to_async
    def delete_chat_message(self, stream_id, user, msg_id):
        from streaming.models import LiveStream, LiveStreamChatMessage
        stream = LiveStream.objects.filter(id=stream_id).first()
        if not stream or not user or (stream.host != user and not user.is_staff):
            return False
        msg = LiveStreamChatMessage.objects.filter(id=msg_id, stream=stream).first()
        if msg:
            msg.is_deleted = True
            msg.save(update_fields=['is_deleted'])
            return True
        return False
