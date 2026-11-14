"""Live-DJ-Effekte für den Studio-Modus (laufen im Audio-Thread, Block für Block, ohne Python-Schleifen pro Sample).

Alle Effekte hängen am Taktraster der Engine (origin/beat), damit sie immer im Takt bleiben:

  0–2  Wiederholer (Roll) 1 · ½ · ¼ Schlag – das letzte Stück wird wiederholt; beim Loslassen läuft die Musik
       genau an der richtigen Stelle weiter (sie lief im Hintergrund mit).
  3    Bremse (Tape-Stop) – die Musik wird langsamer und tiefer, bis sie steht.
  4    Echo – nur solange gedrückt wird, kommt Neues ins Echo; die Wiederholungen klingen danach aus.
  5    Gate – schaltet die Musik in Sechzehnteln an und aus.
  6    8-Bit – Bitcrusher.
  7    Hochpass-Aufbau – Bässe verschwinden langsam; loslassen = Drop.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .synth import SR, _biquads

FX_LIST = [
    ("Wiederholer 1", "🔁", "Ein ganzer Schlag wird immer wiederholt – wie eine hängende Platte. "
     "Loslassen, und die Musik läuft genau im Takt weiter!"),
    ("Wiederholer ½", "🔂", "Ein halber Schlag wird wiederholt – das ratterte schneller."),
    ("Wiederholer ¼", "⏩", "Ein Viertel-Schlag wird wiederholt: brrrrr! Perfekt kurz vor dem Drop."),
    ("Bremse", "⏬", "Die Musik wird langsamer und tiefer, bis sie stehen bleibt – wie ein Plattenspieler ohne Strom."),
    ("Echo", "🗣️", "Alles bekommt ein Echo. Lass los – die Wiederholungen klingen noch nach."),
    ("Gate", "✂️", "Die Musik wird ganz schnell an- und ausgeschaltet: tatatatata!"),
    ("8-Bit", "👾", "Der Bitcrusher macht den Klang grob – wie aus einer alten Spielkonsole."),
    ("Hochpass", "🌪️", "Die Bässe verschwinden langsam, die Spannung steigt. Loslassen = DROP!"),
]
ROLL_BEATS = (1.0, 0.5, 0.25)
BRAKE, ECHO, GATE, CRUSH, HIGHPASS = 3, 4, 5, 6, 7
RAMP = int(0.005 * SR)  # 5 ms Überblendung beim An- und Ausschalten
SEAM = int(0.003 * SR)  # 3 ms Blende an den Nahtstellen des Wiederholers


class LiveFX:
    def __init__(self, beat: float):
        self.set_tempo(beat)

    # ------------------------------------------------------------ Steuerung (nur aus dem Audio-Thread!)

    def set_tempo(self, beat: float) -> None:
        self.beat = beat
        self.ring = np.zeros((int(4 * beat) + 8192, 2), np.float32)  # die letzten ~4 Schläge der Musik
        self.echo_buf = np.zeros((max(int(round(0.75 * beat)), 4096), 2), np.float32)
        self.reset()

    def reset(self) -> None:
        self.mix = np.zeros(8)
        self.target = np.zeros(8)
        self.roll: dict | None = None
        self.brake_start: int | None = None
        self.hp_start: int | None = None
        self.hp_zi = np.zeros((1, 2, 2))
        self.echo_buf[:] = 0
        self.echo_pos = 0
        self.echo_zi = np.zeros((1, 2))
        self.echo_tail = 0

    @property
    def active(self) -> frozenset:
        return frozenset(i for i in range(8) if self.target[i] > 0)

    def on(self, i: int, frame: int, origin: int) -> None:
        if i < 3:
            length = ROLL_BEATS[i] * self.beat
            L = max(int(round(length)), SEAM * 4)
            anchor = int(round(origin + math.floor((frame - origin) / length) * length))
            anchor = min(anchor, frame)
            buf = np.zeros((L, 2), np.float32)
            have = min(frame - anchor, L)
            if have > 0:
                buf[:have] = self._ring_read(anchor, have)
            self.roll = {"i": i, "anchor": anchor, "L": L, "buf": buf}
            for k in range(3):
                self.target[k] = self.mix[k] = 0.0
            self.target[i] = self.mix[i] = 1.0  # der erste Durchgang ist ohnehin live
        elif i == BRAKE:
            self.brake_start = frame
            self.target[i] = self.mix[i] = 1.0  # Start mit Tempo 1 = genau die Live-Musik
        elif i == HIGHPASS:
            self.hp_start = frame
            self.hp_zi[:] = 0
            self.target[i] = 1.0
        else:
            self.target[i] = 1.0
            if i == ECHO:
                self.echo_tail = 1

    def off(self, i: int) -> None:
        if i < 3 and (self.roll is None or self.roll["i"] != i):
            return  # ein anderer Wiederholer hat übernommen
        self.target[i] = 0.0
        if i == ECHO:
            self.echo_tail = int(len(self.echo_buf) * 24)  # Ausklingen lassen

    # ------------------------------------------------------------ Verarbeitung

    def process(self, x: np.ndarray, f0: int, origin: int) -> np.ndarray:
        n = len(x)
        self._ring_write(x, f0)
        y = x.astype(np.float64)
        if self.roll is not None:
            y = self._apply(self.roll["i"], y, self._roll_out(x, f0))
            if self.mix[self.roll["i"]] == 0 and self.target[self.roll["i"]] == 0:
                self.roll = None
        if self.brake_start is not None:
            y = self._apply(BRAKE, y, self._brake_out(f0, n))
            if self.mix[BRAKE] == 0 and self.target[BRAKE] == 0:
                self.brake_start = None
        if self.mix[GATE] or self.target[GATE]:
            y = self._apply(GATE, y, y * self._gate(f0, n, origin)[:, None])
        if self.mix[CRUSH] or self.target[CRUSH]:
            z = np.repeat(y[::6], 6, axis=0)[:n]
            y = self._apply(CRUSH, y, np.round(z * 32) / 32)
        if self.hp_start is not None:
            y = self._apply(HIGHPASS, y, self._highpass(y, f0))
            if self.mix[HIGHPASS] == 0 and self.target[HIGHPASS] == 0:
                self.hp_start = None
        if self.echo_tail > 0:
            y = self._echo(y)
        return y.astype(np.float32)

    def _ramp(self, i: int, n: int):
        cur, tgt = self.mix[i], self.target[i]
        if cur == tgt:
            return cur
        arr = np.clip(cur + np.sign(tgt - cur) * np.arange(1, n + 1) / RAMP, 0.0, 1.0)
        self.mix[i] = arr[-1]
        return arr[:, None]

    def _apply(self, i: int, dry: np.ndarray, wet: np.ndarray) -> np.ndarray:
        m = self._ramp(i, len(dry))
        if np.isscalar(m):
            return wet if m == 1 else dry if m == 0 else dry * (1 - m) + wet * m
        return dry * (1 - m) + wet * m

    # Ringspeicher mit der unbearbeiteten Musik (absolute Frame-Nummern)
    def _ring_write(self, x: np.ndarray, f0: int) -> None:
        idx = (f0 + np.arange(len(x))) % len(self.ring)
        self.ring[idx] = x

    def _ring_read(self, start: int, n: int) -> np.ndarray:
        return self.ring[(start + np.arange(n)) % len(self.ring)]

    def _roll_out(self, x: np.ndarray, f0: int) -> np.ndarray:
        r = self.roll
        L, buf = r["L"], r["buf"]
        rel = f0 + np.arange(len(x)) - r["anchor"]
        live = rel < L
        rec = live & (rel >= 0)
        buf[rel[rec]] = x[rec]
        pos = np.where(live, rel, rel % L)
        out = np.where(live[:, None], x, buf[pos % L]).astype(np.float64)
        # Blende: Ende jedes Durchgangs aus, Anfang jeder Wiederholung ein
        g = np.minimum(1.0, (L - pos) / SEAM)
        g = np.where(live, g, np.minimum(g, pos / SEAM))
        return out * np.clip(g, 0, 1)[:, None]

    def _brake_out(self, f0: int, n: int) -> np.ndarray:
        T = self.beat
        u = np.clip(f0 + np.arange(n) - self.brake_start, 0, T)
        pos = self.brake_start + u - u * u / (2 * T)  # Tempo fällt linear von 1 auf 0
        rate = 1 - u / T
        i0 = np.floor(pos).astype(np.int64)
        frac = (pos - i0)[:, None]
        a = self.ring[i0 % len(self.ring)]
        b = self.ring[(i0 + 1) % len(self.ring)]
        return (a * (1 - frac) + b * frac) * np.minimum(rate * 3, 1)[:, None]

    def _gate(self, f0: int, n: int, origin: int) -> np.ndarray:
        period = self.beat / 4
        ph = ((f0 + np.arange(n) - origin) % period) / period
        edge = 48 / period
        return np.clip(ph / edge, 0, 1) * np.clip((0.55 - ph) / edge, 0, 1)

    def _highpass(self, y: np.ndarray, f0: int) -> np.ndarray:
        k = min(max(f0 - self.hp_start, 0) / (4 * self.beat), 1.0)
        fc = 30 * (2000 / 30) ** k
        sos = _biquads("high", np.array([fc]), 0.9)
        out, self.hp_zi = signal.sosfilt(sos, y, axis=0, zi=self.hp_zi)
        return out

    def _echo(self, y: np.ndarray) -> np.ndarray:
        n = len(y)
        D = len(self.echo_buf)
        send = self._ramp(ECHO, n)
        send = np.broadcast_to(np.asarray(send, dtype=float), (n, 1)) if np.isscalar(send) else send
        out = y.copy()
        s = 0
        while s < n:
            k = min(n - s, D - self.echo_pos)
            idx = slice(self.echo_pos, self.echo_pos + k)
            read = self.echo_buf[idx].astype(np.float64)
            fb, self.echo_zi = signal.lfilter([0.35], [1, -0.65], read, axis=0, zi=self.echo_zi)
            self.echo_buf[idx] = send[s:s + k] * y[s:s + k] + 0.55 * fb[:, ::-1]  # Ping-Pong
            out[s:s + k] += 0.7 * read
            self.echo_pos = (self.echo_pos + k) % D
            s += k
        if self.target[ECHO] == 0 and self.mix[ECHO] == 0:
            self.echo_tail -= n
            if self.echo_tail <= 0:
                self.echo_buf[:] = 0
                self.echo_zi[:] = 0
        return out
