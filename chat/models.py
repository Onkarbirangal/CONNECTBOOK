from django.db import models
from django.conf import settings


class Conversation(models.Model):
    title = models.CharField(max_length=150, blank=True, default='')
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.title:
            return self.title
        names = [p.user.username for p in self.participants.all()[:3]]
        return f"Chat: {', '.join(names)}"

    def get_recipient(self, current_user=None):
        """For direct 1-on-1 chats, returns the other user."""
        if not current_user:
            first_p = self.participants.first()
            return first_p.user if first_p else None
        other_part = self.participants.exclude(user=current_user).first()
        return other_part.user if other_part else current_user

    def get_display_name(self, current_user=None):
        if self.is_group and self.title:
            return self.title
        recipient = self.get_recipient(current_user)
        return recipient.get_display_name() if recipient else "Conversation"

    def get_avatar_url(self, current_user=None):
        if self.is_group:
            return '/static/images/default-group-avatar.svg'
        recipient = self.get_recipient(current_user)
        if recipient and hasattr(recipient, 'profile'):
            return recipient.profile.get_avatar_url()
        return '/static/images/default-avatar.svg'

    @classmethod
    def get_or_create_direct(cls, user1, user2):
        conv = cls.objects.filter(
            is_group=False,
            participants__user=user1
        ).filter(
            participants__user=user2
        ).first()
        if not conv:
            conv = cls.objects.create(is_group=False)
            ConversationParticipant.objects.create(conversation=conv, user=user1)
            ConversationParticipant.objects.create(conversation=conv, user=user2)
        return conv


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_participations')
    is_admin = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('conversation', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.conversation_id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    content = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='messages/%Y/%m/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message #{self.pk} by {self.sender.username} in Chat #{self.conversation_id}"


class MessageReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction} on Message #{self.message_id}"


class CallSession(models.Model):
    CALL_TYPE_CHOICES = [
        ('video', 'Video Call'),
        ('audio', 'Voice Call'),
    ]

    STATUS_CHOICES = [
        ('ringing', 'Ringing'),
        ('accepted', 'In Progress'),
        ('rejected', 'Declined'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
    ]

    room_name = models.CharField(max_length=100, unique=True)
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='initiated_calls')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_calls')
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, default='video')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ringing')
    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.call_type.title()} from {self.caller.username} to {self.receiver.username} ({self.status})"

    def can_participate(self, user):
        if not user or user.is_anonymous:
            return False
        return user == self.caller or user == self.receiver
