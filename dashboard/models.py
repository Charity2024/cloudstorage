"""
Dashboard models for activity tracking and notifications.
"""
from django.db import models
from django.contrib.auth.models import User


class Activity(models.Model):
    """Track user activities."""
    ACTIVITY_TYPES = [
        ('upload', 'File Upload'),
        ('download', 'File Download'),
        ('delete', 'File Delete'),
        ('share', 'File Share'),
        ('cloud_upload', 'Cloud Upload'),
        ('cloud_delete', 'Cloud Delete'),
        ('folder_create', 'Folder Create'),
        ('folder_delete', 'Folder Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    provider_name = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activities'


class Notification(models.Model):
    """User notifications."""
    NOTIFICATION_TYPES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class StorageQuotaAlert(models.Model):
    """Alerts for storage quota thresholds."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quota_alerts')
    threshold_percentage = models.IntegerField(default=80)
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.threshold_percentage}%"
