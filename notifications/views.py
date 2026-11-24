from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Notification


@login_required
def notifications_list_view(request):
    selected_cat = request.GET.get('category', 'all')
    notifications = Notification.objects.filter(recipient=request.user).select_related('actor', 'actor__profile')
    
    if selected_cat in ['social', 'messages', 'groups', 'security', 'general']:
        notifications = notifications.filter(category=selected_cat)
        
    notifications = notifications.order_by('-created_at')
    # Mark as read
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'selected_cat': selected_cat,
    })


@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect(request.META.get('HTTP_REFERER', 'notifications:list'))


@login_required
def unread_count_api(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})


@login_required
def delete_notification(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'deleted'})
    return redirect('notifications:list')
