# ModioDirect v1.0.0 ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

**ModioDirect is a lightweight, single-file CLI that reliably downloads mods straight from mod.io via the official API—safe, fast, and free for use. It also allows manual downloads using an API key, bypassing the official game client.
Supports games like Space Engineers, SnowRunner, and more.

<img width="1007" height="678" alt="ModioDirect-logo" src="https://github.com/user-attachments/assets/b4de5993-b6fb-4980-98ba-ed63c7871732" />

## Features
- Official mod.io API only
- Validates API key
- Supports real mod.io URLs
- Fallback search when slugs fail
- Safe downloads with retries
- Progress bar (tqdm optional)
- Works on Windows & Linux
- Optional `--no-config` for shared machines

## Requirements
- Python 3.9+
- `pip install requests tqdm`

## Usage
```bash
python modiodirect.py
```

To avoid saving the API key to `config.json`:

```bash
python modiodirect.py --no-config
```

Paste a URL like:

```
https://mod.io/g/GAME/m/example-mod
```
## Security Notice:
   Your mod.io API key is private. Never share it or post it publicly.
   ModioDirect stores the key locally and only uses it to communicate
   with the official mod.io API.

# *SIMPLY WALKTHROUGH*:
<img width="1310" height="332" alt="Screenshot 2026-02-06 162920" src="https://github.com/user-attachments/assets/871142df-72c3-42b2-9655-f25d2b956488" />
<img width="1094" height="368" alt="Screenshot 2026-02-06 164436" src="https://github.com/user-attachments/assets/f351d3f7-8bc0-46b5-8c8b-1fe03af22332" />


## Why this exists

Most mod.io download tools are broken, outdated, or unsafe—and frankly, frustrating to use. ModioDirect was made to fix that: simple, reliable, and safe. It gives you full control, letting you manually download mods with an API key and even bypass the official game client when needed. No clutter, no crashes, just the mods you want, when you want them.


## Legal
This tool uses the official mod.io API. Users are responsible for complying with mod.io's Terms of Service.
This tool is not affiliated with, endorsed by, or officially supported by mod.io. Use at your own risk.

## 🔴Access limitations (important)🔴

Some games/mods are private, unlisted, or require OAuth access. In those cases, the mod.io API returns 404 even if the URL exists. This is an access restriction, not a bug in ModioDirect.

If you see:

```
[Error] Game not accessible (404). The game may be private, unpublished, or require OAuth access.
```
<img width="1093" height="309" alt="Screenshot 2026-02-06 170047" src="https://github.com/user-attachments/assets/eb1148df-ef85-468f-a21b-d99cd26901db" />


Try a public game/mod to verify your API key works. "Private/unlisted mods require OAuth and are not accessible with API keys alone."

Future updates may add OAuth support if allowed by mod.io policy.

## Upcoming Features Updates
 ModioDirect is actively maintained. The following features are planned for future releases:
- Batch mod downloads
  Download multiple mods in one run using a text file containing mod.io URLs.
- Optional auto-install to game mod folders
  Detect common game mod directories (opt-in only, user confirmation required).
- Windows standalone executable (.exe)
  A portable build for Windows users that does not require Python.
- PyPI package distribution
  Install ModioDirect using pip install modiodirect and run it as a system command.


## :handshake: Feature requests and contributions are welcome via GitHub issues.



