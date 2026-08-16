#import xbmc
import os
import xbmcvfs
import xbmcaddon
import json
from lib.videodb import VideoDB
from lib.logger import log_info, log_error
from lib.utils import normalize

class Backup:

    def __init__(self, rpc, videodb):
            self.rpc = rpc
            self.videodb = videodb

    def backup_directory(self, directory):

        index = self.videodb.get_directory_index(directory)

        backup_data = []

        log_info("{} files found".format(len(index)))

        for path, item in index.items():
            log_info(str(item))
            break

        entry = {
                    "path": path,
                }

        backup_data.append(entry)


        return backup_data

    def backup_paths(self):

        sources = self.videodb.get_video_source_types()

        if not sources:
            log_info("No video sources found")
            return False

        self.save_json("backup-path.json", {
            "sources": sources
        })

        log_info(f"Backup paths saved: {len(sources)}")

        return True

    def create_movie_backup(self, movie):

        playcount = movie.get("playcount", 0)
        resume_position = movie.get("resume", {}).get("position", 0)

        if playcount == 0 and resume_position == 0:
            return None

        entry = {
            "title": movie.get("title"),
            "label": movie.get("label"),
            "file": movie.get("file"),
            "playcount": movie.get("playcount"),
            "lastplayed": movie.get("lastplayed"),
            "resume": movie.get("resume"),
            "uniqueid": movie.get("uniqueid"),
            "dateadded": movie.get("dateadded"),
        }

        return entry

    def create_musicvideo_backup(self, musicvideo):

        playcount = musicvideo.get("playcount", 0)
        resume_position = musicvideo.get("resume", {}).get("position", 0)

        if playcount == 0 and resume_position == 0:
            return None

        entry = {
            "title": musicvideo.get("title"),
            "label": musicvideo.get("label"),
            "file": musicvideo.get("file"),
            "playcount": musicvideo.get("playcount"),
            "lastplayed": musicvideo.get("lastplayed"),
            "resume": musicvideo.get("resume"),
            "uniqueid": musicvideo.get("uniqueid"),
            "dateadded": musicvideo.get("dateadded"),
        }

        return entry

    def create_episode_backup(self, episode):

        playcount = episode.get("playcount", 0)
        resume_position = episode.get("resume", {}).get("position", 0)

        if playcount == 0 and resume_position == 0:
            return None

        entry = {
            "title": episode.get("title"),
            "file": episode.get("file"),
            "season": episode.get("season"),
            "episode": episode.get("episode"),
            "playcount": episode.get("playcount"),
            "lastplayed": episode.get("lastplayed"),
            "resume": episode.get("resume"),
            "dateadded": episode.get("dateadded"),
            "uniqueid": episode.get("uniqueid"),
        }

        return entry

    def create_videos_backup(self, video):

        playcount = video.get("playcount", 0)
        resume_position = video.get("resume", {}).get("position", 0)

        if playcount == 0 and resume_position == 0:
            return None

        entry = {
            "file": video.get("file"),
            "playcount": video.get("playcount"),
            "lastplayed": video.get("lastplayed"),
            "resume": video.get("resume"),
            "dateadded": video.get("dateadded"),
        }

        return entry


    def backup_movies(self):

        movies = self.videodb.video_library_get_movies()

        backup = []

        for movie in movies:
            entry = self.create_movie_backup(movie)

            if entry:
                backup.append(entry)

        self.save_json("movies.json", {
            "movies": backup
        })

        log_info(f"Movies backed up: {len(backup)}")

        return True
    
    def backup_musicvideos(self):

        musicvideos = self.videodb.video_library_get_musicvideos()

        backup = []

        for musicvideo in musicvideos:
            entry = self.create_musicvideo_backup(musicvideo)

            if entry:
                backup.append(entry)

        self.save_json("musicvideos.json", {
            "musicvideos": backup
        })

        log_info(f"Music videos backed up: {len(backup)}")

        return True

    def backup_episodes(self):

        episodes = self.videodb.video_library_get_episodes()

        backup = []

        for episode in episodes:
            entry = self.create_episode_backup(episode)

            if entry:
                backup.append(entry)

        self.save_json("episodes.json", {
            "episodes": backup
        })

        log_info(f"Episodes backed up: {len(backup)}")

        return True

    def backup_videos(self):

        backup = []

        sources = self.videodb.get_video_source_types()

        if not sources:
            log_info("No video sources found")
            return False

        unknown_sources = [
            source for source in sources
            if source.get("content") == "unknown"
        ]

        blacklist = self.videodb.get_blacklisted_video_sources()

        if not unknown_sources:
            log_info("No unknown video sources found for backup")
            self.save_json("videos.json", {"videos": []})
            return True

        database_entries = self.videodb.get_unknown_video_database_entries()

        if not database_entries:
            log_info("No unknown video entries found in Kodi database")
            self.save_json("videos.json", {"videos": []})
            return True

        for source in unknown_sources:
            source_path = normalize(source.get("path") or "")

            if not self.videodb.is_source_enabled(source):
                log_info(f"Skipping disabled source: {source_path}")
                continue

            if source_path in blacklist:
                log_info(f"Skipping blacklisted source: {source_path}")
                continue

            log_info(f"Backing up videos from: {source_path}")

            for video in database_entries:
                file_path = normalize(video.get("file") or "")
                if not file_path:
                    continue

                source_prefix = source_path.rstrip("/")
                if file_path == source_prefix:
                    entry = self.create_videos_backup(video)
                    if entry is not None:
                        backup.append(entry)
                    continue

                if file_path.startswith(source_prefix + "/"):
                    entry = self.create_videos_backup(video)
                    if entry is not None:
                        backup.append(entry)

        self.save_json("videos.json", {
            "videos": backup
        })

        log_info(f"Videos backed up: {len(backup)}")

        return True

    def save_json(self, filename, data):

        addon = xbmcaddon.Addon()
        backup_folder = addon.getSetting("backup_folder")

        if not backup_folder:
            profile_path = xbmcvfs.translatePath("special://profile")
            backup_folder = os.path.join(profile_path, "addon_data", "script.playstatebackup")
            os.makedirs(backup_folder, exist_ok=True)
            addon.setSetting("backup_folder", backup_folder)

        full_filename = backup_folder.rstrip("/") + "/" + filename

        try:
            with xbmcvfs.File(full_filename, "w") as file:
                text = json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )
                file.write(text)

            log_info("Saved '{}'".format(filename))
            return True

        except Exception as e:
            log_error("Failed to save '{}': {}".format(filename, e))
            return False