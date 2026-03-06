web: gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 4
worker: celery -A core worker --loglevel=info
beat: celery -A core beat --loglevel=info
