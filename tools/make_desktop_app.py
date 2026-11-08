"""Legt die DJ-Schule mit eigenem Icon auf den Schreibtisch (macOS und Linux).

    uv run --with pillow python tools/make_desktop_app.py               # Icon + Starter + Schreibtisch
    uv run --with pillow python tools/make_desktop_app.py --no-install  # nur nach build/

macOS: baut „DJ-Schule.app“. Doppelklick startet die DJ-Schule im Hintergrund und öffnet den Browser;
„Beenden“ (Dock oder Cmd+Q) schickt Strg+C an die App, damit auch die LEDs ausgehen.
Die Ausgabe steht in data/apc-dj.log.

Linux (Ubuntu, Lubuntu, …): legt einen Starter „DJ-Schule“ auf den Schreibtisch und ins Anwendungsmenü.
Doppelklick öffnet ein Terminalfenster mit der App und den Browser; Strg+C oder Schließen des Fensters beendet sie.

Wird der Projektordner verschoben, das Skript neu ausführen.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
APP_NAME = "DJ-Schule"

# Farben der Oberfläche (style.css) und der Pads
BG_TOP, BG_BOTTOM = (58, 42, 122), (20, 17, 42)
PAD_ROWS = [  # oben → unten, (hell, gedimmt)
    ((255, 95, 162), (110, 40, 80)),   # rosa
    ((255, 207, 63), (110, 88, 30)),   # gelb
    ((75, 227, 139), (30, 95, 62)),    # grün
    ((90, 200, 255), (35, 80, 115)),   # blau
]
LIT = {(0, 0), (0, 2), (1, 1), (1, 3), (2, 0), (2, 1), (2, 3), (3, 2)}  # leuchtende Pads (Reihe, Spalte)


def _lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def draw_icon(size: int = 1024, macos: bool = True) -> Image.Image:
    """Zeichnet das Icon (abgerundetes Quadrat), 4× überabgetastet.

    macos=True: Apple-Raster mit Rand und Schatten; sonst fast randlos wie bei Linux-Icon-Themes.
    """
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # macOS: Grundfläche 824/1024 des Rasters, Radius ~ 185/1024 (Apple-Vorgabe)
    inset = round(s * (100 if macos else 32) / 1024)
    radius = round((s - 2 * inset) * 185 / 824)
    box = (inset, inset, s - inset, s - inset)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)

    if macos:
        shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((box[0], box[1] + s // 80, box[2], box[3] + s // 80), radius,
                                                 fill=(0, 0, 0, 140))
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(s / 70)))

    # Hintergrund: Farbverlauf + rosa/violetter Schein wie in der Oberfläche
    bg = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(bg)
    for y in range(s):
        d.line([(0, y), (s, y)], fill=_lerp(BG_TOP, BG_BOTTOM, y / s) + (255,))
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((s * 0.55, s * 0.05, s * 1.15, s * 0.65), fill=(140, 40, 140, 150))
    gd.ellipse((-s * 0.1, -s * 0.2, s * 0.5, s * 0.35), fill=(110, 80, 220, 120))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s / 10)))

    # Pads: 4×4-Raster
    n, area = 4, (s - 2 * inset) * 0.70
    gap = area * 0.075
    pad = (area - gap * (n - 1)) / n
    x0 = (s - area) / 2
    y0 = (s - area) / 2
    pads = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pd, hd = ImageDraw.Draw(pads), ImageDraw.Draw(halo)
    for r in range(n):
        for c in range(n):
            bright, dim = PAD_ROWS[r]
            x, y = x0 + c * (pad + gap), y0 + r * (pad + gap)
            rect = (x, y, x + pad, y + pad)
            lit = (r, c) in LIT
            if lit:
                g = pad * 0.18
                hd.rounded_rectangle((x - g, y - g, x + pad + g, y + pad + g), pad * 0.3, fill=bright + (200,))
            pd.rounded_rectangle(rect, pad * 0.2, fill=(bright if lit else dim) + (255,))
            if lit:  # Glanzlicht oben
                hl = (x + pad * 0.14, y + pad * 0.1, x + pad * 0.86, y + pad * 0.4)
                pd.rounded_rectangle(hl, pad * 0.14, fill=_lerp(bright, (255, 255, 255), 0.45) + (255,))
    bg.alpha_composite(halo.filter(ImageFilter.GaussianBlur(pad * 0.22)))
    bg.alpha_composite(pads)

    # dezente Innenkante oben
    edge = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(box, radius, outline=(255, 255, 255, 40), width=s // 200)
    bg.alpha_composite(edge)

    img.paste(bg, (0, 0), mask)
    return img.resize((size, size), Image.LANCZOS)


def make_icns(icon: Image.Image, out: Path) -> None:
    iconset = BUILD / "AppIcon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir(parents=True)
    for base in (16, 32, 128, 256, 512):
        icon.resize((base, base), Image.LANCZOS).save(iconset / f"icon_{base}x{base}.png")
        icon.resize((base * 2, base * 2), Image.LANCZOS).save(iconset / f"icon_{base}x{base}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)


def _as(s: str) -> str:
    """Zeichenkette als AppleScript-Literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def applescript(uv: str) -> str:
    repo, log = str(ROOT), str(ROOT / "data" / "apc-dj.log")
    return f'''
global appPid, logFile

on run
	set appPid to ""
	set logFile to {_as(log)}
	-- nur nohup in den Hintergrund schicken (nicht die ganze &&-Kette), sonst bleibt die Ausgabe-Pipe offen
	set cmd to "cd " & quoted form of {_as(repo)} & " || exit 1; mkdir -p data; " & ¬
		"nohup sh -c " & quoted form of ({_as(uv)} & " sync -q && exec .venv/bin/apc-dj") & ¬
		" > " & quoted form of logFile & " 2>&1 < /dev/null & echo $!"
	set appPid to do shell script cmd
end run

on idle
	if appPid is not "" then
		try
			do shell script "kill -0 " & appPid
		on error
			set appPid to ""
			set tailText to do shell script "tail -n 12 " & quoted form of logFile & " || true"
			display dialog "Die DJ-Schule wurde beendet." & return & return & tailText ¬
				buttons {{"OK"}} default button 1 with title "DJ-Schule" with icon caution
			quit
		end try
	end if
	return 2
end idle

on quit
	if appPid is not "" then
		try
			do shell script "kill -INT " & appPid & "; for i in $(seq 1 40); do kill -0 " & appPid & ¬
				" 2>/dev/null || exit 0; sleep 0.25; done; kill -TERM " & appPid & " 2>/dev/null; true"
		end try
		set appPid to ""
	end if
	continue quit
end quit
'''


def build_app(uv: str, icns: Path) -> Path:
    app = BUILD / f"{APP_NAME}.app"
    shutil.rmtree(app, ignore_errors=True)
    src = BUILD / "launcher.applescript"
    src.write_text(applescript(uv), encoding="utf-8")
    subprocess.run(["osacompile", "-s", "-o", str(app), str(src)], check=True)  # -s: bleibt offen

    res = app / "Contents" / "Resources"
    shutil.copy(icns, res / "applet.icns")
    plist = app / "Contents" / "Info.plist"
    for key, val in (("CFBundleIdentifier", "de.apc-dj.dj-schule"), ("CFBundleDisplayName", APP_NAME)):
        subprocess.run(["plutil", "-replace", key, "-string", val, str(plist)], check=True)
    # Signatur nach dem Austausch des Icons erneuern (ad hoc), sonst meldet macOS „beschädigt“
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True,
                   capture_output=True)
    return app


# ------------------------------------------------------------------ Linux

def _sh(s: str) -> str:
    """Zeichenkette für die Shell in einfache Anführungszeichen setzen."""
    return "'" + s.replace("'", "'\\''") + "'"


def _desktop_exec(s: str) -> str:
    """Pfad für die Exec-Zeile einer .desktop-Datei (Desktop Entry Spec)."""
    for ch in ("\\", '"', "`", "$"):
        s = s.replace(ch, "\\" + ch)
    return f'"{s}"'.replace("\\", "\\\\").replace("%", "%%")


def linux_start_script(uv: str) -> str:
    return f"""#!/bin/sh
# Startet die DJ-Schule (erzeugt von tools/make_desktop_app.py)
printf '\\033]0;DJ-Schule\\007'
cd {_sh(str(ROOT))} || {{ echo "Projektordner nicht gefunden:" {_sh(str(ROOT))}; read _; exit 1; }}
echo "🎧 DJ-Schule startet … Zum Beenden Strg+C drücken oder dieses Fenster schließen."
echo
trap : INT    # Strg+C nur an die App, das Skript zeigt danach ggf. noch die Meldung
{_sh(uv)} sync -q && .venv/bin/apc-dj
status=$?
if [ "$status" -ne 0 ] && [ "$status" -ne 130 ]; then
    echo
    echo "⚠️  Die DJ-Schule wurde mit einem Fehler beendet (Code $status)."
    printf "Enter drücken zum Schließen … "
    read _
fi
"""


def linux_desktop_entry(start: Path, icon: Path) -> str:
    return f"""[Desktop Entry]
Type=Application
Version=1.0
Name=DJ-Schule
GenericName=DJ-Lernprogramm
Comment=DJ lernen mit dem AKAI APC mini mk2
Exec={_desktop_exec(str(start))}
Icon={icon}
Terminal=true
Categories=AudioVideo;Audio;Education;Music;
Keywords=DJ;MIDI;APC;Musik;
StartupNotify=false
"""


def _desktop_dir() -> Path | None:
    """Schreibtisch-Ordner laut XDG (z. B. ~/Schreibtisch bei deutscher Sprache)."""
    try:
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, check=True).stdout.strip()
        if out and Path(out) != Path.home():
            return Path(out)
    except (OSError, subprocess.CalledProcessError):
        pass
    for name in ("Schreibtisch", "Desktop"):
        if (Path.home() / name).is_dir():
            return Path.home() / name
    return None


def _make_trusted(path: Path) -> None:
    """Ausführbar + „vertrauenswürdig“, damit Ubuntu (GNOME) und Lubuntu (PCManFM-Qt) ohne Rückfrage starten."""
    path.chmod(0o755)
    try:
        subprocess.run(["gio", "set", str(path), "metadata::trusted", "true"], capture_output=True, check=False)
    except OSError:
        pass


def install_linux(uv: str, no_install: bool, dest: Path | None) -> None:
    icon = draw_icon(macos=False)
    out = BUILD / "linux"
    out.mkdir(parents=True, exist_ok=True)
    icon.save(BUILD / "icon.png")

    data_home = Path.home() / ".local" / "share"
    base = out if no_install else data_home / "dj-schule"
    base.mkdir(parents=True, exist_ok=True)
    icon_file = base / "dj-schule.png"
    icon.resize((512, 512), Image.LANCZOS).save(icon_file)
    start = base / "start.sh"
    start.write_text(linux_start_script(uv), encoding="utf-8")
    start.chmod(0o755)
    entry = linux_desktop_entry(start, icon_file)
    (out / "dj-schule.desktop").write_text(entry, encoding="utf-8")
    print(f"✅ gebaut: {out / 'dj-schule.desktop'}")
    if no_install:
        return

    menu = data_home / "applications" / "dj-schule.desktop"
    menu.parent.mkdir(parents=True, exist_ok=True)
    menu.write_text(entry, encoding="utf-8")
    menu.chmod(0o755)
    print(f"📋 im Anwendungsmenü: {menu}")

    desk = dest or _desktop_dir()
    if desk is None or not desk.is_dir():
        print("ℹ️  Kein Schreibtisch-Ordner gefunden – Starter nur im Anwendungsmenü.")
        return
    target = desk / "dj-schule.desktop"
    target.write_text(entry, encoding="utf-8")
    _make_trusted(target)
    print(f"🖥️  auf dem Schreibtisch: {target}")
    print("   Ubuntu: Falls das Icon noch grau ist, Rechtsklick → „Start erlauben“.")


# ------------------------------------------------------------------ Start

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-install", action="store_true", help="nur nach build/ bauen, nichts installieren")
    ap.add_argument("--dest", type=Path, help="Zielordner statt des Schreibtischs")
    args = ap.parse_args()

    uv = shutil.which("uv")
    if not uv:
        sys.exit("uv nicht gefunden – siehe https://docs.astral.sh/uv/")
    uv = str(Path(uv).resolve())
    BUILD.mkdir(exist_ok=True)

    if sys.platform.startswith("linux"):
        install_linux(uv, args.no_install, args.dest)
        return
    if sys.platform != "darwin":
        sys.exit("Nur für macOS und Linux.")

    icon = draw_icon()
    icon.save(BUILD / "icon.png")
    icns = BUILD / "AppIcon.icns"
    make_icns(icon, icns)
    app = build_app(uv, icns)
    print(f"✅ gebaut: {app}")

    if not args.no_install:
        target = (args.dest or Path.home() / "Desktop") / app.name
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(app, target, symlinks=True)
        subprocess.run(["touch", str(target)])  # Finder lädt das Icon neu
        print(f"🖥️  auf dem Schreibtisch: {target}")


if __name__ == "__main__":
    main()
