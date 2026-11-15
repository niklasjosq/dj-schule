#!/usr/bin/env python3
"""Prüft vor jedem `git push`, dass nichts Vertrauliches in das öffentliche Repository gelangt.

Läuft als Git-Hook (.githooks/pre-push). Einmal pro Klon einschalten:

    git config core.hooksPath .githooks

Von Hand:

    python3 tools/push_check.py          # Commits, die noch nicht gepusht sind
    python3 tools/push_check.py --all    # die gesamte Geschichte

Geprüft wird jeder Commit, der gepusht würde: jede hinzugefügte Zeile, Dateinamen und -größen,
Autor-E-Mail und Commit-Nachricht. Gesucht wird nach
* Zugangsdaten: private Schlüssel, Tokens (GitHub, AWS, Slack, OpenAI/Anthropic, Google, …), Passwörter,
  Logins in URLs
* Persönlichem von diesem Rechner: Benutzerordner (/Users/…, /home/…), Rechnername, E-Mail-Adressen
  (außer den noreply-Adressen von GitHub), private IP-Adressen
* Dateien, die nicht ins Repository gehören: .env, Schlüssel, Logs, data/ (Lernfortschritt), aufnahmen/,
  Audio- und Videodateien, eigene Sounds, Datenbanken, Dateien über 5 MB

Findet die Prüfung etwas, wird der Push abgebrochen. Nur wenn es sicher ein Fehlalarm ist:
`git push --no-verify`. Braucht nur die Python-Standardbibliothek (ab Python 3.8), kein uv.
"""
from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
from dataclasses import dataclass

ZERO = "0" * 40
MAX_BYTES = 5 * 1024 * 1024
MAX_SHOWN = 40

# (Grund, Muster, verdecken?) – die Muster sind so geschrieben, dass sie diese Datei selbst nicht treffen
CONTENT_RULES = [
    ("privater Schlüssel", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----", True),
    ("GitHub-Token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})", True),
    ("AWS-Schlüssel", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", True),
    ("Slack-Token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}", True),
    ("API-Schlüssel (OpenAI/Anthropic)", r"\bsk-[A-Za-z0-9_-]{20,}", True),
    ("Google-API-Schlüssel", r"\bAIza[0-9A-Za-z_-]{35}", True),
    ("Stripe-Schlüssel", r"\b[rs]k_live_[0-9A-Za-z]{20,}", True),
    ("Hugging-Face-Token", r"\bhf_[A-Za-z0-9]{30,}", True),
    ("JSON Web Token", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", True),
    ("Login in einer URL", r"\b[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:[^/\s:@'\"]+@", True),
    ("Passwort/Schlüssel im Klartext",
     r"(?i)\b(?:password|passwort|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|auth)\w*"
     r"[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']", True),
    ("Benutzerordner", r"(?:/Users|/home)/[A-Za-z0-9._-]+", False),
    ("Benutzerordner (Windows)", r"\b[A-Za-z]:\\+Users\\+[A-Za-z0-9._ -]+", False),
    ("private IP-Adresse",
     r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b", False),
]

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ALLOWED_EMAIL_ENDINGS = ("@users.noreply.github.com", "@example.com", "@example.org", "@example.net")
ALLOWED_EMAILS = {"noreply@github.com", "noreply@anthropic.com", "git@github.com"}

PATH_RULES = [
    ("Umgebungsvariablen (.env)", r"(?:^|/)\.env(?:\.|$)"),
    ("Schlüssel-/Zertifikatsdatei", r"\.(?:pem|key|p12|pfx|jks|keystore|kdbx|ovpn)$"),
    ("SSH-Schlüssel", r"(?:^|/)id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?$"),
    ("Zugangsdaten-Datei",
     r"(?:^|/)(?:\.netrc|\.npmrc|\.pypirc|\.git-credentials|credentials(?:\.json)?|secrets?\.(?:json|toml|ya?ml))$"),
    ("Logdatei", r"\.log$"),
    ("lokale Daten (Lernfortschritt)", r"^data/"),
    ("Aufnahmen", r"^aufnahmen/"),
    ("eigene Sounds (oft urheberrechtlich geschützt)", r"^sounds/eigene/(?!README\.md$)"),
    ("Audio-/Videodatei", r"(?i)\.(?:wav|mp3|m4a|aac|flac|ogg|aiff?|mp4|mov|webm)$"),
    ("Datenbank", r"(?i)\.(?:sqlite3?|db)$"),
    ("lokale Einstellungen", r"(?:^|/)config\.local\.toml$"),
    ("macOS-Ordnerdaten", r"(?:^|/)\.DS_Store$"),
]


@dataclass
class Finding:
    commit: str
    where: str
    reason: str
    text: str


def _compile(rules):
    return [(reason, re.compile(pat), *rest) for reason, pat, *rest in rules]


_CONTENT = _compile(CONTENT_RULES)
_PATHS = _compile(PATH_RULES)


def _mask(s: str) -> str:
    return s[:6] + "…" if len(s) > 8 else "…"


def email_allowed(email: str) -> bool:
    e = email.lower()
    return e in ALLOWED_EMAILS or e.endswith(ALLOWED_EMAIL_ENDINGS)


def host_patterns(hostnames) -> list:
    """Rechnernamen mit Domain (z. B. „rechner.fritz.box“) – kurze Namen sind oft normale Wörter."""
    out = []
    for h in {h for h in hostnames if h}:
        if "." in h and not h.lower().startswith("localhost"):
            out.append(re.compile(r"(?<![\w.-])" + re.escape(h) + r"(?![\w-])", re.IGNORECASE))
    return out


def scan_text(line: str, hosts=()) -> list:
    """Fundstellen in einer Textzeile: Liste von (Grund, angezeigter Text)."""
    found = []
    for reason, rx, masked in _CONTENT:
        for m in rx.finditer(line):
            found.append((reason, _mask(m.group()) if masked else m.group()))
    for m in EMAIL.finditer(line):
        if not email_allowed(m.group()):
            found.append(("E-Mail-Adresse", m.group()))
    for rx in hosts:
        for m in rx.finditer(line):
            found.append(("Rechnername", m.group()))
    return found


def scan_path(path: str, size=None) -> list:
    """Gründe, warum eine Datei nicht ins Repository gehört."""
    reasons = [reason for reason, rx in _PATHS if rx.search(path)]
    if size is not None and size > MAX_BYTES:
        reasons.append(f"große Datei ({size / 1024 / 1024:.1f} MB)")
    return reasons


# ------------------------------------------------------------------ Git

def git(*args: str, input_text=None) -> str:
    res = subprocess.run(["git", "-c", "core.quotePath=false", *args], capture_output=True,
                         input=input_text.encode() if input_text is not None else None)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {res.stderr.decode(errors='replace').strip()}")
    return res.stdout.decode("utf-8", errors="replace")


def _unquote(p: str) -> str:
    if len(p) >= 2 and p[0] == p[-1] == '"':
        p = p[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return p


def added_lines(patch: str):
    """(Datei, Zeilennummer, Inhalt) für jede hinzugefügte Zeile eines Patches (--unified=0)."""
    path, lineno, in_hunk = None, 0, False
    for raw in patch.splitlines():
        if raw.startswith("diff --git "):
            path, in_hunk = None, False
        elif not in_hunk and raw.startswith("+++ "):
            p = _unquote(raw[4:])
            path = None if p == "/dev/null" else p[2:]
        elif raw.startswith("@@"):
            m = re.match(r"@@ -\S+ \+(\d+)", raw)
            lineno, in_hunk = (int(m.group(1)) if m else 0), True
        elif in_hunk and path is not None and raw.startswith("+"):
            yield path, lineno, raw[1:]
            lineno += 1


def changed_files(sha: str) -> list:
    """(Pfad, Größe) aller hinzugefügten oder geänderten Dateien eines Commits."""
    out = git("diff-tree", "--root", "-r", "--no-commit-id", "--raw", "-z", sha).split("\0")
    entries, i = [], 0
    while i + 1 < len(out):
        meta, path = out[i], out[i + 1]
        i += 2
        if not meta.startswith(":"):
            continue
        _, new_mode, _, new_blob, status = meta[1:].split(" ")[:5]
        if status.startswith("R") or status.startswith("C"):  # Umbenennen: zweiter Pfad folgt
            path, i = out[i], i + 1
        if status.startswith("D") or new_mode == "160000":
            continue
        entries.append((path, new_blob))
    sizes = {}
    if entries:
        batch = git("cat-file", "--batch-check=%(objectname) %(objectsize)",
                    input_text="\n".join(b for _, b in entries) + "\n")
        for line in batch.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                sizes[parts[0]] = int(parts[1])
    return [(p, sizes.get(b)) for p, b in entries]


def scan_commit(sha: str, hosts=()) -> list:
    short = sha[:7]
    findings = []
    meta = git("log", "-1", "--format=%ae%x00%ce%x00%B", sha).split("\0", 2)
    for who, email in (("Autor", meta[0]), ("Committer", meta[1])):
        if email and not email_allowed(email):
            findings.append(Finding(short, f"{who} des Commits", "E-Mail-Adresse (nicht noreply)", email))
    for n, line in enumerate(meta[2].splitlines(), 1):
        for reason, text in scan_text(line, hosts):
            findings.append(Finding(short, f"Commit-Nachricht, Zeile {n}", reason, text))
    for path, size in changed_files(sha):
        for reason in scan_path(path, size):
            findings.append(Finding(short, path, reason, ""))
    patch = git("diff-tree", "-p", "--root", "-r", "--no-commit-id", "--unified=0", "--no-color",
                "--no-ext-diff", "--no-textconv", sha)
    for path, lineno, line in added_lines(patch):
        for reason, text in scan_text(line, hosts):
            findings.append(Finding(short, f"{path}:{lineno}", reason, text))
    return findings


def _rev_list(*args: str) -> list:
    return git("rev-list", "--reverse", *args).split()


def commits_from_hook(stdin_lines) -> list:
    """Commits, die dieser Push veröffentlichen würde (Zeilen von stdin des pre-push-Hooks)."""
    shas = []
    for line in stdin_lines:
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:  # Löschen eines Branches veröffentlicht nichts
            continue
        local, remote = parts[1], parts[3]
        try:
            new = _rev_list(f"{remote}..{local}") if remote != ZERO else None
        except RuntimeError:  # Stand auf dem Server lokal unbekannt
            new = None
        if new is None:
            new = _rev_list(local, "--not", "--remotes")
        shas += [s for s in new if s not in shas]
    return shas


def unpushed_commits() -> list:
    try:
        return _rev_list("@{upstream}..HEAD")
    except RuntimeError:
        return _rev_list("HEAD", "--not", "--remotes")


def report(findings: list, n_commits: int) -> None:
    w = sys.stderr.write
    if not findings:
        w(f"🔒 Push-Prüfung: {n_commits} Commit(s) geprüft – nichts Vertrauliches gefunden.\n")
        return
    w(f"\n🔒 Push-Prüfung: {len(findings)} Fundstelle(n) in {n_commits} Commit(s) – "
      "das darf so nicht ins öffentliche Repository.\n\n")
    for f in findings[:MAX_SHOWN]:
        w(f"  {f.commit}  {f.where}\n           {f.reason}" + (f": {f.text}" if f.text else "") + "\n")
    if len(findings) > MAX_SHOWN:
        w(f"  … und {len(findings) - MAX_SHOWN} weitere\n")
    w("\nBitte entfernen und die Commits ändern (git commit --amend bzw. git rebase -i), dann erneut pushen.\n"
      "Nur wenn es sicher ein Fehlalarm ist: git push --no-verify\n\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hook", action="store_true", help="als pre-push-Hook (Commits von stdin)")
    ap.add_argument("--all", action="store_true", help="die gesamte Geschichte prüfen")
    ap.add_argument("remote", nargs="*", help=argparse.SUPPRESS)  # Name und URL vom Hook
    args = ap.parse_args(argv)
    try:
        if args.all:
            shas = _rev_list("HEAD")
        elif args.hook:
            shas = commits_from_hook(sys.stdin.read().splitlines())
        else:
            shas = unpushed_commits()
        hosts = host_patterns([socket.gethostname()])
        findings = [f for sha in shas for f in scan_commit(sha, hosts)]
    except RuntimeError as e:
        sys.stderr.write(f"🔒 Push-Prüfung fehlgeschlagen: {e}\n")
        return 2
    report(findings, len(shas))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
