"""Rhythmus-Spiel "Hör zu – spiel nach!".

Ablauf pro Runde (je ein Takt):  Zuhören -> Nachspielen -> Ergebnis
Die App spielt ein Muster auf 4 Drum-Pads (Licht + Ton), das Kind spielt es nach.
Bewertet wird, wie genau die Schläge im Takt sitzen.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from .audio.engine import TRACK_SHOTS
from .audio.synth import SR
from .controller import ControlEvent, PadLed
from .layout import shot_pad

if TYPE_CHECKING:
    from .app import App

GAME_PADS = [shot_pad(i) for i in range(4)]  # Kick, Snare, Clap, HiHat
GAME_NAMES = ["Kick", "Snare", "Clap", "HiHat"]
PERFECT = 0.07  # Sekunden
GOOD = 0.14
WINDOW = 0.22  # bis hierhin zählt ein Schlag überhaupt
LEVEL_UP = 3
MAX_LEVEL = 6


def make_pattern(level: int, rng: random.Random) -> list[tuple[int, int]]:
    """Liste von (Achtel-Schritt 0..7, Pad-Index 0..3)."""
    if level == 1:
        return [(s, 0) for s in (0, 2, 4, 6)]
    if level == 2:
        return [(0, 0), (2, 1), (4, 0), (6, 1)]
    if level == 3:
        return [(s, rng.choice([0, 1, 2])) for s in (0, 2, 4, 6)]
    hits = {4: 5, 5: 6, 6: 7}[min(level, 6)]
    sounds = [0, 1, 3] if level == 4 else [0, 1, 2, 3]
    steps = sorted({0} | set(rng.sample(range(1, 8), hits - 1)))
    return [(s, 0 if s == 0 else rng.choice(sounds)) for s in steps]


def rate(err: float) -> str:
    a = abs(err)
    return "perfekt" if a <= PERFECT else "gut" if a <= GOOD else "daneben"


class RhythmGame:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.phase = "idle"
        self.level = 1
        self.score = 0
        self.streak = 0
        self.successes = 0
        self.round_bar: Optional[int] = None  # Takt, in dem vorgespielt wird
        self.origin: Optional[int] = None
        self.pattern: list[tuple[int, int]] = []
        self.expected: list[tuple[float, int]] = []
        self.hits: list[tuple[float, int]] = []
        self.results: list[dict] = []
        self.message = "Drück auf Start!"
        self._prev_metronome = False
        self._t0 = 0.0

    # ------------------------------------------------------------ Steuerung

    def start(self, app: "App") -> None:
        self.reset()
        self._prev_metronome = app.engine.metronome
        app.engine.metronome = True
        app.engine.restart_grid()
        self._t0 = app.engine.clock()
        self.phase = "countin"
        self.message = "Mach dich bereit … zähl mit!"
        self.publish(app)

    def stop(self, app: "App") -> None:
        app.engine.metronome = self._prev_metronome
        self.phase = "idle"
        self.publish(app)

    def bar_frame(self, app: "App", bar: int, step: float = 0) -> float:
        e = app.engine
        return self.origin + bar * e.bar + step * e.bar / 8

    def _schedule(self, app: "App", bar: int) -> None:
        self.round_bar = bar
        self.pattern = make_pattern(self.level, self.rng)
        self.expected = [(self.bar_frame(app, bar + 1, s), p) for s, p in self.pattern]
        self.hits = []
        for s, p in self.pattern:
            buf = app.lib.oneshots[p].data
            app.engine.play(buf, TRACK_SHOTS, at=int(self.bar_frame(app, bar, s)))

    def tick(self, app: "App") -> None:
        if self.phase == "idle":
            return
        snap = app.engine.snapshot
        if self.phase == "countin" and self.round_bar is None:
            if app.engine.clock() - self._t0 < 0.1:  # warten, bis das Raster neu gesetzt ist
                return
            self.origin = snap.origin
        elif self.origin != snap.origin:
            # Raster wurde neu gesetzt (z. B. erste Loop gestartet) -> Runde neu beginnen
            self.origin, self.phase, self.round_bar = snap.origin, "countin", None
            return
        heard = app.engine.heard_frame()
        bar = int((heard - self.origin) // app.engine.bar)

        if self.phase == "countin" and self.round_bar is None:
            self._schedule(app, bar + 2)
            self.message = "Mach dich bereit … zähl mit!"
            self.publish(app)
        elif self.phase in ("countin", "result") and bar == self.round_bar:
            self.phase = "listen"
            self.results = []
            self.message = "👂 Hör gut zu!"
            self.publish(app)
        elif self.phase == "listen" and bar == self.round_bar + 1:
            self.phase = "play"
            self.message = "🥁 Du bist dran!"
            self.publish(app)
        elif self.phase == "play" and heard > self.bar_frame(app, self.round_bar + 2) + WINDOW * SR:
            self._evaluate(app)
            self._schedule(app, self.round_bar + 3)
            self.phase = "result"
            self.publish(app)

    def on_event(self, app: "App", ev: ControlEvent) -> None:
        if ev.kind == "scene" and ev.pressed and ev.index < 4 and self.phase == "idle":
            self.start(app)
            return
        if not (ev.kind == "pad" and ev.pressed and ev.index in GAME_PADS):
            return
        if self.phase not in ("play", "listen", "result") or self.round_bar is None:
            return
        f = app.heard_now()
        start = self.bar_frame(app, self.round_bar + 1) - WINDOW * SR
        end = self.bar_frame(app, self.round_bar + 2) + WINDOW * SR
        if not (start <= f <= end):
            return
        pad = GAME_PADS.index(ev.index)
        self.hits.append((f, pad))
        cands = [(abs(f - ef), ef) for ef, p in self.expected if p == pad]
        if cands:
            d, ef = min(cands)
            r = rate((f - ef) / SR) if d <= WINDOW * SR else "daneben"
        else:
            r = "falsch"
        app.bus.publish({"t": "game_hit", "pad": pad, "rating": r})

    def _evaluate(self, app: "App") -> None:
        used: set[int] = set()
        results = []
        for ef, pad in self.expected:
            best, best_i = None, None
            for i, (hf, hp) in enumerate(self.hits):
                if i in used or hp != pad:
                    continue
                d = (hf - ef) / SR
                if abs(d) <= WINDOW and (best is None or abs(d) < abs(best)):
                    best, best_i = d, i
            if best_i is not None:
                used.add(best_i)
            r = rate(best) if best is not None else "verpasst"
            results.append({"pad": pad, "step": round((ef - self.bar_frame(app, self.round_bar + 1)) / (app.engine.bar / 8)),
                            "rating": r, "ms": None if best is None else round(best * 1000)})
        extra = len(self.hits) - len(used)
        self.results = results
        ok = all(r["rating"] in ("perfekt", "gut") for r in results) and extra <= 1
        self.score += sum(100 if r["rating"] == "perfekt" else 50 if r["rating"] == "gut" else 0 for r in results)
        if ok:
            self.streak += 1
            self.successes += 1
            perfect = all(r["rating"] == "perfekt" for r in results)
            self.message = "🌟 PERFEKT!" if perfect else "👍 Gut gemacht!"
            if self.successes >= LEVEL_UP and self.level < MAX_LEVEL:
                self.level += 1
                self.successes = 0
                self.message += f" Level {self.level}! 🚀"
        else:
            self.streak = 0
            missed = sum(r["rating"] in ("verpasst", "daneben") for r in results)
            self.message = (f"Fast! {missed} Schlag/Schläge daneben – nochmal!" if missed
                            else "Ein paar Extra-Schläge – nochmal!")

    # ------------------------------------------------------------ Anzeige

    def highlights(self, app: "App") -> dict:
        if self.phase == "idle":
            return {("scene", 0): "blink"}
        out = {}
        heard = app.engine.heard_frame()
        for i, p in enumerate(GAME_PADS):
            color = app.layout[p].color
            out[("pad", p)] = PadLed(color, brightness=100 if self.phase == "play" else 25)
        if self.phase == "listen" and self.round_bar is not None:
            for s, p in self.pattern:
                f = self.bar_frame(app, self.round_bar, s)
                if f <= heard < f + 0.15 * SR:
                    out[("pad", GAME_PADS[p])] = PadLed(3, brightness=100)
        return out

    def state(self) -> dict:
        return {"phase": self.phase, "level": self.level, "score": self.score, "streak": self.streak,
                "message": self.message, "names": GAME_NAMES,
                "pattern": [[s, p] for s, p in self.pattern] if self.phase in ("listen", "play", "result") else [],
                "results": self.results}

    def publish(self, app: "App") -> None:
        app.bus.publish({"t": "game", **self.state()})
