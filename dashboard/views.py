"""
Views for dashboard and main interface.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from storage.models import File, Folder
from cloud_providers.models import CloudConnection, CloudUpload
from .models import Activity, Notification


@login_required
def home(request):
    """Main dashboard view."""
    user = request.user
    
    # File statistics
    total_files = File.objects.filter(owner=user).count()
    recent_files = File.objects.filter(owner=user).order_by('-created_at')[:10]
    
    # Storage statistics
    storage_stats = File.objects.filter(owner=user).aggregate(
        total_size=Sum('file_size'),
        compressed_size=Sum('compressed_size'),
        image_count=Count('id', filter=Q(file_type='image')),
        video_count=Count('id', filter=Q(file_type='video')),
        document_count=Count('id', filter=Q(file_type='document')),
        other_count=Count('id', filter=Q(file_type='other'))
    )
    
    total_size = storage_stats['total_size'] or 0
    compressed_size = storage_stats['compressed_size'] or 0
    savings = total_size - compressed_size if compressed_size else 0
    
    # Cloud connections
    connections = CloudConnection.objects.filter(user=user, is_connected=True)
    cloud_uploads = CloudUpload.objects.filter(file__owner=user).order_by('-created_at')[:10]
    
    # Calculate cloud storage stats
    cloud_total = sum(conn.total_storage for conn in connections)
    cloud_used = sum(conn.used_storage for conn in connections)
    
    # Recent activities
    activities = Activity.objects.filter(user=user).order_by('-created_at')[:20]
    
    # Unread notifications
    notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
    
    # File type distribution
    file_type_labels = ['Images', 'Videos', 'Documents', 'Audio', 'Archives', 'Other']
    file_type_data = [
        storage_stats['image_count'] or 0,
        storage_stats['video_count'] or 0,
        storage_stats['document_count'] or 0,
        File.objects.filter(owner=user, file_type='audio').count(),
        File.objects.filter(owner=user, file_type='archive').count(),
        storage_stats['other_count'] or 0,
    ]
    
    # Weekly upload stats
    week_ago = timezone.now() - timedelta(days=7)
    daily_uploads = []
    daily_labels = []
    
    for i in range(7):
        day = week_ago + timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = File.objects.filter(
            owner=user,
            created_at__gte=day,
            created_at__lt=next_day
        ).count()
        daily_uploads.append(count)
        daily_labels.append(day.strftime('%a'))
    
    context = {
        'total_files': total_files,
        'recent_files': recent_files,
        'total_size': total_size,
        'compressed_size': compressed_size,
        'savings': savings,
        'connections': connections,
        'connections_count': connections.count(),
        'cloud_uploads': cloud_uploads,
        'cloud_total': cloud_total,
        'cloud_used': cloud_used,
        'activities': activities,
        'notifications': notifications,
        'notifications_count': notifications.count(),
        'file_type_labels': file_type_labels,
        'file_type_data': file_type_data,
        'daily_labels': daily_labels,
        'daily_uploads': daily_uploads,
        'folders': Folder.objects.filter(owner=user, parent=None)[:10],
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def recent_activity(request):
    """View all recent activities."""
    activities = Activity.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by type
    activity_type = request.GET.get('type')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    context = {
        'activities': activities[:100],
        'activity_types': Activity.ACTIVITY_TYPES,
    }
    return render(request, 'dashboard/activity.html', context)


@login_required
def notifications(request):
    """View all notifications."""
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    if request.GET.get('mark_read'):
        user_notifications.filter(is_read=False).update(is_read=True)
    
    context = {
        'notifications': user_notifications,
        'unread_count': user_notifications.filter(is_read=False).count(),
    }
    return render(request, 'dashboard/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    from django.http import JsonResponse
    
    notification = Notification.objects.filter(
        id=notification_id,
        user=request.user
    ).first()
    
    if notification:
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
def storage_analytics(request):
    """Detailed storage analytics."""
    user = request.user
    
    # Monthly stats
    months = []
    uploads_per_month = []
    storage_per_month = []
    
    for i in range(12):
        month_start = timezone.now() - timedelta(days=30 * (11 - i))
        month_end = month_start + timedelta(days=30)
        
        month_files = File.objects.filter(
            owner=user,
            created_at__gte=month_start,
            created_at__lt=month_end
        )
        
        months.append(month_start.strftime('%b %Y'))
        uploads_per_month.append(month_files.count())
        storage_per_month.append(
            (month_files.aggregate(total=Sum('file_size'))['total'] or 0) / (1024 * 1024)
        )
    
    # Top file types by size
    file_type_sizes = File.objects.filter(owner=user).values('file_type').annotate(
        total_size=Sum('file_size'),
        count=Count('id')
    ).order_by('-total_size')
    
    # Largest files
    largest_files = File.objects.filter(owner=user).order_by('-file_size')[:20]
    
    context = {
        'months': months,
        'uploads_per_month': uploads_per_month,
        'storage_per_month': storage_per_month,
        'file_type_sizes': file_type_sizes,
        'largest_files': largest_files,
    }
    return render(request, 'dashboard/analytics.html', context)
