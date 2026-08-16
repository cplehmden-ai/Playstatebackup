# script.playstatebackup - Addon Dokumentation

## 🎯 Überblick

PlayState Backup sichert die **Gesehen-Zustände** und **Resume-Zeitpunkte** aller Videos extern ab und stellt sie bei Bedarf wieder her.

## ✅ Installation & Verwendung

### Das Addon funktioniert sofort nach Installation - keine weitere Konfiguration notwendig!

Das Addon unterstützt zwei Datenbanktypen:

1. **SQLite (Standard)** - Funktioniert direkt in Kodi
   - Die lokale Videodatenbank wird automatisch erkannt
   - Keine Konfiguration notwendig

2. **MySQL (Optional)** - Für zentrale Kodi-Datenbanken
   - Konfigurieren Sie `advancedsettings.xml` mit MySQL-Zugangsdaten
   - Das Addon verbindet sich automatisch

## 📦 Struktur

```
addon.xml                 # Addon-Metadaten
default.py               # Hauptskript
service.py               # Service/Daemon
lib/
  ├── backup.py          # Backup-Logik
  ├── restore.py         # Restore-Logik
  ├── videodb.py         # Datenbankverbindung (SQLite + MySQL)
  ├── database.py        # DB-Utilities
  ├── jsonrpc.py         # Kodi JSON-RPC API
  ├── logger.py          # Logging
  ├── mysql/             # MySQL Connector (bundled)
  │   └── connector/     # Pure Python MySQL-Client
  └── ...
resources/
  ├── settings.xml       # Addon-Einstellungen
  └── language/          # Lokalisierung
```

## 🔧 MySQL-Konfiguration (Optional)

Wenn Sie MySQL verwenden, konfigurieren Sie `advancedsettings.xml`:

```xml
<advancedsettings>
  <videodatabase>
    <type>mysql</type>
    <host>192.168.1.100</host>
    <port>3306</port>
    <user>kodi_user</user>
    <pass>password</pass>
    <name>MyVideos</name>
  </videodatabase>
</advancedsettings>
```

**Hinweis:** Der Datenbankname wird automatisch zu `myvideos{version}` (z.B. `myvideos131` für Kodi 21).

## 🐛 Entwicklung & Testing

Für Entwickler stehen folgende Tools zur Verfügung:

### Test der Datenbankverbindung
```bash
python test_database.py
```
Überprüft:
- ✓ Module importierbar
- ✓ VideoDB-Klasse ladbar
- ✓ SQLite/MySQL Erkennung
- ✓ Datenbankverbindung

### (Optional) MySQL-Connector aktualisieren
```bash
python setup_mysql_connector.py
```
Der Connector ist bereits enthalten. Dieses Skript ist nur für Updates auf neuere Versionen nötig.

## 📝 Verwendung im Code

```python
from lib.videodb import VideoDB
from lib.jsonrpc import JsonRPC

# JSON-RPC Verbindung zu Kodi
rpc = JsonRPC()

# VideoDB mit automatischer SQLite/MySQL Erkennung
videodb = VideoDB(rpc)

# Datenbankverbindung aufbauen
conn = videodb.get_database_connection()

if conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM version")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
```

## 🔗 MySQL-Datenbanknamen

Das Addon nutzt automatisch die korrekte Datenbank basierend auf der Kodi-Version:

| Kodi Version | Datenbankname |
|---|---|
| Kodi 20 | myvideos120 |
| Kodi 21 | myvideos131 |
| Kodi 22 | myvideos_zukünftig |

Die Versionsnummer wird aus der lokalen SQLite-Datenbank ausgelesen.

## ⚙️ Funktionsweise

### Backup-Prozess
1. Liest alle Filme, Serien und Musikvideos aus der Videobibliothek (via JSON-RPC)
2. Ermittelt Play-State (gesehen/ungegesen) und Resume-Position aller Filme, Serien und Musikvideos (via JSON-RPC)
3. Ermittelt Play-State (gesehen/ungegesen) und Resume-Position aller "sonstigen" Videos (via Datenbank, da es keine RPC Calls dafür gibt)
4. Speichert alles in JSON-Dateien
5. Kann manuell oder automatisch gestartet werden

### Ausschluss einzelner "Sonstige"-Quellen
Für Quellen mit unbekanntem Inhaltstyp (`unknown`) gibt es in den Addon-Einstellungen eine Aktion zum Auswählen und Deaktivieren einzelner Quellen. Standardmäßig sind alle Quellen aktiviert. Wenn eine Quelle ausgeschlossen wird, wird sie beim Backup übersprungen, obwohl sie weiterhin in Kodi als Videoquelle vorhanden ist.

### Restore-Prozess
1. Lädt gespeicherte JSON-Dateien
2. Verbindet sich zur Videodatenbank über JSON-RPC
3. Schreibt Play-State und Resume-Position aller Videos zurück

### Path-Remap-Prozess

Da es sein kann, das sich die Pfade zu den Medienquellen ändern und es bei sonstigen Videos nie, bei Musikvideos selten, bei Filmen und Serien aber meistens externe eindeutige ID gibt (Beispiel IMDB-ID) hat das Addon eine Option, um die Pfade aus dem Backup an die neuen Pfade der Medienquellen anzupassen, damit man auch nach einem Server- Umzug (o.Ä.) sein vollständiges Backup wieder zurück schreiben kann. Bei Filmen und Serien wird der Fallback zum Absichern über den Dateipfad wohl nur sehr selten mal notwendig sein, bei Musikvideos schon häufiger mal. "Sonstige" Videos kann man hingegen nur über den Dateipfad absichern. 


## 🚨 Troubleshooting

### SQLite/MySQL automatisch erkannt?
```bash
python test_database.py
```

### MySQL: "Server nicht erreichbar"
- Überprüfen Sie `advancedsettings.xml` (Host, Port, User, Pass)
- Stellen Sie sicher, dass der MySQL-Server läuft
- Überprüfen Sie Firewall-Einstellungen

### MySQL: "Datenbank nicht gefunden"
Das Addon sucht `myvideos{version}`, z.B. `myvideos131`.
Überprüfen Sie:
```sql
SHOW DATABASES LIKE 'myvideos%';
```

## 📚 Weitere Ressourcen

- [Kodi MySQL Setup](https://kodi.wiki/view/MySQL/Setting_up_MySQL)
- [MySQL Connector/Python Docs](https://dev.mysql.com/doc/connector-python/en/)
- [Kodi JSON-RPC API](https://kodi.wiki/view/JSON-RPC_API)

## � Changelog

### Unreleased
- Neue Option in den Addon-Einstellungen: Einzelne unbekannte Videoquellen vom Backup ausschließen
- Standardmäßig sind alle Videoquellen aktiviert
- Nur Quellen mit unbekanntem Inhaltstyp werden zur Auswahl angeboten

## �📄 Lizenz

GPL-3.0
