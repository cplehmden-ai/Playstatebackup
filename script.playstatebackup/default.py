import json
import sys
import xbmc
import xbmcgui
import xbmcaddon
from lib.backup import Backup
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC
from lib.logger import log_info


def handle_select_unknown_video_sources():
    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    unknown_sources = videodb.get_unknown_video_sources()

    if not unknown_sources:
        xbmcgui.Dialog().ok(
            "PlayState Backup",
            "No unknown video sources were found.\n\nAll sources are enabled by default."
        )
        return

    disabled_paths = videodb.get_disabled_video_sources()
    options = []
    preselect = []

    for index, source in enumerate(unknown_sources):
        path = source.get("path") or ""
        label = source.get("label") or "Unknown source"
        display_label = f"{label} - {path}" if path else label
        options.append(display_label)

        if normalize_source_path(path) in disabled_paths:
            preselect.append(index)

    selected = xbmcgui.Dialog().multiselect(
        "Exclude unknown video sources\nOnly sources without a known content type are listed.\nAll sources are enabled by default.",
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
    log_info(f"Disabled unknown sources: {new_disabled_paths}")


def normalize_source_path(path):
    if not path:
        return ""
    return path.replace("\\", "/").rstrip("/")


def test_videodb_paths(rpc):
    paths = [
        "videodb://",
        "videodb://movies/",
        "videodb://movies/titles/",
        "videodb://tvshows/",
        "videodb://tvshows/titles/",
        "videodb://musicvideos/",
        "videodb://musicvideos/titles/",
        "library://video/",
        "library://video/files/",
    ]

    properties = [
        "playcount",
        "lastplayed",
        "resume",
        "dateadded",
    ]

    for path in paths:
        log_info("")
        log_info("========== TEST PATH ==========")
        log_info(path)

        result = rpc.files_get_directory(
            path,
            media="video",
            properties=properties,
        )

        if not result:
            log_info("RESULT: empty / failed")
            continue

        files = result.get("files", [])

        log_info(
            "RESULT: {} entries".format(len(files))
        )

        for item in files[:20]:
            log_info(str(item))

        if len(files) > 20:
            log_info(
                "... {} more entries".format(
                    len(files) - 20
                )
            )


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "action=select_unknown_video_sources":
        handle_select_unknown_video_sources()
        return

    log_info("Addon started")

    rpc = JsonRPC()

    videodb = VideoDB(rpc)
    backup = Backup(rpc, videodb)

#    log_info("========== TEST started ==========")



   # test_videodb_paths(rpc)

#    mysql_credentials = videodb.get_mysql_credentials()

#    log_info("VideoDB.mysql_credentials result:")
#    log_info(str(mysql_credentials))



#    videodb_version = videodb.get_videodb_version()

#    log_info("VideoDB.GetVersion result:")
#    log_info(str(videodb_version))

    log_info("Starting backup")
    backup.backup_paths()
    backup.backup_episodes()
    backup.backup_movies()
    backup.backup_videos()


#    videodb_connection = 
#    videodb.get_database_connection()
    
    log_info("Backup finished")

if __name__ == "__main__":
    main()