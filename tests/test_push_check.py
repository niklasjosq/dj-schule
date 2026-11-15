"""Push-Prüfung (tools/push_check.py): findet Zugangsdaten und Persönliches, lässt normalen Code durch.

Die Beispiel-Geheimnisse werden erst zur Laufzeit zusammengesetzt, damit diese Datei die Prüfung selbst besteht.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("push_check", ROOT / "tools" / "push_check.py")
pc = importlib.util.module_from_spec(_spec)
sys.modules["push_check"] = pc
_spec.loader.exec_module(pc)


def reasons(line, hosts=()):
    return [r for r, _ in pc.scan_text(line, hosts)]


@pytest.mark.parametrize("line, reason", [
    ("-----BEGIN " + "OPENSSH PRIVATE KEY-----", "privater Schlüssel"),
    ("-----BEGIN " + "PRIVATE KEY-----", "privater Schlüssel"),
    ("token: " + "gh" + "p_" + "a1B2" * 9, "GitHub-Token"),
    ("aws = " + "AK" + "IA" + "ABCDEFGHIJKLMNOP", "AWS-Schlüssel"),
    ("x = " + "xo" + "xb-" + "1234567890-abc", "Slack-Token"),
    ("ANTHROPIC=" + "sk" + "-ant-" + "x" * 30, "API-Schlüssel (OpenAI/Anthropic)"),
    ("key=" + "AI" + "za" + "Sy" + "A" * 33, "Google-API-Schlüssel"),
    ("url = 'https://max:" + "geheim123" + "@example.com/x'", "Login in einer URL"),
    ('password = "' + "hunter2" + "hunter2" + '"', "Passwort/Schlüssel im Klartext"),
    ('"api_key": "' + "abcdef" + "123456" + '"', "Passwort/Schlüssel im Klartext"),
    ("cd " + "/Us" + "ers/maxmuster/projekt", "Benutzerordner"),
    ("Exec=" + "/ho" + "me/schule/dj/start.sh", "Benutzerordner"),
    ("C:" + "\\Users\\" + "Max\\Desktop", "Benutzerordner (Windows)"),
    ("server: " + "192." + "168.178.20", "private IP-Adresse"),
    ("server: " + "10." + "0.0.5", "private IP-Adresse"),
    ("Kontakt: " + "max.muster" + "@" + "gmail.com", "E-Mail-Adresse"),
])
def test_findet_vertrauliches(line, reason):
    assert reason in reasons(line)


def test_geheimnisse_werden_verdeckt_angezeigt():
    secret = "gh" + "p_" + "a1B2" * 9
    [(_, shown)] = pc.scan_text("token = " + secret)
    assert secret not in shown


@pytest.mark.parametrize("line", [
    "Co-Authored-By: Claude Opus 5.5 <noreply" + "@anthropic.com>",
    "Author: niklasjosq <123+niklasjosq" + "@users.noreply.github.com>",
    "    uv run apc-dj --studio --host 0.0.0.0",
    "Oberfläche: http://localhost:8000 und http://127.0.0.1:8000",
    "~/.local/share/applications/dj-schule.desktop",
    "home = Path.home() / '.local' / 'share'",
    'token = ev.kind == "track"',
    '"react@18.3.1" und @media (max-width: 600px)',
    "config.local.toml und version 10.2",
])
def test_normaler_text_ist_ok(line):
    assert reasons(line) == []


def test_rechnername_mit_domain():
    hosts = pc.host_patterns(["Mein-Rechner.fritz.box", "localhost", "kurz"])
    assert len(hosts) == 1
    assert "Rechnername" in reasons("ssh " + "mein-rechner.fritz.box", hosts)
    assert reasons("Mein-Rechner ohne Domain", hosts) == []


@pytest.mark.parametrize("path", [
    ".env", "src/.env.local", "deploy/server.pem", "id_ed25519", ".netrc", "credentials.json",
    "data/progress.json", "data/apc-dj.log", "aufnahmen/DJ-Set_1.wav", "sounds/eigene/beat.wav",
    "musik/song.MP3", "config.local.toml", ".DS_Store", "x.sqlite",
])
def test_verbotene_dateien(path):
    assert pc.scan_path(path)


@pytest.mark.parametrize("path", [
    "README.md", "sounds/eigene/README.md", "src/apc_dj/app.py", "config.toml", "uv.lock",
    "src/apc_dj/web/static/style.css", "tools/make_desktop_app.py",
])
def test_erlaubte_dateien(path):
    assert pc.scan_path(path, 10_000) == []


def test_grosse_datei():
    assert pc.scan_path("bild.png", 6 * 1024 * 1024)


def test_repository_dateien_bestehen_die_pruefung():
    """Die eingecheckten Textdateien (auch diese Prüfung selbst) dürfen nichts auslösen."""
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for name in files.split():
        p = ROOT / name
        if p.suffix in {".png", ".icns", ".wav"} or not p.is_file():
            continue
        assert pc.scan_path(name, p.stat().st_size) == [], name
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            assert pc.scan_text(line) == [], f"{name}:{n}"


# ------------------------------------------------------------------ mit echtem Git

def _git(repo, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True).stdout


def _commit(repo, files, email="1+kind@users.noreply.github.com"):
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", "--", *files)
    _git(repo, "-c", f"user.email={email}", "-c", "user.name=Test", "commit", "-q", "-m", "Test")
    return _git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_commit_mit_geheimnis_und_zeilennummer(repo):
    sha = _commit(repo, {"a.py": "x = 1\ny = 2\n", "b.txt": "ok\n"})
    assert pc.scan_commit(sha) == []
    sha = _commit(repo, {"a.py": "x = 1\ny = 2\nkey = '" + "sk" + "-" + "z" * 24 + "'\n"})
    [f] = pc.scan_commit(sha)
    assert (f.where, f.reason) == ("a.py:3", "API-Schlüssel (OpenAI/Anthropic)")


def test_private_email_als_autor(repo):
    sha = _commit(repo, {"a.txt": "hallo\n"}, email="max.muster" + "@" + "gmail.com")
    assert [f.where for f in pc.scan_commit(sha)] == ["Autor des Commits", "Committer des Commits"]


def test_aufnahme_wird_erkannt(repo):
    sha = _commit(repo, {"aufnahmen/DJ-Set_1.wav": "RIFF"})
    assert [f.reason for f in pc.scan_commit(sha)] == ["Aufnahmen", "Audio-/Videodatei"]


def test_hook_prueft_nur_neue_commits(repo):
    alt = _commit(repo, {"a.txt": "Pfad: " + "/Us" + "ers/max/x\n"})  # schon „gepusht“
    neu = _commit(repo, {"b.txt": "sauber\n"})
    line = f"refs/heads/main {neu} refs/heads/main {alt}"
    assert pc.commits_from_hook([line]) == [neu]
    assert pc.commits_from_hook([f"refs/heads/x {pc.ZERO} refs/heads/x {alt}"]) == []  # Branch löschen
