"""Kleine Klangerzeugung mit numpy: Oszillatoren, Hüllkurven, Instrumente.

Alle Funktionen liefern Mono-Arrays (float32) bei der Abtastrate SR.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

SR = 48000
_rng = np.random.default_rng(7)


def reseed(seed: int) -> None:
    """Zufall neu starten – so klingt jeder Stil bei jedem Start gleich."""
    global _rng
    _rng = np.random.default_rng(seed)


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


# ---------------------------------------------------------------- Bausteine für elektronische Klänge
# (Techno, Acid, Trance, 8-Bit). Oszillatoren nehmen eine Frequenz-Kurve pro Sample, damit Töne
# gleiten, vibrieren oder sich verbiegen können.


def rng() -> np.random.Generator:
    return _rng


def curve(value, n: int | None = None) -> np.ndarray:
    """Zahl oder Kurve als Array mit n Werten."""
    if np.isscalar(value):
        return np.full(int(n), float(value))
    return np.asarray(value, dtype=float)


def _phase(freq: np.ndarray, phase0: float = 0.0) -> np.ndarray:
    return (phase0 + (np.cumsum(freq) - freq) / SR) % 1.0


def _blep(ph: np.ndarray, dt: np.ndarray) -> np.ndarray:
    """PolyBLEP: glättet die Sprünge der Wellenform (weniger schrilles Aliasing)."""
    out = np.zeros_like(ph)
    a = ph < dt
    x = ph[a] / dt[a]
    out[a] = 2 * x - x * x - 1
    b = ph > 1 - dt
    x = (ph[b] - 1) / dt[b]
    out[b] = x * x + 2 * x + 1
    return out


def osc_sine(freq, n: int | None = None, phase0: float = 0.0) -> np.ndarray:
    return np.sin(2 * np.pi * _phase(curve(freq, n), phase0))


def osc_saw(freq, n: int | None = None, phase0: float = 0.0) -> np.ndarray:
    f = curve(freq, n)
    ph = _phase(f, phase0)
    return 2 * ph - 1 - _blep(ph, np.clip(f / SR, 1e-6, 0.5))


def osc_pulse(freq, n: int | None = None, duty=0.5, phase0: float = 0.0) -> np.ndarray:
    """Rechteck/Puls; duty darf eine Kurve sein (Pulsbreiten-Modulation)."""
    f = curve(freq, n)
    ph = _phase(f, phase0)
    dt = np.clip(f / SR, 1e-6, 0.5)
    x = np.where(ph < duty, 1.0, -1.0) + _blep(ph, dt) - _blep((ph - duty) % 1.0, dt)
    return x - (2 * np.asarray(duty) - 1)


def osc_tri(freq, n: int | None = None, steps: int = 0, phase0: float = 0.0) -> np.ndarray:
    """Dreieck; steps=16 ergibt den treppigen Klang alter Spielkonsolen."""
    x = 4 * np.abs(_phase(curve(freq, n), phase0) - 0.5) - 1
    if steps:
        x = np.round((x + 1) / 2 * (steps - 1)) / (steps - 1) * 2 - 1
    return x


SUPERSAW_OFFSETS = (-0.11002313, -0.06288439, -0.01952356, 0.0, 0.01991221, 0.06216538, 0.10745242)


def supersaw(freq, n: int, detune: float = 0.22, mix: float = 0.7) -> np.ndarray:
    """7 gegeneinander verstimmte Sägezähne, links und rechts verschieden -> (n, 2)."""
    f = curve(freq, n)
    out = np.zeros((n, 2))
    for k, off in enumerate(SUPERSAW_OFFSETS):
        g = 1.0 if off == 0 else mix
        for ch in range(2):
            side = 1.0 if off == 0 else (0.85 if k % 2 == ch else 0.35)
            out[:, ch] += g * side * osc_saw(f * (1 + off * detune), phase0=_rng.random())
    return out / (1 + 3.6 * mix)


def fm(freq: float, n: int, ratio: float = 2.0, index: float = 2.0, decay: float = 8.0) -> np.ndarray:
    """FM-Klang: ein Sinus moduliert einen anderen – glockig bis metallisch."""
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t + index * np.exp(-t * decay) * np.sin(2 * np.pi * freq * ratio * t))


def _biquads(kind: str, fc: np.ndarray, q: float) -> np.ndarray:
    """RBJ-Biquad-Koeffizienten (als sos-Zeilen) für viele Grenzfrequenzen auf einmal."""
    w0 = 2 * np.pi * np.clip(fc, 20, SR * 0.45) / SR
    alpha, c = np.sin(w0) / (2 * q), np.cos(w0)
    if kind == "low":
        b0, b1 = (1 - c) / 2, 1 - c
    else:
        b0, b1 = (1 + c) / 2, -(1 + c)
    a0 = 1 + alpha
    return np.stack([b0 / a0, b1 / a0, b0 / a0, np.ones_like(c), -2 * c / a0, (1 - alpha) / a0], axis=-1)


def sweep_filter(x: np.ndarray, cutoff, q: float = 0.7, kind: str = "low", chunk: int = 64) -> np.ndarray:
    """Filter mit wandernder Grenzfrequenz (Hz, Zahl oder Kurve pro Sample), 24 dB/Okt.

    Zwei Biquads hintereinander; die Resonanz q steckt in der zweiten Stufe (das "Quietschen" bei Acid).
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    fc = curve(cutoff, n)[::chunk]
    sos = np.stack([_biquads(kind, fc, 0.707), _biquads(kind, fc, q)], axis=1)
    zi = np.zeros((2, 2) + x.shape[1:])
    y = np.empty_like(x)
    for i, s in enumerate(range(0, n, chunk)):
        y[s:s + chunk], zi = signal.sosfilt(sos[i], x[s:s + chunk], axis=0, zi=zi)
    return y


def drive(x: np.ndarray, amount: float = 2.0) -> np.ndarray:
    """Sanfte Verzerrung (Sättigung)."""
    return np.tanh(amount * x) / np.tanh(amount)


def crush(x: np.ndarray, bits: int = 6, hold: int = 4) -> np.ndarray:
    """Bitcrusher: weniger Stufen und weniger Abtastungen – klingt nach alter Spielkonsole."""
    y = np.repeat(x[::hold], hold, axis=0)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q


def chorus(x: np.ndarray, depth_ms: float = 2.5, base_ms: float = 9.0, rate: float = 0.7,
           mix: float = 0.5) -> np.ndarray:
    """Chorus: leicht schwankend verzögerte Kopien links und rechts -> breiter Stereoklang (n, 2)."""
    i = np.arange(len(x), dtype=float)
    out = np.empty((len(x), 2))
    for ch, ph in enumerate((0.0, np.pi / 2)):
        d = (base_ms + depth_ms * np.sin(2 * np.pi * rate * i / SR + ph)) * SR / 1000
        out[:, ch] = (1 - mix) * x + mix * np.interp(i - d, i, x, left=0.0)
    return out


def _as_stereo(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def reverb(x: np.ndarray, seconds: float = 1.5, mix: float = 0.3, damp: float = 6000,
           dry: float = 1.0) -> np.ndarray:
    """Hall: Faltung mit abklingendem Rauschen (links/rechts verschieden). Ergebnis länger und Stereo."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    env = np.exp(-6.9 * t / seconds) * np.minimum(t / 0.008, 1)
    ir = np.stack([lowpass(_rng.standard_normal(n), damp) * env for _ in range(2)], axis=1)
    ir /= np.sqrt(np.sum(ir ** 2, axis=0))
    xs = _as_stereo(np.asarray(x, dtype=float))
    out = mix * np.stack([signal.fftconvolve(xs[:, c], ir[:, c]) for c in range(2)], axis=1)
    out[:len(xs)] += dry * xs
    return out


def echo(x: np.ndarray, delay: float, feedback: float = 0.5, repeats: int = 6, damp: float = 2500,
         mix: float = 0.6, pingpong: bool = True) -> np.ndarray:
    """Echo (Delay in Sekunden): jede Wiederholung leiser und dumpfer, abwechselnd links/rechts."""
    xs = _as_stereo(np.asarray(x, dtype=float))
    d = int(round(delay * SR))
    out = np.zeros((len(xs) + repeats * d, 2))
    out[:len(xs)] += xs
    tap = xs
    for k in range(1, repeats + 1):
        tap = lowpass(tap.T, damp).T
        side = np.array([1.0, 0.25] if k % 2 else [0.25, 1.0]) if pingpong else np.ones(2)
        out[k * d:k * d + len(xs)] += tap * side * mix * feedback ** (k - 1)
    return out


def pump(buf: np.ndarray, beat_frames: float, depth: float = 0.6, release: float = 0.15,
         attack: float = 0.004) -> np.ndarray:
    """Sidechain-"Pumpen": auf jedem Schlag kurz leiser, dann wieder lauter – macht Platz für die Kick."""
    t = (np.arange(len(buf)) % beat_frames) / SR
    g = 1 - depth * np.exp(-t / release) * np.minimum(t / attack, 1)
    return (buf * (g[:, None] if buf.ndim == 2 else g)).astype(np.float32)


def acid_line(steps, bpm: float, wave: str = "saw", cutoff: float = 250.0, env_mod: float = 3.0,
              q: float = 6.0, decay: float = 0.22, accent: float = 1.0, glide: float = 0.04,
              macro=None, gate: float = 0.55, drive_amt: float = 2.0) -> np.ndarray:
    """Acid-Lauf im Stil einer 303 – in einem Stück gerendert, damit Slides und Filter durchlaufen.

    steps: Liste je Sechzehntel mit (midi oder None, Akzent, Slide).
      Akzent = lauter, heller, kürzer.  Slide = Ton bleibt liegen und gleitet in den nächsten.
    macro: Kurve (Oktaven) über die ganze Länge, z. B. Filter langsam öffnen.
    """
    step = 60.0 / bpm / 4 * SR
    n = int(round(len(steps) * step)) + int(0.3 * SR)
    fr = np.full(n, np.nan)
    gate_sig = np.zeros(n)
    env = np.zeros(n)
    acc_cap = 0.0
    prev_f = None
    for i, (m, acc, slide) in enumerate(steps):
        s, e = int(round(i * step)), int(round((i + 1) * step))
        acc_cap *= np.exp(-step / SR / 0.3)
        if m is None:
            continue
        f = midi_to_freq(m)
        legato = i > 0 and steps[i - 1][0] is not None and steps[i - 1][2]
        nxt = steps[i + 1] if i + 1 < len(steps) else (None, False, False)
        tt = np.arange(e - s) / SR
        fr[s:e] = f + (prev_f - f) * np.exp(-tt / glide) if legato and prev_f else f
        g_end = e if slide and nxt[0] is not None else s + int(gate * step)
        gate_sig[s:g_end] = 1.6 if acc else 1.0
        if acc:
            acc_cap += 0.6
        if not legato:
            d = decay * (0.5 if acc else 1.0)
            k = np.arange(n - s) / SR
            env[s:] = np.exp(-k / d) * (1 + accent * acc_cap * (1.0 if acc else 0.3))
        prev_f = f
    # Frequenz vor dem ersten Ton/in Pausen festhalten
    idx = np.where(np.isnan(fr), 0, np.arange(n))
    np.maximum.accumulate(idx, out=idx)
    first = np.argmax(~np.isnan(fr))
    fr = np.where(np.isnan(fr), fr[idx], fr)
    fr[:first] = fr[first]
    fr = np.nan_to_num(fr, nan=110.0)
    osc = {"saw": osc_saw, "square": lambda f: osc_pulse(f, duty=0.5), "sine": osc_sine,
           "tri": osc_tri}[wave](fr)
    amp = signal.lfilter([0.006], [1, -0.994], gate_sig)  # ca. 3 ms Glättung gegen Knackser
    mac = 0.0 if macro is None else np.interp(np.arange(n), np.linspace(0, n, len(macro)), macro)
    y = sweep_filter(osc, cutoff * 2 ** (env_mod * env + mac), q) * amp
    return drive(y * 1.2, drive_amt)


# ------------------------------------------------------------- elektronische Instrumente


def sub(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.08)
    x = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(4 * np.pi * f * t)
    return drive(x, 1.3) * adsr(len(t), 0.004, 0.1, 0.85, dur, 0.05)


def reese(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.15)
    n = len(t)
    x = osc_saw(f * 0.993, n) + osc_saw(f * 1.007, n, 0.37) + 0.6 * np.sin(np.pi * f * t)
    x = sweep_filter(x, 450 + 250 * np.sin(2 * np.pi * 0.3 * t), 1.5)
    return 0.55 * x * adsr(n, 0.01, 0.2, 0.9, dur, 0.1)


def acid(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.15)
    n = len(t)
    x = sweep_filter(osc_saw(f, n), 240 * 2 ** (3.0 * np.exp(-t / 0.18) + 0.5), q=7)
    return 0.8 * drive(1.4 * x * adsr(n, 0.003, 0.1, 0.8, dur, 0.06), 2.0)


def squelch(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.15)
    n = len(t)
    x = sweep_filter(osc_pulse(f, n), 300 * 2 ** (3.5 * np.exp(-t / 0.3) + 0.8), q=10)
    return 0.75 * drive(1.4 * x * adsr(n, 0.003, 0.1, 0.8, dur, 0.06), 2.5)


def blip(f: float, dur: float) -> np.ndarray:
    t = t_axis(0.6)
    return 1.8 * fm(f, len(t), 2.0, 2.5, 12) * np.exp(-t * 7) * np.minimum(t / 0.002, 1)


def supersaw_inst(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.4)
    x = supersaw(f, len(t), 0.22)
    x = highpass(lowpass(x.T, min(f * 14, 9000)), f * 0.8).T
    return 2.0 * x * adsr(len(t), 0.01, 0.4, 0.8, dur, 0.35)[:, None]


def hoover(f: float, dur: float) -> np.ndarray:
    """Der "Staubsauger"-Klang aus den 90ern: Puls + Säge + Sub, beim Anschlag von unten hochgebogen."""
    t = t_axis(dur + 0.3)
    n = len(t)
    fr = f * 2 ** (-4 * np.exp(-t / 0.07) / 12)
    pw = 0.3 + 0.15 * np.sin(2 * np.pi * 1.3 * t)
    x = osc_saw(fr) + 0.7 * osc_pulse(fr, duty=pw) + 0.6 * osc_pulse(fr / 4, duty=0.5)
    x = chorus(lowpass(x, 4500), 3.5, 10, 0.9, 0.6)
    return 1.3 * x * adsr(n, 0.01, 0.3, 0.85, dur, 0.2)[:, None]


def _chip_env(n: int, dur: float, sustain: float = 0.6) -> np.ndarray:
    v = adsr(n, 0.002, 0.25, sustain, dur, 0.06)
    return np.round(v * 15) / 15  # 16 Lautstärke-Stufen wie bei alten Konsolen


def _vibrato(t: np.ndarray, delay: float = 0.2, depth: float = 0.25, rate: float = 6.0) -> np.ndarray:
    return 2 ** (depth / 12 * np.sin(2 * np.pi * rate * t) * np.clip((t - delay) / 0.1, 0, 1))


def chip_square(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.06)
    return 0.85 * osc_pulse(f * _vibrato(t), duty=0.5) * _chip_env(len(t), dur)


def chip_pulse(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.06)
    return 1.1 * osc_pulse(f * _vibrato(t), duty=0.125) * _chip_env(len(t), dur)


def chip_tri(f: float, dur: float) -> np.ndarray:
    t = t_axis(dur + 0.03)
    return osc_tri(f, len(t), steps=16) * adsr(len(t), 0.002, 0, 1, dur, 0.02)


def orgel(f: float, dur: float) -> np.ndarray:
    """Orgel wie in alten House-Platten: Zugriegel-Obertöne + kurzer Klick."""
    t = t_axis(dur + 0.08)
    x = additive(f, t, [0.8, 0.7, 0.5, 0.35, 0, 0.25, 0, 0.2])
    x += 0.5 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 18)
    return 0.7 * x * adsr(len(t), 0.004, 0.1, 0.8, dur, 0.05)


def dubstab(f: float, dur: float) -> np.ndarray:
    t = t_axis(0.45)
    n = len(t)
    x = osc_saw(f * 0.997, n) + osc_pulse(f * 1.003, n) * 0.6
    x = sweep_filter(x, 500 * 2 ** (1.8 * np.exp(-t / 0.08)), 1.2)
    return x * np.exp(-t * 7) * np.minimum(t / 0.003, 1)


INSTRUMENTS = {
    "klavier": klavier, "lead": lead, "glocke": glocke, "bass": bass,
    "pad": pad, "pluck": pluck, "stab": stab, "vokal": vokal,
    "sub": sub, "reese": reese, "acid": acid, "squelch": squelch, "blip": blip,
    "supersaw": supersaw_inst, "hoover": hoover, "chip_square": chip_square, "chip_pulse": chip_pulse,
    "chip_tri": chip_tri, "orgel": orgel, "dubstab": dubstab,
}


@lru_cache(maxsize=2048)
def render_note(instrument: str, midi: int, dur: float) -> np.ndarray:
    """Gecachter Einzelton (Mono, float32)."""
    return INSTRUMENTS[instrument](midi_to_freq(midi), dur).astype(np.float32)
