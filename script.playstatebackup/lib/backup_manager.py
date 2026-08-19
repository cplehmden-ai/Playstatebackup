from datetime import datetime
import xbmcvfs
import xbmcaddon
from lib.logger import log_debug, log_error
from lib.utils import normalize


class BackupManager:
    """Manages backup versioning with daily folders and retention policies"""

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.backup_folder = self._get_base_backup_folder()
        self.retention_days = self._get_retention_days()

    def _join_path(self, base_path, *parts):
        """
        Join path parts with forward slashes
        Works with Kodi VFS paths (SMB, NFS, HTTP, etc.)
        """
        base = base_path.rstrip("/")
        for part in parts:
            base = base + "/" + part.lstrip("/").rstrip("/")
        return base

    def _dir_exists(self, path):
        """xbmcvfs.exists() requires a trailing slash to reliably detect folders."""
        return xbmcvfs.exists(path.rstrip("/") + "/")

    def _get_base_backup_folder(self):
        """Get the base backup folder, create default if not set"""
        backup_folder = self.addon.getSetting("backup_folder")

        if not backup_folder:
            from xbmcvfs import translatePath
            profile_path = translatePath("special://profile")
            backup_folder = self._join_path(profile_path, "addon_data", "script.playstatebackup")
            # Try to create but suppress Kodi's logging errors
            try:
                xbmcvfs.mkdirs(backup_folder)
            except:
                pass  # Suppress - folder may already exist
            self.addon.setSetting("backup_folder", backup_folder)

        return normalize(backup_folder.rstrip("/"))

    def _get_retention_days(self):
        """Get the configured retention days"""
        try:
            days = int(self.addon.getSetting("backup_retention_days"))
            return max(1, days)  # Minimum 1 day
        except (ValueError, TypeError):
            return 7  # Default to 7 days

    def get_backup_folder_for_date(self, date=None):
        """
        Get the backup folder path for a specific date (YYYY-MM-DD format)
        If date is None, uses today's date
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        folder_path = self._join_path(self.backup_folder, date)
        return normalize(folder_path)

    def ensure_backup_folder_for_date(self, date=None):
        """
        Ensure the backup folder exists for a date
        Returns the folder path
        """
        folder_path = self.get_backup_folder_for_date(date)
        
        try:
            # Try to create directory once - suppress any errors
            # Folder may already exist, or error may be cosmetic (especially with SMB)
            try:
                xbmcvfs.mkdirs(folder_path)
            except:
                pass  # Ignore - folder likely already exists or error is cosmetic
            
            return folder_path
        except Exception as e:
            log_error(f"Critical error with backup folder {folder_path}: {e}")
            return None

    def get_all_daily_folders(self):
        """
        Get all daily backup folders sorted by date (newest first)
        Returns list of tuples: [(date_string, folder_path), ...]
        """
        try:
            folders = []
            if not self._dir_exists(self.backup_folder):
                return folders

            entries = xbmcvfs.listdir(self.backup_folder.rstrip("/") + "/")
            if not entries:
                return folders

            if isinstance(entries, tuple):
                daily_folders, _ = entries
            else:
                daily_folders = entries

            for folder_name in daily_folders or []:
                # Validate YYYY-MM-DD format
                if self._is_valid_date_folder(folder_name):
                    folder_path = self._join_path(self.backup_folder, folder_name)
                    folders.append((folder_name, normalize(folder_path)))

            # Sort by date, newest first
            folders.sort(key=lambda x: x[0], reverse=True)
            return folders
        except Exception as e:
            log_error(f"Failed to get daily folders: {e}")
            return []

    def _is_valid_date_folder(self, folder_name):
        """Check if folder name is in YYYY-MM-DD format"""
        if len(folder_name) != 10:
            return False
        try:
            datetime.strptime(folder_name, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def cleanup_old_daily_folders(self):
        """
        Remove daily folders older than retention_days
        Should be called once per day (typically on first backup of the day)
        """
        try:
            daily_folders = self.get_all_daily_folders()
            if len(daily_folders) <= self.retention_days:
                log_debug(f"Retention check: {len(daily_folders)} folders <= {self.retention_days} days")
                return True

            folders_to_delete = daily_folders[self.retention_days:]
            
            for date_str, folder_path in folders_to_delete:
                if self._delete_folder_recursively(folder_path):
                    log_debug(f"Deleted old backup folder: {date_str}")
                else:
                    log_error(f"Failed to delete backup folder: {folder_path}")

            log_debug(f"Cleanup complete: deleted {len(folders_to_delete)} old backup folders")
            return True
        except Exception as e:
            log_error(f"Cleanup failed: {e}")
            return False

    def _delete_file(self, file_path):
        """Delete a single file"""
        try:
            if xbmcvfs.exists(file_path):
                xbmcvfs.delete(file_path)
                return True
        except Exception as e:
            log_error(f"Failed to delete file {file_path}: {e}")
        return False

    def _delete_folder_recursively(self, folder_path):
        """Delete a folder and all its contents"""
        try:
            if not self._dir_exists(folder_path):
                return True

            # Delete all files in the folder first
            entries = xbmcvfs.listdir(folder_path.rstrip("/") + "/")
            if isinstance(entries, tuple):
                subfolders, files = entries
            else:
                files = entries
                subfolders = []

            for filename in files:
                file_path = self._join_path(folder_path, filename)
                if not self._delete_file(file_path):
                    return False

            # Delete subfolders
            for subfolder_name in subfolders:
                subfolder_path = self._join_path(folder_path, subfolder_name)
                if not self._delete_folder_recursively(subfolder_path):
                    return False

            # Delete the empty folder
            xbmcvfs.rmdir(folder_path)
            return True
        except Exception as e:
            log_error(f"Failed to delete folder {folder_path}: {e}")
            return False

    def should_run_daily_cleanup(self, date=None):
        """
        Check if daily cleanup should run
        Returns True if this is the first backup of the day
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        folder_path = self.get_backup_folder_for_date(date)
        
        try:
            if not self._dir_exists(folder_path):
                return True
            
            # If folder exists but is empty, it's the first backup
            entries = xbmcvfs.listdir(folder_path.rstrip("/") + "/")
            if isinstance(entries, tuple):
                subfolders, files = entries
            else:
                files = entries
            
            return len(files) == 0
        except Exception:
            return False
