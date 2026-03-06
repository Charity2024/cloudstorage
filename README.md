# NYOTA VAULT

A personal multi-cloud storage manager built with Django. Upload, organize, and automatically sync files across Google Drive, Dropbox, OneDrive, and MEGA - all from a single, clean web interface.

![Dashboard Preview](docs/dashboard-preview.png)

## Features

- **User Authentication**: Register, login, and manage your profile
- **File Upload**: Drag & drop interface with progress tracking
- **Image Compression**: Automatic compression to save storage space
- **Multi-Cloud Support**: Sync to Google Drive, Dropbox, OneDrive, and MEGA
- **Folder Management**: Organize files with nested folder structures
- **Dashboard**: Visual analytics and storage statistics
- **Background Tasks**: Async cloud uploads using Celery
- **Local Folder Monitor**: Python script to auto-upload from local folders
- **Responsive Design**: Bootstrap 5 interface works on all devices

## Tech Stack

- **Backend**: Django 4.2, Python 3.11
- **Frontend**: HTML, CSS, Bootstrap 5, JavaScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Task Queue**: Celery + Redis
- **Cloud APIs**: Google Drive API, Dropbox API, Microsoft Graph API, MEGA SDK

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Charity2024/cloudstorage-manager.git
cd cloudstorage-manager

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Database Setup

```bash
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Load initial cloud providers
python manage.py shell -c "from cloud_providers.models import CloudProvider; CloudProvider.objects.get_or_create(name='google_drive', defaults={'display_name': 'Google Drive', 'icon': 'bi-google'}); CloudProvider.objects.get_or_create(name='dropbox', defaults={'display_name': 'Dropbox', 'icon': 'bi-dropbox'}); CloudProvider.objects.get_or_create(name='onedrive', defaults={'display_name': 'OneDrive', 'icon': 'bi-microsoft'}); CloudProvider.objects.get_or_create(name='mega', defaults={'display_name': 'MEGA', 'icon': 'bi-cloud'})"
```

### 4. Run Development Server

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A core worker --loglevel=info

# Terminal 3: Celery beat (for scheduled tasks)
celery -A core beat --loglevel=info
```

Visit http://localhost:8000

## Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## Cloud Provider Setup

### Google Drive

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project
3. Enable Google Drive API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/cloud/google/callback/`
6. Copy Client ID and Secret to `.env`

### Dropbox

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Create a new app
3. Choose "Scoped access"
4. Add redirect URI: `http://localhost:8000/cloud/dropbox/callback/`
5. Copy App Key and Secret to `.env`

### OneDrive

1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Register a new application
3. Add platform: Web
4. Add redirect URI: `http://localhost:8000/cloud/onedrive/callback/`
5. Copy Client ID and Secret to `.env`

### MEGA

1. Create a [MEGA account](https://mega.nz)
2. Add email and password to `.env`
3. No API keys needed - uses direct login

## Folder Monitor Script

Automatically upload files from a local folder:

```bash
# Install watchdog
pip install watchdog requests

# Run monitor
python scripts/folder_monitor.py \
    --folder /path/to/watch \
    --api-url http://localhost:8000 \
    --username your_username \
    --password your_password
```

### Options

- `--folder`: Folder path to monitor
- `--api-url`: Your Django API URL
- `--token`: API token (or use username/password)
- `--no-compress`: Disable image compression
- `--non-recursive`: Monitor only top-level folder
- `--interval`: Polling interval in seconds (default: 5)

## rclone Integration

For advanced sync capabilities, use rclone:

```bash
# Install rclone
# https://rclone.org/install/

# Configure remotes
rclone config

# Sync to all remotes
python scripts/rclone_sync.py --source /path/to/files --all

# Sync to specific remote
python scripts/rclone_sync.py --source /path/to/files --dest gdrive:

# Bidirectional sync
python scripts/rclone_sync.py --source /path/to/files --dest gdrive: --bisync
```

## Production Deployment

### Railway

1. Create account at [Railway](https://railway.app)
2. Connect your GitHub repository
3. Add environment variables from `.env`
4. Deploy!

### Render

1. Create account at [Render](https://render.com)
2. Create new Web Service
3. Connect repository
4. Add environment variables
5. Deploy!

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch
fly launch

# Set secrets
fly secrets set SECRET_KEY=your-secret-key
fly secrets set DATABASE_URL=your-db-url

# Deploy
fly deploy
```

## Project Structure

```
cloudstorage/
├── core/                   # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── accounts/               # User authentication
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── storage/                # File management
│   ├── models.py
│   ├── views.py
│   ├── utils.py
│   └── urls.py
├── cloud_providers/        # Cloud integrations
│   ├── models.py
│   ├── google_drive.py
│   ├── dropbox_api.py
│   ├── onedrive_api.py
│   ├── mega_api.py
│   ├── tasks.py
│   └── urls.py
├── dashboard/              # Main dashboard
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── scripts/                # Utility scripts
│   ├── folder_monitor.py
│   └── rclone_sync.py
├── templates/              # HTML templates
│   ├── base.html
│   ├── accounts/
│   ├── storage/
│   ├── cloud_providers/
│   └── dashboard/
├── static/                 # CSS, JS, images
├── media/                  # Uploaded files
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Login page |
| `/register/` | POST | User registration |
| `/dashboard/` | GET | Main dashboard |
| `/storage/` | GET | File list |
| `/storage/upload/` | POST | Upload files |
| `/storage/folder/create/` | POST | Create folder |
| `/cloud/` | GET | Cloud providers |
| `/cloud/connect/<provider>/` | GET | Connect cloud |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (True/False) | Yes |
| `DATABASE_URL` | PostgreSQL URL (optional) | No |
| `REDIS_URL` | Redis URL for Celery | No |
| `GOOGLE_DRIVE_CLIENT_ID` | Google OAuth client ID | No |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Google OAuth secret | No |
| `DROPBOX_APP_KEY` | Dropbox app key | No |
| `DROPBOX_APP_SECRET` | Dropbox app secret | No |
| `ONEDRIVE_CLIENT_ID` | OneDrive client ID | No |
| `ONEDRIVE_CLIENT_SECRET` | OneDrive secret | No |
| `MEGA_EMAIL` | MEGA account email | No |
| `MEGA_PASSWORD` | MEGA account password | No |

## Troubleshooting

### Celery not working

```bash
# Make sure Redis is running
redis-server

# Check Celery worker logs
celery -A core worker --loglevel=debug
```

### Cloud upload fails

1. Check OAuth credentials are correct
2. Verify redirect URIs match
3. Check Celery worker is running
4. Review logs: `logs/django.log`

### Image compression not working

```bash
# Install Pillow dependencies (Ubuntu/Debian)
sudo apt-get install libjpeg-dev zlib1g-dev

# Reinstall Pillow
pip install --force-reinstall Pillow
```

## Future Improvements

- [ ] File versioning
- [ ] Sharing links with expiration
- [ ] Mobile app (React Native/Flutter)
- [ ] End-to-end encryption
- [ ] Advanced search with filters
- [ ] File preview for documents
- [ ] Team/organization support
- [ ] WebDAV support
- [ ] FTP/SFTP integration
- [ ] Bandwidth throttling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: [Report bugs](https://github.com/Charity2024/cloudstorage-manager/issues)
- Documentation: [Wiki](https://github.com/Charity2024/cloudstorage-manager/wiki)
- Discussions: [GitHub Discussions](https://github.com/Charity2024/cloudstorage-manager/discussions)

---

Made with ❤️ by Charity
