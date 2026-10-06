import xbmcvfs
import json
import gc
import ctypes
from datetime import datetime
from lib.logger import log_debug, log_error
from lib.utils import normalize
from lib.backup_manager import BackupManager


def _get_malloc_trim():
    """Return malloc_trim when exported by the process C runtime, otherwise None."""
    try:
        libc = ctypes.CDLL(None)
        malloc_trim = getattr(libc, "malloc_trim", None)

        if malloc_trim is None:
            return None

        malloc_trim.argtypes = [ctypes.c_size_t]
        malloc_trim.restype = ctypes.c_int
        return malloc_trim

    except Exception:
        return None


_MALLOC_TRIM = _get_malloc_trim()


class Backup:

    def __init__(self, rpc, videodb):
        self.rpc = rpc
        self.videodb = videodb
        self.backup_manager = BackupManager()
        self._daily_cleanup_done = False


    def release_memory(self):
        """Release unreachable Python objects and trim the C heap when supported."""
        collected = gc.collect()
        trimmed = False

        if _MALLOC_TRIM is not None:
            try:
                trimmed = bool(_MALLOC_TRIM(0))
            except Exception:
                # malloc_trim is optional. Python GC has already completed.
                pass

        log_debug(f"Memory cleanup: gc={collected}, malloc_trim={trimmed}")

    def backup_directory(self, directory):

        index = self.videodb.get_directory_index(directory)

        backup_data = []

        log_debug("{} files found".format(len(index)))

        for path, item in index.items():
            log_debug(str(item))
            break

        entry = {
            "path": path,
        }

        backup_data.append(entry)

        return backup_data

    def backup_paths(self):

        sources = self.videodb.get_video_source_types()

        if not sources:
            log_debug("No video sources found")
            return False

        self.save_json("backup-path.json", {
            "sources": sources
        })

        log_debug(f"Backup paths saved: {len(sources)}")

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
        count = 0

        def entries():
            nonlocal count

            for movie in movies:
                entry = self.create_movie_backup(movie)

                if entry is not None:
                    count += 1
                    yield entry

        result = self.save_json_stream("movies.json", "movies", entries())

        # The API result can be large. Drop our reference as soon as possible.
        del movies
        self.release_memory()

        if result:
            log_debug(f"Movies backed up: {count}")

        return result

    def backup_musicvideos(self):

        musicvideos = self.videodb.video_library_get_musicvideos()
        count = 0

        def entries():
            nonlocal count

            for musicvideo in musicvideos:
                entry = self.create_musicvideo_backup(musicvideo)

                if entry is not None:
                    count += 1
                    yield entry

        result = self.save_json_stream("musicvideos.json", "musicvideos", entries())

        del musicvideos
        self.release_memory()

        if result:
            log_debug(f"Music videos backed up: {count}")

        return result

    def backup_episodes(self):

        episodes = self.videodb.video_library_get_episodes()
        count = 0

        def entries():
            nonlocal count

            for episode in episodes:
                entry = self.create_episode_backup(episode)

                if entry is not None:
                    count += 1
                    yield entry

        result = self.save_json_stream("episodes.json", "episodes", entries())

        del episodes
        self.release_memory()

        if result:
            log_debug(f"Episodes backed up: {count}")

        return result

    def backup_videos(self):

        sources = self.videodb.get_video_source_types()

        if not sources:
            log_debug("No video sources found")
            return False

        unknown_sources = []

        blacklist = self.videodb.get_blacklisted_video_sources()

        for source in sources:
            if source.get("content") != "unknown":
                continue

            source_path = normalize(source.get("path") or "")

            if not self.videodb.is_source_enabled(source):
                log_debug(f"Skipping disabled source: {source_path}")
                continue

            if source_path in blacklist:
                log_debug(f"Skipping blacklisted source: {source_path}")
                continue

            unknown_sources.append(source_path.rstrip("/"))

        if not unknown_sources:
            log_debug("No enabled unknown video sources found for backup")
            return self.save_json("videos.json", {"videos": []})

        database_entries = self.videodb.get_unknown_video_database_entries()

        log_debug(f"Backing up videos from {len(unknown_sources)} unknown source(s)")

        def entries():
            count = 0

            # Process every database entry only once. The previous implementation
            # iterated over the complete database once for every unknown source.
            for video in database_entries:
                file_path = normalize(video.get("file") or "")
                if not file_path:
                    continue

                for source_prefix in unknown_sources:
                    if file_path == source_prefix or file_path.startswith(source_prefix + "/"):
                        entry = self.create_videos_backup(video)

                        if entry is not None:
                            count += 1
                            yield entry

                        break

            log_debug(f"Videos backed up: {count}")

        result = self.save_json_stream("videos.json", "videos", entries())

        # The database result may contain many thousands of entries.
        del database_entries
        self.release_memory()

        return result

    def _prepare_json_file(self, filename):
        """
        Prepare the target JSON file and perform the daily cleanup/rotation.
        Returns the full filename or None on error.
        """
        run_cleanup = (
            not self._daily_cleanup_done
            and self.backup_manager.should_run_daily_cleanup()
        )

        today = datetime.now().strftime("%Y-%m-%d")
        backup_folder = self.backup_manager.ensure_backup_folder_for_date(today)

        if not backup_folder:
            log_error("Failed to get or create daily backup folder")
            return None

        if run_cleanup:
            self._perform_daily_cleanup()

        self._daily_cleanup_done = True

        base_name, ext = filename.rsplit(".", 1)
        full_filename = backup_folder.rstrip("/") + "/" + filename
        rotated_filename = (
            backup_folder.rstrip("/") + "/" + f"{base_name}_1.{ext}"
        )

        if xbmcvfs.exists(full_filename):
            xbmcvfs.delete(rotated_filename)
            xbmcvfs.rename(full_filename, rotated_filename)

        return full_filename

    def save_json(self, filename, data):
        """
        Save a complete JSON object to the daily backup folder.
        Intended for small data such as backup-path.json and empty backups.
        Large backup files should use save_json_stream().
        """
        full_filename = self._prepare_json_file(filename)

        if not full_filename:
            return False

        try:
            with xbmcvfs.File(full_filename, "w") as file:
                text = json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )
                file.write(text)

            log_debug(f"Saved '{filename}'")
            return True

        except Exception as e:
            log_error("Failed to save '{}': {}".format(filename, e))
            return False

    def save_json_stream(self, filename, key, entries):
        """
        Stream a JSON array directly to the backup file.

        Only one backup entry and its JSON representation are held at a time.
        This avoids building a large backup list and a second large string with
        json.dumps(), which can otherwise cause very high RAM usage on devices
        with limited memory.
        """
        full_filename = self._prepare_json_file(filename)

        if not full_filename:
            return False

        try:
            with xbmcvfs.File(full_filename, "w") as file:
                file.write("{\n")
                file.write(f'  {json.dumps(key, ensure_ascii=False)}: [')

                first = True

                for entry in entries:
                    if first:
                        first = False
                    else:
                        file.write(",")

                    text = json.dumps(
                        entry,
                        indent=2,
                        ensure_ascii=False
                    )

                    # Keep the same readable indentation as the old output.
                    text = "\n".join(
                        "    " + line
                        for line in text.splitlines()
                    )

                    file.write("\n")
                    file.write(text)

                file.write("\n  ]\n}\n")

            log_debug(f"Saved '{filename}'")
            return True

        except Exception as e:
            log_error("Failed to save '{}': {}".format(filename, e))
            return False

    def _perform_daily_cleanup(self):
        """
        Perform daily cleanup of old backup folders
        Should be called once per day on the first backup
        """
        try:
            log_debug("Running daily backup cleanup...")
            self.backup_manager.cleanup_old_daily_folders()
        except Exception as e:
            log_error(f"Daily cleanup error: {e}")
