from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from events_app.models import Event, EventRSVP

User = get_user_model()


class EventsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='eventhost', email='host@example.com', password='Password123!')
        self.guest = User.objects.create_user(username='guest', email='guest@example.com', password='Password123!')
        self.client.login(username='eventhost', password='Password123!')

    def test_create_event_and_rsvp(self):
        start = timezone.now() + timedelta(days=3)
        res = self.client.post(reverse('events_app:create_event'), {
            'title': 'ConnectBook Launch Party',
            'venue': 'Seattle Waterfront',
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'privacy': 'public',
            'description': 'Celebration of ConnectBook social platform.',
        })
        self.assertEqual(res.status_code, 302)
        event = Event.objects.filter(title='ConnectBook Launch Party').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.organizer, self.user)
        self.assertEqual(event.going_count, 1) # organizer auto-going

        # Guest RSVPs interested
        self.client.login(username='guest', password='Password123!')
        rsvp_res = self.client.post(reverse('events_app:event_rsvp', kwargs={'pk': event.pk}), {
            'status': 'interested'
        })
        self.assertEqual(rsvp_res.status_code, 302)
        self.assertEqual(event.interested_count, 1)
