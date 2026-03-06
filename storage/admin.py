"""
Admin configuration for storage app.
"""
from django.contrib import admin
from .models import Folder, File, FileUpload


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'created_at']
    list_filter = ['created_at', 'owner']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'file_type', 'file_size', 'folder', 'upload_status', 'created_at']
    list_filter = ['file_type', 'upload_status', 'is_compressed', 'created_at', 'owner']
    search_fields = ['name', 'original_name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at', 'compression_ratio']
    actions = ['reupload_to_cloud']
    
    def reupload_to_cloud(self, request, queryset):
        from cloud_providers.tasks import upload_file_to_cloud
        for file in queryset:
            upload_file_to_cloud.delay(file.id)
        self.message_user(request, f"{queryset.count()} files queued for cloud upload.")
    reupload_to_cloud.short_description = "Re-upload selected files to cloud"


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['file', 'chunk_number', 'total_chunks', 'uploaded_at']
    list_filter = ['uploaded_at']
