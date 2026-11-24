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

    def test_friend_request_permission_privacy(self):
        """Verify friend_request_permission='friends_of_friends' restricts strangers."""
        from accounts.models import UserPrivacySetting
        ps, _ = UserPrivacySetting.objects.get_or_create(user=self.u2)
        ps.friend_request_permission = 'friends_of_friends'
        ps.save()

        # u1 and u2 have NO mutual friends
        self.client.login(username='user1', password='Password123!')
        res = self.client.post(reverse('friends:send_request', kwargs={'user_id': self.u2.id}))
        self.assertEqual(res.status_code, 302)
        # Request should not be created
        self.assertFalse(FriendRequest.objects.filter(sender=self.u1, receiver=self.u2).exists())

    def test_friend_suggestions_view_and_ajax_endpoints(self):
        """Test People You May Know suggestions view, AJAX request, dismissal, and undo."""
        u3 = User.objects.create_user(username='user3', email='u3@example.com', password='Password123!')
        self.client.login(username='user1', password='Password123!')

        # 1. Suggestions page via /friends/suggestions/ and /friends/?tab=suggestions
        res1 = self.client.get(reverse('friends:suggestions'))
        self.assertEqual(res1.status_code, 200)
        self.assertIn('suggested_list', res1.context)

        res2 = self.client.get(reverse('friends:list') + '?tab=suggestions')
        self.assertEqual(res2.status_code, 200)
        self.assertIn('suggested_list', res2.context)

        # 2. AJAX Send friend request
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        res_send = self.client.post(
            reverse('friends:send_request', kwargs={'user_id': u3.id}),
            **ajax_headers
        )
        self.assertEqual(res_send.status_code, 200)
        data = res_send.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'sent')
        self.assertTrue(FriendRequest.objects.filter(sender=self.u1, receiver=u3, status='pending').exists())

        # 3. Cannot send to self via AJAX
        res_self = self.client.post(
            reverse('friends:send_request', kwargs={'user_id': self.u1.id}),
            **ajax_headers
        )
        self.assertEqual(res_self.status_code, 400)
        self.assertFalse(res_self.json()['success'])

        # 4. AJAX Cancel friend request
        res_cancel = self.client.post(
            reverse('friends:cancel_request', kwargs={'user_id': u3.id}),
            **ajax_headers
        )
        self.assertEqual(res_cancel.status_code, 200)
        cancel_data = res_cancel.json()
        self.assertTrue(cancel_data['success'])
        self.assertEqual(cancel_data['status'], 'cancelled')
        self.assertFalse(FriendRequest.objects.filter(sender=self.u1, receiver=u3, status='pending').exists())

        # 5. Dismiss friend suggestion
        res_dismiss = self.client.post(
            reverse('friends:dismiss_suggestion', kwargs={'user_id': u3.id}),
            **ajax_headers
        )
        self.assertEqual(res_dismiss.status_code, 200)
        self.assertTrue(res_dismiss.json()['success'])

        # Verify dismissed user is now excluded from suggestions
        res_after_dismiss = self.client.get(reverse('friends:list') + '?tab=suggestions')
        suggested_ids = [u.id for u in res_after_dismiss.context['suggested_list']]
        self.assertNotIn(u3.id, suggested_ids)

        # 6. Undo dismiss friend suggestion
        res_undo = self.client.post(
            reverse('friends:undo_dismiss_suggestion', kwargs={'user_id': u3.id}),
            **ajax_headers
        )
        self.assertEqual(res_undo.status_code, 200)
        self.assertTrue(res_undo.json()['success'])

        # Verify user reappears in suggestions
        res_after_undo = self.client.get(reverse('friends:list') + '?tab=suggestions')
        suggested_ids_undo = [u.id for u in res_after_undo.context['suggested_list']]
        self.assertIn(u3.id, suggested_ids_undo)

    def test_ajax_accept_and_reject_request(self):
        """Test AJAX accept and reject friend request endpoints."""
        freq = FriendRequest.objects.create(sender=self.u2, receiver=self.u1, status='pending')
        self.client.login(username='user1', password='Password123!')
        ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        # Accept request via AJAX
        res_acc = self.client.post(
            reverse('friends:accept_request', kwargs={'request_id': freq.id}),
            **ajax_headers
        )
        self.assertEqual(res_acc.status_code, 200)
        self.assertTrue(res_acc.json()['success'])
        self.assertTrue(Friendship.are_friends(self.u1, self.u2))

        # Test Reject with a new request
        u4 = User.objects.create_user(username='user4', email='u4@example.com', password='Password123!')
        freq2 = FriendRequest.objects.create(sender=u4, receiver=self.u1, status='pending')
        res_rej = self.client.post(
            reverse('friends:reject_request', kwargs={'request_id': freq2.id}),
            **ajax_headers
        )
        self.assertEqual(res_rej.status_code, 200)
        self.assertTrue(res_rej.json()['success'])
        freq2.refresh_from_db()
        self.assertEqual(freq2.status, 'rejected')

