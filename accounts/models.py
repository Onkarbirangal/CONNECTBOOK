from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('custom', 'Custom'),
        ('unspecified', 'Rather not say'),
    ]

    email = models.EmailField(unique=True, verbose_name='Email Address')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Date of Birth')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='unspecified')
    is_verified = models.BooleanField(default=False)
    is_deactivated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def get_display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username


class UserProfile(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, default='')
    hometown = models.CharField(max_length=100, blank=True, default='')
    work = models.CharField(max_length=150, blank=True, default='')
    education = models.CharField(max_length=150, blank=True, default='')
    website = models.URLField(blank=True, default='')
    relationship_status = models.CharField(max_length=50, blank=True, default='')
    profile_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    followers_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    photos_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    is_locked = models.BooleanField(default=False)
    review_tagged_posts = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_dob = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.svg'

    def get_cover_url(self):
        if self.cover_photo and hasattr(self.cover_photo, 'url'):
            return self.cover_photo.url
        return '/static/images/default-cover.svg'


class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        verbose_name = 'Blocked User'
        verbose_name_plural = 'Blocked Users'

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


class RestrictedUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restricted_users')
    restricted_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restricted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'restricted_user')
        verbose_name = 'Restricted User'
        verbose_name_plural = 'Restricted Users'

    def __str__(self):
        return f"{self.user.username} restricted {self.restricted_user.username}"


class MutedUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='muted_users')
    muted_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='muted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'muted_user')
        verbose_name = 'Muted User'
        verbose_name_plural = 'Muted Users'

    def __str__(self):
        return f"{self.user.username} muted {self.muted_user.username}"


class UserPreference(models.Model):
    THEME_CHOICES = [
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    sound_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    notify_reactions = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=True)
    notify_friend_requests = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Preferences"


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_set')
    followed = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"

    @classmethod
    def is_following(cls, follower, followed):
        if not follower or not followed or follower.is_anonymous or followed.is_anonymous or follower == followed:
            return False
        return cls.objects.filter(follower=follower, followed=followed).exists()


class UserPrivacySetting(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    STORY_PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    REQUEST_CHOICES = [
        ('everyone', 'Everyone'),
        ('friends_of_friends', 'Friends of Friends'),
    ]

    MESSAGE_CHOICES = [
        ('everyone', 'Everyone'),
        ('friends', 'Friends Only'),
    ]

    PERMISSION_CHOICES = [
        ('everyone', 'Everyone'),
        ('friends', 'Friends Only'),
        ('no_one', 'No One'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privacy_settings')
    profile_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    post_default_audience = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    story_privacy = models.CharField(max_length=20, choices=STORY_PRIVACY_CHOICES, default='friends')
    friend_request_permission = models.CharField(max_length=30, choices=REQUEST_CHOICES, default='everyone')
    message_permission = models.CharField(max_length=20, choices=MESSAGE_CHOICES, default='everyone')
    tagging_permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='friends')
    mention_permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='everyone')
    search_discoverability = models.BooleanField(default=True)
    read_receipts = models.BooleanField(default=True)
    online_status_visible = models.BooleanField(default=True)
    friends_list_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Privacy Settings"


class UserSessionRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_records')
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"Session for {self.user.username} ({self.device_type or 'Unknown device'})"


class DataExportRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Generation'),
        ('completed', 'Ready for Download'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='data_exports')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    export_file = models.FileField(upload_to='exports/', null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Export for {self.user.username} on {self.requested_at:%Y-%m-%d %H:%M}"


class AccountDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('cancelled', 'Cancelled by User'),
        ('approved', 'Approved / Queued'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deletion_requests')
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_deletion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Deletion request for {self.user.username} ({self.status})"


@receiver(post_save, sender=CustomUser)
def create_or_update_user_extras(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPreference.objects.get_or_create(user=instance)
        UserPrivacySetting.objects.get_or_create(user=instance)
