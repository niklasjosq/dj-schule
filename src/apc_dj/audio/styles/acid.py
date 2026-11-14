"""Musikstil "Acid" – quietschende 303-Bässe mit Akzent und Slide, 808-Kuhglocke, Acid-House-Grooves."""
from __future__ import annotations

import numpy as np

from ..drums import (
    clap, clave, cowbell808, crash, hat808, impact, kick909, resonant_sweep, rim, snare808, tom808, zap,
)
from ..seq import Seq, Sound
from ..synth import SR, acid_line, echo, noise, pump, rng, sweep_filter, t_axis
from .common import (
    add_acid, acid_steps, beats_to_s, chord_hits, loop, loop_sweep, make_shots, motif, seamless,
)


def _one_acid(notes, flags, bpm, **kw) -> np.ndarray:
    """Ein kurzer Acid-Lauf als One-Shot (ein Takt, nur der erste)."""
    steps = acid_steps(notes, flags)[:16]
    return acid_line(steps, bpm, **kw)


def shots(bpm: float):
    return make_shots([
        ("kick", "Acid-Kick", "🥁", kick909(4.5, 0.8), "Eine kräftige Kick für Acid-House."),
        ("snare", "Snare", "🪘", snare808(), "Die Snare aus dem Drumcomputer – trocken und knackig."),
        ("clap", "Clap", "👏", clap(), "Ein Klatschen – auf Schlag 2 und 4."),
        ("hat", "HiHat", "🎩", hat808(False), "Die HiHat tickt metallisch."),
        ("ohat", "HiHat offen", "🎩", hat808(True), "Die offene HiHat zischt zwischen den Kicks."),
        ("tom_lo", "Tom tief", "🪘", tom808(90), "Tiefe Tom aus dem Drumcomputer."),
        ("tom_hi", "Tom hoch", "🪘", tom808(150), "Hohe Tom – gut für Wirbel."),
        ("cowbell", "Kuhglocke", "🐄", cowbell808(), "Die berühmte Drumcomputer-Kuhglocke aus zwei schiefen Tönen."),
        ("crash", "Becken", "💥", crash(), "Das Becken markiert einen neuen Abschnitt."),
        ("squelch", "Quietsch", "🫧", _one_acid("RO..............", "a...............", bpm, q=12,
                                               env_mod=3.5, decay=0.25), "Ein einzelner Acid-Ton: quiiietsch!"),
        ("slide", "Acid-Rutsch", "🛝", _one_acid("RRRRO...........", "ssss............", bpm, q=9,
                                               env_mod=3.0, decay=0.4),
         "Töne, die ineinander rutschen – das nennt man Slide."),
        ("zap", "Zap", "⚡", zap(), "Zapp! Ein Ton, der blitzschnell nach unten fällt."),
        ("boom", "Einschlag", "💣", impact(), "Ein Einschlag mit Hall – perfekt für den Drop."),
        ("riser", "Filter-Riser", "🚀", resonant_sweep(2.0), "Rauschen durch einen quietschenden Filter, der nach oben fährt."),
        ("blubb", "Blubb", "🫧", _one_acid("-...............", "a...............", bpm, q=6,
                                           env_mod=2.0, decay=0.5, cutoff=120), "Ein tiefes Acid-Blubb."),
        ("clave", "Clave", "🥢", clave(), "Zwei Hölzer, die gegeneinander schlagen: tock!"),
    ])


def drums(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("....x.......x...", d["clap"], 0.8)
    s.steps("..x...x...x...x.", d["ohat"], 0.5)
    out.append(loop("a_house", "Acid-House", "🏠", s, 0, "Ein Acid-House-Beat aus Chicago: Kick, Clap und offene HiHat."))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("xoxoxoxxxoxoxoxx", d["hat"], 0.45)
    s.steps("....x.......x...", d["snare"], 0.8)
    s.steps("............xxxx", d["snare"], 0.4, bars=[3])
    out.append(loop("a_shuffle", "Shuffle", "🕺", s, 0, "Die HiHats hüpfen – ein Beat zum Mitwippen."))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("x...x...x...x...", d["clap"], 0.35)
    s.steps("..x...x...x...x.", rim(), 0.4)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.3)
    out.append(loop("a_jack", "Jack", "🦘", s, 0, "Jacken heißt: auf jedem Schlag tanzen! Kick und Clap gleichzeitig."))

    s = Seq(bpm)
    s.steps("x......x..x.....", d["kick"])
    s.steps("........x.......", d["snare"], 0.9)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.4)
    out.append(loop("a_half", "Halbzeit", "🐢", s, 0, "Halbes Tempo-Gefühl: Die Snare kommt nur einmal pro Takt."))
    return out


def perc(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x..x..x...x..x..", d["cowbell"], 0.7, pan=0.3)
    out.append(loop("a_cowbell", "Kuhglocke", "🐄", s, 1, "Die Drumcomputer-Kuhglocke spielt einen Rhythmus zum Tanzen."))

    s = Seq(bpm)
    s.steps("x..x..x...x.x...", d["clave"], 0.8, pan=-0.3)
    s.steps("..x.......x.....", rim(), 0.5, pan=0.3)
    out.append(loop("a_clave", "Claves", "🥢", s, 1, "Holzklänge, die wie ein Uhrwerk klappern."))

    s = Seq(bpm)
    s.steps("..x...x...x...x.", d["ohat"], 0.8)
    s.steps("xo..xo..xo..xo..", d["hat"], 0.4)
    out.append(loop("a_hats", "Offene Hats", "🎩", s, 1, "Offene HiHats zwischen den Schlägen: tss – tss – tss."))

    s = Seq(bpm)
    s.steps("x..x......x.....", d["tom_lo"], 0.8, pan=-0.3)
    s.steps("......x.x....x.x", d["tom_hi"], 0.7, pan=0.3)
    out.append(loop("a_toms", "Toms", "🪘", s, 1, "Trommeln aus dem Drumcomputer – tief und hoch."))
    return out


def bass(bpm) -> list[Sound]:
    out = []
    specs = [
        ("a_zahm", "Acid zahm", "🐑", "R.RRR.R.R.RRR.RO", "a.......a.......",
         dict(cutoff=170, env_mod=2.0, q=3.5, decay=0.25), "Ein Acid-Bass mit wenig Quietschen – zum Eingewöhnen."),
        ("a_quietsch", "Acid quietschig", "🫧", "R.ROR.5RR.ROR3O5", "a..a.a..a..a.a.a",
         dict(cutoff=200, env_mod=3.2, q=10, decay=0.2), "Der Filter ist ganz weit aufgedreht: quiiietsch! Das ist Acid."),
        ("a_slide", "Acid Slide", "🛝", "RRO.R5O.RRO.3-R.", ".s.a.s..as.a.s..",
         dict(cutoff=190, env_mod=2.8, q=8, decay=0.3), "Bei einem Slide rutscht ein Ton in den nächsten – wie auf einer Rutsche."),
        ("a_oktaven", "Acid Oktaven", "🪜", "ROROROROROROR5O3", "a.a...a.a...a.a.",
         dict(cutoff=180, env_mod=2.6, q=7, decay=0.18), "Tief, hoch, tief, hoch: Der Acid-Bass springt in Oktaven."),
    ]
    for sid, label, emoji, notes, flags, kw, info in specs:
        s = Seq(bpm)
        add_acid(s, notes, flags, octave=-12, **kw)
        s.buf = pump(s.buf, s.beat, 0.25)
        out.append(loop(sid, label, emoji, s, 2, info))
    return out


def chords(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    chord_hits(s, "stab", [0.5, 1.75, 2.5, 3.5], 0.25, seventh=True, spread=0.4)
    out.append(loop("a_stabs", "Acid-Stabs", "🔪", s, 3, "Kurze Akkord-Stöße wie in alten Acid-House-Platten."))

    s = Seq(bpm)
    chord_hits(s, "pad", [0], 3.9, spread=0.5)
    loop_sweep(s, np.array([400, 2500, 600, 3500, 400, 2500, 600, 3500, 400]), 6.0)
    out.append(loop("a_squelchchords", "Quietsch-Akkorde", "🌊", s, 3,
                    "Akkorde durch einen Filter, der auf und zu geht – wie eine Welle."))

    s = Seq(bpm)
    chord_hits(s, "orgel", [0, 0.75, 1.5, 2.5, 3.25], 0.4, spread=0.3)
    out.append(loop("a_orgel", "House-Orgel", "⛪", s, 3, "Eine House-Orgel mit hüpfendem Rhythmus."))

    s = Seq(bpm)
    chord_hits(s, "pad", [0], 3.9, seventh=True, spread=0.6)
    s.buf = pump(s.buf, s.beat, 0.6, 0.22)
    out.append(loop("a_pad", "Fläche", "☁️", s, 3, "Weiche Akkorde, die mit der Kick atmen."))
    return out


def arps(bpm) -> list[Sound]:
    out = []
    specs = [
        ("a_hoch", "Acid hoch", "⬆️", "R5OR5OR5OR5OR5OR", "a..a..a..a..a..a", [-0.8, 0.2, 1.2, 2.0], 9,
         "Eine hohe Acid-Tonfolge: Der Filter öffnet sich über 4 Takte."),
        ("a_spirale", "Acid-Spirale", "🌀", "RO3O5ORO3O5OROTO", "a.s.a.s.a.s.a.s.", [1.5, 0.0, 1.5, 0.0], 11,
         "Eine Spirale aus Tönen: Der Filter geht auf und zu."),
        ("a_treppe", "Acid-Treppe", "🪜", "R.3.5.O.R.3.5.O.", "a...a...a...a...", [-0.5, 0.5, 1.0, 2.2], 8,
         "Wie eine Treppe: Ton für Ton nach oben."),
        ("a_echo", "Acid-Echo", "🗣️", "R..O..5..R..3...", "a..s..a..a..s...", [0.5, 1.2, 0.5, 1.8], 10,
         "Wenige Acid-Töne mit Echo – sie springen durch den Raum."),
    ]
    for sid, label, emoji, notes, flags, macro, q, info in specs:
        s = Seq(bpm)
        add_acid(s, notes, flags, octave=12, cutoff=320, env_mod=2.4, q=q, decay=0.14, macro=macro)
        if sid == "a_echo":
            s.buf = echo(s.buf, beats_to_s(bpm, 0.75), 0.5, 4, 3000, 0.5)[:len(s.buf)].astype(np.float32)
        out.append(loop(sid, label, emoji, s, 4, info))
    return out


def leads(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    motif(s, "squelch", [(0, 2, 0.5), (0.75, 3, 0.5), (1.5, 2, 0.5), (2.5, 4, 1.0)], 12)
    out.append(loop("a_squelchlead", "Quietsch-Lead", "🫧", s, 5, "Eine Melodie, die quietscht und blubbert."))

    s = Seq(bpm)
    motif(s, "acid", [(0, 0, 0.5), (0.5, 2, 0.5), (1, 3, 0.75)], 12)  # Ruf
    motif(s, "acid", [(2, 4, 0.5), (2.5, 3, 0.5), (3, 2, 0.75)], 12, pan=0.3)  # Antwort
    out.append(loop("a_ruf", "Ruf und Antwort", "📣", s, 5, "Eine Melodie fragt, eine andere antwortet – wie ein Gespräch."))

    s = Seq(bpm)
    motif(s, "blip", [(0, 3, 0.25), (0.5, 4, 0.25), (1.25, 2, 0.25), (2, 3, 0.25), (3, 5, 0.25)], 12)
    out.append(loop("a_blip", "Blip-Melodie", "💠", s, 5, "Kurze Piepser, die eine Melodie spielen."))

    s = Seq(bpm)
    motif(s, "lead", [(0, 2, 1.5), (2, 1, 0.75), (3, 0, 0.75)], 12)
    out.append(loop("a_lead", "Synth-Melodie", "🎶", s, 5, "Eine einfache Synth-Melodie zum Mitsummen."))
    return out


def fx(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    n = len(s.buf)
    t = np.arange(n) / SR
    k = t / t[-1]
    cut = 200 * 30 ** np.sin(np.pi * k)
    s.add(0, sweep_filter(noise(n / SR), cut, q=10) * np.sin(np.pi * k))
    out.append(loop("a_welle", "Filter-Welle", "🌊", s, 6, "Rauschen durch einen quietschenden Filter: rauf und wieder runter."))

    s = Seq(bpm)
    g = rng()
    for _ in range(10):
        s.add(int(g.integers(0, 64)) / 4, d["squelch"], 0.6, float(g.uniform(-0.7, 0.7)))
    out.append(loop("a_squelchfx", "Quietsch-FX", "🫧", s, 6, "Zufällige Acid-Quietscher, überall im Raum."))

    s = Seq(bpm)
    n = len(s.buf)
    tt = t_axis((n + int(SR)) / SR)
    x = acid_line([(33, False, True)] * 64, bpm, cutoff=150, env_mod=0.5, q=6, decay=2.0, gate=1.0)
    x = np.pad(x, (0, max(0, len(tt) - len(x))))[:len(tt)]
    s.add(0, seamless(x, n, 0.8))
    loop_sweep(s, np.array([200, 900, 300, 1400, 200]), 4.0)
    out.append(loop("a_drone", "Acid-Drone", "🌑", s, 6, "Ein tiefer Acid-Dauerton, dessen Filter langsam wandert."))

    s = Seq(bpm)
    s.add(0, d["boom"])
    s.add(0, d["riser"][::-1] * np.linspace(1, 0, len(d["riser"])), 0.5)
    out.append(loop("a_impact", "Einschlag", "💥", s, 6, "Ein Einschlag auf der Eins – alle 4 Takte."))
    return out


def build(bpm: float):
    oneshots, raw = shots(bpm)
    columns = [drums(bpm, raw), perc(bpm, raw), bass(bpm), chords(bpm), arps(bpm), leads(bpm), fx(bpm, raw)]
    return oneshots, columns
