from fastapi.testclient import TestClient

from apc_dj.app import App, EventBus
from apc_dj.audio.engine import AudioEngine
from apc_dj.web.server import create_server


def test_websocket_roundtrip(lib, tmp_path):
    core = App(AudioEngine(120), lib, EventBus(), progress_file=tmp_path / "p.json")
    client = TestClient(create_server(core))
    assert "DJ-Schule" in client.get("/").text
    assert client.get("/app.js").status_code == 200
    with client.websocket_connect("/ws") as ws:
        state = ws.receive_json()
        assert state["t"] == "state" and len(state["layout"]) == 64
        ws.send_json({"t": "press", "kind": "pad", "index": 24})
        msg = ws.receive_json()
        assert msg == {"t": "press", "kind": "pad", "index": 24, "pressed": True}
        ws.send_json({"t": "mode", "mode": "spiel"})
        seen = {ws.receive_json()["t"] for _ in range(6)}
        assert "status" in seen or "game" in seen
    assert core.mode == "spiel"


def test_foreign_origin_is_rejected(lib, tmp_path):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    core = App(AudioEngine(120), lib, EventBus(), progress_file=tmp_path / "p.json")
    client = TestClient(create_server(core))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={"origin": "https://boese-seite.example"}) as ws:
            ws.receive_json()
    with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as ws:
        assert ws.receive_json()["t"] == "state"


def test_invalid_browser_messages_are_ignored(lib, tmp_path):
    core = App(AudioEngine(120), lib, EventBus(), progress_file=tmp_path / "p.json")
    for bad in [
        {"t": "press", "kind": "track", "index": 100},
        {"t": "press", "kind": "pad", "index": -1},
        {"t": "press", "kind": "note", "index": 60},
        {"t": "press", "kind": "__class__", "index": 0},
        {"t": "press", "kind": "pad", "index": "5"},
        {"t": "fader", "index": 0, "value": float("nan")},
        {"t": "fader", "index": 42, "value": 0.5},
        {"t": "mode", "mode": "hacker"},
        {"t": "lesson", "index": "x"},
        ["keine", "dict"],
    ]:
        core.handle_web(bad)
    assert core.mode == "frei" and core.engine._cmds == type(core.engine._cmds)()
    core.handle_web({"t": "fader", "index": 0, "value": 7})
    assert core.engine.gains[0] == 1.0


def test_broken_audio_command_does_not_kill_audio():
    import numpy as np

    e = AudioEngine(120)
    e.stop_column(100)  # ungültige Spalte
    out = e.render(256)
    assert out.shape == (256, 2) and np.isfinite(out).all()


def test_recording_download_and_path_traversal(lib, tmp_path):
    rec = tmp_path / "aufnahmen"
    rec.mkdir()
    (rec / "DJ-Set_2026-01-01_10-00-00.wav").write_bytes(b"RIFF....WAVE")
    (tmp_path / "geheim.wav").write_bytes(b"geheim")
    (rec / "notizen.txt").write_text("x")
    core = App(AudioEngine(120), lib, EventBus(), progress_file=tmp_path / "p.json", recordings_dir=rec)
    client = TestClient(create_server(core))
    r = client.get("/aufnahmen/DJ-Set_2026-01-01_10-00-00.wav")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert "attachment" not in r.headers.get("content-disposition", "")
    r = client.get("/aufnahmen/DJ-Set_2026-01-01_10-00-00.wav?download=1")
    assert "attachment" in r.headers["content-disposition"]
    for bad in ["../geheim.wav", "%2e%2e%2fgeheim.wav", "..%2Fgeheim.wav", "notizen.txt",
                "DJ-Set_2026-01-01_10-00-01.wav", "DJ-Set_..%2F..%2Fgeheim.wav"]:
        assert client.get(f"/aufnahmen/{bad}").status_code == 404, bad
