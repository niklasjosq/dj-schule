"""Schlagzeug und DJ-Effekte – alles prozedural mit numpy erzeugt (Mono, float32).

Die Klänge der DJ-Schule stehen oben; die Bausteine für Techno, Acid, Trance und 8-Bit darunter.
"""
from __future__ import annotations

import numpy as np

from .synth import SR, bandpass, highpass, lowpass, noise, normalize, saw, t_axis

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
