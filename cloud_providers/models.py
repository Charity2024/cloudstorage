"""
Models for cloud provider connections and uploads.
"""
from django.db import models
from django.contrib.auth.models import User
from storage.models import File


class CloudProvider(models.Model):
    """Available cloud storage providers."""
    PROVIDER_CHOICES = [
        ('google_drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'OneDrive'),
        ('mega', 'MEGA'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='bi-cloud')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class CloudConnection(models.Model):
    """User's connection to a cloud provider."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cloud_connections')
    provider = models.ForeignKey(CloudProvider, on_delete=models.CASCADE, related_name='connections')
    
    # OAuth tokens
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Provider-specific IDs
    provider_user_id = models.CharField(max_length=255, blank=True)
    provider_email = models.EmailField(blank=True)
    
    # Status
    is_connected = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Storage info (in bytes)
    total_storage = models.BigIntegerField(default=0)
    used_storage = models.BigIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'provider']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.provider.display_name}"
    
    @property
    def available_storage(self):
        """Calculate available storage."""
        return max(0, self.total_storage - self.used_storage)
    
    @property
    def usage_percentage(self):
        """Calculate storage usage percentage."""
        if self.total_storage == 0:
            return 0
        return min(100, (self.used_storage / self.total_storage) * 100)


class CloudUpload(models.Model):
    """Track file uploads to cloud providers."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='cloud_uploads')
    connection = models.ForeignKey(CloudConnection, on_delete=models.CASCADE, related_name='uploads')
    
    # Upload details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_file_id = models.CharField(max_length=500, blank=True)
    provider_file_url = models.URLField(blank=True)
    
    # Retry logic
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['file', 'connection']
    
    def __str__(self):
        return f"{self.file.name} -> {self.connection.provider.display_name}"


class SyncRule(models.Model):
    """Rules for automatic file syncing to cloud providers."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sync_rules')
    connection = models.ForeignKey(CloudConnection, on_delete=models.CASCADE, related_name='sync_rules')
    
    # Rule conditions
    folder = models.ForeignKey('storage.Folder', on_delete=models.CASCADE, null=True, blank=True)
    file_types = models.JSONField(default=list, blank=True)  # ['image', 'video', etc.]
    min_file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    max_file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    
    # Rule actions
    auto_upload = models.BooleanField(default=True)
    delete_after_upload = models.BooleanField(default=False)
    compress_before_upload = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Sync Rule: {self.user.username} -> {self.connection.provider.display_name}"
