from django.db import models
from django.conf import settings


class SensitiveAccessLog(models.Model):
    staff_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sensitive_access_logs')
    target_resource = models.CharField(max_length=150)
    reason = models.TextField()
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_access_logs')

    class Meta:
        ordering = ['-accessed_at']

    def __str__(self):
        return f"{self.staff_user.username} accessed {self.target_resource} at {self.accessed_at}"

