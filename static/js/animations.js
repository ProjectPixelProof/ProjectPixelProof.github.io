/* Animation browser: one light index (data/animations.json), one live player at a time.
 *
 * State lives in the URL hash (#world=019&page=2&profile=tracing&agent=Luna&q=maze&set=featured),
 * so every view is a shareable static link. A world's frames are fetched only when it is played;
 * card thumbnails are small WebPs, PAGE_SIZE per page, loaded lazily.
 */
(() => {
  "use strict";
  const PAGE_SIZE = 12;
  const $ = (id) => document.getElementById(id);
  const grid = $("anim-grid"), pages = $("anim-pages"), count = $("anim-count"), empty = $("anim-empty");
  const search = $("anim-search"), collection = $("anim-collection"), profileSel = $("anim-profile"), agentSel = $("anim-agent");
  const rail = $("anim-rail"), railCount = $("anim-rail-count");
  const viewer = $("viewer"), playerRoot = $("player"), strip = $("strip"), links = $("world-links"), position = $("viewer-position");
  let worlds = [], byKey = {}, order = [], filtered = [], current = null, player = null, mountToken = 0;

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  function readHash(hash = location.hash) {
    const p = new URLSearchParams(hash.slice(1));
    return {
      world: p.get("world") || "", page: Math.max(1, parseInt(p.get("page") || "1", 10) || 1),
      profile: p.get("profile") || "", agent: p.get("agent") || "", q: p.get("q") || "", set: p.get("set") || "",
    };
  }
  function writeHash(state, replace) {
    const p = new URLSearchParams();
    if (state.world) p.set("world", state.world);
    if (state.set) p.set("set", state.set);
    if (state.profile) p.set("profile", state.profile);
    if (state.agent) p.set("agent", state.agent);
    if (state.q) p.set("q", state.q);
    if (state.page > 1) p.set("page", state.page);
    const h = "#" + p.toString();
    if (h === location.hash || (h === "#" && !location.hash)) return;
    history[replace ? "replaceState" : "pushState"](null, "", h === "#" ? location.pathname : h);
  }
  function state() {
    return {
      world: current ? current.key : "", page: currentPage, profile: profileSel.value, agent: agentSel.value,
      q: search.value.trim(), set: collection.value,
    };
  }
  let currentPage = 1;

  /* ---------- browsing ---------- */
  function applyFilters() {
    const q = search.value.trim().toLowerCase(), set = collection.value, prof = profileSel.value, agent = agentSel.value;
    filtered = order.filter((w) => {
      if (set === "featured" && !w.showcase) return false;
      if (set === "held" && !w.holdBack) return false;
      if (prof && w.profile !== prof) return false;
      if (agent && w.generator !== agent) return false;
      if (q) {
        const text = [w.headline, w.title, w.question, w.profileLabel, w.generator, w.final, ...w.steps].join(" ").toLowerCase();
        if (!q.split(/\s+/).every((t) => text.includes(t))) return false;
      }
      return true;
    });
  }
  function card(w) {
    const playing = current && current.key === w.key;
    const badge = w.holdBack ? '<span class="anim-badge held">Held back</span>' : "";
    return `<li><a class="anim-card${playing ? " is-playing" : ""}" href="#world=${w.key}" data-key="${w.key}"${playing ? ' aria-current="true"' : ""}>
      <span class="anim-thumb"><img src="static/animations/${w.key}/thumb.webp" alt="" loading="lazy" decoding="async" width="180" height="${Math.round(180 * w.size[1] / w.size[0])}">${badge}${playing ? '<span class="anim-now">Now playing</span>' : ""}</span>
      <span class="anim-card-body"><strong>${esc(w.headline)}</strong><small>${esc(w.title)}</small>
      <span class="anim-meta">${esc(w.profileLabel)} · ${esc(w.generator)}</span>
      <span class="anim-flow"><i class="s">${w.calls} drawing call${w.calls === 1 ? "" : "s"}</i><i class="p">${w.steps.length + 1} inverse step${w.steps.length ? "s" : ""}</i></span></span></a></li>`;
  }
  function renderGrid() {
    const n = filtered.length, last = Math.max(1, Math.ceil(n / PAGE_SIZE));
    currentPage = Math.min(currentPage, last);
    const from = (currentPage - 1) * PAGE_SIZE, slice = filtered.slice(from, from + PAGE_SIZE);
    grid.innerHTML = slice.map(card).join("");
    empty.hidden = n > 0;
    count.textContent = n ? `Showing ${from + 1}–${from + slice.length} of ${n} world${n === 1 ? "" : "s"}` : "No worlds";
    if (last <= 1) { pages.innerHTML = ""; return; }
    const btn = (p, label, aria, dis) =>
      `<button type="button" data-page="${p}"${dis ? " disabled" : ""}${p === currentPage && !aria ? ' aria-current="page"' : ""} aria-label="${aria || "Page " + p}">${label}</button>`;
    let html = btn(currentPage - 1, "← Previous", "Previous page", currentPage === 1);
    for (let p = 1; p <= last; p++) {
      if (p === 1 || p === last || Math.abs(p - currentPage) <= 1) html += btn(p, p);
      else if (Math.abs(p - currentPage) === 2) html += '<span aria-hidden="true">…</span>';
    }
    html += btn(currentPage + 1, "Next →", "Next page", currentPage === last);
    pages.innerHTML = html;
  }
  /* The rail above the player always lists every world, so the others are visible without scrolling. */
  function renderRail() {
    if (!rail) return;
    rail.innerHTML = order.map((w) => {
      const on = current && current.key === w.key;
      return `<li><a class="anim-rail-item${on ? " is-playing" : ""}" href="#world=${w.key}" data-key="${w.key}" title="${esc(w.headline)}"${on ? ' aria-current="true"' : ""}>
        <img src="static/animations/${w.key}/thumb.webp" alt="" decoding="async" width="96" height="96"><span>${esc(w.headline)}</span></a></li>`;
    }).join("");
    if (railCount) railCount.textContent = `${order.length} worlds`;
    const on = rail.querySelector(".is-playing");
    if (on && rail.scrollWidth > rail.clientWidth) rail.scrollLeft = on.parentElement.offsetLeft - (rail.clientWidth - on.offsetWidth) / 2;
  }
  function refresh(resetPage) {
    if (resetPage) currentPage = 1;
    applyFilters();
    renderGrid();
    writeHash(state(), true);
  }

  /* ---------- viewer ---------- */
  function neighbours() {
    const list = filtered.length && filtered.some((w) => current && w.key === current.key) ? filtered : order;
    const i = list.findIndex((w) => current && w.key === current.key);
    return { list, i, prev: list[(i - 1 + list.length) % list.length], next: list[(i + 1) % list.length] };
  }
  function stripItem(cls, label, inner, data) {
    return `<button type="button" class="anim-step ${cls}" ${data}><span class="anim-step-pic">${inner}</span><span class="anim-step-lab">${label}</span></button>`;
  }
  function buildStrip(w, m) {
    const base = `static/animations/${w.key}/`;
    const pic = (overlay) => `<img src="${base}final.webp" alt="" loading="lazy">` + (overlay ? `<img src="${base}${overlay}" alt="" loading="lazy">` : "");
    let html = stripItem("scene", "<b>1</b> Scene and forward answer", `<span class="anim-step-txt">${esc(m.forward.answer)}</span>`, 'data-phase="scene"');
    html += stripItem("render", `<b>2</b> Renderer · ${m.render.events} call${m.render.events === 1 ? "" : "s"}`,
      `<img src="${base}${m.render.frames[Math.floor(m.render.frames.length / 2)].src}" alt="" loading="lazy">`, 'data-phase="render"');
    m.inverse.beats.forEach((b, j) => {
      const inner = b.overlay ? pic(b.overlay) : `<img class="is-grid" src="${base}${b.grid}" alt="" loading="lazy">`;
      html += stripItem("inverse", `<b>3.${j + 1}</b> ${esc(b.title)}`, inner, `data-beat="${j}"`);
    });
    html += stripItem("inverse", `<b>3.${m.inverse.beats.length + 1}</b> ${esc(m.inverse.final.text || "Decide")}`,
      `<span class="anim-step-txt pixels">${esc(m.inverse.answer)}</span>`, `data-beat="${m.inverse.beats.length}"`);
    html += stripItem("check", "<b>4</b> Forward = inverse",
      `<span class="anim-step-txt ok">${esc(m.forward.answer)} = ${esc(m.inverse.answer)}</span>`, 'data-phase="check"');
    strip.innerHTML = `<p class="anim-strip-title">Steps <span>select one to jump there</span></p><div class="anim-strip-row">${html}</div>`;
  }
  function highlight(phase, beat) {
    strip.querySelectorAll(".anim-step").forEach((b) => {
      const on = b.dataset.beat != null ? phase === "inverse" && +b.dataset.beat === beat : b.dataset.phase === phase;
      b.classList.toggle("is-now", on);
      if (on) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    });
  }
  function show(key, opts = {}) {
    const w = byKey[key];
    if (!w) return;
    current = w;
    const token = ++mountToken;
    if (player) { player.destroy(); player = null; }
    playerRoot.innerHTML = '<div class="ppa-loading">Loading animation…</div>';
    strip.innerHTML = "";
    const nb = neighbours();
    position.textContent = `World ${nb.i + 1} of ${nb.list.length}` + (nb.list === filtered && filtered.length < order.length ? " (filtered)" : "");
    const src = `static/questions/${w.id}/`;
    links.innerHTML =
      `<a href="questions.html#world=${encodeURIComponent(w.id)}&amp;sample=1">Try this question ↗</a>` +
      `<a href="${src}inverse.py.txt">Inverse program source ↗</a>` +
      `<a href="${src}generator.py.txt">Scene, renderer, and forward source ↗</a>` +
      `<a href="static/animations/${w.key}/manifest.json">Recorded data (JSON) ↗</a>`;
    fetch(`static/animations/${w.key}/manifest.json`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((m) => {
        if (token !== mountToken) return;
        playerRoot.innerHTML = "";
        const s = document.createElement("script");
        s.type = "application/json";
        s.textContent = JSON.stringify(m);
        playerRoot.appendChild(s);
        playerRoot.setAttribute("data-base", `static/animations/${w.key}/`);
        buildStrip(w, m);
        return window.PPAnim.mount(playerRoot).then((p) => {
          if (token !== mountToken || !p) return;
          player = p;
          if (p.where) { const [ph, bt] = p.where.split(":"); highlight(ph, +bt); }
        });
      })
      .catch((e) => { playerRoot.innerHTML = `<div class="ppa-loading">This animation could not be loaded (${esc(e.message || e)}).</div>`; });
    renderGrid();
    renderRail();
    if (!opts.silent) writeHash(state(), opts.replace);
    if (opts.scroll) viewer.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    if (opts.focus) viewer.focus({ preventScroll: true });
  }

  playerRoot.addEventListener("ppa:position", (e) => highlight(e.detail.phase, e.detail.beat));
  strip.addEventListener("click", (e) => {
    const b = e.target.closest(".anim-step");
    if (!b || !player) return;
    if (b.dataset.beat != null) player.showBeat(+b.dataset.beat);
    else player.showPhase(b.dataset.phase);
  });
  grid.addEventListener("click", (e) => {
    const a = e.target.closest(".anim-card");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    show(a.dataset.key, { scroll: true, focus: true });
  });
  if (rail) rail.addEventListener("click", (e) => {
    const a = e.target.closest(".anim-rail-item");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    show(a.dataset.key);
  });
  pages.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-page]");
    if (!b || b.disabled) return;
    currentPage = +b.dataset.page;
    renderGrid();
    writeHash(state(), false);
    $("browse").scrollIntoView({ block: "start" });
  });
  $("prev-world").addEventListener("click", () => current && show(neighbours().prev.key));
  $("next-world").addEventListener("click", () => current && show(neighbours().next.key));
  let typing;
  search.addEventListener("input", () => { clearTimeout(typing); typing = setTimeout(() => refresh(true), 160); });
  [collection, profileSel, agentSel].forEach((s) => s.addEventListener("change", () => refresh(true)));
  $("anim-reset").addEventListener("click", () => {
    search.value = ""; collection.value = ""; profileSel.value = ""; agentSel.value = "";
    refresh(true);
  });
  // Plain section anchors (#browse, #about) are ordinary in-page links, not view state.
  const isState = () => !location.hash || location.hash.includes("=");
  window.addEventListener("popstate", () => isState() && fromHash(false));
  window.addEventListener("hashchange", () => isState() && fromHash(false));

  function fromHash(first) {
    const s = readHash(isState() ? location.hash : "");
    search.value = s.q; collection.value = s.set; profileSel.value = s.profile; agentSel.value = s.agent;
    currentPage = s.page;
    applyFilters();
    const key = byKey[s.world] ? s.world : first ? (filtered[0] || order[0]).key : current && current.key;
    if (!current || key !== current.key) show(key, { silent: true, scroll: !first && !!s.world });
    else renderGrid();
    if (first && s.world) viewer.scrollIntoView({ block: "start" });
  }

  fetch("data/animations.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((doc) => {
      worlds = doc.worlds;
      worlds.forEach((w) => { byKey[w.key] = w; });
      const rank = {};
      doc.showcase.forEach((k, i) => { rank[k] = i; });
      // Featured worlds first (in curated order), then the rest by study index, held-back worlds last.
      order = worlds.slice().sort((a, b) => {
        const ra = a.holdBack ? 2 : a.showcase ? 0 : 1, rb = b.holdBack ? 2 : b.showcase ? 0 : 1;
        if (ra !== rb) return ra - rb;
        if (ra === 0) return rank[a.key] - rank[b.key];
        return a.key.localeCompare(b.key);
      });
      const profiles = [...new Map(worlds.map((w) => [w.profile, w.profileLabel])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
      profileSel.insertAdjacentHTML("beforeend", profiles.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join(""));
      const agents = [...new Set(worlds.map((w) => w.generator))].sort();
      agentSel.insertAdjacentHTML("beforeend", agents.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join(""));
      fromHash(true);
    })
    .catch((e) => {
      playerRoot.innerHTML = `<div class="ppa-loading">The animation index could not be loaded (${esc(e.message || e)}). If you opened this file directly, serve the folder with a local web server.</div>`;
    });
})();
