"""Live-Effekte (Studio-Modus): im Takt, sauber zurück in die Musik, Keyboard bleibt trocken."""
import time

import numpy as np

from apc_dj.audio.engine import TRACK_KEYS, AudioEngine
from apc_dj.audio.fx import BRAKE, CRUSH, ECHO, GATE, HIGHPASS, RAMP, SEAM, LiveFX
from apc_dj.audio.seq import bar_frames
from conftest import run

BEAT = 24000  # 120 BPM
BLOCK = 256


def signal_at(t):
    """Eindeutiges Testsignal: jeder Frame hat einen anderen Wert."""
    v = (np.asarray(t) % 100000) / 100000.0
    return np.stack([v, -v], axis=1).astype(np.float32)


def feed(fx, start, stop, origin=0, sig=signal_at, events=()):
    """Blöcke durch den Effekt schicken; events: {frame: callable}."""
    out = []
    ev = dict(events)
    for f0 in range(start, stop, BLOCK):
        if f0 in ev:
            ev[f0]()
        out.append(fx.process(sig(np.arange(f0, f0 + BLOCK)), f0, origin))
    return np.concatenate(out)


def test_roll_repeats_grid_slice_and_slips_back_in_time():
    fx = LiveFX(BEAT)
    press, release = 30208, 48128  # Blockgrenzen
    out = feed(fx, 0, 60160, events={press: lambda: fx.on(2, press, 0), release: lambda: fx.off(2)})
    L = BEAT // 4
    anchor = 30000  # Rasterpunkt (Vielfaches von L) vor dem Drücken
    for t in (anchor + L + 1000, anchor + 2 * L + 3000, release - 1000):
        src = anchor + (t - anchor) % L
        np.testing.assert_allclose(out[t], signal_at([src])[0], atol=1e-6)
    t = release + RAMP + 10  # nach dem Loslassen: genau die Live-Musik (lief im Hintergrund weiter)
    np.testing.assert_allclose(out[t:t + 500], signal_at(np.arange(t, t + 500)), atol=1e-6)
    seam = anchor + 2 * L  # Nahtstelle wird weich überblendet
    assert np.abs(out[seam]).max() < 0.01 and SEAM > 0


def test_later_roll_wins_and_releasing_the_old_one_keeps_it():
    fx = LiveFX(BEAT)
    fx.on(0, 1024, 0)
    fx.on(2, 2048, 0)
    fx.off(0)
    assert fx.roll["i"] == 2 and fx.target[2] == 1


def test_brake_slows_down_to_silence_and_returns_live():
    fx = LiveFX(BEAT)
    press, release = 10240, 40192
    out = feed(fx, 0, 50176, events={press: lambda: fx.on(BRAKE, press, 0), release: lambda: fx.off(BRAKE)})
    np.testing.assert_allclose(out[press:press + 10], signal_at(np.arange(press, press + 10)), atol=1e-3)
    assert np.abs(out[press + BEAT + 100:release]).max() == 0
    t = release + RAMP + 10
    np.testing.assert_allclose(out[t:t + 100], signal_at(np.arange(t, t + 100)), atol=1e-6)


def test_echo_repeats_and_rings_out_after_release():
    fx = LiveFX(BEAT)
    D = len(fx.echo_buf)
    imp_at = 2048

    def sig(t):
        x = np.zeros((len(t), 2), np.float32)
        x[t == imp_at] = 1.0
        return x

    out = feed(fx, 0, 4 * D, sig=sig, events={0: lambda: fx.on(ECHO, 0, 0), 4096: lambda: fx.off(ECHO)})
    assert abs(out[imp_at + D, 0] - 0.7) < 0.05  # erstes Echo
    assert np.abs(out[imp_at + 2 * D - 50:imp_at + 2 * D + 200]).max() > 0.05  # klingt nach dem Loslassen weiter


def test_gate_chops_sixteenths_on_the_grid():
    fx = LiveFX(BEAT)
    ones = lambda t: np.ones((len(t), 2), np.float32)  # noqa: E731
    out = feed(fx, 0, 4 * BEAT, sig=ones, events={0: lambda: fx.on(GATE, 0, 0)})
    p = BEAT // 4
    for k in range(4, 12):
        assert out[k * p + int(0.25 * p), 0] > 0.99  # an
        assert out[k * p + int(0.8 * p), 0] < 0.01  # aus


def test_crush_quantises_and_highpass_removes_bass():
    fx = LiveFX(BEAT)
    fx.on(CRUSH, 0, 0)
    out = feed(fx, 0, 4096, sig=lambda t: signal_at(t) * 0.37)
    late = out[RAMP + 10:]
    assert np.allclose(late * 32, np.round(late * 32), atol=1e-4)

    fx = LiveFX(BEAT)
    sine = lambda t: np.repeat(np.sin(2 * np.pi * 50 * t / 48000)[:, None], 2, 1).astype(np.float32)  # noqa: E731
    fx.on(HIGHPASS, 0, 0)
    out = feed(fx, 0, 6 * BEAT, sig=sine)
    assert np.abs(out[5 * BEAT:]).max() < 0.1  # nach einem Takt fast keine Bässe mehr


def test_engine_without_effects_pressed_sounds_unchanged():
    loop = (np.sin(np.arange(96000) / 30.0)[:, None] * np.array([0.3, 0.2])).astype(np.float32)
    a, b = AudioEngine(120), AudioEngine(120, fx=True)
    for e in (a, b):
        e.launch(0, 0, loop)
    np.testing.assert_allclose(run(a, 0.5), run(b, 0.5), atol=1e-6)


def test_keyboard_stays_dry_while_gate_is_on():
    e = AudioEngine(120, fx=True)
    e.fx_on(GATE)
    e.play(np.full((48000, 2), 0.2, np.float32), TRACK_KEYS)
    out = run(e, 0.5)
    assert np.abs(out[1000:20000]).min() > 0.1


def test_stop_all_and_set_tempo_reset_effects():
    e = AudioEngine(120, fx=True)
    e.fx_on(BRAKE)
    run(e, 0.01)
    assert e.fx.brake_start is not None
    e.stop_all()
    run(e, 0.01)
    assert e.fx.brake_start is None
    e.launch(0, 0, np.full((96000, 2), 0.1, np.float32))
    run(e, 0.1)
    e.set_tempo(140)
    run(e, 0.01)
    assert e.bar == bar_frames(140) and e.snapshot.playing == {}
    assert e.origin > 0 and e.fx.beat == bar_frames(140) / 4


def test_all_effects_are_cheap_enough_for_real_time(lib):
    e = AudioEngine(120, fx=True)
    for col in range(7):
        e.launch(col, 0, lib.loops[(col, 0)].data)
    run(e, 0.2)
    for i in (2, BRAKE, ECHO, GATE, CRUSH, HIGHPASS):
        e.fx_on(i)
    run(e, 0.1)
    t = time.perf_counter()
    for _ in range(200):
        e._block(256)
    per_block = (time.perf_counter() - t) / 200
    assert per_block < 0.5 * 256 / 48000, per_block
