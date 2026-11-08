# 🎧 DJ-Schule – AKAI APC mini mk2 mit Python

Ein interaktives Lernwerkzeug für Kinder, die DJ werden wollen. Der **AKAI APC mini mk2** wird direkt per
MIDI angesteuert, ganz ohne Ableton. Python erzeugt alle Klänge selbst. Eine bunte Browser-Oberfläche zeigt
live, welche Tasten gedrückt werden, und erklärt, was passiert.

* **Töne spielen:** Keyboard in a-Moll-Pentatonik (es klingt nie falsch), 4 Instrumente
* **Klangpassagen starten:** 28 Loops in 7 Instrumentenspalten, alle in derselben Tonart und im selben Tempo.
  Sie starten automatisch auf der nächsten Eins.
* **DJ-Effekte:** Airhorn, Scratch, Riser, Boom, Filter-Sweep …
* **Lernen:** 8 geführte Lektionen mit Sternen, ein Rhythmus-Spiel „Hör zu – spiel nach!“ und ein Metronom
* **Ohne Hardware:** Die Oberfläche lässt sich auch mit Maus oder Touch bedienen.

## Installation

Voraussetzung: macOS oder Linux mit [uv](https://docs.astral.sh/uv/) (installiert Python 3.12 automatisch).

```bash
uv sync
```

## Starten

1. **Ableton Live schließen.** Sonst kämpfen beide Programme um die LEDs des Controllers.
2. Controller per USB anschließen.
3. Starten:

```bash
uv run apc-dj
```

Der Browser öffnet sich auf <http://localhost:8000>. Beenden mit `Strg+C`; dabei gehen auch die LEDs aus.

| Option | Bedeutung |
|---|---|
| `--no-controller` | ohne Hardware starten (nur Browser) |
| `--bpm 110` | anderes Tempo (alle Loops werden neu erzeugt) |
| `--host 0.0.0.0` | Oberfläche im WLAN freigeben, z. B. für ein Tablet: `http://<IP-des-Macs>:8000` |
| `--no-browser` | Browser nicht automatisch öffnen |

Weitere Einstellungen stehen in [`config.toml`](config.toml).

## Belegung

```
            Spalte:  1 Drums  2 Perc  3 Bass  4 Akkorde  5 Arp  6 Melodie  7 FX  8 Eigene
 ┌─────────────────────────────────────────────────────────────┐
 │ Reihe 8  Loops, Variante 1                                  │ (Szene 1)  ganze Reihe starten
 │ Reihe 7  Loops, Variante 2                                  │ (Szene 2)
 │ Reihe 6  Loops, Variante 3                                  │ (Szene 3)
 │ Reihe 5  Loops, Variante 4                                  │ (Szene 4)
 │ Reihe 4  Kick Snare Clap HiHat HiHat-offen Tom Tom Kuhglocke │ (Szene 5)  Instrument wechseln
 │ Reihe 3  Becken Airhorn Scratch Laser Boom Riser Sirene Rim  │ (Szene 6)  Metronom an/aus
 │ Reihe 2  Keyboard (hohe Töne)                               │ (Szene 7)  Modus: Frei → Lektionen → Spiel
 │ Reihe 1  Keyboard (tiefe Töne), rosa = Grundton A           │ (Szene 8)  Alles stopp
 └─────────────────────────────────────────────────────────────┘
   Track-Knöpfe 1–8: Spalte stoppen                     SHIFT
   Fader 1–8: Lautstärke je Spalte · Fader 9: Gesamtlautstärke · SHIFT + Fader 9: Filter
```

**LED-Farben:** gedimmt = bereit · hell = läuft · blinkt = wartet auf die nächste Eins (oder: „drück mich!“ in
den Lektionen). Die Farben am Controller und am Bildschirm sind identisch.

## Lernmodi

* **Freies Spielen:** Drück eine Taste, und die Infokarte erklärt kindgerecht, was du hörst.
* **Lektionen:** 1 Hallo Controller · 2 Der Beat · 3 Der Bass kommt dazu · 4 Mischen mit Fadern ·
  5 Melodie spielen · 6 Der Filter-Trick · 7 Der Drop · 8 Szenen wechseln.
  Die Tasten für den nächsten Schritt blinken. Es gibt 1–3 Sterne; der Fortschritt steht in `data/progress.json`.
* **Rhythmus-Spiel:** Die App spielt ein Muster auf Kick, Snare, Clap und HiHat vor, das Kind spielt es nach.
  Bewertet wird bis ±70 ms als „Perfekt“ und bis ±140 ms als „Gut“. Nach 3 geschafften Runden steigt das Level.
  Wenn die Bewertung systematisch zu früh oder zu spät ist, lässt sie sich mit `timing_offset_ms` in
  `config.toml` justieren.

## Eigene Sounds

Lege WAV-Loops in [`sounds/eigene/`](sounds/eigene/README.md); sie erscheinen in Spalte 8.

## Wie funktioniert die Ansteuerung?

Der APC mini mk2 ist ein ganz normales USB-MIDI-Gerät mit den Ports „APC mini mk2 Control“ und „APC mini mk2 Notes“
(Protokoll: [Akai Communication Protocol v1.0](https://cdn.inmusicbrands.com/akai/attachments/APC%20mini%20mk2%20-%20Communication%20Protocol%20-%20v1.0.pdf)).

| Element | Eingang | LED |
|---|---|---|
| Pads 8×8 | Note 0–63 (unten links = 0) | Note On: Velocity = Farbe, Kanal = Helligkeit (0–6), Pulsieren (7–10), Blinken (11–15) |
| Track-Knöpfe | Note 100–107 | Note On Kanal 1: 0 aus, 1 an, 2 blinken |
| Szene-Knöpfe | Note 112–119 | wie Track-Knöpfe |
| Shift | Note 122 | – |
| Fader 1–9 | CC 48–56 | – |

Zum Ausprobieren und Prüfen:

```bash
uv run python tools/midi_monitor.py            # zeigt jede Taste/jeden Fader als MIDI-Nachricht
uv run python tools/midi_monitor.py --led-test # zeigt die Farbpalette auf dem Raster
```

## Aufbau

```
src/apc_dj/
  controller.py       MIDI-Protokoll, Port-Suche, LED-Ausgabe
  audio/synth.py      Oszillatoren, Hüllkurven, Instrumente
  audio/library.py    erzeugt Drums, Effekte, Loops (Am–F–C–G) + lädt eigene WAVs
  audio/engine.py     Echtzeit-Mixer: Taktraster, quantisierte Loops, Fader, Filter, Metronom
  layout.py           welche Taste macht was
  app.py              zentrale Logik: Eingaben → Klang, LEDs, Browser
  lessons.py          geführte Lektionen
  rhythm_game.py      Rhythmus-Spiel
  web/                FastAPI-Server + Oberfläche (HTML/CSS/JS ohne Build-Schritt)
tools/midi_monitor.py
tests/                uv run pytest
```
