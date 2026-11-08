import mido

from apc_dj.controller import PadLed, button_message, decode, find_port, pad_message


def test_decode_pad_track_scene_shift_fader():
    assert decode(mido.Message("note_on", note=0, velocity=127)).kind == "pad"
    ev = decode(mido.Message("note_off", note=63))
    assert (ev.kind, ev.index, ev.pressed) == ("pad", 63, False)
    assert decode(mido.Message("note_on", note=0, velocity=0)).pressed is False
    assert (decode(mido.Message("note_on", note=103, velocity=127)).kind,) == ("track",)
    assert decode(mido.Message("note_on", note=103, velocity=127)).index == 3
    assert decode(mido.Message("note_on", note=119, velocity=127)).index == 7
    assert decode(mido.Message("note_on", note=122, velocity=127)).kind == "shift"
    ev = decode(mido.Message("control_change", control=56, value=127))
    assert (ev.kind, ev.index, ev.value) == ("fader", 8, 1.0)
    assert decode(mido.Message("note_on", note=60, velocity=100), notes_port=True).kind == "note"
    assert decode(mido.Message("control_change", control=7, value=1)) is None


def test_led_encoding():
    m = pad_message(5, PadLed(21, brightness=100))
    assert (m.channel, m.note, m.velocity) == (6, 5, 21)
    assert pad_message(5, PadLed(21, "blink")).channel in range(11, 16)
    assert pad_message(5, PadLed(21, "pulse")).channel in range(7, 11)
    assert button_message(112, 2).bytes() == [0x90, 112, 2]


def test_find_port():
    names = ["IAC Bus", "APC mini mk2 Notes", "APC mini mk2 Control"]
    assert find_port(names, "Control") == "APC mini mk2 Control"
    assert find_port(names, "Notes") == "APC mini mk2 Notes"
    assert find_port(["IAC"], "Control") is None


def test_find_port_linux_alsa_names():
    names = ["Midi Through:Midi Through Port-0 14:0",
             "APC mini mk2:APC mini mk2 APC mini mk2 Notes 20:1",
             "APC mini mk2:APC mini mk2 APC mini mk2 Contr 20:0"]
    assert find_port(names, "Control") == names[2]
    assert find_port(names, "Notes") == names[1]
