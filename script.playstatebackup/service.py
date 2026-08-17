import xbmc
import xbmcaddon
import threading
import time
from datetime import datetime
from lib.backup import Backup
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC
from lib.logger import log_info, log_error


class AutoBackupService:
    """Background service for automatic backup execution"""
    
    MODE_DISABLED = "0"
    MODE_ON_STARTUP = "1"
    MODE_INTERVAL = "2"
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.monitor = xbmc.Monitor()
        self.abort_requested = False
        self.last_backup_time = 0
        
    def get_settings(self):
        """Get current addon settings"""
        mode = self.addon.getSetting("backup_auto_mode")
        interval_minutes = self._get_interval_minutes()
        startup_delay = self._get_startup_delay()
        
        return {
            "mode": mode,
            "interval_minutes": interval_minutes,
            "startup_delay": startup_delay
        }
    
    def _get_interval_minutes(self):
        """Get backup interval in minutes"""
        try:
            minutes = int(self.addon.getSetting("backup_auto_interval"))
            return max(1, minutes)  # Minimum 1 minute
        except (ValueError, TypeError):
            return 60  # Default to 60 minutes
    
    def _get_startup_delay(self):
        """Get startup delay in seconds"""
        try:
            seconds = int(self.addon.getSetting("backup_auto_startup_delay"))
            return max(5, seconds)  # Minimum 5 seconds
        except (ValueError, TypeError):
            return 30  # Default to 30 seconds
    
    def should_run_backup(self):
        """Check if backup should run based on current settings"""
        settings = self.get_settings()
        mode = settings["mode"]
        
        if mode == self.MODE_DISABLED:
            return False
        
        if mode == self.MODE_ON_STARTUP:
            # Only run once per service start
            return False
        
        if mode == self.MODE_INTERVAL:
            # Check if enough time has passed since last backup
            current_time = time.time()
            interval_seconds = settings["interval_minutes"] * 60
            
            if self.last_backup_time == 0:
                # First backup
                return True
            
            if current_time - self.last_backup_time >= interval_seconds:
                return True
        
        return False
    
    def perform_backup(self):
        """Execute backup operation"""
        try:
            log_info("Starting automatic backup...")
            
            rpc = JsonRPC()
            videodb = VideoDB(rpc)
            backup = Backup(rpc, videodb)
            
            # Perform backups
            results = {
                "paths": backup.backup_paths(),
                "movies": backup.backup_movies(),
                "episodes": backup.backup_episodes(),
                "musicvideos": backup.backup_musicvideos(),
                "videos": backup.backup_videos(),
            }
            
            successful = sum(1 for v in results.values() if v)
            log_info(f"Automatic backup completed: {successful}/{len(results)} operations successful")
            
            return True
        except Exception as e:
            log_error(f"Automatic backup failed: {e}")
            return False
    
    def run(self):
        """Main service loop"""
        log_info("Auto-backup service started")
        
        settings = self.get_settings()
        mode = settings["mode"]
        
        if mode == self.MODE_DISABLED:
            log_info("Auto-backup is disabled")
            return
        
        # Handle startup backup with delay
        if mode == self.MODE_ON_STARTUP:
            startup_delay = settings["startup_delay"]
            log_info(f"Startup backup scheduled in {startup_delay} seconds")
            
            # Wait for delay or until abort is requested
            if self.monitor.waitForAbort(startup_delay):
                return
            
            self.perform_backup()
            return
        
        # Handle interval-based backup
        if mode == self.MODE_INTERVAL:
            interval_minutes = settings["interval_minutes"]
            log_info(f"Interval-based backup configured: every {interval_minutes} minutes")
            
            # Service loop - check periodically
            check_interval = 60  # Check every minute
            
            while not self.monitor.abortRequested():
                if self.should_run_backup():
                    self.perform_backup()
                    self.last_backup_time = time.time()
                
                # Wait for next check
                if self.monitor.waitForAbort(check_interval):
                    break
            
            log_info("Auto-backup service stopped")


def main():
    """Entry point for the service"""
    service = AutoBackupService()
    service.run()


if __name__ == "__main__":
    main()
