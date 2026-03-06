"""
URL patterns for storage app.
"""
from django.urls import path
from . import views

app_name = 'storage'

urlpatterns = [
    # File URLs
    path('', views.file_list, name='file_list'),
    path('upload/', views.file_upload, name='file_upload'),
    path('bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('file/<int:pk>/', views.file_detail, name='file_detail'),
    path('file/<int:pk>/download/', views.file_download, name='file_download'),
    path('file/<int:pk>/delete/', views.file_delete, name='file_delete'),
    path('file/<int:pk>/move/', views.file_move, name='file_move'),
    path('file/<int:pk>/rename/', views.file_rename, name='file_rename'),
    
    # Folder URLs
    path('folder/create/', views.folder_create, name='folder_create'),
    path('folder/<int:pk>/', views.folder_detail, name='folder_detail'),
    path('folder/<int:pk>/rename/', views.folder_rename, name='folder_rename'),
    path('folder/<int:pk>/delete/', views.folder_delete, name='folder_delete'),
    
    # AJAX endpoints
    path('ajax/upload/', views.ajax_upload, name='ajax_upload'),
    path('ajax/search/', views.ajax_file_search, name='ajax_file_search'),
]
