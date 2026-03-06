"""
Forms for file and folder management.
"""
from django import forms
from .models import Folder, File


class FolderCreateForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Folder name'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Folder.objects.filter(owner=user)
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "Root (no parent)"
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if '/' in name or '\\' in name:
            raise forms.ValidationError("Folder name cannot contain slashes.")
        return name


class FileUploadForm(forms.ModelForm):
    # Fix: Define the field without 'multiple' in the attrs initially
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
        }),
        help_text="Select one or more files"
    )
    
    folder = forms.ModelChoiceField(
        queryset=Folder.objects.none(),
        required=False,
        empty_label="Root (no folder)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    compress = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Compress images to save storage space"
    )
    
    class Meta:
        model = File
        fields = ['file', 'folder', 'compress']
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(owner=user)
        # Fix: Manually inject the 'multiple' attribute to bypass the ValueError
        self.fields['file'].widget.attrs.update({'multiple': 'multiple'})
        self.user = user


class FileMoveForm(forms.Form):
    target_folder = forms.ModelChoiceField(
        queryset=Folder.objects.none(),
        required=False,
        empty_label="Root",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_folder'].queryset = Folder.objects.filter(owner=user)


class FileRenameForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'New file name'
            })
        }


class FolderRenameForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'New folder name'
            })
        }


class BulkUploadForm(forms.Form):
    # Fix: Same pattern here - move 'multiple' to __init__
    files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.zip,.rar'
        }),
        help_text="Select multiple files to upload"
    )
    folder = forms.ModelChoiceField(
        queryset=Folder.objects.none(),
        required=False,
        empty_label="Root (no folder)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    auto_compress = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Automatically compress images"
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(owner=user)
        # Fix: Manually inject 'multiple'
        self.fields['files'].widget.attrs.update({'multiple': 'multiple'})