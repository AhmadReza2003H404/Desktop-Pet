"""Where things live on each OS."""

import os
import sys
from pathlib import Path

WINDOWS = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")


def config_dir() -> Path:
    """Saved pets and settings: %APPDATA%\\DesktopPets or ~/.config/desktop-pets."""
    if WINDOWS:
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "DesktopPets"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "desktop-pets"


def cache_dir() -> Path:
    """Generated files (sounds): %LOCALAPPDATA%\\DesktopPets or ~/.cache/desktop-pets."""
    if WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "DesktopPets"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "desktop-pets"
