"""Klang-Bibliothek: ein kompletter Klangsatz für einen Musikstil, passend in Tonart und Tempo.

* 16 One-Shots (Drums + DJ-Effekte)
* 8 Spalten x 4 Varianten Loops (je 4 Takte, Akkorde Am – F – C – G)
* Keyboard-Töne (a-Moll-Pentatonik) für 4 Instrumente
* eigene WAV-Dateien aus sounds/eigene/ für Spalte 8
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .seq import KEY_NOTES, LOOP_BARS, PROGRESSION, Seq, Sound, bar_frames, stereo  # noqa: F401
from .styles import STYLE_BY_ID, KeyInstrument, build_style
from .synth import SR, render_note, t_axis

log = logging.getLogger(__name__)


def load_user_loops(folder: Path, bpm: float) -> list[Sound]:
    """Bis zu 4 WAV/AIFF/FLAC-Dateien, auf ganze Takte zugeschnitten."""
    import soundfile as sf
    from scipy.signal import resample_poly

    if not folder.exists():
        return []
    out = []
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".wav", ".aif", ".aiff", ".flac"))
    bar = bar_frames(bpm)
    for p in files[:4]:
        try:
            data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        except Exception as e:  # noqa: BLE001
            log.warning("Kann %s nicht laden: %s", p.name, e)
            continue
        if sr != SR:
            data = resample_poly(data, SR, sr, axis=0).astype(np.float32)
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        data = data[:, :2]
        bars = max(1, int(round(len(data) / bar)))
        target = bars * bar
        if len(data) < target:
            data = np.vstack([data, np.zeros((target - len(data), 2), np.float32)])
        data = data[:target]
        m = np.max(np.abs(data))
        if m > 0:
            data = data * (0.5 / m)
        out.append(Sound(f"user_{p.stem}", p.stem[:14], "⭐", data.astype(np.float32),
                         f"Dein eigener Sound: {p.name}"))
    return out


@dataclass
class Library:
    bpm: float
    style: str = "schule"
    instruments: tuple[KeyInstrument, ...] = ()
    oneshots: list[Sound] = field(default_factory=list)
    loops: dict[tuple[int, int], Sound] = field(default_factory=dict)  # (spalte, variante)
    keys: dict[str, list[np.ndarray]] = field(default_factory=dict)
    clicks: tuple[np.ndarray, np.ndarray] | None = None

    @classmethod
    def build(cls, bpm: float, user_dir: Path | None = None, style: str = "schule") -> "Library":
        info = STYLE_BY_ID[style]
        lib = cls(bpm, style, info.instruments)
        lib.oneshots, columns = build_style(style, bpm)
        columns = list(columns) + [load_user_loops(user_dir, bpm) if user_dir else []]
        for col, sounds in enumerate(columns):
            for var, snd in enumerate(sounds[:4]):
                lib.loops[(col, var)] = snd
        for inst in info.instruments:
            lib.keys[inst.id] = [stereo(render_note(inst.id, m + inst.shift, 4.0), gain=0.45) for m in KEY_NOTES]
        t = t_axis(0.04)
        env = np.exp(-t * 120)
        lib.clicks = (stereo(np.sin(2 * np.pi * 1800 * t) * env, gain=0.5),
                      stereo(np.sin(2 * np.pi * 1100 * t) * env, gain=0.35))
        render_note.cache_clear()  # Einzeltöne werden nicht mehr gebraucht – Speicher freigeben
        return lib

    def instrument(self, name: str) -> KeyInstrument:
        return next(i for i in self.instruments if i.id == name)

    def key_for_midi(self, instrument: str, midi: int) -> np.ndarray:
        return stereo(render_note(instrument, midi + self.instrument(instrument).shift, 4.0), gain=0.45)


def build_library(style: str, bpm: float, user_dir: Path | None = None) -> Library:
    """Für den Hintergrund-Prozess (muss auf Modulebene stehen, damit er sich übertragen lässt)."""
    return Library.build(bpm, user_dir, style)


# --------------------------------------------------------------- Übergabe per Datei
# Ein Stil hat ~200 MB Klangdaten. Statt sie durch eine Pipe zu schicken (doppelter Speicher, und macOS gibt
# den Platz danach kaum zurück), schreibt der Hintergrund-Prozess sie in eine Datei, die die App nur einblendet.


def _slots(lib: Library) -> list[tuple[object, object]]:
    """Alle Klang-Arrays in fester Reihenfolge, als (Behälter, Schlüssel)."""
    out: list[tuple[object, object]] = [(snd, "data") for snd in lib.oneshots]
    out += [(lib.loops[k], "data") for k in sorted(lib.loops)]
    out += [(lib.keys[i.id], n) for i in lib.instruments for n in range(len(lib.keys[i.id]))]
    out += [(lib, "clicks")]
    return out


def _get(box, key):
    return getattr(box, key) if isinstance(key, str) else box[key]


def _set(box, key, value) -> None:
    if isinstance(key, str):
        setattr(box, key, value)
    else:
        box[key] = value


def build_library_file(style: str, bpm: float, user_dir: Path | None, path: str):
    """Im Hintergrund-Prozess: Stil bauen, Klänge in `path` schreiben, Rest (ohne Klänge) zurückgeben."""
    lib = Library.build(bpm, user_dir, style)
    shapes = []
    with open(path, "wb") as f:
        for box, key in _slots(lib):
            value = _get(box, key)
            parts = value if key == "clicks" else (value,)
            shapes.append([p.shape for p in parts])
            for part in parts:
                np.ascontiguousarray(part, dtype=np.float32).tofile(f)
            _set(box, key, None)
    return lib, shapes


def attach_library_file(lib: Library, shapes, path: str) -> Library:
    """In der App: Klänge aus der Datei einblenden (nur lesen); die Datei selbst wird sofort gelöscht."""
    mm = np.memmap(path, dtype=np.float32, mode="r")
    Path(path).unlink(missing_ok=True)  # die Einblendung bleibt gültig, bis sie nicht mehr gebraucht wird
    pos = 0
    for (box, key), part_shapes in zip(_slots(lib), shapes):
        parts = []
        for shape in part_shapes:
            n = int(np.prod(shape))
            parts.append(mm[pos:pos + n].reshape(shape))
            pos += n
        _set(box, key, tuple(parts) if key == "clicks" else parts[0])
    return lib
