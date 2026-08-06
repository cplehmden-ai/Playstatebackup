import xbmc
from lib.jsonrpc import JsonRPC
from lib.utils import normalize
#from lib.logger import log_info

class VideoDB:

    def __init__(self, rpc):
        self.rpc = rpc

    def get_directory_index(self, directory):

        result = self.rpc.files_get_directory(
            directory,
            properties=[
                "playcount",
                "lastplayed",
                "resume",
                "dateadded",
            ]
        )

        if not result:
            return {}

        index = {}

        for item in result.get("files", []):
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
                # extra milliseconds to ensure Kodi has finished
                # all pending database updates.             
                xbmc.sleep(100)
                return True
            

    def open_directory(self, directory):

        command = 'ActivateWindow(Videos,"{}",return)'.format(directory)

        xbmc.executebuiltin(command)

        xbmc.sleep(500)
            
    def get_subdirectories(self, directory):

#        rpc = JsonRPC()

        result = self.rpc.files_get_directory(directory)

        if not result:
            return []

        subdirectories = []

        for item in result.get("files", []):

            if item.get("filetype") == "directory":
                subdirectories.append(item["file"])

        return subdirectories
                
    def collect_directories(self, directory):

        directories = [directory]

        for subdirectory in self.get_subdirectories(directory):
            directories.extend(
                self.collect_directories(subdirectory)
            )

        return directories

    def video_library_get_movies(self):

        result = self.rpc.call("VideoLibrary.GetMovies", {
            "properties": [
                "playcount",
                "lastplayed",
                "resume",
                "dateadded",
                "uniqueid",
                "file",
                "title",
            ]
        })

        if not result:
            return []

        return result.get("result", {}).get("movies", [])


