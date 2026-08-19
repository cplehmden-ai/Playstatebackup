import json
import xbmcvfs
from lib.logger import log_debug, log_error
from lib.utils import normalize

# MusicBrainz artist ids are identical for every video of the same artist and
# therefore cannot be used to identify a single music video.
IGNORED_UNIQUEID_KEYS = ("musicbrainzartist", "mbartist", "artist")


class Restore:

    def __init__(self, rpc, videodb):
        self.rpc = rpc
        self.videodb = videodb

    def _load_json(self, folder_path, filename):
        full_path = folder_path.rstrip("/") + "/" + filename

        if not xbmcvfs.exists(full_path):
            log_debug(f"Backup file not found: {full_path}")
            return None

        try:
            with xbmcvfs.File(full_path, "r") as file:
                text = file.read()
            return json.loads(text)
        except Exception as e:
            log_error(f"Failed to read '{full_path}': {e}")
            return None

    def _comparable_uniqueids(self, uniqueid):
        if not uniqueid:
            return {}

        return {
            key: value
            for key, value in uniqueid.items()
            if value and key.lower() not in IGNORED_UNIQUEID_KEYS
        }

    def _build_index(self, library_items):
        """Index the current library file path by uniqueid (excluding ignored keys)
        and by the (possibly outdated) file path itself."""
        by_uniqueid = {}
        by_path = {}

        for item in library_items:
            file_path = item.get("file")
            if not file_path:
                continue

            for key, value in self._comparable_uniqueids(item.get("uniqueid")).items():
                by_uniqueid[(key, value)] = file_path

            by_path[normalize(file_path)] = file_path

        return by_uniqueid, by_path

    def _find_current_file_path(self, entry, by_uniqueid, by_path):
        # Prefer matching via uniqueid, since it still finds the file even if it was
        # renamed/moved. Only fall back to the backed up file path when no usable
        # uniqueid is available (common for music videos).
        for key, value in self._comparable_uniqueids(entry.get("uniqueid")).items():
            file_path = by_uniqueid.get((key, value))
            if file_path:
                return file_path

        file_path = entry.get("file")
        if not file_path:
            return None

        return by_path.get(normalize(file_path), file_path)

    def _apply_playstate(self, file_path, entry):
        # Files.SetFileDetails works purely by path (no library id required), which
        # avoids type-specific mandatory fields (e.g. "artist" for music videos) that
        # VideoLibrary.SetXDetails would otherwise demand. This requires the media
        # source to be online and reachable.
        params = {
            "file": file_path,
            "media": "video",
            "playcount": entry.get("playcount", 0),
        }

        if entry.get("lastplayed"):
            params["lastplayed"] = entry.get("lastplayed")

        resume = entry.get("resume")
        if resume:
            params["resume"] = {
                "position": resume.get("position", 0),
                "total": resume.get("total", 0),
            }

        response = self.rpc.call("Files.SetFileDetails", params)
        return bool(response) and "error" not in response

    def _restore_entries(self, folder_path, filename, data_key, library_items):
        data = self._load_json(folder_path, filename)
        if not data:
            return 0

        entries = data.get(data_key, [])
        by_uniqueid, by_path = self._build_index(library_items)

        restored = 0
        for entry in entries:
            file_path = self._find_current_file_path(entry, by_uniqueid, by_path)

            if not file_path:
                log_debug(f"No file path found for backup entry: {entry.get('file')}")
                continue

            if self._apply_playstate(file_path, entry):
                restored += 1
            else:
                log_debug(f"Could not restore playstate for unreachable file: {file_path}")

        log_debug(f"Restored {restored}/{len(entries)} entries from '{filename}'")
        return restored

    def restore_movies(self, folder_path):
        return self._restore_entries(
            folder_path,
            "movies.json",
            "movies",
            self.videodb.video_library_get_movies(),
        )

    def restore_episodes(self, folder_path):
        return self._restore_entries(
            folder_path,
            "episodes.json",
            "episodes",
            self.videodb.video_library_get_episodes(),
        )

    def restore_musicvideos(self, folder_path):
        return self._restore_entries(
            folder_path,
            "musicvideos.json",
            "musicvideos",
            self.videodb.video_library_get_musicvideos(),
        )

    def restore_videos(self, folder_path):
        """Uncategorized videos have no library entry, so the backed up file path is
        used directly."""
        return self._restore_entries(folder_path, "videos.json", "videos", [])

