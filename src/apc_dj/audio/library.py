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
