from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import Event, EventRSVP
from .forms import EventForm
from social.models import AuditLog
from notifications.services import send_notification


@login_required
def event_list_view(request):
    tab = request.GET.get('tab', 'upcoming')
    query = request.GET.get('q', '').strip()

    events = Event.objects.all()

    if query:
        events = events.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(venue__icontains=query))

    if tab == 'my_events':
        events = events.filter(organizer=request.user)
    elif tab == 'attending':
        rsvp_event_ids = EventRSVP.objects.filter(user=request.user, status__in=['going', 'interested']).values_list('event_id', flat=True)
        events = events.filter(id__in=rsvp_event_ids)
    else: # upcoming
        events = events.filter(start_time__gte=timezone.now() - timezone.timedelta(hours=6))

    my_events_count = Event.objects.filter(organizer=request.user).count()
    attending_count = EventRSVP.objects.filter(user=request.user, status='going').count()

    return render(request, 'events/event_list.html', {
        'events': events,
        'tab': tab,
        'query': query,
        'my_events_count': my_events_count,
        'attending_count': attending_count,
    })


@login_required
def create_event_view(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            # Organizer automatically RSVP as going
            EventRSVP.objects.create(event=event, user=request.user, status='going')
            AuditLog.objects.create(
                actor=request.user,
                action='EVENT_CREATE',
                target_repr=f"Event {event.title}",
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'event_id': event.id, 'venue': event.venue}
            )
            messages.success(request, f"Event '{event.title}' scheduled successfully!")
            return redirect('events_app:event_detail', pk=event.pk)
    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {'form': form, 'title': 'Create New Event'})


def event_detail_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user_rsvp = event.user_rsvp(request.user) if request.user.is_authenticated else None
    can_manage = event.can_manage(request.user) if request.user.is_authenticated else False
    attendees = event.rsvps.filter(status='going').select_related('user', 'user__profile')[:12]

    return render(request, 'events/event_detail.html', {
        'event': event,
        'user_rsvp': user_rsvp,
        'can_manage': can_manage,
        'attendees': attendees,
    })


@login_required
def edit_event_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.can_manage(request.user):
        messages.error(request, "You are not authorized to edit this event.")
        return redirect('events_app:event_detail', pk=event.pk)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event details updated successfully.")
            return redirect('events_app:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {'form': form, 'event': event, 'title': f"Edit {event.title}"})


@login_required
def delete_event_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.can_manage(request.user):
        messages.error(request, "You are not authorized to delete this event.")
        return redirect('events_app:event_detail', pk=event.pk)

    if request.method == 'POST':
        title = event.title
        event.delete()
        AuditLog.objects.create(
            actor=request.user,
            action='EVENT_DELETE',
            target_repr=f"Event {title}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Event '{title}' has been removed.")
        return redirect('events_app:event_list')

    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
def event_rsvp_view(request, pk):
    event = get_object_or_404(Event, pk=pk)
    status = request.POST.get('status', request.GET.get('status', 'going'))
    if status not in ['going', 'interested', 'not_going']:
        status = 'going'

    rsvp, created = EventRSVP.objects.get_or_create(event=event, user=request.user)
    rsvp.status = status
    rsvp.save()

    if status in ['going', 'interested'] and event.organizer != request.user:
        send_notification(
            recipient=event.organizer,
            actor=request.user,
            notification_type='group_invite',
            title='New Event RSVP',
            message=f"{request.user.get_display_name()} RSVP'd {status.capitalize()} to {event.title}.",
            target_url=f"/events/{event.id}/",
            category='groups'
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'ok',
            'rsvp': status,
            'going_count': event.going_count,
            'interested_count': event.interested_count
        })

    messages.success(request, f"Your RSVP has been updated to '{status.replace('_', ' ').capitalize()}'.")
    return redirect('events_app:event_detail', pk=event.pk)
