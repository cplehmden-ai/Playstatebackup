import xbmc
from lib.jsonrpc import JsonRPC
from lib.utils import normalize
from lib.logger import log_info

class VideoDB:

    def __init__(self, rpc):
        self.rpc = rpc

    def get_directory_index(self, directory):

        result = self.rpc.files_get_directory(directory)

        index = {}

        for item in result:
            index[normalize(item["file"])] = item

        return index

    def wait_for_directory(self, directory):

        while True:

            files = self.get_directory_index(directory)

            all_ready = True

            ready = 0

            for item in files.values():

                if item.get("dateadded"):
                    ready += 1

                if not item.get("dateadded"):
                    all_ready = False
                    break

            if all_ready:
                return True
            
            # One extra second to ensure Kodi has finished
            # all pending database updates.             
            xbmc.sleep(1000)

    def open_directory(self, directory):

        command = 'ActivateWindow(Videos,"{}",return)'.format(directory)

        xbmc.executebuiltin(command)

        xbmc.sleep(500)