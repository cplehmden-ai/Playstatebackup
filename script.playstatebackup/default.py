from lib.logger import log_info
from lib.jsonrpc import JsonRPC
#from lib.utils import select_directory
from lib.videodb import VideoDB
from lib.backup import Backup


def main():

    log_info("started")

    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    backup = Backup(rpc, videodb)

    log_info("Backup started")

    backup.backup_paths()

    backup.backup_videos()

    backup.backup_musicvideos()

    backup.backup_movies()

    backup.backup_episodes()

    log_info("Backup finished")

#    tvshows = videodb.video_library_get_tvshows()

#    log_info(f"TV shows found: {len(tvshows)}")

#    for tvshow in tvshows[:3]:
#        log_info(f"TV show: {tvshow}")


#    episodes = videodb.video_library_get_episodes()

#    log_info(f"Episodes found: {len(episodes)}")

#    for episode in episodes[:100]:
#       log_info(f"Episode: {episode}")

#    source_types = videodb.get_video_source_types()

#    log_info(f"Backup sources found: {len(source_types)}")

#    for source in source_types:
#        log_info(
#            f"Backup source: "
#            f"{source['label']} | "
#            f"{source['path']} | "
#            f"{source['content']}"
#        )


if __name__ == "__main__":
    main()