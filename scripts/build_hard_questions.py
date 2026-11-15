"""Build hard-questions.html from data/hard-questions.json.

    python3 scripts/build_hard_questions.py

An entry with an "animation" key whose manifest exists under static/animations/
also gets the step-by-step player. Run scripts/sync_navigation.py afterwards.
"""
from pathlib import Path
import html, json

ROOT = Path(__file__).resolve().parents[1]
E = html.escape


def build():
    items = json.loads((ROOT / "data" / "hard-questions.json").read_text())
    cards, any_anim = [], False
    for n, q in enumerate(items, 1):
        opts = "".join(f"<span>{E(str(o))}</span>" for o in q["choices"])
        anim = ""
        key = q.get("animation")
        if key and (ROOT / "static" / "animations" / key / "manifest.json").exists():
            any_anim = True
            anim = (f'<details class="hard-anim"><summary>Watch the programs solve it, step by step</summary>'
                    f'<div class="ppa" data-src="static/animations/{E(key)}/manifest.json"></div></details>')
        cards.append(f"""<article class="hard-card" id="{E(q['slug'])}">
          <a class="hard-image" href="{E(q['image'])}"><img src="{E(q['image'])}" width="{q['width']}" height="{q['height']}" loading="lazy" alt="Question image: {E(q['title'])}" /></a>
          <div class="hard-body">
            <p class="hard-kicker">{n} · {E(q['skill'])}</p>
            <h2>{E(q['question'])}</h2>
            <p class="hard-options" aria-label="Answer choices">{opts}</p>
            <details class="hard-answer"><summary>Show the answers</summary>
              <p>Recorded answer: <b class="ok">{E(str(q['answer']))}</b></p>
              {''.join(f'<p>{E(m["name"])} answered: <b class="no">{E(str(m["answer"]))}</b></p>' for m in q['models'])}
            </details>
          </div>
          {anim}
        </article>""")
    player = ('<link rel="stylesheet" href="static/css/pp-anim.css" /><script src="static/js/pp-anim.js" defer></script>' if any_anim else "")
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="Four short generated visual questions that a frontier vision-language model answered wrongly. Try them yourself." />
    <meta name="theme-color" content="#ffffff" />
    <meta property="og:title" content="Short questions a frontier model missed · PixelProof" />
    <meta property="og:description" content="Four short generated visual questions that a frontier model answered wrongly." />
    <meta property="og:type" content="website" />
    <title>Short questions a frontier model missed · PixelProof</title>
    <link rel="icon" href="static/images/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="static/css/bulma.min.css" />
    <link rel="stylesheet" href="static/css/nerfies.css" />
    <link rel="stylesheet" href="static/css/site.css" />
    <link rel="stylesheet" href="static/css/paper.css" />
    <link rel="stylesheet" href="static/css/design.css" />
    <link rel="stylesheet" href="static/css/editorial.css" />
    {player}
    <link rel="stylesheet" href="static/css/hard-questions.css" />
  </head>
  <body class="reading-page hard-page">
    <a class="skip-link" href="#main">Skip to content</a>
    <nav class="site-nav" aria-label="Main navigation"></nav>
    <main id="main">
      <header class="reading-page-intro">
        <div class="container site-width">
          <a href="index.html">← Project overview</a>
          <h1>Short questions a frontier model missed</h1>
          <p>
            Each question below is one sentence, and each image is one that at least one frontier vision-language model
            answered wrongly. Try them before opening the answers.
          </p>
          <p class="hard-note">
            These are development samples generated after submission, chosen because the model missed them; they are
            not a benchmark and we report no accuracy. Each world passed the same automatic forward–inverse check as
            the worlds in the paper; none has been through human review.
          </p>
        </div>
      </header>
      <section class="hard-section"><div class="container site-width">
        {''.join(cards)}
      </div></section>
    </main>
    <footer class="footer">
      <div class="container reading-width has-text-centered">
        <p><strong>PixelProof</strong> · Visual Question Generation through Forward–Inverse Agreement</p>
        <p><a href="THIRD_PARTY_NOTICES.md">Credits &amp; asset notices</a></p>
      </div>
    </footer>
  </body>
</html>
"""
    (ROOT / "hard-questions.html").write_text(page)
    print(len(items), "questions;", "with animations" if any_anim else "no animations yet")


if __name__ == "__main__":
    build()
