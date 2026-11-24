from .models import ConversationParticipant, Message

def unread_messages_processor(request):
    """Provides unread message count and active conversations."""
    if request.user.is_authenticated:
        # Find conversations where the user participates and has unread messages
        unread_count = Message.objects.filter(
            conversation__participants__user=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return {
            'unread_messages_count': unread_count,
        }
    return {
        'unread_messages_count': 0,
    }
