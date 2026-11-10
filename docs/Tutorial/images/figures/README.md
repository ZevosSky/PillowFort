# Authored figures

The tutorial's diagrams and plots are drawn in code, one module per chapter (`ch04.py` for Chapter 4),
on the shared kit `../figure_kit.py`. `../make-tutorial-figures.py` writes each figure as an SVG beside the
chapter images and records it in `../diagrams.json`. This is optional authoring, not part of the engine build:
the SVGs are committed, and a reader never runs these scripts.

```
python make-tutorial-figures.py                    every figure, then diagrams.json
python make-tutorial-figures.py --only ch04 --preview <dir>
```

It needs Matplotlib (its bundled DejaVu fonts are outlined into each SVG). `--preview` also needs resvg-py and
Pillow, and writes three PNGs per figure: `name.png` at twice the size, and `name-light.png` and
`name-dark.png` at the real size on GitHub's light and dark page colours.

## What a module holds

```python
from figure_kit import *

def frames_without_overlap():
    f = Figure("frames-without-overlap", 880, 246, alt="...", source="04-Commands-And-Synchronization.md, section 2")
    ...
    return f

FIGURES = [frames_without_overlap]
```

- **Names** describe the content and carry no chapter number (`shadow-cascade-fit`), because chapters can be
  renumbered. They must not clash with another image in the folder.
- **`alt`** says what the figure shows, in a sentence or two, and the chapter's image line uses the same text.
- **`kind`** is `authored teaching schematic`, or `computed plot` when the data comes from a formula in the
  chapter. A computed figure asserts that it reproduces any numbers the chapter prints.

## Style

- **Size:** at most 880 px wide, drawn at the size GitHub shows it. Body text 15 px, notes 13-14 px, nothing
  under 12.5 px.
- **Card:** the kit draws a white card with a hairline border, so a figure reads on light and dark pages.
- **Colours:** the kit's tokens. Blue is a pass or the CPU's work, gold is data or the GPU's work, teal is a
  derived or highlighted thing, grey is plumbing and notes. Use `GOLD_TEXT`, not `GOLD`, for gold text.
- **Fonts:** sans for labels, bold for names, italic for asides, bold serif (`"vector"`) for vector and
  matrix names such as **n**, **l**, **v**, and mono for code identifiers.
- **Words:** keep the chapter's own terms and numbers. A figure states nothing the text does not, and no
  title inside the figure: the sentence before it introduces it.

## Before a figure is shown to anyone

Render it with `--preview` and look at `name-light.png` and `name-dark.png`:

- Is it correct against the chapter's text: every arrow, label, number and direction?
- Does it read at a glance? Is anything clipped, overlapping, cramped or lopsided?
- Is there dead space to trim?

`make-tutorial-figures.py` also prints a `PROBLEM:` line for text outside the card or overlapping other text.
Fix the source, render again, and look again until nothing is left.
