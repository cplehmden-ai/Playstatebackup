import xbmc
from .constants import LOG_PREFIX

def log_info(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGINFO)


def log_warning(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGWARNING)


def log_error(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGERROR)


def log_debug(message):
    #xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGDEBUG)
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGINFO)
    