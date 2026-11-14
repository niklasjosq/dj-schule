"""Musikstil "Hip-Hop" – Boom-Bap, Lo-Fi und Trap: staubige Drums mit Swing, E-Piano, 808-Bass, Scratches.

Alle Loops dieses Stils haben denselben Swing (die zweite Sechzehntel kommt etwas später) – so grooven sie
zusammen. Alle Melodien sind eigene Erfindungen.
"""
from __future__ import annotations

import numpy as np

from ..drums import (
    airhorn, baby_scratch, clap, crackle, crash, hat808, kick808, kick_dusty, rewind, rim, scratch,
    shaker, snare_boombap, tom808, uplifter,
)
from ..seq import Seq, Sound
from ..synth import SR, echo, fm, lowpass, noise, pump, t_axis
from .common import (
    add_acid, arp, bass_line, beats_to_s, chord_hits, loop, make_shots, motif, seamless,
)

SWING = 0.22  # Anteil einer Sechzehntel, um den jede zweite Sechzehntel später kommt


def _seq(bpm: float) -> Seq:
    return Seq(bpm, swing=SWING)


def _bell() -> np.ndarray:
    t = t_axis(0.6)
    return fm(1568, len(t), 3.5, 1.5, 10) * np.exp(-t * 6)


def shots(bpm: float):
    return make_shots([
        ("kick", "Boom-Kick", "🥁", kick_dusty(), "Die Hip-Hop-Kick: rund und ein bisschen staubig – BOOM."),
        ("snare", "Snare", "🪘", snare_boombap(), "Die fette Hip-Hop-Snare auf 2 und 4 – BAP!"),
        ("clap", "Clap", "👏", clap(), "Ein Klatschen – im Trap kommt es auf Schlag 3."),
        ("hat", "HiHat", "🎩", lowpass(hat808(False), 9000), "Die HiHat tickt mit Swing – das groovt!"),
        ("ohat", "HiHat offen", "🎩", lowpass(hat808(True), 9000), "Die offene HiHat zischt am Ende vom Takt."),
        ("tom", "Tom tief", "🪘", tom808(90), "Eine tiefe Trommel."),
        ("rim", "Rimshot", "🥢", rim(), "Ein Schlag auf den Trommelrand: klack!"),
        ("bell", "Glöckchen", "🔔", _bell(), "Ein helles Glöckchen – beliebt in Trap-Beats."),
        ("crash", "Becken", "💥", crash(), "Das Becken markiert einen neuen Abschnitt."),
        ("scratch", "Scratch", "💿", scratch(), "Der Klassiker: Die Platte wird vor und zurück geschoben."),
        ("scratch2", "Baby-Scratch", "📀", baby_scratch(), "Ein schneller, kurzer Scratch – zick-zick!"),
        ("airhorn", "Airhorn", "📯", airhorn(), "Das Airhorn – sparsam einsetzen!"),
        ("boom", "808-Boom", "💣", kick808(1.6), "Ein riesiger 808-Bass-Schlag. Spürst du ihn?"),
        ("riser", "Riser", "🚀", uplifter(2.0), "Rauschen, das nach oben steigt – gleich kommt der Drop!"),
        ("rewind", "Rückspulen", "⏪", rewind(), "Rewind! Der DJ dreht die Platte zurück – nochmal von vorn!"),
        ("crackle", "Knistern", "📻", crackle(1.0), "So knistert eine alte Schallplatte."),
    ])


def drums(bpm, d) -> list[Sound]:
    out = []
    s = _seq(bpm)
    s.steps("x.........x.x...", d["kick"])
    s.steps("....x.......x...", d["snare"])
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.5)
    s.steps("..............x.", d["ohat"], 0.4, bars=[1, 3])
    out.append(loop("h_boombap", "Boom-Bap", "🥁", s, 0,
                    "Boom-Bap: Kick (BOOM) und Snare (BAP) – so klingt Hip-Hop aus New York!"))

    s = _seq(bpm)
    s.steps("x......x..x.....", d["kick"], 0.8)
    s.steps("....x.......x...", d["snare"], 0.7)
    s.steps("..........o.....", d["rim"], 0.6)
    s.steps("x.oox.oox.oox.oo", d["hat"], 0.35)
    s.buf = lowpass(s.buf.T, 5000).T.astype(np.float32)
    out.append(loop("h_lofi", "Lo-Fi", "☕", s, 0, "Lo-Fi-Hip-Hop: weich und gemütlich – Musik zum Lernen und Entspannen."))

    s = _seq(bpm)
    s.steps("x.......x..x....", d["kick"])
    s.steps("........x.......", d["clap"])
    s.steps("xxxxxxxxxxxxxxxx", d["hat"], 0.35)
    for b in range(4):  # Trap-HiHat-Wirbel in Zweiunddreißigsteln
        for k in range(4):
            s.add(b * 4 + 3 + k / 8, d["hat"], 0.3 + 0.1 * k)
    s.steps("......x.........", d["ohat"], 0.4, bars=[1, 3])
    out.append(loop("h_trap", "Trap", "🧊", s, 0, "Trap: harte Kick, Clap auf 3 und superschnelle HiHat-Wirbel."))

    s = _seq(bpm)
    s.steps("x..x..x...x.....", d["kick"])
    s.steps("....x.......x...", d["clap"], 0.9)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.45)
    out.append(loop("h_oldschool", "Old-School", "📼", s, 0, "Old-School-Hip-Hop aus den 80ern – mit Drumcomputer!"))
    return out


def perc(bpm, d) -> list[Sound]:
    out = []
    s = _seq(bpm)
    s.steps("oxoxoxoxoxoxoxox", shaker(), 0.9)
    out.append(loop("h_shaker", "Shaker", "🧂", s, 1, "Ein Shaker mit Swing – er wackelt ein bisschen hinterher."))

    s = _seq(bpm)
    s.steps("..x..x....x..x.x", d["rim"], 0.8, pan=-0.3)
    out.append(loop("h_rim", "Rimshots", "🥢", s, 1, "Klackende Rimshots zwischen Kick und Snare."))

    s = _seq(bpm)
    s.steps("x..x......x.....", tom808(140), 0.8, pan=-0.3)
    s.steps("......x.x....x.x", tom808(200), 0.7, pan=0.3)
    out.append(loop("h_conga", "Bongos", "🪘", s, 1, "Hohe und tiefe Trommeln wie Bongos."))

    s = _seq(bpm)
    s.steps("x.x.x.x.x.x.x.x.", d["bell"], 0.35, pan=0.3)
    s.steps("....x.......x...", d["ohat"], 0.4)
    out.append(loop("h_bells", "Glöckchen", "🔔", s, 1, "Helle Glöckchen auf jeder Achtel."))
    return out


def bass(bpm) -> list[Sound]:
    out = []
    s = _seq(bpm)
    add_acid(s, "R.......R.R.....", "s.......s.......", octave=-12, wave="sine", cutoff=4000, env_mod=0,
             q=0.7, decay=1.0, gate=0.95, glide=0.07, drive_amt=1.6)
    out.append(loop("h_808", "808-Bass", "🔊", s, 2, "Der 808-Bass: ganz tief und lang – er rutscht von Ton zu Ton."))

    s = _seq(bpm)
    bass_line(s, "sub", "R.........R.R...", 0.6, octave=-12)
    out.append(loop("h_boombass", "Boom-Bass", "🫀", s, 2, "Ein runder Bass, der genau mit der Kick spielt."))

    s = _seq(bpm)
    bass_line(s, "pluck", "R.3.5.O.R.5.3.-.", 0.45, octave=-12)
    s.buf = lowpass(s.buf.T, 900).T.astype(np.float32)
    out.append(loop("h_kontrabass", "Kontrabass", "🎻", s, 2, "Ein gezupfter Bass wie im Jazz – er läuft durch die Akkorde."))

    s = _seq(bpm)
    bass_line(s, "bass", "R..R..O.R..5.R3.", 0.22, octave=-12)
    out.append(loop("h_funk", "Funk-Bass", "🕺", s, 2, "Ein hüpfender Funk-Bass – viele Hip-Hop-Beats leihen sich Funk."))
    return out


def chords(bpm) -> list[Sound]:
    out = []
    s = _seq(bpm)
    chord_hits(s, "epiano", [0, 1.75, 2.5], 1.2, gain=0.5, seventh=True, spread=0.4)
    out.append(loop("h_epiano", "E-Piano", "🎹", s, 3, "Ein weiches E-Piano mit Jazz-Akkorden – sehr gemütlich."))

    s = _seq(bpm)
    chord_hits(s, "lofi_klavier", [0, 2.5], 1.8, gain=0.5, seventh=True)
    out.append(loop("h_lofipiano", "Lo-Fi-Klavier", "📻", s, 3, "Klavier wie von einer alten Kassette: dumpf und leiernd."))

    s = _seq(bpm)
    chord_hits(s, "pad", [0], 3.9, gain=0.5, seventh=True, spread=0.6)
    s.buf = lowpass(s.buf.T, 1800).T.astype(np.float32)
    out.append(loop("h_strings", "Streicher", "🎻", s, 3, "Weiche Streicher-Akkorde im Hintergrund."))

    s = _seq(bpm)
    chord_hits(s, "epiano", [0.75, 1.5, 3.25], 0.3, gain=0.5, seventh=True, spread=0.3)
    out.append(loop("h_jazzstabs", "Jazz-Stabs", "🎷", s, 3, "Kurze Jazz-Akkorde zwischen den Schlägen."))
    return out


def arps(bpm) -> list[Sound]:
    out = []
    s = _seq(bpm)
    arp(s, "glocke", [0, 1, 2, 3, 2, 1], 0.5, 0.45, 24, gain=0.6)
    out.append(loop("h_musicbox", "Spieluhr", "🎠", s, 4, "Eine Spieluhr spielt die Akkordtöne – zart und hell."))

    s = _seq(bpm)
    arp(s, "pluck", [0, 1, 2, 3, 4, 5], 0.25, 0.3, 12, pan_width=0.4)
    out.append(loop("h_harp", "Harfe", "🪕", s, 4, "Wie eine Harfe: Töne perlen nach oben."))

    s = _seq(bpm)
    arp(s, "epiano", [0, 2, 1, 3], 0.5, 0.45, 12, seventh=True)
    out.append(loop("h_eparp", "E-Piano-Arp", "✨", s, 4, "Das E-Piano spielt die Akkordtöne nacheinander."))

    s = _seq(bpm)
    arp(s, "pluck", [0, 2, 4], 0.5, 0.2, 12, pattern="x.x.x..x")
    s.buf = echo(s.buf, beats_to_s(bpm, 0.75), 0.45, 3, 3500, 0.45)[:len(s.buf)].astype(np.float32)
    out.append(loop("h_pizz", "Pizzicato", "🎶", s, 4, "Kurz gezupfte Töne mit Echo."))
    return out


def leads(bpm) -> list[Sound]:
    out = []
    s = _seq(bpm)
    motif(s, "flute", [(0, 3, 0.75), (1, 2, 0.5), (1.5, 1, 1.0), (3, 2, 0.75)], 12, seventh=True)
    out.append(loop("h_flute", "Lo-Fi-Flöte", "🪈", s, 5, "Eine gemütliche Flöte – typisch für Lo-Fi-Hip-Hop."))

    s = _seq(bpm)
    motif(s, "whistle", [(0, 3, 1.5), (2, 4, 0.5), (2.5, 3, 0.5), (3, 2, 0.75)], 12)
    out.append(loop("h_whistle", "Pfeif-Synth", "😗", s, 5, "Ein pfeifender Synth, der in die Töne rutscht – wie im West-Coast-Hip-Hop."))

    s = _seq(bpm)
    motif(s, "vokal", [(0, 0, 0.25), (0.75, 1, 0.25), (1.5, 2, 0.5), (2.5, 1, 0.25), (3.25, 0, 0.25)], 0)
    out.append(loop("h_chops", "Vocal-Chops", "✂️", s, 5, "Zerschnipselte Stimmen – ein Trick aus der Hip-Hop-Werkstatt."))

    s = _seq(bpm)
    motif(s, "glocke", [(0, 3, 0.25), (0.5, 3, 0.25), (1, 4, 0.25), (1.5, 2, 0.5), (2.5, 3, 0.25), (3, 1, 0.5)], 12)
    out.append(loop("h_trapbell", "Trap-Glocke", "🔔", s, 5, "Eine helle Glocken-Melodie – typisch für Trap."))
    return out


def fx(bpm, d) -> list[Sound]:
    out = []
    s = _seq(bpm)
    n = len(s.buf)
    s.add(0, seamless(np.tanh(4 * crackle((n + int(SR)) / SR)), n, 0.5))  # Knackser etwas zähmen
    out.append(loop("h_crackle", "Knistern", "📻", s, 6, "Eine knisternde Schallplatte – das macht den Lo-Fi-Sound."))

    s = _seq(bpm)
    for b in (1, 3):
        s.add(b * 4 + 3, d["scratch"], 0.8)
    s.add(6, d["scratch2"], 0.7)
    out.append(loop("h_scratches", "Scratches", "💿", s, 6, "Der DJ scratcht am Ende jedes zweiten Takts."))

    s = _seq(bpm)
    s.add(16 - 0.9 * bpm / 60, d["rewind"])  # endet genau am Ende der Loop
    s.add(0, d["crash"], 0.5)
    out.append(loop("h_rewind", "Rückspulen", "⏪", s, 6, "Am Ende spult der DJ zurück – und alles fängt von vorne an!"))

    s = _seq(bpm)
    n = len(s.buf)
    rain = lowpass(noise((n + int(SR)) / SR), 2500) * 0.4
    s.add(0, seamless(rain, n, 0.8))
    s.add(0, crackle(s.seconds) * 0.5)
    s.buf = pump(s.buf, s.beat * 4, 0.3, 1.0)
    out.append(loop("h_rain", "Regen", "🌧️", s, 6, "Regen vor dem Fenster – gemütliche Lo-Fi-Stimmung."))
    return out


def build(bpm: float):
    oneshots, raw = shots(bpm)
    columns = [drums(bpm, raw), perc(bpm, raw), bass(bpm), chords(bpm), arps(bpm), leads(bpm), fx(bpm, raw)]
    return oneshots, columns
