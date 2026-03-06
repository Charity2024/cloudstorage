"""
OneDrive API integration using Microsoft Graph API.
"""
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'
AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

SCOPES = ['Files.ReadWrite', 'User.Read', 'offline_access']


def get_auth_url():
    """Generate OneDrive OAuth authorization URL."""
    scopes_str = '%20'.join(SCOPES)
    auth_url = (
        f"{AUTH_URL}?"
        f"client_id={settings.ONEDRIVE_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={settings.ONEDRIVE_REDIRECT_URI}&"
        f"scope={scopes_str}&"
        f"response_mode=query"
    )
    return auth_url


def handle_callback(code):
    """Handle OAuth callback from OneDrive."""
    data = {
        'client_id': settings.ONEDRIVE_CLIENT_ID,
        'client_secret': settings.ONEDRIVE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.ONEDRIVE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Token exchange failed: {response.text}")
    
    token_data = response.json()
    
    return {
        'access_token': token_data['access_token'],
        'refresh_token': token_data['refresh_token'],
        'expires_at': timezone.now() + timedelta(seconds=token_data['expires_in'])
    }


def refresh_token(connection):
    """Refresh expired access token."""
    data = {
        'client_id': settings.ONEDRIVE_CLIENT_ID,
        'client_secret': settings.ONEDRIVE_CLIENT_SECRET,
        'refresh_token': connection.refresh_token,
        'grant_type': 'refresh_token'
    }
    
    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code != 200:
        raise Exception(f"Token refresh failed: {response.text}")
    
    token_data = response.json()
    
    connection.access_token = token_data['access_token']
    connection.token_expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
    connection.save()
    
    return connection.access_token


def get_headers(connection):
    """Get authorization headers for API requests."""
    if connection.token_expires_at and connection.token_expires_at <= timezone.now():
        refresh_token(connection)
    
    return {
        'Authorization': f'Bearer {connection.access_token}',
        'Content-Type': 'application/json'
    }


def upload_file(connection, file_path, file_name, target_folder='CloudStorage'):
    """Upload a file to OneDrive."""
    headers = get_headers(connection)
    
    # Create folder if it doesn't exist
    folder_url = f"{GRAPH_API_BASE}/me/drive/root/children"
    folder_data = {
        'name': target_folder,
        'folder': {},
        '@microsoft.graph.conflictBehavior': 'rename'
    }
    
    requests.post(folder_url, headers=headers, json=folder_data)
    
    # Upload file
    upload_url = f"{GRAPH_API_BASE}/me/drive/root:/{target_folder}/{file_name}:/content"
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    upload_headers = headers.copy()
    upload_headers['Content-Type'] = 'application/octet-stream'
    
    response = requests.put(upload_url, headers=upload_headers, data=file_content)
    
    if response.status_code not in [200, 201]:
        raise Exception(f"Upload failed: {response.text}")
    
    result = response.json()
    
    return {
        'file_id': result['id'],
        'name': result['name'],
        'web_url': result['webUrl'],
        'download_url': result.get('@microsoft.graph.downloadUrl')
    }


def delete_file(connection, file_id):
    """Delete a file from OneDrive."""
    headers = get_headers(connection)
    
    delete_url = f"{GRAPH_API_BASE}/me/drive/items/{file_id}"
    
    response = requests.delete(delete_url, headers=headers)
    
    if response.status_code not in [200, 204]:
        raise Exception(f"Delete failed: {response.text}")
    
    return True


def get_storage_info(connection):
    """Get storage quota information."""
    headers = get_headers(connection)
    
    url = f"{GRAPH_API_BASE}/me/drive"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get storage info: {response.text}")
    
    result = response.json()
    quota = result.get('quota', {})
    
    return {
        'total': quota.get('total', 0),
        'used': quota.get('used', 0),
        'remaining': quota.get('remaining', 0),
        'deleted': quota.get('deleted', 0)
    }


def list_files(connection, folder_path='CloudStorage'):
    """List files in OneDrive."""
    headers = get_headers(connection)
    
    url = f"{GRAPH_API_BASE}/me/drive/root:/{folder_path}:/children"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to list files: {response.text}")
    
    result = response.json()
    
    return result.get('value', [])


def get_user_info(connection):
    """Get user information."""
    headers = get_headers(connection)
    
    url = f"{GRAPH_API_BASE}/me"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get user info: {response.text}")
    
    return response.json()
