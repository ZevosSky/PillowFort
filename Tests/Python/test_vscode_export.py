r"""Exercise generated IntelliSense settings with the native C/C++ compiler.

Run from a VS developer shell on Windows, or the configured Linux harness shell:
    python Tests/Python/test_vscode_export.py --premake Vendor/premake5/premake5.exe
    python3 Tests/Python/test_vscode_export.py --premake /path/to/premake5 \
        --compiler gcc --linux-harness-dir /path/to/Tests/TutorialHarness

Only the standard library is required. Probes and compiler logs go in Build/EditorTests.
"""

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


CONFIGURATIONS = ("Debug", "Release", "Dist")
SOURCE_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def path_key(value: str | Path, directory: Path) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = directory / candidate
    return os.path.normcase(str(candidate.resolve()))


def include_paths(arguments: list[str], directory: Path) -> set[str]:
    paths = set()
    prefixes = ("/external:I", "-isystem", "-iquote", "/I", "-I")
    iterator = iter(arguments[1:])
    for argument in iterator:
        for prefix in prefixes:
            if argument.startswith(prefix):
                value = argument[len(prefix):] or next(iterator, "")
                require(bool(value), f"Include option has no path: {argument}")
                paths.add(path_key(value, directory))
                break
    return paths


def run(command: list[str], directory: Path, log: Path, expect_success=True) -> None:
    result = subprocess.run(command, cwd=directory, capture_output=True,
                            text=True, errors="replace", timeout=180)
    output = result.stdout + result.stderr
    log.write_text(output, encoding="utf-8")
    if expect_success:
        require(result.returncode == 0,
                f"Compiler/generator failed ({result.returncode}); see {log}\n{output[-6000:]}")
    else:
        require(result.returncode != 0,
                f"SandboxGame unexpectedly accepts TinyUSDZ headers; see {log}")
        require("tinyusdz.hh" in output and
                any(marker in output.lower() for marker in
                    ("no such file", "cannot open", "file not found")),
                f"Negative include probe failed for an unexpected reason; see {log}\n{output[-3000:]}")


def syntax_command(entry: dict, source: Path, msvc: bool) -> list[str]:
    """Keep the exported flags, replacing just the compile operation and source."""
    directory = Path(entry["directory"])
    original = path_key(entry["file"], directory)
    arguments = entry["arguments"]
    flags = []
    for argument in arguments[1:]:
        if argument in ("/c", "-c"):
            continue
        if path_key(argument, directory) == original:
            continue
        flags.append(argument)
    return [arguments[0], *flags, "/Zs" if msvc else "-fsyntax-only", str(source)]


def header_probe(configuration: str, debug_runtime: bool, tinyusdz=False, windows_header=False) -> str:
    expected = {"Debug": "PF_DEBUG", "Release": "PF_RELEASE", "Dist": "PF_DIST"}[configuration]
    other = [name for name in ("PF_DEBUG", "PF_RELEASE", "PF_DIST") if name != expected]
    debug_guard = "ifndef" if debug_runtime else "ifdef"
    tiny_header = "#include <tinyusdz.hh>\n" if tinyusdz else ""
    platform_header = "#include <windows.h>\n" if windows_header else ""
    return f"""#ifndef {expected}
#error Missing configuration define
#endif
#if defined({other[0]}) || defined({other[1]})
#error Defines from another configuration leaked in
#endif
#{debug_guard} _DEBUG
#error Incorrect debug runtime define
#endif
#ifndef GLM_ENABLE_EXPERIMENTAL
#error Missing GLM experimental define
#endif
#ifndef GLM_FORCE_DEPTH_ZERO_TO_ONE
#error Missing Vulkan GLM depth convention
#endif
#if defined(_MSVC_LANG)
static_assert(_MSVC_LANG >= 202002L);
#else
static_assert(__cplusplus >= 202002L);
#endif
{platform_header}
#include <concepts>
#include <span>
#include <glm/glm.hpp>
#include <glm/gtx/transform.hpp>
#include <vulkan/vulkan.h>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <imgui.h>
#include <imgui_impl_vulkan.h>
#include <PillowFort/ErrorReporting/Log.h>
{tiny_header}
template<std::integral T> constexpr T twice(T value) {{ return value + value; }}
static_assert(twice(3) == 6);
glm::mat4 transform = glm::translate(glm::vec3(1.0f));
VkApplicationInfo application{{ VK_STRUCTURE_TYPE_APPLICATION_INFO }};
std::span<const int> values;
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--premake", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--compiler", choices=("msc", "gcc", "clang"))
    parser.add_argument("--linux-harness-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    system = platform.system()
    require(system in ("Windows", "Linux"), "Run these native tests on Windows or Linux.")
    compiler = args.compiler or ("msc" if system == "Windows" else "gcc")
    msvc = compiler == "msc"
    require((system == "Windows") == msvc,
            "Use msc on Windows and gcc/clang on Linux for these native checks.")
    require(not args.linux_harness_dir or system == "Linux",
            "The Linux harness option requires Linux.")
    premake = args.premake.resolve()
    output = repo / "Build" / "EditorTests" / f"{system.lower()}-{compiler}"
    output.mkdir(parents=True, exist_ok=True)
    generate = [str(premake)]
    if not msvc:
        generate.append(f"--cc={compiler}")
    if args.linux_harness_dir:
        generate.append(f"--linux-harness-dir={args.linux_harness_dir.resolve()}")
    generate.append("vscode")
    run(generate, repo, output / "generation.log")

    settings = json.loads((repo / ".vscode" / "c_cpp_properties.json").read_text(encoding="utf-8"))
    require(settings.get("version") == 4, "Unsupported C/C++ configuration schema.")
    profiles = {profile["name"]: profile for profile in settings["configurations"]}
    require(set(profiles) == set(CONFIGURATIONS), "Export must provide all three build configurations.")
    sources = {path_key(path, repo) for path in (repo / "Source").rglob("*")
               if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS}
    require(bool(sources), "The repository has no source files to test.")
    engine_log = repo / "Source" / "PillowFort" / "ErrorReporting" / "Log.cpp"
    game_main = repo / "Source" / "SandboxGame" / "Main.cpp"
    tiny_include = repo / "Vendor" / "TinyUSDZ" / "src"
    # Reference branches own this private engine dependency; main does not.
    project_definitions = (repo / "premake5.lua").read_text(encoding="utf-8")
    engine_definition = project_definitions.split('project "PillowFortEngine"', 1)[1].split("\nproject ", 1)[0]
    tiny_dependency = "Vendor/TinyUSDZ/src" in engine_definition
    if tiny_dependency:
        require((tiny_include / "tinyusdz.hh").is_file(),
                "Initialize the TinyUSDZ submodule before running reference checks.")

    for configuration in CONFIGURATIONS:
        profile = profiles[configuration]
        require(profile.get("cppStandard") == "c++20", f"{configuration} fallback is not C++20.")
        expected_macro = {"Debug": "PF_DEBUG", "Release": "PF_RELEASE", "Dist": "PF_DIST"}[configuration]
        fallback_defines = set(profile.get("defines", []))
        require({"GLM_ENABLE_EXPERIMENTAL", "GLM_FORCE_DEPTH_ZERO_TO_ONE", expected_macro}
                <= fallback_defines, f"{configuration} fallback defines are incomplete.")
        require(fallback_defines & {"PF_DEBUG", "PF_RELEASE", "PF_DIST"} == {expected_macro},
                f"{configuration} fallback contains another build configuration's defines.")
        debug_runtime = configuration == "Debug" and (msvc or bool(args.linux_harness_dir))
        require(("_DEBUG" in fallback_defines) == debug_runtime,
                f"{configuration} fallback has the wrong debug runtime define.")
        require(profile.get("intelliSenseMode") ==
                f"{system.lower()}-{'msvc' if msvc else compiler}-x64",
                f"{configuration} IntelliSense target does not match the native compiler.")
        database_path = profile.get("compileCommands", "").replace("${workspaceFolder}", str(repo))
        require(bool(database_path), f"{configuration} has no per-file compilation database.")
        database = Path(database_path)
        if not database.is_absolute():
            database = repo / database
        expected_database = repo / "Build" / "IntelliSense" / configuration / "compile_commands.json"
        require(path_key(database, repo) == path_key(expected_database, repo),
                f"{configuration} profile points at a different configuration's database.")
        entries = json.loads(database.read_text(encoding="utf-8"))
        require(isinstance(entries, list) and bool(entries), f"{configuration} database is empty.")
        by_source = {}
        for entry in entries:
            require(Path(entry["directory"]).is_absolute() and Path(entry["file"]).is_absolute(),
                    "Compilation database paths must be absolute.")
            require(path_key(entry["directory"], repo) == path_key(repo, repo),
                    "Compilation database uses an unexpected working directory.")
            arguments = entry.get("arguments")
            require(isinstance(arguments, list) and len(arguments) > 2 and
                    all(isinstance(argument, str) and argument for argument in arguments),
                    "Compile commands must contain nonempty argument arrays.")
            require("/c" in arguments if msvc else "-c" in arguments,
                    "Compile command does not compile an individual translation unit.")
            key = path_key(entry["file"], repo)
            require(key not in by_source, f"Duplicate compile command: {entry['file']}")
            require(any(path_key(argument, repo) == key for argument in arguments[1:]),
                    f"Compile command does not name its source: {entry['file']}")
            by_source[key] = entry
        require(sources <= set(by_source),
                f"{configuration} omits source files: {sorted(sources - set(by_source))}")

        engine_entry = by_source[path_key(engine_log, repo)]
        game_entry = by_source[path_key(game_main, repo)]
        if tiny_dependency:
            private_path = path_key(tiny_include, repo)
            require(private_path in include_paths(engine_entry["arguments"], repo),
                    "Engine's private TinyUSDZ include directory is missing.")
            require(private_path not in include_paths(game_entry["arguments"], repo),
                    "Engine's private TinyUSDZ include directory leaked into SandboxGame.")
        run(syntax_command(engine_entry, engine_log, msvc), repo,
            output / f"{configuration}-Log.log")
        for name, entry in (("Engine", engine_entry), ("Game", game_entry)):
            probe = output / f"{configuration}-{name}-headers.cpp"
            probe.write_text(header_probe(configuration, debug_runtime,
                                          tinyusdz=tiny_dependency and name == "Engine",
                                          windows_header=msvc or bool(args.linux_harness_dir)),
                             encoding="utf-8")
            run(syntax_command(entry, probe, msvc), repo,
                output / f"{configuration}-{name}-headers.log")
        if tiny_dependency:
            probe = output / f"{configuration}-Game-private-include.cpp"
            probe.write_text("#include <tinyusdz.hh>\n", encoding="utf-8")
            run(syntax_command(game_entry, probe, msvc), repo,
                output / f"{configuration}-Game-private-include.log", expect_success=False)
        print(f"PASS {configuration}: {len(sources)} sources covered; native Log/header probes accepted")
    print(f"PASS {system} {compiler}: logs and probes in {output}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
