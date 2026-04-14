# ModioDirect 🚀

<p align="center">
  <img src="https://raw.githubusercontent.com/Therootexec/ModioDirect/main/assets/ModioDirectLogo1024x1024.png" width="200" alt="ModioDirect Logo">
</p>

<p align="center">
  <a href="https://pypi.org/project/modiodirect/"><img src="https://img.shields.io/pypi/v/modiodirect?style=flat-square" alt="PyPI version"></a>
  <a href="https://github.com/Therootexec/ModioDirect/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Therootexec/ModioDirect?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/github/stars/Therootexec/ModioDirect?style=flat-square" alt="Stars">
</p>

---

**ModioDirect** is a lightweight, single-file CLI tool that reliably downloads mods directly from [mod.io](https://mod.io) via the official API. It is designed to be safe, fast, and transparent—allowing you to bypass official game clients when necessary.

It is perfect for games like **Space Engineers**, **SnowRunner**, **Deep Rock Galactic**, and more.

## ✨ Features

- **Official API**: Uses only the official mod.io API for security and stability.
- **Smart Resolution**: Accepts standard mod.io URLs and handles slug-to-ID resolution automatically.
- **Reliable Downloads**: Built-in automatic retries and an optional progress bar (via `tqdm`).
- **Privacy Focused**: No config mode (`--no-config`) for shared or temporary environments.
- **Batch Processing**: Download multiple mods at once using a text file list.
- **Windows Integration**: Optional auto-install feature for detected game folders.

## 📦 Installation

Install ModioDirect directly from PyPI using pip:

```bash
pip install modiodirect
🚀 Quick Start
Once installed, you can launch the interactive CLI by simply typing:

Bash
modiodirect
Basic Usage
Add your API Key: You will be prompted to enter your mod.io API key.

Paste URL: Paste a mod URL (e.g., https://mod.io/g/GAME/m/example-mod).

Download: The tool handles the rest!

Advanced Commands
No Configuration: Avoid saving your API key to config.json.

Bash
modiodirect --no-config
Auto-Install (Windows): Scan and install directly to game folders.

Bash
modiodirect <mod_url> --install
Batch Mode: To download multiple mods, create a .txt file with one URL per line and enter the following in the app:

Plaintext
file:C:\path\to\mods.txt
🛠 Requirements
Python 3.9+

requests

tqdm (for progress bars)

⚠️ Important Notices
Security
Your mod.io API key is private. Never share it publicly. ModioDirect stores your key locally and only uses it to communicate directly with the official mod.io servers.

Access Limitations
Some games or mods are private, unlisted, or require OAuth authentication.

If you receive a 404 Error or an "Inaccessible" message, it is likely an access restriction on the mod.io side.

ModioDirect currently uses API Key authentication. OAuth-only mods (private mods) are not yet supported.

⚖️ Legal
This tool is not affiliated with, endorsed by, or officially supported by mod.io. Users are responsible for complying with the mod.io Terms of Service.