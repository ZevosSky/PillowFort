"""
    @author Tutorial harness
    @brief  Pixel probes on screenshots (ImageMagick; no Python imaging library needed),
            and the sRGB arithmetic for predicting what a pixel should read.
    @copyright 2026 Gary Yang
"""

from __future__ import annotations

import re
import subprocess


def pixel(png: str, x: int, y: int) -> tuple[int, int, int]:
    """8-bit RGB at (x, y)."""
    out = subprocess.run(["convert", png, "-crop", f"1x1+{x}+{y}", "-depth", "8", "txt:-"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    m = re.search(r"\((\d+),(\d+),(\d+)", out.splitlines()[-1] if out else "")
    if not m:
        raise RuntimeError(f"cannot read pixel {x},{y} of {png}: {out}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def linear_to_srgb(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_byte(c: float) -> int:
    return int(round(min(max(c, 0.0), 1.0) * 255))
