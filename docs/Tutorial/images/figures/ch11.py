"""Chapter 11, Meshes: authored figures.

@author Gary Yang
@brief Figures for 11-Meshes.md
@copyright (C) Gary 2026
"""
import math

from figure_kit import *


def runs(f, x, y, pieces, size=15):
    """Several pieces of text on one line, each in its own font and colour, separated by a space."""
    for string, font, fill in pieces:
        box = f.text(x, y, string, size, font, fill)
        x = box[2] + size * 0.45
    return x


def from_mesh_data_to_the_vertex_shader():
    f = Figure("from-mesh-data-to-the-vertex-shader", 860, 370,
               "The chain from scene::MeshData on the CPU, through uploadMesh to a GpuMesh's vertex and index buffers on "
               "the GPU, bound with vkCmdBindVertexBuffers and vkCmdBindIndexBuffer, read through the pipeline's vertex "
               "input state, to the layout(location = N) inputs of Mesh.vert.glsl.",
               source="11-Meshes.md, section 1 (From gl_VertexIndex to buffers)")
    box_x, box_w, box_h = 24, 196, 48
    centre_x = box_x + box_w / 2
    rows = [40, 136, 232, 328]
    right = 836
    boxes = [("scene::MeshData", "mono-bold", "pass", [[("CPU: vertices, indices, submeshes", "regular", INK)]], "sections 2-4, Scene/"),
             ("GpuMesh", "mono-bold", "data", [[("GPU: a vertex buffer and an index buffer", "regular", INK)]], ""),
             ("vertex input state", "bold", "plain", [[("baked into the pipeline: which bytes are", "regular", INK)],
                                                     [("which attribute, at which location", "regular", INK)]], "section 5, GpuMesh.cpp"),
             ("Mesh.vert.glsl", "mono-bold", "shader", [[("layout(location = N) in ...", "mono", INK)]], "section 9")]
    for y, (name, font, kind, description, where) in zip(rows, boxes):
        node(f, box_x, y, box_w, box_h, name, kind=kind, title_font=font)
        spread = 20 if len(description) > 1 else 0
        for i, pieces in enumerate(description):
            runs(f, box_x + box_w + 22, y - spread / 2 + i * spread, pieces)
        if where:
            f.text(right, y, where, 13.5, "italic", GRAY, "end")
    steps = [[("uploadMesh:", "mono", INK), ("staging buffer → two device-local buffers", "regular", INK)],
             [("vkCmdBindVertexBuffers, vkCmdBindIndexBuffer", "mono", INK)],
             []]
    notes = ["section 6, VulkanGraphics/", "section 11, SceneRenderer", ""]
    for a, b, pieces, note in zip(rows, rows[1:], steps, notes):
        top, bottom = a + box_h / 2, b - box_h / 2
        f.arrow([(centre_x, top + 2), (centre_x, bottom - 2)], GRAY, 2, 12)
        y = (top + bottom) / 2
        if pieces:
            runs(f, centre_x + 20, y, pieces)
        if note:
            f.text(right, y, note, 13.5, "italic", GRAY, "end")
    return f


def winding_on_the_monitor():
    f = Figure("winding-on-the-monitor", 720, 300,
               "Two triangles as they land on the monitor. On the left the corners 0, 1, 2 turn counter-clockwise, a front "
               "with COUNTER_CLOCKWISE. On the right 1 and 2 are swapped, so 0, 1, 2 turn clockwise, a front with CLOCKWISE.",
               source="11-Meshes.md, section 7 (Which side is the front)")

    def triangle(cx, corners, clockwise, caption, setting):
        top, bottom_left, bottom_right = (cx, 80), (cx - 92, 206), (cx + 92, 206)
        at = {0: top}
        at.update(corners(bottom_left, bottom_right))
        points = [at[0], at[1], at[2]]
        f.polygon(points, BLUE_FILL, BLUE, 1.6)
        for i in range(3):
            a, b = points[i], points[(i + 1) % 3]
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            f.arrow([(mid[0] - ux * 14, mid[1] - uy * 14), (mid[0] + ux * 6, mid[1] + uy * 6)], BLUE, 2.2, 13)
        centroid = (sum(p[0] for p in points) / 3, sum(p[1] for p in points) / 3)
        # A turn arrow around the centroid; page y is down, so counter-clockwise on screen is a growing angle here.
        sweep = [(-1 if clockwise else 1) * a for a in range(0, 271, 10)]
        f.arrow([(centroid[0] + 22 * math.cos(math.radians(110 + s)), centroid[1] - 22 * math.sin(math.radians(110 + s)))
                 for s in sweep], TEAL, 1.8, 9)
        for index, (x, y) in at.items():
            f.circle(x, y, 5, BLUE, WHITE, 1.6)
        f.text(at[0][0], at[0][1] - 19, "0", 16, "bold", anchor="middle")
        for index in (1, 2):
            x, y = at[index]
            f.text(x + (-16 if x < cx else 16), y + 4, str(index), 16, "bold", anchor="middle")
        f.text(cx, 28, "on the monitor", 14, "italic", GRAY, "middle")
        f.text(cx, 246, caption, 15, anchor="middle")
        setting_width = measure(setting, 15, "mono")[0]
        lead = "front, with"
        lead_width = measure(lead, 15)[0]
        start = cx - (lead_width + 6 + setting_width) / 2
        box = f.text(start, 272, lead, 15)
        f.text(box[2] + 6, 272, setting, 15, "mono")

    triangle(180, lambda bl, br: {1: bl, 2: br}, False, "0 → 1 → 2 turns counter-clockwise", "COUNTER_CLOCKWISE")
    triangle(540, lambda bl, br: {2: bl, 1: br}, True, "0 → 1 → 2 turns clockwise", "CLOCKWISE")
    return f


def normals_under_a_squash():
    squash = 0.5
    point = (math.cos(math.radians(45)), math.sin(math.radians(45)))
    moved = (point[0], point[1] * squash)
    wrong = (point[0], point[1] * squash)          # the normal times the model matrix
    right = (point[0], point[1] / squash)          # the normal times the inverse-transpose
    wrong = tuple(c / math.hypot(*wrong) for c in wrong)
    right = tuple(c / math.hypot(*right) for c in right)
    wrong_angle, right_angle = (math.degrees(math.atan2(v[1], v[0])) for v in (wrong, right))
    # The chapter's numbers: 45 degrees and (0.71, 0.71) before; 63 degrees, (0.45, 0.89) true; 27 degrees, (0.89, 0.45) wrong.
    assert (round(point[0], 2), round(point[1], 2)) == (0.71, 0.71)
    assert (round(right[0], 2), round(right[1], 2)) == (0.45, 0.89) and round(right_angle) == 63
    assert (round(wrong[0], 2), round(wrong[1], 2)) == (0.89, 0.45) and round(wrong_angle) == 27
    # The true normal is the ellipse's gradient (x, y / squash^2), so it is perpendicular to the squashed surface.
    gradient = (moved[0], moved[1] / squash ** 2)
    assert abs(math.atan2(gradient[1], gradient[0]) - math.radians(right_angle)) < 1e-9

    f = Figure("normals-under-a-squash", 880, 292,
               "A sphere's cross-section with the normal at a point 45 degrees up, (0.71, 0.71). After scale(1, 0.5, 1) the "
               "surface there is flatter: its true normal is 63 degrees up, (0.45, 0.89), while the model matrix gives 27 "
               "degrees up, (0.89, 0.45), tilted the wrong way.",
               kind="computed plot", source="11-Meshes.md, section 13 (How normals move: the normal matrix)",
               parameters={"scale": [1, squash, 1], "trueNormalDegrees": round(right_angle, 2),
                           "modelMatrixNormalDegrees": round(wrong_angle, 2)})
    radius, reach, cy = 92, 84, 150

    def shape(cx, ry, caption):
        f.add(f'<ellipse cx="{number(cx)}" cy="{number(cy)}" rx="{radius}" ry="{number(ry)}" fill="{FILL}" stroke="{INK}" stroke-width="1.8"/>')
        f.text(cx, 270, caption, 15, fill=GRAY, anchor="middle")

    def normal(px, py, direction, color, dash=None):
        f.arrow([(px, py), (px + direction[0] * reach, py - direction[1] * reach)], color, 2.6, 14, dash)

    def angle(px, py, degrees, color, r, label, label_r, label_at):
        f.arc(px, py, r, 0, degrees, color, 1.4)
        f.text(px + label_r * math.cos(math.radians(label_at)), py - label_r * math.sin(math.radians(label_at)),
               label, 13.5, "bold", color, "middle")

    # Before: the sphere.
    cx = 130
    shape(cx, radius, "before: a sphere")
    px, py = cx + radius * point[0], cy - radius * point[1]
    f.line([(px, py), (px + 74, py)], LINE, 1.2, "4 4")
    angle(px, py, 45, INK, 30, "45°", 47, 22.5)
    normal(px, py, point, INK)
    f.circle(px, py, 5, INK, WHITE, 1.6)

    # After: squashed to half its height about the same centre.
    cx = 390
    shape(cx, radius * squash, "after scale(1, 0.5, 1)")
    px, py = cx + radius * moved[0], cy - radius * moved[1]
    f.line([(px, py), (px + 84, py)], LINE, 1.2, "4 4")
    angle(px, py, wrong_angle, RED, 62, "27°", 84, wrong_angle / 2)
    angle(px, py, right_angle, TEAL, 40, "63°", 58, 45)
    normal(px, py, wrong, RED, "7 5")
    normal(px, py, right, TEAL)
    f.circle(px, py, 5, INK, WHITE, 1.6)

    # The key.
    x = 566
    rows = [(INK, None, "normal at ●: 45° up", "(0.71, 0.71)"),
            (TEAL, None, "true normal: 63° up", "(0.45, 0.89)"),
            (RED, "7 5", "model matrix: 27° up", "(0.89, 0.45): tilted the wrong way")]
    for i, (color, dash, label, value) in enumerate(rows):
        y = 46 + i * 58
        f.arrow([(x, y + 18), (x + 26, y - 2)], color, 2.4, 10, dash)
        f.text(x + 40, y, label, 15)
        f.text(x + 40, y + 20, value, 15, fill=GRAY)
    f.text(x, 236, "At ●, squashing made the surface flatter,", 13.5, "italic", GRAY)
    f.text(x, 256, "so its true normal is steeper.", 13.5, "italic", GRAY)
    return f


FIGURES = [from_mesh_data_to_the_vertex_shader, winding_on_the_monitor, normals_under_a_squash]
