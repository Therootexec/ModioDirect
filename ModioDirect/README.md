# ModioDirect

**ModioDirect** is a crash-proof, single-file CLI tool for downloading mods
directly from **mod.io** using the official API.

No browser redirects.
No sketchy tools.
No crashes.

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
https://mod.io/g/spaceengineers/m/assault-weapons-pack1
```

## Why this exists

Most mod.io download tools are broken, outdated, or unsafe.
ModioDirect exists to be boring, correct, and reliable.

## Legal

This tool uses the official mod.io API.
You are responsible for complying with mod.io's terms of service.
