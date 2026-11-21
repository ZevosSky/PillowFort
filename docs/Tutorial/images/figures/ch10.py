"""Chapter 10, Cameras and Depth: authored figures.

@author Gary Yang
@brief Figures for 10-Cameras-And-Depth.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def from_local_space_to_pixels():
    f = Figure("from-local-space-to-pixels", 760, 492,
               "The chain of spaces from local (object) space through world, view and clip space to the framebuffer. "
               "The model, view and projection matrices are computed on the CPU; the divide by w and the viewport are "
               "done by the GPU.",
               source="10-Cameras-And-Depth.md, section 1 (Four spaces, and the one you already know)")
    box_x, box_w, box_h = 24, 196, 44
    centre_x = box_x + box_w / 2
    first, step = 44, 92
    spaces = [("local (object) space", "a cube's corners, around its own centre"),
              ("world space", "right-handed, +Y up, metres — one space for the whole scene"),
              ("view space", "the camera at the origin, looking down −Z, +Y up"),
              ("clip space", "Vulkan's: x right, y DOWN, depth 0..1 after the divide"),
              ("framebuffer", "pixels")]
    steps = [("model matrix", "where this object is", "section 3; per draw", BLUE, BLUE),
             ("view matrix", "where the camera is", "section 4; per frame", BLUE, BLUE),
             ("projection matrix", "the lens", "section 2; per frame", BLUE, BLUE),
             ("divide by w, then the viewport", "", "the GPU does both", GOLD, GOLD_TEXT)]
    for i, (name, description) in enumerate(spaces):
        y = first + i * step
        node(f, box_x, y, box_w, box_h, name, kind="plain")
        f.text(box_x + box_w + 22, y, description, 15)
    for i, (name, what, note, color, ink) in enumerate(steps):
        top = first + i * step + box_h / 2
        bottom = first + (i + 1) * step - box_h / 2
        f.arrow([(centre_x, top + 2), (centre_x, bottom - 2)], color, 2.2, 12)
        y = (top + bottom) / 2
        box = f.text(centre_x + 20, y, name + (":" if what else ""), 15, "bold", ink)
        if what:
            f.text(box[2] + 6, y, what, 15)
        f.text(736, y, note, 13.5, "italic", GRAY, "end")
    # The key gets a row of its own below the chain, right-aligned with the notes, so it does not read as a space's
    # description.
    legend_y = first + 4 * step + box_h / 2 + 28
    entries = [(BLUE, "computed on the CPU"), (GOLD, "done on the GPU")]
    gap, swatch_w, label_gap = 30, 26, 8
    widths = [swatch_w + label_gap + measure(label, 13.5)[0] for _, label in entries]
    x = 736 - sum(widths) - gap * (len(entries) - 1)
    for (color, label), width in zip(entries, widths):
        f.arrow([(x, legend_y), (x + swatch_w, legend_y)], color, 2.2, 10)
        f.text(x + swatch_w + label_gap, legend_y, label, 13.5, fill=GRAY)
        x += width + gap
    return f


def yaw_and_pitch():
    yaw_deg, pitch_deg = 50.0, 30.0
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    # The chapter's forward vector for a no-roll orientation, and what yawPitchOf reads back from it.
    forward = (-math.cos(pitch) * math.sin(yaw), math.sin(pitch), -math.cos(pitch) * math.cos(yaw))
    assert abs(math.atan2(-forward[0], -forward[2]) - yaw) < 1e-9
    assert abs(math.asin(forward[1]) - pitch) < 1e-9
    # Yaw +90 degrees looks down -X, as the chapter's top view marks it.
    assert abs(-math.sin(math.radians(90)) + 1) < 1e-9 and abs(math.cos(math.radians(90))) < 1e-9

    f = Figure("yaw-and-pitch", 840, 366,
               "Two views of the camera's angles. Seen from above, with +Y towards you, yaw 0 looks down -Z and yaw grows "
               "turning left, reaching -X at yaw +90 degrees. Seen from the side, pitch is the angle of forward above the "
               "yaw direction: forward climbs sin(pitch) and keeps cos(pitch) along the ground.",
               kind="computed plot", source="10-Cameras-And-Depth.md, section 6 (Yaw and pitch)",
               parameters={"exampleYawDegrees": yaw_deg, "examplePitchDegrees": pitch_deg})

    # Seen from above: page x is world X, page down is world +Z.
    ox, oy, reach = 236, 196, 124  # leaves "the yaw direction" 32 px from the card edge
    f.text(ox, 26, "Seen from above (+Y towards you)", 15, fill=GRAY, anchor="middle")
    f.line([(ox, oy + reach), (ox, oy)], LINE, 1.5)
    f.arrow([(ox, oy), (ox, oy - reach)], INK, 1.8, 11)
    f.arrow([(ox, oy), (ox + reach, oy)], INK, 1.8, 11)
    f.arrow([(ox, oy), (ox - reach, oy)], INK, 1.8, 11)
    f.text(ox, oy - reach - 16, "−Z", 15, "bold", anchor="middle")
    f.text(ox + 9, oy - reach + 14, "yaw 0", 14, fill=GRAY)
    f.text(ox, oy + reach + 18, "+Z", 15, "bold", anchor="middle")
    f.text(ox + reach + 10, oy, "+X", 15, "bold")
    f.text(ox - reach - 10, oy, "−X", 15, "bold", anchor="end")
    f.text(ox - reach + 4, oy + 22, "yaw +90°", 14, fill=GRAY)

    heading = (forward[0], forward[2])  # its horizontal part, world X and Z
    size = math.hypot(*heading)
    tip = (ox + heading[0] / size * 104, oy + heading[1] / size * 104)
    f.arrow([(ox, oy), tip], BLUE, 2.6, 14)
    f.text(tip[0] - 4, tip[1] + 22, "the yaw direction", 14, fill=BLUE, anchor="end")
    radius = 50
    turn = [(ox - radius * math.sin(math.radians(a)), oy - radius * math.cos(math.radians(a)))
            for a in [yaw_deg * i / 24 for i in range(25)]]
    f.arrow(turn, TEAL, 1.7, 9)
    middle = math.radians(yaw_deg / 2)
    f.text(ox - 82 * math.sin(middle), oy - 82 * math.cos(middle), "yaw", 15, "bold", TEAL, "middle")
    f.circle(ox, oy, 8, WHITE, INK, 1.6)
    f.circle(ox, oy, 2.6, INK)

    # Seen from the side: page right is the yaw direction, page up is +Y.
    sx, sy, length = 496, 300, 230
    f.text(sx + 140, 26, "Seen from the side", 15, fill=GRAY, anchor="middle")
    f.arrow([(sx, sy), (sx, sy - 236)], INK, 1.8, 11)
    f.text(sx - 12, sy - 236, "+Y", 15, "bold", anchor="end")
    f.arrow([(sx, sy), (sx + 312, sy)], INK, 1.8, 11)
    f.text(sx + 312, sy + 26, "the yaw direction", 14, fill=GRAY, anchor="end")
    end = (sx + length * math.cos(pitch), sy - length * math.sin(pitch))
    f.line([(end[0], end[1]), (end[0], sy)], LINE, 1.3, "5 5")
    f.arrow([(sx, sy), end], BLUE, 2.6, 14)
    f.text(end[0] + 10, end[1] - 4, "forward", 15, "bold", BLUE)
    f.text(end[0] + 10, (end[1] + sy) / 2, "sin(pitch)", 14, fill=GRAY)
    f.text((sx + end[0]) / 2, sy + 26, "cos(pitch)", 14, fill=GRAY, anchor="middle")
    f.arc(sx, sy, 92, 0, pitch_deg, TEAL, 1.7)
    middle = pitch_deg / 2
    f.text(sx + 104 * math.cos(math.radians(middle)), sy - 104 * math.sin(math.radians(middle)), "pitch", 15, "bold", TEAL)
    f.circle(sx, sy, 5, INK, WHITE, 1.6)
    return f


FIGURES = [from_local_space_to_pixels, yaw_and_pitch]
