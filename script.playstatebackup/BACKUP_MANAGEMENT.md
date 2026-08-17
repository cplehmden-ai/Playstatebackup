# Backup Management System

## Overview

The backup management system organizes playstate backups into daily folders and implements automatic version control and retention policies.

## Directory Structure

```
backup_folder/
├── 2025-08-15/
│   ├── movies.json
│   ├── episodes.json
│   └── musicvideos.json
├── 2025-08-16/
│   ├── movies.json
│   ├── episodes.json
│   ├── musicvideos.json
│   └── videos.json
└── 2025-08-17/
    ├── movies.json
    └── episodes.json
```

## Features

### 1. Daily Folder Organization
- Each day gets its own folder named `YYYY-MM-DD`
- All backups created on the same day are stored in the same folder
- Makes it easy to restore to a specific date

### 2. Version Control Per Day
- **Maximum 2 backup versions per day** are kept
- When a 3rd backup is created on the same day, the oldest one is automatically deleted
- This saves storage while keeping multiple snapshots during a Kodi session
- Useful for background scheduled backups (e.g., every 60 minutes)

### 3. Retention Policy
- User can configure how many **days** of backups to keep
- Default: 7 days
- Daily folders older than the retention period are automatically deleted
- Cleanup happens on the **first backup of the day**

### 4. Automatic Cleanup

#### Daily Cleanup (runs once per day):
```python
BackupManager.should_run_daily_cleanup()      # Check if first backup of day
BackupManager.cleanup_old_daily_folders()     # Remove folders older than retention days
```

#### Version Cleanup (runs after each backup):
```python
BackupManager.cleanup_backup_versions_for_date()  # Keep only 2 versions per day
```

## Configuration

### User Settings

In Kodi addon settings:
- **Backup Folder**: Where to store all backups (default: `~/.kodi/addon_data/script.playstatebackup/`)
- **Backup Retention (Days)**: How many days of backups to keep (default: 7)

Example retention scenarios:
- 7 days: Keep backups from this week
- 30 days: Keep a month of backups
- 1 day: Keep only today's backups

## Usage

### Basic Backup (automatic)
```python
from lib.backup import Backup
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC

rpc = JsonRPC()
videodb = VideoDB(rpc)
backup = Backup(rpc, videodb)

# Backup methods automatically use daily folders and cleanup
backup.backup_movies()      # Saved to today's folder
backup.backup_episodes()    # Automatic version & retention cleanup
backup.backup_videos()
```

### Manual Backup Management
```python
from lib.backup_manager import BackupManager

manager = BackupManager()

# Get backup folder for a specific date
folder = manager.get_backup_folder_for_date("2025-08-15")

# Ensure folder exists
folder = manager.ensure_backup_folder_for_date()

# Get all daily folders (sorted newest first)
all_folders = manager.get_all_daily_folders()
for date, path in all_folders:
    print(f"{date}: {path}")

# Manual cleanup
manager.cleanup_backup_versions_for_date()      # Keep 2 per day
manager.cleanup_old_daily_folders()             # Remove old days
```

## Storage Example

With retention of 7 days and 2 versions per day:
- Minimum storage: 2 files/day × 7 days = 14 backup files
- Maximum daily growth: ~2 new backups per day

### Scenario: Scheduled backups every 60 minutes

**Day 1 (continuous Kodi session with hourly backups):**
- 06:00 - movies.json, episodes.json, videos.json (kept)
- 07:00 - movies.json, episodes.json, videos.json (old 06:00 deleted, keep 07:00)
- 08:00 - Same pattern... (old 07:00 deleted, keep 08:00)
- Result: End of day has only 2 most recent backups

**Day 7 (oldest day in retention):**
- Has 2 backup versions
- On Day 8, when first backup runs, Day 1 folder is deleted
- Result: Always maintain 7 days of history

## Benefits

1. **Space Efficient**: Keep multiple versions without exponential storage growth
2. **Granular History**: Can restore to any day within retention period
3. **Multiple Snapshots**: 2 versions per day captures session changes
4. **Automatic Maintenance**: No manual cleanup needed
5. **Background Ready**: Designed for periodic unattended backups

## Logging

All operations are logged:
```
INFO: Created backup folder: /path/to/backup/2025-08-17
INFO: Saved 'movies.json' to 2025-08-17
INFO: Version cleanup: kept 2 most recent backups for 2025-08-17
INFO: Running daily backup cleanup...
INFO: Deleted old backup folder: 2025-08-10
INFO: Cleanup complete: deleted 1 old backup folders
```

## Edge Cases

### First backup of the day
- Folder is created automatically
- Daily retention check runs
- Cleanup happens on first backup (fast operation)

### No backups needed
- If playcount and resume position are both 0, no backup entry is created
- Empty daily folders may exist but cleanup still works

### Manual folder deletion
- If user manually deletes a daily folder, the system handles it gracefully
- Cleanup operations skip missing folders

### Configuration changes
- Changing retention days takes effect on next backup
- Existing old folders are cleaned up on next daily run
