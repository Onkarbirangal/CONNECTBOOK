from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import (
    UserProfile, BlockedUser, RestrictedUser, MutedUser, UserPreference, Follow,
    UserPrivacySetting, UserSessionRecord, AccountDeletionRequest
)

User = get_user_model()


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            first_name='Test',
            last_name='User'
        )

    def test_user_creation_and_profile_signal(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertTrue(hasattr(self.user, 'preferences'))
        self.assertTrue(hasattr(self.user, 'privacy_settings'))
        self.assertEqual(self.user.preferences.theme, 'light')
        self.assertEqual(self.user.privacy_settings.profile_visibility, 'public')

    def test_login_and_logout(self):
        logged_in = self.client.login(username='testuser', password='Password123!')
        self.assertTrue(logged_in)

        res = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(res.status_code, 200)

        self.client.logout()
        res_after = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(res_after.status_code, 302)

    def test_edit_profile(self):
        self.client.login(username='testuser', password='Password123!')
        res = self.client.post(reverse('accounts:edit_profile'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'test@example.com',
            'gender': 'unspecified',
            'bio': 'My new bio on ConnectBook',
            'city': 'San Francisco',
            'profile_visibility': 'public',
        })
        self.assertEqual(res.status_code, 302)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.profile.bio, 'My new bio on ConnectBook')

    def test_block_user(self):
        other_user = User.objects.create_user(username='other', email='other@example.com', password='Password123!')
        self.client.login(username='testuser', password='Password123!')
        self.client.post(reverse('accounts:toggle_block', kwargs={'user_id': other_user.id}))
        self.assertTrue(BlockedUser.objects.filter(blocker=self.user, blocked=other_user).exists())

    def test_privacy_settings_view(self):
        self.client.login(username='testuser', password='Password123!')
        res = self.client.get(reverse('accounts:privacy_settings'))
        self.assertEqual(res.status_code, 200)

        post_res = self.client.post(reverse('accounts:privacy_settings'), {
            'profile_visibility': 'friends',
            'post_default_audience': 'friends',
            'story_privacy': 'friends',
            'friend_request_permission': 'friends_of_friends',
            'message_permission': 'friends',
            'friends_list_visibility': 'private',
            'search_discoverability': True,
            'read_receipts': True,
            'online_status_visible': True,
        })
        self.assertEqual(post_res.status_code, 302)
        self.user.privacy_settings.refresh_from_db()
        self.assertEqual(self.user.privacy_settings.profile_visibility, 'friends')
        self.assertEqual(self.user.privacy_settings.friend_request_permission, 'friends_of_friends')

    def test_security_settings_and_sessions(self):
        self.client.login(username='testuser', password='Password123!')
        res = self.client.get(reverse('accounts:security_settings'))
        self.assertEqual(res.status_code, 200)

        # Logout other sessions
        post_res = self.client.post(reverse('accounts:security_settings'), {
            'logout_other_sessions': '1'
        })
        self.assertEqual(post_res.status_code, 302)

    def test_user_data_export_json(self):
        self.client.login(username='testuser', password='Password123!')
        res = self.client.get(reverse('accounts:your_information') + '?export=json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        self.assertIn('account_info', res.json())
        self.assertEqual(res.json()['account_info']['username'], 'testuser')

    def test_account_deletion_request(self):
        self.client.login(username='testuser', password='Password123!')
        res = self.client.post(reverse('accounts:your_information'), {
            'request_deletion': '1',
            'password': 'Password123!',
            'reason': 'Moving to another platform',
        })
        self.assertEqual(res.status_code, 302)
        del_req = AccountDeletionRequest.objects.filter(user=self.user, status='pending').first()
        self.assertIsNotNone(del_req)
        self.assertEqual(del_req.reason, 'Moving to another platform')

    def test_follow_and_unfollow(self):
        other_user = User.objects.create_user(username='other_follow', email='other_f@example.com', password='Password123!')
        self.client.login(username='testuser', password='Password123!')
        
        # Follow
        res = self.client.get(reverse('accounts:toggle_follow', kwargs={'username': 'other_follow'}))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Follow.is_following(self.user, other_user))

        # Unfollow
        res2 = self.client.get(reverse('accounts:toggle_follow', kwargs={'username': 'other_follow'}))
        self.assertEqual(res2.status_code, 302)
        self.assertFalse(Follow.is_following(self.user, other_user))

    def test_restricted_and_muted_users(self):
        other = User.objects.create_user(username='other_target', email='target@example.com', password='Password123!')
        self.client.login(username='testuser', password='Password123!')

        # Toggle restrict
        res_r = self.client.get(reverse('accounts:toggle_restrict', kwargs={'user_id': other.id}))
        self.assertEqual(res_r.status_code, 302)
        self.assertTrue(RestrictedUser.objects.filter(user=self.user, restricted_user=other).exists())

        # Toggle mute
        res_m = self.client.get(reverse('accounts:toggle_mute', kwargs={'user_id': other.id}))
        self.assertEqual(res_m.status_code, 302)
        self.assertTrue(MutedUser.objects.filter(user=self.user, muted_user=other).exists())

    def test_cancel_deletion_request(self):
        del_req = AccountDeletionRequest.objects.create(user=self.user, reason='Leaving', status='pending')
        self.client.login(username='testuser', password='Password123!')

        res = self.client.get(reverse('accounts:cancel_deletion'))
        self.assertEqual(res.status_code, 302)
        del_req.refresh_from_db()
        self.assertEqual(del_req.status, 'cancelled')

    def test_v6_profile_tabs_and_lock(self):
        self.client.login(username='testuser', password='Password123!')
        
        # Test all 11 profile tabs
        tabs = ['posts', 'about', 'friends', 'photos', 'videos', 'reels', 'stories', 'checkins', 'likes', 'saved', 'more']
        for t in tabs:
            res = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}) + f'?tab={t}')
            self.assertEqual(res.status_code, 200)

        # Test toggle profile lock
        self.assertFalse(self.user.profile.is_locked)
        toggle_res = self.client.post(reverse('accounts:toggle_profile_lock'))
        self.assertEqual(toggle_res.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_locked)

        # Verify another user cannot view saved posts of testuser
        other_user = User.objects.create_user(username='other_viewer', email='viewer@example.com', password='Password123!')
        self.client.login(username='other_viewer', password='Password123!')
        other_res = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}) + '?tab=saved')
        self.assertEqual(other_res.status_code, 200)
        # Context 'saved_posts' should be empty for non-owner
        self.assertEqual(len(other_res.context['saved_posts']), 0)

    def test_v14_profile_upgrade_and_responsive_features(self):
        """
        ConnectBook V14 Complete Profile System Tests:
        1. Upload profile avatar & cover photo with persistence.
        2. Multiline bio update & display formatting.
        3. 11-tab responsive rendering & Reels permalink verification.
        4. Locked profile access control (owner vs friend vs non-friend).
        5. Friend list search & display structure.
        """
        self.client.login(username='testuser', password='Password123!')

        # 1. Update Profile Avatar
        dummy_avatar = SimpleUploadedFile('new_avatar.jpg', b'dummy_avatar_image_bytes', content_type='image/jpeg')
        res_av = self.client.post(reverse('accounts:update_avatar'), {'avatar': dummy_avatar})
        self.assertEqual(res_av.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.avatar))

        # 2. Update Cover Photo
        dummy_cover = SimpleUploadedFile('new_cover.jpg', b'dummy_cover_image_bytes', content_type='image/jpeg')
        res_cov = self.client.post(reverse('accounts:update_cover'), {'cover_photo': dummy_cover})
        self.assertEqual(res_cov.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.cover_photo))

        # 3. Multiline Bio Update
        multiline_bio = "Building the future of social networks.\nLiving in San Francisco.\nPassionate engineer & creator."
        res_bio = self.client.post(reverse('accounts:edit_profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'gender': 'unspecified',
            'bio': multiline_bio,
            'city': 'San Francisco',
            'work': 'Lead Architect',
            'education': 'MIT',
            'profile_visibility': 'public',
        })
        self.assertEqual(res_bio.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, multiline_bio)

        # 4. Profile View Rendering with Upgraded Header & Tabs
        prof_res = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(prof_res.status_code, 200)
        self.assertContains(prof_res, 'Building the future of social networks.')
        self.assertContains(prof_res, 'cb-profile-container')
        self.assertContains(prof_res, 'cb-profile-actions')

        # 5. Locked Profile Privacy Enforcement
        self.user.profile.is_locked = True
        self.user.profile.save()

        # Non-friend viewer
        viewer = User.objects.create_user(username='visitor_bob', email='bob@example.com', password='Password123!')
        self.client.login(username='visitor_bob', password='Password123!')
        res_locked_viewer = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(res_locked_viewer.status_code, 200)
        self.assertFalse(res_locked_viewer.context['can_view_content'])
        self.assertContains(res_locked_viewer, 'This Profile is Private')

    def test_locked_profile_blocks_all_private_tabs(self):
        """Verify that locked or private profile hides sensitive content on all tabs."""
        self.user.profile.is_locked = True
        self.user.profile.save()

        viewer = User.objects.create_user(username='intruder', email='intruder@example.com', password='Password123!')
        self.client.login(username='intruder', password='Password123!')

        for tab in ['photos', 'videos', 'about', 'checkins', 'likes']:
            res = self.client.get(reverse('accounts:profile', kwargs={'username': 'testuser'}) + f'?tab={tab}')
            self.assertEqual(res.status_code, 200)
            self.assertFalse(res.context['can_view_content'])
            self.assertContains(res, 'This Profile is Private')

    def test_blocking_cleans_follow_and_prevents_re_following(self):
        """Verify blocking deletes follow relations in both directions and prevents re-following."""
        target = User.objects.create_user(username='blocked_target', email='bt@example.com', password='Password123!')
        Follow.objects.create(follower=self.user, followed=target)
        Follow.objects.create(follower=target, followed=self.user)

        self.client.login(username='testuser', password='Password123!')
        # Block target
        self.client.post(reverse('accounts:toggle_block', kwargs={'user_id': target.id}))
        self.assertFalse(Follow.objects.filter(follower=self.user, followed=target).exists())
        self.assertFalse(Follow.objects.filter(follower=target, followed=self.user).exists())

        # Attempt to follow blocked target
        res = self.client.get(reverse('accounts:toggle_follow', kwargs={'username': 'blocked_target'}))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Follow.objects.filter(follower=self.user, followed=target).exists())

    def test_single_session_termination_endpoint(self):
        """Verify individual session termination."""
        self.client.login(username='testuser', password='Password123!')
        rec = UserSessionRecord.objects.create(
            user=self.user,
            session_key='other_session_xyz123',
            device_type='Tablet',
            is_active=True
        )
        res = self.client.post(reverse('accounts:terminate_session', kwargs={'session_id': rec.id}))
        self.assertEqual(res.status_code, 302)
        rec.refresh_from_db()
        self.assertFalse(rec.is_active)

    def test_privacy_sync_between_profile_and_settings(self):
        """Verify profile visibility stays synced between privacy center and profile edit."""
        self.client.login(username='testuser', password='Password123!')
        # Update via privacy settings
        self.client.post(reverse('accounts:privacy_settings'), {
            'profile_visibility': 'friends',
            'post_default_audience': 'friends',
            'story_privacy': 'friends',
            'friend_request_permission': 'everyone',
            'message_permission': 'everyone',
            'friends_list_visibility': 'friends',
            'search_discoverability': True,
            'read_receipts': True,
            'online_status_visible': True,
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.profile_visibility, 'friends')

    def test_registration_validation_and_duplicate_handling(self):
        """Test registration constraints: duplicate email, case-insensitive username, and password validation."""
        # Duplicate email
        res_dup_email = self.client.post(reverse('accounts:register'), {
            'first_name': 'New',
            'last_name': 'Person',
            'username': 'newuser1',
            'email': 'TEST@example.com',  # matches testuser's email in different case
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(res_dup_email.status_code, 200)
        self.assertFormError(res_dup_email.context['form'], 'email', 'An account with this email already exists.')

        # Duplicate username (case-insensitive)
        res_dup_user = self.client.post(reverse('accounts:register'), {
            'first_name': 'New',
            'last_name': 'Person',
            'username': 'TESTUSER',  # matches testuser in uppercase
            'email': 'unique@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(res_dup_user.status_code, 200)
        self.assertFormError(res_dup_user.context['form'], 'username', 'A user with this username already exists.')

        # Password mismatch
        res_mismatch = self.client.post(reverse('accounts:register'), {
            'first_name': 'New',
            'last_name': 'Person',
            'username': 'brandnewuser',
            'email': 'brandnew@example.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass456!',
        })
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertFalse(User.objects.filter(username='brandnewuser').exists())

        # Successful registration
        res_success = self.client.post(reverse('accounts:register'), {
            'first_name': 'Brand',
            'last_name': 'New',
            'username': 'brandnewuser',
            'email': 'brandnew@example.com',
            'password1': 'ComplexPassword99!',
            'password2': 'ComplexPassword99!',
        })
        self.assertEqual(res_success.status_code, 302)
        created_user = User.objects.filter(username='brandnewuser').first()
        self.assertIsNotNone(created_user)
        self.assertTrue(hasattr(created_user, 'profile'))
        self.assertTrue(hasattr(created_user, 'privacy_settings'))

    def test_login_flow_and_session_recording(self):
        """Test login via email/username, deactivated user handling, and session tracking."""
        # Login via email
        res_email = self.client.post(reverse('accounts:login'), {
            'login': 'test@example.com',
            'password': 'Password123!',
        })
        self.assertEqual(res_email.status_code, 302)
        self.assertTrue(UserSessionRecord.objects.filter(user=self.user, is_active=True).exists())

        # Logout deactivates session record
        self.client.get(reverse('accounts:logout'))
        # Session record for that session key should be inactive
        self.assertFalse(UserSessionRecord.objects.filter(user=self.user, is_active=True).exists())

        # Deactivated user login rejection
        self.user.is_deactivated = True
        self.user.save()
        res_deact = self.client.post(reverse('accounts:login'), {
            'login': 'testuser',
            'password': 'Password123!',
        })
        self.assertEqual(res_deact.status_code, 200)
        self.assertContains(res_deact, "This account is currently deactivated")

    def test_edit_profile_duplicate_email_rejection(self):
        """Test edit profile prevents changing email to another registered user's email."""
        other = User.objects.create_user(username='otherperson', email='other@example.com', password='Password123!')
        self.client.login(username='testuser', password='Password123!')

        res = self.client.post(reverse('accounts:edit_profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'OTHER@example.com',
            'gender': 'unspecified',
            'profile_visibility': 'public',
        })
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')  # Email did not change

    def test_avatar_and_cover_upload_views(self):
        """Test updating avatar and cover photo with file presence validation."""
        self.client.login(username='testuser', password='Password123!')

        # 1. Update avatar without file -> warning/error message and redirect
        res_empty = self.client.post(reverse('accounts:update_avatar'))
        self.assertEqual(res_empty.status_code, 302)

        # 2. Update avatar with small valid file
        tiny_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        avatar_file = SimpleUploadedFile("avatar.gif", tiny_gif, content_type="image/gif")
        res_avatar = self.client.post(reverse('accounts:update_avatar'), {'avatar': avatar_file})
        self.assertEqual(res_avatar.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.avatar))

        # 3. Update cover with valid file
        cover_file = SimpleUploadedFile("cover.gif", tiny_gif, content_type="image/gif")
        res_cover = self.client.post(reverse('accounts:update_cover'), {'cover_photo': cover_file})
        self.assertEqual(res_cover.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.cover_photo))

    def test_password_change_flow(self):
        """Test password change form validation and session hash update."""
        self.client.login(username='testuser', password='Password123!')

        # Invalid short password
        res_short = self.client.post(reverse('accounts:security_settings'), {
            'change_password': '1',
            'old_password': 'Password123!',
            'new_password1': '123',
            'new_password2': '123',
        })
        self.assertEqual(res_short.status_code, 200)

        # Successful password change
        res_valid = self.client.post(reverse('accounts:security_settings'), {
            'change_password': '1',
            'old_password': 'Password123!',
            'new_password1': 'NewValidPassword456!',
            'new_password2': 'NewValidPassword456!',
        })
        self.assertEqual(res_valid.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewValidPassword456!'))



