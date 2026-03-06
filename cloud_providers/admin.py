"""
Admin configuration for cloud_providers app.
"""
from django.contrib import admin
from .models import CloudProvider, CloudConnection, CloudUpload, SyncRule


@admin.register(CloudProvider)
class CloudProviderAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']


@admin.register(CloudConnection)
class CloudConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'is_connected', 'is_active', 'created_at']
    list_filter = ['provider', 'is_connected', 'is_active', 'created_at']
    search_fields = ['user__username', 'provider__name', 'provider_email']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['sync_storage']
    
    def sync_storage(self, request, queryset):
        from .tasks import sync_storage_info
        for conn in queryset:
            sync_storage_info.delay(conn.id)
        self.message_user(request, f"Storage sync queued for {queryset.count()} connections.")
    sync_storage.short_description = "Sync storage info"


@admin.register(CloudUpload)
class CloudUploadAdmin(admin.ModelAdmin):
    list_display = ['file', 'connection', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at', 'connection__provider']
    search_fields = ['file__name', 'connection__provider__name']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['retry_upload']
    
    def retry_upload(self, request, queryset):
        from .tasks import upload_file_to_cloud
        for upload in queryset:
            upload.status = 'pending'
            upload.retry_count = 0
            upload.save()
            upload_file_to_cloud.delay(upload.file.id)
        self.message_user(request, f"{queryset.count()} uploads queued for retry.")
    retry_upload.short_description = "Retry selected uploads"


@admin.register(SyncRule)
class SyncRuleAdmin(admin.ModelAdmin):
    list_display = ['user', 'connection', 'folder', 'auto_upload', 'is_active']
    list_filter = ['is_active', 'auto_upload', 'created_at']
    search_fields = ['user__username', 'connection__provider__name']
