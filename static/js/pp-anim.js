/* PixelProof forward/inverse animation player.
 *
 * Usage: <div class="ppa" data-src="animations/019/manifest.json"></div> + this script + pp-anim.css.
 * Every visual state is a pure function of time t (renderAt), so the same code drives the
 * page, scrubbing, and frame-exact video capture. No dependencies.
 */
(function () {
  'use strict';

  var KW = /\b(def|return|if|elif|else|for|while|in|not|and|or|is|None|True|False|lambda|import|from|as|with|raise|try|except|break|continue|yield|pass|global)\b/;
  var PROFILE = {
    'prior-conflict': 'Prior conflict', 'measurement': 'Measurement', 'tracing': 'Tracing', 'topology': 'Topology',
    'reveal-global-structure': 'Reveal global structure', 'reveal-declared-transform': 'Reveal declared transform',
    'state-tracking': 'State tracking', 'correspondence': 'Correspondence', 'search': 'Search'
  };
  var CHECK_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#12704b"/>' +
    '<path d="M7 12.4l3.2 3.2L17.2 8.6" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var PLAY = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 1.8v10.4L12 7z" fill="currentColor"/></svg>';
  var PAUSE = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2.5" y="1.8" width="3.2" height="10.4" rx="0.8" fill="currentColor"/><rect x="8.3" y="1.8" width="3.2" height="10.4" rx="0.8" fill="currentColor"/></svg>';

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* Minimal Python highlighter: strings, comments, numbers, keywords, called names. */
  function hl(code) {
    var re = /("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|#[^\n]*|\b\d+(?:\.\d+)?(?:e[-+]?\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b(?=\()|\b[A-Za-z_][A-Za-z0-9_]*\b)/g;
    var out = '', last = 0, m;
    while ((m = re.exec(code))) {
      out += esc(code.slice(last, m.index));
      var tok = m[0], cls = null;
      if (tok[0] === '"' || tok[0] === "'") cls = 's';
      else if (tok[0] === '#') cls = 'c';
      else if (/^\d/.test(tok)) cls = 'n';
      else if (KW.test(tok) && tok.match(KW)[0] === tok) cls = 'k';
      else if (code[m.index + tok.length] === '(') cls = 'f';
      out += cls ? '<span class="' + cls + '">' + esc(tok) + '</span>' : esc(tok);
      last = m.index + tok.length;
    }
    return out + esc(code.slice(last));
  }

  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function ease(x) { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); }
  /* opacity of something visible on [a, b) with fade-in fi and fade-out fo */
  function win(t, a, b, fi, fo) {
    if (t < a || t >= b + (fo || 0)) return 0;
    var up = fi ? ease((t - a) / fi) : 1;
    var down = fo ? 1 - ease((t - b) / fo) : (t < b ? 1 : 0);
    return Math.min(up, t < b ? 1 : down);
  }
  function fmt(t) { t = Math.max(0, t); var s = Math.floor(t); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  function Player(root, m, base) {
    this.root = root; this.m = m; this.base = base || '';
    this.t = 0; this.playing = false; this.userPaused = false; this.last = null; this.keys = {};
    this.rate = 1; this.where = null;
    this.plan();
    this.build();
    this.fit();
    /* Until it first plays, show a poster state (scene and forward answer) instead of a blank stage. */
    this.renderAt(this.T.scene[0] + 2.4);
    this.fresh = true;
  }

  /* Give the side panel the height of its tallest state, so nothing is clipped and nothing jumps. */
  Player.prototype.fit = function () {
    var T = this.T, side = this.panes.scene.parentNode, need = 0, self = this;
    var probes = [T.scene[0] + 2.5, T.render[0] + (T.render[1] - T.render[0]) * 0.9, T.fin[0] + 2, T.check[0] + 1];
    T.beats.forEach(function (b) { probes.push(b[0] + 1); });
    side.style.minHeight = '';
    probes.forEach(function (t) {
      self.renderAt(t);
      ['scene', 'render', 'inverse', 'check'].forEach(function (p) { need = Math.max(need, self.panes[p].scrollHeight); });
    });
    var pad = parseFloat(getComputedStyle(side).paddingTop) + parseFloat(getComputedStyle(side).paddingBottom);
    side.style.minHeight = Math.ceil(need + pad + 4) + 'px';
    this.keys = {};
  };

  Player.prototype.url = function (f) { return this.base + f; };

  Player.prototype.plan = function () {
    var m = this.m, n = m.render.frames.length, k = m.inverse.beats.length;
    var dt = clamp(6.2 / n, 0.1, 0.62);
    var T = {};
    T.scene = [0, 3.6];
    T.render = [T.scene[1], T.scene[1] + n * dt + 0.9];
    T.dt = dt;
    var inv0 = T.render[1], scan = 0.9, beat = 2.5, fin = 3.0;
    T.inverse = [inv0, inv0 + scan + k * beat + fin];
    T.scan = [inv0, inv0 + scan];
    T.beats = [];
    for (var j = 0; j < k; j++) T.beats.push([inv0 + scan + j * beat, inv0 + scan + (j + 1) * beat]);
    T.fin = [inv0 + scan + k * beat, T.inverse[1]];
    T.check = [T.inverse[1], T.inverse[1] + 3.4];
    this.T = T;
    this.duration = T.check[1];
  };

  Player.prototype.build = function () {
    var m = this.m, r = this.root, self = this;
    r.innerHTML = '';
    r.setAttribute('role', 'region');
    r.setAttribute('aria-label', 'Animation: ' + m.title);
    r.tabIndex = 0;

    var head = el('div', 'ppa-head');
    head.appendChild(el('p', 'ppa-eyebrow', '<span>' + esc(PROFILE[m.profile] || m.profile_label || m.profile) + ' profile</span>' +
      (m.generator ? '<span>Generated by <b>' + esc(m.generator) + '</b></span>' : '')));
    var tr = el('div', 'ppa-titlerow');
    tr.appendChild(el('h3', 'ppa-title', esc(m.title)));
    head.appendChild(tr);
    var q = el('p', 'ppa-q', '“' + esc(m.question) + '”');
    head.appendChild(q);
    var qt = el('button', 'ppa-qtoggle', 'Show full question');
    qt.type = 'button';
    qt.addEventListener('click', function () {
      var open = q.classList.toggle('is-open');
      qt.textContent = open ? 'Show less' : 'Show full question';
    });
    head.appendChild(qt);
    if (m.hold_back) head.appendChild(el('p', 'ppa-hold', '<b>Held back from the showcase.</b> ' + esc(m.hold_back)));
    r.appendChild(head);

    var body = el('div', 'ppa-body');
    var sw = el('div', 'ppa-stagewrap');
    var st = el('div', 'ppa-stage');
    st.style.aspectRatio = m.image.w + ' / ' + m.image.h;
    st.style.maxWidth = 'calc(540px * ' + (m.image.w / m.image.h).toFixed(4) + ')';
    this.frames = m.render.frames.map(function (f) {
      var im = el('img');
      im.src = self.url(f.src); im.alt = ''; im.decoding = 'async'; im.draggable = false;
      im.style.opacity = 0;
      st.appendChild(im);
      return im;
    });
    this.final = el('img'); this.final.src = this.url(m.image.src); this.final.alt = 'Rendered image: ' + m.title;
    st.appendChild(this.final);
    this.overlays = m.inverse.beats.map(function (b) {
      if (b.overlay) {
        var im = el('img'); im.src = self.url(b.overlay); im.alt = ''; im.style.opacity = 0; st.appendChild(im); return im;
      }
      var g = el('div', 'ppa-grid');
      g.innerHTML = '<img src="' + esc(self.url(b.grid)) + '" alt=""><span>' + esc(b.fn) + '(…) → ' + esc(b.note.split(' returned')[0]) + '</span>';
      g.style.opacity = 0; st.appendChild(g); return g;
    });
    this.marks = m.inverse.beats.map(function (b) {
      return (b.marks || []).map(function (mk) {
        var d = el('div', 'ppa-mark' + (mk.strong ? ' is-strong' : ''), esc(mk.text));
        d.style.left = (mk.x * 100) + '%'; d.style.top = (mk.y * 100) + '%'; d.style.opacity = 0;
        st.appendChild(d); return d;
      });
    });
    this.box = el('div', 'ppa-box'); this.box.style.opacity = 0; st.appendChild(this.box);
    this.scan = el('div', 'ppa-scan'); this.scan.style.opacity = 0; st.appendChild(this.scan);
    this.blank = el('div', 'ppa-layer');
    this.blank.style.background = 'repeating-linear-gradient(135deg, #fbfbfc 0 10px, #f3f4f7 10px 20px)';
    st.appendChild(this.blank);
    this.blankTxt = el('div', 'ppa-grid', '<span style="color:#b65b25">No pixels yet: the answer comes from the scene</span>');
    this.blankTxt.style.background = 'transparent';
    st.appendChild(this.blankTxt);
    sw.appendChild(st);
    this.tag = el('div', 'ppa-stagetag'); sw.appendChild(this.tag);
    body.appendChild(sw);

    var side = el('div', 'ppa-side');
    this.panes = {};
    ['scene', 'render', 'inverse', 'check'].forEach(function (p) {
      var pane = el('div', 'ppa-pane'); pane.style.opacity = 0; side.appendChild(pane); self.panes[p] = pane;
    });
    body.appendChild(side);
    r.appendChild(body);
    this.fillStatic();

    var ctrl = el('div', 'ppa-ctrl');
    this.btn = el('button', 'ppa-btn', PLAY); this.btn.type = 'button'; this.btn.setAttribute('aria-label', 'Play');
    this.btn.addEventListener('click', function () { self.toggle(true); });
    ctrl.appendChild(this.btn);
    var track = el('div', 'ppa-track');
    var T = this.T, D = this.duration;
    this.segs = [['scene', 'Scene → forward', T.scene], ['render', 'Renderer draws', T.render],
      ['inverse', 'Inverse reads pixels', T.inverse], ['check', 'Check', T.check]].map(function (s) {
      var b = el('button', 'ppa-seg ' + s[0], '<span class="bar"><b></b></span><span class="lab">' + s[1] + '</span>');
      b.type = 'button'; b.style.flex = (s[2][1] - s[2][0]) / D;
      b.setAttribute('aria-label', 'Jump to ' + s[1]);
      b.addEventListener('click', function (e) { e.preventDefault(); });
      track.appendChild(b);
      return { el: b, fill: b.querySelector('b'), span: s[2], key: s[0] };
    });
    ctrl.appendChild(track);
    /* Drag anywhere on the track to scrub; a plain click on a label still jumps to that chapter. */
    var drag = null;
    function at(e) {
      var x = e.clientX, hit = null;
      self.segs.forEach(function (s) {
        var r0 = s.el.getBoundingClientRect();
        if (x >= r0.left - 2 && x <= r0.right + 2) hit = { s: s, f: clamp((x - r0.left) / r0.width, 0, 1) };
      });
      if (!hit) {
        var first = self.segs[0].el.getBoundingClientRect();
        hit = x < first.left ? { s: self.segs[0], f: 0 } : { s: self.segs[self.segs.length - 1], f: 1 };
      }
      return hit.s.span[0] + hit.f * (hit.s.span[1] - hit.s.span[0]);
    }
    track.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      drag = { x: e.clientX, moved: false, was: self.playing };
      if (self.playing) self.pause(false);
      track.setPointerCapture(e.pointerId);
    });
    track.addEventListener('pointermove', function (e) {
      if (!drag) return;
      if (Math.abs(e.clientX - drag.x) > 3) drag.moved = true;
      if (drag.moved) { self.seek(at(e)); track.classList.add('is-scrubbing'); }
    });
    function end(e) {
      if (!drag) return;
      var d = drag; drag = null; track.classList.remove('is-scrubbing');
      if (d.moved) { e.preventDefault(); self.suppressClick = true; setTimeout(function () { self.suppressClick = false; }, 0); }
      else self.seek(at(e));
      if (d.was) self.play(); else self.userPaused = true;
    }
    track.addEventListener('pointerup', end);
    track.addEventListener('pointercancel', end);
    this.time = el('span', 'ppa-time'); ctrl.appendChild(this.time);
    this.speed = el('button', 'ppa-speed', '1×'); this.speed.type = 'button';
    this.speed.setAttribute('aria-label', 'Playback speed 1×');
    this.speed.addEventListener('click', function () {
      var rates = [1, 1.5, 0.5], i = rates.indexOf(self.rate);
      self.rate = rates[(i + 1) % rates.length];
      self.speed.textContent = self.rate + '×';
      self.speed.setAttribute('aria-label', 'Playback speed ' + self.rate + '×');
    });
    ctrl.appendChild(this.speed);
    r.appendChild(ctrl);

    var sr = el('p', null, esc(this.summary()));
    sr.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap';
    r.appendChild(sr);

    r.addEventListener('keydown', function (e) {
      if (e.target !== r) return;
      if (e.key === ' ' || e.key === 'k') { e.preventDefault(); self.toggle(true); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); self.step(1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); self.step(-1); }
    });
  };

  Player.prototype.summary = function () {
    var m = this.m;
    return 'Question: ' + m.question + ' Forward program answer from the scene specification: ' + m.forward.answer +
      (m.render.mode === 'saved' ? '. The image is a saved ' + (m.render.engine || '3D') + ' render of that scene. The inverse program reads the pixels: ' :
        '. The renderer draws the image in ' + m.render.events + ' drawing calls. The inverse program reads the pixels: ') +
      m.inverse.beats.map(function (b, i) { return (i + 1) + '. ' + b.title; }).join('; ') +
      '. Inverse answer: ' + m.inverse.answer + '. Both programs agree.';
  };

  Player.prototype.fillStatic = function () {
    var m = this.m;
    this.panes.scene.innerHTML =
      '<p class="ppa-phase scene"><i>1</i>Scene and forward program</p>' +
      '<p class="ppa-lede">A sampled scene specification. The forward program computes the answer from it, before any pixel exists.</p>' +
      '<p class="ppa-label">Scene specification</p><pre class="ppa-code scene">' + esc(m.scene) + '</pre>' +
      '<p class="ppa-label">Forward program</p><pre class="ppa-code fwd">' + hl(m.forward.code) + '</pre>' +
      '<div class="ppa-result" data-k="fres">Forward answer <span class="ppa-chip scene">' + esc(m.forward.answer) + '</span></div>';
    this.fres = this.panes.scene.querySelector('[data-k=fres]');
    this.panes.check.innerHTML =
      '<p class="ppa-phase check"><i>4</i>Self-check</p>' +
      '<p class="ppa-lede">The two programs never share code. One reads the scene, the other reads only the pixels.</p>' +
      '<div class="ppa-verdict"><div class="fw"><small>Forward</small><strong>' + esc(m.forward.answer) + '</strong></div>' +
      '<span class="eq">=</span><div class="iv"><small>Inverse</small><strong>' + esc(m.inverse.answer) + '</strong></div>' + CHECK_SVG + '</div>' +
      (m.render.mode === 'saved' ?
        '<p class="ppa-fineprint">Recorded answer: <b>' + esc(m.answer) + '</b>. The inverse program’s values above were recorded while ' +
        'its own code ran on the saved image. The scene, the forward answer and the image are the saved record; the renderer was not run again.</p>' :
        '<p class="ppa-fineprint">Recorded answer: <b>' + esc(m.answer) + '</b>. The renderer’s drawing calls and the inverse program’s ' +
        'values above were recorded while the world’s own code ran on this scene; the image is the exact one shown to models.</p>');
  };

  Player.prototype.renderPane = function (key, html) {
    if (this.keys[key] === html) return false;
    this.keys[key] = html;
    return true;
  };

  Player.prototype.renderAt = function (t) {
    t = clamp(t, 0, this.duration - 1e-6);
    this.t = t;
    var T = this.T, m = this.m, self = this;
    var phase = t < T.render[0] ? 'scene' : t < T.inverse[0] ? 'render' : t < T.check[0] ? 'inverse' : 'check';

    /* panes: crossfade 0.3s at phase boundaries */
    ['scene', 'render', 'inverse', 'check'].forEach(function (p) {
      var a = T[p][0], b = T[p][1];
      var o = win(t, a, b, p === 'scene' ? 0.35 : 0.3, 0);
      self.panes[p].style.opacity = o;
      self.panes[p].style.visibility = o > 0 ? 'visible' : 'hidden';
      self.panes[p].style.transform = 'translateY(' + ((1 - o) * 6).toFixed(2) + 'px)';
    });
    this.fres.style.opacity = ease((t - 1.7) / 0.4);

    /* stage: blank -> frames -> final + overlays */
    var blankO = phase === 'scene' ? 1 : 1 - ease((t - T.render[0]) / 0.25);
    this.blank.style.opacity = blankO;
    this.blankTxt.style.opacity = phase === 'scene' ? ease((t - 0.4) / 0.4) : 0;
    var n = this.frames.length, dt = T.dt;
    var fi = phase === 'render' ? Math.floor((t - T.render[0]) / dt) : (phase === 'scene' ? -1 : n);
    fi = Math.min(fi, n - 1);
    for (var i = 0; i < n; i++) {
      var o = 0;
      if (phase === 'render') {
        if (i < fi) o = 1;
        else if (i === fi) o = ease((t - T.render[0] - i * dt) / Math.min(0.14, dt * 0.8));
      }
      this.frames[i].style.opacity = o;
    }
    this.final.style.opacity = (phase === 'inverse' || phase === 'check') ? 1 : 0;

    /* changed-region box */
    var f = fi >= 0 && fi < n && phase === 'render' ? m.render.frames[fi] : null;
    if (f && f.box) {
      var since = t - T.render[0] - fi * dt, life = Math.max(0.42, dt * 1.6);
      var bo = since < life ? 1 - ease((since - life * 0.45) / (life * 0.55)) : 0;
      this.box.style.left = (f.box[0] * 100) + '%'; this.box.style.top = (f.box[1] * 100) + '%';
      this.box.style.width = ((f.box[2] - f.box[0]) * 100) + '%'; this.box.style.height = ((f.box[3] - f.box[1]) * 100) + '%';
      this.box.style.opacity = (f.box[2] - f.box[0] > 0.97 && f.box[3] - f.box[1] > 0.97) ? 0 : bo;
    } else this.box.style.opacity = 0;

    /* scan line */
    if (t >= T.scan[0] && t < T.scan[1]) {
      var p = (t - T.scan[0]) / (T.scan[1] - T.scan[0]);
      this.scan.style.opacity = Math.min(1, 4 * (1 - p));
      this.scan.style.top = (ease(p) * 100 - 18) + '%';
    } else this.scan.style.opacity = 0;

    /* overlays and marks */
    var B = T.beats, k = B.length;
    for (var j = 0; j < k; j++) {
      var a = B[j][0], b = B[j][1];
      var oo = win(t, a, b, 0.4, 0.35);
      this.overlays[j].style.opacity = oo;
      this.marks[j].forEach(function (d, q) {
        var mq = win(t, a + 0.45 + q * 0.12, b, 0.3, 0.3);
        d.style.opacity = mq;
        d.style.transform = 'translate(-50%, -50%) scale(' + (0.85 + 0.15 * mq).toFixed(3) + ')';
      });
    }

    /* stage tag */
    var tag = phase === 'scene' ? ['Scene specification', 'var(--ppa-scene)'] :
      phase === 'render' ? [m.render.mode === 'saved' ? 'Renderer · saved ' + (m.render.engine || '3D') + ' render' :
        'Renderer · drawing ' + Math.max(1, (f ? f.event : m.render.events)) + ' / ' + m.render.events, 'var(--ppa-scene)'] :
      phase === 'inverse' ? ['Inverse program · pixels only', 'var(--ppa-pixels)'] : [m.render.mode === 'saved' ? 'Saved render' : 'Image shown to models', 'var(--ppa-positive)'];
    if (this.renderPane('tag', tag[0])) { this.tag.textContent = tag[0]; this.tag.style.color = tag[1]; }

    /* render pane */
    if (phase === 'render') {
      var cur = Math.max(0, fi);
      var fr = m.render.frames[cur];
      var since2 = t - T.render[0] - cur * dt;
      var typed = clamp(since2 / Math.min(0.32, dt * 0.85), 0, 1);
      var list = '';
      var from = Math.max(0, cur - 4);
      for (var q = from; q <= cur; q++) {
        var c = m.render.frames[q].code;
        if (q === cur) {
          var nch = Math.round(c.length * typed);
          list += '<li class="is-now"><em>' + m.render.frames[q].line + '</em>' + hl(c.slice(0, nch)) + (typed < 1 ? '<span class="ppa-caret"></span>' : '') + '</li>';
        } else list += '<li><em>' + m.render.frames[q].line + '</em>' + esc(c) + '</li>';
      }
      var html = m.render.mode === 'saved' ?
        '<p class="ppa-phase render"><i>2</i>Renderer</p>' +
        '<p class="ppa-lede">The renderer builds the scene as 3D objects and hands them to ' + esc(m.render.engine || 'a 3D engine') +
        ', which produces the image. The saved render is shown; the renderer was not run again for this animation.</p>' +
        '<p class="ppa-label">renderer.py, line · statement</p><ul class="ppa-lines">' + list + '</ul>' :
        '<p class="ppa-phase render"><i>2</i>Renderer</p>' +
        '<p class="ppa-lede">The renderer draws the scene with ordinary drawing calls. Each step below is one recorded call; the box marks the pixels it changed.</p>' +
        '<div class="ppa-count"><strong>' + fr.event + '</strong><span>of ' + m.render.events + ' drawing calls' +
        (m.render.events > n ? ' · ' + n + ' snapshots shown' : '') + '</span></div>' +
        '<p class="ppa-label">renderer.py, line · statement</p><ul class="ppa-lines">' + list + '</ul>';
      if (this.renderPane('render', html)) this.panes.render.innerHTML = html;
    }

    /* inverse pane */
    if (phase === 'inverse') {
      var active = -1;
      for (var j2 = 0; j2 < k; j2++) if (t >= B[j2][0] && t < B[j2][1]) active = j2;
      var inFinal = t >= T.fin[0];
      var steps = m.inverse.beats.map(function (bt, j3) {
        var state = inFinal || j3 < active ? 'is-done' : j3 === active ? 'is-now' : '';
        var inner = '<b>' + esc(bt.title) + '</b>' + (state === 'is-done' ? '' : '<code>' + esc(bt.fn) + '()</code>');
        if (state === 'is-now') inner += '<pre class="ppa-code">' + hl(bt.code) + '</pre><span class="ppa-note">' + esc(bt.note) + '</span>';
        return '<li class="' + state + '"><i>' + (j3 + 1) + '</i><div>' + inner + '</div></li>';
      });
      var F = m.inverse.final;
      var fstate = inFinal ? 'is-now' : '';
      var finner = '<b>' + esc(F.text || 'Decide') + '</b>' + (inFinal ? '<code>' + esc(F.fn || 'decision_from_image') + '()</code>' : '');
      if (inFinal) {
        finner += '<pre class="ppa-code">' + hl(F.code) + '</pre>';
        if (F.values.length) finner += '<div class="ppa-vals">' + F.values.map(function (v) {
          return '<div>' + esc(v.label) + ' = <span>' + esc(v.value) + '</span></div>';
        }).join('') + '</div>';
        var showAns = t >= T.fin[0] + 1.1;
        finner += '<div class="ppa-result" style="margin-top:8px;opacity:' + (showAns ? 1 : 0) + '">Inverse answer <span class="ppa-chip pixels">' + esc(m.inverse.answer) + '</span></div>';
      }
      steps.push('<li class="' + fstate + '"><i>' + (k + 1) + '</i><div>' + finner + '</div></li>');
      var ihtml = '<p class="ppa-phase inverse"><i>3</i>Inverse program</p>' +
        '<p class="ppa-lede">A separate program sees only the finished image. Each step shows a value it actually computed.</p>' +
        '<ol class="ppa-steps">' + steps.join('') + '</ol>';
      if (this.renderPane('inverse', ihtml)) this.panes.inverse.innerHTML = ihtml;
    }

    /* controls */
    this.segs.forEach(function (s) {
      var p = clamp((t - s.span[0]) / (s.span[1] - s.span[0]), 0, 1);
      s.fill.style.width = (p * 100).toFixed(2) + '%';
      s.el.classList.toggle('is-now', s.key === phase);
    });
    var tt = fmt(t) + ' / ' + fmt(this.duration);
    if (this.renderPane('time', tt)) this.time.textContent = tt;

    /* Tell the page where we are (phase, inverse step), only when it changes. */
    var beat = -1;
    if (phase === 'inverse') { for (var j4 = 0; j4 < k; j4++) if (t >= B[j4][0] && t < B[j4][1]) beat = j4; if (t >= T.fin[0]) beat = k; }
    var where = phase + ':' + beat;
    if (where !== this.where) {
      this.where = where;
      this.root.dispatchEvent(new CustomEvent('ppa:position', { detail: { phase: phase, beat: beat, player: this } }));
    }
  };

  /* Jump to inverse step j (0-based; j = beats.length is the decision step) and pause there. */
  Player.prototype.showBeat = function (j) {
    var T = this.T, t = j >= T.beats.length ? T.fin[0] + 1.6 : T.beats[j][0] + 1.0;
    this.pause(true);
    this.seek(t);
  };
  Player.prototype.showPhase = function (p) {
    this.pause(true);
    this.seek(p === 'check' ? this.T.check[0] + 0.8 : this.T[p][0] + 0.001);
  };
  Player.prototype.destroy = function () {
    this.pause(false);
    if (this.io) this.io.disconnect();
    this.root.__ppa = null;
    var i = api.players.indexOf(this);
    if (i >= 0) api.players.splice(i, 1);
  };

  Player.prototype.seek = function (t) { this.fresh = false; this.renderAt(t); this.last = null; };
  Player.prototype.marks_ = function () {
    var T = this.T, a = [T.scene[0], T.render[0], T.inverse[0]];
    T.beats.forEach(function (b) { a.push(b[0]); });
    a.push(T.fin[0], T.check[0]);
    return a;
  };
  Player.prototype.step = function (dir) {
    var a = this.marks_(), t = this.t, target = dir > 0 ? null : 0;
    for (var i = 0; i < a.length; i++) {
      if (dir > 0 && a[i] > t + 0.05) { target = a[i]; break; }
      if (dir < 0 && a[i] < t - 0.4) target = a[i];
    }
    if (target === null) target = 0;
    this.pause(true);
    this.seek(target + 0.001);
  };
  Player.prototype.play = function () {
    if (this.playing) return;
    if (this.fresh) { this.fresh = false; this.renderAt(0); }
    this.playing = true; this.last = null;
    this.btn.innerHTML = PAUSE; this.btn.setAttribute('aria-label', 'Pause');
    var self = this;
    function tick(now) {
      if (!self.playing) return;
      if (self.last !== null) {
        var t = self.t + self.rate * (now - self.last) / 1000;
        if (t >= self.duration) t = 0;
        self.renderAt(t);
      }
      self.last = now;
      self.raf = requestAnimationFrame(tick);
    }
    this.raf = requestAnimationFrame(tick);
  };
  Player.prototype.pause = function (byUser) {
    this.playing = false;
    if (byUser) this.userPaused = true;
    cancelAnimationFrame(this.raf);
    this.btn.innerHTML = PLAY; this.btn.setAttribute('aria-label', 'Play');
  };
  Player.prototype.toggle = function (byUser) {
    if (this.playing) this.pause(byUser);
    else { this.userPaused = false; this.play(); }
  };

  var api = { players: [], Player: Player, hl: hl };
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var params = new URLSearchParams(window.location.search);
  var capture = params.has('capture');

  function mount(root) {
    if (root.__ppa) return Promise.resolve(root.__ppa);
    var src = root.getAttribute('data-src');
    var inline = root.querySelector('script[type="application/json"]');
    var base = root.getAttribute('data-base') || (src ? src.replace(/[^\/]*$/, '') : '');
    var load = inline ? Promise.resolve(JSON.parse(inline.textContent)) :
      fetch(src).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    root.innerHTML = '<div class="ppa-loading">Loading animation…</div>';
    return load.then(function (m) {
      if (capture) root.classList.add('is-capture');
      var p = new Player(root, m, base);
      root.__ppa = p;
      api.players.push(p);
      if (capture) return p;
      if (reduce) { p.seek(p.T.check[0] + 0.5); return p; }
      if ('IntersectionObserver' in window) {
        p.io = new IntersectionObserver(function (es) {
          es.forEach(function (e) {
            if (e.isIntersecting && e.intersectionRatio >= 0.35) { if (!p.userPaused && !document.hidden) p.play(); }
            else if (p.playing) p.pause(false);
          });
        }, { threshold: [0, 0.35, 0.6] });
        p.io.observe(root);
      } else p.play();
      return p;
    }).catch(function (err) {
      root.innerHTML = '<div class="ppa-loading">Animation could not be loaded (' + esc(err.message || err) + ').</div>';
    });
  }

  function mountAll(scope) {
    var roots = Array.prototype.slice.call((scope || document).querySelectorAll('.ppa:not([data-manual])'));
    if (!('IntersectionObserver' in window) || capture) return Promise.all(roots.map(mount));
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); mount(e.target); } });
    }, { rootMargin: '600px 0px' });
    roots.forEach(function (r) { io.observe(r); });
    return Promise.resolve();
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) api.players.forEach(function (p) { if (p.playing) { p.pause(false); p.resume = true; } });
    else api.players.forEach(function (p) { if (p.resume) { p.resume = false; p.play(); } });
  });

  api.mount = mount;
  api.mountAll = mountAll;
  window.PPAnim = api;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { mountAll(); });
  else mountAll();
})();
