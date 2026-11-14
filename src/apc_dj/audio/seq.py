"""Gemeinsame Bausteine aller Musikstile: Sound, Stereo, Taktraster und Harmonie.

Damit alles zusammenpasst, halten sich alle Stile an dieselben Regeln:
* jede Loop ist genau LOOP_BARS Takte lang,
* alle Töne folgen der Akkordfolge PROGRESSION (a-Moll: Am – F – C – G),
* jede Spalte hat dieselbe Aufgabe und eine ähnliche Lautstärke (Seq.done_column).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .synth import SR, highpass, render_note

LOOP_BARS = 4
# Akkordfolge pro Takt: (Bass-Grundton, Akkordtöne)
PROGRESSION = [
    (45, (57, 60, 64)),  # Am
    (41, (57, 60, 65)),  # F
    (48, (55, 60, 64)),  # C
    (43, (55, 59, 62)),  # G
]
# Dieselbe Folge mit Septimen – nur leitereigene Töne aus a-Moll
PROGRESSION7 = [
    (45, (57, 60, 64, 67)),  # Am7
    (41, (53, 57, 60, 64)),  # Fmaj7
    (48, (55, 59, 60, 64)),  # Cmaj7
    (43, (55, 59, 62, 65)),  # G7
]
# a-Moll-Pentatonik für das Keyboard (unten links = tiefster Ton)
KEY_NOTES = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93]
# Tonklassen der a-Moll-Tonleiter (A H C D E F G)
A_MINOR = frozenset({9, 11, 0, 2, 4, 5, 7})

# Spalten: 0 Drums, 1 Percussion, 2 Bass, 3 Akkorde, 4 Arpeggio, 5 Melodie, 6 Effekte
# Hochpass pro Spalte (Hz) – so stört keine Spalte den Bass und die Kick der anderen
COLUMN_HIGHPASS = {1: 250, 3: 200, 4: 300, 5: 250}
# Ziel-Lautstärke (RMS) pro Spalte, gemessen an den Loops der DJ-Schule
COLUMN_RMS = [0.144, 0.043, 0.222, 0.082, 0.096, 0.110, 0.056]


def bar_frames(bpm: float) -> int:
    return int(round(4 * 60.0 / bpm * SR))


def stereo(x: np.ndarray, pan: float = 0.0, gain: float = 1.0) -> np.ndarray:
    """Mono -> Stereo mit Panorama -1 (links) .. 1 (rechts). Stereo-Eingaben behalten ihr Bild."""
    ang = (pan + 1) * np.pi / 4
    l, r = np.cos(ang) * np.sqrt(2) * gain, np.sin(ang) * np.sqrt(2) * gain
    if x.ndim == 2:
        return (x * np.array([l, r])).astype(np.float32)
    return np.stack([x * l, x * r], axis=1).astype(np.float32)


@dataclass
class Sound:
    id: str
    label: str
    emoji: str
    data: np.ndarray  # (N, 2) float32
    info: str = ""


def circular(fn, buf: np.ndarray) -> np.ndarray:
    """Filter auf eine Loop anwenden, als ob sie schon ewig läuft (kein Knacks an der Nahtstelle)."""
    n = len(buf)
    return fn(np.concatenate([buf, buf]))[n:]


class Seq:
    """Schreibt Klänge auf ein Raster (in Schlägen); Ausklang wird an den Anfang gefaltet."""

    def __init__(self, bpm: float, bars: int = LOOP_BARS, swing: float = 0.0):
        self.bpm = bpm
        self.bar = bar_frames(bpm)
        self.beat = self.bar / 4
        self.buf = np.zeros((self.bar * bars, 2), dtype=np.float32)
        # Swing: jede zweite Sechzehntel kommt etwas später (Anteil einer Sechzehntel) – der "Groove".
        # Alle Loops eines Stils nutzen denselben Wert, damit sie zusammen grooven.
        self.swing = swing

    @property
    def seconds(self) -> float:
        return len(self.buf) / SR

    def add(self, beat: float, x: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
        if self.swing:
            q = beat * 4
            if abs(q - round(q)) < 1e-6 and int(round(q)) % 2 == 1:
                beat += self.swing / 4
        x = stereo(x, pan, gain)
        n = len(self.buf)
        s = int(round(beat * self.beat)) % n
        while len(x):
            take = min(len(x), n - s)
            self.buf[s:s + take] += x[:take]
            x, s = x[take:], 0

    def steps(self, pattern: str, mono: np.ndarray, gain: float = 1.0, bars=range(LOOP_BARS), pan=0.0):
        """pattern: 16 Zeichen pro Takt, 'x' = Schlag, 'o' = leiser Schlag."""
        for b in bars:
            for i, c in enumerate(pattern):
                if c in "xo":
                    self.add(b * 4 + i / 4, mono, gain * (1 if c == "x" else 0.45), pan)

    def note(self, beat, inst, midi, dur_beats, gain=1.0, pan=0.0):
        self.add(beat, render_note(inst, int(midi), round(dur_beats * self.beat / SR, 3)), gain, pan)

    def done(self, peak: float) -> np.ndarray:
        m = np.max(np.abs(self.buf))
        return self.buf * (peak / m) if m > 0 else self.buf

    def done_column(self, col: int, gain: float = 1.0, peak: float = 0.95) -> np.ndarray:
        """Spalten-Regeln anwenden: Hochpass (Frequenz-Platz) und gleiche Lautstärke wie die DJ-Schule."""
        buf = self.buf.astype(np.float64)
        if col in COLUMN_HIGHPASS:
            buf = circular(lambda x: highpass(x.T, COLUMN_HIGHPASS[col]).T, buf)
        rms = float(np.sqrt(np.mean(buf ** 2)))
        if rms > 0:
            buf *= COLUMN_RMS[col] * gain / rms
        m = float(np.max(np.abs(buf)))
        if m > peak:
            buf *= peak / m
        return buf.astype(np.float32)
