#!/usr/bin/env python3
"""
Local folder monitoring script for CloudStorage Manager.

This script monitors a local folder for new files and automatically:
1. Compresses images
2. Uploads to the Django backend
3. Syncs to connected cloud providers

Usage:
    python folder_monitor.py --folder /path/to/watch --api-url http://localhost:8000 --token YOUR_API_TOKEN
"""

import os
import sys
import time
import argparse
import logging
import requests
from pathlib import Path
from datetime import datetime

# Try to import watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not installed. Falling back to polling mode.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('folder_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class FileHandler(FileSystemEventHandler):
    """Handle file system events."""
    
    def __init__(self, api_url, api_token, compress=True, recursive=True):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.compress = compress
        self.recursive = recursive
        self.processed_files = set()
        
    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Avoid processing the same file multiple times
        if file_path in self.processed_files:
            return
        
        # Wait for file to be completely written
        time.sleep(1)
        
        self.process_file(file_path)
    
    def process_file(self, file_path):
        """Process a single file."""
        try:
            file_path = Path(file_path)
            
            # Skip temporary files
            if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
                return
            
            # Skip directories
            if file_path.is_dir():
                return
            
            logger.info(f"Processing file: {file_path}")
            
            # Check if file is an image
            is_image = file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            
            # Upload file to API
            self.upload_file(file_path, is_image)
            
            self.processed_files.add(str(file_path))
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def upload_file(self, file_path, is_image):
        """Upload file to the Django API."""
        try:
            url = f"{self.api_url}/storage/ajax/upload/"
            
            headers = {
                'Authorization': f'Token {self.api_token}'
            }
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                data = {'compress': 'true' if (is_image and self.compress) else 'false'}
                
                response = requests.post(url, files=files, data=data, headers=headers, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Successfully uploaded: {file_path.name}")
                    
                    # Optionally move to processed folder
                    self.move_to_processed(file_path)
                else:
                    logger.error(f"Upload failed: {result.get('error', 'Unknown error')}")
            else:
                logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
    
    def move_to_processed(self, file_path):
        """Move processed file to a 'processed' subfolder."""
        try:
            processed_dir = file_path.parent / 'processed'
            processed_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            
            file_path.rename(processed_dir / new_name)
            logger.info(f"Moved to processed: {new_name}")
            
        except Exception as e:
            logger.warning(f"Could not move file to processed folder: {e}")


class PollingMonitor:
    """Fallback polling-based file monitor."""
    
    def __init__(self, folder_path, handler, interval=5):
        self.folder_path = Path(folder_path)
        self.handler = handler
        self.interval = interval
        self.known_files = set()
        
    def start(self):
        """Start polling."""
        logger.info(f"Starting polling monitor for: {self.folder_path}")
        
        # Initial scan
        self.scan_folder()
        
        try:
            while True:
                time.sleep(self.interval)
                self.scan_folder()
        except KeyboardInterrupt:
            logger.info("Polling monitor stopped")
    
    def scan_folder(self):
        """Scan folder for new files."""
        current_files = set()
        
        for file_path in self.folder_path.rglob('*'):
            if file_path.is_file():
                current_files.add(str(file_path))
        
        # Find new files
        new_files = current_files - self.known_files
        
        for file_path in new_files:
            self.handler.process_file(file_path)
        
        self.known_files = current_files


def get_api_token(username, password, api_url):
    """Get API token using credentials."""
    try:
        url = f"{api_url}/api/auth/token/"
        response = requests.post(url, data={'username': username, 'password': password})
        
        if response.status_code == 200:
            return response.json().get('token')
        else:
            logger.error(f"Failed to get token: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting token: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Monitor folder for new files and upload to CloudStorage Manager')
    parser.add_argument('--folder', '-f', required=True, help='Folder path to monitor')
    parser.add_argument('--api-url', '-u', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--token', '-t', help='API token (or use --username and --password)')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    parser.add_argument('--no-compress', action='store_true', help='Disable image compression')
    parser.add_argument('--non-recursive', action='store_true', help='Monitor only top-level folder')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Polling interval in seconds (for polling mode)')
    
    args = parser.parse_args()
    
    # Validate folder
    folder_path = Path(args.folder)
    if not folder_path.exists():
        logger.error(f"Folder does not exist: {folder_path}")
        sys.exit(1)
    
    if not folder_path.is_dir():
        logger.error(f"Path is not a directory: {folder_path}")
        sys.exit(1)
    
    # Get API token
    api_token = args.token
    if not api_token and args.username and args.password:
        api_token = get_api_token(args.username, args.password, args.api_url)
    
    if not api_token:
        logger.error("API token required. Provide --token or --username and --password")
        sys.exit(1)
    
    # Create handler
    handler = FileHandler(
        api_url=args.api_url,
        api_token=api_token,
        compress=not args.no_compress,
        recursive=not args.non_recursive
    )
    
    # Start monitoring
    if WATCHDOG_AVAILABLE:
        logger.info(f"Starting watchdog monitor for: {folder_path}")
        
        observer = Observer()
        observer.schedule(handler, str(folder_path), recursive=not args.non_recursive)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Monitor stopped")
        
        observer.join()
    else:
        # Fallback to polling
        monitor = PollingMonitor(folder_path, handler, interval=args.interval)
        monitor.start()


if __name__ == '__main__':
    main()
