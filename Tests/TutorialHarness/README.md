# Tutorial harness (Linux stand-in)

Builds any worktree of this repository — or a plain copy of one, no `.git`
needed — on Linux with **g++ and clang++**, runs `SandboxGame` on **Mesa
lavapipe** under a private **Xvfb** with the **Khronos validation layer**
(synchronization validation on), takes **frame-exact screenshots**, drives
input, and fails on any validation error.

It exists because cloud sessions have no Windows machine. It is a
doc-verification tool, **not a build layer**: `premake5.lua` and
`GenerateProjects.bat` never refer to it, and it reads `premake5.lua` rather
than replacing it. The authoritative pass is still MSVC + premake/MSBuild on a
real GPU (see *What Linux cannot verify*).

## Setup (once per container)

```bash
Tests/TutorialHarness/setup_linux.sh        # idempotent; ~1 h the first time (validation layer)
source Tests/TutorialHarness/env.sh         # optional: pf.py sets its own environment
```

Builds a `VULKAN_SDK`-shaped directory at `/opt/pf-vulkan-sdk` from Khronos git
tags (sources and build trees in `~/.cache/pf-vulkan-sdk`, never in the repo):

| Piece | Version | Where |
| --- | --- | --- |
| Vulkan-Headers, Vulkan-Loader, Vulkan-Utility-Libraries, Vulkan-ValidationLayers, glslang, SPIRV-Tools, SPIRV-Headers | tag `vulkan-sdk-1.4.363.0` (newest SDK tag, 2026-09-18) | `Include/vulkan`, `Include/vk_video`, `Include/vulkan/vk_enum_string_helper.h`, `Lib/libvulkan.so`, `Lib/libVkLayer_khronos_validation.so` + `share/vulkan/explicit_layer.d/` |
| shaderc (glslc) | `v2026.4` — pins the same glslang/SPIRV-Tools commits as the SDK tag | `Bin/glslc`, `Bin/glslangValidator`, `Bin/spirv-val`, `spirv-dis`, `spirv-opt` |
| volk | tag `vulkan-sdk-1.4.363.0` | `Include/Volk/volk.h`, `volk.c` |
| GLM | `1.0.3` (latest release; the SDK's own pick cannot be checked without sdk.lunarg.com) | `Include/glm` |
| VMA | `v3.4.0` (latest release; same caveat) | `Include/vma/vk_mem_alloc.h` |

Gary's Windows SDK is 1.4.357; set `PF_SDK_TAG=vulkan-sdk-1.4.357.0` before
`setup_linux.sh` to build that instead. Individual steps: `setup_linux.sh
--help`.

## Commands

All take a directory: a worktree, or a plain copy of one with `Vendor/`
populated (for example `rsync -a --exclude .git --exclude Build
/home/user/pf-reference/ <scratchpad>/my-copy/`).

```bash
H=/home/user/PillowFort/Tests/TutorialHarness

# Build Debug with g++ and clang++ (out of tree: ~/.cache/pf-build/<dir name>-<path hash>/<config>/)
python3 $H/pf.py build <dir>                       # --config Release|Dist, --compilers gcc, --asan

# Build, then run 120 frames; screenshot after presents 60 and 119
python3 $H/pf.py run <dir> --frames 120 --shot 60 --shot 119 --out <scratchpad>/screenshots/chNN

# The same with input (see "Input scripts")
python3 $H/pf.py run <dir> --frames 130 --script $H/scripts/chapter05-08-stress.txt --out ...

# Run a throwaway copy with a literal edit (OLD must occur exactly once), e.g. a fixed clear color
python3 $H/pf.py run <dir> --variant clear02 --frames 30 --shot 29 \
    --replace Source/SandboxGame/Main.cpp "request.clearColor[0] = 0.5f + 0.5f * std::sin(elapsedSeconds);" \
              "request.clearColor[0] = request.clearColor[1] = request.clearColor[2] = 0.2f;"
                                                    # --patch file.diff works the same way

# AddressSanitizer + UBSan build and run (both compilers)
python3 $H/pf.py run <dir> --asan --frames 130 --script $H/scripts/chapter05-08-stress.txt

# Chapter 05's sync-validation positive control, on a throwaway copy
python3 $H/pf.py control <dir>

# Shader accesses through descriptors are tracked: two compute hazards injected into the program's device
python3 $H/pf.py control --compute <dir>

# Which of chapter NN's code blocks are not in <dir>
python3 $H/pf.py drift NN <dir>                     # --docs <dir>/docs/Tutorial to read another copy

# Pixel values from a screenshot
python3 $H/pf.py probe shot.png 1200,700 150,25

# The docs' section references, links, Next chain, and C1 characters (default: this repo's docs/)
python3 $H/tools/docs_check.py [<dir>/docs]

# Renumber chapters in docs and code comments on both trees (dry run; --apply writes and renames the files)
python3 $H/tools/renumber.py --map 32:33,33:34 <docs tree> <reference tree>
```

`drift`, `probe`, `tools/docs_check.py`, and `tools/renumber.py` are plain Python and also run on
Windows, which the Windows pass on `reference/tutorial-expansion` relies on;
`build`, `run`, and `control` are Linux-only.

Exit status is 0 only when everything passed. `run` prints a summary and
writes to `--out` (default `~/.cache/pf-build/<dir name>-<hash>/runs/<timestamp>/`):
`run.log` (everything the program printed), `validation.log` (the layer's own
log, with message IDs), `result.json`, and the PNGs. Throwaway copies live in
`~/.cache/pf-build/_throwaway/`; vendor objects (ImGui, GLFW) are shared
between directories in `~/.cache/pf-build/_vendor/`, keyed by content, so
several agents can build at once.

### What `build` mirrors

Read from the directory's own `premake5.lua` on every build, so a chapter that
adds a project, a define, an include directory, or a shader stage is picked up:

- every project's `files` globs (`**` crosses directories), `includedirs`,
  `defines`, `links`, `language`/`cdialect`/`cppdialect`, and filters on
  `configurations:` (`system:windows` blocks are skipped). Each project gets
  only its own include directories.
- `warnings "Extra"` → `-Wall -Wextra`, plus `-Wshadow -Wconversion
  -Wno-sign-conversion` as an approximation of the rest of `/W4` (reported in
  their own *msvc-approx* group); `warnings "Off"` → `-w`.
- the `shaderStages` table and `prebuildcommands(shaderCommands("..."))`:
  every `Shaders/**/Name.<stage>.glsl` through `/opt/pf-vulkan-sdk/Bin/glslc
  -fshader-stage=<stage> --target-env=<from premake> <flags for the config>
  -I Shaders/Include`, output mirrored under `Shaders/` beside the executable.
- `prebuildcommands`/`postbuildcommands` written with premake's portable
  tokens (`{COPYDIR}`, `{COPYFILE}`, `{MKDIR}`, `{RMDIR}`, `{DELETE}`) run
  after linking, with `%{wks.location}` = `<dir>/<workspace location>`,
  `%{cfg.targetdir}` = the executable's directory, `%{cfg.buildcfg}`,
  `%{prj.name}`. Any other command fails the build, named — a cmd.exe line
  means nothing here. Both `'...'` and `"..."` Lua strings are read;
  `filter "toolset:msc*"` and `system:windows` blocks are skipped.
- objects are reused only when the compile command and the **content** of
  every input the compiler read (its depfile) are unchanged — not by mtime,
  because throwaway copies keep the original files' older mtimes.
- a `StaticLib` that matches no sources fails the build (MSVC would report
  success, then `LNK1104`).
- **header check** (advisory, reported, never fails the build): every `.h` of
  our projects is compiled alone, as the first include of an empty file. A
  chapter that says "the header needs only X, Y" is checked by this.

Warnings are grouped: **standard** (worth reading), **msvc-approx** (likely
`/W4` hits), **platform-only** (exist only because this is Linux — e.g.
`%llu` with `uint64_t`, MSVC's `#pragma warning`), and **designated-init**
(g++'s `-Wmissing-field-initializers` on the zero-fill idiom every create-info
uses; counted, not listed — MSVC is silent).

### Linux substitutions (each one is platform, never tutorial content)

| What | Why |
| --- | --- |
| GLFW built by its own CMake for X11 | premake's GLFW project lists only the Win32 backend |
| `shims/windows.h` on our projects' include path | `IsDebuggerPresent`, `__debugbreak` (`DebugBreak.h`), `GetModuleFileNameW`/`MAX_PATH`/`DWORD` (`ExecutableFiles.cpp`) |
| `vulkan-1` links as `-lvulkan` from `/opt/pf-vulkan-sdk/Lib` (rpath) | Linux library name |
| `-D_DEBUG` in Debug | MSVC defines it for `/MDd`; `Log.h` keys off it |

If a chapter's code needs a shim for anything the chapter *teaches* — not a
Windows API — that is a finding in the chapter. Report it; do not add a shim.

### What `run` does

- starts a private `Xvfb` (default 1600x1000), forces lavapipe
  (`VK_DRIVER_FILES`), adds the SDK's layer (`VK_ADD_LAYER_PATH`), points
  `VK_LAYER_SETTINGS_PATH` at nothing (no stray `vk_layer_settings.txt` — the
  Linux analogue of a vkconfig override), and configures synchronization
  validation as below. The program's own `VK_EXT_layer_settings` request stays
  in force either way.
- **sync validation settings** (recorded in `result.json` as
  `sync_settings`, and on the summary's `sync validation:` line):

  | Setting | Value | Off switch |
  | --- | --- | --- |
  | the program's own request (tutorial: `"enables"` = sync validation) | as the program sets it | — |
  | `VK_LAYER_VALIDATE_SYNC` | `1` | `--no-force-sync` |
  | `VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC` | `1` | `--no-shader-heuristic` |
  | `syncval_full_validation`, `syncval_record_time_validation` | layer default (on) | — |
  | `syncval_load_op_after_store_op_validation` | layer default (off) | — |

  **Why the heuristic is on.** In VVL 1.4.363, sync validation does not see
  shader reads and writes made through descriptors — storage buffers, storage
  images, sampled images — unless `syncval_shader_accesses_heuristic` is true,
  and its default is false. A compute write followed by an unbarriered copy is
  silent by default (`control --compute` proves both halves). Atomics stay
  untracked even with it on. The layer warns the heuristic can produce false
  positives, so when a run fails on validation with it on, `run` repeats the
  run with it off (into `<out>/heuristic-off/`) and lists every error that
  appears **only** with the heuristic as `heuristic-only:` — the run still
  FAILS. Treat those as leads to investigate, not noise: in the 01-08
  reference, removing the composite pass's barrier on the scene target is
  caught *only* with the heuristic on.
- launches `SandboxGame --frames N` from a working directory that is **not**
  the executable's, so shader loading proves it is executable-relative.
- preloads `tools/pf_framehook.c`, which pauses the program after the chosen
  presents so screenshots and input land on exact frames. It only waits; it
  never calls Vulkan, so it cannot add synchronization that hides a hazard.
- also has the layer write its own log (`VK_LAYER_DEBUG_ACTION=LOG_MSG`,
  `VK_LAYER_LOG_FILENAME=<out>/validation.log`). That log carries the message
  IDs (`VUID-...`, `SYNC-HAZARD-...`); the tutorial's callback prints only
  `pMessage`, which with this layer version does not include them.
- **FAILS** on any `Validation Error` in `validation.log`, any `[ERROR]` line
  the program printed, a non-zero exit, a crash, a sanitizer report, a hang
  (`--timeout`, default 300 s), a failed screenshot, or a script frame that
  never happened. `--allow
  REGEX` tolerates a message you have documented; `--expect REGEX` makes a run
  pass only if the pattern appears (positive controls). The one expected
  warning — chapter 02's deliberate use of the deprecated `"enables"` setting —
  is recognized and labelled.

### Input scripts

One `<present number> <command>` per line, `#` comments:

| Command | Effect |
| --- | --- |
| `shot [name]` | PNG of the window (`name.png`, default `frameNNNNN.png`) |
| `resize W H` | resize the window (swapchain recreation) |
| `click X Y [button]` / `down X Y` / `move X Y` / `up X Y` | mouse, window-relative pixels; drag = `down`, `move`, `up` on later frames |
| `key <keysym>...` / `type <text>` | keyboard (to the window under the pointer) |
| `close` | WM_DELETE_WINDOW, the polite close (`tools/pf_xclose.c`) |
| `xdotool <args>` | anything else; `{win}` is the window id |
| `sleep S` | wait while the program is paused |

Events queue in X while the program is paused and are seen at its next
`glfwPollEvents`. `scripts/chapter05-08-stress.txt` is a worked example.

`--asan` builds with `-fsanitize=address,undefined` (leak detection off: the
loader and driver keep allocations until exit).

### Positive control

`pf.py control <dir>` copies the directory (Vendor symlinked), applies chapter
05's exit-check edit — the end-of-frame (`PRESENT_SRC_KHR`) barrier's source
access `VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT` → `VK_ACCESS_2_NONE` in
`VulkanRenderer.cpp` — builds it, and runs 3 frames twice: once with only the
program's own layer settings, once with `VK_LAYER_VALIDATE_SYNC=1`. Both must
report the write-after-write hazard. `--patch file.diff` (applied with `patch
-p1`) and `--expect REGEX` run any other control the same way. The original
directory is never modified.

`pf.py control --compute <dir>` proves that shader accesses through
descriptors are tracked. It needs no compute code in the program: an
`LD_PRELOAD` library (`tools/pf_syncval_compute.cpp`, shaders
`tools/pf_syncval_*.comp.glsl`) hooks the program's `vkCreateDevice` and, on
that device, records and submits two read-after-write hazards with no
barriers — a dispatch writes a storage buffer and `vkCmdCopyBuffer` reads it;
a dispatch writes a storage buffer and a second dispatch reads it through a
descriptor. Validation is configured exactly as the program configures it
plus the harness environment. Both hazards must be reported with the
heuristic on; the second run, with the layer default, shows both going
unreported. Built as a standalone program instead (no `PF_INTERPOSE`) it tests
the layer alone: `pf_syncval_compute writer.spv reader.spv`.

### Drift check

`pf.py drift NN <dir>` finds chapter NN's fenced code blocks by their first
line and, for each, the file in `<dir>` that contains most of its lines
(whitespace-normalized; comment-only lines and braces ignored). `FULL` blocks
are hidden unless `--all`; `PARTIAL` and `ABSENT` list the missing lines.
Illustrative fragments (`...` placeholders, alternatives the text rejects,
code a later chapter replaces) are expected to show up — read each one rather
than treating the count as a score.

## What Linux cannot verify

The Windows pass on Gary's machine must still cover:

- **MSVC itself**: `/W4 /permissive-` diagnostics (g++/clang warnings are a
  proxy), MSVC-only constructs (`#pragma warning(push, 0)` around VMA), and
  the real premake → `.vcxproj` → MSBuild path, including the prebuild glslc
  step, `debugargs`, and regeneration after adding files.
- **Win32**: `windows.h`, `IsDebuggerPresent`/`__debugbreak` behaviour under the
  VS debugger, `GetModuleFileNameW`, the modal resize loop that freezes
  `glfwPollEvents` while dragging, minimize/restore from the taskbar, DPI
  scaling and moving between monitors, alt-tab surface loss.
- **Real drivers**: lavapipe is conformant but forgiving in places hardware is
  not (memory types — it has one heap; image layouts and compression; timing).
  Present-mode lists differ (lavapipe on X11 offers IMMEDIATE, MAILBOX, FIFO,
  FIFO_RELAXED); the 890M has no MAILBOX. Performance numbers mean nothing here.
- **The vkconfig override** on Gary's machine (`validate_sync = false`) — only
  the Windows run shows whether the program's `"enables"` request survives it.
  The same question applies to `syncval_shader_accesses_heuristic`: an
  override that sets it (or `validate_sync`) outranks the program's request,
  so a chapter that turns the heuristic on in its layer settings must be
  checked with a positive control on Windows too, not only here, where the
  harness forces it on through the environment.
- **sRGB/present path**: the X11 swapchain here is composited by nothing;
  Windows' DWM, HDR displays, and vendor format lists are not exercised.
- **Pixel values** are from lavapipe's rasterizer and the X server; they match
  the encode math, but rounding at the last bit may differ from a GPU readback.
