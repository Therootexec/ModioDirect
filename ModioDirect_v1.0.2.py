#!/usr/bin/env python3
# ModioDirect — v1.0.2               
# Original by TheRootExec | Extended with advanced mod management features                            
# Architecture: Single-file CLI, mod.io API v1. Mod Downloader

# New users
import subprocess
import sys
import os
import time

REQUIRED_PACKAGES = ['requests', 'rich', 'tqdm']

def restart_script():
    print("\033[93m[●]\033[0m Press Enter and launch ModioDirect...", end=" ")
    input()
    os.system('cls' if os.name == 'nt' else 'clear')
    os.execv(sys.executable, [sys.executable] + sys.argv)

def check_and_install_dependencies():
    missing = []
    
    for package in REQUIRED_PACKAGES:
        try:
            if package == 'requests':
                __import__('requests')
            elif package == 'rich':
                __import__('rich')
            elif package == 'tqdm':
                __import__('tqdm')
        except ImportError:
            missing.append(package)
    
    if not missing:
        return True
    
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\033[96m" + r" __  __           _ _       _____  _               _   ")
    print("\033[96m" + r"|  \/  | ___   __| (_) ___ |  __ \(_)_ __ ___  ___| |_ ")
    print("\033[96m" + r"| |\/| |/ _ \ / _` | |/ _ \| |  | | | '__/ _ \/ __| __|")
    print("\033[96m" + r"| |  | | (_) | (_| | | (_) | |__| | | | |  __/ (__| |_ ")
    print("\033[96m" + r"|_|  |_|\___/ \__,_|_|\___/|_____/|_|_|  \___|\___|\__|")
    print("\033[96m" + " " * 15 + "ModioDirect Downloader Tool" + " " * 16)
    print("\033[96m" + " " * 18 + "by TheRootExec v1.0.2" + " " * 19)
    print("\033[93m" + "=" * 57)
    print("\033[93m[!]\033[0m ModioDirect requires the following packages:")
    for pkg in missing:
        print(" \033[93m•\033[0m " + pkg)
    print("\033[93m[!]\033[0m Install missing dependencies? \033[92m[y]\033[0m or \033[91m[n]\033[0m :", end=" ")
    choice = input().strip().lower()
    if choice != 'y':
        print("\033[91m[!] Setup cancelled. Exiting...\033[0m")
        time.sleep(2)
        return False
    print("\033[93m[●]\033[0m Installing dependencies...")
    
    success = True
    for pkg in missing:
        print("   \033[93m[✔]\033[0m " + pkg + "...", end=" ", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", pkg],
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0:
                print("\033[92mOK\033[0m")
            else:
                print("\033[91mFAILED\033[0m")
                success = False
            time.sleep(0.2)
        except Exception:
            print("\033[91mFAILED\033[0m")
            success = False
    
    if not success:
        print("\033[91m[!] Some packages failed to install.\033[0m")
        print("    Please install manually: pip install " + ' '.join(missing))
        input("    Press Enter to exit...")
        return False
    
    print("\033[92m[✔] All dependencies installed!\033[0m")
    print("\033[93m[●]\033[0m Installation complete!")
    
    restart_script()
    return True

if not check_and_install_dependencies():
    sys.exit(1)

import json
import os
import re
import sys
import time
import subprocess
import argparse
import shutil
import zipfile
import tempfile
import traceback
import threading
import hashlib
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone

# Optional dependency 

try:
    from tqdm import tqdm          # type: ignore
except Exception:
    tqdm = None

try:
    import requests                # type: ignore
except Exception:
    requests = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    from rich.table import Table
    import rich.box
    from rich.progress import (
        Progress,
        BarColumn,
        DownloadColumn,
        TransferSpeedColumn,
        TimeRemainingColumn,
        TaskProgressColumn,
        TextColumn,
    )
    _RICH_OK = True
except Exception:
    Console = Panel = Text = Align = Table = Progress = None
    BarColumn = DownloadColumn = TransferSpeedColumn = None
    TimeRemainingColumn = TaskProgressColumn = TextColumn = None
    rich = None
    _RICH_OK = False

# Constants

API_BASE    = "https://api.mod.io/v1"
VERSION     = "1.0.2"
CONFIG_NAME = "config.json"
USER_AGENT  = f"ModioDirect/{VERSION} (TheRootExec)"
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR      = os.path.join(BASE_DIR, "downloads")
BACKUP_DIR        = os.path.join(BASE_DIR, "backups")
CACHE_PATH        = os.path.join(DOWNLOAD_DIR, "mod_cache.json")
PROFILES_PATH     = os.path.join(BASE_DIR, "profiles.json")
LOCKED_PATH       = os.path.join(BASE_DIR, "locked_mods.json")
LOCAL_LIBRARY_PATH = os.path.join(BASE_DIR, "local_library.json")

DEBUG = False

GAMES_DB_PATHS = [
    os.path.join(BASE_DIR, "games.json"),
    os.path.join(DOWNLOAD_DIR, "games.json"),
    os.path.join(os.path.expanduser("~"), "Downloads", "games.json"),
]

URL_REGEX = re.compile(
    r"^https?://(?:www\.)?mod\.io/g/([^/]+)/m/([^/?#]+)",
    re.IGNORECASE,
)

PC_KEYWORDS      = ["windows", "pc", "win64", "win32", "x64", "x86", "desktop"]
CONSOLE_KEYWORDS = ["xbox", "ps4", "ps5", "playstation", "switch", "console", "nintendo"]

console = Console() if Console is not None else None


# datetime ('-')

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _from_timestamp(ts) -> datetime:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except Exception:
        return _utcnow()


def get_timestamp() -> str:
    return _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date(ts) -> str:
    try:
        return _from_timestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "—"


def format_datetime(ts) -> str:
    try:
        return _from_timestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


def ts_for_filename() -> str:
    return _utcnow().strftime("%Y%m%d_%H%M%S")


# Version label 

def friendly_version(version, filename=None, index=None, is_latest=False) -> str:
    
    if version and str(version).strip() and str(version).strip().lower() != "none":
        return str(version).strip()

    if filename and str(filename).strip():
        stem = os.path.splitext(str(filename).strip())[0]
        # Trim common noise suffixes
        stem = re.sub(r"[-_]+(v\d.*)?$", "", stem, flags=re.IGNORECASE).strip("-_ ")
        if stem:
            label = stem[:40]
            return f"{label} {'(Latest)' if is_latest else '(Older Build)'}"

    if index is not None:
        return f"Build #{index} {'(Latest)' if is_latest else '(Older)'}"

    return "(Latest)" if is_latest else "(Older Build)"


# welp

def print_error(msg):
    if console:
        console.print(f"[bold red][Error][/bold red] {msg}")
    else:
        print(f"[Error] {msg}", file=sys.stderr)


def print_info(msg):
    if console:
        console.print(f"[bold cyan][Info][/bold cyan] {msg}")
    else:
        print(f"[Info] {msg}")


def print_status(msg):
    if console:
        console.print(f"[bold blue][Status][/bold blue] {msg}")
    else:
        print(f"[Status] {msg}")


def print_warning(msg):
    if console:
        console.print(f"[bold yellow][Warning][/bold yellow] {msg}")
    else:
        print(f"[Warning] {msg}")


def print_success(msg):
    if console:
        console.print(f"[bold green][OK][/bold green] {msg}")
    else:
        print(f"[OK] {msg}")


def print_plain(msg):
    if console:
        console.print(msg)
    else:
        print(msg)


def print_section(title: str):
    if console:
        console.rule(f"[bold cyan]{title}[/bold cyan]")
    else:
        width = 56
        pad = max(0, (width - len(title) - 2) // 2)
        print(f"{'─' * width}")
        print(f"{'─' * pad} {title} {'─' * pad}")
        print(f"{'─' * width}")


def print_saved_panel(path):
    print_info(f"Saved as: {path}")


def print_download_complete(_filename, _path):
    return

# Banner
def print_banner():
    if console:
        console.print("[bold cyan] __  __           _ _       _____  _               _   [/bold cyan]")
        console.print("[bold cyan]|  \\/  | ___   __| (_) ___ |  __ \\(_)_ __ ___  ___| |_ [/bold cyan]")
        console.print("[bold cyan]| |\\/| |/ _ \\ / _` | |/ _ \\| |  | | | '__/ _ \\/ __| __|[/bold cyan]")
        console.print("[bold cyan]| |  | | (_) | (_| | | (_) | |__| | | | |  __/ (__| |_ [/bold cyan]")
        console.print("[bold cyan]|_|  |_|\\___/ \\__,_|_|\\___/|_____/|_|_|  \\___|\\___|\\__|[/bold cyan]")
        console.print("[bold white]               ModioDirect Downloader Tool[/bold white]")
        console.print(f"[dim cyan]                 by TheRootExec v{VERSION}[/dim cyan]")
        console.print("[cyan]=======================================================[/cyan]")
    else:
        print(r" __  __           _ _       _____  _               _   ")
        print(r"|  \/  | ___   __| (_) ___ |  __ \(_)_ __ ___  ___| |_ ")
        print(r"| |\/| |/ _ \ / _` | |/ _ \| |  | | | '__/ _ \/ __| __|")
        print(r"| |  | | (_) | (_| | | (_) | |__| | | | |  __/ (__| |_ ")
        print(r"|_|  |_|\___/ \__,_|_|\___/|_____/|_|_|  \___|\___|\__|")
        print("              ModioDirect Downloader Tool")
        print(f"                 by TheRootExec v{VERSION}")
        print("========================================================")

# Utility

def animate_status(base, dots=3, delay=0.15):
    try:
        for i in range(dots):
            sys.stdout.write(f"\r{base}{'.' * (i + 1)}")
            sys.stdout.flush()
            time.sleep(delay)
        sys.stdout.write(f"\r{base}   ")
        sys.stdout.flush()
    except Exception:
        print_plain(base)


def cleanup_temp_file(path):
    try:
        if not path:
            return
        parent = os.path.dirname(path)
        if os.path.isfile(path):
            os.remove(path)
        if os.path.isdir(parent) and os.path.basename(parent).startswith("modiodirect_"):
            shutil.rmtree(parent, ignore_errors=True)
    except Exception:
        pass


def clear_screen():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def friendly_error(err):
    if not isinstance(err, str):
        return "Unexpected error occurred."
    s = err.lower()
    if "401" in s or "403" in s or "unauthorized" in s or "private" in s:
        return "Mod is private, inaccessible, or requires authentication."
    if "404" in s or "not found" in s:
        return "Mod is private, inaccessible, or requires authentication."
    if "429" in s or "rate" in s:
        return "Rate limited. Please try again later."
    if "network" in s or "timeout" in s:
        return "Network error occurred."
    return "Unexpected error occurred."


def normalize_name(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_path_input(value):
    if not isinstance(value, str):
        return ""
    return value.strip().strip('"').strip("'")


def expand_path(value):
    if not isinstance(value, str):
        return ""
    cleaned = value.replace("/", "\\")
    cleaned = cleaned.replace("{USERNAME}", os.environ.get("USERNAME", ""))
    cleaned = cleaned.replace("[Manual]", "").strip()
    cleaned = os.path.expandvars(cleaned)
    cleaned = os.path.expanduser(cleaned)
    return cleaned


def format_bytes(num_bytes) -> str:
    try:
        n = float(num_bytes)
    except (TypeError, ValueError):
        return "Unknown"
    if n < 0:
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def compute_file_hash(path, algorithm="md5") -> str | None:
    try:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 256), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def safe_request(method, url, **kwargs):
    if requests is None:
        print_error("'requests' library not installed.")
        return None
    try:
        return requests.request(method, url, **kwargs)
    except Exception:
        print_error("Network error occurred.")
        return None


def get_expected_size(file_obj):
    if not isinstance(file_obj, dict):
        return None
    size = file_obj.get("filesize")
    if isinstance(size, int):
        return size
    dl = file_obj.get("download")
    if isinstance(dl, dict):
        size = dl.get("filesize")
        if isinstance(size, int):
            return size
    return None

# Auto-install dependencies 

def try_auto_install_rich():
    global Console, Panel, Text, Align, Table, Progress, console, _RICH_OK
    if _RICH_OK:
        return True
    print_error("The 'rich' library is required but not installed.")
    choice = input("Install now? (y/n): ").strip().lower()
    if choice != "y":
        return False
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=False)
    except Exception as exc:
        print_error(f"pip failed: {exc}")
        return False
    try:
        from rich.console import Console as _C
        from rich.panel import Panel as _P
        from rich.text import Text as _T
        from rich.align import Align as _A
        from rich.table import Table as _Tb
        from rich.progress import (
            Progress as _Pr,
            BarColumn as _BC,
            DownloadColumn as _DC,
            TransferSpeedColumn as _TS,
            TimeRemainingColumn as _TR,
            TaskProgressColumn as _TP,
            TextColumn as _TxC,
        )
        Console = _C; Panel = _P; Text = _T; Align = _A; Table = _Tb
        Progress = _Pr
        globals().update({
            "BarColumn": _BC, "DownloadColumn": _DC,
            "TransferSpeedColumn": _TS, "TimeRemainingColumn": _TR,
            "TaskProgressColumn": _TP, "TextColumn": _TxC,
        })
        console = Console()
        _RICH_OK = True
        return True
    except Exception:
        print_error("Rich still unavailable after install attempt.")
        return False


def try_auto_install_requests():
    global requests
    if requests is not None:
        return True
    print_error("The 'requests' library is required but not installed.")
    choice = input("Install now? (y/n): ").strip().lower()
    if choice != "y":
        return False
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=False)
    except Exception as exc:
        print_error(f"pip failed: {exc}")
        return False
    try:
        import requests as _r
        requests = _r
        return True
    except Exception:
        print_error("Requests still unavailable after install attempt.")
        return False


# JSON persistence 

def load_json_file(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, type(default)) else default
    except Exception:
        pass
    return default


def save_json_file(path, data) -> bool:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as exc:
        print_error(f"Failed to save {os.path.basename(path)}: {exc}")
        return False


def load_config(config_path) -> dict:
    return load_json_file(config_path, default={})


def save_config(config_path, data) -> bool:
    return save_json_file(config_path, data)


def load_cache() -> dict:
    try:
        if os.path.isfile(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"mods": {}}


def save_cache(cache) -> bool:
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        return True
    except Exception:
        return False


# API key validation 

def validate_api_key(api_key):
    url    = f"{API_BASE}/games"
    params = {"api_key": api_key, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    if console:
        with console.status("[cyan]Connecting to Mod.io...[/cyan]", spinner="dots"):
            time.sleep(0.4)
    else:
        animate_status("Connecting", dots=3, delay=0.12)
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return False, "Network error."
    if resp.status_code == 401:
        return False, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return False, "Rate limited (429). Try again later."
    if resp.status_code >= 400:
        return False, f"API error ({resp.status_code})."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return False, "Empty or invalid API response."
    return True, "API key validated."


def prompt_api_key(config_path, use_config) -> str:
    config  = {}
    api_key = ""
    if use_config:
        config  = load_config(config_path)
        api_key = str(config.get("api_key", "")).strip()
    while True:
        if not api_key:
            api_key = input("Enter your mod.io API key: ").strip()
        if not api_key:
            print_error("API key cannot be empty.")
            continue
        ok, msg = validate_api_key(api_key)
        if ok:
            print_info(msg)
            if use_config:
                config["api_key"] = api_key
                save_config(config_path, config)
            return api_key
        print_error(msg)
        api_key = ""


# fallback

def match_slug(item, slug) -> bool:
    if not isinstance(item, dict):
        return False
    for key in ("name_id", "slug"):
        val = item.get(key)
        if isinstance(val, str) and val.lower() == slug.lower():
            return True
    return False


def resolve_game_id(api_key, game_slug):
    url     = f"{API_BASE}/games"
    params  = {"api_key": api_key, "name_id": game_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp    = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while resolving game."
    if resp.status_code == 401:
        return None, "Invalid API key (401)."
    if resp.status_code == 429:
        return None, "Rate limited (429)."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Invalid API response."
    items = data.get("data")
    if not isinstance(items, list) or not items:
        return fallback_search_game_id(api_key, game_slug)
    game = items[0]
    if not isinstance(game, dict):
        return None, "Unexpected game data format."
    game_id = game.get("id")
    if not isinstance(game_id, int):
        return None, "Missing game_id."
    return game_id, None


def fallback_search_game_id(api_key, game_slug):
    url    = f"{API_BASE}/games"
    params = {"api_key": api_key, "_q": game_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp   = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while searching game."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    items = data.get("data") if isinstance(data, dict) else []
    if not isinstance(items, list) or not items:
        return None, "Game not found."
    for item in items:
        if match_slug(item, game_slug):
            gid = item.get("id") if isinstance(item, dict) else None
            if isinstance(gid, int):
                return gid, None
    return None, "Game not found."


def resolve_mod_id(api_key, game_id, mod_slug):
    url    = f"{API_BASE}/games/{game_id}/mods"
    params = {"api_key": api_key, "name_id": mod_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp   = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code == 401:
        return None, "Invalid API key (401)."
    if resp.status_code == 429:
        return None, "Rate limited (429)."
    if resp.status_code == 404:
        fid, ferr = resolve_mod_id_global(api_key, game_id, mod_slug)
        return (fid, None) if fid else (None, ferr or "Mod not found (404).")
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    items = data.get("data") if isinstance(data, dict) else []
    if not isinstance(items, list) or not items:
        fid, ferr = fallback_search_mod_id(api_key, game_id, mod_slug)
        return (fid, None) if fid else (None, ferr or "Mod not found.")
    mod = items[0]
    if not isinstance(mod, dict):
        return None, "Unexpected mod data format."
    mid = mod.get("id")
    if not isinstance(mid, int):
        return None, "Missing mod_id."
    return mid, None


def resolve_mod_id_global(api_key, game_id, mod_slug):
    url    = f"{API_BASE}/mods"
    params = {"api_key": api_key, "game_id": game_id, "name_id": mod_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp   = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code == 404:
        fid, ferr = resolve_mod_id_global_search(api_key, game_id, mod_slug)
        if fid:
            return fid, None
        nid, nerr = resolve_mod_id_numeric(api_key, game_id, mod_slug)
        return (nid, None) if nid else (None, ferr or nerr or "Mod not found.")
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    items = data.get("data") if isinstance(data, dict) else []
    if not isinstance(items, list) or not items:
        return None, "Mod not found."
    mod = items[0]
    mid = mod.get("id") if isinstance(mod, dict) else None
    return (mid, None) if isinstance(mid, int) else (None, "Missing mod_id.")


def resolve_mod_id_global_search(api_key, game_id, mod_slug):
    url    = f"{API_BASE}/mods"
    params = {"api_key": api_key, "_q": mod_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp   = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    items = data.get("data") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return None, "No results."
    for item in items:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("game_id"), int) and item["game_id"] != game_id:
            continue
        if match_slug(item, mod_slug):
            mid = item.get("id")
            if isinstance(mid, int):
                return mid, None
    return None, "Mod not found."


def resolve_mod_id_numeric(api_key, game_id, mod_slug):
    if not isinstance(mod_slug, str) or not mod_slug.isdigit():
        return None, None
    mod_id  = int(mod_slug)
    url     = f"{API_BASE}/games/{game_id}/mods/{mod_id}"
    params  = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp    = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data = safe_json(resp)
    mid  = data.get("id") if isinstance(data, dict) else None
    return (mid, None) if isinstance(mid, int) else (None, "Missing mod_id.")


def fallback_search_mod_id(api_key, game_id, mod_slug):
    url    = f"{API_BASE}/games/{game_id}/mods"
    params = {"api_key": api_key, "_q": mod_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp   = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    items = data.get("data") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return None, "No results."
    for item in items:
        if match_slug(item, mod_slug):
            mid = item.get("id") if isinstance(item, dict) else None
            if isinstance(mid, int):
                return mid, None
    return None, "Mod not found."


def fetch_game_details(api_key, game_id):
    url     = f"{API_BASE}/games/{game_id}"
    params  = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp    = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code == 404:
        return None, "Game not accessible (404)."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data = safe_json(resp)
    return (data, None) if isinstance(data, dict) else (None, "Invalid response.")


def fetch_mod_details(api_key, game_id, mod_id):
    url     = f"{API_BASE}/games/{game_id}/mods/{mod_id}"
    params  = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp    = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data = safe_json(resp)
    return (data, None) if isinstance(data, dict) else (None, "Invalid response.")


def fetch_mod_files(api_key, game_id, mod_id):
    url     = f"{API_BASE}/games/{game_id}/mods/{mod_id}/files"
    params  = {"api_key": api_key, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp    = safe_request("GET", url, params=params, headers=headers, timeout=20)
    if resp is None:
        return None, "Network error."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code})."
    data  = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Invalid response."
    items = data.get("data")
    if not isinstance(items, list) or not items:
        return None, "No mod files found."
    return items, None


# File selection 

def select_latest_file(files):
    if not isinstance(files, list) or not files:
        return None
    latest, latest_date = None, -1
    for f in files:
        if not isinstance(f, dict):
            continue
        d = f.get("date_added")
        if isinstance(d, int) and d > latest_date:
            latest_date = d
            latest = f
    return latest


def score_file_for_platform(file_obj) -> int:
    if not isinstance(file_obj, dict):
        return 0
    combined = " ".join([
        str(file_obj.get("filename", "")),
        str(file_obj.get("version", "")),
        str(file_obj.get("changelog", "")),
    ]).lower()
    score = 0
    for kw in PC_KEYWORDS:
        if kw in combined:
            score += 10
    for kw in CONSOLE_KEYWORDS:
        if kw in combined:
            score -= 20
    return score


def select_best_file_for_platform(files):
    if not isinstance(files, list) or not files:
        return None
    scored = [
        (score_file_for_platform(f), f.get("date_added", 0), f)
        for f in files if isinstance(f, dict)
    ]
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]


def extract_download_info(file_obj):
    if not isinstance(file_obj, dict):
        return None, None
    dl = file_obj.get("download")
    if not isinstance(dl, dict):
        return None, None
    binary_url = dl.get("binary_url")
    if not isinstance(binary_url, str) or not binary_url.strip():
        return None, None
    binary_url = binary_url.replace("\\/", "/")
    filename   = file_obj.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        try:
            parsed   = urlparse(binary_url)
            basename = os.path.basename(parsed.path or "")
            filename = unquote(basename) if basename else "modfile.bin"
        except Exception:
            filename = "modfile.bin"
    return binary_url, filename


# File and Build Selector

def prompt_file_selector(files):
    
    if not isinstance(files, list) or not files:
        print_error("No files available to select.")
        return None

    sorted_files = sorted(
        [f for f in files if isinstance(f, dict)],
        key=lambda x: x.get("date_added", 0),
        reverse=True,
    )

    print_section("Build Selector")

    if console and Table:
        table = Table(
            title="Available Builds",
            box=rich.box.SIMPLE_HEAD,   # type: ignore
            show_lines=True,
        )
        table.add_column("#",        style="bold cyan", width=4)
        table.add_column("Filename", style="white",     min_width=24)
        table.add_column("Version",  style="green",     width=22)
        table.add_column("Size",     style="yellow",    width=10)
        table.add_column("Date",     style="dim",       width=12)
        table.add_column("Platform", style="magenta",   width=12)

        for idx, f in enumerate(sorted_files, start=1):
            fname   = f.get("filename", "unknown")
            ver     = friendly_version(
                f.get("version"), fname, idx, is_latest=(idx == 1)
            )
            size    = format_bytes(get_expected_size(f) or 0)
            date_s  = format_date(f.get("date_added", 0))
            sc      = score_file_for_platform(f)
            if sc >= 10:
                platform = "[green]PC / Windows[/green]"
            elif sc <= -10:
                platform = "[red]Console[/red]"
            else:
                platform = "[yellow]Unknown[/yellow]"
            table.add_row(str(idx), fname, ver, size, date_s, platform)

        console.print(table)
    else:
        print(f"{'#':<4} {'Filename':<36} {'Version':<22} {'Size':<10} {'Date':<12}")
        print("─" * 88)
        for idx, f in enumerate(sorted_files, start=1):
            fname  = f.get("filename", "unknown")[:34]
            ver    = friendly_version(
                f.get("version"), f.get("filename"), idx, is_latest=(idx == 1)
            )[:20]
            size   = format_bytes(get_expected_size(f) or 0)
            date_s = format_date(f.get("date_added", 0))
            print(f"{idx:<4} {fname:<36} {ver:<22} {size:<10} {date_s:<12}")

    auto_best = select_best_file_for_platform(sorted_files)
    auto_idx  = (sorted_files.index(auto_best) + 1
                 if auto_best in sorted_files else 1)
    print_info(f"Auto-recommended: #{auto_idx} (best PC match)")
    print_plain("  [0] Use recommended")

    raw = input("Select build number (0 = recommended, q = cancel): ").strip()
    if raw.lower() in ("q", "quit", "cancel"):
        return None
    if raw in ("0", ""):
        return auto_best
    try:
        num = int(raw)
        if 1 <= num <= len(sorted_files):
            return sorted_files[num - 1]
    except ValueError:
        pass
    print_warning("Invalid selection — using recommended build.")
    return auto_best


# Mod Rollback sys

def prompt_version_rollback(files):
    
    if not isinstance(files, list) or len(files) <= 1:
        print_info("Only one version available — no rollback options.")
        return None

    sorted_files = sorted(
        [f for f in files if isinstance(f, dict)],
        key=lambda x: x.get("date_added", 0),
        reverse=True,
    )

    print_section("Versions History")

    if console and Table:
        table = Table(
            title="Available Versions",
            box=rich.box.SIMPLE_HEAD,  # type: ignore
            show_lines=True,
        )
        table.add_column("#",          style="bold cyan", width=4)
        table.add_column("Filename",   style="white",     min_width=24)
        table.add_column("Version",    style="green",     width=22)
        table.add_column("Size",       style="yellow",    width=10)
        table.add_column("Date Added", style="dim",       width=18)
        table.add_column("Status",     style="magenta",   width=10)

        for idx, f in enumerate(sorted_files, start=1):
            fname  = f.get("filename", "unknown")
            ver    = friendly_version(
                f.get("version"), fname, idx, is_latest=(idx == 1)
            )
            size   = format_bytes(get_expected_size(f) or 0)
            date_s = format_datetime(f.get("date_added", 0))
            status = "[bold green]LATEST[/bold green]" if idx == 1 else "[dim]older[/dim]"
            table.add_row(str(idx), fname, ver, size, date_s, status)

        console.print(table)
    else:
        print(f"{'#':<4} {'Filename':<36} {'Version':<22} {'Date':<20} {'Status'}")
        print("─" * 96)
        for idx, f in enumerate(sorted_files, start=1):
            fname  = f.get("filename", "unknown")[:34]
            ver    = friendly_version(
                f.get("version"), f.get("filename"), idx, is_latest=(idx == 1)
            )[:20]
            date_s = format_datetime(f.get("date_added", 0))
            status = "LATEST" if idx == 1 else "older"
            print(f"{idx:<4} {fname:<36} {ver:<22} {date_s:<20} {status}")

    raw = input("Select version (1 = latest, q = cancel): ").strip()
    if raw.lower() in ("q", "quit", "cancel"):
        return None
    if raw in ("1", ""):
        return sorted_files[0]
    try:
        num = int(raw)
        if 1 <= num <= len(sorted_files):
            selected = sorted_files[num - 1]
            if num > 1:
                ver_label = friendly_version(
                    selected.get("version"), selected.get("filename"), num
                )
                print_warning(
                    f"Selected older version: {ver_label}"
                )
                print_warning(
                    "This may be outdated or incompatible with the current game version."
                )
            return selected
        print_warning("Invalid selection — using latest.")
        return sorted_files[0]
    except ValueError:
        print_warning("Invalid input — using latest.")
        return sorted_files[0]

# Lock System

def load_locked_mods() -> dict:
    return load_json_file(LOCKED_PATH, default={})


def save_locked_mods(locked) -> bool:
    return save_json_file(LOCKED_PATH, locked)


def is_mod_locked(mod_id) -> bool:
    return str(mod_id) in load_locked_mods()


def lock_mod_version(mod_id, mod_name, file_id, version, filename) -> bool:
    locked = load_locked_mods()
    ver_label = friendly_version(version, filename)
    locked[str(mod_id)] = {
        "mod_id":          mod_id,
        "mod_name":        mod_name,
        "locked_file_id":  file_id,
        "locked_version":  ver_label,
        "locked_filename": filename,
        "locked_at":       get_timestamp(),
    }
    if save_locked_mods(locked):
        print_success(f"Locked: {mod_name} @ {ver_label}")
        return True
    return False


def unlock_mod_version(mod_id) -> bool:
    locked  = load_locked_mods()
    key     = str(mod_id)
    if key in locked:
        name = locked[key].get("mod_name", key)
        del locked[key]
        if save_locked_mods(locked):
            print_success(f"Unlocked: {name}")
            return True
    else:
        print_warning("Mod is not currently locked.")
    return False


def check_lock_before_update(mod_id, new_file_id) -> bool:
    locked = load_locked_mods()
    entry  = locked.get(str(mod_id))
    if not entry:
        return False
    if entry.get("locked_file_id") == new_file_id:
        return False          # same version — no block needed
    print_warning(
        f"'{entry.get('mod_name', mod_id)}' is LOCKED at "
        f"version '{entry.get('locked_version', '?')}'. Update blocked."
    )
    print_warning("Unlock this mod in the Lock Manager to allow updates.")
    return True


def show_locked_mods_menu():
    print_section("Lock Manager")
    locked  = load_locked_mods()
    if not locked:
        print_info("No mods are currently locked.")
        return

    entries = list(locked.items())
    if console and Table:
        table = Table(box=rich.box.SIMPLE_HEAD, show_lines=True)  # type: ignore
        table.add_column("#",        style="bold cyan", width=4)
        table.add_column("Mod",      style="white")
        table.add_column("Version",  style="green",  width=22)
        table.add_column("Locked",   style="dim",    width=22)
        for idx, (mid, info) in enumerate(entries, start=1):
            table.add_row(
                str(idx),
                info.get("mod_name", mid),
                info.get("locked_version", "?"),
                info.get("locked_at", "?")[:19],
            )
        console.print(table)
    else:
        for idx, (mid, info) in enumerate(entries, start=1):
            print(
                f"  [{idx}] {info.get('mod_name', mid)} | "
                f"v{info.get('locked_version','?')} | "
                f"Locked: {info.get('locked_at','?')[:19]}"
            )

    print_plain("  [0] Back")
    raw = input("Select number to unlock (0 = back): ").strip()
    if raw == "0" or not raw:
        return
    try:
        num = int(raw)
        if 1 <= num <= len(entries):
            mid, _ = entries[num - 1]
            unlock_mod_version(int(mid))
    except ValueError:
        print_error("Invalid selection.")

# Update Backups

def backup_mod_file(mod_id, mod_name, current_filename) -> str | None:
    src = os.path.join(DOWNLOAD_DIR, current_filename)
    if not os.path.isfile(src):
        return None
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts          = ts_for_filename()
        backup_name = f"{mod_id}_{ts}_{current_filename}"
        dst         = os.path.join(BACKUP_DIR, backup_name)
        shutil.copy2(src, dst)

        manifest_path = os.path.join(BACKUP_DIR, "backup_manifest.json")
        manifest      = load_json_file(manifest_path, default={})
        manifest.setdefault(str(mod_id), [])
        manifest[str(mod_id)].append({
            "backup_file":      backup_name,
            "original_filename": current_filename,
            "mod_name":         mod_name,
            "backed_up_at":     get_timestamp(),
        })
        # Keep rolling window of 5 backups per mod
        while len(manifest[str(mod_id)]) > 5:
            oldest     = manifest[str(mod_id)].pop(0)
            old_path   = os.path.join(BACKUP_DIR, oldest.get("backup_file", ""))
            if os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
        save_json_file(manifest_path, manifest)
        print_success(f"Backup created: {backup_name}")
        return dst
    except Exception as exc:
        print_warning(f"Backup failed (non-critical): {exc}")
        return None


def restore_mod_backup(mod_id, _cache) -> bool:
    manifest_path = os.path.join(BACKUP_DIR, "backup_manifest.json")
    manifest      = load_json_file(manifest_path, default={})
    entries       = manifest.get(str(mod_id), [])
    if not entries:
        print_error("No backups found for this mod.")
        return False
    latest   = entries[-1]
    bk_file  = latest.get("backup_file", "")
    orig_fn  = latest.get("original_filename", "")
    src      = os.path.join(BACKUP_DIR, bk_file)
    if not os.path.isfile(src):
        print_error(f"Backup file missing: {bk_file}")
        return False
    dst = os.path.join(DOWNLOAD_DIR, orig_fn)
    try:
        shutil.copy2(src, dst)
        print_success(f"Restored: {orig_fn} from {bk_file}")
        return True
    except Exception as exc:
        print_error(f"Restore failed: {exc}")
        return False

# Mod Profiles 

def load_profiles() -> dict:
    return load_json_file(PROFILES_PATH, default={"active": None, "profiles": {}})


def save_profiles(data) -> bool:
    return save_json_file(PROFILES_PATH, data)


def get_profile_names() -> list:
    return list(load_profiles().get("profiles", {}).keys())


def get_active_profile() -> str | None:
    return load_profiles().get("active")


def set_active_profile(name) -> bool:
    data = load_profiles()
    if name not in data.get("profiles", {}):
        print_error(f"Profile '{name}' not found.")
        return False
    data["active"] = name
    save_profiles(data)
    print_success(f"Active profile set to: {name}")
    return True


def create_profile(name, description="") -> bool:
    if not name or not isinstance(name, str):
        print_error("Profile name cannot be empty.")
        return False
    data     = load_profiles()
    profiles = data.setdefault("profiles", {})
    if name in profiles:
        print_warning(f"Profile '{name}' already exists.")
        return False
    profiles[name] = {
        "name":        name,
        "description": description,
        "created_at":  get_timestamp(),
        "updated_at":  get_timestamp(),
        "mods":        [],
    }
    if data.get("active") is None:
        data["active"] = name
    if save_profiles(data):
        print_success(f"Profile '{name}' created.")
        return True
    return False


def add_mod_to_profile(profile_name, mod_id, mod_name, game_slug,
                        mod_slug, file_id=None, version=None,
                        install_path=None) -> bool:
    data     = load_profiles()
    profiles = data.get("profiles", {})
    if profile_name not in profiles:
        print_error(f"Profile '{profile_name}' not found.")
        return False
    mods = profiles[profile_name].setdefault("mods", [])
    for entry in mods:
        if entry.get("mod_id") == mod_id:
            entry.update({
                "mod_name":    mod_name,
                "game_slug":   game_slug,
                "mod_slug":    mod_slug,
                "file_id":     file_id,
                "version":     friendly_version(version, mod_name),
                "install_path": install_path,
                "updated_at":  get_timestamp(),
            })
            profiles[profile_name]["updated_at"] = get_timestamp()
            save_profiles(data)
            print_success(f"Updated '{mod_name}' in profile '{profile_name}'.")
            return True
    mods.append({
        "mod_id":      mod_id,
        "mod_name":    mod_name,
        "game_slug":   game_slug,
        "mod_slug":    mod_slug,
        "file_id":     file_id,
        "version":     friendly_version(version, mod_name),
        "install_path": install_path,
        "added_at":    get_timestamp(),
    })
    profiles[profile_name]["updated_at"] = get_timestamp()
    if save_profiles(data):
        print_success(f"Added '{mod_name}' to profile '{profile_name}'.")
        return True
    return False


def delete_profile(name) -> bool:
    data     = load_profiles()
    profiles = data.get("profiles", {})
    if name not in profiles:
        print_error(f"Profile '{name}' not found.")
        return False
    del profiles[name]
    if data.get("active") == name:
        remaining = list(profiles.keys())
        data["active"] = remaining[0] if remaining else None
    if save_profiles(data):
        print_success(f"Profile '{name}' deleted.")
        return True
    return False


def show_profile_contents(name):
    data    = load_profiles()
    profile = data.get("profiles", {}).get(name)
    if not profile:
        print_error(f"Profile '{name}' not found.")
        return
    print_section(f"Profile: {name}")
    if profile.get("description"):
        print_info(f"Description : {profile['description']}")
    print_info(f"Created     : {profile.get('created_at','?')[:19]}")
    print_info(f"Last Updated: {profile.get('updated_at','?')[:19]}")
    mods = profile.get("mods", [])
    if not mods:
        print_warning("No mods in this profile.")
        return
    if console and Table:
        table = Table(
            title=f"Mods in '{name}'",
            box=rich.box.SIMPLE_HEAD, show_lines=True  # type: ignore
        )
        table.add_column("#",          style="bold cyan", width=4)
        table.add_column("Mod Name",   style="white",     min_width=28)
        table.add_column("Version",    style="green",     width=22)
        table.add_column("Game",       style="dim",       width=18)
        table.add_column("Install Path", style="yellow")
        for idx, m in enumerate(mods, start=1):
            table.add_row(
                str(idx),
                m.get("mod_name", "?"),
                str(m.get("version", "?")),
                m.get("game_slug", "?"),
                m.get("install_path", "—") or "—",
            )
        console.print(table)
    else:
        print(f"{'#':<4} {'Mod Name':<30} {'Version':<22} {'Game':<18}")
        print("─" * 80)
        for idx, m in enumerate(mods, start=1):
            print(
                f"{idx:<4} {m.get('mod_name','?'):<30} "
                f"{str(m.get('version','?')):<22} {m.get('game_slug','?'):<18}"
            )


def restore_profile(profile_name, api_key, cache, force=False):
    data    = load_profiles()
    profile = data.get("profiles", {}).get(profile_name)
    if not profile:
        print_error(f"Profile '{profile_name}' not found.")
        return
    mods = profile.get("mods", [])
    if not mods:
        print_warning("Profile is empty — nothing to restore.")
        return

    print_section(f"Restoring Profile: {profile_name}")
    print_info(f"Restoring {len(mods)} mod(s)...")
    succeeded, failed = 0, 0

    for mod_entry in mods:
        game_slug    = mod_entry.get("game_slug")
        mod_slug     = mod_entry.get("mod_slug")
        install_path = mod_entry.get("install_path")
        mod_name     = mod_entry.get("mod_name", "?")

        if not game_slug or not mod_slug:
            print_warning(f"Skipping incomplete entry: {mod_name}")
            failed += 1
            continue

        print_info(f"  → {mod_name}")
        ok, downloaded_path, _, _, _, _sk, _isk = process_single_mod(
            api_key, game_slug, mod_slug,
            install_requested=False,
            force_requested=force,
            cache=cache,
        )
        if ok and install_path and os.path.isdir(install_path) and downloaded_path:
            install_mod(downloaded_path, install_path, force=force)
        if ok:
            succeeded += 1
        else:
            print_warning(f"  Failed: {mod_name}")
            failed += 1

    print_section("Restore Complete")
    print_success(f"{succeeded}/{len(mods)} mods restored successfully.")
    if failed:
        print_warning(f"{failed} mod(s) failed — check warnings above.")


def profiles_menu(api_key, cache):
    while True:
        active   = get_active_profile() or "None"
        names    = get_profile_names()

        if console:
            console.rule("[bold cyan]PROFILE MANAGER[/bold cyan]")
            console.print(
                f"[bold]Active Profile:[/bold] [bold green][ {active} ][/bold green]"
            )
            console.rule()
        else:
            print_section("PROFILE MANAGER")
            print(f"  Active Profile: [ {active} ]")
            print("─" * 56)

        if names:
            print_plain("  Saved Profiles:")
            for n in names:
                marker = " ◀ active" if n == active else ""
                print_plain(f"    • {n}{marker}")
        else:
            print_info("  No profiles saved yet.")

        print_plain("  Actions:")
        print_plain("  [1] Load Profile  (switch active)")
        print_plain("  [2] Create New Profile")
        print_plain("  [3] Restore Active Profile  (one-click reinstall)")
        print_plain("  [4] View Profile Contents")
        print_plain("  [5] Delete Profile")
        print_plain("  [0] Back to Main Menu")

        choice = input("  Choice: ").strip().lower()

        if choice == "0":
            return

        elif choice == "1":
            if not names:
                print_error("No profiles available.")
                continue
            name = input("  Profile name to load: ").strip()
            if name in names:
                set_active_profile(name)
            else:
                print_error(f"Profile '{name}' not found.")

        elif choice == "2":
            name = input("  Profile name (e.g. Vanilla+, Multiplayer): ").strip()
            if not name:
                print_error("Name cannot be empty.")
                continue
            desc = input("  Description (optional): ").strip()
            create_profile(name, desc)

        elif choice == "3":
            if active == "None" or not active:
                print_error("No active profile. Load one first.")
                continue
            force = (
                input("  Force reinstall even if up-to-date? (y/n): ")
                .strip().lower() == "y"
            )
            restore_profile(active, api_key, cache, force=force)

        elif choice == "4":
            name = input("  Profile name to view: ").strip()
            show_profile_contents(name)
            input("  Press Enter to continue...")

        elif choice == "5":
            name    = input("  Profile name to delete: ").strip()
            confirm = input(f"  Delete '{name}'? This cannot be undone. (y/n): ").strip().lower()
            if confirm == "y":
                delete_profile(name)

        else:
            print_error("Invalid option.")


# Update Checker

def check_for_updates(api_key, cache):
    print_section("Mod Update")
    mods = cache.get("mods", {})
    if not mods:
        print_info("No mods tracked. Download some mods first.")
        return []

    locked           = load_locked_mods()
    updates_available = []
    checked          = 0

    print_info(f"Scanning {len(mods)} mod(s) for updates...")

    for mod_id_str, entry in mods.items():
        try:
            mod_id          = int(mod_id_str)
            mod_name        = entry.get("mod_name", mod_id_str)
            current_file_id = entry.get("latest_version_id")
            current_version = friendly_version(
                entry.get("latest_version_number"),
                entry.get("file_name"),
                index=None,
                is_latest=True,
            )
            game_id = entry.get("game_id")
            if not game_id:
                print_warning(f"  Skipping '{mod_name}' — no game_id in cache.")
                continue

            files, err = fetch_mod_files(api_key, game_id, mod_id)
            if err:
                print_warning(f"  Could not scan '{mod_name}': {err}")
                continue

            latest = select_latest_file(files)
            if not latest:
                continue

            latest_file_id  = latest.get("id")
            latest_version  = friendly_version(
                latest.get("version"), latest.get("filename"),
                index=1, is_latest=True
            )
            checked += 1

            if latest_file_id != current_file_id:
                updates_available.append({
                    "mod_id":          mod_id,
                    "mod_name":        mod_name,
                    "current_version": current_version,
                    "new_version":     latest_version,
                    "new_file_id":     latest_file_id,
                    "locked":          str(mod_id) in locked,
                })
        except Exception as exc:
            print_warning(f"  Scan error for '{mod_id_str}': {exc}")
            continue

    if not updates_available:
        print_success(f"All {checked} mod(s) are up to date.")
        return []

    print_section(f"{len(updates_available)} Update(s) Available")
    if console and Table:
        table = Table(box=rich.box.SIMPLE_HEAD, show_lines=True)  # type: ignore
        table.add_column("Mod",          style="white",       min_width=24)
        table.add_column("Installed",    style="dim",         width=22)
        table.add_column("Available",    style="bold green",  width=22)
        table.add_column("Status",       style="yellow",      width=10)
        for u in updates_available:
            status = "[red]LOCKED[/red]" if u.get("locked") else "Ready"
            table.add_row(
                u["mod_name"],
                u["current_version"],
                u["new_version"],
                status,
            )
        console.print(table)
    else:
        for u in updates_available:
            lock_tag = " [LOCKED]" if u.get("locked") else ""
            print(
                f"  {u['mod_name']}: {u['current_version']} → "
                f"{u['new_version']}{lock_tag}"
            )

    print_info(
        "Use the main download prompt to update specific mods. "
        "No automatic updates are applied."
    )
    return updates_available

# Compatibility Checker

def run_compatibility_check(cache):
    print_section("Compatibility Report")
    mods = cache.get("mods", {})
    if not mods:
        print_info("No mods in cache to check.")
        return

    issues_found = 0

    for mod_id_str, entry in mods.items():
        try:
            mod_name        = entry.get("mod_name", mod_id_str)
            filename        = entry.get("file_name", "")
            expected_size   = entry.get("file_size")
            latest_file_id  = entry.get("latest_version_id")
            installed_file_id = entry.get("installed_version_id")
            installed_path  = entry.get("installed_path", "")

            if filename:
                fp = os.path.join(DOWNLOAD_DIR, filename)
                if not os.path.isfile(fp):
                    print_warning(f"[{mod_name}] Download missing: {filename}")
                    issues_found += 1
                elif expected_size and os.path.getsize(fp) != expected_size:
                    actual = os.path.getsize(fp)
                    print_warning(
                        f"[{mod_name}] File size mismatch — "
                        f"expected {format_bytes(expected_size)}, "
                        f"got {format_bytes(actual)}. Possible corruption."
                    )
                    issues_found += 1

            if (latest_file_id and installed_file_id
                    and latest_file_id != installed_file_id):
                print_warning(
                    f"[{mod_name}] Installed version differs from "
                    f"downloaded version. Consider reinstalling."
                )
                issues_found += 1

            if installed_path and not os.path.isdir(installed_path):
                print_warning(
                    f"[{mod_name}] Install path no longer exists: {installed_path}"
                )
                issues_found += 1

        except Exception as exc:
            print_warning(f"Compatibility check error for '{mod_id_str}': {exc}")
            continue

    if issues_found == 0:
        print_success("No compatibility issues detected.")
    else:
        print_warning(f"{issues_found} issue(s) found — review warnings above.")

# Broken Mod Detection

def detect_broken_mods(cache, api_key=None) -> list:
    print_section("Integrity Scanner")
    mods = cache.get("mods", {})
    if not mods:
        print_info("No mods in cache to scan.")
        return []

    broken = []

    for mod_id_str, entry in mods.items():
        try:
            mod_name      = entry.get("mod_name", mod_id_str)
            filename      = entry.get("file_name", "")
            expected_size = entry.get("file_size")
            issues        = []

            if not filename:
                issues.append("No filename recorded in cache.")
            else:
                fp = os.path.join(DOWNLOAD_DIR, filename)
                if not os.path.isfile(fp):
                    issues.append(f"File missing: {filename}")
                else:
                    actual_size = os.path.getsize(fp)
                    if actual_size == 0:
                        issues.append("File is empty (0 bytes) — download likely failed.")
                    elif expected_size and actual_size != expected_size:
                        issues.append(
                            f"Size mismatch: expected {format_bytes(expected_size)}, "
                            f"got {format_bytes(actual_size)}"
                        )
                    if filename.lower().endswith(".zip"):
                        try:
                            with zipfile.ZipFile(fp, "r") as zf:
                                bad = zf.testzip()
                            if bad:
                                issues.append(
                                    f"ZIP corruption in member: {bad}"
                                )
                        except zipfile.BadZipFile:
                            issues.append("Not a valid ZIP archive.")
                        except Exception:
                            issues.append("Could not verify ZIP integrity.")

            if issues:
                broken.append({
                    "mod_id":   mod_id_str,
                    "mod_name": mod_name,
                    "issues":   issues,
                    "entry":    entry,
                })
        except Exception as exc:
            print_warning(f"Scan error for '{mod_id_str}': {exc}")

    if not broken:
        print_success("All downloaded mods passed integrity checks.")
        return []

    print_warning(f"{len(broken)} broken mod(s) detected:")
    for b in broken:
        if console:
            console.print(f"  [bold red]✗[/bold red] {b['mod_name']}")
        else:
            print(f"  ✗ {b['mod_name']}")
        for issue in b.get("issues", []):
            print_warning(f"      → {issue}")

    if api_key:
        choice = input(
            "  Attempt to re-download broken mods? (y/n): "
        ).strip().lower()
        if choice == "y":
            for b in broken:
                entry     = b["entry"]
                game_slug = entry.get("game_slug")
                mod_slug  = entry.get("mod_slug")
                if not game_slug or not mod_slug:
                    print_warning(
                        f"  Cannot re-download '{b['mod_name']}' — "
                        f"missing slug data in cache."
                    )
                    continue
                print_info(f"  Re-downloading: {b['mod_name']}")
                ok, _, _, _, _, _, _ = process_single_mod(
                    api_key, game_slug, mod_slug,
                    install_requested=False,
                    force_requested=True,
                    cache=cache,
                )
                if ok:
                    print_success(f"  Repaired: {b['mod_name']}")
                else:
                    print_warning(f"  Repair failed: {b['mod_name']}")

    return broken


# offline local moods list 

def _scan_downloads_dir() -> list[dict]:
    results = []
    if not os.path.isdir(DOWNLOAD_DIR):
        return results

    skip_names = {
        "mod_cache.json", "modinfo.json",
        "local_library.json", "games.json",
    }

    for fname in sorted(os.listdir(DOWNLOAD_DIR)):
        if fname in skip_names:
            continue
        if fname.startswith("."):
            continue
        fpath = os.path.join(DOWNLOAD_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            size  = os.path.getsize(fpath)
            mtime = os.path.getmtime(fpath)
            date  = format_date(mtime)
        except Exception:
            size, date = 0, "—"
        results.append({
            "filename":   fname,
            "local_path": fpath,
            "file_size":  size,
            "date":       date,
            "source":     "downloads",
        })
    return results


def _scan_backup_dir() -> list[dict]:
    results = []
    if not os.path.isdir(BACKUP_DIR):
        return results
    manifest_path = os.path.join(BACKUP_DIR, "backup_manifest.json")
    manifest      = load_json_file(manifest_path, default={})

    bk_meta = {}
    for _mid, entries in manifest.items():
        for e in entries:
            bk_meta[e.get("backup_file", "")] = e.get("mod_name", "?")

    for fname in sorted(os.listdir(BACKUP_DIR)):
        if fname in ("backup_manifest.json",) or fname.startswith("."):
            continue
        fpath = os.path.join(BACKUP_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            size  = os.path.getsize(fpath)
            mtime = os.path.getmtime(fpath)
            date  = format_date(mtime)
        except Exception:
            size, date = 0, "—"
        results.append({
            "filename":   fname,
            "local_path": fpath,
            "file_size":  size,
            "date":       date,
            "mod_name":   bk_meta.get(fname, "?"),
            "source":     "backup",
        })
    return results


def index_downloaded_mods(cache) -> dict:
    lib      = load_json_file(LOCAL_LIBRARY_PATH, default={"mods": {}, "backups": []})
    lib_mods = {}

    fn_to_cache = {}
    for _mid, entry in cache.get("mods", {}).items():
        fn = entry.get("file_name", "")
        if fn:
            fn_to_cache[fn] = entry

    for finfo in _scan_downloads_dir():
        fname = finfo["filename"]
        ce    = fn_to_cache.get(fname, {})
        key   = fname  
        lib_mods[key] = {
            "filename":    fname,
            "mod_name":    ce.get("mod_name") or fname,
            "mod_id":      ce.get("mod_id", ""),
            "version":     friendly_version(
                               ce.get("latest_version_number"),
                               fname,
                           ),
            "file_size":   finfo["file_size"],
            "date":        ce.get("download_date", finfo["date"]),
            "local_path":  finfo["local_path"],
            "in_cache":    bool(ce),
        }

    lib["mods"]         = lib_mods
    lib["backups"]      = _scan_backup_dir()
    lib["last_indexed"] = get_timestamp()
    save_json_file(LOCAL_LIBRARY_PATH, lib)
    return lib


def show_local_library(cache):
    print_section("Local Mod Library")
    lib      = index_downloaded_mods(cache)
    lib_mods = lib.get("mods", {})
    backups  = lib.get("backups", [])

    if not lib_mods:
        print_info("No locally downloaded mods found.")
    else:
        entries    = list(lib_mods.values())
        total_size = sum(e.get("file_size", 0) or 0 for e in entries)

        if console and Table:
            table = Table(
                title=f"Downloaded Mods ({len(entries)} file(s))",
                box=rich.box.SIMPLE_HEAD, show_lines=True,  # type: ignore
            )
            table.add_column("#",         style="bold cyan", width=4)
            table.add_column("Filename",  style="white",     min_width=28)
            table.add_column("Mod Name",  style="cyan",      width=24)
            table.add_column("Version",   style="green",     width=18)
            table.add_column("Size",      style="yellow",    width=10)
            table.add_column("Date",      style="dim",       width=12)
            table.add_column("Cached",    style="dim",       width=7)
            for idx, e in enumerate(entries, start=1):
                cached = "[green]Yes[/green]" if e.get("in_cache") else "[dim]No[/dim]"
                table.add_row(
                    str(idx),
                    e.get("filename", "?"),
                    e.get("mod_name", "?"),
                    e.get("version", "?"),
                    format_bytes(e.get("file_size", 0)),
                    str(e.get("date", "?"))[:12],
                    cached,
                )
            console.print(table)
        else:
            print(f"{'#':<4} {'Filename':<32} {'Mod Name':<24} {'Size':<10} {'Date'}")
            print("─" * 84)
            for idx, e in enumerate(entries, start=1):
                print(
                    f"{idx:<4} {e.get('filename','?'):<32} "
                    f"{e.get('mod_name','?'):<24} "
                    f"{format_bytes(e.get('file_size',0)):<10} "
                    f"{str(e.get('date','?'))[:12]}"
                )

        print_info(f"Total download storage: {format_bytes(total_size)}")

    if backups:
        bk_total = sum(b.get("file_size", 0) or 0 for b in backups)
        print_info(f"Backup files: {len(backups)} ({format_bytes(bk_total)})")


# Storage Analyzer...

def analyze_storage(cache):
    print_section("Storage Analyzer")
    lib     = index_downloaded_mods(cache)
    entries = list(lib.get("mods", {}).values())
    backups = lib.get("backups", [])

    if not entries and not backups:
        print_info("No local mod files found.")
        return

    # Sort by size descending
    entries.sort(key=lambda x: x.get("file_size", 0), reverse=True)
    total_dl    = sum(e.get("file_size", 0) or 0 for e in entries)
    total_bk    = sum(b.get("file_size", 0) or 0 for b in backups)
    grand_total = total_dl + total_bk

    if console and Table:
        table = Table(
            title="Mod Storage (Downloads)",
            box=rich.box.SIMPLE_HEAD, show_lines=True,  # type: ignore
        )
        table.add_column("#",          style="bold cyan", width=4)
        table.add_column("Filename",   style="white",     min_width=28)
        table.add_column("Mod Name",   style="cyan",      width=22)
        table.add_column("Size",       style="yellow",    width=12)
        table.add_column("% of Total", style="green",     width=12)
        for idx, e in enumerate(entries, start=1):
            sz  = e.get("file_size", 0) or 0
            pct = (sz / total_dl * 100) if total_dl > 0 else 0
            table.add_row(
                str(idx),
                e.get("filename", "?"),
                e.get("mod_name", "?"),
                format_bytes(sz),
                f"{pct:.1f}%",
            )
        console.print(table)
    else:
        print(f"{'#':<4} {'Filename':<34} {'Size':<12} {'%'}")
        print("─" * 58)
        for idx, e in enumerate(entries, start=1):
            sz  = e.get("file_size", 0) or 0
            pct = (sz / total_dl * 100) if total_dl > 0 else 0
            print(
                f"{idx:<4} {e.get('filename','?'):<34} "
                f"{format_bytes(sz):<12} {pct:.1f}%"
            )

    print_info(f"Downloads total : {format_bytes(total_dl)}")
    print_info(f"Backups total   : {format_bytes(total_bk)}")
    print_info(f"Grand total     : {format_bytes(grand_total)}")

    if backups:
        print_section("Backup Files")
        backups_sorted = sorted(
            backups, key=lambda x: x.get("file_size", 0), reverse=True
        )
        if console and Table:
            btable = Table(box=rich.box.SIMPLE_HEAD, show_lines=True)  # type: ignore
            btable.add_column("Filename", style="dim", min_width=32)
            btable.add_column("Mod",      style="white", width=22)
            btable.add_column("Size",     style="yellow", width=12)
            btable.add_column("Date",     style="dim", width=12)
            for b in backups_sorted:
                btable.add_row(
                    b.get("filename", "?"),
                    b.get("mod_name", "?"),
                    format_bytes(b.get("file_size", 0)),
                    b.get("date", "?"),
                )
            console.print(btable)
        else:
            for b in backups_sorted:
                print(
                    f"  {b.get('filename','?'):<40} "
                    f"{format_bytes(b.get('file_size',0)):<12} "
                    f"{b.get('date','?')}"
                )


# Dependency Detection

_DEP_PATTERNS = [
    (r"requires?\s+(bepinex)",                 "BepInEx"),
    (r"requires?\s+(melonloader)",             "MelonLoader"),
    (r"requires?\s+(unity\s*mod\s*manager|umm)", "Unity Mod Manager"),
    (r"requires?\s+(harmony)",                 "Harmony"),
    (r"requires?\s+(optifine)",                "OptiFine"),
    (r"requires?\s+(forge)",                   "Minecraft Forge"),
    (r"requires?\s+(fabric)",                  "Fabric Loader"),
]


def check_mod_dependencies(mod_details, cache):
    if not isinstance(mod_details, dict):
        return
    combined = " ".join([
        str(mod_details.get("description_plaintext", "")),
        str(mod_details.get("summary", "")),
        " ".join(
            t.get("name", "") for t in mod_details.get("tags", [])
            if isinstance(t, dict)
        ),
    ]).lower()

    cached_names = [
        str(v.get("mod_name", "")).lower()
        for v in cache.get("mods", {}).values()
    ]

    for pattern, dep_name in _DEP_PATTERNS:
        if re.search(pattern, combined):
            if not any(dep_name.lower() in n for n in cached_names):
                print_warning(
                    f"This mod may require: [bold]{dep_name}[/bold]"
                    if console else f"This mod may require: {dep_name}"
                )


# Download Queue Manager not impimeted yet

class DownloadQueueManager:

    def __init__(self):
        self._lock       = threading.Lock()
        self._items      = []
        self._pause_evt  = threading.Event()
        self._pause_evt.set()   
        self._cancelled  = set()

    # API 

    def enqueue(self, api_key, game_slug, mod_slug,
                install_path=None, force=False) -> str:
        item_id = f"{int(time.time()*1000)}_{id(object())}"
        item = {
            "id":           item_id,
            "api_key":      api_key,
            "game_slug":    game_slug,
            "mod_slug":     mod_slug,
            "install_path": install_path,
            "force":        force,
            "status":       "queued",
            "added_at":     get_timestamp(),
        }
        with self._lock:
            self._items.append(item)
        print_info(f"Queued: {game_slug}/{mod_slug}")
        return item_id

    def cancel(self, item_id):
        with self._lock:
            self._cancelled.add(item_id)
            for item in self._items:
                if item["id"] == item_id and item["status"] == "queued":
                    item["status"] = "cancelled"
        print_info(f"Cancelled: {item_id[-8:]}")

    def pause_queue(self):
        self._pause_evt.clear()
        print_info("Queue paused — current download will finish first.")

    def resume_queue(self):
        self._pause_evt.set()
        print_info("Queue resumed.")

    def move_up(self, item_id) -> bool:
        with self._lock:
            queued = [i for i in self._items if i["status"] == "queued"]
            for idx, item in enumerate(queued):
                if item["id"] == item_id and idx > 0:
                    queued[idx], queued[idx - 1] = queued[idx - 1], queued[idx]
                    non_q = [i for i in self._items if i["status"] != "queued"]
                    self._items = non_q + queued
                    print_info(f"Moved up: ...{item_id[-8:]}")
                    return True
        print_warning("Item not found or already at top.")
        return False

    def get_status(self) -> list:
        with self._lock:
            return [
                {k: v for k, v in i.items() if k != "api_key"}
                for i in self._items
            ]

    def process_all(self, cache):
        with self._lock:
            to_process = [i for i in self._items if i["status"] == "queued"]

        for item in to_process:
            self._pause_evt.wait()

            with self._lock:
                if item["id"] in self._cancelled:
                    item["status"] = "cancelled"
                    continue
                item["status"] = "downloading"

            print_info(
                f"  Processing: {item['game_slug']}/{item['mod_slug']}"
            )
            try:
                ok, dl_path, gname, gid, mod_id, _sk, _isk = process_single_mod(
                    item["api_key"],
                    item["game_slug"],
                    item["mod_slug"],
                    install_requested=bool(item.get("install_path")),
                    force_requested=item.get("force", False),
                    cache=cache,
                )
                if ok and item.get("install_path") and dl_path:
                    ip = item["install_path"]
                    if os.path.isdir(ip):
                        install_mod(dl_path, ip, force=item.get("force", False))

                with self._lock:
                    item["status"] = "done" if ok else "failed"

            except Exception as exc:
                print_warning(f"  Queue error: {exc}")
                with self._lock:
                    item["status"] = "failed"

        print_info("Queue processing complete.")


queue_manager = DownloadQueueManager()


def queue_menu(api_key, cache):
    while True:
        print_section("Download Queue")
        status = queue_manager.get_status()

        if not status:
            print_info("Queue is empty.")
        else:
            if console and Table:
                table = Table(box=rich.box.SIMPLE_HEAD, show_lines=True)  # type: ignore
                table.add_column("ID",     style="dim",    width=10)
                table.add_column("Mod",    style="white",  min_width=28)
                table.add_column("Status", style="yellow", width=14)
                for item in status:
                    short = str(item["id"])[-8:]
                    label = (
                        f"{item.get('game_slug','?')}/"
                        f"{item.get('mod_slug','?')}"
                    )
                    table.add_row(short, label, item.get("status", "?"))
                console.print(table)
            else:
                for item in status:
                    short = str(item["id"])[-8:]
                    label = (
                        f"{item.get('game_slug','?')}/"
                        f"{item.get('mod_slug','?')}"
                    )
                    print(f"  [{short}] {label} — {item.get('status','?')}")

        print_plain("  [a] Add mod to queue")
        print_plain("  [s] Start processing")
        print_plain("  [p] Pause   [r] Resume")
        print_plain("  [c] Cancel item   [u] Move item up")
        print_plain("  [0] Back")

        choice = input("  Choice: ").strip().lower()

        if choice == "0":
            return
        elif choice == "a":
            url = input("  Mod URL: ").strip()
            gs, ms = parse_modio_url(url)
            if gs and ms:
                ip_raw = input(
                    "  Install path (blank = download only): "
                ).strip()
                ip = ip_raw if os.path.isdir(ip_raw) else None
                queue_manager.enqueue(api_key, gs, ms, install_path=ip)
            else:
                print_error("Invalid URL.")
        elif choice == "s":
            queue_manager.process_all(cache)
        elif choice == "p":
            queue_manager.pause_queue()
        elif choice == "r":
            queue_manager.resume_queue()
        elif choice == "c":
            suf = input("  Last 8 chars of ID to cancel: ").strip()
            for item in queue_manager.get_status():
                if str(item["id"]).endswith(suf):
                    queue_manager.cancel(item["id"])
                    break
            else:
                print_error("ID not found.")
        elif choice == "u":
            suf = input("  Last 8 chars of ID to move up: ").strip()
            for item in queue_manager.get_status():
                if str(item["id"]).endswith(suf):
                    queue_manager.move_up(item["id"])
                    break
            else:
                print_error("ID not found.")
        else:
            print_error("Invalid option.")


# Mods Lists Export/Import 

def export_mod_list(cache, profile_name=None, output_path=None) -> bool:
    print_section("Export Mod List")
    export_data: dict = {
        "exported_at": get_timestamp(),
        "tool":        f"ModioDirect v{VERSION}",
        "mods":        [],
    }
    if profile_name:
        data    = load_profiles()
        profile = data.get("profiles", {}).get(profile_name)
        if not profile:
            print_error(f"Profile '{profile_name}' not found.")
            return False
        export_data["profile"] = profile_name
        export_data["mods"]    = profile.get("mods", [])
    else:
        for _mid, entry in cache.get("mods", {}).items():
            export_data["mods"].append({
                "mod_id":      entry.get("mod_id"),
                "mod_name":    entry.get("mod_name"),
                "game_slug":   entry.get("game_slug"),
                "mod_slug":    entry.get("mod_slug"),
                "version":     friendly_version(
                                   entry.get("latest_version_number"),
                                   entry.get("file_name"),
                               ),
                "filename":    entry.get("file_name"),
                "download_date": entry.get("download_date"),
            })

    if not output_path:
        suf        = f"_{profile_name}" if profile_name else ""
        output_path = os.path.join(
            BASE_DIR, f"modlist_export{suf}_{ts_for_filename()}.json"
        )
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)
        print_success(
            f"Exported {len(export_data['mods'])} mod(s) to: {output_path}"
        )
        return True
    except Exception as exc:
        print_error(f"Export failed: {exc}")
        return False


def export_mod_list_txt(cache, output_path=None) -> bool:
    mods = cache.get("mods", {})
    if not mods:
        print_error("No mods in cache to export.")
        return False
    if not output_path:
        output_path = os.path.join(
            BASE_DIR, f"modlist_{ts_for_filename()}.txt"
        )
    lines = [f"# ModioDirect Export — {get_timestamp()}", ""]
    for _mid, entry in mods.items():
        mod_name  = entry.get("mod_name", "?")
        game_slug = entry.get("game_slug", "")
        mod_slug  = entry.get("mod_slug", "")
        if game_slug and mod_slug:
            lines += [f"# {mod_name}", f"https://mod.io/g/{game_slug}/m/{mod_slug}", ""]
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        print_success(f"URL list exported to: {output_path}")
        return True
    except Exception as exc:
        print_error(f"Export failed: {exc}")
        return False


def import_mod_list(json_path, api_key, cache, force=False):
    print_section("Import Mod List")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print_error(f"Failed to read import file: {exc}")
        return
    mods = data.get("mods", [])
    if not mods:
        print_error("No mods found in import file.")
        return
    print_info(f"Importing {len(mods)} mod(s)...")
    succeeded, failed = 0, 0
    for entry in mods:
        game_slug = entry.get("game_slug")
        mod_slug  = entry.get("mod_slug")
        mod_name  = entry.get("mod_name", "?")
        if not game_slug or not mod_slug:
            print_warning(f"Skipping incomplete entry: {mod_name}")
            failed += 1
            continue
        print_info(f"  → {mod_name}")
        ok, *_ = process_single_mod(
            api_key, game_slug, mod_slug,
            install_requested=False, force_requested=force, cache=cache,
        )
        succeeded += ok
        if not ok:
            print_warning(f"  Failed: {mod_name}")
            failed += 1
    print_success(f"Import complete: {succeeded}/{len(mods)} succeeded.")
    if failed:
        print_warning(f"{failed} mod(s) failed — check warnings above.")


def export_import_menu(api_key, cache):
    while True:
        print_section("Export / Import")
        print_plain("  [1] Export all mods to JSON")
        print_plain("  [2] Export mod URLs to TXT")
        print_plain("  [3] Export a profile to JSON")
        print_plain("  [4] Import mod list from JSON")
        print_plain("  [0] Back")
        choice = input("  Choice: ").strip()
        if choice == "0":
            return
        elif choice == "1":
            export_mod_list(cache)
        elif choice == "2":
            export_mod_list_txt(cache)
        elif choice == "3":
            name = input("  Profile name: ").strip()
            export_mod_list(cache, profile_name=name)
        elif choice == "4":
            path = normalize_path_input(input("  Path to JSON file: ").strip())
            if not path or not os.path.isfile(path):
                print_error("File not found.")
                continue
            force = input("  Force reinstall? (y/n): ").strip().lower() == "y"
            import_mod_list(path, api_key, cache, force=force)
        else:
            print_error("Invalid option.")



def download_file(url, filename, expected_size=None, allow_existing=True):
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(1, 3):
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            target = filename if (os.path.isabs(filename) or os.path.dirname(filename)) \
                     else os.path.join(DOWNLOAD_DIR, filename)

            if allow_existing and os.path.exists(target):
                print_info(f"File already exists — using: {os.path.basename(target)}")
                return True, True, target

            if os.path.exists(target):
                try:
                    os.remove(target)
                except Exception:
                    pass
        except Exception as exc:
            print_error(f"Failed to prepare download path: {exc}")
            return False, False, ""

        print_status("Downloading...")
        resp = safe_request("GET", url, headers=headers, stream=True, timeout=30)
        if resp is None:
            if attempt == 2:
                return False, False, ""
            time.sleep(1)
            continue
        if resp.status_code == 429:
            print_error("Rate limited — try again later.")
            if attempt == 2:
                return False, False, ""
            time.sleep(3)
            continue
        if resp.status_code >= 400:
            print_error(f"Download error ({resp.status_code}).")
            if attempt == 2:
                return False, False, ""
            time.sleep(1)
            continue

        raw_len    = resp.headers.get("Content-Length")
        total_bytes = int(raw_len) if raw_len and raw_len.isdigit() else None

        # preventing corrupt resumes
        part_target = target + ".part"
        try:
            with open(part_target, "wb") as f:
                if tqdm is not None and total_bytes:
                    with tqdm(
                        total=total_bytes, unit="B",
                        unit_scale=True, desc="Downloading",
                    ) as bar:
                        for chunk in resp.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
                else:
                    downloaded, last_pct = 0, 0
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_bytes:
                                pct = int(downloaded / total_bytes * 100)
                                if pct >= last_pct + 5 or pct == 100:
                                    print(f"  Downloading... {pct}%")
                                    last_pct = pct

            if expected_size is not None:
                actual = os.path.getsize(part_target)
                if actual != expected_size:
                    os.remove(part_target)
                    print_error("File size mismatch — retrying.")
                    if attempt == 2:
                        return False, False, ""
                    time.sleep(1)
                    continue

            os.replace(part_target, target)
            if total_bytes is None:
                print_info("Download complete.")
            return True, False, target

        except Exception as exc:
            print_error(f"Write error: {exc}")
            for p in (part_target, target):
                if os.path.isfile(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            if attempt == 2:
                return False, False, ""
            time.sleep(1)

    return False, False, ""


def download_mod(url, filename=None, expected_size=None, allow_existing=True):
    if not isinstance(url, str) or not url.strip():
        print_error("Download URL is invalid.")
        return None, False
    if not filename:
        try:
            parsed   = urlparse(url)
            basename = os.path.basename(parsed.path or "")
            filename = unquote(basename) if basename else "modfile.bin"
        except Exception:
            filename = "modfile.bin"
    ok, skipped, final_path = download_file(
        url, filename,
        expected_size=expected_size,
        allow_existing=allow_existing,
    )
    return (final_path, skipped) if ok else (None, False)


def extract_mod(zip_path) -> str | None:
    if not isinstance(zip_path, str) or not zip_path:
        print_error("No file path supplied for extraction.")
        return None
    if not os.path.exists(zip_path):
        print_error("File does not exist — cannot extract.")
        return None
    if not zipfile.is_zipfile(zip_path):
        print_error("File is not a valid ZIP — extraction skipped.")
        return None
    try:
        extract_path = tempfile.mkdtemp(prefix="modiodirect_extract_")
        print_status("Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)
        print_status("Extraction complete.")
        return extract_path
    except Exception as exc:
        print_error(f"Extraction error: {exc}")
        return None


def install_mod(zip_path, target_path, force=False) -> bool:
    if not zip_path or not os.path.isfile(zip_path):
        print_error("Mod file is invalid or missing.")
        return False
    if not target_path or not os.path.isdir(target_path):
        print_error("Install target path is invalid.")
        return False
    extracted_path = ""
    try:
        base_name    = os.path.splitext(os.path.basename(zip_path))[0]
        existing_dir = os.path.join(target_path, base_name)
        if os.path.isdir(existing_dir) and os.listdir(existing_dir) and not force:
            print_info("Already installed — nothing to do.")
            return True
        extracted_path = extract_mod(zip_path)
        if not extracted_path:
            print_error("Install skipped — extraction failed.")
            return False
        print_status("Installing...")
        for name in os.listdir(extracted_path):
            src = os.path.join(extracted_path, name)
            dst = os.path.join(target_path, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        print_success(f"Installed to: {target_path}")
        return True
    except Exception as exc:
        print_error(f"Install error: {exc}")
        return False
    finally:
        if extracted_path and os.path.isdir(extracted_path):
            shutil.rmtree(extracted_path, ignore_errors=True)


# Game folder detection

def load_games_db():
    for path in GAMES_DB_PATHS:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            continue
    return None


def get_verified_paths_from_db(game_name) -> list:
    data = load_games_db()
    if not isinstance(data, dict):
        return []
    games = data.get("game_mod_paths")
    if not isinstance(games, list):
        return []
    key = normalize_name(game_name)
    for item in games:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and normalize_name(name) == key:
            paths     = []
            mod_paths = item.get("mod_folder_paths")
            if isinstance(mod_paths, dict):
                for _k, v in mod_paths.items():
                    if isinstance(v, str):
                        paths.append(v)
            return paths
    return []


def get_modio_storage_roots() -> list:
    roots      = []
    public_root = os.path.join(
        os.environ.get("PUBLIC", r"C:\Users\Public"), "mod.io"
    )
    if os.path.isdir(public_root):
        roots.append(public_root)
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        settings = os.path.join(local_app, "mod.io", "globalsettings.json")
        try:
            if os.path.isfile(settings):
                with open(settings, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    r = d.get("RootLocalStoragePath")
                    if isinstance(r, str) and os.path.isdir(r):
                        roots.append(r)
        except Exception:
            pass
    seen, unique = set(), []
    for r in roots:
        k = r.lower()
        if k not in seen:
            seen.add(k)
            unique.append(r)
    return unique


def detect_mod_folders(game_name, game_id) -> list:
    if os.name != "nt":
        return []
    verified = get_verified_paths_from_db(game_name)
    verified_candidates = []
    for p in verified:
        full = expand_path(p)
        if full and os.path.isdir(full):
            verified_candidates.append((f"{game_name} - Verified", full))
    if verified_candidates:
        return verified_candidates

    roots         = []
    steam_root    = r"C:\Program Files (x86)\Steam\steamapps\common"
    epic_root     = r"C:\Program Files\Epic Games"
    if os.path.isdir(steam_root):
        roots.append(steam_root)
    if os.path.isdir(epic_root):
        roots.append(epic_root)

    candidates    = []
    mod_dir_names = {"mods", "mod", "paks"}
    game_key      = normalize_name(game_name)

    for root in roots:
        for base, dirs, _files in os.walk(root):
            rel   = os.path.relpath(base, root)
            depth = rel.count(os.sep) if rel != "." else 0
            if depth > 3:
                dirs[:] = []
                continue
            lower_base = base.lower()
            if lower_base.endswith(os.path.join("bepinex", "plugins")):
                fg = os.path.basename(os.path.dirname(os.path.dirname(base)))
                if game_key and normalize_name(fg) != game_key:
                    continue
                candidates.append((f"{fg} - BepInEx/plugins", base))
            for d in list(dirs):
                if d.lower() in mod_dir_names:
                    full = os.path.join(base, d)
                    fg   = os.path.basename(base)
                    if game_key and normalize_name(fg) != game_key:
                        continue
                    if os.path.isdir(full):
                        candidates.append((f"{fg} - {d}", full))

    if isinstance(game_id, int):
        gid = str(game_id)
        for root in get_modio_storage_roots():
            try:
                for base, dirs, _files in os.walk(root):
                    rel   = os.path.relpath(base, root)
                    depth = rel.count(os.sep) if rel != "." else 0
                    if depth > 2:
                        dirs[:] = []
                        continue
                    for d in list(dirs):
                        if d == gid:
                            path = os.path.join(base, d)
                            if os.path.isdir(path):
                                candidates.append(
                                    (f"mod.io storage (game {gid})", path)
                                )
            except Exception:
                continue

    seen, unique = set(), []
    for label, path in candidates:
        k = path.lower()
        if k not in seen:
            seen.add(k)
            unique.append((label, path))
    return unique


# URL and batch parsing (preserved)

def parse_modio_url(url):
    if not isinstance(url, str):
        return None, None
    raw   = url.strip().split()[0]
    match = URL_REGEX.search(raw)
    if not match:
        return None, None
    gs = match.group(1).strip()
    ms = match.group(2).strip()
    return (gs, ms) if gs and ms else (None, None)


def load_batch_urls(file_path) -> list:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        print_error(f"Failed to read batch file: {exc}")
        return []
    return [
        line.strip() for line in lines
        if isinstance(line, str) and line.strip() and not line.strip().startswith("#")
    ]


def prompt_mod_url():
    while True:
        raw = input(
            "Enter mod URL (or file:PATH, q to exit, help, menu): "
        ).strip()
        install_requested = False
        force_requested   = False

        if " --install" in raw:
            raw               = raw.replace(" --install", "").strip()
            install_requested = True
        if " --force" in raw:
            raw             = raw.replace(" --force", "").strip()
            force_requested = True
        
        low = raw.lower()
        
        if low in ("help", "?"):
            print_plain("  Usage:")
            print_plain("---> Paste  :-- mod.io URL to download")
            print_plain("---> Append :-- install to auto-install")
            print_plain("---> Append :-- force to reinstall regardless of version")
            print_plain("---> file:  :-- \\path\\to\\mods.txt  for batch download")
            print_plain("---> menu   :-- open Extended Features")
            print_plain("---> q      :-- quit")
            continue

        if low in ("q", "quit", "exit"):
            return None, None, install_requested, force_requested

        if low == "menu":
            return "MENU", None, False, False

        if low.startswith("file:"):
            path = normalize_path_input(raw[5:])
            if not path:
                print_error("Batch file path is empty.")
                continue
            return "BATCH_FILE", path, install_requested, force_requested

        if low.endswith(".txt"):
            path = normalize_path_input(raw)
            if os.path.isfile(path):
                return "BATCH_FILE", path, install_requested, force_requested

        if not raw:
            continue

        match = URL_REGEX.search(raw)
        if not match:
            print_error(
                "Invalid URL. Expected: https://mod.io/g/<game>/m/<mod>"
            )
            continue

        gs = match.group(1).strip()
        ms = match.group(2).strip()
        if not gs or not ms:
            print_error("Could not parse game/mod slug from URL.")
            continue
        return gs, ms, install_requested, force_requested


# Core mod processing 

def process_single_mod(
    api_key,
    game_slug,
    mod_slug,
    install_requested,
    force_requested,
    cache,
    selected_file=None,
    skip_lock_check=False,
    profile_name=None,
):
    
    if not game_slug or not mod_slug:
        print_error("Missing game or mod slug.")
        return False, None, "", None, None, False, False

    if console:
        with console.status("[cyan]Fetching mod info...[/cyan]", spinner="dots"):
            time.sleep(0.3)

    # Resolve game
    game_id, err = resolve_game_id(api_key, game_slug)
    if err:
        print_error(friendly_error(err))
        return False, None, "", None, None, False, False

    game_details, gerr = fetch_game_details(api_key, game_id)
    if gerr:
        print_error(friendly_error(gerr))
        return False, None, "", game_id, None, False, False

    game_name = ""
    if isinstance(game_details, dict):
        n = game_details.get("name")
        if isinstance(n, str):
            game_name = n
    if game_name:
        print_info(f"Game : {game_name}")

    # Resolve mod 
    mod_id, err = resolve_mod_id(api_key, game_id, mod_slug)
    if err:
        print_error(friendly_error(err))
        return False, None, game_name, game_id, None, False, False

    mod_details, merr = fetch_mod_details(api_key, game_id, mod_id)
    if merr:
        print_error(friendly_error(merr))
        return False, None, game_name, game_id, None, False, False

    mod_name = ""
    if isinstance(mod_details, dict):
        n = mod_details.get("name")
        if isinstance(n, str):
            mod_name = n
    if mod_name:
        print_info(f"Mod  : {mod_name}")

    # Dependency check
    try:
        check_mod_dependencies(mod_details, cache)
    except Exception:
        pass

    # Resolve file to download
    if selected_file is not None:
        latest_file = selected_file
    else:
        files, err = fetch_mod_files(api_key, game_id, mod_id)
        if err:
            print_error(friendly_error(err))
            return False, None, game_name, game_id, None, False, False
        latest_file = select_best_file_for_platform(files)

    if latest_file is None:
        print_error("Could not determine mod file to download.")
        return False, None, game_name, game_id, None, False, False

    binary_url, filename = extract_download_info(latest_file)
    if not binary_url:
        print_error("No valid download URL found.")
        return False, None, game_name, game_id, None, False, False

    latest_version_id     = latest_file.get("id") if isinstance(latest_file, dict) else None
    latest_version_number = latest_file.get("version") if isinstance(latest_file, dict) else None
    expected_size         = get_expected_size(latest_file)

    ver_label = friendly_version(latest_version_number, filename, is_latest=True)
    print_info(f"File : {filename}  ({ver_label})")

    #  Lock checker
    if not skip_lock_check and not force_requested:
        if check_lock_before_update(mod_id, latest_version_id):
            return True, None, game_name, game_id, mod_id, True, False

    # Backup before replacing an existing version
    cache_mods = cache.get("mods", {}) if isinstance(cache, dict) else {}
    entry      = cache_mods.get(str(mod_id))
    if (entry
            and entry.get("latest_version_id") != latest_version_id
            and entry.get("file_name")):
        try:
            backup_mod_file(mod_id, mod_name, entry["file_name"])
        except Exception:
            pass

    existing_path = os.path.join(DOWNLOAD_DIR, filename) if filename else ""

    downloaded_path  = None
    skipped          = False
    install_skip     = False

    if entry and entry.get("latest_version_id") == latest_version_id and not force_requested:
        if install_requested:
            installed_id   = entry.get("installed_version_id")
            installed_path = entry.get("installed_path")
            if (installed_id == latest_version_id
                    and isinstance(installed_path, str)
                    and os.path.isdir(installed_path)):
                print_info("Already installed and up to date — nothing to do.")
                install_skip = True
                return True, "", game_name, game_id, mod_id, True, install_skip
        if os.path.isfile(existing_path):
            if expected_size is None or os.path.getsize(existing_path) == expected_size:
                print_info("Already up to date — skipping download.")
                downloaded_path = existing_path
                skipped         = True

    # download strategy...
    if downloaded_path is None:
        if not install_requested and os.path.isfile(existing_path) and not force_requested:
            if expected_size is None or os.path.getsize(existing_path) == expected_size:
                print_info("File already downloaded — using existing.")
                downloaded_path, skipped = existing_path, True

        if install_requested and downloaded_path is None:
            if (os.path.isfile(existing_path)
                    and (expected_size is None
                         or os.path.getsize(existing_path) == expected_size)
                    and not force_requested):
                print_info(f"File already exists — using: {os.path.basename(existing_path)}")
                downloaded_path, skipped = existing_path, True
            elif filename:
                temp_dir   = tempfile.mkdtemp(prefix="modiodirect_")
                temp_path  = os.path.join(temp_dir, filename)
                result     = download_mod(
                    binary_url, temp_path,
                    expected_size=expected_size,
                    allow_existing=False,
                )
                if result and result[0]:
                    downloaded_path, skipped = result

        elif downloaded_path is None:
            result = download_mod(
                binary_url, filename,
                expected_size=expected_size,
                allow_existing=True,
            )
            if result and result[0]:
                downloaded_path, skipped = result

    ok = downloaded_path is not None
    if ok:
        if not skipped and not install_requested and filename:
            print_saved_panel(os.path.join(DOWNLOAD_DIR, filename))

        # modinfo.json
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            info = {
                "game_name":       game_name,
                "mod_name":        mod_name,
                "mod_id":          mod_id,
                "file_id":         latest_version_id,
                "version":         ver_label,
                "date_downloaded": get_timestamp(),
                "tool_version":    VERSION,
            }
            with open(os.path.join(DOWNLOAD_DIR, "modinfo.json"),
                      "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception:
            pass
        # Update cache
        if isinstance(cache, dict):
            cache.setdefault("mods", {})
            cache["mods"][str(mod_id)] = {
                "mod_id":               mod_id,
                "mod_name":             mod_name,
                "game_id":              game_id,
                "game_slug":            game_slug,
                "mod_slug":             mod_slug,
                "latest_version_id":    latest_version_id,
                "latest_version_number": latest_version_number,
                "file_name":            filename,
                "file_size":            expected_size,
                "download_date":        get_timestamp(),
            }
            save_cache(cache)

        # Feature 4 — Auto-add to profile
        if profile_name:
            try:
                add_mod_to_profile(
                    profile_name, mod_id, mod_name,
                    game_slug, mod_slug,
                    file_id=latest_version_id,
                    version=latest_version_number,
                )
            except Exception:
                pass

        return True, downloaded_path, game_name, game_id, mod_id, skipped, install_skip

    print_error("Download failed after retries.")
    return False, None, game_name, game_id, mod_id, False, install_skip


#  the advanced download options prompt (interactive only)

def prompt_advanced_download_options(files):
    if not files or len(files) <= 1:
        return select_best_file_for_platform(files) if files else None

    print_plain("  [bold cyan]Multiple versions available:[/bold cyan]"
                if console else "  Multiple versions available:")
    print_plain("    [1] Download recommended build  (auto)")
    print_plain("    [2] Choose specific build        (Build Selector)")
    print_plain("    [3] Download older version       (Rollback)")

    choice = input("  Selection (1/2/3, default=1): ").strip()

    if choice == "2":
        return prompt_file_selector(files)
    elif choice == "3":
        return prompt_version_rollback(files)
    else:
        return select_best_file_for_platform(files)


# Features Hub...

def extended_features_menu(api_key, cache):
    while True:
        active = get_active_profile() or "None"
        print_section("Extended Features")
        if console:
            console.print(
                f"  [dim]Active Profile:[/dim] "
                f"[bold green]{active}[/bold green]   "
                f"[dim]v{VERSION}[/dim]"
            )
        else:
            print(f"  Active Profile: {active}   v{VERSION}")

        print_plain(" [1]  Profile Manager")
        print_plain(" [2]  Mod Locker")
        print_plain(" [3]  Mods versions")
        print_plain(" [4]  Mods Update")
        print_plain(" [5]  Mod Dependency")
        print_plain(" [6]  Mod Repair")
        print_plain(" [7]  Offline Library")
        print_plain(" [8]  Mod Storage")
        print_plain(" [9]  Modlist Export/Import")
        print_plain(" [10] Mods Backup")
        print_plain(" [0]  Exit")
        choice = input(" Select(1-10): ").strip()

        if choice == "0":
            return

        elif choice == "1":
            profiles_menu(api_key, cache)

        elif choice == "2":
            show_locked_mods_menu()
            url = input(
                "  Lock a specific mod version? Enter URL (Enter to skip): "
            ).strip()
            if url:
                gs, ms = parse_modio_url(url)
                if gs and ms:
                    gid, err = resolve_game_id(api_key, gs)
                    if not err:
                        mid, err = resolve_mod_id(api_key, gid, ms)
                        if not err:
                            files, err = fetch_mod_files(api_key, gid, mid)
                            if not err:
                                det, _ = fetch_mod_details(api_key, gid, mid)
                                mname  = (
                                    det.get("name", "") if isinstance(det, dict) else ""
                                )
                                latest = select_latest_file(files)
                                if latest:
                                    lock_mod_version(
                                        mid, mname,
                                        latest.get("id"),
                                        latest.get("version"),
                                        latest.get("filename"),
                                    )
                else:
                    print_error("Invalid URL.")

        elif choice == "3":
            url = input("  Enter the URL for your desired mod release: ").strip()
            gs, ms = parse_modio_url(url)
            if not gs or not ms:
                print_error("Invalid URL.")
                continue
            gid, err = resolve_game_id(api_key, gs)
            if err:
                print_error(friendly_error(err))
                continue
            mid, err = resolve_mod_id(api_key, gid, ms)
            if err:
                print_error(friendly_error(err))
                continue
            files, err = fetch_mod_files(api_key, gid, mid)
            if err:
                print_error(friendly_error(err))
                continue
            selected = prompt_version_rollback(files)
            if selected:
                ok, *_ = process_single_mod(
                    api_key, gs, ms,
                    install_requested=False,
                    force_requested=True,
                    cache=cache,
                    selected_file=selected,
                    skip_lock_check=True,
                )
                if ok:
                    print_success("Rollback download complete.")

        elif choice == "4":
            check_for_updates(api_key, cache)

        elif choice == "5":
            run_compatibility_check(cache)

        elif choice == "6":
            detect_broken_mods(cache, api_key=api_key)

        elif choice == "7":
            show_local_library(cache)

        elif choice == "8":
            analyze_storage(cache)

        elif choice == "9":
            export_import_menu(api_key, cache)

        elif choice == "xx":
            queue_menu(api_key, cache)

        elif choice == "10":
            manifest_path = os.path.join(BACKUP_DIR, "backup_manifest.json")
            manifest      = load_json_file(manifest_path, default={})
            if not manifest:
                print_info("No backups found.")
                continue
            entries = list(manifest.items())
            print_section("Available Backups")
            for idx, (mid, bks) in enumerate(entries, start=1):
                mname   = bks[-1].get("mod_name", mid) if bks else mid
                last_bk = bks[-1].get("backed_up_at", "?")[:19] if bks else "?"
                count   = len(bks)
                print_plain(
                    f"  [{idx}] {mname} — {count} backup(s), "
                    f"latest: {last_bk}"
                )
            raw = input("  Select to restore (0 = cancel): ").strip()
            if raw == "0" or not raw:
                continue
            try:
                num = int(raw)
                if 1 <= num <= len(entries):
                    mid, _ = entries[num - 1]
                    restore_mod_backup(int(mid), cache)
            except ValueError:
                print_error("Invalid selection.")

        else:
            print_error("Invalid option.")

# main entry poin...
def main():
    clear_screen()
    if not try_auto_install_rich():
        print_error("Cannot continue without 'rich'. Exiting.")
        return
    print_banner()
    if not try_auto_install_requests():
        print_error("Cannot continue without 'requests'. Exiting.")
        return

    parser = argparse.ArgumentParser(
        description=f"ModioDirect v{VERSION} — Mod Manager for mod.io",
        epilog=(
            "Examples:"
            f"  python ModioDirect.py https://mod.io/g/spaceengineers/m/my-mod"
            f"  python ModioDirect.py https://mod.io/g/spaceengineers/m/my-mod --install"
            f"  python ModioDirect.py --check-updates"
            f"  python ModioDirect.py --export"
            f"Tip: Type 'menu' at the prompt to open Extended Features."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("mod_url", nargs="?", help="mod.io mod URL")
    parser.add_argument("--install", action="store_true", help="Install mod to detected game folder")
    parser.add_argument("--no-config", action="store_true", help="Do not save API key to config.json")
    parser.add_argument("--no-pause", action="store_true", help="Do not pause on exit")
    parser.add_argument("--debug", action="store_true", help="Show full tracebacks on errors")
    parser.add_argument("--force", action="store_true", help="Reinstall regardless of cached version")
    parser.add_argument("--rollback", action="store_true", help="Show version selector before downloading")
    parser.add_argument("--build-select", action="store_true", help="Show build/file selector before downloading")
    parser.add_argument("--profile", type=str, default=None, help="Add downloaded mod to a named profile")
    parser.add_argument("--check-updates", action="store_true", help="Scan cached mods for updates and exit")
    parser.add_argument("--export", action="store_true", help="Export mod list to JSON and exit")
    args, _unknown = parser.parse_known_args()
    global DEBUG
    DEBUG = args.debug

    config_path = os.path.join(BASE_DIR, CONFIG_NAME)
    use_config  = not args.no_config
    api_key     = prompt_api_key(config_path, use_config)
    cache       = load_cache()

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    if args.check_updates:
        check_for_updates(api_key, cache)
        return

    if args.export:
        export_mod_list(cache)
        return

    while True:
        if args.mod_url:
            game_slug, mod_slug = parse_modio_url(args.mod_url)
            install_requested   = args.install
            force_requested     = args.force
            if not game_slug or not mod_slug:
                print_error("Invalid mod URL.")
                return

            selected_file = None
            if args.rollback or args.build_select:
                try:
                    gid, err = resolve_game_id(api_key, game_slug)
                    if not err:
                        mid, err = resolve_mod_id(api_key, gid, mod_slug)
                        if not err:
                            files, err = fetch_mod_files(api_key, gid, mid)
                            if not err and files:
                                selected_file = (
                                    prompt_version_rollback(files)
                                    if args.rollback
                                    else prompt_file_selector(files)
                                )
                except Exception:
                    selected_file = None

        else:
            game_slug, mod_slug, install_requested, force_requested = (
                prompt_mod_url()
            )

        if game_slug is None and mod_slug is None:
            print_info("Thank you for using ModioDirect;).")
            print_info("Check for updates: https://github.com/Therootexec/ModioDirect")
            return

        if game_slug == "MENU":
            extended_features_menu(api_key, cache)
            if args.mod_url:
                return
            continue

        if game_slug == "BATCH_FILE":
            urls = load_batch_urls(mod_slug)
            if not urls:
                print_error("Batch file is empty or unreadable.")
                if args.mod_url:
                    return
                continue
            print_info(f"Batch mode: {len(urls)} URL(s)")

            batch_target = None
            if install_requested:
                first_valid = next(
                    ((gs, ms) for u in urls
                     for gs, ms in [parse_modio_url(u)] if gs and ms),
                    None,
                )
                if first_valid:
                    gs, ms   = first_valid
                    gid, err = resolve_game_id(api_key, gs)
                    if err:
                        print_error(friendly_error(err))
                        install_requested = False
                    else:
                        gdet, gerr = fetch_game_details(api_key, gid)
                        gname      = (
                            gdet.get("name", "") if not gerr
                            and isinstance(gdet, dict) else ""
                        )
                        candidates = detect_mod_folders(gname, gid)
                        if not candidates:
                            print_error("Mod folder not found — install skipped.")
                            install_requested = False
                        else:
                            print_plain("  Select install location:")
                            for idx, (lbl, pth) in enumerate(candidates, 1):
                                print_plain(f"    [{idx}] {lbl}  →  {pth}")
                            print_plain(
                                f"    [{len(candidates)+1}] Skip install"
                            )
                            ch = input("  Choice (q = cancel): ").strip()
                            if ch.lower() in ("q", "quit"):
                                install_requested = False
                            else:
                                try:
                                    num = int(ch)
                                except ValueError:
                                    num = -1
                                if num == len(candidates) + 1:
                                    install_requested = False
                                elif 1 <= num <= len(candidates):
                                    batch_target = candidates[num - 1][1]
                                else:
                                    print_error("Invalid choice.")
                                    install_requested = False

            completed = 0
            for raw_url in urls:
                gs, ms = parse_modio_url(raw_url)
                if not gs or not ms:
                    print_error(f"Invalid URL: {raw_url}")
                    continue
                print_info(f"  Processing: {raw_url}")
                ok, dl_path, _, _, mod_id, _sk, _isk = process_single_mod(
                    api_key, gs, ms,
                    install_requested, force_requested, cache,
                    profile_name=args.profile,
                )
                if ok and install_requested and batch_target and not _isk:
                    if install_mod(dl_path, batch_target, force=force_requested):
                        if isinstance(cache, dict) and mod_id is not None:
                            cache.setdefault("mods", {})
                            e = cache["mods"].get(str(mod_id), {})
                            e["installed_version_id"] = e.get("latest_version_id")
                            e["installed_path"]       = batch_target
                            cache["mods"][str(mod_id)] = e
                            save_cache(cache)
                    cleanup_temp_file(dl_path)
                if ok:
                    completed += 1

            print_info(f"Batch complete: {completed}/{len(urls)} successful.")

        else:
            selected_file = None
            if not args.mod_url:
                try:
                    gid, err = resolve_game_id(api_key, game_slug)
                    if not err:
                        mid, err = resolve_mod_id(api_key, gid, mod_slug)
                        if not err:
                            files, err = fetch_mod_files(api_key, gid, mid)
                            if not err and files and len(files) > 1:
                                selected_file = prompt_advanced_download_options(
                                    files
                                )
                except Exception:
                    selected_file = None

            ok, dl_path, game_name, game_id, mod_id, _sk, _isk = (
                process_single_mod(
                    api_key, game_slug, mod_slug,
                    install_requested, force_requested, cache,
                    selected_file=selected_file,
                    profile_name=args.profile if args.mod_url else None,
                )
            )

            if ok and install_requested and not _isk:
                candidates = detect_mod_folders(game_name, game_id)
                if not candidates:
                    print_error("Mod folder not found — install skipped.")
                else:
                    print_plain("  Select install location:")
                    for idx, (lbl, pth) in enumerate(candidates, 1):
                        print_plain(f"    [{idx}] {lbl}  →  {pth}")
                    print_plain(f"    [{len(candidates)+1}] Skip install")
                    ch = input("  Choice (q = cancel): ").strip()
                    if ch.lower() not in ("q", "quit"):
                        try:
                            num = int(ch)
                        except ValueError:
                            num = -1
                        if num == len(candidates) + 1:
                            print_info("Install skipped.")
                        elif 1 <= num <= len(candidates):
                            target = candidates[num - 1][1]
                            if install_mod(dl_path, target, force=force_requested):
                                if isinstance(cache, dict) and mod_id is not None:
                                    cache.setdefault("mods", {})
                                    e = cache["mods"].get(str(mod_id), {})
                                    e["installed_version_id"] = e.get("latest_version_id")
                                    e["installed_path"]       = target
                                    cache["mods"][str(mod_id)] = e
                                    save_cache(cache)
                            cleanup_temp_file(dl_path)
                        else:
                            print_error("Invalid choice.")

            if ok and not args.mod_url:
                profile_names = get_profile_names()
                if profile_names:
                    active = get_active_profile()
                    prompt  = (
                        f"  Add to profile? "
                        f"(active: {active or 'none'}, "
                        f"options: {', '.join(profile_names)}, "
                        f"Enter = skip): "
                    )
                    add_to = input(prompt).strip()
                    if add_to and add_to in profile_names and mod_id:
                        e = cache.get("mods", {}).get(str(mod_id), {})
                        add_mod_to_profile(
                            add_to, mod_id,
                            e.get("mod_name", "?"),
                            game_slug, mod_slug,
                            file_id=e.get("latest_version_id"),
                            version=e.get("latest_version_number"),
                        )

        if args.mod_url:
            return


def maybe_pause_on_exit():
    if os.name != "nt":
        return
    if "--no-pause" in sys.argv:
        return
    if len(sys.argv) > 1:
        return
    try:
        input("  Press Enter to exit...")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("Interrupted by user.")
    except Exception:
        print_error("Unexpected error occurred.")
        if DEBUG:
            try:
                traceback.print_exc()
            except Exception:
                pass
    finally:
        maybe_pause_on_exit()
# in case there is an issues with the code dont foget to reach out (^-^)