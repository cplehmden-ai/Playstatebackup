import json
import xbmc

from lib.constants import RPC_ID
from lib.logger import log_info, log_debug, log_error

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

        log_debug(str(request))

        request_json = json.dumps(request)

        response_json = xbmc.executeJSONRPC(request_json)

        try:
            response = json.loads(response_json)
        except Exception as e:
            log_error("Invalid JSON response: {}".format(e))
            log_error(response_json)
            return None

        if "error" in response:
            log_error(str(response["error"]))

        log_debug(str(response))

        return response
    
    def version(self):
        return self.call("JSONRPC.Version")

    def get_setting_value(self, setting_name):
        response = self.call(
            "Settings.GetSettingValue",
            {
                "setting": setting_name
            }
        )

        if response and "result" in response:
            return response["result"]["value"]

        return None  

    def files_get_directory(self, directory):

        params = {
            "directory": directory,
            "media": "video",
            "properties": [
                "dateadded",
                "playcount",
                "lastplayed",
                "resume"
            ]
        }

        response = self.call("Files.GetDirectory", params)

        if not response:
            return []

        if "result" not in response:
            return []

        return response["result"].get("files", [])    