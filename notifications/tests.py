from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.services import send_notification
from accounts.models import MutedUser

User = get_user_model()


class NotificationsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.alice = User.objects.create_user(username='alice', email='alice@example.com', password='Password123!')
        self.bob = User.objects.create_user(username='bob', email='bob@example.com', password='Password123!')

    def test_send_notification_categorization(self):
        n1 = send_notification(
            recipient=self.bob,
            actor=self.alice,
            notification_type='message',
            title='New Message',
            message='Hello Bob'
        )
        self.assertIsNotNone(n1)
        self.assertEqual(n1.category, 'messages')

        n2 = send_notification(
            recipient=self.bob,
            actor=self.alice,
            notification_type='post_reaction',
            title='Liked your post',
            message='Alice liked your post'
        )
        self.assertIsNotNone(n2)
        self.assertEqual(n2.category, 'social')

    def test_muted_user_suppression(self):
        MutedUser.objects.create(user=self.bob, muted_user=self.alice)
        n = send_notification(
            recipient=self.bob,
            actor=self.alice,
            notification_type='post_comment',
            title='Commented on your post',
            message='Hey Bob!'
        )
        self.assertIsNone(n)

    def test_notification_list_category_filter(self):
        Notification.objects.create(recipient=self.bob, actor=self.alice, notification_type='message', category='messages', title='Msg 1')
        Notification.objects.create(recipient=self.bob, actor=self.alice, notification_type='post_reaction', category='social', title='Reaction 1')

        self.client.login(username='bob', password='Password123!')
        res_all = self.client.get(reverse('notifications:list'))
        self.assertEqual(res_all.status_code, 200)

        res_msg = self.client.get(reverse('notifications:list') + '?category=messages')
        self.assertEqual(res_msg.status_code, 200)
        self.assertEqual(len(res_msg.context['notifications']), 1)
