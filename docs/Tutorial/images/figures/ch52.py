"""Chapter 52, Wind Fields and Vorticles: authored figures.

@author Gary Yang
@brief Figures for 52-Wind-Fields-And-Vorticles.md (wind-field-slices.svg comes from make-wind-fields.py)
@copyright (C) Gary 2026
"""
from pathlib import Path
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "52-Wind-Fields-And-Vorticles.md"
GAP, PAD = 34, 32   # between two steps; a step's width beyond its words


def spans_of(x, steps):
    """Each step's (left, right), laid left to right from x."""
    spans = []
    for title in steps:
        w = measure(title, 15, "bold")[0] + PAD
        spans.append((x, x + w))
        x += w + GAP
    return spans


def step_row(f, y, h, steps, spans, look):
    """Boxes along one lane with an arrow between each."""
    fill, stroke, ink = look
    for title, (left, right) in zip(steps, spans):
        f.rect(left, y - h / 2, right - left, h, fill, stroke, 1.4, 8)
        f.text((left + right) / 2, y, title, 15, "bold", ink, "middle")
    for (_, right), (left, _) in zip(spans, spans[1:]):
        f.arrow([(right + 2, y), (left - 2, y)])


def wind_sources_from_cpu_to_gpu():
    text = CHAPTER.read_text(encoding="utf-8")
    sources, record, total = map(int, re.search(r"The UBO contains `(\d+) × (\d+) = (\d+)` bytes", text).groups())
    assert (sources, record, total) == (16, 64, 1024) and sources * record == total   # the "1 KiB wind UBO"

    cpu_steps = ["emit", "move/age", "retire"]
    gpu_steps = ["begin", "emit", "simulate/sample wind", "end", "indirect draw"]
    lane_x, inset = 24, 20
    cpu, gpu = spans_of(lane_x + inset, cpu_steps), spans_of(lane_x + inset, gpu_steps)
    gpu_right = gpu[-1][1] + inset
    width = round(gpu_right + 24)

    f = Figure("wind-sources-from-cpu-to-gpu", width, 348,
               "The CPU source owner emits, moves and ages, and retires wind sources, and after this frame slot's fence "
               "a snapshot goes into that slot's 1 KiB wind UBO. The GPU fountain runs begin, emit, simulate and sample "
               "wind, end and the indirect draw, and reads the UBO only, in its simulate step.",
               source="52-Wind-Fields-And-Vorticles.md, section 1 (Two kinds of particle, two owners)",
               parameters={"windSources": sources, "bytesPerSource": record, "uboBytes": total})
    h, lane_h = 40, 100
    cpu_top, gpu_top = 20, 230
    cpu_y, gpu_y = cpu_top + 62, gpu_top + 62
    sample_x = (gpu[2][0] + gpu[2][1]) / 2
    cpu_right = max(cpu[-1][1] + inset, sample_x + 30)   # wide enough for the snapshot to leave it above the UBO

    f.rect(lane_x, cpu_top, cpu_right - lane_x, lane_h, FILL, LINE, 1.3, 10)
    f.text(lane_x + 14, cpu_top + 20, "CPU source owner", 14, "bold", BLUE)
    step_row(f, cpu_y, h, cpu_steps, cpu, (BLUE, BLUE, WHITE))
    f.rect(lane_x, gpu_top, gpu_right - lane_x, lane_h, FILL, LINE, 1.3, 10)
    f.text(lane_x + 14, gpu_top + 20, "GPU fountain", 14, "bold", GOLD_TEXT)
    step_row(f, gpu_y, h, gpu_steps, gpu, (GOLD_SOFT, GOLD, INK))

    ubo_y, ubo_h = (cpu_top + lane_h + gpu_top) / 2, 44
    title = "1 KiB wind UBO for that slot"
    ubo_w = measure(title, 15, "bold")[0] + 36
    node(f, sample_x - ubo_w / 2, ubo_y, ubo_w, ubo_h, title, kind="teal")

    f.arrow([(sample_x, cpu_top + lane_h), (sample_x, ubo_y - ubo_h / 2)], TEAL, 2)
    f.text(sample_x + 14, (cpu_top + lane_h + ubo_y - ubo_h / 2) / 2, "snapshot after this frame slot’s fence",
           14, "italic", GRAY)
    f.arrow([(sample_x, ubo_y + ubo_h / 2), (sample_x, gpu_y - h / 2)], TEAL, 2)
    f.text(sample_x + 14, (ubo_y + ubo_h / 2 + gpu_top) / 2, "read only", 14, "italic", GRAY)
    f.height = gpu_top + lane_h + 20
    return f


FIGURES = [wind_sources_from_cpu_to_gpu]
