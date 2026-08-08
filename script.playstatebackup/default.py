from lib.logger import log_info#, log_error
from lib.jsonrpc import JsonRPC
#from lib.utils import select_directory
from lib.videodb import VideoDB
#from lib.backup import Backup


def main():
    log_info("started")

    rpc = JsonRPC()
    videodb = VideoDB(rpc)
#    backup = Backup(rpc, videodb)

    source_types = videodb.get_video_source_types()

    log_info(f"Backup sources found: {len(source_types)}")

    for source in source_types:
        log_info(
            f"Backup source: "
            f"{source['label']} | "
            f"{source['path']} | "
            f"{source['content']}"
        )


if __name__ == "__main__":
    main()