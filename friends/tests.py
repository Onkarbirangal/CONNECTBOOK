from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from friends.models import FriendRequest, Friendship

User = get_user_model()

class FriendsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = User.objects.create_user(username='user1', email='u1@example.com', password='Password123!')
        self.u2 = User.objects.create_user(username='user2', email='u2@example.com', password='Password123!')

    def test_friend_request_flow(self):
        self.client.login(username='user1', password='Password123!')

        # Send request
        res = self.client.post(reverse('friends:send_request', kwargs={'user_id': self.u2.id}))
        self.assertEqual(res.status_code, 302)
        freq = FriendRequest.objects.filter(sender=self.u1, receiver=self.u2).first()
        self.assertIsNotNone(freq)
        self.assertEqual(freq.status, 'pending')

        # User2 logs in and accepts
        self.client.logout()
        self.client.login(username='user2', password='Password123!')
        res_acc = self.client.post(reverse('friends:accept_request', kwargs={'request_id': freq.id}))
        self.assertEqual(res_acc.status_code, 302)

        self.assertTrue(Friendship.are_friends(self.u1, self.u2))

    def test_v12_friends_tabs_and_search(self):
        u3 = User.objects.create_user(username='user3', email='u3@example.com', password='Password123!')
        Friendship.objects.create(user1=self.u1, user2=self.u2)
        FriendRequest.objects.create(sender=u3, receiver=self.u1, status='pending')

        self.client.login(username='user1', password='Password123!')

        # 1. All friends tab
        res_all = self.client.get(reverse('friends:list') + '?tab=all')
        self.assertEqual(res_all.status_code, 200)
        self.assertContains(res_all, 'user2')
        self.assertEqual(len(res_all.context['friends']), 1)
        self.assertEqual(res_all.context['total_friends_count'], 1)

        # 2. Search filtering
        res_search = self.client.get(reverse('friends:list') + '?tab=all&q=user2')
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(len(res_search.context['friends']), 1)

        res_search_empty = self.client.get(reverse('friends:list') + '?tab=all&q=nonexistent')
        self.assertEqual(res_search_empty.status_code, 200)
        self.assertEqual(len(res_search_empty.context['friends']), 0)

        # 3. Requests tab
        res_req = self.client.get(reverse('friends:list') + '?tab=requests')
        self.assertEqual(res_req.status_code, 200)
        self.assertEqual(len(res_req.context['pending_received']), 1)
        self.assertEqual(res_req.context['pending_received'][0].sender, u3)

        # 4. Suggestions tab
        res_sug = self.client.get(reverse('friends:list') + '?tab=suggestions')
        self.assertEqual(res_sug.status_code, 200)
        self.assertIn('suggested_list', res_sug.context)

        # 5. Birthdays, followers, following, blocked tabs
        for tab_name in ['birthdays', 'followers', 'following', 'blocked']:
            res = self.client.get(reverse('friends:list') + f'?tab={tab_name}')
            self.assertEqual(res.status_code, 200)

        # 6. Cancel request
        self.client.logout()
        self.client.login(username='user3', password='Password123!')
        res_cancel = self.client.post(reverse('friends:cancel_request', kwargs={'user_id': self.u1.id}))
        self.assertEqual(res_cancel.status_code, 302)
        self.assertFalse(FriendRequest.objects.filter(sender=u3, receiver=self.u1, status='pending').exists())

        # 7. Remove friend
        self.client.logout()
        self.client.login(username='user1', password='Password123!')
        res_remove = self.client.post(reverse('friends:remove_friend', kwargs={'user_id': self.u2.id}))
        self.assertEqual(res_remove.status_code, 302)
        self.assertFalse(Friendship.are_friends(self.u1, self.u2))
