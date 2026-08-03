#import xbmc

from lib.logger import log_info
from lib.jsonrpc import JsonRPC

log_info("started")

rpc = JsonRPC()

rpc.version()

log_info(rpc.get_setting_value("locale.language"))

