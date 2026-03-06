"""
User Profile model extending Django's User.
"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    storage_quota_gb = models.DecimalField(max_digits=10, decimal_places=2, default=15.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    @property
    def used_storage_gb(self):
        """Calculate total storage used by user across all files."""
        from storage.models import File
        total_bytes = File.objects.filter(owner=self.user).aggregate(
            total=models.Sum('file_size')
        )['total'] or 0
        return total_bytes / (1024 ** 3)
    
    @property
    def storage_percentage(self):
        """Calculate percentage of storage used."""
        if self.storage_quota_gb == 0:
            return 0
        return min(100, (self.used_storage_gb / float(self.storage_quota_gb)) * 100)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
