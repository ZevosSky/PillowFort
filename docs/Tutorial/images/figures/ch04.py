"""Chapter 04, Commands and Synchronization: authored figures.

@author Gary Yang
@brief Figures for 04-Commands-And-Synchronization.md
@copyright (C) Gary 2026
"""
from figure_kit import *

MONO_ADVANCE = 1233 / 2048  # DejaVu Sans Mono's advance per unit of size, for text that continues in another font


def frames_without_overlap():
    f = Figure("frames-without-overlap", 880, 300,
               "Timeline of two frames without overlap. The CPU records and then waits while the GPU, idle during "
               "recording, executes, so each processor is idle about half the time. The CPU's wait ends when execution "
               "does; on a third lane the presentation engine presents each frame after that, while the CPU records "
               "the next one.",
               source="04-Commands-And-Synchronization.md, section 2 (Frames in flight)")
    x0, x1 = 120, 856
    k = (x1 - x0) / 58
    for a, b, label in [(0, 29, "frame N"), (29, 58, "frame N+1")]:
        left, right = x0 + a * k + 4, x0 + b * k - 4
        f.text((left + right) / 2, 26, label, 14, fill=GRAY, anchor="middle")
        f.line([(left, 46), (left, 40), (right, 40), (right, 46)], LINE, 1.2)
    # The fence covers execution only, so the CPU's wait ends where execute ends; presenting is
    # the presentation engine's work, after that, and nothing here waits for it.
    lanes = [("CPU", 54, 52, [("record", 0, 13, "busy"), ("wait", 13, 29, "idle"), ("record", 29, 42, "busy"),
                              ("wait", 42, 58, "idle")]),
             ("GPU", 118, 52, [("idle", 0, 13, "idle"), ("execute", 13, 29, "run"), ("idle", 29, 42, "idle"),
                               ("execute", 42, 58, "run")]),
             (None, 182, 44, [("present N-1", 0, 13, "show"), ("present N", 29, 42, "show")])]
    looks = {"busy": (BLUE, BLUE, "white", "bold", None), "run": (GOLD_SOFT, GOLD, INK, "bold", None),
             "show": (FILL, LINE, INK, "regular", None), "idle": (WHITE, LINE, GRAY, "italic", "5 5")}
    for lane, y, h, blocks in lanes:
        if lane:
            f.text(102, y + h / 2, lane, 16, "bold", anchor="end")
        else:
            f.lines(102, y + h / 2 - 9, ["presentation", "engine"], 13.5, "bold", anchor="end", spacing=17)
        for label, a, b, look in blocks:
            fill, stroke, ink, font, dash = looks[look]
            f.rect(x0 + a * k + 2, y, (b - a) * k - 4, h, fill, stroke, 1.3, 7, dash)
            f.text(x0 + (a + b) / 2 * k, y + h / 2, label, 15, font, ink, "middle")
    f.arrow([(x0 + 2, 250), (x1 - 2, 250)], LINE)
    f.text((x0 + x1) / 2, 274, "time", 14, fill=GRAY, anchor="middle")
    return f


def barrier_scopes_on_the_queue():
    f = Figure("barrier-scopes-on-the-queue", 880, 252,
               "The queue in submission order: frame N-1's command buffer, where pass A writes X and pass B reads X, then "
               "frame N's, where a barrier comes before pass A writes X again. Everything ahead of the barrier on the queue, "
               "last frame's command buffer included, is before the barrier; everything after it is after the barrier.",
               source="04-Commands-And-Synchronization.md, section 5 (What \"before\" and \"after\" cover)")
    label = f.text(24, 28, "the queue, in submission order", 14, fill=GRAY)
    f.arrow([(label[2] + 14, 28), (856, 28)], LINE)

    top, bottom, block_top, block_h = 52, 156, 92, 48
    buffers = [(24, 428, "frame N-1’s command buffer"), (440, 856, "frame N’s command buffer")]
    for left, right, name in buffers:
        f.rect(left, top, right - left, bottom - top, FILL, LINE, 1.3, 10)
        f.text(left + 14, top + 20, name, 14, fill=GRAY)

    def block(left, right, title, kind="pass"):
        fill, stroke, ink = {"pass": (BLUE_FILL, BLUE, INK), "barrier": (TEAL, TEAL, WHITE)}[kind]
        f.rect(left, block_top, right - left, block_h, fill, stroke, 1.4, 8)
        f.text((left + right) / 2, block_top + block_h / 2, title, 15, "bold", ink, "middle")

    block(38, 226, "pass A writes X")
    block(238, 414, "pass B reads X")
    barrier_left, barrier_right = 454, 556
    block(barrier_left, barrier_right, "BARRIER", "barrier")
    block(568, 778, "pass A writes X again")
    f.rect(790, block_top, 52, block_h, WHITE, LINE, 1.3, 8, "5 5")
    f.text(816, block_top + block_h / 2, "...", 15, "bold", GRAY, "middle")

    # One divider through the barrier: the two scopes meet there and do not overlap.
    split = (barrier_left + barrier_right) / 2
    f.line([(split, block_top + block_h + 4), (split, 208)], TEAL, 1.6, "5 4")
    rule = 180
    for left, right, name, scope in [(24, split - 6, "before the barrier", "the first synchronization scope"),
                                     (split + 6, 856, "after the barrier", "the second synchronization scope")]:
        f.line([(left, rule - 7), (left, rule), (right, rule), (right, rule - 7)], TEAL, 1.6)
        f.text((left + right) / 2, rule + 22, name, 15, "bold", TEAL, "middle")
        f.text((left + right) / 2, rule + 44, scope, 13.5, "italic", GRAY, "middle")
    return f


def acquire_wait_and_first_barrier():
    f = Figure("acquire-wait-and-first-barrier", 740, 250,
               "The acquire signals imageAvailable, which the submit waits on at COLOR_ATTACHMENT_OUTPUT. An arrow leads "
               "down from that wait to the frame's first barrier, whose srcStageMask names the same stage, and on to the "
               "layout transition and the draw.",
               source="04-Commands-And-Synchronization.md, section 5 (Barriers next to semaphores)")
    stage = "COLOR_ATTACHMENT_OUTPUT"
    top, low, h = 52, 198, 56

    def box(x, w, y, kind="plain"):
        fill, stroke = {"plain": (FILL, LINE), "teal": (TEAL_FILL, TEAL)}[kind]
        f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)

    box(24, 132, top)
    f.text(90, top, "acquire", 15, "bold", anchor="middle")
    box(266, 180, top)
    f.text(356, top, "imageAvailable", 15, "mono-bold", anchor="middle")
    f.arrow([(156, top), (266, top)])
    f.text(211, top - 14, "signals", 13.5, "italic", GRAY, "middle")

    # The barrier sits under the semaphore, so the wait's arrow runs straight down into it.
    barrier_x, barrier_w = 24, 360
    box(barrier_x, barrier_w, low, "teal")
    f.text(barrier_x + barrier_w / 2, low - 12, "first barrier", 15, "bold", anchor="middle")
    prefix = "srcStageMask = "
    width = measure(prefix + stage, 14, "mono")[0]
    start = barrier_x + (barrier_w - width) / 2
    f.text(start, low + 13, prefix, 14, "mono", GRAY)
    f.text(start + len(prefix) * 14 * MONO_ADVANCE, low + 13, stage, 14, "mono-bold", TEAL)

    f.arrow([(356, top + h / 2), (356, low - h / 2)], TEAL, 2.2, 13)
    note = f.text(372, (top + low) / 2, "waited at ", 15, fill=INK)
    f.text(note[2] + 4, (top + low) / 2, stage, 14, "mono-bold", TEAL)

    box(428, 168, low)
    f.text(512, low, "layout transition", 15, "bold", anchor="middle")
    box(632, 84, low)
    f.text(674, low, "draw", 15, "bold", anchor="middle")
    f.arrow([(barrier_x + barrier_w, low), (428, low)])
    f.arrow([(596, low), (632, low)])
    return f


FIGURES = [frames_without_overlap, barrier_scopes_on_the_queue, acquire_wait_and_first_barrier]
