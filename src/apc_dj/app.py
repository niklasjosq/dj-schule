"""Zentrale Logik: Eingaben -> Klang, LEDs und Bildschirm.

Hardware-Tasten und Klicks im Browser erzeugen dieselben ControlEvents. Die App
übersetzt sie in Engine-Befehle, hält ein LED-Modell (Gerät == Bildschirm) und
schickt Ereignisse an alle Browser.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Optional

from .audio.engine import COLUMNS as N_COLUMNS
from .audio.engine import TRACK_KEYS, TRACK_SHOTS, AudioEngine
from .audio.library import KEY_INSTRUMENTS, Library
from .controller import PALETTE, SCENE_BASE, TRACK_BASE, ControlEvent, PadLed
from .layout import COLUMNS, SCENE_LABELS, TRACK_LABELS, PadSpec, build_layout
from .lessons import LessonRunner
from .rhythm_game import RhythmGame

log = logging.getLogger(__name__)

MODES = ["frei", "lektion", "spiel"]
MODE_NAMES = {"frei": "Freies Spielen", "lektion": "Lektionen", "spiel": "Rhythmus-Spiel"}


class EventBus:
    """Verteilt Nachrichten thread-sicher an alle verbundenen Browser (asyncio-Queues)."""

    def __init__(self):
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def subscribe(self, loop: asyncio.AbstractEventLoop) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subs.append((loop, q))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs = [(l, s) for l, s in self._subs if s is not q]

    def publish(self, msg: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(q.put_nowait, msg)
            except RuntimeError:
                pass  # Loop bereits beendet


class App:
    def __init__(self, engine: AudioEngine, lib: Library, bus: Optional[EventBus] = None,
                 timing_offset_ms: float = 0.0, progress_file=None):
        self.engine = engine
        self.lib = lib
        self.bus = bus or EventBus()
        self.controller = None
        self.lock = threading.RLock()
        self.instrument = 0
        self.layout: dict[int, PadSpec] = build_layout(lib, self.inst_name)
        self.mode = "frei"
        self.shift = False
        self.faders = [0.8] * 9
        self.pressed: set[tuple[str, int]] = set()
        self.timing_offset = timing_offset_ms / 1000.0
        self.lessons = LessonRunner(progress_file)
        self.game = RhythmGame()
        self._leds: dict[int, PadLed] = {}
        self._buttons: dict[str, list[int]] = {"track": [0] * 8, "scene": [0] * 8}
        self._last_beat = None
        self._ticker: Optional[threading.Thread] = None
        self._running = False
        engine.clicks = lib.clicks

    # ------------------------------------------------------------ Hilfen

    @property
    def inst_name(self) -> str:
        return KEY_INSTRUMENTS[self.instrument][0]

    def info(self, emoji: str, title: str, text: str) -> None:
        self.bus.publish({"t": "info", "emoji": emoji, "title": title, "text": text})

    def is_playing(self, col: int) -> bool:
        s = self.engine.snapshot
        return col in s.playing and col not in s.stopping

    def heard_now(self) -> float:
        return self.engine.heard_frame(self.engine.clock() - self.timing_offset)

    def current_bar(self) -> int:
        return self.engine.position(self.engine.heard_frame())[0]

    # ------------------------------------------------------------ Eingaben

    def handle(self, ev: ControlEvent) -> None:
        with self.lock:
            if ev.kind in ("pad", "track", "scene", "shift"):
                key = (ev.kind, ev.index)
                (self.pressed.add if ev.pressed else self.pressed.discard)(key)
                self.bus.publish({"t": "press", "kind": ev.kind, "index": ev.index, "pressed": ev.pressed})
            getattr(self, f"_on_{ev.kind}")(ev)
            if self.mode == "lektion":
                self.lessons.on_event(self, ev)
            elif self.mode == "spiel":
                self.game.on_event(self, ev)
            self.refresh_leds()

    def _on_pad(self, ev: ControlEvent) -> None:
        spec = self.layout[ev.index]
        if spec.role == "key":
            buf = self.lib.keys[self.inst_name][spec.col]
            if ev.pressed:
                self.engine.release(("pad", ev.index), 0.03)
                self.engine.play(buf, TRACK_KEYS, key=("pad", ev.index))
                self.info("🎹", f"Ton {spec.label}", spec.info)
            else:
                self.engine.release(("pad", ev.index))
            return
        if not ev.pressed:
            return
        if spec.role == "shot":
            self.engine.play(self.lib.oneshots[spec.col].data, TRACK_SHOTS)
            self.info(spec.emoji, spec.label, spec.info)
        elif spec.role == "loop":
            snd = self.lib.loops.get((spec.col, spec.row))
            if snd is None:
                self.info("📂", "Leeres Pad", spec.info)
                return
            s = self.engine.snapshot
            if (s.playing.get(spec.col) == spec.row and spec.col not in s.stopping
                    and spec.col not in s.pending) or s.pending.get(spec.col) == spec.row:
                self.engine.stop_column(spec.col)
                self.info(spec.emoji, f"{spec.label} stoppt", "Die Loop hört am Ende des Takts auf.")
            else:
                self.engine.launch(spec.col, spec.row, snd.data)
                wait = " Sie startet genau auf der nächsten Eins." if s.running else ""
                self.info(spec.emoji, spec.label, spec.info + wait)

    def _on_note(self, ev: ControlEvent) -> None:
        """Gerät im eigenen Note/Drum-Modus: Ton direkt spielen."""
        if ev.pressed:
            self.engine.play(self.lib.key_for_midi(self.inst_name, ev.index), TRACK_KEYS, key=("note", ev.index))
        else:
            self.engine.release(("note", ev.index))

    def _on_track(self, ev: ControlEvent) -> None:
        if ev.pressed:
            self.engine.stop_column(ev.index)
            name, emoji, _, _ = COLUMNS[ev.index]
            self.info(emoji, f"{name} stoppen", "Die Spalte wird am Ende des Takts leise.")

    def _on_scene(self, ev: ControlEvent) -> None:
        if not ev.pressed:
            return
        i = ev.index
        if i < 4:
            for col in range(N_COLUMNS):
                snd = self.lib.loops.get((col, i))
                if snd is not None:
                    self.engine.launch(col, i, snd.data)
            self.info("🎬", f"Szene {i + 1}",
                      "Eine Szene startet eine ganze Reihe auf einmal – ein neuer Teil des Songs!")
        elif i == 4:
            self.set_instrument((self.instrument + 1) % len(KEY_INSTRUMENTS))
        elif i == 5:
            self.set_metronome(not self.engine.metronome)
        elif i == 6:
            self.set_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)])
        elif i == 7:
            self.engine.stop_all()
            self.info("🛑", "Alles stopp", "Alle Loops sind aus. Stille!")

    def _on_shift(self, ev: ControlEvent) -> None:
        self.shift = ev.pressed

    def _on_fader(self, ev: ControlEvent) -> None:
        i, v = ev.index, ev.value
        if i == 8 and self.shift:
            self.engine.set_cutoff(v)
            self.bus.publish({"t": "filter", "value": v})
            return
        self.faders[i] = v
        if i < 8:
            self.engine.set_gain(i, v)
        else:
            self.engine.set_master(v)
        self.bus.publish({"t": "fader", "index": i, "value": v})

    # ------------------------------------------------------------ Einstellungen

    def set_instrument(self, idx: int) -> None:
        with self.lock:
            self.instrument = idx
            self.layout = build_layout(self.lib, self.inst_name)
            _, label, emoji, _ = KEY_INSTRUMENTS[idx]
            self.info(emoji, f"Instrument: {label}", "Die Tasten unten spielen jetzt ein anderes Instrument.")
            self.bus.publish(self.state())
            self.refresh_leds()

    def set_metronome(self, on: bool) -> None:
        with self.lock:
            self.engine.metronome = on
            if on:
                self.engine.restart_grid()
            self.info("⏱️", "Metronom " + ("an" if on else "aus"),
                      "Das Metronom klickt auf jedem Schlag. Der hohe Klick ist die Eins!")
            self.bus.publish({"t": "status", **self.status()})
            self.refresh_leds()

    def set_mode(self, mode: str) -> None:
        with self.lock:
            if mode == self.mode:
                return
            if self.mode == "lektion":
                self.lessons.leave(self)
            elif self.mode == "spiel":
                self.game.stop(self)
            self.mode = mode
            if mode == "lektion":
                self.lessons.enter(self)
            elif mode == "spiel":
                self.game.start(self)
            self.info({"frei": "🎧", "lektion": "📚", "spiel": "🎯"}[mode], MODE_NAMES[mode],
                      {"frei": "Spiel einfach drauflos!",
                       "lektion": "Schritt für Schritt zum DJ. Die blinkenden Tasten zeigen dir den Weg.",
                       "spiel": "Hör gut zu und spiel das Muster nach!"}[mode])
            self.bus.publish({"t": "status", **self.status()})
            self.refresh_leds()

    def handle_web(self, data: dict) -> None:
        t = data.get("t")
        if t in ("press", "release"):
            self.handle(ControlEvent(data["kind"], int(data["index"]), t == "press", source="web"))
        elif t == "fader":
            self.handle(ControlEvent("fader", int(data["index"]), value=float(data["value"]), source="web"))
        elif t == "mode":
            self.set_mode(data["mode"])
        elif t == "metronome":
            self.set_metronome(bool(data["on"]))
        elif t == "instrument":
            self.set_instrument((self.instrument + 1) % len(KEY_INSTRUMENTS))
        elif t == "lesson":
            with self.lock:
                self.set_mode("lektion")
                self.lessons.start(self, int(data["index"]))
                self.refresh_leds()

    # ------------------------------------------------------------ Zustand für den Browser

    def status(self) -> dict:
        _, label, emoji, _ = KEY_INSTRUMENTS[self.instrument]
        return {"mode": self.mode, "metronome": self.engine.metronome,
                "instrument": f"{emoji} {label}", "bpm": self.engine.bpm}

    def state(self) -> dict:
        with self.lock:
            return {
                "t": "state",
                "layout": [self.layout[p].to_ui() for p in range(64)],
                "columns": [{"name": n, "emoji": e, "color": PALETTE[c]} for n, e, c, _ in COLUMNS],
                "scene_labels": SCENE_LABELS, "track_labels": TRACK_LABELS,
                "leds": {p: self._led_ui(l) for p, l in self._leds.items()},
                "buttons": self._buttons,
                "faders": self.faders, "filter": self.engine.cutoff,
                "controller": getattr(self.controller, "name", None),
                "lessons": self.lessons.state(), "game": self.game.state(),
                **self.status(),
            }

    @staticmethod
    def _led_ui(led: PadLed) -> list:
        return [PALETTE.get(led.color, "#000000") if led.color else None, led.mode, led.brightness]

    # ------------------------------------------------------------ LEDs

    def desired_leds(self) -> tuple[dict[int, PadLed], dict[str, list[int]]]:
        s = self.engine.snapshot
        pads: dict[int, PadLed] = {}
        for p, spec in self.layout.items():
            if spec.role == "loop":
                if spec.color == 0:
                    led = PadLed(0)
                elif s.pending.get(spec.col) == spec.row or (
                        s.playing.get(spec.col) == spec.row and spec.col in s.stopping):
                    led = PadLed(spec.color, "blink")
                elif s.playing.get(spec.col) == spec.row:
                    led = PadLed(spec.color, brightness=100)
                else:
                    led = PadLed(spec.color, brightness=25)
            elif ("pad", p) in self.pressed:
                led = PadLed(3, brightness=100)
            else:
                led = PadLed(spec.color, brightness=50)
            pads[p] = led
        track = [2 if (c in s.pending or c in s.stopping) else 1 if c in s.playing else 0 for c in range(8)]
        scene = [0] * 8
        for i in range(4):
            if i in s.pending.values():
                scene[i] = 2
            elif i in s.playing.values():
                scene[i] = 1
        scene[4] = 1
        scene[5] = 1 if self.engine.metronome else 0
        scene[6] = {"frei": 0, "lektion": 1, "spiel": 2}[self.mode]
        buttons = {"track": track, "scene": scene}
        overlay = (self.lessons.highlights(self) if self.mode == "lektion"
                   else self.game.highlights(self) if self.mode == "spiel" else {})
        for (kind, idx), how in overlay.items():
            if kind == "pad":
                pads[idx] = how if isinstance(how, PadLed) else PadLed(self.layout[idx].color or 3, "blink")
            elif kind in ("track", "scene"):
                buttons[kind][idx] = 2
        return pads, buttons

    def refresh_leds(self) -> None:
        with self.lock:
            pads, buttons = self.desired_leds()
            changed = {p: l for p, l in pads.items() if self._leds.get(p) != l}
            self._leds.update(changed)
            btn_changed = buttons != self._buttons
            self._buttons = buttons
            if self.controller is not None:
                for p, l in changed.items():
                    self.controller.set_pad(p, l)
                if btn_changed:
                    for i in range(8):
                        self.controller.set_button(TRACK_BASE + i, buttons["track"][i])
                        self.controller.set_button(SCENE_BASE + i, buttons["scene"][i])
            if changed or btn_changed:
                self.bus.publish({"t": "leds", "pads": {p: self._led_ui(l) for p, l in changed.items()},
                                  "buttons": buttons})

    # ------------------------------------------------------------ Ticker

    def tick(self) -> None:
        with self.lock:
            s = self.engine.snapshot
            active = s.running or self.engine.metronome or self.mode == "spiel"
            if active:
                bar, beat, frac = self.engine.position(self.engine.heard_frame())
                step = beat * 2 + (1 if frac >= 0.5 else 0)
                cur = (bar, step)
            else:
                cur = None
            if cur != self._last_beat:
                self._last_beat = cur
                self.bus.publish({"t": "beat", "active": active,
                                  "bar": cur[0] if cur else 0, "beat": cur[1] // 2 if cur else 0,
                                  "step": cur[1] if cur else 0})
            if self.mode == "lektion":
                self.lessons.tick(self)
            elif self.mode == "spiel":
                self.game.tick(self)
            self.refresh_leds()

    def start(self) -> None:
        self._running = True

        def loop():
            while self._running:
                try:
                    self.tick()
                except Exception:  # noqa: BLE001
                    log.exception("Fehler im Ticker")
                time.sleep(1 / 60)

        self._ticker = threading.Thread(target=loop, daemon=True, name="ticker")
        self._ticker.start()

    def stop(self) -> None:
        self._running = False
        if self._ticker:
            self._ticker.join(timeout=1)
