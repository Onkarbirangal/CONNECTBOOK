from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from .models import Page, PageFollow
from .forms import PageForm
from social.models import Post, PostMedia, AuditLog


@login_required
def page_list_view(request):
    tab = request.GET.get('tab', 'discover')
    query = request.GET.get('q', '').strip()

    pages = Page.objects.all()
    if query:
        pages = pages.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query))

    if tab == 'my_pages':
        pages = pages.filter(owner=request.user)
    elif tab == 'following':
        followed_ids = PageFollow.objects.filter(user=request.user).values_list('page_id', flat=True)
        pages = pages.filter(id__in=followed_ids)

    my_pages_count = Page.objects.filter(owner=request.user).count()
    following_count = PageFollow.objects.filter(user=request.user).count()

    return render(request, 'pages/page_list.html', {
        'pages': pages,
        'tab': tab,
        'query': query,
        'my_pages_count': my_pages_count,
        'following_count': following_count,
    })


@login_required
def create_page_view(request):
    if request.method == 'POST':
        form = PageForm(request.POST, request.FILES)
        if form.is_valid():
            page = form.save(commit=False)
            page.owner = request.user
            page.save()
            # Owner automatically follows the page
            PageFollow.objects.get_or_create(page=page, user=request.user)
            AuditLog.objects.create(
                actor=request.user,
                action='PAGE_CREATE',
                target_repr=f"Page {page.name}",
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'page_id': page.id, 'category': page.category}
            )
            messages.success(request, f"Your page '{page.name}' has been created successfully!")
            return redirect('pages_app:page_detail', slug=page.slug)
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = PageForm()

    return render(request, 'pages/page_form.html', {'form': form, 'title': 'Create a Page'})


def page_detail_view(request, slug):
    page = get_object_or_404(Page, slug=slug)
    is_following = page.is_follower(request.user) if request.user.is_authenticated else False
    can_manage = page.can_manage(request.user) if request.user.is_authenticated else False

    # Page timeline posts
    posts = Post.objects.filter(page=page).select_related('author', 'author__profile').prefetch_related('media_files', 'reactions', 'comments').order_by('-is_pinned', '-created_at')

    # Handle post creation directly on page timeline by authorized admin
    if request.method == 'POST' and can_manage and 'create_page_post' in request.POST:
        content = request.POST.get('content', '').strip()
        if content or request.FILES.getlist('media'):
            new_post = Post.objects.create(
                author=request.user,
                page=page,
                content=content,
                privacy='public'
            )
            for f in request.FILES.getlist('media'):
                media_type = 'video' if f.content_type.startswith('video/') else 'image'
                PostMedia.objects.create(post=new_post, file=f, media_type=media_type)
            messages.success(request, "Post published to page timeline.")
            return redirect('pages_app:page_detail', slug=page.slug)

    return render(request, 'pages/page_detail.html', {
        'page': page,
        'posts': posts,
        'is_following': is_following,
        'can_manage': can_manage,
    })


@login_required
def edit_page_view(request, slug):
    page = get_object_or_404(Page, slug=slug)
    if not page.can_manage(request.user):
        messages.error(request, "You are not authorized to edit this page.")
        return redirect('pages_app:page_detail', slug=page.slug)

    if request.method == 'POST':
        form = PageForm(request.POST, request.FILES, instance=page)
        if form.is_valid():
            form.save()
            messages.success(request, "Page updated successfully!")
            return redirect('pages_app:page_detail', slug=page.slug)
    else:
        form = PageForm(instance=page)

    return render(request, 'pages/page_form.html', {'form': form, 'page': page, 'title': f"Edit {page.name}"})


@login_required
def delete_page_view(request, slug):
    page = get_object_or_404(Page, slug=slug)
    if page.owner != request.user and not request.user.is_superuser:
        messages.error(request, "Only the page owner can delete this page.")
        return redirect('pages_app:page_detail', slug=page.slug)

    if request.method == 'POST':
        name = page.name
        page.delete()
        AuditLog.objects.create(
            actor=request.user,
            action='PAGE_DELETE',
            target_repr=f"Page {name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Page '{name}' has been deleted.")
        return redirect('pages_app:page_list')

    return render(request, 'pages/page_confirm_delete.html', {'page': page})


@login_required
def toggle_follow_page_view(request, slug):
    page = get_object_or_404(Page, slug=slug)
    follow_rel = PageFollow.objects.filter(page=page, user=request.user).first()
    if follow_rel:
        follow_rel.delete()
        is_following = False
        msg = f"You unfollowed {page.name}."
    else:
        PageFollow.objects.create(page=page, user=request.user)
        is_following = True
        msg = f"You are now following {page.name}."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'ok',
            'is_following': is_following,
            'followers_count': page.total_followers,
            'message': msg
        })

    messages.info(request, msg)
    return redirect('pages_app:page_detail', slug=page.slug)


@login_required
def page_analytics_view(request, slug):
    page = get_object_or_404(Page, slug=slug)
    if not page.can_manage(request.user):
        messages.error(request, "You do not have permission to view analytics for this page.")
        return redirect('pages_app:page_detail', slug=page.slug)

    posts = Post.objects.filter(page=page)
    total_posts = posts.count()
    total_reactions = sum(p.reactions.count() for p in posts)
    total_comments = sum(p.comments.count() for p in posts)
    recent_followers = page.followers.select_related('user', 'user__profile')[:10]

    return render(request, 'pages/page_analytics.html', {
        'page': page,
        'total_posts': total_posts,
        'total_reactions': total_reactions,
        'total_comments': total_comments,
        'recent_followers': recent_followers,
    })
