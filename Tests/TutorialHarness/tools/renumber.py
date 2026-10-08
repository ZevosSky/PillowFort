#!/usr/bin/env python3
"""Renumber tutorial chapters in the docs and in code comments, on one or more trees.

    python3 renumber.py --map 32:33,33:34 <tree> [<tree> ...]            dry run: prints every change
    python3 renumber.py --map 32:33,33:34 --apply <tree> [<tree> ...]    writes them, and renames the chapter files

Run it on both the docs-branch tree and the reference tree, so the text and the code comments move together. A
tree is a checkout's root (it reads docs/, Source/, Shaders/, Assets/ and the rest, skipping Vendor/, .git/ and
Build/), or a single file.

It rewrites a chapter number where the text marks it as one:
  "Chapter 32", "chapters 30-32", "Chapters 31 and 33"   a chapter word followed by numbers, lists and ranges
  "32 §4"                                                 a number before a section sign
  "32-A-Boat.md"                                          a chapter file name in a link
  "[32 — A Boat]", "# 32 — A Boat", "**32 — ...**"        a title
  "(32)"                                                  a parenthesized number, not a call such as radians(30)
  "| 32 |"                                                a number alone in the first cell of a table row
With --apply, docs/Tutorial/NN-*.md files whose number is in the map are renamed too.

REFERENCE.md is skipped: it records history in old numbers ("26 path tracing (was 10)"), which a
blind rewrite would falsify. Update its current-state lines by hand, and add a line saying what moved.

What it cannot catch, so read the dry run and then grep for these by hand:
  - bold numbers such as **27** and bare ranges in prose ("the grass, 25-27, ...");
  - a number that is a chapter only by context ("as 31 does");
  - section moves inside a chapter: those are exact edits, one string at a time, each checked to match once.
Afterwards, run tools/docs_check.py on the docs tree. It must exit 0.
"""
import argparse
import pathlib
import re
import sys

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('trees', nargs='+', type=pathlib.Path)
parser.add_argument('--map', required=True, help='old:new pairs, comma separated, e.g. 32:33,33:34')
parser.add_argument('--apply', action='store_true', help='write the changes (default: print them only)')
args = parser.parse_args()

MAP = {int(a): int(b) for a, b in (pair.split(':') for pair in args.map.split(','))}


def bump(numbers):
    return re.sub(r'\d\d', lambda m: f'{MAP.get(int(m.group(0)), int(m.group(0))):02d}', numbers)


NUM = r'\d\d(?:\s*[-–]\s*\d\d)?'
SEP = r'(?:,\s*(?:and\s+|or\s+)?|\s+and\s+|\s+or\s+|\s+to\s+|\s*/\s*)'
LIST = rf'{NUM}(?:{SEP}{NUM})*'
# (name, pattern, index of the group that holds the numbers)
PATTERNS = [
    ('chapter', re.compile(rf'\b([Cc]h(?:apters?|s?\.?)\s+)({LIST})'), 1),
    ('section', re.compile(rf'(?<![\d.])({NUM})(\s*§)'), 0),
    ('link', re.compile(r'(?<!\d)(\d\d)(-[A-Z][A-Za-z0-9-]*\.md)'), 0),
    ('title', re.compile(r'(\[|^# |\*\*)(\d\d)( — )', re.M), 1),
    ('paren', re.compile(rf'(?<![A-Za-z0-9_])(\()({NUM})(\))'), 1),
    ('table', re.compile(rf'^(\|\s*)({NUM})(\s*\|)', re.M), 1),
]
EXTENSIONS = {'.md', '.h', '.cpp', '.glsl', '.py', '.usda', '.lua', '.txt', '.hlsl'}
SKIP = {'Vendor', '.git', 'Build', '_vendor', 'node_modules', '.claude', 'TutorialHarness'}
SKIP_FILES = {'REFERENCE.md'}   # history in old numbers; edited by hand


def process(path, text, changes):
    for name, pattern, index in PATTERNS:
        def replace(m, name=name, index=index):
            groups = list(m.groups())
            new = bump(groups[index])
            if new != groups[index]:
                start = text.rfind('\n', 0, m.start()) + 1
                end = text.find('\n', m.end())
                changes.append(f'[{name}] {path}:{text[:m.start()].count(chr(10)) + 1}: '
                               f'{groups[index]!r} -> {new!r} | {text[start:end if end >= 0 else None].strip()[:140]}')
            groups[index] = new
            return ''.join(g or '' for g in groups)
        text = pattern.sub(replace, text)
    return text


changes = []
renames = []
for tree in args.trees:
    files = [tree] if tree.is_file() else sorted(
        p for p in tree.rglob('*')
        if p.is_file() and p.suffix in EXTENSIONS and p.name not in SKIP_FILES
        and not SKIP.intersection(p.relative_to(tree).parts))
    for f in files:
        try:
            text = f.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        new = process(str(f), text, changes)
        if args.apply and new != text:
            f.write_text(new, encoding='utf-8')
    chapters = tree / 'docs' / 'Tutorial'
    if chapters.is_dir():
        for f in sorted(chapters.glob('[0-9][0-9]-*.md')):
            number = int(f.name[:2])
            if number in MAP and MAP[number] != number:
                renames.append((f, chapters / f'{MAP[number]:02d}{f.name[2:]}'))

for line in changes:
    print(line)
for old, new in renames:
    print(f'[rename] {old} -> {new.name}')
if args.apply:
    # Two steps, through temporary names, so that 32 -> 33 cannot overwrite the 33 that is about to become 34.
    for old, new in renames:
        old.rename(old.with_name(old.name + '.renumbering'))
    for old, new in renames:
        old.with_name(old.name + '.renumbering').rename(new)
print(f'{len(changes)} changes, {len(renames)} files renamed', '(applied)' if args.apply else '(dry run)')
print('Not touched: REFERENCE.md (update by hand), bold numbers, bare ranges in prose. '
      'Then run tools/docs_check.py.')
