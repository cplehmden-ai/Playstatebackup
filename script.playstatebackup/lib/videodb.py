import json
import xbmc
import lib.constants as constants
from lib.utils import normalize
from lib.logger import log_debug, log_error
import os
import glob
from xbmcvfs import translatePath
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, Union
import sqlite3

class VideoDB:

    def __init__(self, rpc):
        self.rpc = rpc

    def get_kodi_profile_path(self) -> Optional[Path]:
        """
        Ermittelt den Pfad zum Kodi-Profilverzeichnis.
        
        Returns:
            Path zum userdata Verzeichnis oder None wenn nicht gefunden
        """
        # Versuche über Kodi API
        profile_path = translatePath('special://profile')
        if profile_path and profile_path != 'special://profile':
            return Path(profile_path)
        
        return None

    def read_advancedsettings(self) -> Optional[ET.Element]:
        """
        Liest die advancedsettings.xml aus dem Kodi-Profilverzeichnis.
        
        Returns:
            XML Element root oder None wenn Datei nicht gefunden
        """
        profile_path = self.get_kodi_profile_path()
        if not profile_path:
            return None
        
        advanced_settings_file = profile_path / 'advancedsettings.xml'
        
        if not advanced_settings_file.exists():
            return None
        
        try:
            tree = ET.parse(str(advanced_settings_file))
            return tree.getroot()
        except Exception as e:
            log_error(f"Fehler beim Parsen von advancedsettings.xml: {e}")
            return None

    def get_mysql_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Liest die MySQL-Zugangsdaten für die Videodatenbank aus advancedsettings.xml.
        
        Returns:
            Dictionary mit Zugangsdaten oder None wenn nicht konfiguriert
            
        Beispiel:
            {
                'type': 'mysql',
                'host': 'localhost',
                'port': 3306,
                'user': 'kodi',
                'pass': 'password',
                'name': 'MyVideos119'
            }
        """
        root = self.read_advancedsettings()
        if root is None:
            return None
        
        # Suche nach videodatabase Element
        videodb = root.find('.//videodatabase')
        if videodb is None:
            return None
        
        # Überprüfe ob es MySQL ist
        db_type = videodb.findtext('type', '').lower()
        if db_type != 'mysql':
            return None
        
        credentials = {
            'type': videodb.findtext('type'),
            'host': videodb.findtext('host'),
            'port': int(videodb.findtext('port', '3306')),
            'user': videodb.findtext('user'),
            'pass': videodb.findtext('pass'),
            'name': videodb.findtext('name')
        }
        
        return credentials

    def _load_mysql_connector(self):
        """Lädt den gebündelten MySQL-Connector aus dem Projekt; nur als Fallback externe Pakete."""
        import importlib
        import sys

        for module_name in list(sys.modules):
            if module_name == "mysql" or module_name.startswith("mysql."):
                del sys.modules[module_name]

        try:
            bundled_mysql = importlib.import_module("lib.mysql")
            bundled_mysql.__path__ = [str(Path(bundled_mysql.__file__).parent)]
            sys.modules["mysql"] = bundled_mysql
            connector = importlib.import_module("mysql.connector")
            return connector
        except ImportError:
            try:
                connector = importlib.import_module("mysql.connector")
                return connector
            except ImportError:
                log_error("mysql.connector nicht gefunden. Bitte führen Sie setup_mysql_connector.py aus.")
                return None

    def get_database_connection(self) -> Optional[Union[sqlite3.Connection, Any]]:
        """
        Stellt eine Datenbankverbindung her. Bevorzugt MySQL wenn konfiguriert, sonst SQLite.
        
        Priorität:
        1. MySQL (wenn in advancedsettings.xml konfiguriert)
        2. SQLite (lokal, Standard)
        
        Returns:
            sqlite3.Connection oder mysql.connector.connection oder None wenn keine Verbindung möglich
        """
        # Überprüfe zuerst ob MySQL konfiguriert ist
        credentials = self.get_mysql_credentials()
        
        if credentials:
            # MySQL ist konfiguriert - nutze MySQL
            log_debug("MySQL konfiguriert - nutze MySQL Verbindung")
            
            connector = self._load_mysql_connector()
            if connector is None:
                log_error("mysql.connector nicht gefunden. Bitte führen Sie setup_mysql_connector.py aus.")
                return None
            
            try:
                # Bestimme den korrekten Datenbanknamen
                # Format: myvideos + Versionsnummer (z.B. myvideos131 für Kodi 21)
                db_version = self.get_videodb_version()
                
                if db_version:
                    # Nutze die lokale Versionsnummer für MySQL-Verbindung
                    db_name = f"myvideos{db_version}"
                    log_debug(f"Nutze Datenbank aus lokaler Version: {db_name}")
                else:
                    # Fallback auf Credentials wenn keine lokale DB vorhanden
                    db_name = credentials['name']
                    log_debug(f"Nutze Datenbank aus Credentials: {db_name}")
                
                conn = connector.connect(
                    host=credentials['host'],
                    user=credentials['user'],
                    password=credentials['pass'],
                    database=db_name,
                    port=credentials['port']
                )
                
                log_debug(f"MySQL Verbindung hergestellt: {credentials['host']}/{db_name}")
                return conn
            except connector.Error as err:
                if err.errno == 2003:
                    log_error(f"MySQL Server nicht erreichbar: {credentials['host']}:{credentials['port']}")
                elif err.errno == 1045:
                    log_error("MySQL Authentifizierungsfehler - Benutzername oder Passwort falsch")
                elif err.errno == 1049:
                    log_error(f"MySQL Datenbank nicht gefunden: {db_name}")
                else:
                    log_error(f"MySQL Fehler: {err}")
                return None
            except Exception as e:
                log_error(f"MySQL Verbindung fehlgeschlagen: {e}")
                return None
        
        # MySQL nicht konfiguriert - versuche SQLite
        try:
            db_version = self.get_videodb_version()
            if db_version:
                log_debug(f"Nutze lokale SQLite Videodatenbank (Version: {db_version})")
                
                # Verbindung zu SQLite aufbauen
                db_dir = translatePath("special://database/")
                pattern = os.path.join(db_dir, "MyVideos*.db")
                db_files = glob.glob(pattern)
                
                if db_files:
                    db_files.sort()
                    latest_db_path = db_files[-1]
                    conn = sqlite3.connect(latest_db_path)
                    log_debug(f"SQLite Verbindung hergestellt: {latest_db_path}")
                    return conn
        except Exception as e:
            log_error(f"SQLite nicht verfügbar: {e}")
        
        log_error("Keine Datenbankverbindung möglich")
        return None

    def get_database_type(self) -> Optional[str]:
        """
        Gibt den Typ der konfigurierten Videodatenbank zurück.
        
        Returns:
            'sqlite', 'mysql' oder None wenn keine erkannt
        """
        db_version = None
        
        # Überprüfe zuerst SQLite
        try:
            db_version = self.get_videodb_version()
            if db_version:
                return 'sqlite'
        except Exception:
            pass
        
        # Überprüfe dann MySQL
        if self.get_mysql_credentials():
            return 'mysql'
        
        return None


    def get_videodb_version(self):
        """Liest die Datenbankversion aus der SQLite Datenbank"""
        db_version = None
        db_dir = translatePath("special://database/")

        pattern = os.path.join(db_dir, "MyVideos*.db")
        db_files = glob.glob(pattern)

        if db_files:
            db_files.sort()
            latest_db_path = db_files[-1]
            db_filename = os.path.basename(latest_db_path)
            
            log_debug(f"Gefundene DB-Datei: {db_filename}")
            
            conn = sqlite3.connect(latest_db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT idVersion FROM version")
                db_version = cursor.fetchone()[0]
                log_debug(f"Interne Datenbank-Version: {db_version}")
            except Exception as e:
                log_error(f"Fehler beim Lesen der Version: {e}")
            finally:
                conn.close()
        return db_version


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

            if item.get("filetype") != "file":
                continue

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

    def get_disabled_video_sources(self):
        return self.get_blacklisted_video_sources("disabled_video_sources")

    def set_disabled_video_sources(self, paths):
        normalized_paths = [normalize(str(path)) for path in paths if path]
        constants.ADDON.setSetting("disabled_video_sources", json.dumps(normalized_paths))
        return normalized_paths

    def get_blacklisted_video_sources(self, setting_name="blacklisted_video_sources"):
        candidates = [setting_name, "disabled_video_sources"]
        values = set()

        for key in candidates:
            raw_value = constants.ADDON.getSetting(key) or "[]"
            try:
                parsed = json.loads(raw_value)
            except (TypeError, ValueError):
                parsed = []

            if isinstance(parsed, str):
                parsed = [parsed]

            for item in parsed or []:
                if item is None:
                    continue
                values.add(normalize(str(item)))

        return values

    def set_blacklisted_video_sources(self, paths):
        normalized_paths = [normalize(str(path)) for path in paths if path]
        constants.ADDON.setSetting("blacklisted_video_sources", json.dumps(normalized_paths))
        return normalized_paths

    def get_unknown_video_sources(self):
        sources = self.get_video_source_types()
        return [source for source in sources if source.get("content") == "unknown"]

    def _get_bookmark_schema(self, conn):
        """Returns the bookmark column mapping for the current Kodi schema."""
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(bookmark)")
            columns = [row[1] for row in cursor.fetchall()]
        except Exception:
            columns = []

        if "timeInSeconds" in columns and "totalTimeInSeconds" in columns:
            return {
                "resume_col": "b.timeInSeconds",
                "total_col": "b.totalTimeInSeconds",
                "playcount_col": "f.playCount",
                "lastplayed_col": "f.lastPlayed",
            }

        # Kodi 21+ uses this schema; if metadata is unavailable in a lightweight
        # test double or a very minimal DB wrapper, keep the modern mapping as the default.
        return {
            "resume_col": "b.timeInSeconds",
            "total_col": "b.totalTimeInSeconds",
            "playcount_col": "f.playCount",
            "lastplayed_col": "f.lastPlayed",
        }

    def get_unknown_video_database_entries(self):
        conn = self.get_database_connection()
        if conn is None:
            log_error("No database connection available for unknown video backup")
            return []

        try:
            cursor = conn.cursor()
            bookmark_schema = self._get_bookmark_schema(conn)

            if bookmark_schema is None:
                log_error("Unsupported bookmark schema in Kodi database")
                return []

            query = f"""
                SELECT
                    f.idFile,
                    p.strPath AS path_base,
                    f.strFilename AS file_name,
                    f.playCount,
                    f.lastPlayed,
                    f.dateAdded,
                    {bookmark_schema['resume_col']} AS resume_time,
                    {bookmark_schema['total_col']} AS total_time,
                    {bookmark_schema['playcount_col']} AS bookmark_playcount,
                    {bookmark_schema['lastplayed_col']} AS bookmark_lastplayed
                FROM files AS f
                JOIN path AS p ON p.idPath = f.idPath
                LEFT JOIN bookmark AS b ON b.idFile = f.idFile
                WHERE f.strFilename IS NOT NULL
            """

            try:
                cursor.execute(query)
                raw_rows = cursor.fetchall()
            except Exception as e:
                log_error(f"Unknown-video query failed for Kodi bookmark schema: {e}")
                raw_rows = []

            if not raw_rows:
                log_debug("Could not read unknown video entries from Kodi database")
                return []

            entries = []
            for row in raw_rows:
                if len(row) < 10:
                    continue

                file_id, path_base, file_name, playcount, lastplayed, dateadded, resume_time, total_time, bookmark_playcount, bookmark_lastplayed = row[:10]

                path_base = path_base or ""
                file_name = file_name or ""
                if path_base and not path_base.endswith(("/", "\\")) and not file_name.startswith(("/", "\\")):
                    full_path = normalize(f"{path_base}/{file_name}")
                else:
                    full_path = normalize(f"{path_base}{file_name}")

                if not full_path:
                    continue

                resume_value = 0
                if resume_time not in (None, ''):
                    try:
                        resume_value = int(resume_time)
                    except (TypeError, ValueError):
                        resume_value = 0

                entries.append({
                    "idFile": file_id,
                    "file": full_path,
                    "playcount": int(playcount) if playcount not in (None, '') else 0,
                    "lastplayed": lastplayed or bookmark_lastplayed,
                    "dateadded": dateadded,
                    "resume": {
                        "position": resume_value,
                        "total": int(total_time) if total_time not in (None, '') else 0,
                    },
                    "bookmark_playcount": bookmark_playcount,
                    "bookmark_lastplayed": bookmark_lastplayed,
                })

            return entries
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def is_source_enabled(self, source):
        if isinstance(source, dict):
            path = source.get("path")
        else:
            path = source

        if not path:
            return True

        normalized_path = normalize(path)
        return normalized_path not in self.get_disabled_video_sources()

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
                "enabled": self.is_source_enabled(path),
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