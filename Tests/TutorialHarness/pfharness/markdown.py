"""
    @author Tutorial harness
    @brief  Fenced-code-block extraction from the tutorial chapters.
    @copyright 2026 Gary Yang

    Blocks are found by their FIRST LINE, never by position: selecting by index
    silently picked the wrong block the day a chapter gained one. A lookup
    that matches no block, or more than one, is an error
    that names the chapter and lists the near misses.
"""

from __future__ import annotations

import difflib
import glob
import os
import re
from dataclasses import dataclass, field
from typing import Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TUTORIAL_DIR = os.path.join(REPO_ROOT, "docs", "Tutorial")

_FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^`]*)$")


class ExtractionError(Exception):
    """A recipe referred to something the chapter does not (uniquely) contain."""


@dataclass
class Block:
    chapter: str          # "05"
    path: str             # absolute path of the markdown file
    lang: str             # "cpp", "glsl", "text", ... ("" when unlabelled)
    start_line: int       # 1-based line number of the first content line
    lines: list[str]      # content, fence indentation removed
    section: str = ""     # nearest preceding "## " heading

    @property
    def first_line(self) -> str:
        for line in self.lines:
            if line.strip():
                return line.strip()
        return ""

    @property
    def text(self) -> str:
        return "\n".join(self.lines) + "\n"

    def where(self) -> str:
        rel = os.path.relpath(self.path, REPO_ROOT)
        return f"{rel}:{self.start_line} [{self.section}] first line {self.first_line!r}"


@dataclass
class Chapter:
    number: str
    path: str
    blocks: list[Block] = field(default_factory=list)
    text: str = ""

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    def find(self, first_line: str, *, contains: Optional[str] = None,
             lang: Optional[str] = None) -> Block:
        """The one block whose first non-blank line, stripped, equals `first_line`.

        `contains` disambiguates blocks that share a first line: a substring that
        must occur in exactly one of them. It is never an index.
        """
        want = first_line.strip()
        hits = [b for b in self.blocks if b.first_line == want]
        if lang is not None:
            hits = [b for b in hits if b.lang == lang]
        if contains is not None:
            hits = [b for b in hits if contains in b.text]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            near = difflib.get_close_matches(want, [b.first_line for b in self.blocks], n=4, cutoff=0.5)
            raise ExtractionError(
                f"{self.name}: no fenced block starts with {want!r}"
                + (f" containing {contains!r}" if contains else "")
                + (f"\n  closest first lines: {near}" if near else "\n  (no similar first line)"))
        raise ExtractionError(
            f"{self.name}: {len(hits)} fenced blocks start with {want!r}"
            + (f" and contain {contains!r}" if contains else "")
            + "; add or tighten `contains=`:\n  "
            + "\n  ".join(b.where() for b in hits))

    def has_text(self, needle: str) -> bool:
        return needle in self.text


def parse(path: str, number: str) -> Chapter:
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    chapter = Chapter(number=number, path=path, text=raw)
    lines = raw.split("\n")
    section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        match = _FENCE.match(line)
        if not match:
            i += 1
            continue
        indent = match.group("indent")
        fence = match.group("fence")
        info = match.group("info").strip()
        body: list[str] = []
        j = i + 1
        closed = False
        while j < len(lines):
            candidate = lines[j]
            stripped = candidate.strip()
            if stripped.startswith(fence[0] * len(fence)) and set(stripped) <= {fence[0]}:
                closed = True
                break
            # Remove the fence's own indentation (blocks nested in list items).
            if indent and candidate.startswith(indent):
                candidate = candidate[len(indent):]
            body.append(candidate)
            j += 1
        if not closed:
            raise ExtractionError(f"{os.path.basename(path)}:{i + 1}: unterminated code fence")
        lang = info.split()[0] if info else ""
        chapter.blocks.append(Block(chapter=number, path=path, lang=lang,
                                    start_line=i + 2, lines=body, section=section))
        i = j + 1
    return chapter


_CACHE: dict[str, Chapter] = {}


def chapter_path(number: str) -> str:
    """Resolve a chapter by number at run time; files are renamed while we work."""
    pattern = os.path.join(TUTORIAL_DIR, f"{number}-*.md")
    hits = sorted(glob.glob(pattern))
    if len(hits) != 1:
        raise ExtractionError(f"chapter {number}: expected one file matching {pattern}, found {hits}")
    return hits[0]


def load(number: str) -> Chapter:
    if number not in _CACHE:
        _CACHE[number] = parse(chapter_path(number), number)
    return _CACHE[number]


def all_chapters() -> list[str]:
    numbers = []
    for path in sorted(glob.glob(os.path.join(TUTORIAL_DIR, "[0-9][0-9]-*.md"))):
        numbers.append(os.path.basename(path)[:2])
    return numbers
