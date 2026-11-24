from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from social.models import Post, Reaction, Comment, SavedPost, PhotoAlbum, AlbumPhoto, Reel, SavedReel, ReelView, ReelComment
from friends.models import Friendship

User = get_user_model()

class SocialTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.u1 = User.objects.create_user(username='alice', email='alice@example.com', password='Password123!')
        self.u2 = User.objects.create_user(username='bob', email='bob@example.com', password='Password123!')
        self.u3 = User.objects.create_user(username='charlie', email='charlie@example.com', password='Password123!')
        Friendship.objects.create(user1=self.u1, user2=self.u2)

    def test_post_creation_and_privacy(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(reverse('social:create_post'), {
            'content': 'Hello ConnectBook friends! #testing',
            'privacy': 'friends',
        })
        self.assertEqual(res.status_code, 302)
        post = Post.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.content, 'Hello ConnectBook friends! #testing')

        # Bob is friend, can view
        self.assertTrue(post.can_view(self.u2))
        # Charlie is not friend, cannot view
        self.assertFalse(post.can_view(self.u3))

    def test_reaction_and_comment(self):
        post = Post.objects.create(author=self.u1, content='Public post', privacy='public')
        self.client.login(username='bob', password='Password123!')

        # React
        res_react = self.client.post(
            reverse('social:react_post', kwargs={'post_id': post.id}),
            data='{"reaction_type": "love"}',
            content_type='application/json'
        )
        self.assertEqual(res_react.status_code, 200)
        self.assertEqual(post.reactions.count(), 1)
        self.assertEqual(post.reactions.first().reaction_type, 'love')

        # Comment
        res_comment = self.client.post(reverse('social:add_comment', kwargs={'post_id': post.id}), {
            'content': 'Great post!'
        })
        self.assertEqual(res_comment.status_code, 302)
        self.assertEqual(post.comments.count(), 1)

    def test_v3_post_features(self):
        self.client.login(username='alice', password='Password123!')

        # Create draft post
        res_draft = self.client.post(reverse('social:create_post'), {
            'content': 'Draft post content',
            'status': 'draft',
            'privacy': 'public',
        })
        self.assertEqual(res_draft.status_code, 302)
        draft = Post.objects.filter(status='draft').first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.content, 'Draft post content')

        # Edit post and verify edit history
        post = Post.objects.create(author=self.u1, content='Original content', privacy='public')
        res_edit = self.client.post(reverse('social:edit_post', kwargs={'post_id': post.id}), {
            'content': 'Updated content',
            'privacy': 'public',
        })
        self.assertEqual(res_edit.status_code, 302)
        post.refresh_from_db()
        self.assertTrue(post.is_edited)
        self.assertEqual(post.content, 'Updated content')
        self.assertEqual(len(post.edit_history), 1)

        # Toggle archive
        self.client.post(reverse('social:toggle_archive_post', kwargs={'post_id': post.id}))
        post.refresh_from_db()
        self.assertTrue(post.is_archived)

        # Toggle comments
        self.client.post(reverse('social:toggle_comments_post', kwargs={'post_id': post.id}))
        post.refresh_from_db()
        self.assertFalse(post.comments_enabled)

        # Disallow new comments when comments_enabled is False
        self.client.login(username='bob', password='Password123!')
        res_blocked_comment = self.client.post(reverse('social:add_comment', kwargs={'post_id': post.id}), {
            'content': 'This comment should not be allowed'
        })
        self.assertEqual(post.comments.count(), 0)

        # Test saved posts with collections
        self.client.login(username='alice', password='Password123!')
        res_save = self.client.post(reverse('social:toggle_save_post', kwargs={'post_id': post.id}), {
            'collection_name': 'Inspiration'
        })
        self.assertEqual(res_save.status_code, 302)
        saved = SavedPost.objects.filter(user=self.u1, post=post).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.collection_name, 'Inspiration')

        # Test feed tabs
        for tab in ['for_you', 'friends', 'following', 'trending', 'latest', 'drafts', 'archived']:
            res_tab = self.client.get(reverse('social:feed') + f'?tab={tab}')
            self.assertEqual(res_tab.status_code, 200)

    def test_v4_polls_creation_and_voting(self):
        self.client.login(username='alice', password='Password123!')
        res = self.client.post(reverse('social:create_post'), {
            'content': 'What is your favorite language?',
            'privacy': 'public',
            'poll_question': 'Favorite programming language?',
            'poll_option_1': 'Python',
            'poll_option_2': 'JavaScript',
            'poll_option_3': 'Rust',
            'poll_expiration_days': '7',
        })
        self.assertEqual(res.status_code, 302)

        from social.models import Poll, PollOption, PollVote
        post = Post.objects.filter(author=self.u1).order_by('-created_at').first()
        self.assertIsNotNone(post.poll)
        self.assertEqual(post.poll.question, 'Favorite programming language?')
        self.assertEqual(post.poll.options.count(), 3)

        opt_python = post.poll.options.filter(text='Python').first()
        opt_js = post.poll.options.filter(text='JavaScript').first()

        # Bob votes for Python
        self.client.login(username='bob', password='Password123!')
        vote_res = self.client.post(reverse('social:vote_poll', kwargs={'post_id': post.id}), {
            'option_id': opt_python.id
        })
        self.assertEqual(vote_res.status_code, 302)
        self.assertEqual(opt_python.votes_count, 1)
        self.assertEqual(opt_python.percentage, 100.0)

        # Bob changes vote to JavaScript
        vote_res2 = self.client.post(reverse('social:vote_poll', kwargs={'post_id': post.id}), {
            'option_id': opt_js.id
        })
        self.assertEqual(vote_res2.status_code, 302)
        opt_python.refresh_from_db()
        opt_js.refresh_from_db()
        self.assertEqual(opt_python.votes_count, 0)
        self.assertEqual(opt_js.votes_count, 1)

    def test_v4_video_and_reel_models_and_views(self):
        from social.models import Video, Reel, VideoComment, ReelReaction
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create dummy video
        dummy_video_file = SimpleUploadedFile("sample.mp4", b"dummy video content", content_type="video/mp4")
        video = Video.objects.create(
            author=self.u1,
            title='Django 5.2 Deep Dive',
            video_file=dummy_video_file,
            duration=125,
            privacy='public'
        )
        self.assertEqual(video.duration_formatted, '02:05')

        # Video detail view
        self.client.login(username='bob', password='Password123!')
        res_vdetail = self.client.get(reverse('social:video_detail', kwargs={'video_id': video.id}))
        self.assertEqual(res_vdetail.status_code, 200)

        # React to video
        react_res = self.client.post(reverse('social:react_video', kwargs={'video_id': video.id}), {
            'reaction_type': 'like'
        })
        self.assertEqual(react_res.status_code, 302)
        self.assertEqual(video.reactions.count(), 1)

        # Comment on video
        comment_res = self.client.post(reverse('social:add_video_comment', kwargs={'video_id': video.id}), {
            'content': 'Awesome video tutorial!'
        })
        self.assertEqual(comment_res.status_code, 302)
        self.assertEqual(video.comments.count(), 1)

        # Create dummy reel
        dummy_reel_file = SimpleUploadedFile("sample_reel.mp4", b"dummy reel content", content_type="video/mp4")
        reel = Reel.objects.create(
            author=self.u1,
            video_file=dummy_reel_file,
            caption='ConnectBook V4 Reel!'
        )

        # React to reel
        reel_react = self.client.post(reverse('social:react_reel', kwargs={'reel_id': reel.id}))
        self.assertEqual(reel_react.status_code, 302)
        self.assertEqual(reel.reactions.count(), 1)

        # Creator Studio & Explore Views
        self.client.login(username='alice', password='Password123!')
        res_studio = self.client.get(reverse('social:creator_studio'))
        self.assertEqual(res_studio.status_code, 200)

        res_explore = self.client.get(reverse('social:explore'))
        self.assertEqual(res_explore.status_code, 200)

    def test_v5_post_creation_types_and_backgrounds(self):
        self.client.login(username='alice', password='Password123!')

        # 1. Background style post
        res_bg = self.client.post(reverse('social:create_post'), {
            'content': 'Celebrating ConnectBook V5 launch!',
            'privacy': 'public',
            'background_style': 'grad_sunset',
            'post_type': 'text',
        })
        self.assertEqual(res_bg.status_code, 302)
        post_bg = Post.objects.filter(background_style='grad_sunset').first()
        self.assertIsNotNone(post_bg)
        self.assertEqual(post_bg.background_style, 'grad_sunset')

        # 2. Milestone post
        res_ms = self.client.post(reverse('social:create_post'), {
            'content': 'Promoted to Principal Architect today!',
            'privacy': 'friends',
            'milestone_title': 'Career Promotion',
            'post_type': 'milestone',
        })
        self.assertEqual(res_ms.status_code, 302)
        post_ms = Post.objects.filter(milestone_title='Career Promotion').first()
        self.assertIsNotNone(post_ms)
        self.assertEqual(post_ms.post_type, 'milestone')

        # 3. Feeling / Activity & Location post
        res_feeling = self.client.post(reverse('social:create_post'), {
            'content': 'Hiking at the bridge with friends!',
            'privacy': 'public',
            'feeling_category': 'feelings',
            'feeling_text': 'energized',
            'feeling_icon': '⚡',
            'location_name': 'Golden Gate Bridge',
            'location_address': 'San Francisco, CA',
            'post_type': 'feeling',
        })
        self.assertEqual(res_feeling.status_code, 302)
        post_f = Post.objects.filter(feeling_text='energized').first()
        self.assertIsNotNone(post_f)
        self.assertEqual(post_f.location_name, 'Golden Gate Bridge')
        self.assertEqual(post_f.feeling_icon, '⚡')

        # 4. Link sharing post
        res_link = self.client.post(reverse('social:create_post'), {
            'content': 'Check out this awesome announcement',
            'privacy': 'public',
            'link_url': 'https://example.com/announcement',
            'link_title': 'V5 Official Announcement',
            'link_description': 'All details inside',
            'post_type': 'link',
        })
        self.assertEqual(res_link.status_code, 302)
        post_l = Post.objects.filter(link_url='https://example.com/announcement').first()
        self.assertIsNotNone(post_l)
        self.assertEqual(post_l.link_title, 'V5 Official Announcement')

    def test_v5_tagging_and_notifications(self):
        from notifications.models import Notification
        self.client.login(username='alice', password='Password123!')

        # Tag Bob in a post
        res = self.client.post(reverse('social:create_post'), {
            'content': 'Coffee meetup with @bob!',
            'privacy': 'friends',
            'tagged_user_ids': str(self.u2.id),
        })
        self.assertEqual(res.status_code, 302)
        post = Post.objects.filter(content='Coffee meetup with @bob!').first()
        self.assertIsNotNone(post)
        self.assertIn(self.u2, post.tagged_users.all())

        # Verify Bob received notification
        notif = Notification.objects.filter(recipient=self.u2, actor=self.u1, notification_type='tag').first()
        self.assertIsNotNone(notif)
        self.assertIn('tagged you in a post', notif.message)

        # Tag search API
        search_res = self.client.get(reverse('social:tag_search') + '?q=bob')
        self.assertEqual(search_res.status_code, 200)
        users = search_res.json().get('users', [])
        self.assertTrue(any(u['username'] == 'bob' for u in users))

    def test_v5_custom_audiences_and_permissions(self):
        u4 = User.objects.create_user(username='david', email='david@example.com', password='Password123!')
        Friendship.objects.create(user1=self.u1, user2=u4)

        # 1. Friends except Bob
        p_except = Post.objects.create(author=self.u1, content='Secret from Bob', privacy='friends_except')
        p_except.custom_audience_deny.add(self.u2)

        self.assertTrue(p_except.can_view(self.u1)) # author can view
        self.assertFalse(p_except.can_view(self.u2)) # Bob is denied
        self.assertTrue(p_except.can_view(u4))       # David is friend, allowed
        self.assertFalse(p_except.can_view(self.u3)) # Charlie is not friend, denied

        # 2. Specific friends only (Bob only)
        p_specific = Post.objects.create(author=self.u1, content='Only for Bob', privacy='specific_friends')
        p_specific.custom_audience_allow.add(self.u2)

        self.assertTrue(p_specific.can_view(self.u1))
        self.assertTrue(p_specific.can_view(self.u2)) # Bob is in allow list
        self.assertFalse(p_specific.can_view(u4))     # David is friend but not in allow list

    def test_v5_care_reaction(self):
        post = Post.objects.create(author=self.u1, content='Support post', privacy='public')
        self.client.login(username='bob', password='Password123!')

        res = self.client.post(
            reverse('social:react_post', kwargs={'post_id': post.id}),
            data='{"reaction_type": "care"}',
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(post.reactions.count(), 1)
        self.assertEqual(post.reactions.first().reaction_type, 'care')
        self.assertEqual(post.reaction_counts['care'], 1)
        self.assertEqual(post.total_reactions, 1)

    def test_v5_post_views_and_insights_api(self):
        from social.models import PostView
        post = Post.objects.create(author=self.u1, content='Insights test post', privacy='public')

        self.client.login(username='bob', password='Password123!')
        # Bob views post
        view_res = self.client.post(reverse('social:record_post_view', kwargs={'post_id': post.id}))
        self.assertEqual(view_res.status_code, 200)
        self.assertEqual(PostView.objects.filter(post=post).count(), 1)
        post.refresh_from_db()
        self.assertEqual(post.views_count, 1)

        # Charlie views post
        self.client.login(username='charlie', password='Password123!')
        self.client.post(reverse('social:record_post_view', kwargs={'post_id': post.id}))
        post.refresh_from_db()
        self.assertEqual(post.views_count, 2)

        # Add reaction and comment
        Reaction.objects.create(user=self.u2, post=post, reaction_type='love')
        Comment.objects.create(author=self.u2, post=post, content='Loved it!')

        # Author checks insights
        self.client.login(username='alice', password='Password123!')
        insights_res = self.client.get(reverse('social:post_insights', kwargs={'post_id': post.id}))
        self.assertEqual(insights_res.status_code, 200)
        data = insights_res.json().get('data', {})
        self.assertEqual(data['reach'], 2)
        self.assertEqual(data['reactions_count'], 1)
        self.assertEqual(data['comments_count'], 1)
        self.assertGreater(data['engagement_rate'], 0)

    def test_v5_trash_lifecycle_and_management_dashboard(self):
        self.client.login(username='alice', password='Password123!')
        post = Post.objects.create(author=self.u1, content='Post to be trashed', privacy='public')

        # 1. Move to trash
        trash_res = self.client.post(reverse('social:manage_trash_post', kwargs={'post_id': post.id}), {
            'action': 'trash'
        })
        self.assertEqual(trash_res.status_code, 302)
        post.refresh_from_db()
        self.assertTrue(post.is_trashed)
        self.assertIsNotNone(post.trashed_at)

        # Trashed post cannot be viewed by friends
        self.assertFalse(post.can_view(self.u2))

        # Feed does not include trashed post
        feed_res = self.client.get(reverse('social:feed'))
        self.assertNotIn(post, feed_res.context['posts'])

        # 2. My Posts dashboard tabs
        for tab in ['published', 'drafts', 'scheduled', 'archived', 'trashed', 'saved']:
            dash_res = self.client.get(reverse('social:my_posts') + f'?tab={tab}')
            self.assertEqual(dash_res.status_code, 200)

        # 3. Restore post
        restore_res = self.client.post(reverse('social:manage_trash_post', kwargs={'post_id': post.id}), {
            'action': 'restore'
        })
        self.assertEqual(restore_res.status_code, 302)
        post.refresh_from_db()
        self.assertFalse(post.is_trashed)
        self.assertTrue(post.can_view(self.u2))

        # 4. Permanent delete
        del_res = self.client.post(reverse('social:manage_trash_post', kwargs={'post_id': post.id}), {
            'action': 'permanent_delete'
        })
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_v5_link_preview_ssrf_protection(self):
        self.client.login(username='alice', password='Password123!')

        # Loopback / internal blocked
        res_loopback = self.client.get(reverse('social:link_preview') + '?url=http://127.0.0.1:8000/admin')
        self.assertEqual(res_loopback.status_code, 400)

        res_local = self.client.get(reverse('social:link_preview') + '?url=http://localhost:8080')
        self.assertEqual(res_local.status_code, 400)

        # Empty url
        res_empty = self.client.get(reverse('social:link_preview'))
        self.assertEqual(res_empty.status_code, 400)

    def test_v6_photo_albums(self):
        self.client.login(username='alice', password='Password123!')

        # 1. Create photo album
        res = self.client.post(reverse('social:create_album'), {
            'title': 'Vacation 2026',
            'description': 'Trip photos and memories',
            'privacy': 'public',
        })
        self.assertEqual(res.status_code, 302)
        album = PhotoAlbum.objects.filter(title='Vacation 2026').first()
        self.assertIsNotNone(album)
        self.assertEqual(album.user, self.u1)

        # 2. Upload photo to album
        dummy_img = SimpleUploadedFile("vacation.jpg", b"fake_image_bytes", content_type="image/jpeg")
        upload_res = self.client.post(reverse('social:upload_album_photo', kwargs={'album_id': album.id}), {
            'image': dummy_img,
            'caption': 'Sunset on the beach',
        })
        self.assertEqual(upload_res.status_code, 302)
        photo = AlbumPhoto.objects.filter(album=album).first()
        self.assertIsNotNone(photo)
        self.assertEqual(photo.caption, 'Sunset on the beach')

        # 3. View album detail
        detail_res = self.client.get(reverse('social:album_detail', kwargs={'album_id': album.id}))
        self.assertEqual(detail_res.status_code, 200)

        # 4. Edit album
        edit_res = self.client.post(reverse('social:edit_album', kwargs={'album_id': album.id}), {
            'title': 'Vacation 2026 Updated',
            'description': 'Updated trip description',
            'privacy': 'friends',
        })
        self.assertEqual(edit_res.status_code, 302)
        album.refresh_from_db()
        self.assertEqual(album.title, 'Vacation 2026 Updated')

        # 5. Delete photo
        del_photo_res = self.client.post(reverse('social:delete_album_photo', kwargs={'photo_id': photo.id}))
        self.assertEqual(del_photo_res.status_code, 302)
        self.assertFalse(AlbumPhoto.objects.filter(id=photo.id).exists())

        # 6. Delete album
        del_album_res = self.client.post(reverse('social:delete_album', kwargs={'album_id': album.id}))
        self.assertEqual(del_album_res.status_code, 302)
        self.assertFalse(PhotoAlbum.objects.filter(id=album.id).exists())

    def test_v6_reels_and_creator_studio(self):
        self.client.login(username='alice', password='Password123!')

        # 1. Create a Reel
        dummy_vid = SimpleUploadedFile("reel.mp4", b"fake_video_bytes", content_type="video/mp4")
        reel_res = self.client.post(reverse('social:create_reel'), {
            'video_file': dummy_vid,
            'caption': 'My first ConnectBook Reel! #awesome',
            'location': 'New York, NY',
            'privacy': 'public',
            'status': 'published',
            'comments_enabled': 'on',
            'allow_sharing': 'on',
        })
        self.assertEqual(reel_res.status_code, 302)
        reel = Reel.objects.filter(author=self.u1).first()
        self.assertIsNotNone(reel)
        self.assertEqual(reel.location, 'New York, NY')
        self.assertTrue(reel.comments_enabled)

        # 2. Infinite scroll feed API
        feed_api_res = self.client.get(reverse('social:reels_api_feed') + '?page=1')
        self.assertEqual(feed_api_res.status_code, 200)
        feed_data = feed_api_res.json()
        self.assertEqual(feed_data['status'], 'ok')
        self.assertTrue(len(feed_data['reels']) >= 1)
        self.assertEqual(feed_data['reels'][0]['id'], reel.id)

        # 3. Creator Studio view with filters
        for days in ['all', '7', '30', '90']:
            studio_res = self.client.get(reverse('social:creator_studio') + f'?days={days}')
            self.assertEqual(studio_res.status_code, 200)
            self.assertIn('total_views', studio_res.context)
            self.assertIn('engagement_rate', studio_res.context)
            self.assertIn('total_reactions', studio_res.context)
            self.assertIn('total_comments', studio_res.context)
            self.assertIn('total_shares', studio_res.context)
            self.assertIn('total_saves', studio_res.context)

    def test_v7_complete_post_creation_and_display_workflow(self):
        # Step 1: Login as User A (alice)
        self.client.login(username='alice', password='Password123!')

        # Step 2: Create a text post
        res_txt = self.client.post(reverse('social:create_post'), {
            'content': 'V7 Verified Text Post by Alice #connectbook',
            'privacy': 'public',
            'status': 'published',
            'next': reverse('accounts:profile', kwargs={'username': 'alice'})
        })
        # Should redirect back to next (profile)
        self.assertEqual(res_txt.status_code, 302)
        self.assertEqual(res_txt.url, reverse('accounts:profile', kwargs={'username': 'alice'}))

        # Step 3: Verify it exists in SQLite
        txt_post = Post.objects.filter(content__contains='V7 Verified Text Post by Alice').first()
        self.assertIsNotNone(txt_post)
        self.assertEqual(txt_post.author, self.u1)

        # Step 4: Verify it appears in User A's profile
        prof_res = self.client.get(reverse('accounts:profile', kwargs={'username': 'alice'}))
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(txt_post, prof_res.context['posts'])
        self.assertIn('V7 Verified Text Post by Alice', prof_res.content.decode('utf-8'))

        # Step 5: Verify it appears in the home feed
        feed_res = self.client.get(reverse('social:feed'))
        self.assertEqual(feed_res.status_code, 200)
        self.assertIn(txt_post, feed_res.context['posts'])
        self.assertIn('V7 Verified Text Post by Alice', feed_res.content.decode('utf-8'))

        # Step 6: Create an image post
        dummy_img = SimpleUploadedFile('scenic_view.jpg', b'image_bytes_content_123', content_type='image/jpeg')
        res_img = self.client.post(reverse('social:create_post'), {
            'content': 'Beautiful sunset view from the trip!',
            'privacy': 'public',
            'status': 'published',
            'media': dummy_img,
        })
        self.assertEqual(res_img.status_code, 302)

        # Step 7: Verify image storage in SQLite
        img_post = Post.objects.filter(content='Beautiful sunset view from the trip!').first()
        self.assertIsNotNone(img_post)
        self.assertEqual(img_post.media_files.count(), 1)
        media_item = img_post.media_files.first()
        self.assertEqual(media_item.media_type, 'image')

        # Step 8: Verify image display in feed
        feed_img_res = self.client.get(reverse('social:feed'))
        self.assertIn(img_post, feed_img_res.context['posts'])
        self.assertIn(media_item.file.url, feed_img_res.content.decode('utf-8'))

        # Step 9: Create a video post
        dummy_vid = SimpleUploadedFile('clip.mp4', b'video_bytes_content_456', content_type='video/mp4')
        res_vid = self.client.post(reverse('social:create_post'), {
            'content': 'Check out this awesome drone video clip!',
            'privacy': 'public',
            'status': 'published',
            'media': dummy_vid,
        })
        self.assertEqual(res_vid.status_code, 302)

        # Step 10: Verify video storage and playback element
        vid_post = Post.objects.filter(content='Check out this awesome drone video clip!').first()
        self.assertIsNotNone(vid_post)
        self.assertEqual(vid_post.media_files.count(), 1)
        vid_media = vid_post.media_files.first()
        self.assertEqual(vid_media.media_type, 'video')
        feed_vid_res = self.client.get(reverse('social:feed'))
        self.assertIn(vid_post, feed_vid_res.context['posts'])
        self.assertIn(vid_media.file.url, feed_vid_res.content.decode('utf-8'))
        self.assertIn('<video', feed_vid_res.content.decode('utf-8'))

        # Step 11 & 12: Privacy permissions test: User B (bob, friend) vs User C (charlie, non-friend)
        priv_post = Post.objects.create(
            author=self.u1,
            content='Friends-only confidential announcement',
            privacy='friends',
            status='published'
        )
        # Login as User B (friend) -> can view
        self.client.login(username='bob', password='Password123!')
        feed_b = self.client.get(reverse('social:feed'))
        self.assertIn(priv_post, feed_b.context['posts'])

        # Login as User C (non-friend) -> cannot view
        self.client.login(username='charlie', password='Password123!')
        feed_c = self.client.get(reverse('social:feed'))
        self.assertNotIn(priv_post, feed_c.context['posts'])

        # Step 13: Edit post
        self.client.login(username='alice', password='Password123!')
        edit_res = self.client.post(reverse('social:edit_post', kwargs={'post_id': txt_post.id}), {
            'content': 'V7 Verified Text Post by Alice (Edited)',
            'privacy': 'public'
        })
        self.assertEqual(edit_res.status_code, 302)
        txt_post.refresh_from_db()
        self.assertEqual(txt_post.content, 'V7 Verified Text Post by Alice (Edited)')
        self.assertTrue(txt_post.is_edited)

        # Step 14: Delete post (move to trash)
        del_res = self.client.post(reverse('social:manage_trash_post', kwargs={'post_id': txt_post.id}), {
            'action': 'trash'
        })
        self.assertEqual(del_res.status_code, 302)
        txt_post.refresh_from_db()
        self.assertTrue(txt_post.is_trashed)

        # Step 15 & 16: Refresh feed & profile and verify post is no longer displayed
        feed_refresh = self.client.get(reverse('social:feed'))
        self.assertNotIn(txt_post, feed_refresh.context['posts'])
        self.assertNotIn('V7 Verified Text Post by Alice (Edited)', feed_refresh.content.decode('utf-8'))

        prof_refresh = self.client.get(reverse('accounts:profile', kwargs={'username': 'alice'}))
        self.assertNotIn(txt_post, prof_refresh.context['posts'])
        self.assertNotIn('V7 Verified Text Post by Alice (Edited)', prof_refresh.content.decode('utf-8'))

    def test_v8_comprehensive_platform_audit_and_workflows(self):
        """
        ConnectBook V8 Final Master End-to-End Test Suite:
        1. Single Post Permalink View (/posts/<id>/) & Object-Level Privacy Verification.
        2. Single Reel Permalink View (/reels/<id>/), Interactions, and View Tracking.
        3. Cross-Domain Search System (Users, Posts, Videos, Reels, Groups, Pages).
        4. Right Sidebar Dynamic Social Context (Birthdays, Suggested Groups, Suggested Pages).
        """
        # 1. Post Detail Permalink & Privacy Verification
        self.client.login(username='alice', password='Password123!')
        pub_post = Post.objects.create(author=self.u1, content='V8 Public Announcement', privacy='public')
        priv_post = Post.objects.create(author=self.u1, content='V8 Only Me Secrets', privacy='only_me')
        friend_post = Post.objects.create(author=self.u1, content='V8 Friends Only Circle', privacy='friends')

        # Alice accesses own posts
        res_own_pub = self.client.get(reverse('social:post_detail', kwargs={'post_id': pub_post.id}))
        self.assertEqual(res_own_pub.status_code, 200)
        self.assertContains(res_own_pub, 'V8 Public Announcement')
        pub_post.refresh_from_db()
        self.assertGreaterEqual(pub_post.views_count, 1)

        res_own_priv = self.client.get(reverse('social:post_detail', kwargs={'post_id': priv_post.id}))
        self.assertEqual(res_own_priv.status_code, 200)

        # Bob (friend) accesses posts
        self.client.login(username='bob', password='Password123!')
        res_bob_pub = self.client.get(reverse('social:post_detail', kwargs={'post_id': pub_post.id}))
        self.assertEqual(res_bob_pub.status_code, 200)

        res_bob_friend = self.client.get(reverse('social:post_detail', kwargs={'post_id': friend_post.id}))
        self.assertEqual(res_bob_friend.status_code, 200)

        res_bob_priv = self.client.get(reverse('social:post_detail', kwargs={'post_id': priv_post.id}))
        self.assertEqual(res_bob_priv.status_code, 403)
        self.assertContains(res_bob_priv, 'This Content Isn\'t Available Right Now', status_code=403)

        # Charlie (non-friend) accesses posts
        self.client.login(username='charlie', password='Password123!')
        res_charlie_friend = self.client.get(reverse('social:post_detail', kwargs={'post_id': friend_post.id}))
        self.assertEqual(res_charlie_friend.status_code, 403)

        # 2. Reel Detail Permalink & Interactions
        dummy_video = SimpleUploadedFile('reel_test.mp4', b'dummy_reel_data_v8', content_type='video/mp4')
        reel = Reel.objects.create(
            author=self.u1,
            video_file=dummy_video,
            caption='V8 Incredible Sunset Reel #nature',
            audio_title='Original Sunset Audio',
            privacy='public'
        )
        self.client.login(username='bob', password='Password123!')
        res_reel = self.client.get(reverse('social:reel_detail', kwargs={'reel_id': reel.id}))
        self.assertEqual(res_reel.status_code, 200)
        self.assertContains(res_reel, 'V8 Incredible Sunset Reel')
        self.assertContains(res_reel, 'Original Sunset Audio')
        reel.refresh_from_db()
        self.assertGreaterEqual(reel.views_count, 1)

        # React to reel
        res_reel_like = self.client.post(reverse('social:react_reel', kwargs={'reel_id': reel.id}))
        self.assertEqual(res_reel_like.status_code, 302)
        self.assertEqual(reel.reactions.count(), 1)

        # Comment on reel
        res_reel_comment = self.client.post(reverse('social:add_reel_comment', kwargs={'reel_id': reel.id}), {
            'content': 'Stunning sunset capture!'
        })
        self.assertEqual(res_reel_comment.status_code, 302)
        self.assertEqual(reel.comments.count(), 1)

        # 3. Cross-Domain Search
        res_search = self.client.get(reverse('social:search') + '?q=Sunset')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn('reels', res_search.context)
        self.assertIn(reel, res_search.context['reels'])

        # 4. Right Sidebar Context
        self.client.login(username='alice', password='Password123!')
        feed_res = self.client.get(reverse('social:feed'))
        self.assertEqual(feed_res.status_code, 200)
        self.assertIn('birthday_friends', feed_res.context)
        self.assertIn('suggested_groups', feed_res.context)
        self.assertIn('suggested_pages', feed_res.context)
        self.assertIn('suggested_friends', feed_res.context)
        self.assertIn('contacts_list', feed_res.context)

    def test_v11_facebook_reels_platform_and_workflows(self):
        """
        ConnectBook V11 Facebook-Style Dedicated Reels Platform Tests:
        1. Discovery category routing (/reels/?tab=for_you|following|trending|latest|popular|saved).
        2. Creator Studio (/reels/my-reels/) metrics & rendering.
        3. Real-time Reel Comments API (GET & POST /reels/<id>/comments/).
        4. Share Reel to News Feed (/reels/<id>/share-to-feed/).
        5. Smart 10-minute view deduplication (/reels/<id>/view/).
        6. Object-level privacy can_view check on Reel.
        """
        self.client.login(username='alice', password='Password123!')
        dummy_video = SimpleUploadedFile('v11_reel.mp4', b'v11_test_reel_stream_bytes', content_type='video/mp4')
        reel1 = Reel.objects.create(
            author=self.u1,
            video_file=dummy_video,
            caption='V11 Inspiring Mountain Hike #outdoor #adventure',
            audio_title='Mountain Wind Chill',
            privacy='public'
        )
        dummy_video2 = SimpleUploadedFile('v11_reel_friends.mp4', b'v11_test_reel2_bytes', content_type='video/mp4')
        reel_friends = Reel.objects.create(
            author=self.u1,
            video_file=dummy_video2,
            caption='Secret Friends Hangout Reel',
            audio_title='Acoustic Campfire',
            privacy='friends'
        )

        # 1. Category tabs on Reels Feed
        res_feed_default = self.client.get(reverse('social:reels'))
        self.assertEqual(res_feed_default.status_code, 200)
        self.assertEqual(res_feed_default.context['active_tab'], 'for_you')
        self.assertIn(reel1, res_feed_default.context['reels'])

        for tab_name in ['following', 'trending', 'latest', 'popular', 'saved']:
            res_tab = self.client.get(reverse('social:reels') + f'?tab={tab_name}')
            self.assertEqual(res_tab.status_code, 200)
            self.assertEqual(res_tab.context['active_tab'], tab_name)

        # 2. Creator Studio / My Reels
        res_my_reels = self.client.get(reverse('social:my_reels'))
        self.assertEqual(res_my_reels.status_code, 200)
        self.assertEqual(res_my_reels.context['total_reels'], 2)
        self.assertIn('total_views', res_my_reels.context)
        self.assertIn('total_likes', res_my_reels.context)
        self.assertIn('total_comments', res_my_reels.context)

        # 3. Reels Comments API (GET & POST)
        # GET comments
        res_get_comments = self.client.get(reverse('social:reel_comments', kwargs={'reel_id': reel1.id}))
        self.assertEqual(res_get_comments.status_code, 200)
        self.assertEqual(res_get_comments.json()['count'], 0)

        # POST comment
        res_post_comment = self.client.post(
            reverse('social:reel_comments', kwargs={'reel_id': reel1.id}),
            data='{"content": "Love the mountain landscape!"}',
            content_type='application/json'
        )
        self.assertEqual(res_post_comment.status_code, 200)
        data = res_post_comment.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['comment']['content'], 'Love the mountain landscape!')
        self.assertEqual(data['comment']['author_username'], 'alice')

        # Check in DB
        self.assertEqual(reel1.comments.count(), 1)

        # POST empty comment error
        res_empty = self.client.post(
            reverse('social:reel_comments', kwargs={'reel_id': reel1.id}),
            data='{"content": "   "}',
            content_type='application/json'
        )
        self.assertEqual(res_empty.status_code, 400)

        # 4. Share Reel to Feed
        res_share = self.client.post(
            reverse('social:share_reel_to_feed', kwargs={'reel_id': reel1.id}),
            data={'share_caption': 'Sharing this breathtaking hike to my timeline!'}
        )
        self.assertEqual(res_share.status_code, 200)
        share_data = res_share.json()
        self.assertEqual(share_data['status'], 'ok')
        self.assertIn('post_id', share_data)
        shared_post = Post.objects.get(id=share_data['post_id'])
        self.assertIn('Sharing this breathtaking hike to my timeline!', shared_post.content)

        # 5. Smart 10-Minute View Deduplication
        initial_views = reel1.views_count
        res_view1 = self.client.post(reverse('social:increment_reel_view', kwargs={'reel_id': reel1.id}))
        self.assertEqual(res_view1.status_code, 200)
        v1_json = res_view1.json()
        self.assertEqual(v1_json['views_count'], initial_views + 1)
        self.assertFalse(v1_json.get('deduplicated', False))

        # Immediate second view by same user/client should be deduplicated
        res_view2 = self.client.post(reverse('social:increment_reel_view', kwargs={'reel_id': reel1.id}))
        self.assertEqual(res_view2.status_code, 200)
        v2_json = res_view2.json()
        self.assertEqual(v2_json['views_count'], initial_views + 1)
        self.assertTrue(v2_json.get('deduplicated', False))

        # 6. Object-level privacy check
        self.assertTrue(reel1.can_view(self.u1))
        self.assertTrue(reel1.can_view(self.u2))
        self.assertTrue(reel1.can_view(self.u3)) # public reel

        self.assertTrue(reel_friends.can_view(self.u1)) # author
        self.assertTrue(reel_friends.can_view(self.u2)) # friend
        self.assertFalse(reel_friends.can_view(self.u3)) # not a friend

    def test_search_suggestions_excludes_blocked_users(self):
        """Verify search suggestions do not suggest blocked users."""
        from accounts.models import BlockedUser
        BlockedUser.objects.create(blocker=self.u1, blocked=self.u3)

        self.client.login(username='alice', password='Password123!')
        res = self.client.get(reverse('social:search_suggestions') + '?q=charlie')
        self.assertEqual(res.status_code, 200)
        results = res.json().get('results', [])
        found_charlie = any(r['subtitle'] == '@charlie' for r in results)
        self.assertFalse(found_charlie)





