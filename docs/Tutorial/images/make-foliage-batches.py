"""Draw the current flower batching contract; optional authoring, not an engine build.

@author Gary Yang
@brief Show two uniform sizes sharing mesh parts and instance records
@copyright (C) Gary 2026

Requires Matplotlib. --preview writes a PNG for visual inspection. The SVG is a
teaching schematic, not a native renderer capture or an image of the USD mesh.
"""
from pathlib import Path
import argparse
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle


BLUE = "#23639b"
GOLD = "#b66d00"
INK = "#182637"
GRAY = "#536474"


def box(ax, x, y, w, h, title, lines):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#f4f7fa", edgecolor="#8a9aaa", linewidth=.9))
    ax.text(x+1.3, y+h-2.6, title, fontsize=11, weight="bold", color=INK, va="top")
    for i, line in enumerate(lines):
        ax.text(x+1.3, y+h-7.8-4.4*i, line, fontsize=9.5, color=INK, va="top")


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14,
                                linewidth=1.2, color=GRAY, shrinkA=2, shrinkB=2))


def flower(ax, x, y, size, label):
    # Same stylized local shape, uniformly scaled about its root. Not asset geometry.
    tip = y + 17*size
    ax.plot([x, x], [y, tip], color=BLUE, linewidth=2.4*size)
    for dx, dy in [(-2.4, 0), (2.4, 0), (0, 2.4), (0, -2.4)]:
        ax.add_patch(Circle((x+dx*size, tip+dy*size), 1.75*size,
                            facecolor="#efbc66", edgecolor=GOLD, linewidth=.8))
    ax.add_patch(Circle((x, tip), 1.4*size, facecolor=GOLD, edgecolor=GOLD))
    ax.plot(x, y, "o", color=INK, markersize=3)
    ax.text(x, y-3.0, label, color=INK, fontsize=10, weight="bold", ha="center", va="top")
    ax.text(x, y-7.0, f"size {size:g}", color=INK, fontsize=9.5, ha="center", va="top")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    matplotlib.rcParams.update({"font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "pf-foliage-batches-v1"})
    fig, ax = plt.subplots(figsize=(13.2, 6.0))
    fig.subplots_adjust(left=.02, right=.99, bottom=.025, top=.98)
    ax.set(xlim=(0, 110), ylim=(0, 66))
    ax.axis("off")
    ax.text(2, 64, "Two sizes share the same flower instance list", fontsize=17, weight="bold", color=INK, va="top")
    ax.text(2, 58.7, "Example after generation: two flowers in LOD0. This is a schematic, not a renderer capture.",
            fontsize=10.5, color=GRAY, va="top")

    box(ax, 2, 32, 26, 20, "Shared geometry", ["Stem mesh + its material", "Head mesh + its material", "Each mesh is stored once."])
    box(ax, 2, 10, 26, 17, "Generation inputs", ["World cell seeds choices:", "root, size and yaw."])

    box(ax, 34, 32, 37, 20, "Two indirect commands", ["Stem: 2 instances", "Head: 2 instances", "Both: firstInstance = 12800"])
    box(ax, 34, 10, 37, 17, "Same two 32-byte records", ["A: root A, size 0.8, turn.xy (1,0)", "B: root B, size 1.2, turn.xy (1,0)"])
    arrow(ax, (28, 43), (34, 43))
    arrow(ax, (28, 18), (34, 18))
    arrow(ax, (52.5, 32), (52.5, 27))
    ax.text(53.8, 29.5, "select", fontsize=8.5, color=GRAY, va="center")
    arrow(ax, (71, 43), (77, 43))
    arrow(ax, (71, 18), (77, 18))

    ax.text(92, 55, "Same local meshes,\nseparate root + size", fontsize=11, color=INK,
            weight="bold", ha="center", va="top")
    ax.plot([78, 108], [23, 23], color="#8a9aaa", linewidth=.8)
    flower(ax, 84, 23, .8, "A")
    flower(ax, 101, 23, 1.2, "B")
    ax.text(92, 8, "2 stems + 2 heads = 2 flowers", fontsize=9.5, color=INK, ha="center")

    ax.text(2, 5.8, "Flower LOD0 uses region 2: firstInstance = 2 × 6400. These are two commands from the ten-command template.",
            fontsize=9.2, color=GRAY, va="top")
    ax.text(2, 2.2, "A/B are example labels. World-cell identity is upstream of compaction; it is not an extra field in PlantInstance.",
            fontsize=9.2, color=GRAY, va="top")
    output = Path(__file__).with_name("foliage-batches.svg")
    fig.savefig(output, facecolor="white", metadata={"Date": None, "Description":
                "Teaching schematic of Flower LOD0: two commands share two 32-byte records with positive uniform scales 0.8/1.2. "
                "Stylized geometry, not a renderer capture or native verification. World-cell identity is not stored in PlantInstance."})
    output.write_text("\n".join(line.rstrip() for line in output.read_text(encoding="utf-8").splitlines()) + "\n",
                      encoding="utf-8", newline="\n")
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.preview, dpi=130, facecolor="white")
    plt.close(fig)
    print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                      "matplotlib": matplotlib.__version__, "nativeRendererEvidence": False}))


if __name__ == "__main__":
    main()
