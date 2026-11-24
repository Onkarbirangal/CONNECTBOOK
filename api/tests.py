from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from social.models import Post

User = get_user_model()

class APITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', email='api@example.com', password='Password123!')
        self.client.login(username='apiuser', password='Password123!')

    def test_get_current_user_api(self):
        res = self.client.get(reverse('api:current_user'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['username'], 'apiuser')

    def test_post_list_create_api(self):
        # Create post via API
        res = self.client.post(reverse('api:posts_list_create'), {
            'content': 'API created post',
            'privacy': 'public'
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Post.objects.count(), 1)

        # Get posts list
        res_list = self.client.get(reverse('api:posts_list_create'))
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(len(res_list.json()['results']), 1)
