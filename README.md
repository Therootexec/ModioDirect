# ModioDirect v1.0.2 [![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![PyPI version](https://img.shields.io/pypi/v/modiodirect)](https://pypi.org/project/modiodirect/) [![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/Therootexec/ModioDirect) [![GitHub Stars](https://img.shields.io/github/stars/Therootexec/ModioDirect?style=social)](https://github.com/Therootexec/ModioDirect)

**ModioDirect** is a lightweight, single-file CLI that reliably downloads mods directly from [mod.io](https://mod.io) using the official API. It is safe, fast, and free for use. The tool also supports manual downloads using an API key, bypassing the official game client. It works with games such as *Space Engineers*, *SnowRunner*, *Deep Rock Galactic*, and many others.

![ModioDirectLogo1024x1024](https://github.com/user-attachments/assets/fc2687a6-61f1-42fb-bad2-57fa0df6fc73)

---


### Core Capabilities

- Uses only the official mod.io API
- Validates API keys before use
- Accepts standard mod.io URLs
- Fallback search when slugs fail to resolve
- Reliable downloads with automatic retries
- Optional progress bar via `tqdm`
- `--no-config` flag for shared or temporary environments
- Batch mode for multiple mods
- Optional auto-install on Windows (opt-in)
- Available on PyPI

### New in v1.0.2

- **Mod Profiles** – save and load different mod collections
- **Build Selector** – pick any file version to download (thanks to [@VaelophisNyx](https://github.com/VaelophisNyx))
- **Version Locking** – pin mods to specific versions
- **Auto Backups** – old versions saved before updates
- **Offline Library** – view every downloaded file, not just the latest
- **Integrity Scanner** – find and repair broken mods
- **Storage Analyzer** – track disk usage by mod
- **Export/Import** – share mod lists (JSON or TXT)
- **Update Checker** – see available updates
- **Rollback** – download older versions
- **Platform Scoring** – auto-selects PC files, avoids console builds (reported by [Lazyfluf](https://mod.io/u/lazyfluf))
- **Dependency Warnings** – detects missing requirements

### New CLI Options
- check-updates
- export
- rollback
- build-select
- profile
- debug


### New Configuration Files

| File 	                      | Purpose               |
| :--------------------------- | :-------------------- |
| profiles.json	             | Profile storage       |
| locked_mods.json	          | Version lock tracking |
| local_library.json	          | Offline library index |
| backups/backup_manifest.json | Backup tracking       |

> Additional details on these files are provided in the (......)

---

## Requirements
- Python 3.9 or higher
- Install dependencies:
  --requests,--rich,--tqdm

## Installation from PyPI
```
pip install modiodirect
```
```
modiodirect
```

## Basic Usage
```bash
Run: modiodirect.py
```
- When prompted, enter your mod.io API key. Example: ```0923d9369664ba08bd91c67......```

- (Optional)To avoid saving the API key to config.json, use: ``` python modiodirect.py --no-config
<mod_url>```

# *SIMPLY WALKTHROUGH*:
- Go to your [mod.io/me/access](https://mod.io/me/access) and copy:
<img width="1310" height="332" alt="Screenshot 2026-02-06 162920" src="https://github.com/user-attachments/assets/871142df-72c3-42b2-9655-f25d2b956488" />
<img width="1310" height="332" alt="Screenshot 2026-05-26 180452" src="https://github.com/user-attachments/assets/4959068a-7699-4c83-8bf6-6e5ea2985449" />


## Auto-Install (Windows Only) :(Requires the games.json to work)
Install directly to a detected game mod folder (optional):
```bash 
ModioDirect.py <mod_url> --install
```
This will scan common Steam and Epic install locations and let you select a mod folder. 

## Batch Download
- Create a text file (e.g., mods.txt).
- Place one mod.io URL per line.
- In the application, type:
- file:C:\path\to\mods.txt


## :exclamation: Security Notice
Your mod.io API key is private. Never share it or post it publicly.
ModioDirect stores the key locally and only uses it to communicate with the official mod.io API.

## Legal
This tool uses the official mod.io API. Users are responsible for complying with mod.io's Terms of Service.
ModioDirect is not affiliated with, endorsed by, or officially supported by mod.io. Use at your own risk.

## Access Limitations (Important)
Some game mods are private, unlisted, or require OAuth access. In those cases, the mod.io API returns 404 even if the URL exists. This is an access restriction, not a bug in ModioDirect.

If you see:
```
[Error] Mod is private, inaccessible, or requires authentication.
```
<img width="907" height="240" alt="Screenshot 2026-05-26 175602" src="https://github.com/user-attachments/assets/82d0d83a-5722-4851-8622-abda0c18664b" />



## API Key Limitations
- Use a public game or mod to verify that your API key is working.
- API keys can only access publicly available content.
- Private or unlisted mods are not accessible using API keys alone, as they require OAuth-based authentication.
- OAuth support is not currently implemented in ModioDirect. Future updates may add OAuth support if permitted by mod.io's policies.

## On (bata)
- Windows standalone executable (.exe) – coming soon.

## Special Thanks
Thanks to [@Diversion](https://github.com/diversionsec)
