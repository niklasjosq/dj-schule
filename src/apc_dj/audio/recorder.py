"""Aufnahme der Master-Summe als WAV.

Der Audio-Callback ruft nur `feed()` auf: Block kopieren und in eine Queue legen – kein I/O,
keine Locks. Ein eigener Thread schreibt die Blöcke auf die Platte. Die Maximaldauer wird
hart in `feed()` eingehalten, damit eine Datei nie größer wird als erlaubt.
"""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from .synth import SR

log = logging.getLogger(__name__)


class Recorder:
    def __init__(self, max_seconds: float = 300.0):
        self.max_frames = int(max_seconds * SR)
        self.active = False
        self.frames = 0
        self.path: Optional[Path] = None
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._thread: Optional[threading.Thread] = None

    @property
    def seconds(self) -> float:
        return self.frames / SR

    @property
    def full(self) -> bool:
        return self.frames >= self.max_frames

    def start(self, path: Path) -> None:
        if self.active:
            return
        f = sf.SoundFile(path, "w", samplerate=SR, channels=2, subtype="PCM_16", format="WAV")
        self.path = path
        self.frames = 0
        self._queue = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._write, args=(f, self._queue), daemon=True,
                                        name="recorder")
        self._thread.start()
        self.active = True

    def feed(self, block: np.ndarray) -> None:
        """Im Audio-Thread: blockiert nie."""
        if not self.active:
            return
        n = min(len(block), self.max_frames - self.frames)
        if n <= 0:
            return
        self._queue.put_nowait(block[:n].copy())
        self.frames += n

    def stop(self) -> Optional[Path]:
        if not self.active:
            return None
        self.active = False
        self._queue.put_nowait(None)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        return self.path

    @staticmethod
    def _write(f: sf.SoundFile, q: queue.SimpleQueue) -> None:
        try:
            while True:
                block = q.get()
                if block is None:
                    break
                f.write(block)
        except Exception:  # noqa: BLE001
            log.exception("Fehler beim Schreiben der Aufnahme")
        finally:
            f.close()
