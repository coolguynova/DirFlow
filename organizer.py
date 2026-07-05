# ​‌​​​‌​​​‌‌​​‌​‌​‌‌‌​‌‌​​‌‌​​‌​‌​‌‌​‌‌​​​‌‌​‌‌‌‌​‌‌‌​​​​​‌‌​​‌​‌​‌‌​​‌​​​​‌​​​​​​‌‌​​​‌​​‌‌‌‌​​‌​​‌​​​​​​‌​​‌‌‌​​‌‌​‌‌‌‌​‌‌‌​‌‌​​‌‌​​​​‌​​‌​​​​​​​‌​‌‌​‌​​‌​​​​​​‌​​​‌​​​‌‌​‌​​‌​‌‌‌​​‌​​‌​​​‌‌​​‌‌​‌‌​​​‌‌​‌‌‌‌​‌‌‌​‌‌‌
import os
import sys
import time
import shutil
import logging
import hashlib
import argparse
import queue
import threading
import collections
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Dict, Tuple, Deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import custom configurations
import config

# Global variables for TUI and stats tracking
start_time: float = time.time()
total_moved: int = 0
total_duplicates: int = 0
recent_actions: Deque[str] = collections.deque(maxlen=6)
is_tui_active: bool = False
spinner_idx: int = 0
spinner_chars: List[str] = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

class ColorFormatter(logging.Formatter):
    """Custom logging formatter that adds ANSI colors for console stream handlers."""
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    
    FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + FORMAT + RESET,
        logging.INFO: GREEN + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

class TuiLogHandler(logging.Handler):
    """Redirects logs directly into the TUI activity deque with colored badges instead of printing."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            clean_msg = record.getMessage()
            timestamp = datetime.now().strftime('%H:%M:%S')

            # Truncate message to prevent TUI box overflow
            max_msg_len = 40
            if len(clean_msg) > max_msg_len:
                clean_msg = clean_msg[:max_msg_len - 3] + "..."

            # Prepend a colored badge based on log content
            if "Successfully moved:" in clean_msg:
                badge = "\033[1;32m[MOVE]\033[0m"
            elif "Duplicate content" in clean_msg:
                badge = "\033[1;33m[DUPE]\033[0m"
            elif "Failed to move" in clean_msg or "error" in clean_msg.lower():
                badge = "\033[1;31m[FAIL]\033[0m"
            else:
                badge = "\033[1;34m[INFO]\033[0m"

            recent_actions.append(f"{timestamp} {badge} {clean_msg}")
        except Exception:
            self.handleError(record)

# Global variables for CLI options
DRY_RUN: bool = False
TRACKED_DIR: str = config.TRACKED_DIR

# Thread-safe queue for file processing tasks
processing_queue: queue.Queue = queue.Queue()

def is_file_locked(file_path: str) -> bool:
    """Checks if a file is currently locked/written to by another process.
    Handles read-only permissions and Windows sharing violations safely.
    """
    if os.name == 'nt':
        try:
            with open(file_path, 'ab'):
                pass
            return False
        except OSError as e:
            if getattr(e, 'winerror', 0) == 32:
                return True
            return False
    else:
        try:
            import fcntl
            with open(file_path, 'rb') as f:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
            return False
        except ImportError:
            return False
        except (IOError, OSError):
            return True

def get_file_hash(file_path: str) -> Optional[str]:
    """Calculates SHA-256 hash of a file in small chunks to keep RAM usage extremely low (<1MB)."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logging.error(f"Failed to calculate hash for {file_path}: {e}")
        return None

class FileSorterEngine:
    @staticmethod
    def get_safe_destination(target_folder: str, filename: str) -> str:
        """Prevents duplicate files from overwriting each other."""
        base, extension = os.path.splitext(filename)
        counter = 1
        destination_path = os.path.join(target_folder, filename)
        
        while os.path.exists(destination_path):
            new_filename = f"{base}_({counter}){extension}"
            destination_path = os.path.join(target_folder, new_filename)
            counter += 1
            
        return destination_path

    @staticmethod
    def is_file_ready(file_path: str) -> bool:
        """Ensures file size is stable and it is not locked before moving."""
        try:
            if not os.path.exists(file_path):
                return False
            
            if is_file_locked(file_path):
                return False

            initial_size = os.path.getsize(file_path)
            time.sleep(1.2)  
            
            if not os.path.exists(file_path):
                return False
                
            current_size = os.path.getsize(file_path)
            return initial_size == current_size and initial_size > 0
        except (FileNotFoundError, PermissionError):
            return False

    @classmethod
    def process_file(cls, file_path: str) -> None:
        global total_moved, total_duplicates

        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return

        filename = os.path.basename(file_path)
        
        # Skip hidden files
        if filename.startswith('.'):
            return

        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        # Ignore active web download cache files
        if ext in config.TEMP_EXTENSIONS:
            return

        # Determine target folder
        target_subfolder: Optional[str] = None
        if ext in config.EXTENSION_MAP:
            target_subfolder = config.EXTENSION_MAP[ext]
        elif config.OTHER_FOLDER:
            target_subfolder = config.OTHER_FOLDER

        if not target_subfolder:
            return

        target_folder = os.path.join(TRACKED_DIR, target_subfolder)

        if not cls.is_file_ready(file_path):
            return

        # Check if target already exists and match hash
        destination = os.path.join(target_folder, filename)
        
        if os.path.exists(destination) and config.ENABLE_DEDUPLICATION:
            src_hash = get_file_hash(file_path)
            dest_hash = get_file_hash(destination)
            if src_hash and dest_hash and src_hash == dest_hash:
                logging.info(f"Duplicate content detected for {filename}. Cleaned up source file.")
                total_duplicates += 1
                if not DRY_RUN:
                    try:
                        os.remove(file_path)
                    except (FileNotFoundError, PermissionError) as e:
                        logging.error(f"Failed to delete duplicate source {filename}: {e}")
                return

        # Get unique destination path if it still conflicts
        destination = cls.get_safe_destination(target_folder, filename)

        if DRY_RUN:
            logging.info(f"[DRY-RUN] Would move: {filename} -> {os.path.basename(target_folder)}/")
            return

        # Create target directory
        os.makedirs(target_folder, exist_ok=True)

        # Retry loop for locked or busy files
        retries = 3
        for attempt in range(retries):
            try:
                shutil.move(file_path, destination)
                logging.info(f"Successfully moved: {filename} -> {os.path.basename(target_folder)}/")
                total_moved += 1
                break
            except (PermissionError, FileNotFoundError) as error:
                if attempt < retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed to move {filename} (file locked/missing). Retrying...")
                    time.sleep(2.5)
                else:
                    logging.error(f"Failed to move {filename} after {retries} attempts: {error}")
            except OSError as error:
                logging.error(f"OS error moving {filename}: {error}")
                break

def queue_worker() -> None:
    """Background worker thread processing filesystem events sequentially without blocking watchdog."""
    while True:
        file_path = processing_queue.get()
        if file_path is None:
            break
        try:
            FileSorterEngine.process_file(file_path)
        except Exception as e:
            logging.error(f"Worker encountered error processing {file_path}: {e}")
        finally:
            processing_queue.task_done()

class DownloadFolderHandler(FileSystemEventHandler):
    """Listens to active file modifications in real-time and enqueues tasks."""
    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        processing_queue.put(event.src_path)

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        processing_queue.put(event.src_path)

def run_initial_sweep() -> None:
    """Cleans up preexisting files inside the folder right at startup."""
    logging.info(f"Starting initial folder sweep on: {TRACKED_DIR}")
    try:
        for entry in os.scandir(TRACKED_DIR):
            if entry.is_file():
                processing_queue.put(entry.path)
    except Exception as e:
        logging.error(f"Error during initial folder sweep: {e}")

def print_rules() -> None:
    """Prints a beautiful summary of the configured routing rules."""
    print("\n\033[1;36m", end="")
    print(r"""
  ___  _      ___ _
 |   \(_)_ _ | __| |___ _ __
 | |) | | '_|| _|| / _ \ V  V /
 |___/|_|_|  |_| |_\___/\_/\_/ 
                               """)
    print("\033[0m", end="")
    print("\033[1m=== Active Configurations ===\033[0m")
    print(f"\033[1mDefault Monitored Folder:\033[0m {config.TRACKED_DIR}")
    print(f"\033[1mFallback Folder:\033[0m         {config.OTHER_FOLDER or 'None (Ignore unmapped)'}")
    print(f"\033[1mDeduplication (SHA-256):\033[0m {'Enabled' if config.ENABLE_DEDUPLICATION else 'Disabled'}")
    print("\n\033[1mExtension Routing Rules:\033[0m")
    print(f"{'Extension':<15} | {'Destination Folder':<25}")
    print("-" * 43)
    
    sorted_rules = sorted(config.EXTENSION_MAP.items(), key=lambda item: (item[1], item[0]))
    for ext, folder in sorted_rules:
        print(f"  {ext:<13} | {folder:<25}")
    print()

def strip_ansi(s: str) -> str:
    """Removes ANSI escape codes from a string to calculate its printable width."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\033\[[0-9;]*[a-zA-Z]', '', s)

def format_feed_line(line: str, width: int = 56) -> str:
    """Safely pads or truncates activity feed lines containing ANSI escape sequences."""
    plain = strip_ansi(line)
    visible_len = len(plain)
    if visible_len >= width:
        return line
    return line + (" " * (width - visible_len))

def draw_tui() -> None:
    """Draws a live updating terminal dashboard with stats, activity, and uptime."""
    global spinner_idx
    
    uptime_secs = int(time.time() - start_time)
    hrs, remainder = divmod(uptime_secs, 3600)
    mins, secs = divmod(remainder, 60)
    uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
    
    # ANSI escape characters
    clear_screen = "\033[H\033[J"
    cyan = "\033[1;36m"
    yellow = "\033[1;33m"
    green = "\033[1;32m"
    bold = "\033[1m"
    reset = "\033[0m"

    # Select spinner or active green dot depending on queue status
    q_size = processing_queue.qsize()
    if q_size > 0:
        status_icon = f"{yellow}{spinner_chars[spinner_idx]}{reset}"
        status_text = f"Processing Queue ({q_size} files remaining)"
        spinner_idx = (spinner_idx + 1) % len(spinner_chars)
    else:
        status_icon = f"{green}●{reset}"
        status_text = "Idle (Monitoring Directory)"

    # Truncate tracked directory if it exceeds dashboard boundaries
    max_dir_len = 45
    truncated_dir = TRACKED_DIR
    if len(TRACKED_DIR) > max_dir_len:
        truncated_dir = "..." + TRACKED_DIR[-(max_dir_len-3):]

    sys.stdout.write(clear_screen)
    print(f"{cyan}" + r"""  ___  _      ___ _
 |   \(_)_ _ | __| |___ _ __
 | |) | | '_|| _|| / _ \ V  V /
 |___/|_|_|  |_| |_\___/\_/\_/ 
                               """ + f"{reset}")
    
    # Render Dashboard Panel (Internal printable width: exactly 58 characters)
    # Left border: "│ " (2 chars)
    # Right border: " │" (2 chars)
    print(f"{cyan}┌────────────────────────────────────────────────────────────┐{reset}")
    print(f"{cyan}│ {bold}SYSTEM STATUS:{reset}                                            {cyan} │{reset}")
    print(f"{cyan}│ {reset}Engine:      {status_icon} {status_text:<43} {cyan}│{reset}")
    print(f"{cyan}│ {reset}Tracked Dir: {bold}{truncated_dir:<45}{reset}{cyan} │{reset}")
    print(f"{cyan}│ {reset}Uptime:      {bold}{uptime_str:<12}{reset}  Queue Size: {yellow}{q_size:<19}{reset}{cyan} │{reset}")
    print(f"{cyan}├────────────────────────────────────────────────────────────┤{reset}")
    print(f"{cyan}│ {bold}STATISTICS:{reset}                                               {cyan} │{reset}")
    print(f"{cyan}│ {reset}Files Organized:    {green}{total_moved:<10}{reset}  Duplicates Cleaned: {yellow}{total_duplicates:<6}{reset}{cyan} │{reset}")
    print(f"{cyan}├────────────────────────────────────────────────────────────┤{reset}")
    print(f"{cyan}│ {bold}RECENT ACTIVITY FEED:{reset}                                     {cyan} │{reset}")
    
    # Print the last 6 actions or empty padding lines
    feed = list(recent_actions)
    for i in range(6):
        if i < len(feed):
            line = feed[i]
            print(f"{cyan}│ {reset}▸ {format_feed_line(line, width=56)}{cyan} │{reset}")
        else:
            print(f"{cyan}│                                                            │{reset}")
            
    print(f"{cyan}└────────────────────────────────────────────────────────────┘{reset}")
    print("Press Ctrl+C to stop the monitoring daemon.")

def main() -> None:
    global DRY_RUN, TRACKED_DIR, is_tui_active

    # Windows ANSI Terminal Color support activation
    if os.name == 'nt':
        os.system('')

    parser = argparse.ArgumentParser(description="DirFlow: Lightweight real-time file organizer daemon.")
    parser.add_argument('--dir', type=str, default=config.TRACKED_DIR, help="Directory to monitor and organize.")
    parser.add_argument('--dry-run', action='store_true', help="Log actions without modifying any files.")
    parser.add_argument('--once', action='store_true', help="Run a single folder sweep and exit immediately.")
    parser.add_argument('--rules', action='store_true', help="Print current extension mapping rules and exit.")
    args = parser.parse_args()

    if args.rules:
        print_rules()
        sys.exit(0)

    DRY_RUN = args.dry_run
    TRACKED_DIR = os.path.abspath(os.path.expanduser(args.dir))

    if not os.path.exists(TRACKED_DIR):
        print(f"Target directory does not exist: {TRACKED_DIR}", file=sys.stderr)
        sys.exit(1)

    # Determine logging strategy:
    is_tui_active = sys.stdout.isatty() and not args.once and not args.dry_run

    root_logger = logging.getLogger()
    
    # Enable RotatingFileHandler: 5MB maximum log file size with 3 backups
    log_file_path = os.path.join(os.path.dirname(__file__), "file-organizer.log")
    file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    if is_tui_active:
        tui_handler = TuiLogHandler()
        root_logger.addHandler(tui_handler)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter())
        root_logger.addHandler(console_handler)

    # Start the lightweight processing queue worker thread
    worker_thread = threading.Thread(target=queue_worker, daemon=True)
    worker_thread.start()

    run_initial_sweep()

    if args.once:
        processing_queue.join()
        processing_queue.put(None)
        worker_thread.join()
        logging.info("One-time sweep completed successfully. Exiting.")
        sys.exit(0)

    event_handler = DownloadFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, path=TRACKED_DIR, recursive=False)
    
    logging.info(f"Background monitoring engine online for: {TRACKED_DIR} (Dry-run: {DRY_RUN})")
    observer.start()
    
    try:
        while True:
            # Active self-monitoring: terminate daemon if any subthread crashes
            if not observer.is_alive():
                logging.critical("Watchdog observer thread crashed. Terminating daemon.")
                sys.exit(1)
            if not worker_thread.is_alive():
                logging.critical("Worker queue thread crashed. Terminating daemon.")
                sys.exit(1)

            if is_tui_active:
                draw_tui()
            time.sleep(0.3)  # Decreased wait to speed up spinner animation
    except KeyboardInterrupt:
        if is_tui_active:
            # Clear terminal on exit
            sys.stdout.write("\033[H\033[J")
        logging.info("Shutting down file organizer daemon...")
        observer.stop()
    
    observer.join()
    
    # Clean shutdown of worker thread
    processing_queue.put(None)
    worker_thread.join()

if __name__ == "__main__":
    main()
