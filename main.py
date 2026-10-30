"""Desktop pets.

    .venv/bin/python main.py                  # your saved pets (a cat the first time)
    .venv/bin/python main.py kitten calico    # pick species and variant
    .venv/bin/python main.py --list           # show what's available
    .venv/bin/python main.py --install        # add Desktop Pets to the app menu
"""

import os
import signal
import sys

# Wayland won't let apps stay on top or place themselves on screen, so on
# Linux run through XWayland (X11), where GNOME allows both.
if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.registry import discover
from ui import system
from ui.app import PetApp


def main():
    registry = discover()
    args = sys.argv[1:]
    if args[:1] == ["--list"]:
        for cls in registry.values():
            print(f"{cls.species:12} {', '.join(cls.variants)}")
        return

    species = args[0] if args and not args[0].startswith("--") else None
    variant = args[1] if species and len(args) > 1 else None
    if species and species not in registry:
        sys.exit(f"Unknown pet {species!r}. Try: {', '.join(registry)}")
    if variant and variant not in registry[species].variants:
        sys.exit(f"{species} has no variant {variant!r}; pick one of {registry[species].variants}")

    app = QApplication(sys.argv)
    app.setApplicationName("desktop-pets")
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, lambda *_: app.quit())  # Ctrl+C in the terminal

    if args[:1] == ["--install"]:
        system.install_launcher(registry["cat"]("tabby") if "cat" in registry else next(iter(registry.values()))())
        print(f"Installed {system.LAUNCHER}")
        return

    instance = system.SingleInstance()
    if instance.already_running():
        print("Desktop Pets is already running; showing your pets.")
        return

    pets = PetApp(registry, species, variant)
    instance.activated.connect(pets.show_all)

    # let Python see Ctrl+C even while Qt's event loop is busy
    keepalive = QTimer()
    keepalive.timeout.connect(lambda: None)
    keepalive.start(200)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
