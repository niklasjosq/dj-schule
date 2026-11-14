"""Musikstile ("Klangwelten"): jeder Stil liefert einen kompletten Klangsatz.

Ein Stil = 16 One-Shots + 7 Spalten x 4 Loops + 4 Keyboard-Instrumente. Alle Stile halten sich an
dieselben Regeln (siehe ``seq.py``): a-Moll, Akkordfolge Am – F – C – G, gleiche Spalten-Aufgaben,
gleiche One-Shot-Plätze (0 Kick, 1 Snare, 2 Clap, 3 HiHat, …, 12 Boom, 13 Riser).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass

from .. import synth
from ..seq import Sound

STUDIO_BPMS = (120, 125, 128, 130, 135, 138, 140, 145)


@dataclass(frozen=True)
class KeyInstrument:
    id: str  # Name in synth.INSTRUMENTS
    label: str
    emoji: str
    shift: int  # Halbtöne relativ zu KEY_NOTES
    color: int  # Palettenfarbe der Keyboard-Pads


@dataclass(frozen=True)
class StyleInfo:
    id: str
    name: str
    emoji: str
    color: str  # Akzentfarbe im Browser
    intro: str
    instruments: tuple[KeyInstrument, ...]
    default_bpm: float | None = None  # None = Tempo aus config.toml
    bpm_choices: tuple[int, ...] = ()  # leer = Tempo fest
    seed: int = 7

    def to_ui(self, config_bpm: float) -> dict:
        return {"id": self.id, "name": self.name, "emoji": self.emoji, "color": self.color,
                "default_bpm": self.default_bpm or config_bpm, "bpm_choices": list(self.bpm_choices)}


SCHULE = StyleInfo(
    "schule", "DJ-Schule", "🎧", "#ffcf3f",
    "Der Klassiker: Pop und House zum Lernen.",
    (
        KeyInstrument("klavier", "Klavier", "🎹", 0, 41),
        KeyInstrument("lead", "Synth", "🎛️", 0, 17),
        KeyInstrument("glocke", "Glocken", "🔔", 0, 12),
        KeyInstrument("bass", "Bass", "🎸", -24, 44),
    ),
)

HIPHOP = StyleInfo(
    "hiphop", "Hip-Hop", "🧢", "#ffbd6c",
    "Hip-Hop! Boom-Bap, Lo-Fi und Trap: staubige Drums mit Swing, E-Piano, 808-Bass und Scratches.",
    (
        KeyInstrument("epiano", "E-Piano", "🎹", 0, 21),
        KeyInstrument("lofi_klavier", "Lo-Fi-Klavier", "📻", 0, 36),
        KeyInstrument("flute", "Flöte", "🪈", 0, 33),
        KeyInstrument("sub", "808-Bass", "🔊", -24, 44),
    ),
    default_bpm=90, bpm_choices=(80, 85, 88, 90, 93, 95, 100), seed=15,
)
TECHNO = StyleInfo(
    "techno", "Techno", "🏭", "#4cc3ff",
    "Willkommen in der Techno-Welt! Harte Kick, Rumble, Ride-Becken und Akkorde mit Echo – wie in Berlin und Detroit.",
    (
        KeyInstrument("blip", "Blip", "💠", 0, 33),
        KeyInstrument("acid", "Acid", "🧪", -12, 16),
        KeyInstrument("lead", "Synth", "🎛️", 0, 17),
        KeyInstrument("bass", "Bass", "🎸", -24, 44),
    ),
    default_bpm=130, bpm_choices=STUDIO_BPMS, seed=11,
)
ACID = StyleInfo(
    "acid", "Acid", "🧪", "#88ff4c",
    "Acid! Hier quietscht und blubbert der Bass – ein Filter öffnet und schließt sich bei jedem Ton.",
    (
        KeyInstrument("acid", "Acid", "🧪", -12, 16),
        KeyInstrument("squelch", "Quietsch-Lead", "🫧", 0, 21),
        KeyInstrument("blip", "Blip", "💠", 0, 33),
        KeyInstrument("bass", "Bass", "🎸", -24, 44),
    ),
    default_bpm=128, bpm_choices=STUDIO_BPMS, seed=12,
)
TRANCE = StyleInfo(
    "trance", "Trance/Rave", "🌈", "#ff4cff",
    "Trance und Rave: riesige Supersaw-Akkorde, ein heulender Hoover und Uplifter bis zum Höhepunkt!",
    (
        KeyInstrument("supersaw", "Supersaw", "🌈", 0, 52),
        KeyInstrument("pluck", "Pluck", "🪕", 0, 36),
        KeyInstrument("hoover", "Hoover", "🌀", -12, 48),
        KeyInstrument("glocke", "Glocken", "🔔", 0, 12),
    ),
    default_bpm=138, bpm_choices=STUDIO_BPMS, seed=13,
)
CHIP = StyleInfo(
    "chip", "Electro/8-Bit", "👾", "#ff7a3c",
    "Electro und 8-Bit: 808-Drums und Klänge wie aus alten Spielkonsolen – piep, pling, hopp!",
    (
        KeyInstrument("chip_square", "Rechteck", "🟦", 0, 40),
        KeyInstrument("chip_pulse", "Puls", "🔆", 0, 13),
        KeyInstrument("chip_tri", "Dreieck", "🔺", -12, 9),
        KeyInstrument("glocke", "Glocken", "🔔", 0, 12),
    ),
    default_bpm=120, bpm_choices=STUDIO_BPMS, seed=14,
)

STYLES: list[StyleInfo] = [SCHULE, HIPHOP, TECHNO, ACID, TRANCE, CHIP]
STYLE_BY_ID = {s.id: s for s in STYLES}


def build_style(style_id: str, bpm: float) -> tuple[list[Sound], list[list[Sound]]]:
    """(16 One-Shots, 7 Spalten mit je 4 Loops) für einen Stil erzeugen – immer gleich (fester Zufall)."""
    info = STYLE_BY_ID[style_id]
    synth.reseed(info.seed)
    module = importlib.import_module(f"{__name__}.{style_id}")
    return module.build(bpm)
