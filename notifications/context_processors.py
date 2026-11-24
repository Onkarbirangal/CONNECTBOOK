from .models import Notification

def notification_badge_processor(request):
    """Provides unread notifications count and recent notifications."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(recipient=request.user).select_related('actor', 'actor__profile')[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
