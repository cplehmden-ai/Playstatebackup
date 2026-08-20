import sys
import xbmcgui
from lib import pathmap
from lib.backup import Backup
from lib.backup_manager import BackupManager
from lib.constants import ADDON
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC
from lib.logger import log_debug, log_info
from lib.restore import Restore
from lib.utils import normalize


BACKUP_TYPES = (
    (30035, "backup_movies"),
    (30036, "backup_episodes"),
    (30037, "backup_musicvideos"),
    (30038, "backup_videos"),
)

# A video only ends up in the Kodi database once it has a playcount, resume point
# or has been opened in the GUI - so only videos already tracked by Kodi are backed
# up or restored here; no folder scan is triggered.
RESTORE_TYPES = (
    (30035, "restore_movies"),
    (30036, "restore_episodes"),
    (30037, "restore_musicvideos"),
    (30038, "restore_videos"),
)


def run_complete_backup(backup):
    """Back up paths and every supported video type."""
    log_info("Backup started (complete)")
    backup.backup_paths()
    for _, method_name in BACKUP_TYPES:
        getattr(backup, method_name)()
    log_info("Backup finished (complete)")


def select_backup_types(title, types=BACKUP_TYPES):
    """Return the backup/restore methods chosen by the user, or None on cancellation."""
    labels = [ADDON.getLocalizedString(label_id) for label_id, _ in types]
    selected = xbmcgui.Dialog().multiselect(
        title,
        labels,
        preselect=list(range(len(types))),
    )

    if selected is None:
        return None

    return [types[index][1] for index in selected]


def run_partial_backup(backup):
    selected_methods = select_backup_types(ADDON.getLocalizedString(30031))
    if selected_methods is None:
        return

    log_info(f"Backup started (partial): {selected_methods}")
    backup.backup_paths()
    for method_name in selected_methods:
        getattr(backup, method_name)()
    log_info("Backup finished (partial)")


def show_unavailable_action():
    xbmcgui.Dialog().ok(
        ADDON.getLocalizedString(30034),
        ADDON.getLocalizedString(30039),
    )


def select_new_path_for_source(source):
    label = source.get("label") or source.get("path")

    # Always start at the root of the browser (no preset folder), otherwise Kodi
    # tries to jump straight into the (possibly no longer existing) old/current
    # path and never shows the root-level shares, so network sources like SMB
    # can't be reached at all.
    new_path = xbmcgui.Dialog().browseSingle(
        0,
        ADDON.getLocalizedString(30053).format(label),
        "files",
        "",
        False,
        True,
        "",
    )

    if not new_path or new_path.lower().startswith("stack://"):
        return None

    return normalize(new_path)


def build_path_mapping_options(sources, mapping):
    options = []
    for source in sources:
        path = source.get("path")
        label = source.get("label") or path
        mapped_to = mapping.get(path)
        target = mapped_to if mapped_to else ADDON.getLocalizedString(30050)
        options.append(f"{label} ({path}) -> {target}")

    options.append(ADDON.getLocalizedString(30051))
    options.append(ADDON.getLocalizedString(30052))
    return options


def handle_path_mapping_action():
    backup_set = select_backup_set()
    if backup_set is None:
        return

    date_label, folder_path = backup_set

    sources = pathmap.load_enabled_sources(folder_path)
    if not sources:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(30034),
            ADDON.getLocalizedString(30049),
        )
        return

    mapping = pathmap.load_mapping(folder_path)

    while True:
        options = build_path_mapping_options(sources, mapping)
        save_index = len(sources)
        save_and_restore_index = len(sources) + 1

        selection = xbmcgui.Dialog().select(
            ADDON.getLocalizedString(30033),
            options,
        )

        if selection < 0:
            return

        if selection < len(sources):
            source = sources[selection]
            new_path = select_new_path_for_source(source)
            if new_path:
                mapping[source.get("path")] = new_path
            continue

        if selection == save_index:
            pathmap.save_mapping(folder_path, mapping)
            xbmcgui.Dialog().notification(
                ADDON.getLocalizedString(30034),
                ADDON.getLocalizedString(30054),
            )
            continue

        if selection == save_and_restore_index:
            pathmap.save_mapping(folder_path, mapping)

            selected_methods = select_backup_types(ADDON.getLocalizedString(30032), RESTORE_TYPES)
            if selected_methods is None:
                continue

            run_restore(date_label, folder_path, selected_methods, mapping)
            return


def browse_for_backup_set(start_folder):
    """Let the user browse to an arbitrary folder, e.g. a backup set from another device."""
    folder_path = xbmcgui.Dialog().browseSingle(
        0,
        ADDON.getLocalizedString(30041),
        "files",
        "",
        False,
        False,
        start_folder,
    )

    if not folder_path:
        return None

    folder_path = normalize(folder_path)
    date_label = folder_path.rsplit("/", 1)[-1] or folder_path
    return (date_label, folder_path)


def select_backup_set():
    """Let the user choose one of the daily backup sets found in the configured backup
    folder, or browse to a different folder (e.g. one synced from another device)."""
    manager = BackupManager()
    backup_sets = manager.get_all_daily_folders()

    labels = [date for date, _ in backup_sets]
    labels.append(ADDON.getLocalizedString(30046))

    selection = xbmcgui.Dialog().select(
        ADDON.getLocalizedString(30041),
        labels,
        preselect=0,
    )
    if selection < 0:
        return None

    if selection < len(backup_sets):
        return backup_sets[selection]

    return browse_for_backup_set(manager.backup_folder)


def run_restore(date_label, folder_path, selected_methods, path_mapping=None):
    xbmcgui.Dialog().ok(
        ADDON.getLocalizedString(30034),
        ADDON.getLocalizedString(30047),
    )

    log_info(
        "Restore started for backup set {} and types {}".format(
            date_label, selected_methods
        )
    )

    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    restore = Restore(rpc, videodb)

    total_restored = 0
    for method_name in selected_methods:
        total_restored += getattr(restore, method_name)(
            folder_path,
            path_mapping=path_mapping,
        )

    log_info(f"Restore finished for {date_label}: {total_restored} entries restored")
    xbmcgui.Dialog().notification(
        ADDON.getLocalizedString(30034),
        ADDON.getLocalizedString(30045).format(total_restored),
    )


def handle_restore_action():
    backup_set = select_backup_set()
    if backup_set is None:
        return

    date_label, folder_path = backup_set

    selected_methods = select_backup_types(ADDON.getLocalizedString(30032), RESTORE_TYPES)
    if selected_methods is None:
        return

    run_restore(date_label, folder_path, selected_methods)


def handle_backup_action(backup):
    actions = [
        ADDON.getLocalizedString(30030),
        ADDON.getLocalizedString(30031),
        ADDON.getLocalizedString(30032),
        ADDON.getLocalizedString(30033),
    ]
    selection = xbmcgui.Dialog().select(ADDON.getLocalizedString(30034), actions)

    if selection == 0:
        run_complete_backup(backup)
    elif selection == 1:
        run_partial_backup(backup)
    elif selection == 2:
        handle_restore_action()
    elif selection == 3:
        handle_path_mapping_action()


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