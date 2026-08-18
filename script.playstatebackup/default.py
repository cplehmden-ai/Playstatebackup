import sys
import xbmcgui
from lib.backup import Backup
from lib.backup_manager import BackupManager
from lib.constants import ADDON
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC
from lib.logger import log_debug
from lib.utils import normalize


BACKUP_TYPES = (
    (30035, "backup_movies"),
    (30036, "backup_episodes"),
    (30037, "backup_musicvideos"),
    (30038, "backup_videos"),
)


def run_complete_backup(backup):
    """Back up paths and every supported video type."""
    backup.backup_paths()
    for _, method_name in BACKUP_TYPES:
        getattr(backup, method_name)()


def select_backup_types(title):
    """Return the backup methods chosen by the user, or None on cancellation."""
    labels = [ADDON.getLocalizedString(label_id) for label_id, _ in BACKUP_TYPES]
    selected = xbmcgui.Dialog().multiselect(
        title,
        labels,
        preselect=list(range(len(BACKUP_TYPES))),
    )

    if selected is None:
        return None

    return [BACKUP_TYPES[index][1] for index in selected]


def run_partial_backup(backup):
    selected_methods = select_backup_types(ADDON.getLocalizedString(30031))
    if selected_methods is None:
        return

    backup.backup_paths()
    for method_name in selected_methods:
        getattr(backup, method_name)()


def show_unavailable_action():
    xbmcgui.Dialog().ok(
        ADDON.getLocalizedString(30034),
        ADDON.getLocalizedString(30039),
    )


def handle_restore_action():
    selected_methods = select_backup_types(ADDON.getLocalizedString(30032))
    if selected_methods is None:
        return

    backup_sets = BackupManager().get_all_daily_folders()
    if not backup_sets:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(30034),
            ADDON.getLocalizedString(30040),
        )
        return

    labels = [date for date, _ in backup_sets]
    selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(30041), labels)
    if selection < 0:
        return

    log_debug(
        "Restore requested for backup set {} and types {}".format(
            labels[selection], selected_methods
        )
    )
    show_unavailable_action()


def handle_backup_action(backup):
    actions = [
        ADDON.getLocalizedString(30030),
        ADDON.getLocalizedString(30031),
        ADDON.getLocalizedString(30032),
        ADDON.getLocalizedString(30033),
    ]
    selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(30034), actions)

    if selection == 0:
        log_debug("Starting complete backup")
        run_complete_backup(backup)
        log_debug("Complete backup finished")
    elif selection == 1:
        log_debug("Starting partial backup")
        run_partial_backup(backup)
        log_debug("Partial backup finished")
    elif selection == 2:
        handle_restore_action()
    elif selection == 3:
        show_unavailable_action()


def handle_select_unknown_video_sources():
    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    unknown_sources = videodb.get_unknown_video_sources()

    if not unknown_sources:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(30034),
            ADDON.getLocalizedString(30042),
        )
        return

    disabled_paths = videodb.get_disabled_video_sources()
    options = []
    preselect = []

    for index, source in enumerate(unknown_sources):
        path = source.get("path") or ""
        label = source.get("label") or ADDON.getLocalizedString(30043)
        display_label = f"{label} - {path}" if path else label
        options.append(display_label)

        if normalize(path) in disabled_paths:
            preselect.append(index)

    selected = xbmcgui.Dialog().multiselect(
        ADDON.getLocalizedString(30044),
        options,
        preselect=preselect,
    )

    if selected is None:
        return

    new_disabled_paths = [
        unknown_sources[index].get("path")
        for index in selected
        if unknown_sources[index].get("path")
    ]

    videodb.set_disabled_video_sources(new_disabled_paths)
    log_debug(f"Disabled unknown sources: {new_disabled_paths}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "action=select_unknown_video_sources":
        handle_select_unknown_video_sources()
        return

    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    backup = Backup(rpc, videodb)
    handle_backup_action(backup)

if __name__ == "__main__":
    main()