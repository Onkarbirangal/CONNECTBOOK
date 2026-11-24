import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import (
    Post, PostMedia, Reaction, Comment, SavedPost, Hashtag, Report, AuditLog,
    Video, VideoView, VideoReaction, VideoComment, SavedVideo,
    Reel, ReelReaction, ReelComment, SavedReel, ReelView,
    Poll, PollOption, PollVote,
    PhotoAlbum, AlbumPhoto
)
from friends.models import Friendship
from stories.models import Story
from groups_app.models import Group, GroupMembership
from notifications.services import send_notification

User = get_user_model()


@login_required
def feed_view(request):
    tab = request.GET.get('tab', 'for_you')

    # 1. Fetch friend IDs
    friend_ids = Friendship.get_friend_ids(request.user)

    # 2. Blocked users
    from accounts.models import BlockedUser, Follow
    blocked_by_me = BlockedUser.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_me = BlockedUser.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    excluded_user_ids = set(list(blocked_by_me) + list(blocked_me))

    # 3. Following IDs & joined groups/pages
    following_user_ids = set(Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True))
    joined_group_ids = GroupMembership.objects.filter(user=request.user).values_list('group_id', flat=True)
    from pages_app.models import PageFollow
    followed_page_ids = set(PageFollow.objects.filter(user=request.user).values_list('page_id', flat=True))

    base_qs = Post.objects.exclude(author_id__in=excluded_user_ids).filter(is_trashed=False)

    if tab == 'friends':
        posts_qs = base_qs.filter(
            (Q(author_id__in=friend_ids) & (Q(privacy='public') | Q(privacy='friends'))) | Q(author=request.user),
            status='published', is_archived=False
        ).order_by('-created_at')
    elif tab == 'following':
        posts_qs = base_qs.filter(
            (Q(author_id__in=following_user_ids) | Q(page_id__in=followed_page_ids) | Q(author=request.user)),
            status='published', is_archived=False, privacy='public'
        ).order_by('-created_at')
    elif tab == 'latest':
        feed_filter = (
            Q(author=request.user) |
            (Q(author_id__in=friend_ids) & Q(privacy__in=['public', 'friends'])) |
            Q(privacy='public') |
            Q(group_id__in=joined_group_ids) |
            Q(page_id__in=followed_page_ids)
        )
        posts_qs = base_qs.filter(feed_filter, status='published', is_archived=False).order_by('-created_at')
    elif tab == 'trending':
        since = timezone.now() - timedelta(days=3)
        feed_filter = (
            Q(author=request.user) |
            (Q(author_id__in=friend_ids) & Q(privacy__in=['public', 'friends'])) |
            Q(privacy='public') |
            Q(group_id__in=joined_group_ids) |
            Q(page_id__in=followed_page_ids)
        )
        posts_qs = base_qs.filter(feed_filter, created_at__gte=since, status='published', is_archived=False)
    elif tab == 'drafts':
        posts_qs = base_qs.filter(author=request.user, status='draft').order_by('-created_at')
    elif tab == 'archived':
        posts_qs = base_qs.filter(author=request.user, is_archived=True).order_by('-created_at')
    else:  # for_you
        feed_filter = (
            Q(author=request.user) |
            (Q(author_id__in=friend_ids) & Q(privacy__in=['public', 'friends'])) |
            Q(privacy='public') |
            Q(group_id__in=joined_group_ids) |
            Q(page_id__in=followed_page_ids)
        )
        posts_qs = base_qs.filter(feed_filter, status='published', is_archived=False)

    posts_qs = posts_qs.select_related(
        'author', 'author__profile', 'group', 'page', 'original_post', 'original_post__author', 'original_post__author__profile'
    ).prefetch_related(
        'media_files', 'reactions', 'comments', 'comments__author', 'comments__author__profile', 'comments__replies'
    ).distinct()

    # Filter by individual can_view
    raw_posts = [p for p in posts_qs if p.can_view(request.user)]

    # Dynamic ranking algorithm for 'for_you' and 'trending'
    now = timezone.now()
    if tab == 'for_you':
        def calc_score(p):
            age_hours = max((now - p.created_at).total_seconds() / 3600.0, 0.05)
            # High priority boost for author's own freshly created posts
            is_self = 80 if p.author_id == request.user.id else 0
            is_friend = 30 if p.author_id in friend_ids else 0
            is_follow = 20 if p.author_id in following_user_ids or p.page_id in followed_page_ids else 0
            recency_bonus = max(100 - (age_hours * 5), 0)
            interactions = (p.reactions.count() * 2) + (p.comments.count() * 3)
            return (p.is_pinned * 1000) + is_self + is_friend + is_follow + recency_bonus + interactions
        raw_posts.sort(key=calc_score, reverse=True)
    elif tab == 'trending':
        raw_posts.sort(key=lambda p: (p.reactions.count() * 2) + (p.comments.count() * 3), reverse=True)
    elif tab not in ['latest', 'drafts', 'archived']:
        raw_posts.sort(key=lambda p: (p.is_pinned, p.created_at), reverse=True)

    posts = raw_posts[:30]

    # Non-blocking view counter update
    p_ids_to_increment = [p.id for p in posts]
    if p_ids_to_increment:
        from django.db.models import F
        Post.objects.filter(id__in=p_ids_to_increment).update(views_count=F('views_count') + 1)

    # 5. Active Stories (24h) from self and friends
    story_author_ids = [request.user.id] + list(friend_ids)
    active_stories = Story.objects.filter(
        author_id__in=story_author_ids,
        expires_at__gt=timezone.now()
    ).select_related('author', 'author__profile').order_by('-created_at')

    # Group stories by author for carousel display
    grouped_stories = {}
    for st in active_stories:
        if st.author_id not in grouped_stories:
            grouped_stories[st.author_id] = {
                'author': st.author,
                'latest_story': st,
                'count': 0
            }
        grouped_stories[st.author_id]['count'] += 1

    # 6. Friend suggestions (users who are not friends, not blocked, not self)
    suggested_friends = User.objects.exclude(
        id=request.user.id
    ).exclude(
        id__in=friend_ids
    ).exclude(
        id__in=excluded_user_ids
    ).filter(
        is_active=True, is_deactivated=False
    ).select_related('profile')[:5]

    # 7. Contacts (friends) for chat sidebar
    contacts_list = User.objects.filter(
        id__in=friend_ids, is_active=True, is_deactivated=False
    ).select_related('profile')[:12]

    # 8. Birthdays: Friends whose birthday is today
    today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()
    birthday_friends = User.objects.filter(
        id__in=friend_ids,
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
        is_active=True, is_deactivated=False
    ).select_related('profile')

    # 9. Suggested Groups (groups user hasn't joined)
    suggested_groups = Group.objects.exclude(
        memberships__user=request.user
    ).order_by('-created_at')[:3]

    # 10. Suggested Pages (pages user doesn't follow)
    from pages_app.models import Page
    suggested_pages = Page.objects.exclude(
        followers__user=request.user
    ).exclude(
        owner=request.user
    ).order_by('-created_at')[:3]

    context = {
        'active_nav': 'feed',
        'tab': tab,
        'active_tab': tab,
        'posts': posts,
        'stories_list': list(grouped_stories.values()),
        'suggested_friends': suggested_friends,
        'contacts_list': contacts_list,
        'birthday_friends': birthday_friends,
        'suggested_groups': suggested_groups,
        'suggested_pages': suggested_pages,
    }
    return render(request, 'social/feed.html', context)


@login_required
def post_detail_view(request, post_id):
    """
    Renders a single post permalink page with full reactions, comments, and media.
    Enforces can_view privacy permissions.
    """
    post = get_object_or_404(
        Post.objects.select_related(
            'author', 'author__profile', 'group', 'page', 'original_post', 'original_post__author'
        ).prefetch_related(
            'media_files', 'reactions', 'comments', 'comments__author', 'comments__author__profile', 'comments__replies'
        ),
        pk=post_id
    )

    if not post.can_view(request.user):
        return render(request, 'social/post_forbidden.html', {'post': post}, status=403)

    from django.db.models import F
    Post.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
    post.views_count += 1

    return render(request, 'social/post_detail.html', {
        'post': post,
        'active_nav': 'feed',
    })


@login_required
def reel_detail_view(request, reel_id):
    """
    Renders a single reel permalink page with video player, comments, and interactions.
    """
    reel = get_object_or_404(
        Reel.objects.select_related('author', 'author__profile').prefetch_related(
            'reactions', 'comments', 'comments__author', 'comments__author__profile'
        ),
        pk=reel_id
    )

    from django.db.models import F
    Reel.objects.filter(pk=reel.pk).update(views_count=F('views_count') + 1)
    reel.views_count += 1

    user_liked = reel.reactions.filter(user=request.user).exists()
    user_saved = SavedReel.objects.filter(user=request.user, reel=reel).exists()

    from accounts.models import Follow
    is_following = Follow.objects.filter(follower=request.user, followed=reel.author).exists()

    return render(request, 'social/reel_detail.html', {
        'reel': reel,
        'user_liked': user_liked,
        'user_saved': user_saved,
        'is_following': is_following,
        'active_nav': 'videos',
    })


@login_required
def create_post_view(request):
    import os
    import re
    from accounts.models import BlockedUser

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        privacy = request.POST.get('privacy', 'public')
        status = request.POST.get('status', 'published')
        if status not in ['published', 'draft', 'scheduled']:
            status = 'published'

        post_type = request.POST.get('post_type', '').strip()
        background_style = request.POST.get('background_style', 'none').strip()
        feeling_category = request.POST.get('feeling_category', '').strip()
        feeling_text = request.POST.get('feeling_text', '').strip()
        feeling_icon = request.POST.get('feeling_icon', '').strip()
        location_name = request.POST.get('location_name', '').strip()
        location_address = request.POST.get('location_address', '').strip()
        link_url = request.POST.get('link_url', '').strip()
        link_title = request.POST.get('link_title', '').strip()
        link_description = request.POST.get('link_description', '').strip()
        link_image = request.POST.get('link_image', '').strip()
        milestone_title = request.POST.get('milestone_title', '').strip()

        comments_enabled = request.POST.get('comments_enabled', '1') in ['1', 'true', 'on']
        allow_sharing = request.POST.get('allow_sharing', '1') in ['1', 'true', 'on']
        group_id = request.POST.get('group_id')

        # Scheduled post datetime
        scheduled_at_obj = None
        scheduled_raw = request.POST.get('scheduled_at')
        if status == 'scheduled' and scheduled_raw:
            try:
                from datetime import datetime
                scheduled_at_obj = datetime.fromisoformat(scheduled_raw)
                if timezone.is_naive(scheduled_at_obj):
                    scheduled_at_obj = timezone.make_aware(scheduled_at_obj)
            except Exception:
                scheduled_at_obj = timezone.now() + timedelta(days=1)

        group = None
        if group_id:
            group = get_object_or_404(Group, id=group_id)
            if not group.is_member(request.user):
                return HttpResponseForbidden("You must be a member to post in this group.")

        files = request.FILES.getlist('media')
        poll_question = request.POST.get('poll_question', '').strip()

        if not content and not files and not poll_question and not link_url and not milestone_title:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Post cannot be empty.'}, status=400)
            messages.error(request, "Post cannot be empty.")
            return redirect('social:feed')

        # Strict media validation
        ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.webm', '.avi')
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f"Unsupported format '{ext}'."}, status=400)
                messages.error(request, f"Unsupported file format '{ext}'.")
                return redirect('social:feed')
            limit = 52428800 if f.content_type.startswith('video') else 10485760
            if f.size > limit:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f"File {f.name} exceeds upload limit."}, status=400)
                messages.error(request, f"File {f.name} exceeds the maximum upload limit.")
                return redirect('social:feed')

        # Auto-determine post_type if not explicitly set
        if not post_type:
            if files:
                has_video = any(f.content_type.startswith('video') for f in files)
                post_type = 'video' if has_video else 'photo'
            elif poll_question:
                post_type = 'poll'
            elif link_url:
                post_type = 'link'
            elif milestone_title:
                post_type = 'milestone'
            elif feeling_text:
                post_type = 'feeling'
            elif location_name:
                post_type = 'location'
            else:
                post_type = 'text'

        # Background style only allowed for media-free posts
        if files or poll_question:
            background_style = 'none'

        post = Post.objects.create(
            author=request.user,
            content=content,
            post_type=post_type,
            privacy=privacy,
            status=status,
            scheduled_at=scheduled_at_obj,
            comments_enabled=comments_enabled,
            allow_sharing=allow_sharing,
            background_style=background_style,
            feeling_category=feeling_category,
            feeling_text=feeling_text,
            feeling_icon=feeling_icon,
            location_name=location_name,
            location_address=location_address,
            link_url=link_url,
            link_title=link_title,
            link_description=link_description,
            link_image=link_image,
            milestone_title=milestone_title,
            group=group
        )

        # Handle tagged users
        tagged_ids = request.POST.getlist('tagged_user_ids[]')
        if not tagged_ids and request.POST.get('tagged_user_ids'):
            tagged_ids = [x.strip() for x in request.POST.get('tagged_user_ids').split(',') if x.strip()]
        if tagged_ids:
            blocked_ids = BlockedUser.objects.filter(
                Q(blocker=request.user) | Q(blocked=request.user)
            ).values_list('blocked_id', 'blocker_id')
            flat_blocked = set()
            for b1, b2 in blocked_ids:
                flat_blocked.add(b1)
                flat_blocked.add(b2)
            valid_tagged = User.objects.filter(id__in=tagged_ids).exclude(id=request.user.id).exclude(id__in=flat_blocked)
            post.tagged_users.set(valid_tagged)
            for tu in valid_tagged:
                try:
                    send_notification(
                        recipient=tu,
                        actor=request.user,
                        notification_type='tag',
                        title='Tagged in a Post',
                        message=f"{request.user.get_display_name()} tagged you in a post.",
                        target_url=f"/#post-{post.id}"
                    )
                except Exception:
                    pass

        # Handle custom audience allow/deny
        allow_ids = request.POST.getlist('allow_user_ids[]')
        if not allow_ids and request.POST.get('allow_user_ids'):
            allow_ids = [x.strip() for x in request.POST.get('allow_user_ids').split(',') if x.strip()]
        if allow_ids:
            post.custom_audience_allow.set(User.objects.filter(id__in=allow_ids))

        deny_ids = request.POST.getlist('deny_user_ids[]')
        if not deny_ids and request.POST.get('deny_user_ids'):
            deny_ids = [x.strip() for x in request.POST.get('deny_user_ids').split(',') if x.strip()]
        if deny_ids:
            post.custom_audience_deny.set(User.objects.filter(id__in=deny_ids))

        # Handle @mentions in post content
        mention_names = set(re.findall(r'@(\w+)', content))
        if mention_names:
            mentioned = User.objects.filter(username__in=mention_names).exclude(id=request.user.id)
            for mu in mentioned:
                try:
                    send_notification(
                        recipient=mu,
                        actor=request.user,
                        notification_type='mention',
                        title='Mentioned in a Post',
                        message=f"{request.user.get_display_name()} mentioned you in a post.",
                        target_url=f"/#post-{post.id}"
                    )
                except Exception:
                    pass

        # Handle hashtags in content
        words = content.split()
        for word in words:
            if word.startswith('#') and len(word) > 1:
                clean_tag = word[1:].strip('.,!?:;"\'()[]{}').lower()
                if clean_tag:
                    ht, _ = Hashtag.objects.get_or_create(name=clean_tag)
                    ht.posts.add(post)

        # Handle multiple uploaded media files with captions and alt text
        captions = request.POST.getlist('media_captions[]')
        alt_texts = request.POST.getlist('media_alt_text[]')
        for idx, file in enumerate(files):
            m_type = 'video' if file.content_type.startswith('video') else 'image'
            cap = captions[idx] if idx < len(captions) else ''
            alt = alt_texts[idx] if idx < len(alt_texts) else ''
            PostMedia.objects.create(
                post=post,
                file=file,
                media_type=m_type,
                caption=cap,
                alt_text=alt,
                order=idx
            )

        # Handle attached Poll
        if poll_question:
            try:
                poll_days = int(request.POST.get('poll_expiration_days', 7))
            except (ValueError, TypeError):
                poll_days = 7
            exp_date = timezone.now() + timedelta(days=poll_days) if poll_days > 0 else None
            poll = Poll.objects.create(
                post=post,
                question=poll_question,
                expires_at=exp_date
            )
            raw_options = request.POST.getlist('poll_options[]')
            if not raw_options:
                raw_options = [
                    request.POST.get('poll_option_1', '').strip(),
                    request.POST.get('poll_option_2', '').strip(),
                    request.POST.get('poll_option_3', '').strip(),
                    request.POST.get('poll_option_4', '').strip(),
                ]
            valid_opts = [opt.strip() for opt in raw_options if opt and opt.strip()]
            for idx, opt_text in enumerate(valid_opts):
                PollOption.objects.create(poll=poll, text=opt_text, order=idx)

        next_target = request.POST.get('next') or request.META.get('HTTP_REFERER')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            target = next_target or '/'
            return JsonResponse({'status': 'success', 'post_id': post.id, 'redirect_url': target})

        if status == 'draft':
            messages.info(request, "Your post has been saved as a draft.")
            return redirect('/?tab=drafts')
        elif status == 'scheduled':
            messages.info(request, f"Your post has been scheduled for {post.scheduled_at.strftime('%b %d, %Y %I:%M %p')}.")
            return redirect('social:my_posts')
        else:
            messages.success(request, "Your post was published!")

        if group:
            return redirect('groups_app:detail', slug=group.slug)

        if next_target and any(x in next_target for x in ['/profile/', '/groups/', '/my-posts/']):
            return redirect(next_target)

        return redirect('social:feed')

    return redirect('social:feed')


@login_required
def edit_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You can only edit your own posts.")

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        privacy = request.POST.get('privacy', post.privacy)
        if 'comments_enabled' in request.POST:
            post.comments_enabled = request.POST.get('comments_enabled') in ['on', 'true', '1']

        # Record edit history if content changed
        if post.content != content:
            if not isinstance(post.edit_history, list):
                post.edit_history = []
            post.edit_history.append({
                'previous_content': post.content,
                'edited_at': timezone.now().isoformat()
            })
            post.is_edited = True

        post.content = content
        post.privacy = privacy
        post.save()
        messages.success(request, "Post updated successfully.")
        return redirect('social:feed')

    return render(request, 'social/edit_post.html', {'post': post})


@login_required
def toggle_archive_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized.")

    post.is_archived = not post.is_archived
    post.save()
    msg = "Post archived." if post.is_archived else "Post unarchived and restored to feed."
    messages.info(request, msg)
    return redirect('social:feed')


@login_required
def toggle_pin_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized.")

    post.is_pinned = not post.is_pinned
    post.save()
    msg = "Post pinned to top." if post.is_pinned else "Post unpinned."
    messages.info(request, msg)
    return redirect('social:feed')


@login_required
def toggle_comments_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized.")

    post.comments_enabled = not post.comments_enabled
    post.save()
    msg = "Comments enabled." if post.comments_enabled else "Comments disabled for this post."
    messages.info(request, msg)
    return redirect('social:feed')


@login_required
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You are not allowed to delete this post.")

    post.delete()
    messages.info(request, "Post deleted.")
    return redirect('social:feed')


@login_required
def share_post_view(request, post_id):
    original = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        share_content = request.POST.get('content', '').strip()
        shared_post = Post.objects.create(
            author=request.user,
            content=share_content,
            privacy='public',
            original_post=original
        )

        send_notification(
            recipient=original.author,
            actor=request.user,
            notification_type='post_reaction',
            title='Post Shared',
            message=f"{request.user.get_display_name()} shared your post.",
            target_url=f"/#post-{shared_post.id}"
        )

        messages.success(request, "Post shared to your timeline!")
        return redirect('social:feed')

    return render(request, 'social/share_post.html', {'original_post': original})


@login_required
def react_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            r_type = data.get('reaction_type', 'like')
        except Exception:
            r_type = request.POST.get('reaction_type', 'like')

        existing = Reaction.objects.filter(user=request.user, post=post).first()

        if r_type == 'none' or (existing and existing.reaction_type == r_type and 'none' in request.body.decode('utf-8', errors='ignore')):
            if existing:
                existing.delete()
                current_reaction = None
        elif existing:
            existing.reaction_type = r_type
            existing.save()
            current_reaction = r_type
        else:
            Reaction.objects.create(user=request.user, post=post, reaction_type=r_type)
            current_reaction = r_type

            # Notify author
            if post.author != request.user:
                send_notification(
                    recipient=post.author,
                    actor=request.user,
                    notification_type='post_reaction',
                    title='New Reaction',
                    message=f"{request.user.get_display_name()} reacted to your post.",
                    target_url=f"/#post-{post.id}"
                )

        return JsonResponse({
            'status': 'success',
            'user_reaction': current_reaction,
            'total_reactions': post.reactions.count(),
            'reaction_counts': post.reaction_counts
        })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def add_comment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if not post.comments_enabled:
        messages.error(request, "Comments have been disabled for this post.")
        return redirect(f"/#post-{post.id}")

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')

        if not content:
            messages.error(request, "Comment cannot be empty.")
            return redirect('social:feed')

        parent_comment = None
        if parent_id:
            parent_comment = Comment.objects.filter(id=parent_id, post=post).first()

        comment = Comment.objects.create(
            post=post,
            author=request.user,
            content=content,
            parent=parent_comment
        )

        # Notify post author or parent comment author
        notify_user = parent_comment.author if parent_comment else post.author
        if notify_user != request.user:
            notif_type = 'comment_reply' if parent_comment else 'post_comment'
            msg = f"{request.user.get_display_name()} replied to your comment." if parent_comment else f"{request.user.get_display_name()} commented on your post."
            send_notification(
                recipient=notify_user,
                actor=request.user,
                notification_type=notif_type,
                title='New Comment',
                message=msg,
                target_url=f"/#post-{post.id}"
            )

        messages.success(request, "Comment posted.")
        return redirect(f"/#post-{post.id}")

    return redirect('social:feed')


@login_required
def delete_comment_view(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    post_id = comment.post_id
    if comment.author != request.user and comment.post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Not authorized to delete this comment.")

    comment.delete()
    messages.info(request, "Comment removed.")
    return redirect(f"/#post-{post_id}")


@login_required
def toggle_save_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    collection_name = request.POST.get('collection_name', request.GET.get('collection', 'All Posts')).strip() or 'All Posts'
    saved = SavedPost.objects.filter(user=request.user, post=post).first()
    if saved:
        saved.delete()
        messages.info(request, "Post removed from your saved items.")
    else:
        SavedPost.objects.create(user=request.user, post=post, collection_name=collection_name)
        messages.success(request, f"Post saved to '{collection_name}' collection.")
    return redirect(f"/#post-{post.id}")


@login_required
def saved_posts_view(request):
    current_collection = request.GET.get('collection', 'All Posts')
    user_saved = SavedPost.objects.filter(user=request.user)

    # Distinct collections
    collections = list(user_saved.values_list('collection_name', flat=True).distinct())
    if 'All Posts' not in collections:
        collections.insert(0, 'All Posts')

    if current_collection != 'All Posts':
        saved_items = user_saved.filter(collection_name=current_collection)
    else:
        saved_items = user_saved

    saved_items = saved_items.select_related(
        'post', 'post__author', 'post__author__profile'
    ).prefetch_related('post__media_files', 'post__reactions', 'post__comments')

    return render(request, 'social/saved_posts.html', {
        'active_nav': 'saved',
        'saved_items': saved_items,
        'current_collection': current_collection,
        'collections': collections,
    })


@login_required
def memories_view(request):
    # Historical posts on this same calendar month/day in previous years
    today = timezone.now().date()
    memories = Post.objects.filter(
        author=request.user,
        created_at__month=today.month,
        created_at__day=today.day,
        created_at__year__lt=today.year
    ).order_by('-created_at')

    return render(request, 'social/memories.html', {
        'active_nav': 'memories',
        'memories': memories,
        'today': today,
    })


@login_required
def vote_poll_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    poll = getattr(post, 'poll', None)
    if not poll:
        messages.error(request, "This post does not contain a poll.")
        return redirect('social:feed')

    if poll.is_expired:
        messages.error(request, "This poll has expired.")
        return redirect('social:feed')

    if request.method == 'POST':
        option_id = request.POST.get('option_id')
        option = get_object_or_404(PollOption, id=option_id, poll=poll)

        existing_vote = PollVote.objects.filter(poll=poll, user=request.user).first()
        if existing_vote:
            if existing_vote.option == option:
                messages.info(request, "You already voted for this option.")
            else:
                existing_vote.option = option
                existing_vote.save(update_fields=['option'])
                messages.success(request, f"Your vote was changed to '{option.text}'.")
        else:
            PollVote.objects.create(poll=poll, option=option, user=request.user)
            messages.success(request, f"Your vote for '{option.text}' was recorded.")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            results = [{
                'id': opt.id,
                'text': opt.text,
                'votes': opt.votes_count,
                'percentage': opt.percentage
            } for opt in poll.options.all()]
            return JsonResponse({'status': 'ok', 'total_votes': poll.total_votes, 'options': results})

    return redirect(f"/#post-{post.id}")


# ========================================================
# V4: REAL VIDEO POST VIEWS
# ========================================================

@login_required
def video_feed_view(request):
    category = request.GET.get('category', '').strip()
    query = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'for_you')

    videos = Video.objects.select_related('author', 'author__profile').prefetch_related('reactions', 'comments')

    if tab == 'my_videos':
        videos = videos.filter(author=request.user)
    elif tab == 'saved':
        videos = videos.filter(saved_by__user=request.user)
    elif tab == 'trending':
        videos = videos.filter(privacy='public').order_by('-views_count', '-created_at')
    else:
        # For You / Public + Friends
        videos = videos.filter(Q(privacy='public') | Q(author=request.user)).order_by('-created_at')

    if category:
        videos = videos.filter(category=category)

    if query:
        videos = videos.filter(Q(title__icontains=query) | Q(description__icontains=query))

    categories = Video.CATEGORY_CHOICES
    saved_video_ids = set(SavedVideo.objects.filter(user=request.user).values_list('video_id', flat=True))

    return render(request, 'social/video_feed.html', {
        'active_nav': 'videos',
        'videos': videos[:50],
        'categories': categories,
        'selected_category': category,
        'query': query,
        'tab': tab,
        'saved_video_ids': saved_video_ids,
    })


@login_required
def video_detail_view(request, video_id):
    video = get_object_or_404(Video.objects.select_related('author', 'author__profile'), id=video_id)

    if not video.can_view(request.user):
        return HttpResponseForbidden("You do not have permission to view this video.")

    # Deduplicated view count increment (once per 10 minutes per IP/user)
    ip = request.META.get('REMOTE_ADDR')
    ten_min_ago = timezone.now() - timedelta(minutes=10)
    recent_view = VideoView.objects.filter(
        video=video,
        viewed_at__gte=ten_min_ago
    ).filter(Q(viewer=request.user) | Q(ip_address=ip)).exists()

    if not recent_view:
        VideoView.objects.create(video=video, viewer=request.user, ip_address=ip)
        video.views_count += 1
        video.save(update_fields=['views_count'])

    comments = video.comments.filter(parent__isnull=True).select_related('author', 'author__profile').prefetch_related('replies', 'replies__author', 'replies__author__profile')
    is_saved = SavedVideo.objects.filter(user=request.user, video=video).exists()
    has_reacted = VideoReaction.objects.filter(user=request.user, video=video).exists()
    related_videos = Video.objects.filter(category=video.category).exclude(id=video.id).select_related('author', 'author__profile')[:8]

    return render(request, 'social/video_detail.html', {
        'video': video,
        'comments': comments,
        'is_saved': is_saved,
        'has_reacted': has_reacted,
        'related_videos': related_videos,
        'active_nav': 'videos',
    })


@login_required
def upload_video_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'entertainment')
        privacy = request.POST.get('privacy', 'public')
        video_file = request.FILES.get('video_file')
        thumbnail = request.FILES.get('thumbnail')

        if not title:
            messages.error(request, "Video title is required.")
            return render(request, 'social/video_upload.html', {'categories': Video.CATEGORY_CHOICES})

        if not video_file:
            messages.error(request, "Please select a video file to upload.")
            return render(request, 'social/video_upload.html', {'categories': Video.CATEGORY_CHOICES})

        # Validate video format
        ext = os.path.splitext(video_file.name)[1].lower()
        if ext not in ['.mp4', '.webm', '.mov', '.m4v']:
            messages.error(request, f"Unsupported video format '{ext}'. Please upload an MP4, WebM, or MOV file.")
            return render(request, 'social/video_upload.html', {'categories': Video.CATEGORY_CHOICES})

        # Max 50MB
        if video_file.size > 52428800:
            messages.error(request, "Video file size exceeds maximum limit of 50MB.")
            return render(request, 'social/video_upload.html', {'categories': Video.CATEGORY_CHOICES})

        video = Video.objects.create(
            author=request.user,
            title=title,
            description=description,
            category=category,
            privacy=privacy,
            video_file=video_file,
            thumbnail=thumbnail,
            file_size_bytes=video_file.size,
            processing_status='ready'
        )

        AuditLog.objects.create(
            actor=request.user,
            action='VIDEO_UPLOAD',
            target_repr=f"Video: {video.title}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'video_id': video.id, 'category': video.category, 'size': video.file_size_bytes}
        )

        messages.success(request, f"Your video '{video.title}' is now live on ConnectBook Watch!")
        return redirect('social:video_detail', video_id=video.id)

    return render(request, 'social/video_upload.html', {'categories': Video.CATEGORY_CHOICES})


@login_required
def edit_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if not video.can_manage(request.user):
        return HttpResponseForbidden("Unauthorized to edit this video.")

    if request.method == 'POST':
        video.title = request.POST.get('title', video.title).strip()
        video.description = request.POST.get('description', video.description).strip()
        video.category = request.POST.get('category', video.category)
        video.privacy = request.POST.get('privacy', video.privacy)
        new_thumb = request.FILES.get('thumbnail')
        if new_thumb:
            video.thumbnail = new_thumb
        video.save()
        messages.success(request, "Video details updated successfully.")
        return redirect('social:video_detail', video_id=video.id)

    return render(request, 'social/video_edit.html', {'video': video, 'categories': Video.CATEGORY_CHOICES})


@login_required
def delete_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if not video.can_manage(request.user):
        return HttpResponseForbidden("Unauthorized to delete this video.")

    if request.method == 'POST':
        title = video.title
        video.delete()
        messages.info(request, f"Video '{title}' has been deleted.")
        return redirect('social:video_feed')
    return redirect('social:video_detail', video_id=video.id)


@login_required
def react_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    reaction = VideoReaction.objects.filter(video=video, user=request.user).first()
    if reaction:
        reaction.delete()
        status = 'unliked'
    else:
        VideoReaction.objects.create(video=video, user=request.user, reaction_type='like')
        status = 'liked'

        # Notify video creator
        if video.author != request.user:
            send_notification(
                recipient=video.author,
                actor=request.user,
                notification_type='post_reaction',
                title='Video Liked',
                message=f"{request.user.get_display_name()} liked your video '{video.title[:30]}'.",
                target_url=f"/videos/{video.id}/",
                category='social'
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': status, 'likes_count': video.likes_count})
    return redirect('social:video_detail', video_id=video.id)


@login_required
def add_video_comment_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')
        if content:
            parent = VideoComment.objects.filter(id=parent_id, video=video).first() if parent_id else None
            VideoComment.objects.create(video=video, author=request.user, content=content, parent=parent)
            if video.author != request.user:
                send_notification(
                    recipient=video.author,
                    actor=request.user,
                    notification_type='post_comment',
                    title='New Video Comment',
                    message=f"{request.user.get_display_name()} commented on your video.",
                    target_url=f"/videos/{video.id}/",
                    category='social'
                )
            messages.success(request, "Comment posted.")
    return redirect('social:video_detail', video_id=video.id)


@login_required
def toggle_save_video_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    saved = SavedVideo.objects.filter(user=request.user, video=video).first()
    if saved:
        saved.delete()
        messages.info(request, "Video removed from your saved videos.")
    else:
        SavedVideo.objects.create(user=request.user, video=video)
        messages.success(request, "Video saved to your library.")
    return redirect(request.META.get('HTTP_REFERER', f"/videos/{video.id}/"))


# ========================================================
# V4: REELS / SHORT VIDEO VIEWS
# ========================================================

@login_required
def reels_feed_view(request):
    tab = request.GET.get('tab', 'for_you')
    from accounts.models import Follow
    following_ids = set(Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True))

    reels_qs = Reel.objects.filter(status='published').select_related(
        'author', 'author__profile'
    ).prefetch_related('reactions', 'comments', 'comments__author', 'comments__author__profile')

    if tab == 'following':
        reels_qs = reels_qs.filter(author_id__in=following_ids).order_by('-created_at')
    elif tab == 'trending':
        reels_qs = reels_qs.filter(privacy='public').order_by('-views_count', '-created_at')
    elif tab == 'latest':
        reels_qs = reels_qs.order_by('-created_at')
    elif tab == 'popular':
        reels_qs = reels_qs.annotate(likes_cnt=Count('reactions')).order_by('-likes_cnt', '-views_count')
    elif tab == 'saved':
        reels_qs = reels_qs.filter(saved_by__user=request.user).order_by('-created_at')
    else:  # for_you
        reels_qs = reels_qs.order_by('-created_at')

    # Object-level permission filter
    reels = [r for r in reels_qs if r.can_view(request.user)][:50]

    saved_reel_ids = set(SavedReel.objects.filter(user=request.user).values_list('reel_id', flat=True))
    liked_reel_ids = set(ReelReaction.objects.filter(user=request.user).values_list('reel_id', flat=True))

    # Suggested creators with published reels that user doesn't follow yet
    creator_ids = Reel.objects.filter(status='published').exclude(
        author=request.user
    ).exclude(
        author_id__in=following_ids
    ).values_list('author_id', flat=True).distinct()[:5]
    suggested_creators = User.objects.filter(id__in=creator_ids).select_related('profile')

    my_reels_count = Reel.objects.filter(author=request.user).count()

    return render(request, 'social/reels.html', {
        'reels': reels,
        'tab': tab,
        'active_tab': tab,
        'saved_reel_ids': saved_reel_ids,
        'liked_reel_ids': liked_reel_ids,
        'following_ids': following_ids,
        'suggested_creators': suggested_creators,
        'my_reels_count': my_reels_count,
        'active_nav': 'reels',
    })


@login_required
def my_reels_view(request):
    user_reels = Reel.objects.filter(author=request.user).prefetch_related('reactions', 'comments').order_by('-created_at')
    total_views = sum(r.views_count for r in user_reels)
    total_likes = sum(r.likes_count for r in user_reels)
    total_comments = sum(r.comments_count for r in user_reels)

    return render(request, 'social/my_reels.html', {
        'reels': user_reels,
        'total_reels': user_reels.count(),
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'active_nav': 'reels',
    })


@login_required
def upload_reel_view(request):
    if request.method == 'POST':
        caption = request.POST.get('caption', '').strip()
        audio_title = request.POST.get('audio_title', '').strip() or 'Original Audio'
        video_file = request.FILES.get('video_file')
        thumbnail = request.FILES.get('thumbnail')

        if not video_file:
            messages.error(request, "Please select a reel video file.")
            return redirect('social:reels')

        ext = os.path.splitext(video_file.name)[1].lower()
        if ext not in ['.mp4', '.webm', '.mov']:
            messages.error(request, f"Unsupported format '{ext}'. Please upload an MP4, WebM, or MOV.")
            return redirect('social:reels')

        if video_file.size > 52428800:
            messages.error(request, "Reel file size exceeds 50MB.")
            return redirect('social:reels')

        status = request.POST.get('status', 'published')
        privacy = request.POST.get('privacy', 'public')
        location = request.POST.get('location', '').strip()
        comments_enabled = request.POST.get('comments_enabled', 'on') in ['on', 'true', '1', True]
        allow_sharing = request.POST.get('allow_sharing', 'on') in ['on', 'true', '1', True]

        reel = Reel.objects.create(
            author=request.user,
            video_file=video_file,
            thumbnail=thumbnail,
            caption=caption,
            audio_title=audio_title,
            location=location,
            privacy=privacy,
            status=status,
            comments_enabled=comments_enabled,
            allow_sharing=allow_sharing
        )

        # Handle tagged friends
        tagged_ids = request.POST.getlist('tagged_friends')
        if tagged_ids:
            reel.tagged_friends.set(tagged_ids)

        messages.success(request, "Your Reel has been published!" if status == 'published' else "Reel saved as draft.")
        return redirect('social:reels')

    friends = User.objects.filter(id__in=Friendship.get_friend_ids(request.user), is_active=True)
    return render(request, 'social/reel_upload.html', {'friends': friends})


@login_required
def reels_api_feed_view(request):
    """API endpoint for infinite scrolling in reels"""
    page = int(request.GET.get('page', 1))
    page_size = 6
    offset = (page - 1) * page_size

    reels_qs = Reel.objects.filter(status='published').select_related('author', 'author__profile').prefetch_related('reactions', 'comments').order_by('-created_at')
    total = reels_qs.count()
    reels = reels_qs[offset:offset + page_size]

    saved_reel_ids = set(SavedReel.objects.filter(user=request.user).values_list('reel_id', flat=True))
    liked_reel_ids = set(ReelReaction.objects.filter(user=request.user).values_list('reel_id', flat=True))

    data = []
    for r in reels:
        data.append({
            'id': r.id,
            'video_url': r.video_file.url,
            'thumbnail_url': r.get_thumbnail_url(),
            'author_name': r.author.get_display_name(),
            'author_username': r.author.username,
            'author_avatar': r.author.profile.get_avatar_url(),
            'caption': r.caption,
            'audio_title': r.audio_title,
            'likes_count': r.likes_count,
            'comments_count': r.comments_count,
            'views_count': r.views_count,
            'is_liked': r.id in liked_reel_ids,
            'is_saved': r.id in saved_reel_ids,
        })

    return JsonResponse({
        'status': 'ok',
        'reels': data,
        'has_next': (offset + page_size) < total,
        'page': page
    })


@login_required
def react_reel_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    reaction = ReelReaction.objects.filter(reel=reel, user=request.user).first()
    if reaction:
        reaction.delete()
        status = 'unliked'
    else:
        ReelReaction.objects.create(reel=reel, user=request.user)
        status = 'liked'
        if reel.author != request.user:
            send_notification(
                recipient=reel.author,
                actor=request.user,
                notification_type='post_reaction',
                title='Reel Liked',
                message=f"{request.user.get_display_name()} liked your Reel.",
                target_url="/reels/",
                category='social'
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': status, 'likes_count': reel.likes_count})
    return redirect('social:reels')


@login_required
def add_reel_comment_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            ReelComment.objects.create(reel=reel, author=request.user, content=content)
            if reel.author != request.user:
                send_notification(
                    recipient=reel.author,
                    actor=request.user,
                    notification_type='post_comment',
                    title='Reel Comment',
                    message=f"{request.user.get_display_name()} commented on your Reel.",
                    target_url="/reels/",
                    category='social'
                )
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'comments_count': reel.comments_count, 'content': content, 'author': request.user.get_display_name()})
            messages.success(request, "Comment posted on Reel.")
    return redirect('social:reels')


@login_required
def toggle_save_reel_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    saved = SavedReel.objects.filter(user=request.user, reel=reel).first()
    if saved:
        saved.delete()
        status = 'unsaved'
    else:
        SavedReel.objects.create(user=request.user, reel=reel)
        status = 'saved'

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': status})
    return redirect('social:reels')


@login_required
def increment_reel_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    ip = request.META.get('REMOTE_ADDR')
    ten_min_ago = timezone.now() - timedelta(minutes=10)
    
    query = Q()
    if request.user.is_authenticated:
        query |= Q(viewer=request.user)
    if ip:
        query |= Q(ip_address=ip)

    recent_view = False
    if query:
        recent_view = ReelView.objects.filter(
            reel=reel,
            viewed_at__gte=ten_min_ago
        ).filter(query).exists()

    if not recent_view:
        ReelView.objects.create(
            reel=reel,
            viewer=request.user if request.user.is_authenticated else None,
            ip_address=ip if ip else None
        )
        from django.db.models import F
        Reel.objects.filter(pk=reel.pk).update(views_count=F('views_count') + 1)
        reel.views_count += 1
        return JsonResponse({'status': 'ok', 'views_count': reel.views_count, 'deduplicated': False})

    return JsonResponse({'status': 'ok', 'views_count': reel.views_count, 'deduplicated': True})


@login_required
def reel_comments_api_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    if not reel.can_view(request.user):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

    if request.method == 'POST':
        content = ''
        if request.content_type == 'application/json':
            try:
                body = json.loads(request.body.decode('utf-8'))
                content = body.get('content', '').strip()
            except Exception:
                content = ''
        if not content:
            content = request.POST.get('content', '').strip()

        if not content:
            return JsonResponse({'status': 'error', 'message': 'Comment cannot be empty.'}, status=400)
        comment = ReelComment.objects.create(reel=reel, author=request.user, content=content)
        if reel.author != request.user:
            send_notification(
                recipient=reel.author,
                actor=request.user,
                notification_type='post_comment',
                title='Reel Comment',
                message=f"{request.user.get_display_name()} commented on your Reel.",
                target_url=f"/reels/{reel.id}/",
                category='social'
            )
        total_comments = reel.comments.count()
        return JsonResponse({
            'status': 'ok',
            'comment': {
                'id': comment.id,
                'author_name': comment.author.get_display_name(),
                'author_username': comment.author.username,
                'author_avatar': comment.author.profile.get_avatar_url(),
                'content': comment.content,
                'created_at': 'Just now',
            },
            'comments_count': total_comments,
            'count': total_comments,
        })

    # GET comments list
    comments = reel.comments.select_related('author', 'author__profile').order_by('-created_at')[:60]
    data = []
    for c in comments:
        data.append({
            'id': c.id,
            'author_name': c.author.get_display_name(),
            'author_username': c.author.username,
            'author_avatar': c.author.profile.get_avatar_url(),
            'content': c.content,
            'created_at': c.created_at.strftime('%b %d, %H:%M'),
        })
    total_count = reel.comments.count()
    return JsonResponse({'status': 'ok', 'comments': data, 'comments_count': total_count, 'count': total_count})


@login_required
def share_reel_to_feed_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    if not reel.can_view(request.user):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    caption = ''
    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body.decode('utf-8'))
            caption = body.get('share_caption', '') or body.get('content', '')
        except Exception:
            caption = ''
    if not caption:
        caption = request.POST.get('share_caption', '') or request.POST.get('content', '')
    caption = caption.strip()
    share_text = f"{caption}\n\nShared Reel by @{reel.author.username}: /reels/{reel.id}/" if caption else f"Check out this Reel by @{reel.author.username}: /reels/{reel.id}/"
    post = Post.objects.create(
        author=request.user,
        content=share_text,
        post_type='reels',
        privacy='public',
    )
    if reel.author != request.user:
        send_notification(
            recipient=reel.author,
            actor=request.user,
            notification_type='post_reaction',
            title='Reel Shared',
            message=f"{request.user.get_display_name()} shared your Reel to their feed.",
            target_url=f"/reels/{reel.id}/",
            category='social'
        )
    return JsonResponse({'status': 'ok', 'message': 'Reel shared to your feed!', 'post_id': post.id})


@login_required
def search_view(request):
    from pages_app.models import Page
    from events_app.models import Event
    from marketplace.models import MarketplaceListing
    from accounts.models import BlockedUser

    query = request.GET.get('q', '').strip()
    users = []
    posts = []
    groups = []
    pages = []
    events = []
    listings = []

    if query:
        # Blocked users exclusion
        blocked_ids = BlockedUser.objects.filter(
            Q(blocker=request.user) | Q(blocked=request.user)
        ).values_list('blocked_id', 'blocker_id')
        blocked_flat = set([uid for pair in blocked_ids for uid in pair])

        # Search users (respect search discoverability)
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(is_deactivated=True).exclude(id__in=blocked_flat).exclude(
            privacy_settings__search_discoverability=False
        ).select_related('profile')[:10]

        # Search posts
        raw_posts = Post.objects.filter(
            Q(content__icontains=query) |
            Q(hashtags__name__icontains=query)
        ).select_related('author', 'author__profile').distinct()[:15]
        posts = [p for p in raw_posts if p.can_view(request.user)]

        # Search groups
        groups = Group.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:8]

        # Search pages
        pages = Page.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )[:8]

        # Search events
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(venue__icontains=query) |
            Q(description__icontains=query),
            privacy='public'
        )[:8]

        # Search marketplace listings
        listings = MarketplaceListing.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query),
            status='available'
        )[:8]

        # Search videos
        raw_videos = Video.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        ).select_related('author', 'author__profile')[:8]
        videos = [v for v in raw_videos if v.can_view(request.user)]

        # Search reels
        reels = Reel.objects.filter(
            Q(caption__icontains=query) |
            Q(audio_title__icontains=query),
            privacy='public',
            status='published'
        ).select_related('author', 'author__profile')[:8]
    else:
        videos = []
        reels = []

    return render(request, 'social/search_results.html', {
        'query': query,
        'users': users,
        'posts': posts,
        'groups': groups,
        'pages': pages,
        'events': events,
        'listings': listings,
        'videos': videos,
        'reels': reels,
    })


@login_required
def search_suggestions_view(request):
    from pages_app.models import Page
    from events_app.models import Event
    from marketplace.models import MarketplaceListing

    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    results = []
    # Search top users
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(is_deactivated=True).exclude(
        privacy_settings__search_discoverability=False
    ).select_related('profile')[:3]

    for u in users:
        results.append({
            'title': u.get_display_name(),
            'subtitle': f"@{u.username}",
            'url': f"/accounts/profile/{u.username}/",
            'avatar': u.profile.get_avatar_url(),
        })

    # Search top pages
    pages = Page.objects.filter(name__icontains=query)[:2]
    for p in pages:
        results.append({
            'title': p.name,
            'subtitle': f"Page • {p.get_category_display()}",
            'url': f"/pages/{p.slug}/",
            'avatar': p.get_avatar_url(),
        })

    # Search top groups
    groups = Group.objects.filter(name__icontains=query)[:2]
    for g in groups:
        results.append({
            'title': g.name,
            'subtitle': "Group",
            'url': f"/groups/{g.slug}/",
            'avatar': g.get_cover_url(),
        })

    # Search top marketplace listings
    listings = MarketplaceListing.objects.filter(title__icontains=query, status='available')[:2]
    for item in listings:
        results.append({
            'title': item.title,
            'subtitle': f"Marketplace • ${item.price}",
            'url': f"/marketplace/{item.id}/",
            'avatar': item.get_image_url(),
        })

    return JsonResponse({'results': results})


@login_required
def report_content_view(request, target_type, target_id):
    if request.method == 'POST':
        reason = request.POST.get('reason')
        details = request.POST.get('details', '')

        Report.objects.create(
            reporter=request.user,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            details=details
        )
        messages.success(request, "Thank you for letting us know. Our moderation team will review this report.")
        return redirect('social:feed')

    return render(request, 'social/report.html', {
        'target_type': target_type,
        'target_id': target_id,
    })


# ========================================================
# V4: CREATOR STUDIO & CONTENT DISCOVERY (EXPLORE)
# ========================================================

@login_required
def delete_reel_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    if reel.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Not authorized to delete this reel.")
    reel.delete()
    messages.info(request, "Reel deleted.")
    return redirect(request.META.get('HTTP_REFERER', 'social:reels'))


@login_required
def creator_studio_view(request):
    from datetime import timedelta
    from django.db.models import Sum, Q
    from streaming.models import LiveStream
    from accounts.models import Follow

    days = request.GET.get('days', 'all')
    cutoff = None
    if days == '7':
        cutoff = timezone.now() - timedelta(days=7)
    elif days == '30':
        cutoff = timezone.now() - timedelta(days=30)
    elif days == '90':
        cutoff = timezone.now() - timedelta(days=90)

    # Base querysets
    posts_qs = Post.objects.filter(author=request.user)
    videos_qs = Video.objects.filter(author=request.user)
    reels_qs = Reel.objects.filter(author=request.user)

    if cutoff:
        posts_filtered = posts_qs.filter(created_at__gte=cutoff)
        videos_filtered = videos_qs.filter(created_at__gte=cutoff)
        reels_filtered = reels_qs.filter(created_at__gte=cutoff)
    else:
        posts_filtered = posts_qs
        videos_filtered = videos_qs
        reels_filtered = reels_qs

    total_posts = posts_filtered.count()
    total_videos = videos_filtered.count()
    total_reels = reels_filtered.count()
    total_streams = LiveStream.objects.filter(host=request.user).count()
    total_photos = AlbumPhoto.objects.filter(album__user=request.user).count()
    followers_count = Follow.objects.filter(followed=request.user).count()

    # Views & Reach
    video_views_total = sum(v.views_count for v in videos_filtered)
    reel_views_total = sum(r.views_count for r in reels_filtered)
    post_views_total = sum(p.views_count for p in posts_filtered)
    total_views = video_views_total + reel_views_total + post_views_total

    # Engagement
    post_reactions = Reaction.objects.filter(post__in=posts_filtered).count()
    reel_reactions = ReelReaction.objects.filter(reel__in=reels_filtered).count()
    total_reactions = post_reactions + reel_reactions

    post_comments = Comment.objects.filter(post__in=posts_filtered).count()
    reel_comments = ReelComment.objects.filter(reel__in=reels_filtered).count()
    total_comments = post_comments + reel_comments

    total_shares = Post.objects.filter(original_post__in=posts_filtered).count()

    post_saves = SavedPost.objects.filter(post__in=posts_filtered).count()
    reel_saves = SavedReel.objects.filter(reel__in=reels_filtered).count()
    total_saves = post_saves + reel_saves

    total_engagements = total_reactions + total_comments + total_shares + total_saves
    engagement_rate = round((total_engagements / max(total_views, 1)) * 100, 1)

    user_videos = videos_filtered.order_by('-created_at')[:20]
    user_reels = reels_filtered.order_by('-created_at')[:20]
    user_posts = posts_filtered.order_by('-created_at')[:20]
    user_drafts = posts_qs.filter(status='draft').order_by('-created_at')
    user_scheduled = posts_qs.filter(status='scheduled').order_by('scheduled_at')
    user_albums = PhotoAlbum.objects.filter(user=request.user).prefetch_related('photos').order_by('-created_at')[:10]

    return render(request, 'social/creator_studio.html', {
        'active_nav': 'creator_studio',
        'days': days,
        'total_posts': total_posts,
        'total_videos': total_videos,
        'total_reels': total_reels,
        'total_photos': total_photos,
        'total_streams': total_streams,
        'followers_count': followers_count,
        'total_views': total_views,
        'video_views_total': video_views_total,
        'reel_views_total': reel_views_total,
        'post_views_total': post_views_total,
        'total_reactions': total_reactions,
        'total_comments': total_comments,
        'total_shares': total_shares,
        'total_saves': total_saves,
        'total_engagements': total_engagements,
        'engagement_rate': engagement_rate,
        'user_videos': user_videos,
        'user_reels': user_reels,
        'user_posts': user_posts,
        'user_drafts': user_drafts,
        'user_scheduled': user_scheduled,
        'user_albums': user_albums,
    })


@login_required
def explore_view(request):
    from streaming.models import LiveStream

    trending_posts = Post.objects.filter(privacy='public').order_by('-views_count', '-created_at')[:8]
    trending_hashtags = Hashtag.objects.annotate(tag_count=Count('posts')).order_by('-tag_count')[:10]
    popular_videos = Video.objects.filter(privacy='public').order_by('-views_count', '-created_at')[:6]
    popular_reels = Reel.objects.filter(privacy='public').order_by('-views_count', '-created_at')[:8]
    live_streams = LiveStream.objects.filter(status='live')[:4]
    suggested_creators = User.objects.filter(is_active=True).exclude(id=request.user.id).order_by('-date_joined')[:6]

    return render(request, 'social/explore.html', {
        'active_nav': 'explore',
        'trending_posts': trending_posts,
        'trending_hashtags': trending_hashtags,
        'popular_videos': popular_videos,
        'popular_reels': popular_reels,
        'live_streams': live_streams,
        'suggested_creators': suggested_creators,
    })


# ========================================================
# V5: ADVANCED POST CREATION & MANAGEMENT SUPPORTING VIEWS
# ========================================================

@login_required
def search_users_for_tagging_view(request):
    from accounts.models import BlockedUser
    query = request.GET.get('q', '').strip()

    blocked_by_me = BlockedUser.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_me = BlockedUser.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    excluded = set(list(blocked_by_me) + list(blocked_me) + [request.user.id])

    users_qs = User.objects.exclude(id__in=excluded).filter(is_active=True, is_deactivated=False)
    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    users = users_qs.select_related('profile')[:12]
    data = [{
        'id': u.id,
        'username': u.username,
        'display_name': u.get_display_name(),
        'avatar': u.profile.get_avatar_url() if hasattr(u, 'profile') else '/static/images/default-avatar.svg'
    } for u in users]
    return JsonResponse({'users': data})


@login_required
def fetch_link_preview_view(request):
    import urllib.parse
    import urllib.request
    import re

    url = request.POST.get('url', '').strip()
    if not url:
        return JsonResponse({'status': 'error', 'message': 'No URL provided'}, status=400)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        return JsonResponse({'status': 'error', 'message': 'Invalid URL scheme'}, status=400)

    hostname = (parsed.hostname or '').lower()
    # SSRF protection: reject local and private IP addresses
    private_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1', 'testserver']
    if hostname in private_hosts or hostname.endswith('.local') or hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
        return JsonResponse({'status': 'error', 'message': 'Private or restricted URL not allowed'}, status=400)

    title = parsed.netloc
    description = ''
    image = ''

    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ConnectBook/5.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                raw_html = resp.read(65536).decode('utf-8', errors='ignore')
                t_match = re.search(r'<title[^>]*>([^<]+)</title>', raw_html, re.IGNORECASE)
                if t_match:
                    title = t_match.group(1).strip()
                og_t = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if og_t:
                    title = og_t.group(1).strip()
                og_d = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if og_d:
                    description = og_d.group(1).strip()
                og_img = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if og_img:
                    image = og_img.group(1).strip()
    except Exception:
        pass

    return JsonResponse({
        'status': 'ok',
        'url': url,
        'domain': parsed.netloc,
        'title': title[:120],
        'description': description[:200],
        'image': image
    })


@login_required
def post_insights_api_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Only the author can view insights.")

    reach = post.post_views.values('ip_address', 'viewer_id').distinct().count()
    impressions = post.views_count
    reactions_breakdown = post.reaction_counts
    total_r = post.total_reactions
    comments_c = post.total_comments
    shares_c = post.total_shares

    engagement = total_r + comments_c + shares_c
    engagement_rate = round((engagement / max(impressions, 1)) * 100, 1)

    return JsonResponse({
        'status': 'ok',
        'data': {
            'post_id': post.id,
            'reach': reach,
            'impressions': impressions,
            'reactions_count': total_r,
            'reactions_breakdown': reactions_breakdown,
            'comments_count': comments_c,
            'shares_count': shares_c,
            'engagement_rate': engagement_rate
        }
    })


def record_post_view_view(request, post_id):
    from social.models import PostView
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        viewer = request.user if request.user.is_authenticated else None
        ip = request.META.get('REMOTE_ADDR')

        # Avoid recording multiple rapid views within 5 minutes
        recent = post.post_views.filter(viewed_at__gte=timezone.now() - timedelta(minutes=5))
        if viewer:
            recent = recent.filter(viewer=viewer)
        elif ip:
            recent = recent.filter(ip_address=ip)

        if not recent.exists():
            PostView.objects.create(post=post, viewer=viewer, ip_address=ip)
            post.views_count += 1
            post.save(update_fields=['views_count'])

        return JsonResponse({'status': 'ok', 'views_count': post.views_count})
    return JsonResponse({'status': 'ignored'})


@login_required
def manage_trash_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden()

    action = request.POST.get('action', 'trash')
    if action == 'trash':
        post.is_trashed = True
        post.trashed_at = timezone.now()
        post.save(update_fields=['is_trashed', 'trashed_at'])
        messages.info(request, "Post moved to Trash. It has been removed from feeds.")
    elif action == 'restore':
        post.is_trashed = False
        post.trashed_at = None
        post.save(update_fields=['is_trashed', 'trashed_at'])
        messages.success(request, "Post restored from Trash.")
    elif action == 'permanent_delete':
        post.delete()
        messages.success(request, "Post permanently deleted.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'action': action})
    return redirect('social:my_posts')


@login_required
def post_management_dashboard_view(request):
    tab = request.GET.get('tab', 'published')
    post_type = request.GET.get('type', '')

    user_posts = Post.objects.filter(author=request.user)
    if post_type:
        user_posts = user_posts.filter(post_type=post_type)

    published = user_posts.filter(status='published', is_archived=False, is_trashed=False).order_by('-created_at')
    drafts = user_posts.filter(status='draft', is_trashed=False).order_by('-created_at')
    scheduled = user_posts.filter(status='scheduled', is_trashed=False).order_by('scheduled_at')
    archived = user_posts.filter(is_archived=True, is_trashed=False).order_by('-created_at')
    trashed = user_posts.filter(is_trashed=True).order_by('-trashed_at')
    saved_posts = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author').order_by('-saved_at')

    # Instant publish action for scheduled posts
    if request.method == 'POST' and request.POST.get('action') == 'publish_scheduled_now':
        p_id = request.POST.get('post_id')
        p = get_object_or_404(Post, id=p_id, author=request.user)
        p.status = 'published'
        p.scheduled_at = None
        p.created_at = timezone.now()
        p.save()
        messages.success(request, f"Scheduled post #{p.id} published now!")
        return redirect('social:my_posts')

    return render(request, 'social/my_posts.html', {
        'active_nav': 'my_posts',
        'tab': tab,
        'published': published,
        'drafts': drafts,
        'scheduled': scheduled,
        'archived': archived,
        'trashed': trashed,
        'saved_posts': saved_posts,
        'post_types': Post.POST_TYPE_CHOICES,
        'selected_type': post_type,
    })


# ========================================================
# V6: PHOTO ALBUMS AND ALBUM PHOTOS
# ========================================================

@login_required
def create_album_view(request):
    from social.models import PhotoAlbum
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        privacy = request.POST.get('privacy', 'public')
        cover_photo = request.FILES.get('cover_photo')

        if not title:
            messages.error(request, "Please provide an album title.")
            return render(request, 'social/album_form.html', {'title': 'Create Album'})

        album = PhotoAlbum.objects.create(
            user=request.user,
            title=title,
            description=description,
            privacy=privacy,
            cover_photo=cover_photo
        )
        messages.success(request, f"Album '{album.title}' created successfully!")
        return redirect('social:album_detail', album_id=album.id)

    return render(request, 'social/album_form.html', {'title': 'Create Album'})


@login_required
def album_detail_view(request, album_id):
    from social.models import PhotoAlbum
    album = get_object_or_404(PhotoAlbum, id=album_id)
    if not album.can_view(request.user):
        messages.error(request, "This album is private.")
        return redirect('accounts:profile', username=album.user.username)

    is_owner = (request.user == album.user)
    photos = album.photos.all().order_by('-created_at')

    return render(request, 'social/album_detail.html', {
        'album': album,
        'is_owner': is_owner,
        'photos': photos,
    })


@login_required
def edit_album_view(request, album_id):
    from social.models import PhotoAlbum
    album = get_object_or_404(PhotoAlbum, id=album_id, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        privacy = request.POST.get('privacy', 'public')
        cover_photo = request.FILES.get('cover_photo')

        if not title:
            messages.error(request, "Album title cannot be blank.")
            return render(request, 'social/album_form.html', {'album': album, 'title': f"Edit {album.title}"})

        album.title = title
        album.description = description
        album.privacy = privacy
        if cover_photo:
            album.cover_photo = cover_photo
        album.save()

        messages.success(request, "Album details updated.")
        return redirect('social:album_detail', album_id=album.id)

    return render(request, 'social/album_form.html', {'album': album, 'title': f"Edit {album.title}"})


@login_required
def delete_album_view(request, album_id):
    from social.models import PhotoAlbum
    album = get_object_or_404(PhotoAlbum, id=album_id, user=request.user)
    if request.method == 'POST':
        title = album.title
        album.delete()
        messages.success(request, f"Album '{title}' was deleted.")
        return redirect('accounts:profile', username=request.user.username)
    return redirect('social:album_detail', album_id=album.id)


@login_required
def upload_album_photo_view(request, album_id):
    from social.models import PhotoAlbum, AlbumPhoto
    album = get_object_or_404(PhotoAlbum, id=album_id, user=request.user)

    if request.method == 'POST':
        images = request.FILES.getlist('images') or request.FILES.getlist('image')
        if not images and 'image' in request.FILES:
            images = [request.FILES['image']]
        caption = request.POST.get('caption', '').strip()
        alt_text = request.POST.get('alt_text', '').strip()

        if not images:
            messages.error(request, "Please choose at least one photo to upload.")
            return redirect('social:album_detail', album_id=album.id)

        for img in images:
            photo = AlbumPhoto.objects.create(
                album=album,
                user=request.user,
                image=img,
                caption=caption,
                alt_text=alt_text
            )
            # If album has no cover photo, use the first uploaded photo
            if not album.cover_photo:
                album.cover_photo = photo.image
                album.save(update_fields=['cover_photo'])

        messages.success(request, f"{len(images)} photo(s) added to '{album.title}'.")
    return redirect('social:album_detail', album_id=album.id)


@login_required
def delete_album_photo_view(request, photo_id):
    from social.models import AlbumPhoto
    photo = get_object_or_404(AlbumPhoto, id=photo_id, user=request.user)
    album_id = photo.album_id if photo.album else None
    photo.delete()
    messages.success(request, "Photo deleted.")
    if album_id:
        return redirect('social:album_detail', album_id=album_id)
    return redirect('accounts:profile', username=request.user.username)

