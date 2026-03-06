FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations (will be run at startup)
# RUN python manage.py migrate

# Create media directory
RUN mkdir -p /app/media/uploads /app/media/compressed

# Expose port
EXPOSE $PORT

# Start command
CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 4
