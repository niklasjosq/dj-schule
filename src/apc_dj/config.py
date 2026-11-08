"""Einstellungen aus config.toml (alle Werte optional)."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    bpm: float = 120.0
    blocksize: int = 256
    master_max: float = 0.85
    host: str = "127.0.0.1"
    port: int = 8000
    open_browser: bool = True
    timing_offset_ms: float = 0.0
    sounds_dir: Path = Path("sounds/eigene")
    progress_file: Path = Path("data/progress.json")

    @classmethod
    def load(cls, path: Path) -> "Config":
        c = cls()
        if not path.exists():
            return c
        d = tomllib.loads(path.read_text(encoding="utf-8"))
        c.bpm = float(d.get("bpm", c.bpm))
        a = d.get("audio", {})
        c.blocksize = int(a.get("blocksize", c.blocksize))
        c.master_max = float(a.get("lautstaerke_max", c.master_max))
        w = d.get("web", {})
        c.host = w.get("host", c.host)
        c.port = int(w.get("port", c.port))
        c.open_browser = bool(w.get("browser_oeffnen", c.open_browser))
        g = d.get("spiel", {})
        c.timing_offset_ms = float(g.get("timing_offset_ms", c.timing_offset_ms))
        if "eigene_sounds" in d:
            c.sounds_dir = Path(d["eigene_sounds"])
        return c
