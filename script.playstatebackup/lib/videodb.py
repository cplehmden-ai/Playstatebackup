import xbmc
from lib.jsonrpc import JsonRPC
from lib.utils import normalize
from lib.logger import log_info

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


    def video_library_get_musicvideos(self):

        result = self.rpc.call("VideoLibrary.GetMusicvideos", {
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

        return result.get("result", {}).get("musicvideos", [])

    def video_library_get_tvshows(self):

        result = self.rpc.call("VideoLibrary.GetTVShows", {
            "properties": [
                "file",
            ]
        })

        if not result:
            return []

        return result.get("result", {}).get("tvshows", [])    

    def get_videos_from_directory(self, directory):

#        result = self.rpc.files_get_directory(
#            directory,
#            media="video",)

        result = self.rpc.files_get_directory(
            directory,
            media="video",
#            properties=[
#                "playcount",
#                "lastplayed",
#                "resume",
#                "dateadded",
#                "label",
#            ]
        )

        if not result:
            return []

        return result.get("files", [])

    def get_video_sources(self):

        result = self.rpc.call(
            "Files.GetSources",
            {
                "media": "video"
            }
        )

        if not result:
            return []

        return result.get("result", {}).get("sources", [])

    def is_backup_source(self, path):
        if path.startswith("addons://"):
            return False

        if path.startswith("pvr://"):
            return False

        return True

    def get_video_source_types(self):

        sources = self.get_video_sources()

        movies = self.video_library_get_movies()
        tvshows = self.video_library_get_tvshows()
        musicvideos = self.video_library_get_musicvideos()

        movie_paths = [
            normalize(item["file"])
            for item in movies
            if item.get("file")
        ]

        tvshow_paths = [
            normalize(item["file"])
            for item in tvshows
            if item.get("file")
        ]

        musicvideo_paths = [
            normalize(item["file"])
            for item in musicvideos
            if item.get("file")
        ]

        result = []

        for source in sources:

            path = source.get("file")

            if not path:
                continue

            if not self.is_backup_source(path):
                continue

            normalized_source = normalize(path)

            content = "unknown"

            for media_path in movie_paths:
                if media_path.startswith(normalized_source):
                    content = "movies"
                    break

            if content == "unknown":
                for media_path in tvshow_paths:
                    if media_path.startswith(normalized_source):
                        content = "tvshows"
                        break

            if content == "unknown":
                for media_path in musicvideo_paths:
                    if media_path.startswith(normalized_source):
                        content = "musicvideos"
                        break

            result.append({
                "path": path,
                "label": source.get("label", ""),
                "content": content,
            })

        return result    

    def video_library_get_episodes(self):

        result = self.rpc.call("VideoLibrary.GetEpisodes", {
            "properties": [
                "playcount",
                "lastplayed",
                "resume",
                "dateadded",
                "uniqueid",
                "file",
                "title",
                "season",
                "episode",
            ]
        })

        if not result:
            return []

        return result.get("result", {}).get("episodes", [])