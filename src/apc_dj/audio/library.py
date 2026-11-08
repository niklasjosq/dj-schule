"""Erzeugt alle Klänge der DJ-Schule prozedural – passend in Tonart (a-Moll) und Tempo.

* 16 One-Shots (Drums + DJ-Effekte)
* 8 Spalten x 4 Varianten Loops (je 4 Takte, Akkorde Am – F – C – G)
* Keyboard-Töne (a-Moll-Pentatonik) für mehrere Instrumente
* eigene WAV-Dateien aus sounds/eigene/ für Spalte 8
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .synth import (
    SR, bandpass, highpass, lowpass, midi_to_freq, noise, normalize, render_note, saw, t_axis,
)

log = logging.getLogger(__name__)

LOOP_BARS = 4
# Akkordfolge pro Takt: (Bass-Grundton, Akkordtöne)
PROGRESSION = [
    (45, (57, 60, 64)),  # Am
    (41, (57, 60, 65)),  # F
    (48, (55, 60, 64)),  # C
    (43, (55, 59, 62)),  # G
]
# a-Moll-Pentatonik für das Keyboard (unten links = tiefster Ton)
KEY_NOTES = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93]
KEY_INSTRUMENTS = [
    ("klavier", "Klavier", "🎹", 0),
    ("lead", "Synth", "🎛️", 0),
    ("glocke", "Glocken", "🔔", 0),
    ("bass", "Bass", "🎸", -24),
]


def bar_frames(bpm: float) -> int:
    return int(round(4 * 60.0 / bpm * SR))


def stereo(x: np.ndarray, pan: float = 0.0, gain: float = 1.0) -> np.ndarray:
    """Mono -> Stereo mit Panorama -1 (links) .. 1 (rechts)."""
    ang = (pan + 1) * np.pi / 4
    l, r = np.cos(ang) * np.sqrt(2) * gain, np.sin(ang) * np.sqrt(2) * gain
    return np.stack([x * l, x * r], axis=1).astype(np.float32)


@dataclass
class Sound:
    id: str
    label: str
    emoji: str
    data: np.ndarray  # (N, 2) float32
    info: str = ""


# ------------------------------------------------------------------ Drums


def kick() -> np.ndarray:
    t = t_axis(0.45)
    f = 52 + 120 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    x = np.tanh(2.2 * x) + 0.4 * highpass(noise(0.45), 2000) * np.exp(-t * 250)
    return normalize(x, 1.0)


def snare() -> np.ndarray:
    t = t_axis(0.3)
    x = 0.6 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 22)
    x += bandpass(noise(0.3), 1200, 9000) * np.exp(-t * 15)
    return normalize(x, 0.8)


def clap() -> np.ndarray:
    t = t_axis(0.45)
    env = sum(np.where(t >= o, np.exp(-(t - o) * 120), 0) for o in (0, 0.011, 0.023))
    env += np.where(t >= 0.03, 0.6 * np.exp(-(t - 0.03) * 16), 0)
    return normalize(bandpass(noise(0.45), 900, 3000) * env, 0.8)


def hat(open_: bool = False) -> np.ndarray:
    d = 0.45 if open_ else 0.07
    t = t_axis(d)
    return normalize(highpass(noise(d), 7000) * np.exp(-t * (7 if open_ else 65)), 0.45)


def shaker() -> np.ndarray:
    t = t_axis(0.11)
    env = np.minimum(t / 0.015, 1) * np.exp(-t * 35)
    return normalize(bandpass(noise(0.11), 4000, 13000) * env, 0.35)


def tom(f: float) -> np.ndarray:
    t = t_axis(0.5)
    ff = f * (1 + 0.6 * np.exp(-t * 18))
    return normalize(np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 7), 0.8)


def cowbell() -> np.ndarray:
    t = t_axis(0.35)
    x = np.sign(np.sin(2 * np.pi * 545 * t)) + np.sign(np.sin(2 * np.pi * 815 * t))
    return normalize(bandpass(x, 450, 3000) * np.exp(-t * 11), 0.5)


def rim() -> np.ndarray:
    t = t_axis(0.08)
    x = bandpass(noise(0.08), 1500, 5000) * np.exp(-t * 120) + np.sin(2 * np.pi * 1750 * t) * np.exp(-t * 70)
    return normalize(x, 0.6)


def crash() -> np.ndarray:
    t = t_axis(2.0)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (523, 811, 1171, 1489, 2011))
    x = highpass(noise(2.0) + 0.3 * metal, 4500) * np.exp(-t * 2.3)
    return normalize(x, 0.6)


# ------------------------------------------------------------------ DJ-Effekte


def airhorn() -> np.ndarray:
    total = 1.5
    out = np.zeros(int(total * SR))
    for start, length in ((0, 0.16), (0.21, 0.16), (0.42, 0.16), (0.63, 0.75)):
        t = t_axis(length)
        bend = 1 - 0.03 * (t / length) ** 3
        x = sum(saw(f, t, max_h=20) for f in (466, 470, 699)) * bend
        env = np.minimum(t / 0.01, 1) * np.minimum((length - t) / 0.03, 1)
        s = int(start * SR)
        out[s:s + len(t)] += bandpass(x, 300, 4500) * env
    return normalize(out, 0.7)


def scratch() -> np.ndarray:
    t = t_axis(0.7)
    speed = np.sin(2 * np.pi * 3.2 * t)  # vor und zurück
    freq = 180 + 900 * np.abs(speed)
    tone = sum(np.sin(2 * np.pi * k * np.cumsum(freq) / SR) / k for k in range(1, 8))
    x = 0.6 * tone + 0.4 * bandpass(noise(0.7), 800, 4000)
    gate = (np.abs(speed) > 0.12).astype(float)
    gate = np.convolve(gate, np.ones(200) / 200, mode="same")
    return normalize(x * np.abs(speed) * gate, 0.7)


def laser() -> np.ndarray:
    t = t_axis(0.45)
    f = 120 + 3200 * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(3 * ph)) * np.exp(-t * 4)
    return normalize(x, 0.55)


def boom() -> np.ndarray:
    t = t_axis(2.2)
    f = 30 + 60 * np.exp(-t * 4)
    x = np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 1.6)
    x += 0.5 * lowpass(noise(2.2), 900) * np.exp(-t * 5)
    return normalize(x, 0.95)


def sweep_noise(seconds: float, f_from: float, f_to: float, chunks: int = 64) -> np.ndarray:
    """Rauschen durch einen Bandpass, dessen Mitte von f_from nach f_to wandert."""
    n = noise(seconds)
    out = np.zeros_like(n)
    edges = np.linspace(0, len(n), chunks + 1).astype(int)
    for i in range(chunks):
        c = f_from * (f_to / f_from) ** (i / max(chunks - 1, 1))
        seg = bandpass(n[max(edges[i] - 2000, 0):edges[i + 1]], c * 0.7, c * 1.4)
        out[edges[i]:edges[i + 1]] = seg[-(edges[i + 1] - edges[i]):]
    return out


def riser(seconds: float = 2.0) -> np.ndarray:
    t = t_axis(seconds)
    k = t / seconds
    f = 200 * 8 ** k
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    x = (0.6 * sweep_noise(seconds, 400, 8000) + 0.25 * tone) * k ** 2
    return normalize(x, 0.6)


def sirene() -> np.ndarray:
    t = t_axis(1.6)
    f = 850 + 300 * np.sin(2 * np.pi * 2.2 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = lowpass(np.sin(ph) + 0.3 * np.sin(3 * ph), 3000) * np.minimum(t / 0.05, 1) * np.minimum((1.6 - t) / 0.2, 1)
    return normalize(x, 0.5)


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


# ------------------------------------------------------------------ Loops


class Seq:
    """Schreibt Klänge auf ein Raster (in Schlägen); Ausklang wird an den Anfang gefaltet."""

    def __init__(self, bpm: float, bars: int = LOOP_BARS):
        self.bar = bar_frames(bpm)
        self.beat = self.bar / 4
        self.buf = np.zeros((self.bar * bars, 2), dtype=np.float32)

    def add(self, beat: float, mono: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
        x = stereo(mono, pan, gain)
        n = len(self.buf)
        s = int(round(beat * self.beat)) % n
        while len(x):
            take = min(len(x), n - s)
            self.buf[s:s + take] += x[:take]
            x, s = x[take:], 0

    def steps(self, pattern: str, mono: np.ndarray, gain: float = 1.0, bars=range(LOOP_BARS), pan=0.0):
        """pattern: 16 Zeichen pro Takt, 'x' = Schlag, 'o' = leiser Schlag."""
        for b in bars:
            for i, c in enumerate(pattern):
                if c in "xo":
                    self.add(b * 4 + i / 4, mono, gain * (1 if c == "x" else 0.45), pan)

    def note(self, beat, inst, midi, dur_beats, gain=1.0, pan=0.0):
        self.add(beat, render_note(inst, int(midi), round(dur_beats * self.beat / SR, 3)), gain, pan)

    def done(self, peak: float) -> np.ndarray:
        m = np.max(np.abs(self.buf))
        return self.buf * (peak / m) if m > 0 else self.buf


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


def load_user_loops(folder: Path, bpm: float) -> list[Sound]:
    """Bis zu 4 WAV/AIFF/FLAC-Dateien, auf ganze Takte zugeschnitten."""
    import soundfile as sf
    from scipy.signal import resample_poly

    if not folder.exists():
        return []
    out = []
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".wav", ".aif", ".aiff", ".flac"))
    bar = bar_frames(bpm)
    for p in files[:4]:
        try:
            data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        except Exception as e:  # noqa: BLE001
            log.warning("Kann %s nicht laden: %s", p.name, e)
            continue
        if sr != SR:
            data = resample_poly(data, SR, sr, axis=0).astype(np.float32)
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        data = data[:, :2]
        bars = max(1, int(round(len(data) / bar)))
        target = bars * bar
        if len(data) < target:
            data = np.vstack([data, np.zeros((target - len(data), 2), np.float32)])
        data = data[:target]
        m = np.max(np.abs(data))
        if m > 0:
            data = data * (0.5 / m)
        out.append(Sound(f"user_{p.stem}", p.stem[:14], "⭐", data.astype(np.float32),
                         f"Dein eigener Sound: {p.name}"))
    return out


@dataclass
class Library:
    bpm: float
    oneshots: list[Sound] = field(default_factory=list)
    loops: dict[tuple[int, int], Sound] = field(default_factory=dict)  # (spalte, variante)
    keys: dict[str, list[np.ndarray]] = field(default_factory=dict)
    clicks: tuple[np.ndarray, np.ndarray] | None = None

    @classmethod
    def build(cls, bpm: float, user_dir: Path | None = None) -> "Library":
        lib = cls(bpm)
        raw = {}
        for sid, label, emoji, fn, info in ONESHOTS:
            raw[sid] = fn()
            lib.oneshots.append(Sound(sid, label, emoji, stereo(raw[sid], gain=0.8), info))
        raw["shaker"] = shaker()
        columns = [
            drum_loops(bpm, raw), perc_loops(bpm, raw), bass_loops(bpm), chord_loops(bpm),
            arp_loops(bpm), melody_loops(bpm), fx_loops(bpm, raw),
            load_user_loops(user_dir, bpm) if user_dir else [],
        ]
        for col, sounds in enumerate(columns):
            for var, snd in enumerate(sounds[:4]):
                lib.loops[(col, var)] = snd
        for name, _, _, shift in KEY_INSTRUMENTS:
            lib.keys[name] = [stereo(render_note(name, m + shift, 4.0), gain=0.45) for m in KEY_NOTES]
        t = t_axis(0.04)
        env = np.exp(-t * 120)
        lib.clicks = (stereo(np.sin(2 * np.pi * 1800 * t) * env, gain=0.5),
                      stereo(np.sin(2 * np.pi * 1100 * t) * env, gain=0.35))
        return lib

    def key_for_midi(self, instrument: str, midi: int) -> np.ndarray:
        shift = next(s for n, _, _, s in KEY_INSTRUMENTS if n == instrument)
        return stereo(render_note(instrument, midi + shift, 4.0), gain=0.45)
