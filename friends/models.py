from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')
        ordering = ['-created_at']

    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("You cannot send a friend request to yourself.")

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


class Friendship(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')
        ordering = ['-created_at']

    def clean(self):
        if self.user1 == self.user2:
            raise ValidationError("A user cannot be friends with themselves.")

    def save(self, *args, **kwargs):
        if self.user1_id and self.user2_id and self.user1_id > self.user2_id:
            self.user1, self.user2 = self.user2, self.user1
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user1.username} & {self.user2.username}"

    @classmethod
    def are_friends(cls, u1, u2):
        if not u1 or not u2 or u1.is_anonymous or u2.is_anonymous or u1 == u2:
            return False
        first_id, second_id = (u1.id, u2.id) if u1.id < u2.id else (u2.id, u1.id)
        return cls.objects.filter(user1_id=first_id, user2_id=second_id).exists()

    @classmethod
    def get_friend_ids(cls, user):
        if not user or user.is_anonymous:
            return set()
        user_id = user.id if hasattr(user, 'id') else user
        f1 = cls.objects.filter(user1_id=user_id).values_list('user2_id', flat=True)
        f2 = cls.objects.filter(user2_id=user_id).values_list('user1_id', flat=True)
        return set(list(f1) + list(f2))

    @classmethod
    def get_mutual_friends(cls, u1, u2):
        ids1 = cls.get_friend_ids(u1)
        ids2 = cls.get_friend_ids(u2)
        mutual_ids = ids1.intersection(ids2)
        from accounts.models import CustomUser
        return CustomUser.objects.filter(id__in=mutual_ids, is_active=True, is_deactivated=False)


class DismissedSuggestion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dismissed_suggestions')
    dismissed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dismissed_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'dismissed_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} dismissed {self.dismissed_user.username}"

