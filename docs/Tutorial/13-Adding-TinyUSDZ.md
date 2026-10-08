# 13 — Adding a Library: TinyUSDZ

**Goal:** TinyUSDZ, pinned as a submodule and compiled by a premake project of
its own, loads a hand-written `.usda` file and logs its prim tree at startup —
and you know enough of USD to read that file, and any other, line by line.

**ROADMAP:** step 14.

**Module:** `UsdImport`, namespace `pf::usd_import` — new, and the only code
that will ever include a TinyUSDZ header. Changes to `premake5.lua`,
`.gitmodules`, `THIRD_PARTY_NOTICES.md`, and `Source/SandboxGame/Main.cpp`,
and a new `Assets/` folder.

**Prerequisites:**

- Chapter 01 section 3 (the workspace: `apply_vendor_settings`, the GLFW and
  ImGui projects, which projects get which `includedirs`) and section 4
  (submodules, pins, `git submodule status`, `THIRD_PARTY_NOTICES.md`).
- Chapter 02 section 0 (`InitializationResult`).
- Chapter 06 section 1 (files the program reads live beside the executable and
  are found through `executableDirectory()`; the IDE's up-to-date check and
  build steps).
- Chapter 09 section 7 (`main`'s shape: `parseSettings` first, then the
  window, the renderer, and the demo list).
- Chapter 12 (the scene graph) is *not* needed yet. This chapter only reads a
  file and prints it; Chapter 14 turns what it reads into scene nodes.

The chapter has two halves that teach different things. **Sections 1-6 are a
recipe for adding any compiled third-party library to this repository**,
worked through on TinyUSDZ so every step has a real decision in it. **Sections
7-12 are USD itself** — just enough of its model to read a scene file and to
know what Chapter 14 must convert. Section 13 joins them: twenty lines of code
that load a stage and print it.

### What changes, and where

```text
.gitmodules                             section 2: the submodule (git writes it)
Vendor/TinyUSDZ/                        section 2: the pinned source tree
premake5.lua                            sections 3-4: the TinyUSDZ project; section 5: what links it; section 6: the Assets copy
THIRD_PARTY_NOTICES.md                  section 5: TinyUSDZ and what it bundles
Assets/Scenes/FirstStage.usda           section 13: the hand-written test file
Source/PillowFort/UsdImport/            new module
  UsdImport.h, .cpp                     section 13: LogUsdPrimTree
Source/SandboxGame/Main.cpp             section 13: one call at startup
```

Files are added here, so **rerun `GenerateProjects.bat`** once they are on
disk — and once more after the submodule exists, since that is what puts 153
TinyUSDZ sources into a project (section 4).

---

## 1. What kind of library this is

**This is the decision that shapes everything after it.** A C++ library
reaches your program in one of two forms, and they cost very different
amounts:

- **Header-only** — GLM, VMA, `stb_image.h`. The code is in headers; using it
  is an include path, and (for the "single-header" kind) one translation unit
  that `#define`s the implementation, as Chapter 08 section 7 did for VMA.
  Nothing to build, nothing to link.
- **Compiled** — GLFW, ImGui, TinyUSDZ. There are `.c`/`.cc` files that must be
  compiled with the right defines and options, into a library you link.

TinyUSDZ is compiled, and big: about a hundred and fifty source files at the
pin chosen below, with CMake as its build system. That leaves two ways to get it
into a premake workspace:

1. **Run its CMake, link what it produces.** Fast to set up once. But now two
   build systems produce objects for one executable, and they must agree on
   everything that affects the binary interface — runtime library (`/MD` versus
   `/MDd`), architecture, and every define a header looks at — for every
   configuration, by hand. When they disagree MSVC says `LNK2038: mismatch
   detected for 'RuntimeLibrary'`, or, worse, says nothing. And
   `GenerateProjects.bat` is no longer the one step from a clean clone to a
   solution, which ROADMAP's "three commands" promises.
2. **Write a premake project that compiles its sources.** This is what
   Chapter 01 did for GLFW and ImGui, whose own builds are CMake too. The
   library is then built by the same tool, with the same configurations and
   runtime, as everything else, and ROADMAP's guardrail 3 — *premake is
   authoritative for compiling and linking* — stays true.

The second costs one careful read of the library's CMake file, which is
sections 3 and 4. It is the right trade for a library you will build for
years.

Why TinyUSDZ and not Pixar's OpenUSD is decided — ROADMAP's decision table
(the Scenes row) records it — but the reason is worth knowing, because it is
the same test you would apply to any library: OpenUSD needs Python and CMake to build, depends on TBB and Boost
in many configurations, and finds its file-format support through plugins it
loads as DLLs at runtime. TinyUSDZ has no dependencies outside its own tree,
which is what makes the second option possible at all.

---

## 2. Picking and pinning a revision

**This is choosing exactly which TinyUSDZ you build** — a commit, written into
the repository, so that a clone next year builds the same code you built today.
A submodule records a commit hash, not a version or a branch; that hash is
the pin.

Look at what is available before choosing. In a scratch clone:

```bash
git clone https://github.com/lighttransport/tinyusdz.git
git -C tinyusdz tag --list "v*" --sort=-creatordate
```

In October 2026 the newest tags are four `v1.0.0` release candidates,
published within five days of each other, then the 0.9.9 candidates, then
**`v0.9.4` (2026-05-05)**, the newest tag that is not a candidate. The rule
that picks from such a list: **pin the newest release that is not a release
candidate.** A pin is supposed to be something you do not think about for
months, and a candidate is something its own authors expect to replace within
days. (1.0 also renames the project *LightUSD*, with a new header and
namespace; this tutorial stays on 0.9.4 under the name it uses everywhere, and
section 5's rule that only `UsdImport/` sees the library keeps a later move to
one folder.)

So the pin is **`v0.9.4`, commit `dc7684519883358379964a9e6f925969d7477df3`**.

> **Note:** do not trust a library's version constants to tell you what you
> have. At this tag `tinyusdz.hh` still says `version_minor = 9;
> version_micro = 1;` — 0.9.1. The commit hash is the only statement of the
> version that cannot be stale.

Add it as Chapter 01 section 4 changed the other pins: clone into `Vendor/`,
check out the tag inside the submodule, then record the new commit in the
parent repository.

```bash
git submodule add https://github.com/lighttransport/tinyusdz.git Vendor/TinyUSDZ
git -C Vendor/TinyUSDZ checkout v0.9.4
git add .gitmodules Vendor/TinyUSDZ
git submodule status
```

`git submodule status` should list
`dc7684519883358379964a9e6f925969d7477df3 Vendor/TinyUSDZ (v0.9.4)` beside the
GLFW and ImGui lines, with no leading `+` (which would mean the checkout and
the recorded commit disagree). Three things worth knowing:

- **The URL.** GitHub serves the repository under its new name too
  (`lighttransport/lightusd`); if the old one ever stops resolving, change the
  `url` in `.gitmodules` and run `git submodule sync`. The pin does not change.
- **The size.** The clone carries the project's whole history — about 180 MB,
  far more than GLFW and ImGui together. That is a one-time cost per clone.
- **No nested submodules.** TinyUSDZ vendors its own dependencies as plain
  files in `src/external/`, so `git submodule update --init --recursive` — the
  first of ROADMAP's three commands — is all a fresh clone needs.

---

## 3. Choosing what to compile

**This is reading TinyUSDZ's `CMakeLists.txt`** to find which files, defines,
and compiler options produce the library — the authoritative answer, in the
same way Chapter 01 section 4 sent you to GLFW's `src/CMakeLists.txt`. Do not
take the list from a directory listing: `src/` and its `tydra/`, `core/`, and
`crate-path-utils/` folders hold 175 `.cc` files at this pin, and the build
compiles 149 of them. Some of the others are Python
bindings, some are features you have not turned on, and some do not compile at
all — they are leftovers no build uses (`prim-reconstruct-light.cc`, for one,
fails with a dozen errors). A glob would pull them in.

The file is long, but its shape is simple. Three lists build up the sources:

| CMake variable | What it holds |
| --- | --- |
| `TINYUSDZ_SOURCES` | The core: the `.usda` and `.usdc` parsers, the writers, every schema type, `Stage`. Always compiled. |
| the `if (TINYUSDZ_WITH_TYDRA)` block | *Tydra*, TinyUSDZ's helpers for applications that render: scene traversal, material-binding lookup, a whole-scene converter. |
| `TINYUSDZ_DEP_SOURCES` | Bundled third-party code: always LZ4 (USD's binary format compresses with it), and more depending on options. |

and a list of `option(...)` lines decides what joins them. These are the
options this project uses, and the reason for each:

| Option | Default | Here | Why |
| --- | --- | --- | --- |
| `TINYUSDZ_WITH_TYDRA` | on | **on** | Chapter 15 finds a mesh's material with Tydra's `GetBoundMaterial`. Chapter 14 uses one helper. |
| `TINYUSDZ_WITH_BUILTIN_IMAGE_LOADER` | on | **on** | `stb_image` inside TinyUSDZ, so Chapter 15 can decode PNG and JPEG textures with `tinyusdz::image::LoadImageFromFile`. |
| `TINYUSDZ_WITH_EXR`, `_WITH_TIFF` | on, off | off | Float textures. Not used by this tutorial; three more files and a define to turn on. |
| `TINYUSDZ_WITH_COLORIO` | on | off | Color-space lookup tables. Only sets a define that nothing in this file list reads. |
| `TINYUSDZ_WITH_USDMTLX` | on | off | MaterialX. Blender writes `UsdPreviewSurface` unless asked otherwise; Chapter 15 reads that. |
| `TINYUSDZ_WITH_JSON`, `_USDOBJ`, `_USDVOX`, `_USDFBX`, `_AUDIO` | mixed | off | Converters and formats a USD viewer does not need. |
| `TINYUSDZ_WITH_ZSTD_COMPRESSION` | on | off | A TinyUSDZ-only extension to the binary format. Files from Blender or Pixar's tools never use it. |
| `TINYUSDZ_WITH_PXR_COMPAT_API`, `_WITH_PYTHON`, `_WITH_C_API` | mixed | off | Other ways to call the library. |
| `TINYUSDZ_BUILD_TESTS`, `_EXAMPLES`, `_TOOLS` | mixed | off | Not part of the library. |

Two consequences need saying out loud, because they reach later chapters:

- **`stb_image` is now defined inside `TinyUSDZ.lib`.** TinyUSDZ's
  `image-loader.cc` defines `STB_IMAGE_IMPLEMENTATION`, `image-writer.cc`
  defines `STB_IMAGE_WRITE_IMPLEMENTATION`, and `image-util.cc` defines
  `STB_IMAGE_RESIZE_IMPLEMENTATION`. If any PillowFort file defines one of
  those again, the linker sees every `stbi_*` function twice. Use TinyUSDZ's
  image functions, or include `stb_image.h` *without* the define.
- **Some core files survive every option.** `usdObj.cc` and the MaterialX
  parser (`mtlx-*.cc`, `usdMtlx.cc`) are in `TINYUSDZ_SOURCES` itself; only
  their third-party parts depend on the options. They compile without them.

The safe way to turn that table into a file list is to let CMake do it once.
On any machine with CMake (Visual Studio installs one; Linux or WSL is quicker
to type), configure with the options above and ask for a compile database:

```bash
cmake -S Vendor/TinyUSDZ -B build-tinyusdz-list -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DTINYUSDZ_BUILD_TESTS=OFF -DTINYUSDZ_BUILD_EXAMPLES=OFF -DTINYUSDZ_WITH_TYDRA=ON -DTINYUSDZ_WITH_BUILTIN_IMAGE_LOADER=ON -DTINYUSDZ_WITH_EXR=OFF -DTINYUSDZ_WITH_COLORIO=OFF -DTINYUSDZ_WITH_USDMTLX=OFF -DTINYUSDZ_WITH_JSON=OFF -DTINYUSDZ_WITH_USDOBJ=OFF -DTINYUSDZ_WITH_USDVOX=OFF -DTINYUSDZ_WITH_AUDIO=OFF -DTINYUSDZ_WITH_ZSTD_COMPRESSION=OFF -DTINYUSDZ_WITH_PXR_COMPAT_API=OFF -DTINYUSDZ_WITH_USD_TO_GLTF=OFF
```

`build-tinyusdz-list/compile_commands.json` then holds one entry per source
file with the exact command line — 153 files, and every `-D`. (The Visual
Studio generator does not write this file; a Ninja or Makefile generator
does.) It is a scratch step: delete the folder afterwards, and do not add
CMake to the build. The list in section 4 *is* that output.

**Defines.** CMake passes two, `TINYUSDZ_WITH_TYDRA` and `FPNG_NO_SSE=1`, and
at this pin both do nothing (no source tests the first; `fpng.cpp` defaults the
second to 1). Check defines rather than copying them, because **a define that
changes a header changes the binary interface**: it must then reach every
project that includes the header, not just the library's. The headers the
engine includes have two such switches, and this build sets neither.

One define is easy to miss, because it is not TinyUSDZ's: with MSVC, CMake's
default flags are `/DWIN32 /D_WINDOWS`, on every file of every target, and a
compile database made on Linux never shows them. TinyUSDZ depends on `WIN32`.
`io-util.hh` gives its `MMapFileHandle` two Windows-only members under
`#if defined(WIN32)` (not `_WIN32`, which MSVC always defines), and
`<windows.h>` defines `WIN32` too. Without the define, `io-util.cc`, which
includes `<windows.h>` first, and `tinyusdz.cc`, which does not, compile two
different structs under one name: `LoadUSDFromFile` makes the small one, and
`MMapFile` writes the large one's members past its end and crashes. So the
project defines `WIN32` on Windows. `io-util.hh` is included only by
TinyUSDZ's own sources, so the define stays in the library's project.

**Compiler options.** CMake's `if(MSVC)` branches set:

| What CMake sets | premake | Why |
| --- | --- | --- |
| `/bigobj` | `buildoptions` | Several files exceed an object file's default 2^16 sections; without it MSVC stops with `C1128`. TinyUSDZ's own comment says so. |
| `/MP` | `multiprocessorcompile "On"` | Compile the project's files in parallel. `MSBuild /m` only runs *projects* in parallel; 153 files one at a time is minutes. |
| C++ exceptions on | nothing to do | Premake's default is MSVC's default, `/EHsc`. |
| C++17 | `cppdialect "C++17"` | What the library is written and tested against. The engine stays C++20; mixing the two between translation units is fine, and TinyUSDZ's *headers* are compiled as C++20 inside `UsdImport.cpp` anyway. |

RTTI is left on too (TinyUSDZ uses `dynamic_cast`). One option is added that
CMake does not set: **`/utf-8`**. Some sources contain UTF-8 text without a
byte-order mark, which MSVC would otherwise read in the system code page —
harmless on a Western one, warning `C4819` or a mis-read line on a Japanese or
Chinese one. `/utf-8` says what the files are.

---

## 4. The premake project

**This is the TinyUSDZ project in `premake5.lua`,** after the `ImGui` project
and before `PillowFortEngine` — the vendor projects first, as in Chapter 01.
It is the GLFW project's shape: `kind "StaticLib"`, `apply_vendor_settings()`
(warnings off, output folders, `symbols` and `optimize` per configuration), an
explicit `files` list, and the include directory the library's own sources
need.

The list is written out in full, in CMake's order, rather than as a glob plus
exclusions. A glob would pick up the 26 sources CMake leaves out, and since
premake expands globs when it generates, a pin that adds or removes files would
change the build silently. An explicit list is checked by the compiler instead:
a file that does not exist is `C1083: Cannot open source file` with its name.
A glob that matches nothing is worse still: it is the trap Chapter 01 section
3 warns about (a glob that matches nothing builds no `.lib`, and fails later as
`LNK1104`). An explicit list can never match nothing.

The list itself is 153 lines and is in this chapter's **Appendix**; the
project around it is short:

```lua
-- TinyUSDZ v0.9.4 (Chapter 13). The file list is TinyUSDZ's own CMakeLists.txt
-- for the options in Chapter 13 section 3, one line per source, in its order:
-- ${PROJECT_SOURCE_DIR} became "Vendor/TinyUSDZ". Re-derive it when the pin moves.
project "TinyUSDZ"
    kind "StaticLib"
    language "C++"
    cppdialect "C++17"            -- what TinyUSDZ's CMake asks for; it is not tested as C++20
    apply_vendor_settings()

    files
    {
        -- the 153 sources listed in this chapter's Appendix, one per line, in CMake's order
    }

    includedirs { "Vendor/TinyUSDZ/src" }

    -- CMake passes TINYUSDZ_WITH_TYDRA and FPNG_NO_SSE=1, but at this pin no source reads the
    -- first and fpng.cpp defaults the second to 1 itself (section 3). The one define that
    -- matters is one CMake passes without saying so: WIN32, below.

    -- CMake's default MSVC flags carry /DWIN32. io-util.hh gives MMapFileHandle two more members
    -- when WIN32 is defined, and windows.h defines it too, so without this io-util.cc (which
    -- includes windows.h first) and tinyusdz.cc disagree on the struct, and the first
    -- LoadUSDFromFile writes past it and crashes. Only TinyUSDZ's own sources include io-util.hh.
    filter "system:windows"
        defines { "WIN32" }
    filter {}

    multiprocessorcompile "On"     -- /MP: 153 heavy files; MSBuild /m alone builds them one at a time

    filter "toolset:msc*"
        buildoptions
        {
            "/bigobj",            -- TinyUSDZ's CMake sets it: some files exceed 2^16 sections (C1128)
            "/utf-8"              -- its sources are UTF-8, four of them without a BOM
        }
        -- For lib.exe, which warnings "Off" does not reach: 200 functions are defined twice, all
        -- identically (ascii-parser-basetype-typedarray.cc #includes ascii-parser-basetype.cc, and
        -- core/prim-enums.cc repeats three of prim-types.cc's), and each is an LNK4006.
        linkoptions { "/IGNORE:4006" }
    filter {}
```

A few lines deserve a second look:

- **`language "C++"` with `.c` files in the list.** `lz4.c` and
  `mikktspace.c` are C; Visual Studio compiles a `.c` file as C whatever the
  project's language says, exactly as for GLFW's sources. Nothing to do.
- **`filter "toolset:msc*"`**, not `filter "system:windows"`: the options are
  the compiler's, not the operating system's. `clang-cl` on Windows would
  also take them; MinGW would not. `WIN32` is the other way round: it is about
  the operating system, so it is under `filter "system:windows"`.
- **`linkoptions` in a static library** reach `lib.exe`, the librarian, which
  is the program that reports `LNK4006` here. `warnings "Off"` is `/W0` for
  the compiler only. Both duplicates are TinyUSDZ's own and identical, so the
  first copy is as good as the second; `/IGNORE:4006` names the one warning,
  so a duplicate of any other kind still reports.

---

## 5. Who includes it, who links it, and the notices

**This is the rest of `premake5.lua`** — the two projects that use TinyUSDZ —
and the paperwork.

### `PillowFortEngine` gets the include directory, as an external one

`UsdImport.cpp` lives in the engine library and includes `<tinyusdz.hh>`, so
the engine needs TinyUSDZ's `src/` directory on its include path. In the
`PillowFortEngine` project, after its `includedirs` block:

```lua
    -- Chapter 13: only UsdImport/ includes TinyUSDZ. "External" because its headers are
    -- compiled inside our translation units, at our warning level, and are not ours to fix.
    externalincludedirs { "Vendor/TinyUSDZ/src" }
    externalwarnings "Off"
```

Why *external*: a library's headers are compiled again inside every file of
yours that includes them, under **your** warning level — `/W4` here — and
TinyUSDZ's are not written for `/W4`. Its `core/list-op.hh` alone narrows an
`int` into a `uint8_t` seven times (`bits |= flag ? bit : 0;`), and MSVC's
`/W4` reports each one as `C4244`: warnings in `UsdImport.cpp` that you can
neither fix nor stop seeing. Premake writes
`externalincludedirs` as Visual Studio's `ExternalIncludePath`
(`/external:I`) and `externalwarnings "Off"` as `/external:W0`, which keeps
`/W4` for your code and silences it for anything found through those paths
while the compiler reads them. GLFW and ImGui did not need this, because
their headers are clean at `/W4`. A warning MSVC raises later, while
generating optimized code from those headers, is not covered: Chapter 14
section 7 meets one in Release and Dist (`C4702`) and turns it off around its
includes.

### `SandboxGame` links it, and deliberately does not include it

In `SandboxGame`, the `links` line grows by one:

```lua
    -- TinyUSDZ is linked here, where the executable is made - PillowFortEngine is a
    -- static library and does not carry its dependencies. Its include directory is
    -- deliberately NOT here: SandboxGame never includes a TinyUSDZ header (Chapter 13).
    links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

The link belongs on the executable for the reason Chapter 01 section 2 gave
for `vulkan-1` (its third mistake): a static library is an archive of object
files, not a linked program, so its unresolved references to TinyUSDZ are
resolved only where an executable is made — the same reason GLFW and ImGui
are linked by `SandboxGame` although the engine is what calls them. List it
after `PillowFortEngine`: MSVC does not care about the order, but GNU linkers
resolve left to right.

The missing `includedirs` entry is the point: **the include path is how the
rule "TinyUSDZ types never leave `UsdImport/`" is enforced.** If a later
change makes `SandboxGame` fail with
`cannot open include file 'tinyusdz.hh'`, a TinyUSDZ type has leaked into a
header outside the module — and the fix is to the header, not to
`premake5.lua`. The same holds for any engine header: `UsdImport.h` in section
13 includes no TinyUSDZ header, so that anything may include it.

Then **rerun `GenerateProjects.bat`**. The solution gains `TinyUSDZ`, and
`SandboxGame` now depends on it, so a build compiles it first. Its first build
takes a few minutes even with `/MP`; after that it is rebuilt only when the pin
moves.

### `THIRD_PARTY_NOTICES.md`

ROADMAP says to update the notices whenever a redistributed dependency is
added, and the licenses say what "update" means. TinyUSDZ is Apache License
2.0, which asks two things of anyone distributing it, in source or compiled
into a program: include a copy of the license, and keep its copyright notices.
Its own `LICENSE` file is short — the copyright lines and a pointer to the
license's text — so the full text goes into the notices file.

The table gains one row:

```markdown
| TinyUSDZ | `dc7684519883358379964a9e6f925969d7477df3` (tag `v0.9.4`) | <https://github.com/lighttransport/tinyusdz> | `Vendor/TinyUSDZ/LICENSE` |
```

The paragraph under the table, which says vendor trees keep their own extra
notices, now names `Vendor/TinyUSDZ` beside `Vendor/GLFW` and `Vendor/ImGui`.
And the file gains a last section, `## TinyUSDZ license`, holding three things:

1. The two copyright lines from `Vendor/TinyUSDZ/LICENSE` —
   `Copyright (c) 2020-2023 Syoyo Fujita` and
   `Copyright (c) 2024-Present Light Transport Entertainment Inc.`
2. The table of bundled code (in this chapter's Appendix), with a sentence
   saying each of those license texts stays beside its code in
   `Vendor/TinyUSDZ`.
3. The complete text of the Apache License, Version 2.0, from
   <https://www.apache.org/licenses/LICENSE-2.0.txt>, inside a ` ```text `
   fence so Markdown keeps its indentation.

The table exists because TinyUSDZ **bundles** other people's code, and some of
it is compiled into `TinyUSDZ.lib` by the list above — so it ships in
`SandboxGame.exe` too. Which bundled files are compiled has a precise answer,
and reading the folder gets it wrong in both directions: `miniz.c` and
`tinyexr` sit in `src/external/` but are not compiled with these options, while
nlohmann/json is compiled in although the JSON option is off, because three
core files include it. So ask the compiler which files each source includes
(`/showIncludes` in MSVC, `-MM` in g++), and ask again if you change an option
in section 3. For these options the answer is sixteen libraries, large and
small; the Appendix lists them with their licenses, as the notices file takes
them.
All of these are permissive and compatible with the MIT license in
`MIT-License.txt`; none asks for more than keeping the notice.

---

## 6. Where the program's files live: `Assets/`

**This is a new top-level folder for files the program reads at run time**,
other than shaders. The test file in section 13 is the first; Chapter 14 adds
scenes and Chapter 15 textures. They need the same thing shaders got in
Chapter 06 section 1: to be found from any working directory.

Chapter 06's rule carries over unchanged — **resolve relative to the
executable, never the working directory** — and so does its mechanism: a
build step puts the files beside the executable, and code finds them through
`executableDirectory()`. Shaders needed compiling on the way; assets only need
copying. The repository gains:

```text
Assets/
  Scenes/          USD files: FirstStage.usda here, Chapter 14's test scenes later
```

and `SandboxGame` gains one build step, after its `links` line:

```lua
    -- Chapter 13: Assets/ is copied beside the executable after every build, so code
    -- finds it through executableDirectory() (Chapter 06), never the working directory.
    postbuildcommands { '{COPYDIR} "%{wks.location}/../../Assets" "%{cfg.targetdir}/Assets"' }
```

`{COPYDIR}` is premake's portable spelling of "copy a folder recursively"; for
Visual Studio it becomes `xcopy /Q /E /Y /I`. The source path is built from
`%{wks.location}` (`Build/Projects/`) the way Chapter 06's shader commands
build theirs, and the destination is the executable's own folder,
`Build/Artifacts/<Config>/SandboxGame/Assets/`. The single quotes around the
Lua string let it contain the double quotes the paths need.

Why a post-build copy rather than reading `Assets/` from the source tree: a
path into the source tree has to be found somehow — compiled in, which breaks
when the build moves, or relative to the working directory, which is the bug
Chapter 06 exists to prevent. A copy makes the build folder self-contained:
it runs from anywhere, and it is what a packaged build would ship.

Two catches, both familiar from Chapter 06:

- **Visual Studio's up-to-date check knows nothing about `Assets/`.** Edit
  only a `.usda` file and press F5, and the IDE may decide nothing needs
  building, skip the post-build step, and run with the old copy. Build from
  the command line (`MSBuild`), or touch a source file, or Rebuild.
- **Deleting a file from `Assets/` does not delete its copy.** `xcopy` adds and
  overwrites; it never removes. Deleting `Build/` — which must always be safe —
  clears it.

---

## 7. USD in one page: stages, layers, prims, paths

**This is the start of the second half — what is in a USD file.** Everything
here is USD's own model, the same in Pixar's library, in Blender, and in
TinyUSDZ; section 13 is where TinyUSDZ's names for it appear.

> **Jump:** until now every vertex, transform, and camera in this tutorial was
> created by your own code, in your own conventions. From here on, scene data
> arrives from a file written by someone else's tool, in *its* conventions —
> which axis is up, what a unit is, which way triangles wind, where texture
> coordinates start. Keep two things apart for the next two chapters: **USD's
> model** (stage, prims, attributes — this chapter) and **the engine's scene
> graph** (Chapter 12's nodes). Chapter 14 is entirely about converting the
> first into the second, and every bug it prevents comes from mixing them up.

**A layer is a file.** `.usda`, `.usdc`, and `.usdz` are three encodings of the
same thing (section 12). A layer holds a tree of prim descriptions, plus
metadata about the layer itself.

**A stage is what you get by opening a layer** — and, in full USD, by
composing it with every other layer it pulls in (section 11). The stage is the
scene as USD sees it: one tree of **prims**. In code you load a stage and walk
its prims; you rarely deal with layers directly.

**A prim is a node of that tree.** Each has a name, a type, properties, and
children. Its **path** is its position in the tree, written like a file path
from the root: `/World/Geometry/Table/Top`. Paths are how one prim refers to
another — a material binding names the material's path, for example — and the
root, `/`, is not a prim you can hold, just where the paths start. Here is the
test file of section 13 again, as a tree:

```text
/                           the stage's root
  World         Xform
    Geometry    Scope
      Table     Xform
        Top     Mesh
    MainCamera  Camera
```

A prim's children are other prims; its *properties* are its data (section 8).
Do not confuse the two: a mesh's points are a property, not a child.

**`def` declares a prim.** Hand-written and exported files are almost all
`def`. The other keyword this tutorial meets is `class`: a template other prims
copy from, never drawn itself (Chapter 19).

---

## 8. Typed schemas, attributes, relationships, and metadata

**This is what a prim's type means.** The word after `def` — `Xform`, `Mesh`,
`Camera`, `Scope` — is a **typed schema**: a named contract saying which
properties the prim has, their types, and what they mean. The four this
tutorial reads first:

| Schema | What it is | What the engine makes of it (Chapter 14) |
| --- | --- | --- |
| `Xform` | A transform and nothing else — a group that moves its children | A scene node |
| `Scope` | A group with **no** transform — pure organization | A scene node with an identity transform |
| `Mesh` | A polygon mesh: points, faces, normals, texture coordinates | A node with a mesh |
| `Camera` | A camera: focal length, film (sensor) size, clipping range | A node with a camera (Chapter 14 section 6 turns the lens into an angle) |

`Mesh` and `Camera` are *also* transformable: every geometric prim (USD calls
them *gprims*) can carry its own transform. A prim with no type (`def "Name"`)
is legal and acts like a `Scope`. A prim with a type the reader does not
know — a light, before Chapter 16 — still has a place in the tree.

A prim has one type, and may also have **API schemas** applied on top of it:
extra sets of properties, listed in its metadata as
`prepend apiSchemas = ["MaterialBindingAPI"]` (in a single file, `prepend`
changes nothing). Blender applies `MaterialBindingAPI` to every mesh with a
material, which Chapter 15 reads; Chapter 16 meets one on lights.

A prim's **properties** are of two kinds:

- **Attributes** hold values: `point3f[] points = [...]`, `float focalLength =
  35`. Each has a type — scalars, vectors (`float3`, `point3f`, `normal3f`,
  `texCoord2f`: the same three or two floats with a *role* attached), arrays of
  them (`[]`), `token` (an enumerated string), `asset` (a file path). A
  `uniform` attribute is one that cannot change over time (section 10).
- **Relationships** hold *paths* to other prims or properties:
  `rel material:binding = </World/Looks/Red>`. They are how USD links things
  without copying them — materials, light-linking, skeleton bindings.

And **metadata** is data about a prim or a layer rather than scene content:
the `( ... )` after a `def` line (`apiSchemas`, `active = false`,
`doc = "..."`), or after an attribute (`interpolation = "vertex"`), or at the
top of the file (the stage metadata of section 10). Metadata is how USD says
how to *read* the data next to it.

---

## 9. Primvars, interpolation, and transforms

**This is the part of USD that most directly becomes vertex data**, so it is
worth reading slowly.

### Primvars and their interpolation

A **primvar** ("primitive variable") is an attribute named `primvars:...` that
is meant to be interpolated across a gprim's surface — texture coordinates
(`primvars:st`), vertex colors (`primvars:displayColor`), and normals when
written as `primvars:normals`. Every primvar has an **interpolation**,
metadata saying how many values there are and what they are indexed by. For a
`Mesh` with *F* faces, *P* points, and *V* face-vertices (the length of
`faceVertexIndices`):

| Interpolation | Values | One value per | Value for a corner of face *f* at face-vertex *i* using point *p* |
| --- | --- | --- | --- |
| `constant` | 1 | the whole prim | `values[0]` |
| `uniform` | *F* | face | `values[f]` |
| `vertex` | *P* | point | `values[p]` |
| `varying` | *P* | point | `values[p]` |
| `faceVarying` | *V* | corner of a face | `values[i]` |

(`varying` differs from `vertex` only on a **subdivision surface** — a surface
smoothed by repeatedly splitting its faces, whose authored points are only a
coarse cage. Chapter 14 does not subdivide, so for it the two are the same.)

The last column is the whole algorithm Chapter 14 needs. The interesting one is
**`faceVarying`**: a value per *corner*, so two faces sharing a point can
disagree about it — the hard edge of a cube (one point, three normals), a UV
seam (one point, two texture coordinates). The GPU has no such idea: it
indexes one vertex record per index. So Chapter 14 builds one GPU vertex per
distinct combination of position, normal, and texture coordinate, which is how
a cube's 8 points become 24 vertices.

A primvar can also be **indexed**: `primvars:st` holds the distinct values,
and `primvars:st:indices` says which one each element uses. It is a
compression; `values[indices[e]]` is the value for element *e*, and after
expanding it everything above holds unchanged.

**Normals** have two spellings: the `normals` attribute of a mesh (with an
`interpolation` in its metadata, default `vertex`), and `primvars:normals`,
which wins if both exist. Texture coordinates are by convention
`primvars:st`; some exporters name the primvar after the UV map instead
(older Blender versions wrote `primvars:UVMap`), which Chapter 14 handles.

### Transforms are a list of operations

An `Xformable` prim's transform is not stored as a matrix. It is a list of
**xformOps**, each an attribute, and an `xformOpOrder` that says which to apply
and in what order:

```text
double3 xformOp:translate = (1, 0.5, 0)
float xformOp:rotateY = 30
uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateY"]
```

Op types include `translate`, `scale`, `rotateX`/`Y`/`Z`, the three-angle
`rotateXYZ` (and its five other orders), `orient` (a quaternion), and
`transform` (a whole 4x4 matrix). An op only counts if `xformOpOrder` names
it — an `xformOp:` attribute left out of the order is ignored.

**The order reads like matrix multiplication, outermost first.**
`["xformOp:translate", "xformOp:rotateY"]` means *T · R* applied to a
point: rotate first, then translate (Chapter 10 section 1: the matrix next to
the point acts first). With the numbers above, the prim turns
30° about its own centre and then moves, so its centre ends at (1, 0.5, 0).
Reverse the order, `["xformOp:rotateY", "xformOp:translate"]`, and it moves
first, to (1, 0.5, 0), and then the turn swings it 30° about the *parent's* Y
axis, to (0.87, 0.5, −0.5): the same turn, a different place. Blender writes
`["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]` — the familiar
*T · R · S*, which is also the order Chapter 10's `Transform::Matrix()` uses.
A different order is legal and can mean something a *T · R · S* cannot hold —
`["xformOp:scale", "xformOp:rotateZ"]` with an unequal scale shears (Chapter
12 section 5's picture) — which Chapter 14 has to deal with.

When TinyUSDZ turns the ops into one matrix, it writes products in the
opposite order on paper from GLM, because USD multiplies a point from the
other side. Chapter 14 section 3 shows why the sixteen numbers still copy
straight across.

A prim may also start its `xformOpOrder` with `"!resetXformStack!"`, which
means "ignore my parent's transform": its ops are its world transform. It is
rare in exported files; Chapter 14 handles it in two lines.

---

## 10. Stage metadata: up axis, units, and time

**This is the metadata at the top of a file**, between the parentheses after
`#usda 1.0`:

```text
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Y"
)
```

- **`upAxis`** is `"Y"` or `"Z"`. USD itself is happy with either; the
  content-creation tools that write it disagree — Maya and Houdini default to
  Y-up, Blender and 3ds Max to Z-up. A
  Z-up stage *is* rotated a quarter turn relative to a Y-up one, and nothing
  else in the file says so. **Not authoring `upAxis` means Y**.
- **`metersPerUnit`** is the length of one unit of the stage's numbers, in
  metres: `1` for metres, `0.01` for centimetres (Maya's and many film
  pipelines' default), `0.0254` for inches. **Not authoring it means
  centimetres** (`0.01`) in Pixar's library — a famous surprise, though
  TinyUSDZ's fallback at this pin is `1.0`. Write it explicitly in every file
  you author.
- **`defaultPrim`** names the root prim to use when another file references
  this one without naming a prim. It does not limit what is drawn.

The engine's contract (the index, "Cameras, geometry, and scenes") is +Y up and
one unit per metre, so these two numbers are what Chapter 14 converts — once,
at import.

**Time.** Any attribute that is not `uniform` can hold **time samples** — a
value per time code, written `float xformOp:rotateY.timeSamples = { 0: 0,
24: 360 }` — instead of, or as well as, a single **default** value. Asking
for an attribute's value means asking *at a time*;
there is a special time code, **`Default`**, that means "the value written
without a time".

This engine has no animation, so **everything is read at the default time**.
That is a choice with a consequence: an attribute authored *only* as time
samples has no default value, and the reader falls back to the schema's
fallback value (a camera's focal length, 50 mm) or to nothing. Blender writes
plain default values unless you export animation, so this rarely bites —
Chapter 14 says what to tick and untick.

---

## 11. Composition, and why this tutorial does none

USD's power, and most of its complexity, is **composition**: building one
stage from many files. A layer can **sublayer** others (stack them, like layers
in an image editor); a prim can **reference** a prim in another file or the
same one (bring its subtree in as if it were written here), or load it as a
**payload** (the same, but on demand); and a prim can carry **variant sets**
(named alternatives, such as "LOD high/low", of which one is selected).

**This tutorial composes nothing.** `tinyusdz::LoadUSDFromFile` reads one file
into a stage: sublayers are not stacked, a referencing prim arrives empty, and
the prims inside a variant do not appear at all. (TinyUSDZ's separate
composing path drops `PointInstancer` prims at this pin, which Chapter 19
needs.) Single-file exports, which is what Blender writes by default, need no
composition, and Chapter 14 says which Blender settings keep it that way.

---

## 12. `.usda`, `.usdc`, `.usdz`

**These are the three file formats, and TinyUSDZ reads all three through the
same call:**

| Extension | What it is | When you see it |
| --- | --- | --- |
| `.usda` | Text. Everything in this chapter's examples. | Hand-written files, debugging, diffs. Slow and large for big meshes. |
| `.usdc` | Binary ("crate"), LZ4-compressed arrays. | What tools write by default for real assets. Fast to read. |
| `.usdz` | An uncompressed zip of a `.usda`/`.usdc` and the textures it uses, read in place. | Self-contained delivery: one file, AR Quick Look on iOS. |
| `.usd` | Either `.usda` or `.usdc`; the reader looks at the first bytes. | Pipelines that switch format without renaming. |

`LoadUSDFromFile` detects the format from the content, not the name. Write
`.usda` while learning — you can read what the exporter did — and switch to
`.usdc` when files get big.

---

## 13. Loading a stage and printing it

**This is the module's first code: `LogUsdPrimTree`, called once from
`main`.** It reads a file, prints the stage metadata of section 10 and the
prim tree of section 7, and keeps nothing. That is deliberately all: it proves
the library builds, links, and reads a file from beside the executable,
before Chapter 14 builds anything on it.

### The test file

Save this as `Assets/Scenes/FirstStage.usda`. It is small, but it uses most of
sections 7-10: a `Scope` grouping without a transform, an `Xform` with two
xformOps in a non-trivial order, a `Mesh` with a `vertex`-interpolated
primvar, a `Camera`, and the three stage metadata lines.

```text
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "World"
{
    def Scope "Geometry"
    {
        def Xform "Table" (
            doc = "Turned 30 degrees about its own +Y, then moved to (1, 0.5, 0)."
        )
        {
            double3 xformOp:translate = (1, 0.5, 0)
            float xformOp:rotateY = 30
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateY"]

            def Mesh "Top"
            {
                int[] faceVertexCounts = [4]
                int[] faceVertexIndices = [0, 1, 2, 3]
                point3f[] points = [(-1, 0, 1), (1, 0, 1), (1, 0, -1), (-1, 0, -1)]
                texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
                    interpolation = "vertex"
                )
            }
        }
    }

    def Camera "MainCamera"
    {
        float focalLength = 35
        float verticalAperture = 24
        float2 clippingRange = (0.1, 100)
        double3 xformOp:translate = (0, 1.5, 6)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }
}
```

The `Table`'s ops are section 9's example: *T · R*, so the tabletop turns
about its own centre and then moves, and its centre ends at (1, 0.5, 0) — with
the order reversed it would end at (0.87, 0.5, −0.5). Chapter 14's viewer draws
this file once it imports meshes, and its inspector shows the `Table` node's
translation. The `doc` metadata is ignored by everything; it is there to show
where prim metadata goes.

### The header

**This is `Source/PillowFort/UsdImport/UsdImport.h`.** It is the module's only
public header, and it includes **no TinyUSDZ header** — the rule of section 5,
in code. A caller passes a path and gets back Chapter 02's
`InitializationResult`: a missing or unreadable file is reported, not
asserted (ROADMAP's conventions).

```cpp
// Source/PillowFort/UsdImport/UsdImport.h, inside namespace pf::usd_import.
// Deliberately includes no TinyUSDZ header, so nothing that includes this one
// needs TinyUSDZ's include directory.
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"

#include <filesystem>

namespace pf::usd_import {

// Load a .usda, .usdc, or .usdz file and log its stage metadata and prim tree,
// one line per prim. Nothing is kept.
InitializationResult LogUsdPrimTree(const std::filesystem::path& file);

} // namespace pf::usd_import
```

`LogUsdPrimTree` is a free function, and free functions are camelCase; this
one and Chapter 14's `ImportUsdFile` are the one exception the index's naming
rule makes (Reference, "Cameras, geometry, and scenes"), so that the way into
`pf::usd_import` stands out. The file-scope helpers below stay camelCase.

### The implementation

**This is `Source/PillowFort/UsdImport/UsdImport.cpp`.** Three file-scope
helpers and the public function:

```text
UsdImport.cpp
  includes
  static toUtf8(path)                 a path as UTF-8, the way TinyUSDZ takes file names
  static loadStage(file, stage)       LoadUSDFromFile, with its warnings and errors logged  (Chapter 14 reuses it)
  static logPrim(prim, depth)         one line per prim, depth first
  namespace pf::usd_import {
      LogUsdPrimTree(file)
  }
```

The includes and `toUtf8` first. TinyUSDZ takes file names as `std::string`
holding UTF-8 and widens them itself on Windows (its `io-util.cc` calls
`MultiByteToWideChar(CP_UTF8, ...)`). `std::filesystem::path::string()` would
instead convert to the system's ANSI code page, which is fine until a folder
is called `Szenen` with an umlaut somewhere — then it is a file that exists
and cannot be opened. `u8string()` is the honest conversion; in C++20 it
returns `std::u8string`, whose bytes are copied into a `std::string`.

```cpp
// Source/PillowFort/UsdImport/UsdImport.cpp
#include "PillowFort/UsdImport/UsdImport.h"

#include "PillowFort/ErrorReporting/Log.h"

#include <tinyusdz.hh>      // LoadUSDFromFile, Stage, Prim, and every schema type
#include <pprint-enum.hh>   // tinyusdz::to_string(Axis)

#include <format>
#include <string>

// File scope, above the namespace block. TinyUSDZ takes UTF-8 file names and
// widens them itself on Windows; path::string() would convert to the ANSI code
// page instead and break any path with a character outside it.
static std::string toUtf8(const std::filesystem::path& path)
{
    const std::u8string utf8 = path.u8string();
    return std::string(reinterpret_cast<const char*>(utf8.c_str()), utf8.size());
}
```

The TinyUSDZ headers are included with angle brackets and found through the
`externalincludedirs` of section 5. `tinyusdz.hh` brings in the loader, the
`Stage`, and every schema type; `pprint-enum.hh` adds the `to_string`
overloads for its enums.

**`loadStage`** wraps the one call that does the work. `LoadUSDFromFile`
reports through two strings — warnings that do not stop it, and an error when
it returns `false` — and both are worth logging: TinyUSDZ's warnings are how
you learn that it skipped something it did not understand.

```cpp
// File scope, above the namespace block. Chapter 14 calls it too.
static InitializationResult loadStage(const std::filesystem::path& file, tinyusdz::Stage& stage)
{
    std::string warning;
    std::string error;
    const bool loaded = tinyusdz::LoadUSDFromFile(toUtf8(file), &stage, &warning, &error);

    if (!warning.empty())
    {
        Log::warning(std::format("TinyUSDZ: {}", warning).c_str());
    }
    if (!loaded)
    {
        return InitializationResult::failure(
            std::format("Could not load {}: {}", toUtf8(file), error));
    }
    return InitializationResult::success();
}
```

The stage is an out-parameter rather than a return value because
`tinyusdz::Stage` is the caller's to keep for as long as it walks the prims —
in Chapter 14, for the whole import.

**`logPrim`** prints one prim and recurses into its children. Two of
`tinyusdz::Prim`'s accessors are all it needs: `element_name()`, the last
component of the prim's path, and `prim_type_name()`, the schema name written
after `def` (empty for a typeless prim). Depth-first order prints the tree in
the same order as the file.

```cpp
// File scope, above the namespace block. Depth first, so the log reads like the file.
static void logPrim(const tinyusdz::Prim& prim, int depth)
{
    Log::info(std::format("{}{} ({})", std::string(static_cast<size_t>(depth) * 2, ' '),
                          prim.element_name(), prim.prim_type_name()).c_str());

    for (const tinyusdz::Prim& child : prim.children())
    {
        logPrim(child, depth + 1);
    }
}
```

Then **`LogUsdPrimTree`** itself, inside the namespace. `stage.metas()` is the
stage metadata of section 10. Its fields are TinyUSDZ's
`TypedAttributeWithFallback`: `get_value()` returns the authored value, or the
fallback when the file says nothing — which is how a file without `upAxis`
still prints `Y`. `stage.root_prims()` are the prims directly under `/`.

```cpp
namespace pf::usd_import {

InitializationResult LogUsdPrimTree(const std::filesystem::path& file)
{
    tinyusdz::Stage stage;
    if (auto result = loadStage(file, stage); !result) { return result; }

    const tinyusdz::StageMetas& metas = stage.metas();
    Log::info(std::format("{}: upAxis {}, metersPerUnit {}, defaultPrim \"{}\"",
                          toUtf8(file.filename()),
                          tinyusdz::to_string(metas.upAxis.get_value()),
                          metas.metersPerUnit.get_value(),
                          metas.defaultPrim.str()).c_str());

    for (const tinyusdz::Prim& root : stage.root_prims())
    {
        logPrim(root, 1);
    }
    return InitializationResult::success();
}

} // namespace pf::usd_import
```

`tinyusdz::Stage` does no I/O after loading and frees everything in its
destructor, so returning early on failure leaks nothing.

### Calling it

**This is `Source/SandboxGame/Main.cpp`,** the first lines of `main`, right
after `parseSettings`. It needs two includes —
`"PillowFort/UsdImport/UsdImport.h"` and
`"PillowFort/VulkanGraphics/ExecutableFiles.h"` (for `executableDirectory`) —
and then:

```cpp
    // Chapter 13's exit check: a hand-written stage's prim tree, printed once at startup.
    // A failure is reported, not fatal - nothing else depends on it yet.
    const auto firstStage = vulkan_graphics::executableDirectory() / "Assets" / "Scenes" / "FirstStage.usda";
    if (const auto result = usd_import::LogUsdPrimTree(firstStage); !result)
    {
        Log::warning(std::format("USD: {}", result.message()).c_str());
    }
```

It runs before the window opens because it needs nothing from Vulkan; the log
appears at the top of the console. Chapter 14 replaces these lines with a demo
that imports the scene and draws it.

`main.cpp` includes `UsdImport.h`, which includes no TinyUSDZ header — so
`SandboxGame`, which has no TinyUSDZ include path (section 5), compiles. Try
the opposite once, to see the rule enforce itself: add `#include
<tinyusdz.hh>` to `Main.cpp` and the build stops with `C1083: Cannot open
include file: 'tinyusdz.hh'`. Take it out again.

Add the files, rerun `GenerateProjects.bat`, and build. The console starts
with:

```text
[INFO] FirstStage.usda: upAxis Y, metersPerUnit 1, defaultPrim "World"
[INFO]   World (Xform)
[INFO]     Geometry (Scope)
[INFO]       Table (Xform)
[INFO]         Top (Mesh)
[INFO]     MainCamera (Camera)
```

and the program then runs exactly as it did at the end of Chapter 12.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| `C1083: Cannot open source file: '...\Vendor\TinyUSDZ\src\....cc'` for every TinyUSDZ file | The submodule is not checked out: `git submodule update --init --recursive`, then regenerate |
| `C1083` for one file only | The pin moved, or the list was retyped wrong; compare with section 4 and with the pinned `CMakeLists.txt` |
| `C1128: number of sections exceeded object file format limit` | `/bigobj` missing — the `filter "toolset:msc*"` block is not reaching the TinyUSDZ project |
| An access violation in `tinyusdz::io::MMapFile` on the first file load | `WIN32` is not defined for the TinyUSDZ project (section 3) |
| About 200 `LNK4006: ... already defined in ...; second definition ignored` from TinyUSDZ | `/IGNORE:4006` missing from the project's `linkoptions` (section 4) |
| `LNK2019` for `tinyusdz::LoadUSDFromFile` | `"TinyUSDZ"` missing from `SandboxGame`'s `links`, or the solution not regenerated |
| `LNK2005` / `LNK1169` for `stbi_load` or another `stbi_` function | Something in PillowFort defines `STB_IMAGE_IMPLEMENTATION` too (section 3) |
| `LNK2038: mismatch detected for 'RuntimeLibrary'` | TinyUSDZ was built by its own CMake and linked, instead of by the premake project (section 1) |
| `cannot open include file 'tinyusdz.hh'` in a `SandboxGame` or demo file | A TinyUSDZ header was included outside `UsdImport/` — by that file or a header it includes (section 5) |
| A wall of `C4244` warnings from `list-op.hh` and other TinyUSDZ headers | The engine got the path through `includedirs` instead of `externalincludedirs` |
| `USD: Could not load ...FirstStage.usda: ...` at startup | `Assets/` not copied: the post-build step did not run (IDE up-to-date check, section 6) or the file is not at `Assets/Scenes/` |
| The log prints `upAxis Y` for a file that says `"Z"` | The file failed to parse partway; read the `TinyUSDZ:` warning line above it |

---

## Exit check

- [ ] `git submodule status` lists
      `dc7684519883358379964a9e6f925969d7477df3 Vendor/TinyUSDZ (v0.9.4)`
      with no leading `+` or `-`.
- [ ] A clean clone still builds in ROADMAP's three commands:
      `git submodule update --init --recursive`, `GenerateProjects.bat`, build.
      The solution has five projects, `TinyUSDZ.vcxproj` lists 153 source
      files, and Debug, Release, and Dist all build.
- [ ] The build output has **no warnings from TinyUSDZ** — neither from its
      own project (warnings off, and no `LNK4006` from the librarian) nor from
      its headers inside `UsdImport.cpp`
      (external, `/external:W0`) — and `UsdImport.cpp` itself is clean at
      `/W4`.
- [ ] Starting `SandboxGame` — from Visual Studio, from Explorer, and from a
      terminal in another folder — prints the six lines of section 13 first,
      then runs as it did after Chapter 12, validation-clean.
- [ ] Renaming `Assets/Scenes/FirstStage.usda` and rebuilding prints a
      `USD: Could not load` warning and the program still runs. (Delete
      `Build/Artifacts/<Config>/SandboxGame/Assets` too — the old copy stays
      otherwise, section 6.)
- [ ] Adding `#include <tinyusdz.hh>` to `Main.cpp` fails to compile, and
      removing it builds again.
- [ ] `THIRD_PARTY_NOTICES.md` has the TinyUSDZ row, the Apache 2.0 text with
      TinyUSDZ's copyright lines, and the table of bundled code.

---

## Appendix: the two lists

### TinyUSDZ's source list

Reference for section 4: the `files` block of the `TinyUSDZ` project, exactly
as `premake5.lua` holds it. It is `compile_commands.json`'s list from section 3,
in CMake's order, with `${PROJECT_SOURCE_DIR}` written as `Vendor/TinyUSDZ`.
Paste it in place of the placeholder `files` block in section 4.

```lua
    files
    {
        -- TINYUSDZ_SOURCES: parsers, writers, schemas, the Stage
        "Vendor/TinyUSDZ/src/crate-path-utils/path_sort.cc",
        "Vendor/TinyUSDZ/src/crate-path-utils/tree_encode.cc",
        "Vendor/TinyUSDZ/src/arg-parser.cc",
        "Vendor/TinyUSDZ/src/asset-resolution.cc",
        "Vendor/TinyUSDZ/src/tinyusdz.cc",
        "Vendor/TinyUSDZ/src/xform.cc",
        "Vendor/TinyUSDZ/src/performance.cc",
        "Vendor/TinyUSDZ/src/ascii-parser.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-props.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-entry.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-basetype.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-basetype-typedarray.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-timesamples.cc",
        "Vendor/TinyUSDZ/src/ascii-parser-timesamples-array.cc",
        "Vendor/TinyUSDZ/src/audio-loader.cc",
        "Vendor/TinyUSDZ/src/base122.cc",
        "Vendor/TinyUSDZ/src/usda-reader.cc",
        "Vendor/TinyUSDZ/src/usdc-reader.cc",
        "Vendor/TinyUSDZ/src/usdc-reader-property.cc",
        "Vendor/TinyUSDZ/src/usdc-reader-prim.cc",
        "Vendor/TinyUSDZ/src/usdc-reader-reconstruct.cc",
        "Vendor/TinyUSDZ/src/usda-writer.cc",
        "Vendor/TinyUSDZ/src/usdc-writer.cc",
        "Vendor/TinyUSDZ/src/composition.cc",
        "Vendor/TinyUSDZ/src/composition-reconstruct.cc",
        "Vendor/TinyUSDZ/src/composition-graph.cc",
        "Vendor/TinyUSDZ/src/core/instance-key.cc",
        "Vendor/TinyUSDZ/src/hash-util.cc",
        "Vendor/TinyUSDZ/src/chunk-reader.cc",
        "Vendor/TinyUSDZ/src/crate-reader.cc",
        "Vendor/TinyUSDZ/src/crate-reader-arrays.cc",
        "Vendor/TinyUSDZ/src/crate-reader-values.cc",
        "Vendor/TinyUSDZ/src/crate-reader-paths.cc",
        "Vendor/TinyUSDZ/src/crate-reader-timesamples.cc",
        "Vendor/TinyUSDZ/src/crate-format.cc",
        "Vendor/TinyUSDZ/src/crate-writer.cc",
        "Vendor/TinyUSDZ/src/stage-converter.cc",
        "Vendor/TinyUSDZ/src/sconv-geom.cc",
        "Vendor/TinyUSDZ/src/sconv-physics.cc",
        "Vendor/TinyUSDZ/src/sconv-ar.cc",
        "Vendor/TinyUSDZ/src/sconv-media.cc",
        "Vendor/TinyUSDZ/src/sconv-shader.cc",
        "Vendor/TinyUSDZ/src/sconv-light.cc",
        "Vendor/TinyUSDZ/src/sconv-skel.cc",
        "Vendor/TinyUSDZ/src/sconv-layer.cc",
        "Vendor/TinyUSDZ/src/crate-pprint.cc",
        "Vendor/TinyUSDZ/src/crate-dump.cc",
        "Vendor/TinyUSDZ/src/path-util.cc",
        "Vendor/TinyUSDZ/src/prim-reconstruct.cc",
        "Vendor/TinyUSDZ/src/prim-reconstruct-shader.cc",
        "Vendor/TinyUSDZ/src/prim-reconstruct-physics.cc",
        "Vendor/TinyUSDZ/src/prim-reconstruct-ar.cc",
        "Vendor/TinyUSDZ/src/prim-reconstruct-media.cc",
        "Vendor/TinyUSDZ/src/prim-composition.cc",
        "Vendor/TinyUSDZ/src/prim-types.cc",
        "Vendor/TinyUSDZ/src/core/prim-enums.cc",
        "Vendor/TinyUSDZ/src/enum-handlers.cc",
        "Vendor/TinyUSDZ/src/layer.cc",
        "Vendor/TinyUSDZ/src/primvar.cc",
        "Vendor/TinyUSDZ/src/str-util.cc",
        "Vendor/TinyUSDZ/src/usd-dump.cc",
        "Vendor/TinyUSDZ/src/value-pprint.cc",
        "Vendor/TinyUSDZ/src/value-types.cc",
        "Vendor/TinyUSDZ/src/color-space.cc",
        "Vendor/TinyUSDZ/src/usd-validation.cc",
        "Vendor/TinyUSDZ/src/tiny-format.cc",
        "Vendor/TinyUSDZ/src/tiny-string.cc",
        "Vendor/TinyUSDZ/src/io-util.cc",
        "Vendor/TinyUSDZ/src/image-loader.cc",
        "Vendor/TinyUSDZ/src/image-writer.cc",
        "Vendor/TinyUSDZ/src/image-util.cc",
        "Vendor/TinyUSDZ/src/linear-algebra.cc",
        "Vendor/TinyUSDZ/src/value-eval-util.cc",
        "Vendor/TinyUSDZ/src/usdGeom.cc",
        "Vendor/TinyUSDZ/src/usdSkel.cc",
        "Vendor/TinyUSDZ/src/usdShade.cc",
        "Vendor/TinyUSDZ/src/usdLux.cc",
        "Vendor/TinyUSDZ/src/mtlx-xml-tokenizer.cc",
        "Vendor/TinyUSDZ/src/mtlx-xml-parser.cc",
        "Vendor/TinyUSDZ/src/mtlx-dom.cc",
        "Vendor/TinyUSDZ/src/mtlx-simple-parser.cc",
        "Vendor/TinyUSDZ/src/usdMtlx.cc",
        "Vendor/TinyUSDZ/src/usdPhysics.cc",
        "Vendor/TinyUSDZ/src/mjcPhysics.cc",
        "Vendor/TinyUSDZ/src/usdObj.cc",
        "Vendor/TinyUSDZ/src/pprint-enum.cc",
        "Vendor/TinyUSDZ/src/pprint-meta.cc",
        "Vendor/TinyUSDZ/src/pprint-geom.cc",
        "Vendor/TinyUSDZ/src/pprint-shader.cc",
        "Vendor/TinyUSDZ/src/pprint-light.cc",
        "Vendor/TinyUSDZ/src/pprint-skel.cc",
        "Vendor/TinyUSDZ/src/pprint-physics.cc",
        "Vendor/TinyUSDZ/src/pprint-ar.cc",
        "Vendor/TinyUSDZ/src/pprint-media.cc",
        "Vendor/TinyUSDZ/src/pprinter.cc",
        "Vendor/TinyUSDZ/src/timesamples-pprint.cc",
        "Vendor/TinyUSDZ/src/timesamples.cc",
        "Vendor/TinyUSDZ/src/timesamples-inst-scalar.cc",
        "Vendor/TinyUSDZ/src/timesamples-inst-scalar-role.cc",
        "Vendor/TinyUSDZ/src/timesamples-inst-array.cc",
        "Vendor/TinyUSDZ/src/timesamples-inst-array-role.cc",
        "Vendor/TinyUSDZ/src/timesamples-inst-array-basic.cc",
        "Vendor/TinyUSDZ/src/stage.cc",
        "Vendor/TinyUSDZ/src/uuid-gen.cc",
        "Vendor/TinyUSDZ/src/parser-timing.cc",
        "Vendor/TinyUSDZ/src/sha256.cc",
        "Vendor/TinyUSDZ/src/typed-array.cc",
        "Vendor/TinyUSDZ/src/task-queue.cc",
        "Vendor/TinyUSDZ/src/prim-pprint-parallel.cc",

        -- TINYUSDZ_WITH_TYDRA: the scene-access helpers
        "Vendor/TinyUSDZ/src/tydra/facial.cc",
        "Vendor/TinyUSDZ/src/tydra/prim-apply.cc",
        "Vendor/TinyUSDZ/src/tydra/scene-access.cc",
        "Vendor/TinyUSDZ/src/tydra/scene-analysis.cc",
        "Vendor/TinyUSDZ/src/tydra/attribute-eval.cc",
        "Vendor/TinyUSDZ/src/tydra/attribute-eval-typed-all.cc",
        "Vendor/TinyUSDZ/src/tydra/command-and-history.cc",
        "Vendor/TinyUSDZ/src/tydra/obj-export.cc",
        "Vendor/TinyUSDZ/src/tydra/usd-export.cc",
        "Vendor/TinyUSDZ/src/tydra/shader-network.cc",
        "Vendor/TinyUSDZ/src/tydra/render-data.cc",
        "Vendor/TinyUSDZ/src/tydra/render-data-mesh.cc",
        "Vendor/TinyUSDZ/src/tydra/render-data-material.cc",
        "Vendor/TinyUSDZ/src/tydra/render-data-anim.cc",
        "Vendor/TinyUSDZ/src/tydra/render-data-pprint.cc",
        "Vendor/TinyUSDZ/src/tydra/raytracing-data.cc",
        "Vendor/TinyUSDZ/src/tydra/raytracing-scene-converter.cc",
        "Vendor/TinyUSDZ/src/tydra/material-serializer.cc",
        "Vendor/TinyUSDZ/src/tydra/materialx-to-json.cc",
        "Vendor/TinyUSDZ/src/tydra/physics-to-json.cc",
        "Vendor/TinyUSDZ/src/tydra/ar-to-json.cc",
        "Vendor/TinyUSDZ/src/tydra/ik-solver.cc",
        "Vendor/TinyUSDZ/src/tydra/rb-collision.cc",
        "Vendor/TinyUSDZ/src/tydra/rb-dynamics.cc",
        "Vendor/TinyUSDZ/src/tydra/render-scene-dump.cc",
        "Vendor/TinyUSDZ/src/tydra/bone-util.cc",
        "Vendor/TinyUSDZ/src/tydra/layer-to-renderscene.cc",
        "Vendor/TinyUSDZ/src/tydra/texture-util.cc",
        "Vendor/TinyUSDZ/src/tydra/common-utils.cc",
        "Vendor/TinyUSDZ/src/tydra/variant-support.cc",
        "Vendor/TinyUSDZ/src/tydra/variant-converter.cc",
        "Vendor/TinyUSDZ/src/tydra/variant-applier.cc",
        "Vendor/TinyUSDZ/src/tydra/mcp.cc",
        "Vendor/TinyUSDZ/src/tydra/mcp-tools.cc",
        "Vendor/TinyUSDZ/src/tydra/mcp-resources.cc",
        "Vendor/TinyUSDZ/src/tydra/mcp-server.cc",
        "Vendor/TinyUSDZ/src/tydra/diff-and-compare.cc",
        "Vendor/TinyUSDZ/src/tydra/js-script.cc",
        "Vendor/TinyUSDZ/src/tydra/threejs-exporter.cc",

        -- TINYUSDZ_DEP_SOURCES for these options: LZ4 (USDC compression), MikkTSpace
        -- (Tydra's tangents), fpng (the built-in image loader's PNG writer)
        "Vendor/TinyUSDZ/src/integerCoding.cpp",
        "Vendor/TinyUSDZ/src/lz4-compression.cc",
        "Vendor/TinyUSDZ/src/lz4/lz4.c",
        "Vendor/TinyUSDZ/src/external/mikktspace/mikktspace.c",
        "Vendor/TinyUSDZ/src/external/fpng.cpp"
    }
```

### Bundled code compiled into `TinyUSDZ.lib`

Reference for section 5: what the options of section 3 compile into the
library, found with `/showIncludes`, and the license of each. This is the
table that goes into `THIRD_PARTY_NOTICES.md`.

| Bundled code | Where | License |
| --- | --- | --- |
| LZ4 | `src/lz4/` | BSD 2-Clause (in `lz4.c`'s header) |
| MikkTSpace | `src/external/mikktspace/` | zlib-style (in `mikktspace.h`) |
| fpng | `src/external/fpng.cpp` | Unlicense (public domain), at the end of the file |
| stb_image, stb_image_write, stb_image_resize2 | `src/external/` | MIT or public domain, at the end of each file |
| `integerCoding` (from Pixar's USD) | `src/integerCoding.cpp` | Apache 2.0 with Pixar's trademark modification (in the file) |
| fast_float | `src/external/fast_float/` | Apache 2.0, MIT, or Boost (`LICENSE-*`) |
| dragonbox | `src/external/dragonbox/` | Apache 2.0 with LLVM exception, or Boost |
| optional-lite, expected-lite, span-lite (nonstd) | `src/nonstd/` | Boost Software License 1.0 |
| ghc::filesystem | `src/external/filesystem/` | MIT |
| glob | `src/external/glob/` | MIT |
| nlohmann/json | `src/external/jsonhpp/` | MIT |
| mapbox earcut, eternal | `src/external/mapbox/` | ISC |
| linalg | `src/external/linalg.h` | Unlicense |
| xxHash | `src/external/xxhash.h` | BSD 2-Clause |
| yyjson (header) | `src/external/yyjson.h` | MIT |
| atoi (jsteemann) | `src/external/jsteemann/` | Apache 2.0 |

---

Next: [14 — Importing USD Scenes](14-Importing-USD-Scenes.md)
