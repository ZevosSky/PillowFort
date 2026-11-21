"""
    @author Tutorial harness
    @brief  Drift check: which of a chapter's code blocks are not (fully) present
            in a worktree. Lets a chapter's author confirm the implementation
            matches the text, block by block.
    @copyright 2026 Gary Yang

    Blocks are identified by their first line (markdown.py), never by position.
    Matching is line-wise and whitespace-normalized; comment-only lines, braces,
    and access specifiers are skipped, because a block is "present" when its
    code is, wherever the implementation put its commentary. A block is matched
    against the single file that contains most of its lines, so code split
    across files shows up as PARTIAL with the missing lines listed.
"""

from __future__ import annotations

import os
import re

from . import markdown

CODE_LANGS = {"cpp", "c", "c++", "h", "hpp", "glsl", "lua", "hlsl", "slang"}
SCAN_ROOTS = ("Source", "Shaders", "premake5.lua", "Tests")
SCAN_EXTS = (".h", ".hpp", ".c", ".cpp", ".cc", ".glsl", ".lua", ".inl", ".slang")
TRIVIAL = re.compile(r"^(?:[{}()\[\];,]+|public:|private:|protected:|#pragma once|#endif|else|do|\.\.\.)$")


def normalize(line: str) -> str:
    line = re.sub(r"\s+", " ", line.strip())
    if not line.startswith(("//", "/*")):
        line = re.sub(r"\s*//.*$", "", line)
        line = re.sub(r"\s*/\*.*?\*/\s*$", "", line)
    return line.strip()


def significant(line: str) -> bool:
    if not line:
        return False
    if line.startswith(("//", "/*", "*", "--")):
        return False
    return not TRIVIAL.match(line)


def index_worktree(root: str) -> dict[str, set[str]]:
    files: dict[str, set[str]] = {}
    for entry in SCAN_ROOTS:
        path = os.path.join(root, entry)
        candidates = [path] if os.path.isfile(path) else [
            os.path.join(dp, f) for dp, _d, fs in os.walk(path) for f in fs]
        for full in candidates:
            if not full.endswith(SCAN_EXTS):
                continue
            with open(full, encoding="utf-8", errors="replace") as handle:
                files[os.path.relpath(full, root)] = {normalize(l) for l in handle}
    return files


def main(args) -> int:
    if args.docs:
        markdown.TUTORIAL_DIR = os.path.abspath(args.docs)
    chapter = markdown.load(args.chapter)
    files = index_worktree(os.path.abspath(args.worktree))
    if not files:
        print(f"no source files under {args.worktree}")
        return 2
    print(f"drift: {chapter.path} vs {os.path.abspath(args.worktree)}")
    counts = {"FULL": 0, "PARTIAL": 0, "ABSENT": 0}
    for block in chapter.blocks:
        if block.lang.lower() not in CODE_LANGS:
            continue
        lines = [normalize(l) for l in block.lines]
        wanted = [l for l in lines if significant(l)]
        if not wanted:
            continue
        best_file, best_hits = "", -1
        for rel, present in files.items():
            hits = sum(1 for l in wanted if l in present)
            if hits > best_hits:
                best_file, best_hits = rel, hits
        missing = [l for l in wanted if l not in files.get(best_file, set())]
        status = "FULL" if not missing else ("ABSENT" if best_hits <= len(wanted) // 4 else "PARTIAL")
        counts[status] += 1
        if status == "FULL" and not args.all:
            continue
        print(f"\n[{status}] {block.where()}")
        print(f"    best match: {best_file} ({best_hits}/{len(wanted)} lines)")
        for line in missing[:12]:
            print(f"    missing: {line}")
        if len(missing) > 12:
            print(f"    ... and {len(missing) - 12} more")
    print(f"\nblocks: {counts['FULL']} full, {counts['PARTIAL']} partial, {counts['ABSENT']} absent "
          f"(illustrative fragments - '...' placeholders, alternatives the text rejects - are expected "
          f"to be partial or absent; read each one)")
    return 0
