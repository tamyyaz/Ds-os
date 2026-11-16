/* Darksham Launcher UI. Plain JS, no dependencies, works from file:// and from a local server.
   Dev options in the URL: ?lang=en  &select=2  &tab=1  &static=1 (no intro, frozen background) */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const q = new URLSearchParams(location.search);
  const STATIC = q.has("static");

  // ------------------------------------------------------------------ text
  const T = {
    ar: { games: "الألعاب", profile: "الملف الشخصي", apps: "التطبيقات", play: "تشغيل", move: "تنقّل", tabs: "تبديل القسم", lang: "EN",
      hours: "ساعة", last: "آخر لعب", today: "اليوم", yesterday: "أمس", days: "قبل %d يوم", never: "لم تُلعب بعد",
      player: "لاعب Darksham", stat_games: "عدد الألعاب", stat_hours: "ساعات اللعب", soon: "قريباً", apps_sub: "التطبيقات قادمة في نسخة لاحقة",
      demo: "معاينة: لن تُشغَّل «%s» من هنا", empty: "ما لقينا ألعاب" },
    en: { games: "Games", profile: "Profile", apps: "Apps", play: "Play", move: "Move", tabs: "Switch tab", lang: "عربي",
      hours: "h", last: "Last played", today: "Today", yesterday: "Yesterday", days: "%d days ago", never: "Never played",
      player: "Darksham player", stat_games: "Games", stat_hours: "Hours played", soon: "Coming soon", apps_sub: "Apps arrive in a later version",
      demo: "Preview: \"%s\" will not start from here", empty: "No games found" },
  };
  let lang = q.get("lang") || "ar";
  const t = (k, ...a) => (T[lang][k] || k).replace(/%[sd]/g, () => a.shift());
  const rtl = () => lang === "ar";

  const ICON = {
    pad: '<svg viewBox="0 0 24 24"><path d="M7 7h10a5 5 0 0 1 4.8 6.3l-.9 3.3a2.6 2.6 0 0 1-4.4 1l-1.8-2.1H9.3l-1.8 2.1a2.6 2.6 0 0 1-4.4-1l-.9-3.3A5 5 0 0 1 7 7z"/><path d="M8 10v3M6.5 11.5h3"/></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    cal: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
  };

  // ------------------------------------------------------------------ data
  const games = (window.LIBRARY && window.LIBRARY.games) || [];
  let idx = clamp(parseInt(q.get("select") || "0", 10) || 0, 0, Math.max(0, games.length - 1));
  let tab = ["games", "profile", "apps"].indexOf(q.get("tab") || "games");
  if (tab < 0) tab = clamp(parseInt(q.get("tab"), 10) || 0, 0, 2);
  let pad = false;
  let started = false;

  // ------------------------------------------------------------------ sound + haptics (synthesised, no files)
  let actx = null;
  function blip(freq, dur = 0.07, vol = 0.035, type = "sine", glide = 0.75) {
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)(); if (actx.state === "suspended") actx.resume();
      const o = actx.createOscillator(), g = actx.createGain(), now = actx.currentTime;
      o.type = type; o.frequency.setValueAtTime(freq, now); o.frequency.exponentialRampToValueAtTime(freq * glide, now + dur);
      g.gain.setValueAtTime(0.0001, now); g.gain.exponentialRampToValueAtTime(vol, now + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
      o.connect(g).connect(actx.destination); o.start(now); o.stop(now + dur + 0.02);
    } catch (e) { /* no audio, fine */ }
  }
  const sfx = { move: () => blip(1120, 0.06, 0.03), tab: () => blip(760, 0.09, 0.035, "triangle"), ok: () => { blip(520, 0.14, 0.04, "triangle", 1.5); setTimeout(() => blip(780, 0.2, 0.035, "triangle", 1.4), 70); }, edge: () => blip(300, 0.08, 0.03, "sine", 0.6) };
  function rumble(ms = 22, strong = 0.1, weak = 0.35) {
    for (const g of navigator.getGamepads ? navigator.getGamepads() : []) {
      if (g && g.vibrationActuator && g.vibrationActuator.playEffect) g.vibrationActuator.playEffect("dual-rumble", { duration: ms, strongMagnitude: strong, weakMagnitude: weak }).catch(() => {});
    }
  }

  // ------------------------------------------------------------------ springs
  class Spring {
    constructor(x = 0, k = 170, c = 22) { this.x = x; this.v = 0; this.to = x; this.k = k; this.c = c; }
    step(dt) { dt = Math.min(dt, 1 / 30); const a = this.k * (this.to - this.x) - this.c * this.v; this.v += a * dt; this.x += this.v * dt; return this.x; }
  }
  const row = new Spring(idx, 150, 20);

  // ------------------------------------------------------------------ stage fit
  function fit() { document.documentElement.style.setProperty("--k", Math.min(innerWidth / 1920, innerHeight / 1080)); }
  addEventListener("resize", fit); fit();

  // ------------------------------------------------------------------ cards
  const rowEl = $("#row");
  const cards = games.map((g, i) => {
    const c = el("div", "card");
    c.innerHTML = '<div class="glow"></div><div class="art"><img alt="" draggable="false"><div class="name"></div></div><div class="shine"></div><div class="ring"></div>';
    const img = $("img", c);
    img.src = g.cover || g.hero;
    $(".name", c).textContent = g.cover ? "" : g.title;
    c.addEventListener("click", () => { if (tab !== 0) return; if (i === idx) launch(); else select(i); });
    rowEl.appendChild(c);
    return { el: c, intro: new Spring(STATIC ? 1 : 0, 120, 14), delay: 0.45 + i * 0.08, f: 0 };
  });

  const STEP = 248, FOCUS = 1.14, EXTRA = 220 * (FOCUS - 1);
  function layoutCards(time, dt) {
    const pos = row.step(dt);
    const W = 1920, floor = 960, m = 96;
    cards.forEach((c, i) => {
      const d = i - pos, ad = Math.abs(d);
      const f = clamp(1 - ad, 0, 1);
      const s = lerp(1, FOCUS, f);
      const left = m + d * STEP + EXTRA * clamp(d, 0, 1);
      const cx = left + 220 * s * 0.5;
      const sx = rtl() ? W - cx : cx;
      if (!started && !STATIC) c.intro.to = 0;
      const intro = c.intro.step(dt);
      const lift = -14 * f;
      const sway = f > 0.01 ? f : 0;
      const ry = (sway * Math.sin(time * 0.9) * 5 + clamp(d, -1.5, 1.5) * (rtl() ? 9 : -9));
      const rx = sway * Math.cos(time * 0.7) * 2.6;
      const z = f * 70 - ad * 30;
      const a = clamp(1 + d * 1.1, 0, 1) * clamp(intro, 0, 1);
      c.el.style.transform = `translate3d(${sx - 110}px, ${floor - 330 + lift + (1 - intro) * 130}px, ${z}px) scale(${s}) rotateX(${rx}deg) rotateY(${ry}deg)`;
      c.el.style.transformOrigin = "50% 100%";
      c.el.style.opacity = a;
      c.el.style.visibility = a > 0.01 ? "visible" : "hidden";
      c.el.style.zIndex = String(Math.round(20 - ad * 3));
      c.el.style.setProperty("--f", f.toFixed(3));
      c.el.style.setProperty("--sx", (50 + ry * 6).toFixed(1) + "%");
      c.el.style.setProperty("--sy", (28 - rx * 8).toFixed(1) + "%");
    });
  }

  // ------------------------------------------------------------------ background + info
  const heroImgs = [$(".hero .a"), $(".hero .b")];
  const fillImgs = [$(".fill .a"), $(".fill .b")];
  let front = 0;
  function setBackdrop(g, instant) {
    const nextIdx = 1 - front;
    const set = (imgs, src, zoomFrom) => {
      const n = imgs[nextIdx], o = imgs[front];
      const same = n.dataset.src === src;
      n.dataset.src = src;
      if (!same) n.src = src;
      const go = () => {
        if (instant) { n.style.opacity = 1; o.style.opacity = 0; return; }
        n.getAnimations().forEach((a) => a.cancel());
        n.animate([{ opacity: 0, transform: `scale(${zoomFrom})`, filter: "blur(14px)" }, { opacity: 1, transform: "scale(1)", filter: "blur(0px)" }], { duration: 1400, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" });
        o.getAnimations().forEach((a) => a.cancel());
        o.animate([{ opacity: parseFloat(getComputedStyle(o).opacity) || 1 }, { opacity: 0 }], { duration: 900, fill: "forwards" });
      };
      if (same && n.complete) go(); else { n.onload = go; n.onerror = go; }
    };
    set(heroImgs, g.hero || g.cover, 1.09);
    set(fillImgs, g.blur || g.hero || g.cover, 1.04);
    front = nextIdx;
  }

  const logo = $("#logo"), title = $("#title"), chips = $("#chips");
  function lastText(ts) {
    if (!ts) return t("never");
    const days = Math.floor((Date.now() / 1000 - ts) / 86400);
    return days <= 0 ? t("today") : days === 1 ? t("yesterday") : t("days", days);
  }
  function chip(icon, text, cls) { const c = el("span", "chip " + (cls || ""), (icon || "") + "<span></span>"); $("span", c).textContent = text; return c; }

  function showGame(g, instant) {
    const root = document.documentElement.style;
    root.setProperty("--accent", g.accent); root.setProperty("--deep", g.dark);
    FX.setColors(g.accent, g.dark); if (instant) FX.snap();
    setBackdrop(g, instant);
    logo.style.display = g.logo ? "" : "none"; title.style.display = g.logo ? "none" : "";
    if (g.logo) logo.src = g.logo; title.textContent = g.title; logo.alt = g.title;
    chips.replaceChildren(
      chip(ICON.pad, g.source === "steam" ? "Steam" : "Darksham", "src"),
      chip(ICON.clock, `${String(g.hours).replace(/\.0$/, "")} ${t("hours")}`),
      chip(ICON.cal, `${t("last")}: ${lastText(g.last_played)}`));
    if (instant) return;
    const ease = "cubic-bezier(.16,1,.3,1)";
    const blocks = [$(".logo-wrap"), ...chips.children, $(".actions")];
    blocks.forEach((b, i) => {
      b.getAnimations().forEach((a) => a.cancel());
      b.animate([{ opacity: 0, transform: "translateY(26px)", filter: "blur(10px)" }, { opacity: 1, transform: "none", filter: "blur(0)" }],
        { duration: 700, delay: i * 55, easing: ease, fill: "backwards" });
    });
  }

  // ------------------------------------------------------------------ tabs, pages, hints
  const tabsEl = $("#tabs"), pill = $(".pill", tabsEl);
  const tabBtns = [...tabsEl.querySelectorAll("button")];
  tabBtns.forEach((b, i) => b.addEventListener("click", () => setTab(i)));
  let pillPlaced = false;
  function placePill() { const b = tabBtns[tab]; if (!pillPlaced) { pill.style.transition = "none"; requestAnimationFrame(() => (pill.style.transition = "")); pillPlaced = true; } pill.style.left = b.offsetLeft + "px"; pill.style.width = b.offsetWidth + "px"; tabBtns.forEach((x, i) => x.classList.toggle("on", i === tab)); }

  const hoursText = (h) => `${String(h).replace(/\.0$/, "")} ${t("hours")}`;
  function buildProfile() {
    $("#p-name").textContent = t("player");
    const total = games.reduce((sum, g) => sum + g.hours, 0);
    $("#p-sub").textContent = `${games.length} ${t("stat_games")} · ${Math.round(total)} ${t("hours")}`;
    const stats = $("#p-tiles"); stats.replaceChildren();
    [[games.length, t("stat_games")], [Math.round(total), t("stat_hours")]].forEach(([n, label]) => {
      const st = el("div", "stat", "<b></b><span></span>"); $("span", st).textContent = label; $("b", st).dataset.n = n; $("b", st).textContent = n; stats.appendChild(st);
    });
    const bars = $("#p-bars"); bars.replaceChildren();
    const max = Math.max(1, ...games.map((g) => g.hours));
    games.slice(0, 5).forEach((g) => {
      const r = el("div", "r", "<span></span><div class='t'><i></i></div><span></span>");
      const [a, , c] = r.children; a.textContent = g.title; c.textContent = hoursText(g.hours);
      const bar = $("i", r); bar.style.width = Math.max(1.5, g.hours / max * 100) + "%"; bar.style.setProperty("--c", g.accent); bar.style.setProperty("--origin", rtl() ? "right" : "left");
      bars.appendChild(r);
    });
  }
  function animateProfile() {
    $$bars().forEach((b, i) => b.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 1100, delay: 250 + i * 90, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" }));
    document.querySelectorAll("#p-tiles b").forEach((b) => {
      const n = +b.dataset.n, t0 = performance.now();
      (function tick(now) { const p = clamp((now - t0) / 1100, 0, 1); b.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(tick); })(t0);
    });
    $(".avatar.big").animate([{ transform: "scale(.6)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], { duration: 800, easing: "cubic-bezier(.34,1.56,.64,1)", fill: "backwards" });
    $("#p-panel").animate([{ opacity: 0, transform: "translateY(22px)" }, { opacity: 1, transform: "none" }], { duration: 700, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" });
  }
  const $$bars = () => [...document.querySelectorAll("#p-bars i")];

  function setTab(i) {
    if (i === tab) return;
    tab = (i + 3) % 3; sfx.tab(); rumble(18, 0.05, 0.2); applyTab(true);
  }
  function applyTab(animate) {
    placePill();
    const games_ = tab === 0;
    $("#row").style.display = games_ ? "" : "none";
    $("#info").style.display = games_ ? "" : "none";
    $("#page-profile").classList.toggle("on", tab === 1);
    $("#page-apps").classList.toggle("on", tab === 2);
    if (tab === 1) { buildProfile(); if (animate) animateProfile(); }
    if (tab === 2 && animate) $("#page-apps").animate([{ opacity: 0, transform: "translateY(24px)" }, { opacity: 1, transform: "none" }], { duration: 600, easing: "cubic-bezier(.16,1,.3,1)" });
    if (tab === 0 && animate) { $("#info").animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500 }); }
  }

  function key(what) {
    return { accept: pad ? "A" : "Enter", tabs: pad ? "LB / RB" : "Q / E", lang: pad ? "Y" : "F2", move: pad ? "D-pad" : "← →" }[what];
  }
  function buildHints() {
    $("#hints").replaceChildren(...[["move", t("move")], ["accept", t("play")], ["tabs", t("tabs")], ["lang", t("lang")]].map(([k, label]) => {
      const d = el("div", "", "<kbd></kbd><span></span>"); $("kbd", d).textContent = key(k); $("span", d).textContent = label; return d;
    }));
    $("#play-key").textContent = key("accept");
  }
  // The key hints are shown once (first launch), then fade away; F1 shows them again.
  const hintsEl = $("#hints");
  let hintTimer = 0;
  function flashHints(ms) { hintsEl.classList.add("show"); clearTimeout(hintTimer); hintTimer = setTimeout(() => hintsEl.classList.remove("show"), ms); }
  function firstRunHints() {
    let seen = false;
    try { seen = localStorage.getItem("darksham.hints") === "1"; } catch (e) { /* no storage: show every time */ }
    if (q.has("hints")) seen = false;
    if (seen || STATIC) return;
    setTimeout(() => flashHints(9000), 1800);
    try { localStorage.setItem("darksham.hints", "1"); } catch (e) { /* ignore */ }
  }

  function applyLang() {
    document.documentElement.lang = lang; document.documentElement.dir = rtl() ? "rtl" : "ltr";
    tabBtns.forEach((b) => (b.textContent = t(b.dataset.tab))); $("#play-label").textContent = t("play");
    $("#a-title").textContent = t("soon"); $("#a-sub").textContent = t("apps_sub");
    buildHints(); if (games.length) showGame(games[idx], true); if (tab === 1) buildProfile();
    requestAnimationFrame(placePill);
  }

  // ------------------------------------------------------------------ actions
  function select(i) {
    i = clamp(i, 0, games.length - 1);
    if (i === idx) { sfx.edge(); rumble(30, 0.2, 0.1); return; }
    idx = i; row.to = i; sfx.move(); rumble(); showGame(games[idx], false);
  }
  function move(screenDir) { if (tab !== 0 || !games.length) return; select(idx + (rtl() ? -screenDir : screenDir)); }

  const toast = $("#toast"); let toastTimer = 0;
  function showToast(text) { toast.textContent = text; toast.classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove("on"), 2600); }
  function launch() {
    if (tab !== 0 || !games.length) return;
    const g = games[idx]; sfx.ok(); rumble(60, 0.3, 0.5);
    const p = $("#play"); p.classList.add("press"); setTimeout(() => p.classList.remove("press"), 160);
    if (window.darksham && window.darksham.launch) window.darksham.launch(g.id); else showToast(t("demo", g.title));
  }
  $("#play").addEventListener("click", launch);
  $("#fav").addEventListener("click", (e) => e.currentTarget.classList.toggle("on"));
  function toggleLang() { lang = rtl() ? "en" : "ar"; applyLang(); sfx.tab(); }

  // ------------------------------------------------------------------ input
  const held = {}; // key -> {since, last}
  function repeat(name, down, now, fn) {
    const h = held[name] || (held[name] = { since: 0, last: 0, on: false });
    if (down && !h.on) { h.on = true; h.since = h.last = now; fn(); }
    else if (down && now - h.since > 420 && now - h.last > 130) { h.last = now; fn(); }
    else if (!down) h.on = false;
  }
  addEventListener("keydown", (e) => {
    if (pad) { pad = false; buildHints(); }
    if (e.repeat) return;
    const k = e.key;
    if (k === "ArrowRight") move(1); else if (k === "ArrowLeft") move(-1);
    else if (k === "Enter" || k === " ") launch();
    else if (k === "e" || k === "E") setTab(tab + 1); else if (k === "q" || k === "Q") setTab(tab - 1);
    else if (k === "F2") { e.preventDefault(); toggleLang(); }
    else if (k === "F1") { e.preventDefault(); flashHints(6000); }
  });
  let prevBtn = {};
  function pollPad(now) {
    const gp = (navigator.getGamepads && [...navigator.getGamepads()].find(Boolean)); if (!gp) return;
    const ax = gp.axes[0] || 0;
    const right = gp.buttons[15]?.pressed || ax > 0.55, left = gp.buttons[14]?.pressed || ax < -0.55;
    if (right || left || gp.buttons.some((b) => b.pressed)) { if (!pad) { pad = true; buildHints(); } }
    repeat("r", right, now, () => move(1)); repeat("l", left, now, () => move(-1));
    const edge = (i, fn) => { const p = !!gp.buttons[i]?.pressed; if (p && !prevBtn[i]) fn(); prevBtn[i] = p; };
    edge(0, launch); edge(5, () => setTab(tab + 1)); edge(4, () => setTab(tab - 1)); edge(3, toggleLang);
  }

  // ------------------------------------------------------------------ loop + start
  let last = performance.now(), clock = 0;
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now; clock += dt;
    const time = STATIC ? 3 : clock;
    if (tab === 0) layoutCards(time, dt);
    FX.tick(time, STATIC ? 0.0001 : dt);
    pollPad(now);
    requestAnimationFrame(frame);
  }
  function begin() {
    applyLang(); applyTab(false);
    $("#clock").textContent = new Date().toTimeString().slice(0, 5);
    setInterval(() => { $("#clock").textContent = new Date().toTimeString().slice(0, 5); }, 15000);
    if (!games.length) { showToast(t("empty")); }
    if (games.length) showGame(games[idx], true);
    if (!STATIC) {
      $(".top").animate([{ opacity: 0, transform: "translateY(-20px)" }, { opacity: 1, transform: "none" }], { duration: 900, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" });
      $(".bg").animate([{ opacity: 0, transform: "scale(1.06)" }, { opacity: 1, transform: "none" }], { duration: 1600, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" });
      [$(".logo-wrap"), ...chips.children, $(".actions")].forEach((b, i) => b.animate([{ opacity: 0, transform: "translateY(30px)", filter: "blur(12px)" }, { opacity: 1, transform: "none", filter: "blur(0)" }], { duration: 900, delay: 350 + i * 90, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" }));
      cards.forEach((c) => setTimeout(() => (c.intro.to = 1), c.delay * 1000));
    }
    started = true;
    firstRunHints();
    if (q.has("auto")) setTimeout(() => move(parseInt(q.get("auto"), 10) || 1), 500); // dev: simulate a key press
    requestAnimationFrame((n) => { last = n; frame(n); });
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(begin); else begin();
})();
