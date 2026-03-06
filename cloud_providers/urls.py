"""
URL patterns for cloud_providers app.
"""
from django.urls import path
from . import views

app_name = 'cloud_providers'

urlpatterns = [
    path('', views.provider_list, name='provider_list'),
    path('connect/<str:provider_name>/', views.connect_provider, name='connect'),
    path('callback/google/', views.oauth_callback, {'provider_name': 'google_drive'}, name='google_callback'),
    path('callback/dropbox/', views.oauth_callback, {'provider_name': 'dropbox'}, name='dropbox_callback'),
    path('callback/onedrive/', views.oauth_callback, {'provider_name': 'onedrive'}, name='onedrive_callback'),
    path('mega/connect/', views.mega_connect, name='mega_connect'),
    path('disconnect/<int:connection_id>/', views.disconnect_provider, name='disconnect'),
    path('connection/<int:connection_id>/', views.connection_detail, name='connection_detail'),
    path('connection/<int:connection_id>/sync/', views.sync_storage, name='sync_storage'),
    path('upload-status/<int:upload_id>/', views.upload_status, name='upload_status'),
    path('files/', views.cloud_files, name='cloud_files'),
]
