# How ModioDirect Works

ModioDirect uses only the official mod.io REST API and never scrapes pages.

Flow:
1. Ask for API key and validate it with a lightweight API call.
2. Parse a mod.io URL to extract the game slug and mod slug.
3. Resolve the game slug to a game ID.
4. Resolve the mod slug to a mod ID within that game.
5. Fetch mod files and select the newest one by date_added.
6. Download the file with a safe, retrying stream.
7. Save optional metadata to downloads/modinfo.json.

Safety guarantees:
- All network calls are wrapped in try/except.
- No list indexing without length checks.
- Invalid inputs re-prompt instead of crashing.
