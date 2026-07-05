```text
  ___  _      ___ _
 |   \(_)_ _ | __| |___ _ __
 | |) | | '_|| _|| / _ \ V  V /
 |___/|_|_|  |_| |_\___/\_/\_/
```

# DirFlow

A lightweight, real-time background file sorter for Linux, macOS, and Windows. It monitors a directory (such as `~/Downloads`) and automatically organizes incoming files into subfolders based on extension.

## Features

- **Low Overhead**: Runs as a background daemon consuming <15MB RAM. Processes tasks sequentially using a queue to keep directory monitoring non-blocking.
- **TUI Dashboard**: Renders a live terminal dashboard showing uptime, queue sizes, and file actions. Falls back to standard logging when running in the background (e.g. systemd).
- **Collision Deduplication**: Performs SHA-256 hash checks during filename collisions, removing exact duplicates instead of creating redundant files (like `file_(1).ext`).
- **Write-Lock Aware**: Uses system-level locks (`fcntl` on Unix, exclusive sharing checks on Windows) combined with size checks to ensure downloads are complete before moving them.
- **Cross-Platform**: Automated setup scripts configure and launch background agents on Linux, macOS, and Windows natively.

## Installation

### System-Wide
```bash
pip install .
```
This registers the global `dirflow` CLI command.

### Manual Run / Development
```bash
git clone https://github.com/coolguynova/DirFlow.git
cd DirFlow
pip install -r requirements.txt
```

## Usage

```bash
# Start the daemon
dirflow

# Monitor a custom directory
dirflow --dir ~/Desktop

# Run a single folder sweep and exit
dirflow --once

# Print configuration rules
dirflow --rules

# Run a simulation without moving files
dirflow --dry-run
```

## Background Deployment

You can configure DirFlow to run automatically on system boot or user login.

### Linux & macOS
Run the Unix setup script:
```bash
./install.sh
```
* **Linux**: Sets up a `systemd` user service (`dirflow.service`).
* **macOS**: Sets up a `launchd` LaunchAgent (`com.dirflow.daemon`).

### Windows
Run the PowerShell setup script:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
* This registers a shortcut in the Windows Startup Folder running DirFlow windowless via `pythonw.exe`.

## License
MIT. See [LICENSE](LICENSE) for details.
