# Automatische Backup-Funktionalität

## Überblick

Das Addon kann jetzt automatisch im Hintergrund Backups erstellen, ohne dass der Benutzer eingreifen muss.

## Konfigurationsoptionen

In den Addon-Einstellungen unter **Automatische Sicherung**:

### 1. Automatische Sicherungsmodus
Drei Optionen:
- **Deaktiviert** (Standard) - Keine automatischen Backups
- **Beim Kodi-Start** - Ein Backup beim Start von Kodi
- **Zeitbasiert** - Regelmäßige Backups im eingestellten Intervall

### 2. Startversögerung (Sekunden)
*Nur aktiv bei "Beim Kodi-Start"*
- Verzögerung vor dem Backup nach dem Kodi-Start
- Standard: 30 Sekunden
- Minimum: 5 Sekunden
- **Warum?** Kodi lädt beim Start extrem viele Services. Die Verzögerung gibt dem System Zeit, sich zu stabilisieren.

### 3. Sicherungsintervall (Minuten)
*Nur aktiv bei "Zeitbasiert"*
- Zeit zwischen Backups
- Standard: 60 Minuten
- Minimum: 1 Minute

## Wie es funktioniert

### Beim Kodi-Start
```
1. Kodi startet
2. Service wird geladen (start="login" in addon.xml)
3. Wartet auf konfigurierte Verzögerung (Standard: 30 Sekunden)
4. Führt einmal Backup aus
5. Service beendet sich
```

### Zeitbasiert (Hintergrund-Monitoring)
```
1. Kodi startet
2. Service wird geladen
3. Service läuft im Hintergrund
4. Alle 60 Sekunden wird überprüft, ob Backup nötig ist
5. Wenn Backup-Intervall abgelaufen ist:
   - Backup wird ausgeführt
   - Zeitstempel wird aktualisiert
6. Service läuft bis Kodi beendet wird
```

## Service-Logik (service.py)

### AutoBackupService-Klasse
- `get_settings()` - Liest aktuelle Konfiguration
- `should_run_backup()` - Überprüft, ob Backup nötig ist
- `perform_backup()` - Führt alle Backup-Operationen aus
- `run()` - Hauptservice-Loop

### Backup-Operationen
Bei jedem automatischen Backup werden folgende Datensätze gesichert:
1. Video-Quellen (backup_paths)
2. Filme (backup_movies)
3. Episoden (backup_episodes)
4. Musikvideos (backup_musicvideos)
5. Unbekannte Videos (backup_videos)

## Kombination mit Backup-Management

Das automatische Backup arbeitet zusammen mit dem Backup-Management-System:
- Backups werden in Tagesordnern organisiert (`YYYY-MM-DD`)
- Maximum 2 Versionen pro Tag werden behalten
- Alte Tagesordner werden nach der konfigurierten Aufbewahrungsdauer gelöscht

### Beispiel-Szenario: Stündliche Backups mit 7-Tage-Retention
```
Einstellungen:
- Modus: Zeitbasiert
- Intervall: 60 Minuten
- Aufbewahrung: 7 Tage

Ergebnis:
- Tag 1: Hält maximal 2 Backups (ca. 6:00 AM und 5:00 PM)
- Tag 2-7: Jeweils 2 Backups
- Tag 8: Wird komplett gelöscht
- Gesamt: ~14 Backup-Dateien im Speicher
```

## Logging

Alle automatischen Backups werden geloggt:
```
INFO: Auto-backup service started
INFO: Interval-based backup configured: every 60 minutes
INFO: Starting automatic backup...
INFO: Automatic backup completed: 5/5 operations successful
INFO: Auto-backup service stopped
```

## Fehlerbehandlung

Wenn ein automatisches Backup fehlschlägt:
```
ERROR: Automatic backup failed: [Error Details]
```
- Fehler werden protokolliert, aber führen nicht zum Stopp des Services
- Der Service versucht das nächste Backup im konfigurierten Intervall

## Technische Details

### Service-Start
- In `addon.xml`: `<extension point="xbmc.service" library="service.py" start="login"/>`
- `start="login"` bedeutet: Der Service startet automatisch beim Kodi-Login
- Kein manueller Start nötig

### Monitor und Abort-Handling
- Nutzt `xbmc.Monitor()` für graceful Shutdown
- Beim Herunterfahren von Kodi wird der Service sauber beendet
- Läuft nicht, wenn Addon deaktiviert ist

### Timing
- "Zeitbasiert"-Modus prüft alle 60 Sekunden
- Verhindert zu häufige Überprüfungen (spart CPU)
- Backups laufen parallel zur normalen Kodi-Nutzung

## Szenarien

### Szenario 1: Nur manuelle Backups
```
Einstellung: Deaktiviert
→ Service lädt, beendet sich sofort
→ Nur manuelles Backup über Script möglich
```

### Szenario 2: Backup beim Start
```
Einstellung: Beim Kodi-Start, 30 Sekunden Verzögerung
→ Kodi startet
→ Service wartet 30 Sekunden
→ Backup läuft automatisch
→ Service beendet sich
→ Benutzer kann Kodi normal nutzen
```

### Szenario 3: Kontinuierliche Backups
```
Einstellung: Zeitbasiert, alle 60 Minuten
→ Service läuft im Hintergrund
→ Jede Stunde wird ein neues Backup erstellt
→ Läuft während Kodi aktiv ist
→ Pausiert nicht den Videowiedergabe
```

## Performance-Überlegungen

- Backup-Operationen nehmen JSON-Daten aus der Kodi-DB
- Dauert typischerweise 1-5 Sekunden
- SMB-Pfade können länger dauern (Netzwerk-I/O)
- Service hält den Rest von Kodi nicht auf
- CPU-Last ist gering (hauptsächlich Disk-I/O)

## Zukunfts-Verbesserungen

Mögliche Erweiterungen:
- Tageszeit-basierte Backups (z.B. jeden Tag um 02:00 Uhr)
- Benachrichtigungen bei Backup-Erfolg/Fehler
- Konfigurierbare Backup-Operationen (z.B. nur bestimmte Typen)
- Logging-Statistiken (Backup-Häufigkeit, Dateigröße)
