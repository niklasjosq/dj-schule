"""Die neuen Musikstile: vollständig, im Takt, gleich laut wie die DJ-Schule und immer in a-Moll."""
import hashlib

import numpy as np
import pytest

from apc_dj.audio import synth
from apc_dj.audio.library import Library
from apc_dj.audio.seq import A_MINOR, COLUMN_RMS, KEY_NOTES, bar_frames
from apc_dj.audio.styles import STYLE_BY_ID, STYLES
from apc_dj.controller import PALETTE

NEW_STYLES = [s.id for s in STYLES if s.id != "schule"]


def build_recording_notes(style, bpm, monkeypatch):
    """Stil bauen und dabei jeden erzeugten Ton (MIDI-Nummer) mitschreiben."""
    notes = []
    real = synth.midi_to_freq

    def spy(m):
        notes.append(m)
        return real(m)

    synth.render_note.cache_clear()
    monkeypatch.setattr(synth, "midi_to_freq", spy)
    lib = Library.build(bpm, None, style)
    monkeypatch.setattr(synth, "midi_to_freq", real)
    return lib, notes


@pytest.fixture(scope="module")
def built():
    mp = pytest.MonkeyPatch()
    out = {sid: build_recording_notes(sid, STYLE_BY_ID[sid].default_bpm, mp) for sid in NEW_STYLES}
    mp.undo()
    return out


@pytest.mark.parametrize("sid", NEW_STYLES)
def test_style_has_full_grid_of_loops_in_time(built, sid):
    lib, _ = built[sid]
    bpm = STYLE_BY_ID[sid].default_bpm
    assert lib.bpm == bpm and lib.style == sid
    for col in range(7):
        for var in range(4):
            snd = lib.loops[(col, var)]
            assert snd.data.shape == (4 * bar_frames(bpm), 2), snd.id
            assert snd.data.dtype == np.float32
            assert np.isfinite(snd.data).all(), snd.id
            assert np.abs(snd.data).max() <= 0.951, snd.id
            assert snd.info and 0 < len(snd.label) <= 16, snd.id
    assert (7, 0) not in lib.loops  # Spalte 8 = eigene Sounds


@pytest.mark.parametrize("sid", NEW_STYLES)
def test_columns_are_as_loud_as_in_dj_schule(built, sid):
    lib, _ = built[sid]
    for (col, var), snd in lib.loops.items():
        rms = float(np.sqrt(np.mean(snd.data.astype(float) ** 2)))
        assert abs(20 * np.log10(rms / COLUMN_RMS[col])) <= 3, (snd.id, rms)


@pytest.mark.parametrize("sid", NEW_STYLES)
def test_one_shot_slots_keep_their_roles(built, sid):
    lib, _ = built[sid]
    ids = [s.id for s in lib.oneshots]
    assert len(ids) == 16 and len(set(ids)) == 16
    assert ids[:4] == ["kick", "snare", "clap", "hat"]  # Rhythmus-Spiel
    assert ids[12] == "boom" and ids[13] == "riser"  # Lektion "Der Drop"
    for s in lib.oneshots:
        assert s.data.ndim == 2 and s.data.shape[1] == 2 and np.isfinite(s.data).all() and s.info


@pytest.mark.parametrize("sid", NEW_STYLES)
def test_keyboard_has_four_instruments(built, sid):
    lib, _ = built[sid]
    assert len(lib.instruments) == 4
    for inst in lib.instruments:
        assert inst.id in synth.INSTRUMENTS and inst.color in PALETTE
        assert len(lib.keys[inst.id]) == len(KEY_NOTES)
        assert all(np.isfinite(b).all() and np.abs(b).max() < 1.2 for b in lib.keys[inst.id])


@pytest.mark.parametrize("sid", NEW_STYLES)
def test_every_note_is_in_a_minor(built, sid):
    """Alles passt zusammen: kein Ton außerhalb der a-Moll-Tonleiter."""
    _, notes = built[sid]
    assert notes
    wrong = sorted({int(m) for m in notes if int(m) % 12 not in A_MINOR})
    assert not wrong, wrong


def test_other_bpm_changes_loop_length():
    lib = Library.build(140, None, "chip")
    assert lib.bpm == 140
    assert lib.loops[(0, 0)].data.shape[0] == 4 * bar_frames(140)


def test_styles_render_deterministically():
    def digest():
        lib = Library.build(120, None, "chip")
        h = hashlib.sha256()
        for k in sorted(lib.loops):
            h.update(lib.loops[k].data.tobytes())
        return h.hexdigest()

    assert digest() == digest()


def test_style_registry_is_consistent():
    assert STYLES[0].id == "schule" and STYLES[0].bpm_choices == ()
    for s in STYLES[1:]:
        assert s.default_bpm in s.bpm_choices
        assert s.color.startswith("#") and s.intro
