"""Build 3d-scenes-and-photographs.html from the two page parts written by
build_photographs.py and build_blender.py (content/part-*.html).
Text only; no generated code is run. Run sync_navigation.py afterwards.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def part(name):
    text = (ROOT / "content" / name).read_text()
    main = re.search(r'<main id="main">(.*)</main>', text, re.S).group(1)
    head, body = main.split("</header>", 1)
    paras = re.search(r"</h1>(.*)</div>\s*$", head, re.S).group(1)
    return paras.strip(), body.strip(), text


def build():
    photo_intro, photo_body, _ = part("part-photographs.html")
    bl_intro, bl_body, bl_text = part("part-blender.html")
    script = re.search(r"<script>\s*document\.querySelectorAll\('\.bl-toggle'\).*?</script>", bl_text, re.S).group(0)
    page = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="The PixelProof forward–inverse check applied to 3D scenes rendered in Blender and to photographs from an image-generation model. Exploratory samples made after submission." />
    <meta name="theme-color" content="#ffffff" />
    <meta property="og:title" content="3D scenes and photographs · PixelProof" />
    <meta property="og:description" content="The same forward–inverse check on 3D scenes rendered in Blender and on photographs." />
    <meta property="og:type" content="website" />
    <title>3D scenes and photographs · PixelProof</title>
    <link rel="icon" href="static/images/favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="static/css/bulma.min.css" />
    <link rel="stylesheet" href="static/css/nerfies.css" />
    <link rel="stylesheet" href="static/css/site.css" />
    <link rel="stylesheet" href="static/css/paper.css" />
    <link rel="stylesheet" href="static/css/design.css" />
    <link rel="stylesheet" href="static/css/editorial.css" />
    <link rel="stylesheet" href="static/css/pp-anim.css" /><script src="static/js/pp-anim.js" defer></script>
    <link rel="stylesheet" href="static/css/photographs.css" />
    <link rel="stylesheet" href="static/css/blender.css" />
    <link rel="stylesheet" href="static/css/beyond.css" />
  </head>
  <body class="reading-page photographs-page bl-page beyond-page">
    <a class="skip-link" href="#main">Skip to content</a>
    <nav class="site-nav" aria-label="Main navigation"></nav>
    <main id="main">
      <header class="reading-page-intro">
        <div class="container site-width">
          <a href="index.html">← Project overview</a>
          <h1>3D scenes and photographs</h1>
          <p>
            The worlds in the paper are 2D images drawn with Python code. After submission we kept the
            forward–inverse check unchanged and gave the coding agent two other ways to make an image: Blender
            for 3D scenes, and an image-generation model that turns a program rendering into a photograph.
            In both, one program computes the answer and a second program must recover it from the pixels alone.
          </p>
          <p>
            Both are first runs. The samples below are exploratory, none has been through formal human review,
            and we report no model accuracy on them.
          </p>
          <nav class="page-contents" aria-label="On this page"><a href="#blender">3D scenes in Blender</a><a href="#photographs">Photographs</a></nav>
        </div>
      </header>
      <div class="reading-page-intro beyond-part" id="blender">
        <div class="container site-width">
          <h2>3D scenes rendered in Blender</h2>
          {bl_intro}
        </div>
      </div>
      {bl_body}
      <div class="reading-page-intro beyond-part" id="photographs">
        <div class="container site-width">
          <h2>From program renderings to photographs</h2>
          {photo_intro}
        </div>
      </div>
      {photo_body}
    </main>
    <footer class="footer">
      <div class="container reading-width has-text-centered">
        <p><strong>PixelProof</strong> · Visual Question Generation through Forward–Inverse Agreement</p>
        <p>Images are resized to at most 768 px. Select an image to open it.</p>
        <p><a href="THIRD_PARTY_NOTICES.md">Credits &amp; asset notices</a></p>
      </div>
    </footer>
    {script}
  </body>
</html>
'''
    (ROOT / "3d-scenes-and-photographs.html").write_text(page)
    print("3d-scenes-and-photographs.html written")


if __name__ == "__main__":
    build()
