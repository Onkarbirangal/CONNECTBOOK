from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification
from accounts.models import BlockedUser, MutedUser, UserPreference

def send_notification(recipient, actor, notification_type, title, message, target_url='', category=None):
    """Creates a notification respecting user privacy/preferences and attempts real-time WebSocket push."""
    if not recipient or not actor or recipient == actor:
        return None

    # Check blocked or muted users
    if BlockedUser.objects.filter(blocker=recipient, blocked=actor).exists() or \
       BlockedUser.objects.filter(blocker=actor, blocked=recipient).exists():
        return None

    if MutedUser.objects.filter(user=recipient, muted_user=actor).exists():
        return None

    # Check notification preferences
    prefs = getattr(recipient, 'preferences', None)
    if prefs:
        if notification_type in ['post_comment', 'comment_reply'] and not prefs.notify_comments:
            return None
        if notification_type == 'post_reaction' and not prefs.notify_reactions:
            return None
        if notification_type == 'message' and not prefs.notify_messages:
            return None
        if notification_type in ['friend_request', 'friend_accepted'] and not prefs.notify_friend_requests:
            return None

    # Categorization
    if not category:
        if notification_type == 'message':
            category = 'messages'
        elif notification_type in ['post_reaction', 'post_comment', 'comment_reply', 'mention', 'friend_request', 'friend_accepted']:
            category = 'social'
        elif notification_type.startswith('group_'):
            category = 'groups'
        else:
            category = 'general'

    safe_title = str(title)[:250]
    safe_message = str(message)[:500]

    notif = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        category=category,
        title=safe_title,
        message=safe_message,
        target_url=target_url,
    )

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            unread_count = Notification.objects.filter(recipient=recipient, is_read=False).count()
            actor_avatar = actor.profile.get_avatar_url() if hasattr(actor, 'profile') else '/static/images/default-avatar.svg'
            async_to_sync(channel_layer.group_send)(
                f'notify_{recipient.id}',
                {
                    'type': 'user_notification',
                    'id': notif.id,
                    'category': category,
                    'title': safe_title,
                    'message': safe_message,
                    'target_url': target_url,
                    'actor_name': actor.get_display_name(),
                    'actor_avatar': actor_avatar,
                    'created_at': 'Just now',
                    'unread_count': unread_count,
                }
            )
    except Exception:
        pass

    return notif
