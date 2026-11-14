"""Welche Taste macht was? – Belegung des 8x8-Rasters.

  Reihen 5–8 (oben):   Loops, 8 Spalten (Instrumente) x 4 Varianten
  Reihen 3–4:          One-Shots (Drums + DJ-Effekte)
  Reihen 1–2 (unten):  Keyboard (a-Moll-Pentatonik)
"""
from __future__ import annotations

from dataclasses import dataclass

from .audio.library import Library
from .audio.seq import KEY_NOTES
from .controller import PALETTE

# (Name, Emoji, Palettenfarbe, Erklärung)
COLUMNS = [
    ("Drums", "🥁", 5, "Der Beat – das Herz der Musik."),
    ("Percussion", "🪘", 9, "Extra-Rhythmus: Shaker, Trommeln, Kuhglocke."),
    ("Bass", "🎸", 45, "Der Bass: tief und kräftig, man spürt ihn im Bauch."),
    ("Akkorde", "🎹", 21, "Akkorde geben die Stimmung: fröhlich oder traurig."),
    ("Arpeggio", "✨", 37, "Akkordtöne nacheinander – das glitzert!"),
    ("Melodie", "🎶", 13, "Die Melodie: zum Mitsingen."),
    ("Effekte", "🌌", 49, "Effekte bauen Spannung auf."),
    ("Eigene", "⭐", 57, "Deine eigenen Sounds aus dem Ordner sounds/eigene."),
]
DRUM_SHOT_COLOR = 8
FX_SHOT_COLOR = 53
ROOT_COLOR = 56
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"]

SCENE_LABELS = ["Szene 1", "Szene 2", "Szene 3", "Szene 4", "Instrument", "Metronom", "Modus", "Alles stopp"]
TRACK_LABELS = [f"Stopp {c[0]}" for c in COLUMNS]


@dataclass(frozen=True)
class PadSpec:
    pad: int
    role: str  # "loop" | "shot" | "key"
    label: str
    emoji: str
    color: int  # Palettenindex (0 = leer)
    info: str
    col: int = 0  # Loop: Spalte; Shot: Index in lib.oneshots; Key: Index in KEY_NOTES
    row: int = 0  # Loop: Variante 0..3

    def to_ui(self) -> dict:
        return {"pad": self.pad, "role": self.role, "label": self.label, "emoji": self.emoji,
                "color": PALETTE.get(self.color, "#333"), "col": self.col, "row": self.row}


def loop_pad(col: int, variant: int) -> int:
    return (7 - variant) * 8 + col


def shot_pad(i: int) -> int:
    return 24 + i if i < 8 else 16 + (i - 8)


def build_layout(lib: Library, instrument: str) -> dict[int, PadSpec]:
    specs: dict[int, PadSpec] = {}
    for col, (name, emoji, color, info) in enumerate(COLUMNS):
        for v in range(4):
            snd = lib.loops.get((col, v))
            p = loop_pad(col, v)
            if snd is None:
                specs[p] = PadSpec(p, "loop", "leer", "", 0, f"{name}: Hier ist noch kein Sound. {info}", col, v)
            else:
                specs[p] = PadSpec(p, "loop", snd.label, snd.emoji, color, f"{name}: {snd.info}", col, v)
    for i, snd in enumerate(lib.oneshots):
        color = DRUM_SHOT_COLOR if i < 9 else FX_SHOT_COLOR
        specs[shot_pad(i)] = PadSpec(shot_pad(i), "shot", snd.label, snd.emoji, color, snd.info, i)
    inst = lib.instrument(instrument)
    for k, midi in enumerate(KEY_NOTES):
        m = midi + inst.shift
        name = NOTE_NAMES[m % 12]
        root = m % 12 == 9
        specs[k] = PadSpec(
            k, "key", f"{name}{m // 12 - 1}", "", ROOT_COLOR if root else inst.color,
            "Der Grundton A – hier fühlt sich die Melodie zu Hause." if root
            else "Töne der a-Moll-Pentatonik: Alle passen zur Musik!", k)
    return specs


ROOT_KEY_PADS = [k for k, m in enumerate(KEY_NOTES) if m % 12 == 9]
