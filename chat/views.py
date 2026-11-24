import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Max
from django.contrib.auth import get_user_model
from .models import Conversation, ConversationParticipant, Message, MessageReaction, CallSession
from friends.models import Friendship
from notifications.services import send_notification

User = get_user_model()


@login_required
def inbox_view(request):
    show_archived = request.GET.get('archived') == '1'
    search_q = request.GET.get('q', '').strip()
    participations = ConversationParticipant.objects.filter(
        user=request.user,
        is_archived=show_archived
    ).select_related('conversation')
    conversations = [p.conversation for p in participations]

    for conv in conversations:
        conv.other_user = conv.get_recipient(request.user)
        conv.unread_count = conv.messages.exclude(sender=request.user).filter(is_read=False).count()

    if search_q:
        q_lower = search_q.lower()
        conversations = [c for c in conversations if (c.other_user and (q_lower in c.other_user.get_display_name().lower() or q_lower in c.other_user.username.lower())) or (c.title and q_lower in c.title.lower())]

    active_conversation = conversations[0] if conversations else None
    messages_list = []
    recipient = None
    active_part = None

    if active_conversation:
        messages_list = active_conversation.messages.filter(is_deleted=False).select_related(
            'sender', 'sender__profile', 'reply_to', 'reply_to__sender'
        ).prefetch_related('reactions', 'reactions__user').order_by('created_at')
        recipient = active_conversation.get_recipient(request.user)
        active_part = active_conversation.participants.filter(user=request.user).first()

    return render(request, 'chat/messenger.html', {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'active_part': active_part,
        'messages_list': messages_list,
        'recipient': recipient,
        'show_archived': show_archived,
        'search_q': search_q,
    })


@login_required
def conversation_view(request, conversation_id):
    active_conversation = get_object_or_404(Conversation, id=conversation_id)

    # Verify participant
    active_part = active_conversation.participants.filter(user=request.user).first()
    if not active_part:
        return HttpResponseForbidden("You are not a participant in this conversation.")

    # Mark messages as read
    active_conversation.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)

    participations = ConversationParticipant.objects.filter(
        user=request.user,
        is_archived=active_part.is_archived
    ).select_related('conversation')
    conversations = [p.conversation for p in participations]

    for conv in conversations:
        conv.other_user = conv.get_recipient(request.user)
        conv.unread_count = conv.messages.exclude(sender=request.user).filter(is_read=False).count()

    messages_list = active_conversation.messages.filter(is_deleted=False).select_related(
        'sender', 'sender__profile', 'reply_to', 'reply_to__sender'
    ).prefetch_related('reactions', 'reactions__user').order_by('created_at')
    recipient = active_conversation.get_recipient(request.user)

    return render(request, 'chat/messenger.html', {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'active_part': active_part,
        'messages_list': messages_list,
        'recipient': recipient,
        'show_archived': active_part.is_archived,
    })


@login_required
def direct_chat_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot start a conversation with yourself.")
        return redirect('chat:inbox')

    # Look for existing direct conversation
    existing_conv = Conversation.objects.filter(
        is_group=False,
        participants__user=request.user
    ).filter(
        participants__user=target_user
    ).first()

    if not existing_conv:
        existing_conv = Conversation.objects.create(is_group=False)
        ConversationParticipant.objects.create(conversation=existing_conv, user=request.user)
        ConversationParticipant.objects.create(conversation=existing_conv, user=target_user)

    return redirect('chat:conversation', conversation_id=existing_conv.id)


@login_required
def send_message_http(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    if not conv.participants.filter(user=request.user).exists():
        return HttpResponseForbidden()

    if request.method == 'POST':
        data = {}
        try:
            data = json.loads(request.body)
            content = data.get('message', '').strip()
        except Exception:
            data = {}
            content = (request.POST.get('message') or request.POST.get('content') or '').strip()

        attachment = request.FILES.get('attachment')
        if content or attachment:
            reply_to_id = request.POST.get('reply_to_id') or (data.get('reply_to_id') if isinstance(data, dict) else None)
            
            reply_to_msg = None
            if reply_to_id:
                reply_to_msg = Message.objects.filter(id=reply_to_id, conversation=conv).first()

            msg = Message.objects.create(
                conversation=conv,
                sender=request.user,
                content=content or ("Sent an attachment" if attachment else ""),
                attachment=attachment,
                reply_to=reply_to_msg
            )
            conv.updated_at = timezone.now()
            conv.save(update_fields=['updated_at'])

            recipient = conv.get_recipient(request.user)
            if recipient:
                snippet = content[:40] if content else "Sent an attachment"
                send_notification(
                    recipient=recipient,
                    actor=request.user,
                    notification_type='message',
                    title='New Message',
                    message=f"{request.user.get_display_name()}: {snippet}",
                    target_url=f"/chat/{conv.id}/"
                )

            return JsonResponse({
                'status': 'success',
                'success': True,
                'attachment_url': msg.attachment.url if msg.attachment else None,
                'message': {
                    'id': msg.id,
                    'content': msg.content,
                    'attachment_url': msg.attachment.url if msg.attachment else None,
                    'sender_id': request.user.id,
                    'created_at': msg.created_at.strftime('%I:%M %p'),
                }
            })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def toggle_mute_conversation_view(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    part = get_object_or_404(ConversationParticipant, conversation=conv, user=request.user)
    part.is_muted = not part.is_muted
    part.save(update_fields=['is_muted'])
    msg = "Conversation muted" if part.is_muted else "Conversation unmuted"
    messages.success(request, msg)
    return redirect('chat:conversation', conversation_id=conv.id)


@login_required
def toggle_archive_conversation_view(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    part = get_object_or_404(ConversationParticipant, conversation=conv, user=request.user)
    part.is_archived = not part.is_archived
    part.save(update_fields=['is_archived'])
    msg = "Conversation archived" if part.is_archived else "Conversation unarchived"
    messages.success(request, msg)
    return redirect('chat:inbox')


@login_required
def react_message_view(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    if not msg.conversation.participants.filter(user=request.user).exists():
        return HttpResponseForbidden()

    reaction_type = request.POST.get('reaction', 'like')
    existing = MessageReaction.objects.filter(message=msg, user=request.user).first()
    if existing:
        if existing.reaction == reaction_type:
            existing.delete()
            status = 'removed'
        else:
            existing.reaction = reaction_type
            existing.save(update_fields=['reaction'])
            status = 'updated'
    else:
        MessageReaction.objects.create(message=msg, user=request.user, reaction=reaction_type)
        status = 'added'

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'status': status})
    return redirect('chat:conversation', conversation_id=msg.conversation_id)


@login_required
def edit_message_view(request, message_id):
    msg = get_object_or_404(Message, id=message_id, sender=request.user, is_deleted=False)
    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        if new_content:
            msg.content = new_content
            msg.is_edited = True
            msg.edited_at = timezone.now()
            msg.save(update_fields=['content', 'is_edited', 'edited_at'])
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'content': msg.content})
    return redirect('chat:conversation', conversation_id=msg.conversation_id)


@login_required
def delete_message_view(request, message_id):
    msg = get_object_or_404(Message, id=message_id, sender=request.user)
    msg.is_deleted = True
    msg.content = 'This message was deleted'
    msg.save(update_fields=['is_deleted', 'content'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('chat:conversation', conversation_id=msg.conversation_id)


@login_required
def get_messages_api(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id)
    if not conv.participants.filter(user=request.user).exists():
        return HttpResponseForbidden()

    messages_qs = conv.messages.filter(is_deleted=False).select_related('sender').order_by('created_at')[:50]
    data = []
    for m in messages_qs:
        data.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.get_display_name(),
            'content': m.content,
            'created_at': m.created_at.strftime('%I:%M %p'),
        })
    return JsonResponse({'messages': data})


# ========================================================
# V4: WEBRTC VIDEO / AUDIO CALLING VIEWS
# ========================================================

@login_required
def start_call_view(request, user_id, call_type='video'):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot call yourself.")
        return redirect('chat:inbox')

    if call_type not in ['video', 'audio']:
        call_type = 'video'

    room_name = f"cb_{uuid.uuid4().hex[:12]}"
    session = CallSession.objects.create(
        room_name=room_name,
        caller=request.user,
        receiver=target_user,
        call_type=call_type,
        status='ringing'
    )

    try:
        send_notification(
            recipient=target_user,
            notification_type='call',
            title=f"Incoming {call_type.title()} Call",
            body=f"{request.user.get_display_name()} is calling you...",
            link=f"/messages/call/{room_name}/",
            sender=request.user
        )
    except Exception:
        pass

    return redirect('chat:call_room', room_name=room_name)


@login_required
def call_room_view(request, room_name):
    session = get_object_or_404(CallSession, room_name=room_name)
    if not session.can_participate(request.user):
        return HttpResponseForbidden("You are not authorized to join this call.")

    is_caller = (request.user == session.caller)
    peer = session.receiver if is_caller else session.caller

    return render(request, 'chat/call_room.html', {
        'session': session,
        'is_caller': is_caller,
        'peer': peer,
        'call_type': session.call_type,
        'room_name': room_name,
    })


@login_required
def end_call_http_view(request, room_name):
    session = get_object_or_404(CallSession, room_name=room_name)
    if session.can_participate(request.user):
        if session.status != 'ended':
            session.status = 'ended'
            session.ended_at = timezone.now()
            if session.answered_at:
                delta = (session.ended_at - session.answered_at).total_seconds()
                session.duration_seconds = max(0, int(delta))
            session.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ended', 'duration': session.duration_seconds})
    return redirect('chat:inbox')

