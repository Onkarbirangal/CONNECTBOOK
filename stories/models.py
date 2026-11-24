from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def default_story_expiry():
    return timezone.now() + timedelta(hours=24)


class Story(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('text', 'Text'),
    ]

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stories')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    media_file = models.FileField(upload_to='stories/%Y/%m/', null=True, blank=True)
    text_content = models.TextField(blank=True, default='')
    background_color = models.CharField(max_length=50, default='linear-gradient(135deg, #1877F2 0%, #00C6FF 100%)')
    font_style = models.CharField(max_length=50, default='system-ui')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='friends')
    location = models.CharField(max_length=150, blank=True, default='')
    tagged_friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='tagged_stories')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_story_expiry)

    class Meta:
        ordering = ['-created_at']

    def is_active(self):
        return timezone.now() < self.expires_at

    def can_view(self, user):
        if not user or user.is_anonymous:
            return self.privacy == 'public'
        if user == self.author or user.is_superuser:
            return True
        if self.privacy == 'public':
            return True
        if self.privacy == 'friends':
            from friends.models import Friendship
            return Friendship.are_friends(self.author, user)
        return False

    def __str__(self):
        return f"Story #{self.pk} by {self.author.username}"


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='viewed_stories')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'viewer')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.viewer.username} viewed Story #{self.story_id}"


class StoryReaction(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_reactions')
    reaction_type = models.CharField(max_length=20, default='love')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to Story #{self.story_id}"


class StoryReply(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_replies')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.user.username} on Story #{self.story_id}"


class StoryHighlight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='story_highlights')
    title = models.CharField(max_length=100)
    cover_image = models.ImageField(upload_to='highlights/covers/%Y/%m/', null=True, blank=True)
    stories = models.ManyToManyField(Story, related_name='highlights')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Highlight '{self.title}' by {self.user.username}"

    def get_cover_url(self):
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        first_story = self.stories.filter(media_type='image').first()
        if first_story and first_story.media_file:
            return first_story.media_file.url
        return '/static/images/default-cover.svg'
