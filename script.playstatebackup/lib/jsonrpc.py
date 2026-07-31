import json
import xbmc

from lib.constants import RPC_ID
from lib.logger import log_info, log_debug

class JsonRPC:

    def __init__(self):
        log_info("JsonRPC initialized")

    def call(self, method, params=None):
        request = {
            "jsonrpc": "2.0",
            "id": RPC_ID,
            "method": method,
        }
        if params is not None:
            request["params"] = params  

        request_json = json.dumps(request)
        response_json = xbmc.executeJSONRPC(request_json)
        response = json.loads(response_json)


        log_debug(str(request))    
        log_debug(str(response))

        return response

