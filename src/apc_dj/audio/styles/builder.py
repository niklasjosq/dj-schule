"""Erzeugt Musikstile im Hintergrund, während die App weiterläuft.

Das Rechnen passiert in einem eigenen Prozess: So muss der Audio-Thread nie auf Python warten (kein Knacksen),
und der Speicher des Rechen-Prozesses wird nach jedem Stil wieder frei.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import tempfile
import threading
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import Optional

from ..library import attach_library_file, build_library, build_library_file

log = logging.getLogger(__name__)


class StyleBuilder:
    def __init__(self):
        self._pool = None
        self._lock = threading.Lock()

    def _new_pool(self):
        try:
            return ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"),
                                       max_tasks_per_child=1)
        except Exception as e:  # noqa: BLE001
            log.warning("Kein Hintergrund-Prozess möglich (%s) – rechne im Thread (kann kurz knacksen).", e)
            return ThreadPoolExecutor(max_workers=1)

    def submit(self, style: str, bpm: float, user_dir: Optional[Path]) -> Future:
        fd, path = tempfile.mkstemp(prefix="apc-dj-", suffix=".f32")
        os.close(fd)
        with self._lock:
            if self._pool is None:
                self._pool = self._new_pool()
            try:
                inner = self._pool.submit(build_library_file, style, bpm, user_dir, path)
            except (BrokenProcessPool, RuntimeError):
                self._pool = self._new_pool()
                inner = self._pool.submit(build_library_file, style, bpm, user_dir, path)
        outer: Future = Future()

        def done(f: Future) -> None:
            try:
                lib, shapes = f.result()
                outer.set_result(attach_library_file(lib, shapes, path))
            except BaseException as e:  # noqa: BLE001
                Path(path).unlink(missing_ok=True)
                outer.set_exception(e)

        inner.add_done_callback(done)
        return outer

    def shutdown(self) -> None:
        with self._lock:
            if self._pool is not None:
                self._pool.shutdown(wait=False, cancel_futures=True)
                self._pool = None


class SyncBuilder:
    """Für Tests: rechnet sofort im selben Thread."""

    def submit(self, style: str, bpm: float, user_dir: Optional[Path]) -> Future:
        f: Future = Future()
        try:
            f.set_result(build_library(style, bpm, user_dir))
        except Exception as e:  # noqa: BLE001
            f.set_exception(e)
        return f

    def shutdown(self) -> None:
        pass
