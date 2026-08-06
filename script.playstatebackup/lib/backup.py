#import xbmc
from lib.videodb import VideoDB
from lib.logger import log_info

class Backup:

    def __init__(self, rpc, videodb):
            self.rpc = rpc
            self.videodb = videodb

    def backup_directory(self, directory):

        index = self.videodb.get_directory_index(directory)

        backup_data = []

        log_info("{} files found".format(len(index)))

        for path, item in index.items():
            log_info(str(item))
            break

        entry = {
                    "path": path,
                }

        backup_data.append(entry)


        return backup_data

    def create_movie_backup(self, movie):

        playcount = movie.get("playcount", 0)
        resume_position = movie.get("resume", {}).get("position", 0)

        if playcount == 0 and resume_position == 0:
            return None

        entry = {
            "title": movie.get("title"),
            "file": movie.get("file"),
            "playcount": movie.get("playcount"),
            "lastplayed": movie.get("lastplayed"),
            "resume": movie.get("resume"),
            "uniqueid": movie.get("uniqueid"),
        }

        return entry


    def backup_movies(self):

        movies = self.videodb.video_library_get_movies()

        backup = []

        for movie in movies:
            entry = self.create_movie_backup(movie)

            if entry:
                backup.append(entry)

        return backup