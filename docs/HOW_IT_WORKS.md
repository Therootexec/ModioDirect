# How ModioDirect Works

ModioDirect communicates exclusively with the official mod.io API.

## Core Flow
1. **Authentication** – Prompts for API key and validates it via a lightweight API call
2. **URL Parsing** – Extracts game slug and mod slug from a mod.io URL
3. **Game Resolution** – Resolves game slug → game ID
4. **Mod Resolution** – Resolves mod slug → mod ID  
5. **File Selection** – Fetches available mod files and selects the latest version
6. **Download** – Downloads file with retry logic + progress feedback
7. **Metadata** – Saves metadata to `downloads/modinfo.json`

## Install Mode (`--install`)
When `--install` is used:
- Downloads mod to a temporary directory
- Extracts contents
- Copies files to user‑specified mod folder
- Cleans up temporary files

**Note:** Auto‑install is Windows‑only and requires an existing mod folder.  
The tool will never create folders automatically.

## Caching & Version Control
- All downloads logged in `downloads/mod_cache.json`
- Skips re‑downloading if the same version already exists
- Prevents redundant operations

## Error Handling & Safety
- All network requests are wrapped with proper error handling
- No unsafe list indexing
- Input validation prevents crashes from malformed data
- User‑friendly error messages (no stack traces in normal operation)
