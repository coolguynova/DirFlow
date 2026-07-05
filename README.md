```text
  ___  _      ___ _
 |   \(_)_ _ | __| |___ _ __
 | |) | | '_|| _|| / _ \ V  V /
 |___/|_|_|  |_| |_\___/\_/\_/
```

# DirFlow

A lightweight, real-time background file organization daemon for Linux, macOS, and Windows. It monitors your specified directories (like `~/Downloads`), detects new file additions or modifications, and routes them to structured directories based on their file extensions.

## Features

- **Real-Time Directory Monitoring**: Uses `watchdog` to respond to filesystem changes instantly.
- **Ultra-Low Memory Footprint**: 
  - Offloads tasks to a standard `queue.Queue` worker thread.
  - Hashing is performed *only* on file name collisions.
  - Reads files in tiny 64KB chunks to keep memory usage under 20MB.
- **Live Terminal TUI Dashboard**: Automatically renders a live dashboard showing system status, file stats, and activity feed with colored badges when run interactively. Falls back to plain logs when run as a background service.
- **Strict PEP-484 Typing**: Fully type-annotated code structure for robustness.
- **Smart Duplicate Prevention**: Computes SHA-256 content hashes when naming collisions occur. If content matches exactly, it cleans up the redundant file instead of creating renaming duplicates (e.g. `file_(1).ext`).
- **Unmapped Extensions Routing**: Routes files with unrecognized extensions to a fallback `Others/` folder rather than ignoring them.
- **Robust Error Handling**: Automatically retries locked or busy files (e.g., active browser writes) with backoff.
- **CLI Options**: Supports targeting custom directories and dry-run execution modes.
- **Multi-Platform Daemon Support**: Easy deployment as a background service on Linux, macOS, and Windows.

---

## Installation

### Option A: Install System-Wide (Recommended)
You can install DirFlow system-wide using `pip` from the repository root:
```bash
pip install .
```
This registers the command `dirflow` system-wide.

### Option B: Development/Manual Run
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/dirflow.git
   cd dirflow
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Custom options can be configured directly inside `config.py`:
- `TRACKED_DIR`: The default directory to monitor (e.g. `~/Downloads`).
- `TEMP_EXTENSIONS`: File extensions to skip temporarily (e.g. active web browser downloads like `.crdownload` or `.part`).
- `OTHER_FOLDER`: The folder name where files with unmapped extensions are routed (e.g. `Others`). Set to `None` to ignore unmapped files instead.
- `ENABLE_DEDUPLICATION`: Set to `True` to enable content-based hash comparisons on name collision.
- `EXTENSION_MAP`: A dictionary mapping extensions (e.g., `.pdf`, `.mp4`) to target category folders.

---

## Usage

If installed system-wide:
```bash
dirflow
```

Otherwise, run directly:
```bash
python organizer.py
```

### Interactive TUI Dashboard:
When launched in an interactive terminal, the daemon presents a visual live dashboard detailing active monitoring states, queues, stats, and a scrolling window of the last 6 actions.

### Command Line Arguments:
* `--dir <path>`: Override the default tracked directory.
  ```bash
  python organizer.py --dir ~/Desktop
  ```
* `--dry-run`: View planned operations without modifying or moving any files (automatically falls back to plain log lines).
  ```bash
  python organizer.py --dry-run
  ```
* `--once`: Run a single folder sweep and exit immediately instead of starting the daemon.
  ```bash
  python organizer.py --once
  ```
* `--rules`: Print the current extension mapping rules and active configuration, then exit.
  ```bash
  python organizer.py --rules
  ```

---

## Running Tests

Execute the unit tests using Python's built-in testing framework:
```bash
python3 -m unittest discover tests/
```

---

## Deploy as a Background Daemon (Linux, macOS, & Windows)

You can run DirFlow continuously in the background. Automated installation scripts are provided to configure the path mappings dynamically and run the organizer on system startup or login.

### Linux (Systemd) & macOS (Launchd)
Run the Unix installer script from the terminal:
```bash
./install.sh
```
* **On Linux**: Registers and starts a background `systemd` user service (`dirflow.service`).
* **On macOS**: Registers and starts a background `launchd` LaunchAgent daemon (`com.dirflow.daemon`).

### Windows (Startup Shortcut)
Run the PowerShell installer script:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
* **On Windows**: Configures a shortcut in your **Windows Startup Folder** to run the organizer silently via `pythonw.exe` (windowless background Python execution).

---

## Managing the Service

### Linux (Systemd):
* **Status**: `systemctl --user status dirflow.service`
* **Stop**: `systemctl --user stop dirflow.service`

### macOS (Launchd):
* **Stop**: `launchctl unload ~/Library/LaunchAgents/com.dirflow.daemon.plist`
* **Start**: `launchctl load -w ~/Library/LaunchAgents/com.dirflow.daemon.plist`

### Windows (Startup):
* **Stop**: Stop `pythonw` from Windows Task Manager or run `Stop-Process -Name 'pythonw'` in PowerShell.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
