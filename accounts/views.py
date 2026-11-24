import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.contrib.auth import get_user_model
from .forms import RegisterForm, LoginForm, UserProfileForm, UserBasicInfoForm, UserPrivacySettingForm
from .models import (
    UserProfile, BlockedUser, RestrictedUser, MutedUser, UserPreference, Follow,
    UserPrivacySetting, UserSessionRecord, DataExportRequest, AccountDeletionRequest
)
from friends.models import Friendship, FriendRequest
from social.models import Post, PostMedia, AuditLog, Reaction, SavedPost

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('social:feed')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to ConnectBook, {user.first_name}! Your account is ready.")
            return redirect('social:feed')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('social:feed')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_input = form.cleaned_data['login'].strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Check if login_input is email or username
            user_obj = None
            if '@' in login_input:
                user_obj = User.objects.filter(email__iexact=login_input).first()
            if not user_obj:
                user_obj = User.objects.filter(username__iexact=login_input).first()

            if user_obj:
                if user_obj.is_deactivated:
                    messages.error(request, "This account is currently deactivated. Please contact support to reactivate.")
                    return render(request, 'accounts/login.html', {'form': form})

                user = authenticate(request, username=user_obj.username, password=password)
                if user is not None:
                    login(request, user)
                    if not remember_me:
                        request.session.set_expiry(0) # Session expires on browser close
                    else:
                        request.session.set_expiry(1209600) # 2 weeks
                    next_url = request.GET.get('next')
                    if next_url and not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
                        next_url = None
                    return redirect(next_url if next_url else 'social:feed')

            messages.error(request, "Invalid username/email or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)

    # Check if blocked
    is_blocked = BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=profile_user) | Q(blocker=profile_user, blocked=request.user)
    ).exists()

    if is_blocked and profile_user != request.user:
        return render(request, 'accounts/blocked_profile.html', {'profile_user': profile_user})

    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    privacy_settings, _ = UserPrivacySetting.objects.get_or_create(user=profile_user)
    is_own_profile = (request.user == profile_user)

    # Relationship status
    are_friends = Friendship.are_friends(request.user, profile_user)
    pending_request_sent = FriendRequest.objects.filter(sender=request.user, receiver=profile_user, status='pending').exists()
    pending_request_received = FriendRequest.objects.filter(sender=profile_user, receiver=request.user, status='pending').first()

    # Active tab and subtab
    tab = request.GET.get('tab', 'posts')
    subtab = request.GET.get('subtab', 'your_photos')

    # Content structures
    posts = []
    friends_list = []
    friends_hidden = False
    photos = []
    albums = []
    videos = []
    reels = []
    story_highlights = []
    active_stories = []
    checkin_posts = []
    liked_posts = []
    saved_posts = []
    marketplace_items = []

    # Check visibility permissions
    is_locked = bool(profile and profile.is_locked)
    profile_vis = 'public'
    if privacy_settings and privacy_settings.profile_visibility:
        profile_vis = privacy_settings.profile_visibility
    elif profile and profile.profile_visibility:
        profile_vis = profile.profile_visibility

    if is_locked and not (is_own_profile or are_friends):
        can_view_content = False
    elif profile_vis == 'private' and not is_own_profile:
        can_view_content = False
    elif profile_vis == 'friends' and not (is_own_profile or are_friends):
        can_view_content = False
    else:
        can_view_content = True

    if tab == 'posts' and can_view_content:
        posts_filter = Q(author=profile_user, group__isnull=True, is_trashed=False)
        if not is_own_profile:
            posts_filter &= Q(status='published', is_archived=False)
        else:
            posts_filter &= Q(is_archived=False)

        raw_posts = Post.objects.filter(
            posts_filter
        ).select_related(
            'author', 'author__profile', 'original_post', 'original_post__author', 'original_post__author__profile'
        ).prefetch_related(
            'media_files', 'reactions', 'comments', 'comments__author', 'comments__author__profile', 'tagged_users'
        ).order_by('-is_pinned', '-created_at')
        posts = [p for p in raw_posts if p.can_view(request.user)]

    elif tab == 'friends':
        fl_vis = privacy_settings.friends_list_visibility if privacy_settings else 'public'
        if is_locked and not (is_own_profile or are_friends):
            friends_hidden = True
        elif fl_vis == 'private' and not is_own_profile:
            friends_hidden = True
        elif fl_vis == 'friends' and not (are_friends or is_own_profile):
            friends_hidden = True
        else:
            friend_ids = Friendship.get_friend_ids(profile_user)
            friends_list = User.objects.filter(id__in=friend_ids, is_active=True, is_deactivated=False).select_related('profile')

    elif tab == 'photos':
        from social.models import PhotoAlbum, AlbumPhoto
        if can_view_content:
            if subtab == 'albums':
                raw_albums = PhotoAlbum.objects.filter(user=profile_user).prefetch_related('photos')
                albums = [a for a in raw_albums if a.can_view(request.user)]
            elif subtab == 'photos_of_you':
                photos = AlbumPhoto.objects.filter(tagged_users=profile_user).select_related('user')
            else:
                post_photos = list(PostMedia.objects.filter(post__author=profile_user, media_type='image', post__is_trashed=False).select_related('post'))
                album_photos = list(AlbumPhoto.objects.filter(user=profile_user))
                photos = post_photos + album_photos
                albums = PhotoAlbum.objects.filter(user=profile_user)

    elif tab == 'videos':
        from social.models import Video
        if can_view_content:
            videos = Video.objects.filter(author=profile_user).select_related('author')
            post_videos = PostMedia.objects.filter(post__author=profile_user, media_type='video', post__is_trashed=False).select_related('post')

    elif tab == 'reels':
        from social.models import Reel
        reels_qs = Reel.objects.filter(author=profile_user)
        if not is_own_profile:
            reels_qs = reels_qs.filter(status='published')
        reels = reels_qs.select_related('author').order_by('-created_at')

    elif tab == 'stories':
        from stories.models import Story, StoryHighlight
        if can_view_content:
            story_highlights = StoryHighlight.objects.filter(user=profile_user).prefetch_related('stories')
            raw_stories = Story.objects.filter(author=profile_user, expires_at__gt=timezone.now()).order_by('created_at')
            active_stories = [s for s in raw_stories if s.can_view(request.user)]

    elif tab == 'checkins':
        if can_view_content:
            raw_checkins = Post.objects.filter(
                author=profile_user,
                group__isnull=True,
                is_trashed=False
            ).exclude(location_name='').select_related('author', 'author__profile').prefetch_related('media_files', 'reactions', 'comments').order_by('-created_at')
            checkin_posts = [p for p in raw_checkins if p.can_view(request.user)]

    elif tab == 'likes':
        if can_view_content:
            liked_reactions = Reaction.objects.filter(user=profile_user).select_related('post', 'post__author', 'post__author__profile').order_by('-created_at')[:40]
            liked_posts = [r.post for r in liked_reactions if r.post and not r.post.is_trashed and r.post.can_view(request.user)]

    elif tab == 'saved' and is_own_profile:
        saved_posts = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author', 'post__author__profile').order_by('-saved_at')

    elif tab == 'more':
        from marketplace.models import MarketplaceListing
        marketplace_items = MarketplaceListing.objects.filter(seller=profile_user).order_by('-created_at')[:8]

    # Mutual friends count
    mutual_friends = Friendship.get_mutual_friends(request.user, profile_user) if not is_own_profile else []
    total_friends_count = len(Friendship.get_friend_ids(profile_user))

    # Follow counts & status
    is_following = Follow.is_following(request.user, profile_user) if not is_own_profile else False
    followers_count = profile_user.followers_set.count()
    following_count = profile_user.following_set.count()

    # Story highlights for header bar
    from stories.models import StoryHighlight
    profile_highlights = StoryHighlight.objects.filter(user=profile_user).prefetch_related('stories')[:6]

    context = {
        'profile_user': profile_user,
        'profile': profile,
        'privacy_settings': privacy_settings,
        'is_own_profile': is_own_profile,
        'can_view_content': can_view_content,
        'are_friends': are_friends,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'pending_request_sent': pending_request_sent,
        'pending_request_received': pending_request_received,
        'tab': tab,
        'subtab': subtab,
        'posts': posts,
        'friends_list': friends_list,
        'friends_hidden': friends_hidden,
        'photos': photos,
        'albums': albums,
        'videos': videos,
        'reels': reels,
        'active_stories': active_stories,
        'story_highlights': story_highlights,
        'profile_highlights': profile_highlights,
        'checkin_posts': checkin_posts,
        'liked_posts': liked_posts,
        'saved_posts': saved_posts,
        'marketplace_items': marketplace_items,
        'total_friends_count': total_friends_count,
        'mutual_friends': mutual_friends,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def update_avatar_view(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, "Profile picture updated successfully!")
    return redirect('accounts:profile', username=request.user.username)


@login_required
def update_cover_view(request):
    if request.method == 'POST' and request.FILES.get('cover_photo'):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.cover_photo = request.FILES['cover_photo']
        profile.save()
        messages.success(request, "Cover photo updated successfully!")
    return redirect('accounts:profile', username=request.user.username)


@login_required
def toggle_profile_lock_view(request):
    if request.method == 'POST':
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.is_locked = not profile.is_locked
        profile.save()
        status_str = "locked" if profile.is_locked else "unlocked"
        messages.success(request, f"Your profile is now {status_str}.")
    return redirect('accounts:profile', username=request.user.username)


@login_required
def edit_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserBasicInfoForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            # Synchronize profile_visibility to UserPrivacySetting
            privacy_setting, _ = UserPrivacySetting.objects.get_or_create(user=request.user)
            if privacy_setting.profile_visibility != profile.profile_visibility:
                privacy_setting.profile_visibility = profile.profile_visibility
                privacy_setting.save(update_fields=['profile_visibility'])
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('accounts:profile', username=request.user.username)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserBasicInfoForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
def settings_view(request):
    prefs, _ = UserPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('accounts:settings')
        else:
            messages.error(request, "Please correct the password errors.")
    else:
        password_form = PasswordChangeForm(request.user)

    blocked_users = BlockedUser.objects.filter(blocker=request.user).select_related('blocked', 'blocked__profile')

    return render(request, 'accounts/settings.html', {
        'password_form': password_form,
        'preferences': prefs,
        'blocked_users': blocked_users,
    })


@login_required
def deactivate_account_view(request):
    if request.method == 'POST':
        request.user.is_deactivated = True
        request.user.save()
        logout(request)
        messages.warning(request, "Your account has been deactivated.")
        return redirect('accounts:login')
    return render(request, 'accounts/confirm_deactivate.html')


@login_required
def toggle_block_user_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot block yourself.")
        return redirect('social:feed')

    blocked_rel = BlockedUser.objects.filter(blocker=request.user, blocked=target_user).first()
    if blocked_rel:
        blocked_rel.delete()
        messages.success(request, f"You have unblocked {target_user.get_display_name()}.")
    else:
        BlockedUser.objects.create(blocker=request.user, blocked=target_user)
        # Also remove friendships or pending requests if any
        Friendship.objects.filter(
            Q(user1=request.user, user2=target_user) | Q(user1=target_user, user2=request.user)
        ).delete()
        FriendRequest.objects.filter(
            Q(sender=request.user, receiver=target_user) | Q(sender=target_user, receiver=request.user)
        ).delete()
        # Clean up Follow relationships in both directions
        Follow.objects.filter(
            Q(follower=request.user, followed=target_user) | Q(follower=target_user, followed=request.user)
        ).delete()
        messages.info(request, f"You have blocked {target_user.get_display_name()}.")

    return redirect('accounts:settings')


@login_required
def api_toggle_theme(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            theme = data.get('theme', 'light')
            if theme in ['light', 'dark']:
                prefs, _ = UserPreference.objects.get_or_create(user=request.user)
                prefs.theme = theme
                prefs.save()
                return JsonResponse({'status': 'success', 'theme': theme})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            messages.success(request, f"Password reset instructions have been simulated for {email}. (Use settings to change password in local dev).")
        else:
            messages.error(request, "No account found with this email.")
        return render(request, 'accounts/forgot_password_done.html', {'email': email})
    return render(request, 'accounts/forgot_password.html')


@login_required
def privacy_settings_view(request):
    privacy_setting, _ = UserPrivacySetting.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserPrivacySettingForm(request.POST, instance=privacy_setting)
        if form.is_valid():
            form.save()
            # Synchronize profile_visibility to UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if profile.profile_visibility != privacy_setting.profile_visibility:
                profile.profile_visibility = privacy_setting.profile_visibility
                profile.save(update_fields=['profile_visibility'])
            messages.success(request, "Your privacy settings have been updated successfully.")
            return redirect('accounts:privacy_settings')
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = UserPrivacySettingForm(instance=privacy_setting)

    blocked_users = BlockedUser.objects.filter(blocker=request.user).select_related('blocked', 'blocked__profile')
    restricted_users = RestrictedUser.objects.filter(user=request.user).select_related('restricted_user', 'restricted_user__profile')
    muted_users = MutedUser.objects.filter(user=request.user).select_related('muted_user', 'muted_user__profile')

    return render(request, 'accounts/privacy_settings.html', {
        'form': form,
        'privacy_setting': privacy_setting,
        'blocked_users': blocked_users,
        'restricted_users': restricted_users,
        'muted_users': muted_users,
    })


@login_required
def toggle_restrict_user_view(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot restrict yourself.")
        return redirect('accounts:privacy_settings')

    rel = RestrictedUser.objects.filter(user=request.user, restricted_user=target).first()
    if rel:
        rel.delete()
        messages.success(request, f"Unrestricted {target.get_display_name()}.")
    else:
        RestrictedUser.objects.create(user=request.user, restricted_user=target)
        messages.info(request, f"Restricted {target.get_display_name()}. Their interactions with your content will be limited.")
    return redirect('accounts:privacy_settings')


@login_required
def toggle_mute_user_view(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot mute yourself.")
        return redirect('accounts:privacy_settings')

    rel = MutedUser.objects.filter(user=request.user, muted_user=target).first()
    if rel:
        rel.delete()
        messages.success(request, f"Unmuted {target.get_display_name()}.")
    else:
        MutedUser.objects.create(user=request.user, muted_user=target)
        messages.info(request, f"Muted {target.get_display_name()}. You will not receive notifications from them.")
    return redirect('accounts:privacy_settings')


@login_required
def terminate_session_view(request, session_id):
    record = get_object_or_404(UserSessionRecord, id=session_id, user=request.user)
    Session.objects.filter(session_key=record.session_key).delete()
    record.is_active = False
    record.save(update_fields=['is_active'])
    messages.success(request, "Session terminated successfully.")
    return redirect('accounts:security_settings')


@login_required
def cancel_deletion_view(request):
    latest_req = AccountDeletionRequest.objects.filter(user=request.user, status='pending').first()
    if latest_req:
        latest_req.status = 'cancelled'
        latest_req.save(update_fields=['status'])
        messages.success(request, "Your scheduled account deletion has been cancelled.")
    else:
        messages.info(request, "No pending deletion request found.")
    return redirect('accounts:your_information')


@login_required
def security_settings_view(request):
    # Ensure active session record for current session
    current_key = request.session.session_key
    if current_key:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        ua = request.META.get('HTTP_USER_AGENT', 'Browser')
        device = 'Mobile Device' if ('Mobile' in ua or 'Android' in ua or 'iPhone' in ua) else 'Desktop Computer'
        UserSessionRecord.objects.get_or_create(
            user=request.user,
            session_key=current_key,
            defaults={
                'ip_address': ip,
                'user_agent': ua[:250],
                'device_type': device,
                'is_active': True,
            }
        )

    if request.method == 'POST':
        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was successfully updated!")
                return redirect('accounts:security_settings')
            else:
                messages.error(request, "Please correct the password errors.")
        elif 'logout_other_sessions' in request.POST:
            if current_key:
                # Expire other sessions in Session store
                other_sessions = UserSessionRecord.objects.filter(user=request.user, is_active=True).exclude(session_key=current_key)
                for rec in other_sessions:
                    Session.objects.filter(session_key=rec.session_key).delete()
                other_sessions.update(is_active=False)
                messages.success(request, "All other sessions have been logged out.")
            return redirect('accounts:security_settings')
        elif 'logout_all_sessions' in request.POST:
            all_sessions = UserSessionRecord.objects.filter(user=request.user, is_active=True)
            for rec in all_sessions:
                Session.objects.filter(session_key=rec.session_key).delete()
            all_sessions.update(is_active=False)
            logout(request)
            messages.info(request, "All sessions logged out.")
            return redirect('accounts:login')
    else:
        password_form = PasswordChangeForm(request.user)

    active_sessions = UserSessionRecord.objects.filter(user=request.user, is_active=True).order_by('-last_activity')

    return render(request, 'accounts/security_settings.html', {
        'password_form': password_form,
        'active_sessions': active_sessions,
        'current_key': current_key,
    })


@login_required
def your_information_view(request):
    # JSON Data Export Request
    if request.GET.get('export') == 'json' or (request.method == 'POST' and 'export_json' in request.POST):
        friend_ids = Friendship.get_friend_ids(request.user)
        friends = User.objects.filter(id__in=friend_ids).values('id', 'username', 'first_name', 'last_name')
        
        posts = []
        for p in Post.objects.filter(author=request.user):
            m_urls = []
            for m in p.media_files.all():
                if m.file:
                    try:
                        m_urls.append(m.file.url)
                    except Exception:
                        pass
            posts.append({
                'id': p.id,
                'content': p.content,
                'privacy': p.privacy,
                'created_at': p.created_at.isoformat(),
                'reactions_count': p.reactions.count(),
                'comments_count': p.comments.count(),
                'media_files': m_urls,
            })

        comments = []
        for c in request.user.comments.all():
            comments.append({
                'id': c.id,
                'post_id': c.post_id,
                'content': c.content,
                'created_at': c.created_at.isoformat(),
            })

        user_data = {
            'account_info': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'date_joined': request.user.date_joined.isoformat(),
            },
            'profile': {
                'bio': request.user.profile.bio if hasattr(request.user, 'profile') else '',
                'city': request.user.profile.city if hasattr(request.user, 'profile') else '',
                'work': request.user.profile.work if hasattr(request.user, 'profile') else '',
            },
            'friends': list(friends),
            'posts': posts,
            'comments': comments,
            'exported_at': timezone.now().isoformat(),
            'application': 'ConnectBook Social Network',
        }

        # Log audit trail
        AuditLog.objects.create(
            actor=request.user,
            action='DATA_EXPORT_JSON',
            target_repr=f'User {request.user.username}',
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'exported_posts': len(posts), 'exported_comments': len(comments)}
        )
        DataExportRequest.objects.create(user=request.user, status='completed', download_count=1)

        response = HttpResponse(json.dumps(user_data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="connectbook_{request.user.username}_data.json"'
        return response

    # Account Deletion Request
    if request.method == 'POST' and 'request_deletion' in request.POST:
        password = request.POST.get('password', '')
        reason = request.POST.get('reason', '').strip()
        if not request.user.check_password(password):
            messages.error(request, "Incorrect password. Could not schedule account deletion.")
        else:
            scheduled_date = timezone.now() + timezone.timedelta(days=14)
            AccountDeletionRequest.objects.create(
                user=request.user,
                reason=reason,
                scheduled_deletion_date=scheduled_date,
                status='pending'
            )
            AuditLog.objects.create(
                actor=request.user,
                action='ACCOUNT_DELETION_REQUEST',
                target_repr=f'User {request.user.username}',
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'reason': reason}
            )
            messages.warning(request, f"Your account deletion request has been submitted. It is scheduled for deletion on {scheduled_date.strftime('%B %d, %Y')}. You can cancel this anytime before then.")
            return redirect('accounts:your_information')

    # Cancel Account Deletion
    if request.method == 'POST' and 'cancel_deletion' in request.POST:
        pending_del = AccountDeletionRequest.objects.filter(user=request.user, status='pending').first()
        if pending_del:
            pending_del.status = 'cancelled'
            pending_del.save()
            messages.success(request, "Your scheduled account deletion has been cancelled.")
            return redirect('accounts:your_information')

    # Information overview stats
    stats = {
        'posts_count': request.user.posts.count(),
        'comments_count': request.user.comments.count(),
        'reactions_count': request.user.reactions.count(),
        'friends_count': len(Friendship.get_friend_ids(request.user)),
        'followers_count': request.user.followers_set.count(),
        'following_count': request.user.following_set.count(),
    }
    deletion_request = AccountDeletionRequest.objects.filter(user=request.user, status='pending').first()
    recent_exports = DataExportRequest.objects.filter(user=request.user)[:5]

    return render(request, 'accounts/your_information.html', {
        'stats': stats,
        'deletion_request': deletion_request,
        'recent_exports': recent_exports,
    })


@login_required
def toggle_follow_view(request, username):
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'status': 'error', 'message': 'You cannot follow yourself.'}, status=400)
        messages.error(request, "You cannot follow yourself.")
        return redirect('accounts:profile', username=username)

    # Check if blocked in either direction
    is_blocked = BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=target_user) | Q(blocker=target_user, blocked=request.user)
    ).exists()
    if is_blocked:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'status': 'error', 'message': 'Cannot follow a blocked user.'}, status=403)
        messages.error(request, "Cannot follow a blocked user.")
        return redirect('social:feed')

    follow_rel = Follow.objects.filter(follower=request.user, followed=target_user).first()
    if follow_rel:
        follow_rel.delete()
        is_following = False
        msg = f"You unfollowed {target_user.get_display_name()}."
    else:
        Follow.objects.create(follower=request.user, followed=target_user)
        is_following = True
        msg = f"You are now following {target_user.get_display_name()}."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'ok',
            'is_following': is_following,
            'followers_count': target_user.followers_set.count(),
            'message': msg
        })

    messages.info(request, msg)
    return redirect('accounts:profile', username=username)


@login_required
def followers_list_view(request, username):
    profile_user = get_object_or_404(User, username=username)

    # Blocked check
    is_blocked = BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=profile_user) | Q(blocker=profile_user, blocked=request.user)
    ).exists()
    if is_blocked and profile_user != request.user:
        return render(request, 'accounts/blocked_profile.html', {'profile_user': profile_user})

    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    is_own_profile = (request.user == profile_user)
    are_friends = Friendship.are_friends(request.user, profile_user)

    vis = getattr(profile, 'followers_visibility', 'public')
    if (vis == 'private' and not is_own_profile) or (vis == 'friends' and not (is_own_profile or are_friends)):
        followers = User.objects.none()
        is_hidden = True
    elif profile.is_locked and not (is_own_profile or are_friends):
        followers = User.objects.none()
        is_hidden = True
    else:
        followers = User.objects.filter(following_set__followed=profile_user, is_active=True, is_deactivated=False).select_related('profile')
        is_hidden = False

    return render(request, 'accounts/follow_list.html', {
        'profile_user': profile_user,
        'user_list': followers,
        'list_type': 'Followers',
        'is_hidden': is_hidden,
    })


@login_required
def following_list_view(request, username):
    profile_user = get_object_or_404(User, username=username)

    # Blocked check
    is_blocked = BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=profile_user) | Q(blocker=profile_user, blocked=request.user)
    ).exists()
    if is_blocked and profile_user != request.user:
        return render(request, 'accounts/blocked_profile.html', {'profile_user': profile_user})

    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    is_own_profile = (request.user == profile_user)
    are_friends = Friendship.are_friends(request.user, profile_user)

    vis = getattr(profile, 'followers_visibility', 'public')
    if (vis == 'private' and not is_own_profile) or (vis == 'friends' and not (is_own_profile or are_friends)):
        following = User.objects.none()
        is_hidden = True
    elif profile.is_locked and not (is_own_profile or are_friends):
        following = User.objects.none()
        is_hidden = True
    else:
        following = User.objects.filter(followers_set__follower=profile_user, is_active=True, is_deactivated=False).select_related('profile')
        is_hidden = False

    return render(request, 'accounts/follow_list.html', {
        'profile_user': profile_user,
        'user_list': following,
        'list_type': 'Following',
        'is_hidden': is_hidden,
    })
