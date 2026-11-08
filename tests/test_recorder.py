import numpy as np
import soundfile as sf

from apc_dj.audio.engine import AudioEngine
from apc_dj.audio.recorder import Recorder
from conftest import run

BAR = 96000


def test_records_master_output_to_wav(tmp_path):
    e = AudioEngine(120)
    e.recorder = Recorder()
    run(e, 0.1)  # vor der Aufnahme – kommt nicht in die Datei
    path = tmp_path / "set.wav"
    e.recorder.start(path)
    e.launch(0, 0, np.full((BAR, 2), 0.3, np.float32))
    out = run(e, 0.5)
    assert e.recorder.stop() == path
    data, sr = sf.read(path, dtype="float32")
    assert sr == 48000 and data.shape == (len(out), 2)
    assert np.allclose(data, out, atol=1 / 16000)  # 16 Bit
    assert np.abs(data).max() > 0.1


def test_nothing_written_without_recording(tmp_path):
    e = AudioEngine(120)
    rec = Recorder()
    e.recorder = rec
    run(e, 0.1)
    assert rec.frames == 0 and not list(tmp_path.iterdir())


def test_hard_limit_caps_file_length(tmp_path):
    e = AudioEngine(120)
    e.recorder = Recorder(max_seconds=0.2)
    path = tmp_path / "set.wav"
    e.recorder.start(path)
    run(e, 0.5)
    assert e.recorder.full
    e.recorder.stop()
    assert sf.info(str(path)).frames == int(0.2 * 48000)
