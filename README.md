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
Unter Linux zuerst die [Systempakete](#linux-ubuntu-und-lubuntu) installieren.

```bash
uv sync
```

### Linux (Ubuntu und Lubuntu)

Die Anleitung gilt für **Ubuntu und Lubuntu 22.04 LTS und 24.04 LTS** (auch Zwischenversionen ab 20.04).
Lubuntu ist dasselbe System mit schlankerer Oberfläche (LXQt); alle Schritte sind identisch. Andere Distributionen
siehe [unten](#andere-distributionen).

Voraussetzung ist ein **64-Bit-Rechner** (x86_64, oder ARM64 wie ein Raspberry Pi 4/5 mit Ubuntu). Das ist bei
Lubuntu ab Version 19.04 ohnehin der Fall. Ubuntu 18.04 und älter ist zu alt (zu altes glibc für die fertigen
Python-Pakete).

**1. Systempakete installieren**

Terminal öffnen (Ubuntu: `Strg+Alt+T`; Lubuntu: Menü → Systemwerkzeuge → QTerminal) und eingeben:

```bash
sudo apt update
sudo apt install libportaudio2 alsa-utils curl
```

* `libportaudio2` ist für die Tonausgabe nötig. Fehlt das Paket, startet die App trotzdem, bleibt aber **stumm**
  (im Terminal steht dann „Keine Audioausgabe … laufe stumm weiter“).
* `alsa-utils` bringt `amidi` und `aconnect` zum Prüfen der MIDI-Verbindung mit.
* `curl` fehlt bei einer frischen Ubuntu-Installation und wird für den uv-Installer gebraucht.
* libsndfile und die MIDI-Bibliothek stecken schon in den Python-Paketen; Python selbst holt uv.

Danach uv installieren und die App im Projektordner einrichten:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # danach Terminal schließen und neu öffnen
cd ~/midi-controller                               # bzw. dort, wo der Projektordner liegt
uv sync
```

**2. Treiber prüfen**

Der APC mini mk2 ist ein standardkonformes USB-MIDI-Gerät. Es braucht **keinen Herstellertreiber**. Der Ubuntu-Kernel
bringt alles mit:

| Kernelmodul | Aufgabe |
|---|---|
| `snd_usb_audio` | USB-Audio- und USB-MIDI-Treiber, erkennt den Controller |
| `snd_rawmidi` | MIDI-Grundlage, wird von `snd_usb_audio` mitgeladen |
| `snd_seq` | ALSA-Sequencer; darüber findet und öffnet die App die MIDI-Ports |

Ubuntu lädt diese Module automatisch, sobald der Controller angesteckt wird. Prüfen (Controller eingesteckt):

```bash
lsusb | grep -i akai                      # Controller vom System erkannt?
lsmod | grep -E 'snd_usb_audio|snd_seq'   # Module geladen?
amidi -l                                  # MIDI-Ports, z. B. „APC mini mk2 … Contr“ und „… Notes“
aconnect -l                               # dasselbe aus Sicht des ALSA-Sequencers
```

Fehlt ein Modul, von Hand laden und dauerhaft eintragen:

```bash
sudo modprobe snd-usb-audio
sudo modprobe snd-seq
printf 'snd-usb-audio\nsnd-seq\n' | sudo tee /etc/modules-load.d/apc-dj.conf
```

Meldet `modprobe`, dass das Modul nicht gefunden wird (kommt bei Cloud- oder Minimal-Images mit `linux-virtual`
vor), fehlt das Paket mit den Zusatzmodulen:

```bash
sudo apt install linux-modules-extra-$(uname -r)   # danach neu starten
```

Zeigt `lsusb` keinen Akai-Eintrag, liegt es am Kabel oder USB-Anschluss: ein anderes Kabel (manche können nur laden)
oder einen Port direkt am Rechner statt am Hub probieren. `sudo dmesg | tail` zeigt, was beim Einstecken passiert.

**3. Zugriffsrechte**

Wer sich normal am Ubuntu- oder Lubuntu-Desktop anmeldet, darf automatisch auf Audio- und MIDI-Geräte zugreifen.
Nur wenn die App per SSH, ohne Desktop oder als Dienst läuft, muss der Benutzer in die Gruppe `audio`:

```bash
sudo usermod -aG audio "$USER"    # danach ab- und wieder anmelden
groups                            # „audio“ sollte erscheinen
```

**4. Ton einrichten**

Die App spielt über das ALSA-Standardgerät. Ubuntu leitet das an den Sound-Server weiter, also an den Ausgang, der
in den Systemeinstellungen gewählt ist (Ubuntu: Einstellungen → Ton; Lubuntu: Lautsprecher-Symbol in der Leiste oder
`pavucontrol-qt`). Welcher Sound-Server läuft, hängt von der Version ab:

| Version | Sound-Server | nötige ALSA-Weiterleitung (normalerweise vorinstalliert) |
|---|---|---|
| 22.10 und neuer (z. B. 24.04) | PipeWire | `pipewire-alsa` |
| 22.04 und älter | PulseAudio | `libasound2-plugins` |

Kommt kein Ton, obwohl die App „🔊 Audio: …“ meldet, prüfen, ob die Weiterleitung da ist:

```bash
aplay -L | grep -E '^(pipewire|pulse)$'   # sollte „pipewire“ oder „pulse“ zeigen
sudo apt install pipewire-alsa            # falls leer, auf 22.10+; auf 22.04: libasound2-plugins
```

Knackt oder stottert der Ton (vor allem auf älteren Rechnern, für die Lubuntu oft genutzt wird), in
[`config.toml`](config.toml) `blocksize = 512` setzen.

**5. Testen**

```bash
uv run python tools/midi_monitor.py   # Tasten drücken: jede Eingabe erscheint als MIDI-Nachricht
uv run apc-dj
```

Der Standardbrowser (bei Ubuntu und Lubuntu Firefox) öffnet sich mit der Oberfläche. Auf einem Rechner ohne
Bildschirm: `uv run apc-dj --no-browser --host 0.0.0.0` starten und die Oberfläche auf einem Tablet im selben WLAN
öffnen (siehe [Sicherheit](#sicherheit--datenschutz)).

#### Andere Distributionen

Gleiche Schritte, andere Paketnamen: Debian / Linux Mint / Raspberry Pi OS (64 Bit) wie Ubuntu;
Fedora `sudo dnf install portaudio alsa-utils`; Arch `sudo pacman -S portaudio alsa-utils`.

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
| `--host 0.0.0.0` | Oberfläche im WLAN freigeben, z. B. für ein Tablet: `http://<IP-des-Rechners>:8000` |
| `--no-browser` | Browser nicht automatisch öffnen |

Weitere Einstellungen stehen in [`config.toml`](config.toml).

### Schreibtisch-Icon (macOS)

```bash
uv run --with pillow python tools/make_desktop_app.py
```

Das legt **DJ-Schule.app** mit eigenem Icon auf den Schreibtisch. Ein Doppelklick startet die App ohne Terminal
und öffnet den Browser. Beenden über das Dock oder mit `Cmd+Q`; dabei gehen auch die LEDs aus. Die Ausgabe steht
in `data/apc-dj.log`. Wenn der Projektordner verschoben wird, das Skript einfach erneut ausführen.

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

## Sicherheit & Datenschutz

* Die Oberfläche läuft standardmäßig nur auf diesem Rechner (`127.0.0.1`).
* Die WebSocket-Schnittstelle nimmt nur Verbindungen der eigenen Oberfläche an. Fremde Webseiten im selben
  Browser können die App nicht fernsteuern. Alle Eingaben aus dem Browser werden auf gültige Werte geprüft.
* Mit `--host 0.0.0.0` kann **jedes Gerät im selben WLAN** die Oberfläche öffnen und bedienen, ohne Passwort.
  Das nur in vertrauenswürdigen Netzen nutzen.
* Es werden keine externen Dienste geladen und keine Daten gesendet. Der Lernfortschritt bleibt lokal in
  `data/progress.json` und wird nicht eingecheckt, genauso wie eigene Sounds in `sounds/eigene/`.

## Lizenz

[MIT](LICENSE)
