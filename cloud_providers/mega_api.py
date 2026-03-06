"""
MEGA API integration using mega.py library.
"""
from mega import Mega
from django.conf import settings
import os


def get_mega_client(connection=None):
    """Get authenticated MEGA client."""
    mega = Mega()
    
    if connection and connection.access_token:
        # Login with existing session (if supported)
        try:
            # mega.py doesn't support session resume directly
            # We'll need to login with credentials
            email = connection.provider_email or settings.MEGA_EMAIL
            password = settings.MEGA_PASSWORD
            
            if email and password:
                m = mega.login(email, password)
                return m
        except Exception:
            pass
    
    # Try environment credentials
    email = settings.MEGA_EMAIL
    password = settings.MEGA_PASSWORD
    
    if email and password:
        try:
            m = mega.login(email, password)
            return m
        except Exception as e:
            raise Exception(f"MEGA login failed: {str(e)}")
    
    # Anonymous login (very limited)
    try:
        m = mega.login()
        return m
    except Exception as e:
        raise Exception(f"MEGA anonymous login failed: {str(e)}")


def upload_file(connection, file_path, file_name, target_folder='CloudStorage'):
    """Upload a file to MEGA."""
    m = get_mega_client(connection)
    
    # Create or find folder
    folder = m.find(target_folder)
    if not folder:
        m.create_folder(target_folder)
        folder = m.find(target_folder)
    
    # Upload file
    file = m.upload(file_path, folder[0] if folder else None)
    
    # Get public link
    try:
        link = m.get_upload_link(file)
    except Exception:
        link = None
    
    return {
        'file_id': file,
        'name': file_name,
        'public_link': link
    }


def delete_file(connection, file_id):
    """Delete a file from MEGA."""
    m = get_mega_client(connection)
    
    try:
        m.destroy(file_id)
        return True
    except Exception as e:
        raise Exception(f"MEGA delete failed: {str(e)}")


def get_storage_info(connection=None):
    """Get storage quota information."""
    m = get_mega_client(connection)
    
    try:
        space = m.get_storage_space()
        
        return {
            'total': space.get('total', 0),
            'used': space.get('used', 0),
            'free': space.get('free', 0)
        }
    except Exception as e:
        raise Exception(f"Failed to get MEGA storage info: {str(e)}")


def list_files(connection, folder_name='CloudStorage'):
    """List files in MEGA."""
    m = get_mega_client(connection)
    
    try:
        files = m.get_files()
        
        result = []
        for file_id, file_info in files.items():
            if file_info['a'] and 'n' in file_info['a']:
                result.append({
                    'id': file_id,
                    'name': file_info['a']['n'],
                    'size': file_info.get('s', 0),
                    'type': 'folder' if file_info['t'] == 1 else 'file'
                })
        
        return result
    except Exception as e:
        raise Exception(f"Failed to list MEGA files: {str(e)}")


def create_folder(connection, folder_name):
    """Create a folder in MEGA."""
    m = get_mega_client(connection)
    
    try:
        folder = m.create_folder(folder_name)
        return {'folder_id': folder}
    except Exception as e:
        raise Exception(f"MEGA folder creation failed: {str(e)}")


def download_file(connection, file_id, output_path):
    """Download a file from MEGA."""
    m = get_mega_client(connection)
    
    try:
        m.download(file_id, output_path)
        return True
    except Exception as e:
        raise Exception(f"MEGA download failed: {str(e)}")
