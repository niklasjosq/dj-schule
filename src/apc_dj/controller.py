"""Direkte Ansteuerung des AKAI APC mini mk2 über MIDI (mido + python-rtmidi).

Protokoll (Akai "APC mini mk2 Communication Protocol v1.0"):
  * Pads 8x8:        Note 0..63, unten links = 0, note = reihe*8 + spalte
  * Track-Buttons:   Note 100..107 (links -> rechts)
  * Scene-Buttons:   Note 112..119 (oben -> unten)
  * Shift:           Note 122
  * Fader 1..9:      CC 48..56
  * Pad-LED:         Note On, Velocity = Palettenfarbe, Kanal = Helligkeit/Verhalten
  * Button-LED:      Note On Kanal 0, Velocity 0 = aus, 1 = an, 2 = blinken
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

import mido

PAD_COUNT = 64
TRACK_BASE = 100
SCENE_BASE = 112
SHIFT_NOTE = 122
FADER_CC_BASE = 48
FADER_COUNT = 9

# Kanal der Pad-LED-Nachricht bestimmt das Verhalten
BRIGHTNESS = {10: 0, 25: 1, 50: 2, 65: 3, 75: 4, 90: 5, 100: 6}
PULSE = {16: 7, 8: 8, 4: 9, 2: 10}  # Pulsieren in 1/16 .. 1/2
BLINK = {24: 11, 16: 12, 8: 13, 4: 14, 2: 15}  # Blinken in 1/24 .. 1/2

# Ausgewählte Palettenfarben (Velocity) mit passender Bildschirmfarbe
PALETTE: dict[int, str] = {
    0: "#000000", 1: "#1e1e1e", 2: "#7f7f7f", 3: "#ffffff",
    4: "#ff4c4c", 5: "#ff0000", 8: "#ffbd6c", 9: "#ff5400",
    12: "#ffff4c", 13: "#ffff00", 16: "#88ff4c", 17: "#54ff00",
    20: "#4cff4c", 21: "#00ff00", 29: "#00ff55", 33: "#00ff99",
    36: "#4cc3ff", 37: "#00a9ff", 40: "#4c88ff", 41: "#0055ff",
    44: "#4c4cff", 45: "#0000ff", 48: "#874cff", 49: "#5400ff",
    52: "#ff4cff", 53: "#ff00ff", 56: "#ff4c87", 57: "#ff0054",
}

PORT_HINT = "APC mini mk2"


@dataclass(frozen=True)
class ControlEvent:
    """Eine Eingabe – egal ob vom Gerät oder aus dem Browser."""

    kind: str  # "pad" | "track" | "scene" | "shift" | "fader" | "note"
    index: int  # Pad 0..63, Track 0..7, Scene 0..7, Fader 0..8, Note (MIDI) für "note"
    pressed: bool = True
    value: float = 0.0  # Fader 0..1
    source: str = "hardware"


def decode(msg: mido.Message, notes_port: bool = False) -> Optional[ControlEvent]:
    """Übersetzt eine MIDI-Nachricht des APC in ein ControlEvent."""
    if msg.type in ("note_on", "note_off"):
        pressed = msg.type == "note_on" and msg.velocity > 0
        n = msg.note
        if notes_port:
            # Gerät ist in seinem eigenen Drum-/Note-Modus -> einfach Ton spielen
            return ControlEvent("note", n, pressed)
        if 0 <= n < PAD_COUNT:
            return ControlEvent("pad", n, pressed)
        if TRACK_BASE <= n < TRACK_BASE + 8:
            return ControlEvent("track", n - TRACK_BASE, pressed)
        if SCENE_BASE <= n < SCENE_BASE + 8:
            return ControlEvent("scene", n - SCENE_BASE, pressed)
        if n == SHIFT_NOTE:
            return ControlEvent("shift", 0, pressed)
    elif msg.type == "control_change":
        i = msg.control - FADER_CC_BASE
        if 0 <= i < FADER_COUNT:
            return ControlEvent("fader", i, value=msg.value / 127.0)
    return None


@dataclass(frozen=True)
class PadLed:
    color: int = 0  # Palettenindex
    mode: str = "solid"  # "solid" | "pulse" | "blink"
    brightness: int = 100  # nur für solid

    def channel(self) -> int:
        if self.mode == "pulse":
            return PULSE[4]
        if self.mode == "blink":
            return BLINK[4]
        return BRIGHTNESS[self.brightness]


def pad_message(pad: int, led: PadLed) -> mido.Message:
    return mido.Message("note_on", channel=led.channel(), note=pad, velocity=led.color)


def button_message(note: int, state: int) -> mido.Message:
    """state: 0 = aus, 1 = an, 2 = blinken."""
    return mido.Message("note_on", channel=0, note=note, velocity=state)


def find_port(names: list[str], suffix: str) -> Optional[str]:
    # Unter Linux kürzt ALSA die Namen, z. B. "APC mini mk2:APC mini mk2 APC mini mk2 Contr 20:0"
    key = suffix[:5].lower()
    for n in names:
        if PORT_HINT.lower() in n.lower() and key in n.lower():
            return n
    for n in names:
        if PORT_HINT.lower() in n.lower() and suffix == "Control":
            return n
    return None


class APCMiniMk2:
    """Öffnet die Ports, liefert Eingaben als ControlEvents, setzt LEDs (nur Änderungen)."""

    def __init__(self, on_event: Callable[[ControlEvent], None]):
        self.on_event = on_event
        self._lock = threading.Lock()
        self._pads: dict[int, PadLed] = {}
        self._buttons: dict[int, int] = {}
        ctrl = find_port(mido.get_input_names(), "Control")
        out = find_port(mido.get_output_names(), "Control")
        if not ctrl or not out:
            raise RuntimeError(
                "APC mini mk2 nicht gefunden. Ist er per USB angeschlossen? "
                f"Gefundene Ports: {mido.get_input_names()}"
            )
        self.name = ctrl
        self.inp = mido.open_input(ctrl, callback=lambda m: self._dispatch(m, False))
        notes = find_port(mido.get_input_names(), "Notes")
        self.notes_inp = (
            mido.open_input(notes, callback=lambda m: self._dispatch(m, True)) if notes else None
        )
        self.out = mido.open_output(out)

    def _dispatch(self, msg: mido.Message, notes_port: bool) -> None:
        ev = decode(msg, notes_port)
        if ev is not None:
            self.on_event(ev)

    def set_pad(self, pad: int, led: PadLed) -> None:
        with self._lock:
            if self._pads.get(pad) == led:
                return
            self._pads[pad] = led
            self.out.send(pad_message(pad, led))

    def set_button(self, note: int, state: int) -> None:
        with self._lock:
            if self._buttons.get(note) == state:
                return
            self._buttons[note] = state
            self.out.send(button_message(note, state))

    def clear(self) -> None:
        with self._lock:
            for p in range(PAD_COUNT):
                self.out.send(pad_message(p, PadLed(0)))
            for n in list(range(TRACK_BASE, TRACK_BASE + 8)) + list(range(SCENE_BASE, SCENE_BASE + 8)):
                self.out.send(button_message(n, 0))
            self._pads.clear()
            self._buttons.clear()

    def close(self) -> None:
        try:
            self.clear()
        finally:
            self.inp.close()
            if self.notes_inp:
                self.notes_inp.close()
            self.out.close()
