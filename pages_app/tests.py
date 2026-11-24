from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from pages_app.models import Page, PageFollow
from social.models import Post

User = get_user_model()


class PagesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='pagecreator', email='creator@example.com', password='Password123!')
        self.client.login(username='pagecreator', password='Password123!')

    def test_create_and_follow_page(self):
        res = self.client.post(reverse('pages_app:create_page'), {
            'name': 'Innovate AI Hub',
            'category': 'business',
            'bio': 'All about modern AI',
            'description': 'Exploring artificial intelligence and technology.',
        })
        self.assertEqual(res.status_code, 302)
        page = Page.objects.filter(name='Innovate AI Hub').first()
        self.assertIsNotNone(page)
        self.assertEqual(page.owner, self.user)
        self.assertTrue(page.is_follower(self.user))

        # View page detail
        detail_res = self.client.get(reverse('pages_app:page_detail', kwargs={'slug': page.slug}))
        self.assertEqual(detail_res.status_code, 200)

        # Unfollow page
        unfollow_res = self.client.get(reverse('pages_app:toggle_follow', kwargs={'slug': page.slug}))
        self.assertEqual(unfollow_res.status_code, 302)
        self.assertFalse(page.is_follower(self.user))

    def test_page_post_creation(self):
        page = Page.objects.create(name='Dev News', owner=self.user)
        res = self.client.post(reverse('pages_app:page_detail', kwargs={'slug': page.slug}), {
            'create_page_post': '1',
            'content': 'Welcome to our official page!',
        })
        self.assertEqual(res.status_code, 302)
        post = Post.objects.filter(page=page).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.content, 'Welcome to our official page!')
