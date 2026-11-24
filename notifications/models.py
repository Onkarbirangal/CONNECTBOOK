from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend Request'),
        ('friend_accepted', 'Friend Request Accepted'),
        ('post_reaction', 'Post Reaction'),
        ('post_comment', 'Post Comment'),
        ('comment_reply', 'Comment Reply'),
        ('mention', 'Mention'),
        ('message', 'New Message'),
        ('group_invite', 'Group Invitation'),
        ('group_join_request', 'Group Join Request'),
        ('group_post', 'Group Post'),
    ]

    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('social', 'Social & Interactions'),
        ('messages', 'Messages'),
        ('security', 'Account & Security'),
        ('groups', 'Groups & Events'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='triggered_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='general')
    title = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True, default='')
    target_url = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username} from {self.actor.username} ({self.notification_type})"
