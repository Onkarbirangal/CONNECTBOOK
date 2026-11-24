from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Group(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public Group'),
        ('private', 'Private Group'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    cover_photo = models.ImageField(upload_to='groups/covers/', null=True, blank=True)
    icon = models.ImageField(upload_to='groups/icons/', null=True, blank=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'group'
            slug = base_slug
            counter = 1
            while Group.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_cover_url(self):
        if self.cover_photo and hasattr(self.cover_photo, 'url'):
            return self.cover_photo.url
        return '/static/images/default-group-cover.svg'

    def is_member(self, user):
        if not user or user.is_anonymous:
            return False
        return self.memberships.filter(user=user).exists()

    def is_admin(self, user):
        if not user or user.is_anonymous:
            return False
        return self.creator == user or self.memberships.filter(user=user, role__in=['admin', 'moderator']).exists()


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class GroupJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_join_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.group.name} ({self.status})"


class GroupRule(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='rules')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.group.name} Rule: {self.title}"


class GroupAnnouncement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_pinned = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"Announcement in {self.group.name}: {self.title}"
