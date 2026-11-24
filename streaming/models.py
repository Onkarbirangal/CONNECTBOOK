import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class LiveStream(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live Now'),
        ('ended', 'Ended'),
    ]

    CATEGORY_CHOICES = [
        ('General', 'General & Chat'),
        ('Gaming', 'Gaming'),
        ('Music', 'Music & Performing'),
        ('Education', 'Tech & Education'),
        ('Entertainment', 'Entertainment'),
        ('Sports', 'Sports & Fitness'),
    ]

    AUDIENCE_CHOICES = [
        ('public', 'Public (Everyone)'),
        ('friends', 'Friends Only'),
        ('private', 'Private (Only Me)'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_streams')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='public')
    scheduled_start = models.DateTimeField(default=timezone.now)
    actual_start = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    stream_key = models.CharField(max_length=64, blank=True, unique=True)
    thumbnail = models.ImageField(upload_to='livestreams/', blank=True, null=True)
    viewer_count = models.PositiveIntegerField(default=0)
    peak_viewers = models.PositiveIntegerField(default=0)
    slow_mode_seconds = models.PositiveIntegerField(default=0, help_text="Chat delay in seconds")
    whip_url = models.CharField(max_length=255, blank=True, default='')
    rtmp_url = models.CharField(max_length=255, blank=True, default='')
    hls_playback_url = models.CharField(max_length=255, blank=True, default='')
    is_recording_available = models.BooleanField(default=False)
    recording_file = models.FileField(upload_to='livestreams/recordings/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_start']

    def __str__(self):
        return f"{self.title} ({self.status}) - Host: {self.host.username}"

    def save(self, *args, **kwargs):
        if not self.stream_key:
            self.stream_key = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def get_thumbnail_url(self):
        if self.thumbnail and hasattr(self.thumbnail, 'url'):
            return self.thumbnail.url
        return '/static/images/default-cover.svg'

    def can_manage(self, user):
        if not user or user.is_anonymous:
            return False
        return user == self.host or user.is_superuser


class LiveStreamViewer(models.Model):
    stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='viewers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='stream_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-joined_at']

    def __str__(self):
        u = self.user.username if self.user else (self.ip_address or 'Anonymous')
        return f"{u} viewing {self.stream.title}"


class LiveStreamChatMessage(models.Model):
    stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_chat_messages')
    message = models.CharField(max_length=500)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} in {self.stream.title}: {self.message[:30]}"


class LiveStreamBlockedUser(models.Model):
    stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='blocked_viewers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    blocked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stream_blocks_issued')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('stream', 'user')

    def __str__(self):
        return f"{self.user.username} blocked in {self.stream.title}"


class LiveStreamRecording(models.Model):
    stream = models.OneToOneField(LiveStream, on_delete=models.CASCADE, related_name='recording_record')
    recording_file = models.FileField(upload_to='livestreams/replays/%Y/%m/', null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recording for {self.stream.title}"
