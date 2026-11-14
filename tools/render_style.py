"""Alle Loops und One-Shots eines Musikstils als WAV speichern – zum Probehören beim Klang-Basteln.

    uv run python tools/render_style.py techno            # Standard-Tempo des Stils
    uv run python tools/render_style.py acid --bpm 135

Die Dateien landen in data/vorhoeren/<stil>-<bpm>/ (wird nicht eingecheckt).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import soundfile as sf  # noqa: E402

from apc_dj.audio.library import Library  # noqa: E402
from apc_dj.audio.styles import STYLE_BY_ID  # noqa: E402
from apc_dj.audio.synth import SR  # noqa: E402
from apc_dj.layout import COLUMNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("style", choices=sorted(STYLE_BY_ID))
    ap.add_argument("--bpm", type=float)
    args = ap.parse_args()
    info = STYLE_BY_ID[args.style]
    bpm = args.bpm or info.default_bpm or 120
    lib = Library.build(bpm, None, args.style)
    out = ROOT / "data" / "vorhoeren" / f"{args.style}-{bpm:g}"
    out.mkdir(parents=True, exist_ok=True)
    for (col, var), snd in sorted(lib.loops.items()):
        sf.write(out / f"loop_{col + 1}{'ABCD'[var]}_{COLUMNS[col][0]}_{snd.id}.wav", snd.data, SR)
    for i, snd in enumerate(lib.oneshots):
        sf.write(out / f"shot_{i:02d}_{snd.id}.wav", snd.data, SR)
    print(f"{len(lib.loops)} Loops und {len(lib.oneshots)} One-Shots in {out}")


if __name__ == "__main__":
    main()
