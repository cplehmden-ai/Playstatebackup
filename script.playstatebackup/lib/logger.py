import xbmc
from .constants import LOG_PREFIX

def log_error(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGERROR)

def log_debug(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGDEBUG)

def log_info(message):
    xbmc.log(f"{LOG_PREFIX} {message}", xbmc.LOGINFO)
    