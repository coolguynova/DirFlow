import os

# The directory to clean up. "~" automatically points to your home folder.
TRACKED_DIR = os.path.expanduser("~/Downloads")

# Temporary files created by web browsers while a download is active.
# The organizer skips these until the download fully finishes.
TEMP_EXTENSIONS = {'.tmp', '.crdownload', '.part', '.download'}

# Move unmapped extensions here. Set to None to ignore unmapped files.
OTHER_FOLDER = 'Others'

# Enable content-based (hash) duplicate checking on name collision
ENABLE_DEDUPLICATION = True

# Route extensions to their respective folders
EXTENSION_MAP = {
    # Documents
    '.pdf': 'Documents',
    '.docx': 'Documents',
    '.doc': 'Documents',
    '.txt': 'Documents',
    '.xlsx': 'Documents',
    '.pptx': 'Documents',
    
    # Images
    '.png': 'Images',
    '.jpg': 'Images',
    '.jpeg': 'Images',
    '.webp': 'Images',
    '.gif': 'Images',
    '.svg': 'Images',
    
    # Videos
    '.mp4': 'Videos',
    '.mkv': 'Videos',
    '.mov': 'Videos',
    '.avi': 'Videos',
    
    # Audio
    '.mp3': 'Audio',
    '.wav': 'Audio',
    '.flac': 'Audio',
    
    # Archives & Installers
    '.zip': 'Archives',
    '.tar': 'Archives',
    '.gz': 'Archives',
    '.rar': 'Archives',
    '.7z': 'Archives',
    '.exe': 'Installers',
    '.msi': 'Installers',
    '.dmg': 'Installers',
}