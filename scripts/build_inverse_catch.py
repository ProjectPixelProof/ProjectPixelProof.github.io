"""Build the piano example from the paper's Fig. 4: an inverse program catches a renderer bug.

The images are the manuscript's own figure assets, copied byte for byte. The text
follows the paper's caption and the inverse-program results paragraph.
"""
import hashlib

IMAGES = ['piano_buggy_image', 'piano_buggy_step1_keep', 'piano_buggy_step2_blobs',
          'piano_buggy_step3_count', 'piano_fixed_image']
QUESTION = 'How many separate raised black keys are visible above the seven white keys?'
STOP_IMAGES = ['input', 'step1_red', 'step2_hull', 'step3_profile', 'step4_fit']
STOP_QUESTION = 'How many straight sides does the red STOP sign’s outer boundary have?'


def copy_images(root, paper):
    manifest = []
    for name in IMAGES:
        src = paper / 'figures/assets' / f'{name}.png'
        dest = root / 'static/images/method' / f'{name}.png'
        dest.write_bytes(src.read_bytes())
        manifest.append({'paperImage': str(src.relative_to(paper)), 'path': str(dest.relative_to(root)),
                         'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
    for name in STOP_IMAGES:
        src = paper / 'figures/inverse-steps/stopsign' / f'{name}.png'
        dest = root / 'static/images/method' / f'stopsign_{name}.png'
        dest.write_bytes(src.read_bytes())
        manifest.append({'paperImage': str(src.relative_to(paper)), 'path': str(dest.relative_to(root)),
                         'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
    return manifest


def figure():
    img = lambda name, alt: f'<img src="static/images/method/{name}.png" alt="{alt}" loading="lazy">'
    steps = [('piano_buggy_image', 'Rendered piano image with five black keys', '', 'Rendered image'),
             ('piano_buggy_step1_keep', 'Black pixels kept by the inverse program', '1', 'Keep black pixels'),
             ('piano_buggy_step2_blobs', 'Five connected regions, each in its own color', '2', 'Group connected regions'),
             ('piano_buggy_step3_count', 'Five regions numbered one to five', '3', 'Count separate keys')]
    items = ''.join(f'<li>{img(n, a)}<span>' + (f'<b>{k}</b>' if k else '') + f'{label}</span></li>' for n, a, k, label in steps)
    return ('<figure class="catch-figure">'
            '<div class="catch-layout">'
            '<div class="catch-panel catch-before">'
            f'<p class="catch-question">“{QUESTION}”</p>'
            f'<ol class="catch-steps">{items}</ol>'
            '<p class="catch-verdict is-fail"><span>Forward <strong>4</strong></span><span class="catch-sign" aria-label="does not equal">≠</span>'
            '<span>Inverse <strong>5</strong></span><em>Self-check fails</em></p>'
            '</div>'
            '<p class="catch-arrow"><span>Agent repairs the renderer</span></p>'
            '<div class="catch-panel catch-after">'
            f'<div class="catch-fixed">{img("piano_fixed_image", "Repaired piano image with four black keys")}<span>Repaired image</span></div>'
            '<p class="catch-verdict is-pass"><span>Forward <strong>4</strong></span><span class="catch-sign" aria-label="equals">=</span>'
            '<span>Inverse <strong>4</strong></span><em>Checks pass</em></p>'
            '</div>'
            '</div>'
            '<figcaption>Given a rendered piano octave, the inverse program processes the image deterministically and '
            'arrives at the answer 5. This does not match the forward program’s answer of 4, revealing a bug in the renderer. '
            'The mismatch is feedback that helps the agent repair the renderer (right). Without the inverse program, this '
            'world would have recorded the wrong answer 4 for an image with five black keys. Steps 1–3 are the inverse '
            'program’s own outputs on the faulty image.</figcaption>'
            '</figure>')


def stop_figure():
    steps = [('input', 'STOP sign with ten straight sides', '', 'Input image'),
             ('step1_red', 'Saturated red pixels kept by the inverse program', '1', 'Keep saturated red pixels'),
             ('step2_hull', 'Outer boundary of the red region and its center', '2', 'Get boundary and its center'),
             ('step3_profile', 'Distance from the center to the boundary at each angle', '3', 'Boundary distance from center by angle'),
             ('step4_fit', 'Fit error of regular polygons with 6 to 10 sides; 10 fits best', '4', 'Fit error of regular 6–10-gons; 10 fits best')]
    items = ''.join(f'<li><img src="static/images/method/stopsign_{n}.png" alt="{a}" loading="lazy"><span>'
                    + (f'<b>{k}</b>' if k else '') + f'{label}</span></li>' for n, a, k, label in steps)
    return ('<figure class="catch-figure catch-stop">'
            '<div class="catch-panel">'
            f'<p class="catch-question">“{STOP_QUESTION}”</p>'
            f'<ol class="catch-steps">{items}</ol>'
            '<p class="catch-verdict is-pass"><span>Forward <strong>10</strong></span><span class="catch-sign" aria-label="equals">=</span>'
            '<span>Inverse <strong>10</strong></span><em>Checks pass</em></p>'
            '</div>'
            '<figcaption>The agent writes an inverse program to measure the stop sign’s outline from the image alone and '
            'recover its number of sides, matching the forward program’s answer of 10.</figcaption>'
            '</figure>')


FINDINGS = ('<p><strong>Why it matters.</strong> For 29% of the worlds, the inverse program failed at least once '
            'during generation, and the agent fixed its code before submitting. Nearly half of these fixes changed how '
            'the image was drawn or sampled.</p>'
            '<p>In a later 200-scene replay, the forward and inverse programs disagreed on some of the new scenes for 1.6% '
            'of previously verified worlds; these worlds are removed before evaluation and training. In a controlled test, '
            'the checks detected all 300 image replacements that changed the answer.</p>')


def summary(block_id, compact=False):
    if compact:
        return (f'<div id="{block_id}" class="inverse-summary">'
                '<h4>The inverse program catches errors that other checks miss</h4>'
                '<div class="inverse-summary-text"><p>For 29% of the worlds, the inverse program failed at least once '
                'during generation and the agent fixed its code. In one case, a renderer bug drew five black keys '
                'when the scene called for four; the inverse program counted five.</p>'
                '<a class="inverse-summary-button" href="programs.html#inverse-catch">See the piano example '
                '<span aria-hidden="true">→</span></a></div></div>')
    return (f'<div id="{block_id}" class="inverse-summary">'
            '<h4>The inverse program catches errors that other checks miss</h4>'
            + figure() + '<div class="inverse-summary-text">' + FINDINGS +
            '<a class="inverse-summary-button" href="programs.html#inverse-catch">Why the inverse program matters '
            '<span aria-hidden="true">→</span></a></div></div>')


def section():
    return ('<section class="section paper-section" id="inverse-catch"><div class="container site-width">'
            '<header class="section-intro"><p class="eyebrow">A real catch during generation</p>'
            '<h2>Why the inverse program matters</h2>'
            '<p>The forward program reads the answer from the scene specification, so it cannot notice when the image is '
            'drawn wrongly. The inverse program reads the answer from the pixels. When the two disagree, the agent learns '
            'that its code is wrong, often in how the image is drawn.</p></header>'
            + figure() + stop_figure() +
            '<div class="catch-notes">'
            '<p><strong>What went wrong.</strong> The question asks how many separate black keys are visible. The renderer was meant '
            'to leave out one of five black keys, but it chose a new random key to leave out at every position, so in this '
            'scene it left none out. The scene specification still recorded four black keys, and the forward program '
            'answered four.</p>'
            '<p><strong>How the inverse program caught it.</strong> The inverse program kept the black pixels, grouped them '
            'into connected regions, and counted the separate keys. It found five, disagreed with the forward answer, and '
            'the agent’s self-check failed. The agent fixed the renderer so it chooses one key to leave out; on the '
            'repaired image both programs answer four.</p>'
            + FINDINGS +
            '<p class="small-note">The world was generated by '
            'Sol (high) during profile-steered generation (prior-conflict profile).</p>'
            '</div></div></section>\n')
