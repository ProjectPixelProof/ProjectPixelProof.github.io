# PixelProof project website

Source for <https://projectpixelproof.github.io/>, the project page for
*PixelProof: Visual Question Generation through Forward–Inverse Agreement*.

## Pages

- `index.html`: overview, method, and a summary of each result.
- `questions.html`: all 2,439 replay-verified worlds as interactive questions, with
  three instances per world and filters by experiment, discovery profile, and
  coding agent.
- `programs.html`: forward and inverse program examples, the piano example of an
  inverse program catching a renderer bug, and step-by-step inverse programs.
- `steering.html` and `steering-gallery.html`: the nine spatial patterns and
  examples of each.
- `results.html`: full result tables and additional training studies.

The question images, question texts, and answers are the original recorded
instances. Program source files in `static/questions/` are shown as text and are
never run by the site.

## View locally

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8765>. Use a local server rather than opening
`index.html` directly, because the question explorer loads JSON files. No build
step is needed, and the site has no analytics.

## Related resources

- Code: <https://github.com/ProjectPixelProof/PixelProof>
- Models and datasets: <https://huggingface.co/collections/PixelProof/models-and-datasets-6ab5721714129252f17c21fd>

## Credits

The page layout is adapted from the
[Nerfies project website](https://github.com/nerfies/nerfies.github.io) under
CC BY-SA 4.0. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for template,
font, and stylesheet notices.
