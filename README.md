# ModioDirect v1.0.1 ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

**ModioDirect is a lightweight, single-file CLI that reliably downloads mods straight from mod.io via the official API—safe, fast, and free for use. It also allows manual downloads using an API key, bypassing the official game client.
Supports games like Space Engineers, SnowRunner, and more.

![ModioDirectLogo1024x1024](https://github.com/user-attachments/assets/fc2687a6-61f1-42fb-bad2-57fa0df6fc73)




## Features
- Official mod.io API only
- Validates API key
- Supports real mod.io URLs
- Fallback search when slugs fail
- Safe downloads with retries
- Progress bar (tqdm optional)
- Works on Windows & Linux
- Optional `--no-config` for shared machines
- Batch mode support
- Optional auto‑install on Windows (opt‑in)

## Requirements
- Python 3.9+
- `pip install requests tqdm`

## Install From PyPI
```bash
pip install modiodirect
```
Run:
```bash
modiodirect
```

## How To Use It
```bash
python modiodirect.py 
```
## Add Your Mod.io API Key E.g 
```bash
0923d9369664ba08bd91c67.........
```
(optional) To avoid saving the API key to `config.json`:

```bash
python modiodirect.py --no-config
```

Paste a URL like:

```
https://mod.io/g/GAME/m/example-mod
```
## Auto‑Install (Windows Only)
   Install directly to a detected game mod folder (optional):

```bash
python ModioDirect.py <mod_url> --install
```

This will scan common Steam/Epic install locations and let you pick a mod folder.

## Batch Download (Simple)  
1. Create a text file (example: `mods.txt`)
2. Put one mod.io URL per line
3. In the app, type:

```
file:C:\path\to\mods.txt
```
## :exclamation: Security Notice:
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


API Key Limitations
Use a public game or mod to verify that your API key is working.
API keys can only access publicly available content.
Private or unlisted mods are not accessible using API keys alone, as they require OAuth-based authentication.
OAuth support is not currently implemented in ModioDirect. Future updates may add OAuth support if permitted by mod.io’s policies.

## Upcoming Features Updates
 ModioDirect is actively maintained. The following features are planned for future releases:
- Windows standalone executable (.exe)
  A portable build for Windows users that does not require Python.


## 🌟 Special Thanks

Thanks to [@Diversion-CTF](https://github.com/Diversion-CTF) For helping with the logo

## 🤝 Contributions and feature requests are welcome
Please open an issue to discuss your ideas or suggestions.

