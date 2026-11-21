"""Chapter 09, The Demo Harness: authored figures.

@author Gary Yang
@brief Figures for 09-Demo-Harness.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def demo_switch_sequence():
    f = Figure("demo-switch-sequence", 880, 348,
               "Switching demos: request a demo, wait for previous GPU use, deactivate and tear down the old demo, set up "
               "the candidate, resize it, and only then publish the active pointer. A failure in Setup or Resize tears "
               "the candidate down, retains the error and leaves no active demo.",
               source="09-Demo-Harness.md, section 5 (switchDemo)")
    w, h = 220, 58
    columns = [24, 330, 636]
    first, second, failed = 54, 176, 296
    looks = {"input": (WHITE, LINE, INK), "pass": (BLUE_FILL, BLUE, INK), "teal": (TEAL_FILL, TEAL, TEAL)}

    def step(x, y, lines, kind="pass"):
        fill, stroke, ink = looks[kind]
        f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
        f.lines(x + w / 2, y - (len(lines) - 1) * 10, lines, 15, "bold", ink, "middle", 20)

    step(columns[0], first, ["request a demo"], "input")
    step(columns[1], first, ["wait for previous", "GPU use"])
    step(columns[2], first, ["deactivate / tear down", "old demo"])
    step(columns[0], second, ["Setup candidate"])
    step(columns[1], second, ["Resize candidate"])
    step(columns[2], second, ["publish active pointer"], "teal")
    for row in (first, second):
        for a, b in zip(columns, columns[1:]):
            f.arrow([(a + w, row), (b, row)])
    # The sequence wraps from the end of the first row to the start of the second.
    turn = (first + second) / 2
    f.arrow([(columns[2] + w / 2, first + h / 2), (columns[2] + w / 2, turn),
             (columns[0] + w / 2, turn), (columns[0] + w / 2, second - h / 2)])

    left, right = columns[0], columns[1] + w
    f.rect(left, failed - h / 2, right - left, h, WHITE, RED, 1.5, 10)
    f.text((left + right) / 2, failed - 10, "tear down candidate, retain error,", 15, anchor="middle")
    f.text((left + right) / 2, failed + 10, "leave no active demo", 15, anchor="middle")
    for x in (columns[0] + w / 2, columns[1] + w / 2):
        f.arrow([(x, second + h / 2), (x, failed - h / 2)], RED, 1.7)
        f.text(x + 12, (second + failed) / 2, "failure", 13.5, "italic", RED)
    return f


FIGURES = [demo_switch_sequence]
