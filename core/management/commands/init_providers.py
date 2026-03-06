"""
Initialize cloud providers in the database.
"""
from django.core.management.base import BaseCommand
from cloud_providers.models import CloudProvider


class Command(BaseCommand):
    help = 'Initialize default cloud providers'

    def handle(self, *args, **options):
        providers = [
            {
                'name': 'google_drive',
                'display_name': 'Google Drive',
                'icon': 'bi-google',
                'description': '15 GB free storage. Great for documents, photos, and videos.'
            },
            {
                'name': 'dropbox',
                'display_name': 'Dropbox',
                'icon': 'bi-dropbox',
                'description': '2 GB free storage. Excellent for file sharing and collaboration.'
            },
            {
                'name': 'onedrive',
                'display_name': 'OneDrive',
                'icon': 'bi-microsoft',
                'description': '5 GB free storage. Best for Microsoft Office users.'
            },
            {
                'name': 'mega',
                'display_name': 'MEGA',
                'icon': 'bi-cloud',
                'description': '20 GB free storage. End-to-end encryption for maximum privacy.'
            },
        ]
        
        for provider_data in providers:
            provider, created = CloudProvider.objects.get_or_create(
                name=provider_data['name'],
                defaults={
                    'display_name': provider_data['display_name'],
                    'icon': provider_data['icon'],
                    'description': provider_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created provider: {provider.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Provider already exists: {provider.display_name}')
                )
        
        self.stdout.write(self.style.SUCCESS('Cloud providers initialized successfully!'))
