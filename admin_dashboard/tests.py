from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from admin_dashboard.models import SensitiveAccessLog
from accounts.models import AccountDeletionRequest

User = get_user_model()


class AdminDashboardTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin_t@example.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )
        self.regular = User.objects.create_user(
            username='regular_test',
            email='regular@example.com',
            password='Password123!'
        )

    def test_admin_access_control(self):
        # Regular user denied access to admin-panel
        self.client.login(username='regular_test', password='Password123!')
        res_reg = self.client.get(reverse('admin_dashboard:overview'))
        self.assertEqual(res_reg.status_code, 302) # redirected by user_passes_test

        # Staff user granted access
        self.client.login(username='admin_test', password='Password123!')
        res_adm = self.client.get(reverse('admin_dashboard:overview'))
        self.assertEqual(res_adm.status_code, 200)

    def test_privacy_security_center_and_sensitive_access(self):
        self.client.login(username='admin_test', password='Password123!')
        res = self.client.get(reverse('admin_dashboard:privacy_security'))
        self.assertEqual(res.status_code, 200)

        # Log sensitive access
        post_res = self.client.post(reverse('admin_dashboard:log_sensitive_access'), {
            'target_resource': 'User #14 Compliance Verification',
            'reason': 'Handling escalated safety complaint',
        })
        self.assertEqual(post_res.status_code, 302)
        log = SensitiveAccessLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.staff_user, self.admin)
        self.assertEqual(log.target_resource, 'User #14 Compliance Verification')

    def test_handle_deletion_request(self):
        del_req = AccountDeletionRequest.objects.create(user=self.regular, reason='Test reason')
        self.client.login(username='admin_test', password='Password123!')

        res = self.client.get(reverse('admin_dashboard:handle_deletion_request', kwargs={
            'request_id': del_req.id,
            'action': 'approve'
        }))
        self.assertEqual(res.status_code, 302)
        del_req.refresh_from_db()
        self.assertEqual(del_req.status, 'approved')
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.is_deactivated)

    def test_v4_admin_media_and_streams_moderation(self):
        from social.models import Video, Reel
        from streaming.models import LiveStream
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_vid = SimpleUploadedFile("ad_vid.mp4", b"content", content_type="video/mp4")
        video = Video.objects.create(author=self.regular, title='Violating Video', video_file=dummy_vid)
        dummy_reel = SimpleUploadedFile("ad_reel.mp4", b"content", content_type="video/mp4")
        reel = Reel.objects.create(author=self.regular, video_file=dummy_reel, caption='Violating Reel')
        stream = LiveStream.objects.create(host=self.regular, title='Violating Stream', status='live')

        self.client.login(username='admin_test', password='Password123!')

        # Media moderation page
        res_media = self.client.get(reverse('admin_dashboard:media_moderation'))
        self.assertEqual(res_media.status_code, 200)

        # Streams moderation page
        res_streams = self.client.get(reverse('admin_dashboard:streams_moderation'))
        self.assertEqual(res_streams.status_code, 200)

        # Admin deletes video
        del_v_res = self.client.post(reverse('admin_dashboard:admin_delete_video', kwargs={'video_id': video.id}))
        self.assertEqual(del_v_res.status_code, 302)
        self.assertFalse(Video.objects.filter(id=video.id).exists())

        # Admin deletes reel
        del_r_res = self.client.post(reverse('admin_dashboard:admin_delete_reel', kwargs={'reel_id': reel.id}))
        self.assertEqual(del_r_res.status_code, 302)
        self.assertFalse(Reel.objects.filter(id=reel.id).exists())

        # Admin force ends stream
        end_s_res = self.client.post(reverse('admin_dashboard:admin_force_end_stream', kwargs={'stream_id': stream.id}))
        self.assertEqual(end_s_res.status_code, 302)
        stream.refresh_from_db()
        self.assertEqual(stream.status, 'ended')

