"""Build photographs.html from the photorealistic example gallery.

    python3 scripts/build_photographs.py --source <gallery folder with index.html and img/>

Copies the image pairs to static/photographs/ and writes a page in the site's
own layout. Run scripts/sync_navigation.py afterwards.
"""
from pathlib import Path
import argparse, html, re, shutil

ROOT = Path(__file__).resolve().parents[1]


def parse(source):
    text = re.sub(r"<style.*?</style>", "", (source / "index.html").read_text(), flags=re.S)
    sections = []
    for sec in re.finditer(r'<section id="([^"]+)">(.*?)</section>', text, flags=re.S):
        body = sec.group(2)
        title = re.search(r"<h2>(.*?)</h2>", body, flags=re.S).group(1).strip()
        lede = re.search(r'<p class="lede">(.*?)</p>', body, flags=re.S).group(1).strip()
        worlds = []
        for card in re.split(r'<div class="card" id="', body)[1:]:
            wid = card.split('"', 1)[0]
            name = re.search(r"<h3>(.*?)</h3>", card, flags=re.S).group(1).strip()
            question = re.search(r'<p class="question">(.*?)</p>', card, flags=re.S).group(1).strip()
            options = re.findall(r'<span class="opt">(.*?)</span>', card)
            samples = []
            for fig in re.findall(r'<figure class="sample">(.*?)</figure>', card, flags=re.S):
                imgs = re.findall(r'<img src="img/([^"]+)"[^>]*alt="([^"]*)"', fig)
                expected = re.search(r"expected answer: <b>(.*?)</b>", fig).group(1)
                recovered = re.search(r"inverse program: recovered (.*?)</span>", fig).group(1)
                assert len(imgs) == 2 and "rendering" in imgs[0][0] and "photograph" in imgs[1][0], imgs
                assert html.unescape(expected) == html.unescape(recovered), (wid, expected, recovered)
                samples.append((imgs[0], imgs[1], expected))
            assert samples, wid
            worlds.append((wid, name, question, options, samples))
        sections.append((sec.group(1), title, lede, worlds))
    return sections


def build(source):
    sections = parse(source)
    out = ROOT / "static" / "photographs"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    n_worlds = sum(len(s[3]) for s in sections)
    n_pairs = sum(len(w[4]) for s in sections for w in s[3])
    parts = []
    for sid, title, lede, worlds in sections:
        parts.append(f'<section class="photo-section" id="{sid}" aria-labelledby="{sid}-heading"><div class="container site-width">'
                     f'<h2 id="{sid}-heading">{title}</h2><p class="photo-lede">{lede}</p>')
        for wid, name, question, options, samples in worlds:
            opts = "".join(f"<span>{o}</span>" for o in options)
            parts.append(f'<article class="photo-world" id="{wid}"><h3>{name}</h3><p class="photo-question">{question}</p>'
                         f'<p class="photo-options" aria-label="Answer choices">{opts}</p><div class="photo-grid">')
            for (r, ralt), (p, palt), expected in samples:
                for f in (r, p):
                    shutil.copyfile(source / "img" / f, out / f)
                parts.append(
                    '<figure class="photo-pair"><div class="photo-images">'
                    f'<a href="static/photographs/{r}"><img src="static/photographs/{r}" width="768" height="768" loading="lazy" alt="{ralt}" /><span>Rendering</span></a>'
                    f'<a href="static/photographs/{p}"><img src="static/photographs/{p}" width="768" height="768" loading="lazy" alt="{palt}" /><span>Photograph</span></a>'
                    f'</div><figcaption>Answer: <b>{expected}</b> · recovered by the inverse program from both images</figcaption></figure>')
            parts.append("</div></article>")
        parts.append("</div></section>")
    toc = "".join(f'<a href="#{sid}">{title}</a>' for sid, title, _, _ in sections)
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="A feasibility experiment: PixelProof question worlds whose program renderings are turned into photographs, with the same inverse program recovering the answer from both." />
    <meta name="theme-color" content="#ffffff" />
    <meta property="og:title" content="From program renderings to photographs · PixelProof" />
    <meta property="og:description" content="Program renderings and the photographs generated from them, checked by the same inverse program." />
    <meta property="og:type" content="website" />
    <title>From program renderings to photographs · PixelProof</title>
    <link rel="icon" href="static/images/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="static/css/bulma.min.css" />
    <link rel="stylesheet" href="static/css/nerfies.css" />
    <link rel="stylesheet" href="static/css/site.css" />
    <link rel="stylesheet" href="static/css/paper.css" />
    <link rel="stylesheet" href="static/css/design.css" />
    <link rel="stylesheet" href="static/css/editorial.css" />
    <link rel="stylesheet" href="static/css/photographs.css" />
  </head>
  <body class="reading-page photographs-page">
    <a class="skip-link" href="#main">Skip to content</a>
    <nav class="site-nav" aria-label="Main navigation"></nav>
    <main id="main">
      <header class="reading-page-intro">
        <div class="container site-width">
          <a href="index.html">← Project overview</a>
          <h1>From program renderings to photographs</h1>
          <p>
            Each pair below shows a rendering drawn by a world’s program and a photograph that an image-generation
            model produced from that rendering. A world passes only if the same pixel-only inverse program recovers the
            expected answer from all five renderings and all five photographs. In a two-hour run, 20 of 40 worlds
            passed; {n_worlds} of them are shown here, with {n_pairs} image pairs.
          </p>
          <p class="photo-note">
            This is a first feasibility experiment run after submission, not a benchmark. These are development
            samples: the check is automatic, there was no formal human review, and a pass does not certify that a photograph is
            free of other artifacts. The worlds shown are a selection of the passing ones, and the pairs were screened by eye
            before inclusion, so a world may show fewer than five pairs.
          </p>
          <nav class="page-contents" aria-label="On this page">{toc}</nav>
        </div>
      </header>
      {''.join(parts)}
    </main>
    <footer class="footer">
      <div class="container reading-width has-text-centered">
        <p><strong>PixelProof</strong> · Visual Question Generation through Forward–Inverse Agreement</p>
        <p>Images are resized to at most 768 px. Select an image to open it.</p>
        <p><a href="THIRD_PARTY_NOTICES.md">Credits &amp; asset notices</a></p>
      </div>
    </footer>
  </body>
</html>
"""
    (ROOT / "content" / "part-photographs.html").write_text(page)  # merged into 3d-scenes-and-photographs.html by build_beyond.py
    print(f"{n_worlds} worlds, {n_pairs} pairs, {len(list(out.iterdir()))} images")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    build(ap.parse_args().source)
