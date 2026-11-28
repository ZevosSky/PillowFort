# Settings as Rows, and What a Shader Declares

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Goal:** make each of the grass's 32 wind settings, and every particle setting but the preset's index, one row of
a table, and let the code that named each setting in several places walk the rows instead: the panel draws them,
packing walks them, and applying a preset walks them for what it keeps. At every step, prove that the program does
what it did before the lesson. Part 1, sections 1 to 6, starts by deleting one packing line on purpose and asking
what notices; builds what a test needs; then builds the rows, the grass's in sections 3 and 4 and the particles' in
sections 5 and 6, and says where they stop. Part 2, section 7, reads one compiled shader module, the other side of
the bytes you pack.

**Form:** typed into your tree from its own text, over the assembled reference; one supplied CPU test, and beside
it a header you fill by copying your own code. The tree holds Chapter 57 complete, and the page prints every line
it changes.

**GPU idea:** A uniform or push block is bytes at offsets the compiler fixed; the GPU reads whatever the host left
there, and nothing checks that each field was written. The compiled module states the shader's side of that
contract (its sets, bindings, kinds, block offsets and push-constant range) in decorations and types you can read.
Part 1 works on the host's side: each setting is written once, as a row, and packing walks the rows. Part 2 reads
the shader's side in one module, Chapter 57's `end` pass, with `spirv-dis`.

Reused, not new: Chapter 53's table of wind settings, with its member pointers and stringized names, the functions
that walk it for `--grass-response` and **Log values**, and its contract test, whose file does not change; Chapter
9, section 6's guarded widgets, which a panel drawn from rows still calls; Chapter 8, section 8's one layout in two
languages; Chapter 54's presets; and Chapter 57's `end` pass, the module Part 2 reads.

**Read after:** [Chapter 57](57-The-Frame-Declared.md), with its exit check passed, in the assembled reference.
Like 57, this page is a detour from the renderer route: when you finish, go back to
[Chapter 22](22-Deferred-Shading.md). The index and the other chapters call it the reflection lesson. [Chapter 56](56-Everything-Bends.md),
Everything Bends, is read after it, and it retires the copy section 2 makes.

**ROADMAP:** step 21+ — the `Grass` and `Particles` demos' settings become rows.

**Module:** `pf::debug_panels` gains `SettingRows.h` and one template in `DemoPanel.h`. No class gains a member:
the two demos gain free functions and their tables, in their own namespaces.

**Math:** none.

**Prerequisites:**

- [Chapter 53, section 2](53-Rolling-Wind.md#2-a-steady-wind-and-a-blade-that-stays-whole), its
  [six places for a setting](53-Rolling-Wind.md#six-places-for-a-setting-typed-once), and
  [the 32 wind-response settings](53-Rolling-Wind.md#the-32-wind-response-settings): the six places, the table, the
  `AlwaysClamp` flag and the **Log values** line.
- [Chapter 9, section 6](09-Demo-Harness.md#6-the-triangle-becomes-a-demo) and its
  [guarded float slider](09-Demo-Harness.md#a-guarded-float-slider): the guarded widgets every panel goes through.
- [Chapter 21, section 5](21-GPU-Particles.md#5-drawing-the-particles) and
  [section 7](21-GPU-Particles.md#7-the-panel-and-the-numbers-that-come-back): `ParticleAppearance`'s push, and the
  panel.
- [Chapter 52, section 3](52-Wind-Fields-And-Vorticles.md#3-velocity-is-not-acceleration): the local wind's
  settings.
- [Chapter 54, section 2](54-Shaping-A-Particle-Effect.md#2-births-on-a-shape),
  [section 3](54-Shaping-A-Particle-Effect.md#3-a-clock-for-the-effect),
  [section 4](54-Shaping-A-Particle-Effect.md#4-starting-full) and
  [section 5](54-Shaping-A-Particle-Effect.md#5-curves-baked-into-an-image): presets, the clock and its bursts,
  prewarm, curves.
- [Chapter 55, section 1](55-Sorted-Smoke.md#1-glow-then-cover),
  [section 3](55-Sorted-Smoke.md#3-the-sort-on-the-gpu) and
  [section 5](55-Sorted-Smoke.md#5-a-flipbook-baked-in-compute): cover, the sort, the flipbook.
- [Chapter 57, section 7](57-The-Frame-Declared.md#7-particles-declared-and-the-first-rule-breaks): `end`'s
  declared uses, for Part 2.
- [Chapter 8, section 5](08-Resources-And-Descriptors.md#5-push-constants-the-imgui-slider-path),
  [section 6](08-Resources-And-Descriptors.md#6-descriptor-sets) and
  [section 8](08-Resources-And-Descriptors.md#8-one-layout-two-languages): push constants, descriptor sets, and one
  layout in two languages.
- [Chapter 6, section 1](06-Shaders-And-Pipelines.md#1-the-shader-build) and
  [section 8](06-Shaders-And-Pipelines.md#8-when-the-second-pipeline-arrives): glslc's flags, and layouts by hand,
  where "generating them from SPIR-V reflection is the automation to consider after the third".
- [Chapter 1, section 1](01-Environment-And-Build.md#1-what-is-actually-in-your-sdk): the SDK's `spirv-dis`.
- [Chapter 45, section 2](45-Scene-Documents-And-Properties.md#2-bind-a-name-to-a-real-member) and
  [section 4](45-Scene-Documents-And-Properties.md#4-generate-controls-from-the-described-values): only if you read
  it; section 6 compares the two.

## Where the code goes

| File | What sections 2 to 6 do there |
| --- | --- |
| **New:** `Tests/TutorialHarness/SettingsByHand.h` (yours alone: [Chapter 56](56-Everything-Bends.md) deletes it) | Section 2: the copy, filled by copying your own code before anything moves |
| `premake5.lua`, `Tests/TutorialHarness/SettingRowsTests.cpp` | Section 2: the test's project, and the test, supplied at stage 0. Sections 3, 5 and 6: its `PF_TEST_STAGE` line raised to 1, 2 and 3 |
| `Source/PillowFort/Demos/Grass/GrassDemo.h`, `Source/PillowFort/Demos/Grass/GrassDemo.cpp` | Section 2: the body of the **Wind response** header moved into `drawWindResponse`, a function a test can call. Section 4: the panel from the rows |
| `Source/PillowFort/Demos/Particles/ParticlesDemo.h`, `Source/PillowFort/Demos/Particles/ParticlesDemo.cpp` | Section 2: the panel's settings and the three packings moved into functions a test can call, with two small structs and three constants in the header. Section 5: the particles' rows, and the packing and the panel from them. Section 6: applying a preset by the rows |
| **New:** `Source/PillowFort/DebugPanels/SettingRows.h` | Section 3: the row, its checks, and packing from the rows. Section 5: the row grows for the particles. Section 6: keeping a row's value |
| `Source/PillowFort/Demos/Grass/GrassField.h`, `Source/PillowFort/Demos/Grass/GrassField.cpp` | Section 3: one row per wind setting, and packing from the rows |
| `Source/PillowFort/DebugPanels/DemoPanel.h` | Section 4: `drawSettingRows`, the one template. Section 5: it draws the particles' rows too |
| `Tests/TutorialHarness/Checkpoints/Manifest.psd1` | Section 4: `SettingRows.h` joins a checkpoint's list of files, because `DemoPanel.h` now includes it |

The supplied test builds only when the solution is generated with `GenerateProjects.bat --tutorial-tests`, the
option [`docs/Premake.md`](../Premake.md) describes. Sections 2 and 3 add files, so each runs it again: premake
bakes its file lists in when it generates, and a plain regeneration drops the test projects. Sections 4 to 6 add
none, and Part 2 changes no file in your tree.

The supplied test, which section 2 copies in, keeps its own lists of the settings it checks, and those lists answer
the attempts of sections 3 and 5. Read it, if you want to, after them.

**Moves.** Code that moves without changing is not printed again: you cut it and paste it. Every move is written in
one form, so that it can be done from the words alone:

> **Move.** In `File`, cut the N lines from the line `FIRST` through the line `LAST`, inclusive; the line after
> them is `NEXT`. Paste them, dedented by K spaces, *(place)*. In their place type: *(the lines printed under the
> move)*

- `FIRST` occurs once in the file, and `LAST` followed by `NEXT` occurs once; where it would not, the words name
  the lines after `NEXT` too, until the run is unique. When the line after them is blank, the form names the one
  after it too: "the line after them is blank, and the next is `...`". A line that holds a backtick is quoted by
  how it starts: "the line that starts `...`".
- N counts every line cut, blank lines included. Count before you cut: if the N-th line, counting `FIRST` as the
  first, is not `LAST`, stop, and compare your code with the chapter that printed it.
- Dedented by K spaces: take K spaces off the front of every pasted line; a blank line stays blank. "Unchanged"
  means K is 0.
- The place is one of three: directly under the line `ANCHOR` in another file, where `ANCHOR` occurs once; between
  the braces of the function printed above, an empty function the page has just had you type; or directly under the
  line `ANCHOR` of the function printed above.
- In their place you type the lines printed under the move, or nothing, where it says "In their place type
  nothing."
- A **copy** is the same form with "copy" for "cut", and nothing typed in their place: section 2 fills
  `SettingsByHand.h` this way.
- An edit inside the pasted lines, such as `static` becoming `inline`, is named after the paste, with the line it
  applies to.

**Blank lines.** A new function, struct member block or file-scope block you add gets one blank line above it and
one below it, as its neighbours have, except as the last thing in a class or struct, where it sits directly against
the closing `};`. Constants or comment lines that join a run of constants are the exception: they sit directly
against their neighbours, and the text says "with no blank line between" where that is so. Pasted lines bring the
blank lines they had and no others: they sit directly under their anchor, and what followed the anchor follows
them. In `SettingsByHand.h`, each block of the copy, its comment and what you paste under it, is a file-scope
block: one blank line between blocks, and one between the last block and `} // namespace by_hand`.

# Part 1 — Settings as rows (sections 1–6)

Chapter 53 wrote each of its 32 wind settings in six places, and the `Particles` demo writes each of its settings
in a struct, in a widget and, for most of them, in a line that packs it, with a line of its own in `applyPreset`
for each one a preset leaves alone. This part gives each setting one row, a description that the panel, the packing
and the presets all read.

## 1. A line nothing missed

This section types nothing. It deletes one line, runs a test, and puts the line back.

`PackParameters`, in `GrassField.cpp`, packs Chapter 53's 32 wind settings into `GrassParameters` with one
designated-initialiser line each. Here is one of them, `gustJitter`'s, as a mistake to try and put back: delete it
from `PackParameters`.

```cpp
        .gustJitter      = clampTo(settings.gustJitter, GUST_JITTER_RANGE),
```

**Predict, then run.** Your tree holds Chapter 53's contract test, `TutorialGrassWindTests`: 38 checks and a
summary line. Build it with the line gone. Will the build warn? Will any of the 38 checks fail? Which check is
nearest to the line, and why does it not see it? Write your answers down, then build and run from the repository
root:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialGrassWindTests
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialGrassWindTests\TutorialGrassWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialGrassWindTests failed.' }
```

The build has 0 warnings, and the test passes: all 38 checks and its summary line, exit 0. Its last line is the one
it prints when nothing failed:

```text
PASS: grass wind contract: the name table, the hash, dragBend, the spring, the fronts, the soft stop and the guards.
```

Nothing in your tree saw it. The slider still moves `gustJitter`, and **Log values** still prints it, but
`PackParameters` no longer writes it into the block the GPU reads. A designated initialiser may leave a field out,
and the compiler says nothing when it does. What the GPU then read in that field was not measured; no test here
looks at it.

**The nearest check.** Six of the 38 checks touch `gustJitter`, and all six work on `GrassSettings`, before the
line: the pinned **Log values** line prints it; four checks write it through the `--grass-response` lookup, and one
of them, `a value past the range is clamped to it and reported`, sets 5 and finds 0.45, the top of the very range
your deleted line clamped to; and the bounds check holds it to `GUST_JITTER_RANGE`. The checks that do read a
packed block, the continuity sweeps and the second half of the guards, get it from `defaultParameters()`, which
calls `PackParameters` on the default settings, and then compare it with a model of the shader's answer that is
built from that same block. Whatever `gustJitter` the block holds, the model holds too.

**Where else the setting is written.** Leave the line out for now; the attempt below is easier to check with it
missing. Search your tree for `gustJitter` in `Source/` and `Shaders/`, with your editor or with
`git grep -n gustJitter -- Source Shaders` from the repository root. You find five lines: four of Chapter 53's six
places and its one reader. The other two places are the range, which is named `GUST_JITTER_RANGE` and so is not
found, and the pack line you deleted:

| Place | File | What it holds |
| --- | --- | --- |
| a field of `GrassParameters` | `Shaders/Grass/GrassTypes.h` | the block's float, declared once for C++ and GLSL |
| a member of `GrassSettings` | `GrassField.h` | the CPU's value, 0.45 by default |
| a `WindRange` | `GrassField.h` | `GUST_JITTER_RANGE`, 0 to 0.45, for the slider and the clamp |
| a row of `WIND_RESPONSE_SETTINGS` | `GrassField.h` | the name, the member, the range and two decimals, for `--grass-response` and **Log values** |
| a line of `PackParameters` | `GrassField.cpp` | the line you deleted |
| a `windSlider` | `GrassDemo.cpp` | **Gust jitter (spacings)**, in the Gusts node |
| the reader | `Shaders/Grass/GrassGenerateKernel.glsl` | `grass.gustJitter`, handed to `frontResponse` |

Leave out the field, the member or the range and the build stops; leave out the slider and the panel shows it. A
pack line left out is missing from nothing you look at: the slider, the table, the lookup and the log line all work
on `GrassSettings`, before the line; the shader reads the block, after it; and the line is the only thing between
them.

**Two that are not like the others.** Read the 32 lines and the six tree nodes once more: one pack line is not a
plain clamp of one setting to its own range, and one slider is not a plain slider. Whatever replaces them has to
keep both; section 3's attempt asks how.

<a id="ch57-missed-line"></a>

### Attempt CH57-missed-line: a test, or a structure?

Predict first. Chapter 53's test packed the defaults through `PackParameters` and still passed: what does a test of
packing need that it lacked? The only code that packs the block is the code under test, so what can a test compare
the block with? Would the default settings alone be enough? And if you add a 33rd wind setting tomorrow and forget
its pack line, would your test notice?

Design a test, with only what your tree has now, that would have failed on the deleted line. Say what it compares,
against what, and over which values. You need not build it: section 2 builds one like it.

**Acceptance:** trace your test by hand on both packings, the one with the line and the one without. For one case,
write the value it sets for `gustJitter`, the field it reads from each side, and what it finds in each. It must
pass on the first packing and fail on the second, with a message that names the setting. Then name one mistake your
test cannot see, and say why it cannot.

**Transfer:** the particles. `RecordStep` packs `ParticleSimulation` with the same kind of designated initialiser,
and some of its floats are copied from `ParticleSettings` unchanged. Delete one of those lines in your head. Which
of your tests looks at that field, and at which settings? What must change in the code before your test can even
call that packing?

<details>
<summary>Hint 1: what a test can call</summary>

`PackParameters` is a `const` member of `GrassField`, and it needs no device: Chapter 53's test calls it on a
default `GrassField` in `defaultParameters()`. So a test can fill a `GrassSettings`, call it, and read every field
of the block it returns. The question is what to read the block against.

</details>

<details>
<summary>Hint 2: an answer that is not the code under test</summary>

Chapter 53's checks miss the line because their model is built from the block itself. You need a second answer that
does not come from `PackParameters`. Your tree has one: the 32 lines as they were before you deleted one. Kept in a
function of their own and left alone, they say what the packing did.

</details>

<details>
<summary>Hint 3: values that move every setting</summary>

One case can pass by luck, when what the engine leaves in a field it does not write happens to equal what you set.
Move each setting on its own to the ends of its range and past them, then many at once, and compare all 32 fields
in every case, bit for bit: a NaN never equals itself, and -0 equals 0.

</details>

<details>
<summary>Worked solution: a frozen copy, compared field by field</summary>

**What it compares.** The block `PackParameters` returns, against the block that a frozen copy of your 32 packing
lines returns from the same settings. The copy is the lines from `GrassField.cpp`, copied before any change into a
function, `packWindResponse(settings)`, that fills an otherwise empty `GrassParameters`. It calls the same
`clampTo` with the same Chapter 53 range constants, so it names your ranges instead of repeating their numbers.

**Which fields.** The 32 wind-response fields, each read through a `float GrassParameters::*` from a list in the
test and compared by its bits, with the setting's name, the case and both values in the message.

**Which values.** The defaults; each of the 32 settings on its own at the bottom and the top of its range, one
below and one above, `1e30`, `-1e30`, NaN and -0; all 32 at their minimum, and all at their maximum; random
settings; and a few pairs of `gustLengthMin` and `gustLengthMax`, since Chapter 53's expression reads both. Section
2 builds exactly this, as the copy and as stage 0's first comparison, which runs 284 cases.

**The trace.** Take the case that sets `gustJitter` to 0.45, the top of `GUST_JITTER_RANGE`. With the line, both
blocks' `gustJitter` hold 0.45, and the case passes. Without it, the copy's holds 0.45 and the engine's block holds
0 there, because C++ zeroes a member the designated initializer does not name and `GrassParameters` gives it no
default; the case fails, naming `gustJitter`.

**What it cannot see.**

- The same slip in both: if you made the copy after the slip, or make the same mistake in each, they agree.
- A clamp to another constant of the same value. `RIPPLE_JITTER_RANGE` is 0 to 0.45 too, so
  `.gustJitter = clampTo(settings.gustJitter, RIPPLE_JITTER_RANGE)` packs the same bits in every case, until one of
  the two ranges changes.
- A shader that reads the wrong field, or none: the test reads the block, not the shader.
- The next setting. The test knows the 32 it lists, so a 33rd setting whose pack line you forget is in neither the
  copy nor the list.

**The transfer.** Of your tests, `TutorialMirrorBatchTests` compares `Record`'s simulation push with Chapter 21's,
at the defaults only. And there is nothing to call. The initialiser is written inside `RecordStep`, a member that
records into a command buffer, reads `m_settings` and the step's own values, and pushes the result. Before a test
can call that packing with settings of its own, it has to become a function of the settings and the step, which is
section 2's first job. The comparison then works on any block, converted fields included, because it compares what
packing returns, not how each line is written: a `vec4` is compared as four floats, and the integers as integers.

</details>

Section 3's attempt takes up the other half of this attempt's question: what shape makes the line impossible to
forget?

### Checkpoint

Put the line back where you deleted it, between the `.gustSpacing` and `.gustCrestLength` lines of
`PackParameters`; your editor's undo is enough. Build and run the lines above again. The build has 0 warnings, and
`TutorialGrassWindTests` ends with the same `PASS: grass wind contract` line. It passed with the line missing too,
which is what this section came to show. Your tree is as Chapter 57 left it.

## 2. Before you change anything, keep what your code does

Sections 3 to 6 replace code you typed in Chapters 21, 52, 53, 54 and 55, and each replacement must leave the
program doing exactly what it did. This section sets up the proof first: **the copy** of your code, **the seams** a
test can call, and **the supplied test** comparing them at stage 0. On screen, nothing changes.

> **Jump: a seam, and why a test needs a free function.** A test compares two answers to one question, so it must
> ask the question itself, with settings it chose. The demos give it nothing to ask: the `Particles` panel is drawn
> inside `Update`, and its packing is written inside `RecordStep` and `RecordParticles`, members of a demo whose
> `Setup` made a device's buffers and pipelines; the grass's wind sliders are drawn inside the static
> `drawGrassPanel`. The supplied test has no window and no device. A *seam* is a place where code can be called
> from outside without changing what it does: here, a free function that takes the settings and returns the block,
> or draws the widgets into whatever ImGui window is current. The demo calls it where the code was; the test calls
> it with settings of its own.

Two things need no seam: `GrassField::PackParameters`, a `const` member that Chapter 53's test already calls on a
`GrassField` with no device, and `ParticlesDemo::SetPreset`, which is public and touches nothing on the GPU, so the
test makes a `ParticlesDemo` and calls it.

### The copy

**The copy** is your code as it is now, kept compiled beside the supplied test so that every later stage is
compared with what your program did before the lesson; the first later chapter to change these settings retires it
whole, so keep yours until then.

Copy, do not retype: the copy must hold what you typed, slips and all, or it vouches for this page instead of for
your code. Each block starts with a comment you type, recording where its lines come from, their first and last
lines, the chapter that last printed them, and the copy's edit. Six blocks are whole functions; seven put your
lines into an empty function, so that the test can call `by_hand::packSimulation` and `packSimulation` with the
same arguments. Do all thirteen before the seams, which cut the same lines out of the demos. The copy names
`ParticleStep` and `ParticleFragmentWords`, which the seams add, so nothing builds it before the checkpoint.

> **Jump: `inline` in a header.** A function defined in a header is defined again in every file that includes it.
> `inline` is C++'s word for that: every copy is the same definition, and the linker keeps one. `static`, which the
> whole functions had in their `.cpp` files, gives each including file a private copy instead, and MSVC at `/W4`
> warns, C4505, about a `static` function a file defines and never calls. Only the supplied test includes this
> header, so either would link; `inline` says what the functions are.

Create `Tests/TutorialHarness/SettingsByHand.h` with this text. Each block below goes into it directly above its
last line:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Your settings as you wrote them by hand, before the rows: the settings lesson's oracle
/// @copyright (C) Gary 2026
///========================================================
#pragma once

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/Demos/Grass/GrassDemo.h"
#include "PillowFort/Demos/Grass/GrassField.h"
#include "PillowFort/Demos/Particles/ParticlesDemo.h"
#include "Particles/EmitterShapes.h"   // the packing below names EMITTER_SHAPE_*, which ParticlesDemo.h does not include

#include <imgui.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iterator>
#include <string>

// The engine's code at the start of the settings lesson, copied from the base tree before anything moved. The supplied
// test compares what the rows do with what these do, so a row that drifts from the hand-written line it replaces is a
// failure.
namespace by_hand {

using namespace pf::demos::grass;
using namespace pf::demos::particles;

} // namespace by_hand
```

**1. `clampTo`, from `GrassField.cpp`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Grass/GrassField.cpp.
//   first line: // File scope, above PackParameters: the setting held inside its slider's range.
//   last line:  }
//   last printed: Chapter 53, section 2 ("A steady wind, and a blade that stays whole", "Six places for a
//                 setting, typed once"); `static` became `inline`.
```

**Copy.** In `GrassField.cpp`, copy the 5 lines from the line
`// File scope, above PackParameters: the setting held inside its slider's range.` through the line `}`, inclusive;
the line after them is blank, and the next is
`static const WindResponseSetting* findWindResponseSetting(std::string_view name)`. Paste them, unchanged, directly
under the line that starts `//                 setting, typed once");` in `SettingsByHand.h`. In the pasted line
`static float clampTo(float value, WindRange range)`, `static` becomes `inline`.

**2. `packWindResponse`, your 32 packing lines.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Grass/GrassField.cpp (inside GrassField::PackParameters's initializer,
//             after "// Chapter 53: the wind response").
//   first line: // Gusts
//   last line:  .farHighlight    = clampTo(settings.farHighlight, FAR_HIGHLIGHT_RANGE),
//   last printed: Chapter 53: Lean and Blades in section 2, Gusts and Spring in section 4, Ripples in section
//                 5, Wind shading in section 6.
inline GrassParameters packWindResponse(const GrassSettings& settings)
{
    return GrassParameters{
    };
}
```

**Copy.** In `GrassField.cpp`, copy the 38 lines from the line `        // Gusts` through the line
`        .farHighlight    = clampTo(settings.farHighlight, FAR_HIGHLIGHT_RANGE),`, inclusive; the line after them
is `    };`. Paste them, unchanged, directly under the line `    return GrassParameters{` of the function printed
above.

**3. `windSlider`, from `GrassDemo.cpp`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Grass/GrassDemo.cpp.
//   first line: // One wind-response slider: its range is the one PackParameters clamps to, and a typed value
//               stays inside it.
//   last line:  }
//   last printed: Chapter 53, section 2 ("Six places for a setting, typed once"); `static` became `inline`.
```

**Copy.** In `GrassDemo.cpp`, copy the 5 lines from the line
`// One wind-response slider: its range is the one PackParameters clamps to, and a typed value stays inside it.`
through the line `}`, inclusive; the line after them is blank, and the next is
`// The demo's panel (Chapter 25 section 2, grown in Chapters 26 and 27), below "Camera".`. Paste them, unchanged,
directly under the line that starts
`//   last printed: Chapter 53, section 2 ("Six places for a setting, typed once");` in `SettingsByHand.h`. In the
pasted line `static void windSlider(const char* label, float* value, WindRange range, const char* format)`,
`static` becomes `inline`.

**4. `drawWindResponse`, the six tree nodes.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Grass/GrassDemo.cpp (drawGrassPanel's six tree nodes, lines 165-232).
//   first line: if (ImGui::TreeNode("Gusts"))
//   last line:  }  (the Wind shading node's closing brace)
//   last printed: Chapter 53, section 6 (the Wind shading node; its other five nodes in sections 2 to 5).
inline void drawWindResponse(GrassSettings& settings)
{
}
```

**Copy.** In `GrassDemo.cpp`, copy the 68 lines from the line `            if (ImGui::TreeNode("Gusts"))` through
the line `            }`, inclusive; the line after them is blank, and the next is
`            if (ImGui::Button("Log values"))`. Paste them, dedented by 8 spaces, between the braces of the
function printed above.

**5. `srgbToLinear`, from `ParticlesDemo.cpp`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp.
//   first line: // File scope, above the namespace block. Section 5: the swatches are sRGB, the
//   last line:  }
//   last printed: Chapter 21, section 5 ("Drawing the particles"); `static` became `inline`.
```

**Copy.** In `ParticlesDemo.cpp`, copy the 6 lines from the line
`// File scope, above the namespace block. Section 5: the swatches are sRGB, the` through the line `}`, inclusive;
the line after them is blank, and the next is
`// File scope, above the namespace block. Section 8: the fewest valid timestamp bits of any`. Paste them,
unchanged, directly under the line that starts
`//   last printed: Chapter 21, section 5 ("Drawing the particles");` in `SettingsByHand.h`. In the pasted line
`static float srgbToLinear(float value)`, `static` becomes `inline`.

**6. `keepInRange`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp.
//   first line: // File scope. For what a clamped, guarded slider cannot hold: a range that moves, past which
//               the
//   last line:  }
//   last printed: Chapter 54, section 3 ("A clock for the effect"); `static` became `inline`.
```

**Copy.** In `ParticlesDemo.cpp`, copy the 7 lines from the line
`// File scope. For what a clamped, guarded slider cannot hold: a range that moves, past which the` through the
line `}`, inclusive; the line after them is blank, and the next starts `// File scope. One table's keys`. Paste
them, unchanged, directly under the line that starts
`//   last printed: Chapter 54, section 3 ("A clock for the effect");` in `SettingsByHand.h`. In the pasted line
`static void keepInRange(float& value, float low, float high)`, `static` becomes `inline`.

**7. `coversAnything`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp.
//   first line: // Chapter 55, section 3. True when these settings draw particles that cover: the curves look
//               with a
//   last line:  }
//   last printed: Chapter 55, section 3 ("The sort on the GPU"); `static` became `inline`.
```

**Copy.** In `ParticlesDemo.cpp`, copy the 10 lines from the line
`// Chapter 55, section 3. True when these settings draw particles that cover: the curves look with a` through the
line `}`, inclusive; the line after them is blank, and the next is
`// Replaces the settings a preset names, its prewarm included. Paused, the pool, the soft distance`. Paste them,
unchanged, directly under the line that starts `//   last printed: Chapter 55, section 3 ("The sort on the GPU");`
in `SettingsByHand.h`. In the pasted line `static bool coversAnything(const ParticleSettings& settings)`, `static`
becomes `inline`.

**8. `drawKeys`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp.
//   first line: // File scope. One table's keys: a life and whatever `drawValue` shows for a key.
//   last line:  }
//   last printed: Chapter 54, section 5 ("Curves baked into an image"); `static` became `inline`.
```

**Copy.** In `ParticlesDemo.cpp`, copy the 20 lines from the line that starts `// File scope. One table's keys`
through the line `}`, inclusive; the line after them is blank, and the next is
`// Section 7. Edits the settings and shows what came back from the GPU. True when`. Paste them, unchanged,
directly under the line that starts `//   last printed: Chapter 54, section 5 ("Curves baked into an image");` in
`SettingsByHand.h`. In the pasted line `static void drawKeys(const char* name, Table& table, DrawValue drawValue)`,
`static` becomes `inline`.

**9. `drawParticleSettings`, the panel from Sort to Pool.** Add this directly above the line
`} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp (drawParticlePanel's body, lines 326-477).
//   first line: // Chapter 55, section 3. Unsorted covering particles are shown only as the problem, and say
//               so.
//   last line:  }  (the Pool group's closing brace)
//   last printed: Chapter 55, section 3 (Sort), section 4 (Check order), section 5 (Flipbook), section 1 (the
//                 Coverage curve); Chapter 54, sections 3 and 4 (Emission), section 2 (Shape, Emitter), section
//                 5 (Look, Curves); Chapter 21, section 7 (Forces and the sliders). Pool: Chapter 21, section
//                 7, printed there as ImGui::SliderInt/ImGui::Checkbox; the reference's guarded calls are
//                 printed nowhere. Local wind: not found (Chapter 52 links the source).
inline bool drawParticleSettings(ParticleSettings& settings, EmissionSchedule& schedule, WindSources& wind,
                                bool& checkOrder, const std::string& orderVerdict)
{
    bool reset = false;
    return reset;
}
```

**Copy.** In `ParticlesDemo.cpp`, copy the 152 lines from the line
`        // Chapter 55, section 3. Unsorted covering particles are shown only as the problem, and say so.` through
the line `        }`, inclusive (the Pool group's closing brace); the line after them is blank, and the next is
`        ImGui::SeparatorText("Barriers (Chapter 57)");`. Paste them, dedented by 4 spaces, directly under the line
`    bool reset = false;` of the function printed above.

**10. `packSimulation`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp (ParticlesDemo::RecordStep, lines 1171-1193).
//   first line: const float    spread  = glm::radians(m_settings.spreadDegrees);
//   last line:  };
//   last printed: Chapter 54, section 4 ("Starting full"); the reader's edits: the settings and the step's
//                 values come in as parameters.
inline ParticleSimulation packSimulation(const ParticleSettings& settings, const ParticleStep& step)
{
}
```

**Copy.** In `ParticlesDemo.cpp`, copy the 23 lines from the line
`    const float    spread  = glm::radians(m_settings.spreadDegrees);` through the line `    };`, inclusive; the
line after them is `    vkCmdPushConstants(commandBuffer, m_computeLayout, VK_SHADER_STAGE_COMPUTE_BIT,`. Paste
them, unchanged, between the braces of the function printed above. Then, in the pasted lines:

- every `m_settings.` becomes `settings.`, seventeen times;
- the line `    const ParticleSimulation simulation{` becomes `    return ParticleSimulation{`;
- in the `.deltaTime` line, `deltaSeconds` becomes `step.deltaTime`;
- in the `.emitRequest` line, `static_cast<uint32_t>(request)` becomes `step.emitRequest`;
- in the `.frameNumber` line, `m_frameNumber++` becomes `step.frameNumber`;
- in the `.currentList` line, the value `current` becomes `step.currentList`;
- in the `.windSourceCount` line, `m_windSources.Count()` becomes `step.windSources`.

**11. `packAppearance`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp (ParticlesDemo::RecordParticles, lines
//             1444-1453).
//   first line: const float* start = m_settings.startColor;
//   last line:  };
//   last printed: Chapter 21, section 5 ("Drawing the particles"; the curves look's reading of it in Chapter
//                 54, section 5); `m_currentList` became the parameter `aliveList`.
inline ParticleAppearance packAppearance(const ParticleSettings& settings, uint32_t aliveList)
{
}
```

**Copy.** In `ParticlesDemo.cpp`, copy the 10 lines from the line `    const float* start = m_settings.startColor;`
through the line `    };`, inclusive; the line after them is
`    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT,`. Paste them, unchanged, between
the braces of the function printed above. Then, in the pasted lines, every `m_settings.` becomes `settings.`, five
times; the line `    const ParticleAppearance appearance{` becomes `    return ParticleAppearance{`; and in the
`.aliveList` line, `m_currentList` becomes `aliveList`.

**12. `packFragmentWords`.** Add this directly above the line `} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp (ParticlesDemo::RecordParticles, lines
//             1457-1458).
//   first line: const struct { float softDistance; uint32_t flipbook; } fragmentWords{
//   last line:  m_settings.softDistance, m_settings.lookKind == LOOK_CURVES && m_settings.flipbook ? 1u : 0u };
//   last printed: Chapter 55, section 5 ("A flipbook baked in compute").
inline ParticleFragmentWords packFragmentWords(const ParticleSettings& settings)
{
}
```

**Copy.** In `ParticlesDemo.cpp`, copy the 2 lines from the line
`    const struct { float softDistance; uint32_t flipbook; } fragmentWords{` through the line
`        m_settings.softDistance, m_settings.lookKind == LOOK_CURVES && m_settings.flipbook ? 1u : 0u };`,
inclusive; the line after them is
`    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_FRAGMENT_BIT,`. Paste them, unchanged, between
the braces of the function printed above. Then the first pasted line becomes `    return ParticleFragmentWords{`,
and in the second, every `m_settings.` becomes `settings.`, three times.

**13. `keepWhatAPresetLeaves`, `applyPreset`'s nine lines.** Add this directly above the line
`} // namespace by_hand`:

```cpp
// Copied from Source/PillowFort/Demos/Particles/ParticlesDemo.cpp (applyPreset's nine lines,
//             applied.softDistance to applied.windDrift; not `applied.preset = index;`).
//   first line: applied.softDistance     = settings.softDistance;
//   last line:  applied.windDrift        = settings.windDrift;
//   last printed: Chapter 55, section 3 (Sort's rule; the other eight in Chapter 54, section 2, where the rest
//                 of applyPreset is printed).
inline void keepWhatAPresetLeaves(const ParticleSettings& settings, ParticleSettings& applied)
{
}
```

**Copy.** In `ParticlesDemo.cpp`, copy the 9 lines from the line
`    applied.softDistance     = settings.softDistance;` through the line
`    applied.windDrift        = settings.windDrift;`, inclusive; the line after them is `    settings = applied;`.
Paste them, unchanged, between the braces of the function printed above.

The copy is done: 493 lines, if your code has the reference's lines. Only a failure of stage 0 sends you back to it
(below).

### The seams

**`GrassDemo.h`.** The wind panel's body becomes a function of the settings, declared beside the demo. Add this
directly above the line `} // namespace pf::demos::grass`:

```cpp
// The body of the "Wind response" header, a function so a test can draw it.
void drawWindResponse(GrassSettings& settings);
```

**`GrassDemo.cpp`.** The function goes directly above the line
`// The demo's panel (Chapter 25 section 2, grown in Chapters 26 and 27), below "Camera".`, after `windSlider`,
which it calls. Type it empty first:

```cpp
// The body of the "Wind response" header, a function so a test can draw it.
void drawWindResponse(GrassSettings& settings)
{
}
```

**Move.** In `GrassDemo.cpp`, cut the 68 lines from the line `            if (ImGui::TreeNode("Gusts"))` through
the line `            }`, inclusive; the line after them is blank, and the next is
`            if (ImGui::Button("Log values"))`. Paste them, dedented by 8 spaces, between the braces of the
function printed above. In their place type:

```cpp
            drawWindResponse(settings);
```

The header's `ImGuiTreeNodeFlags_DefaultOpen` and the **Log values** button stay in `drawGrassPanel`: the function
is the six nodes and nothing else.

**`ParticlesDemo.h`.** Add the block below directly above the line
`// GPU timestamp intervals, named for the commands between markers; not exclusive pass costs (section 8).`. Three
constants come over from `ParticlesDemo.cpp`, because the moved panel and your copy both name them; each becomes
`inline constexpr`, one definition for every file that includes the header, with its value unchanged (compare it
with the line you delete below). Two structs name what a seam takes or returns: `ParticleStep`, the five values
`RecordStep` adds to the settings each step, and `ParticleFragmentWords`, Chapter 55's two fragment words, an
unnamed struct until now, which no function could return. Then the four seams are declared:

```cpp
// Chapter 54, section 4. Prewarm runs a reset's first frame as many short steps: at most 60 a
// second of effect time, and the panel's slider stops here.
inline constexpr float MAX_PREWARM_SECONDS = 4.0f;

// The shape and look combos' labels, indexed by EMITTER_SHAPE_* and LOOK_*. ParticlesDemo.cpp asserts that each has an
// entry for every shape and look: this header stays free of EmitterShapes.h, whose macros are the shaders' own.
inline constexpr const char* SHAPE_LABELS[] = { "Point", "Disc", "Ball", "Sphere", "Box" };
inline constexpr const char* LOOK_LABELS[] = { "Chapter 21", "Curves" };

// What one simulation step adds to the settings when they are packed for the GPU.
struct ParticleStep
{
    float    deltaTime;
    uint32_t emitRequest;
    uint32_t frameNumber;
    uint32_t currentList;
    uint32_t windSources;
};

// The fragment stage's push constants (Chapter 55): the soft distance and the flipbook switch.
struct ParticleFragmentWords
{
    float    softDistance;
    uint32_t flipbook;
};

// The settings as the GPU's blocks, a function each so a test can compare them.
ParticleSimulation packSimulation(const ParticleSettings& settings, const ParticleStep& step);
ParticleAppearance packAppearance(const ParticleSettings& settings, uint32_t aliveList);
ParticleFragmentWords packFragmentWords(const ParticleSettings& settings);

// The panel's settings, from "Sort back to front" to the end of "Pool": a function so a test can draw them.
// True when the pool must be reset.
bool drawParticleSettings(ParticleSettings& settings, EmissionSchedule& schedule, WindSources& wind,
                          bool& checkOrder, const std::string& orderVerdict);
```

**`ParticlesDemo.cpp`**, from the top down. The constants leave. Replace the two lines
`// second of effect time, and the panel's slider stops at MAX_PREWARM_SECONDS.` and
`static constexpr float MAX_PREWARM_SECONDS      = 4.0f;` with this one:

```cpp
// second of effect time.
```

Replace the line `// The shape and look combos' labels, indexed by EMITTER_SHAPE_* and LOOK_*.` and the line under
it, `static constexpr const char* SHAPE_LABELS[] = { "Point", "Disc", "Ball", "Sphere", "Box" };`, with the line
below, and delete the line `static constexpr const char* LOOK_LABELS[] = { "Chapter 21", "Curves" };`. The two
`static_assert`s stay where they are, beside `PRESET_COUNT`: they name `EmitterShapes.h`'s macros, which are the
shaders' own, and the header does not include it.

```cpp
// A label for every shape and every look. The arrays are in ParticlesDemo.h, which does not include EmitterShapes.h.
```

The panel's settings come next. Their function goes directly above the line
`// Section 7. Edits the settings and shows what came back from the GPU. True when`, after `drawKeys`, the last
helper it calls. Type it with its first and last lines only:

```cpp
// The panel's settings from "Sort back to front" to the end of "Pool", a function so a test can draw them. True when
// the pool must be reset.
bool drawParticleSettings(ParticleSettings& settings, EmissionSchedule& schedule, WindSources& wind,
                          bool& checkOrder, const std::string& orderVerdict)
{
    bool reset = false;

    return reset;
}
```

**Move.** In `ParticlesDemo.cpp`, cut the 152 lines from the line
`        // Chapter 55, section 3. Unsorted covering particles are shown only as the problem, and say so.` through
the line `        }`, inclusive; the line after them is blank, and the next is
`        ImGui::SeparatorText("Barriers (Chapter 57)");`. Paste them, dedented by 4 spaces, directly under the line
`    bool reset = false;` of the function printed above. In their place type:

```cpp
        reset |= drawParticleSettings(settings, schedule, wind, checkOrder, orderVerdict);
```

The preset picker, the counters, the timings and Chapter 57's barrier controls stay in `drawParticlePanel`. The
function holds everything from **Sort back to front** to the end of **Pool**, and returns the reset that **Max
particles** and **Reset** ask for.

**The three packings, printed whole.** They are your initialisers with the copy's edits (blocks 10 to 12), and two
more: two comments go to the call sites, where the values they speak of now are, and `spread`'s declaration loses
the alignment it had among `RecordStep`'s locals. Add them directly above the line
`void ParticlesDemo::RecordCompute(VkCommandBuffer commandBuffer, uint32_t frameIndex)`:

```cpp
// Packing: the settings as the GPU's blocks, a function each so a test can compare them. Chapter 54: the step's
// values come in as `step`; the rest is read from the settings.
ParticleSimulation packSimulation(const ParticleSettings& settings, const ParticleStep& step)
{
    const float spread = glm::radians(settings.spreadDegrees);
    return ParticleSimulation{
        .emitterPosition   = glm::vec4(0.0f, settings.emitterHeight, 0.0f,
                                                  (static_cast<uint32_t>(settings.shapeKind) & EMITTER_SHAPE_KIND_MASK) == EMITTER_SHAPE_POINT ? 0.0f : settings.shapeSize),
        .gravity           = glm::vec4(0.0f, -settings.gravity, 0.0f, settings.drag),
        .deltaTime         = step.deltaTime,
        .speed             = settings.speed,
        .speedVariation    = settings.speedVariation,
        .spreadAngle       = spread,
        .lifetime          = settings.lifetime,
        .lifetimeVariation = settings.lifetimeVariation,
        .groundHeight      = 0.0f,
        .restitution       = settings.restitution,
        .friction          = settings.friction,
        .emitRequest       = step.emitRequest,
        .frameNumber       = step.frameNumber,
        .currentList       = step.currentList,
        .maxParticles      = static_cast<uint32_t>(settings.maxParticles),
        .windSourceCount   = settings.windEnabled ? step.windSources : 0u,
        .windResponseRate  = settings.windResponseRate,
        .emitterShape      = (static_cast<uint32_t>(settings.shapeKind) & EMITTER_SHAPE_KIND_MASK)
                           | (settings.launchOutward ? EMITTER_SHAPE_LAUNCH_OUTWARD : 0u),
    };
}

ParticleAppearance packAppearance(const ParticleSettings& settings, uint32_t aliveList)
{
    const float* start = settings.startColor;
    const float* end   = settings.endColor;
    return ParticleAppearance{
        .startColor   = glm::vec4(srgbToLinear(start[0]), srgbToLinear(start[1]), srgbToLinear(start[2]), start[3]),
        .endColor     = glm::vec4(srgbToLinear(end[0]), srgbToLinear(end[1]), srgbToLinear(end[2]), end[3]),
        .startSize    = settings.startSize,
        .endSize      = settings.endSize,
        .aliveList    = aliveList,
        .maxParticles = static_cast<uint32_t>(settings.maxParticles),
    };
}

ParticleFragmentWords packFragmentWords(const ParticleSettings& settings)
{
    return ParticleFragmentWords{
        settings.softDistance, settings.lookKind == LOOK_CURVES && settings.flipbook ? 1u : 0u };
}
```

**The call sites.** In `RecordStep`, replace the 23 lines from the line
`    const float    spread  = glm::radians(m_settings.spreadDegrees);` through the line `    };` after them,
inclusive, with the two middle lines of this listing; its first line and its last are already there:

```cpp
    const uint32_t current = m_currentList;
    const ParticleSimulation simulation = packSimulation(
        m_settings, { deltaSeconds, static_cast<uint32_t>(request), m_frameNumber++, current, m_windSources.Count() });   // once per step: m_frameNumber seeds the births
    vkCmdPushConstants(commandBuffer, m_computeLayout, VK_SHADER_STAGE_COMPUTE_BIT,
```

The braces list `ParticleStep`'s members in their order, and `m_frameNumber++` still runs once a step.

In `RecordParticles`, replace the 10 lines from the line `    const float* start = m_settings.startColor;` through
the line `    };` after them, inclusive, with the middle line of this listing; the comment line above it and the
call below it are already there:

```cpp
    // is linear already.
    const ParticleAppearance appearance = packAppearance(m_settings, m_currentList);   // RecordCompute flipped it to the list simulate filled
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT,
```

Then replace the two lines from the line
`    const struct { float softDistance; uint32_t flipbook; } fragmentWords{` through the line under it with the
middle line of this one; its first and last lines are already there:

```cpp
    // The soft distance, and Chapter 55's flipbook switch, which only ParticleCurves.frag reads.
    const ParticleFragmentWords fragmentWords = packFragmentWords(m_settings);
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_FRAGMENT_BIT,
```

Those are the only places that pack the particles now, and the regions above show it: nothing else writes the three
blocks.

### Checkpoint: the seams build

Every engine file you changed already existed, and the copy you made is in no project yet, so there is nothing to
generate. Build `SandboxGame` alone; the engine builds with it:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
```

The build has 0 warnings. Then run each demo for a few seconds in Debug:

```powershell
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Particles
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Grass
```

Open the groups of the `Particles` panel, and the **Wind response** nodes of the `Grass` panel: they look as they
did. The seams changed where the code is, not what it does. The copy and the test are not in the solution yet; the
next part adds them.

### The supplied test

**`premake5.lua`.** The test's project goes inside the `if _OPTIONS["tutorial-tests"] then` block, directly above
the line `    project "TutorialSceneMathTests"`, with a blank line between. Its files name the copy too, so that
the copy shows in the solution beside the test that includes it:

```lua
    -- The settings lesson: what the rows pack, draw, type into and keep, against your own hand-written code.
    project "TutorialSettingRowsTests"
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/SettingRowsTests.cpp", "Tests/TutorialHarness/SettingsByHand.h" }
        includedirs { "Vendor/GLFW/include", "Vendor/ImGui", "Vendor/ImGui/backends" }
        links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

**`SettingRowsTests.cpp`, supplied.** A learning branch made from `start` already has the file at
`Tests/TutorialHarness/SettingRowsTests.cpp`; otherwise copy it from the same path in a `reference-main` checkout
([Which checkout](../VulkanTutorial.md#choose-your-checkout) says how to keep one). It is 2,767 lines, CPU only: it
links the engine and ImGui, draws each panel in a headless ImGui window, and needs no OS window and no device. The
reference's copy is at stage 4 (on a learning branch made from `start` the copy already says 0, so there the line
is already in place). Replace the line that starts `#define PF_TEST_STAGE` with this one, which says 0:

```cpp
#define PF_TEST_STAGE 0   // raised in sections 3, 5 and 6 of the lesson, and in section 1 of Chapter 56
```

Sections 3, 5 and 6 raise it, each by a typed edit of the digit. Leave `#define PF_TEST_COPY (PF_TEST_STAGE < 4)`, a few lines below
it, as it is: it is the switch that a later chapter sets to 0 when it retires your copy.

### What stage 0 proves

**Predict first.** When stage 0 passes, what has it proved? Would it pass if this page had printed an edit wrongly,
the same way for the copy and for the seam? Does it see `RecordStep`'s call to `packSimulation`, or only the
function?

It proves that each seam does what your copy does, over every case the test runs, bit for bit where it compares
bytes:

- the grass's packing: `PackParameters` against your 32 lines, over the attempt's 284 cases;
- the particles' three packings against your initialisers, over the defaults, each preset, and cases that move each
  member;
- the presets: `SetPreset` against your keep lines, from eight starts (section 6 says why seven are needed);
- both panels, drawn in the headless window: ImGui's logged text, then the draw list;
- typed input into every slider, each checkbox, each colour channel and each button, in your copy and in the
  engine.

It does not prove the edits. The copy and the seams follow the same printed edits (the dedents, `static` to
`inline`, `m_settings` to `settings`), so an edit printed wrongly would be in both, and stage 0 would pass: your
reading of each edit against your own code is the only check of them. Nor does it see the call sites. It calls
`packSimulation` with steps of its own, and only `TutorialMirrorBatchTests` sees the push `Record` makes, at the
defaults.

### When stage 0 fails

A failure line names what it compared and the case: for packing, the setting's name, the case, and both values, as
hex and as a number; for a panel, the case and the first line of the panel's text that differs, your copy's beside
the engine's. Three sources decide which side is right: your copy (your earlier code, as Chapters 21, 52, 53, 54
and 55 had you type it), the earlier chapter's printed text (each block's comment names it), and this page's
printed lines.

- **Your seam differs from your copy, and your copy matches its chapter:** the slip is in this section's work, a
  cut, a paste, a dedent, an edit or a line of the printed packings. Fix the seam.
- **Your copy differs from its chapter's text:** you mistyped it then. Fix the copy's line to the chapter's, with a
  comment saying what you had. Your program changes on purpose, by that one value.
- **This page differs from the earlier chapter:** follow the earlier chapter in your copy and your seam, and report
  the page.

One case is the reference's own. Chapter 21, section 7 prints the Pool group with `ImGui::SliderInt` and
`ImGui::Checkbox`; the reference draws it through `pf::debug_panels::sliderInt` and `checkbox`, wrappers in
`DemoPanel.cpp` that give the widget a stable id and place its label (`sliderInt` through `responsive`; `checkbox`
with a layout of its own that wraps a long label), and no later chapter prints that form. Follow the reference's
guarded calls in your copy, and note it in a comment. For Pool, and for Local wind, whose block Chapter 52 links
instead of printing, no later printed text wins: compare with `Source/PillowFort/Demos/Particles/ParticlesDemo.cpp`
in a `reference-main` checkout.

### Checkpoint

The copy, the supplied test and its project are new to premake, so generate again with the test projects, build the
three tests, and run them from the repository root:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:TutorialSettingRowsTests;TutorialMirrorBatchTests;TutorialGrassWindTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialSettingRowsTests\TutorialSettingRowsTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialSettingRowsTests failed.' }
& .\Build\Artifacts\Debug\TutorialMirrorBatchTests\TutorialMirrorBatchTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialMirrorBatchTests failed.' }
& .\Build\Artifacts\Debug\TutorialGrassWindTests\TutorialGrassWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialGrassWindTests failed.' }
```

The build has 0 warnings. `TutorialSettingRowsTests` prints 21 lines. The first two check the test's own lists, its
eight preset names and its 32 wind settings:

```text
PASS: the lesson's eight presets
PASS: the lesson's 32 wind sliders
```

Then come the comparisons of "What stage 0 proves", in that order, and three checks of how the test names a widget
when a draw list differs. The last line is:

```text
PASS: settings rows, stage 0 (2013 checks)
```

`TutorialMirrorBatchTests`'s last line starts `PASS: camera admission`, and `TutorialGrassWindTests` ends with the
same `PASS: grass wind contract` line as in section 1.

## 3. One row per setting, and packing from the rows

Section 1 ended on a question: what shape makes the line impossible to forget? Before the attempt, write one
sentence of your own: what single thing could hold every fact that the six places repeat? Your tree already holds
half of an answer.

<a id="ch57-one-row"></a>

### Attempt CH57-one-row: one description for six places

Predict first. Of `gustSpacing`'s six places, which hold a fact that exists nowhere else, and which only repeat
facts the others hold? Its pack line writes `GrassParameters::gustSpacing` and its slider edits
`GrassSettings::gustSpacing`: can one description point at both, and what would stop it pointing at `gustSpacing`
in one struct and at `gustJitter` in the other? Section 1 asked you to find one pack line that is not a plain clamp
and one slider that is not a plain slider: can a description made of constants say what each does, and is what each
depends on a fact about the setting, or about where it is drawn?

Take Chapter 53's six places for `gustSpacing`: the field, the member with its default, the range constant, the
row, the pack line, and the slider call inside the Gusts node. For each, name the part of one description that
replaces it, or say why the place stays. Then do the same for the pack line and the slider you found in section 1.

**Acceptance:** from your description alone, without looking at your code, write four things for `gustSpacing`: its
pack line, its slider call, the text it adds to the **Log values** line at its default, and its `--grass-response`
key. Then compare each with your code, character for character apart from the spaces that align columns; a
difference is a part your description lacks. Last, write the C++ type of each part, as a struct would declare it,
and for every part that points into a struct, say which struct, and what the compiler refuses if a row points at
the wrong one.

**Transfer:** the Grass panel's **Grass casts shadows** checkbox, `grassShadows`, which `PackParameters` packs as
`settings.grassShadows ? 1u : 0u`. What does the same description need to hold a checkbox, and which of its parts
would a checkbox leave empty?

<details>
<summary>Hint 1: what each place holds</summary>

Chapter 53's `WIND_RESPONSE_SETTINGS` row holds a setting's name, stringized so it cannot be misspelled, a pointer
to its member, its range and its decimals, and two readers walk it, `--grass-response` and **Log values**, so
neither keeps a list of its own. [Chapter 53, section 2](53-Rolling-Wind.md#six-places-for-a-setting-typed-once)
gives each place its reason. For each, write down what it holds that no other place holds. The field is declared in
a header the shaders include too. The member carries the default. The range constant is a name that your copy and
Chapter 53's test use. Then look at the pack line and the slider call: is any of their tokens a fact that one of
the other places, or the row, does not already have?

</details>

<details>
<summary>Hint 2: the two lines, token by token</summary>

Write `gustSpacing`'s pack line above its slider call, and mark each token: `gustSpacing` (how many times, and in
which structs?), `GUST_SPACING_RANGE`, `"Gust spacing (m)"`, `"%.1f"`, and, inside `windSlider`,
`ImGuiSliderFlags_AlwaysClamp`. The slider call has one more fact that is not on its line: the node it sits in.
Each token needs a part of the row, or a function that reads the rows.

</details>

<details>
<summary>Hint 3: what a constant cannot say</summary>

A row is the same whatever the settings hold. `gustLengthMax`'s lower bound is the value of `gustLengthMin`, and
Far highlight's greying depends on `surfaceModel`. Neither is a constant. A fact that changes with the settings
stays where it is typed today; the question is what the row gives that line to work with.

</details>

<details>
<summary>Worked solution: the float row</summary>

| Chapter 53's place | What only it holds | In the row |
| --- | --- | --- |
| 1. `GrassParameters::gustSpacing`, in `GrassTypes.h` | the block's layout, which the shaders read from the same header | stays; the row points at it: `field`, a `float GrassParameters::*` |
| 2. `GrassSettings::gustSpacing`, default 17 | the CPU's state | stays; the row points at it: `member`, a `float GrassSettings::*`, as Chapter 53's row did |
| 3. `GUST_SPACING_RANGE` | the ends, under a name your copy and Chapter 53's test use | stays; the row names it: `range` |
| 4. the row | the name, and the decimals the log line prints | grows into the description: `name`, `decimals` |
| 5. the pack line | nothing: its field, member and range are places 1 to 3 | gone: one walk writes each row's field from its member, held inside its range |
| 6. the slider call | its label, which is on that line and nowhere else, and its place in the Gusts node | gone: `label`; `decimals`, for the format; a flag for `ImGuiSliderFlags_AlwaysClamp`; and `group`, for the node, read by one function that draws a group |

From that row the four things come back: `.gustSpacing = clampTo(settings.gustSpacing, GUST_SPACING_RANGE),`, then
`windSlider("Gust spacing (m)", &settings.gustSpacing, GUST_SPACING_RANGE, "%.1f");`, then ` gustSpacing=17.0`, and
the key `gustSpacing`, which is the name. A description without the label, or with the range as two numbers instead
of the constant, fails the comparison.

The description holds two pointers to members, bound by one name: `member`, Chapter 53's, a
`float GrassSettings::*`, and `field`, a `float GrassParameters::*`. Each type names its class, so the compiler
refuses a member of the settings where the field goes. A macro that writes both from one token, `&GrassSettings::M`
and `&GrassParameters::M`, cannot pair `gustSpacing`'s member with `gustJitter`'s field.

**`gustLengthMax`.** Its row is like the other 31, with `GUST_LENGTH_RANGE` and its own field. Its lower bound is
another setting's value, which no constant of a row can say, so its place 5 stays, as one statement: Chapter 53's
expression, typed once after the walk, replaces what the walk wrote.

**Far highlight.** Its row is a float row like the others, in a group of its own. The greying and the tooltip
depend on the surface model and on where the slider is drawn, so they stay at the call site, around the one call
that draws that group: six tree nodes, seven groups.

**The transfer.** A checkbox's value is a `bool`, so the row needs a pointer of another type,
`bool GrassSettings::*`, and a label and a group. It has no range, no decimals and no flag that holds a typed
value. Its packing is a conversion, `? 1u : 0u`, which a `float` field cannot say, so that line stays typed.
Section 5 gives the row such kinds for the particles; the Grass demo's other controls stay hand-written.

</details>

### The row

**This is `SettingRows.h`**, a new file in `Source/PillowFort/DebugPanels/`, beside `DemoPanel.h`, in
`pf::debug_panels`. It includes no ImGui header, so a demo's header can hold a table, and packing can walk it,
without the panel's headers. It holds four things: `SettingRange`, Chapter 53's `WindRange` under a name every
table can use (`WindRange` becomes its alias below, so Chapter 53's 31 constants stay as they are); `SettingFlags`,
with one flag for now, `SETTING_HOLDS`, which is what `windSlider` gave every slider,
`ImGuiSliderFlags_AlwaysClamp`; the row, `SettingRow<Settings, Block, Group>`, whose `name`, `member`, `range` and
`decimals` are Chapter 53's, with `field`, where packing copies the member, and `label`, `group` and `flags`, which
the panel reads from section 4; and `settingRowsValid`, `constexpr`, so a `static_assert` can run its five rules
over a whole table while the header compiles.

> **Jump:** what is the type of a pointer to `GrassParameters::gustSpacing`? It is `float GrassParameters::*`: not
> an address, but a name for one member of any `GrassParameters`. `parameters.*field` is that member of
> `parameters`, and assigning to it writes the block. Chapter 53's row held one such pointer,
> `float GrassSettings::*`, to read a setting by name. A row now holds two, bound by one name: `member` into the
> CPU's settings and `field` into the GPU's block. That pair is the new idea. Each pointer's type names its class,
> so a member of `GrassSettings` cannot go where the field goes; and the grass macro below writes both from one
> token, so a row cannot pair one setting's member with another setting's field.

Sections 5 and 6 add to this file; for now it is the float row, whole:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  A setting as a row: its name, the member that holds it, where packing copies it and how the panel draws it
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/DebugPanels/SettingRows.h
#pragma once

#include <array>
#include <cstddef>
#include <type_traits>

namespace pf::debug_panels {

struct SettingRange { float min, max; };

// A row's flags. SETTING_HOLDS is ImGuiSliderFlags_AlwaysClamp: a typed value stays inside the range. Without it a typed
// finite value may leave (the guarded slider still puts back a NaN or an infinity).
enum SettingFlags : int
{
    SETTING_HOLDS = 1 << 0,
};

// One setting: the float member that holds it, where packing copies it, and how the panel shows it. Group is the table's
// own enum of the calls that draw it, so a group from another table's enum does not compile.
template <class Settings, class Block, class Group>
struct SettingRow
{
    static_assert(std::is_enum_v<Group>, "a table's groups are its own enum");
    const char*       name;                  // the member's own name: the key of --grass-response and the log line, and the tests'
    float Settings::* member   = nullptr;    // a float: a slider
    float Block::*    field    = nullptr;    // where packing copies member; null: converted by hand, or CPU only
    SettingRange      range    = {};         // the slider's ends, and packing's clamp when the caller asks for one
    int               decimals = -1;         // a float slider's "%.<decimals>f" and the log line's: 0 to 3
    const char*       label    = nullptr;    // the control's label
    Group             group    = {};         // which call draws it: a table's own enum
    int               flags    = 0;          // SettingFlags
};

// Each rule has its reason:
//  - a row needs its name (lookups and logs print it);
//  - a member, because the member is what the panel draws and packing copies;
//  - decimals 0 to 3 (the panel indexes a four-entry format table, and a negative precision throws in the log line);
//  - a range whose min is above its max breaks std::clamp;
//  - a label, which is the widget's id and its text.
template <class Settings, class Block, class Group, std::size_t Count>
constexpr bool settingRowsValid(const std::array<SettingRow<Settings, Block, Group>, Count>& rows)
{
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if (row.name == nullptr) { return false; }
        if (row.member == nullptr) { return false; }
        if (row.decimals < 0 || row.decimals > 3) { return false; }
        if (row.range.min > row.range.max) { return false; }
        if (row.label == nullptr) { return false; }
    }
    return true;
}

} // namespace pf::debug_panels
```

### The grass table

**This is the table**, in `GrassField.h`: five edits, from the top down. The header reads the row, so it includes
it, directly above the line `#include "PillowFort/Demos/Demo.h"`:

```cpp
#include "PillowFort/DebugPanels/SettingRows.h"
```

`WindRange` becomes the shared range. Replace the line `struct WindRange { float min, max; };` with the line below;
the comment above it stays, and is still true:

```cpp
using WindRange = debug_panels::SettingRange;
```

Then Chapter 53's row type and macro give way to three things. **`WindResponseGroup`** is the table's own enum of
groups: a group is the run of rows one call draws, not a category, so there is one per tree node of **Wind
response**, and a seventh, `WIND_SHADING_LEGACY`, for Far highlight, which Wind shading's node draws on its own
inside a disabled block. **`WindResponseSetting`** keeps its name, so every line that names it compiles unchanged,
and is now the shared row over `GrassSettings`, `GrassParameters` and that enum. **The macro** takes five
arguments, `(M, RANGE, DECIMALS, LABEL, GROUP)`, and writes the rest itself: `#M`, `&GrassSettings::M` and
`&GrassParameters::M` from one token, and `SETTING_HOLDS` on every row, as `windSlider` gave every slider its clamp
flag. It uses designated initialisers, so a member added to the row later, as section 5 does, cannot shift the
values after it. One trap: the preprocessor splits a macro's arguments at every comma outside parentheses, so a
literal range `{ 0.0f, 5.0f }` arrives as two arguments and the call has one too many. All 32 rows pass a named
constant; a literal needs parentheses, `(WindRange{ 0.0f, 5.0f })`.

Replace the 12 lines from the line that starts
`// The wind-response settings by name, in GrassSettings' six groups` through the line
`#define PF_WIND_RESPONSE_ROW(member, range, decimals) { #member, &GrassSettings::member, range, decimals }` with
these; the line after them, `inline constexpr auto WIND_RESPONSE_SETTINGS = std::to_array<WindResponseSetting>({`,
stays:

```cpp
// The run of rows one call draws: one per tree node of the "Wind response" header, except Far highlight, which Wind
// shading's node draws on its own between BeginDisabled and EndDisabled (only Legacy fade reads it).
enum WindResponseGroup : int
{
    WIND_GUSTS, WIND_RIPPLES, WIND_SPRING, WIND_LEAN, WIND_BLADES, WIND_SHADING, WIND_SHADING_LEGACY
};

// The wind-response settings by name, in the panel's six tree nodes: the one place the names exist. A row is the
// member's own name (stringized, so it cannot drift), the member, the GPU block's field it packs into (named by the same
// token, so a row cannot pack into another field), its range, the decimals it prints with, its slider's label and the
// group that draws it, and every row holds a typed value inside its range (SETTING_HOLDS). The table's jobs: the panel
// draws from it, packing copies from it, `--grass-response <name>=<value>` looks a setting up in it, and the "Log values"
// line prints from it (same order, same decimals).
using WindResponseSetting = debug_panels::SettingRow<GrassSettings, GrassParameters, WindResponseGroup>;

// Designated, so a member added to the row later cannot shift the fields after it.
#define PF_WIND_RESPONSE_ROW(M, RANGE, DECIMALS, LABEL, GROUP) \
    { .name = #M, .member = &GrassSettings::M, .field = &GrassParameters::M, .range = RANGE, .decimals = DECIMALS, \
      .label = LABEL, .group = GROUP, .flags = debug_panels::SETTING_HOLDS }
```

Each row gains the label its `windSlider` call passes and the group of its tree node; the names, ranges, decimals
and group comments stay. Replace the 38 lines between the line
`inline constexpr auto WIND_RESPONSE_SETTINGS = std::to_array<WindResponseSetting>({` and the table's closing
`});`, the six group comments and the 32 rows, with these:

```cpp
    // Gusts: where the big fronts are
    PF_WIND_RESPONSE_ROW(frontSpeed, FRONT_SPEED_RANGE, 2, "Front speed (x wind)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustSpacing, GUST_SPACING_RANGE, 1, "Gust spacing (m)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustJitter, GUST_JITTER_RANGE, 2, "Gust jitter (spacings)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustCrestLength, GUST_CREST_LENGTH_RANGE, 1, "Gust crest length (m)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustCrestBend, GUST_CREST_BEND_RANGE, 2, "Gust crest bend (spacings)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustOccupancy, GUST_OCCUPANCY_RANGE, 2, "Gust occupancy", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustLengthMin, GUST_LENGTH_RANGE, 1, "Gust length min (m)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(gustLengthMax, GUST_LENGTH_RANGE, 1, "Gust length max (m)", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(frontSizeFloor, FRONT_SIZE_FLOOR_RANGE, 2, "Front size floor", WIND_GUSTS),
    PF_WIND_RESPONSE_ROW(swellWeight, SWELL_WEIGHT_RANGE, 2, "Swell weight", WIND_GUSTS),
    // Ripples: the small layer
    PF_WIND_RESPONSE_ROW(rippleStrength, RIPPLE_STRENGTH_RANGE, 2, "Ripple strength (x gust lean)", WIND_RIPPLES),
    PF_WIND_RESPONSE_ROW(rippleSpacing, RIPPLE_SPACING_RANGE, 2, "Ripple spacing (m)", WIND_RIPPLES),
    PF_WIND_RESPONSE_ROW(rippleJitter, RIPPLE_JITTER_RANGE, 2, "Ripple jitter (spacings)", WIND_RIPPLES),
    PF_WIND_RESPONSE_ROW(rippleOccupancy, RIPPLE_OCCUPANCY_RANGE, 2, "Ripple occupancy", WIND_RIPPLES),
    PF_WIND_RESPONSE_ROW(rippleBaseline, RIPPLE_BASELINE_RANGE, 2, "Ripple baseline", WIND_RIPPLES),
    // Spring: how a clump answers a front
    PF_WIND_RESPONSE_ROW(springFrequency, SPRING_FREQUENCY_RANGE, 2, "Spring frequency (Hz)", WIND_SPRING),
    PF_WIND_RESPONSE_ROW(springDamping, SPRING_DAMPING_RANGE, 2, "Spring damping (ratio)", WIND_SPRING),
    PF_WIND_RESPONSE_ROW(springSpread, SPRING_SPREAD_RANGE, 2, "Spring spread", WIND_SPRING),
    PF_WIND_RESPONSE_ROW(tipLag, TIP_LAG_RANGE, 2, "Tip lag (s)", WIND_SPRING),
    // Lean: how far the grass goes over
    PF_WIND_RESPONSE_ROW(steadyLean, STEADY_LEAN_RANGE, 3, "Steady lean (rad)", WIND_LEAN),
    PF_WIND_RESPONSE_ROW(gustLean, GUST_LEAN_RANGE, 3, "Gust lean (rad)", WIND_LEAN),
    PF_WIND_RESPONSE_ROW(dragKnee, DRAG_KNEE_RANGE, 1, "Drag knee (m/s)", WIND_LEAN),
    PF_WIND_RESPONSE_ROW(leanLimit, LEAN_LIMIT_RANGE, 2, "Lean limit (rad)", WIND_LEAN),
    PF_WIND_RESPONSE_ROW(impostorLean, IMPOSTOR_LEAN_RANGE, 2, "Impostor lean (x tip lean)", WIND_LEAN),
    // Blades: one blade against the next
    PF_WIND_RESPONSE_ROW(bladeLagSpread, BLADE_LAG_SPREAD_RANGE, 2, "Blade lag spread (s)", WIND_BLADES),
    PF_WIND_RESPONSE_ROW(bladeFlutter, BLADE_FLUTTER_RANGE, 3, "Blade flutter (rad)", WIND_BLADES),
    PF_WIND_RESPONSE_ROW(crosswindShrink, CROSSWIND_SHRINK_RANGE, 2, "Crosswind shrink", WIND_BLADES),
    PF_WIND_RESPONSE_ROW(swingStraighten, SWING_STRAIGHTEN_RANGE, 2, "Straighten in a swing", WIND_BLADES),
    // Wind shading
    PF_WIND_RESPONSE_ROW(gustBrightness, GUST_BRIGHTNESS_RANGE, 2, "Gust brightness", WIND_SHADING),
    PF_WIND_RESPONSE_ROW(layLight, LAY_LIGHT_RANGE, 2, "Lay light", WIND_SHADING),
    PF_WIND_RESPONSE_ROW(rootRoughness, ROOT_ROUGHNESS_RANGE, 2, "Root roughness (x tip)", WIND_SHADING),
    PF_WIND_RESPONSE_ROW(farHighlight, FAR_HIGHLIGHT_RANGE, 2, "Far highlight (Legacy fade)", WIND_SHADING_LEGACY),
```

Last, the validator runs over the table. Add this directly under the line
`static_assert(WIND_RESPONSE_SETTINGS.size() == 32, "one row per wind-response setting");`:

```cpp
static_assert(debug_panels::settingRowsValid(WIND_RESPONSE_SETTINGS));
```

A row without a label, with decimals 4, or with its range's ends swapped now stops the build in `GrassField.h`.

### Checkpoint: the rows compile

`SettingRows.h` is new, so generate first. Then build the game and two tests, and run both from the repository
root:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests;TutorialGrassWindTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialSettingRowsTests\TutorialSettingRowsTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialSettingRowsTests failed.' }
& .\Build\Artifacts\Debug\TutorialGrassWindTests\TutorialGrassWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialGrassWindTests failed.' }
```

- **The build** ends with `0 Warning(s)` and `0 Error(s)`. `PackParameters` still has its 32 lines and the panel
  its `windSlider` calls.
- **The supplied test** is still at stage 0, so it prints section 2's report, ending
  `PASS: settings rows, stage 0 (2013 checks)`. From the table it takes only the names, members and ranges it
  builds its cases from.
- **`TutorialGrassWindTests`** passes, all 38 checks and its summary line. Its table checks read the new rows
  through `.name`, `.member`, `.range` and `.decimals`, and three of them say what came through:

```text
PASS: the table's rows are GrassSettings' floats in declaration order: each member 4 bytes after the one before
PASS: the "Log values" line for default GrassSettings under the Grass demo's default world wind is byte-identical to the recorded output
PASS: every row stores its own range's max for a huge value and its min for a hugely negative one
```

Nothing here reads `field`, `label`, `group` or `flags`: packing reads `field` at the end of this section, and the
panel reads the other three in section 4.

### Packing from the rows

**This is the walk**, `packSettingRows`, in `SettingRows.h`, a template over any table. For each row with both a
member and a field, it copies the member into the field, clamped to the row's range when `clamp` is set. The clamp
is the caller's choice for the whole table, not a row's: Chapter 53 holds every grass value inside its range before
the GPU sees it, and section 5's particles pack theirs straight, as typed. The test for `member` looks redundant
today, since the validator requires a member, but section 5's other kinds leave it null. `std::clamp` needs
`<algorithm>`, which goes directly above the line `#include <array>`:

```cpp
#include <algorithm>
```

The function goes directly above the line `} // namespace pf::debug_panels`, with a blank line between:

```cpp
// Copies each float row that has a field into that field of the GPU block, held inside the row's range when `clamp` is
// set.
template <class Settings, class Block, class Group, std::size_t Count>
void packSettingRows(const std::array<SettingRow<Settings, Block, Group>, Count>& rows, const Settings& settings,
                     Block& block, bool clamp)
{
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if (row.member != nullptr && row.field != nullptr)
        {
            const float value = settings.*(row.member);
            block.*(row.field) = clamp ? std::clamp(value, row.range.min, row.range.max) : value;
        }
    }
}
```

**This is `packWindResponse`**, in `GrassField.cpp`: Chapter 53's fifth place, for all 32 settings at once. It is
one walk with the clamp on, then Chapter 53's expression for `gustLengthMax`, as a statement. The walk clamps
`gustLengthMax` to its own range, and the statement then replaces it with the value clamped between the shortest
gust and the range's top, so the longest gust is never shorter than the shortest; this statement is now `clampTo`'s
only caller. The statement keeps a hole that Chapter 53's expression already had: with a NaN `gustLengthMin`,
`gustLengthMax` can stay below the range's minimum. No user path reaches it, and the supplied test packs that very
case, so your copy and the walk give the same bytes.

It goes directly above the line
`GrassParameters GrassField::PackParameters(const GrassSettings& settings, const GrassFrame& frame) const`, with a
blank line between:

```cpp
// File scope, above PackParameters: the 32 wind settings into their fields, each held inside its slider's range. The walk
// writes gustLengthMax first, held only to its own range; the statement below then replaces it, so the longest gust is
// never shorter than the shortest (Chapter 53's expression, as a statement).
static void packWindResponse(const GrassSettings& settings, GrassParameters& parameters)
{
    debug_panels::packSettingRows(WIND_RESPONSE_SETTINGS, settings, parameters, true);
    parameters.gustLengthMax = std::clamp(settings.gustLengthMax, clampTo(settings.gustLengthMin, GUST_LENGTH_RANGE),
                                          GUST_LENGTH_RANGE.max);
}
```

**This is the end of `PackParameters`.** In its initialiser, delete the 39 lines from the line
`        // Chapter 53: the wind response` through the line
`        .farHighlight    = clampTo(settings.farHighlight, FAR_HIGHLIGHT_RANGE),`: the comment, the six group
comments and the 32 lines. The line after them is `    };`. The initialiser now leaves the 32 wind fields at zero,
and the walk writes them once the block exists. Add the call directly under the line
`    std::copy(frame.frustum.planes.begin(), frame.frustum.planes.end(), parameters.frustumPlanes);`. The listing
shows the function's end as it now reads; only the `packWindResponse` line is new, and the five lines around it are
already there:

```cpp
        .shadowCandidates = settings.grassShadows ? 1u : 0u,
        .sampleCount = static_cast<uint>(m_context.formats.samples),
    };
    std::copy(frame.frustum.planes.begin(), frame.frustum.planes.end(), parameters.frustumPlanes);
    packWindResponse(settings, parameters);   // Chapter 53: the wind response
    return parameters;
```

Compare it with yours, looking for a second place. If one of the 39 lines were left in the initialiser, it would
write the same bytes as the walk today, so no test would see it, and it would drift from its row later. In yours,
the last initialiser is `.sampleCount`, and the only wind line is the call.

**What a warning says here.** Drop Chapter 53's expression from `packWindResponse` and `clampTo` loses its last
caller: MSVC at /W4 warns C4505 about a static function nobody calls, while Chapter 53's test still passes all 38
checks. The supplied test sees the dropped expression too, by comparing with your copy. The warning needs no copy:
once a later chapter retires it, the warning may be the only signal that the expression has gone, which is why
every build on this page ends at 0 warnings.

### Which side wins, for the rows

Section 2's three sources still decide; a row adds one case: your row differs from this page's, so you mistyped it,
and you fix the row. A grass range cannot differ (your rows and your copy name the same constants, and Chapter 53's
test checks each name's own constant unless two are equal); a row's decimals print in the **Log values** line,
which Chapter 53's test pins, so where your copy's slider format and your row's decimals disagree, the decimals
win, and you edit the copy's format. The control at this section's checkpoint shows it.

**Stage 1.** The test has more to check now that the table exists. In `Tests/TutorialHarness/SettingRowsTests.cpp`,
replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 1   // raised in sections 3, 5 and 6 of the lesson, and in section 1 of Chapter 56
```

### Checkpoint

No file is new since the checkpoint above, so there is nothing to generate. Build the game and four tests, and run
them from the repository root:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests;TutorialGrassWindTests;TutorialWorldWindTests;TutorialWorldWindTurnTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialSettingRowsTests\TutorialSettingRowsTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialSettingRowsTests failed.' }
& .\Build\Artifacts\Debug\TutorialGrassWindTests\TutorialGrassWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialGrassWindTests failed.' }
& .\Build\Artifacts\Debug\TutorialWorldWindTests\TutorialWorldWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialWorldWindTests failed.' }
& .\Build\Artifacts\Debug\TutorialWorldWindTurnTests\TutorialWorldWindTurnTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialWorldWindTurnTests failed.' }
```

- **The build** ends with `0 Warning(s)` and `0 Error(s)`; the warning above is why that matters.
- **The supplied test** prints section 2's lines, then five new ones before its last:

```text
PASS: the grass table is valid
PASS: no member between farHighlight and thicken
PASS: the grass table has a row for each of GRASS_WIND's 32
PASS: grass rows: each name of GRASS_WIND once, in order (32 cases)
PASS: grass rows: each row's member and field (32 cases)
PASS: settings rows, stage 1 (2080 checks)
```

Section 2's `PASS: grass packing: PackParameters against the copy's packWindResponse (284 cases)` now runs your
walk against your 32 hand lines. The new lines check the table against `GRASS_WIND`, the test's own list of the 32:
that the `static_assert` holds at run time; that no member sits between `farHighlight` and `thicken`, since one
added after the last wind setting moves `thicken`; and that each name appears once, in order, with its member and
field, so each wind field is written by exactly one row.

**The other tests.** `TutorialGrassWindTests` passes, all 38 checks and its summary line. The two world-wind tests
pack a `GrassParameters` through `PackParameters`, so they run the walk too, and pass: `TutorialWorldWindTests`
ends `PASS: 110 checks: calm zeros, ...`, and `TutorialWorldWindTurnTests` ends
`PASS: 399 checks: refused turn rates and directions, ...`.

**A prediction, then a run.** Give `gustSpacing`'s row 2 decimals instead of 1. Which checks fail, in which of the
two tests, and why? Make the change, a mistake to try and put back:

```cpp
    PF_WIND_RESPONSE_ROW(gustSpacing, GUST_SPACING_RANGE, 2, "Gust spacing (m)", WIND_GUSTS),
```

Build, to 0 warnings, and run `TutorialSettingRowsTests` and `TutorialGrassWindTests`. The supplied test passes,
`PASS: settings rows, stage 1 (2080 checks)`: packing has no decimals, and the panel is still drawn by `windSlider`
with its own `"%.1f"`, so nothing it compares reads a row's decimals yet. Chapter 53's test fails one check:

```text
FAIL: the "Log values" line for default GrassSettings under the Grass demo's default world wind is byte-identical to the recorded output
1 checks failed.
```

The `got:` line it prints above the failure has `gustSpacing=17.00`, where the recorded line has
`gustSpacing=17.0`. The decimals are pinned by the log line and Chapter 53's test, not by your copy; from section 4
they are the slider's format too. Put the 1 back, build, and both tests pass again.

## 4. The panel from the rows

Since section 3 the rows hold every part of a wind slider. This section draws **Wind response** from them through
one function, and the sixth place, `windSlider`, goes. Nothing on screen changes; the supplied test, still at stage
1, compares the panel drawn from your rows with the one your copy draws by hand.

### One function draws a group

**This is `drawSettingRows`**, in `DemoPanel.h`. It walks a table and draws each row of one group, in table order,
as a guarded float slider: the `sliderFloat` of [Chapter 9, section 6](09-Demo-Harness.md#a-guarded-float-slider),
not ImGui's own, so a slider drawn from a row puts back a typed NaN or infinity as every other slider does, and no
other function draws rows. The format comes from a four-entry table indexed by the row's decimals, which is why the
validator refuses decimals outside 0 to 3. `SETTING_HOLDS` becomes `ImGuiSliderFlags_AlwaysClamp`. It draws float
rows only; section 5 teaches it the other kinds.

Its group parameter has the table's own enum type, deduced from both the table and the group you pass, so a group
from another table's enum, or a bare number, does not compile. A wrong group of the right enum does compile, and
the supplied test's panel checks catch that one: the control at the end of this section shows its message.

A group that draws no row is a mistake in the caller, and in Debug the `assert` stops there; the supplied test
routes the C runtime's reports to its error output, so its run ends instead of waiting on a dialog. In Release the
assert is gone and an empty group draws nothing, and `(void)drew;` keeps that build from warning about a variable
it sets and never reads.

The header now needs the row type, `std::array`, `assert` and `std::size_t`. Replace the line `#include <imgui.h>`
with these seven lines; the third is that line, unchanged:

```cpp
#include "PillowFort/DebugPanels/SettingRows.h"

#include <imgui.h>

#include <array>
#include <cassert>
#include <cstddef>
```

The function goes directly under the line `bool checkbox(const char*, bool*);`, the header's last declaration, with
a blank line between:

```cpp
// Draws each row of `group`, in table order, as a guarded float slider: "%.<decimals>f", and a typed value held inside the
// range when the row says SETTING_HOLDS. This draws float rows only. Returns whether a slider changed. A group that draws
// no row is a mistake in the caller.
template <class Settings, class Block, class Group, std::size_t Count>
bool drawSettingRows(const std::array<SettingRow<Settings, Block, Group>, Count>& rows, Group group, Settings& settings)
{
    static constexpr const char* FORMAT[4] = { "%.0f", "%.1f", "%.2f", "%.3f" };
    bool changed = false;
    bool drew = false;
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if (row.group != group) { continue; }
        drew = true;
        ImGuiSliderFlags flags = 0;
        if ((row.flags & SETTING_HOLDS) != 0) { flags |= ImGuiSliderFlags_AlwaysClamp; }
        changed |= sliderFloat(row.label, &(settings.*row.member), row.range.min, row.range.max, FORMAT[row.decimals], flags);
    }
    assert(drew && "no row of this group");
    (void)drew;
    return changed;
}
```

### Wind response, from the rows

**This is `drawWindResponse`**, in `GrassDemo.cpp`, the seam section 2 moved out of the panel. Each of its six tree
nodes now makes one call for its group, where it had a `windSlider` line for each setting. Wind shading's node
makes two: its own group, then Far highlight's, between `BeginDisabled` and `EndDisabled`, with the tooltip after
it. The condition that greys it out and the tooltip stay by hand at the call site, and `IsItemHovered` asks about
the last item drawn, which is that group's one row.

Replace the whole function, the 71 lines from the line `void drawWindResponse(GrassSettings& settings)` through its
closing `}`, with these; the line after them is blank, the one after that is
`// The demo's panel (Chapter 25 section 2, grown in Chapters 26 and 27), below "Camera".`, and the comment above
the function stays:

```cpp
void drawWindResponse(GrassSettings& settings)
{
    if (ImGui::TreeNode("Gusts"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_GUSTS, settings);
        ImGui::TreePop();
    }

    if (ImGui::TreeNode("Ripples"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_RIPPLES, settings);
        ImGui::TreePop();
    }

    if (ImGui::TreeNode("Spring"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_SPRING, settings);
        ImGui::TreePop();
    }

    if (ImGui::TreeNode("Lean"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_LEAN, settings);
        ImGui::TreePop();
    }

    if (ImGui::TreeNode("Blades"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_BLADES, settings);
        ImGui::TreePop();
    }

    if (ImGui::TreeNode("Wind shading"))
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_SHADING, settings);
        // Only Legacy fade blends far normals toward the ground, so only it reads Far highlight. It is a group of its own so
        // it can be drawn disabled otherwise, and the tooltip asks about the group's one row, the last item drawn.
        ImGui::BeginDisabled(settings.surfaceModel != GRASS_SURFACE_LEGACY);
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_SHADING_LEGACY, settings);
        if (settings.surfaceModel != GRASS_SURFACE_LEGACY && ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled))
        {
            ImGui::SetTooltip("Only Legacy fade blends far normals toward the ground.");
        }
        ImGui::EndDisabled();
        ImGui::TreePop();
    }
}
```

`windSlider` now has no caller, and /W4 warns C4505 about a static function nobody calls, so it goes. Delete the
six lines from the line
`// One wind-response slider: its range is the one PackParameters clamps to, and a typed value stays inside it.`
through the blank line under `windSlider`'s closing `}`; the line after them is
`// The body of the "Wind response" header, a function so a test can draw it.`

The comment above the **Wind response** header in `drawGrassPanel` describes the nodes. Replace the line
`        // One node per group, in GrassSettings' order, each listing its settings in that order, as the log line does.`
with:

```cpp
        // One tree node per group of GrassSettings, in its order; each node draws its rows in table order, which is the log
        // line's order (Far highlight is a group of its own, inside Wind shading).
```

### A snapshot names its files

A snapshot holds only the files its manifest names. Chapter 42's prepared CPU pair, `ch42-integrated-drift`
([Chapter 42, section 2](42-One-Wind.md#2-a-wind-that-turns-without-jumping)), compiles the real `WorldWind.cpp`,
whose panel function includes `DemoPanel.h`, and `DemoPanel.h` now includes `SettingRows.h`, so the manifest names
it too. In `Tests/TutorialHarness/Checkpoints/Manifest.psd1`, directly under the line
`                'Source/PillowFort/DebugPanels/DemoPanel.h'`, the only line that names that header, add the line
`                'Source/PillowFort/DebugPanels/SettingRows.h'`, indented by the same 16 spaces.

### Checkpoint

No file is new, so there is nothing to generate. Build the game and three tests, and run them from the repository
root:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests;TutorialGrassWindTests;TutorialUiScaleTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialSettingRowsTests\TutorialSettingRowsTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialSettingRowsTests failed.' }
& .\Build\Artifacts\Debug\TutorialGrassWindTests\TutorialGrassWindTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialGrassWindTests failed.' }
& .\Build\Artifacts\Debug\TutorialUiScaleTests\TutorialUiScaleTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialUiScaleTests failed.' }
```

- **The build** ends with `0 Warning(s)` and `0 Error(s)`.
- **The supplied test**, still at stage 1, prints the same report as section 3's checkpoint, ending
  `PASS: settings rows, stage 1 (2080 checks)`. Two of its lines now compare the panel drawn from your rows with
  your `windSlider` calls in the copy, by ImGui's logged text (each label and value) and then the draw list, and by
  typing into each of the 32 sliders, a huge number, its negative, a NaN and an infinity among the texts:

```text
PASS: grass panel: drawWindResponse against the copy (text, then draw list) (17 cases)
PASS: grass typed input: each wind slider, the copy against the engine (192 cases)
```

- **`TutorialGrassWindTests`** passes, all 38 checks and its summary line. **`TutorialUiScaleTests`** passes: it
  counts the direct ImGui float calls in `Source/` outside `DemoPanel.cpp`, and `drawSettingRows` makes none.
- **The program.** Run Grass in Debug, `& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Grass`. **Wind
  response** is open, with its six collapsed nodes, each holding the sliders, labels and values it held before; Far
  highlight is greyed out unless **Shading** is Legacy fade. With Shading at Blade lighting, the default, hover
  over it for its tooltip: no case of the supplied test hovers, so the tooltip is the one part of this panel it
  never sees. **Log values** prints the same line as before this page. Close the window.

### A prediction, then a run

Drop "(m)" from Gust spacing's label, in its row. Which checks fail, and which test stays quiet? Make the change, a
mistake to try and put back:

```cpp
    PF_WIND_RESPONSE_ROW(gustSpacing, GUST_SPACING_RANGE, 1, "Gust spacing", WIND_GUSTS),
```

Build, to 0 warnings, and run `TutorialSettingRowsTests` and `TutorialGrassWindTests`. Chapter 53's test passes: it
reads the names, members, ranges and decimals, never a label. The supplied test ends
`FAIL: 22 of 2079 checks, stage 1`: one fewer than 2080, because typed input counts five cases, not six, for the
slider it cannot find. Its first failure is the panel comparison's:

```text
FAIL: grass panel: drawWindResponse against the copy (text, then draw list): case 'default-legacy': text differs at line 3: copy [    { 17.0 } Gust spacing (m)], live [    { 17.0 } Gust spacing]
```

The same comparison fails in 16 of its 17 cases. Then five typed-input checks for Gust spacing fail with the first
message below, and one check that names a draw-list difference cannot place the slider. When the live panel has no
slider the copy has, the typed-input checks say which slip they found:

- `no row has this label: its label differs from the guide's, or its row is missing: compare your row's label with the chapter`
- `a row has this label, but the row's group is wrong: it is not a group drawn under this header or node: compare the row's group with the chapter`
- `a row has this label and the right group, but nothing draws it there: no call draws its group under this header or node (the fourth case: a slip outside the rows)`

The first two compare your row with this page's, a label and a group. The test's own text calls the third "the
fourth case": a call drawing the wrong group is a fourth kind of slip, outside the rows and the three sources. Your
copy's slider still says "(m)", so the comparison catches the change; a label you change on purpose is two edits
while the copy is in, the row and the copy's slider. Put "(m)" back, build, and the test passes again.

## 5. Every kind of setting: the particles

Chapter 53's 32 settings were all one kind, each packed, clamped, into the field of its own name. The particles'
settings are neither. This section gives the row a kind, writes the particles' two tables, packs from them, and
then draws `drawParticleSettings` from them, with a checkpoint halfway.

<a id="ch57-kinds"></a>

### Attempt CH57-kinds: what kind of setting is each

Predict first. Of `ParticleSettings`' 34 members, how many does a float slider draw, and how many of those does
`packSimulation` copy unchanged into the field of the same name? `speed` and `spreadDegrees` sit side by side under
Emitter: what does packing do to each? Which members can no single widget draw? `preset` is an int picked from a
combo, like `shapeKind`: what does picking a preset change that picking a shape does not?

Sort the members of `ParticleSettings`, then `EmissionSettings`' three, by the control that draws them and by
whether packing copies them **straight** into `ParticleSimulation`: unchanged, into the field of the same name.
Single out the members that are not one value with one control, and say what each is instead. Read
`drawParticleSettings`, `drawParticlePanel` and the three pack functions as section 2 left them.

**Acceptance:** every member of `ParticleSettings` appears once, and your counts add to 34. Each member you call
straight names its field, and that field's line in `packSimulation` reads the member and nothing else. Each member
you single out is shown, from its type or from the code that draws it, to hold more than one value or to have no
control of its own.

**Transfer:** on paper only, add a float that the CPU reads and a preset leaves alone. List its places today, and
once every member has a row. Which of the row's pointers stays null, and which of today's places is still a line of
its own until section 6?

<details>
<summary>Hint 1: walk the panel, one call at a time</summary>

Each call in `drawParticleSettings` draws one control: write the member it edits beside it. A member you never meet
is drawn elsewhere, or by a loop: look in `drawParticlePanel`, and inside the Emission and Curves headers.

</details>

<details>
<summary>Hint 2: straight means unchanged, and the same name</summary>

In `packSimulation`, a line whose right side is `settings.` and the field's own name, with nothing applied, is
straight. A `vec4`'s lane, a conversion, a condition or a word built from two members is not, and nor is a float
copied into another block.

</details>

<details>
<summary>Hint 3: one value, one control</summary>

Look at each member's type. A struct, or an array of structs, holds more than one value; then ask whether one
widget draws it all. `float startColor[4]` is four floats, but one colour editor draws them. For `preset`, ask what
choosing an entry does to the other members.

</details>

<details>
<summary>Worked solution: the 34 members, sorted</summary>

| Control | Members | What packing does |
| --- | --- | --- |
| float slider | `speed`, `speedVariation`, `lifetime`, `lifetimeVariation`, `restitution`, `friction`, `windResponseRate` | straight |
| float slider | `shapeSize`, `emitterHeight`, `spreadDegrees`, `gravity`, `drag` | converted: lanes, radians |
| float slider | `startSize`, `endSize`, `softDistance` | copied, into other blocks |
| float slider | `emitRate`, `prewarmSeconds`, `windRadius`, `windLifetime`, `windDrift` | none: the CPU reads them |
| int slider | `maxParticles` | converted to `uint32_t` |
| combo | `shapeKind`, `lookKind`, `blend` | the shape word; the pipeline |
| checkbox | `sortBackToFront`, `launchOutward`, `windEnabled`, `flipbook`, `paused` | a word, a count; the CPU |
| colour editor | `startColor`, `endColor` | converted from sRGB |
| singled out | `curves`, `emission`, `preset` | none |

That is 20 float sliders, 7 of them straight, and 34 members. `spreadDegrees` becomes radians in `spreadAngle`; the
sizes and the soft distance are copied unchanged, but into `ParticleAppearance` and `ParticleFragmentWords`.

- **`curves`** is a `ParticleLook`: four key tables, each a count and its keys, drawn by `drawKeys` with each key's
  life held between its neighbours. Many values, no single widget.
- **`emission`** is an `EmissionSettings` of three: a `duration` slider the CPU's clock reads, a `looping`
  checkbox, and `bursts`, singled out again: four slots, each a time whose range moves with the duration, and a
  count.
- **`preset`** is one int, but its picker in `drawParticlePanel` is an action: choosing an entry applies a whole
  preset, rewriting the members it names. No control sets it alone.

The colours stay: four floats, one colour, one control.

**The transfer.** Today such a float has four places: the member, its slider, its line in `applyPreset`, and its
use. After section 6 it has three: the member, one row, and its use; the row's `field` stays null, since nothing
packs it. Until then the `applyPreset` line stays beside the row, and section 6 makes it a flag on the row. It
stays on paper because the supplied test lists the 34 members.

</details>

### A row of any kind

A row named its setting with one pointer. The particles need one for each kind of member a control edits, an `int`,
a `bool`, four floats, or a function that draws several values, and exactly one is set: that is the row's **kind**,
and it says which guarded call draws the row. A combo is an int row with labels, `items`. A `note` is the grey
`ImGui::TextDisabled` line the panel typed under four of its controls.

> **Jump:** two declarations you may not have written. `float (Settings::* color)[4]` reads from the name outwards:
> `color` points at a member of `Settings` that is an array of four floats, as `startColor` is.
> `settings.*row.color` is that array, which passes to a `float*` as `settings.startColor` did.
> `void (*editor)(Settings&)` is a plain function pointer. A function's address is a constant the linker fills in,
> so `&editCurves` can sit in a `constexpr` table that a `static_assert` checks, while the function is defined in
> another file, which must give it a name other files see: the editors are declared in the header and are not
> `static`.

**`SettingRows.h`.** Ten edits, from the top down. Replace the line
`/// @brief  A setting as a row: its name, the member that holds it, where packing copies it and how the panel draws it`
with these two, which name what a row holds by the end of section 6:

```cpp
/// @brief  A setting as a row: its name, the member that holds it, where packing copies it, how the panel draws it, and
///         whether a preset keeps it
```

Replace the line `struct SettingRange { float min, max; };` with:

```cpp
struct SettingRange { float min, max; };   // an int row's ends too: whole numbers below 2^24 are exact in a float
```

Four of the rows' sliders are logarithmic (Rate, the two sizes and Max particles). Replace the line
`// finite value may leave (the guarded slider still puts back a NaN or an infinity).` with these two:

```cpp
// finite value may leave (the guarded slider still puts back a NaN or an infinity). SETTING_LOGARITHMIC is
// ImGuiSliderFlags_Logarithmic.
```

and the line `    SETTING_HOLDS = 1 << 0,` with these two:

```cpp
    SETTING_HOLDS       = 1 << 0,
    SETTING_LOGARITHMIC = 1 << 1,
```

The emission settings pack into no block, and `NoBlock` is the empty struct their table names: `float NoBlock::*`
is a valid type with nothing to point at. Replace the two comment lines from
`// One setting: the float member that holds it, where packing copies it, and how the panel shows it. Group is the table's`
through `// own enum of the calls that draw it, so a group from another table's enum does not compile.` with these:

```cpp
struct NoBlock {};   // the Block of a table nothing packs straight into a GPU block

// One setting: the one member that holds it (which one says how the panel draws it), where packing copies it, and how
// the panel shows it. Exactly one of member, integer, toggle, color and editor is set. Group is the table's own enum of
// the calls that draw it, so a group from another table's enum does not compile.
```

Replace the line
`    const char*       name;                  // the member's own name: the key of --grass-response and the log line, and the tests'`
with these two:

```cpp
    const char*       name;                  // the member's own name: the key of --grass-response and the log line for the grass,
                                             // and the tests' for every table
```

and the line
`    int               decimals = -1;         // a float slider's "%.<decimals>f" and the log line's: 0 to 3` with:

```cpp
    int               decimals = -1;         // a float slider's "%.<decimals>f" and the log line's: 0 to 3; -1, unset, on every other kind
```

The kinds go at the end of the struct, directly under the line
`    int               flags    = 0;          // SettingFlags`. Designators follow the members' order and the
grass's rows name `name` through `flags`, so appended members leave every grass row as it was:

```cpp
    int  Settings::*  integer    = nullptr;  // an int: a slider over range, or a combo over items
    const char* const* items     = nullptr;  // a combo's labels
    int               itemCount  = 0;
    bool Settings::*  toggle     = nullptr;  // a checkbox
    float (Settings::* color)[4] = nullptr;  // a colour editor, rgba
    void (*editor)(Settings&)    = nullptr;  // several values with one editor (bursts, curves): this function draws them
    const char*       note       = nullptr;  // grey text under the control
```

**The validator.** A second kind, decimals on a checkbox, a range on a combo or a count with no labels would each
be dropped without a word, so each is refused at compile time, and each rule's reason is its comment line. Section
3's "a member" becomes "exactly one kind", and its label rule makes room for an editor, which draws its own labels.
Replace the four comment lines from
`//  - a member, because the member is what the panel draws and packing copies;` through
`//  - a label, which is the widget's id and its text.` with these twelve; the last is section 3's range rule:

```cpp
//  - exactly one kind, because the kind is how the panel draws the row;
//  - items only with an integer (they are its labels), and then at least one, or the combo is empty; a count only with items,
//    or it would be dropped silently;
//  - a float row's decimals are 0 to 3 (the panel indexes a four-entry format table, and a negative precision throws in the
//    log line); every other kind leaves them at -1, or they would be dropped silently;
//  - a range only on a slider (a float row, or an int row without items), or it would be dropped silently;
//  - a field only with a member (packing copies floats);
//  - HOLDS and LOGARITHMIC only on a slider (a checkbox, colour, combo or editor has no range to hold or to scale);
//  - a label on every kind but an editor, and none on an editor (the label is the widget's id, and an editor draws its own
//    labels);
//  - an int slider's ends are whole numbers (they are cut to ints);
//  - a range whose min is above its max breaks std::clamp.
```

Then replace the four lines from `        if (row.member == nullptr) { return false; }` through
`        if (row.label == nullptr) { return false; }` with these fourteen; the last is section 3's range check,
unchanged:

```cpp
        const int kinds = (row.member != nullptr ? 1 : 0) + (row.integer != nullptr ? 1 : 0) + (row.toggle != nullptr ? 1 : 0)
                        + (row.color != nullptr ? 1 : 0) + (row.editor != nullptr ? 1 : 0);
        if (kinds != 1) { return false; }
        if (row.items != nullptr ? (row.integer == nullptr || row.itemCount <= 0) : row.itemCount != 0) { return false; }
        if (row.member != nullptr ? (row.decimals < 0 || row.decimals > 3) : row.decimals != -1) { return false; }
        const bool slider = row.member != nullptr || (row.integer != nullptr && row.items == nullptr);
        if (!slider && (row.range.min != 0.0f || row.range.max != 0.0f)) { return false; }
        if (row.field != nullptr && row.member == nullptr) { return false; }
        if ((row.flags & (SETTING_HOLDS | SETTING_LOGARITHMIC)) != 0 && !slider) { return false; }
        if ((row.editor == nullptr) == (row.label == nullptr)) { return false; }
        if (row.integer != nullptr && row.items == nullptr
            && (row.range.min != static_cast<float>(static_cast<int>(row.range.min))
                || row.range.max != static_cast<float>(static_cast<int>(row.range.max)))) { return false; }
        if (row.range.min > row.range.max) { return false; }
```

The grass's rows meet every rule, so section 3's `static_assert` holds. `packSettingRows` does not change: it skips
a row without both a `member` and a `field`, which is every row of another kind.

### The particles' tables

**`ParticlesDemo.h`.** Seven edits, from the top down. Add this directly above the line
`#include "PillowFort/Demos/Demo.h"`:

```cpp
#include "PillowFort/DebugPanels/SettingRows.h"
```

The combo rows count their labels with `std::size`. Add this directly under the line `#include <cstdint>`:

```cpp
#include <iterator>
```

Replace the two comment lines from
`// The shape and look combos' labels, indexed by EMITTER_SHAPE_* and LOOK_*. ParticlesDemo.cpp asserts that each has an`
through
`// entry for every shape and look: this header stays free of EmitterShapes.h, whose macros are the shaders' own.`
with these three:

```cpp
// The shape, look and blending combos' labels, indexed by EMITTER_SHAPE_*, LOOK_* and the blend setting (0 additive,
// 1 premultiplied alpha). ParticlesDemo.cpp asserts that the first two have an entry for every shape and look: the header
// stays free of EmitterShapes.h, whose macros and using-declarations are the shaders' own.
```

The panel drew Blending from one string, `"Additive\0Premultiplied alpha\0"`. A row's `items` is an array, so
Blending's labels become one, asserted against the setting's two modes. Add these directly under the line
`inline constexpr const char* LOOK_LABELS[] = { "Chapter 21", "Curves" };`:

```cpp
inline constexpr const char* BLEND_LABELS[] = { "Additive", "Premultiplied alpha" };
static_assert(std::size(BLEND_LABELS) == 2);
```

The tables point at the two editors, which `ParticlesDemo.cpp` defines later in this section, and name the groups,
each table's own enum. Add these directly under the line `static_assert(std::size(BLEND_LABELS) == 2);`, after one
blank line:

```cpp
// The panel's editors for what one row cannot hold: the bursts, and the curves' keys.
void editBursts(EmissionSettings& emission);
void editCurves(ParticleSettings& settings);

// Which call of drawParticleSettings draws a row.
enum ParticleGroup : int
{
    PARTICLE_SORT, PARTICLE_SHAPE, PARTICLE_EMITTER, PARTICLE_PREWARM, PARTICLE_FORCES, PARTICLE_WIND_ON, PARTICLE_WIND,
    PARTICLE_LOOK, PARTICLE_LOOK_21, PARTICLE_LOOK_CURVES, PARTICLE_SOFT, PARTICLE_CURVES, PARTICLE_POOL_SIZE, PARTICLE_POOL,
};
enum EmissionGroup : int { EMISSION_CLOCK, EMISSION_BURSTS };
```

**A group is a run, not a category:** the rows one `drawSettingRows` call draws. A run ends wherever a hand line, a
condition or a header falls between two controls. `PARTICLE_SORT` is Sort alone, the warning and Check order
following it; `PARTICLE_SHAPE`, `PARTICLE_EMITTER` and `PARTICLE_FORCES` are each a header's whole body. Emission
draws `EMISSION_CLOCK`, `PARTICLE_PREWARM` from the other table, then by hand Play, Stop, the effect time, the
bursts fired and the bursts' sentence, then `EMISSION_BURSTS`. `PARTICLE_WIND_ON` is the wind's checkbox, then the
sources' count, then `PARTICLE_WIND`, then the emit buttons, Clear and two grey lines. `PARTICLE_LOOK_21` and
`PARTICLE_LOOK_CURVES` sit inside the two `if`s on the look, between `PARTICLE_LOOK` and `PARTICLE_SOFT`;
`PARTICLE_CURVES` is under the Curves header, which only the curves look shows. `PARTICLE_POOL_SIZE` is Max
particles, whose change resets the pool, and `PARTICLE_POOL` is Paused, whose change does not; Reset follows. That
is 14 groups and 2; each needs a row, or section 4's assertion fires in Debug.

The row macros go directly under the line `enum EmissionGroup : int { EMISSION_CLOCK, EMISSION_BURSTS };`, after
one blank line: one per kind, and two for a float. `PF_STRAIGHT_ROW` names the field with the same token, so it
cannot pack into a field of another name. The range is two arguments, because a braced `{ 0.0f, 5.0f }` would split
at its comma. `PF_TOGGLE_ROW` takes no `FLAGS`, since no flag means anything for a checkbox yet; section 6 adds it.
`PF_EDITOR_ROW` holds a function, so it names the member left of a comma, where a misspelling fails to compile:

```cpp
// One row of each kind. The name always comes from the member (#M), so a row cannot name one member and hold another. A
// straight row's field is the GPU block's member of the same name (S: the settings, B: the block).
#define PF_STRAIGHT_ROW(S, B, M, LOW, HIGH, DECIMALS, LABEL, GROUP, FLAGS, NOTE) \
    { .name = #M, .member = &S::M, .field = &B::M, .range = { LOW, HIGH }, .decimals = DECIMALS, .label = LABEL, \
      .group = GROUP, .flags = FLAGS, .note = NOTE }
#define PF_FLOAT_ROW(S, M, LOW, HIGH, DECIMALS, LABEL, GROUP, FLAGS, NOTE) \
    { .name = #M, .member = &S::M, .range = { LOW, HIGH }, .decimals = DECIMALS, .label = LABEL, .group = GROUP, \
      .flags = FLAGS, .note = NOTE }
#define PF_INT_ROW(S, M, LOW, HIGH, LABEL, GROUP, FLAGS) \
    { .name = #M, .range = { LOW, HIGH }, .label = LABEL, .group = GROUP, .flags = FLAGS, .integer = &S::M }
#define PF_COMBO_ROW(S, M, ITEMS, LABEL, GROUP) \
    { .name = #M, .label = LABEL, .group = GROUP, .integer = &S::M, .items = ITEMS, .itemCount = static_cast<int>(std::size(ITEMS)) }
#define PF_TOGGLE_ROW(S, M, LABEL, GROUP, NOTE) \
    { .name = #M, .label = LABEL, .group = GROUP, .toggle = &S::M, .note = NOTE }
#define PF_COLOR_ROW(S, M, LABEL, GROUP) { .name = #M, .label = LABEL, .group = GROUP, .color = &S::M }
#define PF_EDITOR_ROW(S, M, EDITOR, GROUP) { .name = (static_cast<void>(&S::M), #M), .group = GROUP, .editor = EDITOR }
```

The two tables go directly under the line that starts `#define PF_EDITOR_ROW(S, M, EDITOR, GROUP)`, after one blank
line, and the macros end after them. The particles' 32 rows are in the panel's order, each with the range, label
and note of the line it replaces. A row's decimals come from its slider's format (`"%.0f"` is 0, and a slider that
named none used the default `"%.3f"`), and `ImGuiSliderFlags_AlwaysClamp` and `ImGuiSliderFlags_Logarithmic` become
`SETTING_HOLDS` and `SETTING_LOGARITHMIC`. The emission table's block is `NoBlock`:

```cpp
// ParticleSettings by row, in the panel's order: the member, the field of ParticleSimulation that packing copies it to
// (where the block holds it straight), its range, the control's label, the group that draws it and its flags.
inline constexpr auto PARTICLE_ROWS = std::to_array<pf::debug_panels::SettingRow<ParticleSettings, ParticleSimulation, ParticleGroup>>({
    PF_TOGGLE_ROW(ParticleSettings, sortBackToFront, "Sort back to front", PARTICLE_SORT, nullptr),
    PF_COMBO_ROW(ParticleSettings, shapeKind, SHAPE_LABELS, "Shape", PARTICLE_SHAPE),
    PF_FLOAT_ROW(ParticleSettings, shapeSize, 0.0f, 5.0f, 2, "Shape size (m)", PARTICLE_SHAPE, pf::debug_panels::SETTING_HOLDS,
                 "Radius, or a box's half-extent. A disc lies flat, across the cone's +Y axis."),
    PF_TOGGLE_ROW(ParticleSettings, launchOutward, "Launch outward", PARTICLE_SHAPE, nullptr),
    PF_FLOAT_ROW(ParticleSettings, emitRate, 0.0f, 100000.0f, 0, "Rate (per s)", PARTICLE_EMITTER,
                 pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_LOGARITHMIC, nullptr),
    PF_FLOAT_ROW(ParticleSettings, emitterHeight, 0.0f, 10.0f, 2, "Height (m)", PARTICLE_EMITTER, pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, speed, 0.0f, 30.0f, 3, "Speed (m/s)", PARTICLE_EMITTER, 0, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, speedVariation, 0.0f, 1.0f, 3, "Speed variation", PARTICLE_EMITTER, 0, nullptr),
    PF_FLOAT_ROW(ParticleSettings, spreadDegrees, 0.0f, 180.0f, 3, "Spread (deg)", PARTICLE_EMITTER, 0, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, lifetime, 0.1f, 10.0f, 3, "Lifetime (s)", PARTICLE_EMITTER, 0, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, lifetimeVariation, 0.0f, 1.0f, 3, "Lifetime variation", PARTICLE_EMITTER, 0, nullptr),
    PF_FLOAT_ROW(ParticleSettings, prewarmSeconds, 0.0f, MAX_PREWARM_SECONDS, 1, "Prewarm (s)", PARTICLE_PREWARM,
                 pf::debug_panels::SETTING_HOLDS, "After a reset, simulate this long before the first frame is drawn."),
    PF_FLOAT_ROW(ParticleSettings, gravity, -5.0f, 20.0f, 3, "Gravity (m/s2)", PARTICLE_FORCES, 0, nullptr),
    PF_FLOAT_ROW(ParticleSettings, drag, 0.0f, 5.0f, 3, "Drag (per s)", PARTICLE_FORCES, 0, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, restitution, 0.0f, 1.0f, 3, "Restitution", PARTICLE_FORCES, 0, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, friction, 0.0f, 1.0f, 3, "Friction", PARTICLE_FORCES, 0, nullptr),
    PF_TOGGLE_ROW(ParticleSettings, windEnabled, "Enable local wind", PARTICLE_WIND_ON, nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, windResponseRate, 0.0f, 10.0f, 2, "Wind response (per s)", PARTICLE_WIND,
                    pf::debug_panels::SETTING_HOLDS,
                    "Next source: radius, lifetime and drift apply when emitted."),
    PF_FLOAT_ROW(ParticleSettings, windRadius, 0.5f, 12.0f, 2, "Source radius (m)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_FLOAT_ROW(ParticleSettings, windLifetime, 0.5f, 20.0f, 2, "Source lifetime (s)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_FLOAT_ROW(ParticleSettings, windDrift, -2.0f, 2.0f, 2, "Source drift +X (m/s)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_COMBO_ROW(ParticleSettings, lookKind, LOOK_LABELS, "Look", PARTICLE_LOOK),
    PF_COLOR_ROW(ParticleSettings, startColor, "Start color", PARTICLE_LOOK_21),
    PF_COLOR_ROW(ParticleSettings, endColor, "End color", PARTICLE_LOOK_21),
    PF_FLOAT_ROW(ParticleSettings, startSize, 0.005f, 1.0f, 3, "Start size (m)", PARTICLE_LOOK_21, pf::debug_panels::SETTING_LOGARITHMIC, nullptr),
    PF_FLOAT_ROW(ParticleSettings, endSize, 0.005f, 1.0f, 3, "End size (m)", PARTICLE_LOOK_21, pf::debug_panels::SETTING_LOGARITHMIC, nullptr),
    // Chapter 21's look only: Curves blends premultiplied (Chapter 55), its glow adding.
    PF_COMBO_ROW(ParticleSettings, blend, BLEND_LABELS, "Blending", PARTICLE_LOOK_21),
    PF_TOGGLE_ROW(ParticleSettings, flipbook, "Flipbook", PARTICLE_LOOK_CURVES,
                  "Smoke puffs from an atlas baked at setup; off, Chapter 54's round card."),
    PF_FLOAT_ROW(ParticleSettings, softDistance, 0.0f, 1.0f, 2, "Soft intersection (m)", PARTICLE_SOFT,
                 pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_EDITOR_ROW(ParticleSettings, curves, &editCurves, PARTICLE_CURVES),
    // SETTING_HOLDS: the shaders index every pool buffer with this, so even a value typed with Ctrl+click must stay within
    // PARTICLE_CAPACITY, and at least 1 for the reset.
    PF_INT_ROW(ParticleSettings, maxParticles, 1024.0f, 1048576.0f, "Max particles", PARTICLE_POOL_SIZE,
               pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_LOGARITHMIC),
    PF_TOGGLE_ROW(ParticleSettings, paused, "Paused", PARTICLE_POOL, nullptr),
});
static_assert(pf::debug_panels::settingRowsValid(PARTICLE_ROWS));

// EmissionSettings by row: the clock, and the bursts' editor.
inline constexpr auto EMISSION_ROWS = std::to_array<pf::debug_panels::SettingRow<EmissionSettings, pf::debug_panels::NoBlock, EmissionGroup>>({
    PF_FLOAT_ROW(EmissionSettings, duration, 0.1f, 30.0f, 2, "Duration (s)", EMISSION_CLOCK, pf::debug_panels::SETTING_HOLDS, nullptr),
    PF_TOGGLE_ROW(EmissionSettings, looping, "Looping", EMISSION_CLOCK, nullptr),
    PF_EDITOR_ROW(EmissionSettings, bursts, &editBursts, EMISSION_BURSTS),
});
static_assert(pf::debug_panels::settingRowsValid(EMISSION_ROWS));
#undef PF_STRAIGHT_ROW
#undef PF_FLOAT_ROW
#undef PF_INT_ROW
#undef PF_COMBO_ROW
#undef PF_TOGGLE_ROW
#undef PF_COLOR_ROW
#undef PF_EDITOR_ROW
```

**Build.** Nothing calls the editors, and nothing reads the tables while the program runs, so this build checks
that they compile: 0 warnings, both `static_assert`s holding. No file is new, so there is nothing to generate;
build `SandboxGame` alone:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
```

### Packing walks the rows

**`ParticlesDemo.cpp`.** The seven `PF_STRAIGHT_ROW`s are the seven floats `packSimulation` copied by hand, so the
walk writes them now. Replace the whole of `packSimulation`, from the line
`ParticleSimulation packSimulation(const ParticleSettings& settings, const ParticleStep& step)` through the `}`
that ends it, with:

```cpp
ParticleSimulation packSimulation(const ParticleSettings& settings, const ParticleStep& step)
{
    const float spread = glm::radians(settings.spreadDegrees);
    ParticleSimulation simulation{
        .emitterPosition   = glm::vec4(0.0f, settings.emitterHeight, 0.0f,
                                                  (static_cast<uint32_t>(settings.shapeKind) & EMITTER_SHAPE_KIND_MASK) == EMITTER_SHAPE_POINT ? 0.0f : settings.shapeSize),
        .gravity           = glm::vec4(0.0f, -settings.gravity, 0.0f, settings.drag),
        .deltaTime         = step.deltaTime,
        .spreadAngle       = spread,
        .groundHeight      = 0.0f,
        .emitRequest       = step.emitRequest,
        .frameNumber       = step.frameNumber,
        .currentList       = step.currentList,
        .maxParticles      = static_cast<uint32_t>(settings.maxParticles),
        .windSourceCount   = settings.windEnabled ? step.windSources : 0u,
        .emitterShape      = (static_cast<uint32_t>(settings.shapeKind) & EMITTER_SHAPE_KIND_MASK)
                           | (settings.launchOutward ? EMITTER_SHAPE_LAUNCH_OUTWARD : 0u),
    };
    // The seven straight fields come from the rows. `false`: no clamp, because the particles never clamped at packing; their
    // sliders and Record's guards decide what is held.
    debug_panels::packSettingRows(PARTICLE_ROWS, settings, simulation, false);
    return simulation;
}
```

The seven fields left out of the initializer start at zero, and the walk writes each. The radians, the pool size's
conversion, the wind's condition and the shape word are not copies, and the four lanes cannot be a row's: a `field`
is a `float Block::*`, and `gravity.w` is a member of a member.

The walk passes `false`, because the particles never clamped at packing. **What the particles' rows keep, as
today:** ten float rows hold a typed value in range: shape size, rate, height, prewarm, the wind response rate, the
source's radius, lifetime and drift, the soft distance, and the duration. Eleven take any finite typed value,
`1e30` included: speed, speed variation, spread, lifetime, lifetime variation, gravity, drag, restitution,
friction, and the two sizes. A free value is packed as typed; `Record` refuses a bad rate, prewarm or pool size,
and `WriteWindSources` a bad wind response.

Do not build yet: the program now reads the table at run time, and the table holds the editors' addresses, which
the next step defines.

### The two editors move out of the panel

Each of Chapter 54's two editor blocks becomes a function, unchanged, which the panel calls where the block was.
Each is printed first as a shell that the move fills. Add this one directly above the line
`// The panel's settings from "Sort back to front" to the end of "Pool", a function so a test can draw them. True when`,
with a blank line between. Its parameter is named `emission`, like the panel's reference, so the lines need no
edit:

```cpp
// The bursts' editor: each slot's time and count. Chapter 54.
void editBursts(EmissionSettings& emission)
{
}
```

**Move.** In `ParticlesDemo.cpp`, cut the 13 lines from the line
`        for (int i = 0; i < EmissionSettings::MAX_BURSTS; ++i)` through the line `        }`, inclusive; the line
after them is `    }`, then a blank line, and then `    if (ImGui::CollapsingHeader("Forces"))`. Paste them,
dedented by 4 spaces, between the braces of the function printed above. In their place type:

```cpp
        editBursts(settings.emission);
```

The curves' shell goes directly above the same line,
`// The panel's settings from "Sort back to front" to the end of "Pool", a function so a test can draw them. True when`,
with a blank line between, so it lands under `editBursts`. Its comment takes the panel's sentence about life:

```cpp
// The Curves look's keys (Chapter 54): life 0 is birth and 1 the end of a particle's life.
void editCurves(ParticleSettings& settings)
{
}
```

**Move.** In `ParticlesDemo.cpp`, cut the 13 lines from the line
`        drawKeys("Color", settings.curves.color, [](GradientKey& key) {` through the line
`        drawCurve("Coverage", "Coverage", settings.curves.coverage, MAX_PARTICLE_COVERAGE);   // Chapter 55`,
inclusive; the line after them is `    }`. Paste them, dedented by 4 spaces, between the braces of the function
printed above. In their place type:

```cpp
        editCurves(settings);
```

Then replace the line
`    // Chapter 54: the Curves look's keys. Life 0 is birth and 1 the end of a particle's life.` with:

```cpp
    // Chapter 54: the Curves look's keys.
```

### Checkpoint: packing walks the rows

No file is new, so there is nothing to generate. Build the game and the test, and run the test from the repository
root:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialSettingRowsTests\TutorialSettingRowsTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialSettingRowsTests failed.' }
```

The build has 0 warnings. The test is still at stage 1 and prints section 4's report, line for line, ending:

```text
PASS: settings rows, stage 1 (2080 checks)
```

Two of its lines now say more: `packSimulation against the copy` compares the walk with your copy's
`packSimulation`, and `drawParticleSettings against the copy` compares a panel that calls the editors with your
copy's, which draws them inline. Nothing draws the particles' rows yet.

### Drawing every kind

**`DemoPanel.h`.** Two edits. Each kind goes through a `debug_panels` function, not ImGui's own: `sliderFloat` and
`colorEdit4`, the guarded ones of [Chapter 9, section 6](09-Demo-Harness.md#6-the-triangle-becomes-a-demo), or
`combo`, `sliderInt` and `checkbox`, the wrappers that Chapters 54 and 55 call, which set the widget's id and place
its label. A combo is an int row with items, so `items` is tested before `integer`, and a note follows any kind. An
editor returns nothing, so its changes are not counted, as the panel never counted them; the test checks that its
group returns false even when it changes a value. Replace the three comment lines above `drawSettingRows`'
`template` line, the last of which is `// no row is a mistake in the caller.`, with:

```cpp
// Draws each row of `group`, in table order, with the guarded call its kind needs, then its note. Returns whether a slider,
// combo, checkbox or colour changed; an editor's own changes are not counted. A group that draws no row is a mistake in
// the caller.
```

Then replace the line
`        changed |= sliderFloat(row.label, &(settings.*row.member), row.range.min, row.range.max, FORMAT[row.decimals], flags);`
with these eight; the second is that line, now behind `if (row.member)`:

```cpp
        if ((row.flags & SETTING_LOGARITHMIC) != 0) { flags |= ImGuiSliderFlags_Logarithmic; }
        if (row.member)       { changed |= sliderFloat(row.label, &(settings.*row.member), row.range.min, row.range.max, FORMAT[row.decimals], flags); }
        else if (row.items)   { changed |= combo(row.label, &(settings.*row.integer), row.items, row.itemCount); }
        else if (row.integer) { changed |= sliderInt(row.label, &(settings.*row.integer), static_cast<int>(row.range.min), static_cast<int>(row.range.max), "%d", flags); }
        else if (row.toggle)  { changed |= checkbox(row.label, &(settings.*row.toggle)); }
        else if (row.color)   { changed |= colorEdit4(row.label, settings.*row.color); }
        else if (row.editor)  { row.editor(settings); }
        if (row.note)         { ImGui::TextDisabled("%s", row.note); }
```

### The particles' panel from the rows

Replace `drawParticleSettings` whole: from its first line,
`bool drawParticleSettings(ParticleSettings& settings, EmissionSchedule& schedule, WindSources& wind,`, through the
`}` that ends it, which a blank line and the line
`// Section 7. Edits the settings and shows what came back from the GPU. True when` follow. It becomes:

```cpp
bool drawParticleSettings(ParticleSettings& settings, EmissionSchedule& schedule, WindSources& wind,
                          bool& checkOrder, const std::string& orderVerdict)
{
    using pf::debug_panels::drawSettingRows;
    bool reset = false;
    // Chapter 55, section 3. Unsorted covering particles are shown only as the problem, and say so.
    drawSettingRows(PARTICLE_ROWS, PARTICLE_SORT, settings);
    if (!settings.sortBackToFront && coversAnything(settings))
    {
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.75f, 0.2f, 1.0f));
        ImGui::TextWrapped("Sort is off: these particles cover, so they flicker where they overlap. This is the order problem, not the look.");
        ImGui::PopStyleColor();
    }
    // Chapter 55, section 4: checks the next sorted frame's order from the GPU's own keys.
    if (settings.sortBackToFront && ImGui::Button("Check order")) { checkOrder = true; }
    if (!orderVerdict.empty()) { ImGui::TextWrapped("%s", orderVerdict.c_str()); }

    // The counts stay in view; each group of controls folds away under its name (Chapter 09 section 6).
    if (ImGui::CollapsingHeader("Shape"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_SHAPE, settings);
    }

    if (ImGui::CollapsingHeader("Emitter"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_EMITTER, settings);
    }

    if (ImGui::CollapsingHeader("Emission"))
    {
        EmissionSettings& emission = settings.emission;
        drawSettingRows(EMISSION_ROWS, EMISSION_CLOCK, emission);
        drawSettingRows(PARTICLE_ROWS, PARTICLE_PREWARM, settings);
        if (ImGui::Button("Play")) { schedule.Play(); }
        ImGui::SameLine();
        if (ImGui::Button("Stop")) { schedule.Stop(); }
        ImGui::Text("Effect time %.2f s  (%s)", schedule.Time(emission),
                    schedule.IsFinished() ? "finished" : schedule.IsPlaying() ? "playing" : "stopped");
        ImGui::Text("Bursts fired %llu", static_cast<unsigned long long>(schedule.BurstsFired()));
        ImGui::TextDisabled("A burst is a time on the clock and a count; zero is unused.");
        drawSettingRows(EMISSION_ROWS, EMISSION_BURSTS, emission);
    }

    if (ImGui::CollapsingHeader("Forces"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_FORCES, settings);
    }

    if (ImGui::CollapsingHeader("Local wind (Chapter 52)"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_WIND_ON, settings);
        ImGui::Text("Invisible sources: %u / %u", wind.Count(), uint32_t(PARTICLE_WIND_CAPACITY));
        drawSettingRows(PARTICLE_ROWS, PARTICLE_WIND, settings);
        const auto emit = [&](int shape) {
            WindSourceDescription source;
            source.radius = settings.windRadius;
            source.lifetime = settings.windLifetime;
            source.driftVelocity.x = settings.windDrift;
            if (shape == 0) { source.angularSpeed = 3.0f; source.linearVelocity.y = 1.0f; }
            if (shape == 1) { source.linearVelocity = {7.0f, 1.0f, 0.0f}; }
            if (shape == 2) { source.radialSpeed = 10.0f; }
            if (wind.Emit(source)) { settings.windEnabled = true; }
        };
        if (ImGui::Button("Emit swirl")) { emit(0); }
        ImGui::SameLine();
        if (ImGui::Button("Emit gust")) { emit(1); }
        ImGui::SameLine();
        if (ImGui::Button("Emit blast")) { emit(2); }
        if (ImGui::Button("Clear wind sources")) { wind.Clear(); }
        ImGui::TextDisabled("Emit near the fountain at (0, 2, 0). Sources drift and fade.");
        ImGui::TextDisabled("At 16 sources, wait for one to fade or clear them before emitting.");
    }

    if (ImGui::CollapsingHeader("Look"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_LOOK, settings);
        if (settings.lookKind == LOOK_CHAPTER_21)
        {
            // Chapter 21's look: two colours, two sizes and its blending.
            drawSettingRows(PARTICLE_ROWS, PARTICLE_LOOK_21, settings);
        }
        if (settings.lookKind == LOOK_CURVES)   // Chapter 55, section 5
        {
            drawSettingRows(PARTICLE_ROWS, PARTICLE_LOOK_CURVES, settings);
        }
        drawSettingRows(PARTICLE_ROWS, PARTICLE_SOFT, settings);
    }

    // Chapter 54: the Curves look's keys.
    if (settings.lookKind == LOOK_CURVES && ImGui::CollapsingHeader("Curves"))
    {
        drawSettingRows(PARTICLE_ROWS, PARTICLE_CURVES, settings);
    }

    if (ImGui::CollapsingHeader("Pool"))
    {
        // The size's reset; its row holds a typed value (the reason is on the row).
        reset |= drawSettingRows(PARTICLE_ROWS, PARTICLE_POOL_SIZE, settings);
        drawSettingRows(PARTICLE_ROWS, PARTICLE_POOL, settings);
        reset |= ImGui::Button("Reset");
    }

    return reset;
}
```

The new lines are the `using` line, one `drawSettingRows` call per run and two comments; the rest is yours
unchanged, and the reset still comes only from Max particles and Reset.

### Checkpoint

Raise the test to stage 2. In `SettingRowsTests.cpp`, replace the line that starts
`#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 2   // raised in sections 3, 5 and 6 of the lesson, and in section 1 of Chapter 56
```

No file is new, so there is nothing to generate. Build the game and six tests, and run each from the repository
root; `TutorialMirrorBatchTests` checks the simulation push at the defaults, which now comes through the walk:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests;TutorialMirrorBatchTests;TutorialDeclaredFrameTests;TutorialParticleEffectTests;TutorialParticleSmokeTests;TutorialUiScaleTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
foreach ($test in 'TutorialSettingRowsTests', 'TutorialMirrorBatchTests', 'TutorialDeclaredFrameTests', 'TutorialParticleEffectTests', 'TutorialParticleSmokeTests', 'TutorialUiScaleTests')
{
    & ".\Build\Artifacts\Debug\$test\$test.exe"
    if ($LASTEXITCODE -ne 0) { throw "$test failed." }
}
```

The build has 0 warnings. `TutorialSettingRowsTests` gains a third line and, before its last, seventeen more; the
third and the last are:

```text
PASS: the lesson's 34 settings members
PASS: settings rows, stage 2 (2141 checks)
```

The seventeen check both tables valid, the two structs' sizes, each member drawn by exactly one row (none for
`preset` or `emission`), the emission rows, the seven straight fields each written by one row of its name,
`drawSettingRows`' result for each kind, and `packSettingRows` with its clamp and without. The comparisons with
your copy now run against the panel the rows draw. The other five pass, `TutorialDeclaredFrameTests` ending
`PASS: toy, Life, Particles, sort, curves` as in Chapter 57. Then a short run in Debug:

```powershell
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Particles
```

The fountain starts. Open each header: the controls, their order and their values are those of section 2's run.
Pick Firework, then Smoke, from **Preset**: each looks and moves as before, with Flipbook under Look and the Curves
header shown.

If a particle case fails, [section 2's rules](#when-stage-0-fails), the Pool group's guarded calls among them, and
[section 3's for the rows](#which-side-wins-for-the-rows) say which side to fix. A particle row's range is a
literal in both your copy and your row, so, unlike a grass range, it can differ.

### A control: Max particles on a linear track

Predict first. Max particles' row says `SETTING_LOGARITHMIC`, as its slider did. Take the flag off and build. Does
the validator refuse the row? Which comparisons fail: packing, typed input, or the panel's draw lists? What does
the failure name?

A mistake to try and put back: in `ParticlesDemo.h`, change Max particles' second line,
`               pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_LOGARITHMIC),`, to:

```cpp
               pf::debug_panels::SETTING_HOLDS),
```

The answer, as the reference measured it: 0 warnings, since a held int slider with no scale is a valid row, and the
test fails 33 of its 2141 checks. Packing, typed input, the checkboxes and the colours pass: the flag is not
packed, and it changes how the track maps to values, not what a typed value becomes. The panel's draw lists differ
in 33 of its 44 cases: the logged label and value are the same, the slider's grab sits elsewhere on the track, and
the message names the first vertex that differs and the widget that holds it:

```text
FAIL: particle panel: drawParticleSettings against the copy (text, then draw list): case 'particles-default-look0': vertex 4832 differs (copy 371.400024,1306.000000, live 65.041061,1306.000000), in the widget 'Max particles'
FAIL: 33 of 2141 checks, stage 2
```

Only the comparison of what is drawn sees a scale. Put the flag back, rebuild, and the test passes again.

## 6. What a preset leaves alone, and where the line is

A preset is a look, not a session. `applyPreset`, from
[Chapter 54, section 2](54-Shaping-A-Particle-Effect.md#2-births-on-a-shape), which the panel's **Preset** combo
and `--particle-preset` both call, replaces your settings with a preset's and gives back what belongs to you, the
person at the panel. That second list is the last hand-written list of the particle settings, and the rows can hold
it: a flag on each row it names, and one walk.

**Predict first.** Open `applyPreset` in your `ParticlesDemo.cpp`, as Chapters 54 and 55 left it, and write three
answers before you read on. When you pick a preset, which of your settings survive it? Which setting is decided by
a line of its own, neither kept nor replaced? And which list does a setting you add tomorrow join if you write
nothing for it: the preset's, or yours?

The function starts from the preset's whole `ParticleSettings`, so everything is the preset's unless a line says
otherwise. Eight lines say otherwise: the soft distance, the pool size, **Paused**, and the five local-wind
settings of [Chapter 52, section 3](52-Wind-Fields-And-Vorticles.md#3-velocity-is-not-acceleration) are copied back
from yours. One line decides Sort on its own: a preset that covers turns it on, and one that only glows leaves it
as you had it ([Chapter 55, section 3](55-Sorted-Smoke.md#3-the-sort-on-the-gpu)). And `preset` is set to the index
you picked. So a setting you add tomorrow is the preset's, replaced by the preset's own value, until you add a
ninth line to a function far from the setting's row.

After this section the list is the rows'. A row flagged `SETTING_KEPT` is *kept*, and `keepSettingRows` copies the
kept rows back from your settings. Sort keeps its own line.

**`SettingRows.h`.** Five edits. The flag joins the other two. Replace the line `// ImGuiSliderFlags_Logarithmic.`,
the end of the comment above `enum SettingFlags`, with these two:

```cpp
// ImGuiSliderFlags_Logarithmic. SETTING_KEPT is no widget flag: keepSettingRows copies the row's value, so a preset leaves
// it as the person set it.
```

and add the flag directly under the line `    SETTING_LOGARITHMIC = 1 << 1,`:

```cpp
    SETTING_KEPT        = 1 << 2,
```

One kind can never be kept: an editor. Its row holds the function that draws its values and no pointer to the
values themselves, so a walk would have nothing to copy, and the flag would promise a keep that never happens. The
validator makes that a build error. Replace the last line of its list of reasons,
`//  - a range whose min is above its max breaks std::clamp.`, with these three:

```cpp
//  - a range whose min is above its max breaks std::clamp;
//  - an editor is never kept, because an editor row holds no pointer to its values, so there is nothing for
//    keepSettingRows to copy.
```

and add the rule directly under the line `        if (row.range.min > row.range.max) { return false; }`:

```cpp
        if ((row.flags & SETTING_KEPT) != 0 && row.editor != nullptr) { return false; }
```

The walk has `packSettingRows`' shape, from one `Settings` to another instead of into a block, and it reads every
kind it can copy: a float, an int (a slider or a combo), a checkbox and a colour. Add it at the end of the
namespace, directly above the line `} // namespace pf::debug_panels`, with a blank line between them:

```cpp
// Copies each SETTING_KEPT row from `from` to `to`: what a preset leaves as the person set it. The colour is copied
// channel by channel, because an array member cannot be assigned whole. An editor row is never kept (the validator refuses
// it), so this never meets one.
template <class Settings, class Block, class Group, std::size_t Count>
void keepSettingRows(const std::array<SettingRow<Settings, Block, Group>, Count>& rows, const Settings& from, Settings& to)
{
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if ((row.flags & SETTING_KEPT) == 0) { continue; }
        if (row.member != nullptr) { to.*(row.member) = from.*(row.member); }
        else if (row.integer != nullptr) { to.*(row.integer) = from.*(row.integer); }
        else if (row.toggle != nullptr) { to.*(row.toggle) = from.*(row.toggle); }
        else if (row.color != nullptr)
        {
            for (int channel = 0; channel < 4; ++channel) { (to.*(row.color))[channel] = (from.*(row.color))[channel]; }
        }
    }
}
```

**`ParticlesDemo.h`.** Two of the kept settings are checkboxes, **Paused** and **Enable local wind**, so the
toggle's macro gains the flags argument that the float and int macros already take. `.flags` goes between `.group`
and `.toggle` because designated initializers must name the members in `SettingRow`'s order. Replace the two lines
that start `#define PF_TOGGLE_ROW(S, M, LABEL, GROUP, NOTE) \` with:

```cpp
#define PF_TOGGLE_ROW(S, M, LABEL, GROUP, FLAGS, NOTE) \
    { .name = #M, .label = LABEL, .group = GROUP, .flags = FLAGS, .toggle = &S::M, .note = NOTE }
```

Every toggle row now passes a flag before its note, `SETTING_KEPT` or 0, and the table's comment says what the new
flag means. Replace the line
`// (where the block holds it straight), its range, the control's label, the group that draws it and its flags.`
with these two:

```cpp
// (where the block holds it straight), its range, the control's label, the group that draws it and its flags
// (SETTING_KEPT: a preset leaves it as you set it).
```

Sort is a toggle and is not kept: `applyPreset`'s own line decides it after the walk, and would overwrite whatever
a flag had kept. The row says so instead of carrying a flag that does nothing. Replace the line
`    PF_TOGGLE_ROW(ParticleSettings, sortBackToFront, "Sort back to front", PARTICLE_SORT, nullptr),` with these
two:

```cpp
    // Not kept: applyPreset's own line decides Sort.
    PF_TOGGLE_ROW(ParticleSettings, sortBackToFront, "Sort back to front", PARTICLE_SORT, 0, nullptr),
```

**Launch outward** is the preset's. Replace the line
`    PF_TOGGLE_ROW(ParticleSettings, launchOutward, "Launch outward", PARTICLE_SHAPE, nullptr),` with:

```cpp
    PF_TOGGLE_ROW(ParticleSettings, launchOutward, "Launch outward", PARTICLE_SHAPE, 0, nullptr),
```

The local wind belongs to whoever is blowing it, not to a look: its checkbox and its four sliders are kept, the
sliders with the flag beside `SETTING_HOLDS`. Replace the ten lines from the line
`    PF_TOGGLE_ROW(ParticleSettings, windEnabled, "Enable local wind", PARTICLE_WIND_ON, nullptr),` through
`windDrift`'s second line, `                 pf::debug_panels::SETTING_HOLDS, nullptr),`, the line directly above
`    PF_COMBO_ROW(ParticleSettings, lookKind, LOOK_LABELS, "Look", PARTICLE_LOOK),`, with these eleven. Each slider
row's first line is unchanged, and so is the wind response's note:

```cpp
    PF_TOGGLE_ROW(ParticleSettings, windEnabled, "Enable local wind", PARTICLE_WIND_ON, pf::debug_panels::SETTING_KEPT,
                  nullptr),
    PF_STRAIGHT_ROW(ParticleSettings, ParticleSimulation, windResponseRate, 0.0f, 10.0f, 2, "Wind response (per s)", PARTICLE_WIND,
                    pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_KEPT,
                    "Next source: radius, lifetime and drift apply when emitted."),
    PF_FLOAT_ROW(ParticleSettings, windRadius, 0.5f, 12.0f, 2, "Source radius (m)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_KEPT, nullptr),
    PF_FLOAT_ROW(ParticleSettings, windLifetime, 0.5f, 20.0f, 2, "Source lifetime (s)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_KEPT, nullptr),
    PF_FLOAT_ROW(ParticleSettings, windDrift, -2.0f, 2.0f, 2, "Source drift +X (m/s)", PARTICLE_WIND,
                 pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_KEPT, nullptr),
```

**Flipbook** is the preset's. Replace the line
`    PF_TOGGLE_ROW(ParticleSettings, flipbook, "Flipbook", PARTICLE_LOOK_CURVES,` with this one; the note under it
stays:

```cpp
    PF_TOGGLE_ROW(ParticleSettings, flipbook, "Flipbook", PARTICLE_LOOK_CURVES, 0,
```

The soft distance, the pool size and **Paused** are yours. Replace the soft distance's row, the two lines from the
line `    PF_FLOAT_ROW(ParticleSettings, softDistance, 0.0f, 1.0f, 2, "Soft intersection (m)", PARTICLE_SOFT,`,
with these two; the first is unchanged:

```cpp
    PF_FLOAT_ROW(ParticleSettings, softDistance, 0.0f, 1.0f, 2, "Soft intersection (m)", PARTICLE_SOFT,
                 pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_KEPT, nullptr),
```

then replace the line `               pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_LOGARITHMIC),`,
the end of `maxParticles`' row, with these two:

```cpp
               pf::debug_panels::SETTING_HOLDS | pf::debug_panels::SETTING_LOGARITHMIC |
               pf::debug_panels::SETTING_KEPT),
```

and replace the line `    PF_TOGGLE_ROW(ParticleSettings, paused, "Paused", PARTICLE_POOL, nullptr),` with:

```cpp
    PF_TOGGLE_ROW(ParticleSettings, paused, "Paused", PARTICLE_POOL, pf::debug_panels::SETTING_KEPT, nullptr),
```

Nothing in `EMISSION_ROWS` is kept, as your eight lines kept nothing of `emission`; `applyPreset` walks
`PARTICLE_ROWS` only. Replace the line
`    PF_TOGGLE_ROW(EmissionSettings, looping, "Looping", EMISSION_CLOCK, nullptr),` with:

```cpp
    PF_TOGGLE_ROW(EmissionSettings, looping, "Looping", EMISSION_CLOCK, 0, nullptr),
```

**`ParticlesDemo.cpp`.** The eight lines become one call. The index's line stays, because `preset` has no row
(section 5's one exception). Sort's line moves after the walk and reads the same values there: `coversAnything`
looks only at the look, the blend and the coverage curve, none of them kept, and `settings` is replaced only on the
last line. Replace the eighteen lines from the line
`// Replaces the settings a preset names, its prewarm included. Paused, the pool, the soft distance` through
`applyPreset`'s closing `}` (the line after them is blank, and the next is
`bool ParticlesDemo::SetPreset(std::string_view name)`) with:

```cpp
// Replaces the settings a preset names, its prewarm included. The rows marked SETTING_KEPT name what belongs to the
// person at the panel, not to a look. Chapter 55: a preset that covers arrives sorted; one that only glows leaves Sort as
// it was.
static void applyPreset(ParticleSettings& settings, int index)
{
    ParticleSettings applied = PRESETS[index].values;
    applied.preset = index;
    debug_panels::keepSettingRows(PARTICLE_ROWS, settings, applied);
    // Sort's own line, after the walk: a covering preset turns the sort on whatever the person had, so Sort is not a kept
    // row (a flag on it would be overwritten here).
    applied.sortBackToFront = coversAnything(applied) || settings.sortBackToFront;
    settings = applied;
}
```

**`SettingRowsTests.cpp`.** Replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 3   // raised in sections 3, 5 and 6 of the lesson, and in section 1 of Chapter 56
```

Stage 3 adds 20 checks, in four lines: no emission row is kept; exactly the eight rows above are kept, by name;
`keepSettingRows` copies a kept float, int, toggle and colour; and it leaves an unkept float alone. The presets'
comparison has run since stage 0: for each of the eight presets and each of eight starts, it calls `SetPreset` from
that start and compares every member with what the preset gives default settings, then your copy's
`keepWhatAPresetLeaves` run from the same start; and from each start, an unknown name must change nothing: 72
cases. Not every start can see a kept setting. No preset names any of the eight, so from the default start a kept
setting and the preset's default are the same value. The seven other starts do the work: two move all eight off
their defaults, one with Sort on and one with it off, and five are seeded.

### Checkpoint

No file is new, so there is nothing to generate. Build the game, the supplied test and eight other CPU tests, and
run the tests from the repository root:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialSettingRowsTests;TutorialMirrorBatchTests;TutorialGrassWindTests;TutorialDeclaredFrameTests;TutorialUiScaleTests;TutorialWorldWindTests;TutorialWorldWindTurnTests;TutorialParticleEffectTests;TutorialParticleSmokeTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
foreach ($test in 'TutorialSettingRowsTests', 'TutorialMirrorBatchTests', 'TutorialGrassWindTests', 'TutorialDeclaredFrameTests', 'TutorialUiScaleTests', 'TutorialWorldWindTests', 'TutorialWorldWindTurnTests', 'TutorialParticleEffectTests', 'TutorialParticleSmokeTests')
{
    & ".\Build\Artifacts\Debug\$test\$test.exe"
    if ($LASTEXITCODE -ne 0) { throw "$test failed." }
}
```

The build has 0 warnings. The supplied test prints section 5's report with four lines more before its last:

```text
PASS: no EMISSION_ROWS row is flagged SETTING_KEPT (nothing keeps emission rows)
PASS: kept rows: exactly the eight a preset leaves alone (17 cases)
PASS: keepSettingRows copies a kept float, int, toggle and colour
PASS: keepSettingRows leaves an unkept float alone
PASS: settings rows, stage 3 (2161 checks)
```

Above them, `PASS: presets: SetPreset against the copy's keepWhatAPresetLeaves (72 cases)` is unchanged: the walk
keeps what your eight lines kept. The eight other tests pass, ending as they did in sections 1 to 5.

### Control: a setting that stops being kept

Predict, then run. Take `SETTING_KEPT` off the source radius's row. Does it still build? Which of the test's checks
fail, and from which of the eight starts? From a start whose source radius is 7 m, what does each side hold after
the fountain preset is applied?

This is a mistake to try and put back. In `windRadius`'s row, the second line becomes:

```cpp
                 pf::debug_panels::SETTING_HOLDS, nullptr),
```

Measured on the reference: it builds with 0 warnings, and the supplied test fails 58 checks, ending
`FAIL: 58 of 2160 checks, stage 3`. Fifty-six are the presets' comparison: every preset, from seven starts. The
first reads:

```text
FAIL: presets: SetPreset against the copy's keepWhatAPresetLeaves: preset 'fountain' from start 'kept-sort-on': member windRadius: copy 0x40e00000 (7), live 0x40a00000 (5)
```

Eleven more like it follow, then
`FAIL: presets: SetPreset against the copy's keepWhatAPresetLeaves: and 44 more of 72 cases`. Your copy kept the
start's 7 m; the rows no longer keep it, so the preset's 5 m, the struct's default, replaced it. The default start
passes for every preset, for the reason above: both sides hold 5 there. The other two failures are stage 3's own:

```text
FAIL: kept rows: exactly the eight a preset leaves alone: eight rows are kept: 7 rows are kept
FAIL: kept rows: exactly the eight a preset leaves alone: row windRadius is kept: windRadius is not marked SETTING_KEPT
```

The total is 2160, one fewer than 2161, because that check has one case for each kept row it finds. Only the
supplied test was run for this control. Put the flag back, rebuild, and the test passes again.

### Places, counted honestly

What the rows change is the number of places: how many you edit for one change, and how far apart they sit. On your
tree now:

| Change | Before the lesson | After |
| --- | --- | --- |
| Add a grass wind setting | 7: member, field, constant, table row, pack line, slider, and the table's size assert (Chapter 53 counts six) | 4: member, field, row, and the table's size assert; a fifth, a constant, only if you want one; and, while the supplied test is in, its `GRASS_WIND` list. A literal range in the macro must be a named constant or wrapped in parentheses: `{ 0.0f, 5.0f }` splits into two macro arguments |
| Tune a grass range | 1: the constant | 1: the constant (the copy names it too) |
| Change a grass label | 1: the slider | 1: the row, and, while the copy is in, the copy's slider too, or its comparison fails |
| Tune a particle range or change its label | 1: the slider | 1: the row, and while the copy is in, the copy's literal too |
| Add a particle float straight to the GPU | 4: member, field, slider, pack line, plus a preset line where a preset differs | 3: member, field, row, plus the same preset line, and, while the supplied test is in, its `PARTICLE_NAMES` list |
| Add a particle setting a preset leaves alone | the above plus a line in `applyPreset` | the row with `SETTING_KEPT` |
| Add a particle checkbox, combo or colour | member, widget, its use | member, row, its use, and the test's list while it is in |
| Start a new run between hand lines | the widgets where they go | plus a group value and a `drawSettingRows` call |

While the copy is in, each such change also edits the copy's pack line or slider and the test's counts of 32 and
34; whoever changes these settings retires the copy first, as [section 2](#the-copy) says.

In both columns you also edit, when the change touches them, each block's size assert and padding
(`GrassParameters` 720 bytes; `ParticleSimulation` 96 with no free word), `MirrorBatchTests`' 96-byte literal, the
GLSL header, and `GrassWindTests`' two hand lists (the bounds and the pinned line) when a grass setting is added.

As the macros stand, a kept row is a float, an int slider or a checkbox: their macros take flags, and the combo's
and the colour's do not yet. The rows save places, not lines: across the engine the lesson adds 628 lines and
removes 358, 270 more than before.

### Where the line is

Not everything became a row. What stays typed, and why:

- **Converted packing and the lanes.** A row's `field` copies one float unchanged into one `float` of the block.
  The sRGB colours, the radians, the sizes and the flipbook word are converted or go into another block, and a
  `float Block::*` cannot name one lane of a `vec4`: drag goes into `gravity.w` and the shape's size into
  `emitterPosition.w`. Each stays a typed line in `packSimulation`, `packAppearance` or `packFragmentWords`;
  section 7 finds where `gravity.w` sits.
- **The editors' insides, the conditions, the picker and the struct.** The bursts and the curves keep their keys
  and repairs, and Look's two branches and the Curves header stay `if`s around a group. `preset` has no row:
  picking one applies it whole, frames the camera and resets the pool, an action a `void(Settings&)` editor cannot
  return. The rows point into `ParticleSettings` and do not declare it, and `PRESETS` still lists only what differs
  from it.
- **The counters and the buttons.** Play and Stop, the sources' count, the emit buttons, the sort warning, Check
  order, Reset and Far highlight's disabled block are hand lines between the runs.

The Grass demo's other sliders and the other demos' panels stay hand-written: they hold more than eighty float
sliders, fewer than half of which go straight to a GPU field, so the field, the part of a row that closed section
1's hole, would be empty for most.

### If you read Chapter 45

[Chapter 45, section 2](45-Scene-Documents-And-Properties.md#2-bind-a-name-to-a-real-member) had the same idea: its
`PropertyBinding` binds a key to a member once, through a pointer to member, and every read and write goes through
that binding. Its job is different: it serves documents and editor commands, and its inspector
([section 4](45-Scene-Documents-And-Properties.md#4-generate-controls-from-the-described-values)) picks a widget
from the value's type, with no range, format, group or GPU field. The sharpest difference is the name: Chapter 45
writes its keys out, so that renaming a C++ member does not rename a property that a document or a command already
uses, while the rows' names are stringized from the member, as Chapter 53's were, so renaming a grass member
renames its `--grass-response` key and changes the **Log values** line that `TutorialGrassWindTests` pins. The
reference also tried EnTT's reflection, and found it no better for either job, the settings or Chapter 45's
documents.

### Chapter 56

[Chapter 56](56-Everything-Bends.md), Everything Bends, is the first chapter after this page to change these settings. It
moves the grass's thirteen front settings into the world wind, so the moved settings get another struct and another
block, and four functions that walk the grass's table could not walk it unchanged: `findWindResponseSetting`,
`windResponseNames`, `applyWindResponse` and `windResponseLine`. Chapter 56 rewrites them. It also edits supplied
tests: Chapter 53's contiguity check, its 32-entry bounds, its count and its pinned line, and this page's
`GRASS_WIND` list (stage 1). Those edits keep the earlier stages working for a reader on `start`. A setting moved into
a lane of a `vec4` needs a named float field to stay a row, and one that reaches two blocks, a lane of `FrameData` and
the compute pass's block, has its second destination packed by hand beside the walk, since a row names one field. And as
the first chapter to change these settings, it retires your copy whole: it deletes `SettingsByHand.h` and sets
`PF_TEST_COPY` to 0. The reference tags the last commit that had the file, `checkpoints/settings-by-hand`, so that
anyone can see how the settings were written by hand; the tag marks that commit on the reference.

### What nothing catches

These pass every check on this page:

1. **The same slip twice.** The same mistake in your earlier code and in this page's row, when you follow the page.
   Your earlier chapters' own tests are the only independent check.
2. **The shader side.** A shader that reads the wrong field, or none.
3. **A second place left behind.** A designated line left beside the walk, or a stale initializer beside an unused
   pack function, writes the same bytes today and drifts later. The page printed `packWindResponse`,
   `packSimulation` and the region of `PackParameters` and `RecordStep` around each call, so you can see there is
   none.
4. **Call sites beyond the defaults.** `TutorialMirrorBatchTests` checks `Record`'s simulation push only at the
   defaults.
5. **Tooltips and combo popups.** Tooltips are shown only on hover. Combo popups are not driven, though each
   value's display is compared.
6. **The flag and the log line elsewhere.** Unchanged code, compared only at the defaults and the range ends.
7. **Padding.** A new `ParticleSettings` member that fits in another's padding.
8. **What the copy and the rows share,** compared only against itself: the range constants, the label arrays,
   `MAX_PREWARM_SECONDS`, `PRESETS`, the struct defaults, the block layouts, the guarded widgets and `std::clamp`.
9. **The editors' insides,** beyond the draw lists and typed input at keys 0 and 1.
10. **The empty-group assertion is Debug only.** In Release, a group left with no rows draws nothing.
11. **A grass row naming another setting's constant of equal value.**
12. **A validator rule written to fit its one negative example.** Most rules have a second negative example; a rule
    is only as wide as its examples.
13. **The test's limits.** It includes `ParticlesDemo.h` under `#define private public`, which works only because
    it calls no private member function. An interactive Debug run of the program still shows the CRT assertion
    dialog, since `Main.cpp` routes reports to stderr only with `--frames`.
14. **A wrong group of the right enum** compiles, and the panel checks catch it; **a held range freed** is seen
    only by typed input.
15. **Hand lines between the runs** (the buttons, counters and warnings listed above) are checked only by the panel
    comparison: the draw lists, and the buttons pressed in both.

# Part 2 — Read a SPIR-V module (section 7)

Part 1 made the host's side of the bytes hard to get wrong. The GPU idea's second sentence is about the other side:
the compiled module states what the shader expects, its sets, bindings, kinds, block offsets and push-constant
range, and this part reads one module with the SDK's own tools. You type no code.

## 7. What the end pass declares

The module is `ParticleEnd.comp`, the `end` pass that
[Chapter 57, section 7](57-The-Frame-Declared.md#7-particles-declared-and-the-first-rule-breaks) declared by hand
with two uses: `{ m_counters.buffer, uses::ComputeRead }` and `{ m_indirect.buffer, uses::ComputeWrite }`. Its
whole `main`, from `Shaders/Particles/ParticleEnd.comp.glsl`:

```text
void main()
{
    // Six vertices make one camera-facing quad; one instance per live particle.
    uint next = 1u - simulation.currentList;
    indirect.draw = DrawIndirectCommand(6u, counters.aliveCount[next], 0u, 0u);
}
```

It includes `ParticleBuffers.glsl`, which declares the particle set as every compute pass sees it: five storage
buffers at set 0, bindings 0 to 4, and one push block, `PushConstants`, holding a `ParticleSimulation`.

**Predict first.** Write your answers down; the section answers each of them.

1. Which bindings does `main` touch, and which will an optimized module, compiled with `-O`, drop?
2. `end` reads one member of the push block, `currentList`, but the module states the whole block. At which offset
   does it hold `speed`, the field one of your rows writes?
3. At which byte does `gravity.w` sit?
4. A C++ question, not a SPIR-V one: why can no row name `gravity.w`?
5. Where does the block's last member sit, and so how big is the push block?

### Compile it yourself

The build has already compiled this shader, but do not read its module. Debug compiles with `-g -O0`, and `-g`
embeds the text of all four source files with their absolute paths on your PC: the Debug module disassembles to 655
lines, most of them your GLSL. Compile it again with premake's Debug command, `-g` left out, into your temporary
folder, and disassemble it. From the repository root:

```powershell
& "$env:VULKAN_SDK\Bin\glslc.exe" -fshader-stage=compute --target-env=vulkan1.3 -O0 -I Shaders\Include Shaders\Particles\ParticleEnd.comp.glsl -o "$env:TEMP\ParticleEnd.spv"
& "$env:VULKAN_SDK\Bin\spirv-dis.exe" "$env:TEMP\ParticleEnd.spv" -o "$env:TEMP\ParticleEnd.spvasm"
```

Then the optimized module, with Release's `-O`:

```powershell
& "$env:VULKAN_SDK\Bin\glslc.exe" -fshader-stage=compute --target-env=vulkan1.3 -O -I Shaders\Include Shaders\Particles\ParticleEnd.comp.glsl -o "$env:TEMP\ParticleEnd.O.spv"
& "$env:VULKAN_SDK\Bin\spirv-dis.exe" "$env:TEMP\ParticleEnd.O.spv" -o "$env:TEMP\ParticleEnd.O.spvasm"
```

Both tools are in your SDK's `Bin` folder
([Chapter 1, section 1](01-Environment-And-Build.md#1-what-is-actually-in-your-sdk)). Open `ParticleEnd.spvasm` in
any editor: 200 lines, and the `-O` one 95. Every line quoted here is from SDK 1.4.363: `glslc --version` begins
`shaderc v2026.4` and `spirv-dis --version` `SPIRV-Tools v2026.4`. Another SDK may number its ids differently and
count other lines; the guide's 1.4.357 was not tried.

### A map of the 200 lines

| Lines | What |
| --- | --- |
| 1-13 | the header and the entry point |
| 14-77 | names: skim them |
| 78-136 | decorations |
| 137-184 | types, constants and the global variables |
| 185-200 | `main` |

**The header and the entry point.** `; Version: 1.6` is the SPIR-V version that `--target-env=vulkan1.3` asks for.
The entry point names the stage, the function and the module's interface, and the execution mode is the shader's
`local_size_x = 1`:

```text
               OpEntryPoint GLCompute %main "main" %_ %__0 %__1 %__2 %__3 %__4
               OpExecutionMode %main LocalSize 1 1 1
```

> **Jump:** an id and a decoration. Every type, constant, variable, function and computed value in a module has an
> id, a number; `; Bound: 62` in the header says every id here is below 62. `spirv-dis` prints an id by the name an
> `OpName` gives it, `%main` or `%ParticleSimulation`, or by its number, `%20`, when there is none. A decoration is
> a fact about an id, stated in an instruction of its own after the id is declared: `OpDecorate %__1 Binding 3`
> says the variable `%__1` is binding 3, and `OpMemberDecorate %ParticleSimulation 3 Offset 36` says member 3 of
> that struct starts 36 bytes in. The `layout(...)` qualifiers and std430 rules you wrote arrive as decorations,
> and the driver's compiler reads them, as you can.

**The names.** They are for people, and `-O` strips them all. Two things in them look wrong and are not. The first
is `OpName %_ ""` at line 37: `PushConstants` is a block with no instance name (`ParticleBuffers.glsl` declares
nothing between its closing brace and the `;`), so glslang names its variable with the empty string, and
`spirv-dis`, which needs something to print, makes it `%_`. The five buffers have no instance names either, so they
print as `%__0` to `%__4`, numbered in the order the module names them, not by binding: `%__0` is binding 4. The
second is a second `DrawIndirectCommand` (lines 61-65), which the types explain.

**The decorations.** Three of `ParticleSimulation`'s eighteen, at lines 79, 81 and 95:

```text
               OpMemberDecorate %ParticleSimulation 1 Offset 16
               OpMemberDecorate %ParticleSimulation 3 Offset 36
               OpMemberDecorate %ParticleSimulation 17 Offset 92
```

Members count from 0 in declaration order, and the offsets are the ones `ParticleTypes.h`'s comments give. Member 3
is `speed`, at 36: question 2. Member 1 is `gravity` at 16, a `vec4` of four floats, so `x` is at 16, `y` at 20,
`z` at 24 and `w` at byte 28: question 3. Member 17 is `emitterShape` at 92, and the struct's type at line 144 says
it is a `%uint`, 4 bytes, so the block ends at 96. That is `sizeof(ParticleSimulation)` in `ParticleTypes.h`'s
`static_assert`, and the push range your `CreateComputePipelines` creates: question 5. Two `vec4`s and sixteen
4-byte members fill every byte from 0 to 96, which is Part 1's "no free word": a new straight float grows the
block.

Further down, each buffer has a `Binding` and a `DescriptorSet`, as binding 4 does at lines 110 and 111:

```text
               OpDecorate %__0 Binding 4
               OpDecorate %__0 DescriptorSet 0
```

Five `Binding` decorations in all, 0 to 4, each at set 0. The push block has none: a push constant is not a
descriptor.

**The types.** A variable's kind is read from its storage class and its type. Each buffer variable is a pointer
into the `StorageBuffer` class, to a struct decorated `Block`, which is what a GLSL `buffer` block compiles to; the
push block's class is `PushConstant` (line 147):

```text
%_ptr_StorageBuffer_IndirectBuffer = OpTypePointer StorageBuffer %IndirectBuffer
        %__0 = OpVariable %_ptr_StorageBuffer_IndirectBuffer StorageBuffer
```

Here is the second `DrawIndirectCommand`. Line 153's is the type inside `ParticleIndirect`, the one with `Offset`
decorations (lines 101-104). Line 168's has the same four members and no decorations:

```text
%DrawIndirectCommand_0 = OpTypeStruct %uint %uint %uint %uint
```

glslang makes one type per layout: the struct as it lies in a buffer, with offsets, and the same struct as a plain
value, with none. The constructor in `main` builds the plain value.

> **Jump:** `-O0` keeps globals nothing uses. `-O0` removes nothing, and `ParticleBuffers.glsl` declares all five
> buffers for every compute pass, so this module declares the particles, the dead list and the alive lists,
> bindings 0 to 2, though `end` never touches them. At `-O0` the entry point lists all six variables too (line 9),
> so neither the declarations nor the entry point say what this stage uses. Read use from `main`: a variable that
> no instruction in `main` names is declared and unused.

**`main`.** Lines 188 to 198 are the shader's two statements:

```text
         %20 = OpAccessChain %_ptr_PushConstant_uint %_ %int_0 %int_13
         %21 = OpLoad %uint %20
         %22 = OpISub %uint %uint_1 %21
               OpStore %next %22
         %37 = OpLoad %uint %next
         %39 = OpAccessChain %_ptr_StorageBuffer_uint %__1 %int_0 %int_0 %37
         %40 = OpLoad %uint %39
         %43 = OpCompositeConstruct %DrawIndirectCommand_0 %uint_6 %40 %uint_0 %uint_0
         %45 = OpAccessChain %_ptr_StorageBuffer_DrawIndirectCommand %__0 %int_0 %int_2
         %46 = OpCopyLogical %DrawIndirectCommand %43
               OpStore %45 %46
```

An `OpAccessChain` is a pointer into a variable, one member or element at a time. `%_ %int_0 %int_13` is the push
block's member 0, `simulation`, then its member 13, `currentList`; `OpISub` is `1u - currentList`.
`%__1 %int_0 %int_0 %37` is binding 3's `counters`, its member 0, `aliveCount`, at element `next`, and `OpLoad`
reads it. `%__0 %int_0 %int_2` is binding 4's `indirect`, its member 2, `draw`, and `OpStore` writes it. In
between, `OpCompositeConstruct` builds the plain `%DrawIndirectCommand_0`, and `OpCopyLogical`, an instruction
SPIR-V 1.4 added, copies it member by member into the laid-out `%DrawIndirectCommand` the buffer holds, so the
store has the buffer's own type. So `main` touches three globals: the push block, binding 3, read, and binding 4,
written. Those are Chapter 57's two declared uses, `ComputeRead` of the counters and `ComputeWrite` of the draw's
arguments: question 1's first half.

**At `-O`.** `ParticleEnd.O.spvasm` has no names at all, and its entry point lists three variables:

```text
               OpEntryPoint GLCompute %4 "main" %15 %28 %36
```

Two `Binding` decorations are left, `OpDecorate %28 Binding 4` at line 43 and `OpDecorate %36 Binding 3` at line
51, each with `DescriptorSet 0` under it. Bindings 0 to 2 are gone: dead-code removal drops a variable nothing
uses, which answers question 1's second half. It does not trim a block that is used: all eighteen of the push
block's offsets are still there (lines 11-28), though `end` reads 4 of its 96 bytes. The plain type and the copy
are gone too, because the optimizer builds the laid-out type directly:

```text
         %46 = OpCompositeConstruct %_struct_24 %uint_6 %40 %uint_0 %uint_0
```

So a module at `-O0` tells you what its source declared, and at `-O` what the stage uses.

**Question 4 is C++.** A row's `field` is a single `float ParticleSimulation::*`, a pointer to one member of the
block. `gravity` is a member, of type `vec4`, and its `w` is a member of that member: reaching it takes a path of
two pointers, one to `gravity` and one to the `vec4`'s `w`. Chapter 45's `makeProperty` takes such a second
pointer, `Nested`, to reach `Transform::translation` inside `Node::local`. A row's field has no second, and this
lesson adds none, so drag reaches byte 28 by a typed line in `packSimulation`.

### Your notes

Write one line for each binding: its set, its binding, its kind, and whether `main` touches it. Add one for the
push block: its stage, its offset and its size. Then open `CreateDescriptors` in your `ParticlesDemo.cpp`, and the
push range in `CreateComputePipelines`, and put each line beside what your code creates.

Your code creates one particle set layout, bound at set 0 for the compute passes and at set 1 for the draw, with
six bindings: 0 to 4 storage buffers for the compute stage (0 and 2 for the vertex stage too), and 5, the scene
depth, a combined image sampler for the fragment stage. The module states 0 to 4 at set 0, all storage buffers;
binding 5 is not in it, because no compute shader declares it, and the compute pipelines' layout also lists the
wind sources' layout at set 1, which `ParticleEnd` does not declare, since it reads no wind. The push range is
`sizeof(ParticleSimulation)` from 0 for the compute stage, the 96 bytes the decorations end at.
[Chapter 8, section 8](08-Resources-And-Descriptors.md#8-one-layout-two-languages) made C++ prove its side of the
block with `static_assert`s; the module is the shader's side, and until now nothing put the two next to each other.

### Checkpoint

At `-O` the module has exactly two `Binding` decorations. From the repository root:

```powershell
Select-String -Path "$env:TEMP\ParticleEnd.O.spvasm" -Pattern ' Binding ' | ForEach-Object { $_.Line }
```

prints two lines, one ending `Binding 4` and one ending `Binding 3`. With SDK 1.4.363 they are:

```text
               OpDecorate %28 Binding 4
               OpDecorate %36 Binding 3
```

and your notes list the same two bindings, 3 and 4, as the ones `main` touches; the ids may differ in another SDK,
the two endings do not. The same command on `ParticleEnd.spvasm` prints five. The block's last member is at
`Offset 92`: the line `OpMemberDecorate %ParticleSimulation 17 Offset 92`, at line 95 in SDK 1.4.363.

### Going further: a walker, as an exercise

[Chapter 6, section 8](06-Shaders-And-Pipelines.md#8-when-the-second-pipeline-arrives) left pipeline layouts
written by hand and named generating them from SPIR-V reflection as the automation to consider later. The exercise
here is a check, not a generator: a small standalone program that walks a module's words and compares what the
shader declares with the layout you wrote, when a pipeline is created. The reference tried one, outside the engine:
it reads the stage, each descriptor variable's set, binding, kind and name, whether a function names it, and the
push block's offsets, and compares only what the stage uses. It matched what the demo creates.

It stays an exercise because it detects nothing validation does not: each mistake planted in the trial has a
validation message of its own. Its rule for use, an id named inside a function, agreed with `-O`'s dead-code
removal on the particle stages. It cannot see what is in the descriptors, the set numbers a bind uses, a push
call's stage flags, image formats, or which members of a push block a stage reads. If you write it, no engine class
changes and nothing later depends on it.

## Exit check

Under [the hygiene every exit check assumes](../VulkanTutorial.md#conventions-every-chapter-uses), in **Debug**:

- **The supplied test**, at stage 3, ends `PASS: settings rows, stage 3 (2161 checks)`, still comparing the rows
  with your copy.
- **The other tests pass**, run from the repository root: `TutorialGrassWindTests`, its 38 checks and its summary
  line
  `PASS: grass wind contract: the name table, the hash, dragBend, the spring, the fronts, the soft stop and the guards.`;
  `TutorialMirrorBatchTests`, ending `PASS: camera admission, ...`; `TutorialDeclaredFrameTests`, ending
  `PASS: toy, Life, Particles, sort, curves`; and `TutorialUiScaleTests`, `TutorialWorldWindTests`,
  `TutorialWorldWindTurnTests`, `TutorialParticleEffectTests` and `TutorialParticleSmokeTests`.
- **Log values** prints the same line as before this page: `TutorialGrassWindTests` pins it.
- **The panels and the presets behave as before.** Run
  `& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Grass` and the same with `--demo Particles` for a
  short while each: the **Wind response** node with its six groups, and the particles' headers, look as they did.
  In Particles, turn the local wind on and change the pool size, untick **Sort back to front**, then pick Smoke:
  the wind and the pool stay as you set them, and Sort comes back on, because Smoke covers. The reference compared
  the packed bytes, the panels, typed input, the presets and the log line with Chapter 57's, and they were
  identical at every section.
- **Your copy stays.** `SettingsByHand.h` is still compiled and compared (`PF_TEST_COPY` 1). Keep it until the
  first chapter that changes these settings retires it: that is [Chapter 56, section 1](56-Everything-Bends.md#1-a-front-is-a-fact-of-the-island).
- **Part 2.** Your notes list set 0's five storage buffers, with 3 and 4 touched by `main`; the `-O` module has two
  `Binding` decorations; the push block ends at 96 bytes.

You can now answer these:

- Why did a missing packing line pass every check, and what fails now if a straight field has no row?
- What is a row's second pointer, and why can it not name `gravity.w`?
- What does a typed `1e30` speed do today, and why did the rows not change that?
- Which start of the presets' comparison cannot tell a kept setting from a preset's default, and why is Sort's row
  not kept?
- What are `Offset` decorations, and why does `-O` drop bindings but keep every member of the push block?
- Where does your copy go when a later chapter changes these settings, and why keep it until then?

[Chapter 56, Everything Bends](56-Everything-Bends.md), is read after this page.

Back on the renderer route: [22 — Deferred Shading](22-Deferred-Shading.md).
