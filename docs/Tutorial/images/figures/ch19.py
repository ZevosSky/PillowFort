"""Chapter 19, Instancing and Indirect Draws: authored figures.

@author Gary Yang
@brief Figures for 19-Instancing-And-Indirect.md
@copyright (C) Gary 2026
"""
from figure_kit import *


def runs(f, x, y, parts, size=15, anchor="start"):
    """One line made of (text, font, colour) runs, such as prose with a code name in it. A run that starts with a
    space gets a wider gap before it, as after a colon."""
    leads = [size * 0.3 if text.startswith(" ") else 0.0 for text, _, _ in parts]
    parts = [(text.lstrip(), font, colour) for text, font, colour in parts]
    widths = [measure(text, size, font)[0] for text, font, _ in parts]
    gap = size * 0.36
    total = sum(widths) + sum(leads) + gap * (len(parts) - 1)
    left = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
    for (text, font, colour), width, lead in zip(parts, widths, leads):
        left += lead
        f.text(left, y, text, size, font, colour)
        left += width + gap
    return left - gap


def plate(f, x, y, w, h, lines, kind="plain", size=14.5):
    """A box centred vertically on y holding one or two lines, each a list of (text, font) runs."""
    fill, stroke = {"plain": (FILL, LINE), "pass": (BLUE_FILL, BLUE), "data": (GOLD_FILL, GOLD),
                    "shader": (FILL, LINE)}[kind]
    f.rect(x, y - h / 2, w, h, fill, stroke, 1.4, 10)
    first = y - (len(lines) - 1) * 10
    for i, parts in enumerate(lines):
        runs(f, x + w / 2, first + 20 * i, [(t, fnt, INK if i == 0 or kind != "data" else GRAY) for t, fnt in parts],
             size if i == 0 or kind != "data" else 13, "middle")


def from_draw_items_to_indirect_draws():
    f = Figure("from-draw-items-to-indirect-draws", 880, 664,
               "Scene::CollectDraws makes the list of DrawItems; PrepareDraws sorts it, writes every item's matrices to "
               "the instance buffer, and makes one indirect command per run of equal items and one DrawRun per run of "
               "commands with the same material, cull mode and front face. RecordBatches binds the shared vertex and "
               "index buffers once, then per DrawRun binds its pipeline and material and issues one "
               "vkCmdDrawIndexedIndirect, and Mesh.vert.glsl reads each instance's model matrix by gl_InstanceIndex.",
               source="19-Instancing-And-Indirect.md, What you are actually writing")
    left_w, gold_x = 412, 500
    gold_w = 856 - gold_x
    mono, sans, bold = "mono", "regular", "bold"

    # Chapter 12's list is the input, unchanged.
    top = 48
    plate(f, 24, top, 228, 44, [[("Scene::CollectDraws", "mono-bold")]], "pass")
    plate(f, 296, top, 150, 44, [[("DrawItem[]", "mono-bold")]], "data")
    f.arrow([(252, top), (296, top)])
    f.lines(462, top - 9, ["Chapter 12: one per visible submesh,", "culled per node"], 13.5, "italic", GRAY, spacing=19)

    def divider(y, parts):
        width = sum(measure(t, 14, fnt)[0] for t, fnt, _ in parts) + 14 * 0.36 * (len(parts) - 1)
        f.line([(24, y), (856 - width - 14, y)], HAIR, 1.4)   # the rule stops short of its label
        runs(f, 856, y, parts, 14, "end")

    divider(100, [("SceneRenderer, in the demo's", sans, GRAY), ("Record", mono, GRAY)])

    # PrepareDraws, on the CPU: one sort, then one walk over the sorted list that makes three things together, so the
    # three rows hang off one rail from the sort rather than following from each other.
    runs(f, 24, 132, [("PrepareDraws", "mono-bold", INK), ("(sections 3-6), on the CPU", sans, GRAY)], 15)
    s1, s2, s3, s4 = 178, 242, 306, 376
    plate(f, 24, s1, 832, 46, [[("sort by", sans), ("(cutout?, doubleSided?, mirrored?, material, mesh, submesh),", mono)],
                               [("so equal items sit together", "italic")]])
    f.arrow([(371, top + 22), (371, s1 - 23)])
    rail_x, row_x = 40, 64
    row_w = 24 + left_w - row_x
    plate(f, row_x, s2, row_w, 44, [[("every item's matrices", sans)]])
    plate(f, gold_x, s2, gold_w, 50, [[("the instance buffer", bold)], [("set 0 binding 2, in sorted order", sans)]], "data")
    plate(f, row_x, s3, row_w, 44, [[("every run of equal items", sans)]])
    plate(f, gold_x, s3, gold_w, 50, [[("ONE", bold), ("VkDrawIndexedIndirectCommand", "mono-bold")],
                                      [("instanceCount = its length", mono)]], "data")
    plate(f, row_x, s4, row_w, 58, [[("every run of commands with the same", sans)],
                                    [("material, cull mode, and front face", sans)]])
    assert measure("every run of commands with the same", 14.5)[0] + 40 < row_w
    plate(f, gold_x, s4, gold_w, 50, [[("one", bold), ("DrawRun", "mono-bold")]], "data")
    for y in (s2, s3, s4):
        f.arrow([(24 + left_w, y), (gold_x, y)])
    f.line([(rail_x, s1 + 23), (rail_x, s3)], GRAY, 1.5)
    for y in (s2, s3):
        f.arrow([(rail_x, y), (row_x, y)], GRAY, 1.5, 9)
    f.arrow([(rail_x, s3), (rail_x, s4), (row_x, s4)], GRAY, 1.5, 9)

    # RecordDraws / RecordBatches, into the command buffer.
    runs(f, 24, 440, [("RecordDraws / RecordBatches", "mono-bold", INK), ("(section 6), into the command buffer", sans, GRAY)],
         15)
    r1, r2 = 486, 556
    plate(f, 24, r1, left_w, 44, [[("bind the shared vertex and index buffers", sans)]], "pass")
    f.text(24 + left_w + 14, r1, "once (section 4)", 13.5, "italic", GRAY)
    # Full width, so the gold arrow from the DrawRun above lands on its top edge.
    plate(f, 24, r2, 832, 44, [[("per", sans), ("DrawRun:", mono), (" bind its pipeline and material, then ONE", sans),
                                ("vkCmdDrawIndexedIndirect", mono)]], "pass")
    f.arrow([(24 + left_w / 2, r1 + 22), (24 + left_w / 2, r2 - 22)])
    drop_x = gold_x + gold_w / 2
    assert 24 + 10 < drop_x < 24 + 832 - 10   # clear of the plate's rounded corners
    f.arrow([(drop_x, s4 + 25), (drop_x, r2 - 22)], GOLD, 1.8)

    # The vertex shader reads each instance's matrix from the buffer.
    f.line([(24, 596), (856, 596)], HAIR, 1.4)
    shader = [("Mesh.vert.glsl:", "mono-bold"), (" instances[gl_InstanceIndex].model", mono)]
    width = sum(measure(t, 14.5, fnt)[0] for t, fnt in shader) + 14.5 * 0.36 + 40
    plate(f, 24, 628, width, 40, [shader], "shader")
    return f


def the_sort_key_and_what_it_picks():
    f = Figure("the-sort-key-and-what-it-picks", 820, 196,
               "The sort key, cutout?, doubleSided?, mirrored?, material, mesh, submesh: cutout picks the pipeline, "
               "doubleSided the cull mode, mirrored the front face, material set 1, and mesh with submesh the command. "
               "The first four are the same for a whole run of commands, which is bound once.",
               source="19-Instancing-And-Indirect.md, section 5 (Batching the draw list)")
    fields = ["cutout?", "doubleSided?", "mirrored?", "material", "mesh", "submesh"]
    picks = [("pipeline", [0]), ("cull", [1]), ("front face", [2]), ("set 1", [3]), ("command", [4, 5])]
    widths = [measure(name, 15, "mono-bold")[0] + 30 for name in fields]
    gap, paren = 10, 18
    total = sum(widths) + gap * (len(fields) - 1) + 2 * paren
    x = (820 - total) / 2
    row, h = 92, 44
    f.text(x + 4, row, "(", 26, "mono", GRAY, "middle")
    boxes = []
    left = x + paren
    for name, width in zip(fields, widths):
        node(f, left, row, width, h, name, kind="plain", title_font="mono-bold")
        boxes.append((left, left + width))
        left += width + gap
    f.text(left - gap + paren - 4, row, ")", 26, "mono", GRAY, "middle")

    # Below: what each field picks, as the chapter lines them up.
    rule = row + h / 2 + 14
    for label, members in picks:
        a, b = boxes[members[0]][0] + 6, boxes[members[-1]][1] - 6
        f.line([(a, rule - 6), (a, rule), (b, rule), (b, rule - 6)], LINE, 1.4)
        f.text((a + b) / 2, rule + 22, label, 15, "bold", INK, "middle")

    # Above: what a run of commands shares, so section 6 binds it once.
    rule = row - h / 2 - 14
    a, b = boxes[0][0] + 6, boxes[3][1] - 6
    f.line([(a, rule + 6), (a, rule), (b, rule), (b, rule + 6)], TEAL, 1.6)
    f.text((a + b) / 2, rule - 20, "the same for a whole run of commands: bound once", 14, "bold", TEAL, "middle")
    return f


def two_commands_in_the_shared_buffers():
    # Section 5's trace: three sorted items share a material and rasterizer state, two copies of the same submesh of
    # mesh A and one submesh of mesh B. They fill instance slots 0, 1 and 2 and make two commands in one run.
    items = ["A", "A", "B"]
    commands = []
    for slot, mesh in enumerate(items):
        if commands and commands[-1]["mesh"] == mesh:
            commands[-1]["instanceCount"] += 1
        else:
            commands.append({"mesh": mesh, "instanceCount": 1, "firstInstance": slot})
    assert [(c["mesh"], c["firstInstance"], c["instanceCount"]) for c in commands] == [("A", 0, 2), ("B", 2, 1)]

    f = Figure("two-commands-in-the-shared-buffers", 880, 504,
               "Section 5's trace in the shared buffers. The vertex buffer holds mesh A's vertices from A's vertexOffset "
               "and mesh B's from B's; the index buffer holds A's two submeshes from A's firstIndex and B's submesh from "
               "B's. Command A draws A's submesh 1: firstIndex is mesh.firstIndex plus submesh.firstIndex, vertexOffset "
               "is mesh.vertexOffset, and firstInstance 0 with instanceCount 2 reads instance slots 0 and 1. Command B "
               "draws B's submesh 0 with firstInstance 2 and instanceCount 1, slot 2. The two commands form one run.",
               source="19-Instancing-And-Indirect.md, section 5 (Batching the draw list)",
               parameters={"items": items, "commands": commands})
    left, right = 172, 856
    a_fill, a_line, a_text = GOLD_FILL, GOLD, GOLD_TEXT
    b_fill, b_line, b_text = TEAL_FILL, TEAL, TEAL

    def name(y, title, note):
        f.text(24, y - 9, title, 14.5, "bold")
        f.text(24, y + 11, note, 12.5, fill=GRAY)

    def segment(x0, x1, y, fill, stroke, label, dash=None, label_fill=INK):
        f.rect(x0, y - 18, x1 - x0, 36, fill, stroke, 1.4, 0, dash)
        f.text((x0 + x1) / 2, y, label, 13.5, fill=label_fill, anchor="middle")

    def tick(x, y, label, colour, above):
        if above:
            f.line([(x, y - 18), (x, y - 30)], colour, 1.6)
            f.text(x + 5, y - 30, label, 13, fill=colour)
        else:
            f.line([(x, y + 18), (x, y + 30)], colour, 1.6)
            f.text(x + 5, y + 30, label, 13, fill=colour)

    # The vertex buffer: each mesh at its own vertexOffset; above a strip, where a MeshRange starts.
    vy = 70
    name(vy, "vertex buffer", "shared, section 4")
    a_end, b_end = 440, 620
    segment(left, a_end, vy, a_fill, a_line, "mesh A's vertices")
    segment(a_end, b_end, vy, b_fill, b_line, "mesh B's vertices")
    segment(b_end, right, vy, FILL, LINE, "unused capacity", "5 4", GRAY)
    tick(left, vy, "mesh A's vertexOffset", a_text, True)
    tick(a_end, vy, "mesh B's vertexOffset", b_text, True)

    # The index buffer: A's two submeshes, then B's one; below a strip, where a command points.
    iy = 170
    name(iy, "index buffer", "shared, section 4")
    sub, a_end, b_end = 302, 500, 660
    segment(left, sub, iy, FILL, a_line, "A, submesh 0")
    segment(sub, a_end, iy, a_fill, a_line, "A, submesh 1")
    segment(a_end, b_end, iy, b_fill, b_line, "B, submesh 0")
    segment(b_end, right, iy, FILL, LINE, "unused capacity", "5 4", GRAY)
    tick(left, iy, "mesh A's firstIndex", a_text, True)
    tick(a_end, iy, "mesh B's firstIndex", b_text, True)
    tick(sub, iy, "command A's firstIndex", a_text, False)
    tick(a_end + 2, iy, "command B's firstIndex", b_text, False)

    # The instance buffer: one slot per item, in sorted order.
    ny = 270
    name(ny, "instance buffer", "set 0 binding 2")
    slot = 100
    for i, mesh in enumerate(items):
        fill, stroke = (a_fill, a_line) if mesh == "A" else (b_fill, b_line)
        segment(left + i * slot, left + (i + 1) * slot, ny, fill, stroke, f"slot {i}: {mesh}")
    segment(left + len(items) * slot, right, ny, FILL, LINE, "slots of later commands", "5 4", GRAY)
    tick(left, ny, "command A's firstInstance", a_text, False)
    tick(left + 2 * slot, ny, "command B's firstInstance", b_text, False)

    # The two commands, as section 5's code fills them.
    def card(x, w, fill, stroke, title, values):
        top = 330
        f.rect(x, top, w, 138, fill, stroke, 1.4, 10)
        f.text(x + 16, top + 22, title, 14, "bold")
        fields = ["indexCount", "instanceCount", "firstIndex", "vertexOffset", "firstInstance"]
        for i, (field, value) in enumerate(zip(fields, values)):
            f.text(x + 16, top + 46 + 18 * i, f"{field} = {value}", 12.5, "mono")

    card(24, 408, a_fill, a_line, "command A: two copies of A's submesh 1",
         ["submesh.indexCount", "2", "mesh.firstIndex + submesh.firstIndex", "mesh.vertexOffset", "0"])
    card(448, 408, b_fill, b_line, "command B: one copy of B's submesh 0",
         ["submesh.indexCount", "1", "mesh.firstIndex + submesh.firstIndex", "mesh.vertexOffset", "2"])
    f.text(440, 488, "the same material and rasterizer state: one run, which one multi-draw call can issue (section 6)",
           13.5, "italic", GRAY, "middle")
    return f


FIGURES = [from_draw_items_to_indirect_draws, the_sort_key_and_what_it_picks, two_commands_in_the_shared_buffers]
