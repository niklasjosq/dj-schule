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

STYLES: list[StyleInfo] = [SCHULE]
STYLE_BY_ID = {s.id: s for s in STYLES}


def build_style(style_id: str, bpm: float) -> tuple[list[Sound], list[list[Sound]]]:
    """(16 One-Shots, 7 Spalten mit je 4 Loops) für einen Stil erzeugen – immer gleich (fester Zufall)."""
    info = STYLE_BY_ID[style_id]
    synth.reseed(info.seed)
    module = importlib.import_module(f"{__name__}.{style_id}")
    return module.build(bpm)
