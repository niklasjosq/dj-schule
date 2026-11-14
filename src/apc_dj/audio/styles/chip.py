"""Musikstil "Electro/8-Bit" – 808-Electro und Klänge wie aus alten Spielkonsolen (Rechteck, Dreieck, Rauschen).

Alle Melodien sind eigene Erfindungen.
"""
from __future__ import annotations

import numpy as np

from ..drums import (
    chip_kick, chip_laser, chip_noise, chip_riser, clap, coin, cowbell808, explosion, gameover, hat808, jump,
    kick808, powerup, snare808, tom808,
)
from ..seq import Seq, Sound
from ..synth import SR, crush, echo, lowpass, osc_pulse, rng, t_axis
from .common import (
    add_acid, arp, bass_line, beats_to_s, chord_hits, chord_note, loop, make_shots, motif, seamless,
)


def shots(bpm: float):
    return make_shots([
        ("kick", "808-Kick", "🥁", kick808(0.9), "Die 808-Kick: tief und lang – sie brummt richtig nach."),
        ("snare", "808-Snare", "🪘", snare808(), "Die Snare aus dem berühmten Drumcomputer 808."),
        ("clap", "Clap", "👏", clap(), "Ein Klatschen – auf Schlag 2 und 4."),
        ("hat", "HiHat", "🎩", hat808(False), "Die 808-HiHat: kurz und metallisch."),
        ("ohat", "HiHat offen", "🎩", hat808(True), "Die offene 808-HiHat zischt länger."),
        ("tom_lo", "Tom tief", "🪘", tom808(85), "Eine tiefe 808-Tom: bumm."),
        ("tom_hi", "Tom hoch", "🪘", tom808(140), "Eine hohe 808-Tom: dumm."),
        ("cowbell", "Kuhglocke", "🐄", cowbell808(), "Die 808-Kuhglocke – ein Klassiker im Electro."),
        ("crash", "Rausch-Becken", "💥", chip_noise(1.2, 12000, 3), "Ein Becken aus dem Rausch-Kanal einer alten Konsole."),
        ("coin", "Münze", "🪙", coin(), "Pling! Wie wenn man im Spiel eine Münze einsammelt."),
        ("jump", "Sprung", "🦘", jump(), "Hopp! Ein Sprung-Geräusch aus einem alten Videospiel."),
        ("powerup", "Power-Up", "⭐", powerup(), "Ein Power-Up: Töne, die ganz schnell nach oben klettern."),
        ("boom", "Explosion", "💥", explosion(), "Eine 8-Bit-Explosion: krrrschhh!"),
        ("riser", "8-Bit-Riser", "🚀", chip_riser(2.0), "Ein Arpeggio, das immer höher und schneller wird."),
        ("gameover", "Game Over", "👻", gameover(), "Oh nein – Game Over! Die Töne fallen nach unten."),
        ("laser", "Laser", "⚡", chip_laser(), "Ein Laser aus der Spielkonsole: piuu!"),
    ])


def drums(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x.....x...x.....", d["kick"])
    s.steps("....x.......x...", d["snare"], 0.9)
    s.steps("xoxoxoxoxoxoxoxo", d["hat"], 0.4)
    s.steps("..........x..x..", d["cowbell"], 0.4, bars=[1, 3])
    out.append(loop("c_electro", "Electro-Break", "🤖", s, 0, "Electro wie in den 80ern: 808-Kick, Snare und Kuhglocke."))

    s = Seq(bpm)
    ck, cs, ch = chip_kick(), chip_noise(0.18, 6000, 18), chip_noise(0.05, 15000, 60)
    s.steps("x...x...x...x...", ck)
    s.steps("....x.......x...", cs, 0.8)
    s.steps("x.x.x.x.x.x.x.x.", ch, 0.5)
    out.append(loop("c_chipbeat", "Chip-Beat", "👾", s, 0, "Ein Beat nur aus Konsolen-Klängen: Dreieck-Kick und Rauschen."))

    s = Seq(bpm)
    s.steps("x......x..x.....", d["kick"])
    s.steps("........x.......", d["clap"], 0.9)
    s.steps("xoxoxoxoxoxoxxxx", d["hat"], 0.45)
    out.append(loop("c_half", "808-Halbzeit", "🐢", s, 0, "Langsames Gefühl mit tiefer 808-Kick."))

    s = Seq(bpm)
    s.steps("x..x......x.....", ck)
    s.steps("....x..x.x..x...", cs, 0.8)
    s.steps("xxxxxxxxxxxxxxxx", ch, 0.35)
    out.append(loop("c_chipbreak", "Chip-Break", "🕹️", s, 0, "Ein zappeliger Breakbeat aus der Spielkonsole."))
    return out


def perc(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x..x..x...x..x..", d["cowbell"], 0.6, pan=0.3)
    s.steps("..x.......x.....", d["tom_hi"], 0.4, pan=-0.3)
    out.append(loop("c_cowbell", "Kuhglocke", "🐄", s, 1, "Die 808-Kuhglocke – sie klingt ein bisschen schief, und das ist gut so!"))

    s = Seq(bpm)
    s.steps("xoxxxoxxxoxxxoxo", chip_noise(0.05, 15000, 60), 0.8)
    s.steps("..x...x...x...x.", chip_noise(0.15, 15000, 20, periodic=True), 0.5)
    out.append(loop("c_noisehats", "Rausch-Hats", "📺", s, 1, "HiHats aus dem Rausch-Kanal: wie ein alter Fernseher."))

    s = Seq(bpm)
    blips = [osc_pulse(f, int(0.05 * SR), 0.25) * np.linspace(1, 0, int(0.05 * SR)) for f in (1760, 2093, 2637)]
    for i, c in enumerate("x.x..x.xx.x..x.x" * 4):
        if c == "x":
            s.add(i / 4, blips[i % 3], 0.6, 0.5 * np.sin(i))
    out.append(loop("c_chipperc", "Chip-Perc", "🔹", s, 1, "Kurze, hohe Piepser als Rhythmus."))

    s = Seq(bpm)
    s.steps("x..x......x.....", d["tom_lo"], 0.8, pan=-0.3)
    s.steps("......x.x....x.x", d["tom_hi"], 0.7, pan=0.3)
    out.append(loop("c_toms", "808-Toms", "🪘", s, 1, "Tiefe und hohe 808-Trommeln."))
    return out


def bass(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    bass_line(s, "chip_square", "R.O.R.O.R.O.R5O.", 0.4, octave=-12)
    s.buf = lowpass(s.buf.T, 2500).T.astype(np.float32)
    out.append(loop("c_squarebass", "Rechteck-Bass", "🟦", s, 2, "Ein Bass aus Rechteck-Tönen, der in Oktaven hüpft."))

    s = Seq(bpm)
    bass_line(s, "chip_tri", "R.R.RR.RR.R.RRO.", 0.22, octave=-12)
    out.append(loop("c_tribass", "Dreieck-Bass", "🔺", s, 2, "Der Dreieck-Bass alter Spielkonsolen: weich und treppig."))

    s = Seq(bpm)
    bass_line(s, "bass", "R..R..R.R..R..O.", 0.3, octave=-12)
    out.append(loop("c_synthbass", "Synth-Bass", "🎸", s, 2, "Ein Electro-Bass mit einem hüpfenden Rhythmus."))

    s = Seq(bpm)
    add_acid(s, "R.....R.O.....-.", "s.....s.s.....s.", octave=-12, wave="sine", cutoff=4000, env_mod=0,
             q=0.7, decay=1.0, gate=0.95, glide=0.07, drive_amt=1.5)
    out.append(loop("c_808", "808-Rutsch", "🛝", s, 2, "Ein ganz tiefer 808-Bass, der von Ton zu Ton rutscht."))
    return out


def chords(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    arp(s, "chip_square", [0, 1, 2], 0.125, 0.12, 12, gain=0.6)
    out.append(loop("c_chipchords", "Chip-Akkorde", "🎮", s, 3,
                    "Alte Konsolen konnten keine Akkorde – also spielten sie die Töne superschnell nacheinander!"))

    s = Seq(bpm)
    chord_hits(s, "chip_pulse", [0.5, 1.5, 2.5, 3.5], 0.25, spread=0.4)
    out.append(loop("c_stabs", "Rechteck-Stabs", "🟪", s, 3, "Kurze Akkord-Stöße mit schmalem Rechteck."))

    s = Seq(bpm)
    for b in range(4):
        for k in range(3):
            n = int(s.beat * 4) + int(0.2 * SR)
            t = np.arange(n) / SR
            duty = 0.3 + 0.2 * np.sin(2 * np.pi * (0.7 + 0.2 * k) * t)
            x = osc_pulse(440 * 2 ** ((chord_note(b, k) - 69) / 12), n, duty) * np.minimum(t / 0.05, 1)
            x *= np.minimum((n - np.arange(n)) / (0.15 * SR), 1)
            s.add(b * 4, lowpass(x, 3000), 0.4, (k - 1) * 0.5)
    out.append(loop("c_pwm", "PWM-Fläche", "🫧", s, 3, "Eine Fläche, bei der sich die Form der Welle langsam verändert."))

    s = Seq(bpm)
    chord_hits(s, "vokal", [0, 2], 1.8, octave=-12, spread=0.5)
    s.buf = crush(s.buf, 6, 2).astype(np.float32)
    out.append(loop("c_robochor", "Roboter-Chor", "🤖", s, 3, "Ein Chor aus Roboter-Stimmen – mit wenigen Bits."))
    return out


def arps(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    arp(s, "chip_pulse", [0, 1, 2, 3, 4, 3, 2, 1], 0.125, 0.11, 12, gain=0.7)
    out.append(loop("c_arp32", "Chip-Arp", "⚡", s, 4, "Ein superschneller Arp – Zweiunddreißigstel wie in einem Videospiel."))

    s = Seq(bpm)
    arp(s, "chip_square", [0, 2, 1, 3], 0.25, 0.2, 12, pan_width=0.4)
    out.append(loop("c_squarearp", "Rechteck-Arp", "🟦", s, 4, "Akkordtöne nacheinander, mit Rechteck-Klang."))

    s = Seq(bpm)
    arp(s, "chip_tri", [0, 1, 2, 3, 4, 5], 0.25, 0.2, 12)
    out.append(loop("c_triarp", "Dreieck-Arp", "🔺", s, 4, "Ein weicher Arp mit dem Dreieck-Klang."))

    s = Seq(bpm)
    arp(s, "chip_pulse", [0, 2, 4], 0.5, 0.2, 12, pattern="x.x.x...")
    s.buf = echo(s.buf, beats_to_s(bpm, 0.75), 0.5, 4, 4000, 0.5)[:len(s.buf)].astype(np.float32)
    out.append(loop("c_echoarp", "Echo-Arp", "🗣️", s, 4, "Wenige Töne – das Echo macht den Rest."))
    return out


def leads(bpm) -> list[Sound]:
    out = []
    melody = [(0, 3, 0.5), (0.5, 4, 0.5), (1, 5, 1.0), (2, 4, 0.5), (2.5, 3, 0.5), (3, 2, 1.0),
              (4, 3, 0.5), (4.5, 4, 0.5), (5, 3, 0.5), (5.5, 2, 0.5), (6, 1, 1.5),
              (8, 2, 0.5), (8.5, 3, 0.5), (9, 4, 1.0), (10, 5, 0.5), (10.5, 4, 0.5), (11, 3, 1.0),
              (12, 4, 0.5), (12.5, 3, 0.5), (13, 2, 0.5), (13.5, 1, 0.5), (14, 0, 1.5)]
    s = Seq(bpm)
    motif(s, "chip_square", melody, 12, per_bar=False)
    out.append(loop("c_melody", "Chip-Melodie", "🎵", s, 5, "Eine fröhliche Melodie wie aus einem Videospiel."))

    s = Seq(bpm)
    motif(s, "chip_pulse", [(0, 3, 1.75), (2, 2, 0.75), (3, 4, 0.75)], 12)
    out.append(loop("c_vibrato", "Vibrato-Lead", "〰️", s, 5, "Lange Töne, die zittern – das nennt man Vibrato."))

    s = Seq(bpm)
    motif(s, "vokal", [(0, 0, 0.25), (0.5, 0, 0.25), (1, 2, 0.5), (2, 1, 0.25), (2.5, 2, 0.25), (3, 0, 0.5)], 0)
    s.buf = crush(s.buf, 4, 4).astype(np.float32)
    out.append(loop("c_robo", "Roboter-Stimme", "🤖", s, 5, "Eine Roboter-Stimme mit ganz wenigen Bits: bip-bop!"))

    s = Seq(bpm)
    motif(s, "chip_pulse", [(0.5, 2, 0.25), (1, 3, 0.25), (1.5, 4, 0.5), (2.5, 3, 0.25), (3, 2, 0.5)], 24, gain=0.8)
    out.append(loop("c_pulse", "Puls-Lead", "🔆", s, 5, "Eine hohe, schnelle Melodie mit schmalem Puls-Klang."))
    return out


def fx(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.add(0, chip_riser(s.seconds))
    out.append(loop("c_riser", "8-Bit-Riser", "🚀", s, 6, "Töne klettern 4 Takte lang nach oben – gleich passiert was!"))

    s = Seq(bpm)
    s.add(0, d["powerup"])
    s.add(8, d["coin"], 0.7, 0.4)
    s.add(12, d["jump"], 0.7, -0.4)
    out.append(loop("c_levelup", "Level-Up", "🏆", s, 6, "Power-Up, Münze, Sprung – wie beim Spielen!"))

    s = Seq(bpm)
    n = len(s.buf)
    t = t_axis((n + int(SR)) / SR)
    x = 0.3 * osc_pulse(110, len(t), 0.5) + 0.3 * osc_pulse(164.8, len(t), 0.25)
    s.add(0, seamless(lowpass(x, 900) * 0.6, n, 0.8))
    g = rng()
    for _ in range(12):
        s.add(int(g.integers(0, 64)) / 4, d["coin"][: int(0.06 * SR)] * 0.5, 0.4, float(g.uniform(-0.8, 0.8)))
    out.append(loop("c_atmo", "Arcade-Atmo", "🕹️", s, 6, "Leises Summen und Piepsen – wie in einer Spielhalle."))

    s = Seq(bpm)
    g = rng()
    for _ in range(12):
        pos = int(g.integers(0, 64)) / 4
        src = d["laser"] if g.random() < 0.5 else d["boom"][: int(0.1 * SR)]
        s.add(pos, crush(np.tile(src[: int(0.05 * SR)], 3), 3, 8), 0.6, float(g.uniform(-0.8, 0.8)))
    out.append(loop("c_glitch", "Glitch", "📟", s, 6, "Absichtlich kaputte Konsolen-Geräusche."))
    return out


def build(bpm: float):
    oneshots, raw = shots(bpm)
    columns = [drums(bpm, raw), perc(bpm, raw), bass(bpm), chords(bpm), arps(bpm), leads(bpm), fx(bpm, raw)]
    return oneshots, columns
