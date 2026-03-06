"""
Views for cloud provider management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import CloudProvider, CloudConnection, CloudUpload
from .google_drive import get_auth_url as get_google_auth_url, handle_callback as handle_google_callback
from .dropbox_api import get_auth_url as get_dropbox_auth_url, handle_callback as handle_dropbox_callback
from .onedrive_api import get_auth_url as get_onedrive_auth_url, handle_callback as handle_onedrive_callback
from .tasks import sync_storage_info


@login_required
def provider_list(request):
    """List all available cloud providers and user's connections."""
    providers = CloudProvider.objects.filter(is_active=True)
    connections = CloudConnection.objects.filter(user=request.user)
    
    # Get storage stats
    total_cloud_storage = sum(conn.total_storage for conn in connections)
    total_cloud_used = sum(conn.used_storage for conn in connections)
    
    context = {
        'providers': providers,
        'connections': connections,
        'total_cloud_storage': total_cloud_storage,
        'total_cloud_used': total_cloud_used,
    }
    return render(request, 'cloud_providers/provider_list.html', context)


@login_required
def connect_provider(request, provider_name):
    """Initiate OAuth flow for a cloud provider."""
    provider = get_object_or_404(CloudProvider, name=provider_name, is_active=True)
    
    # Generate authorization URL based on provider
    if provider_name == 'google_drive':
        auth_url, state = get_google_auth_url(request)
        request.session['oauth_state'] = state
        request.session['oauth_provider'] = provider_name
        return redirect(auth_url)
    
    elif provider_name == 'dropbox':
        auth_url = get_dropbox_auth_url()
        request.session['oauth_provider'] = provider_name
        return redirect(auth_url)
    
    elif provider_name == 'onedrive':
        auth_url = get_onedrive_auth_url()
        request.session['oauth_provider'] = provider_name
        return redirect(auth_url)
    
    elif provider_name == 'mega':
        # MEGA uses username/password, not OAuth
        return redirect('cloud_providers:mega_connect')
    
    messages.error(request, 'Unknown provider.')
    return redirect('cloud_providers:provider_list')


@login_required
def oauth_callback(request, provider_name):
    """Handle OAuth callback from cloud providers."""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f'Authorization failed: {error}')
        return redirect('cloud_providers:provider_list')
    
    if not code:
        messages.error(request, 'Authorization code not received.')
        return redirect('cloud_providers:provider_list')
    
    try:
        provider = CloudProvider.objects.get(name=provider_name)
        
        # Get tokens based on provider
        if provider_name == 'google_drive':
            tokens = handle_google_callback(request, code)
        elif provider_name == 'dropbox':
            tokens = handle_dropbox_callback(request, code)
        elif provider_name == 'onedrive':
            tokens = handle_onedrive_callback(code)
        else:
            raise Exception("Unknown provider")
        
        # Create or update connection
        connection, created = CloudConnection.objects.update_or_create(
            user=request.user,
            provider=provider,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': tokens.get('refresh_token', ''),
                'is_connected': True,
                'provider_email': tokens.get('email', '')
            }
        )
        
        # Sync storage info
        sync_storage_info.delay(connection.id)
        
        messages.success(request, f'Successfully connected to {provider.display_name}!')
        
    except Exception as e:
        messages.error(request, f'Connection failed: {str(e)}')
    
    return redirect('cloud_providers:provider_list')


@login_required
def disconnect_provider(request, connection_id):
    """Disconnect a cloud provider."""
    connection = get_object_or_404(CloudConnection, id=connection_id, user=request.user)
    
    if request.method == 'POST':
        provider_name = connection.provider.display_name
        connection.is_connected = False
        connection.access_token = ''
        connection.refresh_token = ''
        connection.save()
        messages.success(request, f'Disconnected from {provider_name}.')
        return redirect('cloud_providers:provider_list')
    
    return render(request, 'cloud_providers/disconnect_confirm.html', {'connection': connection})


@login_required
def connection_detail(request, connection_id):
    """View details of a cloud connection."""
    connection = get_object_or_404(CloudConnection, id=connection_id, user=request.user)
    uploads = CloudUpload.objects.filter(connection=connection)[:50]
    
    context = {
        'connection': connection,
        'uploads': uploads,
    }
    return render(request, 'cloud_providers/connection_detail.html', context)


@login_required
def sync_storage(request, connection_id):
    """Manually trigger storage sync."""
    connection = get_object_or_404(CloudConnection, id=connection_id, user=request.user)
    
    sync_storage_info.delay(connection.id)
    messages.info(request, 'Storage sync queued. Refresh the page in a moment to see updated stats.')
    
    return redirect('cloud_providers:connection_detail', connection_id=connection.id)


@login_required
def upload_status(request, upload_id):
    """Get upload status via AJAX."""
    upload = get_object_or_404(CloudUpload, id=upload_id, file__owner=request.user)
    
    return JsonResponse({
        'id': upload.id,
        'status': upload.status,
        'provider': upload.connection.provider.display_name,
        'file_name': upload.file.name,
        'retry_count': upload.retry_count,
        'provider_url': upload.provider_file_url,
        'created_at': upload.created_at.isoformat(),
        'completed_at': upload.completed_at.isoformat() if upload.completed_at else None
    })


@login_required
def mega_connect(request):
    """Handle MEGA connection (uses email/password)."""
    from django.conf import settings
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            from .mega_api import get_mega_client
            
            # Test connection
            m = get_mega_client()
            
            provider = CloudProvider.objects.get(name='mega')
            
            connection, created = CloudConnection.objects.update_or_create(
                user=request.user,
                provider=provider,
                defaults={
                    'access_token': 'connected',
                    'is_connected': True,
                    'provider_email': email
                }
            )
            
            sync_storage_info.delay(connection.id)
            
            messages.success(request, 'Successfully connected to MEGA!')
            return redirect('cloud_providers:provider_list')
            
        except Exception as e:
            messages.error(request, f'MEGA connection failed: {str(e)}')
    
    return render(request, 'cloud_providers/mega_connect.html')


@login_required
def cloud_files(request):
    """View files across all cloud providers."""
    uploads = CloudUpload.objects.filter(
        file__owner=request.user
    ).select_related('file', 'connection', 'connection__provider')
    
    # Filter by provider
    provider_filter = request.GET.get('provider')
    if provider_filter:
        uploads = uploads.filter(connection__provider__name=provider_filter)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        uploads = uploads.filter(status=status_filter)
    
    context = {
        'uploads': uploads,
        'providers': CloudProvider.objects.filter(is_active=True),
    }
    return render(request, 'cloud_providers/cloud_files.html', context)
