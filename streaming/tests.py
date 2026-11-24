from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from streaming.models import LiveStream

User = get_user_model()


class StreamingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.host = User.objects.create_user(username='broadcaster', email='stream@example.com', password='Password123!')
        self.client.login(username='broadcaster', password='Password123!')

    def test_schedule_and_start_broadcast(self):
        sched_time = timezone.now() + timedelta(days=1)
        res = self.client.post(reverse('streaming:schedule_stream'), {
            'title': 'Live Coding Session',
            'scheduled_start': sched_time.strftime('%Y-%m-%dT%H:%M'),
            'description': 'Building features live on ConnectBook.',
        })
        self.assertEqual(res.status_code, 302)
        stream = LiveStream.objects.filter(title='Live Coding Session').first()
        self.assertIsNotNone(stream)
        self.assertEqual(stream.status, 'scheduled')

        # Start stream
        start_res = self.client.post(reverse('streaming:toggle_status', kwargs={'pk': stream.pk}), {
            'action': 'start'
        })
        self.assertEqual(start_res.status_code, 302)
        stream.refresh_from_db()
        self.assertEqual(stream.status, 'live')

        # End stream
        end_res = self.client.post(reverse('streaming:toggle_status', kwargs={'pk': stream.pk}), {
            'action': 'end'
        })
        self.assertEqual(end_res.status_code, 302)
        stream.refresh_from_db()
        self.assertEqual(stream.status, 'ended')

    def test_v4_stream_dashboard_and_moderation(self):
        # Schedule stream
        stream = LiveStream.objects.create(
            title='Tech Talk',
            host=self.host,
            category='Education',
            audience='public',
            status='scheduled'
        )

        # Host can access studio dashboard
        dash_url = reverse('streaming:stream_dashboard', kwargs={'pk': stream.pk})
        res_dash = self.client.get(dash_url)
        self.assertEqual(res_dash.status_code, 200)

        # Other user cannot access host's studio dashboard
        viewer = User.objects.create_user(username='viewer_user', email='v@example.com', password='Password123!')
        self.client.login(username='viewer_user', password='Password123!')
        res_dash_unauth = self.client.get(dash_url)
        self.assertEqual(res_dash_unauth.status_code, 403)

        # Viewer can access public stream room
        room_url = reverse('streaming:stream_room', kwargs={'pk': stream.pk})
        res_room = self.client.get(room_url)
        self.assertEqual(res_room.status_code, 200)

        # Test deleting a chat message as host
        from streaming.models import LiveStreamChatMessage
        chat_msg = LiveStreamChatMessage.objects.create(stream=stream, sender=viewer, message='Hello world')
        self.client.login(username='broadcaster', password='Password123!')
        del_chat_res = self.client.post(reverse('streaming:delete_chat', kwargs={'pk': stream.pk, 'message_id': chat_msg.id}))
        self.assertEqual(del_chat_res.status_code, 200)
        chat_msg.refresh_from_db()
        self.assertTrue(chat_msg.is_deleted)

