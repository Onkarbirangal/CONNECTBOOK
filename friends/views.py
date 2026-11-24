from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import FriendRequest, Friendship
from accounts.models import BlockedUser
from notifications.services import send_notification

User = get_user_model()


@login_required
def friends_list_view(request):
    tab = request.GET.get('tab', 'all')
    search_q = request.GET.get('q', '').strip()

    friend_ids = Friendship.get_friend_ids(request.user)
    all_friends_qs = User.objects.filter(id__in=friend_ids, is_active=True, is_deactivated=False).select_related('profile')

    pending_received = FriendRequest.objects.filter(receiver=request.user, status='pending').select_related('sender', 'sender__profile')
    pending_sent = FriendRequest.objects.filter(sender=request.user, status='pending').select_related('receiver', 'receiver__profile')

    # Suggestions calculation
    sent_request_ids = FriendRequest.objects.filter(sender=request.user, status='pending').values_list('receiver_id', flat=True)
    received_request_ids = FriendRequest.objects.filter(receiver=request.user, status='pending').values_list('sender_id', flat=True)
    exclude_ids = set(friend_ids) | set(sent_request_ids) | set(received_request_ids) | {request.user.id}
    
    suggestions_qs = User.objects.exclude(
        id__in=exclude_ids
    ).filter(
        is_active=True, is_deactivated=False
    ).select_related('profile')

    # Birthdays calculation
    today = timezone.now().date()
    birthdays_qs = all_friends_qs.filter(
        date_of_birth__month=today.month
    )

    # Followers / Following / Blocked
    from accounts.models import Follow, BlockedUser
    followers_qs = Follow.objects.filter(followed=request.user).select_related('follower', 'follower__profile')
    following_qs = Follow.objects.filter(follower=request.user).select_related('followed', 'followed__profile')
    blocked_qs = BlockedUser.objects.filter(blocker=request.user).select_related('blocked', 'blocked__profile')

    # Apply search filter to active list
    friends = all_friends_qs
    if search_q:
        q_filter = Q(first_name__icontains=search_q) | Q(last_name__icontains=search_q) | Q(username__icontains=search_q)
        friends = friends.filter(q_filter)
        suggestions_qs = suggestions_qs.filter(q_filter)
        pending_received = pending_received.filter(Q(sender__first_name__icontains=search_q) | Q(sender__last_name__icontains=search_q) | Q(sender__username__icontains=search_q))
        pending_sent = pending_sent.filter(Q(receiver__first_name__icontains=search_q) | Q(receiver__last_name__icontains=search_q) | Q(receiver__username__icontains=search_q))
        followers_qs = followers_qs.filter(Q(follower__first_name__icontains=search_q) | Q(follower__last_name__icontains=search_q) | Q(follower__username__icontains=search_q))
        following_qs = following_qs.filter(Q(followed__first_name__icontains=search_q) | Q(followed__last_name__icontains=search_q) | Q(followed__username__icontains=search_q))

    # Compute mutual friends count and attach to each user object
    friends_list = list(friends)
    for f in friends_list:
        other_friend_ids = Friendship.get_friend_ids(f)
        f.mutual_count = len(friend_ids.intersection(other_friend_ids))

    received_list = list(pending_received)
    for req in received_list:
        other_friend_ids = Friendship.get_friend_ids(req.sender)
        req.sender.mutual_count = len(friend_ids.intersection(other_friend_ids))

    sent_list = list(pending_sent)
    for req in sent_list:
        other_friend_ids = Friendship.get_friend_ids(req.receiver)
        req.receiver.mutual_count = len(friend_ids.intersection(other_friend_ids))

    suggested_list = list(suggestions_qs[:24])
    for s in suggested_list:
        other_friend_ids = Friendship.get_friend_ids(s)
        s.mutual_count = len(friend_ids.intersection(other_friend_ids))
    # Sort suggestions by mutual friends descending
    suggested_list.sort(key=lambda u: u.mutual_count, reverse=True)

    birthdays_list = list(birthdays_qs)
    for b in birthdays_list:
        other_friend_ids = Friendship.get_friend_ids(b)
        b.mutual_count = len(friend_ids.intersection(other_friend_ids))

    followers_list = list(followers_qs)
    for fol in followers_list:
        other_friend_ids = Friendship.get_friend_ids(fol.follower)
        fol.follower.mutual_count = len(friend_ids.intersection(other_friend_ids))

    following_list = list(following_qs)
    for fol in following_list:
        other_friend_ids = Friendship.get_friend_ids(fol.followed)
        fol.followed.mutual_count = len(friend_ids.intersection(other_friend_ids))

    return render(request, 'friends/friends_list.html', {
        'active_nav': 'friends',
        'tab': tab,
        'search_q': search_q,
        'friends': friends_list,
        'pending_received': received_list,
        'pending_sent': sent_list,
        'suggested_list': suggested_list,
        'birthdays': birthdays_list,
        'followers': followers_list,
        'following': following_list,
        'blocked_users': blocked_qs,
        'total_friends_count': len(friend_ids),
        'pending_received_count': pending_received.count(),
        'pending_sent_count': pending_sent.count(),
        'suggestions_count': len(suggested_list),
        'birthdays_count': len(birthdays_list),
        'followers_count': len(followers_list),
        'following_count': len(following_list),
        'blocked_count': blocked_qs.count(),
    })


@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)

    if receiver == request.user:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('accounts:profile', username=receiver.username)

    # Check block
    if BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=receiver) | Q(blocker=receiver, blocked=request.user)
    ).exists():
        messages.error(request, "Unable to send friend request.")
        return redirect('social:feed')

    # Check if already friends
    if Friendship.are_friends(request.user, receiver):
        messages.info(request, "You are already friends.")
        return redirect('accounts:profile', username=receiver.username)

    freq, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
        defaults={'status': 'pending'}
    )
    if not created and freq.status != 'pending':
        freq.status = 'pending'
        freq.save()

    send_notification(
        recipient=receiver,
        actor=request.user,
        notification_type='friend_request',
        title='Friend Request',
        message=f"{request.user.get_display_name()} sent you a friend request.",
        target_url=f"/friends/"
    )

    messages.success(request, f"Friend request sent to {receiver.get_display_name()}.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def accept_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user, status='pending')
    freq.status = 'accepted'
    freq.save()

    Friendship.objects.get_or_create(user1=freq.sender, user2=freq.receiver)

    send_notification(
        recipient=freq.sender,
        actor=request.user,
        notification_type='friend_accepted',
        title='Friend Request Accepted',
        message=f"{request.user.get_display_name()} accepted your friend request.",
        target_url=f"/accounts/profile/{request.user.username}/"
    )

    messages.success(request, f"You are now friends with {freq.sender.get_display_name()}!")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def reject_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user, status='pending')
    freq.status = 'rejected'
    freq.save()
    messages.info(request, "Friend request declined.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def cancel_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    FriendRequest.objects.filter(sender=request.user, receiver=receiver, status='pending').delete()
    messages.info(request, "Friend request cancelled.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def remove_friend(request, user_id):
    target = get_object_or_404(User, id=user_id)
    Friendship.objects.filter(
        Q(user1=request.user, user2=target) | Q(user1=target, user2=request.user)
    ).delete()
    FriendRequest.objects.filter(
        Q(sender=request.user, receiver=target) | Q(sender=target, receiver=request.user)
    ).delete()
    messages.info(request, f"Removed {target.get_display_name()} from friends.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def friend_suggestions_view(request):
    friend_ids = Friendship.get_friend_ids(request.user)
    sent_request_ids = FriendRequest.objects.filter(sender=request.user, status='pending').values_list('receiver_id', flat=True)

    suggested = User.objects.exclude(
        id=request.user.id
    ).exclude(
        id__in=friend_ids
    ).exclude(
        id__in=sent_request_ids
    ).filter(
        is_active=True, is_deactivated=False
    ).select_related('profile')[:20]

    return render(request, 'friends/suggestions.html', {
        'suggested': suggested,
    })
