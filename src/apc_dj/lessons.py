"""Geführte Lektionen: Schritt für Schritt zum DJ.

Jeder Schritt hat einen Text, Ziel-Tasten (blinken am Gerät und am Bildschirm) und eine
Prüfung. Die Prüfung läuft bei jeder Eingabe und bei jedem Ticker-Takt.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from .controller import ControlEvent
from .layout import ROOT_KEY_PADS, loop_pad, shot_pad

if TYPE_CHECKING:
    from .app import App

DRUMS, BASS, CHORDS, MELODY = loop_pad(0, 0), loop_pad(2, 0), loop_pad(3, 0), loop_pad(5, 0)
RISER, BOOM = shot_pad(13), shot_pad(12)
KEY_PADS = list(range(16))


@dataclass
class Ctx:
    app: "App"
    ev: Optional[ControlEvent]
    mem: dict

    def pressed(self, kind: str, index: Optional[int] = None) -> bool:
        e = self.ev
        return bool(e and e.kind == kind and e.pressed and (index is None or e.index == index))

    def key_pressed(self, pads=None) -> bool:
        return self.pressed("pad") and self.app.layout[self.ev.index].role == "key" and (
            pads is None or self.ev.index in pads)

    def playing(self, *cols: int) -> bool:
        return all(self.app.is_playing(c) for c in cols)

    def silent(self, col: int) -> bool:
        s = self.app.engine.snapshot
        return col not in s.playing and col not in s.pending

    def bars(self) -> int:
        return self.app.current_bar() - self.mem.setdefault("bar0", self.app.current_bar())

    def count(self, name: str, cond: bool) -> int:
        if cond:
            self.mem[name] = self.mem.get(name, 0) + 1
        return self.mem.get(name, 0)


@dataclass
class Step:
    text: str
    check: Callable[[Ctx], bool]
    targets: list = field(default_factory=list)  # [("pad", n), ("track", i), ("scene", i), ("fader", i), ("shift", 0)]


@dataclass
class Lesson:
    title: str
    emoji: str
    intro: str
    steps: list[Step]


LESSONS = [
    Lesson("Hallo Controller", "👋", "Lerne deinen Controller kennen.", [
        Step("Drück auf irgendein buntes Pad!", lambda c: c.pressed("pad")),
        Step("Super! Unten sind die Schieberegler – die Fader. Schieb einen davon hoch oder runter.",
             lambda c: c.ev is not None and c.ev.kind == "fader", [("fader", i) for i in range(9)]),
        Step("Rechts sind runde Knöpfe. Der unterste (Szene-Knopf 8) stoppt alles. Drück ihn!",
             lambda c: c.pressed("scene", 7), [("scene", 7)]),
    ]),
    Lesson("Der Beat", "🥁", "Jeder Song braucht einen Beat.", [
        Step("Ein DJ beginnt meist mit dem Beat. Drück das blinkende rote Pad oben links!",
             lambda c: c.playing(0), [("pad", DRUMS)]),
        Step("Hörst du die Kick? Zähl mit: 1 – 2 – 3 – 4! Schau auf die Punkte oben. (Warte 2 Takte)",
             lambda c: c.bars() >= 2),
        Step("Probier einen anderen Beat: Drück ein rotes Pad weiter unten in derselben Spalte.",
             lambda c: c.app.engine.snapshot.playing.get(0, 0) != 0 and c.playing(0),
             [("pad", loop_pad(0, v)) for v in (1, 2, 3)]),
    ]),
    Lesson("Der Bass kommt dazu", "🎸", "Der Bass ist das Fundament.", [
        Step("Starte zuerst wieder den Beat.", lambda c: c.playing(0), [("pad", DRUMS)]),
        Step("Jetzt der Bass – das blaue Pad. Achtung: Er wartet auf die nächste Eins!",
             lambda c: 2 in c.app.engine.snapshot.pending or c.playing(2), [("pad", BASS)]),
        Step("Siehst du es blinken? Das Pad wartet auf den Anfang des nächsten Takts. So bleibt alles im Takt!",
             lambda c: c.playing(2)),
        Step("Stopp den Bass mit dem dritten Knopf in der unteren Reihe (Track 3).",
             lambda c: c.silent(2), [("track", 2)]),
    ]),
    Lesson("Mischen mit Fadern", "🎚️", "DJs mischen Teile ein und aus.", [
        Step("Starte Beat und Bass.", lambda c: c.playing(0, 2), [("pad", DRUMS), ("pad", BASS)]),
        Step("Fader 3 ist die Lautstärke vom Bass. Schieb ihn ganz nach unten.",
             lambda c: c.app.faders[2] < 0.05, [("fader", 2)]),
        Step("Und jetzt langsam wieder ganz hoch – so blenden DJs Teile ein!",
             lambda c: c.app.faders[2] > 0.85, [("fader", 2)]),
        Step("Fader 9 ganz rechts ist die Gesamtlautstärke. Bewege ihn!",
             lambda c: c.ev is not None and c.ev.kind == "fader" and c.ev.index == 8 and not c.app.shift,
             [("fader", 8)]),
    ]),
    Lesson("Melodie spielen", "🎹", "Die zwei unteren Reihen sind ein Keyboard.", [
        Step("Spiel 5 Töne auf den zwei unteren Reihen!",
             lambda c: c.count("keys", c.key_pressed()) >= 5, [("pad", p) for p in KEY_PADS]),
        Step("Die rosa Tasten sind der Grundton A. Spiel einen davon!",
             lambda c: c.key_pressed(ROOT_KEY_PADS), [("pad", p) for p in ROOT_KEY_PADS]),
        Step("Wechsle das Instrument mit dem fünften runden Knopf rechts (Szene 5).",
             lambda c: c.pressed("scene", 4), [("scene", 4)]),
        Step("Starte die Akkorde (grün) und spiel 6 Töne dazu – hier klingt nichts falsch!",
             lambda c: c.count("keys", c.key_pressed() and c.playing(3)) >= 6, [("pad", CHORDS)]),
    ]),
    Lesson("Der Filter-Trick", "🌊", "Ein Filter macht den Klang dumpf oder hell.", [
        Step("Starte Beat und Akkorde.", lambda c: c.playing(0, 3), [("pad", DRUMS), ("pad", CHORDS)]),
        Step("Halte SHIFT gedrückt und schieb Fader 9 nach unten. Klingt wie unter Wasser!",
             lambda c: c.app.engine.cutoff < 0.3, [("shift", 0), ("fader", 8)]),
        Step("Halte SHIFT und schieb Fader 9 wieder ganz hoch – das ist ein Filter-Sweep!",
             lambda c: c.app.engine.cutoff > 0.9, [("shift", 0), ("fader", 8)]),
    ]),
    Lesson("Der Drop", "💣", "Spannung aufbauen – und dann: DROP!", [
        Step("Starte Beat, Bass und Melodie.", lambda c: c.playing(0, 2, 5),
             [("pad", DRUMS), ("pad", BASS), ("pad", MELODY)]),
        Step("Jetzt bauen wir Spannung auf: Stopp den Beat mit Track-Knopf 1 (unten links).",
             lambda c: c.silent(0), [("track", 0)]),
        Step("Drück den Riser 🚀 und zähl laut bis 4 …", lambda c: c.pressed("pad", RISER), [("pad", RISER)]),
        Step("JETZT: Beat wieder an! Er kommt genau auf der Eins – das ist der Drop! (Boom 💣 dazu?)",
             lambda c: c.playing(0), [("pad", DRUMS), ("pad", BOOM)]),
    ]),
    Lesson("Szenen wechseln", "🎬", "Ganze Song-Teile auf einen Druck.", [
        Step("Die oberen runden Knöpfe rechts starten eine ganze Reihe. Drück Szene 1!",
             lambda c: c.pressed("scene", 0), [("scene", 0)]),
        Step("Hör 2 Takte lang zu …", lambda c: c.bars() >= 2),
        Step("Wechsle zu Szene 3 – ein ganz neuer Song-Teil!", lambda c: c.pressed("scene", 2), [("scene", 2)]),
        Step("Hör 2 Takte lang zu …", lambda c: c.bars() >= 2),
        Step("Zum Schluss: Szene 8 stoppt alles. Verbeugen – Applaus!", lambda c: c.pressed("scene", 7), [("scene", 7)]),
    ]),
]


class LessonRunner:
    def __init__(self, progress_file: Optional[Path] = None):
        self.progress_file = progress_file
        self.stars: dict[str, int] = {}
        if progress_file and Path(progress_file).exists():
            try:
                self.stars = json.loads(Path(progress_file).read_text())
            except (OSError, ValueError):
                self.stars = {}
        self.current: Optional[int] = None
        self.step = 0
        self.mem: dict = {}
        self.mistakes = 0
        self.finished_at: Optional[float] = None
        self.result_stars = 0

    # -------------------------------------------------------------- Ablauf

    def enter(self, app: "App") -> None:
        nxt = next((i for i, l in enumerate(LESSONS) if self.stars.get(l.title, 0) == 0), 0)
        self.start(app, nxt)

    def leave(self, app: "App") -> None:
        self.current = None
        self.publish(app)

    def start(self, app: "App", idx: int) -> None:
        self.current = idx % len(LESSONS)
        self.step = 0
        self.mem = {}
        self.mistakes = 0
        self.finished_at = None
        app.engine.stop_all()
        les = LESSONS[self.current]
        app.info(les.emoji, f"Lektion {self.current + 1}: {les.title}", les.intro)
        self.publish(app)

    def _check(self, app: "App", ev: Optional[ControlEvent]) -> None:
        if self.current is None or self.finished_at is not None:
            return
        les = LESSONS[self.current]
        st = les.steps[self.step]
        if ev is not None and ev.kind == "pad" and ev.pressed:
            targets = [i for k, i in st.targets if k == "pad"]
            if targets and ev.index not in targets:
                self.mistakes += 1
        if st.check(Ctx(app, ev, self.mem)):
            self.step += 1
            self.mem = {"bar0": app.current_bar()}
            if self.step >= len(les.steps):
                self.finished_at = time.monotonic()
                self.result_stars = 3 if self.mistakes <= 2 else 2 if self.mistakes <= 6 else 1
                self.stars[les.title] = max(self.stars.get(les.title, 0), self.result_stars)
                self._save()
                app.info("🏆", "Geschafft!", f"Lektion „{les.title}“ abgeschlossen: " + "⭐" * self.result_stars)
            self.publish(app)

    def on_event(self, app: "App", ev: ControlEvent) -> None:
        self._check(app, ev)

    def tick(self, app: "App") -> None:
        if self.finished_at is not None and time.monotonic() - self.finished_at > 4:
            self.start(app, (self.current or 0) + 1)
            return
        self._check(app, None)

    # -------------------------------------------------------------- Anzeige

    def highlights(self, app: "App") -> dict:
        if self.current is None or self.finished_at is not None:
            return {}
        return {t: "blink" for t in LESSONS[self.current].steps[self.step].targets}

    def state(self) -> dict:
        cur = None
        if self.current is not None:
            les = LESSONS[self.current]
            done = self.finished_at is not None
            cur = {"index": self.current, "title": les.title, "emoji": les.emoji,
                   "step": min(self.step, len(les.steps)), "steps": len(les.steps), "done": done,
                   "text": "Geschafft! Gleich geht's weiter …" if done else les.steps[self.step].text,
                   "targets": [] if done else [list(t) for t in les.steps[self.step].targets],
                   "stars": self.result_stars if done else 0}
        return {"list": [{"title": l.title, "emoji": l.emoji, "stars": self.stars.get(l.title, 0)}
                         for l in LESSONS], "current": cur}

    def publish(self, app: "App") -> None:
        app.bus.publish({"t": "lesson", **self.state()})

    def _save(self) -> None:
        if self.progress_file:
            p = Path(self.progress_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self.stars, ensure_ascii=False, indent=1))
