from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils.text import slugify
from .models import Group, GroupMembership, GroupJoinRequest, GroupRule, GroupAnnouncement
from social.models import Post
from notifications.services import send_notification


@login_required
def group_list_view(request):
    my_memberships = GroupMembership.objects.filter(user=request.user).select_related('group')
    my_groups = [m.group for m in my_memberships]
    my_group_ids = [g.id for g in my_groups]

    suggested_groups = Group.objects.exclude(id__in=my_group_ids)[:12]

    return render(request, 'groups/group_list.html', {
        'active_nav': 'groups',
        'my_groups': my_groups,
        'suggested_groups': suggested_groups,
    })


@login_required
def create_group_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        privacy = request.POST.get('privacy', 'public')
        cover_photo = request.FILES.get('cover_photo')

        if not name:
            messages.error(request, "Group name is required.")
            return render(request, 'groups/create_group.html')

        base_slug = slugify(name) or 'group'
        slug = base_slug
        count = 1
        while Group.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        group = Group.objects.create(
            name=name,
            slug=slug,
            description=description,
            privacy=privacy,
            cover_photo=cover_photo,
            creator=request.user
        )

        GroupMembership.objects.create(
            group=group,
            user=request.user,
            role='admin'
        )

        messages.success(request, f"Group '{group.name}' created successfully!")
        return redirect('groups_app:detail', slug=group.slug)

    return render(request, 'groups/create_group.html')


@login_required
def group_detail_view(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(group=group, user=request.user).first()
    is_member = membership is not None
    is_admin = group.creator == request.user or (membership and membership.role in ['admin', 'moderator'])
    has_pending_join = GroupJoinRequest.objects.filter(group=group, user=request.user, status='pending').exists()

    # If private and not member, hide posts
    can_view_posts = (group.privacy == 'public') or is_member

    posts = []
    if can_view_posts:
        posts = Post.objects.filter(group=group).select_related('author', 'author__profile').prefetch_related('media_files', 'reactions', 'comments').order_by('-created_at')

    members_count = group.memberships.count()
    members_preview = group.memberships.select_related('user', 'user__profile')[:8]
    rules = group.rules.all()
    announcements = group.announcements.all()

    return render(request, 'groups/group_detail.html', {
        'group': group,
        'is_member': is_member,
        'is_admin': is_admin,
        'has_pending_join': has_pending_join,
        'posts': posts,
        'members_count': members_count,
        'members_preview': members_preview,
        'rules': rules,
        'announcements': announcements,
    })


@login_required
def join_group_view(request, slug):
    group = get_object_or_404(Group, slug=slug)

    if group.is_member(request.user):
        messages.info(request, "You are already a member of this group.")
        return redirect('groups_app:detail', slug=group.slug)

    if group.privacy == 'public':
        GroupMembership.objects.create(group=group, user=request.user, role='member')
        messages.success(request, f"You joined {group.name}!")
    else:
        # Private group requires join request
        req, created = GroupJoinRequest.objects.get_or_create(group=group, user=request.user)
        if created:
            send_notification(
                recipient=group.creator,
                actor=request.user,
                notification_type='group_join_request',
                title='Group Join Request',
                message=f"{request.user.get_display_name()} requested to join {group.name}.",
                target_url=f"/groups/{group.slug}/"
            )
            messages.info(request, "Join request sent to group admins.")

    return redirect('groups_app:detail', slug=group.slug)


@login_required
def leave_group_view(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(group=group, user=request.user).first()
    if membership:
        if group.creator == request.user and group.memberships.filter(role='admin').count() <= 1:
            messages.error(request, "You are the creator of this group. Assign another admin before leaving or delete the group.")
            return redirect('groups_app:detail', slug=group.slug)
        membership.delete()
        messages.info(request, f"You have left {group.name}.")

    return redirect('groups_app:list')


@login_required
def create_announcement_view(request, slug):
    group = get_object_or_404(Group, slug=slug)
    if not group.is_admin(request.user):
        return HttpResponseForbidden("Only group admins and moderators can post announcements.")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            GroupAnnouncement.objects.create(
                group=group,
                author=request.user,
                title=title,
                content=content,
                is_pinned=True
            )
            messages.success(request, "Group announcement posted successfully!")
    return redirect('groups_app:detail', slug=group.slug)


@login_required
def create_rule_view(request, slug):
    group = get_object_or_404(Group, slug=slug)
    if not group.is_admin(request.user):
        return HttpResponseForbidden("Only group admins can define group rules.")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if title:
            next_order = group.rules.count() + 1
            GroupRule.objects.create(
                group=group,
                title=title,
                description=description,
                order=next_order
            )
            messages.success(request, f"Rule '{title}' added to group.")
    return redirect('groups_app:detail', slug=group.slug)
