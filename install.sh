#!/usr/bin/env bash
# Desktop Pets installer for Linux: makes a virtual environment, installs PySide6,
# adds "Desktop Pets" to your app menu, and starts it.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    echo "Desktop Pets needs Python 3.10 or newer (found: $("$PYTHON" --version 2>&1))." >&2
    exit 1
fi

echo "==> Creating virtual environment in .venv"
"$PYTHON" -m venv .venv

echo "==> Installing PySide6 (this can take a minute)"
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

echo "==> Checking Qt can open windows"
if ! QT_QPA_PLATFORM=xcb .venv/bin/python -c 'from PySide6.QtWidgets import QApplication; QApplication([])' >/dev/null 2>&1; then
    echo
    echo "Qt is missing some system libraries. On Ubuntu/Debian run:"
    echo "  sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1"
    echo "(Fedora: sudo dnf install xcb-util-cursor xcb-util-wm xcb-util-keysyms libxkbcommon-x11)"
    echo "(Arch:   sudo pacman -S xcb-util-cursor xcb-util-wm xcb-util-keysyms libxkbcommon-x11)"
    echo "Then run ./install.sh again."
    exit 1
fi

echo "==> Adding Desktop Pets to your app menu"
.venv/bin/python main.py --install

echo "==> Starting your pet!"
nohup .venv/bin/python main.py >/dev/null 2>&1 &
echo "Done. Next time, open \"Desktop Pets\" from your app menu."
