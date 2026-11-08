from apc_dj.controller import ControlEvent, SCENE_BASE, TRACK_BASE
from apc_dj.layout import loop_pad, shot_pad
from conftest import run


def press(app, kind, index, source="hardware"):
    app.handle(ControlEvent(kind, index, True, source=source))
    app.handle(ControlEvent(kind, index, False, source=source))


def test_layout_covers_all_pads(app):
    roles = [app.layout[p].role for p in range(64)]
    assert roles.count("loop") == 32 and roles.count("shot") == 16 and roles.count("key") == 16


def test_loop_pad_starts_and_stops_with_leds(app):
    press(app, "pad", loop_pad(0, 0))
    run(app.engine, 0.05)
    app.refresh_leds()
    assert app.engine.snapshot.playing == {0: 0}
    led = app.controller.pads[loop_pad(0, 0)]
    assert led.brightness == 100 and led.mode == "solid"
    assert app.controller.buttons[TRACK_BASE] == 1
    press(app, "pad", loop_pad(0, 0))
    run(app.engine, 0.05)
    app.refresh_leds()
    assert app.controller.pads[loop_pad(0, 0)].mode == "blink"  # stoppt am Taktende
    assert app.bus.of("info")[-1]["title"].endswith("stoppt")


def test_press_events_reach_browser(app):
    press(app, "pad", shot_pad(0), source="web")
    presses = app.bus.of("press")
    assert presses[0] == {"t": "press", "kind": "pad", "index": shot_pad(0), "pressed": True}
    assert any(v.track == 8 for v in app.engine.voices) or app.engine._cmds


def test_scene_launches_row(app):
    press(app, "scene", 0)
    run(app.engine, 0.05)
    assert set(app.engine.snapshot.playing) == {0, 1, 2, 3, 4, 5, 6}


def test_fader_and_shift_filter(app):
    app.handle(ControlEvent("fader", 2, value=0.0))
    assert app.engine.gains[2] == 0.0
    app.handle(ControlEvent("shift", 0, True))
    app.handle(ControlEvent("fader", 8, value=0.1))
    assert app.engine.cutoff == 0.1 and app.faders[8] == 0.8


def test_instrument_and_mode_buttons(app):
    press(app, "scene", 4)
    assert app.instrument == 1
    press(app, "scene", 5)
    assert app.engine.metronome
    press(app, "scene", 6)
    assert app.mode == "lektion"
    app.refresh_leds()
    assert app.controller.buttons[SCENE_BASE + 6] == 1


def test_state_is_json_serializable(app):
    import json
    json.dumps(app.state())
