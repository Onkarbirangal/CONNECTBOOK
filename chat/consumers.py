import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        is_participant = await self.check_participant(self.conversation_id, self.user)
        if not is_participant:
            await self.close()
            return

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
        try:
            data = json.loads(text_data)
            action = data.get('action', 'message')

            if action == 'message':
                content = data.get('message', '').strip()
                reply_to_id = data.get('reply_to_id')
                if not content:
                    return

                msg_obj = await self.save_message(self.conversation_id, self.user, content, reply_to_id)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': msg_obj['id'],
                        'sender_id': self.user.id,
                        'sender_username': self.user.username,
                        'sender_name': self.user.get_display_name(),
                        'sender_avatar': msg_obj['avatar'],
                        'content': content,
                        'reply_to': msg_obj.get('reply_to'),
                        'created_at': msg_obj['created_at'],
                    }
                )
            elif action == 'react':
                msg_id = data.get('message_id')
                reaction = data.get('reaction', 'like')
                res = await self.save_reaction(msg_id, self.user, reaction)
                if res:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_reaction',
                            'message_id': msg_id,
                            'reaction': reaction,
                            'user_id': self.user.id,
                            'action': res['action'],
                        }
                    )
            elif action == 'edit':
                msg_id = data.get('message_id')
                new_content = data.get('content', '').strip()
                if new_content and await self.edit_message(msg_id, self.user, new_content):
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_edit',
                            'message_id': msg_id,
                            'content': new_content,
                        }
                    )
            elif action == 'delete':
                msg_id = data.get('message_id')
                if await self.delete_message(msg_id, self.user):
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_delete',
                            'message_id': msg_id,
                        }
                    )
            elif action == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'sender_id': self.user.id,
                        'sender_name': self.user.get_display_name(),
                        'is_typing': data.get('is_typing', True),
                    }
                )
        except Exception:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'content': event['content'],
            'reply_to': event.get('reply_to'),
            'created_at': event['created_at'],
        }))

    async def chat_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'reaction': event['reaction'],
            'user_id': event['user_id'],
            'action': event['action'],
        }))

    async def chat_edit(self, event):
        await self.send(text_data=json.dumps({
            'type': 'edit',
            'message_id': event['message_id'],
            'content': event['content'],
        }))

    async def chat_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': event['message_id'],
        }))

    async def typing_indicator(self, event):
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender_id': event['sender_id'],
                'sender_name': event['sender_name'],
                'is_typing': event['is_typing'],
            }))

    @database_sync_to_async
    def check_participant(self, conv_id, user):
        from chat.models import ConversationParticipant
        return ConversationParticipant.objects.filter(conversation_id=conv_id, user=user).exists()

    @database_sync_to_async
    def save_message(self, conv_id, user, content, reply_to_id=None):
        from chat.models import Conversation, Message
        from django.utils import timezone
        conv = Conversation.objects.get(id=conv_id)
        reply_to_msg = None
        if reply_to_id:
            reply_to_msg = Message.objects.filter(id=reply_to_id, conversation=conv).first()

        msg = Message.objects.create(
            conversation=conv,
            sender=user,
            content=content,
            reply_to=reply_to_msg
        )
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        avatar = user.profile.get_avatar_url() if hasattr(user, 'profile') else '/static/images/default-avatar.svg'

        reply_info = None
        if reply_to_msg:
            reply_info = {
                'id': reply_to_msg.id,
                'sender_name': reply_to_msg.sender.get_display_name(),
                'content': reply_to_msg.content[:60],
            }

        return {
            'id': msg.id,
            'created_at': msg.created_at.strftime('%I:%M %p'),
            'avatar': avatar,
            'reply_to': reply_info,
        }

    @database_sync_to_async
    def save_reaction(self, msg_id, user, reaction):
        from chat.models import Message, MessageReaction
        msg = Message.objects.filter(id=msg_id, conversation_id=self.conversation_id).first()
        if not msg:
            return None
        existing = MessageReaction.objects.filter(message=msg, user=user).first()
        if existing:
            if existing.reaction == reaction:
                existing.delete()
                return {'action': 'removed'}
            else:
                existing.reaction = reaction
                existing.save(update_fields=['reaction'])
                return {'action': 'updated'}
        else:
            MessageReaction.objects.create(message=msg, user=user, reaction=reaction)
            return {'action': 'added'}

    @database_sync_to_async
    def edit_message(self, msg_id, user, new_content):
        from chat.models import Message
        from django.utils import timezone
        msg = Message.objects.filter(id=msg_id, sender=user, conversation_id=self.conversation_id, is_deleted=False).first()
        if msg:
            msg.content = new_content
            msg.is_edited = True
            msg.edited_at = timezone.now()
            msg.save(update_fields=['content', 'is_edited', 'edited_at'])
            return True
        return False

    @database_sync_to_async
    def delete_message(self, msg_id, user):
        from chat.models import Message
        msg = Message.objects.filter(id=msg_id, sender=user, conversation_id=self.conversation_id).first()
        if msg:
            msg.is_deleted = True
            msg.content = 'This message was deleted'
            msg.save(update_fields=['is_deleted', 'content'])
            return True
        return False


# ========================================================
# V4: WEBRTC CALL SIGNALING CONSUMER
# ========================================================

class CallSignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'call_{self.room_name}'
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        can_participate = await self.check_call_participant(self.room_name, self.user)
        if not can_participate:
            await self.close()
            return

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
            # Notify peer that user left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_signal',
                    'sender_id': self.user.id,
                    'data': {'action': 'peer-left'}
                }
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'call-accept':
                await self.update_call_status(self.room_name, 'accepted')
            elif action == 'call-reject':
                await self.update_call_status(self.room_name, 'rejected')
            elif action == 'call-end':
                await self.update_call_status(self.room_name, 'ended')

            # Broadcast signaling payload to peer in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_signal',
                    'sender_id': self.user.id,
                    'data': data
                }
            )
        except Exception:
            pass

    async def call_signal(self, event):
        # Do not bounce back to self
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def check_call_participant(self, room_name, user):
        from chat.models import CallSession
        session = CallSession.objects.filter(room_name=room_name).first()
        if not session:
            return False
        return session.can_participate(user)

    @database_sync_to_async
    def update_call_status(self, room_name, status):
        from chat.models import CallSession
        from django.utils import timezone
        session = CallSession.objects.filter(room_name=room_name).first()
        if session:
            session.status = status
            if status == 'accepted' and not session.answered_at:
                session.answered_at = timezone.now()
            elif status in ['ended', 'rejected']:
                session.ended_at = timezone.now()
                if session.answered_at:
                    delta = (session.ended_at - session.answered_at).total_seconds()
                    session.duration_seconds = max(0, int(delta))
            session.save()
