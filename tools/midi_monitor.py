"""MIDI-Monitor für den APC mini mk2.

  uv run python tools/midi_monitor.py            # Ports zeigen + Eingaben mitschreiben
  uv run python tools/midi_monitor.py --led-test # Farbpalette auf dem Raster anzeigen
"""
import argparse
import sys
import time

import mido

sys.path.insert(0, "src")
from apc_dj.controller import (  # noqa: E402
    PadLed, button_message, decode, find_port, pad_message,
)


def led_test(out: mido.ports.BaseOutput) -> None:
    for page in (0, 64):
        print(f"Palette {page}..{page + 63} (Pad unten links = {page})")
        for pad in range(64):
            out.send(pad_message(pad, PadLed(page + pad)))
        for n in list(range(100, 108)) + list(range(112, 120)):
            out.send(button_message(n, 1))
        time.sleep(4)
    print("Helligkeit 10..100 % in Rot, dann Pulsieren und Blinken")
    for i, b in enumerate((10, 25, 50, 65, 75, 90, 100)):
        for col in range(8):
            out.send(pad_message(i * 8 + col, PadLed(5, brightness=b)))
    for col in range(8):
        out.send(pad_message(56 + col, PadLed(21, "pulse" if col < 4 else "blink")))
    time.sleep(5)
    for pad in range(64):
        out.send(pad_message(pad, PadLed(0)))
    for n in list(range(100, 108)) + list(range(112, 120)):
        out.send(button_message(n, 0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--led-test", action="store_true")
    args = ap.parse_args()
    print("Eingänge:", mido.get_input_names())
    print("Ausgänge:", mido.get_output_names())
    if args.led_test:
        name = find_port(mido.get_output_names(), "Control")
        if not name:
            sys.exit("APC mini mk2 nicht gefunden")
        with mido.open_output(name) as out:
            led_test(out)
        return

    ports = [n for n in mido.get_input_names() if "apc" in n.lower()]
    opened = []
    for n in ports:
        notes = "notes" in n.lower()
        opened.append(mido.open_input(
            n, callback=lambda m, n=n, notes=notes: print(f"[{n}] {m}  ->  {decode(m, notes)}")))
    print("Drücke Tasten/bewege Fader (Strg+C beendet) …")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in opened:
            p.close()


if __name__ == "__main__":
    main()
