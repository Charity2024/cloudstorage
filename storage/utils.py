"""
Utility functions for file handling and image compression.
"""
import os
import io
import magic
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile


def get_file_type(file_path):
    """Detect file type using python-magic."""
    try:
        mime = magic.from_file(file_path, mime=True)
        return mime
    except Exception:
        return 'application/octet-stream'


def get_file_size(file_path):
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def compress_image(image_file, quality=None, max_width=None, max_height=None):
    """
    Compress an image file.
    
    Args:
        image_file: Django FileField or file path
        quality: JPEG quality (1-100), defaults to settings.IMAGE_COMPRESSION_QUALITY
        max_width: Maximum width, defaults to settings.MAX_IMAGE_WIDTH
        max_height: Maximum height, defaults to settings.MAX_IMAGE_HEIGHT
    
    Returns:
        tuple: (compressed_image_bytes, original_size, compressed_size)
    """
    quality = quality or getattr(settings, 'IMAGE_COMPRESSION_QUALITY', 85)
    max_width = max_width or getattr(settings, 'MAX_IMAGE_WIDTH', 1920)
    max_height = max_height or getattr(settings, 'MAX_IMAGE_HEIGHT', 1080)
    
    # Open image
    if hasattr(image_file, 'path'):
        img = Image.open(image_file.path)
        original_size = os.path.getsize(image_file.path)
    else:
        img = Image.open(image_file)
        image_file.seek(0, os.SEEK_END)
        original_size = image_file.tell()
        image_file.seek(0)
    
    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    
    # Resize if too large
    original_width, original_height = img.size
    if original_width > max_width or original_height > max_height:
        ratio = min(max_width / original_width, max_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Save compressed image
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    
    compressed_size = output.tell()
    
    return output, original_size, compressed_size


def compress_file(file_instance):
    """
    Compress a file based on its type.
    Currently supports image compression.
    
    Args:
        file_instance: File model instance
    
    Returns:
        bool: True if compression was successful
    """
    from .models import File
    
    if file_instance.file_type != 'image':
        return False
    
    try:
        # Compress image
        compressed_image, original_size, compressed_size = compress_image(file_instance.file)
        
        # Save compressed image
        file_name = os.path.splitext(file_instance.name)[0] + '.jpg'
        file_instance.file.save(
            file_name,
            ContentFile(compressed_image.read()),
            save=False
        )
        
        # Update file info
        file_instance.is_compressed = True
        file_instance.compressed_size = compressed_size
        file_instance.compression_ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0
        file_instance.file_size = compressed_size
        file_instance.save()
        
        return True
        
    except Exception as e:
        print(f"Compression error: {e}")
        return False


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def get_folder_tree(user, parent=None, level=0):
    """Get folder tree structure for a user."""
    from .models import Folder
    
    folders = Folder.objects.filter(owner=user, parent=parent)
    tree = []
    
    for folder in folders:
        tree.append({
            'folder': folder,
            'level': level,
            'has_children': folder.subfolders.exists()
        })
        if folder.subfolders.exists():
            tree.extend(get_folder_tree(user, folder, level + 1))
    
    return tree


def create_folder_path(user, path_string):
    """Create folder structure from path string (e.g., 'photos/2024/january')."""
    from .models import Folder
    
    parts = path_string.strip('/').split('/')
    parent = None
    current_path = ""
    
    for part in parts:
        if not part:
            continue
        
        current_path = f"{current_path}/{part}" if current_path else part
        
        folder, created = Folder.objects.get_or_create(
            name=part,
            owner=user,
            parent=parent
        )
        parent = folder
    
    return parent
