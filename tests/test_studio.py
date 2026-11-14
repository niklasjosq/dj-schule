"""Studio-Modus: Musikstile mit eigenem Tempo und Live-Effekte – und ohne Studio-Modus bleibt alles wie bisher."""
from concurrent.futures import Future

import numpy as np

import pytest

from apc_dj.app import App
from apc_dj.audio.engine import AudioEngine
from apc_dj.audio.library import build_library
from apc_dj.audio.seq import bar_frames
from apc_dj.controller import ControlEvent
from apc_dj.layout import shot_pad
from conftest import FakeController, RecordingBus, run

_BUILT = {}


class MemoBuilder:
    """Wie SyncBuilder, merkt sich aber fertige Stile über alle Tests hinweg (schneller)."""

    def __init__(self):
        self.calls = []

    def submit(self, style, bpm, user_dir):
        self.calls.append((style, bpm))
        if (style, bpm) not in _BUILT:
            _BUILT[(style, bpm)] = build_library(style, bpm, user_dir)
        f = Future()
        f.set_result(_BUILT[(style, bpm)])
        return f

    def shutdown(self):
        pass


class ManualBuilder:
    """Ergebnisse kommen erst, wenn der Test es sagt (für "veraltete" Ergebnisse)."""

    def __init__(self):
        self.pending = []

    def submit(self, style, bpm, user_dir):
        f = Future()
        self.pending.append(((style, bpm), f))
        return f

    def finish(self, key):
        for k, f in self.pending:
            if k == key:
                if key not in _BUILT:
                    _BUILT[key] = build_library(*key)
                f.set_result(_BUILT[key])

    def shutdown(self):
        pass


def make_app(lib, tmp_path, studio=True, builder=None):
    engine = AudioEngine(120, fx=studio)
    engine.clock = lambda: engine.frame / 48000
    a = App(engine, lib, RecordingBus(), progress_file=tmp_path / "p.json", recordings_dir=tmp_path / "rec",
            studio=studio, builder=builder or MemoBuilder())
    a.controller = FakeController()
    return a


@pytest.fixture
def studio(lib, tmp_path):
    return make_app(lib, tmp_path)


def press(app, kind, index, pressed=True):
    app.handle(ControlEvent(kind, index, pressed))


def test_default_mode_is_unchanged(app):
    assert app.studio is False and app.engine.fx is None
    st = app.state()
    assert st["features"] == {"studio": False} and "styles" not in st and "style" not in st
    app.handle_web({"t": "style", "id": "chip"})
    app.handle_web({"t": "press", "kind": "fx", "index": 0})
    assert app.lib.style == "schule"
    # SHIFT + Track stoppt wie bisher die Spalte
    app.handle(ControlEvent("pad", 56))  # Drums starten
    run(app.engine, 0.05)
    press(app, "shift", 0)
    press(app, "track", 0)
    run(app.engine, 0.01)
    assert 0 in app.engine.snapshot.stopping


def test_style_switch_swaps_sounds_and_tempo(studio):
    studio.handle(ControlEvent("pad", 56))
    run(studio.engine, 0.1)
    studio.select_style("chip", 140)
    run(studio.engine, 0.01)
    assert studio.lib.style == "chip" and studio.lib.bpm == 140
    assert studio.engine.bar == bar_frames(140) and studio.engine.snapshot.playing == {}
    assert studio.layout[shot_pad(9)].label == "Münze"
    assert studio.state()["style"] == "chip" and studio.status()["bpm"] == 140
    assert any(m["t"] == "state" and m["style"] == "chip" for m in studio.bus.messages)


def test_invalid_choices_are_ignored(studio):
    for args in (("nope", None), ("chip", 131), ("chip", "130"), (None, None), ("schule", 140)):
        studio.select_style(*args)
    assert studio.lib.style == "schule" and studio.lib.bpm == 120
    studio.handle_web({"t": "style", "id": "chip", "bpm": float("nan")})
    studio.handle_web({"t": "style", "id": "chip", "bpm": True})
    assert studio.lib.style == "schule"


def test_web_style_message_uses_default_bpm(studio):
    studio.handle_web({"t": "style", "id": "chip"})
    assert (studio.lib.style, studio.lib.bpm) == ("chip", 120)
    studio.handle_web({"t": "style", "id": "chip", "bpm": 125})
    assert studio.lib.bpm == 125


def test_stale_build_result_is_ignored(lib, tmp_path):
    b = ManualBuilder()
    a = make_app(lib, tmp_path, builder=b)
    a.select_style("chip", 125)
    assert a.loading == ("chip", 125.0) and a.status()["loading"] == {"id": "chip", "bpm": 125.0}
    a.select_style("chip", 130)
    b.finish(("chip", 125.0))
    assert a.lib.style == "schule" and a.loading == ("chip", 130.0)
    b.finish(("chip", 130.0))
    assert (a.lib.style, a.lib.bpm, a.loading) == ("chip", 130.0, None)


def test_cache_keeps_dj_schule_and_one_style(studio):
    b = studio.builder
    studio.select_style("chip", 120)
    studio.select_style("schule")
    studio.select_style("chip", 120)
    assert b.calls == [("chip", 120.0)]  # zurück zur DJ-Schule und wieder hin: nichts neu erzeugt
    studio.select_style("chip", 125)
    assert set(studio._libs) == {("schule", 120.0), ("chip", 125.0)}


def test_lessons_use_dj_schule_and_refuse_other_styles(studio):
    studio.select_style("chip", 120)
    studio.set_mode("lektion")
    assert studio.lib.style == "schule"
    studio.select_style("chip", 120)
    assert studio.lib.style == "schule"
    studio.set_mode("frei")
    studio.select_style("chip", 120)
    assert studio.lib.style == "chip"


def test_shift_track_holds_effect_until_track_released(studio):
    press(studio, "shift", 0)
    press(studio, "track", 2)
    run(studio.engine, 0.01)
    assert studio.fx_held == {2: "hardware"} and studio.engine.fx.target[2] == 1
    assert studio._buttons["track"][2] == 1  # LED zeigt den Effekt, solange SHIFT gehalten wird
    press(studio, "shift", 0, False)  # SHIFT zuerst loslassen
    press(studio, "track", 2, False)
    run(studio.engine, 0.01)
    assert studio.fx_held == {} and studio.engine.fx.target[2] == 0
    # ohne SHIFT stoppt der Track-Knopf weiter die Spalte
    studio.handle(ControlEvent("pad", 56))
    run(studio.engine, 0.05)
    press(studio, "track", 0)
    run(studio.engine, 0.01)
    assert 0 in studio.engine.snapshot.stopping and studio.fx_held == {}


def test_effects_from_the_browser_and_disconnect(studio):
    studio.handle_web({"t": "press", "kind": "fx", "index": 4})
    assert studio.fx_held == {4: "web"}
    studio.handle_web({"t": "press", "kind": "fx", "index": 99})
    assert studio.fx_held == {4: "web"}
    studio.web_disconnected()
    run(studio.engine, 0.01)
    assert studio.fx_held == {} and studio.engine.fx.target[4] == 0


def test_no_effects_in_game_and_stop_all_clears_them(studio):
    studio.handle_web({"t": "press", "kind": "fx", "index": 5})
    press(studio, "scene", 7)  # Alles stopp
    run(studio.engine, 0.01)
    assert studio.fx_held == {} and studio.engine.fx.target[5] == 0
    studio.set_mode("spiel")
    studio.handle_web({"t": "press", "kind": "fx", "index": 5})
    assert studio.fx_held == {}


def test_instrument_picker(studio):
    studio.handle_web({"t": "instrument", "index": 2})
    assert studio.instrument == 2 and studio.status()["instrument_index"] == 2
    studio.handle_web({"t": "instrument", "index": 9})
    assert studio.instrument == 2
    studio.handle_web({"t": "instrument"})
    assert studio.instrument == 3


def test_game_plays_the_current_style(studio):
    studio.select_style("chip", 120)
    studio.set_mode("spiel")
    assert studio.lib.oneshots[0].label == "808-Kick"


def test_real_builder_renders_in_a_separate_process():
    from apc_dj.audio.styles.builder import StyleBuilder

    b = StyleBuilder()
    try:
        lib = b.submit("chip", 125.0, None).result(timeout=120)
    finally:
        b.shutdown()
    assert lib.style == "chip" and lib.bpm == 125 and len(lib.loops) == 28


def test_file_handover_keeps_every_sound(tmp_path):
    from apc_dj.audio.library import attach_library_file, build_library, build_library_file

    path = str(tmp_path / "x.f32")
    lib, shapes = build_library_file("chip", 130.0, None, path)
    assert lib.oneshots[0].data is None  # die Klänge stecken nur in der Datei
    lib = attach_library_file(lib, shapes, path)
    ref = build_library("chip", 130.0)
    assert not (tmp_path / "x.f32").exists()
    for k in ref.loops:
        assert np.array_equal(lib.loops[k].data, ref.loops[k].data)
    for a, b in zip(lib.oneshots, ref.oneshots):
        assert np.array_equal(a.data, b.data)
    for name in ref.keys:
        assert all(np.array_equal(x, y) for x, y in zip(lib.keys[name], ref.keys[name]))
    assert all(np.array_equal(x, y) for x, y in zip(lib.clicks, ref.clicks))
