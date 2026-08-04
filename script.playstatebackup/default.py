import xbmc
import time
from lib.logger import log_info
from lib.jsonrpc import JsonRPC
from lib.utils import select_directory
from lib.videodb import VideoDB

def main():
    log_info("started")

    rpc = JsonRPC()
    videodb = VideoDB(rpc)

    directory = select_directory()

    if not directory:
        return

    start = time.time()
    log_info("Opening directory: {}".format(directory))

    videodb.open_directory(directory)
    videodb.wait_for_directory(directory)
    log_info("All files in directory are ready")
    elapsed = time.time() - start
    log_info("Elapsed time: {:.2f} seconds".format(elapsed))
    xbmc.executebuiltin("Action(Back)")

if __name__ == "__main__":
    main()