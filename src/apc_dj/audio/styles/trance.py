"""Musikstil "Trance/Rave" – Supersaw-Akkorde, Hoover, rollender Offbeat-Bass, Gates und Uplifter."""
from __future__ import annotations

import numpy as np

from ..drums import (
    clap_room, crash, downlifter, hat808, impact, kick909, laser, metal6, rave_stab, ride, shaker, snare909,
    snare_roll, tom808, uplifter,
)
from ..seq import Seq, Sound
from ..synth import SR, highpass, lowpass, noise, pump, render_note, t_axis
from .common import (
    arp, bass_line, chord_hits, gate, loop, loop_sweep, make_shots, motif, seamless,
)


def _tamb() -> np.ndarray:
    """Tamburin: helle Schellen (Metall) + Rascheln."""
    t = t_axis(0.18)
    x = highpass(metal6(0.18, 2.3), 6000) * np.exp(-t * 25)
    sh = shaker()
    return 0.4 * x / max(np.abs(x).max(), 1e-9) + 0.6 * np.pad(sh, (0, len(t) - len(sh)))


def shots(bpm: float):
    hoover_hit = render_note("hoover", 45, 0.5)
    return make_shots([
        ("kick", "Trance-Kick", "🥁", kick909(4.0, 1.2), "Eine kräftige Kick mit viel Druck – sie treibt den Trance an."),
        ("snare", "Snare", "🪘", snare909(), "Eine helle Snare – gut für Wirbel vor dem Höhepunkt."),
        ("clap", "Clap", "👏", clap_room(), "Ein Clap mit Hall – wie in einer riesigen Halle."),
        ("hat", "HiHat", "🎩", hat808(False), "Die HiHat tickt zwischen den Schlägen."),
        ("ohat", "HiHat offen", "🎩", hat808(True), "Die offene HiHat zischt auf dem Offbeat: un-TS, un-TS!"),
        ("tom_lo", "Tom tief", "🪘", tom808(100), "Eine tiefe Trommel."),
        ("tom_hi", "Tom hoch", "🪘", tom808(170), "Eine hohe Trommel."),
        ("ride", "Ride", "🛎️", ride(), "Das Ride-Becken klingelt hell und lang."),
        ("crash", "Becken", "💥", crash(), "Das Becken markiert den Höhepunkt: KSSSHHH!"),
        ("ravestab", "Rave-Stab", "🎺", rave_stab(), "Ein Akkord-Schlag wie auf den ersten Rave-Partys."),
        ("hoover", "Hoover", "🌀", hoover_hit.mean(axis=1), "Der Hoover heult wie ein Staubsauger – berühmt aus den 90ern."),
        ("laser", "Laser", "🔦", laser(), "Piuuu! Ein Laser-Strahl aus dem Synthesizer."),
        ("boom", "Einschlag", "💣", impact(), "Ein Einschlag mit Hall – für den Drop."),
        ("riser", "Uplifter", "🚀", uplifter(2.0), "Rauschen, das nach oben steigt. Gleich kommt der Höhepunkt!"),
        ("down", "Downlifter", "🛬", downlifter(2.0), "Rauschen, das nach unten fällt – wie eine Landung."),
        ("roll", "Wirbel", "🥁", snare_roll(2.0), "Ein Trommelwirbel, der immer schneller wird. Brrrrrr!"),
    ])


def drums(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("..x...x...x...x.", d["ohat"], 0.6)
    s.steps("....x.......x...", d["clap"], 0.6)
    s.steps("xoxoxoxoxoxoxoxo", d["hat"], 0.25)
    out.append(loop("tr_beat", "Trance-Beat", "🥁", s, 0, "Kick auf jedem Schlag, offene HiHat dazwischen: un-TS, un-TS!"))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("x.x.x.x.x.x.x.x.", d["snare"], 0.35, bars=[0])
    s.steps("x.x.x.x.x.x.x.x.", d["snare"], 0.5, bars=[1])
    s.steps("xxxxxxxxxxxxxxxx", d["snare"], 0.6, bars=[2])
    for i in range(32):  # letzter Takt: Zweiunddreißigstel, immer lauter
        s.add(12 + i / 8, d["snare"], 0.4 + 0.6 * i / 31)
    out.append(loop("tr_wirbel", "Wirbel-Aufbau", "📈", s, 0,
                    "Die Snare wird immer schneller: Achtel, Sechzehntel, Zweiunddreißigstel – und dann der Drop!"))

    s = Seq(bpm)
    s.steps("x.........x.....", d["kick"])
    s.steps("....x..o.o..x..o", d["snare"], 0.9)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.45)
    s.steps("..x.......x.....", d["ohat"], 0.3)
    out.append(loop("tr_break", "Rave-Break", "💃", s, 0, "Ein Breakbeat wie auf den Rave-Partys der 90er – zappelig und schnell."))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("..x...x...x...x.", d["hat"], 0.6)
    out.append(loop("tr_kick", "Nur Kick", "💓", s, 0, "Nur Kick und HiHat – Platz für Akkorde und Melodie."))
    return out


def perc(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("..x...x...x...x.", d["clap"], 0.6)
    out.append(loop("tr_offclap", "Offbeat-Claps", "👏", s, 1, "Claps zwischen den Kicks – das schiebt nach vorne."))

    s = Seq(bpm)
    s.steps("x.x.x.x.x.x.x.x.", d["ride"], 0.7)
    out.append(loop("tr_ride", "Ride", "🛎️", s, 1, "Das Ride-Becken klingelt auf jeder Achtel."))

    s = Seq(bpm)
    s.steps("oxoxoxoxoxoxoxox", shaker(), 0.9)
    out.append(loop("tr_shaker", "Shaker", "🧂", s, 1, "Ein schneller Shaker – wie eine Dose voller Reis."))

    s = Seq(bpm)
    s.steps("..x.x.x...x.x.xx", _tamb(), 0.8, pan=0.3)
    s.steps("x.......x.......", d["tom_hi"], 0.4, pan=-0.3)
    out.append(loop("tr_tamb", "Tamburin", "🪇", s, 1, "Ein klingelndes Tamburin und hohe Trommeln."))
    return out


def bass(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    bass_line(s, "bass", ".RRR.RRR.RRR.RRR", 0.2, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.55)
    out.append(loop("tr_rolling", "Rollender Bass", "🌀", s, 2, "Der typische Trance-Bass: drei Töne zwischen jeder Kick."))

    s = Seq(bpm)
    bass_line(s, "hoover", "R.......R...O...", 0.9, octave=-12)
    s.buf = lowpass(s.buf.T, 1200).T.astype(np.float32)
    s.buf = pump(s.buf, s.beat, 0.4)
    out.append(loop("tr_hooverbass", "Hoover-Bass", "🌪️", s, 2, "Ein heulender Hoover-Bass – sehr laut und sehr rave!"))

    s = Seq(bpm)
    bass_line(s, "sub", "..R...R...R...R.", 0.45, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.7)
    out.append(loop("tr_sub", "Sub-Bass", "🫀", s, 2, "Ein tiefer, runder Bass zwischen den Kicks."))

    s = Seq(bpm)
    bass_line(s, "bass", "..R...O...R...O.", 0.4, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.5)
    out.append(loop("tr_oktav", "Oktav-Bass", "🪜", s, 2, "Der Bass springt zwischen tief und hoch."))
    return out


def chords(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    chord_hits(s, "supersaw", [0], 3.9, gain=0.45)
    s.buf = pump(s.buf, s.beat, 0.75, 0.2)
    out.append(loop("tr_supersaw", "Supersaw", "🌈", s, 3,
                    "Supersaw: sieben verstimmte Klänge auf einmal – riesig und breit! Sie pumpen mit der Kick."))

    s = Seq(bpm)
    chord_hits(s, "pad", [0], 3.95, seventh=True, spread=0.5)
    gate(s, "x.xx.x.xx.xx.x.x")
    out.append(loop("tr_gate", "Gate-Fläche", "✂️", s, 3, "Eine Fläche, die rhythmisch an- und ausgeschaltet wird: Trance-Gate!"))

    s = Seq(bpm)
    chord_hits(s, "pluck", [0, 0.75, 1.5, 2.5, 3.25], 0.3, octave=12, spread=0.4)
    out.append(loop("tr_pluck", "Pluck-Akkorde", "🪕", s, 3, "Gezupfte Akkorde im Trance-Rhythmus."))

    s = Seq(bpm)
    chord_hits(s, "klavier", [0, 1.5, 3], 1.2, seventh=True)
    out.append(loop("tr_piano", "Rave-Klavier", "🎹", s, 3, "Klavier-Akkorde wie in einer Rave-Hymne."))
    return out


def arps(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    arp(s, "pluck", [0, 1, 2, 3, 2, 1], 0.25, 0.22, 12, pan_width=0.5)
    s.buf = pump(s.buf, s.beat, 0.4)
    out.append(loop("tr_arp", "Trance-Arp", "✨", s, 4, "Der klassische Trance-Arp: schnelle Akkordtöne rauf und runter."))

    s = Seq(bpm)
    arp(s, "supersaw", [0, 2, 1, 3], 0.25, 0.2, 12, gain=0.6)
    loop_sweep(s, np.array([1200, 6000, 1200, 8000, 1200]), 1.2)
    out.append(loop("tr_sawarp", "Supersaw-Arp", "🌈", s, 4, "Ein Arpeggio aus Supersaws, mit einem Filter, der auf und zu geht."))

    s = Seq(bpm)
    arp(s, "glocke", [0, 1, 2, 3], 0.5, 0.45, 12, pan_width=0.4)
    out.append(loop("tr_bellarp", "Glocken-Arp", "🔔", s, 4, "Glocken, die die Akkordtöne nacheinander spielen."))

    s = Seq(bpm)
    arp(s, "chip_square", [0, 1, 2, 3, 4, 3, 2, 1], 0.25, 0.2, 12)
    out.append(loop("tr_squarearp", "Rechteck-Arp", "🟦", s, 4, "Ein schneller Arp mit Rechteck-Klang."))
    return out


def leads(bpm) -> list[Sound]:
    out = []
    anthem = [(0, 3, 1.5), (1.5, 2, 0.5), (2, 1, 1.0), (3, 2, 1.0),
              (4, 3, 1.5), (5.5, 4, 0.5), (6, 3, 1.0), (7, 2, 1.0),
              (8, 4, 1.5), (9.5, 3, 0.5), (10, 2, 1.0), (11, 3, 1.0),
              (12, 2, 1.0), (13, 3, 1.0), (14, 4, 2.0)]
    s = Seq(bpm)
    motif(s, "supersaw", anthem, 12, gain=0.8, per_bar=False)
    out.append(loop("tr_anthem", "Hymne", "🏟️", s, 5, "Eine große Melodie zum Arme-Hochreißen – die Trance-Hymne!"))

    s = Seq(bpm)
    motif(s, "hoover", [(0, 2, 1.0), (1.5, 1, 0.5), (2, 0, 1.5)], 12)
    out.append(loop("tr_hoover", "Hoover-Lead", "🌀", s, 5, "Ein heulender Hoover spielt die Melodie."))

    s = Seq(bpm)
    motif(s, "pluck", [(0, 3, 0.4), (0.5, 4, 0.4), (1, 3, 0.4), (1.75, 2, 0.4), (2.5, 3, 0.4), (3, 5, 0.4),
                       (3.5, 4, 0.4)], 12)
    out.append(loop("tr_pluck", "Pluck-Melodie", "🪕", s, 5, "Eine gezupfte Melodie, schnell und fröhlich."))

    s = Seq(bpm)
    motif(s, "vokal", [(0, 1, 3.8)], 0, per_bar=True)
    out.append(loop("tr_ooh", "Ooh-Chor", "🗣️", s, 5, "Eine Computer-Stimme singt lange Töne: Oooh!"))
    return out


def fx(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.add(0, uplifter(s.seconds))
    s.add(0, snare_roll(s.seconds) * np.linspace(0, 1, int(s.seconds * SR)) ** 2, 0.4)
    out.append(loop("tr_up", "Uplifter", "🚀", s, 6, "Rauschen und ein Wirbel steigen 4 Takte lang. Danach: Höhepunkt!"))

    s = Seq(bpm)
    s.add(0, d["boom"])
    s.add(0, downlifter(s.seconds / 2), 0.8)
    out.append(loop("tr_down", "Downlifter", "🛬", s, 6, "Ein Einschlag, danach fällt das Rauschen nach unten."))

    s = Seq(bpm)
    n = len(s.buf)
    x = noise((n + int(SR)) / SR)
    s.add(0, seamless(lowpass(x, 3000) * 0.5, n, 0.8))
    loop_sweep(s, np.array([300, 4000, 800, 6000, 300]), 3.0)
    out.append(loop("tr_noise", "Rausch-Welle", "🌬️", s, 6, "Weißes Rauschen wie Meeresrauschen – mit einem Filter, der wandert."))

    s = Seq(bpm)
    s.add(0, d["boom"])
    s.add(0, d["crash"], 0.6)
    s.add(0, d["ravestab"], 0.6)
    out.append(loop("tr_impact", "Höhepunkt", "💥", s, 6, "Einschlag, Becken und Rave-Stab auf der Eins – alle 4 Takte."))
    return out


def build(bpm: float):
    oneshots, raw = shots(bpm)
    columns = [drums(bpm, raw), perc(bpm, raw), bass(bpm), chords(bpm), arps(bpm), leads(bpm), fx(bpm, raw)]
    return oneshots, columns
