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


# ------------------------------------------------------------ Aufnahme

def test_record_via_browser_creates_wav(app, tmp_path):
    from conftest import run
    import soundfile as sf

    app.handle_web({"t": "record", "on": True})
    assert app.recorder.active
    assert app.bus.of("status")[-1]["recording"] is True
    run(app.engine, 1.2)
    app.tick()
    assert app.bus.of("rec")[-1]["seconds"] == 1
    app.handle_web({"t": "record", "on": False})
    assert not app.recorder.active
    files = list((tmp_path / "aufnahmen").glob("DJ-Set_*.wav"))
    assert len(files) == 1 and abs(sf.info(str(files[0])).duration - 1.2) < 0.01
    items = app.bus.of("recordings")[-1]["items"]
    assert items[0]["name"] == files[0].name and items[0]["seconds"] == 1.2
    assert app.state()["recordings"] == items
    assert app.recording_path(files[0].name) == files[0].resolve()


def test_recording_stops_automatically_at_limit(lib, tmp_path):
    from conftest import RecordingBus, run
    import soundfile as sf
    from apc_dj.app import App
    from apc_dj.audio.engine import AudioEngine

    engine = AudioEngine(120)
    a = App(engine, lib, RecordingBus(), progress_file=tmp_path / "p.json",
            recordings_dir=tmp_path / "rec", max_rec_minutes=0.005)  # 0,3 s
    a.set_recording(True)
    run(engine, 0.5)
    a.tick()
    assert not a.recorder.active
    assert any("voll" in m["title"] for m in a.bus.of("info"))
    (f,) = (tmp_path / "rec").glob("*.wav")
    assert sf.info(str(f)).frames == int(0.3 * 48000)


def test_no_recording_when_storage_full(lib, tmp_path):
    from conftest import RecordingBus
    from apc_dj.app import App
    from apc_dj.audio.engine import AudioEngine

    rec = tmp_path / "rec"
    rec.mkdir()
    (rec / "DJ-Set_2026-01-01_10-00-00.wav").write_bytes(b"\0" * 600_000)
    a = App(AudioEngine(120), lib, RecordingBus(), progress_file=tmp_path / "p.json",
            recordings_dir=rec, max_rec_minutes=0.05, max_rec_total_mb=1)  # 3 s ≈ 0,58 MB
    a.set_recording(True)
    assert not a.recorder.active
    assert a.bus.of("info")[-1]["title"] == "Speicher voll"


def test_record_ignores_non_bool(app):
    app.handle_web({"t": "record", "on": "ja"})
    assert not app.recorder.active


def test_delete_recording(app, tmp_path):
    rec = tmp_path / "aufnahmen"
    rec.mkdir()
    keep = tmp_path / "wichtig.wav"
    keep.write_bytes(b"x")
    f = rec / "DJ-Set_2026-01-01_10-00-00.wav"
    f.write_bytes(b"x")
    for bad in ["../wichtig.wav", "DJ-Set_..%2F..%2Fwichtig.wav", None, 42, ["x"]]:
        app.handle_web({"t": "delete_recording", "name": bad})
    assert keep.exists() and f.exists()
    app.handle_web({"t": "delete_recording", "name": f.name})
    assert not f.exists() and keep.exists()
    assert app.bus.of("recordings")[-1]["items"] == []


def test_running_recording_cannot_be_deleted(app):
    app.set_recording(True)
    path = app.recorder.path
    app.handle_web({"t": "delete_recording", "name": path.name})
    app.set_recording(False)
    assert path.exists()
