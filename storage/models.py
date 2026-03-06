"""
Models for file and folder management.
"""
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


def generate_unique_filename(instance, filename):
    """Generate unique filename for uploaded files."""
    ext = filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('uploads', unique_name)


class Folder(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'parent', 'owner']
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """Get full path of folder."""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name
    
    def get_absolute_url(self):
        return reverse('storage:folder_detail', kwargs={'pk': self.pk})
    
    @property
    def file_count(self):
        """Count files in this folder."""
        return self.files.count()
    
    @property
    def total_size(self):
        """Calculate total size of files in this folder."""
        total = self.files.aggregate(total=models.Sum('file_size'))['total'] or 0
        for subfolder in self.subfolders.all():
            total += subfolder.total_size
        return total


class File(models.Model):
    FILE_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('archive', 'Archive'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=generate_unique_filename)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    mime_type = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)
    compressed_size = models.BigIntegerField(null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    
    # Compression settings
    is_compressed = models.BooleanField(default=False)
    compression_ratio = models.FloatField(null=True, blank=True)
    
    # Cloud upload status
    upload_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('storage:file_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        # Detect file type from mime_type
        if self.mime_type:
            if self.mime_type.startswith('image/'):
                self.file_type = 'image'
            elif self.mime_type.startswith('video/'):
                self.file_type = 'video'
            elif self.mime_type.startswith('audio/'):
                self.file_type = 'audio'
            elif any(self.mime_type.endswith(ext) for ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']):
                self.file_type = 'document'
            elif any(self.mime_type.endswith(ext) for ext in ['zip', 'rar', '7z', 'tar', 'gz']):
                self.file_type = 'archive'
        
        super().save(*args, **kwargs)
    
    @property
    def compression_savings(self):
        """Calculate storage savings from compression."""
        if self.is_compressed and self.compressed_size:
            return self.file_size - self.compressed_size
        return 0
    
    @property
    def compression_percentage(self):
        """Calculate compression percentage."""
        if self.is_compressed and self.compressed_size and self.file_size > 0:
            return ((self.file_size - self.compressed_size) / self.file_size) * 100
        return 0
    
    def get_file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.name)[1].lower()
    
    def get_icon_class(self):
        """Get Bootstrap icon class based on file type."""
        icons = {
            'image': 'bi-image',
            'video': 'bi-film',
            'audio': 'bi-music-note-beamed',
            'document': 'bi-file-earmark-text',
            'archive': 'bi-file-earmark-zip',
            'other': 'bi-file-earmark',
        }
        return icons.get(self.file_type, 'bi-file-earmark')


class FileUpload(models.Model):
    """Track file upload progress."""
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='uploads')
    chunk_number = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
