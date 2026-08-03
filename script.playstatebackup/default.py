from lib.logger import log_info
from lib.jsonrpc import JsonRPC
from lib.utils import select_directory, build_file_index

log_info("started")

rpc = JsonRPC()

directory = select_directory()

rpc.version()

log_info(rpc.get_setting_value("locale.language"))

if directory:
    files = build_file_index(directory)
    log_info("Indexed files: {}".format(len(files)))

    log_info("Entries: {}".format(len(files)))
