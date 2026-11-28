"""Write the tutorial's authored figures from figures/ch*.py; optional authoring, not an engine build.

@author Gary Yang
@brief Build every authored figure, preview it, and record it in diagrams.json
@copyright (C) Gary 2026

    python make-tutorial-figures.py                   all figures, then diagrams.json
    python make-tutorial-figures.py --only ch04,ch29  some modules; diagrams.json untouched
    python make-tutorial-figures.py --preview DIR     also PNG previews for inspection

Requires Matplotlib (fonts and text outlines); --preview also needs resvg-py and Pillow. The
SVGs are teaching schematics and computed plots, never renderer captures.
"""
from hashlib import sha256
from importlib import metadata
from pathlib import Path
import argparse
import importlib.util
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figure_kit  # noqa: E402

GENERATOR = Path(__file__).name


def load(module_path):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preview(figure, svg, folder):
    import resvg_py
    from PIL import Image
    import io
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=figure.width * 2, skip_system_fonts=True))
    (folder / f"{figure.name}.png").write_bytes(png)
    image = Image.open(io.BytesIO(png)).convert("RGBA").resize((figure.width, figure.height), Image.LANCZOS)
    for theme, colour in (("light", "#ffffff"), ("dark", "#0d1117")):
        sheet = Image.new("RGBA", (figure.width + 32, figure.height + 32), colour)
        sheet.alpha_composite(image, (16, 16))
        sheet.convert("RGB").save(folder / f"{figure.name}-{theme}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="comma-separated module names, such as ch04,ch29")
    parser.add_argument("--preview", type=Path, help="folder for PNG previews: 2x, and real size on light and dark")
    args = parser.parse_args()

    modules = sorted((HERE / "figures").glob("ch*.py"))
    if args.only:
        wanted = set(args.only.split(","))
        modules = [m for m in modules if m.stem in wanted]
        missing = wanted - {m.stem for m in modules}
        if missing:
            sys.exit(f"no such module: {', '.join(sorted(missing))}")
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)

    others = {p.name for p in HERE.iterdir() if p.is_file()}
    records, names, problems = [], set(), []
    for module_path in modules:
        module = load(module_path)
        for build in module.FIGURES:
            figure = build()
            if figure.name in names:
                problems.append(f"{figure.name}: built twice")
            names.add(figure.name)
            problems += figure.problems()
            svg = figure.svg()
            out = HERE / f"{figure.name}.svg"
            out.write_text(svg, encoding="utf-8", newline="\n")
            if args.preview:
                preview(figure, svg, args.preview)
            records.append({
                "id": figure.name, "file": out.name, "sha256": sha256(svg.encode("utf-8")).hexdigest(),
                "kind": figure.kind, "nativeRendererEvidence": False, "source": figure.source,
                "generator": f"{GENERATOR} figures/{module_path.name}",
                "generatorSha256": sha256(module_path.read_bytes() + (HERE / "figure_kit.py").read_bytes()).hexdigest(),
                "authoringTools": {"python": platform.python_version(), "matplotlib": metadata.version("matplotlib"),
                                   "font": "DejaVu, outlined"},
                "parameters": figure.parameters,
                "controls": "Rendered with resvg at 2x and inspected at display size on light and dark pages; "
                            "text clipping and overlap checked by figure_kit.Figure.problems; "
                            "content checked against the chapter text it illustrates.",
                "regenerate": f"Optional authoring only: python {GENERATOR}; Matplotlib required, resvg-py and Pillow "
                              "for --preview. Not part of the engine build.",
            })
            print(f"{figure.name}.svg  {len(svg) // 1024} KiB")

    for problem in problems:
        print("PROBLEM:", problem)
    if not args.only:
        manifest_path = HERE / "diagrams.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        kept = [e for e in manifest["diagrams"] if not e.get("generator", "").startswith(GENERATOR)]
        manifest["diagrams"] = kept + records
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"diagrams.json: {len(kept)} kept, {len(records)} from {GENERATOR}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
