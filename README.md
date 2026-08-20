# PlayState Backup for Kodi

PlayState Backup stores the playback status of your videos outside Kodi's video database. The saved states can be restored whenever needed.

This is especially useful when:

- rebuilding Kodi's video database
- moving to a different device or system
- recovering from database problems
- moving a media collection to another drive or server

## Features

- Backup and restore for movies
- Backup and restore for TV shows and episodes
- Backup and restore for music videos
- Backup and restore for other, uncategorized videos
- Storage of watched status, playcount, and resume position
- Full or partial backups
- Automatic backups at Kodi startup or at a configurable interval
- Daily backup sets with configurable retention
- Exclusion of individual unknown video sources from backups
- Support for local and centralized Kodi video databases
- Multilingual user interface

## Path Mapping

When media paths change after a migration, the old sources in a backup set can be mapped to their new locations once.

Example:

```text
D:\Videos\     ->     smb://server/Movies/
```

The mapping also applies to files in subfolders. It is only needed when restoring after a media path change. A regular restore uses the paths stored in the backup as usual.

## Installation

The addon is available through the [Kodinerds Repository](https://repo.kodinerds.net/index.php).

It can also be installed like any other Kodi addon, for example from a ZIP file.

After installation, choose a backup location in the addon settings. The backup and restore functions are then available from the addon menu.

## Backup Storage

Each backup set is stored in its own daily folder. The storage location can be local or on a network share accessible to Kodi.

Backup files contain only the information required for restoration. The media files themselves are not copied.

## Notes

- Media sources should be online and reachable during a restore.
- A restore updates playback status but does not scan new media into Kodi's library.
- Matching uncategorized videos relies heavily on their file paths.
- Create a current backup before making major changes to Kodi's video database.

## License

GPL-3.0
