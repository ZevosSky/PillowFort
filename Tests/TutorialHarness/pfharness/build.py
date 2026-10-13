"""
    @author Tutorial harness
    @brief  Builds any worktree of this repository on Linux, mirroring its own
            premake5.lua, with g++ and clang++; compiles its shaders the way the
            prebuild step does.
    @copyright 2026 Gary Yang

    MSVC is not available on Linux. -Wall -Wextra (premake's `warnings "Extra"`)
    is the stand-in for /W4. -Wshadow and -Wconversion are added because /W4
    also covers C4456-C4458 (shadowing) and C4244/C4267 (narrowing); those hits
    are reported in their own "msvc-approx" group: likely on MSVC, not certain.

    Linux substitutions, each one labelled where it is made:
      * GLFW is built with its own CMake for X11. premake's GLFW project lists
        only the Win32 backend (under `filter "system:windows"`).
      * shims/windows.h stands in for <windows.h> (IsDebuggerPresent,
        __debugbreak, GetModuleFileNameW). Platform API only - if a chapter's
        code ever needs it for something the chapter teaches, that is a finding.
      * `vulkan-1` links as libvulkan.so from the SDK directory.
      * _DEBUG is defined in Debug because MSVC's /MDd does; Log.h keys off it.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import premake

HARNESS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_ROOT = os.environ.get("PF_BUILD_ROOT", os.path.expanduser("~/.cache/pf-build"))
VULKAN_SDK = os.environ.get("PF_VULKAN_SDK") or os.environ.get("VULKAN_SDK") or "/opt/pf-vulkan-sdk"
JOBS = int(os.environ.get("PF_JOBS", os.cpu_count() or 4))

COMPILERS = {"gcc": ("gcc", "g++"), "clang": ("clang", "clang++")}
WARNINGS_EXTRA = ["-Wall", "-Wextra"]
MSVC_APPROX = ["-Wshadow", "-Wconversion", "-Wno-sign-conversion"]
MSVC_APPROX_FLAGS = ("-Wshadow", "-Wconversion", "-Wfloat-conversion", "-Wshorten-64-to-32",
                     "-Wimplicit-int-conversion", "-Wimplicit-float-conversion",
                     "-Wimplicit-int-float-conversion", "-Wshadow-field-in-constructor",
                     "-Wshadow-field", "-Wshadow-uncaptured-local", "-Warith-conversion")
# g++ warns about every member a designated initializer leaves out - the Vulkan
# create-info idiom this tutorial uses everywhere, which relies on zero-fill.
# MSVC says nothing at /W4. Counted per compiler, not listed.
GCC_IDIOM_FLAGS = ("-Wmissing-field-initializers",)
# Diagnostics that exist only because this is not Windows: reported, never counted.
PLATFORM_ONLY = [
    (re.compile(r"pragma warning|unknown pragma"), "MSVC-only #pragma warning"),
    (re.compile(r".%llu. expects argument of type .long long unsigned int.*has type .long unsigned int."
                r"|'unsigned long long' but the argument has type 'uint64_t'"),
     "uint64_t is unsigned long on LP64 Linux, unsigned long long on Windows"),
]
SHIM_DIR = os.path.join(HARNESS_DIR, "shims")


class BuildError(Exception):
    pass


@dataclass
class Diagnostic:
    compiler: str
    severity: str
    file: str
    line: int
    column: int
    message: str
    flag: str = ""
    group: str = ""        # standard / msvc-approx / platform-only

    def short(self) -> str:
        flag = f" [{self.flag}]" if self.flag else ""
        return f"{self.file}:{self.line}:{self.column}: {self.severity}: {self.message}{flag}"


@dataclass
class BuildResult:
    worktree: str
    configuration: str
    out_dir: str
    diagnostics: list[Diagnostic] = field(default_factory=list)
    failed: dict[str, list[str]] = field(default_factory=dict)      # compiler -> failing units / steps
    shader_errors: list[str] = field(default_factory=list)
    shader_count: int = 0
    executables: dict[str, str] = field(default_factory=dict)       # compiler -> path
    substitutions: list[str] = field(default_factory=list)
    header_problems: list[str] = field(default_factory=list)        # headers that do not compile alone

    @property
    def ok(self) -> bool:
        return not self.failed and not self.shader_errors

    def counted(self, group: Optional[str] = None) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity in ("warning", "error")
                and (group is None or d.group == group)]


def _run(cmd: list[str], cwd: Optional[str] = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


def _resolve_dir(root: str, inc: str) -> str:
    if inc.startswith("$VULKAN_SDK"):
        return VULKAN_SDK + inc[len("$VULKAN_SDK"):]
    if inc.startswith("$"):
        name, _, rest = inc[1:].partition("/")
        return os.environ.get(name, "") + ("/" + rest if rest else "")
    return os.path.normpath(os.path.join(root, inc))


def _is_vendor(path: str) -> bool:
    return path.startswith("Vendor/")


# ------------------------------------------------------------- diagnostics

_DIAG = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<sev>fatal error|error|warning|note): "
                   r"(?P<msg>.*?)(?: \[(?P<flag>-W[^\]]+)\])?$")


def parse_diagnostics(compiler: str, text: str, root: str) -> list[Diagnostic]:
    out = []
    for raw in text.splitlines():
        m = _DIAG.match(raw)
        if not m:
            continue
        path = os.path.normpath(m.group("file"))
        rel = os.path.relpath(path, root) if path.startswith(root + os.sep) else path
        diag = Diagnostic(compiler=compiler, severity="error" if m.group("sev") == "fatal error" else m.group("sev"),
                          file=rel, line=int(m.group("line")), column=int(m.group("col")),
                          message=m.group("msg"), flag=(m.group("flag") or "").split(",")[0])
        diag.group = "standard"
        for pattern, _why in PLATFORM_ONLY:
            if pattern.search(diag.message) or pattern.search(diag.flag):
                diag.group = "platform-only"
        if diag.group == "standard" and diag.flag.split("=")[0] in MSVC_APPROX_FLAGS:
            diag.group = "msvc-approx"
        if diag.group == "standard" and diag.flag in GCC_IDIOM_FLAGS:
            diag.group = "designated-init"
        out.append(diag)
    return out


# ------------------------------------------------------------- vendor: GLFW via CMake

_TREE_HASHES: dict[str, str] = {}
_SOURCE_EXTS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".inl", ".m", ".txt", ".cmake", ".in")


def tree_hash(path: str) -> str:
    """Content hash of a vendor tree's sources. No git: plain copies of a worktree must build too."""
    path = os.path.abspath(path)
    if path in _TREE_HASHES:
        return _TREE_HASHES[path]
    digest = hashlib.sha1()
    for dirpath, dirs, names in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(names):
            if name.endswith(_SOURCE_EXTS):
                full = os.path.join(dirpath, name)
                digest.update(os.path.relpath(full, path).encode() + b"\0")
                with open(full, "rb") as handle:
                    digest.update(handle.read())
    _TREE_HASHES[path] = digest.hexdigest()
    return _TREE_HASHES[path]


def glfw_library(root: str) -> str:
    source = os.path.join(root, "Vendor/GLFW")
    if not os.path.exists(os.path.join(source, "CMakeLists.txt")):
        raise BuildError(f"{source} is empty: initialize the submodules (or copy Vendor/ with the worktree)")
    build = os.path.join(BUILD_ROOT, "_vendor", f"glfw-x11-{tree_hash(source)[:16]}")
    lib = os.path.join(build, "src", "libglfw3.a")
    if os.path.exists(lib):
        return lib
    os.makedirs(os.path.dirname(build), exist_ok=True)
    with open(build + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)     # several agents may ask for the same GLFW at once
        if os.path.exists(lib):
            return lib
        _cmake_glfw(root, build)
    return lib


def _cmake_glfw(root: str, build: str) -> None:
    for cmd in (["cmake", "-S", os.path.join(root, "Vendor/GLFW"), "-B", build, "-G", "Ninja",
                 "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                 "-DGLFW_BUILD_WAYLAND=OFF", "-DGLFW_BUILD_X11=ON", "-DGLFW_BUILD_EXAMPLES=OFF",
                 "-DGLFW_BUILD_TESTS=OFF", "-DGLFW_BUILD_DOCS=OFF"],
                ["cmake", "--build", build, "-j", str(JOBS)]):
        code, out = _run(cmd)
        if code != 0:
            raise BuildError(f"GLFW (CMake, X11) failed:\n{out[-3000:]}")


# ------------------------------------------------------------- compile one project

_FILE_HASHES: dict[tuple, str] = {}


def _file_hash(path: str) -> str:
    """Content hash, memoized per (path, mtime, size) within one process."""
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key not in _FILE_HASHES:
        with open(path, "rb") as handle:
            _FILE_HASHES[key] = hashlib.sha1(handle.read()).hexdigest()
    return _FILE_HASHES[key]


def _depfile_inputs(depfile: str) -> list[str]:
    with open(depfile) as handle:
        return handle.read().replace("\\\n", " ").split(":", 1)[-1].split()


def _record_inputs(obj: str) -> None:
    """Fingerprint every input the compiler read (from its depfile), by CONTENT.

    Not by mtime: throwaway copies (`control`, `run --replace/--patch`) copy sources with
    their original, older mtimes, so after one patched build an mtime check would keep
    linking the patched object into the next, unpatched copy."""
    inputs = {dep: _file_hash(dep) for dep in _depfile_inputs(obj + ".d") if os.path.exists(dep)}
    with open(obj + ".inputs", "w") as handle:
        json.dump(inputs, handle)


def _up_to_date(obj: str, cmd_hash: str) -> bool:
    stamp, inputs_file = obj + ".cmd", obj + ".inputs"
    if not all(os.path.exists(p) for p in (obj, stamp, inputs_file, obj + ".log")):
        return False
    with open(stamp) as handle:
        if handle.read() != cmd_hash:
            return False
    with open(inputs_file) as handle:
        inputs = json.load(handle)
    return bool(inputs) and all(os.path.exists(dep) and _file_hash(dep) == digest
                                for dep, digest in inputs.items())


def _compile(job) -> tuple[str, int, str]:
    cmd, obj, src, shared = job
    os.makedirs(os.path.dirname(obj), exist_ok=True)
    cmd_hash = hashlib.sha1("\0".join(cmd).encode()).hexdigest()
    if (shared and os.path.exists(obj) and os.path.exists(obj + ".log")) or _up_to_date(obj, cmd_hash):
        with open(obj + ".log") as handle:
            return src, 0, handle.read()
    # Write beside, then rename: several agents may build the same shared vendor object at once.
    tmp = f"{obj}.{os.getpid()}.tmp"
    cmd = [tmp if c == obj else (tmp + ".d" if c == obj + ".d" else c) for c in cmd]
    code, text = _run(cmd)
    with open(obj + ".log", "w") as handle:
        handle.write(text)
    if code == 0:
        os.replace(tmp + ".d", obj + ".d")
        os.replace(tmp, obj)
        _record_inputs(obj)
        with open(obj + ".cmd", "w") as handle:
            handle.write(cmd_hash)
    else:
        for leftover in (tmp, tmp + ".d", obj):
            if os.path.exists(leftover):
                os.remove(leftover)
    return src, code, text


def default_name(root: str) -> str:
    """<folder>-<hash of the absolute path>: two agents' copies that share a folder name
    must not share a build directory."""
    root = os.path.abspath(root).rstrip("/")
    return f"{os.path.basename(root)}-{hashlib.sha1(root.encode()).hexdigest()[:8]}"


def build(root: str, *, configuration: str = "Debug", compilers: tuple[str, ...] = ("gcc", "clang"),
          name: Optional[str] = None, sanitize: bool = False, msvc_approx: bool = True,
          log=print) -> BuildResult:
    root = os.path.abspath(root)
    name = name or default_name(root)
    out_dir = os.path.join(BUILD_ROOT, name, configuration + ("-asan" if sanitize else ""))
    os.makedirs(out_dir, exist_ok=True)
    workspace = premake.read(root)
    result = BuildResult(worktree=root, configuration=configuration, out_dir=out_dir)

    app_name = workspace.startproject or next(n for n, p in workspace.projects.items()
                                               if p.kind in ("ConsoleApp", "WindowedApp"))
    app = workspace.projects[app_name]

    opt = ["-g", "-O0"] if configuration == "Debug" else ["-O2"]
    san = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if sanitize else []

    for compiler in compilers:
        cc, cxx = COMPILERS[compiler]
        libs: dict[str, str] = {}
        jobs = []
        project_units: dict[str, list[str]] = {}
        shared_roots: dict[str, str] = {}   # vendor projects whose objects live under _vendor
        for pname, project in workspace.projects.items():
            if pname == "GLFW":
                libs[pname] = glfw_library(root)
                note = ("GLFW: built by its own CMake for X11 (premake's GLFW project lists only the "
                        "Win32 backend under filter \"system:windows\")")
                if note not in result.substitutions:
                    result.substitutions.append(note)
                continue
            files = premake.expand_files(root, project, configuration)
            units = [f for f in files if f.endswith((".c", ".cpp", ".cc", ".cxx"))]
            vendor = project.warnings == "Off" or all(_is_vendor(f) for f in files)
            includes = []
            for inc in project.values("includedirs", configuration):
                path = _resolve_dir(root, inc)
                includes += (["-isystem", path] if inc.startswith("$") or _is_vendor(inc) else ["-I", path])
            for inc in project.values("externalincludedirs", configuration):
                includes += ["-isystem", _resolve_dir(root, inc)]
            if not vendor:
                includes += ["-isystem", SHIM_DIR]
            defines = [f"-D{d}" for d in project.values("defines", configuration)]
            if configuration == "Debug" and not vendor:
                defines.append("-D_DEBUG")
            warn = ["-w"] if vendor else WARNINGS_EXTRA + (MSVC_APPROX if msvc_approx else [])
            # Vendor objects are shared across worktrees: keyed by the submodule commit(s) and
            # the flags with the worktree path taken out, and reused without a dependency scan.
            obj_root = os.path.join(out_dir, "obj", compiler, pname)
            shared = False
            if vendor and units:
                modules = sorted({"/".join(u.split("/")[:2]) for u in units})
                hashes = [tree_hash(os.path.join(root, m)) for m in modules]
                key = hashlib.sha1("\0".join(hashes + opt + san + defines + includes).replace(root, "<root>")
                                   .encode()).hexdigest()[:16]
                obj_root = os.path.join(BUILD_ROOT, "_vendor", f"{pname}-{key}", compiler)
                shared = True
                shared_roots[pname] = obj_root
            project_units[pname] = []
            for unit in units:
                is_c = unit.endswith(".c")
                std = f"-std={(project.cdialect or 'c11').lower()}" if is_c else \
                      f"-std={(project.cppdialect or 'C++20').lower().replace('c++', 'c++')}"
                obj = os.path.join(obj_root, unit + ".o")
                cmd = [cc if is_c else cxx, std, *opt, *san, *warn, *defines, *includes, "-MMD", "-MF", obj + ".d",
                       "-c", os.path.join(root, unit), "-o", obj]
                jobs.append((cmd, obj, unit, shared))
                project_units[pname].append(obj)
            if not vendor and not result.substitutions.count("shims/windows.h on the include path"):
                result.substitutions.append("shims/windows.h on the include path")

        if compiler == compilers[0]:
            header_jobs = []
            for pname, project in workspace.projects.items():
                if pname == "GLFW" or project.warnings == "Off":
                    continue
                for header in premake.expand_files(root, project, configuration):
                    if header.endswith((".h", ".hpp")) and not _is_vendor(header):
                        flags = next((j[0] for j in jobs if f"/obj/{compiler}/{pname}/" in j[1]), None)
                        if flags:
                            header_jobs.append((flags, header))
        log(f"[{compiler}] compiling {len(jobs)} units")
        with ThreadPoolExecutor(JOBS) as pool:
            for unit, code, text in pool.map(_compile, jobs):
                if not _is_vendor(unit):
                    result.diagnostics += parse_diagnostics(compiler, text, root)
                if code != 0:
                    result.failed.setdefault(compiler, []).append(unit)
                    if not _DIAG.search(text):
                        result.diagnostics.append(Diagnostic(compiler, "error", unit, 0, 0, text.strip()[-800:], group="standard"))
        if compiler in result.failed:
            continue

        for pname, objects in project_units.items():
            project = workspace.projects[pname]
            if project.kind == "StaticLib":
                if not objects:
                    # premake reports success and produces no .lib; MSVC then fails with LNK1104.
                    result.failed.setdefault(compiler, []).append(
                        f"project {pname} matched no source files (MSVC: no .lib, then LNK1104 in its user)")
                    continue
                lib = os.path.join(out_dir, "lib", compiler, f"lib{pname}.a")
                os.makedirs(os.path.dirname(lib), exist_ok=True)
                if os.path.exists(lib):
                    os.remove(lib)
                # A shared vendor library is a thin archive: it names the objects under _vendor
                # instead of copying them, so a tree costs kilobytes for it, not the ~1 GB a
                # full copy of TinyUSDZ's Debug objects took in every tree.
                code, text = _run(["ar", "rcsT" if pname in shared_roots else "rcs", lib, *objects])
                if code != 0:
                    result.failed.setdefault(compiler, []).append(f"ar {pname}: {text}")
                libs[pname] = lib

        target_dir = os.path.join(out_dir, compiler, app_name)
        os.makedirs(target_dir, exist_ok=True)
        exe = os.path.join(target_dir, app_name)
        link_libs = []
        system_libs = []
        for link in app.values("links", configuration):
            if link in libs:
                link_libs.append(libs[link])
            elif link in ("vulkan-1", "vulkan"):
                system_libs += [f"-L{VULKAN_SDK}/Lib", "-lvulkan", f"-Wl,-rpath,{VULKAN_SDK}/Lib"]
            elif link in workspace.projects:
                pass   # a project that failed or produced nothing; already reported
            else:
                system_libs.append(f"-l{link}")
        # Static archives in premake order, then again so cross-references between them resolve.
        cmd = [COMPILERS[compiler][1], *san, "-o", exe, *project_units.get(app_name, []),
               "-Wl,--start-group", *link_libs, "-Wl,--end-group", *system_libs, "-ldl", "-lpthread", "-lm"]
        code, text = _run(cmd)
        if code != 0:
            result.failed.setdefault(compiler, []).append("link:\n" + text)
        else:
            result.executables[compiler] = exe
            for problem in (_build_commands(workspace, app, configuration, target_dir, "prebuildcommands", result)
                            + _build_commands(workspace, app, configuration, target_dir, "postbuildcommands", result)):
                result.failed.setdefault(compiler, []).append(problem)
            if "vulkan-1 -> -lvulkan" not in result.substitutions:
                result.substitutions.append("vulkan-1 -> -lvulkan")

    result.header_problems = _check_headers(root, header_jobs if compilers else [])
    _compile_shaders(root, workspace, app, configuration, result)
    with open(os.path.join(out_dir, "build-result.json"), "w") as handle:
        json.dump(asdict(result), handle, indent=2)
    return result


_TOKENS = {"COPYDIR", "COPYFILE", "MKDIR", "RMDIR", "DELETE", "ECHO"}


def _build_commands(workspace: premake.Workspace, project: premake.Project, configuration: str,
                    target_dir: str, attribute: str, result: BuildResult) -> list[str]:
    """Mirror premake's portable {TOKEN} build commands. Anything else is reported, not run:
    a raw shell command written for cmd.exe means nothing here."""
    problems = []
    for command in project.values(attribute, configuration):
        expanded = command
        for token, value in (("%{wks.location}", workspace.location), ("%{cfg.targetdir}", target_dir),
                             ("%{cfg.buildcfg}", configuration), ("%{prj.name}", project.name),
                             ("%{prj.location}", workspace.location)):
            expanded = expanded.replace(token, value)
        if "%{" in expanded:
            problems.append(f"{attribute}: unmirrored premake token in {command!r}")
            continue
        m = re.match(r"^\{(\w+)\}\s*(.*)$", expanded.strip())
        if not m or m.group(1) not in _TOKENS:
            problems.append(f"{attribute}: not a portable {{TOKEN}} command, not run on Linux: {command!r}")
            continue
        verb, args = m.group(1), [os.path.normpath(a) for a in shlex.split(m.group(2))]
        try:
            if verb == "COPYDIR":
                if not os.path.isdir(args[0]):
                    problems.append(f"{attribute}: {{COPYDIR}} source missing: {args[0]}")
                    continue
                shutil.copytree(args[0], args[1], dirs_exist_ok=True)
            elif verb == "COPYFILE":
                os.makedirs(os.path.dirname(args[1]) if not os.path.isdir(args[1]) else args[1], exist_ok=True)
                shutil.copy2(args[0], args[1])
            elif verb == "MKDIR":
                os.makedirs(args[0], exist_ok=True)
            elif verb == "RMDIR":
                shutil.rmtree(args[0], ignore_errors=True)
            elif verb == "DELETE":
                if os.path.exists(args[0]):
                    os.remove(args[0])
            note = f"{attribute} mirrored: {command}"
            if note not in result.substitutions:
                result.substitutions.append(note)
        except (OSError, IndexError) as error:
            problems.append(f"{attribute}: {command!r} failed: {error}")
    return problems


def _check_headers(root: str, header_jobs: list) -> list[str]:
    """Each header must compile on its own (`#include` it first in an empty file). Chapters
    state what a header includes; a header that only works after some other include is a
    trap for whoever includes it first. Advisory: reported, does not fail the build."""
    def check(job) -> Optional[str]:
        cmd, header = job
        flags = [c for c in cmd[1:cmd.index("-MMD")]]
        source = os.path.join(root, header)
        proc = subprocess.run([cmd[0], *flags, "-fsyntax-only", "-x", "c++", "-"],
                              input=f'#include "{source}"\n', stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            first = next((l for l in proc.stdout.splitlines() if "error" in l), proc.stdout.strip()[:300])
            return f"{header}: does not compile on its own: {first.replace(root + '/', '')}"
        return None
    with ThreadPoolExecutor(JOBS) as pool:
        return [p for p in pool.map(check, header_jobs) if p]


def _compile_shaders(root: str, workspace: premake.Workspace, app: premake.Project,
                     configuration: str, result: BuildResult) -> None:
    rule = workspace.shader_rule
    flags = premake.shader_flags(app, configuration)
    if rule is None or flags is None:
        return
    glslc = os.path.join(VULKAN_SDK, "Bin", "glslc")
    shader_root = os.path.join(root, rule.root)
    staging = os.path.join(result.out_dir, "shaders")
    for dirpath, _dirs, names in os.walk(shader_root):
        for fname in sorted(names):
            if not fname.endswith(".glsl"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), shader_root)[:-len(".glsl")]   # Triangle/Triangle.vert
            stage = rule.stages.get(rel.rsplit(".", 1)[-1]) if "." in rel else None
            if not stage:
                continue      # an include, compiled only through the files that use it
            out = os.path.join(staging, rule.root, rel + ".spv")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            cmd = [glslc, f"-fshader-stage={stage}", f"--target-env={rule.target_env}", *shlex.split(flags),
                   "-I", os.path.join(shader_root, "Include"), os.path.join(shader_root, rel + ".glsl"), "-o", out]
            code, text = _run(cmd)
            result.shader_count += 1
            if code != 0:
                result.shader_errors.append(f"{rule.root}/{rel}.glsl ({flags}):\n{text.replace(root + '/', '')}")
            elif text.strip():
                result.diagnostics.append(Diagnostic("glslc", "warning", f"{rule.root}/{rel}.glsl", 0, 0,
                                                     text.strip(), group="standard"))
    # Beside each executable, mirrored, as premake's {MKDIR} + -o "%{cfg.targetdir}/Shaders/..." does.
    for exe in result.executables.values():
        dest = os.path.join(os.path.dirname(exe), rule.root)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        if os.path.exists(os.path.join(staging, rule.root)):
            shutil.copytree(os.path.join(staging, rule.root), dest)


def summarize(result: BuildResult) -> str:
    lines = [f"build {result.worktree} [{result.configuration}] -> {result.out_dir}"]
    for sub in result.substitutions:
        lines.append(f"  linux substitution: {sub}")
    for compiler in sorted({d.compiler for d in result.diagnostics} | set(result.failed)):
        ds = [d for d in result.diagnostics if d.compiler == compiler and d.severity in ("warning", "error")]
        groups = {}
        for d in ds:
            groups.setdefault(d.group, []).append(d)
        status = "FAILED" if compiler in result.failed else "ok"
        counts = ", ".join(f"{g}: {len(v)}" for g, v in sorted(groups.items())) or "no warnings"
        lines.append(f"  {compiler}: {status} ({counts})")
        if groups.get("designated-init"):
            lines.append(f"    (designated-init: g++ -Wmissing-field-initializers on omitted members of "
                         f"aggregate initializers; MSVC /W4 is silent - not listed)")
        seen = set()
        for d in ds:
            if d.group == "designated-init":
                continue
            key = (d.file, d.line, d.message)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"    [{d.group}] {d.short()}")
        for item in result.failed.get(compiler, []):
            lines.append(f"    FAILED: {item.strip()[:2000]}")
    lines.append(f"  headers compiled on their own: {len(result.header_problems)} problem(s)")
    for problem in result.header_problems:
        lines.append(f"    {problem}")
    lines.append(f"  shaders: {result.shader_count} compiled, {len(result.shader_errors)} failed")
    for err in result.shader_errors:
        lines.append("    " + err.replace("\n", "\n    "))
    for compiler, exe in result.executables.items():
        lines.append(f"  executable ({compiler}): {exe}")
    return "\n".join(lines)
