"""
Admin configuration for dashboard app.
"""
from django.contrib import admin
from .models import Activity, Notification, StorageQuotaAlert


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'description', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__username', 'description', 'file_name']
    readonly_fields = ['created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"


@admin.register(StorageQuotaAlert)
class StorageQuotaAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'threshold_percentage', 'is_active', 'last_triggered']
    list_filter = ['is_active', 'threshold_percentage']
    search_fields = ['user__username']
