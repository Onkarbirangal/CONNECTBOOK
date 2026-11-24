from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Page(models.Model):
    CATEGORY_CHOICES = [
        ('business', 'Business or Brand'),
        ('community', 'Community or Cause'),
        ('entertainment', 'Entertainment'),
        ('creator', 'Public Figure / Creator'),
        ('organization', 'Non-Profit / Organization'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=160)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='business')
    bio = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='pages/avatars/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='pages/covers/', blank=True, null=True)
    website = models.URLField(blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_pages')
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='administered_pages', blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "page"
            candidate = base_slug
            counter = 1
            while Page.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.svg'

    def get_cover_url(self):
        if self.cover_photo and hasattr(self.cover_photo, 'url'):
            return self.cover_photo.url
        return '/static/images/default-cover.svg'

    @property
    def total_followers(self):
        return self.followers.count()

    def is_follower(self, user):
        if not user or user.is_anonymous:
            return False
        return self.followers.filter(user=user).exists()

    def can_manage(self, user):
        if not user or user.is_anonymous:
            return False
        if user == self.owner or user.is_superuser:
            return True
        return self.admins.filter(pk=user.pk).exists()


class PageFollow(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='followers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='page_follows')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('page', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} follows {self.page.name}"
