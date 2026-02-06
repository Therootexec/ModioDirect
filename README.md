# ModioDirect

**ModioDirect is a lightweight, single-file CLI that reliably downloads mods straight from mod.io via the official API—safe, fast, and hassle-free. It also allows manual downloads using an API key, bypassing the official game client.
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
https://mod.io/g/spaceengineers/m/assault-weapons-pack1
```

## Why this exists

Most mod.io download tools are broken, outdated, or unsafe.
ModioDirect exists to be simple, reliable, and safe. It also allows manual downloads using an API key, bypassing the official game client

#Feature Comparison Table With Others
| Feature | ModioDirect | SEModDownloaderMod.io | ModioModNetworker |
   |--------|-------------|------------------------|-------------------|
   | CLI Only | ✅ | ❌ | ❌ |
   | No GUI Needed | ✅ | ❌ | ❌ |
   | Single File | ✅ | ❌ | ❌ |
   | Cross-Game | ✅ | Limited | Game-Specific |

## Legal

This tool uses the official mod.io API.
You are responsible for complying with mod.io's terms of service.

## Access limitations (important)

Some games/mods are private, unlisted, or require OAuth access. In those cases, the mod.io API returns 404 even if the URL exists. This is an access restriction, not a bug in ModioDirect.

If you see:

```
[Error] Game not accessible (404). The game may be private, unpublished, or require OAuth access.
```

Try a public game/mod to verify your API key works. Private/unlisted mods require OAuth and are not accessible with API keys alone.

Future updates may add OAuth support if allowed by mod.io policy.

