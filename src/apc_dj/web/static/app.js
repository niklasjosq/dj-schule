// DJ-Schule – Browser-Oberfläche. Spiegelt den APC mini mk2 und schickt Klicks an Python.
"use strict";

const $ = (id) => document.getElementById(id);
const S = { layout: [], leds: {}, buttons: { track: Array(8).fill(0), scene: Array(8).fill(0) },
            faders: Array(9).fill(0.8), mode: "frei", metronome: false, lessons: null, game: null,
            beat: { active: false, bar: 0, beat: 0, step: 0 }, targets: [] };
const EL = { pads: [], tracks: [], scenes: [], faders: [] };
let ws = null;

// ------------------------------------------------------------------ Aufbau
function pressable(el, kind, index) {
  const down = (e) => { e.preventDefault(); el.setPointerCapture?.(e.pointerId); send({ t: "press", kind, index }); };
  const up = (e) => { e.preventDefault(); send({ t: "release", kind, index }); };
  el.addEventListener("pointerdown", down);
  el.addEventListener("pointerup", up);
  el.addEventListener("pointercancel", up);
  el.addEventListener("contextmenu", (e) => e.preventDefault());
}

function build() {
  const grid = $("grid");
  for (let r = 7; r >= 0; r--) {
    for (let c = 0; c < 8; c++) {
      const p = r * 8 + c;
      const b = document.createElement("button");
      b.className = "pad";
      b.innerHTML = '<span class="emo"></span><span class="lbl"></span>';
      pressable(b, "pad", p);
      grid.appendChild(b);
      EL.pads[p] = b;
    }
  }
  for (let i = 0; i < 8; i++) {
    const s = document.createElement("button");
    s.className = "round green";
    s.textContent = i + 1;
    pressable(s, "scene", i);
    $("scenes").appendChild(s);
    EL.scenes[i] = s;
    const t = document.createElement("button");
    t.className = "round red";
    t.textContent = i + 1;
    pressable(t, "track", i);
    $("tracks").appendChild(t);
    EL.tracks[i] = t;
  }
  pressable($("shift"), "shift", 0);
  for (let i = 0; i < 9; i++) {
    const f = document.createElement("div");
    f.className = "fader";
    f.innerHTML = `<input type="range" min="0" max="1" step="0.01" value="0.8" aria-label="Fader ${i + 1}"><span>${i === 8 ? "Master" : i + 1}</span>`;
    f.querySelector("input").addEventListener("input", (e) => send({ t: "fader", index: i, value: +e.target.value }));
    $("faders").appendChild(f);
    EL.faders[i] = f;
  }
  document.querySelectorAll("#modes button").forEach((b) =>
    b.addEventListener("click", () => send({ t: "mode", mode: b.dataset.mode })));
  $("metronome").addEventListener("click", () => send({ t: "metronome", on: !S.metronome }));
  $("instrument").addEventListener("click", () => send({ t: "instrument" }));
  buildGameGrid();
}

// ------------------------------------------------------------------ Darstellung
function mix(hex, pct) { return `color-mix(in srgb, ${hex} ${pct}%, #26262b)`; }

function renderPad(p) {
  const el = EL.pads[p];
  const spec = S.layout[p];
  if (!el || !spec) return;
  el.querySelector(".emo").textContent = spec.emoji || "";
  el.querySelector(".lbl").textContent = spec.label === "leer" ? "" : spec.label;
  el.classList.toggle("key", spec.role === "key");
  const led = S.leds[p];
  el.classList.remove("blink");
  if (!led || !led[0]) {
    el.style.background = "#3a3a40";
  } else {
    const [hex, mode, bright] = led;
    el.style.background = mode === "solid" ? mix(hex, bright >= 100 ? 100 : bright >= 50 ? 62 : 36) : hex;
    if (mode !== "solid") el.classList.add("blink");
    el.style.boxShadow = mode === "solid" && bright >= 100 ? `0 0 16px ${hex}` : "";
  }
  el.title = `${spec.emoji} ${spec.label}`;
}

function renderButtons() {
  ["track", "scene"].forEach((kind) => {
    const els = kind === "track" ? EL.tracks : EL.scenes;
    S.buttons[kind].forEach((v, i) => {
      els[i].classList.toggle("on", v === 1);
      els[i].classList.toggle("blink", v === 2);
    });
  });
  (S.sceneLabels || []).forEach((l, i) => (EL.scenes[i].title = l));
  (S.trackLabels || []).forEach((l, i) => (EL.tracks[i].title = l));
}

function renderTargets() {
  document.querySelectorAll(".target").forEach((e) => e.classList.remove("target"));
  if (S.mode !== "lektion") return;
  for (const [kind, i] of S.targets) {
    if (kind === "pad") EL.pads[i]?.classList.add("target");
    if (kind === "fader") EL.faders[i]?.classList.add("target");
    if (kind === "shift") $("shift").classList.add("target");
  }
}

function renderStatus() {
  document.querySelectorAll("#modes button").forEach((b) => b.classList.toggle("active", b.dataset.mode === S.mode));
  $("metronome").classList.toggle("on", S.metronome);
  $("instrument").textContent = S.instrument || "🎹";
  $("bpm").textContent = `${S.bpm || 120} BPM`;
  $("panelFrei").hidden = S.mode !== "frei";
  $("panelLektion").hidden = S.mode !== "lektion";
  $("panelSpiel").hidden = S.mode !== "spiel";
}

function renderFaders() {
  S.faders.forEach((v, i) => { const inp = EL.faders[i].querySelector("input"); if (document.activeElement !== inp) inp.value = v; });
  $("filterBar").style.width = `${Math.round((S.filter ?? 1) * 100)}%`;
}

function renderBeat() {
  const b = S.beat;
  [...$("beats").children].forEach((d, i) => {
    d.classList.toggle("on", b.active && i === b.beat);
    d.classList.toggle("one", i === 0);
  });
  [...$("bars").children].forEach((d, i) => d.classList.toggle("on", b.active && i <= ((b.bar % 4) + 4) % 4));
  $("beatLabel").textContent = b.active
    ? `Takt ${(((b.bar % 4) + 4) % 4) + 1} von 4 · Schlag ${b.beat + 1}`
    : "Starte eine Loop – dann zählen wir mit!";
  renderGameCursor();
}

function renderLegend(columns) {
  $("legend").innerHTML = columns.map((c) => `<span><i style="background:${c.color}"></i>${c.emoji} ${c.name}</span>`).join("");
}

function showInfo(m) {
  $("infoEmoji").textContent = m.emoji || "🎵";
  $("infoTitle").textContent = m.title;
  $("infoText").textContent = m.text;
  const card = $("info");
  card.classList.remove("pop"); void card.offsetWidth; card.classList.add("pop");
}

// ------------------------------------------------------------------ Lektionen
function renderLessons() {
  const L = S.lessons;
  if (!L) return;
  const cur = L.current;
  $("lessonList").innerHTML = "";
  L.list.forEach((l, i) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.className = cur && cur.index === i ? "current" : "";
    b.innerHTML = `<span>${i + 1}. ${l.emoji} ${l.title}</span><span>${"⭐".repeat(l.stars)}${"☆".repeat(3 - l.stars)}</span>`;
    b.addEventListener("click", () => send({ t: "lesson", index: i }));
    li.appendChild(b);
    $("lessonList").appendChild(li);
  });
  if (!cur) { $("lessonCurrent").innerHTML = "<p>Wähle eine Lektion aus!</p>"; S.targets = []; return; }
  const pct = Math.round((cur.step / cur.steps) * 100);
  $("lessonCurrent").innerHTML = `<div class="lesson-now">
      <h2>${cur.emoji} ${cur.index + 1}. ${cur.title}</h2>
      <div class="progress"><i style="width:${pct}%"></i></div>
      <div class="step ${cur.done ? "done" : ""}">${cur.done ? "🏆 Geschafft! " + "⭐".repeat(cur.stars) : `<small>Schritt ${cur.step + 1} von ${cur.steps}</small><br>${cur.text}`}</div>
    </div>`;
  S.targets = cur.targets || [];
  renderTargets();
}

// ------------------------------------------------------------------ Spiel
const GAME_EMO = ["🥁", "🪘", "👏", "🎩"];
function buildGameGrid() {
  const g = $("gGrid");
  g.innerHTML = "";
  ["Kick", "Snare", "Clap", "HiHat"].forEach((name, r) => {
    const n = document.createElement("div");
    n.className = "name";
    n.textContent = `${GAME_EMO[r]} ${name}`;
    g.appendChild(n);
    for (let s = 0; s < 8; s++) {
      const c = document.createElement("div");
      c.className = "cell" + (s % 2 === 0 ? " beat" : "");
      c.dataset.r = r; c.dataset.s = s;
      g.appendChild(c);
    }
  });
}

function renderGame() {
  const G = S.game;
  if (!G) return;
  $("gLevel").textContent = G.level;
  $("gScore").textContent = G.score;
  $("gStreak").textContent = G.streak;
  $("gMsg").textContent = G.message;
  document.querySelectorAll("#gGrid .cell").forEach((c) => {
    c.className = "cell" + (+c.dataset.s % 2 === 0 ? " beat" : "");
    c.textContent = "";
  });
  const cell = (s, r) => document.querySelector(`#gGrid .cell[data-r="${r}"][data-s="${s}"]`);
  if (G.phase === "result" && G.results.length) {
    G.results.forEach((r) => { const c = cell(r.step, r.pad); if (c) { c.classList.add(r.rating); c.textContent = r.rating === "perfekt" ? "★" : r.rating === "gut" ? "✓" : "✗"; } });
  } else {
    G.pattern.forEach(([s, p]) => { const c = cell(s, p); if (c) { c.classList.add("hit"); c.textContent = GAME_EMO[p]; } });
  }
  renderGameCursor();
}

function renderGameCursor() {
  document.querySelectorAll("#gGrid .cell.now").forEach((c) => c.classList.remove("now"));
  if (S.mode !== "spiel" || !S.game || !["listen", "play"].includes(S.game.phase)) return;
  document.querySelectorAll(`#gGrid .cell[data-s="${S.beat.step}"]`).forEach((c) => c.classList.add("now"));
}

function toast(rating) {
  const t = document.createElement("div");
  t.className = `toast ${rating}`;
  t.textContent = { perfekt: "Perfekt! 🌟", gut: "Gut! 👍", daneben: "Daneben", falsch: "Falsches Pad" }[rating] || rating;
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 900);
}

// ------------------------------------------------------------------ Nachrichten
function onMessage(m) {
  switch (m.t) {
    case "state":
      Object.assign(S, { layout: m.layout, leds: m.leds, buttons: m.buttons, faders: m.faders, filter: m.filter,
        mode: m.mode, metronome: m.metronome, instrument: m.instrument, bpm: m.bpm, lessons: m.lessons, game: m.game,
        sceneLabels: m.scene_labels, trackLabels: m.track_labels });
      $("conn").textContent = m.controller ? "🎛️ APC verbunden" : "🖱️ ohne Controller";
      renderLegend(m.columns);
      for (let p = 0; p < 64; p++) renderPad(p);
      renderButtons(); renderStatus(); renderFaders(); renderLessons(); renderGame();
      break;
    case "leds":
      Object.assign(S.leds, m.pads);
      Object.keys(m.pads).forEach((p) => renderPad(+p));
      S.buttons = m.buttons; renderButtons();
      break;
    case "press": {
      const el = m.kind === "pad" ? EL.pads[m.index] : m.kind === "track" ? EL.tracks[m.index]
        : m.kind === "scene" ? EL.scenes[m.index] : $("shift");
      el?.classList.toggle("pressed", m.pressed);
      break;
    }
    case "fader": S.faders[m.index] = m.value; renderFaders(); break;
    case "filter": S.filter = m.value; renderFaders(); break;
    case "beat": S.beat = m; renderBeat(); break;
    case "info": showInfo(m); break;
    case "status": Object.assign(S, m); renderStatus(); renderTargets(); renderGameCursor(); break;
    case "lesson": S.lessons = m; renderLessons(); break;
    case "game": S.game = m; renderGame(); break;
    case "game_hit": toast(m.rating); break;
  }
}

function send(m) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); }

function connect() {
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onopen = () => $("conn").classList.replace("bad", "ok") || $("conn").classList.add("ok");
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  ws.onclose = () => {
    $("conn").textContent = "⚠️ getrennt – verbinde neu …";
    $("conn").classList.remove("ok"); $("conn").classList.add("bad");
    setTimeout(connect, 1000);
  };
}

build();
connect();
