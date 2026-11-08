import numpy as np

from apc_dj.audio.engine import AudioEngine, TRACK_SHOTS
from conftest import run

BAR = 96000  # 120 BPM, 48 kHz


def loop(value=0.1, bars=1):
    return np.full((BAR * bars, 2), value, np.float32)


def test_first_loop_starts_immediately_and_sets_grid():
    e = AudioEngine(120)
    run(e, 0.1)
    e.launch(0, 0, loop())
    out = run(e, 0.1)
    assert e.slots[0].buf is not None
    assert e.origin == 4800  # Start genau beim nächsten Block
    assert np.abs(out).max() > 0.01


def test_second_loop_waits_for_next_bar():
    e = AudioEngine(120)
    e.launch(0, 0, loop())
    run(e, 0.5)
    e.launch(1, 2, loop())
    run(e, 0.01)
    assert e.snapshot.pending == {1: 2}
    run(e, 1.6)  # 0,5 + 1,6 > 2 s = 1 Takt
    assert e.snapshot.playing == {0: 0, 1: 2}
    assert e.slots[1].start == BAR


def test_stop_column_is_quantized():
    e = AudioEngine(120)
    e.launch(0, 0, loop())
    run(e, 0.3)
    e.stop_column(0)
    run(e, 0.01)
    assert 0 in e.snapshot.stopping
    run(e, 1.8)
    assert e.snapshot.playing == {}


def test_loops_are_phase_aligned_to_grid():
    e = AudioEngine(120)
    ramp = np.repeat(np.arange(BAR * 2, dtype=np.float32)[:, None], 2, axis=1)
    dst = np.zeros((256, 2), np.float32)
    e.origin = 1000
    e._mix_loop(dst, ramp, 1000 + BAR * 2 + 5, 0, 256)
    assert dst[0, 0] == 5  # nach genau einer Loop-Länge wieder am Anfang


def test_voice_at_frame_and_release():
    e = AudioEngine(120)
    buf = np.full((48000, 2), 0.2, np.float32)
    e.play(buf, TRACK_SHOTS, at=1000)
    out = run(e, 0.05)
    assert np.abs(out[:990]).max() < 1e-4
    assert np.abs(out[1100:1200]).max() > 0.01
    e.play(buf, 9, key="k")
    run(e, 0.02)
    e.release("k", 0.01)
    run(e, 0.05)
    assert all(v.key != "k" for v in e.voices)


def test_metronome_clicks_on_beats():
    e = AudioEngine(120)
    click = np.full((100, 2), 0.3, np.float32)
    e.clicks = (click, click)
    e.metronome = True
    out = run(e, 1.1)
    loud = np.where(np.abs(out[:, 0]) > 0.05)[0]
    starts = sorted({int(i) // 1000 * 1000 for i in loud})
    assert starts[0] == 0 and any(abs(s - 24000) <= 1000 for s in starts)


def test_output_never_clips(lib):
    e = AudioEngine(120)
    for col in range(7):
        e.launch(col, 0, lib.loops[(col, 0)].data)
    for s in lib.oneshots:
        e.play(s.data, TRACK_SHOTS)
    e.set_master(1.0)
    out = run(e, 1.0)
    assert np.abs(out).max() <= 1.0
    assert np.isfinite(out).all()
