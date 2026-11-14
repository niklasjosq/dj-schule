"""Musikstil "DJ-Schule" – der ursprüngliche Klangsatz (Pop/House, a-Moll, Am – F – C – G).

* 16 One-Shots (Drums + DJ-Effekte)
* 7 Spalten x 4 Varianten Loops (je 4 Takte)
"""
from __future__ import annotations

import numpy as np

from ..drums import (
    airhorn, boom, clap, cowbell, crash, hat, kick, laser, rim, riser, scratch, shaker, sirene, snare,
    sweep_noise, tom,
)
from ..seq import PROGRESSION, Seq, Sound, stereo
from ..synth import SR

ONESHOTS = [
    ("kick", "Kick", "🥁", kick, "Die Kick ist die große Trommel – der Herzschlag der Musik. BUMM!"),
    ("snare", "Snare", "🪘", snare, "Die Snare knallt meist auf Schlag 2 und 4."),
    ("clap", "Clap", "👏", clap, "Ein Klatschen – wie im Publikum!"),
    ("hat", "HiHat", "🎩", lambda: hat(False), "Die HiHat tickt schnell und hält alles zusammen."),
    ("ohat", "HiHat offen", "🎩", lambda: hat(True), "Die offene HiHat zischt länger: tssss."),
    ("tom_lo", "Tom tief", "🪘", lambda: tom(90), "Tiefe Tom – klingt wie eine Urwaldtrommel."),
    ("tom_hi", "Tom hoch", "🪘", lambda: tom(160), "Hohe Tom – gut für Trommelwirbel."),
    ("cowbell", "Kuhglocke", "🐄", cowbell, "Die Kuhglocke – ja, wirklich aus der Musik!"),
    ("crash", "Becken", "💥", crash, "Das Becken markiert einen neuen Abschnitt: KSSSHHH!"),
    ("airhorn", "Airhorn", "📯", airhorn, "Das Airhorn ist der berühmteste DJ-Effekt. Sparsam einsetzen!"),
    ("scratch", "Scratch", "💿", scratch, "So klingt es, wenn ein DJ die Platte hin und her schiebt."),
    ("laser", "Laser", "⚡", laser, "Piuuu! Ein Laser-Effekt aus dem Synthesizer."),
    ("boom", "Boom", "💣", boom, "Ein tiefer Einschlag – perfekt für den Drop."),
    ("riser", "Riser", "🚀", lambda: riser(2.0), "Der Riser steigt nach oben und baut Spannung auf."),
    ("sirene", "Sirene", "🚨", sirene, "Die Sirene macht die Leute auf der Tanzfläche wach."),
    ("rim", "Rimshot", "🥢", rim, "Ein Schlag auf den Trommelrand: klack!"),
]


def drum_loops(bpm, d) -> list[Sound]:
    out = []

    s = Seq(bpm)  # House
    s.steps("x...x...x...x...", d["kick"])
    s.steps("....x.......x...", d["clap"], 0.8)
    s.steps("..x...x...x...x.", d["ohat"], 0.5)
    s.steps("x.o.x.o.x.o.x.o.", d["hat"], 0.4)
    s.steps("............xxxx", d["snare"], 0.5, bars=[3])
    out.append(Sound("drums_house", "House-Beat", "🥁", s.done(0.6),
                     "Four-to-the-floor: Die Kick auf jedem Schlag. So klingt House-Musik!"))

    s = Seq(bpm)  # Hip-Hop
    s.steps("x......x..x.....", d["kick"])
    s.steps("....x.......x...", d["snare"], 0.9)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.5)
    out.append(Sound("drums_hiphop", "Hip-Hop", "🧢", s.done(0.6),
                     "Ein Hip-Hop-Beat: Kick und Snare wechseln sich ab – Boom-Tschak!"))

    s = Seq(bpm)  # Breakbeat
    s.steps("x.x.......x.....", d["kick"])
    s.steps("....x..o.o..x..o", d["snare"], 0.9)
    s.steps("x.x.x.x.x.x.x.x.", d["hat"], 0.45)
    out.append(Sound("drums_break", "Breakbeat", "💃", s.done(0.6),
                     "Breakbeat: Die Schläge hüpfen herum. Das gibt Energie!"))

    s = Seq(bpm)  # Halftime / Trap
    s.steps("x......x..x.....", d["kick"])
    s.steps("........x.......", d["clap"], 0.9)
    s.steps("xoxoxoxoxoxoxoxo", d["hat"], 0.45, bars=[0, 2])
    s.steps("xoxoxoxoxoxoxxxx", d["hat"], 0.45, bars=[1, 3])
    out.append(Sound("drums_trap", "Halftime", "🐢", s.done(0.6),
                     "Halftime: Die Snare kommt nur einmal pro Takt – das fühlt sich langsamer an."))
    return out


def perc_loops(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    s.steps("oxoxoxoxoxoxoxox", d["shaker"], 0.8)
    out.append(Sound("perc_shaker", "Shaker", "🧂", s.done(0.35), "Der Shaker raschelt wie eine Dose voller Reis."))
    s = Seq(bpm)
    s.steps("..x...x...x...x.", d["ohat"], 0.8)
    s.steps("xoxoxoxoxoxoxoxo", d["hat"], 0.4)
    out.append(Sound("perc_hats", "HiHats", "🎩", s.done(0.35), "Schnelle HiHats treiben den Song nach vorne."))
    s = Seq(bpm)
    s.steps("x..x......x.....", d["tom_lo"], 0.8, pan=-0.3)
    s.steps("......x.x....x.x", d["tom_hi"], 0.7, pan=0.3)
    out.append(Sound("perc_toms", "Trommeln", "🪘", s.done(0.4), "Trommeln wie in einem Dschungel-Orchester!"))
    s = Seq(bpm)
    s.steps("x..x..x...x..x..", d["cowbell"], 0.6, pan=0.4)
    s.steps("..x...x.x.....x.", d["rim"], 0.7, pan=-0.4)
    out.append(Sound("perc_cowbell", "Kuhglocke", "🐄", s.done(0.35), "Kuhglocke und Rimshot – ein lustiger Groove."))
    return out


def bass_loops(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    for b, (root, _) in enumerate(PROGRESSION):
        for i in range(8):
            s.note(b * 4 + i / 2, "bass", root + (12 if i == 7 else 0), 0.4)
    out.append(Sound("bass_8", "Achtel-Bass", "🎸", s.done(0.5), "Der Bass spielt den tiefsten Ton des Akkords – das Fundament."))
    s = Seq(bpm)
    for b, (root, _) in enumerate(PROGRESSION):
        for beat in range(4):
            s.note(b * 4 + beat + 0.5, "bass", root, 0.4)
    out.append(Sound("bass_off", "Offbeat-Bass", "🎸", s.done(0.5), "Der Bass spielt zwischen den Kicks – typisch für House."))
    s = Seq(bpm)
    for b, (root, _) in enumerate(PROGRESSION):
        for pos, iv in ((0, 0), (0.75, 0), (1.5, 12), (2.5, 0), (3, 7), (3.5, 12)):
            s.note(b * 4 + pos, "bass", root + iv, 0.35)
    out.append(Sound("bass_funk", "Funky-Bass", "🕺", s.done(0.5), "Ein hüpfender Bass mit Oktavsprüngen – sehr funky!"))
    s = Seq(bpm)
    for b, (root, _) in enumerate(PROGRESSION):
        s.note(b * 4, "bass", root, 3.8)
    out.append(Sound("bass_long", "Langer Bass", "🐋", s.done(0.5), "Lange Basstöne wie ein Wal-Gesang."))
    return out


def chord_loops(bpm) -> list[Sound]:
    out = []
    s = Seq(bpm)
    for b, (_, ch) in enumerate(PROGRESSION):
        for m in ch:
            s.note(b * 4, "pad", m, 3.9, 0.5)
    out.append(Sound("chords_pad", "Flächen", "☁️", s.done(0.4), "Akkorde sind mehrere Töne gleichzeitig. Diese klingen weich wie Wolken."))
    s = Seq(bpm)
    for b, (_, ch) in enumerate(PROGRESSION):
        for beat in range(4):
            for m in ch:
                s.note(b * 4 + beat + 0.5, "stab", m, 0.25, 0.5)
    out.append(Sound("chords_stab", "Stabs", "🔪", s.done(0.4), "Kurze Akkord-Stöße zwischen den Schlägen."))
    s = Seq(bpm)
    for b, (_, ch) in enumerate(PROGRESSION):
        for pos, dur in ((0, 1.4), (1.5, 1.4), (3, 0.9)):
            for m in ch:
                s.note(b * 4 + pos, "klavier", m, dur, 0.5)
    out.append(Sound("chords_piano", "Klavier", "🎹", s.done(0.45), "Klavier-Akkorde: Am – F – C – G, die wohl beliebteste Akkordfolge!"))
    s = Seq(bpm)
    for b, (_, ch) in enumerate(PROGRESSION):
        for pos in (0, 0.75, 1.5, 2.5, 3.25):
            for m in ch:
                s.note(b * 4 + pos, "pluck", m + 12, 0.3, 0.5)
    out.append(Sound("chords_pluck", "Pluck", "🪕", s.done(0.4), "Gezupfte Akkorde, wie bei einer Harfe."))
    return out


def arp_loops(bpm) -> list[Sound]:
    out = []
    specs = [
        ("arp_up", "Arp hoch", "⬆️", "pluck", 0.25, lambda ch: [ch[0], ch[1], ch[2], ch[0] + 12],
         "Ein Arpeggio spielt die Akkordtöne nacheinander – hier immer nach oben."),
        ("arp_updown", "Arp rauf-runter", "↕️", "glocke", 0.5, lambda ch: [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1]],
         "Rauf und runter, wie eine Achterbahn."),
        ("arp_broken", "Gebrochen", "🧩", "klavier", 0.5, lambda ch: [ch[0], ch[2], ch[1], ch[2]],
         "Gebrochene Akkorde: Die Töne springen hin und her."),
        ("arp_oct", "Oktaven", "🪜", "pluck", 0.25, lambda ch: [ch[0] + 12, ch[0] + 24],
         "Zwei gleiche Töne im Oktavabstand – tief, hoch, tief, hoch."),
    ]
    for sid, label, emoji, inst, step, fn, info in specs:
        s = Seq(bpm)
        for b, (_, ch) in enumerate(PROGRESSION):
            tones = fn(ch)
            for i in range(int(4 / step)):
                s.note(b * 4 + i * step, inst, tones[i % len(tones)] + 12, step * 0.9, 0.6, pan=0.3 * np.sin(i))
        out.append(Sound(sid, label, emoji, s.done(0.35), info))
    return out


def melody_loops(bpm) -> list[Sound]:
    hook1 = [(0, 76, 1), (1, 74, .5), (1.5, 72, .5), (2, 69, 1.5), (4, 72, 1), (5, 69, .5), (5.5, 72, .5),
             (6, 74, 1.5), (8, 76, 1), (9, 79, .5), (9.5, 76, .5), (10, 74, 1), (11, 72, 1),
             (12, 74, 1), (13, 72, .5), (13.5, 69, .5), (14, 67, 1.5)]
    hook2 = [(0, 81, 1), (1.5, 79, .5), (2, 76, 2), (4, 72, 1), (5.5, 74, .5), (6, 76, 2),
             (8, 79, 1), (9.5, 76, .5), (10, 72, 2), (12, 74, 1), (13.5, 76, .5), (14, 79, 2)]
    riff = [69, 72, 76, 72, 74, 72, 69, 67]
    hook3 = [(b * 4 + i / 2, n, 0.45) for b in range(3) for i, n in enumerate(riff)]
    hook3 += [(12 + i / 2, n, 0.45) for i, n in enumerate([67, 69, 72, 74, 76, 79, 76, 74])]
    hook4 = [(0, 69, 3.5), (4, 72, 3.5), (8, 76, 3.5), (12, 74, 3.5)]
    out = []
    for sid, label, emoji, inst, notes, shift, info in (
        ("mel_lead", "Synth-Melodie", "🎶", "lead", hook1, 0, "Die Melodie ist der Teil, den man mitsingen kann."),
        ("mel_glocke", "Glocken", "🔔", "glocke", hook2, 0, "Eine Glocken-Melodie – hell und glitzernd."),
        ("mel_riff", "Klavier-Riff", "🎹", "klavier", hook3, 0, "Ein Riff ist eine kurze Melodie, die sich wiederholt."),
        ("mel_vokal", "Aaah-Stimme", "🗣️", "vokal", hook4, -12, "Eine Computer-Stimme singt: Aaaah!"),
    ):
        s = Seq(bpm)
        for pos, m, dur in notes:
            s.note(pos, inst, m + shift, dur)
        out.append(Sound(sid, label, emoji, s.done(0.4), info))
    return out


def fx_loops(bpm, d) -> list[Sound]:
    out = []
    s = Seq(bpm)
    secs = len(s.buf) / SR
    s.add(0, riser(secs))
    out.append(Sound("fx_riser", "Spannung", "🚀", s.done(0.35), "Ein Riser steigt 4 Takte lang an. Danach kommt oft der Drop!"))
    s = Seq(bpm)
    for b, (_, ch) in enumerate(PROGRESSION):
        for pos in (0, 0.75, 1.5, 2.5, 3.0):
            s.note(b * 4 + pos, "vokal", ch[(int(pos * 4)) % 3], 0.22, 0.7, pan=0.4 * np.cos(pos * 3))
    out.append(Sound("fx_chops", "Vokal-Chops", "✂️", s.done(0.35), "Zerschnippelte Stimmen – das nennt man Vocal Chops."))
    s = Seq(bpm)
    secs = len(s.buf) / SR
    wind = sweep_noise(secs, 300, 1200, 32) + sweep_noise(secs, 1200, 300, 32)
    s.add(0, wind * 0.6)
    for b, (root, _) in enumerate(PROGRESSION):
        s.note(b * 4, "pad", root + 12, 3.9, 0.35)
    out.append(Sound("fx_atmo", "Atmosphäre", "🌌", s.done(0.3), "Wind und Weltraum – eine Atmosphäre für ruhige Momente."))
    s = Seq(bpm)
    s.add(0, d["boom"])
    s.add(0, d["crash"], 0.6)
    s.add(0, sweep_noise(2.0, 6000, 300) * np.linspace(1, 0, int(2.0 * SR)), 0.4)
    out.append(Sound("fx_impact", "Einschlag", "💥", s.done(0.45), "Ein Einschlag auf der Eins – alle 4 Takte."))
    return out


def build(bpm: float) -> tuple[list[Sound], list[list[Sound]]]:
    raw = {}
    shots = []
    for sid, label, emoji, fn, info in ONESHOTS:
        raw[sid] = fn()
        shots.append(Sound(sid, label, emoji, stereo(raw[sid], gain=0.8), info))
    raw["shaker"] = shaker()
    columns = [
        drum_loops(bpm, raw), perc_loops(bpm, raw), bass_loops(bpm), chord_loops(bpm),
        arp_loops(bpm), melody_loops(bpm), fx_loops(bpm, raw),
    ]
    return shots, columns
