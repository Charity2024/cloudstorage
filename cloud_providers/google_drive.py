"""
Google Drive API integration.
"""
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings
from django.urls import reverse


SCOPES = ['https://www.googleapis.com/auth/drive']


def get_google_drive_service(connection):
    """Get authenticated Google Drive service."""
    creds = None
    
    if connection.access_token:
        creds = Credentials.from_authorized_user_info({
            'token': connection.access_token,
            'refresh_token': connection.refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': settings.GOOGLE_DRIVE_CLIENT_ID,
            'client_secret': settings.GOOGLE_DRIVE_CLIENT_SECRET,
            'scopes': SCOPES
        })
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update tokens in database
            connection.access_token = creds.token
            connection.refresh_token = creds.refresh_token
            connection.save()
        else:
            return None
    
    return build('drive', 'v3', credentials=creds)


def get_auth_url(request):
    """Generate Google OAuth authorization URL."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_DRIVE_REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return authorization_url, state


def handle_callback(request, code):
    """Handle OAuth callback from Google."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_DRIVE_REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    
    return {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'expires_at': credentials.expiry
    }


def upload_file(connection, file_path, file_name, mime_type=None):
    """Upload a file to Google Drive."""
    service = get_google_drive_service(connection)
    
    if not service:
        raise Exception("Failed to authenticate with Google Drive")
    
    file_metadata = {'name': file_name}
    
    if mime_type:
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    else:
        media = MediaFileUpload(file_path, resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()
    
    return {
        'file_id': file.get('id'),
        'web_view_link': file.get('webViewLink'),
        'download_link': file.get('webContentLink')
    }


def delete_file(connection, file_id):
    """Delete a file from Google Drive."""
    service = get_google_drive_service(connection)
    
    if not service:
        raise Exception("Failed to authenticate with Google Drive")
    
    service.files().delete(fileId=file_id).execute()
    return True


def get_storage_info(connection):
    """Get storage quota information."""
    service = get_google_drive_service(connection)
    
    if not service:
        raise Exception("Failed to authenticate with Google Drive")
    
    about = service.about().get(fields='storageQuota').execute()
    quota = about.get('storageQuota', {})
    
    return {
        'limit': int(quota.get('limit', 0)),
        'usage': int(quota.get('usage', 0)),
        'usage_in_drive': int(quota.get('usageInDrive', 0)),
        'usage_in_drive_trash': int(quota.get('usageInDriveTrash', 0))
    }


def list_files(connection, page_size=100):
    """List files in Google Drive."""
    service = get_google_drive_service(connection)
    
    if not service:
        raise Exception("Failed to authenticate with Google Drive")
    
    results = service.files().list(
        pageSize=page_size,
        fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
    ).execute()
    
    return results.get('files', [])
