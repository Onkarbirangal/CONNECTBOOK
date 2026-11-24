from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from stories.models import Story, StoryReaction, StoryReply, StoryHighlight
from chat.models import Message

User = get_user_model()


class StoriesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='author1', email='author@example.com', password='Password123!')
        self.user2 = User.objects.create_user(username='viewer1', email='viewer@example.com', password='Password123!')
        self.client.login(username='author1', password='Password123!')

    def test_v6_stories_reactions_replies_highlights(self):
        # 1. Create a story
        res = self.client.post(reverse('stories:create_story'), {
            'media_type': 'text',
            'text_content': 'Hello from ConnectBook V6 Stories!',
            'background_color': 'linear-gradient(135deg, #1877f2, #00c6ff)',
            'location': 'San Francisco, CA',
            'privacy': 'public',
        })
        self.assertEqual(res.status_code, 302)
        story = Story.objects.filter(author=self.user1).first()
        self.assertIsNotNone(story)
        self.assertEqual(story.location, 'San Francisco, CA')

        # 2. Viewer logs in and reacts to story
        self.client.login(username='viewer1', password='Password123!')
        react_res = self.client.post(reverse('stories:react_story_api', kwargs={'story_id': story.id}), {
            'reaction_type': 'love'
        })
        self.assertEqual(react_res.status_code, 200)
        self.assertEqual(react_res.json()['status'], 'ok')
        self.assertTrue(StoryReaction.objects.filter(story=story, user=self.user2, reaction_type='love').exists())

        # 3. Viewer replies to story
        reply_res = self.client.post(reverse('stories:reply_story_api', kwargs={'story_id': story.id}), {
            'message': 'Love this story gradient!'
        })
        self.assertEqual(reply_res.status_code, 200)
        self.assertEqual(reply_res.json()['status'], 'ok')
        self.assertTrue(StoryReply.objects.filter(story=story, user=self.user2).exists())

        # Verify chat message was dispatched to story author
        chat_msg = Message.objects.filter(sender=self.user2).first()
        self.assertIsNotNone(chat_msg)
        self.assertIn('Replied to your story', chat_msg.content)

        # 4. Author creates StoryHighlight
        self.client.login(username='author1', password='Password123!')
        hl_res = self.client.post(reverse('stories:create_highlight'), {
            'title': 'Best Moments',
            'story_ids': [story.id]
        })
        self.assertEqual(hl_res.status_code, 302)
        highlight = StoryHighlight.objects.filter(user=self.user1, title='Best Moments').first()
        self.assertIsNotNone(highlight)
        self.assertEqual(highlight.stories.count(), 1)

        # 5. Fetch highlight stories API
        hl_api_res = self.client.get(reverse('stories:highlight_stories_api', kwargs={'highlight_id': highlight.id}))
        self.assertEqual(hl_api_res.status_code, 200)
        hl_data = hl_api_res.json()
        self.assertTrue(len(hl_data['stories']) >= 1)
        self.assertEqual(hl_data['stories'][0]['id'], story.id)

        # 6. View story archive
        archive_res = self.client.get(reverse('stories:story_archive'))
        self.assertEqual(archive_res.status_code, 200)
        self.assertIn(story, archive_res.context['stories'])
