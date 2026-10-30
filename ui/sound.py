"""Little cartoon sound effects, synthesised on first run (no audio files to ship).

Sounds are written as WAVs to the cache folder (core/paths.py) and played with
QSoundEffect. If audio isn't available, everything quietly does nothing.
"""

import math
import random
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl

from core.paths import cache_dir

try:
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # Qt built without multimedia
    QSoundEffect = None

RATE = 22050
CACHE = cache_dir() / "sounds"
VERSION = 1  # bump to regenerate the files after changing a recipe


def _tone(seconds: float, freq, harmonics=(1.0,), vibrato=(0.0, 0.0), envelope=None, noise=0.0):
    """freq: Hz, or a function of progress 0..1. envelope: function of progress -> 0..1."""
    n = int(RATE * seconds)
    out, phase = [], 0.0
    rng = random.Random(7)
    for i in range(n):
        x = i / n
        f = freq(x) if callable(freq) else freq
        f += math.sin(2 * math.pi * vibrato[0] * i / RATE) * vibrato[1]
        phase += 2 * math.pi * f / RATE
        s = sum(a * math.sin(phase * (k + 1)) for k, a in enumerate(harmonics)) / sum(harmonics)
        if noise:
            s = s * (1 - noise) + rng.uniform(-1, 1) * noise
        env = envelope(x) if envelope else min(1.0, x * 20) * (1 - x)
        out.append(s * env)
    return out


def _lowpass(samples, amount=0.2):
    out, y = [], 0.0
    for s in samples:
        y += amount * (s - y)
        out.append(y)
    return out


def _silence(seconds):
    return [0.0] * int(RATE * seconds)


def _fade(x, attack=0.05):
    return min(1.0, x / attack) * (1 - x) ** 1.5


RECIPES = {
    "pop": lambda: _tone(0.07, lambda x: 900 - 600 * x, envelope=lambda x: (1 - x) ** 2),
    "boing": lambda: _tone(0.35, lambda x: 180 + 420 * x, vibrato=(28, 60), envelope=lambda x: (1 - x) ** 2),
    "munch": lambda: sum((_lowpass(_tone(0.05, 200, noise=0.8), 0.3) + _silence(0.06) for _ in range(3)), []),
    "bonk": lambda: _lowpass(_tone(0.18, lambda x: 140 - 60 * x, harmonics=(1, 0.5, 0.3), noise=0.3,
                                   envelope=lambda x: (1 - x) ** 3), 0.4),
    "whoosh": lambda: _lowpass(_tone(0.4, 300, noise=1.0, envelope=lambda x: math.sin(math.pi * x)), 0.08),
    "meow": lambda: _tone(0.45, lambda x: 560 + 380 * math.sin(math.pi * min(1, x * 1.3)) - 120 * x,
                          harmonics=(1, 0.6, 0.35, 0.2), vibrato=(7, 12), envelope=_fade),
    "bark": lambda: sum((_lowpass(_tone(0.11, lambda x: 380 - 160 * x, harmonics=(1, 0.8, 0.5, 0.3),
                                        noise=0.25, envelope=lambda x: (1 - x) ** 1.5), 0.5)
                         + _silence(0.07) for _ in range(2)), []),
    "bleat": lambda: _tone(0.65, lambda x: 430 - 40 * x, harmonics=(1, 0.7, 0.5, 0.3), vibrato=(17, 45),
                           envelope=lambda x: _fade(x) * (0.75 + 0.25 * math.sin(x * 2 * math.pi * 17))),
    "grunt": lambda: _lowpass(_tone(0.3, lambda x: 150 - 40 * x, harmonics=(1, 0.9, 0.7, 0.5), noise=0.15,
                                    envelope=_fade), 0.35),
    "shutter": lambda: _lowpass(_tone(0.03, 900, noise=1.0, envelope=lambda x: 1 - x), 0.6) + _silence(0.05)
    + _lowpass(_tone(0.05, 500, noise=1.0, envelope=lambda x: (1 - x) ** 2), 0.5),
    "squeak": lambda: sum((_tone(0.09, lambda x: 1300 + 500 * x, envelope=lambda x: math.sin(math.pi * x))
                           + _silence(0.05) for _ in range(2)), []),
}


def _write(path: Path, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s / peak * 0.8 * 32767)) for s in samples))


def ensure_files() -> Path:
    folder = CACHE / f"v{VERSION}"
    folder.mkdir(parents=True, exist_ok=True)
    for name, recipe in RECIPES.items():
        path = folder / f"{name}.wav"
        if not path.exists():
            _write(path, recipe())
    return folder


class Sounds:
    def __init__(self, enabled: bool = True, volume: float = 0.35):
        self.enabled = enabled
        self.volume = volume
        self.effects: dict = {}
        self.folder: Path | None = None

    def play(self, name: str, volume: float = 1.0):
        if not self.enabled or not name or QSoundEffect is None or name not in RECIPES:
            return
        if self.folder is None:
            try:
                self.folder = ensure_files()
            except OSError:
                self.enabled = False
                return
        effect = self.effects.get(name)
        if effect is None:
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(self.folder / f"{name}.wav")))
            self.effects[name] = effect
        effect.setVolume(self.volume * volume)
        effect.play()
