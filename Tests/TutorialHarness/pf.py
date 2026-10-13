#!/usr/bin/env python3
"""
    @author Tutorial harness
    @brief  Linux stand-in for building and running a PillowFort worktree:
            build (g++ and clang++, mirroring the worktree's premake5.lua), run
            on lavapipe under Xvfb with validation and frame-exact screenshots,
            the chapter 05 sync-validation positive control, and a drift check
            between a chapter's code blocks and a worktree.
    @copyright 2026 Gary Yang

    Not a build layer: premake5.lua and GenerateProjects.bat never call this.
    See README.md beside it.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_build(args) -> int:
    # Imported here, as run is below: build needs fcntl, which Windows lacks, and
    # drift and probe must work there too.
    from pfharness import build as pfbuild
    result = pfbuild.build(args.worktree, configuration=args.config, compilers=tuple(args.compilers.split(",")),
                           name=args.name, sanitize=args.asan, msvc_approx=not args.no_msvc_approx)
    print(pfbuild.summarize(result))
    if args.werror and result.counted("standard"):
        return 1
    return 0 if result.ok else 1


def cmd_run(args) -> int:
    from pfharness import run as pfrun
    return pfrun.main(args)


def cmd_control(args) -> int:
    from pfharness import run as pfrun
    return pfrun.control(args)


def cmd_drift(args) -> int:
    from pfharness import drift
    return drift.main(args)


def cmd_probe(args) -> int:
    from pfharness import image
    for point in args.points:
        x, y = (int(v) for v in point.split(","))
        print(f"{x},{y}: {image.pixel(args.png, x, y)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_build_options(p):
        p.add_argument("worktree", help="path to a worktree of this repository")
        p.add_argument("--config", default="Debug", choices=["Debug", "Release", "Dist"])
        p.add_argument("--compilers", default="gcc,clang", help="comma list of gcc, clang")
        p.add_argument("--name", help="build directory name (default: the worktree's folder name)")
        p.add_argument("--asan", action="store_true", help="AddressSanitizer + UBSan build")
        p.add_argument("--no-msvc-approx", action="store_true",
                       help="drop -Wshadow -Wconversion (the /W4 approximations)")

    p = sub.add_parser("build", help="compile a worktree with g++ and clang++")
    add_build_options(p)
    p.add_argument("--werror", action="store_true", help="exit 1 on any standard-group warning")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("run", help="build, then run SandboxGame on lavapipe under Xvfb")
    add_build_options(p)
    p.add_argument("--frames", type=int, default=120, help="passed to SandboxGame as --frames N")
    p.add_argument("--shot", type=int, action="append", default=[], metavar="FRAME",
                   help="screenshot after this present (repeatable)")
    p.add_argument("--script", help="input script: lines of '<frame> <command>' (see README)")
    p.add_argument("--compiler", default="gcc", help="which build to run (gcc or clang)")
    p.add_argument("--out", help="output directory for logs and screenshots")
    p.add_argument("--size", default="1600x1000", help="Xvfb screen size")
    p.add_argument("--timeout", type=float, default=300.0, help="seconds before the run is killed")
    p.add_argument("--no-force-sync", action="store_true",
                   help="do not set VK_LAYER_VALIDATE_SYNC=1; rely on the app's own layer settings")
    p.add_argument("--no-shader-heuristic", action="store_true",
                   help="VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC=0: the layer default, which does not "
                        "track shader accesses through descriptors")
    p.add_argument("--app-settings-only", action="store_true",
                   help="set neither VK_LAYER_VALIDATE_SYNC nor VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC, so only "
                        "the program's own VK_EXT_layer_settings request configures sync validation")
    p.add_argument("--expect", action="append", default=[], metavar="REGEX",
                   help="the run passes only if this appears in the log (positive controls)")
    p.add_argument("--allow", action="append", default=[], metavar="REGEX",
                   help="a validation message matching this does not fail the run")
    p.add_argument("--no-build", action="store_true", help="run the existing build")
    p.add_argument("--app-args", default="", help="extra arguments for SandboxGame, e.g. '--present mailbox'")
    p.add_argument("--replace", nargs=3, action="append", default=[], metavar=("FILE", "OLD", "NEW"),
                   help="run a throwaway copy with this literal edit (OLD must occur exactly once); repeatable")
    p.add_argument("--patch", action="append", default=[], metavar="DIFF",
                   help="run a throwaway copy with this unified diff applied (patch -p1); repeatable")
    p.add_argument("--variant", default="variant", help="label for the throwaway copy (with --replace/--patch)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("control", help="sync-validation positive controls: chapter 05's barrier (default), "
                                         "or --compute for shader accesses through descriptors")
    p.add_argument("worktree")
    p.add_argument("--compute", action="store_true",
                   help="inject two compute read-after-write hazards into the program's own device "
                        "(LD_PRELOAD; the directory is not modified) and require both to be reported")
    p.add_argument("--no-shader-heuristic", action="store_true",
                   help="run the barrier control with the layer default (heuristic off)")
    p.add_argument("--patch", help="a unified diff to apply instead of the built-in chapter 05 edit")
    p.add_argument("--expect", action="append", default=[], metavar="REGEX")
    p.add_argument("--out", help="output directory")
    p.set_defaults(func=cmd_control)

    p = sub.add_parser("drift", help="chapter code blocks whose lines are missing from a worktree")
    p.add_argument("chapter", help="chapter number, e.g. 09")
    p.add_argument("worktree")
    p.add_argument("--docs", help="docs/Tutorial directory to read the chapter from "
                                  "(default: this repository's)")
    p.add_argument("--all", action="store_true", help="also list blocks that match fully")
    p.set_defaults(func=cmd_drift)

    p = sub.add_parser("probe", help="print pixel values from a screenshot")
    p.add_argument("png")
    p.add_argument("points", nargs="+", metavar="X,Y")
    p.set_defaults(func=cmd_probe)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
