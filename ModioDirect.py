#!/usr/bin/env python3
# ModioDirect by TheRootExec
# Direct Downloader for mod.io (official API only)

import json
import os
import re
import sys
import time
from urllib.parse import urlparse, unquote

# Optional tqdm
try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None

# Required requests
try:
    import requests  # type: ignore
except Exception:
    requests = None


API_BASE = "https://api.mod.io/v1"
CONFIG_NAME = "config.json"
USER_AGENT = "ModioDirect/1.1 (TheRootExec)"
DOWNLOAD_DIR = "downloads"
URL_REGEX = re.compile(
    r"^https?://(?:www\.)?mod\.io/g/([^/]+)/m/([^/?#]+)",
    re.IGNORECASE,
)


def print_error(msg):
    print(f"[Error] {msg}")


def print_info(msg):
    print(f"[Info] {msg}")


def print_banner():
    print(r" __  __           _ _       _____  _               _   ")
    print(r"|  \/  | ___   __| (_) ___ |  __ \(_)_ __ ___  ___| |_ ")
    print(r"| |\/| |/ _ \ / _` | |/ _ \| |  | | | '__/ _ \/ __| __|")
    print(r"| |  | | (_) | (_| | | (_) | |__| | | | |  __/ (__| |_ ")
    print(r"|_|  |_|\___/ \__,_|_|\___/|_____/|_|_|  \___|\___|\__|")
    print("\n             ModioDirect Downloader Tool")
    print("                     by TheRootExec")
    print("-------------------------------------------------------")


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
    except Exception as exc:
        print_error(f"Network error: {exc}")
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
    # Test API key by listing 1 game
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
        api_key = ""  # force re-prompt


def prompt_mod_url():
    while True:
        url = input("Enter mod.io mod URL: ").strip()
        if not url:
            print_error("URL cannot be empty.")
            continue
        match = URL_REGEX.search(url)
        if not match:
            print_error("Invalid mod.io URL. Expected: https://mod.io/g/<game_slug>/m/<mod_slug>")
            continue
        game_slug = match.group(1).strip()
        mod_slug = match.group(2).strip()
        if not game_slug or not mod_slug:
            print_error("Could not parse game_slug or mod_slug from URL.")
            continue
        return game_slug, mod_slug


def resolve_game_id(api_key, game_slug):
    url = f"{API_BASE}/games"
    # Filtering uses direct field parameters, e.g. name_id=<slug>
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
        # Fallback: search and match by name_id/slug
        fallback_id, fallback_err = fallback_search_game_id(api_key, game_slug)
        if fallback_id is not None:
            return fallback_id, None
        return None, fallback_err or "Game not found for provided game_slug."
    # Never index without length check:
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
    # _q is the documented full-text search parameter
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
    # Filtering uses direct field parameters, e.g. name_id=<slug>
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
        # Some API keys are restricted; try global mods endpoint as fallback
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
        # Fallback: search and match by name_id/slug
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
        # Try a global search by query and filter client-side
        search_id, search_err = resolve_mod_id_global_search(api_key, game_id, mod_slug)
        if search_id is not None:
            return search_id, None
        # If mod_slug is numeric, try direct mod lookup
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
        # Ensure game_id matches
        item_game_id = item.get("game_id")
        if isinstance(item_game_id, int) and item_game_id != game_id:
            continue
        if match_slug(item, mod_slug):
            mod_id = item.get("id")
            if isinstance(mod_id, int):
                return mod_id, None
    return None, "Mod not found for provided mod_slug."


def resolve_mod_id_numeric(api_key, game_id, mod_slug):
    # If the slug is numeric, try direct mod ID
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
    # _q is the documented full-text search parameter
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
    # Fix escaped slashes
    binary_url = binary_url.replace("\\/", "/")
    # Determine filename
    filename = file_obj.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        # Try from URL
        try:
            parsed = urlparse(binary_url)
            path = parsed.path or ""
            basename = os.path.basename(path)
            filename = unquote(basename) if basename else "modfile.bin"
        except Exception:
            filename = "modfile.bin"
    return binary_url, filename


def download_file(url, filename):
    headers = {"User-Agent": USER_AGENT}
    # Attempt twice max
    for attempt in range(1, 3):
        resp = safe_request("GET", url, headers=headers, stream=True, timeout=30)
        if resp is None:
            print_error("Download failed due to network error.")
            if attempt == 2:
                return False
            time.sleep(1)
            continue
        if resp.status_code == 429:
            print_error("Rate limited (429) during download.")
            if attempt == 2:
                return False
            time.sleep(2)
            continue
        if resp.status_code >= 400:
            print_error(f"Download failed with status {resp.status_code}.")
            if attempt == 2:
                return False
            time.sleep(1)
            continue

        total = resp.headers.get("Content-Length")
        try:
            total_bytes = int(total) if total is not None else None
        except Exception:
            total_bytes = None

        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            filename = os.path.join(DOWNLOAD_DIR, filename)
            with open(filename, "wb") as f:
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
            return True
        except Exception as exc:
            print_error(f"Failed to write file: {exc}")
            if attempt == 2:
                return False
            time.sleep(1)
    return False


def main():
    print_banner()
    if requests is None:
        print_error("The 'requests' library is required. Install it with: pip install requests")
        return

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME)
    use_config = "--no-config" not in sys.argv
    api_key = prompt_api_key(config_path, use_config)

    while True:
        game_slug, mod_slug = prompt_mod_url()

        game_id, err = resolve_game_id(api_key, game_slug)
        if err:
            print_error(err)
            continue
        game_details, gerr = fetch_game_details(api_key, game_id)
        if gerr:
            print_error(gerr)
            continue
        # Surface the resolved game name early
        game_name = ""
        if isinstance(game_details, dict):
            name = game_details.get("name")
            if isinstance(name, str):
                game_name = name
        if game_name:
            print_info(f"Game : {game_name}")

        mod_id, err = resolve_mod_id(api_key, game_id, mod_slug)
        if err:
            print_error(err)
            continue
        mod_details, merr = fetch_mod_details(api_key, game_id, mod_id)
        if merr:
            print_error(merr)
            continue

        mod_name = ""
        if isinstance(mod_details, dict):
            name = mod_details.get("name")
            if isinstance(name, str):
                mod_name = name

        if mod_name:
            print_info(f"Mod  : {mod_name}")

        files, err = fetch_mod_files(api_key, game_id, mod_id)
        if err:
            print_error(err)
            continue

        latest_file = select_latest_file(files)
        if latest_file is None:
            print_error("Could not determine latest mod file.")
            continue

        binary_url, filename = extract_download_info(latest_file)
        if not binary_url:
            print_error("No valid download URL found in mod file.")
            continue

        print_info(f"Latest file: {filename}")
        ok = download_file(binary_url, filename)
        if ok:
            print_info(f"Saved as: {filename}")
            # Optional JSON export
            try:
                os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                info_path = os.path.join(DOWNLOAD_DIR, "modinfo.json")
                info = {
                    "game_name": game_name,
                    "mod_name": mod_name,
                    "mod_id": mod_id,
                    "file_id": latest_file.get("id") if isinstance(latest_file, dict) else None,
                    "date_downloaded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                with open(info_path, "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=2)
            except Exception as exc:
                print_error(f"Failed to write modinfo.json: {exc}")
        else:
            print_error("Download failed after retry.")

        # Ask if user wants another
        again = input("Download another mod? (y/n): ").strip().lower()
        if again != "y":
            print_info("Exiting.")
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("Interrupted by user.")
    except Exception as exc:
        print_error(f"Unexpected error: {exc}")

"""
Simulated full run (example):

ModioDirect - mod.io downloader
Enter your mod.io API key: 12345INVALID
[Error] Invalid API key (401 Unauthorized).
Enter your mod.io API key: 67890VALID
[Info] API key validated.
Enter mod.io mod URL: https://mod.io/g/spaceengineers/m/assault-weapons-pack1
[Info] Game : Space Engineers
[Info] Mod  : Assault Weapons Pack
[Info] Latest file: assault_weapons_pack1.zip
Downloading... 5%
Downloading... 10%
...
Downloading... 100%
[Info] Saved as: assault_weapons_pack1.zip
Download another mod? (y/n): n
[Info] Exiting.

"""

