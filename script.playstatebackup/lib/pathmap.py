import json
import xbmcvfs
from lib.logger import log_debug, log_error
from lib.utils import normalize

MAPPING_FILENAME = "path-mapping.json"


def _full_path(folder_path, filename):
    return folder_path.rstrip("/") + "/" + filename


def load_enabled_sources(folder_path):
    """Read backup-path.json from a backup set and return only the sources that
    were enabled at backup time (blacklisted/disabled sources are kept in the
    file but must not be offered for path mapping)."""
    full_path = _full_path(folder_path, "backup-path.json")

    if not xbmcvfs.exists(full_path):
        log_debug(f"No backup-path.json found in {folder_path}")
        return []

    try:
        with xbmcvfs.File(full_path, "r") as file:
            data = json.loads(file.read())
    except Exception as e:
        log_error(f"Failed to read '{full_path}': {e}")
        return []

    sources = data.get("sources", [])
    return [source for source in sources if source.get("enabled")]


def load_mapping(folder_path):
    """Load a previously saved path mapping ({old_path: new_path}) for a backup set."""
    full_path = _full_path(folder_path, MAPPING_FILENAME)

    if not xbmcvfs.exists(full_path):
        return {}

    try:
        with xbmcvfs.File(full_path, "r") as file:
            data = json.loads(file.read())
        mapping = data.get("mapping", {}) or {}
        return {
            old_path: new_path
            for old_path, new_path in mapping.items()
            if isinstance(old_path, str)
            and isinstance(new_path, str)
            and not new_path.lower().startswith("stack://")
        }
    except Exception as e:
        log_error(f"Failed to read '{full_path}': {e}")
        return {}


def save_mapping(folder_path, mapping):
    full_path = _full_path(folder_path, MAPPING_FILENAME)

    try:
        with xbmcvfs.File(full_path, "w") as file:
            file.write(json.dumps({"mapping": mapping}))
        log_debug(f"Path mapping saved: {len(mapping)} entries")
        return True
    except Exception as e:
        log_error(f"Failed to write '{full_path}': {e}")
        return False


def apply_mapping(file_path, mapping):
    """Replace the (old) backed up path prefix of a file with its mapped
    replacement, keeping the relative path below it intact."""
    if not file_path or file_path.lower().startswith("stack://") or not mapping:
        return file_path

    normalized_file = normalize(file_path)
    # Compare case-insensitively since drive letters/UNC hosts saved by
    # Files.GetSources may differ in case from the path Kodi later reports
    # for a library item on the same (case-insensitive) filesystem.
    lowered_file = normalized_file.lower()

    best_old_path = None
    best_prefix_length = -1

    for old_path in mapping:
        normalized_old = normalize(old_path)
        if not normalized_old:
            continue

        lowered_old = normalized_old.lower()
        if lowered_file == lowered_old or lowered_file.startswith(lowered_old + "/"):
            if len(lowered_old) > best_prefix_length:
                best_old_path = old_path
                best_prefix_length = len(lowered_old)

    if best_old_path is None:
        return file_path

    new_path = normalize(mapping[best_old_path])
    if new_path.lower().startswith("stack://"):
        return file_path
    remainder = normalized_file[best_prefix_length:]
    return new_path + remainder

