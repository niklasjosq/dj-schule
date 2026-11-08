"""Echtzeit-Mixer mit Taktraster.

* Loops (8 Spalten) laufen phasengleich zum Taktraster und starten/stoppen quantisiert
  auf den nächsten Takt – so passen sie immer zusammen.
* One-Shots und Keyboard-Töne laufen als "Voices" (sofort oder zu einem festen Frame).
* Pro Spalte Lautstärke (Fader), Master-Lautstärke, Master-Tiefpass (Filter-Sweep),
  Metronom, Soft-Limiter.

Der Audio-Callback blockiert nie: Befehle kommen über eine deque herein und werden am
Anfang jedes Blocks im Audio-Thread ausgeführt.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import signal

from .library import bar_frames
from .synth import SR

log = logging.getLogger(__name__)

COLUMNS = 8
TRACK_SHOTS = 8
TRACK_KEYS = 9
N_TRACKS = 10


@dataclass
class Voice:
    buf: np.ndarray
    track: int
    start: int  # absoluter Frame
    gain: float = 1.0
    key: Optional[object] = None  # für Note-Off
    release_left: Optional[int] = None
    release_len: int = 1

    def done(self, frame: int) -> bool:
        return frame - self.start >= len(self.buf) or (self.release_left is not None and self.release_left <= 0)


@dataclass
class LoopSlot:
    buf: Optional[np.ndarray] = None
    row: Optional[int] = None
    start: int = 0  # ab diesem Frame hörbar
    stop: Optional[int] = None  # ab diesem Frame still
    pending_buf: Optional[np.ndarray] = None
    pending_row: Optional[int] = None
    pending_start: int = 0


@dataclass(frozen=True)
class Snapshot:
    frame: int
    time: float  # time.monotonic() beim Block
    latency: float
    origin: int
    bar: int  # Frames pro Takt
    playing: dict  # spalte -> reihe
    pending: dict  # spalte -> reihe
    stopping: frozenset
    running: bool  # spielt irgendeine Loop?


class AudioEngine:
    def __init__(self, bpm: float = 120.0, blocksize: int = 256, master_max: float = 0.85):
        self.bpm = bpm
        self.bar = bar_frames(bpm)
        self.beat = self.bar / 4
        self.blocksize = blocksize
        self.master_max = master_max
        self.frame = 0
        self.origin = 0
        self.slots = [LoopSlot() for _ in range(COLUMNS)]
        self.voices: list[Voice] = []
        self.gains = np.ones(N_TRACKS, np.float32)
        self.gains[:COLUMNS] = 0.8
        self._gains_now = self.gains.copy()
        self.master = 0.8
        self._master_now = self.master
        self.cutoff = 1.0
        self._set_filter(1.0)
        self._zi = np.zeros((len(self._a) - 1, 2))
        self.metronome = False
        self.clicks: Optional[tuple[np.ndarray, np.ndarray]] = None
        self._cmds: deque[Callable[[], None]] = deque()
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.latency = 0.0
        self.clock = time.monotonic  # in Tests austauschbar
        self.snapshot = self._make_snapshot(self.clock(), 0)

    # ------------------------------------------------------------ Steuerung (thread-sicher)

    def launch(self, col: int, row: int, buf: np.ndarray) -> None:
        self._cmds.append(lambda: self._launch(col, row, buf))

    def stop_column(self, col: int) -> None:
        self._cmds.append(lambda: self._stop_column(col))

    def stop_all(self) -> None:
        self._cmds.append(self._stop_all)

    def play(self, buf: np.ndarray, track: int, gain: float = 1.0, key=None, at: Optional[int] = None) -> None:
        """Voice sofort (oder ab Frame `at`) abspielen."""
        self._cmds.append(lambda: self._play(buf, track, gain, key, at))

    def release(self, key, seconds: float = 0.12) -> None:
        self._cmds.append(lambda: self._release(key, int(seconds * SR)))

    def set_gain(self, track: int, value: float) -> None:
        self.gains[track] = float(np.clip(value, 0, 1))

    def set_master(self, value: float) -> None:
        self.master = float(np.clip(value, 0, 1))

    def set_cutoff(self, value: float) -> None:
        self.cutoff = float(np.clip(value, 0, 1))
        self._cmds.append(lambda: self._set_filter(self.cutoff))

    def restart_grid(self) -> None:
        """Setzt das Taktraster auf 'jetzt', wenn keine Loop läuft (z. B. für das Spiel)."""
        self._cmds.append(lambda: None if self._any_loop() else setattr(self, "origin", self.frame))

    # ------------------------------------------------------------ Zeit

    def next_bar(self, frame: int) -> int:
        k = math.ceil((frame - self.origin) / self.bar)
        return self.origin + k * self.bar

    def heard_frame(self, at: Optional[float] = None) -> float:
        """Welcher Frame ist zur Zeit `at` (monotonic) aus dem Lautsprecher zu hören?"""
        s = self.snapshot
        at = self.clock() if at is None else at
        return s.frame + (at - s.time - s.latency) * SR

    def position(self, frame: float) -> tuple[int, int, float]:
        """(Takt, Schlag 0..3, Anteil im Schlag) relativ zum Raster."""
        rel = (frame - self.origin) / self.beat
        beat_total = math.floor(rel)
        return beat_total // 4, beat_total % 4, rel - beat_total

    # ------------------------------------------------------------ Befehle (Audio-Thread)

    def _any_loop(self) -> bool:
        return any(s.buf is not None or s.pending_buf is not None for s in self.slots)

    def _launch(self, col, row, buf):
        slot = self.slots[col]
        if not self._any_loop():
            self.origin = self.frame  # erstes Starten: Raster neu ausrichten, sofort los
            slot.buf, slot.row, slot.start, slot.stop = buf, row, self.frame, None
            return
        slot.pending_buf, slot.pending_row = buf, row
        slot.pending_start = self.next_bar(self.frame)
        slot.stop = None  # ein geplanter Stopp wird durch den Wechsel ersetzt

    def _stop_column(self, col):
        slot = self.slots[col]
        if slot.pending_buf is not None and slot.buf is None:
            slot.pending_buf = slot.pending_row = None  # nur geplant -> einfach abbrechen
            return
        slot.pending_buf = slot.pending_row = None
        if slot.buf is not None:
            slot.stop = self.next_bar(self.frame + 1)

    def _stop_all(self):
        for slot in self.slots:
            slot.buf = slot.row = slot.pending_buf = slot.pending_row = slot.stop = None
        self.voices = [v for v in self.voices if v.track == TRACK_KEYS]

    def _play(self, buf, track, gain, key, at):
        start = self.frame if at is None else max(at, self.frame)
        self.voices.append(Voice(buf, track, start, gain, key))

    def _release(self, key, n):
        for v in self.voices:
            if v.key == key and v.release_left is None:
                v.release_left = v.release_len = max(n, 1)

    def _set_filter(self, value):
        cutoff = 120 * (19000 / 120) ** value
        b, a = signal.butter(2, cutoff / (SR / 2), "low")
        self._b, self._a = b, a

    # ------------------------------------------------------------ Mischen

    def render(self, frames: int) -> np.ndarray:
        while self._cmds:
            try:
                self._cmds.popleft()()
            except Exception:  # noqa: BLE001 – ein fehlerhafter Befehl darf den Ton nie abwürgen
                log.exception("Fehler beim Ausführen eines Audio-Befehls")
        f0 = self.frame
        f1 = f0 + frames
        tracks = np.zeros((N_TRACKS, frames, 2), np.float32)

        for col, slot in enumerate(self.slots):
            # geplanter Wechsel / Start innerhalb dieses Blocks?
            switch = slot.pending_start - f0 if slot.pending_buf is not None and slot.pending_start < f1 else None
            end = frames
            if switch is not None:
                end = max(switch, 0)
            if slot.buf is not None:
                stop_at = frames if slot.stop is None else min(frames, max(slot.stop - f0, 0))
                a = max(slot.start - f0, 0)
                b = min(end, stop_at)
                if b > a:
                    self._mix_loop(tracks[col], slot.buf, f0, a, b)
                if slot.stop is not None and slot.stop < f1:
                    slot.buf = slot.row = slot.stop = None
            if switch is not None:
                slot.buf, slot.row, slot.start, slot.stop = slot.pending_buf, slot.pending_row, slot.pending_start, None
                slot.pending_buf = slot.pending_row = None
                self._mix_loop(tracks[col], slot.buf, f0, max(switch, 0), frames)

        if self.metronome and self.clicks:
            first = math.ceil((f0 - self.origin) / self.beat)
            k = first
            while True:
                fb = int(round(self.origin + k * self.beat))
                if fb >= f1:
                    break
                if fb >= f0:
                    click = self.clicks[0] if k % 4 == 0 else self.clicks[1]
                    self.voices.append(Voice(click, TRACK_SHOTS, fb, 1.0))
                k += 1

        alive = []
        for v in self.voices:
            a = max(v.start - f0, 0)
            if a >= frames:
                alive.append(v)
                continue
            pos = f0 + a - v.start
            n = min(frames - a, len(v.buf) - pos)
            if n > 0:
                chunk = v.buf[pos:pos + n] * v.gain
                if v.release_left is not None:
                    left = v.release_left - np.arange(n)
                    chunk = chunk * (np.clip(left, 0, None) / v.release_len)[:, None]
                    v.release_left -= n
                tracks[v.track, a:a + n] += chunk
            if not v.done(f1):
                alive.append(v)
        self.voices = alive

        # Lautstärken pro Spur glätten (kein Knacken)
        ramp = np.linspace(0, 1, frames, dtype=np.float32)[:, None]
        out = np.zeros((frames, 2), np.float32)
        for tr in range(N_TRACKS):
            g0, g1 = self._gains_now[tr], self.gains[tr]
            if g0 == 0 and g1 == 0:
                continue
            out += tracks[tr] * (g0 + (g1 - g0) * ramp)
        self._gains_now = self.gains.copy()
        m0, m1 = self._master_now, self.master * self.master_max
        out *= m0 + (m1 - m0) * ramp
        self._master_now = m1

        out, self._zi = signal.lfilter(self._b, self._a, out, axis=0, zi=self._zi)
        out = np.tanh(out).astype(np.float32)  # Soft-Limiter
        self.frame = f1
        return out

    def _mix_loop(self, dst, buf, f0, a, b):
        """Loop-Ausschnitt mischen – Phase immer relativ zum Raster-Ursprung."""
        idx = (np.arange(f0 + a, f0 + b) - self.origin) % len(buf)
        dst[a:b] += buf[idx]

    # ------------------------------------------------------------ Snapshot

    def _make_snapshot(self, now: float, frame: int) -> Snapshot:
        return Snapshot(
            frame=frame, time=now, latency=self.latency, origin=self.origin, bar=self.bar,
            playing={c: s.row for c, s in enumerate(self.slots) if s.buf is not None},
            pending={c: s.pending_row for c, s in enumerate(self.slots) if s.pending_buf is not None},
            stopping=frozenset(c for c, s in enumerate(self.slots) if s.stop is not None),
            running=self._any_loop(),
        )

    def _block(self, frames: int) -> np.ndarray:
        now = self.clock()
        f0 = self.frame
        out = self.render(frames)
        self.snapshot = self._make_snapshot(now, f0)
        return out

    # ------------------------------------------------------------ Start/Stopp

    def start(self) -> str:
        """Startet die Audioausgabe. Gibt den Gerätenamen zurück (oder 'stumm')."""
        self._running = True
        try:
            import sounddevice as sd

            def cb(outdata, frames, t, status):
                if status:
                    log.debug("Audio-Status: %s", status)
                self.latency = max(t.outputBufferDacTime - t.currentTime, 0.0) if t.currentTime else 0.0
                outdata[:] = self._block(frames)

            self._stream = sd.OutputStream(samplerate=SR, channels=2, dtype="float32",
                                           blocksize=self.blocksize, latency="low", callback=cb)
            self._stream.start()
            return sd.query_devices(self._stream.device)["name"]
        except Exception as e:  # noqa: BLE001
            log.warning("Keine Audioausgabe (%s) – laufe stumm weiter.", e)
            self._thread = threading.Thread(target=self._silent_loop, daemon=True)
            self._thread.start()
            return "stumm"

    def _silent_loop(self):
        period = self.blocksize / SR
        nxt = time.monotonic()
        while self._running:
            self._block(self.blocksize)
            nxt += period
            time.sleep(max(0.0, nxt - time.monotonic()))

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

