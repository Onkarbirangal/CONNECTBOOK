from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from chat.models import Conversation, ConversationParticipant, Message, MessageReaction

User = get_user_model()


class ChatTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(username='alice', email='alice@example.com', password='Password123!')
        self.bob = User.objects.create_user(username='bob', email='bob@example.com', password='Password123!')
        self.conv = Conversation.objects.create(is_group=False)
        self.p_alice = ConversationParticipant.objects.create(conversation=self.conv, user=self.alice)
        self.p_bob = ConversationParticipant.objects.create(conversation=self.conv, user=self.bob)

    def test_send_message_and_reply(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(
            reverse('chat:send_http', kwargs={'conversation_id': self.conv.id}),
            data='{"message": "Hello Bob!"}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        msg1 = Message.objects.first()
        self.assertIsNotNone(msg1)
        self.assertEqual(msg1.content, 'Hello Bob!')

        # Bob replies to msg1
        self.client.login(username='bob', password='Password123!')
        res_reply = self.client.post(
            reverse('chat:send_http', kwargs={'conversation_id': self.conv.id}),
            data=f'{{"message": "Hi Alice, replying to you!", "reply_to_id": {msg1.id}}}',
            content_type='application/json'
        )
        self.assertEqual(res_reply.status_code, 200)
        msg2 = Message.objects.order_by('-created_at').first()
        self.assertEqual(msg2.reply_to, msg1)

    def test_message_reaction_and_edit_delete(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.alice, content='React to me')
        self.client.login(username='bob', password='Password123!')

        # Bob reacts
        res_react = self.client.post(reverse('chat:react_message', kwargs={'message_id': msg.id}), {
            'reaction': 'love'
        })
        self.assertEqual(res_react.status_code, 302)
        self.assertEqual(msg.reactions.count(), 1)
        self.assertEqual(msg.reactions.first().reaction, 'love')

        # Alice edits her message
        self.client.login(username='alice', password='Password123!')
        res_edit = self.client.post(reverse('chat:edit_message', kwargs={'message_id': msg.id}), {
            'content': 'Edited content'
        })
        self.assertEqual(res_edit.status_code, 302)
        msg.refresh_from_db()
        self.assertTrue(msg.is_edited)
        self.assertEqual(msg.content, 'Edited content')

        # Alice deletes her message
        res_del = self.client.post(reverse('chat:delete_message', kwargs={'message_id': msg.id}))
        self.assertEqual(res_del.status_code, 302)
        msg.refresh_from_db()
        self.assertTrue(msg.is_deleted)

    def test_conversation_mute_and_archive(self):
        self.client.login(username='alice', password='Password123!')

        # Toggle mute
        res_mute = self.client.post(reverse('chat:toggle_mute', kwargs={'conversation_id': self.conv.id}))
        self.assertEqual(res_mute.status_code, 302)
        self.p_alice.refresh_from_db()
        self.assertTrue(self.p_alice.is_muted)

        # Toggle archive
        res_arch = self.client.post(reverse('chat:toggle_archive', kwargs={'conversation_id': self.conv.id}))
        self.assertEqual(res_arch.status_code, 302)
        self.p_alice.refresh_from_db()
        self.assertTrue(self.p_alice.is_archived)

    def test_v4_webrtc_calling(self):
        self.client.login(username='alice', password='Password123!')

        # Start a video call with Bob
        res = self.client.get(reverse('chat:start_call', kwargs={'user_id': self.bob.id, 'call_type': 'video'}))
        self.assertEqual(res.status_code, 302)

        from chat.models import CallSession
        session = CallSession.objects.first()
        self.assertIsNotNone(session)
        self.assertEqual(session.caller, self.alice)
        self.assertEqual(session.receiver, self.bob)
        self.assertEqual(session.call_type, 'video')
        self.assertEqual(session.status, 'ringing')

        # Alice joins the call room
        room_url = reverse('chat:call_room', kwargs={'room_name': session.room_name})
        res_room_alice = self.client.get(room_url)
        self.assertEqual(res_room_alice.status_code, 200)

        # Bob joins the call room
        self.client.login(username='bob', password='Password123!')
        res_room_bob = self.client.get(room_url)
        self.assertEqual(res_room_bob.status_code, 200)

        # Unauthorized user charlie tries to join
        charlie = User.objects.create_user(username='charlie', email='charlie@example.com', password='Password123!')
        self.client.login(username='charlie', password='Password123!')
        res_room_charlie = self.client.get(room_url)
        self.assertEqual(res_room_charlie.status_code, 403)

        # End call via HTTP
        self.client.login(username='alice', password='Password123!')
        end_url = reverse('chat:end_call_http', kwargs={'room_name': session.room_name})
        res_end = self.client.post(end_url)
        self.assertEqual(res_end.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.status, 'ended')
        self.assertIsNotNone(session.ended_at)

    def test_v12_messenger_views_and_attachments(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='alice', password='Password123!')

        # 1. Messenger main view & conversation view render cleanly
        res_main = self.client.get(reverse('chat:messenger'))
        self.assertEqual(res_main.status_code, 200)

        res_conv = self.client.get(reverse('chat:conversation', kwargs={'conversation_id': self.conv.id}))
        self.assertEqual(res_conv.status_code, 200)
        self.assertEqual(res_conv.context['active_conversation'], self.conv)

        # 2. Model method parameter safety
        self.assertIsNotNone(self.conv.get_avatar_url())
        self.assertIsNotNone(self.conv.get_display_name())
        self.assertIsNotNone(self.conv.get_recipient())

        # 3. Conversation search filtering
        res_search_match = self.client.get(reverse('chat:messenger') + '?q=bob')
        self.assertEqual(res_search_match.status_code, 200)
        self.assertEqual(len(res_search_match.context['conversations']), 1)

        res_search_miss = self.client.get(reverse('chat:messenger') + '?q=nonexistent')
        self.assertEqual(res_search_miss.status_code, 200)
        self.assertEqual(len(res_search_miss.context['conversations']), 0)

        # 4. Send message with multipart image attachment
        fake_image = SimpleUploadedFile(
            name='test_chat_photo.jpg',
            content=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00',
            content_type='image/jpeg'
        )
        res_attach = self.client.post(
            reverse('chat:send_http', kwargs={'conversation_id': self.conv.id}),
            data={
                'message': 'Here is a photo attachment',
                'attachment': fake_image
            }
        )
        self.assertEqual(res_attach.status_code, 200)
        data = res_attach.json()
        self.assertTrue(data.get('success'))
        self.assertIsNotNone(data.get('attachment_url'))

        latest_msg = Message.objects.order_by('-created_at').first()
        self.assertEqual(latest_msg.content, 'Here is a photo attachment')
        self.assertTrue(bool(latest_msg.attachment))

        # 5. Responsive UI elements
        self.assertContains(res_conv, 'cb-chat-back-btn')
        self.assertContains(res_conv, 'cb-chat-action-btn')
        self.assertContains(res_conv, 'cb-composer-btn')
        self.assertContains(res_conv, 'cb-composer-input')
        self.assertContains(res_conv, 'cb-messenger-messages-area')
        self.assertContains(res_conv, 'cb-messenger-composer')
        self.assertContains(res_conv, 'viewport')

