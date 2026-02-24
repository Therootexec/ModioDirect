#!/usr/bin/env python3

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
from urllib.parse import urlparse, unquote

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None

try:
    import requests  # type: ignore
except Exception:
    requests = None


API_BASE = "https://api.mod.io/v1"
VERSION = "1.0.1"
CONFIG_NAME = "config.json"
USER_AGENT = "ModioDirect/1.1 (TheRootExec)"
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
CACHE_PATH = os.path.join(DOWNLOAD_DIR, "mod_cache.json")
DEBUG = False
GAMES_DB_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "games.json"),
    os.path.join(DOWNLOAD_DIR, "games.json"),
    os.path.join(os.path.expanduser("~"), "Downloads", "games.json"),
]
URL_REGEX = re.compile(
    r"^https?://(?:www\.)?mod\.io/g/([^/]+)/m/([^/?#]+)",
    re.IGNORECASE,
)


def print_error(msg):
    print(f"[Error] {msg}")


def print_info(msg):
    print(f"[Info] {msg}")


def print_status(msg):
    print(f"[Status] {msg}")


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


def load_cache():
    try:
        if os.path.isfile(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"mods": {}}


def save_cache(cache):
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        return True
    except Exception:
        return False


def get_expected_size(file_obj):
    if not isinstance(file_obj, dict):
        return None
    size = file_obj.get("filesize")
    if isinstance(size, int):
        return size
    download = file_obj.get("download")
    if isinstance(download, dict):
        size = download.get("filesize")
        if isinstance(size, int):
            return size
    return None


def friendly_error(err):
    if not isinstance(err, str):
        return "Unexpected error occurred."
    s = err.lower()
    if "401" in s or "403" in s or "unauthorized" in s or "oauth" in s or "private" in s:
        return "Mod is private, inaccessible, or requires authentication."
    if "404" in s or "not found" in s:
        return "Mod or game not found."
    if "429" in s or "rate" in s:
        return "Rate limited. Try again later."
    if "network" in s or "timeout" in s:
        return "Network error occurred."
    return "Unexpected error occurred."


def print_banner():
    print(r" __  __           _ _       _____  _               _   ")
    print(r"|  \/  | ___   __| (_) ___ |  __ \(_)_ __ ___  ___| |_ ")
    print(r"| |\/| |/ _ \ / _` | |/ _ \| |  | | | '__/ _ \/ __| __|")
    print(r"| |  | | (_) | (_| | | (_) | |__| | | | |  __/ (__| |_ ")
    print(r"|_|  |_|\___/ \__,_|_|\___/|_____/|_|_|  \___|\___|\__|")
    print("\n             ModioDirect Downloader Tool")
    print("                 by TheRootExec v1.0.1")
    print("-------------------------------------------------------")


def try_auto_install_requests():
    global requests
    if requests is not None:
        return True
    print_error("The 'requests' library is required but not installed.")
    choice = input("Install requirements now? (y/n): ").strip().lower()
    if choice != "y":
        return False
    try:
        cmd = [sys.executable, "-m", "pip", "install", "requests"]
        subprocess.run(cmd, check=False)
    except Exception as exc:
        print_error(f"Failed to run pip: {exc}")
        return False
    try:
        import requests as _requests  # type: ignore
        requests = _requests
        return True
    except Exception:
        print_error("Requests is still not available after install attempt.")
        return False


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def safe_request(method, url, **kwargs):
    if requests is None:
        print_error("The 'requests' library is not installed. Install it with: pip install requests")
        return None
    try:
        return requests.request(method, url, **kwargs)
    except Exception:
        print_error("Network error occurred.")
        return None




def load_config(config_path):
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_config(config_path, data):
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as exc:
        print_error(f"Failed to save config: {exc}")
        return False


def validate_api_key(api_key):
    url = f"{API_BASE}/games"
    params = {"api_key": api_key, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return False, "Network error or requests missing."
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


def prompt_api_key(config_path, use_config):
    config = {}
    api_key = ""
    if use_config:
        config = load_config(config_path)
        if isinstance(config, dict):
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


def normalize_path_input(value):
    if not isinstance(value, str):
        return ""
    return value.strip().strip("\"").strip("'")


def prompt_mod_url():
    while True:
        raw = input("Enter mod URL (or file:PATH, q to exit, help): ").strip()
        install_requested = False
        force_requested = False
        if " --install" in raw:
            raw = raw.replace(" --install", "").strip()
            install_requested = True
        if " --force" in raw:
            raw = raw.replace(" --force", "").strip()
            force_requested = True
        if raw.lower() in ("help", "?"):
            print("Usage:")
            print("  Paste a mod.io URL")
            print("  Or type file:C:\\path\\to\\mods.txt for batch")
            print("  Add --install to auto-install if a mod folder is detected")
            print("  Type q to exit")
            continue
        if raw.lower() in ("q", "quit", "exit"):
            return None, None, install_requested, force_requested
        if raw.lower().startswith("file:"):
            path = normalize_path_input(raw[5:])
            if not path:
                print_error("Batch file path is empty.")
                continue
            return "BATCH_FILE", path, install_requested, force_requested
        # Allow direct path to batch file without file: prefix
        if raw.lower().endswith(".txt"):
            path = normalize_path_input(raw)
            if os.path.isfile(path):
                return "BATCH_FILE", path, install_requested, force_requested
        if not raw:
            print_error("URL cannot be empty.")
            continue
        match = URL_REGEX.search(raw)
        if not match:
            print_error("Invalid mod.io URL. Expected: https://mod.io/g/<game_slug>/m/<mod_slug>")
            continue
        game_slug = match.group(1).strip()
        mod_slug = match.group(2).strip()
        if not game_slug or not mod_slug:
            print_error("Could not parse game_slug or mod_slug from URL.")
            continue
        return game_slug, mod_slug, install_requested, force_requested


def load_batch_urls(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        print_error(f"Failed to read batch file: {exc}")
        return []
    urls = []
    for line in lines:
        if not isinstance(line, str):
            continue
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def parse_modio_url(url):
    if not isinstance(url, str):
        return None, None
    raw = url.strip().split()[0]
    match = URL_REGEX.search(raw)
    if not match:
        return None, None
    game_slug = match.group(1).strip()
    mod_slug = match.group(2).strip()
    if not game_slug or not mod_slug:
        return None, None
    return game_slug, mod_slug


def resolve_game_id(api_key, game_slug):
    url = f"{API_BASE}/games"
    params = {"api_key": api_key, "name_id": game_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while resolving game."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while resolving game."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while resolving game."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while resolving game."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        fallback_id, fallback_err = fallback_search_game_id(api_key, game_slug)
        if fallback_id is not None:
            return fallback_id, None
        return None, fallback_err or "Game not found for provided game_slug."
    game = items[0] if len(items) > 0 else None
    if not isinstance(game, dict):
        return None, "Unexpected game data format."
    game_id = game.get("id")
    if not isinstance(game_id, int):
        return None, "Missing game_id in API response."
    return game_id, None


def match_slug(item, slug):
    if not isinstance(item, dict):
        return False
    name_id = item.get("name_id")
    if isinstance(name_id, str) and name_id.lower() == slug.lower():
        return True
    alt_slug = item.get("slug")
    if isinstance(alt_slug, str) and alt_slug.lower() == slug.lower():
        return True
    return False


def fallback_search_game_id(api_key, game_slug):
    url = f"{API_BASE}/games"
    params = {"api_key": api_key, "_q": game_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while searching game."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while searching game."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while searching game."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while searching game."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        return None, "Game not found for provided game_slug."
    for item in items:
        if match_slug(item, game_slug):
            game_id = item.get("id") if isinstance(item, dict) else None
            if isinstance(game_id, int):
                return game_id, None
    return None, "Game not found for provided game_slug."


def resolve_mod_id(api_key, game_id, mod_slug):
    url = f"{API_BASE}/games/{game_id}/mods"
    params = {"api_key": api_key, "name_id": mod_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while resolving mod."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while resolving mod."
    if resp.status_code == 404:
        fallback_id, fallback_err = resolve_mod_id_global(api_key, game_id, mod_slug)
        if fallback_id is not None:
            return fallback_id, None
        return None, fallback_err or "API returned 404 while resolving mod. The game or mod may be inaccessible with this API key."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while resolving mod."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while resolving mod."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        fallback_id, fallback_err = fallback_search_mod_id(api_key, game_id, mod_slug)
        if fallback_id is not None:
            return fallback_id, None
        return None, fallback_err or "Mod not found for provided mod_slug."
    mod = items[0] if len(items) > 0 else None
    if not isinstance(mod, dict):
        return None, "Unexpected mod data format."
    mod_id = mod.get("id")
    if not isinstance(mod_id, int):
        return None, "Missing mod_id in API response."
    return mod_id, None


def resolve_mod_id_global(api_key, game_id, mod_slug):
    url = f"{API_BASE}/mods"
    params = {"api_key": api_key, "game_id": game_id, "name_id": mod_slug, "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while resolving mod (global)."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while resolving mod (global)."
    if resp.status_code == 404:
        search_id, search_err = resolve_mod_id_global_search(api_key, game_id, mod_slug)
        if search_id is not None:
            return search_id, None
        numeric_id, numeric_err = resolve_mod_id_numeric(api_key, game_id, mod_slug)
        if numeric_id is not None:
            return numeric_id, None
        return None, search_err or numeric_err or "API error (404) while resolving mod (global)."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while resolving mod (global)."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while resolving mod (global)."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        return None, "Mod not found for provided mod_slug."
    mod = items[0] if len(items) > 0 else None
    if not isinstance(mod, dict):
        return None, "Unexpected mod data format."
    mod_id = mod.get("id")
    if not isinstance(mod_id, int):
        return None, "Missing mod_id in API response."
    return mod_id, None


def resolve_mod_id_global_search(api_key, game_id, mod_slug):
    url = f"{API_BASE}/mods"
    params = {"api_key": api_key, "_q": mod_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while searching mod (global)."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while searching mod (global)."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while searching mod (global)."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while searching mod (global)."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        return None, "Mod not found for provided mod_slug."
    for item in items:
        if not isinstance(item, dict):
            continue
        item_game_id = item.get("game_id")
        if isinstance(item_game_id, int) and item_game_id != game_id:
            continue
        if match_slug(item, mod_slug):
            mod_id = item.get("id")
            if isinstance(mod_id, int):
                return mod_id, None
    return None, "Mod not found for provided mod_slug."


def resolve_mod_id_numeric(api_key, game_id, mod_slug):
    if not isinstance(mod_slug, str) or not mod_slug.isdigit():
        return None, None
    mod_id = int(mod_slug)
    url = f"{API_BASE}/games/{game_id}/mods/{mod_id}"
    params = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while resolving mod by numeric ID."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while resolving mod by numeric ID."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while resolving mod by numeric ID."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while resolving mod by numeric ID."
    mid = data.get("id")
    if not isinstance(mid, int):
        return None, "Missing mod_id in API response."
    return mid, None


def fallback_search_mod_id(api_key, game_id, mod_slug):
    url = f"{API_BASE}/games/{game_id}/mods"
    params = {"api_key": api_key, "_q": mod_slug, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while searching mod."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while searching mod."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while searching mod."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while searching mod."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        return None, "Mod not found for provided mod_slug."
    for item in items:
        if match_slug(item, mod_slug):
            mod_id = item.get("id") if isinstance(item, dict) else None
            if isinstance(mod_id, int):
                return mod_id, None
    return None, "Mod not found for provided mod_slug."


def fetch_game_details(api_key, game_id):
    url = f"{API_BASE}/games/{game_id}"
    params = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while fetching game details."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while fetching game details."
    if resp.status_code == 404:
        return None, "Game not accessible (404). The game may be private, unpublished, or require OAuth access."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while fetching game details."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while fetching game details."
    return data, None


def fetch_mod_details(api_key, game_id, mod_id):
    url = f"{API_BASE}/games/{game_id}/mods/{mod_id}"
    params = {"api_key": api_key}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=15)
    if resp is None:
        return None, "Network error while fetching mod details."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while fetching mod details."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while fetching mod details."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while fetching mod details."
    return data, None


def fetch_mod_files(api_key, game_id, mod_id):
    url = f"{API_BASE}/games/{game_id}/mods/{mod_id}/files"
    params = {"api_key": api_key, "limit": 100}
    headers = {"User-Agent": USER_AGENT}
    resp = safe_request("GET", url, params=params, headers=headers, timeout=20)
    if resp is None:
        return None, "Network error while fetching mod files."
    if resp.status_code == 401:
        return None, "Invalid API key (401 Unauthorized)."
    if resp.status_code == 429:
        return None, "Rate limited (429) while fetching mod files."
    if resp.status_code >= 400:
        return None, f"API error ({resp.status_code}) while fetching mod files."
    data = safe_json(resp)
    if not isinstance(data, dict):
        return None, "Empty or invalid API response while fetching mod files."
    items = data.get("data")
    if not isinstance(items, list) or len(items) == 0:
        return None, "No mod files found."
    return items, None


def select_latest_file(files):
    if not isinstance(files, list) or len(files) == 0:
        return None
    latest = None
    latest_date = -1
    for f in files:
        if not isinstance(f, dict):
            continue
        date_added = f.get("date_added")
        if isinstance(date_added, int) and date_added > latest_date:
            latest_date = date_added
            latest = f
    return latest


def extract_download_info(file_obj):
    if not isinstance(file_obj, dict):
        return None, None
    download = file_obj.get("download")
    if not isinstance(download, dict):
        return None, None
    binary_url = download.get("binary_url")
    if not isinstance(binary_url, str) or not binary_url.strip():
        return None, None
    binary_url = binary_url.replace("\\/", "/")
    filename = file_obj.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        try:
            parsed = urlparse(binary_url)
            path = parsed.path or ""
            basename = os.path.basename(path)
            filename = unquote(basename) if basename else "modfile.bin"
        except Exception:
            filename = "modfile.bin"
    return binary_url, filename


def download_file(url, filename, expected_size=None, allow_existing=True):
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, 3):
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            if os.path.isabs(filename) or os.path.dirname(filename):
                target = filename
            else:
                target = os.path.join(DOWNLOAD_DIR, filename)
            if allow_existing and os.path.exists(target):
                print_info(f"File already exists, skipping: {target}")
                print_info("Using existing file.")
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
            print_error("Network error occurred.")
            if attempt == 2:
                return False, False, ""
            time.sleep(1)
            continue
        if resp.status_code == 429:
            print_error("Rate limited. Try again later.")
            if attempt == 2:
                return False, False, ""
            time.sleep(2)
            continue
        if resp.status_code >= 400:
            print_error("Unexpected error occurred.")
            if attempt == 2:
                return False, False, ""
            time.sleep(1)
            continue

        total = resp.headers.get("Content-Length")
        try:
            total_bytes = int(total) if total is not None else None
        except Exception:
            total_bytes = None

        try:
            with open(target, "wb") as f:
                if tqdm is not None and total_bytes is not None:
                    with tqdm(total=total_bytes, unit="B", unit_scale=True, desc="Downloading") as bar:
                        for chunk in resp.iter_content(chunk_size=1024 * 256):
                            if not chunk:
                                continue
                            f.write(chunk)
                            bar.update(len(chunk))
                else:
                    downloaded = 0
                    last_print = 0
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes:
                            pct = int((downloaded / total_bytes) * 100)
                            if pct >= last_print + 5 or pct == 100:
                                print(f"Downloading... {pct}%")
                                last_print = pct
            if total_bytes is None:
                print_info("Download complete (size unknown).")
            if expected_size is not None:
                try:
                    actual = os.path.getsize(target)
                    if actual != expected_size:
                        try:
                            os.remove(target)
                        except Exception:
                            pass
                        print_error("Downloaded file size mismatch. Retrying.")
                        if attempt == 2:
                            return False, False, ""
                        time.sleep(1)
                        continue
                except Exception:
                    pass
            print_status("Download complete.")
            return True, False, target
        except Exception:
            print_error("Unexpected error occurred.")
            if attempt == 2:
                return False, False, ""
            time.sleep(1)
    return False, False, ""


def download_mod(url, filename=None, expected_size=None, allow_existing=True):
    if not isinstance(url, str) or not url.strip():
        print_error("Download URL is invalid.")
        return None
    if not filename:
        try:
            parsed = urlparse(url)
            path = parsed.path or ""
            base = os.path.basename(path)
            filename = unquote(base) if base else None
        except Exception:
            filename = None
    if not filename:
        filename = "modfile.bin"
    ok, skipped, final_path = download_file(url, filename, expected_size=expected_size, allow_existing=allow_existing)
    if not ok:
        return None, False
    return final_path, skipped


def extract_mod(zip_path):
    if not isinstance(zip_path, str) or not zip_path:
        print_error("No downloaded file to extract.")
        return None
    if not os.path.exists(zip_path):
        print_error("Downloaded file does not exist.")
        return None
    if not zipfile.is_zipfile(zip_path):
        print_error("Downloaded file is not a ZIP. Extraction skipped.")
        return None
    try:
        extract_path = tempfile.mkdtemp(prefix="modiodirect_extract_")
        print_status("Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)
        print_status("Extraction complete.")
        return extract_path
    except Exception:
        print_error("Unexpected error occurred.")
        return None


def normalize_name(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def expand_path(value):
    if not isinstance(value, str):
        return ""
    cleaned = value.replace("/", "\\")
    cleaned = cleaned.replace("{USERNAME}", os.environ.get("USERNAME", ""))
    cleaned = cleaned.replace("[Manual]", "").strip()
    cleaned = os.path.expandvars(cleaned)
    cleaned = os.path.expanduser(cleaned)
    return cleaned


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


def get_verified_paths_from_db(game_name):
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
            paths = []
            mod_paths = item.get("mod_folder_paths")
            if isinstance(mod_paths, dict):
                for _k, v in mod_paths.items():
                    if isinstance(v, str):
                        paths.append(v)
            return paths
    return []


def get_modio_storage_roots():
    roots = []
    public_root = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "mod.io")
    if os.path.isdir(public_root):
        roots.append(public_root)
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        settings = os.path.join(local_app, "mod.io", "globalsettings.json")
        try:
            if os.path.isfile(settings):
                with open(settings, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    root = data.get("RootLocalStoragePath")
                    if isinstance(root, str) and os.path.isdir(root):
                        roots.append(root)
        except Exception:
            pass
    seen = set()
    unique = []
    for r in roots:
        key = r.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def detect_mod_folders(game_name, game_id):
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

    roots = []
    steam_root = r"C:\Program Files (x86)\Steam\steamapps\common"
    epic_root = r"C:\Program Files\Epic Games"
    if os.path.isdir(steam_root):
        roots.append(steam_root)
    if os.path.isdir(epic_root):
        roots.append(epic_root)

    candidates = []
    mod_dir_names = {"mods", "mod", "paks"}
    game_key = normalize_name(game_name)
    for root in roots:
        for base, dirs, _files in os.walk(root):
            rel = os.path.relpath(base, root)
            depth = rel.count(os.sep) if rel != "." else 0
            if depth > 3:
                dirs[:] = []
                continue

            lower_base = base.lower()
            if lower_base.endswith(os.path.join("bepinex", "plugins")):
                found_game = os.path.basename(os.path.dirname(os.path.dirname(base)))
                if game_key and normalize_name(found_game) != game_key:
                    continue
                label = f"{found_game} - BepInEx/plugins"
                candidates.append((label, base))

            for d in list(dirs):
                if d.lower() in mod_dir_names:
                    full = os.path.join(base, d)
                    found_game = os.path.basename(base)
                    if game_key and normalize_name(found_game) != game_key:
                        continue
                    if os.path.isdir(full):
                        label = f"{found_game} - {d}"
                        candidates.append((label, full))

    if isinstance(game_id, int):
        gid = str(game_id)
        for root in get_modio_storage_roots():
            try:
                for base, dirs, _files in os.walk(root):
                    rel = os.path.relpath(base, root)
                    depth = rel.count(os.sep) if rel != "." else 0
                    if depth > 2:
                        dirs[:] = []
                        continue
                    for d in list(dirs):
                        if d == gid:
                            path = os.path.join(base, d)
                            if os.path.isdir(path):
                                label = f"mod.io storage (game_id {gid})"
                                candidates.append((label, path))
            except Exception:
                continue
    seen = set()
    unique = []
    for label, path in candidates:
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((label, path))
    return unique


def install_mod(zip_path, target_path, force=False):
    if not zip_path or not os.path.isfile(zip_path):
        print_error("Downloaded mod file is invalid.")
        return False
    if not target_path:
        print_error("Target install path is invalid.")
        return False
    if not os.path.isdir(target_path):
        print_error("Target install path is invalid.")
        return False
    extracted_path = ""
    try:
        base_name = os.path.splitext(os.path.basename(zip_path))[0]
        existing_dir = os.path.join(target_path, base_name)
        if os.path.isdir(existing_dir) and os.listdir(existing_dir) and not force:
            print_info("Up to date — nothing to do.")
            return True
        extracted_path = extract_mod(zip_path)
        if not extracted_path:
            print_error("Install skipped (extraction failed).")
            return False
        print_status("Installing...")
        for name in os.listdir(extracted_path):
            src = os.path.join(extracted_path, name)
            dst = os.path.join(target_path, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        print_status("Install complete.")
        print_info(f"Mod installed successfully: {target_path}")
        return True
    except Exception:
        print_error("Unexpected error occurred.")
        return False
    finally:
        if extracted_path and os.path.isdir(extracted_path):
            shutil.rmtree(extracted_path, ignore_errors=True)


def process_single_mod(api_key, game_slug, mod_slug, install_requested, force_requested, cache):
    if not game_slug or not mod_slug:
        print_error("Missing game or mod slug.")
        return False, None, "", None, None, False, False

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
        name = game_details.get("name")
        if isinstance(name, str):
            game_name = name
    if game_name:
        print_info(f"Game : {game_name}")

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
        name = mod_details.get("name")
        if isinstance(name, str):
            mod_name = name

    if mod_name:
        print_info(f"Mod  : {mod_name}")

    files, err = fetch_mod_files(api_key, game_id, mod_id)
    if err:
        print_error(friendly_error(err))
        return False, None, game_name, game_id, None, False, False

    latest_file = select_latest_file(files)
    if latest_file is None:
        print_error("Could not determine latest mod file.")
        return False, None, game_name, game_id, None, False, False

    binary_url, filename = extract_download_info(latest_file)
    if not binary_url:
        print_error("No valid download URL found in mod file.")
        return False, None, game_name, game_id, None, False, False

    latest_version_id = latest_file.get("id") if isinstance(latest_file, dict) else None
    latest_version_number = latest_file.get("version") if isinstance(latest_file, dict) else None
    expected_size = get_expected_size(latest_file)

    print_info(f"Latest file: {filename}")
    cache_mods = cache.get("mods", {}) if isinstance(cache, dict) else {}
    entry = cache_mods.get(str(mod_id)) if isinstance(cache_mods, dict) else None
    existing_path = os.path.join(DOWNLOAD_DIR, filename) if filename else ""

    downloaded_path = None
    skipped = False
    install_skip = False
    if entry and entry.get("latest_version_id") == latest_version_id and not force_requested:
        if install_requested:
            installed_id = entry.get("installed_version_id")
            installed_path = entry.get("installed_path")
            if installed_id == latest_version_id and isinstance(installed_path, str) and os.path.isdir(installed_path):
                print_info("Up to date — nothing to do.")
                install_skip = True
                return True, "", game_name, game_id, mod_id, True, install_skip
        if os.path.isfile(existing_path):
            if expected_size is None or os.path.getsize(existing_path) == expected_size:
                print_info("Already latest version. Skipping download.")
                downloaded_path = existing_path
                skipped = True

    if downloaded_path is None:
        if not install_requested and os.path.isfile(existing_path) and not force_requested:
            if expected_size is None or os.path.getsize(existing_path) == expected_size:
                print_info("Already downloaded. Using existing file.")
                downloaded_path, skipped = existing_path, True
        if downloaded_path is not None:
            pass
        if install_requested:
            if os.path.isfile(existing_path) and (expected_size is None or os.path.getsize(existing_path) == expected_size) and not force_requested:
                print_info(f"File already exists, skipping: {existing_path}")
                downloaded_path, skipped = existing_path, True
            else:
                if filename:
                    temp_dir = tempfile.mkdtemp(prefix="modiodirect_")
                    temp_path = os.path.join(temp_dir, filename)
                    result = download_mod(
                        binary_url,
                        temp_path,
                        expected_size=expected_size,
                        allow_existing=False,
                    )
                    if result:
                        downloaded_path, skipped = result
        else:
            if downloaded_path is None:
                result = download_mod(
                    binary_url,
                    filename,
                    expected_size=expected_size,
                    allow_existing=True,
                )
                if result is not None:
                    downloaded_path, skipped = result

    ok = downloaded_path is not None
    if ok:
        if not skipped and not install_requested:
            if filename:
                print_info(f"Saved as: {os.path.join(DOWNLOAD_DIR, filename)}")
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            info_path = os.path.join(DOWNLOAD_DIR, "modinfo.json")
            info = {
                "game_name": game_name,
                "mod_name": mod_name,
                "mod_id": mod_id,
                "file_id": latest_version_id,
                "date_downloaded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception:
            print_error("Unexpected error occurred.")
        if isinstance(cache, dict):
            cache.setdefault("mods", {})
            cache["mods"][str(mod_id)] = {
                "mod_id": mod_id,
                "mod_name": mod_name,
                "latest_version_id": latest_version_id,
                "latest_version_number": latest_version_number,
                "file_name": filename,
                "file_size": expected_size,
                "download_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            save_cache(cache)
        return True, downloaded_path, game_name, game_id, mod_id, skipped, install_skip

    print_error("Download failed after retry.")
    return False, None, game_name, game_id, mod_id, False, install_skip


def main():
    print_banner()
    if not try_auto_install_requests():
        print_error("Cannot continue without 'requests'.")
        return

    parser = argparse.ArgumentParser(
        description="ModioDirect - crash-proof mod.io downloader",
        epilog=(
            "Examples:\n"
            "  python ModioDirect.py https://mod.io/g/spaceengineers/m/assault-weapons-pack1\n"
            "  python ModioDirect.py https://mod.io/g/spaceengineers/m/assault-weapons-pack1 --install\n"
            "  python ModioDirect.py --no-config\n"
            "Tip: Paste a URL at the prompt, or type file:C:\\path\\to\\mods.txt for batch."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("mod_url", nargs="?", help="mod.io mod URL")
    parser.add_argument("--install", action="store_true", help="Install mod to detected game folder (opt-in)")
    parser.add_argument("--no-config", action="store_true", help="Do not save API key to config.json")
    parser.add_argument("--no-pause", action="store_true", help="Do not pause on exit")
    parser.add_argument("--debug", action="store_true", help="Show technical errors")
    parser.add_argument("--force", action="store_true", help="Reinstall regardless of version")
    args, _unknown = parser.parse_known_args()
    global DEBUG
    DEBUG = args.debug

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)
    use_config = not args.no_config
    api_key = prompt_api_key(config_path, use_config)
    cache = load_cache()

    while True:
        if args.mod_url:
            game_slug, mod_slug = parse_modio_url(args.mod_url)
            install_requested = args.install
            force_requested = args.force
            if not game_slug or not mod_slug:
                print_error("Invalid mod URL.")
                return
        else:
            game_slug, mod_slug, install_requested, force_requested = prompt_mod_url()
        if game_slug is None and mod_slug is None:
            print_info("Thanks for using ModioDirect.")
            print_info("Check GitHub for more: https://github.com/Therootexec/ModioDirect")
            return
        if game_slug == "BATCH_FILE":
            urls = load_batch_urls(mod_slug)
            if not urls:
                print_error("Batch file is empty or unreadable.")
                continue
            print_info(f"Batch mode: {len(urls)} URL(s)")
            batch_target = None
            if install_requested:
                first_valid = None
                for raw_url in urls:
                    gs, ms = parse_modio_url(raw_url)
                    if gs and ms:
                        first_valid = (gs, ms)
                        break
                if first_valid:
                    gs, ms = first_valid
                    gid, err = resolve_game_id(api_key, gs)
                    if err:
                        print_error(friendly_error(err))
                        install_requested = False
                    else:
                        gdetails, gerr = fetch_game_details(api_key, gid)
                        gname = ""
                        if not gerr and isinstance(gdetails, dict):
                            name = gdetails.get("name")
                            if isinstance(name, str):
                                gname = name
                        candidates = detect_mod_folders(gname, gid)
                        if not candidates:
                            print_error("Mod folder not found. Install skipped.")
                            install_requested = False
                        else:
                            print("Select install location:")
                            for idx, (label, path) in enumerate(candidates, start=1):
                                print(f"[{idx}] {label} -> {path}")
                            print(f"[{len(candidates)+1}] Skip install")
                            choice = input("Choose a number (or 'q' to cancel): ").strip()
                            if choice.lower() in ("q", "quit", "exit", "back"):
                                print_info("Install skipped.")
                                install_requested = False
                                batch_target = None
                                choice = ""
                            try:
                                num = int(choice)
                            except Exception:
                                num = -1
                            if num == len(candidates) + 1:
                                print_info("Install skipped.")
                                install_requested = False
                            elif 1 <= num <= len(candidates):
                                _label, target = candidates[num - 1]
                                batch_target = target
                            else:
                                print_error("Invalid choice.")
                                install_requested = False
            completed = 0
            for raw_url in urls:
                gs, ms = parse_modio_url(raw_url)
                if not gs or not ms:
                    print_error(f"Invalid URL in batch file: {raw_url}")
                    continue
                print_info(f"Processing: {raw_url}")
                ok, downloaded_path, game_name, game_id, mod_id, _skipped, install_skip = process_single_mod(api_key, gs, ms, install_requested, force_requested, cache)
                if ok and install_requested and batch_target and not install_skip:
                    if install_mod(downloaded_path, batch_target, force=force_requested):
                        if isinstance(cache, dict) and mod_id is not None:
                            cache.setdefault("mods", {})
                            entry = cache["mods"].get(str(mod_id), {})
                            entry["installed_version_id"] = entry.get("latest_version_id")
                            entry["installed_path"] = batch_target
                            cache["mods"][str(mod_id)] = entry
                            save_cache(cache)
                    cleanup_temp_file(downloaded_path)
                if ok:
                    completed += 1
            print_info(f"Batch complete: {completed}/{len(urls)} successful.")
        else:
            ok, downloaded_path, game_name, game_id, mod_id, _skipped, install_skip = process_single_mod(api_key, game_slug, mod_slug, install_requested, force_requested, cache)
            if ok and install_requested and not install_skip:
                candidates = detect_mod_folders(game_name, game_id)
                if not candidates:
                    print_error("Mod folder not found. Install skipped.")
                else:
                    print("Select install location:")
                    for idx, (label, path) in enumerate(candidates, start=1):
                        print(f"[{idx}] {label} -> {path}")
                    print(f"[{len(candidates)+1}] Skip install")
                    choice = input("Choose a number (or 'q' to cancel): ").strip()
                    if choice.lower() in ("q", "quit", "exit", "back"):
                        print_info("Install skipped.")
                        choice = ""
                    try:
                        num = int(choice)
                    except Exception:
                        num = -1
                    if num == len(candidates) + 1:
                        print_info("Install skipped.")
                    elif 1 <= num <= len(candidates):
                        _label, target = candidates[num - 1]
                        if install_mod(downloaded_path, target, force=force_requested):
                            if isinstance(cache, dict) and mod_id is not None:
                                cache.setdefault("mods", {})
                                entry = cache["mods"].get(str(mod_id), {})
                                entry["installed_version_id"] = entry.get("latest_version_id")
                                entry["installed_path"] = target
                                cache["mods"][str(mod_id)] = entry
                                save_cache(cache)
                        cleanup_temp_file(downloaded_path)
                    else:
                        print_error("Invalid choice.")

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
        input("Press Enter to exit...")
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
