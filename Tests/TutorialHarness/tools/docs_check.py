#!/usr/bin/env python3
"""Check the tutorial's cross-references after an edit, a renumbering, or a split.

    python3 docs_check.py [docs dir]        (default: the docs/ beside Tests/)

Four checks, each printing what it finds:
  1. Every "Chapter NN section M" and "NN §M" (lists and ranges too) names a
     "## M." heading that exists in chapter NN.
  2. Every relative Markdown link outside code blocks reaches a file, and its
     #anchor a heading in that file (GitHub's slug rules).
  3. Each chapter's last "Next:" link points to the following chapter; the last
     chapters may end without one.
  4. No C1 control characters (U+0080-U+009F): a "\\202" read as an octal
     escape has mangled a path before.

Exit status is 0 when nothing is reported.
"""
import glob
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', '..', '..', 'docs')
root = os.path.normpath(root)
chapters = sorted(glob.glob(os.path.join(root, 'Tutorial', '[0-9][0-9]-*.md')))
files = chapters + [os.path.join(root, 'VulkanTutorial.md')]
problems = 0


def report(message):
    global problems
    problems += 1
    print(message)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


# 1. Section references.
sections = {int(os.path.basename(f)[:2]): set(int(m) for m in re.findall(r'^##+ (?:Section )?(\d+)[.:]', read(f), re.M))
            for f in chapters}
wordy = re.compile(r'Chapter\s+(\d\d)(?:\'s)?\s+sections?\s+((?:\d+(?:\s*-\s*\d+)?(?:,\s*|\s+and\s+|\s+or\s+|,\s+and\s+)?)+)')
# In the short form a further section repeats its "§" ("10 §1 and §8"); a bare
# number after a comma ("31 §6, 32 §3", "17 §13, 22, and 27") starts a chapter.
short = re.compile(r'\b(\d\d) (§\d+(?:-\d+)?(?:(?:,|,? and| or) §\d+(?:-\d+)?)*)')
references = 0
for f in files:
    text = read(f)
    for pattern in (wordy, short):
        for m in pattern.finditer(text):
            chapter = int(m.group(1))
            for a, b in re.findall(r'(\d+)(?:\s*-\s*(\d+))?', m.group(2)):
                for section in (range(int(a), int(b) + 1) if b else [int(a)]):
                    references += 1
                    if section not in sections.get(chapter, set()):
                        line = text[:m.start()].count('\n') + 1
                        report(f'{os.path.relpath(f, root)}:{line}: no section {section} in chapter {chapter}  [{m.group(0)!r}]')


# 2. Links and anchors.
def slug(heading):
    heading = re.sub(r'[`*_~]', '', heading.strip().lower())
    return re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')


markdown = glob.glob(os.path.join(root, '**', '*.md'), recursive=True)
anchors = {}
for f in markdown:
    text = read(f)
    anchors[os.path.normpath(f)] = ({slug(h) for h in re.findall(r'^#+\s+(.*)$', text, re.M)}
                                    | set(re.findall(r'<a\s+(?:id|name)="([^"]+)"', text)))
links = 0
for f in markdown:
    prose = re.sub(r'```.*?```', '', read(f), flags=re.S)
    for target in re.findall(r'\]\(([^)\s]+)\)', prose):
        if re.match(r'(https?|mailto):', target):
            continue
        links += 1
        path, _, anchor = target.partition('#')
        resolved = os.path.normpath(os.path.join(os.path.dirname(f), path)) if path else os.path.normpath(f)
        if not os.path.exists(resolved):
            report(f'{os.path.relpath(f, root)}: link to a missing file: {target}')
        elif anchor and resolved.endswith('.md') and anchor not in anchors.get(resolved, set()):
            report(f'{os.path.relpath(f, root)}: link to a missing heading: {target}')

# 3. The Next chain.
for current, following in zip(chapters, chapters[1:]):
    nexts = re.findall(r'Next: \[[^\]]*\]\(([^)]*)\)', read(current))
    if nexts and nexts[-1] != os.path.basename(following):
        report(f'{os.path.basename(current)}: Next points to {nexts[-1]}, not {os.path.basename(following)}')
    elif not nexts and following != chapters[-1]:
        report(f'{os.path.basename(current)}: no Next link')

# 4. C1 control characters.
for f in markdown:
    text = read(f)
    for i, ch in enumerate(text):
        if 0x80 <= ord(ch) <= 0x9F:
            report(f'{os.path.relpath(f, root)}:{text[:i].count(chr(10)) + 1}: C1 control character U+{ord(ch):04X}')

print(f'{references} section references, {links} links, {len(chapters)} chapters: {problems} reported')
sys.exit(1 if problems else 0)
