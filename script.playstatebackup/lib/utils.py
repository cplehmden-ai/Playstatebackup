import xbmcgui
import os
import xml.etree.ElementTree as ET
import xbmcvfs
from lib.constants import ADDON
from lib.logger import log_debug, log_error

def normalize(path):
    if not path:
        return ""

    return path.replace("\\", "/").rstrip("/")

def select_directory():
    dialog = xbmcgui.Dialog()

    directory = dialog.browseSingle(
        0,
        ADDON.getLocalizedString(30001),
        "files"
    )

    if not directory:
        return ""

    return normalize(directory)

def find_file(file_index, path):
    return file_index.get(normalize(path))

def read_mysql_credentials():

    xml_path = xbmcvfs.translatePath('special://userdata/advancedsettings.xml')

    my_setting_value = 'default_value'

    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            node = root.find('.//videodatabase/host')
            if node is not None and node.text:
                my_setting_value = node.text
                
        except ET.ParseError as e:
            log_error(f"Fehler beim Lesen der advancedsettings.xml: {e}")

    # Verwenden des Wertes im Add-on
    log_debug(f"Gelesener Wert: {my_setting_value}")
