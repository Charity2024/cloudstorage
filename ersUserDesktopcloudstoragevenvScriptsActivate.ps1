warning: in the working copy of 'storage/forms.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/storage/forms.py b/storage/forms.py[m
[1mindex 82ddf03..9d6905a 100644[m
[1m--- a/storage/forms.py[m
[1m+++ b/storage/forms.py[m
[36m@@ -33,12 +33,21 @@[m [mclass FolderCreateForm(forms.ModelForm):[m
 [m
 [m
 class FileUploadForm(forms.ModelForm):[m
[32m+[m[32m    # Fix: Define the field without 'multiple' in the attrs initially[m
[32m+[m[32m    file = forms.FileField([m
[32m+[m[32m        widget=forms.FileInput(attrs={[m
[32m+[m[32m            'class': 'form-control',[m
[32m+[m[32m        }),[m
[32m+[m[32m        help_text="Select one or more files"[m
[32m+[m[32m    )[m
[32m+[m[41m    [m
     folder = forms.ModelChoiceField([m
         queryset=Folder.objects.none(),[m
         required=False,[m
         empty_label="Root (no folder)",[m
         widget=forms.Select(attrs={'class': 'form-select'})[m
     )[m
[32m+[m[41m    [m
     compress = forms.BooleanField([m
         required=False,[m
         initial=True,[m
[36m@@ -49,16 +58,12 @@[m [mclass FileUploadForm(forms.ModelForm):[m
     class Meta:[m
         model = File[m
         fields = ['file', 'folder', 'compress'][m
[31m-        widgets = {[m
[31m-            'file': forms.ClearableFileInput(attrs={[m
[31m-                'class': 'form-control',[m
[31m-                'multiple': True[m
[31m-            })[m
[31m-        }[m
     [m
     def __init__(self, user, *args, **kwargs):[m
         super().__init__(*args, **kwargs)[m
         self.fields['folder'].queryset = Folder.objects.filter(owner=user)[m
[32m+[m[32m        # Fix: Manually inject the 'multiple' attribute to bypass the ValueError[m
[32m+[m[32m        self.fields['file'].widget.attrs.update({'multiple': 'multiple'})[m
         self.user = user[m
 [m
 [m
[36m@@ -100,10 +105,10 @@[m [mclass FolderRenameForm(forms.ModelForm):[m
 [m
 [m
 class BulkUploadForm(forms.Form):[m
[32m+[m[32m    # Fix: Same pattern here - move 'multiple' to __init__[m
     files = forms.FileField([m
[31m-        widget=forms.ClearableFileInput(attrs={[m
[32m+[m[32m        widget=forms.FileInput(attrs={[m
             'class': 'form-control',[m
[31m-            'multiple': True,[m
             'accept': 'image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.zip,.rar'[m
         }),[m
         help_text="Select multiple files to upload"[m
[36m@@ -124,3 +129,5 @@[m [mclass BulkUploadForm(forms.Form):[m
     def __init__(self, user, *args, **kwargs):[m
         super().__init__(*args, **kwargs)[m
         self.fields['folder'].queryset = Folder.objects.filter(owner=user)[m
[32m+[m[32m        # Fix: Manually inject 'multiple'[m
[32m+[m[32m        self.fields['files'].widget.attrs.update({'multiple': 'multiple'})[m
\ No newline at end of file[m
