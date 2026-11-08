import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from apc_dj.app import App, EventBus  # noqa: E402
from apc_dj.audio.engine import AudioEngine  # noqa: E402
from apc_dj.audio.library import Library  # noqa: E402


class RecordingBus(EventBus):
    def __init__(self):
        super().__init__()
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)

    def of(self, t):
        return [m for m in self.messages if m.get("t") == t]


class FakeController:
    name = "Fake APC"

    def __init__(self):
        self.pads, self.buttons = {}, {}

    def set_pad(self, pad, led):
        self.pads[pad] = led

    def set_button(self, note, state):
        self.buttons[note] = state


@pytest.fixture(scope="session")
def lib():
    return Library.build(120)


def run(engine, seconds):
    """Engine offline rendern (ohne Audiogerät)."""
    n = int(seconds * 48000)
    out = []
    while n > 0:
        out.append(engine._block(min(256, n)))
        n -= 256
    return np.concatenate(out)


@pytest.fixture
def app(lib, tmp_path):
    engine = AudioEngine(120)
    engine.clock = lambda: engine.frame / 48000
    a = App(engine, lib, RecordingBus(), progress_file=tmp_path / "p.json")
    a.controller = FakeController()
    return a
