# core/settings.py

import os

# Standard local hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Dynamically add the Render domain assigned to your web service
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# ... (rest of your settings)