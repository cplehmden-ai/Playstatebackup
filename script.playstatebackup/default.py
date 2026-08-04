import xbmc
import time
from lib.logger import log_info, log_error
from lib.jsonrpc import JsonRPC
from lib.utils import select_directory
from lib.videodb import VideoDB

def main():
    log_info("started")

    rpc = JsonRPC()
    videodb = VideoDB(rpc)

    directory = select_directory()

    if directory:

        log_info("Opening directory: {}".format(directory))

        subdirs = videodb.collect_directories(directory)

        log_info("Found {} subdirectories".format(len(subdirs)))

        for subdir in subdirs:
            log_info(subdir)

if __name__ == "__main__":
    main()