import xbmc
import time
from lib.logger import log_info, log_error
from lib.jsonrpc import JsonRPC
from lib.utils import select_directory
from lib.videodb import VideoDB
from lib.backup import Backup

def main():
    log_info("started")

    rpc = JsonRPC()
    videodb = VideoDB(rpc)
    backup = Backup(rpc, videodb)

    movie_backup = backup.backup_movies()

    log_info("Movies backed up: {}".format(len(movie_backup)))

    for movie in movie_backup:
        log_info(str(movie))

    
#    movies = videodb.video_library_get_movies()

#    log_info("Found {} movies".format(len(movies)))

#    if movies:
#        movie = movies[0]

#        log_info(str(movie))

#    directory = select_directory()

#    if directory:

#        log_info("Opening directory: {}".format(directory))

#        backup_data = backup.backup_directory(directory)

#        log_info("Backup contains {} entries".format(len(backup_data)))

#        for entry in backup_data:
#            log_info(str(entry))
 
if __name__ == "__main__":
    main()