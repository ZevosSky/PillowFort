"""Shared drawing kit for the tutorial's authored figures; optional authoring, not an engine build.

@author Gary Yang
@brief Palette, outlined text and drawing helpers for figures/ch*.py
@copyright (C) Gary 2026

Each figure is a self-contained SVG: plain shapes, explicit colours and text outlined from
Matplotlib's bundled DejaVu fonts, so it looks the same on every reader's machine. The figures
are teaching schematics and computed plots, never renderer captures. See figures/README.md.
"""
from html import escape
from pathlib import Path
import math

import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

# make-foliage-batches.py's colours, plus tints of them and one extra accent.
INK, GRAY, LINE, HAIR = "#182637", "#536474", "#8a9aaa", "#d5dce4"
FILL, BLUE, BLUE_FILL = "#f4f7fa", "#23639b", "#dfeaf4"
GOLD, GOLD_TEXT, GOLD_SOFT, GOLD_FILL = "#b66d00", "#8a5200", "#efbc66", "#fbeed6"
TEAL, TEAL_FILL = "#1f7a6d", "#dcefe9"
RED, GREEN, VIOLET = "#c2412d", "#2f7d32", "#6a4c9c"
GRID = "#e4e9ef"
WHITE = "#ffffff"

MAX_WIDTH = 880  # GitHub's Markdown column; a wider figure is scaled down and its text shrinks.

_FONT_FILES = {
    "regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf", "italic": "DejaVuSans-Oblique.ttf",
    "vector": "DejaVuSerif-Bold.ttf",  # bold serif for vector names: a sans "l" is a bare bar
    "mono": "DejaVuSansMono.ttf", "mono-bold": "DejaVuSansMono-Bold.ttf",
}
_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONTS = {name: FontProperties(fname=str(_FONT_DIR / file)) for name, file in _FONT_FILES.items()}


def number(value):
    """Short, stable numbers for SVG attributes."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def measure(string, size=15, font="regular"):
    """Ink width and height of one line of text, for laying out boxes before drawing them."""
    extents = TextPath((0, 0), string, size=size, prop=FONTS[font]).get_extents()
    return extents.x1 - extents.x0, extents.y1 - extents.y0


def encode_srgb(value):
    """Linear to sRGB-encoded, as the swapchain or composite applies it."""
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def unit(degrees):
    """A unit vector in SVG space (y down) for a mathematical angle (counter-clockwise from +x)."""
    radians = math.radians(degrees)
    return (math.cos(radians), -math.sin(radians))


class Figure:
    """One SVG figure. Coordinates are pixels at the size GitHub shows it, y down."""

    def __init__(self, name, width, height, alt, kind="authored teaching schematic", source="", parameters=None):
        self.name, self.width, self.height, self.alt = name, width, height, alt
        self.kind, self.source, self.parameters = kind, source, parameters or {}
        self.defs, self.parts, self.texts = [], [], []

    # Raw markup, for anything the helpers do not cover (gradients, clip paths, patterns).
    def add(self, markup):
        self.parts.append(markup)

    def rect(self, x, y, w, h, fill="none", stroke="none", width=1.2, radius=0, dash=None, opacity=None):
        extra = (f' stroke-dasharray="{dash}"' if dash else "") + (f' opacity="{number(opacity)}"' if opacity is not None else "")
        self.add(f'<rect x="{number(x)}" y="{number(y)}" width="{number(w)}" height="{number(h)}" rx="{number(radius)}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{number(width)}"{extra}/>')

    def line(self, points, stroke=GRAY, width=1.5, dash=None, fill="none", closed=False):
        d = "M" + " L".join(f"{number(x)} {number(y)}" for x, y in points) + (" Z" if closed else "")
        dashes = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{number(width)}" '
                 f'stroke-linecap="round" stroke-linejoin="round"{dashes}/>')

    def polygon(self, points, fill=FILL, stroke="none", width=1.2, opacity=None):
        self.line(points, stroke, width, fill=fill, closed=True)
        if opacity is not None:
            self.parts[-1] = self.parts[-1].replace("<path ", f'<path opacity="{number(opacity)}" ', 1)

    def circle(self, x, y, r, fill="none", stroke="none", width=1.2):
        self.add(f'<circle cx="{number(x)}" cy="{number(y)}" r="{number(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{number(width)}"/>')

    def arc(self, cx, cy, radius, start, end, stroke=TEAL, width=1.3, dash=None):
        """An arc between two mathematical angles (degrees, counter-clockwise from +x), drawn the short way."""
        a = (cx + radius * unit(start)[0], cy + radius * unit(start)[1])
        b = (cx + radius * unit(end)[0], cy + radius * unit(end)[1])
        sweep = 0 if (end - start) % 360 < 180 else 1
        dashes = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M{number(a[0])} {number(a[1])} A{number(radius)} {number(radius)} 0 0 {sweep} {number(b[0])} {number(b[1])}" '
                 f'fill="none" stroke="{stroke}" stroke-width="{number(width)}" stroke-linecap="round"{dashes}/>')

    def arrow(self, points, color=GRAY, width=1.7, head=11, dash=None, both=False):
        """A polyline ending in a filled head. both=True puts a head at the start too."""
        heads = []

        def head_at(tail, tip):
            length = math.hypot(tip[0] - tail[0], tip[1] - tail[1])
            ux, uy = (tip[0] - tail[0]) / length, (tip[1] - tail[1]) / length
            base = (tip[0] - ux * head, tip[1] - uy * head)
            side = head * 0.46
            wing = [(base[0] - uy * side, base[1] + ux * side), tip, (base[0] + uy * side, base[1] - ux * side)]
            d = "M" + " L".join(f"{number(x)} {number(y)}" for x, y in wing) + " Z"
            heads.append(f'<path d="{d}" fill="{color}" stroke="{color}" stroke-width="1" stroke-linejoin="round"/>')
            return base
        points = list(points)
        end = head_at(points[-2], points[-1])
        start = head_at(points[1], points[0]) if both else points[0]
        self.line([start] + points[1:-1] + [end], color, width, dash)  # shaft first, so a dash never covers a head
        self.parts.extend(heads)

    def text(self, x, y, string, size=15, font="regular", fill=INK, anchor="start", rotate=None):
        """One line of outlined text; y is the optical middle of the line. Returns its ink box."""
        path = TextPath((0, 0), string, size=size, prop=FONTS[font])
        extents = path.get_extents()
        shift = {"start": 0, "middle": -(extents.x0 + extents.x1) / 2, "end": -extents.x1}[anchor]
        baseline = size * 0.36
        d, curve = [], []
        for (px, py), code in zip(path.vertices, path.codes):
            point = f"{number(px + shift)} {number(baseline - py)}"
            if code == 1:
                d.append("M" + point)
            elif code == 2:
                d.append("L" + point)
            elif code in (3, 4):
                curve.append(point)
                if len(curve) == code - 1:
                    d.append(("Q" if code == 3 else "C") + " ".join(curve))
                    curve = []
            elif code == 79:
                d.append("Z")
        place = f"translate({number(x)} {number(y)})" + (f" rotate({number(rotate)})" if rotate else "")
        self.add(f'<path transform="{place}" fill="{fill}" d="{"".join(d)}"/>')
        box = (x + extents.x0 + shift, y + baseline - extents.y1, x + extents.x1 + shift, y + baseline - extents.y0)
        if not rotate:
            self.texts.append((string, box))
        return box

    def lines(self, x, y, strings, size=15, font="regular", fill=INK, anchor="start", spacing=None):
        """Several lines of text, the first centred on y."""
        step = spacing or size * 1.35
        return [self.text(x, y + i * step, s, size, font, fill, anchor) for i, s in enumerate(strings)]

    def hatch(self, x0, x1, y, depth=13, step=17, color=LINE):
        """Short diagonal strokes under a surface line, the drafting sign for solid ground."""
        x = x0 + 8
        while x < x1 - 4:
            self.line([(x + 12, y + 3), (x, y + depth + 3)], color, 1.1)
            x += step

    def problems(self, margin=6):
        """Layout faults a reviewer would otherwise have to spot by eye."""
        found = []
        if self.width > MAX_WIDTH:
            found.append(f"{self.name}: {self.width} px wide, over {MAX_WIDTH}")
        for string, (x0, y0, x1, y1) in self.texts:
            if x0 < margin or y0 < margin or x1 > self.width - margin or y1 > self.height - margin:
                found.append(f"{self.name}: text {string!r} runs outside the card")
        for i, (a, (ax0, ay0, ax1, ay1)) in enumerate(self.texts):
            for b, (bx0, by0, bx1, by1) in self.texts[i + 1:]:
                overlap = (min(ax1, bx1) - max(ax0, bx0)) * (min(ay1, by1) - max(ay0, by0))
                if min(ax1, bx1) > max(ax0, bx0) and min(ay1, by1) > max(ay0, by0) and overlap > 2:
                    found.append(f"{self.name}: text {a!r} overlaps {b!r}")
        return found

    def svg(self):
        defs = f"<defs>{''.join(self.defs)}</defs>\n" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" role="img" aria-label="{escape(self.alt, quote=True)}">\n'
                f"<title>{escape(self.alt)}</title>\n{defs}"
                f'<rect x="0.5" y="0.5" width="{self.width - 1}" height="{self.height - 1}" rx="12" fill="{WHITE}" stroke="{HAIR}"/>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


def node(f, x, y, w, h, title, note="", kind="pass", title_font="bold", size=15):
    """A rounded box centred vertically on y: a pass, data, a shader, an input or a plain box."""
    fill, stroke = {"pass": (BLUE_FILL, BLUE), "data": (GOLD_FILL, GOLD), "shader": (FILL, LINE),
                    "input": (WHITE, LINE), "teal": (TEAL_FILL, TEAL), "plain": (FILL, LINE)}[kind]
    f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
    if note:
        f.text(x + w / 2, y - 10, title, size, title_font, anchor="middle")
        f.text(x + w / 2, y + 12, note, 13, fill=GRAY, anchor="middle")
    elif title:
        f.text(x + w / 2, y, title, size, title_font, anchor="middle")


def swatch(f, x, y, kind, label):
    """One legend row: a small box in a node's colours and its meaning."""
    fill, stroke = {"pass": (BLUE_FILL, BLUE), "data": (GOLD_FILL, GOLD), "shader": (FILL, LINE),
                    "teal": (TEAL_FILL, TEAL), "input": (WHITE, LINE)}[kind]
    f.rect(x, y - 10, 30, 20, fill, stroke, 1.3, 5)
    f.text(x + 40, y, label, 13.5, fill=GRAY)
