"""
Context processors for storage app.
"""
from .models import File, Folder


def storage_stats(request):
    """Add storage statistics to all templates."""
    if request.user.is_authenticated:
        total_files = File.objects.filter(owner=request.user).count()
        total_folders = Folder.objects.filter(owner=request.user).count()
        
        # File type breakdown
        file_types = File.objects.filter(owner=request.user).values('file_type').distinct()
        
        return {
            'total_files': total_files,
            'total_folders': total_folders,
            'file_types': [ft['file_type'] for ft in file_types],
        }
    
    return {}
