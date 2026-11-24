from django.db import models
from django.conf import settings
from django.utils import timezone


class Post(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('friends_except', 'Friends Except...'),
        ('specific_friends', 'Specific Friends...'),
        ('only_me', 'Only Me'),
        ('custom', 'Custom Audience'),
    ]

    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    ]

    POST_TYPE_CHOICES = [
        ('text', 'Text Post'),
        ('photo', 'Photo Post'),
        ('video', 'Video Post'),
        ('reels', 'Reel Post'),
        ('story_share', 'Story Sharing'),
        ('live_share', 'Live Video Sharing'),
        ('link', 'Link Sharing'),
        ('poll', 'Poll Post'),
        ('question', 'Question Post'),
        ('feeling', 'Feeling / Activity'),
        ('location', 'Location Check-in'),
        ('event_share', 'Event Sharing'),
        ('group_post', 'Group Post'),
        ('page_post', 'Page Post'),
        ('profile_update', 'Profile Update'),
        ('milestone', 'Milestone Post'),
        ('birthday', 'Birthday Post'),
        ('celebration', 'Celebration Post'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True, default='')
    post_type = models.CharField(max_length=30, choices=POST_TYPE_CHOICES, default='text', db_index=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published', db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    comments_enabled = models.BooleanField(default=True)
    allow_sharing = models.BooleanField(default=True)
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    group = models.ForeignKey('groups_app.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    page = models.ForeignKey('pages_app.Page', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    original_post = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='shares')
    is_pinned = models.BooleanField(default=False)

    # V5 Advanced Attributes
    background_style = models.CharField(max_length=50, blank=True, default='none')
    feeling_category = models.CharField(max_length=50, blank=True, default='')
    feeling_text = models.CharField(max_length=100, blank=True, default='')
    feeling_icon = models.CharField(max_length=20, blank=True, default='')
    location_name = models.CharField(max_length=200, blank=True, default='')
    location_address = models.CharField(max_length=255, blank=True, default='')
    link_url = models.URLField(max_length=500, blank=True, default='')
    link_title = models.CharField(max_length=255, blank=True, default='')
    link_description = models.TextField(blank=True, default='')
    link_image = models.URLField(max_length=500, blank=True, default='')
    tagged_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='tagged_in_posts')
    custom_audience_allow = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='allowed_in_posts')
    custom_audience_deny = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='denied_in_posts')
    milestone_title = models.CharField(max_length=200, blank=True, default='')
    is_trashed = models.BooleanField(default=False, db_index=True)
    trashed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"Post #{self.pk} by {self.author.username}"

    def can_view(self, user):
        # 1. Author can always view
        if user == self.author:
            return True

        # Trashed post cannot be viewed by other users
        if self.is_trashed:
            return False

        # Check block status
        if not user.is_anonymous:
            from accounts.models import BlockedUser
            if BlockedUser.objects.filter(
                models.Q(blocker=self.author, blocked=user) | models.Q(blocker=user, blocked=self.author)
            ).exists():
                return False

        # Group post check
        if self.group:
            if self.group.privacy == 'private':
                if user.is_anonymous or not self.group.is_member(user):
                    return False

        # Privacy checks
        if self.privacy == 'public':
            return True
        elif self.privacy == 'friends':
            if user.is_anonymous:
                return False
            from friends.models import Friendship
            return Friendship.are_friends(self.author, user)
        elif self.privacy == 'friends_except':
            if user.is_anonymous:
                return False
            from friends.models import Friendship
            if not Friendship.are_friends(self.author, user):
                return False
            return not self.custom_audience_deny.filter(id=user.id).exists()
        elif self.privacy == 'specific_friends':
            if user.is_anonymous:
                return False
            return self.custom_audience_allow.filter(id=user.id).exists()
        elif self.privacy == 'only_me':
            return user == self.author
        elif self.privacy == 'custom':
            if user.is_anonymous:
                return False
            if self.custom_audience_deny.filter(id=user.id).exists():
                return False
            if self.custom_audience_allow.filter(id=user.id).exists():
                return True
            from friends.models import Friendship
            return Friendship.are_friends(self.author, user)
        return False

    @property
    def reaction_counts(self):
        counts = {}
        for r_type in ['like', 'love', 'care', 'haha', 'wow', 'sad', 'angry']:
            c = self.reactions.filter(reaction_type=r_type).count()
            if c > 0:
                counts[r_type] = c
        return counts

    @property
    def total_reactions(self):
        return self.reactions.count()

    @property
    def total_comments(self):
        return self.comments.count()

    @property
    def total_shares(self):
        return self.shares.count()

    def user_reaction(self, user):
        if not user or user.is_anonymous:
            return None
        r = self.reactions.filter(user=user).first()
        return r.reaction_type if r else None


class PostMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='posts/%Y/%m/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    caption = models.CharField(max_length=255, blank=True, default='')
    alt_text = models.CharField(max_length=255, blank=True, default='')
    location = models.CharField(max_length=200, blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.media_type} for Post #{self.post_id}"


class Reaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('care', 'Care'),
        ('haha', 'Haha'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reactions')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} on Post #{self.post_id}"
        return f"{self.user.username} reacted {self.reaction_type} on Post #{self.post_id}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on Post #{self.post_id}"

    @property
    def total_likes(self):
        return self.reactions.count()


class CommentReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('care', 'Care'),
        ('haha', 'Haha'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comment_reactions')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')

    def __str__(self):
        return f"{self.user.username} liked comment #{self.comment_id}"


class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by_users')
    collection_name = models.CharField(max_length=100, default='All Posts', db_index=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} saved Post #{self.post_id}"


class PostView(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='viewed_posts')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        u = self.viewer.username if self.viewer else (self.ip_address or 'Anonymous')
        return f"{u} viewed Post #{self.post_id}"


class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    posts = models.ManyToManyField(Post, related_name='hashtags', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.name}"


class Report(models.Model):
    TARGET_TYPE_CHOICES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('user', 'User'),
        ('group', 'Group'),
        ('page', 'Page'),
        ('event', 'Event'),
        ('listing', 'Marketplace Listing'),
        ('video', 'Video'),
        ('reel', 'Reel'),
        ('stream', 'Live Stream'),
    ]

    REASON_CHOICES = [
        ('spam', 'Spam or Scam'),
        ('harassment', 'Harassment or Bullying'),
        ('hate_speech', 'Hate Speech'),
        ('violence', 'Violence or Dangerous Content'),
        ('nudity', 'Nudity or Sexual Content'),
        ('false_info', 'False Information'),
        ('other', 'Other Violation'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('resolved', 'Resolved - Action Taken'),
        ('dismissed', 'Dismissed - No Violation'),
    ]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    details = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    action_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.pk}: {self.target_type} ({self.status})"


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=100)
    target_repr = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor}: {self.action}"


# ========================================================
# V4: REAL VIDEO POST SYSTEM
# ========================================================

class Video(models.Model):
    CATEGORY_CHOICES = [
        ('entertainment', 'Entertainment'),
        ('music', 'Music'),
        ('gaming', 'Gaming'),
        ('education', 'Education & Learning'),
        ('tech', 'Technology & Science'),
        ('lifestyle', 'Lifestyle & Travel'),
        ('sports', 'Sports & Fitness'),
        ('news', 'News & Current Affairs'),
        ('other', 'Other'),
    ]

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    PROCESSING_CHOICES = [
        ('processing', 'Processing'),
        ('ready', 'Ready for Playback'),
        ('failed', 'Processing Failed'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    video_file = models.FileField(upload_to='videos/%Y/%m/')
    thumbnail = models.ImageField(upload_to='videos/thumbnails/%Y/%m/', null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='entertainment')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    file_size_bytes = models.BigIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    processing_status = models.CharField(max_length=20, choices=PROCESSING_CHOICES, default='ready')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    def get_thumbnail_url(self):
        if self.thumbnail and hasattr(self.thumbnail, 'url'):
            return self.thumbnail.url
        return '/static/images/default-cover.svg'

    @property
    def duration_formatted(self):
        mins = self.duration // 60
        secs = self.duration % 60
        return f"{mins:02d}:{secs:02d}"

    def can_view(self, user):
        if self.privacy == 'public':
            return True
        if not user or user.is_anonymous:
            return False
        if user == self.author:
            return True
        if self.privacy == 'friends':
            from friends.models import Friendship
            return Friendship.are_friends(self.author, user)
        return False

    def can_manage(self, user):
        if not user or user.is_anonymous:
            return False
        return user == self.author or user.is_superuser or user.is_staff

    @property
    def likes_count(self):
        return self.reactions.count()

    @property
    def comments_count(self):
        return self.comments.count()


class VideoView(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='video_views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='viewed_videos')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    watch_time_seconds = models.PositiveIntegerField(default=0)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        user_repr = self.viewer.username if self.viewer else (self.ip_address or 'Anonymous')
        return f"{user_repr} viewed {self.video.title}"


class VideoReaction(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_reactions')
    reaction_type = models.CharField(max_length=20, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('video', 'user')

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} on {self.video.title}"


class VideoComment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.video.title}"


class SavedVideo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_videos')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.video.title}"


# ========================================================
# V4: REELS / SHORT VIDEO SYSTEM
# ========================================================

class Reel(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reels')
    video_file = models.FileField(upload_to='reels/%Y/%m/')
    thumbnail = models.ImageField(upload_to='reels/thumbnails/%Y/%m/', null=True, blank=True)
    caption = models.TextField(blank=True, default='')
    audio_title = models.CharField(max_length=150, default='Original Audio')
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds (e.g. 15-90s)")
    views_count = models.PositiveIntegerField(default=0)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    location = models.CharField(max_length=150, blank=True, default='')
    tagged_friends = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='tagged_reels')
    comments_enabled = models.BooleanField(default=True)
    allow_sharing = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=[('published', 'Published'), ('draft', 'Draft')], default='published')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reel #{self.pk} by {self.author.username}"

    def get_thumbnail_url(self):
        if self.thumbnail and hasattr(self.thumbnail, 'url'):
            return self.thumbnail.url
        return '/static/images/default-cover.svg'

    @property
    def duration_formatted(self):
        mins = self.duration // 60
        secs = self.duration % 60
        return f"{mins:02d}:{secs:02d}"

    @property
    def likes_count(self):
        return self.reactions.count()

    @property
    def comments_count(self):
        return self.comments.count()

    def can_view(self, user):
        if self.privacy == 'public':
            return True
        if not user or user.is_anonymous:
            return False
        if user == self.author or user.is_superuser or user.is_staff:
            return True
        if self.privacy == 'friends':
            from friends.models import Friendship
            return Friendship.are_friends(self.author, user)
        return False


class ReelReaction(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reel_reactions')
    reaction_type = models.CharField(max_length=20, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reel', 'user')

    def __str__(self):
        return f"{self.user.username} liked Reel #{self.reel_id}"


class ReelComment(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reel_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on Reel #{self.reel_id} by {self.author.username}"


class SavedReel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_reels')
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'reel')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved Reel #{self.reel_id}"


class ReelView(models.Model):
    reel = models.ForeignKey(Reel, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reel_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"View on Reel #{self.reel_id}"


# ========================================================
# V6: PHOTO ALBUMS & ALBUM PHOTOS
# ========================================================

class PhotoAlbum(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('only_me', 'Only Me'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='photo_albums')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    cover_photo = models.ImageField(upload_to='albums/covers/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    def can_view(self, viewer):
        if not viewer or viewer.is_anonymous:
            return self.privacy == 'public'
        if viewer == self.user or viewer.is_superuser:
            return True
        if self.privacy == 'public':
            return True
        if self.privacy == 'friends':
            from friends.models import Friendship
            return Friendship.are_friends(self.user, viewer)
        return False


class AlbumPhoto(models.Model):
    album = models.ForeignKey(PhotoAlbum, on_delete=models.CASCADE, related_name='photos', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='album_photos')
    image = models.ImageField(upload_to='albums/photos/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True, default='')
    alt_text = models.CharField(max_length=255, blank=True, default='')
    tagged_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='tagged_in_photos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo #{self.id} by {self.user.username}"


# ========================================================
# V4: POLLS AND INTERACTIVE POSTS
# ========================================================

class Poll(models.Model):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name='poll')
    question = models.CharField(max_length=255)
    expires_at = models.DateTimeField(null=True, blank=True)
    allow_multiple = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def total_votes(self):
        return self.votes.count()

    def user_has_voted(self, user):
        if not user or user.is_anonymous:
            return False
        return self.votes.filter(user=user).exists()


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.text} ({self.votes_count} votes)"

    @property
    def votes_count(self):
        return self.votes.count()

    @property
    def percentage(self):
        total = self.poll.total_votes
        if total == 0:
            return 0
        return round((self.votes_count / total) * 100, 1)


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='poll_votes')
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'user')

    def __str__(self):
        return f"{self.user.username} voted for '{self.option.text}'"
