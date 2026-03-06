"""
Dropbox API integration.
"""
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from django.conf import settings


def get_dropbox_client(connection):
    """Get authenticated Dropbox client."""
    if not connection.access_token:
        return None
    
    try:
        dbx = dropbox.Dropbox(connection.access_token)
        # Verify token is valid
        dbx.users_get_current_account()
        return dbx
    except AuthError:
        # Token expired or invalid
        return None


def get_auth_url():
    """Generate Dropbox OAuth authorization URL."""
    auth_flow = dropbox.DropboxOAuth2Flow(
        settings.DROPBOX_APP_KEY,
        settings.DROPBOX_APP_SECRET,
        settings.DROPBOX_REDIRECT_URI,
        session={},
        csrf_token_session_key='dropbox-auth-csrf-token'
    )
    
    authorize_url = auth_flow.start()
    return authorize_url


def handle_callback(request, code):
    """Handle OAuth callback from Dropbox."""
    auth_flow = dropbox.DropboxOAuth2Flow(
        settings.DROPBOX_APP_KEY,
        settings.DROPBOX_APP_SECRET,
        settings.DROPBOX_REDIRECT_URI,
        session={},
        csrf_token_session_key='dropbox-auth-csrf-token'
    )
    
    oauth_result = auth_flow.finish({'code': code, 'state': request.GET.get('state', '')})
    
    return {
        'access_token': oauth_result.access_token,
        'refresh_token': oauth_result.refresh_token,
        'account_id': oauth_result.account_id,
        'user_id': oauth_result.user_id
    }


def upload_file(connection, file_path, file_name, target_path='/CloudStorage/'):
    """Upload a file to Dropbox."""
    dbx = get_dropbox_client(connection)
    
    if not dbx:
        raise Exception("Failed to authenticate with Dropbox")
    
    dropbox_path = f"{target_path}{file_name}"
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    try:
        response = dbx.files_upload(
            file_content,
            dropbox_path,
            mode=WriteMode('overwrite')
        )
        
        # Get shared link
        shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        
        return {
            'file_id': response.id,
            'path': response.path_display,
            'shared_link': shared_link.url if shared_link else None
        }
    except ApiError as e:
        raise Exception(f"Dropbox API error: {str(e)}")


def delete_file(connection, path):
    """Delete a file from Dropbox."""
    dbx = get_dropbox_client(connection)
    
    if not dbx:
        raise Exception("Failed to authenticate with Dropbox")
    
    try:
        dbx.files_delete_v2(path)
        return True
    except ApiError as e:
        raise Exception(f"Dropbox API error: {str(e)}")


def get_storage_info(connection):
    """Get storage quota information."""
    dbx = get_dropbox_client(connection)
    
    if not dbx:
        raise Exception("Failed to authenticate with Dropbox")
    
    try:
        space_usage = dbx.users_get_space_usage()
        
        return {
            'used': space_usage.used,
            'allocation': space_usage.allocation.get_individual().allocated if space_usage.allocation.is_individual() else 0,
            'available': space_usage.allocation.get_individual().allocated - space_usage.used if space_usage.allocation.is_individual() else 0
        }
    except ApiError as e:
        raise Exception(f"Dropbox API error: {str(e)}")


def list_files(connection, path=''):
    """List files in Dropbox."""
    dbx = get_dropbox_client(connection)
    
    if not dbx:
        raise Exception("Failed to authenticate with Dropbox")
    
    try:
        result = dbx.files_list_folder(path)
        
        files = []
        for entry in result.entries:
            files.append({
                'name': entry.name,
                'path': entry.path_display,
                'id': entry.id,
                'size': entry.size if hasattr(entry, 'size') else 0,
                'modified': entry.server_modified if hasattr(entry, 'server_modified') else None
            })
        
        return files
    except ApiError as e:
        raise Exception(f"Dropbox API error: {str(e)}")


def create_folder(connection, path):
    """Create a folder in Dropbox."""
    dbx = get_dropbox_client(connection)
    
    if not dbx:
        raise Exception("Failed to authenticate with Dropbox")
    
    try:
        result = dbx.files_create_folder_v2(path)
        return {
            'folder_id': result.metadata.id,
            'path': result.metadata.path_display
        }
    except ApiError as e:
        raise Exception(f"Dropbox API error: {str(e)}")
