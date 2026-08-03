import xbmcgui
from lib.constants import ADDON
from lib.jsonrpc import JsonRPC

def normalize(path):
    if not path:
        return ""

    return path.replace("\\", "/").rstrip("/")

def select_directory():
    dialog = xbmcgui.Dialog()

    return dialog.browseSingle(
        0,
        ADDON.getLocalizedString(30001),
        "files"
    )

def build_file_index(directory):

    rpc = JsonRPC()

    result = rpc.files_get_directory(directory)

    if not result:
        return {}

    index = {}

    for item in result:
        index[normalize(item["file"])] = item

    return index