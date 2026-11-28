# 57 — The Frame, Declared

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Goal:** let every pass of a frame say what it reads and writes, and let a small layer record the barriers between
those uses: the barriers you typed by hand in Chapters 20, 21, 54 and 55. Part 1, sections 1 to 3, reads your
barriers as pairs of uses, writes the row two uses make, and keeps a history per resource, across frames. Part 2,
sections 4 and 5, declares Life's passes, and Life's typed barriers step aside a pair at a time, B0 last. Part 3,
sections 6 to 8, does the same for Particles' compute, where the first rule for reads breaks on a new kind of
reader and is replaced. Part 4, sections 9 to 11, declares the sort, Check order, the draw and the engine's images,
and ends on what catches each mistake and what stays by hand. An explain print shows each derived barrier as the
call you would have typed.

**Form:** typed into your tree from its own text, over the assembled reference; one supplied CPU test. The tree
holds Chapter 55 complete, and the chapter prints every line it changes.

**GPU idea:** a pipeline barrier is a fact about two uses of one resource on one queue. The earlier use gives the
first scope and what to make available, the later use the second scope and what to make visible, and an image's
layout changes where the two disagree. A write waits for the last write and for every read since; a read waits for
the last write only if that write has not already been made visible to its kind of reader, so a new kind of reader
needs a barrier of its own even when nothing was written in between. Kept per resource across frames, that history
derives each barrier in the order you record the work. It starts from your promise that Setup's own barriers, not
the fence wait after them, left each resource ready for its first reader: a host fence wait makes nothing visible
(Chapter 36, section 8). And a dispatch is held to what its shader can touch, not to what a push constant selects.

Reused, not new: Chapter 4's three questions and its appendix's rows, which section 2 checks at compile time; your
barriers from Chapters 20, 21, 54 and 55, each staying where you typed it, behind one `if`; and Chapter 36, section
8's fence wait, the reason Setup's barriers stay typed.

**Read after:** [Chapter 55](55-Sorted-Smoke.md), with its exit check passed, in the assembled reference. Like 55,
it is a detour from the renderer route: when you finish, go back to [Chapter 22](22-Deferred-Shading.md). [The
reflection lesson](SettingsAsRows.md) is read after this one.

**ROADMAP:** step 21+ — the `Life` and `Particles` demos record their barriers a second way.

**Module:** `pf::vulkan_graphics`, two new files, `DeclaredFrame.h` and `DeclaredFrame.cpp`, beside
`VulkanBarriers`. Your typed calls are **the hand route**, and it stays the default: on it each demo records the
same barrier calls, in the same order, as at the end of Chapter 55. The layer is **the declared route**, chosen in
each demo's panel by **Declared barriers**, or for both demos at start by `--frame-route declared`; **Explain one
frame** and `--frame-explain N` print one frame's derived barriers to the log. The layer derives barriers in the
order you record the work and never moves the work: no render graph, no scheduling, no reordering, and no layer
over another graphics API.

**Math:** none new. Stage and access masks are sets of bits, joined by `|`.

**Prerequisites:**

- [Chapter 4, section 2](04-Commands-And-Synchronization.md#2-frames-in-flight),
  [section 5](04-Commands-And-Synchronization.md#5-barriers-and-the-three-questions-they-answer) and its
  [appendix of barriers](04-Commands-And-Synchronization.md#appendix-barriers-the-later-chapters-add): frames in
  flight; the three questions, the two scopes, available and visible, and the rows section 2 checks.
- [Chapter 8, section 4](08-Resources-And-Descriptors.md#4-getting-the-offscreen-image-to-the-screen): the scene
  image's contract with the composite, handed in and back in `SHADER_READ_ONLY_OPTIMAL`, which Life's display and
  Particles' hand-back keep.
- [Chapter 10, section 9](10-Cameras-And-Depth.md#9-the-depth-buffer) and
  [Chapter 18, section 5](18-Anti-Aliasing.md#5-resolving-under-dynamic-rendering): the scene depth, written by the
  depth tests at one sample and by the resolve at more.
- [Chapter 19, section 4](19-Instancing-And-Indirect.md#4-one-vertex-buffer-for-every-mesh): `memoryBarrier`, the
  global memory barrier, one call for every buffer at once.
- [Chapter 20, section 4](20-Compute-Fundamentals.md#4-storage-images),
  [section 5](20-Compute-Fundamentals.md#5-barriers-between-dispatches),
  [section 8](20-Compute-Fundamentals.md#8-counting-storage-buffers-atomics-and-subgroups) and
  [section 9](20-Compute-Fundamentals.md#9-reading-results-back-without-stalling): Life's storage images in
  `GENERAL`; barriers between dispatches, what sync validation sees (an atomic as a read) and the return trip; the
  counters and their fill, a clear; the readback and its barrier to the host.
- [Chapter 21, section 3](21-GPU-Particles.md#3-the-passes),
  [section 4](21-GPU-Particles.md#4-recording-the-compute) and
  [section 5](21-GPU-Particles.md#5-drawing-the-particles): the passes, their barriers and their return trip, and
  the draw in [a second rendering scope](21-GPU-Particles.md#a-second-rendering-scope-after-the-scene-pass), whose
  depth hand-back is the first half of a chain.
- [Chapter 21, section 9](21-GPU-Particles.md#9-exercise-soft-particles): the soft fade, which samples the scene
  depth.
- [Chapter 36, section 8](36-Terrain-To-The-Horizon.md#8-the-heightmap-on-the-gpu): sync validation does not follow
  a resource across `immediateSubmit`'s fence wait, so a barrier there rests on the three questions alone.
- [Chapter 54, section 5](54-Shaping-A-Particle-Effect.md#5-curves-baked-into-an-image) and
  [section 6](54-Shaping-A-Particle-Effect.md#6-one-image-rewritten-inside-the-frame): the ramp, and its copy
  inside the frame.
- [Chapter 55, section 3](55-Sorted-Smoke.md#3-the-sort-on-the-gpu) and
  [section 4](55-Sorted-Smoke.md#4-checking-the-sort): the sort's passes and their barriers, and Check order's
  copies.

## Where the code goes

| File | What sections 2 to 10 do there |
| --- | --- |
| **New:** `Source/PillowFort/VulkanGraphics/DeclaredFrame.h`, `Source/PillowFort/VulkanGraphics/DeclaredFrame.cpp` | Section 2: a use, the uses the two demos make, the row two uses make, Chapter 4's rows checked at compile time. Section 3: the layer: tracked histories, passes and hand-overs, the first rule, Explain. Section 8: the visible set replaces the first rule |
| `premake5.lua`, `Tests/TutorialHarness/UploadFailureTests.cpp`, `Tests/TutorialHarness/DeclaredFrameTests.cpp` | Section 3: the test project, the two copy spies' detail, and the test, supplied at stage 0. Sections 4, 6, 9 and 10: its `PF_TEST_STAGE` line raised to 1, 2, 3 and 4 |
| `Source/PillowFort/Demos/Life/LifeDemo.h`, `Source/PillowFort/Demos/Life/LifeDemo.cpp` | Section 4: the tracked resources, the route, `Begin` and `End`, **Declared barriers** and **Explain one frame**. Section 5: Life's passes and hand-overs, and its nine sites step aside |
| `Source/SandboxGame/Main.cpp` | Section 4: `--frame-route` and `--frame-explain`, handed to Life. Section 6: to Particles too |
| `Source/PillowFort/Demos/Particles/ParticlesDemo.h`, `Source/PillowFort/Demos/Particles/ParticlesDemo.cpp` | Section 6: the same plumbing. Section 7: the compute passes, the copies out, the hand-over to the host, the draw's buffers; their sites step aside. Section 9: the sort's call, Check order's buffer and its copy. Section 10: the engine's images arrive, the draw's images, the last hand-overs |
| `Source/PillowFort/Demos/Particles/ParticleSort.h`, `Source/PillowFort/Demos/Particles/ParticleSort.cpp` | Section 9: the three borrowed buffers kept, the frame's `DeclaredFrame` passed in, a pass for every dispatch |
| `Source/PillowFort/Demos/Particles/ParticleRamp.h`, `Source/PillowFort/Demos/Particles/ParticleRamp.cpp` | Section 6: `Image()`. Section 10: the frame's copy declared; Setup's upload keeps its typed calls |

Sections 2 and 3 add files, so each runs `GenerateProjects.bat --tutorial-tests` again
([Chapter 1, section 3](01-Environment-And-Build.md#3-the-corrected-workspace)): premake bakes its file lists in
when it generates, and the flag keeps the test projects in the solution, as in Chapter 55; sections 4–10 add none.

**Blank lines.** A new function, struct member block or file-scope block you add gets one blank line above it and
one below it, as its neighbours have, except as the last thing in a class or struct, where it sits directly against
the closing `};`. Constants or comment lines that join a run of constants are the exception: they sit directly
against their neighbours, and the text says "with no blank line between" where that is so.

# Part 1 — A barrier from two uses (sections 1–3)

Every barrier you have typed was argued from Chapter 4's three questions, one call at a time. This part turns that
argument into code: section 1 reads the barriers as pairs of uses, section 2 makes a use a type and a pair's row a
function, and section 3 keeps a history per resource and records from it.

## 1. Your barriers, as pairs of uses

Life records barriers at nine places in `LifeDemo.cpp`, and Particles at sixteen, across `ParticlesDemo.cpp`,
`ParticleSort.cpp` and `ParticleRamp.cpp`, not counting the atlas bake's two, which run once at Setup. You typed
all of them, in Chapters 20, 21, 54 and 55, and each time the chapter argued the call from the three questions of
[Chapter 4, section 5](04-Commands-And-Synchronization.md#5-barriers-and-the-three-questions-they-answer). At one
step a frame, Life records eight barrier calls, and the fountain twelve, two of them inside the engine's
`beginScenePass`. You type nothing.

Each barrier stands between two uses of one resource: something done to it, and the next thing done to it that must
wait. Take C, the barrier in `RecordReadback` before the copy of Life's counters:

```text
resource      m_statistics
earlier use   the last step's atomics       COMPUTE_SHADER   SHADER_STORAGE_READ | SHADER_STORAGE_WRITE
later use     the copy reads the counters   COPY             TRANSFER_READ
barrier C     COMPUTE_SHADER / SHADER_STORAGE_WRITE  ->  COPY / TRANSFER_READ
```

The two uses answer Chapter 4's three questions between them:

- **Q1, execution.** The first scope's stages are the earlier use's; the second scope's are the later use's.
- **Q2, memory.** What to make available is what the earlier use wrote: its write bits only, because a read leaves
  nothing to flush. What to make visible is everything the later use does: its reads, so that they see the write,
  and its writes, so that they land after it
  ([Chapter 20, section 5](20-Compute-Fundamentals.md#5-barriers-between-dispatches) said why a ping-pong names
  both).
- **Q3, layout.** For an image, the old layout is the one the earlier use needed, or `UNDEFINED` when the later use
  rewrites every texel, and the new layout is the one the later use needs. Where the two agree, nothing changes. A
  buffer has no layout.

An atomic is a read and a write
([Chapter 20, section 8](20-Compute-Fundamentals.md#8-counting-storage-buffers-atomics-and-subgroups)), so C's
source keeps the write and drops the read. H, at the end of `RecordDisplay`, stands between the display writing the
scene image in `GENERAL` and the composite sampling it in `SHADER_READ_ONLY_OPTIMAL`: the uses disagree on the
layout, so the barrier changes it. I, at the start of `RecordDisplay`, stands between last frame's composite read
and this frame's display writing every pixel: an earlier read gives a source access of `NONE`, and a later use that
rewrites every texel gives an old layout of `UNDEFINED`. That earlier use sits in last frame's command buffer, and
the barrier reaches it because its first scope is everything ahead of it on the queue
([Chapter 4, section 5](04-Commands-And-Synchronization.md#what-before-and-after-cover)).

Not every call holds one pair. A global memory barrier names no resource, so it covers every buffer, and every
image whose layout stays, at once
([Chapter 19, section 4](19-Instancing-And-Indirect.md#4-one-vertex-buffer-for-every-mesh)), and the chapters used
that to give one call several jobs. A, at the top of `RecordClearStatistics`, makes the fill wait for two earlier
uses of the counters, last frame's atomics and last frame's copy, so its source names both stages,
`COMPUTE_SHADER | COPY`. The copy's half adds no access bit: the copy only read. One call, two rows joined by `|`.

So the pairs are the facts, and the calls are how the chapters wrote them down. If every pass said which uses it
makes, of which resource, a program could find, for each use, the earlier uses it must wait for, and record the
barrier between them, in the order you record the work. Before building that program, write the pairs down.

**The sites.** Each site has a letter, and every later section names the sites by these letters. Life's nine are:
B0 at the top of `Record`, the return trip of [Chapter 20, section 5](20-Compute-Fundamentals.md#the-return-trip);
A and B around the fill, in `RecordClearStatistics`; S after the seed, in `RecordSeed`; T after every step, in
`RecordStep`; C and D around the copy, in `RecordReadback`; and I and H around the display's dispatch, in
`RecordDisplay`, H through `handBackSceneTarget`.

Particles' sixteen are, in `RecordStep`: A at the top of every step, R after the reset, B after begin, the two
`computeToComputeBarrier` calls after emit and after simulate (written **c2c** below), K1 and K2 around Check
order's copy of the list before the sort, and E at the end of every step. S follows every dispatch of the sort, in
`ParticleSort::Record`. H follows the copies out, in `RecordCompute`. R1 and R2 stand around the ramp's copy in
`ParticleRamp::RecordCopyCommands`, on a frame after a curve edit. P1, P2 and P3 stand around the particles'
rendering scope, in `RecordParticles`, and the hand-back, `handBackSceneTarget`, ends `Record`. The letters are
each demo's own: Particles' A, B, S and H are not Life's.

<a id="ch57-pairs"></a>

### Attempt CH57-pairs: each barrier, as the two uses it stands between

Predict first. B0, at the top of Life's `Record`, and T, after every step, are the same call,
`computeToComputeBarrier`. Are they the same pair of uses? A's source names `COPY` with no transfer access: which
use is that half of, and why does it need no access bit? Which of Life's sites stand between uses in two different
frames, and which site's later use is not on the GPU at all?

Design a table of Life's nine sites. For each, write the resource, the earlier use and the later use, each as a
stage and an access, with a layout for the scene image. Then check that the three questions, asked of your two
uses, give the masks of the call you typed.

**Acceptance:** each of the nine sites has its resource and both uses, and the three bullets above turn them into
the typed masks and layouts. Where a call's masks are wider than one pair, the table names every pair the call
serves. The answer names the three sites whose earlier use is in last frame's command buffer, and the one whose
later use is the CPU's.

**Transfer:** Particles' sixteen sites, the same way. Which of them have another owner's use on one side: the scene
pass on the engine's images, or the composite? Which reach back to last frame?

<details>
<summary>Hint 1: read the comments above the calls</summary>

The chapters wrote each barrier's two uses into the comment above it: "the atomics' writes, before the copy reads
the counters" is C. Read a call's source half as the earlier use and its destination half as the later use. Where a
comment names two writers or two readers, the call serves more than one pair.

</details>

<details>
<summary>Hint 2: a read on the earlier side</summary>

A read leaves nothing to make available. So a site whose source access is `NONE`, or whose source names a stage
that only read, has a read as its earlier use, or as one of them. Find those first: I, and the `COPY` half of A.
Then look at B0: which image do the seed and a first step each overwrite, and what read it last?

</details>

<details>
<summary>Hint 3: walk two frames</summary>

Some uses are not in the same `Record`. Walk two frames in a row, and for each resource ask what this frame does to
it first and what last frame did to it last. For `m_readback[f]`, ask who reads it after D, and when.

</details>

<details>
<summary>Worked solution: Life's nine sites, then Particles' sixteen</summary>

**How a use is written here.** A use is a stage and an access. *Compute read* is `COMPUTE_SHADER` /
`SHADER_STORAGE_READ`, *compute write* is `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE`, and *compute read-write* is
both, which is what an atomic is. *Copy read* and *copy write* are `COPY` / `TRANSFER_READ` and `COPY` /
`TRANSFER_WRITE`, and *clear write*, the fill, is `CLEAR` / `TRANSFER_WRITE`. *Host read* is `HOST` / `HOST_READ`,
and a *sampled read* is `SHADER_SAMPLED_READ` at the stage named. Section 2 gives each of these a name in code.

| Site | Resource | Earlier use | Later use |
| --- | --- | --- | --- |
| B0 | the cells | before the seed, last frame's display; before the first step, the last reads of the image it overwrites: compute read | this frame's seed, or its first step: compute write |
| A | `m_statistics` | last frame's atomics: compute read-write; last frame's copy: copy read | the fill: clear write |
| B | `m_statistics` | the fill: clear write | the last step's atomics: compute read-write |
| S | the image the seed wrote | the seed: compute write | the first step, or when paused the display: compute read |
| T | the image a step wrote | the step: compute write | the next step reads it and the one after overwrites it: compute read-write; after the last step, the display reads it |
| C | `m_statistics` | the last step's atomics: compute read-write | the copy: copy read |
| D | `m_readback[f]` | the copy: copy write | `ReadStatistics`, two frames later, after the slot's fence: host read |
| I | the scene image | last frame's composite: sampled read at `FRAGMENT_SHADER`, `SHADER_READ_ONLY_OPTIMAL` | the display, over every pixel: compute write, `GENERAL` |
| H | the scene image | the display: compute write, `GENERAL` | the composite: sampled read at `FRAGMENT_SHADER`, `SHADER_READ_ONLY_OPTIMAL` |

**B0 and T are one call and two pairs.** T is a write, then a read and a later write: the ping-pong row of Chapter
4's appendix. It also orders the next step's write after this step's read of the other image, by execution alone.
B0 is a read, then a write, so its pair needs the order and no access at all; the `SHADER_STORAGE_WRITE` in its
source comes with the helper, not with the pair.

**A is two pairs.** The atomics' half is a write after a write; the copy's half is a write after a read, so it adds
`COPY` to the source stages and nothing to the source access.

**Three sites reach into last frame:** A, B0 and I. Each names a use in last frame's command buffer, which the
barrier reaches because its first scope is everything ahead of it on the queue. A program that looks at one command
buffer cannot pair these: each resource's last uses have to outlive the command buffer that made them.

**One later use is the CPU's.** D's reader is `ReadStatistics`, two frames later, after `drawFrame` has waited on
the slot's fence. The fence orders the copy before the read; D is what makes the copy's write visible to the host.

**Two uses are another owner's.** I's earlier use and H's later use are the composite's, which the engine records
after the demo. Chapter 8's contract says what they are.

**The transfer: Particles.** *Indirect read* is `DRAW_INDIRECT` / `INDIRECT_COMMAND_READ`. List c is the list the
step starts from, and list 1 − c the one simulate fills.

| Site | Resource | Earlier use | Later use |
| --- | --- | --- | --- |
| A | `m_indirect`, `m_particles`, the lists, `m_counters` | last frame's draw, or the step before's: indirect read, storage read at `VERTEX_SHADER`; the copies out: copy read; the compute passes: compute write | this step's passes: compute read-write |
| R | `m_counters`, `m_deadList` | reset: compute write | begin and emit: compute read and write |
| B | `m_counters`, `m_indirect` | begin: compute write | emit's dispatch: indirect read; emit's shader: compute read-write |
| c2c after emit | `m_particles`, list c, `m_counters` | emit: compute write, its atomics read-write | simulate: compute read-write |
| c2c after simulate | `m_particles`, list 1 − c, `m_deadList`, `m_counters` | simulate: compute write, its atomics read-write | end, and the sort's first pass: compute read |
| K1 | list 1 − c | simulate: compute write | Check order's copy before the sort: copy read |
| K2 | list 1 − c | that copy: copy read | the sort's write-back: compute write |
| S | the sort's items, and the list | one sort pass: compute write | the next: compute read-write |
| E | `m_indirect`, `m_particles`, the list, `m_counters` | end, simulate and the sort: compute write | the draw: indirect read, storage read at `VERTEX_SHADER`; the copies out: copy read |
| H | `m_readback[slot]`, and Check order's buffer | the copies out: copy write | the CPU, two frames later: host read |
| R1 | the ramp | last frame's vertex shader: sampled read, `SHADER_READ_ONLY_OPTIMAL` | the copy, over every texel: copy write, `TRANSFER_DST_OPTIMAL` |
| R2 | the ramp | the copy: copy write, `TRANSFER_DST_OPTIMAL` | the vertex shader: sampled read, `SHADER_READ_ONLY_OPTIMAL` |
| P1 | scene colour | the scene pass: colour attachment write | the particles' blend: colour attachment read and write, layout kept |
| P2 | scene depth | the scene pass: the depth tests' write, or at more than one sample the resolve's | the particles' read-only depth test, and the soft fade's sampled read: `DEPTH_READ_ONLY_OPTIMAL` |
| P3 | scene depth | those two reads | next frame's scene pass: depth test and write, `DEPTH_ATTACHMENT_OPTIMAL` |
| hand-back | scene colour | the particles' blend, `COLOR_ATTACHMENT_OPTIMAL` | the composite: sampled read at `FRAGMENT_SHADER`, `SHADER_READ_ONLY_OPTIMAL` |

**Another owner's uses.** P1 and P2 start from the scene pass, which the engine's `beginScenePass` opens on the
engine's images; P3 ends at next frame's scene pass, and the hand-back at the composite.

**Last frame.** A on the frame's first step reaches back to last frame's draw, copies and compute; on a prewarm's
later steps the step before is the earlier use. R1 waits for last frame's vertex shader, and P3's later use is next
frame's scene pass.

</details>

The tables hold what one command buffer cannot: last frame's uses, the CPU's read, the engine's.

## 2. A use, and the row two uses make

This section makes section 1's use a type, names the uses the two demos make, and writes the rule as a function.
Nothing in a frame calls it yet: the compiler checks it against the rows you typed, so a wrong rule, or a wrong bit
in a use the rows name, stops the build.

> **Jump:** two pairs of terms from
> [Chapter 4, section 5](04-Commands-And-Synchronization.md#5-barriers-and-the-three-questions-they-answer) carry
> the rest of this chapter; keep them exact. A barrier's **first scope** is everything ahead of it on the queue,
> last frame's work included, cut down to its source stages (for waiting, with the stages before them in the same
> pipeline: [Chapter 4, section 5](04-Commands-And-Synchronization.md#what-before-and-after-cover)), and its
> **second scope** is everything after it, cut down to its destination stages: the first finishes those stages
> before the second starts its own. Memory takes two more steps. The source access mask makes the first scope's
> writes **available**, out of the writer's caches. The destination access mask makes available writes **visible**
> to the accesses it names, at the stages it names, and to nothing else: a write made visible to compute's storage
> reads is not visible to a copy's transfer reads, nor to the host.

### Where the code goes

Both files are new, in `Source/PillowFort/VulkanGraphics/`, beside `VulkanBarriers`; the checkpoint regenerates the
projects.

**`DeclaredFrame.h`, a new file in `Source/PillowFort/VulkanGraphics/`.** It comes in three pieces, typed one after
the other with one blank line between them. The first opens the file and holds `ResourceUse`, a use without its
resource, which section 3 pairs with a handle: `stage` and `access` say where the use runs and what it does to
memory there, `layout` is what an image needs for it (a buffer's is ignored), and `overwrite` says it rewrites
every texel, so the old contents can go and a barrier's old layout can be `UNDEFINED`. Vulkan's access bits do not
come sorted into reads and writes, so `WRITE_ACCESS` lists the eight write bits a frame can name, and every other
bit is a read. `writeAccess` keeps the part a barrier's source makes available, and `readAccess` the rest:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 57: passes declare what they read and write, and the barriers are derived from it
/// @copyright (C) Gary 2026
///========================================================
#pragma once

#include <vulkan/vulkan.h>

#include <cstdint>

// Source/PillowFort/VulkanGraphics/DeclaredFrame.h, inside namespace pf::vulkan_graphics
namespace pf::vulkan_graphics {

// Chapter 57 section 2. One side of a Chapter 04 row: the stages a use runs in, what it does to memory
// there, and, for an image, the layout it needs. A use with a write bit in its access is a write.
struct ResourceUse
{
    VkPipelineStageFlags2 stage     = VK_PIPELINE_STAGE_2_NONE;
    VkAccessFlags2        access    = VK_ACCESS_2_NONE;
    VkImageLayout         layout    = VK_IMAGE_LAYOUT_UNDEFINED;   // images only
    bool                  overwrite = false;                       // every texel rewritten: the old contents can go
};

// The eight write bits a frame can name; every other access bit is a read.
inline constexpr VkAccessFlags2 WRITE_ACCESS =
    VK_ACCESS_2_SHADER_WRITE_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT
    | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_TRANSFER_WRITE_BIT | VK_ACCESS_2_HOST_WRITE_BIT
    | VK_ACCESS_2_MEMORY_WRITE_BIT | VK_ACCESS_2_ACCELERATION_STRUCTURE_WRITE_BIT_KHR;

constexpr VkAccessFlags2 writeAccess(VkAccessFlags2 access) { return access & WRITE_ACCESS; }
constexpr VkAccessFlags2 readAccess(VkAccessFlags2 access) { return access & ~WRITE_ACCESS; }
```

The second piece names the uses: nineteen constants, eighteen for the uses section 1's tables wrote in words and
`Unknown`, Chapter 4's "not sure" source, which section 3 gives a resource whose history it does not know. The
compute uses carry `GENERAL`, so one name serves a buffer and Life's cell images, which never leave that layout.
`ComputeReadWrite` includes atomics: declared as a read, an atomic's write would be made available by nothing, and
sync validation, which records an atomic as a read
([Chapter 20, section 5](20-Compute-Fundamentals.md#what-sync-validation-can-see)), would not say so. `ClearWrite`
is `vkCmdFillBuffer`, which synchronisation counts as a clear (Chapter 20, section 8), and `SceneDepthWrite` names
both of the scene depth's writers, the tests at one sample and the resolve at more:

```cpp
// The uses the two frames make, each named after the Chapter 04 row it is half of.
namespace uses {
inline constexpr ResourceUse ComputeRead{ VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_READ_BIT,
                                          VK_IMAGE_LAYOUT_GENERAL };
inline constexpr ResourceUse ComputeWrite{ VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                                           VK_IMAGE_LAYOUT_GENERAL };
// A dispatch that reads and writes the same resource, atomics included: an atomic is a read and a write.
inline constexpr ResourceUse ComputeReadWrite{ VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                                               VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                                               VK_IMAGE_LAYOUT_GENERAL };
inline constexpr ResourceUse ComputeOverwrite{ VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                                               VK_IMAGE_LAYOUT_GENERAL, true };
inline constexpr ResourceUse IndirectRead{ VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT, VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT };
inline constexpr ResourceUse VertexStorageRead{ VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_READ_BIT };
inline constexpr ResourceUse VertexSampled{ VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                            VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
inline constexpr ResourceUse CopyRead{ VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT };
inline constexpr ResourceUse CopyWrite{ VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT };
inline constexpr ResourceUse CopyOverwrite{ VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                                            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, true };
inline constexpr ResourceUse ClearWrite{ VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT };   // vkCmdFillBuffer
inline constexpr ResourceUse HostRead{ VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT };
inline constexpr ResourceUse SceneColorWrite{ VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                                              VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                                              VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
// Written by the depth tests at 1x, by the resolve at Nx (Chapter 18): both.
inline constexpr ResourceUse SceneDepthWrite{ VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                                                  | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                                              VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                                              VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL };
inline constexpr ResourceUse ColorBlend{ VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                                         VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                                         VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
inline constexpr ResourceUse DepthTestAndSample{ VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                                                     | VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                                 VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                                 VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL };
inline constexpr ResourceUse DepthAttachment{ VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                                              VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                                              VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL };
inline constexpr ResourceUse SampledByComposite{ VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
// Chapter 04's "not sure" source: what a resource's first use waits for when its history is unknown.
inline constexpr ResourceUse Unknown{ VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT };
} // namespace uses
```

The third piece is the rule, and the file's end. `BarrierHalves` holds a barrier's six answers, the fields of
Chapter 4, section 5's `VkImageMemoryBarrier2`, with `==` so that rows compare. `barrierBetween` is section 1's
three bullets in code: the earlier use's stages and write bits, the later use's stages and whole access, and the
layouts, `UNDEFINED` before a use that rewrites every texel. It is `constexpr`, so the compiler can run it.
`operator|` joins two rows into one call, as Life's A and Particles' A, B and E do: stages and accesses as sets,
and the first row's layouts, because one image barrier has one pair:

```cpp
// A barrier's six answers (Chapter 04 section 5). All NONE and UNDEFINED by default.
struct BarrierHalves
{
    VkPipelineStageFlags2 srcStage  = VK_PIPELINE_STAGE_2_NONE;
    VkAccessFlags2        srcAccess = VK_ACCESS_2_NONE;
    VkPipelineStageFlags2 dstStage  = VK_PIPELINE_STAGE_2_NONE;
    VkAccessFlags2        dstAccess = VK_ACCESS_2_NONE;
    VkImageLayout         oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VkImageLayout         newLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    bool operator==(const BarrierHalves&) const = default;
};

// Chapter 04's three questions, asked of two uses: what finished first and whose writes to flush (the earlier
// use), what waits and whose caches to invalidate (the later one), and the layout each needs.
constexpr BarrierHalves barrierBetween(ResourceUse earlier, ResourceUse later)
{
    return { earlier.stage, writeAccess(earlier.access), later.stage, later.access,
             later.overwrite ? VK_IMAGE_LAYOUT_UNDEFINED : earlier.layout, later.layout };
}

// Two rows in one call: the stages and accesses joined, the layouts of the first.
constexpr BarrierHalves operator|(BarrierHalves a, BarrierHalves b)
{
    return { a.srcStage | b.srcStage, a.srcAccess | b.srcAccess, a.dstStage | b.dstStage, a.dstAccess | b.dstAccess,
             a.oldLayout, a.newLayout };
}

} // namespace pf::vulkan_graphics
```

**`DeclaredFrame.cpp`, a new file beside it.** It comes in three pieces, each typed directly under the one before,
with no blank line between them. Nothing in it runs; every line is checked while the engine compiles. The first
opens a namespace, `rows`, of short names for the check, and `masks`, which clears both layouts so that a buffer's
row compares only its four masks: the compute uses carry `GENERAL`, and a buffer has no layout:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 57: the per-resource history, and the rule that turns two uses into a barrier
/// @copyright (C) Gary 2026
///========================================================
#include "PillowFort/VulkanGraphics/DeclaredFrame.h"

// Source/PillowFort/VulkanGraphics/DeclaredFrame.cpp, inside namespace pf::vulkan_graphics
namespace pf::vulkan_graphics {

// Chapter 57 section 2: the rows the two frames type, each derived from the two uses it stands between.
// Short names for this check only. A buffer has no layout, so a buffer's row compares the four masks.
namespace rows {
constexpr VkPipelineStageFlags2 COMPUTE = VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, COPY = VK_PIPELINE_STAGE_2_COPY_BIT,
    CLEAR = VK_PIPELINE_STAGE_2_CLEAR_BIT, HOST = VK_PIPELINE_STAGE_2_HOST_BIT,
    INDIRECT = VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT, VERTEX = VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT,
    FRAGMENT = VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
    TESTS = VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
    OUTPUT = VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT;
constexpr VkAccessFlags2 NONE = VK_ACCESS_2_NONE, SR = VK_ACCESS_2_SHADER_STORAGE_READ_BIT,
    SW = VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT, SAMPLED = VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
    TR = VK_ACCESS_2_TRANSFER_READ_BIT, TW = VK_ACCESS_2_TRANSFER_WRITE_BIT, HOST_READ = VK_ACCESS_2_HOST_READ_BIT,
    ICR = VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT, CR = VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT,
    CW = VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT, DR = VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT,
    DW = VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
constexpr VkImageLayout GENERAL = VK_IMAGE_LAYOUT_GENERAL, UNDEFINED = VK_IMAGE_LAYOUT_UNDEFINED,
    READ_ONLY = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, TRANSFER_DST = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
    ATTACHMENT = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, DEPTH = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
    DEPTH_READ = VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL;
constexpr BarrierHalves masks(BarrierHalves halves)
{
    halves.oldLayout = halves.newLayout = UNDEFINED;
    return halves;
}
using namespace uses;
```

The second is Chapter 20's rows. Each `static_assert` compares `barrierBetween` of two uses, or of several joined
by `|`, with the row as Chapter 4 prints it, and carries the row's name: Life's A (last frame's atomics and copy,
joined), B, C, D, the ping-pong row that S and T type, then I and H:

```cpp
// Chapter 20: Life.
static_assert(masks(barrierBetween(ComputeReadWrite, ClearWrite) | barrierBetween(CopyRead, ClearWrite))
              == BarrierHalves{ COMPUTE | COPY, SW, CLEAR, TW },
              "Counters: last frame's atomics and readback copy, before vkCmdFillBuffer");
static_assert(masks(barrierBetween(ClearWrite, ComputeReadWrite)) == BarrierHalves{ CLEAR, TW, COMPUTE, SR | SW },
              "Counters zeroed by vkCmdFillBuffer, then used by compute");
static_assert(masks(barrierBetween(ComputeReadWrite, CopyRead)) == BarrierHalves{ COMPUTE, SW, COPY, TR },
              "Compute-written counters copied for readback");
static_assert(masks(barrierBetween(CopyWrite, HostRead)) == BarrierHalves{ COPY, TW, HOST, HOST_READ },
              "Readback copy visible to the CPU, before the fence");
static_assert(barrierBetween(ComputeWrite, ComputeReadWrite)
              == BarrierHalves{ COMPUTE, SW, COMPUTE, SR | SW, GENERAL, GENERAL },
              "Storage image ping-pong between dispatches");
static_assert(barrierBetween(SampledByComposite, ComputeOverwrite)
              == BarrierHalves{ FRAGMENT, NONE, COMPUTE, SW, UNDEFINED, GENERAL },
              "Sampled result handed back to compute, next frame");
static_assert(barrierBetween(ComputeWrite, SampledByComposite)
              == BarrierHalves{ COMPUTE, SW, FRAGMENT, SAMPLED, GENERAL, READ_ONLY },
              "Compute result sampled by a later shader");
```

The third is Particles' rows, from Chapters 21, 54 and 55: A (four earlier uses joined), B, E, K2, R1, R2, P1, P2
and the hand-back. The last check is from the cookbook in Chapter 4, section 5, whose "Begin frame" and "Offscreen
target, start of frame" rows share their layouts and differ in their source, because their earlier uses differ: a
layout cannot tell them apart. It checks that the composite's read, before the scene pass's colour write over every
texel, gives a source of `FRAGMENT_SHADER`:

```cpp
// Chapters 21, 54 and 55: Particles.
static_assert(masks(barrierBetween(IndirectRead, ComputeReadWrite) | barrierBetween(VertexStorageRead, ComputeReadWrite)
                    | barrierBetween(CopyRead, ComputeReadWrite) | barrierBetween(ComputeWrite, ComputeReadWrite))
              == BarrierHalves{ INDIRECT | VERTEX | COPY | COMPUTE, SW, COMPUTE, SR | SW },
              "...its return trip, at the top of next frame's compute");
static_assert(masks(barrierBetween(ComputeWrite, IndirectRead) | barrierBetween(ComputeWrite, ComputeReadWrite))
              == BarrierHalves{ COMPUTE, SW, INDIRECT | COMPUTE, ICR | SR | SW },
              "Compute wrote arguments for later dispatches");
static_assert(masks(barrierBetween(ComputeWrite, IndirectRead) | barrierBetween(ComputeWrite, VertexStorageRead)
                    | barrierBetween(ComputeWrite, CopyRead))
              == BarrierHalves{ COMPUTE, SW, INDIRECT | VERTEX | COPY, ICR | SR | TR },
              "Compute wrote draw arguments and what the vertex shader reads");
static_assert(masks(barrierBetween(CopyRead, ComputeWrite)) == BarrierHalves{ COPY, NONE, COMPUTE, SW },
              "A copy's read of a buffer, then a compute write to it");
static_assert(barrierBetween(VertexSampled, CopyOverwrite)
              == BarrierHalves{ VERTEX, NONE, COPY, TW, UNDEFINED, TRANSFER_DST },
              "A table image rewritten each time the CPU changes it, before its copy");
static_assert(barrierBetween(CopyOverwrite, VertexSampled)
              == BarrierHalves{ COPY, TW, VERTEX, SAMPLED, TRANSFER_DST, READ_ONLY },
              "...and after its copy: a read after write into this frame's vertex stage");
static_assert(barrierBetween(SceneColorWrite, ColorBlend)
              == BarrierHalves{ OUTPUT, CW, OUTPUT, CR | CW, ATTACHMENT, ATTACHMENT },
              "Scene color from the scene pass into a second, blended scope");
static_assert(barrierBetween(SceneDepthWrite, DepthTestAndSample)
              == BarrierHalves{ TESTS | OUTPUT, DW | CW, TESTS | FRAGMENT, DR | SAMPLED, DEPTH, DEPTH_READ },
              "Scene depth after the scene pass, to a read-only depth test, with the soft particles' read");
static_assert(barrierBetween(ColorBlend, SampledByComposite)
              == BarrierHalves{ OUTPUT, CW, FRAGMENT, SAMPLED, ATTACHMENT, READ_ONLY },
              "Offscreen target, drawn and about to be composited");
// Chapter 04 section 5: two rows with the same layouts and different earlier uses. A layout cannot tell them apart.
static_assert(barrierBetween(SampledByComposite, { OUTPUT, CW, ATTACHMENT, true }).srcStage == FRAGMENT,
              "Offscreen target, start of frame: last frame's composite read it");
} // namespace rows

} // namespace pf::vulkan_graphics
```

These seventeen of Chapter 4's rows, fifteen from its appendix and two from section 5's cookbook (the hand-back's
and the last), cover every barrier section 1 listed but P3, the depth's return trip: K1 is C's row, Particles' H is
D's, and every `computeToComputeBarrier` has the ping-pong row's masks. A rule that gave any row differently, or a
wrong bit in a use these rows name, stops the build, and the error names the row. Three uses are in no row,
`ComputeRead`, `DepthAttachment` (P3's) and `Unknown`, so a wrong bit in one of them builds. The supplied test
(section 3) sees a wrong `ComputeRead`: its toy group compares the derived rows exactly, and from stage 1 its
declared-uses check holds each pass's uses, not a hand-over's, to tables of its own. `Unknown` reaches only its
model, in the route switch from hand to declared. Nothing here is shown to see a narrowed `DepthAttachment`: the
engine's own depth barrier may hide it.

### Checkpoint

Generate again (two new files), then build the game in Debug. Nothing but `DeclaredFrame.cpp` includes the header
yet, so the engine's compile of that file is the whole check:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The game build failed.' }
```

- **The build** ends with `0 Warning(s)` and `0 Error(s)`, and the program records the same barriers as before:
  nothing in a frame calls the new code. The reference built each section at /W4 with no warning using MSVC's v145
  tools and SDK 1.4.363, not the v143 tools and SDK 1.4.357 this guide assumes.
- **The control.** In `uses::CopyRead`, in `DeclaredFrame.h`, replace `VK_PIPELINE_STAGE_2_COPY_BIT` with
  `VK_PIPELINE_STAGE_2_TRANSFER_BIT`, and build again. The build stops. Five rows fail, every row with a copy's
  read on one side: Life's A and C, and Particles' A, E and K2. Among the errors:

```text
error C2338: static assertion failed: 'Compute-written counters copied for readback'
```

`TRANSFER` is the stage of every transfer command at once: copies, blits, resolves and clears. A barrier that named
it would still order the copy, a wider barrier than the one you typed, but the check compares rows bit for bit, and
you typed `COPY`. Put `VK_PIPELINE_STAGE_2_COPY_BIT` back and build again, to 0 warnings.

Section 3 gives these uses a resource, and each resource a history.

## 3. State that outlives the command buffer

Section 2's `barrierBetween` makes a barrier from two uses written side by side. A frame rarely has them side by
side: when Life records `vkCmdFillBuffer`, the uses barrier A's first half names are last frame's step and readback
copy, in another command buffer that may still be running. This section builds what remembers them: a history per
resource, kept across frames by a small class; the rules that turn a history and a new use into a barrier; and a
print of each derived barrier as the call you would have typed. Then the supplied test arrives, and its first group
checks the layer alone against Chapter 4's rows.

**Why a history, and why across frames.** The renderer records one command buffer per frame in flight and records
it again each time its slot comes round
([Chapter 4, section 2](04-Commands-And-Synchronization.md#2-frames-in-flight)), while Life's buffers and images
live from `Setup` to `Teardown`. So the earlier use a barrier needs is often in an earlier command buffer: A waits
for last frame's step and copy, and I for last frame's composite. A barrier can still name them, because its first
scope holds every command submitted before it on the same queue. What is missing is a record of what they were, so
the layer keeps one for each resource: the last write, who made it and in which frame, whether a reader has waited
for it, and the reads since. That record lives as long as the resources do, in one `DeclaredFrame` per demo, a
member beside the buffers it describes (section 4 adds Life's, `m_passes`); a frame's command buffer is only lent
to it, by `Begin`. Eight rules keep it. The calls they name, `Track`, `Begin`, `Leave`, `Arrive` and `End`, are the
class below, where each rule is argued; later pointers, "(rule 6)", come back to this list:

1. A write, or a layout change, waits for the last write and for every read since it.
2. A read waits for the last write unless some reader has already waited for it: section 3's first rule, one bool
   per resource. Section 8 asks whom the write was made visible to.
3. A storage image in `GENERAL` is treated as a buffer; any other image gets its own `transitionImage`, and a
   layout change is a write that always takes its use as the second scope.
4. A pass's buffer waits join one `memoryBarrier`, recorded first; its image barriers follow in declared order.
5. A barrier is credited only to the resources it was recorded for.
6. `Track` starts a history empty; a `Leave` to the host marks the resource, and `Begin`, `FRAMES_IN_FLIGHT` frames
   later, treats its last uses as ordered by the slot's fence.
7. After hand-recorded frames every history holds an unknown write until its first declared write.
8. `Arrive` gives another owner's image this frame's history; `End` drops it and ends the frame's declared route.

> **Jump:** until now the earlier use of a barrier you typed was usually a few lines above it. The layer's is often
> in another frame, and frames overlap. Keep three facts in mind. **Frames in flight:** with `FRAMES_IN_FLIGHT` at
> 2, the GPU may still be running frame N − 1 while the CPU records frame N; before `Record`, `drawFrame` waits on
> the fence of frame N − 2, the last frame to use this slot. A barrier at the top of frame N is ordered after frame
> N − 1's commands by its first scope, with no fence involved. **The host's read:** the CPU reads a readback buffer
> after that slot's fence, `FRAMES_IN_FLIGHT` frames after the copy that wrote it, which is why there is one buffer
> per slot ([Chapter 20, section 9](20-Compute-Fundamentals.md#9-reading-results-back-without-stalling)). **What a
> fence does not do:** a host fence wait orders execution and makes nothing visible.
> [Chapter 36, section 8](36-Terrain-To-The-Horizon.md#8-the-heightmap-on-the-gpu) relied on it: the heightmap's
> last barrier names the vertex shader of a later submission, though `immediateSubmit` waited on its fence in
> between. A copy's write reaches the host through a barrier to `HOST` / `HOST_READ` recorded before the submit
> (Life's D), and reaches a later reader on the GPU only through a barrier that names that reader. So once a slot's
> fence has been waited on, a later write to the buffer can need no barrier, and a later read on the GPU still
> needs one.

### Where the code goes

`DeclaredFrame.h` and `DeclaredFrame.cpp` get the rest of the layer: the class, the history, the first rule and
Explain. Then the supplied test's plumbing: the two copy stand-ins in `UploadFailureTests.cpp`, a project in
`premake5.lua`, and the test file, copied. Type them in this order. No demo uses the layer yet; section 4 starts
Life on it.

**`DeclaredFrame.h`.** The class keeps names and lists of uses, so the header needs four more standard headers. Add
them directly under the line `#include <cstdint>`:

```cpp
#include <initializer_list>
#include <span>
#include <string>
#include <vector>
```

Everything else goes at the end of the header, directly above its last line, `} // namespace pf::vulkan_graphics`,
in five pieces typed one after the other, with one blank line between each piece and the next and one blank line
between the last piece and that line.

The first piece is one use of one resource. A pass names its uses as pairs, a buffer or an image with one of
section 2's `ResourceUse`s, and `PassUse` is the pair. Its two constructors let a pair be written as braces,
`{ m_statistics.buffer, uses::ClearWrite }`. It keeps the handle as a number with a flag for its kind: a `VkBuffer`
and a `VkImage` may share a handle value, so the two together name the resource.

```cpp
// Chapter 57 section 3. One use of one buffer or image by a pass.
struct PassUse
{
    PassUse(VkBuffer buffer, ResourceUse use) : handle(reinterpret_cast<uint64_t>(buffer)), image(false), use(use) {}
    PassUse(VkImage image, ResourceUse use) : handle(reinterpret_cast<uint64_t>(image)), image(true), use(use) {}
    uint64_t    handle;
    bool        image;   // a VkBuffer and a VkImage may share a handle value: the pair names a resource
    ResourceUse use;
};
```

The second piece is what the layer did, kept so that it can be read back. `RecordedBarrier` is one call it
recorded: section 2's six answers and, for an image barrier, the image and its aspect. `DeclaredPass` is one
declaration as it was made: the name, whether it was a hand-over, and a copy of its uses. Explain prints from them,
and the supplied test checks them against the commands the frame really recorded.

```cpp
// What the layer recorded, and what each pass declared: Explain and the supplied test read them.
struct RecordedBarrier
{
    BarrierHalves      halves;
    VkImage            image  = VK_NULL_HANDLE;   // null: a memoryBarrier
    VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT;
};
struct DeclaredPass
{
    const char*          name;
    bool                 leaving;   // a Leave: a use made ready here, for whoever makes it
    std::vector<PassUse> uses;
};
```

The third piece opens the class with the calls that bracket a demo's life. `Track` is called at the end of `Setup`,
once for each buffer and image a command of the frame writes, an image with the layout `Setup` left it in, and the
resource starts with an empty history. That is a promise, yours, and nothing checks it: that `Setup`'s own last
barriers made each resource ready for its first reader in a frame. Life keeps it: `createStorageImage`'s barrier
moved both cell images to `GENERAL` for compute to read and write, and its destination scope covers later frames
([Chapter 20, section 4](20-Compute-Fundamentals.md#4-storage-images)), while each of Life's buffers is written by
its first use in a frame. `Forget` drops a buffer before it is destroyed, because a buffer made later may get the
same handle; section 9's Check order buffer, tracked when `Record` makes it rather than at the end of `Setup`,
needs both. `Clear` drops everything, in `Teardown`. The layer keeps the names it is given across frames without
copying them, so names are string literals; and since Explain prints an image's name inside the call it pastes, the
demos name each resource by the expression that holds it, `"m_cells[0]"`.

```cpp
class DeclaredFrame
{
public:
    // The end of Setup: the reader's promise that Setup's last barriers made each resource ready for its first
    // reader in a frame (Chapter 36 section 8). Its history starts empty. The layer keeps every name it is given
    // across frames, so names are string literals.
    void Track(VkBuffer buffer, const char* name);
    void Track(VkImage image, const char* name, VkImageLayout layout, VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT);
    void Forget(VkBuffer buffer);   // before destroying it: a later buffer may get the same handle
    void Clear();                   // Teardown
```

The fourth piece is a frame. `Begin` lends the layer this frame's command buffer, counts the frame, and names its
route: declared, where the layer records the barriers, or hand, your typed calls, the default. Its comment says why
the count keeps step with the renderer's frame slot: a submitted frame ran one `Begin`, and any frame that fails
before its submit, in `Record` or after it, is not submitted, and Main shuts down. Section 4 wires the route to the
panel's **Declared barriers** checkbox and to `--frame-route`. Each typed call will ask `Declared()`: section 5
puts each of Life's behind `if (!m_passes.Declared())`. `End` closes the frame and returns its explanation, if one
was asked for. Between them come the declarations. `Pass(name, uses)` goes just before the commands it names, and
the layer records the barriers those uses need right there, where your typed calls stand; it never moves a command.
`Leave(to, uses)` is a hand-over: it makes a use ready here for whoever makes it next, mostly another owner. Life's
readback buffer leaves to `"the host"`, which derives D, Chapter 4's "Readback copy visible to the CPU, before the
fence"; later sections hand over to the composite, the next scene pass and the vertex shaders. `Arrive` is the
other direction: another owner's image, for this frame only (the engine's scene images, sections 5 and 10). `Pass`
and `Leave` take their uses as a braced list, or as a `std::span` over a local array when the length depends on a
CPU choice, so a demo's use lists allocate nothing. `Recorded()` and `Declarations()` hand out the frame's calls
and declarations.

```cpp
    // Frames are counted by Begin, and a buffer left to the host settles FRAMES_IN_FLIGHT Begins later, so the count
    // must move with the renderer's slot. It does: a submitted frame ran one Record and one Begin, and the slot moves
    // after the submit; any frame that fails before its submit, in Record or after it, is not submitted, and Main
    // shuts down; and Teardown's Clear starts every history again.
    void Begin(VkCommandBuffer commandBuffer, bool declared, bool explain, const char* demo);
    bool Declared() const { return m_declared; }
    // Another owner's image, for this frame only, with the use it was last put to.
    void Arrive(const char* from, VkImage image, const char* name, ResourceUse lastUse,
                VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT);
    void Pass(const char* name, std::initializer_list<PassUse> passUses);
    void Pass(const char* name, std::span<const PassUse> passUses);
    // A hand-over: a use made ready here, at this point of the frame, for whoever makes it: the host, the composite,
    // the next frame's scene pass, or the ramp's vertex shaders (the curves draw reads it later in the same frame).
    void Leave(const char* to, std::initializer_list<PassUse> passUses);
    void Leave(const char* to, std::span<const PassUse> passUses);
    std::vector<std::string> End();   // the explanation when one was asked for, else empty

    const std::vector<RecordedBarrier>& Recorded() const { return m_recorded; }       // this frame's calls
    const std::vector<DeclaredPass>&    Declarations() const { return m_declarations; }   // this frame's passes
```

The last piece is the history, private. For each resource: what it is (its handle and kind, its name, an image's
aspect, the layout the layer believes it is in, and whether it arrived); its last write, as the use that made it,
the pass that declared it and the frame; `waited`, which is this section's first rule in one bool, whether any
reader has waited for that write; the reads since, as stages and the passes' names; and three fields for the host,
which rule 6 uses. Then two helpers, the lists a frame fills, and the counts Explain prints. The layer's `m_passes`
counts passes; the demos' member of the same name is the layer itself.

```cpp
private:
    struct Resource
    {
        uint64_t           handle  = 0;
        bool               image   = false;
        const char*        name    = "";
        VkImageAspectFlags aspect  = VK_IMAGE_ASPECT_COLOR_BIT;
        VkImageLayout      layout  = VK_IMAGE_LAYOUT_UNDEFINED;
        bool               arrived = false;   // another owner's, this frame only
        // The last write, and whether any reader has waited for it (section 3's first rule; section 8 replaces it).
        bool                     written    = false;
        ResourceUse              write{};
        const char*              writer     = "";
        uint64_t                 writeFrame = 0;
        bool                     waited     = false;
        // The reads since it: their stages, and the passes that made them.
        VkPipelineStageFlags2    readStages = VK_PIPELINE_STAGE_2_NONE;
        std::vector<const char*> readers;
        uint64_t                 lastFrame  = 0;       // the frame of its last use
        bool                     leftToHost = false;   // its last use was a Leave to the host, in lastFrame
        bool                     fenced     = false;   // a slot's fence has ordered its last write and the reads
    };

    Resource* Find(uint64_t handle, bool image);
    void Record(const char* what, std::span<const PassUse> passUses, bool leaving);

    std::vector<Resource>        m_resources;
    std::vector<RecordedBarrier> m_recorded;
    std::vector<DeclaredPass>    m_declarations;
    std::vector<std::string>     m_explanation;
    VkCommandBuffer              m_commandBuffer = VK_NULL_HANDLE;
    const char*                  m_demo = "";
    uint64_t                     m_frame = 0, m_frames = 0;   // this frame, counted from 0; frames begun
    unsigned                     m_passes = 0, m_leaves = 0, m_calls = 0;
    bool                         m_declared = false, m_historyKnown = true, m_explain = false;
};
```

**A build, before the bodies.** The header is whole. Build the game in Debug with section 2's MSBuild line; no file
is new, so there is nothing to generate. It ends with `0 Warning(s)` and `0 Error(s)`: the header compiles, and
since nothing calls the class yet, the link does not miss the bodies that come next.

**`DeclaredFrame.cpp`.** It records with Chapter 4's `transitionImage` and the `memoryBarrier` of
[Chapter 19, section 4](19-Instancing-And-Indirect.md#4-one-vertex-buffer-for-every-mesh), reads
`FRAMES_IN_FLIGHT`, and prints flags through the SDK's `vk_enum_string_helper.h`, which spells each enum value as
its name. Directly under the line `#include "PillowFort/VulkanGraphics/DeclaredFrame.h"`, after one blank line, add
the includes:

```cpp
#include "PillowFort/VulkanGraphics/VulkanBarriers.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"   // FRAMES_IN_FLIGHT

#include <vulkan/vk_enum_string_helper.h>

#include <algorithm>
#include <cassert>
#include <format>
#include <string_view>
#include <utility>
```

Then, after one blank line, the helpers Explain prints with, at file scope in an unnamed namespace. `flagNames`
turns a mask into its bits' names, lowest bit first, joined by ` | `, the form a call you paste needs; `stages` and
`accesses` give it the SDK's spellings. `shortName` and `halfName` shorten a stage and an access to
`COMPUTE_SHADER/SHADER_STORAGE_WRITE` for the reasons printed above each call. The blank line already above
`// Source/PillowFort/VulkanGraphics/DeclaredFrame.cpp, inside namespace pf::vulkan_graphics` stays between them
and that line:

```cpp
// File scope, above the namespace block: the names Explain prints.
namespace {

std::string flagNames(uint64_t bits, const char* (*name)(uint64_t), const char* none)
{
    if (bits == 0) { return none; }
    std::string joined;
    for (int bit = 0; bit < 64; ++bit)
    {
        const uint64_t flag = uint64_t{ 1 } << bit;
        if ((bits & flag) == 0) { continue; }
        if (!joined.empty()) { joined += " | "; }
        joined += name(flag);
    }
    return joined;
}

std::string stages(VkPipelineStageFlags2 bits)
{
    return flagNames(bits, string_VkPipelineStageFlagBits2, "VK_PIPELINE_STAGE_2_NONE");
}
std::string accesses(VkAccessFlags2 bits)
{
    return flagNames(bits, string_VkAccessFlagBits2, "VK_ACCESS_2_NONE");
}

// The short form for a because: line: COMPUTE_SHADER/SHADER_STORAGE_WRITE.
std::string shortName(std::string name, std::string_view prefix)
{
    for (size_t at = name.find(prefix); at != std::string::npos; at = name.find(prefix)) { name.erase(at, prefix.size()); }
    for (size_t at = name.find("_BIT"); at != std::string::npos; at = name.find("_BIT")) { name.erase(at, 4); }
    return name;
}
std::string halfName(VkPipelineStageFlags2 stage, VkAccessFlags2 access)
{
    return shortName(stages(stage), "VK_PIPELINE_STAGE_2_") + "/" + shortName(accesses(access), "VK_ACCESS_2_");
}

} // namespace
```

The rest of the file goes directly under the line `} // namespace rows`, after one blank line, in twelve pieces
typed one after the other with one blank line between each piece and the next. The blank line and the
`} // namespace pf::vulkan_graphics` already under `} // namespace rows` stay below the last piece.

The first piece is the bodies of the bracket. `Track` refuses a resource tracked twice and starts it empty;
`Forget` erases a buffer by its handle; `Clear` also ends the route and marks the history known, so the next
`Setup`'s `Track` starts afresh:

```cpp
// Chapter 57 section 3.
void DeclaredFrame::Track(VkBuffer buffer, const char* name)
{
    assert(Find(reinterpret_cast<uint64_t>(buffer), false) == nullptr && "a buffer tracked twice");
    m_resources.push_back({ .handle = reinterpret_cast<uint64_t>(buffer), .name = name });
}

void DeclaredFrame::Track(VkImage image, const char* name, VkImageLayout layout, VkImageAspectFlags aspect)
{
    assert(Find(reinterpret_cast<uint64_t>(image), true) == nullptr && "an image tracked twice");
    m_resources.push_back({ .handle = reinterpret_cast<uint64_t>(image), .image = true, .name = name,
                            .aspect = aspect, .layout = layout });
}

void DeclaredFrame::Forget(VkBuffer buffer)
{
    const uint64_t handle = reinterpret_cast<uint64_t>(buffer);
    std::erase_if(m_resources, [&](const Resource& resource) { return !resource.image && resource.handle == handle; });
}

void DeclaredFrame::Clear()
{
    m_resources.clear();
    m_historyKnown = true;
    m_declared     = false;
}
```

`Begin` starts the frame. It takes the command buffer, the route, whether to explain (only on the declared route:
on the hand route nothing was derived), and the demo's name for the print. It counts the frame, which gives the
frame number Explain prints, empties the frame's records, and drops an image that arrived in a frame that never
reached `End`. Then, before any pass is declared, it changes a history in two cases. If the frames before this one
were recorded by hand, the layer saw none of their uses, so each history becomes one write it knows nothing about,
section 2's `uses::Unknown`: Chapter 4's "not sure" source (rule 7). Otherwise, a resource whose last use was a
hand-over to the host, `FRAMES_IN_FLIGHT` or more frames ago, is settled: its reads are dropped, its write is kept,
and it is marked `fenced` (rule 6). `m_historyKnown` then remembers which route this frame took.

```cpp
void DeclaredFrame::Begin(VkCommandBuffer commandBuffer, bool declared, bool explain, const char* demo)
{
    m_commandBuffer = commandBuffer;
    m_declared      = declared;
    m_explain       = declared && explain;
    m_demo          = demo;
    m_frame         = m_frames++;
    m_recorded.clear();
    m_declarations.clear();
    m_explanation.clear();
    m_passes = m_leaves = m_calls = 0;
    // An image that arrived in a frame that never reached End.
    std::erase_if(m_resources, [](const Resource& resource) { return resource.arrived; });

    for (Resource& resource : m_resources)
    {
        const Resource empty{ .handle = resource.handle, .image = resource.image, .name = resource.name,
                              .aspect = resource.aspect, .layout = resource.layout };
        // Frames recorded by hand left no history: Chapter 04's "not sure" source, once per resource.
        if (declared && !m_historyKnown)
        {
            resource            = empty;
            resource.written    = true;
            resource.write      = uses::Unknown;
            resource.writer     = "the hand route";
            resource.writeFrame = m_frame;
        }
        // Left to the host and not used since: the host read it after this slot's fence, FRAMES_IN_FLIGHT frames
        // later. That fence ordered the last write and every read before this frame, so a write now waits for
        // nothing. It made nothing visible, though (Chapter 36 section 8), so the write stays in the history and a
        // read now waits for it as the rule says: an earlier submission on this queue, inside that barrier's first
        // scope.
        else if (resource.leftToHost && resource.lastFrame + FRAMES_IN_FLIGHT <= m_frame)
        {
            resource.leftToHost = false;
            resource.fenced     = true;
            resource.readStages = VK_PIPELINE_STAGE_2_NONE;
            resource.readers.clear();
        }
    }
    m_historyKnown = declared;
    if (m_explain) { m_explanation.push_back(std::format("explain: {}, frame {}, declared route", demo, m_frame)); }
}
```

`Arrive` gives another owner's image a history for this frame alone, from the use it was last put to (rule 8). A
write becomes its last write, made by `from`. A read becomes the reads since, with no write recorded before them:
whatever wrote the image was made visible to that read by its owner. Section 8 sharpens its read case. The image
must arrive in a layout and must not also be tracked; on the hand route `Arrive` does nothing.

```cpp
void DeclaredFrame::Arrive(const char* from, VkImage image, const char* name, ResourceUse lastUse,
                           VkImageAspectFlags aspect)
{
    if (!m_declared) { return; }
    assert(lastUse.layout != VK_IMAGE_LAYOUT_UNDEFINED && "an image arrives in a layout");
    assert(Find(reinterpret_cast<uint64_t>(image), true) == nullptr && "an image both tracked and arrived");
    Resource arrived{ .handle = reinterpret_cast<uint64_t>(image), .image = true, .name = name, .aspect = aspect,
                      .layout = lastUse.layout, .arrived = true, .lastFrame = m_frame };
    if (writeAccess(lastUse.access) != 0)
    {
        arrived.written    = true;
        arrived.write      = lastUse;
        arrived.writer     = from;
        arrived.writeFrame = m_frame;
    }
    else
    {
        // Whatever wrote it last was made visible to this read.
        arrived.readStages = lastUse.stage;
        arrived.readers    = { from };
    }
    m_resources.push_back(std::move(arrived));
}
```

`End` drops the arrived images and ends the declared route for the frame, so `Declared()` is false until the next
`Begin` and a guarded call outside `Begin` and `End` is the hand route's. It returns the explanation, closed by a
line that counts the frame's passes, hand-overs and calls, or nothing when none was asked for.

```cpp
std::vector<std::string> DeclaredFrame::End()
{
    std::erase_if(m_resources, [](const Resource& resource) { return resource.arrived; });
    m_commandBuffer = VK_NULL_HANDLE;
    m_declared      = false;   // a guarded call outside Begin and End is the hand route's
    if (!m_explain) { return {}; }
    m_explanation.push_back(std::format("explain: {}, frame {}: {} passes, {} hand-overs, {} calls",
                                        m_demo, m_frame, m_passes, m_leaves, m_calls));
    return std::exchange(m_explanation, {});
}
```

`Pass` and `Leave` hand their uses to `Record`, with whether this is a hand-over. They are out of line for the
supplied test's sake. It includes the header with `#define private public`, and MSVC's mangled name for a member
includes its access, so an inline `Pass` compiled into the test would call a `Record` that the engine never defined
under that name, and the link would fail with `LNK2019`.

```cpp
// Out of line: the tests include the header with private made public, which changes a private member's name.
void DeclaredFrame::Pass(const char* name, std::initializer_list<PassUse> passUses)
{
    Record(name, { passUses.begin(), passUses.size() }, false);
}
void DeclaredFrame::Pass(const char* name, std::span<const PassUse> passUses)
{
    Record(name, passUses, false);
}
void DeclaredFrame::Leave(const char* to, std::initializer_list<PassUse> passUses)
{
    Record(to, { passUses.begin(), passUses.size() }, true);
}
void DeclaredFrame::Leave(const char* to, std::span<const PassUse> passUses)
{
    Record(to, passUses, true);
}
```

`Find` looks a resource up by the pair, handle and kind:

```cpp
DeclaredFrame::Resource* DeclaredFrame::Find(uint64_t handle, bool image)
{
    for (Resource& resource : m_resources)
    {
        if (resource.handle == handle && resource.image == image) { return &resource; }
    }
    return nullptr;
}
```

**`Record`**, in six pieces. It runs once per `Pass` or `Leave`, in the order you call them, and records the
barriers the declared uses need at that point in the command buffer. On the hand route it returns at its first
line. Otherwise it keeps a copy of the declaration for Explain and the test, and walks the uses. For each it finds
the resource and says what kind of use this is, asks the rules what the use waits for, gives the barrier its form,
and writes the use into the history. Then it records the calls. A declaration costs a little: the copy, and for a
pass with image barriers a small vector, both freed each frame. The hand route allocates nothing in the layer.

The first piece finds the resource and classifies the use. Three asserts catch mistakes in Debug: a resource nobody
tracked (a Release build drops that use silently), an image declared with a buffer's use (one with no layout), and
a resource used again too soon after it was handed to the host, which the assert's comment explains. `reads` and
`writes` are section 2's split of the access bits. `ownBarrier` and `changesLayout` are rule 3's two questions
about an image: a storage image in `GENERAL`, used in `GENERAL`, is treated as a buffer, and any other image gets a
barrier of its own, which changes the layout when the use needs a different one or rewrites every texel.

```cpp
void DeclaredFrame::Record(const char* what, std::span<const PassUse> passUses, bool leaving)
{
    if (!m_declared) { return; }   // the hand route: every barrier is the reader's own call
    if (leaving) { ++m_leaves; } else { ++m_passes; }
    m_declarations.push_back({ what, leaving, { passUses.begin(), passUses.end() } });

    BarrierHalves                memory{};
    std::vector<RecordedBarrier> images;
    std::vector<std::string>     because;
    for (const PassUse& passUse : passUses)
    {
        Resource* found = Find(passUse.handle, passUse.image);
        assert(found != nullptr && "a pass declared a resource nobody tracked");
        if (found == nullptr) { continue; }
        Resource&          resource = *found;
        const ResourceUse& use      = passUse.use;
        assert(!(resource.image && use.layout == VK_IMAGE_LAYOUT_UNDEFINED) && "an image declared with a buffer's use");
        // The host reads after this slot's fence, frames from now: a GPU use before then would race it, and no
        // barrier can order the host. A resource the host reads needs one per frame in flight.
        assert(!(resource.leftToHost && resource.lastFrame + FRAMES_IN_FLIGHT > m_frame)
               && "a resource left to the host is used again before its slot's fence");
        const bool reads         = readAccess(use.access) != 0;
        const bool writes        = writeAccess(use.access) != 0;
        // A storage image in GENERAL is treated as a buffer; any other image gets a barrier of its own.
        const bool ownBarrier    = resource.image
                                && !(resource.layout == VK_IMAGE_LAYOUT_GENERAL && use.layout == VK_IMAGE_LAYOUT_GENERAL);
        const bool changesLayout = ownBarrier && (use.overwrite || use.layout != resource.layout);
```

The second piece holds the use's **term**, its part of this pass's barrier, and three small helpers. `add` joins a
pair of halves into the term with section 2's `operator|` and, when explaining, writes a `because:` line: the
resource, the kind of wait, whom it waits for, and the two halves. `writer` and `readersNamed` name the last writer
and the readers since, and build strings only when explaining. A writer whose use includes `SHADER_STORAGE_WRITE`
prints as `"pass" (declared writable)`: the layer knows what a pass declared, not what its shader stored.

```cpp
        BarrierHalves term{};
        bool          any = false;
        const auto add = [&](BarrierHalves halves, const char* kind, const std::string& who) {
            term = any ? term | halves : halves;
            any  = true;
            if (m_explain)
            {
                because.push_back(std::format("  because: {}: {}, {} {} -> {}", resource.name, kind, who,
                                              halfName(halves.srcStage, halves.srcAccess),
                                              halfName(halves.dstStage, halves.dstAccess)));
            }
        };
        // Who made the last write, for a because: line. A shader's write is the binding's: the layer knows what a
        // pass declared, not what its shader stored. A layout change wrote nothing of its own.
        const auto writer = [&]() {
            if (!m_explain) { return std::string(); }
            std::string who;
            if (resource.write.access == VK_ACCESS_2_NONE)
            {
                who = std::format("the layout change before \"{}\"", resource.writer);
            }
            else
            {
                const bool binding = (resource.write.access & VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT) != 0;
                who = std::format("\"{}\"{}", resource.writer, binding ? " (declared writable)" : "");
            }
            return resource.writeFrame == m_frame ? who : std::format("{} (frame {})", who, resource.writeFrame);
        };
        const auto readersNamed = [&]() {
            std::string names;
            if (!m_explain) { return names; }
            for (const char* reader : resource.readers)
            {
                names += std::format("{}\"{}\"", names.empty() ? "" : ", ", reader);
            }
            return names;
        };
```

The third piece is the two rules that decide what a use waits for.

**Rule 1: a write, or a layout change, waits for the last write and for every read since it.** The write term is
`barrierBetween(resource.write, use)`, section 2's row made from the two uses. The read term has no access in its
first half: a read leaves nothing to make available, so ordering after it is enough, Chapter 4's write after read.
Two cases skip the write term: a `fenced` resource has none to wait for (rule 6), and when the last write was a
layout change whose stages are all among the reads since, the read term already orders after it.

**Rule 2, the first rule: a read waits for the last write unless some reader has already waited for it.** One bool
per resource, `waited`, set when a read's own term waits for the write (a layout change sets it too) and cleared by
the next write. Life's test and its GPU run are clean under it (section 5); Particles' test fails under it, by
design (section 7), and section 8 replaces the bool.

```cpp
        // A write, or a layout change, waits for the last write and for every read since it.
        // A read waits for the last write unless some reader has already waited for it.
        if (writes || changesLayout)
        {
            // Nothing to wait for after a fence; and a layout change's own stages are its readers', waited below.
            const bool waitWrite = resource.written && !resource.fenced
                                && !(resource.write.access == VK_ACCESS_2_NONE
                                     && (resource.readStages & resource.write.stage) == resource.write.stage);
            if (waitWrite)
            {
                add(barrierBetween(resource.write, use),
                    writes ? (reads ? "read and write after write" : "write after write") : "layout change after write",
                    writer());
            }
            if (resource.readStages != VK_PIPELINE_STAGE_2_NONE)
            {
                add({ resource.readStages, VK_ACCESS_2_NONE, use.stage, use.access },
                    writes ? "write after read" : "layout change after read", readersNamed());
            }
        }
        else if (reads && resource.written && !resource.waited)
        {
            add(barrierBetween(resource.write, use), "read after write", writer());
        }
```

The fourth piece gives the term its form. **Rule 3: a storage image in `GENERAL` is treated as a buffer; any other
image gets its own `transitionImage`.** A layout change is a write of its own, so it gets a barrier even when there
is nothing to wait for: then the term is `NONE` before and the use after, Chapter 4's "Staging upload into a new
texture" row, never an empty barrier. The old layout is `UNDEFINED` when the use rewrites every texel, which lets
the contents go. **Rule 4: every other term of a pass joins one `memoryBarrier`.** Buffers and `GENERAL` storage
images share it, joined with `operator|`, and the image barriers wait in a list.

```cpp
        if (ownBarrier)
        {
            if (any || changesLayout)
            {
                if (!any)
                {
                    // Nothing to wait for, but the change itself must come before the use: Chapter 04's
                    // "Staging upload into a new texture" row, NONE before, the use after.
                    term = { VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE, use.stage, use.access };
                    if (m_explain)
                    {
                        because.push_back(std::format("  because: {}: a layout change, nothing to wait for", resource.name));
                    }
                }
                term.oldLayout = use.overwrite ? VK_IMAGE_LAYOUT_UNDEFINED : resource.layout;
                term.newLayout = use.layout;
                images.push_back({ term, reinterpret_cast<VkImage>(resource.handle), resource.aspect });
            }
            resource.layout = use.layout;
        }
        else if (any)
        {
            memory = memory | term;
        }
```

The fifth piece writes the use into the history. A write replaces the last write and empties the reads. A layout
change becomes the last write, at the use's stages with no access, already waited for by this use, which becomes
its reader if it reads. A read joins the reads. **Rule 5: a barrier is credited only to the resources it was
recorded for.** `waited` is set only from this resource's own term, `if (any)`: a `memoryBarrier` is global and may
in fact cover a resource whose use added nothing to it, but the history does not count on that. The host is kept
out of the reads: no later barrier can wait for the host, whose read the slot's fence orders, and what was made
visible to the host is visible to nothing on the device. A read by the host leaves only `leftToHost` behind.

```cpp
        // The history, after this use. The host is no stage a later barrier could wait for (its read is ordered by
        // the slot's fence), and what was made visible to it is visible to no use on the device: a read by the
        // host leaves only leftToHost behind.
        const VkPipelineStageFlags2 readerStages = use.stage & ~VK_PIPELINE_STAGE_2_HOST_BIT;
        resource.lastFrame  = m_frame;
        resource.leftToHost = leaving && use.stage == VK_PIPELINE_STAGE_2_HOST_BIT;
        if (writes)
        {
            resource.written    = true;
            resource.write      = use;
            resource.writer     = what;
            resource.writeFrame = m_frame;
            resource.waited     = false;
            resource.readStages = VK_PIPELINE_STAGE_2_NONE;
            resource.readers.clear();
            resource.fenced     = false;
        }
        else if (changesLayout)
        {
            // The layout change is a write, made visible to this use by its own barrier.
            resource.written    = true;
            resource.write      = { use.stage, VK_ACCESS_2_NONE, use.layout };
            resource.writer     = what;
            resource.writeFrame = m_frame;
            resource.waited     = true;
            resource.readStages = reads ? readerStages : VK_PIPELINE_STAGE_2_NONE;
            resource.readers.assign(reads ? 1 : 0, what);
            resource.fenced     = false;
        }
        else if (reads && readerStages != VK_PIPELINE_STAGE_2_NONE)
        {
            if (any) { resource.waited = true; }
            resource.readStages |= readerStages;
            if (std::ranges::find(resource.readers, what) == resource.readers.end()) { resource.readers.push_back(what); }
        }
    }
```

The last piece records the calls, in **rule 4's order**: the one `memoryBarrier` first, then the image barriers in
the order their uses were declared. A pass whose uses needed nothing records nothing and prints nothing. Each call
is kept in `m_recorded` and, when explaining, printed under its reasons: a header, `#n before "pass"` or
`#n leaving to "owner"`, numbered among the passes or the hand-overs, then the call as you would type it.

```cpp
    const unsigned calls = (memory.dstStage != VK_PIPELINE_STAGE_2_NONE ? 1u : 0u) + static_cast<unsigned>(images.size());
    if (calls == 0) { return; }
    m_calls += calls;
    if (m_explain)
    {
        m_explanation.push_back(std::format("#{} {} \"{}\": {} call{}", leaving ? m_leaves : m_passes,
                                            leaving ? "leaving to" : "before", what, calls, calls == 1 ? "" : "s"));
        m_explanation.insert(m_explanation.end(), because.begin(), because.end());
    }
    if (memory.dstStage != VK_PIPELINE_STAGE_2_NONE)
    {
        memoryBarrier(m_commandBuffer, memory.srcStage, memory.srcAccess, memory.dstStage, memory.dstAccess);
        m_recorded.push_back({ memory });
        if (m_explain)
        {
            m_explanation.push_back(std::format("  memoryBarrier(commandBuffer,\n"
                                                "                {}, {},\n"
                                                "                {}, {});",
                                                stages(memory.srcStage), accesses(memory.srcAccess),
                                                stages(memory.dstStage), accesses(memory.dstAccess)));
        }
    }
    for (const RecordedBarrier& image : images)
    {
        const BarrierHalves& h = image.halves;
        transitionImage(m_commandBuffer, image.image, h.oldLayout, h.newLayout, h.srcStage, h.srcAccess, h.dstStage,
                        h.dstAccess, image.aspect);
        m_recorded.push_back(image);
        if (m_explain)
        {
            const Resource* named = Find(reinterpret_cast<uint64_t>(image.image), true);
            m_explanation.push_back(std::format("  transitionImage(commandBuffer, {}, {}, {},\n"
                                                "                  {}, {},\n"
                                                "                  {}, {}{});",
                                                named ? named->name : "?", string_VkImageLayout(h.oldLayout),
                                                string_VkImageLayout(h.newLayout), stages(h.srcStage), accesses(h.srcAccess),
                                                stages(h.dstStage), accesses(h.dstAccess),
                                                image.aspect == VK_IMAGE_ASPECT_COLOR_BIT ? ""
                                                    : ", VK_IMAGE_ASPECT_DEPTH_BIT"));
        }
    }
}
```

**Rules 6 and 7, at the frame's edges.** A settled resource keeps its write but not its reads: a write waits for
nothing, and a GPU read still waits for the write. After hand frames `Begin` writes `uses::Unknown`, named
`"the hand route"`; the first write waits for it, and so does the first read before that write.

**Explain.** Ask for an explanation (section 4 adds the panel's **Explain one frame** button and
`--frame-explain N`), and `End` returns lines like these. They come from the supplied test's toy group, which
prints each line of an explanation after a `|`:

```text
   | #3 before "write again": 1 call
   |   because: toy counters: write after write, "write" (declared writable) COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_WRITE
   |   because: toy counters: write after read, "read" COMPUTE_SHADER/NONE -> COMPUTE_SHADER/SHADER_STORAGE_WRITE
   |   memoryBarrier(commandBuffer,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

"write again" writes the toy's counters after "write" wrote them and "read" read them: rule 1's two terms, a line
each, joined into one call whose source access is the write's alone. Further down the same frame, the toy's table,
tracked in `SHADER_READ_ONLY_OPTIMAL` and with nothing in its history, is rewritten by a copy:

```text
   | #8 before "upload": 1 call
   |   because: toy table: a layout change, nothing to wait for
   |   transitionImage(commandBuffer, toy table, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                  VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
```

That is rule 3's layout change with nothing to wait for, `NONE` before. Each call is spelled as you would type it:
full flag names, lowest bit first, `commandBuffer` as the variable, and for an image the name you gave `Track`, so
a call pastes where your typed one stood. A `because:` line names one of seven kinds: read after write, write after
write, read and write after write, write after read, layout change after write, layout change after read, or a
layout change with nothing to wait for. A writer from an earlier frame carries `(frame N)`. An explanation opens
with the demo, the frame, counted by `Begin`s from 0, and the route, and closes with the frame's passes, hand-overs
and calls. Passes that recorded nothing are left out, which is why the numbers skip.

### The supplied test

`TutorialDeclaredFrameTests` checks the layer, and from section 4 each demo's two routes, on the CPU: it opens no
window and makes no device. It arrives now because its first group, the toy group, can run already.

**What it runs.** It includes `UploadFailureTests.cpp`, the stand-ins for Vulkan's entry points that
`TutorialMirrorBatchTests` already includes, with the engine's own barrier helpers left real, so every barrier and
command a frame records reaches the test. The toy group, stage 0, drives a `DeclaredFrame` of its own over five
fake resources (three buffers, a storage image in `GENERAL` and a sampled image) through three frames. It writes
out each pass's barriers as Chapter 4's rows, checks the layer's calls against them, and checks `Recorded()`
against what the stand-ins saw. From stage 1 it sets up Life, and from stage 2 Particles, with fake handles tracked
through the demo's own `TrackResources()`, and runs the demo's real `Record` on both routes, three to five frames
per case; two Life cases switch route at frame 2, one each way, and the switch to declared exercises rule 7.

**What it checks**, on every frame of every demo case:

- **Same work.** Both routes record the same commands apart from barriers: the same kind, pipeline, bound
  descriptor sets and two handles (a fill's buffer, a copy's source and destination, an indirect command's buffer
  and offset). It does not compare group counts, push constants, copy regions or rendering info.
- **The oracle.** A small model of the queue reads each route's stream and reports a hazard where a use is not
  ordered after the use it conflicts with, or a write was not made visible to a later reader, the host included. It
  does not read the shaders to learn what each command touches. It has its own tables, per pipeline and per
  command, written by hand, with atomics as a read and a write and its own eight write bits: a second declaration
  of the same frames, written apart from yours, used to judge the barriers yours produced. A mistake both
  declarations share is one the test cannot see.
- **Declared uses.** Every access the tables give a command on a tracked resource must be declared, at its stages
  and with its read and write bits, by the nearest pass declared before the command, and the tables must allow that
  pass's name. Nothing searches ahead or skips: a pass that is missing or too narrow fails at its own command.
- **Tracking.** After every frame on both routes, the layer tracks exactly the test's own list of the demo's
  resources.
- **Fidelity.** `Recorded()` appears in the frame's barrier stream, in order, so Explain prints what ran.

**What it prints.** For each frame of a demo's case, a count line,
`frame N: hand <hand> calls; declared <declared> calls: <layer> from the layer, <typed> typed`: the barriers each
route recorded, and of the declared route's, how many the layer recorded and how many are typed calls you have not
yet put behind a guard. From section 6 Particles adds `, <engine> the engine's`: the barriers on the scene's images
right before the scene pass's clear, which no route types. For one frame in each group it prints the gap view: for
each gap between two commands where either route has a barrier, `gap before` the command, then the hand route's
barriers and the declared route's, each declared one tagged `[layer]`, `[typed]` or `[engine]`. A hazard names its
command by its index in the frame's stream, barriers counted, and by the pass the tables give it. A group your
stage has not reached prints one `SKIP:` line, so a skipped group is never read as a pass; a failure prints
`FAIL:`, and the program exits with a nonzero code. It prints no hash to compare with the reference's: Explain's
names come from your SDK's `vk_enum_string_helper.h`, whose spellings can differ between SDK versions.

**Stages.** One line near the top, `#define PF_TEST_STAGE`, says how far your tree has come: 0 here, 1 in section 4
(Life), 2 in section 6 (Particles), 3 in section 9 (the sort) and 4 in section 10 (the scene images and the
curves). Code that names a member a later section adds is compiled only from that stage. At stage 4, a typed
barrier left on a declared frame is a failure too.

**`UploadFailureTests.cpp`, in `Tests/TutorialHarness/`.** The test names a copy by its source and destination and
judges the barriers around it, so the copy stand-ins must say what they copied; from stage 1 the test checks that
they do. Replace the ten lines from
`VKAPI_ATTR void VKAPI_CALL vkCmdCopyBuffer(VkCommandBuffer, VkBuffer, VkBuffer, uint32_t, const VkBufferCopy*)`
down to the `}` that closes `vkCmdCopyBufferToImage`, the two copy stand-ins, with these two.
`TutorialMirrorBatchTests` still counts the copies as before and does not read the detail:

```cpp
VKAPI_ATTR void VKAPI_CALL vkCmdCopyBuffer(VkCommandBuffer, VkBuffer source, VkBuffer destination, uint32_t, const VkBufferCopy* regions)
{
    ++calls.copies;
    // Chapter 57: what was copied where, for the test that checks the barriers around it.
    const uint64_t detail[5] = { reinterpret_cast<uint64_t>(source), reinterpret_cast<uint64_t>(destination),
                                 regions[0].srcOffset, regions[0].dstOffset, regions[0].size };
    if (commandSpy) { commandSpy("copyBuffer", detail); }
}
VKAPI_ATTR void VKAPI_CALL vkCmdCopyBufferToImage(VkCommandBuffer, VkBuffer source, VkImage destination, VkImageLayout, uint32_t,
                                                 const VkBufferImageCopy*)
{
    ++calls.copies;
    const uint64_t detail[2] = { reinterpret_cast<uint64_t>(source), reinterpret_cast<uint64_t>(destination) };   // Chapter 57
    if (commandSpy) { commandSpy("copyBufferToImage", detail); }
}
```

**`premake5.lua`.** The test's project goes inside the `if _OPTIONS["tutorial-tests"] then` block, directly above
the line `    project "TutorialSceneMathTests"`, with a blank line between:

```lua
    -- Chapter 57: the frames' barriers on both routes, checked by a small model of the queue.
    project "TutorialDeclaredFrameTests"
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/DeclaredFrameTests.cpp" }
        includedirs { "Vendor/GLFW/include", "Vendor/ImGui", "Vendor/ImGui/backends" }
        links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

**`DeclaredFrameTests.cpp`, supplied.** It is `Tests/TutorialHarness/DeclaredFrameTests.cpp`. A learning branch
made from `start` already has it at that path; otherwise copy it there from the same path in a `reference-main`
checkout ([Which checkout](../VulkanTutorial.md#choose-your-checkout) says how to keep one). It is about fifteen
hundred lines, most of them the model and its tables, and typing them would bury the chapter. The reference's
finished copy is at stage 4 (on a learning branch made from `start` the copy already says 0, so there the line is
already in place). Replace the line that starts `#define PF_TEST_STAGE` with this one, which says 0:

```cpp
#define PF_TEST_STAGE 0
```

Sections 4, 6, 9 and 10 raise it, each by a typed edit, which is also what makes the build compile the test again.

### Checkpoint

The test file and its project are new to premake, so generate again with the test projects
([Chapter 1, section 3](01-Environment-And-Build.md#3-the-corrected-workspace)), build the test, and run it from
the repository root, as [Chapter 55, section 2](55-Sorted-Smoke.md#2-keys-and-a-network-on-the-cpu-first) ran its
own:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialDeclaredFrameTests
if ($LASTEXITCODE -ne 0) { throw 'The acceptance test build failed.' }
& .\Build\Artifacts\Debug\TutorialDeclaredFrameTests\TutorialDeclaredFrameTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialDeclaredFrameTests failed.' }
```

**The toy group.** It explains all three toy frames (above: two of frame 0's seven calls) and ends:

```text
PASS: stage 0: 9 barriers derived as Chapter 04's rows

SKIP: Life: PF_TEST_STAGE is below 1 (Chapter 57, section 4 raises it)
SKIP: Particles: PF_TEST_STAGE is below 2 (Chapter 57, section 6 raises it)
SKIP: sort: PF_TEST_STAGE is below 3 (Chapter 57, section 9 raises it)
SKIP: curves: PF_TEST_STAGE is below 4 (Chapter 57, section 10 raises it)

PASS: toy
```

Nine barriers: seven in frame 0 and one in each of the next two. Frames 1 and 2 are the history at work:

```text
-- toy frame 1: 1 calls
   | explain: toy, frame 1, declared route
   | #1 before "clear": 1 call
   |   because: toy counters: write after write, "write again" (declared writable) (frame 0) COMPUTE_SHADER/SHADER_STORAGE_WRITE -> CLEAR/TRANSFER_WRITE
   |   because: toy counters: write after read, "copy out" COPY/NONE -> CLEAR/TRANSFER_WRITE
   |   memoryBarrier(commandBuffer,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
   | explain: toy, frame 1: 1 passes, 0 hand-overs, 1 calls
-- toy frame 2: 1 calls
   | explain: toy, frame 2, declared route
   | #2 before "read results": 1 call
   |   because: toy results: read after write, "copy" (frame 0) COPY/TRANSFER_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ
   |   memoryBarrier(commandBuffer,
                VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_READ_BIT);
   | explain: toy, frame 2: 2 passes, 0 hand-overs, 1 calls
```

Frame 1 declares one pass, the clear, and its barrier comes from frame 0's history: rule 1's write term for "write
again" and its read term for "copy out", joined into Chapter 4's "Counters: last frame's atomics and readback copy,
before `vkCmdFillBuffer`" row, which is Life's A. Frame 2 comes two frames after frame 0 handed the readback and
results buffers to the host, so `Begin` settled both (rule 6). Its pass 1, "copy again", writes the readback buffer
and records nothing, so it is not printed: the host's read is done and the slot's fence ordered the old copy, so
the new one waits for nothing. "read results" reads the results buffer on the GPU and waits for frame 0's copy: the
fence made nothing visible.

- **`TutorialMirrorBatchTests`** shares `UploadFailureTests.cpp`. Build it with `/t:TutorialMirrorBatchTests` and
  run `.\Build\Artifacts\Debug\TutorialMirrorBatchTests\TutorialMirrorBatchTests.exe` from the repository root: its
  last line starts `PASS: camera admission`.
- **On screen, nothing changes.** No demo includes `DeclaredFrame.h` yet.

Part 2 puts Life on the layer: section 4 gets it ready to declare.

# Part 2 — Life, declared (sections 4–5)

This part puts Chapter 20's Life on the layer: section 4 adds the plumbing and declares nothing, and section 5
declares Life's passes, moves its nine typed barriers aside a pair at a time, B0 last, and runs Life on the GPU.

## 4. Life, ready to declare

Before Life declares a pass, it gives the layer four things: a `DeclaredFrame` of its own, `m_passes`; its
resources, tracked at the end of `Setup` (section 3's promise, which Life keeps); every frame between `Begin` and
`End`; and the route, from the panel's **Declared barriers** or `--frame-route hand|declared`, with **Explain one
frame** and `--frame-explain N` for one frame's print. Nothing declares a pass yet, so both routes record your
calls.

Life tracks what it owns and its frame writes: the two cell images, the statistics buffer and the two readback
buffers. The scene image is the engine's, rebuilt on a resize, so section 5 has it arrive each frame instead.
`Begin` goes after `ReadStatistics`, the host's read after this slot's fence, and before the first command; `End`
after the last.

### Where the code goes

No file is new. **`LifeDemo.h`.** Three edits. The include goes directly under the line
`#include "PillowFort/Demos/Demo.h"`:

```cpp
#include "PillowFort/VulkanGraphics/DeclaredFrame.h"   // Chapter 57
```

Two public members go directly under the line that declares `Teardown`,
`    void                 Teardown() override;` with its comment `// section 7`, with a blank line between.
`SetFrameRoute` takes the command line's choice. `TrackResources` is the list, public, as its comment says, because
the supplied test calls it on fake handles of its own and includes this header with `private` made public, which
changes a private member's link name under MSVC:

```cpp
    // Chapter 57: record the barriers from what each pass declares, instead of the calls typed by hand,
    // and log the derived barriers of one frame (the explainFrame-th Record, counted from 0; -1 for none).
    void SetFrameRoute(bool declared, int explainFrame) { m_declaredBarriers = declared; m_explainFrame = explainFrame; }
    // Called at the end of Setup. Public because the supplied test calls it on its own fake handles, and MSVC gives a
    // private member another link name in a file that includes this header with private made public.
    void TrackResources();
```

The state goes at the end of the class, directly under the line
`    uint32_t       m_seed       = 1;  // feeds the random soup; a new one per reseed`, with a blank line between.
The panel is drawn in `Update` and acted on in `Record`, so the checkbox and the button are members:

```cpp
    // Chapter 57: the frame, declared.
    vulkan_graphics::DeclaredFrame m_passes;
    bool                           m_declaredBarriers = false;   // the panel's checkbox; hand by default
    bool                           m_explainNext      = false;   // the panel's button
    int                            m_explainFrame     = -1;      // --frame-explain
    int                            m_recordedFrames   = 0;
```

**`LifeDemo.cpp`.** Eight edits, from the top down. Replace the line
`static void drawLifePanel(LifeSettings& settings, const LifeStatistics& statistics, uint64_t generation)` with
these two:

```cpp
static void drawLifePanel(LifeSettings& settings, const LifeStatistics& statistics, uint64_t generation,
                          bool& declaredBarriers, bool& explainNext)
```

and add the controls directly under the line `        settings.reseed |= ImGui::Button("Reseed");`, with a blank
line between. The button is greyed out on the hand route, which has no derived barriers to explain:

```cpp
        ImGui::SeparatorText("Barriers (Chapter 57)");
        pf::debug_panels::checkbox("Declared barriers", &declaredBarriers);
        ImGui::BeginDisabled(!declaredBarriers);   // only the declared route has barriers to explain
        explainNext |= ImGui::Button("Explain one frame");
        ImGui::EndDisabled();
```

`Setup` tracks once everything it creates exists. Add this directly under the line
`    m_readbackPending.fill(false);`:

```cpp
    TrackResources();   // Chapter 57
```

and the function directly above the line `InitializationResult LifeDemo::CreatePipelines()`, with a blank line
between. An image is tracked in the layout `Setup` left it in; a buffer has none. The `static_assert` keeps the two
readback lines honest, one per frame in flight:

```cpp
// Chapter 57 section 4. Every buffer and image of Life's own that a command of the frame writes. Setup's own barriers
// made each ready for its first reader; tracking promises that, and starts each history empty.
void LifeDemo::TrackResources()
{
    m_passes.Track(m_cells[0].image, "m_cells[0]", VK_IMAGE_LAYOUT_GENERAL);
    m_passes.Track(m_cells[1].image, "m_cells[1]", VK_IMAGE_LAYOUT_GENERAL);
    m_passes.Track(m_statistics.buffer, "m_statistics");
    static_assert(vulkan_graphics::FRAMES_IN_FLIGHT == 2, "one readback per slot");
    m_passes.Track(m_readback[0].buffer, "m_readback[0]");
    m_passes.Track(m_readback[1].buffer, "m_readback[1]");
}
```

In `Update`, replace the line `    drawLifePanel(m_settings, m_latest, m_generation);` with:

```cpp
    drawLifePanel(m_settings, m_latest, m_generation, m_declaredBarriers, m_explainNext);
```

In `Record`, the frame begins on the layer. `--frame-explain N` names the N-th `Record`, counted from 0, and the
button asks for the next one and is then spent; `Begin` keeps `explain` only on the declared route. Add these lines
directly under the line `    const bool count = steps > 0;`, with a blank line between:

```cpp
    // Chapter 57: on the declared route the layer records each pass's barriers, and the typed calls step aside.
    const bool explain = m_recordedFrames++ == m_explainFrame || m_explainNext;
    m_explainNext = false;
    m_passes.Begin(commandBuffer, m_declaredBarriers, explain, "Life");
```

`End` returns the explanation when one was asked for, and the demo logs it. Add this directly under the line
`    RecordDisplay(commandBuffer, frame.targets);                       // section 7`:

```cpp
    for (const std::string& line : m_passes.End()) { Log::info(line.c_str()); }   // Chapter 57
```

`Teardown` destroys what the layer tracks, and the next `Setup` may create resources with the same handle values,
so the list goes too. Add this directly under the line `    m_sets            = {};`:

```cpp
    m_passes.Clear();   // Chapter 57
```

**`Main.cpp`.** Four edits. The settings gain two fields, directly under the line
`    std::string                       particlePreset;   // Chapter 54: empty keeps the demo's own settings`:

```cpp
    std::string                       frameRoute = "hand";   // Chapter 57: hand or declared
    int                               frameExplain = -1;     // Chapter 57: the Record to explain, counted from 0
```

The parser reads them, directly under the line
`        else if (key == "--particle-preset") { settings.particlePreset = value; }`:

```cpp
        else if (key == "--frame-route") { settings.frameRoute = value; }                       // Chapter 57
        else if (key == "--frame-explain") { settings.frameExplain = std::atoi(argv[i + 1]); }   // Chapter 57
```

A route that is neither stops the program, as the other flags' checks do; an explanation asked of the hand route,
which would print nothing, gets a warning. Add these lines directly above the line that starts
`    if (!settings.uiWorkspaceValuesValid`:

```cpp
    if ((settings.frameRoute != "hand" && settings.frameRoute != "declared") || settings.frameExplain < -1)   // Chapter 57
    {
        Log::error(std::format("--frame-route must be hand or declared, not \"{}\"; --frame-explain is a frame or -1.",
                               settings.frameRoute).c_str());
        return 1;
    }
    if (settings.frameExplain >= 0 && settings.frameRoute != "declared")
    {
        Log::warning("--frame-explain explains the declared route only: add --frame-route declared.");
    }
```

Life gets the choice as it is built. Replace the line
`    demoList.push_back(std::make_unique<demos::life::LifeDemo>());               // Chapter 20` with these three;
the middle one is that line, unchanged, and section 6 hands `declaredBarriers` to Particles too:

```cpp
    const bool declaredBarriers = settings.frameRoute == "declared";   // Chapter 57
    demoList.push_back(std::make_unique<demos::life::LifeDemo>());               // Chapter 20
    static_cast<demos::life::LifeDemo&>(*demoList.back()).SetFrameRoute(declaredBarriers, settings.frameExplain);
```

**`DeclaredFrameTests.cpp`.** The Life group calls `TrackResources`, so it is compiled only from stage 1. Replace
the line `#define PF_TEST_STAGE 0` with:

```cpp
#define PF_TEST_STAGE 1
```

### Checkpoint

No file is new, so there is nothing to generate. Build the game and the test, and run the test from the repository
root; every checkpoint of sections 4 to 8 runs these lines:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:SandboxGame;TutorialDeclaredFrameTests'
if ($LASTEXITCODE -ne 0) { throw 'The build failed.' }
& .\Build\Artifacts\Debug\TutorialDeclaredFrameTests\TutorialDeclaredFrameTests.exe
if ($LASTEXITCODE -ne 0) { throw 'TutorialDeclaredFrameTests failed.' }
```

After the toy group, Life's group runs seven cases: 1, 4 and 16 steps a frame, a Reseed mid-run, paused with a
Reseed, and the two route switches, each through Life's real `Record` on both routes. Every declared frame says it
had nothing to check, and the routes match. For "Life, 1 step", frame 2:

```text
frame 2: no pass declared, so no declared use is checked
frame 2: hand 8 calls; declared 8 calls: 0 from the layer, 8 typed
```

Frame 0, the seed frame, has nine on both, S among them, and the gap view under frame 2 pairs each hand call with
its twin, tagged `[typed]`. The report ends with the `SKIP:` lines for Particles, the sort and the curves, then
`PASS: toy, Life`. The two routes record the same calls, so there is nothing new to see on screen.

## 5. Life, declared

Six steps, with the test after each. Step 5a declares every pass and hand-over and leaves your calls recording:
wasteful, correct, and easy to compare. Steps 5b to 5f move your calls aside a pair at a time, B0 last, so a
mistake shows at the step that made it. Each goes behind `if (!m_passes.Declared())`, one call to a guard:
`Declared()` is true only between `Begin` and `End` on the declared route, so the hand route still records it.

### 5a. Every pass declared, every call still typed

A pass goes directly above its first command, where your typed barriers stand, and a hand-over directly under the
command whose result leaves. All six edits are in `LifeDemo.cpp`. The seed writes the current cell image. In
`RecordSeed`, add this directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_seedPipeline);`:

```cpp
    m_passes.Pass("seed", { { m_cells[m_current].image, uses::ComputeWrite } });   // Chapter 57
```

A step reads the current image and writes the other; the ping-pong's parity stays yours, and the pass is handed the
two images it touches. It also declares the statistics, on every step, though only the frame's last step counts.

> **Jump:** a pass declares what its shader *can* touch, not what one dispatch of it does. `LifeStep.comp.glsl`
> binds the statistics at binding 2 and reaches its atomics through `if (parameters.countStatistics != 0u)`, a push
> constant. The barrier is recorded on the CPU before any of that runs, so it is held to the shader's **static
> use**: every binding its code refers to, whatever a branch decides at run time. That is the contract for every
> dispatch in this chapter, and sync validation's shader-access heuristic reads a dispatch the same way
> ([Chapter 20, section 5](20-Compute-Fundamentals.md#what-sync-validation-can-see)), as do the test's tables. An
> atomic is declared `ComputeReadWrite` ([Chapter 20, section 8](20-Compute-Fundamentals.md#atomics)), though sync
> validation records it as a read and so cannot see a hazard whose writer is an atomic.

In `RecordStep`, add these lines directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_stepPipeline);`:

```cpp
    // Chapter 57: the step shader binds the statistics on every step; the push constant decides only whether
    // it counts, so every step declares them.
    m_passes.Pass("step", { { m_cells[m_current].image, uses::ComputeRead },
                            { m_cells[1 - m_current].image, uses::ComputeWrite },
                            { m_statistics.buffer, uses::ComputeReadWrite } });
```

The fill is a clear write. In `RecordClearStatistics`, add this directly above the comment line
`    // The return trip for the buffer: last frame's atomics wrote it and its readback copy read it.`:

```cpp
    m_passes.Pass("clear statistics", { { m_statistics.buffer, uses::ClearWrite } });   // Chapter 57
```

The copy reads the counters and writes this slot's readback buffer. In `RecordReadback`, add these lines directly
above the comment line `    // The atomics' writes, before the copy reads the counters.`:

```cpp
    m_passes.Pass("copy statistics", { { m_statistics.buffer, uses::CopyRead },   // Chapter 57
                                       { m_readback[frameIndex].buffer, uses::CopyWrite } });
```

The readback's next reader is the host, which no command records, so it is a hand-over. Add this directly under the
line `    vkCmdCopyBuffer(commandBuffer, m_statistics.buffer, m_readback[frameIndex].buffer, 1, &region);`:

```cpp
    m_passes.Leave("the host", { { m_readback[frameIndex].buffer, uses::HostRead } });   // Chapter 57
```

The display reads the newest cells; its write of the scene image waits for step 5e. In `RecordDisplay`, add this
directly under the comment line `    // and the display pass overwrites every pixel.`:

```cpp
    m_passes.Pass("display", { { m_cells[m_current].image, uses::ComputeRead } });   // Chapter 57
```

**Check 5a.** Rebuild and run the test. "Life, 1 step" reads
`frame 2: hand 8 calls; declared 13 calls: 5 from the layer, 8 typed` (frame 0:
`frame 0: hand 9 calls; declared 13 calls: 4 from the layer, 9 typed`): your eight, and on top of them the layer's
five, before the fill, the step and the copy, at the host's hand-over and before the display. The report ends
`PASS: toy, Life`, here and after every step below.

### 5b. S and T, the steps' barriers

Life's S stands between the seed's write and the first step's read, which the step's pass now asks for. T stands
between one step and the next: the next reads what this one wrote, and overwrites what it read; the next step's
pass asks for both, and after the frame's last step the display's pass asks for the read. In `RecordSeed`, replace
the line `    computeToComputeBarrier(commandBuffer);   // the first step reads what this wrote` with:

```cpp
    if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }   // the first step reads what this wrote
```

and in `RecordStep`, replace the line `    computeToComputeBarrier(commandBuffer);` directly under the comment
`    // Section 5: the next step reads what this one wrote, and overwrites what it read.` with:

```cpp
    if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

**Check 5b.** `frame 2: hand 8 calls; declared 12 calls: 5 from the layer, 7 typed` (frame 0:
`frame 0: hand 9 calls; declared 11 calls: 4 from the layer, 7 typed`).

### 5c. A and B, the clear

A makes the fill wait for last frame's atomics, a write, and last frame's copy, a read; the history kept both, and
"clear statistics" asks for a write after write and a write after read. B makes this frame's atomics wait for the
fill, and the step's pass asks for a read and write after write. In `RecordClearStatistics`, replace the four lines
of the `memoryBarrier` call directly under the comment
`    // The return trip for the buffer: last frame's atomics wrote it and its readback copy read it.` with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
    }
```

and the four lines of the `memoryBarrier` call directly under the comment
`    // The zeros, before this frame's atomics read and write them.` with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
```

**Check 5c.** `frame 2: hand 8 calls; declared 10 calls: 5 from the layer, 5 typed` (frame 0:
`frame 0: hand 9 calls; declared 9 calls: 4 from the layer, 5 typed`).

### 5d. C and D, the readback

C makes the copy wait for the atomics' write, and "copy statistics" asks for a read after write. D makes the copy's
write visible to the host, and the `Leave` asks for it. In `RecordReadback`, replace the three lines of the
`memoryBarrier` call directly under the comment `    // The atomics' writes, before the copy reads the counters.`
with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
    }
```

and the three lines of the `memoryBarrier` call that ends
`VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);`, under the comment that starts
`    // The copy's writes, visible to the CPU`, with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    }
```

**Check 5d.** `frame 2: hand 8 calls; declared 8 calls: 5 from the layer, 3 typed` (frame 0:
`frame 0: hand 9 calls; declared 7 calls: 4 from the layer, 3 typed`).

### 5e. I and H, the scene image

The scene image arrives each frame as
[Chapter 8](08-Resources-And-Descriptors.md#4-getting-the-offscreen-image-to-the-screen)'s contract says, last
sampled by the composite in `SHADER_READ_ONLY_OPTIMAL`, and `Arrive` states that at the top of the frame. The
display writes every pixel, `ComputeOverwrite`: against the arrived read, a write after read and a layout change
from `UNDEFINED`, in a `transitionImage` of its own (rule 3). On the program's first frame and after a resize the
image is new and holds nothing, not what `Arrive` claims; the claim is safe only because the display overwrites
every pixel and so transitions from `UNDEFINED` whatever the image held. That is I, Chapter 4's "Sampled result
handed back to compute, next frame". Leaving to the composite is a layout change after the display's write, H,
"Compute result sampled by a later shader". `End` drops the image.

In `Record`, add these lines directly under the line
`    m_passes.Begin(commandBuffer, m_declaredBarriers, explain, "Life");`. The image is named as `RecordDisplay`
calls it, where Explain's calls paste:

```cpp
    // Chapter 08's contract, stated: the scene image arrives last sampled by the composite.
    m_passes.Arrive("the composite", frame.targets.colorImage, "targets.colorImage",
                    uses::SampledByComposite);
```

In `RecordDisplay`, replace step 5a's line
`    m_passes.Pass("display", { { m_cells[m_current].image, uses::ComputeRead } });   // Chapter 57` with these
two:

```cpp
    m_passes.Pass("display", { { m_cells[m_current].image, uses::ComputeRead },   // Chapter 57
                               { targets.colorImage, uses::ComputeOverwrite } });
```

replace the four lines of the `transitionImage` call directly under them with:

```cpp
    if (!m_passes.Declared())
    {
        transitionImage(commandBuffer, targets.colorImage,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
```

and replace the two lines of the `handBackSceneTarget` call, directly under the comment line
`    // composite's fragment shader.`, with the hand-over and the guarded call:

```cpp
    m_passes.Leave("the composite", { { targets.colorImage, uses::SampledByComposite } });   // Chapter 57
    if (!m_passes.Declared())
    {
        handBackSceneTarget(commandBuffer, targets, VK_IMAGE_LAYOUT_GENERAL,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
```

**Check 5e.** `frame 2: hand 8 calls; declared 8 calls: 7 from the layer, 1 typed` (frame 0:
`frame 0: hand 9 calls; declared 7 calls: 6 from the layer, 1 typed`): the layer's two more are I and H.

### 5f. B0, the frame's first barrier

B0 is the cells' return trip ([Chapter 20, section 5](20-Compute-Fundamentals.md#the-return-trip)): last frame
wrote and read the cell images, and this frame's seed or first step overwrites one. It goes last because it stands
for no pair at its own site: its pair belongs to the first pass that writes a cell image, where the layer has
derived it since step 5a: the first step's barrier, joined to B's term by rule 4, or on a Reseed frame the seed's.
In `Record`, replace the line `    computeToComputeBarrier(commandBuffer);` directly under the comment line
`    // cells; this frame's first dispatch must not write them before it finishes.` with:

```cpp
    if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

**Check 5f.** `frame 2: hand 8 calls; declared 7 calls: 7 from the layer, 0 typed` (frame 0:
`frame 0: hand 9 calls; declared 6 calls: 6 from the layer, 0 typed`).

### Checkpoint

**The test.** Life's group passes with nothing typed on the declared route, and the report ends `PASS: toy, Life`.
The other cases, hand against declared calls a frame: a Reseed mid-run 9 → 8, 4 steps 11 → 10, 16 steps 23 → 22,
paused 3 → 2, paused with a Reseed 4 → 4. A running frame has one fewer: B0's job is inside the first step's
barrier, and T's read moved to the display's pass. On frame 0 every history starts empty, so neither the clear nor
the seed waits for anything, no A and no B0, and the step's wait for the seed joins B's term in one barrier: three
fewer. The route switches pass too.

**Life on the GPU, declared.** Run it in **Debug**, where the validation layer, with the sync validation and
shader-access heuristic Chapter 2 asks for, is the evidence:

```powershell
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Life --frame-route declared --frame-explain 60
```

Validation reports no sync hazard and no VUID, in the reference's run on the RTX 5090. **Explain one frame** asks
for the next frame's print (the reference used the flag; the button was built, not clicked). Frame 60's is 39
lines; the step's barrier is B with B0's job, three terms in one call:

```text
[INFO] #2 before "step": 1 call
[INFO]   because: m_cells[1]: write after write, "step" (declared writable) (frame 58) COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_WRITE
[INFO]   because: m_cells[1]: write after read, "display", "step" COMPUTE_SHADER/NONE -> COMPUTE_SHADER/SHADER_STORAGE_WRITE
[INFO]   because: m_statistics: read and write after write, "clear statistics" CLEAR/TRANSFER_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ | SHADER_STORAGE_WRITE
[INFO]   memoryBarrier(commandBuffer,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

Frame 58's step wrote `m_cells[1]`, frame 58's display and frame 59's step read it, and frame 60's step overwrites
it. The explanation closes with `[INFO] explain: Life, frame 60: 4 passes, 2 hand-overs, 7 calls`.

**The same picture.** Capture frame 300 on each route and compare the files:

```powershell
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Life --frame-route hand --frames 300 --capture life-hand.bmp
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Life --frame-route declared --frames 300 --capture life-declared.bmp
(Get-FileHash life-hand.bmp).Hash -eq (Get-FileHash life-declared.bmp).Hash
```

In the reference's run the two captures were byte for byte the same, and the last line prints `True`.

<a id="ch57-host-reader"></a>

### Attempt CH57-host-reader: what the host's read leaves behind

Predict first. Frame 2 copies the counters into `m_readback[0]`, and the host reads it at the top of frame 4's
`Record`, after slot 0's fence. What does the `Leave` to "the host" derive in frame 2, and why can it not be left
to the fence? Frame 4 then copies into `m_readback[0]` again: what does that copy wait for? And a compute pass of
frame 4 that read it instead?

For each of the three uses, say what the history holds when it arrives and which rule gives its barrier, then find
each in `DeclaredFrame.cpp`.

**Acceptance:** the hand-over's barrier is D, `COPY` / `TRANSFER_WRITE` to `HOST` / `HOST_READ`, in frame 2 after
the copy, with why nowhere later will do. Frame 4's copy gets no barrier, with what ordered the old copy and the
host's read before it. A GPU read gets one from frame 2's copy, with why neither D nor the fence counts for it.
Section 3's toy, frame 2, shows the last two.

**Transfer:** with one readback buffer for both slots, what would frame 3's copy do to frame 2's numbers? Could a
barrier prevent it, and what does the layer do?

<details>
<summary>Hint 1: where the host's read happens</summary>

`ReadStatistics` runs on the CPU after `drawFrame` waited on the slot's fence. No command buffer holds it, so no
later barrier can name it. Which command buffer is the last place a barrier for it can go?

</details>

<details>
<summary>Hint 2: what the fence did, and did not do</summary>

A host fence wait orders execution and makes nothing visible
([Chapter 36, section 8](36-Terrain-To-The-Horizon.md#8-the-heightmap-on-the-gpu)). Ask rule 1 of the copy, a
write, and rule 2 of the GPU read; in the layer, follow `leftToHost` and `fenced` into `Begin`.

</details>

<details>
<summary>Hint 3: the toy's third frame</summary>

Section 3's toy group, frame 2, does both: `copy again` into the buffer the host read gets no barrier, and
`read results` on the GPU gets one. Read that frame's `because:` line: whose write does the read wait for, and from
which frame?

</details>

<details>
<summary>Worked solution: one barrier for the host, none for the next copy, one for a GPU reader</summary>

**The hand-over.** The last write is frame 2's copy, so the host's read is a read after write:
`barrierBetween(CopyWrite, HostRead)`, `COPY` / `TRANSFER_WRITE` to `HOST` / `HOST_READ`, which is D. It must be in
frame 2, after the copy and before the submit: the fence orders the copy before the host's read but makes nothing
visible, and no later command buffer can name a read that is not on the queue. The host's read joins no reader's
history: what was made visible to the host is visible to nothing on the device; `leftToHost` marks the buffer.

**Frame 4's copy.** Frame 4 records into slot 0 after its fence and after `ReadStatistics`, and `Begin` settles the
buffer, left to the host two frames ago and unused since: `fenced`, no reads. The copy is a write, and the fence
ordered the old copy and the host's read before frame 4 was submitted, so `fenced` drops the write term: no
barrier, the toy's "copy again".

**A GPU read instead.** D made the write visible to the host only, the host's read left only `leftToHost` behind,
so no reader has waited, and the fence made nothing visible: by rule 2 the read waits for frame 2's copy, `COPY` /
`TRANSFER_WRITE` to its own stage and read, an earlier submission inside the barrier's first scope: the toy's "read
results".

**The transfer.** Frame 3 does not wait for slot 0's fence, so its copy could land before the host reads frame 2's
numbers, and no barrier can order the host. The layer asserts in Debug at frame 3's copy,
`a resource left to the host is used again before its slot's fence`: hence one readback buffer per frame in flight
([Chapter 20, section 9](20-Compute-Fundamentals.md#9-reading-results-back-without-stalling)).

</details>

### Two mistakes worth trying

Make each, rebuild, run the test, and put the line back.

- **C6: drop the host's hand-over.** In `RecordReadback`, delete the line
  `    m_passes.Leave("the host", { { m_readback[frameIndex].buffer, uses::HostRead } });   // Chapter 57`, leaving
  D behind its guard. On the GPU it is a race: the host may read before the copy is visible to it. The test fails
  at the top of each frame where the host reads a buffer a declared frame copied into: the host reads
  `m_readback[0]`, and "copy statistics"' write "was never made visible to the host". One such frame passes: in
  "declared then hand at frame 2" the test credits hand frame 2's barrier to the host to frame 1's copy, though the
  host waited only on slot 1's fence (section 11). Sync validation says nothing: it does not look across a fence
  wait.
- **C2: declare the statistics on the counting step only.** In `RecordStep`, put the step's three uses in a local
  array, `const PassUse stepUses[]`, and pass `std::span(stepUses, countStatistics ? 3u : 2u)` to `Pass`. It shows
  at four steps a frame: the test's "Life, 4 steps", or **Steps per frame** on the GPU. Nothing races, since a step
  that does not count never runs the atomics, but the declaration breaks the Jump box's contract, and both checks
  that hold a dispatch to its static use see it. The test fails, `declares no use of m_statistics`, its model too.
  Sync validation, in the reference's run on the RTX 5090, reported a `SYNC-HAZARD-READ-AFTER-WRITE` at a
  `vkCmdDispatch` after the clear: by static use, step 0, the first dispatch whose shader uses them.

# Part 3 — Particles, and the first rule breaks (sections 6–8)

Every write in Life has one kind of reader, so section 3's first rule was enough. Particles hands its compute's
results to an indirect draw, a vertex shader and a copy: section 7 breaks the rule, section 8 replaces it.

## 6. Particles, ready to declare

The plumbing is section 4's, with three differences. **What is tracked:** the pool's particles, dead list, alive
lists (one buffer), counters and indirect arguments, the readback buffers, the sort's items, and the ramp,
rewritten after a curve edit and left by `Setup`'s upload in `SHADER_READ_ONLY_OPTIMAL`. The rule is that only a
resource some command of a frame writes is tracked and declared, but not the sky's images: what `m_sky.Update`
records writes them inside the frame, and the Sky types its own barriers for them. The frame and wind uniform
buffers and the ramp's staging buffer, written by the host after the slot's fence and made visible by the submit
itself, are left out, and so is the flipbook atlas, which only `Setup`'s bake writes though the curves look samples
it; a reader who later rebakes the atlas inside a frame must track it and declare its uses. Check order's buffer is
tracked while it exists (section 9); the engine's scene images arrive instead (section 10). **`Begin`'s place:**
after the CPU's work for the slot, before the first command, the ramp's copy after a curve edit. **An early
return:** a failed staging write of the ramp returns after `Begin`, and skipping `End` would leave `Declared()`
true outside the frame, so that path calls `End`.

### Where the code goes

No file is new. **`ParticlesDemo.h`.** Three edits, as Life's. The include goes directly under the line
`#include "PillowFort/Scene/Transform.h"`:

```cpp
#include "PillowFort/VulkanGraphics/DeclaredFrame.h"   // Chapter 57
```

the two public members directly under the line
`    void Frame(const ParticleFraming& framing);  // Chapter 54: points the orbit camera`, with a blank line
between:

```cpp
    // Chapter 57: record the barriers from what each pass declares, instead of the calls typed by hand,
    // and log the derived barriers of one frame (the explainFrame-th Record, counted from 0; -1 for none).
    void SetFrameRoute(bool declared, int explainFrame) { m_declaredBarriers = declared; m_explainFrame = explainFrame; }
    // Called at the end of Setup. Public because the supplied test calls it on its own fake handles, and MSVC gives a
    // private member another link name in a file that includes this header with private made public.
    void TrackResources();
```

and the state at the end of the class, directly under the line `    OrderCheck m_orderCheck;`, with a blank line
between:

```cpp
    // Chapter 57: the frame, declared.
    vulkan_graphics::DeclaredFrame m_passes;
    bool                           m_declaredBarriers = false;   // the panel's checkbox; hand by default
    bool                           m_explainNext      = false;   // the panel's button
    int                            m_explainFrame     = -1;      // --frame-explain
    int                            m_recordedFrames   = 0;
```

**`ParticleRamp.h`.** The ramp's image, for the list. Add this directly under the line
`    VkDescriptorSet       Set() const { return m_set; }`:

```cpp
    VkImage               Image() const { return m_ramp.image; }   // Chapter 57: named to the passes
```

**`ParticlesDemo.cpp`.** Nine edits. Replace the last line of `drawParticlePanel`'s parameter list,
`                              bool& checkOrder, const std::string& orderVerdict)`, with these two:

```cpp
                              bool& checkOrder, const std::string& orderVerdict,
                              bool& declaredBarriers, bool& explainNext)
```

The controls go at the panel's top level, after the **Pool** block. The first two lines below are already there,
the end of that block; add the rest directly under them, with the blank line shown:

```cpp
            reset |= ImGui::Button("Reset");
        }

        ImGui::SeparatorText("Barriers (Chapter 57)");
        pf::debug_panels::checkbox("Declared barriers", &declaredBarriers);
        ImGui::BeginDisabled(!declaredBarriers);
        explainNext |= ImGui::Button("Explain one frame");
        ImGui::EndDisabled();
```

In `Update`, replace the last line of the panel's call,
`                                          m_sortCount, m_orderCheck.requested, m_orderCheck.verdict);`, with these
two:

```cpp
                                          m_sortCount, m_orderCheck.requested, m_orderCheck.verdict,
                                          m_declaredBarriers, m_explainNext);
```

Add this directly under the line `    m_timestampsPending.fill(false);`, at the end of `Setup`:

```cpp
    TrackResources();   // Chapter 57
```

and the function directly above the line `InitializationResult ParticlesDemo::CreateBuffers()`, with a blank line
between. The `static_assert` is Life's. The ramp's name is the one `ParticleRamp`'s own code uses, because section
10 declares its copy there:

```cpp
// Chapter 57 section 6. Every buffer and image a command of the frame writes, but the sky's, whose barriers the Sky
// types itself. Setup's own barriers made each ready for its first reader; tracking promises that, and starts each
// history empty.
void ParticlesDemo::TrackResources()
{
    m_passes.Track(m_particles.buffer, "m_particles");
    m_passes.Track(m_deadList.buffer, "m_deadList");
    m_passes.Track(m_aliveLists.buffer, "m_aliveLists");   // both lists: one buffer
    m_passes.Track(m_counters.buffer, "m_counters");
    m_passes.Track(m_indirect.buffer, "m_indirect");
    static_assert(vulkan_graphics::FRAMES_IN_FLIGHT == 2, "one readback per slot");
    m_passes.Track(m_readback[0].buffer, "m_readback[0]");
    m_passes.Track(m_readback[1].buffer, "m_readback[1]");
    m_passes.Track(m_sort.Items(), "the sort's items");
    // Named as ParticleRamp's own code names it: its copy's barriers are the ones Explain prints.
    m_passes.Track(m_ramp.Image(), "m_ramp.image", VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
}
```

In `Record`, add these lines directly under the line
`    if (auto result = WriteWindSources(frameIndex); !result) { return result; }`, with a blank line between:

```cpp
    // Chapter 57: on the declared route the layer records each pass's barriers, and the typed calls step aside.
    const bool explain = m_recordedFrames++ == m_explainFrame || m_explainNext;
    m_explainNext = false;
    m_passes.Begin(commandBuffer, m_declaredBarriers, explain, "Particles");
```

Replace the line `        if (auto result = m_ramp.Stage(frameIndex, m_bake.table); !result) { return result; }`
with:

```cpp
        if (auto result = m_ramp.Stage(frameIndex, m_bake.table); !result)
        {
            m_passes.End();   // Chapter 57: the layer must not stay on the declared route outside a frame
            return result;
        }
```

Add this directly under the line `    handBackSceneTarget(commandBuffer, frame.targets);`, the frame's last
command:

```cpp
    for (const std::string& line : m_passes.End()) { Log::info(line.c_str()); }   // Chapter 57
```

and this in `Teardown`, directly under the line `    m_sky.Shutdown();   // Chapter 23`:

```cpp
    m_passes.Clear();   // Chapter 57
```

**`Main.cpp`.** Add this directly above the line
`    static_cast<demos::particles::ParticlesDemo&>(*demoList.back()).SetSoftDistance(settings.softDistance);`:

```cpp
    static_cast<demos::particles::ParticlesDemo&>(*demoList.back()).SetFrameRoute(declaredBarriers, settings.frameExplain);
```

**`DeclaredFrameTests.cpp`.** Replace the line `#define PF_TEST_STAGE 1` with:

```cpp
#define PF_TEST_STAGE 2
```

### Checkpoint

Rebuild and run the test as in section 4. Life is as section 5 left it. Particles' group runs three cases, the
default fountain, a reset with three prewarm steps and the fountain at 4x; nothing is declared, so the routes
match. "Particles, default fountain", frame 2:

```text
frame 2: no pass declared, so no declared use is checked
frame 2: hand 12 calls; declared 12 calls: 0 from the layer, 10 typed, 2 the engine's
```

The engine's two are `beginScenePass`'s barriers on the scene colour and depth, which neither route types; four at
4x. The report ends `PASS: toy, Life, Particles`, after the sort's and the curves' `SKIP:` lines.

## 7. Particles, declared, and the first rule breaks

Section 5's order again, over the compute, the copies out, the host's hand-over and the draw's buffers; the sort's,
Check order's, the images' and the ramp's barriers stay typed until sections 9 and 10. The last step makes the test
fail, on purpose.

### 7a. The passes and hand-overs declared

Each pass names what its shader can touch (static use, atomics as reads and writes) and what its command reads: an
indirect dispatch reads its size from `m_indirect`, `IndirectRead`. All eight edits are in `ParticlesDemo.cpp`.
Reset writes the counters and the dead list. In `RecordStep`, add these lines directly above the line
`        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_resetPipeline);`:

```cpp
        m_passes.Pass("reset", { { m_counters.buffer, uses::ComputeWrite },   // Chapter 57
                                 { m_deadList.buffer, uses::ComputeWrite } });
```

Begin reads and writes the counts and writes the dispatch sizes. Add these directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_beginPipeline);`:

```cpp
    m_passes.Pass("begin", { { m_counters.buffer, uses::ComputeReadWrite },   // Chapter 57
                             { m_indirect.buffer, uses::ComputeWrite } });
```

Emit pops free slots from the dead list with atomics on the counters, writes new particles and appends them to the
current list. Add these directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_emitPipeline);`:

```cpp
    m_passes.Pass("emit", { { m_indirect.buffer, uses::IndirectRead },   // Chapter 57
                            { m_counters.buffer, uses::ComputeReadWrite },
                            { m_deadList.buffer, uses::ComputeRead },
                            { m_particles.buffer, uses::ComputeWrite },
                            { m_aliveLists.buffer, uses::ComputeWrite } });
```

Simulate moves every particle, pushes the dead onto the dead list and appends the living to the other list. Add
these directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_simulatePipeline);`:

```cpp
    m_passes.Pass("simulate", { { m_indirect.buffer, uses::IndirectRead },   // Chapter 57
                                { m_counters.buffer, uses::ComputeReadWrite },
                                { m_deadList.buffer, uses::ComputeWrite },
                                { m_particles.buffer, uses::ComputeReadWrite },
                                { m_aliveLists.buffer, uses::ComputeReadWrite } });
```

End reads the survivors' count and writes the draw's arguments. Add these directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_endPipeline);`:

```cpp
    m_passes.Pass("end", { { m_counters.buffer, uses::ComputeRead },   // Chapter 57
                           { m_indirect.buffer, uses::ComputeWrite } });
```

The counters' copy is a pass named for the copies section 9 adds to it. In `RecordCompute`, add these directly
under the comment line `    // 7. Chapter 20 section 9: the counters, out to this slot's readback buffer.`:

```cpp
    m_passes.Pass("copies out", { { m_counters.buffer, uses::CopyRead },   // Chapter 57
                                 { m_readback[frameIndex].buffer, uses::CopyWrite } });
```

The readback leaves to the host, as Life's did. Add this directly above the three lines of the `memoryBarrier` call
that ends `VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);`, near the end of `RecordCompute`:

```cpp
    m_passes.Leave("the host", { { m_readback[frameIndex].buffer, uses::HostRead } });   // Chapter 57
```

The draw reads its arguments, the particles and the alive list; its images join it in section 10. In
`RecordParticles`, add these directly above the comment line
`    // The scene pass left color in COLOR_ATTACHMENT_OPTIMAL and depth in`:

```cpp
    // Chapter 57: what the draw reads; the images join them in section 10.
    m_passes.Pass("particles", { { m_indirect.buffer, uses::IndirectRead },
                                { m_particles.buffer, uses::VertexStorageRead },
                                { m_aliveLists.buffer, uses::VertexStorageRead } });
```

**Check 7a.** "Particles, default fountain":
`frame 2: hand 12 calls; declared 18 calls: 6 from the layer, 10 typed, 2 the engine's` (frame 0:
`frame 0: hand 12 calls; declared 17 calls: 5 from the layer, 10 typed, 2 the engine's`). The layer's six stand
before begin, emit, simulate, end and the draw, and at the host's hand-over; none before the copy, where your E
still is.

### 7b. R, the two c2c, B, A and H

Each barrier now has passes that ask for it: begin and emit for R; simulate and end for the c2c's; emit for B,
arguments and storage; begin and emit for A, each for what it touches; the `Leave` for H. In `RecordStep`, replace
the line `        computeToComputeBarrier(commandBuffer);` directly above the line
`        m_resetRequested = false;` with:

```cpp
        if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

the line `    computeToComputeBarrier(commandBuffer);` directly above the line
`    if (lastInFrame) { WriteTimestamp(commandBuffer, frameIndex, 1); }` with:

```cpp
    if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

and the line `    computeToComputeBarrier(commandBuffer);` directly above the line
`    if (lastInFrame) { WriteTimestamp(commandBuffer, frameIndex, 2); }` with:

```cpp
    if (!m_passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

Replace the five lines of the `memoryBarrier` call directly under the comment line
`    // as storage by their shaders.` (B) with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT
                          | VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
```

and the six lines of the `memoryBarrier` call directly under the comment line
`    //    frame's first, where the previous step's passes are the readers and writers.` (A) with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                          | VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                      VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
```

Last, in `RecordCompute`, replace the three lines of the host's `memoryBarrier` call, directly under the `Leave`
you added in step 7a, with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    }
```

**Check 7b.** `frame 2: hand 12 calls; declared 13 calls: 6 from the layer, 5 typed, 2 the engine's` (frame 0:
`frame 0: hand 12 calls; declared 12 calls: 5 from the layer, 5 typed, 2 the engine's`). Not every derived call is
a twin. `VERTEX_SHADER` moves from A's source to the barrier before emit, which overwrites what last frame's vertex
shader read. The barrier before end also names `DRAW_INDIRECT`, where emit and simulate read `m_indirect`; end
writes only the draw arguments, other bytes, but the layer sees whole buffers (section 11).

### 7c. E, the end barrier

E hands the step's results to everything after the compute: the arguments to the indirect draw, the particles and
the list to the vertex shader, the counters to the copy. The draw's half has a pass that asks for it, "particles",
after the scene pass; the copy's has "copies out". In `RecordStep`, replace the six lines of the `memoryBarrier`
call directly under the comment line `    // alive list, and the copy of the counters after the last step.` with:

```cpp
    if (!m_passes.Declared())
    {
        memoryBarrier(commandBuffer,
                      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                          | VK_PIPELINE_STAGE_2_COPY_BIT,
                      VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_READ_BIT
                          | VK_ACCESS_2_TRANSFER_READ_BIT);
    }
```

**Check 7c.** `frame 2: hand 12 calls; declared 12 calls: 6 from the layer, 4 typed, 2 the engine's`. The four
typed are P1 to P3 and the hand-back, section 10's. This run already fails; the failure follows below.

### Checkpoint

Rebuild and run the test. It fails, and exits with a nonzero code, so the script's last line throws; that is
expected here. The first `FAIL:` line is:

```text
FAIL: Particles, default fountain (declared): frame 0, command 7: READ-AFTER-WRITE: "copies out" (command 7) reads m_counters at COPY/TRANSFER_READ; "simulate" (command 4) wrote it
```

It prints ten, then `FAIL: 10 failures`, and all ten are this one hazard, in each declared frame of each Particles
case; command numbers count barriers too. The fountain's frame 2 gap view shows end's derived barrier, then the
copy, with your E on the hand route and nothing on the declared one:

```text
   gap before vkCmdDispatch
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE)
      declared: memoryBarrier(DRAW_INDIRECT|COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE) [layer]
   gap before vkCmdCopyBuffer(m_counters -> m_readback[0])
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> DRAW_INDIRECT|VERTEX_SHADER|COPY/INDIRECT_COMMAND_READ|TRANSFER_READ|SHADER_STORAGE_READ)
```

**Why.** The layer did what section 3's first rule says. Simulate's atomics wrote `m_counters`; end reads them in a
compute shader, so before end the layer derived a read after write, `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` to
`COMPUTE_SHADER` / `SHADER_STORAGE_READ`, and set the bool: a reader has waited. "copies out" then reads the
counters with a copy, the bool says a reader waited, and the copy gets nothing. But end's barrier made the write
visible to its second scope, compute shaders, and to nothing else. Nor did it order the copy: `COPY` is in no
destination mask since simulate, so the copy may run before simulate's atomics finish. The copy is a new kind of
reader, and nothing between simulate and it made the write visible to it; on the hand route E did, with `COPY` /
`TRANSFER_READ` in its destination.

**On the GPU** this is a race: the copy can read counts not yet made available. The reference ran the first rule on
the GPU (the finished tree with section 8's edits reversed, the fountain, declared): sync validation reported
`SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdCopyBuffer`, "which was previously written by vkCmdDispatch", up to ten
times, its message limit, not a count. The test names simulate. Validation names only a `vkCmdDispatch`; since it
records an atomic as a read, the writer it means is begin, the last plain dispatch to write the counters.

**Running this tree.** It races on the declared route by design: the counters' copy, and, with the sort on and
**Check order** pressed, Check order's copies too. If you run it at all, run it with the sort off and Check order
unpressed. The race is the point of this section; section 8 removes it.

**Not yet true.** Until section 9 declares the sort, the layer does not know that the sort writes the alive lists
and its items. In this tree and section 8's, with the sort on, both are correct only because the layer's barriers
are global memory barriers, and terms recorded for other resources in the same barrier cover them. The layer's
history of them is wrong until section 9.

## 8. Made visible to whom

A barrier makes a write visible to the uses in its second scope, its stages and accesses, and to no others. So in
place of the bool the history keeps those uses, the **visible set**: every use the last write has been made visible
to. A read is covered when one use in the set has all of its stages and all of its read accesses; otherwise it
waits for the write, and its use joins the set. A new write empties the set. That is rule 2 as section 8 asks it,
whom the write was made visible to, in code.

### Where the code goes

No file is new. One member changes in `DeclaredFrame.h`, and `DeclaredFrame.cpp` changes in six places.
**`DeclaredFrame.h`.** In `Resource`, replace the six lines from
`        // The last write, and whether any reader has waited for it (section 3's first rule; section 8 replaces it).`
to `        bool                     waited     = false;` with these six; the four between are unchanged:

```cpp
        // The last write, and the uses it has been made visible to.
        bool                     written    = false;
        ResourceUse              write{};
        const char*              writer     = "";
        uint64_t                 writeFrame = 0;
        std::vector<ResourceUse> visibleTo;
```

**`DeclaredFrame.cpp`.** An image that arrives after a read: its owner made the write before it visible to that
read, and to nothing else the layer knows of. In `Arrive`, replace the comment line
`        // Whatever wrote it last was made visible to this read.` with these two:

```cpp
        // Whatever wrote it last was made visible to this read, and to nothing else we know of.
        arrived.visibleTo  = { lastUse };
```

In `Record`, the rule's comment: replace the line
`        // A read waits for the last write unless some reader has already waited for it.` with:

```cpp
        // A read waits for the last write unless that write was already made visible to its kind of reader.
```

The read's branch. `covered` asks the set for one use with all of this read's stages and read bits; a read not
covered waits for the write, as before. An arrived image has no write the layer knows, so a reader of another kind
waits for the arrived read's stages, which chains it after the owner's barrier, and names its own access, a
`because:` line of an eighth kind, read after an arrived read. Replace the four lines from
`        else if (reads && resource.written && !resource.waited)` to the `        }` that closes that branch with:

```cpp
        else if (reads && (resource.written || !resource.visibleTo.empty()))
        {
            const bool covered = std::ranges::any_of(resource.visibleTo, [&](const ResourceUse& seen) {
                return (use.stage & ~seen.stage) == 0 && (readAccess(use.access) & ~seen.access) == 0;
            });
            if (!covered && resource.written) { add(barrierBetween(resource.write, use), "read after write", writer()); }
            // An image that arrived after a read: its write was made visible to that read only.
            else if (!covered)
            {
                add({ resource.readStages, VK_ACCESS_2_NONE, use.stage, use.access }, "read after an arrived read",
                    readersNamed());
            }
        }
```

Then the history after the use. A write is visible to nobody yet: replace the line
`            resource.waited     = false;` with:

```cpp
            resource.visibleTo.clear();
```

A layout change is a write its own barrier made visible to this use (rule 3): replace the line
`            resource.waited     = true;` with:

```cpp
            resource.visibleTo  = { use };
```

A read that waited in this pass's barrier joins the set; a covered read adds nothing. Replace the line
`            if (any) { resource.waited = true; }` with:

```cpp
            if (any) { resource.visibleTo.push_back(use); }
```

`covered` asks one use at a time, not the set's union, so a read that only two uses together would cover waits
again: a barrier more, never one less.

### Checkpoint

Rebuild and run the test. It passes again and ends `PASS: toy, Life, Particles`. "Particles, default fountain":
`frame 2: hand 12 calls; declared 13 calls: 7 from the layer, 4 typed, 2 the engine's`, the seventh before the
copy, `declared: memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COPY/TRANSFER_READ) [layer]`. E is now two
derived barriers, its copy half and its draw half: one call more than by hand. Life's lines do not change, and
section 7's caution about the alive lists and the items holds until section 9.

<a id="ch57-new-reader"></a>

### Attempt CH57-new-reader: a reader the write was not made visible to

Predict first. In the fountain's last step simulate's atomics write `m_counters`. Three later uses meet that write:
end's compute read, the copy in "copies out", and next frame's begin, which reads and writes the counters. For
each, what term does the layer record for simulate's write, and which of the three would section 3's bool have
answered differently?

Write down what the visible set holds as each use arrives and after it, then say in one sentence, naming a second
scope, why "copies out" needs a barrier for a write compute has already waited for.

**Acceptance:** end's term ends at `COMPUTE_SHADER` / `SHADER_STORAGE_READ` and the copy's at `COPY` /
`TRANSFER_READ`, both from `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE`; begin's come from rule 1 and empty the set.
Only the copy's answer differs from the bool's.

**Transfer:** with the sort off, after the draw's barrier, the particles' set holds `VertexStorageRead`. A second
draw in the same frame reads the particles in its vertex shader, and a third in a fragment shader. Which needs a
barrier, and what would the bool have given each?

<details>
<summary>Hint 1: to whom a barrier makes a write visible</summary>

A barrier's destination half is its second scope: the stages that wait and the accesses the write is made visible
to. End's term for the counters names `COMPUTE_SHADER` and `SHADER_STORAGE_READ`. What does a copy run at, and read
with?

</details>

<details>
<summary>Hint 2: a write does not ask</summary>

Rule 1 waits for the last write and every read since, whatever was made visible to whom; after it, nothing has seen
the new write.

</details>

<details>
<summary>Hint 3: the bool's one answer</summary>

Under section 3's rule, end's barrier sets `waited` for the counters' write. What does the copy's read ask then,
and what answer does it get? Section 7's failing line is that answer.

</details>

<details>
<summary>Worked solution: end, the copy, and next frame's begin</summary>

**End.** Simulate's write has an empty set, so end's read waits: a read after write, joined into end's barrier with
its terms for `m_indirect`. The set becomes `{ ComputeRead }`; the bool agrees.

**The copy.** The set's one use has neither `COPY` nor `TRANSFER_READ`, so the copy waits too, Chapter 4's
"Compute-written counters copied for readback", and the set becomes `{ ComputeRead, CopyRead }`. End's barrier made
the write visible to its second scope, compute shaders, and neither ordered the copy nor made the write visible to
it: a new kind of reader needs a barrier of its own though nothing was written in between. The bool gave it
nothing, section 7's failure.

**Next frame's begin.** A write, so rule 1: a write after write for the atomics, a write after read for end's and
the copy's reads, and the set empties. A write asks neither the bool nor the set.

**The transfer.** The second vertex-shader read is covered and needs nothing. The fragment shader's is not,
`FRAGMENT_SHADER` being in no use of the set, so it waits for the last write; the bool would have given it nothing.

</details>

### A mistake worth trying

- **C1: declare an atomic as a read.** In `LifeDemo.cpp`'s `RecordStep`, change the statistics' use in the step's
  pass from `uses::ComputeReadWrite` to `uses::ComputeRead`. The layer orders only the writes it is told about: it
  now takes the clear as the statistics' last writer, so nothing makes the atomics' writes available to the copy, a
  race on the GPU. The test fails, `m_statistics is written as SHADER_STORAGE_WRITE, declared as NONE`, and its
  model reports the copy's read after the step's write. Sync validation is silent: an atomic is a read to it, so it
  agrees with the mistake. Put `uses::ComputeReadWrite` back.

Part 4 declares what is still typed, starting with the sort and Check order in section 9.

# Part 4 — The whole frame (sections 9–11)

Two groups of typed calls are left on the declared route: the sort's, with Check order's around its first copy, and
the draw's, with the engine's two images and the ramp. Section 9 declares the first and section 10 the second, and
section 11 says what catches each kind of mistake and what stays by hand.

## 9. The sort and Check order

Chapter 55's sort is one pipeline with one set of four storage buffers, the particles, the alive lists, the
counters and the items, and five passes picked by a word in the push constants
([Chapter 55, section 3](55-Sorted-Smoke.md#3-the-sort-on-the-gpu)). By hand, S, a compute-to-compute barrier,
follows every dispatch, and K1 and K2 stand around Check order's first copy
([Chapter 55, section 4](55-Sorted-Smoke.md#4-checking-the-sort)). On the declared route each dispatch is a pass.

**What a sort pass declares.** By its word, KEYS reads the particles, the list and the counters and writes the
items; WRITE_BACK reads the counters and the items and writes the list; the three passes between them work on the
items alone. But the word is a push constant, and the pipeline and its set are the same in every pass, so the
shader can touch all four buffers in each. Section 5's contract decides: a dispatch is declared by its shader's
static use, as sync validation's heuristic and the test's tables judge it. So every sort pass declares the
particles and the counters `ComputeRead`, and the lists and the items `ComputeReadWrite`. Between two sort passes
those uses give one barrier, the one S types.

**Where the barriers move.** A barrier is credited only to the resources it was recorded for (rule 5). By hand,
KEYS relies on the barrier after simulate, which, being a memory barrier, covered every buffer. On the declared
route that barrier stands before "end" and was recorded for end's uses, the counters and the draw's arguments, so
the layer records another before KEYS, for the particles, the lists and the items. After WRITE_BACK it records
none, where the hand route has S: what the sort wrote is read next by the draw, and on a check by its copies, and
those get barriers of their own. The sort's count is the same on both routes.

**Check order.** Its buffer is created when a check is armed and destroyed when the slot comes round, so it is
tracked when created, with an empty history that is simply true, and forgotten before it is destroyed: the layer
knows a resource by its handle, and a later buffer may get the same one. The test checks the tracked list after
every frame. K1 and K2 become a pass, "list before the sort", a copy that reads the lists and writes the buffer:
K1's job is derived before it, and K2's joins the barrier before KEYS as a write after read on the lists. On the
frame that records the copies, "copies out" and the host hand-over take Check order's uses too. Its three copies
and the counters' copy are one pass with no barrier between them, because they write different buffers, or
different ranges of one. The layer sees whole buffers, though, so on that frame "copies out" also waits for "list
before the sort"'s write to the same buffer: a `COPY`/`TRANSFER_WRITE` to `COPY`/`TRANSFER_WRITE` term that the
hand route does not type.

Those uses depend on a CPU choice, so they are local arrays passed with a count, through the `std::span` forms of
`Pass` and `Leave` (section 3). The arrays live on the stack and allocate nothing; on a frame with no check, the
count leaves out Check order's entries. The block of copies clears `m_orderCheck.armed`, so the frame copies the
flag into `armed` first.

### Where the code goes

No file is new. **`ParticleSort.h`.** Four edits. Add the layer's header directly under the line
`#include "PillowFort/ErrorReporting/InitializationResult.h"`:

```cpp
#include "PillowFort/VulkanGraphics/DeclaredFrame.h"   // Chapter 57
```

`Record` takes the frame's layer. Replace the last line of its declaration,
`                                  const glm::vec3& cameraPosition, const glm::vec3& cameraForward);`, with these
two:

```cpp
                                  const glm::vec3& cameraPosition, const glm::vec3& cameraForward,
                                  vulkan_graphics::DeclaredFrame& passes);   // Chapter 57
```

`Initialize` writes the three buffers it borrows into the set and keeps none of them; the passes need to name them.
Add these four lines directly under the line
`    vulkan_graphics::AllocatedBuffer m_items;           // uvec2 (key, slot) per entry, the capacity's worth`:

```cpp
    // Chapter 57: the three borrowed buffers, kept so the passes can name them.
    VkBuffer              m_particles  = VK_NULL_HANDLE;
    VkBuffer              m_aliveLists = VK_NULL_HANDLE;
    VkBuffer              m_counters   = VK_NULL_HANDLE;
```

Three comments describe barriers that are now typed on the hand route only. Above `Record`, replace the line
`    // more and held to the capacity here. A barrier follows every dispatch. Returns that padded size.` with:

```cpp
    // more and held to the capacity here. By hand, a barrier follows every dispatch; on the declared route the layer
    // derives them from the passes. Returns that padded size.
```

In `ParticleSort.cpp`, replace the line
`    // Each dispatch reads what the one before it wrote, so a barrier follows every one.` with:

```cpp
    // Each dispatch reads what the one before it wrote, so by hand a barrier follows every one; on the declared
    // route the layer derives them from the passes.
```

and in `ParticlesDemo.cpp`'s `RecordStep`, replace the line
`    // so nothing stands between them, and the end barrier below covers the sort's write-back for the draw.` with:

```cpp
    // so nothing stands between them, and the end barrier below covers the sort's write-back for the draw (by
    // hand; on the declared route the layer derives these barriers from the passes).
```

**`ParticleSort.cpp`.** Five more edits. Add this directly under the line `#include <bit>`, for `std::size`:

```cpp
#include <iterator>
```

In `Initialize`, replace the two lines `    m_vulkan   = context;` and `    m_capacity = capacity;` with these
five, aligned again:

```cpp
    m_vulkan     = context;
    m_capacity   = capacity;
    m_particles  = particles;    // Chapter 57
    m_aliveLists = aliveLists;
    m_counters   = counters;
```

In `Record`'s definition, replace the line above its opening brace,
`                              const glm::vec3& cameraPosition, const glm::vec3& cameraForward)`, with these two:

```cpp
                              const glm::vec3& cameraPosition, const glm::vec3& cameraForward,
                              DeclaredFrame& passes)
```

Every dispatch goes through the `dispatch` lambda, so the pass is declared there. Its name comes from the pass
word, and the test's tables allow each sort dispatch only its own name, so type them as printed. Add these lines
directly under the lambda's first line,
`    const auto dispatch = [&](uint32_t pass, uint32_t k, uint32_t j, uint32_t groups) {`:

```cpp
        // Chapter 57: the one shader binds all four buffers in every pass, whatever the pass word says,
        // so every dispatch declares all four.
        static constexpr const char* names[] = { "sort: keys", "sort: block sort", "sort: global step",
                                                 "sort: block merge", "sort: write back" };
        passes.Pass(pass < std::size(names) ? names[pass] : "sort",
                    { { m_particles, uses::ComputeRead }, { m_aliveLists, uses::ComputeReadWrite },
                      { m_counters, uses::ComputeRead }, { m_items.buffer, uses::ComputeReadWrite } });
```

S steps aside. Replace the line `        computeToComputeBarrier(commandBuffer);` under
`        vkCmdDispatch(commandBuffer, groups, 1, 1);` with:

```cpp
        if (!passes.Declared()) { computeToComputeBarrier(commandBuffer); }
```

**`ParticlesDemo.cpp`.** Ten more edits. Add these two directly under the line `#include <format>`:

```cpp
#include <iterator>
#include <span>
```

In `RecordStep`, the sort gets the layer: replace the `m_sort.Record` call's second line,
`                                        m_cameraTransform.translation, m_cameraTransform.Forward());`, with:

```cpp
                                        m_cameraTransform.translation, m_cameraTransform.Forward(), m_passes);
```

In `Record`, the buffer is tracked as soon as a check has one. Add this directly under the line
`        m_orderCheck.armed  = m_orderCheck.buffer.buffer != VK_NULL_HANDLE;`:

```cpp
        if (m_orderCheck.armed) { m_passes.Track(m_orderCheck.buffer.buffer, "Check order's buffer"); }   // Chapter 57
```

In `ReadOrderCheck`, it is forgotten before either `destroyBuffer`. Inside the branch for a failed readback, add
this directly above the line `        destroyBuffer(m_vulkan, check.buffer);`:

```cpp
        m_passes.Forget(check.buffer.buffer);   // Chapter 57: a later buffer may get this handle
```

and after the branch, directly above the line `    destroyBuffer(m_vulkan, check.buffer);` that a blank line and
`    const uint32_t* before = data.data();` follow, add:

```cpp
    m_passes.Forget(check.buffer.buffer);   // Chapter 57
```

Back in `RecordStep`, inside `if (m_orderCheck.armed)`, the copy before the sort becomes a pass and K1 steps aside.
Replace the three lines of the first `memoryBarrier` call, directly under the line
`                const VkDeviceSize listBytes = sizeof(uint32_t) * static_cast<VkDeviceSize>(m_settings.maxParticles);`,
with:

```cpp
                m_passes.Pass("list before the sort", { { m_aliveLists.buffer, uses::CopyRead },   // Chapter 57
                                                        { m_orderCheck.buffer.buffer, uses::CopyWrite } });
                if (!m_passes.Declared())
                {
                    memoryBarrier(commandBuffer,
                                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
                }
```

and K2, the three lines of the second, directly under the line
`                vkCmdCopyBuffer(commandBuffer, m_aliveLists.buffer, m_orderCheck.buffer.buffer, 1, &before);`,
with:

```cpp
                if (!m_passes.Declared())
                {
                    memoryBarrier(commandBuffer,
                                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_NONE,
                                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
                }
```

In `RecordCompute`, replace section 7's two lines, from
`    m_passes.Pass("copies out", { { m_counters.buffer, uses::CopyRead },   // Chapter 57` to
`                                 { m_readback[frameIndex].buffer, uses::CopyWrite } });`, with these seven:

```cpp
    // Chapter 57: Check order's three copies join the counters' when this frame records them.
    const bool armed = m_orderCheck.armed;
    const PassUse copyUses[] = {
        { m_counters.buffer, uses::CopyRead }, { m_readback[frameIndex].buffer, uses::CopyWrite },
        { m_sort.Items(), uses::CopyRead }, { m_aliveLists.buffer, uses::CopyRead },
        { m_orderCheck.buffer.buffer, uses::CopyWrite } };
    m_passes.Pass("copies out", std::span(copyUses, armed ? std::size(copyUses) : size_t{ 2 }));
```

Below the counters' copy, Chapter 55's comment on Check order's other copies is true by hand only. The first line
below, the comment's last, is already there; replace the line under it, `    if (m_orderCheck.armed)`, with the
other two:

```cpp
    // to copies, and the barrier below makes these copies visible to the host, as the counters' copy.
    // (By hand; on the declared route the layer derives those barriers from the passes.)
    if (armed)
```

Last, replace section 7's hand-over, the line
`    m_passes.Leave("the host", { { m_readback[frameIndex].buffer, uses::HostRead } });   // Chapter 57`, with:

```cpp
    const PassUse hostUses[] = { { m_readback[frameIndex].buffer, uses::HostRead },   // Chapter 57
                                 { m_orderCheck.buffer.buffer, uses::HostRead } };
    m_passes.Leave("the host", std::span(hostUses, armed ? std::size(hostUses) : size_t{ 1 }));
```

**The supplied test.** Stage 3 builds its sort cases, which name the members `ParticleSort` now keeps. In
`Tests/TutorialHarness/DeclaredFrameTests.cpp`, change the `2` in the line `#define PF_TEST_STAGE 2` to `3`:

```cpp
#define PF_TEST_STAGE 3
```

### Checkpoint

No file is new. Build `TutorialDeclaredFrameTests` and run it from the repository root, as in section 4.

- **The sort runs.** Each sort case keeps four typed calls a frame, P1, P2, P3 and the hand-back, the draw's, which
  section 10 declares. None is the sort's or Check order's:

```text
==== Particles, sort on, n 1,024
frame 0: hand 15 calls; declared 15 calls: 9 from the layer, 4 typed, 2 the engine's
frame 1: hand 15 calls; declared 16 calls: 10 from the layer, 4 typed, 2 the engine's
frame 2: hand 15 calls; declared 16 calls: 10 from the layer, 4 typed, 2 the engine's
```

- At n 4,096, frame 1 reads
  `frame 1: hand 20 calls; declared 21 calls: 15 from the layer, 4 typed, 2 the engine's`, and in the case
  "Particles, sort on, Check order at frame 1", the frame Check order records reads
  `frame 1: hand 17 calls; declared 17 calls: 11 from the layer, 4 typed, 2 the engine's`.
- **Where the sort's barriers went.** The gap view of n 1,024's frame 2, its four gaps from KEYS to the counters'
  copy. Before KEYS there is a declared barrier and none by hand; before the copy, two by hand, S after WRITE_BACK
  and E, and one declared, E's copy half:

```text
   gap before vkCmdDispatch
      declared: memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE) [layer]
   gap before vkCmdDispatch
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE)
      declared: memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE) [layer]
   gap before vkCmdDispatch
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE)
      declared: memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE) [layer]
   gap before vkCmdCopyBuffer(m_counters -> m_readback[0])
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COMPUTE_SHADER/SHADER_STORAGE_READ|SHADER_STORAGE_WRITE)
      hand:     memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> DRAW_INDIRECT|VERTEX_SHADER|COPY/INDIRECT_COMMAND_READ|TRANSFER_READ|SHADER_STORAGE_READ)
      declared: memoryBarrier(COMPUTE_SHADER/SHADER_STORAGE_WRITE -> COPY/TRANSFER_READ) [layer]
```

- The report ends with `SKIP: curves: PF_TEST_STAGE is below 4 (Chapter 57, section 10 raises it)`, a blank line,
  and `PASS: toy, Life, Particles, sort`.

**A mistake worth trying, C4: each sort pass declared by its word.** It looks more precise. In `ParticleSort.cpp`,
replace the `passes.Pass` call's two lines of uses, the ones that start
`                    { { m_particles, uses::ComputeRead },` and
`                      { m_counters, uses::ComputeRead },`, with this:

```cpp
                    pass == PARTICLE_SORT_PASS_KEYS
                        ? std::initializer_list<vulkan_graphics::PassUse>{ { m_particles, uses::ComputeRead }, { m_aliveLists, uses::ComputeRead },
                                                                          { m_counters, uses::ComputeRead }, { m_items.buffer, uses::ComputeWrite } }
                        : pass == PARTICLE_SORT_PASS_WRITE_BACK
                        ? std::initializer_list<vulkan_graphics::PassUse>{ { m_aliveLists, uses::ComputeWrite }, { m_counters, uses::ComputeRead },
                                                                          { m_items.buffer, uses::ComputeRead } }
                        : std::initializer_list<vulkan_graphics::PassUse>{ { m_items.buffer, uses::ComputeReadWrite } });   // CONTROL C4
```

Rebuild and run the test: every declared frame that sorts fails at "sort: keys" with
`m_aliveLists is written as SHADER_STORAGE_WRITE, declared as NONE`, and at each later sort pass with
`declares no use of m_particles`, Check order or not; on the Check order frame the model adds a write after read at
KEYS. Build the game and run Smoke on the declared route,
`--demo Particles --particle-preset smoke --frame-route declared`, then press **Check order**. Nothing races: by
its word KEYS writes only the items. Validation is quiet until Check order, then reports one write after read at
KEYS' `vkCmdDispatch`. It judges KEYS by its shader, which may write the lists that the copy before the sort has
just read, and the narrow declaration gave the barrier before KEYS nothing that waits for that copy. Without the
copy, the barrier's terms for other resources happen to cover KEYS. Put the two lines back.

## 10. The draw, the engine's images, the ramp

The draw is the last pass with typed barriers, and the first whose images are not the demo's. The scene's colour
and depth are the engine's: `beginScenePass` and `endScenePass` record the scene pass with barriers of their own,
the engine builds the images again when the window changes size, and its own passes use them between this demo's
frames. So they are not tracked. They arrive, as Life's scene image did in section 5: after `endScenePass`,
`Arrive` gives each this frame's history, the scene pass's write, and `End` drops it (rule 8). `SceneDepthWrite`
names both of the depth's writers, the tests at 1x and the resolve with MSAA
([Chapter 18, section 5](18-Anti-Aliasing.md#5-resolving-under-dynamic-rendering)), as P2's source does.

The draw's pass grows from section 7's three buffers to six uses. The colour, `ColorBlend`, is read and written in
the layout the scene pass left; an image not in `GENERAL` gets its own `transitionImage` (rule 3), so that is P1.
The depth, `DepthTestAndSample`, is read by the depth test and by the soft fade
([Chapter 21, section 9](21-GPU-Particles.md#9-exercise-soft-particles)) in the read-only layout: P2. The ramp,
`VertexSampled`, is read only by the curves look's vertex shader, through set 2, which no other look binds; it goes
last in the array so the count can leave it out, and `curvesLook` moves up to the pass. After the draw, the depth
goes back to the next scene pass in the layout
[Chapter 10, section 9](10-Cameras-And-Depth.md#9-the-depth-buffer)'s scene pass expects, as Chapter 21's return
trip does: `DepthAttachment` is a write after the draw's reads, P3, whose source names the fragment stage for the
soft fade. The colour goes to the engine's composite, `SampledByComposite`: the hand-back. Next frame the scene
pass begins with `beginScenePass`'s own barriers on both images. No route types those; the test counts them as the
engine's, two at 1x and four at 4x.

**The ramp.** After a curve edit, the frame copies the new table into the image before anything else
([Chapter 54, section 6](54-Shaping-A-Particle-Effect.md#6-one-image-rewritten-inside-the-frame)), between R1 and
R2. On the declared route that copy is a pass, "ramp copy", whose use, `CopyOverwrite`, rewrites every texel: the
reason R1's old layout is `UNDEFINED`. A hand-over to "the vertex shaders" takes R2's place, because the image must
be back in `SHADER_READ_ONLY_OPTIMAL` whichever look draws next: set 2 was written with that layout, and section
6's `Track` promised it. `Setup`'s `Upload` records the same commands, outside any frame, into `immediateSubmit`'s
command buffer. So the function both share takes a pointer to the layer: `Upload` passes null, and the typed calls
stay when it is null or the route is hand. `RecordCopy`, which only a frame calls, takes a reference.

### Where the code goes

No file is new. **`ParticlesDemo.cpp`.** Eight edits. In `Record`, add these lines directly under the line
`    endScenePass(commandBuffer);`:

```cpp
    // Chapter 57: the scene pass is another owner's; the images arrive as it left them.
    m_passes.Arrive("the scene pass", frame.targets.colorImage, "targets.colorImage", uses::SceneColorWrite);
    m_passes.Arrive("the scene pass", frame.targets.depthImage, "targets.depthImage", uses::SceneDepthWrite,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
```

In `RecordParticles`, replace the four lines from
`    // Chapter 57: what the draw reads; the images join them in section 10.` to
`                                { m_aliveLists.buffer, uses::VertexStorageRead } });` with these eight:

```cpp
    // Chapter 57: the draw's uses of the resources a command of the frame writes. The ramp is read only by the curves
    // look; the flipbook atlas it also samples is written only by Setup's bake, so it is not tracked.
    const bool curvesLook = m_settings.lookKind == LOOK_CURVES;
    const PassUse drawUses[] = {
        { m_indirect.buffer, uses::IndirectRead }, { m_particles.buffer, uses::VertexStorageRead },
        { m_aliveLists.buffer, uses::VertexStorageRead }, { targets.colorImage, uses::ColorBlend },
        { targets.depthImage, uses::DepthTestAndSample }, { m_ramp.Image(), uses::VertexSampled } };
    m_passes.Pass("particles", std::span(drawUses, curvesLook ? std::size(drawUses) : std::size(drawUses) - 1));
```

The line `    const bool curvesLook = m_settings.lookKind == LOOK_CURVES;` is now in the function twice. Further
down, delete the old one, directly above the line
`    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS,`.

P1 steps aside. Replace the five lines of the `transitionImage` call on `targets.colorImage`, under the comment
line `    // the depth test only reads the depth, so it moves to the read-only layout.`, with:

```cpp
    if (!m_passes.Declared())
    {
        transitionImage(commandBuffer, targets.colorImage,
                        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                        VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    }
```

So does P2: replace the nine lines of the `transitionImage` call on `targets.depthImage`, under the comment line
`    // the source names both.`, with:

```cpp
    if (!m_passes.Declared())
    {
        transitionImage(commandBuffer, targets.depthImage,
                        VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                            | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                            | VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                        VK_IMAGE_ASPECT_DEPTH_BIT);
    }
```

At the end of the function, the depth's return trip becomes a hand-over. Add this directly under the comment line
`    // frame's scene pass expects, after this pass's depth tests have read it.`:

```cpp
    // Chapter 57: DepthAttachment is the 1x use. At 4x the next scene pass writes this image only by its depth resolve,
    // at COLOR_ATTACHMENT_OUTPUT, after the engine's own barrier, whose source names the fragment tests and so chains.
    m_passes.Leave("the next scene pass", { { targets.depthImage, uses::DepthAttachment } });   // Chapter 57
```

and replace P3, the eight lines of the `transitionImage` call under it, with:

```cpp
    if (!m_passes.Declared())
    {
        transitionImage(commandBuffer, targets.depthImage,
                        VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                            | VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                        VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                        VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                        VK_IMAGE_ASPECT_DEPTH_BIT);
    }
```

In `Record`, replace the line `    handBackSceneTarget(commandBuffer, frame.targets);` with:

```cpp
    m_passes.Leave("the composite", { { frame.targets.colorImage, uses::SampledByComposite } });   // Chapter 57
    if (!m_passes.Declared())
    {
        handBackSceneTarget(commandBuffer, frame.targets);
    }
```

**`ParticleRamp.h`.** Three edits. Add this directly under the line
`#include "PillowFort/ErrorReporting/InitializationResult.h"`:

```cpp
#include "PillowFort/VulkanGraphics/DeclaredFrame.h"   // Chapter 57
```

Replace the line `    void                 RecordCopy(VkCommandBuffer commandBuffer, uint32_t frameIndex);` with
these two:

```cpp
    void                 RecordCopy(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                    vulkan_graphics::DeclaredFrame& passes);   // Chapter 57: only Setup's Upload has no frame
```

and the line
`    void RecordCopyCommands(VkCommandBuffer commandBuffer, VkBuffer source);   // the two barriers and the copy`
with these two:

```cpp
    void RecordCopyCommands(VkCommandBuffer commandBuffer, VkBuffer source,
                            vulkan_graphics::DeclaredFrame* passes);   // the two barriers and the copy
```

**`ParticleRamp.cpp`.** Five edits. Replace the shared function's first two lines,
`void ParticleRamp::RecordCopyCommands(VkCommandBuffer commandBuffer, VkBuffer source)` and the `{` under it, with
these five:

```cpp
void ParticleRamp::RecordCopyCommands(VkCommandBuffer commandBuffer, VkBuffer source, DeclaredFrame* passes)
{
    // Chapter 57: the frame's copy declares what it writes; Setup's upload has no frame and keeps the typed calls.
    if (passes) { passes->Pass("ramp copy", { { m_ramp.image, uses::CopyOverwrite } }); }
    const bool hand = passes == nullptr || !passes->Declared();
```

R1 steps aside. Replace the four lines of the `transitionImage` call under the comment line
`    // can be UNDEFINED because every texel is rewritten.` with:

```cpp
    if (hand)
    {
        transitionImage(commandBuffer, m_ramp.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);
    }
```

R2 becomes the hand-over. Replace the four lines of the `transitionImage` call under the comment line
`    // Read after write: the copy's data, to the vertex shaders that sample it next.` with:

```cpp
    if (passes) { passes->Leave("the vertex shaders", { { m_ramp.image, uses::VertexSampled } }); }
    if (hand)
    {
        transitionImage(commandBuffer, m_ramp.image,
                        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
```

In `Upload`, replace the line `        RecordCopyCommands(commandBuffer, staging.buffer);` with:

```cpp
        RecordCopyCommands(commandBuffer, staging.buffer, nullptr);
```

and replace `RecordCopy`'s first three lines, from
`void ParticleRamp::RecordCopy(VkCommandBuffer commandBuffer, uint32_t frameIndex)` to
`    RecordCopyCommands(commandBuffer, m_staging[frameIndex].buffer);`, with:

```cpp
void ParticleRamp::RecordCopy(VkCommandBuffer commandBuffer, uint32_t frameIndex, DeclaredFrame& passes)
{
    RecordCopyCommands(commandBuffer, m_staging[frameIndex].buffer, &passes);
```

**`ParticlesDemo.cpp`, once more.** In `Record`, replace the line
`        m_ramp.RecordCopy(commandBuffer, frameIndex);` with:

```cpp
        m_ramp.RecordCopy(commandBuffer, frameIndex, m_passes);
```

**The supplied test.** Stage 4 builds the curves cases and adds one check: a declared frame with any typed barrier
fails. Change the `3` in the line `#define PF_TEST_STAGE 3` to `4`:

```cpp
#define PF_TEST_STAGE 4
```

### Checkpoint

Build `TutorialDeclaredFrameTests` and run it as in section 4.

- **No typed barrier is left.** The default fountain's frame 2 reads
  `frame 2: hand 12 calls; declared 13 calls: 11 from the layer, 0 typed, 2 the engine's`. The two left are
  `beginScenePass`'s, four at 4x. The declared route has one call more because E is split: its copy half before the
  copies, its draw half after the scene pass, with P1 and P2.
- **Every case, hand to declared, calls a frame:** Life at 1 step 8 → 7 (frame 0 9 → 6; a Reseed mid-run 9 → 8), 4
  steps 11 → 10, 16 steps 23 → 22, paused 3 → 2, paused with Reseed 4 → 4; Particles' default 12 → 13, a reset with
  3 prewarm steps 28 → 26 (between prewarm steps nothing but the next step's compute reads, so E is not derived
  there), 4x 14 → 15 (the engine's 4), the sort at n 1,024 15 → 16 and at n 4,096 20 → 21, the Check order frame 17
  → 17, and the frame that copies a curve edit 14 → 15, whose gap view shows R1 and R2 derived where they stood.
  The route switches, hand then declared and declared then hand, are clean for Life at 2 steps and for Particles
  with the sort on.
- The report ends with no SKIP line: `PASS: toy, Life, Particles, sort, curves`.

**The end of Particles, on the GPU.** Build the game in **Debug**, because validation is the evidence, and run the
fountain on the declared route with frame 60 explained:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The game build failed.' }
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Particles --frame-route declared --frame-explain 60
```

- **The fountain.** Validation prints no sync message and no VUID. The log explains frame 60: begin, emit,
  simulate, end, "copies out", the hand-over to the host, the draw and its two hand-overs. Before the draw, the
  arrived images get these reasons, and the last hand-over prints the call it derived:

```text
[INFO]   because: targets.colorImage: read and write after write, "the scene pass" COLOR_ATTACHMENT_OUTPUT/COLOR_ATTACHMENT_WRITE -> COLOR_ATTACHMENT_OUTPUT/COLOR_ATTACHMENT_READ | COLOR_ATTACHMENT_WRITE
[INFO]   because: targets.depthImage: layout change after write, "the scene pass" EARLY_FRAGMENT_TESTS | LATE_FRAGMENT_TESTS | COLOR_ATTACHMENT_OUTPUT/COLOR_ATTACHMENT_WRITE | DEPTH_STENCIL_ATTACHMENT_WRITE -> FRAGMENT_SHADER | EARLY_FRAGMENT_TESTS | LATE_FRAGMENT_TESTS/DEPTH_STENCIL_ATTACHMENT_READ | SHADER_SAMPLED_READ
```

```text
[INFO] #3 leaving to "the composite": 1 call
[INFO]   because: targets.colorImage: layout change after write, "particles" COLOR_ATTACHMENT_OUTPUT/COLOR_ATTACHMENT_WRITE -> FRAGMENT_SHADER/SHADER_SAMPLED_READ
[INFO]   transitionImage(commandBuffer, targets.colorImage, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                  VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
[INFO] explain: Particles, frame 60: 6 passes, 3 hand-overs, 11 calls
```

- That call names `targets.colorImage`, which pastes where the typed calls lived, in `RecordParticles` and in
  `handBackSceneTarget`'s body, but not in `Record`, where the hand-over sits and the image is
  `frame.targets.colorImage`.
- **Smoke with Check order**, `--particle-preset smoke` added to the command above, on each route, pressing **Check
  order**: validation stays quiet, and the verdict has the same form on both. In the reference's runs a check at
  frame 60 gave `Check order: 183 particles in key order, a permutation; 841 sentinels after them.` on each route.
  Explained on the declared route, that frame is `explain: Particles, frame 60: 10 passes, 3 hand-overs, 15 calls`,
  and "copies out" carries the term the layer adds because it cannot see ranges:
  `because: Check order's buffer: write after write, "list before the sort" COPY/TRANSFER_WRITE -> COPY/TRANSFER_WRITE`.
- **Fire to smoke at 4x**, likewise `--particle-preset fire-to-smoke --msaa 4 --soft-distance 0.5`, on the declared
  route: the soft distance makes the fragment shader read the depth, the read P2's and P3's fragment stage is for.
  Validation stays quiet. The reference's runs were quiet too under the sun sky (`--sky sun --clouds 0`), and
  through a resize and a change of **MSAA** while Smoke ran.

**A mistake worth trying, C5: the draw without its `IndirectRead`.** In `RecordParticles`, delete
`{ m_indirect.buffer, uses::IndirectRead }, ` from the start of `drawUses`' first row, so the row reads
`        { m_particles.buffer, uses::VertexStorageRead },`; the span takes its count from the array. The test
fails: the draw's pass declares no use of `m_indirect`, and the model finds the draw reading it after end's write.
This one races on the GPU. The barrier before the draw still makes compute's writes visible to the vertex shaders,
but the draw reads its arguments earlier, at `DRAW_INDIRECT`, outside that barrier's second scope, and validation
reports a read after write at `vkCmdDrawIndirect`. Put the entry back.

**C7: the draw without `m_particles`.** Delete ` { m_particles.buffer, uses::VertexStorageRead },` from the end of
that row instead, so it reads `        { m_indirect.buffer, uses::IndirectRead },`. The test fails: the pass
`declares no use of m_particles`. Validation is silent, and nothing races this frame: the lists' term in the same
barrier has the same stages and access, and a memory barrier covers every buffer. What is wrong is the layer's
history. It does not know the draw read the particles, whose safety rests on the lists' term. Put the entry back.

## 11. What catches what, and what stays by hand

This section types nothing. The mistakes the chapter had you try, and C3, which only the reference ran: what each
does on the GPU, and what the test and validation say.

| Mistake | A race on the GPU? | The supplied test | Sync validation |
| --- | --- | --- | --- |
| The first rule kept (section 7's tree) | Yes: the copy can read counts not yet made available; with the sort on and Check order pressed, the draw also reads after Check order's copies | FAIL at "copies out" (and on the Check order frame, the draw's reads of `m_particles` and `m_aliveLists`) | Read after write at `vkCmdCopyBuffer` |
| C1: Life's statistics declared as a read (section 8) | Yes | FAIL: `m_statistics is written as SHADER_STORAGE_WRITE, declared as NONE`, and the model's read after write at the copy | Silent: an atomic is a read to it |
| C2: the statistics declared on the counting step only, at 4 steps (section 5) | No: steps that do not count never run the atomics; the declaration breaks the contract | FAIL: `declares no use of m_statistics`; the model too | Read after write at a `vkCmdDispatch`: by the shader's static use, step 0's |
| C3: every `Begin` forgets the histories (in `DeclaredFrame::Begin`; not offered above) | Yes | FAIL: the toy's "clear" and "read results" get no barrier; Life's write after read at the clear | Write after read at `vkQueueSubmit2` |
| C4: each sort pass declared by its word (section 9) | No: KEYS writes only the items; the declaration breaks the contract | FAIL: `m_aliveLists is written as SHADER_STORAGE_WRITE, declared as NONE` at "sort: keys", and `declares no use of m_particles` at each later sort pass | With Check order armed, one write after read at KEYS' `vkCmdDispatch`; otherwise quiet |
| C5: the draw without `IndirectRead` (section 10) | Yes | FAIL: `declares no use of m_indirect`, and the model's read after write at the draw | Read after write at `vkCmdDrawIndirect` |
| C6: Life's host `Leave` dropped (section 5) | Yes: the host may read before the copy is visible | FAIL: the host reads `m_readback[0]`, and "copy statistics"' write "was never made visible to the host" | Silent: it does not look across a fence wait |
| C7: the draw without `m_particles` (section 10) | Not this frame (the lists' term covers the draw), but the layer's history is wrong | FAIL: `declares no use of m_particles` | Silent |

The validation column was seen on the final code on the RTX 5090, the first rule and C3 in one session of the
reference's and the other six in a later one. The test column ran on the final code.

Read the table by its columns. Validation misses C1 and C6, two races: it records an atomic as a read, and it does
not look across a host fence wait. The test catches both, and its declared-uses check also fails C2, C4 and C7,
where nothing races but the declaration is wrong. Validation, which also judges a dispatch by its shader's static
use, reports C2, and C4 once Check order is armed, with no race behind either. Section 2's control, not in the
table, stops the build.

**Seen by nothing here:** `barrier()` inside a dispatch (neither the test nor validation sees it; Chapter 55,
section 4's Check order catches it on the fountain); what a push constant keeps a dispatch from touching, since the
declarations, the test and validation all go by static use; a barrier that names one stage of a write made at
several, which the model counts as covering all of it; a missing `Track` in Release, or in a demo the test does not
know (Debug asserts); `Track`'s promise itself; an `UNDEFINED` old layout that drops contents wrongly; host writes;
a use split across two entries for one resource (the test compares unions per resource); and the test's tables
themselves, one reading of the GLSL.

**What the test cannot see.** The engine's scene images are not in its declared-uses check; only its model of the
queue judges them, and it leaves out the 4x resolve's reads of the multisampled colour and depth, which are the
engine's too. A declaration wider than the real use passes it, and a `Leave`'s uses are never held to its tables:
only its model judges the use that follows. Its model credits any barrier to the host recorded before a host read,
whether or not the host waited for that submission. Neither it nor the layer sees whether copies inside one pass
really touch disjoint ranges. Its draw table models every `vkCmdDraw` as the opaque ground, and every case runs
with the sky off. No case runs a reset with the sort on, a preset switch, the flipbook, or the curves look or the
sort at 4x.

**What stays by hand.** Which image of a ping-pong and which alive list is current: the passes name physical
handles. Setup's barriers inside `immediateSubmit`, which the `Track` list promises named each first reader. Host
work after the slot's fence and before the submit. Other owners' passes, one `Arrive` or `Leave` each, and what
`m_sky.Update` records, whose barriers the Sky types itself. "Every texel rewritten" (`overwrite`), and what one
pass may hold without a barrier inside it, as Check order's three copies to disjoint ranges. Atomics, declared
`ComputeReadWrite`. `barrier()` inside a dispatch. And every other demo's barriers, all still typed.

**Where the layer stops.** It tracks whole buffers, so it waits where two uses touch disjoint parts of one: Check
order's four copies, in two passes, into its one buffer, and end's write of the draw arguments after emit's and
simulate's indirect reads of other bytes of `m_indirect`. The test models Check order's ranges, so the two differ
there; `m_indirect` is one buffer to both. It never moves work and chooses nothing but the barriers' masks; each
demo owns its `DeclaredFrame`. No cost was measured, on either route. The hand route stays the default, its barrier
stream unchanged: the 25 guards each wrap one call.

## Exit check

Under [the hygiene every exit check assumes](../VulkanTutorial.md#conventions-every-chapter-uses), in **Debug**:

- **Both demos, both routes.** `--demo Life` and `--demo Particles`, each with `--frame-route hand` and with
  `--frame-route declared`, at 1x and with `--msaa 4`; for Particles, the fountain, `--particle-preset smoke` and
  `--particle-preset fire-to-smoke`. Validation prints no sync message and no VUID.
- **Life's picture does not depend on the route.** Section 5's two captures at frame 300, one per route, are byte
  for byte the same.
- **Check order** on Smoke, on each route, finds the particles in key order, a permutation, with sentinels after
  them.
- **Explain.** `--frame-explain 60` with `--frame-route declared`, on each demo: every call printed is one the hand
  route types at that site, or one of the differences sections 5, 7, 9 and 10 named. The panel's **Explain one
  frame**, enabled while **Declared barriers** is ticked, asks for the same print of the next frame.
- **A route switch while running.** Tick and untick **Declared barriers** in each demo. The reference checked both
  switches for both demos in the test, and once per demo on the RTX 5090 (hand, declared, hand, through a temporary
  hook, not the checkbox); on your GPU validation is the witness.
- **The supplied test**, at stage 4, ends `PASS: toy, Life, Particles, sort, curves`. `TutorialMirrorBatchTests`,
  run from the repository root, passes.
- **The controls** of sections 2, 5, 8, 9 and 10, one at a time, each put back after it, say what the table says.

You can now answer these:

- Given two uses of one resource on one queue, what are the barrier's stages, accesses and layouts, and which of
  Chapter 4's rows is that?
- Why does the counters' copy need a barrier when compute has already waited for simulate's write?
- What does `Track` promise, and why does a host fence wait order the slot's last write but make nothing visible?
- Why is a sort pass declared by its shader's four bindings and not by its pass word, and what notices if it is
  not?
- Why do the scene's images arrive each frame instead of being tracked, and whose barriers does no route type?
- Which mistakes does validation miss here, which does the test miss, and which does nothing catch?

[The reflection lesson](SettingsAsRows.md) is read after this one.

Back on the renderer route: [22 — Deferred Shading](22-Deferred-Shading.md).
