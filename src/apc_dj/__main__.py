"""Startet die DJ-Schule:  uv run apc-dj  [--no-controller] [--bpm 120] [--port 8000]"""
from __future__ import annotations

import argparse
import asyncio
import sys
import logging
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from .app import App
from .audio.engine import AudioEngine
from .audio.library import Library
from .config import Config
from .web.server import create_server

log = logging.getLogger("apc_dj")


def main() -> None:
    ap = argparse.ArgumentParser(description="DJ-Schule mit dem AKAI APC mini mk2")
    ap.add_argument("--config", default="config.toml", type=Path)
    ap.add_argument("--no-controller", action="store_true", help="ohne Hardware starten (nur Browser)")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--host")
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")

    cfg = Config.load(args.config)
    cfg.bpm = args.bpm or cfg.bpm
    cfg.host = args.host or cfg.host
    cfg.port = args.port or cfg.port

    print(f"🎵 Erzeuge Sounds ({cfg.bpm:g} BPM) …", flush=True)
    t = time.time()
    lib = Library.build(cfg.bpm, cfg.sounds_dir)
    print(f"   fertig in {time.time() - t:.1f} s – {len(lib.loops)} Loops, {len(lib.oneshots)} One-Shots")

    engine = AudioEngine(cfg.bpm, cfg.blocksize, cfg.master_max)
    device = engine.start()
    print(f"🔊 Audio: {device}")

    core = App(engine, lib, timing_offset_ms=cfg.timing_offset_ms, progress_file=cfg.progress_file)
    if not args.no_controller:
        try:
            from .controller import APCMiniMk2
            core.controller = APCMiniMk2(core.handle)
            core.controller.clear()
            print(f"🎛️  Controller: {core.controller.name}")
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  {e}\n   Weiter ohne Controller – die Oberfläche funktioniert mit Maus/Touch.")
    core.start()

    url = f"http://{'localhost' if cfg.host in ('127.0.0.1', '0.0.0.0') else cfg.host}:{cfg.port}"
    print(f"🌐 Oberfläche: {url}   (Strg+C beendet)")
    if cfg.open_browser and not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    server = uvicorn.Server(uvicorn.Config(create_server(core), host=cfg.host, port=cfg.port,
                                           log_level="warning"))
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        pass
    finally:
        core.stop()
        if core.controller is not None:
            core.controller.close()
        engine.stop()
        print("👋 Tschüss!")


if __name__ == "__main__":
    main()
