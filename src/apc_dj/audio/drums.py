"""Schlagzeug und DJ-Effekte – alles prozedural mit numpy erzeugt (Mono, float32).

Die Klänge der DJ-Schule stehen oben; die Bausteine für Techno, Acid, Trance und 8-Bit darunter.
"""
from __future__ import annotations

import numpy as np

from .synth import (
    SR, bandpass, drive, echo, fm, highpass, lowpass, midi_to_freq, noise, normalize, osc_pulse, osc_saw,
    osc_tri, reverb, rng, saw, sweep_filter, t_axis,
)

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


# ================================================================== Elektronische Drums
# 808-Metall: sechs Rechteck-Oszillatoren mit "schiefen" Frequenzen (Werner et al., ICMC 2014)
METAL_FREQS = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)


def metal6(seconds: float, scale: float = 1.0) -> np.ndarray:
    t = t_axis(seconds)
    return sum(np.sign(np.sin(2 * np.pi * f * scale * t + k)) for k, f in enumerate(METAL_FREQS)) / 6


def kick909(decay: float = 5.5, punch: float = 1.0) -> np.ndarray:
    t = t_axis(0.5)
    f = 48 + 190 * np.exp(-t * 32) + 30 * np.exp(-t * 7)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)
    click = punch * (0.5 * highpass(noise(0.5), 3000) * np.exp(-t * 400) + 0.4 * (t < 0.0015))
    return normalize(drive(body * 1.6, 2.5) + click, 1.0)


def kick808(decay: float = 0.9) -> np.ndarray:
    t = t_axis(decay + 0.2)
    f = 47 + 70 * np.exp(-t * 38)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.6 / decay)
    return normalize(drive(x, 1.6), 1.0)


def snare808() -> np.ndarray:
    t = t_axis(0.3)
    tone = 0.6 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 22) + 0.4 * np.sin(2 * np.pi * 330 * t) * np.exp(-t * 28)
    return normalize(tone + 0.8 * bandpass(noise(0.3), 2000, 10000) * np.exp(-t * 18), 0.8)


def snare909() -> np.ndarray:
    t = t_axis(0.35)
    f = 185 * (1 + 0.3 * np.exp(-t * 40))
    tone = 0.7 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
    return normalize(tone + bandpass(noise(0.35), 1500, 12000) * np.exp(-t * 12), 0.8)


def hat808(open_: bool = False) -> np.ndarray:
    d = 0.5 if open_ else 0.09
    t = t_axis(d)
    x = bandpass(metal6(d), 6500, 12000) + 0.3 * highpass(noise(d), 9000)
    return normalize(highpass(x, 7000) * np.exp(-t * (6 if open_ else 45)), 0.45)


def ride() -> np.ndarray:
    t = t_axis(1.6)
    x = bandpass(metal6(1.6, 1.4), 3500, 9000) * (0.6 * np.exp(-t * 2.2) + 0.4 * np.exp(-t * 12))
    x += 0.25 * highpass(noise(1.6), 8000) * np.exp(-t * 6)
    return normalize(x, 0.45)


def cowbell808() -> np.ndarray:
    t = t_axis(0.4)
    x = np.sign(np.sin(2 * np.pi * 540 * t)) + np.sign(np.sin(2 * np.pi * 800 * t))
    return normalize(bandpass(x, 500, 2600) * (0.6 * np.exp(-t * 60) + 0.4 * np.exp(-t * 9)), 0.5)


def clave() -> np.ndarray:
    t = t_axis(0.08)
    return normalize(np.sin(2 * np.pi * 2500 * t) * np.exp(-t * 90), 0.5)


def tom808(f: float) -> np.ndarray:
    t = t_axis(0.6)
    ff = f * (1 + 0.25 * np.exp(-t * 25))
    return normalize(np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 5.5), 0.8)


def metal_perc(f: float = 620) -> np.ndarray:
    """Kurzer metallischer Schlag (FM) – wie auf ein Rohr geklopft."""
    t = t_axis(0.25)
    return normalize(fm(f, len(t), 3.47, 4.0, 20) * np.exp(-t * 22), 0.6)


def clap_room() -> np.ndarray:
    """Clap mit kurzem Raumhall."""
    x = reverb(clap(), 0.6, mix=0.35, damp=7000)
    return normalize(x[:, 0] + x[:, 1], 0.8)


def chip_noise(seconds: float = 0.15, rate: float = 9000, decay: float = 25, periodic: bool = False) -> np.ndarray:
    """Rausch-Kanal alter Konsolen: Zufallswerte, die eine Weile gehalten werden; periodic = metallischer."""
    n = int(seconds * SR)
    hold = max(int(SR / rate), 1)
    vals = rng().choice([-1.0, 1.0], size=(n // hold + 1))
    if periodic:
        vals = np.resize(vals[:31], len(vals))
    x = np.repeat(vals, hold)[:n]
    env = np.round(np.exp(-np.arange(n) / SR * decay) * 15) / 15
    return normalize(x * env, 0.6)


def chip_kick() -> np.ndarray:
    t = t_axis(0.25)
    f = 45 + 300 * np.exp(-t * 30)
    x = osc_tri(f, steps=16) * np.round(np.exp(-t * 12) * 15) / 15
    return normalize(x, 1.0)


# ================================================================== Elektronische Effekte


def uplifter(seconds: float = 2.0) -> np.ndarray:
    t = t_axis(seconds)
    k = t / seconds
    tone = osc_saw(300 * 6 ** k, len(t)) * 0.15
    x = (sweep_noise(seconds, 300, 9000) + tone) * k ** 1.5
    return normalize(highpass(x, 200), 0.6)


def downlifter(seconds: float = 2.0) -> np.ndarray:
    t = t_axis(seconds)
    k = t / seconds
    x = sweep_noise(seconds, 9000, 250) * (1 - k) ** 2
    x += 0.4 * np.sin(2 * np.pi * np.cumsum(400 * 0.12 ** k) / SR) * (1 - k)
    return normalize(x * np.minimum(t / 0.01, 1), 0.6)


def sub_drop() -> np.ndarray:
    t = t_axis(1.4)
    f = 30 + 70 * np.exp(-t * 2.5)
    return normalize(drive(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8), 1.5), 0.95)


def zap() -> np.ndarray:
    t = t_axis(0.3)
    f = 80 + 3000 * np.exp(-t * 22)
    return normalize(osc_pulse(f, duty=0.3) * np.exp(-t * 9), 0.5)


def reverse_crash() -> np.ndarray:
    x = crash()[::-1]
    t = t_axis(len(x) / SR)
    return normalize(x * (t / t[-1]) ** 2, 0.6)


def impact() -> np.ndarray:
    """Tiefer Einschlag mit Hall."""
    x = reverb(boom(), 1.8, mix=0.3, damp=3000)
    return normalize(x[:, 0] + x[:, 1], 0.95)


def rave_stab() -> np.ndarray:
    """Akkord-Schlag (a-Moll) – der Klang der frühen Rave-Partys."""
    t = t_axis(0.7)
    n = len(t)
    x = sum(osc_saw(midi_to_freq(m) * d, n, p) for m in (57, 60, 64, 69) for d, p in ((0.996, 0.1), (1.004, 0.6)))
    x += 0.5 * osc_pulse(midi_to_freq(45), n)
    x = sweep_filter(x, 800 * 2 ** (2.5 * np.exp(-t / 0.12)), 2.0) * np.exp(-t * 5)
    y = reverb(x * np.minimum(t / 0.003, 1), 1.2, mix=0.25)
    return normalize(y[:, 0] + y[:, 1], 0.7)


def dub_siren() -> np.ndarray:
    t = t_axis(1.2)
    f = 600 * 2 ** (0.5 * np.sign(np.sin(2 * np.pi * 3 * t)) + t * 0.6)
    x = osc_pulse(f, duty=0.5) * np.minimum(t / 0.01, 1) * np.minimum((1.2 - t) / 0.1, 1)
    y = echo(lowpass(x, 3000), 0.3, 0.5, 4)
    return normalize(y[:, 0] + y[:, 1], 0.5)


def resonant_sweep(seconds: float = 2.0) -> np.ndarray:
    """Rauschen durch einen quietschenden Filter, der nach oben fährt."""
    t = t_axis(seconds)
    k = t / seconds
    x = sweep_filter(noise(seconds), 200 * 40 ** k, q=9) * k ** 1.5
    return normalize(x, 0.6)


def snare_roll(seconds: float = 2.0) -> np.ndarray:
    """Trommelwirbel, der immer schneller und lauter wird."""
    out = np.zeros(int(seconds * SR))
    s = snare909()
    pos, gap = 0.0, 0.25
    while pos < seconds - 0.02:
        i = int(pos * SR)
        seg = s[:len(out) - i] * (0.3 + 0.7 * pos / seconds)
        out[i:i + len(seg)] += seg
        pos += gap
        gap = max(gap * 0.88, 0.03)
    return normalize(out, 0.7)


def _chip_notes(notes, seconds_each: float, duty: float = 0.5) -> np.ndarray:
    parts = []
    for m in notes:
        t = t_axis(seconds_each)
        parts.append(osc_pulse(midi_to_freq(m), len(t), duty) * np.round(np.exp(-t * 3) * 15) / 15)
    return np.concatenate(parts)


def coin() -> np.ndarray:
    a = _chip_notes([83], 0.07)
    t = t_axis(0.4)
    b = osc_pulse(midi_to_freq(88), len(t)) * np.round(np.exp(-t * 7) * 15) / 15
    return normalize(np.concatenate([a, b]), 0.5)


def jump() -> np.ndarray:
    t = t_axis(0.22)
    f = 250 * 4 ** (t / 0.22)
    return normalize(osc_pulse(f, duty=0.25) * np.round((1 - t / 0.22) * 15) / 15, 0.5)


def powerup() -> np.ndarray:
    scale = [57, 60, 64, 69, 72, 76, 81, 84, 88, 93]
    return normalize(_chip_notes(scale + scale[-3:], 0.045), 0.5)


def gameover() -> np.ndarray:
    return normalize(_chip_notes([76, 72, 69, 67, 64, 60, 57, 45], 0.16, 0.25), 0.5)


def explosion() -> np.ndarray:
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    rates = 6000 * np.exp(-t * 2.5) + 300
    ph = np.cumsum(rates / SR).astype(int)
    vals = rng().uniform(-1, 1, ph[-1] + 1)
    x = vals[ph] * np.round(np.exp(-t * 3) * 15) / 15
    k = chip_kick()
    return normalize(x + 0.6 * np.pad(k, (0, n - len(k))), 0.95)


def chip_riser(seconds: float = 2.0) -> np.ndarray:
    """8-Bit-Riser: ein Arpeggio, das immer höher und schneller wird."""
    out = []
    total, m = 0.0, 0
    tones = [57, 60, 64, 69]
    while total < seconds:
        d = max(0.09 * (1 - total / seconds), 0.025)
        out.append(_chip_notes([tones[m % 4] + 12 * (m // 4 % 3)], d))
        total += d
        m += 1
    x = np.concatenate(out)[:int(seconds * SR)]
    return normalize(x * np.linspace(0.4, 1, len(x)), 0.5)


def chip_laser() -> np.ndarray:
    t = t_axis(0.25)
    f = 2000 * 0.1 ** (t / 0.25)
    return normalize(osc_pulse(f, duty=0.125) * np.round((1 - t / 0.25) * 15) / 15, 0.5)


# ================================================================== Hip-Hop


def kick_dusty() -> np.ndarray:
    """Staubige Boom-Bap-Kick: kurz, rund und etwas dumpf – wie von einer alten Platte."""
    t = t_axis(0.5)
    f = 50 + 90 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
    x += 0.3 * lowpass(noise(0.5), 1500) * np.exp(-t * 60)
    return normalize(lowpass(drive(x * 1.4, 2.0), 3000), 1.0)


def snare_boombap() -> np.ndarray:
    """Fette Hip-Hop-Snare: Snare + Clap übereinander, mit kurzem Raum."""
    s = snare909()
    c = clap()[:len(s)]
    x = reverb(s + 0.6 * np.pad(c, (0, len(s) - len(c))), 0.5, mix=0.25, damp=6000)
    return normalize(lowpass(x[:, 0] + x[:, 1], 9000), 0.8)


def crackle(seconds: float) -> np.ndarray:
    """Knistern einer Schallplatte: viele kleine Knackser und leises Rauschen."""
    n = int(seconds * SR)
    x = 0.04 * lowpass(noise(seconds), 4000)
    g = rng()
    for pos in g.integers(0, n - 200, int(seconds * 25)):
        k = int(g.integers(20, 120))
        x[pos:pos + k] += g.uniform(-1, 1) * np.exp(-np.arange(k) / (k / 4))
    return highpass(x, 800)


def rewind() -> np.ndarray:
    """Rückspulen: die Platte wird schnell zurückgedreht – wiiiuuu!"""
    t = t_axis(0.9)
    f = 2400 * np.exp(-t * 3.5) + 150
    wob = 1 + 0.3 * np.sin(2 * np.pi * 9 * t)
    x = osc_saw(f * wob, len(t)) * 0.4 + sweep_noise(0.9, 6000, 400)
    return normalize(bandpass(x, 200, 7000) * np.minimum(t / 0.02, 1) * (1 - t / 0.9), 0.6)


def baby_scratch() -> np.ndarray:
    """Schneller Scratch: die Platte wird zweimal kurz vor und zurück geschoben."""
    t = t_axis(0.4)
    speed = np.sin(2 * np.pi * 5 * t)
    freq = 250 + 1300 * np.abs(speed)
    tone = sum(np.sin(2 * np.pi * k * np.cumsum(freq) / SR) / k for k in range(1, 6))
    x = (0.6 * tone + 0.4 * bandpass(noise(0.4), 900, 5000)) * np.abs(speed)
    return normalize(x * np.minimum((0.4 - t) / 0.02, 1), 0.7)
