"""Chapter 37, Objects at a Distance: authored figures.

@author Gary Yang
@brief Figures for 37-Objects-At-A-Distance.md
@copyright (C) Gary 2026
"""
from pathlib import Path
import re

from figure_kit import *

CHAPTER = Path(__file__).resolve().parents[2] / "37-Objects-At-A-Distance.md"


def square_of(camera_cell, side):
    """The cells of the pool's square along one axis: side / 2 before the camera's cell, side / 2 - 1 after it."""
    return list(range(camera_cell - side // 2, camera_cell + side // 2))


def cells_and_slots_of_the_tree_pool():
    text = CHAPTER.read_text(encoding="utf-8")
    slots = int(re.search(r"TREE_SLOTS = (\d+);", text).group(1))
    assert slots == 76 and square_of(0, slots)[0] == -38 and square_of(0, slots)[-1] == 37  # "38 behind, 37 ahead"
    side = 6   # section 7's example: six slots in place of 76
    before, after = square_of(3, side), square_of(4, side)
    assert before == [0, 1, 2, 3, 4, 5] and after == [1, 2, 3, 4, 5, 6]
    assert [c % side for c in after] == [1, 2, 3, 4, 5, 0]   # the chapter's second slot row

    f = Figure("cells-and-slots-of-the-tree-pool", 784, 412,
               "Six slots in place of 76: with the camera in cell 3, the square is cells 0 to 5, in slots 0 to 5. When "
               "the camera crosses into cell 4, the square is cells 1 to 6, and cell 6 takes slot 0, which cell 0 has "
               "left.",
               source="37-Objects-At-A-Distance.md, section 7 (A pool that wraps round)",
               parameters={"slotsInTheExample": side, "slotsInTheChapter": slots})
    x0, cell_w, cell_h, slot_h = 106, 76, 40, 32
    shown = range(0, 7)   # the world's cells 0 to 6, at the same place in both panels

    def cx(cell):
        return x0 + (cell + 0.5) * cell_w

    def panel(top, camera, square, heading, moved=None):
        f.text(24, top, heading, 15)
        row, slot_row = top + 70, top + 70 + cell_h / 2 + 12 + slot_h / 2
        left, right = x0 + square[0] * cell_w, x0 + (square[-1] + 1) * cell_w
        bracket = row - cell_h / 2 - 9
        f.line([(left + 3, bracket + 6), (left + 3, bracket), (right - 3, bracket), (right - 3, bracket + 6)], LINE, 1.2)
        f.text((left + right) / 2, bracket - 11, "the square", 13.5, "italic", GRAY, "middle")
        f.text(x0 - 16, row, "cell", 15, "bold", anchor="end")
        f.text(x0 - 16, slot_row, "slot", 15, "bold", GOLD_TEXT, "end")
        for cell in shown:
            inside = cell in square
            fill, stroke, dash = (TEAL_FILL, TEAL, None) if cell == camera else \
                (FILL, LINE, None) if inside else (WHITE, HAIR, "5 4")
            f.rect(cx(cell) - cell_w / 2 + 3, row - cell_h / 2, cell_w - 6, cell_h, fill, stroke, 1.4, 6, dash)
            ink = TEAL if cell == camera else INK if inside else LINE
            f.text(cx(cell) - (9 if cell == camera else 0), row, str(cell), 16, "bold", ink, "middle")
            if cell == camera:
                f.circle(cx(cell) + 14, row, 6, INK, WHITE, 2)
            if inside:
                fresh = cell == moved
                f.rect(cx(cell) - 20, slot_row - slot_h / 2, 40, slot_h, GOLD if fresh else GOLD_FILL, GOLD, 1.4, 6)
                f.text(cx(cell), slot_row, str(cell % side), 15, "bold", WHITE if fresh else INK, "middle")
        return slot_row

    panel(28, 3, before, "the camera in cell 3: the square is cells 0 to 5")
    slot_row = panel(214, 4, after, "the camera crosses into cell 4: the square is cells 1 to 6", moved=6)

    # Slot 0 leaves cell 0, now outside the square, and holds cell 6.
    f.rect(cx(0) - 20, slot_row - slot_h / 2, 40, slot_h, WHITE, LINE, 1.3, 6, "5 4")
    f.text(cx(0), slot_row, "0", 15, "bold", LINE, "middle")
    low = slot_row + slot_h / 2 + 22
    f.arrow([(cx(0), slot_row + slot_h / 2 + 4), (cx(0), low), (cx(6), low), (cx(6), slot_row + slot_h / 2 + 4)], GOLD, 1.9, 11)
    f.text((cx(0) + cx(6)) / 2, low + 20, "cell 6 takes slot 0, which cell 0 has left", 15, fill=GOLD_TEXT, anchor="middle")

    lx = x0 + 7 * cell_w + 22
    f.circle(lx + 6, 98, 6, INK, WHITE, 2)
    f.text(lx + 20, 98, "the camera", 14, fill=GRAY)
    return f


FIGURES = [cells_and_slots_of_the_tree_pool]
