"""
Celery tasks for cloud provider operations.
"""
import os
from celery import shared_task
from django.utils import timezone
from .models import CloudConnection, CloudUpload, CloudProvider
from storage.models import File


@shared_task(bind=True, max_retries=3)
def upload_file_to_cloud(self, file_id):
    """Upload a file to all connected cloud providers."""
    try:
        file = File.objects.get(id=file_id)
        user = file.owner
        
        # Get all active connections for user
        connections = CloudConnection.objects.filter(
            user=user,
            is_connected=True,
            is_active=True
        )
        
        for connection in connections:
            # Check if already uploaded
            existing = CloudUpload.objects.filter(
                file=file,
                connection=connection
            ).first()
            
            if existing and existing.status == 'completed':
                continue
            
            # Create or update upload record
            upload, created = CloudUpload.objects.get_or_create(
                file=file,
                connection=connection,
                defaults={'status': 'uploading'}
            )
            
            if not created:
                upload.status = 'uploading'
                upload.retry_count += 1
                upload.save()
            
            try:
                # Upload based on provider type
                if connection.provider.name == 'google_drive':
                    result = upload_to_google_drive(connection, file)
                elif connection.provider.name == 'dropbox':
                    result = upload_to_dropbox(connection, file)
                elif connection.provider.name == 'onedrive':
                    result = upload_to_onedrive(connection, file)
                elif connection.provider.name == 'mega':
                    result = upload_to_mega(connection, file)
                else:
                    raise Exception(f"Unknown provider: {connection.provider.name}")
                
                # Update upload record
                upload.status = 'completed'
                upload.provider_file_id = result.get('file_id', '')
                upload.provider_file_url = result.get('web_url') or result.get('shared_link') or result.get('public_link', '')
                upload.completed_at = timezone.now()
                upload.save()
                
                # Update file status
                file.upload_status = 'completed'
                file.save()
                
            except Exception as e:
                upload.status = 'failed'
                upload.last_error = str(e)
                upload.save()
                
                # Retry if needed
                if upload.retry_count < upload.max_retries:
                    upload.status = 'retrying'
                    upload.save()
                    raise self.retry(exc=e, countdown=60 * (upload.retry_count + 1))
        
        return f"File {file_id} processed for cloud upload"
        
    except File.DoesNotExist:
        return f"File {file_id} not found"
    except Exception as e:
        raise self.retry(exc=e, countdown=60)


def upload_to_google_drive(connection, file):
    """Upload file to Google Drive."""
    from .google_drive import upload_file
    
    if not file.file or not file.file.path:
        raise Exception("File or file path not available")
    
    return upload_file(
        connection,
        file.file.path,
        file.name,
        file.mime_type
    )


def upload_to_dropbox(connection, file):
    """Upload file to Dropbox."""
    from .dropbox_api import upload_file
    
    if not file.file or not file.file.path:
        raise Exception("File or file path not available")
    
    return upload_file(
        connection,
        file.file.path,
        file.name
    )


def upload_to_onedrive(connection, file):
    """Upload file to OneDrive."""
    from .onedrive_api import upload_file
    
    if not file.file or not file.file.path:
        raise Exception("File or file path not available")
    
    return upload_file(
        connection,
        file.file.path,
        file.name
    )


def upload_to_mega(connection, file):
    """Upload file to MEGA."""
    from .mega_api import upload_file
    
    if not file.file or not file.file.path:
        raise Exception("File or file path not available")
    
    return upload_file(
        connection,
        file.file.path,
        file.name
    )


@shared_task
def sync_storage_info(connection_id):
    """Sync storage information for a cloud connection."""
    try:
        connection = CloudConnection.objects.get(id=connection_id)
        
        if connection.provider.name == 'google_drive':
            from .google_drive import get_storage_info
            info = get_storage_info(connection)
            connection.total_storage = info['limit']
            connection.used_storage = info['usage']
            
        elif connection.provider.name == 'dropbox':
            from .dropbox_api import get_storage_info
            info = get_storage_info(connection)
            connection.total_storage = info['allocation']
            connection.used_storage = info['used']
            
        elif connection.provider.name == 'onedrive':
            from .onedrive_api import get_storage_info
            info = get_storage_info(connection)
            connection.total_storage = info['total']
            connection.used_storage = info['used']
            
        elif connection.provider.name == 'mega':
            from .mega_api import get_storage_info
            info = get_storage_info(connection)
            connection.total_storage = info['total']
            connection.used_storage = info['used']
        
        connection.save()
        return f"Updated storage info for {connection}"
        
    except CloudConnection.DoesNotExist:
        return f"Connection {connection_id} not found"
    except Exception as e:
        return f"Error syncing storage info: {str(e)}"


@shared_task
def cleanup_failed_uploads():
    """Clean up failed uploads older than 7 days."""
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(days=7)
    
    failed_uploads = CloudUpload.objects.filter(
        status='failed',
        created_at__lt=cutoff
    )
    
    count = failed_uploads.count()
    failed_uploads.delete()
    
    return f"Cleaned up {count} failed uploads"


@shared_task
def retry_failed_uploads():
    """Retry failed uploads."""
    failed_uploads = CloudUpload.objects.filter(
        status__in=['failed', 'retrying'],
        retry_count__lt=3
    )
    
    for upload in failed_uploads:
        upload_file_to_cloud.delay(upload.file.id)
    
    return f"Queued {failed_uploads.count()} uploads for retry"
