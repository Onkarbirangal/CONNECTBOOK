import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Story, StoryView

User = get_user_model()


@login_required
def create_story_view(request):
    if request.method == 'POST':
        media_type = request.POST.get('media_type', 'image')
        media_file = request.FILES.get('media_file')
        text_content = request.POST.get('text_content', '').strip()
        background_color = request.POST.get('background_color', 'linear-gradient(135deg, #1877F2 0%, #00C6FF 100%)')
        privacy = request.POST.get('privacy', 'friends')
        location = request.POST.get('location', '').strip()

        if media_type in ['image', 'video'] and not media_file:
            messages.error(request, "Please select an image or video for your story.")
            return redirect('stories:create_story')
        elif media_type == 'text' and not text_content:
            messages.error(request, "Please type some text for your story.")
            return redirect('stories:create_story')

        story = Story.objects.create(
            author=request.user,
            media_type=media_type,
            media_file=media_file,
            text_content=text_content,
            background_color=background_color,
            privacy=privacy,
            location=location,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        tagged_ids = request.POST.getlist('tagged_friends')
        if tagged_ids:
            story.tagged_friends.set(tagged_ids)

        messages.success(request, "Story posted! It will disappear after 24 hours.")
        return redirect('social:feed')

    from friends.models import Friendship
    friends = User.objects.filter(id__in=Friendship.get_friend_ids(request.user), is_active=True)
    return render(request, 'stories/create_story.html', {'friends': friends})


@login_required
def user_stories_api(request, user_id):
    author = get_object_or_404(User, id=user_id)
    raw_stories = Story.objects.filter(
        author=author,
        expires_at__gt=timezone.now()
    ).order_by('created_at')

    # Enforce story privacy
    active_stories = [s for s in raw_stories if s.can_view(request.user)]

    stories_data = []
    for s in active_stories:
        media_url = s.media_file.url if s.media_file else ''
        stories_data.append({
            'id': s.id,
            'media_type': s.media_type,
            'media_url': media_url,
            'text_content': s.text_content,
            'background_color': s.background_color,
            'location': s.location,
            'author_name': s.author.get_display_name(),
            'author_avatar': s.author.profile.get_avatar_url(),
            'time_ago': f"{s.created_at.strftime('%I:%M %p')}",
            'views_count': s.views.count(),
        })

    return JsonResponse({'stories': stories_data})


@login_required
def highlight_stories_api(request, highlight_id):
    from .models import StoryHighlight
    highlight = get_object_or_404(StoryHighlight, id=highlight_id)
    stories_data = []
    for s in highlight.stories.all().order_by('created_at'):
        media_url = s.media_file.url if s.media_file else ''
        stories_data.append({
            'id': s.id,
            'media_type': s.media_type,
            'media_url': media_url,
            'text_content': s.text_content,
            'background_color': s.background_color,
            'location': s.location,
            'author_name': highlight.user.get_display_name(),
            'author_avatar': highlight.user.profile.get_avatar_url(),
            'time_ago': highlight.title,
            'views_count': s.views.count(),
        })
    return JsonResponse({'stories': stories_data})


@login_required
def create_highlight_view(request):
    from .models import StoryHighlight
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        cover_image = request.FILES.get('cover_image')
        story_ids = request.POST.getlist('story_ids')

        if not title:
            messages.error(request, "Please enter a highlight title.")
            return redirect('accounts:profile', username=request.user.username)

        highlight = StoryHighlight.objects.create(
            user=request.user,
            title=title,
            cover_image=cover_image
        )
        if story_ids:
            highlight.stories.set(story_ids)
        else:
            # Pick user's latest stories by default
            latest = Story.objects.filter(author=request.user)[:5]
            highlight.stories.set(latest)

        messages.success(request, f"Story Highlight '{highlight.title}' created!")
    return redirect('accounts:profile', username=request.user.username)


@login_required
def react_story_api(request, story_id):
    from .models import StoryReaction
    story = get_object_or_404(Story, id=story_id)
    if not story.can_view(request.user):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    r_type = request.POST.get('reaction_type', 'love')
    reaction, created = StoryReaction.objects.get_or_create(
        story=story,
        user=request.user,
        defaults={'reaction_type': r_type}
    )
    if not created:
        reaction.reaction_type = r_type
        reaction.save(update_fields=['reaction_type'])

    return JsonResponse({'status': 'ok', 'reaction': r_type})


@login_required
def reply_story_api(request, story_id):
    from .models import StoryReply
    from chat.models import Conversation, Message
    story = get_object_or_404(Story, id=story_id)
    if not story.can_view(request.user):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    message_text = request.POST.get('message', '').strip()

    if not message_text:
        return JsonResponse({'status': 'error', 'message': 'Empty message'}, status=400)

    # Record reply
    StoryReply.objects.create(
        story=story,
        user=request.user,
        message=message_text
    )

    # Deliver direct chat message to story author if not self
    if story.author != request.user:
        conv = Conversation.get_or_create_direct(request.user, story.author)
        content = f"Replied to your story: \"{message_text}\""
        Message.objects.create(conversation=conv, sender=request.user, content=content)

    return JsonResponse({'status': 'ok', 'message': 'Reply sent!'})


@login_required
def story_archive_view(request):
    expired_stories = Story.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'stories/story_archive.html', {'stories': expired_stories})


@login_required
def view_story_api(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if not story.can_view(request.user):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if story.author != request.user:
        StoryView.objects.get_or_create(story=story, viewer=request.user)
    return JsonResponse({'status': 'viewed'})


@login_required
def delete_story_view(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if story.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Not authorized to delete this story.")
    story.delete()
    messages.info(request, "Story deleted.")
    return redirect('social:feed')
