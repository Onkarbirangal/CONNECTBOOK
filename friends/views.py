from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import FriendRequest, Friendship, DismissedSuggestion
from accounts.models import BlockedUser, Follow
from notifications.services import send_notification

User = get_user_model()


def is_ajax_request(request):
    """Helper to detect AJAX or Fetch API requests."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or request.POST.get('ajax') == 'true'
        or request.GET.get('ajax') == 'true'
    )


def get_scored_suggestions(user, search_q=None, filter_type='all'):
    """
    Intelligent friend suggestion algorithm ranking by:
    - Mutual friends count
    - Follower/following relationships
    - Shared group memberships
    - Location, hometown, work alignment
    - Account recency
    Excludes self, existing friends, pending requests (sent/received),
    blocked users (both directions), and dismissed suggestions.
    """
    friend_ids = Friendship.get_friend_ids(user)
    sent_request_ids = FriendRequest.objects.filter(sender=user, status='pending').values_list('receiver_id', flat=True)
    received_request_ids = FriendRequest.objects.filter(receiver=user, status='pending').values_list('sender_id', flat=True)

    # Blocked users in either direction
    blocked_ids = BlockedUser.objects.filter(
        Q(blocker=user) | Q(blocked=user)
    ).values_list('blocked_id', 'blocker_id')
    flat_blocked = set([uid for pair in blocked_ids for uid in pair])

    # Dismissed suggestions in DB and session
    db_dismissed = set(DismissedSuggestion.objects.filter(user=user).values_list('dismissed_user_id', flat=True))

    exclude_ids = set(friend_ids) | set(sent_request_ids) | set(received_request_ids) | flat_blocked | db_dismissed | {user.id}

    candidates_qs = User.objects.exclude(
        id__in=exclude_ids
    ).filter(
        is_active=True, is_deactivated=False
    ).select_related('profile')

    if search_q:
        q_filter = Q(first_name__icontains=search_q) | Q(last_name__icontains=search_q) | Q(username__icontains=search_q)
        candidates_qs = candidates_qs.filter(q_filter)

    candidates = list(candidates_qs)

    # Group memberships
    user_to_groups = {}
    try:
        from groups_app.models import GroupMembership
        user_group_ids = set(GroupMembership.objects.filter(user=user).values_list('group_id', flat=True))
        if user_group_ids:
            candidate_group_memberships = GroupMembership.objects.filter(
                user__in=candidates, group_id__in=user_group_ids
            ).select_related('group')
            for gm in candidate_group_memberships:
                user_to_groups.setdefault(gm.user_id, []).append(gm.group.name)
    except Exception:
        pass

    # Follow relationships
    user_followers = set(Follow.objects.filter(followed=user, follower__in=candidates).values_list('follower_id', flat=True))
    user_following = set(Follow.objects.filter(follower=user, followed__in=candidates).values_list('followed_id', flat=True))

    user_profile = getattr(user, 'profile', None)

    for c in candidates:
        c_friend_ids = Friendship.get_friend_ids(c)
        mutual_ids = friend_ids.intersection(c_friend_ids)
        c.mutual_count = len(mutual_ids)

        score = 0
        reason = ""

        # Mutual friends (highest weight)
        if c.mutual_count > 0:
            score += c.mutual_count * 20
            reason = f"{c.mutual_count} mutual friend{'s' if c.mutual_count != 1 else ''}"

        # Follower connection
        if c.id in user_followers:
            score += 10
            if not reason:
                reason = "Follows you"

        # Following connection
        if c.id in user_following:
            score += 8
            if not reason:
                reason = "You follow them"

        # Shared groups
        shared_groups = user_to_groups.get(c.id, [])
        if shared_groups:
            score += len(shared_groups) * 6
            if not reason:
                reason = f"Member of {shared_groups[0]}"

        # Location / Hometown / Work
        c_profile = getattr(c, 'profile', None)
        if user_profile and c_profile:
            if getattr(user_profile, 'city', None) and getattr(c_profile, 'city', None) and user_profile.city.lower() == c_profile.city.lower():
                score += 5
                if not reason:
                    reason = f"Lives in {c_profile.city}"
            elif getattr(user_profile, 'hometown', None) and getattr(c_profile, 'hometown', None) and user_profile.hometown.lower() == c_profile.hometown.lower():
                score += 4
                if not reason:
                    reason = f"From {c_profile.hometown}"
            elif getattr(user_profile, 'work', None) and getattr(c_profile, 'work', None) and user_profile.work.lower() == c_profile.work.lower():
                score += 4
                if not reason:
                    reason = f"Works at {c_profile.work}"

        # New to ConnectBook (< 30 days)
        if (timezone.now() - c.date_joined).days <= 30:
            score += 3
            if not reason:
                reason = "New to ConnectBook"

        if not reason:
            reason = "Suggested for you"

        c.suggestion_reason = reason
        c.suggestion_score = score
        c.shared_groups_count = len(shared_groups)

    # Filter and sort
    if filter_type == 'mutual':
        candidates = [c for c in candidates if c.mutual_count > 0]
        candidates.sort(key=lambda u: (u.mutual_count, u.suggestion_score), reverse=True)
    elif filter_type == 'recent':
        candidates.sort(key=lambda u: u.date_joined, reverse=True)
    elif filter_type == 'groups':
        candidates = [c for c in candidates if c.shared_groups_count > 0]
        candidates.sort(key=lambda u: (u.shared_groups_count, u.suggestion_score), reverse=True)
    else:
        # Default 'all': score descending, then date_joined descending
        candidates.sort(key=lambda u: (u.suggestion_score, u.date_joined), reverse=True)

    return candidates


@login_required
def friends_list_view(request):
    tab = request.GET.get('tab', 'all')
    search_q = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', 'all')

    friend_ids = Friendship.get_friend_ids(request.user)
    all_friends_qs = User.objects.filter(id__in=friend_ids, is_active=True, is_deactivated=False).select_related('profile')

    pending_received = FriendRequest.objects.filter(receiver=request.user, status='pending').select_related('sender', 'sender__profile')
    pending_sent = FriendRequest.objects.filter(sender=request.user, status='pending').select_related('receiver', 'receiver__profile')

    # Birthdays calculation
    today = timezone.now().date()
    birthdays_qs = all_friends_qs.filter(date_of_birth__month=today.month)

    # Followers / Following / Blocked
    followers_qs = Follow.objects.filter(followed=request.user).select_related('follower', 'follower__profile')
    following_qs = Follow.objects.filter(follower=request.user).select_related('followed', 'followed__profile')
    blocked_qs = BlockedUser.objects.filter(blocker=request.user).select_related('blocked', 'blocked__profile')

    # Suggestions calculation via intelligent algorithm
    all_scored_suggestions = get_scored_suggestions(request.user, search_q=search_q if tab == 'suggestions' else None, filter_type=filter_type)
    total_suggestions_count = len(all_scored_suggestions)

    # Paginate suggestions (12 per page = 3x4 grid)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(all_scored_suggestions, 12)
    try:
        suggestions_page = paginator.page(page_number)
    except PageNotAnInteger:
        suggestions_page = paginator.page(1)
    except EmptyPage:
        suggestions_page = paginator.page(paginator.num_pages)

    suggested_list = list(suggestions_page.object_list)

    # Apply search filter to friends and requests if in those tabs
    friends = all_friends_qs
    if search_q and tab != 'suggestions':
        q_filter = Q(first_name__icontains=search_q) | Q(last_name__icontains=search_q) | Q(username__icontains=search_q)
        friends = friends.filter(q_filter)
        pending_received = pending_received.filter(Q(sender__first_name__icontains=search_q) | Q(sender__last_name__icontains=search_q) | Q(sender__username__icontains=search_q))
        pending_sent = pending_sent.filter(Q(receiver__first_name__icontains=search_q) | Q(receiver__last_name__icontains=search_q) | Q(receiver__username__icontains=search_q))
        followers_qs = followers_qs.filter(Q(follower__first_name__icontains=search_q) | Q(follower__last_name__icontains=search_q) | Q(follower__username__icontains=search_q))
        following_qs = following_qs.filter(Q(followed__first_name__icontains=search_q) | Q(followed__last_name__icontains=search_q) | Q(followed__username__icontains=search_q))

    # Compute mutual friends count for other lists
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
        'filter_type': filter_type,
        'friends': friends_list,
        'pending_received': received_list,
        'pending_sent': sent_list,
        'suggested_list': suggested_list,
        'suggestions_page_obj': suggestions_page,
        'birthdays': birthdays_list,
        'followers': followers_list,
        'following': following_list,
        'blocked_users': blocked_qs,
        'total_friends_count': len(friend_ids),
        'pending_received_count': pending_received.count(),
        'pending_sent_count': pending_sent.count(),
        'suggestions_count': total_suggestions_count,
        'total_suggestions_count': total_suggestions_count,
        'birthdays_count': len(birthdays_list),
        'followers_count': len(followers_list),
        'following_count': len(following_list),
        'blocked_count': blocked_qs.count(),
    })


@login_required
def friend_suggestions_view(request):
    """View dedicated to People You May Know / Friend Suggestions."""
    get_params = request.GET.copy()
    get_params['tab'] = 'suggestions'
    request.GET = get_params
    return friends_list_view(request)


@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    is_ajax = is_ajax_request(request)

    if receiver == request.user:
        msg = "You cannot send a friend request to yourself."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('accounts:profile', username=receiver.username)

    # Check block
    if BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=receiver) | Q(blocker=receiver, blocked=request.user)
    ).exists():
        msg = "Unable to send friend request."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg}, status=403)
        messages.error(request, msg)
        return redirect('social:feed')

    # Check if already friends
    if Friendship.are_friends(request.user, receiver):
        msg = "You are already friends."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg, 'status': 'already_friends'}, status=400)
        messages.info(request, msg)
        return redirect('accounts:profile', username=receiver.username)

    # Check receiver's privacy setting for friend requests
    rec_privacy = getattr(receiver, 'privacy_settings', None)
    if rec_privacy and rec_privacy.friend_request_permission == 'friends_of_friends':
        mutuals = Friendship.get_mutual_friends(request.user, receiver)
        if not mutuals:
            msg = f"{receiver.get_display_name()} only accepts friend requests from friends of friends."
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg, 'status': 'privacy_restricted'}, status=403)
            messages.error(request, msg)
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
        target_url="/friends/?tab=requests"
    )

    sent_count = FriendRequest.objects.filter(sender=request.user, status='pending').count()

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'sent',
            'message': f"Friend request sent to {receiver.get_display_name()}.",
            'user_id': receiver.id,
            'pending_sent_count': sent_count,
        })

    messages.success(request, f"Friend request sent to {receiver.get_display_name()}.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def accept_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user, status='pending')
    is_ajax = is_ajax_request(request)
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

    received_count = FriendRequest.objects.filter(receiver=request.user, status='pending').count()
    total_friends = len(Friendship.get_friend_ids(request.user))

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'accepted',
            'message': f"You are now friends with {freq.sender.get_display_name()}!",
            'request_id': request_id,
            'sender_id': freq.sender.id,
            'pending_received_count': received_count,
            'total_friends_count': total_friends,
        })

    messages.success(request, f"You are now friends with {freq.sender.get_display_name()}!")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def reject_friend_request(request, request_id):
    freq = get_object_or_404(FriendRequest, id=request_id, receiver=request.user, status='pending')
    is_ajax = is_ajax_request(request)
    freq.status = 'rejected'
    freq.save()

    received_count = FriendRequest.objects.filter(receiver=request.user, status='pending').count()

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'rejected',
            'message': "Friend request declined.",
            'request_id': request_id,
            'pending_received_count': received_count,
        })

    messages.info(request, "Friend request declined.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def cancel_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    is_ajax = is_ajax_request(request)
    FriendRequest.objects.filter(sender=request.user, receiver=receiver, status='pending').delete()

    sent_count = FriendRequest.objects.filter(sender=request.user, status='pending').count()

    if is_ajax:
        return JsonResponse({
            'success': True,
            'status': 'cancelled',
            'message': f"Friend request to {receiver.get_display_name()} cancelled.",
            'user_id': receiver.id,
            'pending_sent_count': sent_count,
        })

    messages.info(request, "Friend request cancelled.")
    return redirect(request.META.get('HTTP_REFERER', 'friends:list'))


@login_required
def dismiss_suggestion_api(request, user_id):
    """Dismiss a friend suggestion via AJAX or POST."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST required")

    target = get_object_or_404(User, id=user_id)
    DismissedSuggestion.objects.get_or_create(user=request.user, dismissed_user=target)

    remaining_suggestions = get_scored_suggestions(request.user)
    remaining_count = len(remaining_suggestions)

    return JsonResponse({
        'success': True,
        'message': f"Removed {target.get_display_name()} from suggestions.",
        'user_id': target.id,
        'remaining_count': remaining_count,
    })


@login_required
def undo_dismiss_suggestion_api(request, user_id):
    """Restore a previously dismissed friend suggestion."""
    if request.method != 'POST':
        return HttpResponseForbidden("POST required")

    target = get_object_or_404(User, id=user_id)
    DismissedSuggestion.objects.filter(user=request.user, dismissed_user=target).delete()

    remaining_suggestions = get_scored_suggestions(request.user)
    remaining_count = len(remaining_suggestions)

    return JsonResponse({
        'success': True,
        'message': f"Restored {target.get_display_name()} to suggestions.",
        'user_id': target.id,
        'remaining_count': remaining_count,
    })


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
