from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from .models import LiveStream, LiveStreamChatMessage, LiveStreamViewer
from .forms import LiveStreamForm
from social.models import AuditLog


@login_required
def stream_list_view(request):
    tab = request.GET.get('tab', 'live')
    category = request.GET.get('category', '')

    live_qs = LiveStream.objects.filter(status='live')
    scheduled_qs = LiveStream.objects.filter(status='scheduled')
    ended_qs = LiveStream.objects.filter(status='ended')

    if category:
        live_qs = live_qs.filter(category=category)
        scheduled_qs = scheduled_qs.filter(category=category)
        ended_qs = ended_qs.filter(category=category)

    live_now = live_qs.select_related('host', 'host__profile').order_by('-actual_start')
    scheduled = scheduled_qs.select_related('host', 'host__profile').order_by('scheduled_start')
    ended = ended_qs.select_related('host', 'host__profile').order_by('-ended_at')[:12]

    categories = LiveStream.CATEGORY_CHOICES

    return render(request, 'streaming/stream_list.html', {
        'live_now': live_now,
        'scheduled': scheduled,
        'ended': ended,
        'tab': tab,
        'categories': categories,
        'selected_category': category,
    })


@login_required
def schedule_stream_view(request):
    if request.method == 'POST':
        form = LiveStreamForm(request.POST, request.FILES)
        if form.is_valid():
            stream = form.save(commit=False)
            stream.host = request.user
            stream.save()
            AuditLog.objects.create(
                actor=request.user,
                action='STREAM_SCHEDULE',
                target_repr=f"LiveStream {stream.title}",
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'stream_id': stream.id, 'scheduled_start': str(stream.scheduled_start)}
            )
            messages.success(request, f"Live stream '{stream.title}' created successfully! Welcome to your Studio.")
            return redirect('streaming:stream_dashboard', pk=stream.pk)
    else:
        form = LiveStreamForm()

    return render(request, 'streaming/stream_form.html', {'form': form, 'title': 'Create / Schedule Broadcast'})


@login_required
def stream_dashboard_view(request, pk):
    stream = get_object_or_404(LiveStream, pk=pk)
    if not stream.can_manage(request.user):
        return HttpResponseForbidden("You do not have permission to manage this broadcast.")

    chat_messages = stream.chat_messages.filter(is_deleted=False).select_related('sender', 'sender__profile').order_by('created_at')[:60]

    rtmp_server = "rtmp://localhost:1935/live/"
    whip_endpoint = f"http://localhost:8554/live/{stream.stream_key}/whip"
    hls_playback = stream.hls_playback_url or f"http://localhost:8888/live/{stream.stream_key}/index.m3u8"

    return render(request, 'streaming/stream_dashboard.html', {
        'stream': stream,
        'rtmp_server': rtmp_server,
        'whip_endpoint': whip_endpoint,
        'hls_playback': hls_playback,
        'chat_messages': chat_messages,
    })


def stream_room_view(request, pk):
    stream = get_object_or_404(LiveStream.objects.select_related('host', 'host__profile'), pk=pk)
    can_manage = stream.can_manage(request.user) if request.user.is_authenticated else False

    chat_messages = stream.chat_messages.filter(is_deleted=False).select_related('sender', 'sender__profile').order_by('created_at')[:50]

    return render(request, 'streaming/stream_room.html', {
        'stream': stream,
        'can_manage': can_manage,
        'chat_messages': chat_messages,
    })


@login_required
def toggle_stream_status_view(request, pk):
    stream = get_object_or_404(LiveStream, pk=pk)
    if not stream.can_manage(request.user):
        messages.error(request, "Unauthorized to control this broadcast.")
        return redirect('streaming:stream_room', pk=stream.pk)

    action = request.POST.get('action', '')
    if action == 'start':
        stream.status = 'live'
        stream.actual_start = timezone.now()
        stream.save()
        messages.success(request, "Broadcast is now LIVE!")
    elif action == 'end':
        stream.status = 'ended'
        stream.ended_at = timezone.now()
        stream.save()
        messages.info(request, "Live broadcast concluded.")

    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer:
        return redirect('streaming:stream_dashboard', pk=stream.pk)
    return redirect('streaming:stream_room', pk=stream.pk)


@login_required
def delete_stream_chat_view(request, pk, message_id):
    stream = get_object_or_404(LiveStream, pk=pk)
    if not stream.can_manage(request.user):
        return HttpResponseForbidden()

    msg = get_object_or_404(LiveStreamChatMessage, id=message_id, stream=stream)
    msg.is_deleted = True
    msg.save(update_fields=['is_deleted'])
    return JsonResponse({'status': 'deleted'})
