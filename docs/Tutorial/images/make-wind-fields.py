"""Generate Chapter 52's analytic field diagram; unrelated to engine builds.

@author Gary Yang
@brief Plot pure wind terms and lifetime fade, before particle response
@copyright (C) Gary 2026

Optional authoring dependencies: Python, NumPy, Matplotlib. Run this file to
replace wind-field-slices.svg beside it. --preview writes a separate PNG for
visual inspection. No renderer capture or game slide is used.
"""

from pathlib import Path
import argparse
import hashlib
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle
import numpy as np


def field(x, z, term, age_fraction):
    """Return U's X/Z components for a center-zero, radius-two source."""
    q2 = (x * x + z * z) / 4.0
    support = np.maximum(1.0 - q2, 0.0) ** 2
    remaining = 1.0 - age_fraction
    weight = support * remaining**2 * (3.0 - 2.0 * remaining)
    if term == "swirl":
        # 3 * cross((0, 1, 0), (x, 0, z)) = (3z, 0, -3x).
        raw_x, raw_z = 3.0 * z, -3.0 * x
    elif term == "gust":
        raw_x, raw_z = np.full_like(x, 4.0), np.zeros_like(z)
    elif term == "radial":
        raw_x, raw_z = 6.0 * x / 2.0, 6.0 * z / 2.0
    else:
        raise ValueError(term)
    return weight * raw_x, weight * raw_z


def check_hand_values():
    # Independent scalar samples derived in the lesson's units. Also verify
    # that the fade changes magnitude, not direction, in every panel.
    samples = {"swirl": (0.0, -1.6875), "gust": (2.25, 0.0), "radial": (1.6875, 0.0)}
    for term, expected in samples.items():
        for age, factor in [(0.0, 1.0), (0.5, 0.5)]:
            actual = np.asarray(field(np.asarray(1.0), np.asarray(0.0), term, age))
            np.testing.assert_allclose(actual, np.asarray(expected) * factor, rtol=0, atol=1e-12)
            np.testing.assert_array_equal(field(np.asarray(2.0), np.asarray(0.0), term, age), (0.0, 0.0))
    np.testing.assert_array_equal(field(np.asarray(0.0), np.asarray(0.0), "gust", 0), (4.0, 0.0))
    for term in ["swirl", "radial"]:
        np.testing.assert_array_equal(field(np.asarray(0.0), np.asarray(0.0), term, 0), (0.0, 0.0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, help="Optional PNG inspection output")
    args = parser.parse_args()
    check_hand_values()
    matplotlib.rcParams.update({"font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "pf-ch52-wind-fields-v1"})
    fig, axes = plt.subplots(2, 3, figsize=(12, 8.9), layout="constrained")
    fig.set_constrained_layout_pads(w_pad=0.1, h_pad=0.12, hspace=0.05)
    fig.suptitle("Three local wind terms\nXZ slice at y = 0; center (0, 0, 0), support radius 2 m", fontsize=16)
    grid = np.linspace(-2.0, 2.0, 17)
    x, z = np.meshgrid(grid, grid)
    # Exclude exterior points rather than plotting arbitrary directions there.
    inside = (x * x + z * z) < 4.0
    x, z = x[inside], z[inside]
    norm = Normalize(0, 4)
    titles = [("swirl", "Swirl: axis +Y, angular speed 3 rad/s"),
              ("gust", "Gust: linear velocity +4 m/s along X"),
              ("radial", "Radial: raw speed 6 m/s at R")]
    for row, age in enumerate([0.0, 0.5]):
        for column, (term, title) in enumerate(titles):
            ax = axes[row, column]
            u, v = field(x, z, term, age)
            arrows = ax.quiver(x, z, u, v, np.hypot(u, v), cmap="viridis", norm=norm,
                              angles="xy", scale_units="xy", scale=7.0, pivot="middle",
                              width=0.008, minlength=0.0)
            ax.add_patch(Circle((0, 0), 2.0, fill=False, color="#777777", linestyle="--", linewidth=1.1))
            ax.scatter([0], [0], color="#111111", s=11, zorder=3)
            ax.set(xlim=(-2.25, 2.25), ylim=(-2.25, 2.25), aspect="equal",
                   xlabel="X (m)", ylabel="Z (m)", xticks=[-2, -1, 0, 1, 2], yticks=[-2, -1, 0, 1, 2])
            ax.set_title(f"{title}\nAge / lifetime = {age:g}", fontsize=10)
            ax.grid(color="#dddddd", linewidth=0.5)
            ax.set_axisbelow(True)
    fig.colorbar(arrows, ax=axes, orientation="horizontal", shrink=0.62, pad=0.04,
                 label="Weighted contribution speed |U| (m/s); same arrow scale in every panel")
    output = Path(__file__).with_name("wind-field-slices.svg")
    fig.savefig(output, facecolor="white", metadata={"Date": None, "Description":
                "Analytic weighted velocity contributions, not a renderer capture. Each column uses only its named term. "
                "The bottom row has half the lifetime weight. Particle response is not plotted."})
    # Matplotlib leaves spaces before path-data newlines. The newline remains
    # a token separator; trim those spaces for the repository's text checks.
    output.write_text("\n".join(line.rstrip() for line in output.read_text(encoding="utf-8").splitlines()) + "\n",
                      encoding="utf-8", newline="\n")
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.preview, dpi=130, facecolor="white")
    plt.close(fig)
    print(json.dumps({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                      "kind": "computed analytic diagram", "matplotlib": matplotlib.__version__,
                      "numpy": np.__version__, "hand_value_controls": "passed", "native_evidence": False}))


if __name__ == "__main__":
    main()
