"""Kleine Klangerzeugung mit numpy: Oszillatoren, Hüllkurven, Instrumente.

Alle Funktionen liefern Mono-Arrays (float32) bei der Abtastrate SR.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

SR = 48000
_rng = np.random.default_rng(7)


def midi_to_freq(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def t_axis(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def adsr(n: int, a: float, d: float, s: float, hold: float, r: float) -> np.ndarray:
    """Hüllkurve mit Länge n Samples: Attack, Decay auf Sustain bis hold, dann Release."""
    a, d, r = max(a, 1e-4), max(d, 1e-4), max(r, 1e-4)

    def ads(tt):
        return np.where(tt < a, tt / a, np.where(tt < a + d, 1 - (1 - s) * (tt - a) / d, s))

    t = np.arange(n) / SR
    level_at_hold = float(ads(np.array([hold]))[0])
    release = level_at_hold * np.clip(1 - (t - hold) / r, 0, 1)
    return np.where(t < hold, ads(t), release)


def additive(freq: float, t: np.ndarray, amps, decays=None, detune: float = 0.0) -> np.ndarray:
    """Summe von Obertönen; amps[k] gehört zu Oberton k+1. decays: Abklingrate pro Oberton."""
    out = np.zeros_like(t)
    f = freq * (1 + detune)
    for k, amp in enumerate(amps, start=1):
        if f * k > SR * 0.45:
            break
        h = amp * np.sin(2 * np.pi * f * k * t)
        if decays is not None:
            h *= np.exp(-t * decays[k - 1])
        out += h
    return out


def saw(freq: float, t: np.ndarray, detune: float = 0.0, max_h: int = 40) -> np.ndarray:
    n_h = int(min(max_h, (SR * 0.4) // max(freq, 1)))
    return additive(freq, t, [1 / k for k in range(1, n_h + 1)], detune=detune) * 0.6


def lowpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    b, a = signal.butter(order, min(cutoff, SR * 0.45) / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def highpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    b, a = signal.butter(order, cutoff / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    b, a = signal.butter(order, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def noise(seconds: float) -> np.ndarray:
    return _rng.uniform(-1, 1, int(seconds * SR))


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x)) if len(x) else 0
    return (x * (peak / m) if m > 0 else x).astype(np.float32)


# ---------------------------------------------------------------- Instrumente
# Jede Funktion: (Frequenz, gehaltene Dauer in s) -> Mono-Array inkl. Ausklang


def klavier(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.6)
    x = additive(f, t, [1, 0.5, 0.3, 0.2, 0.12, 0.08, 0.05, 0.03],
                 decays=[1.2 + k * 0.9 for k in range(8)])
    x += 0.3 * additive(f, t, [1, 0.3], decays=[1.6, 3], detune=0.002)
    return x * adsr(len(t), 0.004, 0.0, 1.0, dur, 0.25)


def lead(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.2)
    x = saw(f, t, -0.004) + saw(f, t, 0.004) + 0.4 * np.sin(2 * np.pi * f / 2 * t)
    x = lowpass(x, 3500)
    return x * adsr(len(t), 0.01, 0.15, 0.7, dur, 0.15)


def glocke(f: float, dur: float) -> np.ndarray:
    t = t_axis(max(dur, 1.2) + 0.4)
    index = 2.5 * np.exp(-t * 4)
    x = np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * f * 3.5 * t))
    x += 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3)
    return x * np.exp(-t * 2.2) * adsr(len(t), 0.002, 0, 1, max(dur, 1.2), 0.3)


def bass(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.1)
    x = lowpass(saw(f, t, max_h=25), 700) + 0.8 * np.sin(2 * np.pi * f * t)
    return x * adsr(len(t), 0.005, 0.2, 0.65, dur, 0.06)


def pad(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.6)
    x = saw(f, t, -0.006, 20) + saw(f, t, 0.006, 20) + saw(f, t, 0.0, 20)
    x = lowpass(x, 1400)
    return x * adsr(len(t), 0.35, 0.3, 0.8, dur, 0.5)


def pluck(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.4)
    x = additive(f, t, [1 / k for k in range(1, 16)], decays=[4 + k * 2.5 for k in range(15)])
    return x * adsr(len(t), 0.002, 0, 1, dur, 0.2)


def stab(f: float, dur: float) -> np.ndarray:
    t = t_axis(0.35)
    x = lowpass(saw(f, t, -0.005) + saw(f, t, 0.005), 2500)
    return x * np.exp(-t * 9)


def vokal(f: float, dur: float) -> np.ndarray:
    """Synthetisches "Aah" (Formant-Synthese)."""
    t = t_axis(dur + 0.1)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t)
    phase = np.cumsum(f * vib) / SR
    src = sum(np.sin(2 * np.pi * k * phase) / k for k in range(1, int(5000 // f)))
    x = (bandpass(src, 650, 950) + 0.6 * bandpass(src, 1050, 1300) + 0.25 * bandpass(src, 2700, 3100))
    return x * adsr(len(t), 0.03, 0.1, 0.8, dur, 0.08)


INSTRUMENTS = {
    "klavier": klavier, "lead": lead, "glocke": glocke, "bass": bass,
    "pad": pad, "pluck": pluck, "stab": stab, "vokal": vokal,
}


@lru_cache(maxsize=2048)
def render_note(instrument: str, midi: int, dur: float) -> np.ndarray:
    """Gecachter Einzelton (Mono, float32)."""
    return INSTRUMENTS[instrument](midi_to_freq(midi), dur).astype(np.float32)
