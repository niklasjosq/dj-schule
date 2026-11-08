from apc_dj.controller import ControlEvent
from apc_dj.lessons import LESSONS
from apc_dj.layout import loop_pad
from conftest import run


def test_lesson_beat_flow(app):
    app.set_mode("lektion")
    app.handle_web({"t": "lesson", "index": 1})
    assert app.lessons.current == 1
    assert ("pad", loop_pad(0, 0)) in app.lessons.highlights(app)
    app.handle(ControlEvent("pad", loop_pad(0, 0), True))
    run(app.engine, 0.05)
    app.tick()
    assert app.lessons.step == 1
    run(app.engine, 4.2)  # 2 Takte
    app.tick()
    app.tick()
    assert app.lessons.step == 2
    app.handle(ControlEvent("pad", loop_pad(0, 2), True))
    run(app.engine, 2.1)
    app.tick()
    assert app.lessons.finished_at is not None
    assert app.lessons.stars["Der Beat"] == 3
    assert app.lessons.progress_file.exists()


def test_all_lessons_have_valid_targets():
    for les in LESSONS:
        assert les.steps
        for st in les.steps:
            for kind, idx in st.targets:
                assert kind in ("pad", "track", "scene", "fader", "shift")
