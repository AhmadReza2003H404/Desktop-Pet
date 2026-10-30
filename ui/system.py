"""Desktop integration: app-menu launcher, start at login, idle time, single instance.

Linux: a .desktop file in the app grid, ~/.config/autostart, GNOME's idle monitor.
Windows: a Start Menu shortcut, the HKCU "Run" registry key, GetLastInputInfo.
"""

import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from core.paths import WINDOWS, config_dir
from core.pet import Pet, PetView, State

PROJECT = Path(__file__).resolve().parent.parent
MAIN = PROJECT / "main.py"
SOCKET_NAME = "desktop-pets-" + re.sub(r"\W+", "_", getpass.getuser())

if WINDOWS:
    START_MENU = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / \
        "Microsoft" / "Windows" / "Start Menu" / "Programs"
    LAUNCHER = START_MENU / "Desktop Pets.lnk"
    ICON = config_dir() / "desktop-pets.ico"
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    RUN_VALUE = "DesktopPets"
else:
    DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    LAUNCHER = DATA / "applications" / "desktop-pets.desktop"
    ICON = DATA / "icons" / "hicolor" / "256x256" / "apps" / "desktop-pets.png"
    AUTOSTART = CONFIG / "autostart" / "desktop-pets.desktop"


def _python() -> Path:
    """On Windows, pythonw.exe runs without a console window popping up."""
    exe = Path(sys.executable)
    if WINDOWS and exe.name.lower() == "python.exe" and exe.with_name("pythonw.exe").exists():
        return exe.with_name("pythonw.exe")
    return exe


def _command() -> str:
    return f'"{_python()}" "{MAIN}"'


def _write_icon(pet: Pet):
    ICON.parent.mkdir(parents=True, exist_ok=True)
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.scale(256 / pet.width, 256 / pet.height)
    pet.draw(p, PetView(State.SIT, 0, 0, 1, 0, (0.2, 0.3), 0, False))
    p.end()
    pixmap.save(str(ICON), "ICO" if WINDOWS else "PNG")


# --- Linux ------------------------------------------------------------------

def _desktop_entry() -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Desktop Pets",
        "Comment=Little pets that live on your screen",
        f"Exec={_command()}",
        f"Path={PROJECT}",
        "Icon=desktop-pets",
        "Terminal=false",
        "Categories=Game;Amusement;",
        "StartupNotify=false",
        "",
    ])


# --- Windows ----------------------------------------------------------------

def _ps_quote(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _windows_shortcut(path: Path):
    """Make a .lnk through PowerShell's WScript.Shell (no extra Python packages needed)."""
    quoted_main = '"' + str(MAIN) + '"'
    script = "; ".join([
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({_ps_quote(path)})",
        f"$s.TargetPath = {_ps_quote(_python())}",
        f"$s.Arguments = {_ps_quote(quoted_main)}",
        f"$s.WorkingDirectory = {_ps_quote(PROJECT)}",
        f"$s.IconLocation = {_ps_quote(ICON)}",
        "$s.Description = 'Little pets that live on your screen'",
        "$s.Save()",
    ])
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# --- both -------------------------------------------------------------------

def launcher_installed() -> bool:
    return LAUNCHER.exists()


def install_launcher(pet: Pet):
    """Add "Desktop Pets" to the Start Menu (Windows) or the app grid (Linux)."""
    _write_icon(pet)
    LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        _windows_shortcut(LAUNCHER)
    else:
        LAUNCHER.write_text(_desktop_entry(), encoding="utf-8")


def autostart_enabled() -> bool:
    if WINDOWS:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, RUN_VALUE)
            return True
        except OSError:
            return False
    return AUTOSTART.exists()


def set_autostart(on: bool):
    if WINDOWS:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except OSError:
                    pass
        return
    if on:
        AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
        AUTOSTART.write_text(_desktop_entry(), encoding="utf-8")
    elif AUTOSTART.exists():
        AUTOSTART.unlink()


class SingleInstance(QObject):
    """Only one copy of the app runs. Launching it again just un-hides the pets."""

    activated = Signal()

    def __init__(self):
        super().__init__()
        self.server: QLocalServer | None = None

    def already_running(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(SOCKET_NAME)
        if socket.waitForConnected(300):
            socket.write(b"show")
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            return True
        QLocalServer.removeServer(SOCKET_NAME)  # stale socket from a crash
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_connection)
        self.server.listen(SOCKET_NAME)
        return False

    def _on_connection(self):
        while self.server.hasPendingConnections():
            self.server.nextPendingConnection().close()
            self.activated.emit()


def idle_seconds() -> float | None:
    """How long since the last keyboard/mouse input. None if the OS won't say."""
    if WINDOWS:
        import ctypes

        class LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000

    from PySide6.QtDBus import QDBusConnection, QDBusInterface

    monitor = QDBusInterface("org.gnome.Mutter.IdleMonitor", "/org/gnome/Mutter/IdleMonitor/Core",
                             "org.gnome.Mutter.IdleMonitor", QDBusConnection.sessionBus())
    if not monitor.isValid():
        return None  # not GNOME: away mode just stays off
    reply = monitor.call("GetIdletime")
    args = reply.arguments()
    return args[0] / 1000 if args else None
