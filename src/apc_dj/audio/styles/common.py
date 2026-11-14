"""Gemeinsame Hilfen für die Musikstile.

Alle Töne werden relativ zum Akkord des Takts angegeben (Grundton, Terz, Quinte, Oktave …). So folgen Bass,
Akkorde und Melodien automatisch der Akkordfolge Am – F – C – G und passen immer zusammen.
"""
from __future__ import annotations

import numpy as np

from ..seq import LOOP_BARS, PROGRESSION, PROGRESSION7, Seq, Sound, stereo
from ..synth import SR, acid_line, render_note, sweep_filter

# Lautstärke (Spitze) je One-Shot-Platz – wie bei der DJ-Schule
SHOT_PEAK = [1.0, 0.8, 0.8, 0.45, 0.45, 0.8, 0.8, 0.5, 0.6, 0.7, 0.7, 0.55, 0.95, 0.6, 0.5, 0.6]

# Bass-/Acid-Muster: Zeichen -> Abstand zum Grundton ("3" = Terz des jeweiligen Akkords)
INTERVALS = {"R": 0, "O": 12, "5": 7, "-": -5, "T": 24, "F": 19}


def make_shots(specs) -> tuple[list[Sound], dict[str, np.ndarray]]:
    """16 x (id, Name, Emoji, Klang, Info) in der festen Platz-Reihenfolge -> Sounds + Rohklänge."""
    assert len(specs) == 16
    shots, raw = [], {}
    for i, (sid, label, emoji, x, info) in enumerate(specs):
        x = np.asarray(x, dtype=float)
        m = float(np.max(np.abs(x)))
        raw[sid] = (x * (SHOT_PEAK[i] / m) if m > 0 else x).astype(np.float32)
        shots.append(Sound(sid, label, emoji, stereo(raw[sid], gain=0.8), info))
    return shots, raw


def loop(sid: str, label: str, emoji: str, s: Seq, col: int, info: str, gain: float = 1.0) -> Sound:
    return Sound(sid, label, emoji, s.done_column(col, gain), info)


def root(bar: int) -> int:
    return PROGRESSION[bar % 4][0]


def third(bar: int) -> int:
    return 3 if bar % 4 == 0 else 4  # Am: kleine Terz, F/C/G: große Terz


def interval(bar: int, ch: str) -> int | None:
    if ch.upper() == "3":
        return third(bar)
    return INTERVALS.get(ch.upper())


def chord_note(bar: int, deg: int, seventh: bool = False) -> int:
    """deg-ter Akkordton (0, 1, 2 …), darüber in der nächsten Oktave weiter."""
    tones = (PROGRESSION7 if seventh else PROGRESSION)[bar % 4][1]
    return tones[deg % len(tones)] + 12 * (deg // len(tones))


def bass_line(s: Seq, inst: str, pattern: str, dur: float = 0.22, gain: float = 1.0,
              octave: int = 0, pan: float = 0.0) -> None:
    """pattern: 16 Zeichen je Takt (gilt für alle Takte) oder 64 für alle 4 Takte; Kleinbuchstaben = leiser."""
    for b in range(LOOP_BARS):
        p = pattern[b * 16:(b + 1) * 16] if len(pattern) > 16 else pattern
        for i, ch in enumerate(p):
            iv = interval(b, ch)
            if iv is not None:
                g = gain * (0.6 if ch.islower() else 1.0)
                s.note(b * 4 + i / 4, inst, root(b) + octave + iv, dur, g, pan)


def acid_steps(notes: str, flags: str, octave: int = 0) -> list:
    """Acid-Muster: notes/flags je 16 Zeichen (pro Takt wiederholt) oder 64.

    flags: 'a' = Akzent, 's' = Slide, 'b' = beides, '.' = nichts.
    """
    out = []
    for b in range(LOOP_BARS):
        n = notes[b * 16:(b + 1) * 16] if len(notes) > 16 else notes
        f = flags[b * 16:(b + 1) * 16] if len(flags) > 16 else flags
        for ch, fl in zip(n, f):
            iv = interval(b, ch)
            out.append((None if iv is None else root(b) + octave + iv, fl in "ab", fl in "sb"))
    return out


def add_acid(s: Seq, notes: str, flags: str, octave: int = 0, gain: float = 1.0, **kw) -> None:
    s.add(0, acid_line(acid_steps(notes, flags, octave), s.bpm, **kw), gain)


def chord_hits(s: Seq, inst: str, positions, dur: float, gain: float = 0.5, seventh: bool = False,
               octave: int = 0, spread: float = 0.0) -> None:
    """Ganze Akkorde auf die Positionen (Schläge im Takt) setzen; spread verteilt die Töne im Stereobild."""
    for b in range(LOOP_BARS):
        tones = (PROGRESSION7 if seventh else PROGRESSION)[b % 4][1]
        for pos in positions:
            for k, m in enumerate(tones):
                pan = spread * (k / max(len(tones) - 1, 1) * 2 - 1)
                s.note(b * 4 + pos, inst, m + octave, dur, gain, pan)


def chord_audio(bar: int, inst: str, dur_s: float, seventh: bool = False, octave: int = 0) -> np.ndarray:
    tones = (PROGRESSION7 if seventh else PROGRESSION)[bar % 4][1]
    parts = [render_note(inst, m + octave, dur_s) for m in tones]
    n = max(len(p) for p in parts)
    return sum(np.pad(p, [(0, n - len(p))] + [(0, 0)] * (p.ndim - 1)) for p in parts)


def motif(s: Seq, inst: str, notes, octave: int = 12, gain: float = 1.0, pan: float = 0.0,
          seventh: bool = False, per_bar: bool = True) -> None:
    """notes: (Schlag, Akkordton-Nr., Dauer). per_bar: das Motiv wiederholt sich in jedem Takt."""
    bars = range(LOOP_BARS) if per_bar else [None]
    for b in bars:
        for pos, deg, dur in notes:
            beat = b * 4 + pos if b is not None else pos
            bar = b if b is not None else int(pos // 4)
            s.note(beat, inst, chord_note(bar, deg, seventh) + octave, dur, gain, pan)


def arp(s: Seq, inst: str, order, step: float, dur: float, octave: int = 12, gain: float = 1.0,
        seventh: bool = False, pan_width: float = 0.0, pattern: str | None = None) -> None:
    """Arpeggio: Akkordtöne in der Reihenfolge `order`, alle `step` Schläge; pattern ('x'/'.') lässt Lücken."""
    n = int(round(4 / step))
    for b in range(LOOP_BARS):
        k = 0
        for i in range(n):
            if pattern and pattern[i % len(pattern)] != "x":
                continue
            deg = order[k % len(order)]
            k += 1
            s.note(b * 4 + i * step, inst, chord_note(b, deg, seventh) + octave, dur, gain,
                   pan_width * np.sin(i * 1.3))


def gate(s: Seq, pattern: str, smooth_ms: float = 2.0) -> None:
    """Rhythmisches An/Aus (Trance-Gate) über die ganze Loop; pattern = 16 Zeichen je Takt."""
    n = len(s.buf)
    step = s.beat / 4
    idx = (np.arange(n) / step).astype(int) % len(pattern)
    g = np.array([1.0 if c == "x" else 0.0 for c in pattern])[idx]
    k = max(int(smooth_ms / 1000 * SR), 1)
    g = np.convolve(np.concatenate([g[-k:], g]), np.ones(k) / k, mode="valid")[:n]
    s.buf *= g[:, None].astype(np.float32)


def loop_sweep(s: Seq, cutoff: np.ndarray, q: float = 1.0) -> None:
    """Filter mit Kurve (Hz) über die ganze Loop – nahtlos, als liefe die Loop schon lange."""
    n = len(s.buf)
    cut = np.interp(np.arange(n), np.linspace(0, n, len(cutoff)), cutoff)
    y = sweep_filter(np.concatenate([s.buf, s.buf]), np.tile(cut, 2), q)[n:]
    s.buf = y.astype(np.float32)


def seamless(x: np.ndarray, n: int, fade_s: float = 0.5) -> np.ndarray:
    """Klang mit Länge n + Überhang so überblenden, dass er als Loop ohne Knacks durchläuft."""
    f = min(int(fade_s * SR), len(x) - n)
    x = np.array(x[:n + f], dtype=float)
    ramp = np.linspace(0, 1, f)
    shape = (f,) + (1,) * (x.ndim - 1)
    x[:f] *= np.sqrt(ramp).reshape(shape)
    x[n:n + f] *= np.sqrt(1 - ramp).reshape(shape)
    return x


def beats_to_s(bpm: float, beats: float) -> float:
    return beats * 60.0 / bpm
