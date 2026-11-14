"""Musikstil "Techno" – Berlin/Detroit: harte Kick, Rumble, Ride, Dub-Akkorde mit Echo, hypnotische Sequenzen."""
from __future__ import annotations

import numpy as np

from ..drums import (
    clap_room, crash, downlifter, dub_siren, hat808, impact, kick909, metal_perc, reverse_crash, ride, rim,
    snare909, sub_drop, tom808, uplifter, zap,
)
from ..seq import Seq, Sound
from ..synth import SR, crush, echo, lowpass, osc_saw, pump, render_note, reverb, rng, t_axis
from .common import (
    add_acid, arp, bass_line, beats_to_s, chord_audio, chord_hits, chord_note, loop, loop_sweep, make_shots, motif,
    seamless,
)


def _dub_stab(bpm: float) -> np.ndarray:
    return echo(chord_audio(0, "dubstab", 0.2, seventh=True), beats_to_s(bpm, 0.75), 0.55, 5, 1800)


def shots(bpm: float):
    return make_shots([
        ("kick", "Techno-Kick", "🥁", kick909(), "Die Techno-Kick ist kurz und hart. Sie schiebt die ganze Nacht!"),
        ("snare", "Snare", "🪘", snare909(), "Eine knallige Snare – im Techno wird sie nur sparsam eingesetzt."),
        ("clap", "Clap", "👏", clap_room(), "Ein Clap mit Hall – als ob man in einer großen Halle klatscht."),
        ("hat", "HiHat", "🎩", hat808(False), "Die HiHat klingt metallisch. Sie entsteht aus sechs schiefen Tönen."),
        ("ohat", "HiHat offen", "🎩", hat808(True), "Die offene HiHat zischt zwischen den Kicks: tss – tss!"),
        ("tom", "Tom tief", "🪘", tom808(95), "Eine tiefe Trommel aus dem Drumcomputer."),
        ("metal", "Metall", "🔩", metal_perc(620), "Klingt wie ein Schlag auf ein Metallrohr – typisch Techno."),
        ("ride", "Ride", "🛎️", ride(), "Das Ride-Becken klingelt lang. Es treibt viele Techno-Tracks an."),
        ("crash", "Becken", "💥", crash(), "Das Becken markiert einen neuen Abschnitt: KSSSHHH!"),
        ("dubstab", "Dub-Stab", "🌫️", _dub_stab(bpm), "Ein Akkord mit Echo – so klingt Dub-Techno aus Berlin."),
        ("subdrop", "Sub-Drop", "🕳️", sub_drop(), "Ein ganz tiefer Ton, der nach unten rutscht. Spürst du ihn im Bauch?"),
        ("zap", "Zap", "⚡", zap(), "Zapp! Ein Ton, der blitzschnell nach unten fällt."),
        ("boom", "Einschlag", "💣", impact(), "Ein Einschlag mit Hall – perfekt für den Drop."),
        ("riser", "Riser", "🚀", uplifter(2.0), "Rauschen, das nach oben steigt – gleich passiert etwas!"),
        ("siren", "Dub-Sirene", "🚨", dub_siren(), "Die Dub-Sirene mit Echo – uiuiui!"),
        ("reverse", "Rückwärts", "⏪", reverse_crash(), "Ein Becken, rückwärts abgespielt. Es saugt alles ein!"),
    ])


def drums(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("..x...x...x...x.", d["ohat"], 0.55)
    s.steps("x.o.x.o.x.o.x.oo", d["hat"], 0.35)
    s.steps("....x.......x...", d["clap"], 0.6)
    out.append(loop("t_drums", "Techno-Beat", "🥁", s, 0,
                    "Die Kick auf jedem Schlag, dazwischen die offene HiHat. Das ist Techno!"))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    tail = reverb(d["kick"], 2.5, mix=1.0, dry=0.0, damp=900).mean(axis=1)
    rum = Seq(bpm)
    rum.steps("x...x...x...x...", lowpass(tail, 160))
    rum.buf = pump(rum.buf, rum.beat, depth=0.95, release=0.1)
    s.buf += rum.buf * (0.8 * np.abs(s.buf).max() / max(np.abs(rum.buf).max(), 1e-9))
    s.steps("..x...x...x...x.", d["hat"], 0.4)
    out.append(loop("t_rumble", "Rumble", "🌋", s, 0,
                    "Rumble: Die Kick bekommt einen riesigen Hall, der tief grummelt – wie ein Gewitter im Keller."))

    s = Seq(bpm)
    s.steps("x...x...x...x...", d["kick"])
    s.steps("...x..x....x..x.", rim(), 0.5)
    s.steps("x.oox.oox.oox.oo", d["hat"], 0.3)
    s.steps("............x...", d["clap"], 0.5)
    s.steps("..........x.....", d["metal"], 0.4, bars=[1, 3])
    out.append(loop("t_minimal", "Minimal", "🔬", s, 0,
                    "Minimal-Techno: ganz wenige Klänge, die sich langsam ineinander verhaken."))

    s = Seq(bpm)
    s.steps("x..x..x...x.x...", d["kick"])
    s.steps("....x.......x...", d["clap"], 0.7)
    s.steps("xoxoxoxoxoxoxxox", d["hat"], 0.35)
    s.steps("..x.......x.....", d["ohat"], 0.4)
    out.append(loop("t_broken", "Gebrochen", "🧱", s, 0,
                    "Ein gebrochener Beat: Die Kick hüpft herum, statt gerade durchzulaufen."))
    return out


def perc(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("o.x.o.x.o.x.o.x.", d["ride"], 0.7)
    out.append(loop("t_ride", "Ride", "🛎️", s, 1, "Das Ride-Becken klingelt auf jeder Achtel – das treibt an!"))

    s = Seq(bpm)
    s.steps("xooxxoxoxooxxoxx", d["hat"], 0.7)
    s.steps("..x...x...x...x.", d["ohat"], 0.35)
    out.append(loop("t_hats", "HiHats 16", "🎩", s, 1, "Sechzehntel-HiHats mit Betonungen – wie ein schnelles Ticken."))

    s = Seq(bpm)
    for k in range(0, 64, 3):  # alle 3 Sechzehntel: verschiebt sich gegen den 4er-Takt
        s.add(k / 4, d["metal"] if k % 2 == 0 else metal_perc(880), 0.7, 0.4 if k % 2 else -0.4)
    out.append(loop("t_poly", "Metall 3/16", "🔩", s, 1,
                    "Ein Klang, der alle 3 Sechzehntel kommt – er wandert gegen den Takt. Das macht hypnotisch!"))

    s = Seq(bpm)
    s.steps("....x.......x...", d["clap"], bars=[0, 1, 2])
    s.steps("....x...x.x.xxxx", d["clap"], 0.8, bars=[3])
    out.append(loop("t_claprolle", "Clap-Rolle", "👏", s, 1, "Claps mit Hall – am Ende ein Wirbel, der Spannung macht."))
    return out


def bass(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    bass_line(s, "bass", ".RRR.RRR.RRR.RRR", 0.2, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.5)
    out.append(loop("t_rolling", "Rollender Bass", "🌀", s, 2,
                    "Ein rollender Bass: drei schnelle Töne zwischen jeder Kick – rrr, rrr, rrr!"))

    s = Seq(bpm)
    bass_line(s, "sub", "..R...R...R...R.", 0.4, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.7)
    out.append(loop("t_sub", "Sub-Puls", "🫀", s, 2, "Ein ganz tiefer Sinus-Bass zwischen den Kicks. Mehr fühlen als hören!"))

    s = Seq(bpm)
    bass_line(s, "reese", "R...............", 3.9, octave=-12)
    s.buf = pump(s.buf, s.beat, 0.4)
    out.append(loop("t_reese", "Reese", "🐍", s, 2, "Der Reese-Bass: zwei verstimmte Töne reiben sich und wabern."))

    s = Seq(bpm)
    add_acid(s, "R.RO.RR.R5.RO.R-", "a...s..a....a...", octave=-12, cutoff=180, env_mod=2.6, q=4, decay=0.2)
    s.buf = pump(s.buf, s.beat, 0.3)
    out.append(loop("t_acidbass", "Acid-Bass", "🧪", s, 2, "Ein Bass, der blubbert – der Filter öffnet sich bei jedem Ton."))
    return out


def chords(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    for b in range(4):
        x = echo(chord_audio(b, "dubstab", 0.2, seventh=True), beats_to_s(bpm, 0.75), 0.55, 6, 1800)
        for pos in (0.5, 2.5, 3.75):
            s.add(b * 4 + pos, x, 0.6)
    s.buf = pump(s.buf, s.beat, 0.3)
    out.append(loop("t_dubchord", "Dub-Akkord", "🌫️", s, 3,
                    "Dub-Techno: ein Akkord, der als Echo immer leiser und dumpfer wird – wie im Nebel."))

    s = Seq(bpm)
    chord_hits(s, "stab", [p / 4 for p, c in enumerate("x..x..x...x..x..") if c == "x"], 0.3, seventh=True, spread=0.4)
    s.buf = reverb(s.buf, 0.8, 0.25)[:len(s.buf)].astype(np.float32)
    out.append(loop("t_detroit", "Detroit-Stab", "🏙️", s, 3,
                    "Akkord-Stöße wie in Detroit, wo Techno erfunden wurde."))

    s = Seq(bpm)
    chord_hits(s, "pad", [0], 3.9, seventh=True, spread=0.5)
    s.buf = pump(s.buf, s.beat, 0.8, 0.2)
    out.append(loop("t_pumppad", "Pump-Fläche", "🫁", s, 3,
                    "Eine Fläche, die auf jedem Schlag leiser wird und wieder anschwillt – sie atmet mit der Kick."))

    s = Seq(bpm)
    chord_hits(s, "orgel", [0.5, 1.5, 2.5, 3.5], 0.3, spread=0.3)
    out.append(loop("t_orgel", "Orgel-Stab", "⛪", s, 3, "Kurze Orgel-Akkorde zwischen den Schlägen – wie in alten Clubs."))
    return out


def arps(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    k = 0
    while k * 3 < 64:  # alle 3 Sechzehntel ein Ton -> Muster verschiebt sich gegen den Takt
        bar = (k * 3) // 16
        s.note(k * 0.75, "blip", chord_note(bar, k % 4, seventh=True) + 12, 0.25, 1.0, 0.3 * np.sin(k))
        k += 1
    loop_sweep(s, np.array([900, 3500, 1600, 5000, 900]), 2.0)
    out.append(loop("t_hypno", "Hypno-Sequenz", "🌀", s, 4,
                    "Eine Tonfolge, die gegen den Takt läuft und sich nie ganz wiederholt. Hypnotisch!"))

    s = Seq(bpm)
    arp(s, "blip", [0, 2, 1, 3], 0.25, 0.2, 12, pattern="x.xx.x.xx.x.xx.x", pan_width=0.4)
    out.append(loop("t_blipseq", "Blip-Sequenz", "💠", s, 4, "Kurze Blips wie aus einem Raumschiff-Computer."))

    s = Seq(bpm)
    for b in range(4):
        for i, pos in enumerate((0.5, 1.5, 2.5, 3.5)):
            note = render_note("glocke", chord_note(b, (i * 2) % 4, True) + 12, 0.3)
            s.add(b * 4 + pos, echo(note, beats_to_s(bpm, 0.75), 0.45, 3, 4000), 0.6)
    out.append(loop("t_fmseq", "FM-Echo", "🔔", s, 4, "Glockige FM-Töne mit Echo – sie hüpfen von links nach rechts."))

    s = Seq(bpm)
    add_acid(s, "R5OR3O5RO3R5O.RO", "a.s..a.s.a..s.a.", octave=0, cutoff=300,
             env_mod=2.5, q=9, decay=0.15, macro=[-0.6, 0.4, 1.4, 2.0])
    out.append(loop("t_acidseq", "Acid-Sequenz", "🧪", s, 4,
                    "Eine Acid-Tonfolge: Der Filter öffnet sich über 4 Takte immer weiter – iiiuuu!"))
    return out


def leads(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    motif(s, "lead", [(0, 2, 1.25), (1.5, 1, 0.5), (2, 0, 0.75), (3, 1, 0.75)], 12, seventh=True)
    s.buf = echo(s.buf, beats_to_s(bpm, 0.75), 0.4, 3, 3000, 0.35)[:len(s.buf)].astype(np.float32)
    out.append(loop("t_scifi", "Sci-Fi-Lead", "🛸", s, 5, "Eine Synth-Melodie mit Echo – wie Musik aus einem Science-Fiction-Film."))

    s = Seq(bpm)
    motif(s, "glocke", [(0, 3, 0.5), (0.75, 4, 0.5), (1.5, 2, 1.0), (3, 1, 0.5)], 12)
    out.append(loop("t_glockenruf", "Glocken-Ruf", "🔔", s, 5, "Ein kurzer Glocken-Ruf, der sich jeden Takt wiederholt."))

    s = Seq(bpm)
    motif(s, "vokal", [(0, 0, 0.25), (0.75, 1, 0.25), (1.5, 2, 0.25), (2.25, 1, 0.25), (3, 0, 0.5)], 0)
    s.buf = crush(s.buf, 5, 3).astype(np.float32)
    out.append(loop("t_robo", "Robo-Stimme", "🤖", s, 5, "Eine Roboter-Stimme: zerhackt und mit wenigen Bits – piep-bop!"))

    s = Seq(bpm)
    motif(s, "hoover", [(0, 0, 1.5), (2.5, 2, 1.0)], 0)
    out.append(loop("t_hoover", "Hoover-Ruf", "🌀", s, 5, "Der Hoover-Sound heult wie ein Staubsauger – berühmt aus den 90ern!"))
    return out


def fx(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.add(0, uplifter(s.seconds))
    out.append(loop("t_uplift", "Uplifter", "🚀", s, 6, "Rauschen steigt 4 Takte lang nach oben. Danach: Drop!"))

    s = Seq(bpm)
    s.add(0, d["boom"])
    s.add(0, downlifter(beats_to_s(bpm, 8)), 0.8)
    out.append(loop("t_down", "Downlifter", "🛬", s, 6, "Ein Einschlag, danach rauscht es nach unten – wie eine Landung."))

    s = Seq(bpm)
    n = len(s.buf)
    t = t_axis((n + int(SR)) / SR)
    x = osc_saw(55 * 0.997, len(t)) + osc_saw(82.4 * 1.003, len(t), 0.3) + 0.5 * osc_saw(110, len(t), 0.6)
    s.add(0, seamless(reverb(lowpass(x, 600), 2.0, 0.5)[:len(t)], n, 0.8))
    loop_sweep(s, np.array([300, 900, 400, 1200, 300]), 1.5)
    out.append(loop("t_drone", "Drone", "🌑", s, 6, "Ein dunkler Dauerton, der langsam heller und dunkler wird."))

    s = Seq(bpm)
    g = rng()
    for _ in range(14):
        pos = int(g.integers(0, 64)) / 4
        burst = crush(d["zap"][: int(0.08 * SR)] if g.random() < 0.5 else d["metal"][: int(0.06 * SR)], 4, 6)
        s.add(pos, np.tile(burst, 3), 0.6, float(g.uniform(-0.8, 0.8)))
    out.append(loop("t_glitch", "Glitch", "📟", s, 6, "Kaputte Computer-Geräusche – absichtlich! Das nennt man Glitch."))
    return out


def build(bpm: float):
    oneshots, raw = shots(bpm)
    columns = [drums(bpm, raw), perc(bpm, raw), bass(bpm), chords(bpm), arps(bpm), leads(bpm), fx(bpm, raw)]
    return oneshots, columns
