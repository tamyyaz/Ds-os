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
      demo: "معاينة: لن تُشغَّل «%s» من هنا", empty: "ما لقينا ألعاب", store: "المتجر", details: "التفاصيل", open_steam: "فتح في Steam", shelf: "الأقسام",
      free: "مجاني", in_library: "في مكتبتك", temp_source: "مصدر مؤقت", arabic_yes: "يدعم العربية", loading: "جاري تحميل المتجر…", store_fail: "تعذّر الوصول للمتجر، تحقق من الإنترنت", retry: "إعادة المحاولة",
      opened_steam: "فُتحت صفحة «%s» في Steam", developer: "المطوّر", publisher: "الناشر", release: "الإصدار", genre: "النوع", platforms: "المنصات", no_details: "ما في تفاصيل لهاللعبة",
      store_note: "متجر <b>Darksham</b> الخاص قيد العمل. حالياً المتجر من Steam كمصدر مؤقت.",
      sh_featured: "مميّز", sh_top_sellers: "الأكثر مبيعاً", sh_specials: "عروض", sh_new_releases: "إصدارات جديدة", sh_coming_soon: "قريباً", back: "رجوع", launching: "جاري تشغيل «%s»…", busy: "جاري التشغيل", launch_fail: "تعذّر تشغيل «%s»: %s" },
    en: { games: "Games", profile: "Profile", apps: "Apps", play: "Play", move: "Move", tabs: "Switch tab", lang: "عربي",
      hours: "h", last: "Last played", today: "Today", yesterday: "Yesterday", days: "%d days ago", never: "Never played",
      player: "Darksham player", stat_games: "Games", stat_hours: "Hours played", soon: "Coming soon", apps_sub: "Apps arrive in a later version",
      demo: "Preview: \"%s\" will not start from here", empty: "No games found", store: "Store", details: "Details", open_steam: "Open in Steam", shelf: "Shelves",
      free: "Free", in_library: "In your library", temp_source: "temporary source", arabic_yes: "Arabic supported", loading: "Loading the store…", store_fail: "Could not reach the store, check your connection", retry: "Retry",
      opened_steam: "Opened \"%s\" in Steam", developer: "Developer", publisher: "Publisher", release: "Release", genre: "Genre", platforms: "Platforms", no_details: "No details for this game",
      store_note: "The <b>Darksham</b> store is in progress. For now the store is Steam, as a temporary source.",
      sh_featured: "Featured", sh_top_sellers: "Top sellers", sh_specials: "Specials", sh_new_releases: "New releases", sh_coming_soon: "Coming soon", back: "Back", launching: "Starting \"%s\"…", busy: "Starting", launch_fail: "Could not start \"%s\": %s" },
  };
  let lang = q.get("lang") || (() => { try { return localStorage.getItem("darksham.lang"); } catch (e) { return null; } })() || "ar";
  if (!T[lang]) lang = "ar";
  const t = (k, ...a) => (T[lang][k] || k).replace(/%[sd]/g, () => a.shift());
  const rtl = () => lang === "ar";

  const ICON = {
    pad: '<svg viewBox="0 0 24 24"><path d="M7 7h10a5 5 0 0 1 4.8 6.3l-.9 3.3a2.6 2.6 0 0 1-4.4 1l-1.8-2.1H9.3l-1.8 2.1a2.6 2.6 0 0 1-4.4-1l-.9-3.3A5 5 0 0 1 7 7z"/><path d="M8 10v3M6.5 11.5h3"/></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    cal: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
  };

  // ------------------------------------------------------------------ data
  const TABS = ["games", "store", "profile", "apps"];
  let library = [];        // installed games: from the backend (http) or from library.js (file://)
  let games = [];          // the list shown in the card row: the library, or one store shelf
  let idx = 0;
  const API = location.protocol.startsWith("http");
  const TOKEN = (window.DARKSHAM && window.DARKSHAM.token) || "";
  let tab = TABS.indexOf(q.get("tab") || "games");
  if (tab < 0) tab = clamp(parseInt(q.get("tab"), 10) || 0, 0, TABS.length - 1);
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
  const cards = [];
  function buildCards() {
    games.forEach((g, i) => {
    const c = el("div", "card");
    c.innerHTML = '<div class="glow"></div><div class="art"><img alt="" draggable="false"><div class="name"></div></div><div class="shine"></div><div class="ring"></div>';
    const img = $("img", c);
    img.onerror = () => { const fb = g.header || g.capsule; if (fb && !img.dataset.fb) { img.dataset.fb = "1"; img.src = "/store-img?u=" + encodeURIComponent(fb); } };
    if (g.source === "store") img.onload = () => storeColours(g, img);
    const artSrc = g.cover || g.hero || g.capsule || g.header;
    if (artSrc) img.src = artSrc; else img.style.display = "none";
    $(".name", c).textContent = g.cover ? "" : g.title;
    if (g.source === "store") $(".art", c).insertAdjacentHTML("afterend", cardTag(g));
    c.addEventListener("click", () => { if (tab > 1) return; if (i === idx) launch(); else select(i); });
    rowEl.appendChild(c);
    cards.push({ el: c, intro: new Spring(STATIC ? 1 : 0, 120, 14), delay: 0.45 + i * 0.08, f: 0 });
    });
  }

  async function loadLibrary() {
    if (API) {
      try { const r = await fetch("/api/library", { cache: "no-store" }); if (r.ok) return (await r.json()).games || []; } catch (e) { /* fall through */ }
    }
    return new Promise((resolve) => {
      const sc = document.createElement("script"); sc.src = "library.js";
      sc.onload = () => resolve((window.LIBRARY && window.LIBRARY.games) || []); sc.onerror = () => resolve([]);
      document.head.appendChild(sc);
    });
  }

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
    const set = (imgs, src, zoomFrom, fb) => {
      const n = imgs[nextIdx], o = imgs[front];
      if (!src) { // no art for this game: fade the old picture out and leave the coloured glow
        n.getAnimations().forEach((a) => a.cancel()); o.getAnimations().forEach((a) => a.cancel());
        n.removeAttribute("src"); n.dataset.src = ""; n.style.opacity = 0;
        o.animate([{ opacity: parseFloat(getComputedStyle(o).opacity) || 0 }, { opacity: 0 }], { duration: instant ? 0 : 500, fill: "forwards" });
        return;
      }
      const same = n.dataset.src === src;
      n.dataset.src = src;
      if (!same) n.src = src;
      const go = () => {
        if (instant) { n.getAnimations().forEach((a) => a.cancel()); o.getAnimations().forEach((a) => a.cancel()); n.style.opacity = 1; o.style.opacity = 0; return; }
        n.getAnimations().forEach((a) => a.cancel());
        n.animate([{ opacity: 0, transform: `scale(${zoomFrom})`, filter: "blur(14px)" }, { opacity: 1, transform: "scale(1)", filter: "blur(0px)" }], { duration: 1400, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" });
        o.getAnimations().forEach((a) => a.cancel());
        o.animate([{ opacity: parseFloat(getComputedStyle(o).opacity) || 1 }, { opacity: 0 }], { duration: 900, fill: "forwards" });
      };
      let triedFb = false;
      n.onload = go;
      n.onerror = () => { if (fb && !triedFb && n.dataset.src !== fb) { triedFb = true; n.dataset.src = fb; n.src = fb; } else go(); };
      if (same && n.complete && n.naturalWidth) go();
    };
    set(heroImgs, g.source === "lutris" ? "" : g.hero || g.cover, 1.09, g.capsule || g.header);
    set(fillImgs, g.blur || g.hero || g.cover, 1.04, g.capsule || g.header);
    front = nextIdx;
  }

  const logo = $("#logo"), title = $("#title"), chips = $("#chips");
  function lastText(ts) {
    if (!ts) return t("never");
    const days = Math.floor((Date.now() / 1000 - ts) / 86400);
    return days <= 0 ? t("today") : days === 1 ? t("yesterday") : t("days", days);
  }
  function chip(icon, text, cls) { const c = el("span", "chip " + (cls || ""), (icon || "") + "<span></span>"); $("span", c).textContent = text; return c; }

  function applyColors(g, snap) {
    const root = document.documentElement.style;
    root.setProperty("--accent", g.accent); root.setProperty("--deep", g.dark);
    FX.setColors(g.accent, g.dark); if (snap) FX.snap();
  }
  // Store art comes from our own origin (the backend proxies it), so the canvas can read it: pick the most vivid colour.
  function storeColours(g, img) {
    if (g.coloured || !img.naturalWidth) return;
    try {
      const c = document.createElement("canvas"); c.width = c.height = 32;
      const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(img, 0, 0, 32, 32);
      const d = x.getImageData(0, 0, 32, 32).data; let best = -1, rgb = [138, 184, 255];
      for (let i = 0; i < d.length; i += 4) {
        const r = d[i] / 255, gg = d[i + 1] / 255, b = d[i + 2] / 255, mx = Math.max(r, gg, b), mn = Math.min(r, gg, b);
        const sat = mx ? (mx - mn) / mx : 0, sc = sat * mx * (mx > .25 && mx < .95 ? 1 : .4);
        if (sc > best) { best = sc; rgb = [d[i], d[i + 1], d[i + 2]]; }
      }
      const toHex = (a) => "#" + a.map((v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, "0")).join("");
      const mx = Math.max(...rgb) || 1, k = 205 / mx;   // brighten to a usable accent, and take a deep shade for the dark colour
      g.accent = toHex(rgb.map((v) => v * Math.max(1, k))); g.dark = toHex(rgb.map((v) => v * 0.16));
      g.coloured = true;
      if (games[idx] === g) applyColors(g, false);
    } catch (e) { /* canvas blocked: keep the default accent */ }
  }
  function money(cents, cur) {
    try { return new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD", currencyDisplay: "narrowSymbol" }).format(cents / 100); } catch (e) { return (cents / 100).toFixed(2); }
  }
  function priceBits(g) {
    const p = g.price;
    if (!p || p.final == null) return { text: t("soon"), off: 0, was: "" };
    if (p.final === 0) return { text: t("free"), off: 0, was: "" };
    return { text: money(p.final, p.currency), off: p.discount || 0, was: p.discount ? money(p.original, p.currency) : "" };
  }
  function cardTag(g) {
    const b = priceBits(g);
    return '<div class="tag">' + (b.off ? "<span class='off' dir='ltr'>-" + b.off + "%</span>" : "") + "<span dir='ltr'>" + b.text + "</span></div>";
  }
  function setLogo(g) {
    logo.onerror = () => { logo.style.display = "none"; title.style.display = ""; };
    logo.onload = () => { logo.style.display = ""; title.style.display = "none"; };
    title.textContent = g.title; logo.alt = g.title;
    if (g.logo) { logo.style.display = ""; title.style.display = "none"; logo.src = g.logo; } else { logo.style.display = "none"; title.style.display = ""; }
  }

  function showGame(g, instant) {
    applyColors(g, instant);
    setBackdrop(g, instant);
    setLogo(g);
    $("#info").classList.toggle("store", g.source === "store");
    if (g.source === "store") {
      const b = priceBits(g), owned = library.some((l) => l.appid === String(g.appid));
      const det = g.det && g.det[lang];
      const list = [chip(ICON.pad, "Steam", "src")];
      const pc = chip(null, ""); pc.className = "chip" + (b.off ? " deal" : ""); pc.innerHTML = '<span dir="ltr"></span>';
      $("span", pc).textContent = (b.off ? "-" + b.off + "%  " : "") + b.text;
      if (b.was) { const sEl = document.createElement("s"); sEl.dir = "ltr"; sEl.textContent = b.was; pc.appendChild(sEl); }
      list.push(pc);
      if (owned) list.push(chip(null, t("in_library"), "ok"));
      if (det) {
        if (det.arabic) list.push(chip(null, t("arabic_yes"), "ok"));
      }
      chips.replaceChildren(...list);
      if (!det) wantDetails(g);
    } else {
      const srcName = { steam: "Steam", lutris: "Lutris" }[g.source] || "Darksham";
      const runner = g.runner ? { wine: "Wine", linux: "Linux", dosbox: "DOSBox", libretro: "RetroArch" }[g.runner] || g.runner : "";
      chips.replaceChildren(
        chip(ICON.pad, srcName, "src"),
        ...(runner ? [chip(null, runner)] : []),
        chip(ICON.clock, `${String(g.hours).replace(/\.0$/, "")} ${t("hours")}`),
        chip(ICON.cal, `${t("last")}: ${lastText(g.last_played)}`));
      // store details exist for Steam games only
      $("#more").style.display = g.source === "steam" ? "" : "none";
    }
    if (instant) return;
    const ease = "cubic-bezier(.16,1,.3,1)";
    const blocks = [$(".logo-wrap"), ...chips.children, $(".actions")];
    blocks.forEach((bl, i) => {
      bl.getAnimations().forEach((an) => an.cancel());
      bl.animate([{ opacity: 0, transform: "translateY(26px)", filter: "blur(10px)" }, { opacity: 1, transform: "none", filter: "blur(0)" }],
        { duration: 700, delay: i * 55, easing: ease, fill: "backwards" });
    });
  }

  // ------------------------------------------------------------------ store (Steam as a temporary source)
  const store = { loaded: false, lang: "", loading: false, error: false, shelves: [], shelf: 0, idx: {} };
  function mapStoreItem(x) {
    const id = x.appid;
    return { id: "store:" + id, appid: id, title: x.name, source: "store", hours: 0, last_played: 0, accent: "#8ab8ff", dark: "#0b1020",
      cover: `/store-art/${id}/cover`, hero: `/store-art/${id}/hero`, logo: `/store-art/${id}/logo`, header: x.header, capsule: x.capsule,
      price: { final: x.final, original: x.original, discount: x.discount, currency: x.currency }, det: {} };
  }
  function useList(items, i, animate) {
    rowEl.replaceChildren(); cards.length = 0;
    games = items; idx = clamp(i || 0, 0, Math.max(0, items.length - 1)); row.x = row.to = idx;
    $("#info").style.visibility = items.length ? "" : "hidden";
    buildCards();
    if (animate && !STATIC) cards.forEach((c, k) => { c.intro.x = 0; c.intro.v = 0; c.intro.to = 0; setTimeout(() => (c.intro.to = 1), 120 + k * 70); });
    else cards.forEach((c) => { c.intro.x = c.intro.to = 1; c.intro.v = 0; });
    if (games.length) showGame(games[idx], !animate);
  }
  function storeMsg(text, err) {
    const m = $("#store-msg"); m.classList.toggle("on", !!text); m.classList.toggle("err", !!err); $("#store-msg-text").textContent = text || ""; $("#store-retry").textContent = t("retry");
  }
  function buildShelves() {
    const box = $("#shelves"); box.replaceChildren();
    store.shelves.forEach((sh, i) => { const b = el("button", i === store.shelf ? "on" : ""); b.textContent = t("sh_" + sh.id); b.addEventListener("click", () => setShelf(i)); box.appendChild(b); });
    $("#store-note").innerHTML = t("store_note");
  }
  function setShelf(i) {
    if (!store.shelves.length) return;
    i = (i + store.shelves.length) % store.shelves.length;
    store.idx[store.shelf] = idx; store.shelf = i; sfx.tab(); rumble(14, 0.05, 0.2);
    [...$("#shelves").children].forEach((b, k) => b.classList.toggle("on", k === i));
    useList(store.shelves[i].items, store.idx[i] || 0, true);
  }
  async function loadStore() {
    if (!API) { store.error = true; return; }
    store.loading = true; store.error = false; storeMsg(t("loading"), false);
    try {
      const r = await fetch("/api/store/home?lang=" + lang, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      store.shelves = (j.shelves || []).map((sh) => ({ id: sh.id, items: sh.items.map(mapStoreItem) }));
      store.lang = lang; store.loaded = true; store.shelf = 0; store.idx = {};
    } catch (e) { store.error = true; }
    store.loading = false;
  }
  async function enterStore(animate) {
    if (tab !== 1) return;
    $("#shelves").classList.add("on"); $("#store-note").classList.add("on");
    if (!store.loaded || store.lang !== lang) {
      useList([], 0); storeMsg(t("loading"), false);
      await loadStore();
      if (tab !== 1) return;
    }
    if (store.error || !store.shelves.length) { storeMsg(API ? t("store_fail") : t("demo", t("store")), true); useList([], 0); return; }
    storeMsg("");
    if (!store.devApplied) { store.devApplied = true; store.shelf = clamp(parseInt(q.get("shelf") || "0", 10) || 0, 0, store.shelves.length - 1); if (q.has("sel")) store.idx[store.shelf] = parseInt(q.get("sel"), 10) || 0; if (q.has("detail")) setTimeout(openDetail, 1200); }
    buildShelves();
    useList(store.shelves[store.shelf].items, store.idx[store.shelf] || 0, animate !== false);
  }
  function leaveStore() {
    $("#shelves").classList.remove("on"); $("#store-note").classList.remove("on"); storeMsg("");
    $("#info").classList.remove("store");
    useList(library, store.libIdx || 0, false);
  }
  $("#store-retry").addEventListener("click", () => { store.loaded = false; enterStore(true); });

  // details are fetched when a store item is selected (debounced), then reused
  let detTimer = 0;
  function wantDetails(g) { clearTimeout(detTimer); detTimer = setTimeout(() => getDetails(g).then(() => { if (games[idx] === g && tab === 1 && !detailOpen) showGame(g, true); }), 350); }
  async function getDetails(g) {
    if (g.det[lang]) return g.det[lang];
    try { const r = await fetch(`/api/store/app/${g.appid}?lang=${lang}`); if (r.ok) g.det[lang] = await r.json(); } catch (e) { /* offline */ }
    return g.det[lang];
  }

  // ---- details sheet
  let detailOpen = false, shotTimer = 0, shotI = 0, shotFront = 0, shotList = [];
  const shotImgs = [$("#shot-a"), $("#shot-b")];
  function showShot(i, instant) {
    if (!shotList.length) { shotImgs.forEach((im) => im.classList.remove("on")); return; }
    shotI = (i + shotList.length) % shotList.length;
    const n = shotImgs[1 - shotFront], o = shotImgs[shotFront];
    n.onload = () => { n.classList.add("on"); o.classList.remove("on"); shotFront = 1 - shotFront; };
    n.src = "/store-img?u=" + encodeURIComponent(shotList[shotI]);
    [...$("#shot-thumbs").children].forEach((d, k) => d.classList.toggle("on", k === shotI));
  }
  async function openDetail() {
    const g = games[idx]; if (!g || (g.source !== "store" && g.source !== "steam")) return;
    g.det = g.det || {};
    const isStore = g.source === "store";
    detailOpen = true; sfx.ok(); rumble(30, 0.15, 0.3);
    $("#detail").classList.add("on");
    $("#d-title").textContent = g.title; $("#d-open-label").textContent = isStore ? t("open_steam") : t("play"); $("#d-open-key").textContent = key("accept");
    if (isStore) {
      const b = priceBits(g);
      $("#d-price").innerHTML = '<span dir="ltr">' + (b.off ? `<em>-${b.off}%</em>` : "") + (b.was ? `<s>${b.was}</s>` : "") + b.text + "</span>";
    } else {  // an installed game: how long you played instead of a price
      $("#d-price").innerHTML = '<span class="h"></span><span class="l"></span>';
      $("#d-price .h").textContent = hoursText(g.hours); $("#d-price .l").textContent = `${t("last")}: ${lastText(g.last_played)}`;
    }
    $("#d-desc").textContent = ""; $("#d-facts").replaceChildren(); $("#d-chips").replaceChildren(); $("#shot-thumbs").replaceChildren();
    shotList = []; shotImgs.forEach((im) => im.classList.remove("on"));
    shotImgs[shotFront].src = (isStore ? g.capsule || g.header : g.hero || g.cover) || ""; shotImgs[shotFront].onload = () => shotImgs[shotFront].classList.add("on");
    const det = await getDetails(g);
    if (!detailOpen || games[idx] !== g) return;
    if (!det) { $("#d-desc").textContent = t("no_details"); return; }
    $("#d-desc").textContent = det.description || "";
    const chipsEl = $("#d-chips"); chipsEl.replaceChildren(...det.genres.map((x) => chip(null, x)), ...(det.arabic ? [chip(null, t("arabic_yes"), "ok")] : []));
    const facts = [[t("developer"), det.developers.join(", ")], [t("publisher"), det.publishers.join(", ")], [t("release"), det.release], [t("platforms"), [det.windows && "Windows", det.linux && "Linux"].filter(Boolean).join(" · ")]].filter((f) => f[1]);
    $("#d-facts").replaceChildren(...facts.flatMap(([k, v]) => { const dt = el("dt"); dt.textContent = k; const dd = el("dd"); dd.textContent = v; return [dt, dd]; }));
    shotList = det.screenshots || [];
    $("#shot-thumbs").replaceChildren(...(det.thumbs || shotList).slice(0, shotList.length).map((u, k) => { const im = el("img"); im.src = "/store-img?u=" + encodeURIComponent(u); im.alt = ""; im.addEventListener("click", () => { showShot(k); clearInterval(shotTimer); shotTimer = setInterval(() => showShot(shotI + 1), 4200); }); return im; }));
    shotFront = 0; showShot(0);
    clearInterval(shotTimer); shotTimer = setInterval(() => showShot(shotI + 1), 4200);
  }
  function closeDetail() { if (!detailOpen) return; detailOpen = false; clearInterval(shotTimer); $("#detail").classList.remove("on"); sfx.tab(); }
  // the sheet's big button: buy (store item: hand the page to Steam) or play (installed game)
  function detailPrimary() {
    const g = games[idx]; if (!g) return;
    if (g.source === "store") openInSteam(); else { closeDetail(); launch(); }
  }
  async function openInSteam() {
    const g = games[idx]; if (!g || !API || !TOKEN) { showToast(t("demo", g ? g.title : "")); return; }
    try {
      const r = await fetch("/api/store/open", { method: "POST", headers: { "Content-Type": "application/json", "X-Darksham-Token": TOKEN }, body: JSON.stringify({ appid: String(g.appid) }) });
      const j = await r.json().catch(() => ({}));
      showToast(j.ok ? t("opened_steam", g.title) : t("launch_fail", g.title, j.message || j.error || r.status));
    } catch (e) { showToast(t("launch_fail", g.title, String(e))); }
    sfx.ok();
  }
  $("#d-open").addEventListener("click", detailPrimary);
  $("#more").addEventListener("click", openDetail);
  $("#d-close").addEventListener("click", closeDetail);
  $("#detail").addEventListener("click", (e) => { if (e.target.id === "detail") closeDetail(); });

  // ------------------------------------------------------------------ tabs, pages, hints
  const tabsEl = $("#tabs"), pill = $(".pill", tabsEl);
  const tabBtns = [...tabsEl.querySelectorAll("button")];
  tabBtns.forEach((b, i) => b.addEventListener("click", () => setTab(i)));
  let pillPlaced = false;
  function placePill() { const b = tabBtns[tab]; if (!pillPlaced) { pill.style.transition = "none"; requestAnimationFrame(() => (pill.style.transition = "")); pillPlaced = true; } pill.style.left = b.offsetLeft + "px"; pill.style.width = b.offsetWidth + "px"; tabBtns.forEach((x, i) => x.classList.toggle("on", i === tab)); }

  const hoursText = (h) => `${String(h).replace(/\.0$/, "")} ${t("hours")}`;
  function buildProfile() {
    $("#p-name").textContent = t("player");
    const total = library.reduce((sum, g) => sum + g.hours, 0);
    $("#p-sub").textContent = `${library.length} ${t("stat_games")} · ${Math.round(total)} ${t("hours")}`;
    const stats = $("#p-tiles"); stats.replaceChildren();
    [[library.length, t("stat_games")], [Math.round(total), t("stat_hours")]].forEach(([n, label]) => {
      const st = el("div", "stat", "<b></b><span></span>"); $("span", st).textContent = label; $("b", st).dataset.n = n; $("b", st).textContent = n; stats.appendChild(st);
    });
    const bars = $("#p-bars"); bars.replaceChildren();
    const max = Math.max(1, ...library.map((g) => g.hours));
    library.slice(0, 5).forEach((g) => {
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
    closeDetail();
    const was = tab; tab = (i + TABS.length) % TABS.length; sfx.tab(); rumble(18, 0.05, 0.2);
    if (was === 0) store.libIdx = idx;
    if (was === 1 && tab !== 1) leaveStore();
    applyTab(true);
    if (tab === 1) enterStore(true);
  }
  function applyTab(animate) {
    placePill();
    const cardsTab = tab <= 1;
    $("#row").style.display = cardsTab ? "" : "none";
    $("#info").style.display = cardsTab ? "" : "none";
    $("#page-profile").classList.toggle("on", tab === 2);
    $("#page-apps").classList.toggle("on", tab === 3);
    $("#play-label").textContent = tab === 1 ? t("details") : t("play");
    buildHints();
    if (tab === 2) { buildProfile(); if (animate) animateProfile(); }
    if (tab === 3 && animate) $("#page-apps").animate([{ opacity: 0, transform: "translateY(24px)" }, { opacity: 1, transform: "none" }], { duration: 600, easing: "cubic-bezier(.16,1,.3,1)" });
    if (cardsTab && animate) { $("#info").animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500 }); }
  }

  function key(what) {
    return { accept: pad ? "A" : "Enter", tabs: pad ? "LB / RB" : "Q / E", lang: pad ? "Y" : "F2", move: pad ? "D-pad" : "← →", shelf: pad ? "D-pad ↑↓" : "↑ ↓", details: pad ? "X" : "↑", back: pad ? "B" : "Esc" }[what];
  }
  function buildHints() {
    const items = [["move", t("move")], ["accept", tab === 1 ? t("details") : t("play")], ["tabs", t("tabs")], ["lang", t("lang")]];
    if (tab === 1) items.splice(1, 0, ["shelf", t("shelf")]);
    if (tab === 0) items.splice(2, 0, ["details", t("details")]);
    $("#hints").replaceChildren(...items.map(([k, label]) => {
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
    tabBtns.forEach((b) => (b.textContent = t(b.dataset.tab))); $("#play-label").textContent = tab === 1 ? t("details") : t("play");
    $("#a-title").textContent = t("soon"); $("#a-sub").textContent = t("apps_sub");
    buildHints(); if (games.length) showGame(games[idx], true); if (tab === 2) buildProfile();
    if (tab === 1 && store.loaded && store.lang !== lang) { closeDetail(); enterStore(false); }
    else if (tab === 1 && store.loaded) buildShelves();
    requestAnimationFrame(placePill);
  }

  // ------------------------------------------------------------------ actions
  function select(i) {
    i = clamp(i, 0, games.length - 1);
    if (i === idx) { sfx.edge(); rumble(30, 0.2, 0.1); return; }
    idx = i; row.to = i; sfx.move(); rumble(); showGame(games[idx], false);
  }
  function move(screenDir) { if (tab > 1 || detailOpen || !games.length) return; select(idx + (rtl() ? -screenDir : screenDir)); }

  const toast = $("#toast"); let toastTimer = 0;
  function showToast(text) { toast.textContent = text; toast.classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove("on"), 2600); }
  let busy = false;
  function setBusy(on) { busy = on; $("#play").classList.toggle("busy", on); $("#play-label").textContent = on ? t("busy") : t("play"); }
  async function launch() {
    if (detailOpen) { detailPrimary(); return; }
    if (tab === 1) { if (games.length) openDetail(); return; }
    if (tab !== 0 || !games.length || busy) return;
    const g = games[idx]; sfx.ok(); rumble(60, 0.3, 0.5);
    const p = $("#play"); p.classList.add("press"); setTimeout(() => p.classList.remove("press"), 160);
    if (!API || !TOKEN) { showToast(t("demo", g.title)); return; }   // opened from disk: no backend, nothing to start
    setBusy(true);
    try {
      const r = await fetch("/api/launch", { method: "POST", headers: { "Content-Type": "application/json", "X-Darksham-Token": TOKEN }, body: JSON.stringify({ id: g.id }) });
      const j = await r.json().catch(() => ({}));
      showToast(j.ok ? t("launching", g.title) : t("launch_fail", g.title, j.message || j.error || r.status));
    } catch (e) { showToast(t("launch_fail", g.title, String(e))); }
    setTimeout(() => setBusy(false), 6000);
  }
  $("#play").addEventListener("click", launch);
  $("#fav").addEventListener("click", (e) => e.currentTarget.classList.toggle("on"));
  function toggleLang() {
    lang = rtl() ? "en" : "ar"; applyLang(); sfx.tab();
    try { localStorage.setItem("darksham.lang", lang); } catch (e) { /* no storage: the choice just is not remembered */ }
  }

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
    if (detailOpen) {
      if (k === "Escape" || k === "Backspace") closeDetail();
      else if (k === "Enter" || k === " ") detailPrimary();
      else if (k === "ArrowRight") showShot(shotI + (rtl() ? -1 : 1)); else if (k === "ArrowLeft") showShot(shotI + (rtl() ? 1 : -1));
      return;
    }
    if (tab === 0 && k === "ArrowUp") { e.preventDefault(); openDetail(); return; }
    if (tab === 1 && (k === "ArrowDown" || k === "ArrowUp")) { e.preventDefault(); setShelf(store.shelf + (k === "ArrowDown" ? 1 : -1)); return; }
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
    edge(0, launch); edge(1, closeDetail); edge(5, () => setTab(tab + 1)); edge(4, () => setTab(tab - 1)); edge(3, toggleLang); edge(2, () => { if (tab <= 1 && !detailOpen) openDetail(); });
    const ay = gp.axes[1] || 0, down = gp.buttons[13]?.pressed || ay > 0.6, up = gp.buttons[12]?.pressed || ay < -0.6;
    if (tab === 1 && !detailOpen) { repeat("d", down, now, () => setShelf(store.shelf + 1)); repeat("u", up, now, () => setShelf(store.shelf - 1)); }
  }

  // ------------------------------------------------------------------ loop + start
  let last = performance.now(), clock = 0;
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now; clock += dt;
    const time = STATIC ? 3 : clock;
    if (tab <= 1) layoutCards(time, dt);
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
    if (q.has("busy")) setBusy(true); // dev: show the launching state
    if (q.has("detail") && tab === 0) setTimeout(openDetail, 1200); // dev: open the details of the selected installed game
    if (q.has("goto")) setTimeout(() => setTab(parseInt(q.get("goto"), 10) || 0), parseInt(q.get("at") || "4000", 10)); // dev: switch tab after a delay
    if (q.has("auto")) setTimeout(() => move(parseInt(q.get("auto"), 10) || 1), 500); // dev: simulate a key press
    requestAnimationFrame((n) => { last = n; frame(n); });
  }
  Promise.all([document.fonts && document.fonts.ready, loadLibrary()]).then(([, list]) => {
    library = list; games = library;
    idx = clamp(parseInt(q.get("select") || "0", 10) || 0, 0, Math.max(0, games.length - 1));
    row.x = row.to = idx;
    buildCards();
    begin();
    if (tab === 1) enterStore(false);
  });
})();
