from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from social.models import Post, Comment, Report, AuditLog, Video, Reel
from groups_app.models import Group
from pages_app.models import Page
from events_app.models import Event
from marketplace.models import MarketplaceListing
from streaming.models import LiveStream
from accounts.models import DataExportRequest, AccountDeletionRequest, UserSessionRecord
from .models import SensitiveAccessLog

User = get_user_model()


def staff_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view_func)


@staff_required
def overview_view(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True, is_deactivated=False).count()
    suspended_users = User.objects.filter(is_active=False).count() + User.objects.filter(is_deactivated=True).count()
    total_posts = Post.objects.count()
    total_comments = Comment.objects.count()
    total_groups = Group.objects.count()
    total_pages = Page.objects.count()
    total_events = Event.objects.count()
    total_listings = MarketplaceListing.objects.count()
    total_streams = LiveStream.objects.count()
    pending_reports = Report.objects.filter(status='pending').count()
    pending_deletions = AccountDeletionRequest.objects.filter(status='pending').count()

    recent_users = User.objects.order_by('-date_joined')[:6]
    recent_reports = Report.objects.filter(status='pending').select_related('reporter')[:6]

    # Registration count over last 7 days for Chart.js
    now = timezone.now()
    days_data = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        u_count = User.objects.filter(date_joined__date=day_date).count()
        p_count = Post.objects.filter(created_at__date=day_date).count()
        days_data.append({
            'date': day_date.strftime('%b %d'),
            'users': u_count,
            'posts': p_count,
        })

    return render(request, 'admin_dashboard/overview.html', {
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_groups': total_groups,
        'total_pages': total_pages,
        'total_events': total_events,
        'total_listings': total_listings,
        'total_streams': total_streams,
        'pending_reports': pending_reports,
        'pending_deletions': pending_deletions,
        'recent_users': recent_users,
        'recent_reports': recent_reports,
        'days_data': days_data,
    })


@staff_required
def users_management_view(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')

    users = User.objects.select_related('profile').order_by('-date_joined')
    if query:
        users = users.filter(username__icontains=query) | users.filter(email__icontains=query) | users.filter(first_name__icontains=query)

    if role_filter == 'staff':
        users = users.filter(is_staff=True)
    elif role_filter == 'superuser':
        users = users.filter(is_superuser=True)
    elif role_filter == 'deactivated':
        users = users.filter(is_deactivated=True)

    return render(request, 'admin_dashboard/users.html', {'users': users[:100], 'query': query, 'role_filter': role_filter})


@staff_required
def toggle_user_active_view(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if u.is_superuser:
        messages.error(request, "Cannot alter superuser status here.")
        return redirect('admin_dashboard:users')

    u.is_active = not u.is_active
    u.save()

    AuditLog.objects.create(
        actor=request.user,
        action=f"Toggled user active state ({'Activated' if u.is_active else 'Deactivated'})",
        target_repr=f"User: {u.username}",
        ip_address=request.META.get('REMOTE_ADDR'),
        details={'user_id': u.id, 'active': u.is_active}
    )

    messages.success(request, f"User {u.username} status updated.")
    return redirect('admin_dashboard:users')


@staff_required
def moderation_queue_view(request):
    status_filter = request.GET.get('status', 'all')
    reports = Report.objects.select_related('reporter', 'reviewed_by').order_by('-created_at')
    if status_filter != 'all':
        reports = reports.filter(status=status_filter)
    return render(request, 'admin_dashboard/moderation.html', {'reports': reports, 'status_filter': status_filter})


@staff_required
def resolve_report_view(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        action = request.POST.get('action') # 'resolve_remove' or 'dismiss'
        notes = request.POST.get('notes', '')

        if action == 'resolve_remove':
            report.status = 'resolved'
            report.action_notes = f"Removed content. {notes}"

            # Delete target content based on target_type
            if report.target_type == 'post':
                Post.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'comment':
                Comment.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'page':
                Page.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'event':
                Event.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'listing':
                MarketplaceListing.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'group':
                Group.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'video':
                Video.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'reel':
                Reel.objects.filter(id=report.target_id).delete()
            elif report.target_type == 'livestream':
                LiveStream.objects.filter(id=report.target_id).delete()

            messages.success(request, f"Report #{report.id} resolved and target {report.target_type} removed.")
        else:
            report.status = 'dismissed'
            report.action_notes = f"Dismissed as no violation. {notes}"
            messages.info(request, f"Report #{report.id} dismissed.")

        report.reviewed_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        AuditLog.objects.create(
            actor=request.user,
            action=f"Handled Report #{report.id} ({report.status})",
            target_repr=f"{report.target_type} #{report.target_id}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'reason': report.reason, 'notes': report.action_notes}
        )

    return redirect('admin_dashboard:moderation')


@staff_required
def bulk_resolve_reports_view(request):
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        action = request.POST.get('bulk_action') # 'dismiss' or 'resolve_remove'
        if report_ids and action in ['dismiss', 'resolve_remove']:
            reports = Report.objects.filter(id__in=report_ids, status='pending')
            count = 0
            for r in reports:
                if action == 'resolve_remove':
                    r.status = 'resolved'
                    r.action_notes = 'Bulk resolved and removed by admin.'
                    if r.target_type == 'post':
                        Post.objects.filter(id=r.target_id).delete()
                    elif r.target_type == 'comment':
                        Comment.objects.filter(id=r.target_id).delete()
                    elif r.target_type == 'video':
                        Video.objects.filter(id=r.target_id).delete()
                    elif r.target_type == 'reel':
                        Reel.objects.filter(id=r.target_id).delete()
                    elif r.target_type == 'livestream':
                        LiveStream.objects.filter(id=r.target_id).delete()
                else:
                    r.status = 'dismissed'
                    r.action_notes = 'Bulk dismissed by admin.'
                r.reviewed_by = request.user
                r.resolved_at = timezone.now()
                r.save()
                count += 1
            messages.success(request, f"Bulk action completed: {count} reports updated.")
    return redirect('admin_dashboard:moderation')


@staff_required
def audit_logs_view(request):
    logs = AuditLog.objects.select_related('actor').order_by('-timestamp')[:100]
    return render(request, 'admin_dashboard/audit_logs.html', {'logs': logs})


@staff_required
def privacy_security_view(request):
    """
    ConnectBook Admin Privacy & Security Center (/admin-panel/privacy-security/)
    Section 30 & 31:
    - Staff role permissions overview
    - Sensitive Access logging and compliance records
    - User Privacy Complaints & Data Access Requests
    - Account Deletion Requests
    - Security activity & audit logs
    """
    staff_users = User.objects.filter(is_staff=True).select_related('profile')
    deletion_requests = AccountDeletionRequest.objects.select_related('user').order_by('-requested_at')[:20]
    data_exports = DataExportRequest.objects.select_related('user').order_by('-requested_at')[:20]
    sensitive_access_logs = SensitiveAccessLog.objects.select_related('staff_user').order_by('-accessed_at')[:30]
    security_audits = AuditLog.objects.filter(
        action__in=['DATA_EXPORT_JSON', 'ACCOUNT_DELETION_REQUEST', 'SENSITIVE_ACCESS_LOGGED', 'PAGE_DELETE', 'EVENT_DELETE']
    ).select_related('actor')[:30]

    return render(request, 'admin_dashboard/privacy_security.html', {
        'staff_users': staff_users,
        'deletion_requests': deletion_requests,
        'data_exports': data_exports,
        'sensitive_access_logs': sensitive_access_logs,
        'security_audits': security_audits,
    })


@staff_required
def handle_deletion_request_view(request, request_id, action):
    del_req = get_object_or_404(AccountDeletionRequest, id=request_id)
    if action == 'approve':
        target_user = del_req.user
        del_req.status = 'approved'
        del_req.save()
        target_user.is_active = False
        target_user.is_deactivated = True
        target_user.save()
        AuditLog.objects.create(
            actor=request.user,
            action='ADMIN_APPROVED_DELETION',
            target_repr=f"User {target_user.username}",
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'reason': del_req.reason}
        )
        messages.success(request, f"Deletion request for user {target_user.username} has been approved.")
    elif action == 'reject':
        del_req.status = 'cancelled'
        del_req.save()
        messages.info(request, f"Deletion request for user {del_req.user.username} rejected/cancelled.")

    return redirect('admin_dashboard:privacy_security')


@staff_required
def log_sensitive_access_view(request):
    if request.method == 'POST':
        resource = request.POST.get('target_resource', '').strip()
        reason = request.POST.get('reason', '').strip()
        if resource and reason:
            SensitiveAccessLog.objects.create(
                staff_user=request.user,
                target_resource=resource,
                reason=reason,
                ip_address=request.META.get('REMOTE_ADDR'),
                approved_by=request.user if request.user.is_superuser else None
            )
            AuditLog.objects.create(
                actor=request.user,
                action='SENSITIVE_ACCESS_LOGGED',
                target_repr=resource,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'reason': reason}
            )
            messages.success(request, "Sensitive access record logged successfully.")
        else:
            messages.error(request, "Target resource and reason are required.")
    return redirect('admin_dashboard:privacy_security')


# ========================================================
# V4: MEDIA & LIVE STREAM MODERATION
# ========================================================

@staff_required
def media_moderation_view(request):
    media_type = request.GET.get('type', 'all')
    videos = Video.objects.select_related('author').order_by('-created_at')[:50]
    reels = Reel.objects.select_related('author').order_by('-created_at')[:50]

    return render(request, 'admin_dashboard/media_moderation.html', {
        'media_type': media_type,
        'videos': videos,
        'reels': reels,
    })


@staff_required
def delete_video_admin_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    AuditLog.objects.create(
        actor=request.user,
        action="ADMIN_DELETE_VIDEO",
        target_repr=f"Video #{video.id} '{video.title}'",
        ip_address=request.META.get('REMOTE_ADDR'),
        details={'author': video.author.username}
    )
    video.delete()
    messages.success(request, f"Video #{video_id} permanently removed.")
    return redirect('admin_dashboard:media_moderation')


@staff_required
def delete_reel_admin_view(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    AuditLog.objects.create(
        actor=request.user,
        action="ADMIN_DELETE_REEL",
        target_repr=f"Reel #{reel.id}",
        ip_address=request.META.get('REMOTE_ADDR'),
        details={'author': reel.author.username}
    )
    reel.delete()
    messages.success(request, f"Reel #{reel_id} permanently removed.")
    return redirect('admin_dashboard:media_moderation')


@staff_required
def streams_moderation_view(request):
    live_streams = LiveStream.objects.filter(status='live').select_related('host').order_by('-actual_start')
    scheduled_streams = LiveStream.objects.filter(status='scheduled').select_related('host').order_by('scheduled_start')
    ended_streams = LiveStream.objects.filter(status='ended').select_related('host').order_by('-ended_at')[:20]

    return render(request, 'admin_dashboard/streams_moderation.html', {
        'live_streams': live_streams,
        'scheduled_streams': scheduled_streams,
        'ended_streams': ended_streams,
    })


@staff_required
def force_end_stream_admin_view(request, stream_id):
    stream = get_object_or_404(LiveStream, id=stream_id)
    stream.status = 'ended'
    stream.ended_at = timezone.now()
    stream.save()
    AuditLog.objects.create(
        actor=request.user,
        action="ADMIN_FORCE_END_STREAM",
        target_repr=f"LiveStream #{stream.id} '{stream.title}'",
        ip_address=request.META.get('REMOTE_ADDR'),
        details={'host': stream.host.username}
    )
    messages.warning(request, f"LiveStream #{stream.id} '{stream.title}' forcibly terminated.")
    return redirect('admin_dashboard:streams_moderation')

