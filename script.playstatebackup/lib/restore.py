import json
import xbmcvfs
from lib import pathmap
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
                by_uniqueid.setdefault((key, value), []).append(item)

            by_path[normalize(file_path)] = file_path

        return by_uniqueid, by_path

    def _find_current_file_path(self, entry, by_uniqueid, by_path):
        # Prefer matching via uniqueid, since it still finds the file even if it was
        # renamed/moved. Only fall back to the backed up file path when no usable
        # uniqueid is available (common for music videos).
        file_path = entry.get("file")
        normalized_entry_path = normalize(file_path) if file_path else None

        for key, value in self._comparable_uniqueids(entry.get("uniqueid")).items():
            candidates = by_uniqueid.get((key, value), [])
            if not candidates:
                continue

            # A shared id (for example a series id) is not sufficient to select
            # one episode. Prefer the original path, then episode coordinates.
            if normalized_entry_path:
                for candidate in candidates:
                    if normalize(candidate.get("file")) == normalized_entry_path:
                        candidate_path = candidate.get("file")
                        if candidate_path and not candidate_path.lower().startswith("stack://"):
                            return candidate_path

            has_episode_identity = (
                entry.get("season") is not None
                and entry.get("episode") is not None
            )
            if has_episode_identity:
                episode_candidates = [
                    candidate
                    for candidate in candidates
                    if candidate.get("season") == entry.get("season")
                    and candidate.get("episode") == entry.get("episode")
                ]
                if len(episode_candidates) == 1:
                    candidate_path = episode_candidates[0].get("file")
                    if candidate_path and not candidate_path.lower().startswith("stack://"):
                        return candidate_path

            if not has_episode_identity and len(candidates) == 1:
                candidate_path = candidates[0].get("file")
                if candidate_path and not candidate_path.lower().startswith("stack://"):
                    return candidate_path

        if not file_path:
            return None

        current_path = by_path.get(normalize(file_path), file_path)
        if current_path and current_path.lower().startswith("stack://"):
            return None
        return current_path

    def _apply_playstate(self, file_path, entry):
        # Files.SetFileDetails works purely by path (no library id required), which
        # avoids type-specific mandatory fields (e.g. "artist" for music videos) that
        # VideoLibrary.SetXDetails would otherwise demand. This requires the media
        # source to be online and reachable.
        if not file_path or file_path.lower().startswith("stack://"):
            log_debug(f"Skipping stacked media entry during restore: {file_path}")
            return False

        try:
            playcount = int(entry.get("playcount") or 0)
        except (TypeError, ValueError):
            playcount = 0

        params = {
            "file": file_path,
            "media": "video",
            "playcount": playcount,
        }

        if entry.get("lastplayed"):
            params["lastplayed"] = entry.get("lastplayed")

        resume = entry.get("resume")
        if isinstance(resume, dict):
            try:
                position = int(resume.get("position") or 0)
            except (TypeError, ValueError):
                position = 0
            try:
                total = int(resume.get("total") or 0)
            except (TypeError, ValueError):
                total = 0

            params["resume"] = {
                "position": position,
                "total": total,
            }

        response = self.rpc.call(
            "Files.SetFileDetails",
            params,
            log_rpc_errors=False,
        )
        return bool(response) and "error" not in response

    def _apply_path_mapping(self, entry, path_mapping):
        file_path = entry.get("file")
        if not file_path:
            return entry

        mapped_path = pathmap.apply_mapping(file_path, path_mapping)
        if mapped_path == file_path:
            return entry

        mapped_entry = dict(entry)
        mapped_entry["file"] = mapped_path
        return mapped_entry

    def _restore_entries(
        self,
        folder_path,
        filename,
        data_key,
        library_items,
        database_fallback=False,
        path_mapping=None,
    ):
        data = self._load_json(folder_path, filename)
        if not data:
            return 0

        entries = data.get(data_key, [])

        entries = [
            entry
            for entry in entries
            if not (entry.get("file") or "").lower().startswith("stack://")
        ]

        if path_mapping:
            entries = [self._apply_path_mapping(entry, path_mapping) for entry in entries]

        by_uniqueid, by_path = self._build_index(library_items)

        restored = 0
        for entry in entries:
            file_path = self._find_current_file_path(entry, by_uniqueid, by_path)

            if not file_path:
                log_debug(f"No file path found for backup entry: {entry.get('file')}")
                continue

            if normalize(file_path) not in by_path and not xbmcvfs.exists(file_path):
                log_debug(f"Skipping unavailable file from backup: {file_path}")
                continue

            restored_entry = self._apply_playstate(file_path, entry)
            if not restored_entry and database_fallback:
                restored_entry = self.videodb.set_unknown_video_playstate(file_path, entry)

            if restored_entry:
                restored += 1
            else:
                log_debug(f"Could not restore playstate for unreachable file: {file_path}")

        log_debug(f"Restored {restored}/{len(entries)} entries from '{filename}'")
        return restored

    def restore_movies(self, folder_path, path_mapping=None):
        return self._restore_entries(
            folder_path,
            "movies.json",
            "movies",
            self.videodb.video_library_get_movies(),
            path_mapping=path_mapping,
        )

    def restore_episodes(self, folder_path, path_mapping=None):
        return self._restore_entries(
            folder_path,
            "episodes.json",
            "episodes",
            self.videodb.video_library_get_episodes(),
            path_mapping=path_mapping,
        )

    def restore_musicvideos(self, folder_path, path_mapping=None):
        return self._restore_entries(
            folder_path,
            "musicvideos.json",
            "musicvideos",
            self.videodb.video_library_get_musicvideos(),
            path_mapping=path_mapping,
        )

    def restore_videos(self, folder_path, path_mapping=None):
        """Uncategorized videos have no library entry, so the backed up file path is
        used directly."""
        return self._restore_entries(
            folder_path,
            "videos.json",
            "videos",
            [],
            database_fallback=True,
            path_mapping=path_mapping,
        )

