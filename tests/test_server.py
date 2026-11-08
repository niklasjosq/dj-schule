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
