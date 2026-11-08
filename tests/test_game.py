import random

from apc_dj.controller import ControlEvent
from apc_dj.rhythm_game import GAME_PADS, RhythmGame, make_pattern, rate
from conftest import run


def test_patterns_per_level():
    rng = random.Random(1)
    for level in range(1, 7):
        p = make_pattern(level, rng)
        assert p[0][0] == 0
        assert all(0 <= s < 8 and 0 <= pad < 4 for s, pad in p)


def test_rating():
    assert rate(0.01) == "perfekt" and rate(-0.1) == "gut" and rate(0.2) == "daneben"


def test_full_round_with_perfect_hits(app, monkeypatch):
    app.game = RhythmGame(seed=3)
    app.set_mode("spiel")
    run(app.engine, 0.2)
    app.tick()
    g = app.game
    assert g.round_bar is not None and g.phase == "countin"
    play_start = g.bar_frame(app, g.round_bar + 1)
    # perfekte Schläge simulieren: heard_now() liefert exakt den erwarteten Frame
    for ef, pad in g.expected:
        monkeypatch.setattr(app, "heard_now", lambda ef=ef: ef + 100)
        g.phase = "play"
        app.handle(ControlEvent("pad", GAME_PADS[pad], True))
    while app.engine.frame < play_start + app.engine.bar + 48000 * 0.5:
        run(app.engine, 0.1)
        app.tick()
    assert g.results and all(r["rating"] == "perfekt" for r in g.results)
    assert g.score == 100 * len(g.results) and g.streak == 1
