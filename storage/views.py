"""
Views for file and folder management.
"""
import os
import magic
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import Folder, File
from .forms import (
    FolderCreateForm, FileUploadForm, FileMoveForm,
    FileRenameForm, FolderRenameForm, BulkUploadForm
)
from .utils import compress_file, format_file_size, get_file_type
from cloud_providers.tasks import upload_file_to_cloud


@login_required
def file_list(request):
    """Display all files for the current user."""
    files = File.objects.filter(owner=request.user)
    folders = Folder.objects.filter(owner=request.user, parent=None)
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        files = files.filter(
            Q(name__icontains=query) | 
            Q(original_name__icontains=query)
        )
    
    # Filter by file type
    file_type = request.GET.get('type')
    if file_type:
        files = files.filter(file_type=file_type)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    files = files.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(files, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'files': page_obj,
        'folders': folders,
        'page_obj': page_obj,
        'query': query,
        'file_type': file_type,
        'sort_by': sort_by,
        'total_files': files.count(),
        'total_size': files.aggregate(total=Sum('file_size'))['total'] or 0,
    }
    return render(request, 'storage/file_list.html', context)


@login_required
def folder_detail(request, pk):
    """Display folder contents."""
    folder = get_object_or_404(Folder, pk=pk, owner=request.user)
    files = File.objects.filter(folder=folder, owner=request.user)
    subfolders = Folder.objects.filter(parent=folder, owner=request.user)
    
    context = {
        'folder': folder,
        'files': files,
        'subfolders': subfolders,
        'breadcrumbs': get_breadcrumbs(folder),
    }
    return render(request, 'storage/folder_detail.html', context)


@login_required
def folder_create(request):
    """Create a new folder."""
    if request.method == 'POST':
        form = FolderCreateForm(request.user, request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.owner = request.user
            folder.save()
            messages.success(request, f'Folder "{folder.name}" created successfully!')
            return redirect('storage:folder_detail', pk=folder.pk) if folder.parent else redirect('storage:file_list')
    else:
        form = FolderCreateForm(request.user)
    
    return render(request, 'storage/folder_form.html', {'form': form, 'action': 'Create'})


@login_required
def folder_rename(request, pk):
    """Rename a folder."""
    folder = get_object_or_404(Folder, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = FolderRenameForm(request.POST, instance=folder)
        if form.is_valid():
            form.save()
            messages.success(request, 'Folder renamed successfully!')
            return redirect('storage:folder_detail', pk=folder.pk) if folder.parent else redirect('storage:file_list')
    else:
        form = FolderRenameForm(instance=folder)
    
    return render(request, 'storage/folder_form.html', {'form': form, 'action': 'Rename', 'folder': folder})


@login_required
def folder_delete(request, pk):
    """Delete a folder and all its contents."""
    folder = get_object_or_404(Folder, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        parent = folder.parent
        folder_name = folder.name
        folder.delete()
        messages.success(request, f'Folder "{folder_name}" deleted successfully!')
        return redirect('storage:folder_detail', pk=parent.pk) if parent else redirect('storage:file_list')
    
    return render(request, 'storage/folder_confirm_delete.html', {'folder': folder})


@login_required
def file_upload(request):
    """Handle multiple file uploads with optional compression."""
    if request.method == 'POST':
        form = FileUploadForm(request.user, request.POST, request.FILES)
        files = request.FILES.getlist('file')
        folder_id = request.POST.get('folder')
        compress = request.POST.get('compress') in ['on', 'true', '1', 'yes']
        
        folder = None
        if folder_id:
            folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)
        
        uploaded_count = 0
        if files:
            for uploaded_file in files:
                try:
                    mime_type = get_file_type(uploaded_file.temporary_file_path())
                except (AttributeError, ValueError):
                    mime_type = uploaded_file.content_type or 'application/octet-stream'
                
                file_instance = File(
                    name=uploaded_file.name,
                    original_name=uploaded_file.name,
                    file=uploaded_file,
                    mime_type=mime_type,
                    file_size=uploaded_file.size,
                    folder=folder,
                    owner=request.user
                )
                file_instance.save()
                
                # Use direct attribute access instead of getattr
                if compress and file_instance.file_type == 'image':
                    compress_file(file_instance)
                
                upload_file_to_cloud.delay(file_instance.id)
                uploaded_count += 1
            
            messages.success(request, f'{uploaded_count} file(s) uploaded successfully!')
        else:
            messages.error(request, "No files selected.")

        if folder:
            return redirect('storage:folder_detail', pk=folder.pk)
        return redirect('storage:file_list')
    else:
        form = FileUploadForm(request.user)
    
    return render(request, 'storage/file_upload.html', {'form': form})


@login_required
def file_detail(request, pk):
    """Display file details."""
    file = get_object_or_404(File, pk=pk, owner=request.user)
    cloud_uploads = file.cloud_uploads.all()
    
    context = {
        'file': file,
        'cloud_uploads': cloud_uploads,
        'download_url': request.build_absolute_uri(file.file.url) if file.file else "#",
    }
    return render(request, 'storage/file_detail.html', context)


@login_required
def file_download(request, pk):
    """Download a file."""
    file = get_object_or_404(File, pk=pk, owner=request.user)
    
    if not file.file or not file.file.name:
        messages.error(request, "File not found or has been deleted.")
        if file.folder:
            return redirect('storage:folder_detail', pk=file.folder.pk)
        return redirect('storage:file_list')
    
    response = FileResponse(file.file, as_attachment=True, filename=file.original_name)
    return response


@login_required
def file_delete(request, pk):
    """Delete a file."""
    file = get_object_or_404(File, pk=pk, owner=request.user)
    folder = file.folder
    
    if request.method == 'POST':
        file_name = file.name
        file.delete()
        messages.success(request, f'File "{file_name}" deleted successfully!')
        if folder:
            return redirect('storage:folder_detail', pk=folder.pk)
        return redirect('storage:file_list')
    
    return render(request, 'storage/file_confirm_delete.html', {'file': file})


@login_required
def file_move(request, pk):
    """Move a file to another folder."""
    file = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = FileMoveForm(request.user, request.POST)
        if form.is_valid():
            target_folder = form.cleaned_data['target_folder']
            file.folder = target_folder
            file.save()
            messages.success(request, 'File moved successfully!')
            if target_folder:
                return redirect('storage:folder_detail', pk=target_folder.pk)
            return redirect('storage:file_list')
    else:
        form = FileMoveForm(request.user)
    
    return render(request, 'storage/file_move.html', {'form': form, 'file': file})


@login_required
def file_rename(request, pk):
    """Rename a file."""
    file = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = FileRenameForm(request.POST, instance=file)
        if form.is_valid():
            form.save()
            messages.success(request, 'File renamed successfully!')
            return redirect('storage:file_detail', pk=file.pk)
    else:
        form = FileRenameForm(instance=file)
    
    return render(request, 'storage/file_rename.html', {'form': form, 'file': file})


@login_required
def bulk_upload(request):
    """Handle bulk file uploads."""
    if request.method == 'POST':
        form = BulkUploadForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            folder = form.cleaned_data['folder']
            auto_compress = form.cleaned_data['auto_compress']
            
            uploaded_count = 0
            for uploaded_file in files:
                file_instance = File(
                    name=uploaded_file.name,
                    original_name=uploaded_file.name,
                    file=uploaded_file,
                    mime_type=uploaded_file.content_type or 'application/octet-stream',
                    file_size=uploaded_file.size,
                    folder=folder,
                    owner=request.user
                )
                file_instance.save()
                
                # Use direct attribute access instead of getattr
                if auto_compress and file_instance.file_type == 'image':
                    compress_file(file_instance)
                
                upload_file_to_cloud.delay(file_instance.id)
                uploaded_count += 1
            
            messages.success(request, f'{uploaded_count} file(s) uploaded successfully!')
            return redirect('storage:file_list')
    else:
        form = BulkUploadForm(request.user)
    
    return render(request, 'storage/bulk_upload.html', {'form': form})


def get_breadcrumbs(folder):
    """Generate breadcrumb trail for a folder."""
    breadcrumbs = []
    current = folder
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent
    return breadcrumbs


@login_required
@require_POST
def ajax_upload(request):
    """AJAX endpoint for file uploads."""
    if request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        folder_id = request.POST.get('folder')
        compress = request.POST.get('compress') in ['true', '1', 'yes', 'on']
        
        folder = None
        if folder_id:
            folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)
        
        file_instance = File(
            name=uploaded_file.name,
            original_name=uploaded_file.name,
            file=uploaded_file,
            mime_type=uploaded_file.content_type or 'application/octet-stream',
            file_size=uploaded_file.size,
            folder=folder,
            owner=request.user
        )
        file_instance.save()
        
        # Use direct attribute access instead of getattr
        if compress and file_instance.file_type == 'image':
            compress_file(file_instance)
        
        upload_file_to_cloud.delay(file_instance.id)
        
        return JsonResponse({
            'success': True,
            'file_id': file_instance.id,
            'file_name': file_instance.name,
            'file_size': format_file_size(file_instance.file_size),
            'file_type': file_instance.file_type
        })
    return JsonResponse({'success': False, 'error': 'No file provided'})


@login_required
def ajax_file_search(request):
    """AJAX endpoint for file search."""
    query = request.GET.get('q', '')
    files = File.objects.filter(owner=request.user).filter(
        Q(name__icontains=query) | Q(original_name__icontains=query)
    )[:10]
    
    results = [{
        'id': f.id,
        'name': f.name,
        'type': f.file_type,
        'size': format_file_size(f.file_size),
        'url': f.get_absolute_url()
    } for f in files]
    
    return JsonResponse({'results': results})
