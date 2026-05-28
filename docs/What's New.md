ModioDirect v1.0.2 – What's New
Here's the changelog for the update v1.0.2. 

1. Mod Profiles
Save different mod setups as named profiles. Each profile tracks which mods go together, their versions, and where they're installed. Switch between profiles with one command, or restore an entire profile's worth of mods in a single operation.

2. Version Locking
Pin a mod to a specific version. The update checker will warn you if a newer version exists but won't touch locked mods. Prevents broken updates from overwriting a working setup.

3. Automatic Backups
When updating a mod, the old version gets backed up automatically to the backups/ folder. Keeps the last 5 versions per mod. Restore from backup if an update causes problems.

4. Offline Library
The tool now scans your entire downloads folder instead of relying only on cache data. Shows every mod file you've downloaded, not just the most recent one. Also indexes backup files separately.

5. Integrity Scanner
Checks downloaded mods for corruption or incomplete downloads. Verifies file sizes and tests ZIP archives. If something's broken, offers to re-download it automatically.

6. Storage Analyzer
Breaks down disk usage by mod file. Shows which files take up the most space and separates download storage from backup storage.

7. Export & Import
Export your mod list to JSON or a simple text file with URLs. Import a previously exported list to re-download everything. Works with individual profiles too.

8. Update Checker
Scans cached mods against the mod.io API and reports which ones have newer versions available. No automatic updates – just information.

9. Compatibility Checker
Compares installed files against cache data. Flags missing files, size mismatches, or install paths that no longer exist.

10. Build Selector & Rollback
When a mod has multiple file versions, you get an interactive table showing filename, version, size, date, and platform compatibility. Pick any version to download. For rollbacks, the same interface works but warns you about using older builds.

11. Platform Scoring
Automatically detects PC-friendly files based on keywords (windows, pc, win64, x64, desktop) and filters out console-specific builds (xbox, ps4, ps5, switch). Picks the best match by default.

12. Dependency Warnings
Scans mod descriptions for common dependency names (BepInEx, MelonLoader, Harmony, Forge, Fabric). If a dependency isn't in your local cache, you get a warning before downloading.

CLI Additions:
- check-updates :   Scan for updates 
- export :          Export/import mod list to JSON/TXT 
- rollback :        Show version selector before download
- build-select :    Show build selector before download
- profile NAME :    Add downloaded mod to a named profile
- debug :           Show full tracebacks on errors
- force :           Reinstall regardless of cached version

New Files
|File 	                       | Purpose               |
| :--------------------------- | :---------------------|
| profiles.json	               | Profile storage       |
| locked_mods.json	           | Version lock tracking |
| local_library.json	         |Offline library index  |
| backups/backup_manifest.json |Backup tracking        |       

Full code on GitHub: https://github.com/Therootexec/ModioDirect
