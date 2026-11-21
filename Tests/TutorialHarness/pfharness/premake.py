"""
    @author Tutorial harness
    @brief  Reads a worktree's premake5.lua - projects, globs, include dirs,
            defines, links, and the shader prebuild rule - so the Linux build
            mirrors what premake would generate for Visual Studio.
    @copyright 2026 Gary Yang

    Read fresh from the worktree on every build: chapters add projects (TinyUSDZ),
    include directories, defines, and shader stages, and a mirror that hard-codes
    any of it would drift. Each project gets exactly its own include list:
    a helper which added every include directory globally once masked
    SandboxGame missing the GLFW and ImGui paths.

    It is a reader for the subset of premake this repository uses, not a premake
    implementation. Anything it does not understand is an error naming the line,
    never a silent skip.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from typing import Optional


class PremakeParseError(Exception):
    pass


def strip_comments(text: str) -> str:
    """Drop Lua `--` comments, but not a `--` inside a string literal (glslc flags)."""
    out = []
    for line in text.split("\n"):
        quote = None
        cut = len(line)
        for i, ch in enumerate(line):
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif line.startswith("--", i):
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


@dataclass
class Setting:
    """One value-list statement, with the filter it sits under ("" = none)."""
    filter: str
    values: list[str]


@dataclass
class Project:
    name: str
    kind: str = ""                 # StaticLib / ConsoleApp / WindowedApp / SharedLib
    language: str = "C++"
    cdialect: str = ""
    cppdialect: str = ""
    warnings: str = ""             # "Off" / "Extra" / ...
    files: list[Setting] = field(default_factory=list)
    removefiles: list[Setting] = field(default_factory=list)
    includedirs: list[Setting] = field(default_factory=list)
    externalincludedirs: list[Setting] = field(default_factory=list)
    defines: list[Setting] = field(default_factory=list)
    links: list[Setting] = field(default_factory=list)
    buildoptions: list[Setting] = field(default_factory=list)
    prebuildcommands: list[Setting] = field(default_factory=list)    # other than shaderCommands(...)
    postbuildcommands: list[Setting] = field(default_factory=list)
    shader_flags: dict[str, str] = field(default_factory=dict)   # config filter -> glslc flags
    ignored: list[str] = field(default_factory=list)            # statements read but not mirrored

    @staticmethod
    def _applies(filt: str, configuration: str) -> bool:
        if filt == "":
            return True
        terms = [t.strip() for t in filt.split(",")]
        for term in terms:
            key, _, value = term.partition(":")
            negate = value.startswith("not ")
            value = value[4:] if negate else value
            if key == "configurations":
                ok = configuration.lower() == value.lower()
            elif key == "system":
                ok = value.lower() == "linux"
            elif key in ("action", "toolset"):
                ok = False
            elif key == "files":
                ok = False     # per-file settings: reported in `ignored`
            else:
                ok = False
            if negate:
                ok = not ok
            if not ok:
                return False
        return True

    def values(self, attribute: str, configuration: str) -> list[str]:
        out: list[str] = []
        for setting in getattr(self, attribute):
            if self._applies(setting.filter, configuration):
                out.extend(setting.values)
        return out

    def windows_only(self, attribute: str) -> list[str]:
        out: list[str] = []
        for setting in getattr(self, attribute):
            if "system:windows" in setting.filter:
                out.extend(setting.values)
        return out


@dataclass
class ShaderRule:
    stages: dict[str, str]          # file suffix -> glslc stage name
    target_env: str                 # e.g. "vulkan1.3"
    root: str                       # "Shaders"


@dataclass
class Workspace:
    root: str
    projects: dict[str, Project]
    shader_rule: Optional[ShaderRule]
    startproject: str = ""
    location: str = ""              # workspace `location`, for %{wks.location}


_STRING = r'"(?:[^"\\]|\\.)*"|' + r"'(?:[^'\\]|\\.)*'"


def _split_top(body: str, sep: str = ",") -> list[str]:
    """Split on `sep` outside string literals, parentheses, and braces."""
    out, depth, quote, start, i = [], 0, None, 0, 0
    while i < len(body):
        ch = body[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
        elif ch == sep and depth == 0:
            out.append(body[start:i])
            start = i + 1
        i += 1
    out.append(body[start:])
    return [x for x in out if x.strip()]


def _scan_group(text: str, i: int) -> tuple[str, int]:
    """text[i] is '{' or '('; returns (body, index after the matching close), quote-aware."""
    open_ch = text[i]
    close_ch = "}" if open_ch == "{" else ")"
    depth, quote, j = 0, None, i
    while j < len(text):
        ch = text[j]
        if quote:
            if ch == "\\":
                j += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    raise PremakeParseError(f"premake5.lua: unbalanced {open_ch!r} near {text[i:i + 60]!r}")


def _skip_string(text: str, i: int) -> int:
    quote, j = text[i], i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == quote:
            return j + 1
        j += 1
    raise PremakeParseError(f"premake5.lua: unterminated string near {text[i:i + 60]!r}")


class _Reader:
    def __init__(self, root: str, text: str):
        self.root = root
        self.text = text
        self.variables: dict[str, str] = {"vulkanSDK": "$VULKAN_SDK"}
        for m in re.finditer(r'^\s*local\s+(\w+)\s*=\s*(' + _STRING + r')\s*$', text, re.M):
            self.variables[m.group(1)] = m.group(2)[1:-1]
        for m in re.finditer(r'^\s*local\s+(\w+)\s*=\s*os\.getenv\(["\'](\w+)["\']\)', text, re.M):
            self.variables[m.group(1)] = f"${m.group(2)}"

    def item(self, expr: str) -> str:
        """A string literal ('...' or "..."), a variable, or a `..` concatenation of those."""
        out = ""
        for part in (p.strip() for p in _split_top(expr, ".") if p.strip()):
            if re.fullmatch(_STRING, part):
                out += part[1:-1]
            elif part in self.variables:
                out += self.variables[part]
            else:
                raise PremakeParseError(f"premake5.lua: cannot evaluate {expr.strip()!r} (unknown term {part!r})")
        return out

    def items(self, body: str) -> list[str]:
        return [self.item(x) for x in _split_top(body)]


_LIST_ATTRS = ("files", "removefiles", "includedirs", "externalincludedirs", "defines", "links", "buildoptions",
               "prebuildcommands", "postbuildcommands")
_SCALAR_ATTRS = ("kind", "language", "cdialect", "cppdialect", "warnings")
_KEYWORDS = {"local", "function", "end", "if", "then", "else", "elseif", "for", "in", "do", "while",
             "return", "and", "or", "not", "nil", "true", "false", "repeat", "until"}


def _apply_body(reader: _Reader, body: str, project: Project, functions: dict[str, str],
                base_filter: str = "") -> None:
    """A small statement scanner for the premake subset this repository uses."""
    current = base_filter
    i, n = 0, len(body)
    ident = re.compile(r"[A-Za-z_][\w.]*")
    while i < n:
        ch = body[i]
        if ch in "\"'":
            i = _skip_string(body, i)
            continue
        m = ident.match(body, i)
        if not m or (i > 0 and (body[i - 1].isalnum() or body[i - 1] == "_")):
            i += 1
            continue
        name = m.group(0)
        j = m.end()
        while j < n and body[j] in " \t\r\n":
            j += 1
        nxt = body[j] if j < n else ""
        if name in _KEYWORDS:
            i = m.end()
            continue
        if nxt == "=" and not body.startswith("==", j):
            line_end = body.find("\n", j)
            i = n if line_end < 0 else line_end      # an assignment: skip the line
            continue
        if name == "filter":
            if nxt == "{":
                inner, i = _scan_group(body, j)
                current = ", ".join(reader.items(inner)) if inner.strip() else ""
            elif nxt in "\"'":
                end = _skip_string(body, j)
                current = body[j + 1:end - 1]
                i = end
            else:
                i = j
            continue
        if nxt == "(":
            args, end = _scan_group(body, j)
            if not args.strip() and name in functions:
                _apply_body(reader, functions[name], project, functions, current)
            elif name == "prebuildcommands":
                shader = re.fullmatch(r"\s*shaderCommands\s*\(\s*(" + _STRING + r")\s*\)\s*", args)
                if shader:
                    project.shader_flags[current] = shader.group(1)[1:-1]
                else:
                    project.prebuildcommands.append(Setting(current, reader.items(args.strip()[1:-1])
                                                            if args.strip().startswith("{") else [reader.item(args)]))
            i = end
            continue
        if nxt == "{":
            inner, i = _scan_group(body, j)
            values = reader.items(inner)
        elif nxt in "\"'":
            end = _skip_string(body, j)
            values = [body[j + 1:end - 1]]
            i = end
        else:
            i = m.end()
            continue
        if name in _LIST_ATTRS:
            getattr(project, name).append(Setting(current, values))
        elif name in _SCALAR_ATTRS:
            if Project._applies(current, "Debug") or current == "":
                setattr(project, name, values[0])
        # Everything else (targetdir, objdir, symbols, optimize, multiprocessorcompile,
        # externalwarnings, ...) does not change what is compiled on Linux.


def read(root: str) -> Workspace:
    path = os.path.join(root, "premake5.lua")
    with open(path, encoding="utf-8") as handle:
        text = strip_comments(handle.read())
    reader = _Reader(root, text)

    functions: dict[str, str] = {}
    for m in re.finditer(r"^local\s+function\s+(\w+)\s*\(\s*\)(.*?)^end\b", text, re.M | re.S):
        functions[m.group(1)] = m.group(2)

    projects: dict[str, Project] = {}
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'^project\s+["\']([^"\']+)["\']', text, re.M)]
    if not starts:
        raise PremakeParseError(f"{path}: no projects found")
    for index, (start, name) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        project = Project(name)
        _apply_body(reader, text[start:end], project, functions)
        projects[name] = project

    startproject = ""
    sp = re.search(r'startproject\s+["\']([^"\']+)["\']', text)
    if sp:
        startproject = sp.group(1)
    loc = re.search(r'^workspace\b.*?^\s*location\s+["\']([^"\']+)["\']', text, re.M | re.S)
    location = os.path.normpath(os.path.join(root, loc.group(1))) if loc else root

    rule = None
    stages_match = re.search(r"local\s+shaderStages\s*=\s*\{([^}]*)\}", text)
    if stages_match:
        env_match = re.search(r"--target-env=(\S+?)['\"\s]", text)
        glob_match = re.search(r'os\.matchfiles\("(\w+)/\*\*\.glsl"\)', text)
        if not (env_match and glob_match):
            raise PremakeParseError(f"{path}: shaderStages found but not --target-env / os.matchfiles")
        rule = ShaderRule(stages=dict(re.findall(r'(\w+)\s*=\s*"(\w+)"', stages_match.group(1))),
                          target_env=env_match.group(1), root=glob_match.group(1))
    return Workspace(root=root, projects=projects, shader_rule=rule, startproject=startproject,
                     location=location)


def _glob_regex(pattern: str) -> re.Pattern:
    """premake glob: `**` crosses directories, `*` does not."""
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


def expand_files(root: str, project: Project, configuration: str) -> list[str]:
    """The project's files, repo-relative, as premake would list them at generation time."""
    patterns = project.values("files", configuration)
    removals = [_glob_regex(p) for p in project.values("removefiles", configuration)]
    all_files: Optional[list[str]] = None
    out: list[str] = []
    for pattern in patterns:
        if "*" not in pattern:
            if os.path.exists(os.path.join(root, pattern)):
                out.append(pattern)
            continue
        if all_files is None:
            all_files = []
            for dirpath, dirs, names in os.walk(root, followlinks=True):
                rel_dir = os.path.relpath(dirpath, root)
                dirs[:] = [d for d in dirs if not (rel_dir == "." and d in (".git", "Build"))]
                for name in names:
                    all_files.append(os.path.normpath(os.path.join(rel_dir, name)))
        regex = _glob_regex(pattern)
        out.extend(f for f in all_files if regex.match(f))
    seen = set()
    result = []
    for f in out:
        if f not in seen and not any(r.match(f) for r in removals):
            seen.add(f)
            result.append(f)
    return sorted(result)


def shader_flags(project: Project, configuration: str) -> Optional[str]:
    for filt, flags in project.shader_flags.items():
        if Project._applies(filt, configuration):
            return flags
    return None
