#!/usr/bin/env python3
"""
rclone-based sync script for CloudStorage Manager.

This script uses rclone to sync files to multiple cloud providers.
rclone must be installed and configured separately.

Installation:
    https://rclone.org/install/

Configuration:
    rclone config

Usage:
    python rclone_sync.py --source /path/to/files --dest remote:bucket/folder
"""

import os
import sys
import argparse
import subprocess
import logging
import json
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rclone_sync.log')
    ]
)
logger = logging.getLogger(__name__)


def check_rclone():
    """Check if rclone is installed."""
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def list_remotes():
    """List configured rclone remotes."""
    try:
        result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
        if result.returncode == 0:
            return [r.strip() for r in result.stdout.strip().split('\n') if r.strip()]
        return []
    except Exception as e:
        logger.error(f"Error listing remotes: {e}")
        return []


def sync_to_remote(source, remote, folder='', dry_run=False, delete_excluded=False):
    """Sync local folder to remote."""
    try:
        dest = f"{remote}{folder}"
        
        cmd = ['rclone', 'sync', str(source), dest, '-v', '--progress']
        
        if dry_run:
            cmd.append('--dry-run')
        
        if delete_excluded:
            cmd.append('--delete-excluded')
        
        # Add common filters
        cmd.extend([
            '--exclude', '.DS_Store',
            '--exclude', 'Thumbs.db',
            '--exclude', '*.tmp',
            '--exclude', 'processed/',
        ])
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Sync completed successfully to {remote}")
            return True
        else:
            logger.error(f"Sync failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        return False


def copy_to_remote(source, remote, folder='', dry_run=False):
    """Copy files to remote (without deleting)."""
    try:
        dest = f"{remote}{folder}"
        
        cmd = ['rclone', 'copy', str(source), dest, '-v', '--progress']
        
        if dry_run:
            cmd.append('--dry-run')
        
        # Add common filters
        cmd.extend([
            '--exclude', '.DS_Store',
            '--exclude', 'Thumbs.db',
            '--exclude', '*.tmp',
        ])
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Copy completed successfully to {remote}")
            return True
        else:
            logger.error(f"Copy failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error during copy: {e}")
        return False


def get_remote_size(remote, folder=''):
    """Get size of remote folder."""
    try:
        path = f"{remote}{folder}"
        
        result = subprocess.run(
            ['rclone', 'size', path, '--json'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data
        return None
        
    except Exception as e:
        logger.error(f"Error getting remote size: {e}")
        return None


def bisync(source, remote, folder='', dry_run=False):
    """Bidirectional sync between local and remote."""
    try:
        dest = f"{remote}{folder}"
        
        cmd = ['rclone', 'bisync', str(source), dest, '-v', '--progress']
        
        if dry_run:
            cmd.append('--dry-run')
        
        # Add common filters
        cmd.extend([
            '--exclude', '.DS_Store',
            '--exclude', 'Thumbs.db',
            '--exclude', '*.tmp',
        ])
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Bisync completed successfully with {remote}")
            return True
        else:
            logger.error(f"Bisync failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error during bisync: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Sync files to cloud using rclone')
    parser.add_argument('--source', '-s', required=True, help='Source folder path')
    parser.add_argument('--dest', '-d', help='Destination remote (e.g., gdrive:, dropbox:, etc.)')
    parser.add_argument('--folder', '-f', default='', help='Destination folder path on remote')
    parser.add_argument('--list-remotes', '-l', action='store_true', help='List configured remotes')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Perform a trial run with no changes')
    parser.add_argument('--copy', '-c', action='store_true', help='Copy only (no delete)')
    parser.add_argument('--bisync', '-b', action='store_true', help='Bidirectional sync')
    parser.add_argument('--delete-excluded', action='store_true', help='Delete files not in source')
    parser.add_argument('--all', '-a', action='store_true', help='Sync to all configured remotes')
    
    args = parser.parse_args()
    
    # Check rclone
    if not check_rclone():
        logger.error("rclone is not installed. Please install it first:")
        logger.error("https://rclone.org/install/")
        sys.exit(1)
    
    # List remotes
    if args.list_remotes:
        remotes = list_remotes()
        print("Configured remotes:")
        for remote in remotes:
            print(f"  - {remote}")
        return
    
    # Validate source
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source folder does not exist: {source_path}")
        sys.exit(1)
    
    # Get remotes to sync
    if args.all:
        remotes = list_remotes()
        if not remotes:
            logger.error("No remotes configured")
            sys.exit(1)
    elif args.dest:
        remotes = [args.dest]
    else:
        logger.error("Please specify --dest or --all")
        sys.exit(1)
    
    # Sync to each remote
    success_count = 0
    for remote in remotes:
        logger.info(f"Processing remote: {remote}")
        
        if args.bisync:
            if bisync(source_path, remote, args.folder, args.dry_run):
                success_count += 1
        elif args.copy:
            if copy_to_remote(source_path, remote, args.folder, args.dry_run):
                success_count += 1
        else:
            if sync_to_remote(source_path, remote, args.folder, args.dry_run, args.delete_excluded):
                success_count += 1
    
    logger.info(f"Completed: {success_count}/{len(remotes)} remotes synced successfully")


if __name__ == '__main__':
    main()
