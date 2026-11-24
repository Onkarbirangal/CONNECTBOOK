from django.db import models
from django.conf import settings


class Event(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public Event'),
        ('private', 'Private Event'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    cover_image = models.ImageField(upload_to='events/covers/', blank=True, null=True)
    venue = models.CharField(max_length=255, default='Online / TBD')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return self.title

    def get_cover_url(self):
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        return '/static/images/default-cover.svg'

    @property
    def going_count(self):
        return self.rsvps.filter(status='going').count()

    @property
    def interested_count(self):
        return self.rsvps.filter(status='interested').count()

    def user_rsvp(self, user):
        if not user or user.is_anonymous:
            return None
        rsvp = self.rsvps.filter(user=user).first()
        return rsvp.status if rsvp else None

    def can_manage(self, user):
        if not user or user.is_anonymous:
            return False
        return user == self.organizer or user.is_superuser


class EventRSVP(models.Model):
    STATUS_CHOICES = [
        ('going', 'Going'),
        ('interested', 'Interested'),
        ('not_going', 'Not Going'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_rsvps')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='going')
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.status} for {self.event.title}"
