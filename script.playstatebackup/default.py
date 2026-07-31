from lib.logger import (
    log_info,
    log_warning,
    log_error,
    log_debug,
)
from lib.jsonrpc import JsonRPC

log_info("started")

rpc = JsonRPC()
result = rpc.call("JSONRPC.Version")

log_info(str(result))