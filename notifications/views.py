from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from accounts.decorators import officer_required
from accounts.models import User, Cadet
from .models import Notification, BulkNotification

@login_required
def notification_list(request):
    """User's notifications"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Filter
    filter_type = request.GET.get('type')
    filter_read = request.GET.get('read')
    
    if filter_type:
        notifications = notifications.filter(notification_type=filter_type)
    
    if filter_read == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_read == 'read':
        notifications = notifications.filter(is_read=True)
    
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'notification_types': Notification.NOTIFICATION_TYPE_CHOICES,
    }
    
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """View notification and mark as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    
    # Mark as read
    notification.mark_as_read()
    
    # Redirect to action URL if exists
    if notification.action_url:
        return redirect(notification.action_url)
    
    return render(request, 'notifications/notification_detail.html', {'notification': notification})


@login_required
def notification_mark_read(request, pk):
    """Mark single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    messages.success(request, 'Notification marked as read.')
    return redirect('notification_list')


@login_required
def notification_mark_all_read(request):
    """Mark all notifications as read"""
    count = Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    messages.success(request, f'{count} notifications marked as read.')
    return redirect('notification_list')


@login_required
def notification_delete(request, pk):
    """Delete notification"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    messages.success(request, 'Notification deleted.')
    return redirect('notification_list')


@officer_required
def send_bulk_notification(request):
    """Send bulk notification to multiple users"""
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        priority = request.POST.get('priority', 'MEDIUM')
        target_audience = request.POST.get('target_audience')
        
        # Create bulk notification record
        bulk_notif = BulkNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            target_audience=target_audience,
            sent_by=request.user
        )
        
        # Determine recipients
        recipients = []
        
        if target_audience == 'ALL_CADETS':
            recipients = User.objects.filter(role='CADET')
        elif target_audience == 'ALL_OFFICERS':
            recipients = User.objects.filter(role='OFFICER')
        elif target_audience == 'UNIT':
            unit_id = request.POST.get('target_unit')
            if unit_id:
                recipients = User.objects.filter(
                    Q(cadet_profile__unit_id=unit_id) | Q(officer_profile__unit_id=unit_id)
                )
        elif target_audience == 'YEAR':
            year = request.POST.get('target_year')
            if year:
                recipients = User.objects.filter(cadet_profile__year_of_study=year)
        elif target_audience == 'ALL':
            recipients = User.objects.filter(is_active=True)
        
        # Create individual notifications
        notifications_to_create = []
        for recipient in recipients:
            notifications_to_create.append(
                Notification(
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    priority=priority,
                    recipient=recipient,
                    sender=request.user
                )
            )
        
        # Bulk create
        created = Notification.objects.bulk_create(notifications_to_create)
        bulk_notif.recipients_count = len(created)
        bulk_notif.save()
        
        messages.success(request, f'Notification sent to {len(created)} recipients!')
        return redirect('notification_list')
    
    from units.models import Unit
    context = {
        'units': Unit.objects.all(),
        'notification_types': Notification.NOTIFICATION_TYPE_CHOICES,
        'priorities': Notification.PRIORITY_CHOICES,
    }
    
    return render(request, 'notifications/send_bulk.html', context)


@officer_required
def bulk_notification_history(request):
    """View bulk notification history"""
    bulk_notifications = BulkNotification.objects.all()
    
    if request.user.role == 'OFFICER':
        bulk_notifications = bulk_notifications.filter(sent_by=request.user)
    
    return render(request, 'notifications/bulk_history.html', {
        'bulk_notifications': bulk_notifications
    })

