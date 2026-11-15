"""Build blender-scenes.html from the Blender export folder.

    python3 scripts/build_blender.py --source <export folder>

For each selected world it copies three fresh images, draws what the inverse
program measured (only values saved by the check run; nothing is recomputed
and no generated code is run), and embeds the inverse program verbatim.
Without --source it rebuilds the page from data/blender.json.
Run scripts/sync_navigation.py afterwards.
"""
from pathlib import Path
import argparse, html, json, math

ROOT = Path(__file__).resolve().parents[1]
E = html.escape
OUT = ROOT / "static" / "blender"

# (folder, slug, kicker, animation key)
PICKS = [
    ("spatial_relationships_3d/ring_interlock", "rings", "3D spatial relationships", "b01"),
    ("mechanisms_connections/pinned_frame_mobility", "frame", "Mechanisms", "b05"),
    ("mechanisms_connections/crank_revolution", "crank", "Mechanisms", None),
    ("mechanisms_connections/spring_compliance", "springs", "Mechanisms", "b06"),
    ("functional_inspection/strap_weave", "weave", "Functional inspection", None),
    ("functional_inspection/tripod_lamp_projection", "tripod", "Functional inspection", None),
    ("functional_inspection/socket_neighbor", "sockets", "Functional inspection", "b04"),
    ("mechanisms_connections/tackle_support", "pulley", "Mechanisms", None),
    ("spatial_relationships_3d/roof_dihedral", "roof", "3D spatial relationships", None),
]

A, B, W = (255, 45, 150, 255), (0, 200, 255, 255), (255, 255, 255, 255)


class Pen:
    """Draws on a transparent layer; every stroke gets a white halo."""

    def __init__(self, size):
        from PIL import Image, ImageDraw
        self.im = Image.new("RGBA", size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.used = False

    def line(self, pts, c=A, w=5):
        self.used = True
        pts = [tuple(p) for p in pts]
        self.d.line(pts, fill=W, width=w + 4)
        self.d.line(pts, fill=c, width=w)

    def box(self, x, y, w, h, c=A):
        self.line([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], c, 4)

    def dot(self, x, y, c=A, r=11):
        self.used = True
        self.d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=W)
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=c)

    def ring(self, x, y, r, c=A):
        self.ellipse((x, y), (2 * r, 2 * r), 0, c)

    def ellipse(self, center, axes, angle, c=A):
        t = math.radians(angle)
        pts = []
        for i in range(121):
            u = 2 * math.pi * i / 120
            x, y = axes[0] / 2 * math.cos(u), axes[1] / 2 * math.sin(u)
            pts.append((center[0] + math.cos(t) * x - math.sin(t) * y, center[1] + math.sin(t) * x + math.cos(t) * y))
        self.line(pts, c, 4)


def side(i, n=2, names=("Left", "Right")):
    return names[i] if n == 2 else str(i + 1)


def rings(d, p):
    for e, c in zip(d["ellipses"], (B, A)):
        p.ellipse(e["center"], e["axes"], e["angle"], c)
    for k in d["crossings"]:
        p.dot(*k["xy"], c=(255, 210, 0, 255))
    tops = [k["over"] for k in d["crossings"]]
    return [f"Crossing {i + 1}: the {t} ring is on top." for i, t in enumerate(tops)] + [
        "Different rings on top at the two crossings: linked." if tops[0] != tops[1]
        else "The same ring on top at both crossings: not linked."]


def pulley(d, p):
    y0, y1 = d["gap_rows"]
    xs = d["vertical_rope_x"]
    for x in xs[:-1]:
        p.line([(x, y0), (x, y1)], A)
    p.line([(xs[-1], y0), (xs[-1], y1)], B)
    return [f"{len(xs)} vertical rope runs between the blocks.",
            "The rightmost run continues down to the free end, so it is the pulled end (blue).",
            f"The other {d['supporting_runs']} runs hold up the lower block (pink)."]


def bracket(d, p):
    f, h, g = d["free_joint"], d["horizontal_wall_joint"], d["diagonal_wall_joint"]
    p.line([(f["x"], f["y"]), (g["x"], g["y"])], A)
    p.line([(f["x"], f["y"]), (h["x"], h["y"])], B)
    for q in d["pins"]:
        p.dot(q["x"], q["y"], c=(255, 210, 0, 255))
    rise = d["projected_anchor_rise_px"]
    return ["Three pin heads found (yellow).",
            f"The diagonal's wall pin is {abs(rise):.0f} px {'above' if rise > 0 else 'below'} the loaded pin.",
            "Rule: the diagonal must push the loaded pin up. Wall pin above means it pulls (tension); below means it pushes (compression)."]


def sockets(d, p):
    out = []
    for i, s in enumerate(d["strips"]):
        row = ", ".join("plug" if t["occupied"] else "empty" for t in s["stations"])
        out.append(f"{side(i)} strip, top to bottom: {row}." + (" Two empty sockets are neighbours." if s["qualifies"] else ""))
    return out


def frame(d, p):
    out = []
    for i, o in enumerate(d["objects"]):
        pv = o["pivots"]
        for a, b in o["bars"]:
            p.line([pv[a], pv[b]], A)
        for j, q in enumerate(pv):
            p.dot(*q, c=B if j in o["fixed"] else (255, 210, 0, 255))
        out.append(f"{side(i)} frame: {len(o['bars'])} bars between 4 pins; "
                   + ("it can still change shape." if o["internal_dof"] else "the bars lock its shape."))
    return out + ["Blue pins are the two fixed lower pivots."]


def crank(d, p):
    out = []
    for i, o in enumerate(d["objects"]):
        pv = o["pivots_px"]
        p.line([pv[0], pv[1]], A)
        p.line([pv[1], pv[2]], B)
        p.line([pv[2], pv[3]], B)
        for q in pv:
            p.dot(*q, c=(255, 210, 0, 255))
        L = o["lengths_px"]
        out.append(f"{side(i)} linkage: crank {L['input']:.0f}, coupler {L['coupler']:.0f}, output {L['output']:.0f}, ground {L['ground']:.0f} px; "
                   + ("the crank can turn fully." if o["full_turn"] else "the crank cannot turn fully."))
    return out + ["Pink is the left grounded crank."]


def springs(d, p):
    out = []
    for i, a in enumerate(d["assemblies"]):
        for s in a["stages"]:
            x0, y0, x1, y1 = s["band"]
            for u, v in s["spring_spans"]:
                p.box(u, y0, v - u, y1 - y0)
        n = [s["parallel_count"] for s in a["stages"]]
        out.append(f"{side(i)} assembly: {' then '.join(str(k) for k in n)} springs side by side; stretch is proportional to "
                   + " + ".join(f"1/{k}" for k in n) + f" = {a['compliance']:.2f}.")
    return out + ["More springs side by side are stiffer; stages in a chain add their stretch."]


def thread(d, p):
    p.box(*d["metal_bbox"])
    s = d["gradient_covariance_score"]
    return [f"Ridge slant score on the screw: {s:+.2f} "
            + ("(ridges lean one way: left-hand thread)." if s > 0 else "(ridges lean the other way: right-hand thread)."),
            "Rule: turning clockwise drives a right-hand screw toward the nut and a left-hand screw away from it."]


def weave(d, p):
    return [f"{len(d['states'])} bars found. Strap at each bar, in order: " + ", ".join(d["states"]) + ".",
            "It alternates all the way." if not d["violations"] else "Two neighbouring bars have the same state, so it does not alternate."]


def battery(d, p):
    out = []
    for i, t in enumerate(d["terminals"]):
        p.box(*t["body"], c=B)
        _, w, h, x, y = t["metal_face"][:5]
        p.box(x, y, w, h)
        out.append(f"{side(i)} cell: the metal end is {t['width_ratio']:.2f} of the cell's width, so it is the {t['terminal_type']} end.")
    return out + ["One flat end and one button end: opposite terminals." if d["opposite"] else "Both ends are the same type."]


def tripod(d, p):
    f = d["feet"]
    p.line(f + [f[0]], B)
    for q in f:
        p.dot(*q, c=B)
    c = d["shade"]["center"]
    p.ring(c[0], c[1], d["shade"]["radius"])
    p.dot(c[0], c[1], r=8)
    inside = min(d["signed_edge_distances_px"]) > 0
    return ["Triangle through the three feet (blue); shade centre (pink).",
            "Signed distance from the centre to each side: " + ", ".join(f"{v:+.0f}" for v in d["signed_edge_distances_px"]) + " px.",
            "All positive: the centre is inside." if inside else "One is negative: the centre is outside."]


def roof(d, p):
    x0, y0, x1, y1 = d["roof_bounds"]
    p.line([(d["seam_x"], y0), (d["seam_x"], y1)], A)
    l, r = d["left_image_slope"], d["right_image_slope"]
    return [f"Fold found at x = {d['seam_x']:.0f} (pink).",
            f"Along the roof's far edge, the image height changes by {l:+.2f} per pixel left of the fold and {r:+.2f} right of it.",
            "The edge peaks at the fold: a ridge." if l < 0 < r else "The edge dips at the fold: a valley."]


DRAW = dict(rings=rings, pulley=pulley, bracket=bracket, sockets=sockets, frame=frame, crank=crank,
            springs=springs, thread=thread, weave=weave, battery=battery, tripod=tripod, roof=roof)


def collect(source):
    from PIL import Image
    source = Path(source)
    worlds = {w["candidate_id"]: w for w in json.loads((source / "data" / "worlds.json").read_text())}
    items = []
    for folder, slug, kicker, anim in PICKS:
        src = source / "rebuttal_samples" / folder
        name = folder.split("/")[-1]
        world = worlds[name]
        assert world["status"] == "fresh_pass", name
        samples = json.loads((src / "samples.json").read_text())
        dst = OUT / slug
        dst.mkdir(parents=True, exist_ok=True)
        shots = []
        for n, s in enumerate(samples, 1):
            assert s["check_kind"] == "fresh" and s["matched"] and s["expected_answer"] == s["inverse_answer"], s["id"]
            im = Image.open(src / s["publication_file"]).convert("RGB")
            im.save(dst / f"{n}.jpg", quality=88, optimize=True)
            pen = Pen(im.size)
            lines = DRAW[slug](s["inverse_result"]["diagnostics"], pen)
            if pen.used:
                pen.im.save(dst / f"{n}-measured.png", optimize=True)
            shots.append(dict(image=f"static/blender/{slug}/{n}.jpg",
                              overlay=f"static/blender/{slug}/{n}-measured.png" if pen.used else None,
                              width=im.size[0], height=im.size[1], answer=str(s["expected_answer"]), readout=lines))
        code = (source / "implementations" / world["selected_source_sha256"] / "world" / "oracle.py").read_text()
        (dst / "inverse.py").write_text(code)
        q = samples[0]
        items.append(dict(slug=slug, title=world["title"], kicker=kicker, question=q["exact_question"],
                          choices=[str(c) for c in q["choices"]], shots=shots, code=f"static/blender/{slug}/inverse.py",
                          code_lines=len(code.splitlines()), animation=anim))
    (ROOT / "data" / "blender.json").write_text(json.dumps(items, indent=1) + "\n")
    return items


def build(items):
    cards, any_anim = [], False
    for n, w in enumerate(items, 1):
        opts = "".join(f"<span>{E(o)}</span>" for o in w["choices"])
        figs = []
        for s in w["shots"]:
            ov = (f'<img class="bl-overlay" src="{E(s["overlay"])}" width="{s["width"]}" height="{s["height"]}" loading="lazy" alt="" />'
                  if s["overlay"] else "")
            figs.append(f"""<figure class="bl-shot">
              <div class="bl-frame"><img src="{E(s['image'])}" width="{s['width']}" height="{s['height']}" loading="lazy" alt="Rendered scene: {E(w['title'])}" />{ov}</div>
              <figcaption class="bl-reveal"><p class="bl-answer">Answer from both programs: <b>{E(s['answer'])}</b></p>
                <ul>{''.join(f'<li>{E(t)}</li>' for t in s['readout'])}</ul></figcaption>
            </figure>""")
        code = (ROOT / w["code"]).read_text()
        anim = ""
        key = w.get("animation")
        if key and (ROOT / "static" / "animations" / key / "manifest.json").exists():
            any_anim = True
            anim = (f'<details class="bl-more"><summary>Watch the inverse program work, step by step</summary>'
                    f'<div class="ppa" data-src="static/animations/{E(key)}/manifest.json"></div></details>')
        has_ov = any(s["overlay"] for s in w["shots"])
        label = "Show what the inverse program measured" if has_ov else "Show what the inverse program read"
        cards.append(f"""<article class="bl-card" id="{E(w['slug'])}">
          <header>
            <p class="bl-kicker">{n} · {E(w['kicker'])}</p>
            <h2>{E(w['question'])}</h2>
            <p class="bl-options" aria-label="Answer choices">{opts}</p>
            <button class="bl-toggle" type="button" aria-pressed="false">{label}</button>
          </header>
          <div class="bl-shots">{''.join(figs)}</div>
          {anim}
          <details class="bl-more"><summary>Inverse program as generated ({w['code_lines']} lines)</summary>
            <pre class="bl-code"><code>{E(code)}</code></pre></details>
        </article>""")
    player = ('<link rel="stylesheet" href="static/css/pp-anim.css" /><script src="static/js/pp-anim.js" defer></script>' if any_anim else "")
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="Exploratory 3D scenes rendered in Blender, each with a question whose answer is computed by one program and recovered from the pixels by another." />
    <meta name="theme-color" content="#ffffff" />
    <meta property="og:title" content="3D scenes rendered in Blender · PixelProof" />
    <meta property="og:description" content="Exploratory 3D scenes with answers checked by forward–inverse agreement." />
    <meta property="og:type" content="website" />
    <title>3D scenes rendered in Blender · PixelProof</title>
    <link rel="icon" href="static/images/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="static/css/bulma.min.css" />
    <link rel="stylesheet" href="static/css/nerfies.css" />
    <link rel="stylesheet" href="static/css/site.css" />
    <link rel="stylesheet" href="static/css/paper.css" />
    <link rel="stylesheet" href="static/css/design.css" />
    <link rel="stylesheet" href="static/css/editorial.css" />
    {player}
    <link rel="stylesheet" href="static/css/blender.css" />
  </head>
  <body class="reading-page bl-page">
    <a class="skip-link" href="#main">Skip to content</a>
    <nav class="site-nav" aria-label="Main navigation"></nav>
    <main id="main">
      <header class="reading-page-intro">
        <div class="container site-width">
          <a href="index.html">← Project overview</a>
          <h1>3D scenes rendered in Blender</h1>
          <p>
            The same forward–inverse check, with a 3D renderer in place of 2D drawing code. One program builds a scene,
            renders it in Blender and computes the answer; a second program receives only the rendered image and the
            question, and must reach the same answer from the pixels.
          </p>
          <p class="bl-note">
            Exploratory samples made after submission; they are not part of the paper's dataset and we report no model
            accuracy on them. One coding agent ran for two hours on each of three themes and attempted 23 worlds: 22
            passed the check during development, and 20 passed it again on six new scenes each (120 of 120 answers
            agree). This page shows 9 of those 20, chosen by us, with three scenes each. No world has been through
            human review, and one agent wrote both programs of each world.
          </p>
        </div>
      </header>
      <section class="bl-section"><div class="container site-width">
        {''.join(cards)}
      </div></section>
    </main>
    <footer class="footer">
      <div class="container reading-width has-text-centered">
        <p><strong>PixelProof</strong> · Visual Question Generation through Forward–Inverse Agreement</p>
        <p><a href="THIRD_PARTY_NOTICES.md">Credits &amp; asset notices</a></p>
      </div>
    </footer>
    <script>
      document.querySelectorAll('.bl-toggle').forEach(function (b) {{
        var shown = b.textContent, hidden = 'Hide the measurements';
        b.addEventListener('click', function () {{
          var on = b.closest('.bl-card').classList.toggle('is-measured');
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
          b.textContent = on ? hidden : shown;
        }});
      }});
    </script>
  </body>
</html>
"""
    (ROOT / "content" / "part-blender.html").write_text(page)  # merged into 3d-scenes-and-photographs.html by build_beyond.py
    print(len(items), "worlds;", "with animations" if any_anim else "no animations yet")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    a = ap.parse_args()
    build(collect(a.source) if a.source else json.loads((ROOT / "data" / "blender.json").read_text()))
