# 56 — Everything Bends

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Chapter 56's pages:** **1. Section 1 — One front for the whole island** · [2. Section 2 — A tree bends from its foot](EverythingBendsATree.md) · [3. Part 2 — Every part attached, every view the same](EverythingBendsAttached.md) · [4. Parts 3 and 4 — Once a frame, and the clouds aloft](EverythingBendsOnceAFrame.md).

**Goal:** the plants, their shadows and the clouds join the grass's wind. One front crosses the coastal grass and then
the trees lean in turn, their branches and leaves moving with them and staying attached; the ferns and flowers sway
where they stand; every shadow follows its crown; past the trunk's fade (about 450 m) the forest stands still; Horizon's
clouds drift on the wind aloft. Part 1, sections 1 and 2, makes the fronts the world wind's, as rows, and bends a tree
from its foot. Part 2, sections 3 to 5, keeps every branch and leaf attached, sways the understory and moves every
shadow with its crown. Part 3, section 6, works out each trunk's answer once a frame. Part 4, sections 7 and 8, puts
Horizon's clouds on the wind aloft and says what the wind still does not do.

**Form:** typed into your tree from its own text, over the assembled reference; one supplied CPU test. The tree holds
the reflection lesson complete. The chapter prints every line it changes, including its edits to four tests already in
your tree (`SettingRowsTests.cpp`'s stage line, `GrassWindTests.cpp`, `WorldWindTests.cpp` and
`RendererConvergenceTests.cpp`), except what is supplied: the test, `PlantWindTests.cpp`; `SettingRowsTests.cpp` whole,
where your copy is older than this chapter (section 1 says how to tell); and two files of the reference's own CPU
checkpoints, `Tests/TutorialHarness/Checkpoints/Manifest.psd1` and `PanelStub.cpp`, which only the reference tree has
(its Chapter 42 pair needs them once section 1's `WorldWind.h` gains its include and its panel's new calls). Nor does it
print one case each that the reference adds to its own `MirrorBatchTests.cpp` and `CloudHistoryTests.cpp`, which
sections 6 and 7 name.

**GPU idea:** the plants bend in their vertex shaders, every pass that draws one calling the same function, and Part 3
moves the part that is the same for a whole plant into a compute pass. Sections 2 to 5 build the per-vertex form: one
function, included by every pass that must agree, fed by the frame block, the instance and the run's push constants,
and a second pipeline for each vertex stage that bends, because a branch inside the old shader would put the wind's
code in every calm draw. The culling takes a margin worked out from the function's clamped maxima. With the switch off,
every plant draws with the old shaders, and every margin is 0. Part 3 computes the trunk's lean once a frame for each
of a plant's slots in the instance buffer (a near oak has four: bark and leaves, for the camera and for the casters),
each from the same inputs, and one barrier hands it to the camera pass and every shadow cascade. A stage that cannot
read the frame block gets it another way: the grass's compute pass gets the thirteen front floats packed from it, and
the lean pass a set that reuses set 0's numbers ([Chapter 22, section 6](22-Deferred-Shading.md#6-the-lighting-pass)).
Section 7 applies Chapter 42's integrated offset and teaches no new GPU idea.

**Read after:** [the reflection lesson](SettingsAsRows.md) and [Chapter 53](53-Rolling-Wind.md), in the assembled
reference. Like 53, it is a detour from the far-view route: when you finish, go back to
[43 — Waves to the Shore](43-Waves-To-The-Shore.md). Nothing [Chapter 57](57-The-Frame-Declared.md) teaches is used
here.

**ROADMAP:** step 21+ — the `Horizon` demo's plants, their shadows and its clouds take the world wind.

**Module:** `pf::vulkan_graphics` (`WorldWind`, `SceneRenderer`, `ShadowMaps`, `Clouds`, `Sky`), `pf::debug_panels`
(`SettingRows.h`'s walkers) and the Horizon demo. `FrameData` grows from 448 to 544 bytes by appending; the instance
record keeps its 112 bytes. Two command-line flags, `--wind-fronts` and `--plant-wind`, are the harness the checkpoints
use.

**Math:** a turn about a point (section 1); a shear and its inverse transpose, and a distance kept by a pull-back
(section 2); a damped spring's step answer, Chapter 53's, reused (sections 2 and 3); a pixel's size at a distance,
Chapter 37's, reused (sections 2 and 3); a bound by the triangle inequality (section 4); an integrated offset, Chapter
42's, reused (section 7).

**Prerequisites:**

- [Chapter 53, sections 3](53-Rolling-Wind.md#3-a-push-and-its-swing-back) to
  [5](53-Rolling-Wind.md#5-nothing-is-ever-still): the step answer, `frontResponse`, the fronts' frame, the thirteen
  front settings and `GrassWindSource.h`, compiled as C++ and GLSL; and
  [section 7](53-Rolling-Wind.md#7-what-this-wind-does-not-do-yet), the pivot section 1 cures.
- [Chapter 42, section 1](42-One-Wind.md#1-four-winds-in-one-frame) and
  [section 2](42-One-Wind.md#2-a-wind-that-turns-without-jumping): one `WorldWind` per demo, the summed offset, the
  turn, and section 1's capture-and-hash checkpoint.
- [The reflection lesson, sections 3](SettingsAsRows.md#3-one-row-per-setting-and-packing-from-the-rows) to
  [6](SettingsAsRows.md#6-what-a-preset-leaves-alone-and-where-the-line-is): rows and kinds, `packSettingRows`,
  `drawSettingRows`, and its supplied test with your copy, `SettingsByHand.h`.
- [Chapter 47, section 4](47-Grass-Representation-Handover.md#4-animate-derived-data): the root-pinned shear,
  `grassClumpUnlean`; [Chapter 11, section 13](11-Meshes.md#13-how-normals-move-the-normal-matrix): a normal moves by
  the inverse transpose.
- [Chapter 39, sections 2](39-Plants.md#2-leaves-are-cards) to [4](39-Plants.md#4-far-trees-cast-their-stand-ins),
  [6](39-Plants.md#6-leaves-that-thin-out), [9](39-Plants.md#9-planted-by-the-gpu) and
  [10](39-Plants.md#10-drawn-from-the-counts): the plant-space contract (`uv.y` is 1 at a card's base), the leaf
  pipelines and `BindLeafRun`, the casters, the leaf plates, the understory.
- [Chapter 40, sections 1](40-Forests-To-The-Horizon.md#1-a-picture-that-is-still-a-surface) and
  [2](40-Forests-To-The-Horizon.md#2-exactly-one-owner): impostors and the 490 m handover, `TREE_MESH_ENTER`.
- [Chapter 37, sections 5](37-Objects-At-A-Distance.md#5-height-on-screen),
  [8](37-Objects-At-A-Distance.md#8-shadows-near-the-camera) and
  [9](37-Objects-At-A-Distance.md#9-what-each-pass-costs): a length's size on screen and the levels, shadows near the
  camera, the pass timers.
- [Chapter 19, sections 3](19-Instancing-And-Indirect.md#3-the-instance-buffer) and
  [8](19-Instancing-And-Indirect.md#8-the-shadow-casters-batched-too): `InstanceData` and the batched casters;
  [Chapter 17, section 11](17-Shadows.md#11-cascaded-shadow-maps): cascades.
- [Chapter 12, section 10](12-Scene-Graph.md#10-culling-on-the-cpu): `frustumFromViewProjection`'s planes have unit
  normals, so a plane's `w` is in metres (section 4's margin).
- [Chapter 28, sections 10](28-Clouds.md#10-wind) and [13](28-Clouds.md#13-time-slicing-and-the-running-average): the
  clouds' wind and the restart of their history.
- For Part 3: [the list at the top of its page](EverythingBendsOnceAFrame.md#part-3--once-a-frame-section-6).
- The optional test projects (`GenerateProjects.bat --tutorial-tests`), and `PlantWindTests.cpp`, which is supplied, not
  typed.

## Where the code goes

| File | What sections 1 to 7 do there |
| --- | --- |
| `Shaders/Include/SharedShaderTypes.h`, `Source/PillowFort/VulkanGraphics/FrameData.h` | Section 1: `WindFronts`, `FrameData` from 448 to 512 bytes, and `applyWorldWind` copies it. Section 2: `PlantWind`, 512 to 544. Section 5: `ShadowDrawData`'s three free words. Section 6: the instance record's two lanes, bytes 76 and 92 of 112 |
| `Source/PillowFort/VulkanGraphics/WorldWind.h`, `Source/PillowFort/VulkanGraphics/WorldWind.cpp` | Section 1: the thirteen fronts as rows, the clamp in `Publish`, `--wind-fronts`, the panel's **Fronts**, and the pivot: `SetPivot` and a correction only the fronts read. Section 7: `Offset()` and `cloudOffsetAloft` |
| `Source/PillowFort/DebugPanels/SettingRows.h` | Section 1: the four walkers, templates over any table |
| `Shaders/Grass/GrassTypes.h`, `Shaders/Grass/GrassGenerateKernel.glsl` | Section 1: two free floats take the travel correction, and the kernel's front-frame line adds it |
| `Source/PillowFort/Demos/Grass/GrassField.h`, `Source/PillowFort/Demos/Grass/GrassField.cpp`, `Source/PillowFort/Demos/Grass/GrassDemo.h`, `Source/PillowFort/Demos/Grass/GrassDemo.cpp` | Section 1: the fronts leave the grass's settings, `PackParameters` copies them from the world wind, the **Answer** node, `SetWindFront`, the pivot |
| `Source/PillowFort/Demos/Horizon/CoastalArea.h`, `Source/PillowFort/Demos/Horizon/CoastalArea.cpp` | Section 1: `Prepare` takes the whole `WorldWindState` |
| `Source/PillowFort/Demos/Horizon/HorizonDemo.h`, `Source/PillowFort/Demos/Horizon/HorizonDemo.cpp` | Section 1: `WIND_VIEWS` with "Wind edge", `SetWindFront`, the pivot, the state to the coast. Section 2: "Wind wood", the plants' rows and **Plants in the wind**, `RegisterPlantWind`, the leaf twins and their push range, the plates' wind-free copies. Section 3: "Oak at 10 m", the flutter in the table. Section 4: the understory's twins and its frustum margin. Section 5: "Lone tree", "Frustum edge", "Cascade edge", the trees' frustum margin, **Still shadows**. Section 6: the lean pass in the frame. Section 7: the clouds' offset |
| **New:** `Shaders/Include/PlantWindSource.h`, `Shaders/Include/PlantWind.glsl` | Section 2: the trunk's answer, the bend from the foot, its normal, the fades. Section 3: the branch and the flutter. Section 4: the bound, `plantWindBound`. Section 6: the twins read the stored lean |
| **New:** `Source/PillowFort/Demos/Horizon/PlantWindTable.h` | Section 2: `speciesWindHeight` and `PLANT_BEND_GAIN`. Section 3: `plantMaterialWind` |
| `Shaders/Horizon/HorizonTypes.h`, `Shaders/Horizon/Leaf.vert.glsl`, **New:** `Shaders/Horizon/LeafBody.glsl`, `Shaders/Horizon/LeafWind.vert.glsl` | Section 2: `FlatDraw`'s three words, the leaf body and its wind twin. Section 3: the branch and flutter terms. Section 6: the stored lean |
| `Shaders/Horizon/Understory.vert.glsl`, **New:** `Shaders/Horizon/UnderstoryBody.glsl`, `Shaders/Horizon/UnderstoryWind.vert.glsl` | Section 4: the understory's body and its twin |
| `Shaders/Shadows/ShadowDepth.vert.glsl`, **New:** `Shaders/Shadows/ShadowDepthBody.glsl`, `Shaders/Shadows/ShadowDepthWind.vert.glsl`, `Source/PillowFort/VulkanGraphics/ShadowMaps.h`, `Source/PillowFort/VulkanGraphics/ShadowMaps.cpp` | Section 5: the shadow body and its twin, created only for a demo with material wind. Section 6: the stored lean |
| `Source/PillowFort/VulkanGraphics/SceneRenderer.h`, `Source/PillowFort/VulkanGraphics/SceneRenderer.cpp` | Section 2: the per-material wind table. Section 5: the shadow twin per run, and a bending caster's bounds grown. Section 6: the record as a free function, the "leaned" mark and its check |
| **New:** `Shaders/Horizon/TrunkLean.comp.glsl`, `Shaders/Include/BentInstances.glsl`, `Source/PillowFort/Demos/Horizon/TrunkLeans.h`, `Source/PillowFort/Demos/Horizon/TrunkLeans.cpp` | Section 6: the lean pass, its set and its one barrier |
| `Shaders/Include/CloudTypes.h`, `Source/PillowFort/VulkanGraphics/Clouds.h`, `Source/PillowFort/VulkanGraphics/Clouds.cpp`, `Source/PillowFort/VulkanGraphics/Sky.h`, `Source/PillowFort/VulkanGraphics/Sky.cpp` | Section 7: an offset handed in, passed through the sky |
| `Source/SandboxGame/Main.cpp` | Section 1: `--wind-fronts`. Section 2: `--plant-wind 0\|1` |
| `premake5.lua`, `Tests/TutorialHarness/PlantWindTests.cpp`, `Tests/TutorialHarness/SettingRowsTests.cpp`, **Deleted:** `SettingsByHand.h` | Section 1: the supplied test's project, at stage 1; the reflection lesson's test at stage 4, and your copy retired. Sections 2 to 7: the supplied test's stage raised |
| `Tests/TutorialHarness/GrassWindTests.cpp`, `Tests/TutorialHarness/WorldWindTests.cpp`, `Tests/TutorialHarness/RendererConvergenceTests.cpp` | Section 1: your tests follow the fronts and `FrameData`'s size. Section 2: the size again |
| `Tests/TutorialHarness/MirrorBatchTests.cpp`, `Tests/TutorialHarness/CloudHistoryTests.cpp` | Sections 6 and 7: a case each in the reference's own tests, named there, not printed |

Sections 1, 2, 4, 5 and 6 add files, and section 1 deletes one, so each runs `GenerateProjects.bat --tutorial-tests`
again ([Chapter 1, section 3](01-Environment-And-Build.md#3-the-corrected-workspace)): premake bakes its file lists in
when it generates, and a file it has not seen is not built. Sections 3 and 7 add none.

**Blank lines.** A new function, struct member block or file-scope block you add gets one blank line above it and one
below it, as its neighbours have, except as the last thing in a class or struct, where it sits directly against the
closing `};`. Constants or comment lines that join a run of constants are the exception: they sit directly against their
neighbours, and the text says "with no blank line between" where that is so.

# Part 1 — One front for the whole island (sections 1–2)

Section 1 moves the fronts out of the grass into the world wind, where every stage that reads the frame finds them, and
turns their frame about the viewer when the wind turns. Section 2 bends a tree from its foot on those fronts.

## 1. A front is a fact of the island

Chapter 53's fronts belong to the grass: thirteen of its 32 wind-response settings say where a front is, they live in
`GrassSettings`, and only the grass's compute pass reads them. First add a place to watch that from. In
`HorizonDemo.cpp`, below `PLANT_VIEWS` and the blank line after it, add `WIND_VIEWS`, with a blank line below it:

```cpp
// Chapter 56: places to watch the wind from. "Wind edge" stands in the grass with oaks 25 to 80 m behind it, the wind
// running left to right across the frame: a front that crosses the grass is seen reaching the trees (section 1 shows it
// stopping short of them).
constexpr std::array<View, 1> WIND_VIEWS{ {
    { "Wind edge", { 808.0f, -60.0f }, 2.5f, 180.0f, -2.0f },
} };
```

`SelectView` and `DrawPropControls` each walk a brace list of these arrays. In both, put
`std::span<const View>(WIND_VIEWS), ` just before `std::span<const View>(FAR_FOREST_VIEWS)`. A bookmark changes no
frame. Build, and stand there:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64 /t:SandboxGame
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4
```

You stand in the coastal grass, the wind running left to right across the frame, with oaks behind the grass.
Fronts roll through the grass toward the oaks and stop short of them: the oaks do not move, nor do the ferns under them.

**Keep this build before you change anything.** The checkpoints of sections 1, 2 and 5 compare frames with it, as
[Chapter 42, section 1](42-One-Wind.md#1-four-winds-in-one-frame) did:

```powershell
Copy-Item -Recurse .\Build\Artifacts\Release\SandboxGame ..\SandboxGame-before-56
```

Nothing is broken there: a tree cannot answer a front it cannot read. A front must first become a fact of the island,
published by the world wind beside its direction and speed.

> **Jump:** this section retires the reflection lesson's copy of your old code, `SettingsByHand.h`, so from here on
> nothing compares the rows with the code you wrote before them. The settings test checks rules every table must keep:
> a row's member and field named by one token, its range and its group, and the fronts' rows in `WindFronts`' order,
> each 4 bytes after the last. A slip a row shared with your old code was already invisible to it (the lesson's "What
> nothing catches"); now there is no old code to compare with.

**When the wind turns.** [Chapter 53, section 7](53-Rolling-Wind.md#7-what-this-wind-does-not-do-yet) named a limit:
when the wind turns, the fronts' frame turns about a point near the world origin. A tree will make that plain, so see it
now in the grass, with the kept build, at Coast, which stands 2.6 km from the world origin.
`--wind-turn-at 180 --wind-turn-to 90` turns Chapter 42's wind from −90 to 90 degrees from frame 180, at its 30 degrees
a second:

```powershell
& ..\SandboxGame-before-56\SandboxGame.exe --demo Horizon --horizon-view Coast --sky sun --msaa 4 `
    --wind-turn-at 180 --wind-turn-to 90
```

For the six seconds of the turn the field shivers: the pattern of fronts is swept through it far faster than the wind
blows, and the blades step from frame to frame instead of swinging. When the turn ends, the fronts roll on.

The frame is the cause. The kernel's `frontFrame = xz - frontSpeed * windTravel` measures a clump's place along and
across the wind's current direction from the point `frontSpeed * windTravel`, which starts at the world origin and rides
downwind. When the direction turns by dθ, the frame turns about that point, and a clump D from it moves through the
pattern by about D × dθ. When the turn starts the point is still near the world origin, 2,574 m from Coast's grass, so
Chapter 42's 30 degrees a second, 0.524 radians, sweeps the gusts past it at 2,574 × 0.524 / 17 ≈ 79 gust spacings a
second. A slower turn is no cure, since the point rides away from the world origin at the wind's speed for as long as
the run lasts.

> **Jump:** until here every front a reader saw could be rebuilt from the settings and the clock alone. The cure this
> section works out keeps a number that only a turning frame changes and nothing resets, so after a turn, where the
> fronts are depends on the run's history. Hold that: it is the stored state Chapter 53, section 7 said a cure would
> need.

<a id="ch56-one-front"></a>

### Attempt CH56-one-front: which settings say where a front is

Predict first: of the grass's 32 wind-response settings
([Chapter 53's table](53-Rolling-Wind.md#the-32-wind-response-settings)), which say where a front is, and which say how
a clump answers it? Which must a tree share with the grass at its foot? Then the turn you just watched: Chapter 53 named
the cure, a frame that turns about the camera. Say the frame's origin is F, the camera stands at p on the ground, and
this frame's published direction turned by dθ. Where must F go, so that the grass at p sees no sweep? What does a clump
D metres from p still see? And since F is frontSpeed times the travel, what must the world wind add to the travel to
put F there? Both answers follow the hints: the first opens the worked solution, and the second is its paragraph
**The cure**.

**Acceptance:** the settings that say where a front is are rows of a block, `WindFronts`, that the world wind publishes
in `FrameData`, where every vertex stage can read it; the grass keeps the rest. The grass's picture does not change:
Horizon at Coast with the sky off captures the same frame, byte for byte, with the kept build and the new one. And
[Chapter 53, section 7](53-Rolling-Wind.md#7-what-this-wind-does-not-do-yet)'s limit is gone: when the wind turns, the
bands at Coast turn where they stand instead of sweeping through the grass. The supplied test's stage 1 drives that
through two members of `WorldWind`, `SetPivot(glm::vec2)`, which a demo calls each frame, and `TravelCorrection()`, a
correction only the fronts read, and passes.

**Transfer:** a tree answers the ripples too, as the grass does through `rippleStrength`. Should the tree's share of the
ripples be a fourteenth row of `WindFronts`? Say why, and where it belongs instead.

<details>
<summary>Hint 1: Chapter 42's rule</summary>

`WorldWind.h` states it: how a reader responds to the wind belongs to the reader, not to the wind. Take Chapter 53's six
groups one setting at a time, and ask whether it moves a front or changes how hard the grass takes one.

</details>

<details>
<summary>Hint 2: two that look like layout</summary>

Two settings sit among the gusts and the ripples and say nothing about where a front is. One scales how much the slow
swell lifts this grass's gusts; the other, how much of a ripple's answer this grass adds to a gust's.

</details>

<details>
<summary>Hint 3: where it goes, and where F goes</summary>

The block is a struct in `SharedShaderTypes.h`, appended to `FrameData`. The settings, their ranges and their rows go
beside the wind's own in `WorldWind.h`, and the clamp in `WorldWind::Publish`. The grass's compute pass cannot read
`FrameData`, so `PackParameters` copies the published block into `GrassParameters`. The turn's correction is the world
wind's too: `WorldWind::Advance` works it out, two of the block's spare floats carry it, and the grass kernel's
front-frame line adds it.

For the turn, turn F about p by dθ, the angle the direction turned. What happens to p's own along and across, measured
from the turned F along the turned direction? The correction is the number that puts F at its turned place, and only
the next turn moves it.

</details>

<details>
<summary>Worked solution: thirteen rows for the world wind, a copy for the grass, a pivot for the turn</summary>

**Answer to the first prediction.** Thirteen say where a front is: nine of **Gusts** (`frontSpeed`, `gustSpacing`,
`gustJitter`, `gustCrestLength`, `gustCrestBend`, `gustOccupancy`, `gustLengthMin`, `gustLengthMax`, `frontSizeFloor`)
and four of **Ripples** (`rippleSpacing`, `rippleJitter`, `rippleOccupancy`, `rippleBaseline`). A tree must share all
thirteen, or it answers other fronts than the grass at its foot. The other nineteen are the grass's answer and stay with
it: **Spring**, **Lean**, **Blades**, **Wind shading**, and the two that look like layout and are not, `swellWeight` and
`rippleStrength`. A tree has an answer of its own to the same fronts (section 2).

**The block.** Every vertex stage reads the frame through `FrameData`, set 0 binding 0, so the fronts go there, as a
struct C++ and GLSL share. Thirteen floats padded to sixteen are 64 bytes in std140 and in C++ alike, and appended at
448 they move no offset an earlier chapter printed. Two of the three spare floats, `travelCorrectionX` and
`travelCorrectionY`, belong to the turn at the end of this section; until then they stay 0. In `SharedShaderTypes.h`,
above the comment that starts `/* Chapter 10: everything that is the same for every draw in a frame. Set 0,`, add, with
a blank line below it:

```cpp
/* Chapter 56 section 1: where the wind's gust and ripple fronts are. Chapter 53 kept these thirteen numbers in the
   grass's own settings; the world wind publishes them now, so a tree reads the same fronts a blade does. FrameData
   holds one. std140: sixteen floats are 64 bytes in a block and in C++ alike. All zero is calm. */
struct WindFronts
{
    /* Gusts: where the big fronts are */
    float frontSpeed;        /*   0  how fast fronts travel, as a multiple of the wind speed */
    float gustSpacing;       /*   4  metres between gust fronts along the wind, before jitter */
    float gustJitter;        /*   8  how far a gust front moves off its slot, in spacings */
    float gustCrestLength;   /*  12  metres per cell of the noise that shapes a front along its crest */
    float gustCrestBend;     /*  16  how far a gust crest bends, in spacings */
    float gustOccupancy;     /*  20  share of a gust crest that carries a gust */
    float gustLengthMin;     /*  24  metres: the shortest push along the wind */
    float gustLengthMax;     /*  28  metres: the longest push, never shorter than the shortest */
    float frontSizeFloor;    /*  32  smallest size the size noise leaves an occupied front, both layers */
    /* Ripples: the small layer, so nothing is still */
    float rippleSpacing;     /*  36  metres between ripple fronts */
    float rippleJitter;      /*  40  how far a ripple front moves off its slot, in spacings */
    float rippleOccupancy;   /*  44  share of a ripple crest that carries a ripple */
    float rippleBaseline;    /*  48  share of its full size every ripple front keeps, even off its occupied stretch */
    float travelCorrectionX; /*  52  correction to the fronts' travel, in metres of travel: their frame moves by frontSpeed times it (Chapter 56 section 1); only the fronts read it, the wind's offset is untouched */
    float travelCorrectionY; /*  56 */
    float padding2;          /*  60  keeps the size a multiple of 16 */
};
```

`FrameData` holds one at its end, and the block's own layout is asserted beside it. Replace the lines from the one below
the `windGust` member down to `static_assert(sizeof(FrameData) == 448, "FrameData layout drifted.");` with these, and
below the `windGust` offset assert add
`static_assert(offsetof(FrameData, windFronts) == 448, "FrameData alignment drifted.");`, indented as its neighbours:

```cpp
    /* Chapter 56 section 1: where the wind's fronts are, published by the same owner. All zero is calm. */
    WindFronts windFronts;  /* 448  64 bytes */
};

#ifdef __cplusplus
    static_assert(sizeof(WindFronts) == 64, "WindFronts layout drifted.");
    static_assert(offsetof(WindFronts, gustSpacing) == 4 && offsetof(WindFronts, gustLengthMax) == 28 &&
                  offsetof(WindFronts, frontSizeFloor) == 32 && offsetof(WindFronts, rippleSpacing) == 36 &&
                  offsetof(WindFronts, rippleBaseline) == 48 && offsetof(WindFronts, padding2) == 60,
                  "WindFronts alignment drifted.");
    static_assert(sizeof(FrameData) == 512, "FrameData layout drifted.");
```

**The settings and the state.** The thirteen move into `WorldWindSettings` with Chapter 53's names and defaults, and the
published state carries the block, so `applyWorldWind` copies it with the rest: `WorldWindState` grows from 32 to
96 bytes. In `WorldWind.h`, replace the three lines from `#include "PillowFort/ErrorReporting/InitializationResult.h"`
to `#include <glm/glm.hpp>` with:

```cpp
#include "PillowFort/DebugPanels/SettingRows.h"
#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "SharedShaderTypes.h"

#include <array>
#include <cmath>
#include <glm/glm.hpp>
#include <string>
#include <string_view>
```

Then replace everything from the line below `paused` down to the `};` that closes `WorldWindState` with:

```cpp
    // Chapter 56 section 1: where the fronts are. Chapter 53 kept these thirteen in the grass's settings, with these
    // defaults; every reader answers the same fronts now, each in its own way. Their names are shared::WindFronts'.
    // Gusts: where the big fronts are
    float frontSpeed      = 1.0f;    // how fast gust and ripple fronts travel, as a multiple of the wind speed
    float gustSpacing     = 17.0f;   // metres between gust fronts along the wind, before jitter
    float gustJitter      = 0.45f;   // how far a gust front moves off its slot, in spacings; 0 is a metronome
    float gustCrestLength = 16.0f;   // metres per cell of the noise that shapes a front along its crest
    float gustCrestBend   = 0.4f;    // how far a gust crest bends, in spacings
    float gustOccupancy   = 0.95f;   // share of a gust crest that carries a gust
    float gustLengthMin   = 3.0f;    // metres: the shortest push along the wind
    float gustLengthMax   = 6.0f;    // metres: the longest push (published as at least the minimum)
    float frontSizeFloor  = 0.15f;   // smallest size the size noise leaves an occupied front, both layers
    // Ripples: the small layer, so nothing is still
    float rippleSpacing   = 3.75f;   // metres between ripple fronts
    float rippleJitter    = 0.45f;   // how far a ripple front moves off its slot, in spacings
    float rippleOccupancy = 0.55f;   // share of a ripple crest that carries a ripple
    float rippleBaseline  = 0.2f;    // share of its full size every ripple front keeps, even off its occupied stretch
};

// What one frame publishes: FrameData's windDirection, windGust and windFronts, field for field. All zero is calm,
// and a reader treats a gust size below WorldWind::MIN_GUST_SIZE as calm instead of dividing by it.
struct WorldWindState
{
    glm::vec4 direction{ 0.0f };   // xy: the unit vector it blows along, world xz; zw: the gust offset, metres
    glm::vec4 gust{ 0.0f };        // x strength, y gust size in metres, z mean speed in m/s; w unused
    shared::WindFronts fronts{};   // Chapter 56 section 1: where the fronts are, held inside their ranges
};
```

**The rows.** The reflection lesson made each grass setting a row: its name, its member, the block's field it packs
into, its range, decimals, label and group. The fronts' rows are the same, with `WorldWindSettings` as the settings and
`shared::WindFronts` as the block, and their ranges move out of `GrassField.h` unchanged. Below `WorldWindState`, above
the comment that starts `// One per demo, constructed by the demo`, add, with a blank line on each side:

```cpp
// A slider's range, and the clamp Publish applies to what the panel (or a typed value) gives it: one home for both.
using WindRange = debug_panels::SettingRange;

// Chapter 56 section 1: the fronts' ranges, in the settings' order. Gust length min and max share one. Chapter 53 named
// them in the grass's header; they are the wind's now.
inline constexpr WindRange FRONT_SPEED_RANGE       { 0.3f, 2.0f };
inline constexpr WindRange GUST_SPACING_RANGE      { 6.0f, 60.0f };
inline constexpr WindRange GUST_JITTER_RANGE       { 0.0f, 0.45f };
inline constexpr WindRange GUST_CREST_LENGTH_RANGE { 4.0f, 80.0f };
inline constexpr WindRange GUST_CREST_BEND_RANGE   { 0.0f, 0.6f };
inline constexpr WindRange GUST_OCCUPANCY_RANGE    { 0.0f, 1.0f };
inline constexpr WindRange GUST_LENGTH_RANGE       { 0.5f, 30.0f };
inline constexpr WindRange FRONT_SIZE_FLOOR_RANGE  { 0.0f, 1.0f };
inline constexpr WindRange RIPPLE_SPACING_RANGE    { 2.0f, 12.0f };
inline constexpr WindRange RIPPLE_JITTER_RANGE     { 0.0f, 0.45f };
inline constexpr WindRange RIPPLE_OCCUPANCY_RANGE  { 0.0f, 1.0f };
inline constexpr WindRange RIPPLE_BASELINE_RANGE   { 0.0f, 1.0f };

// The run of rows one call draws: one per tree node under the wind panel's "Fronts".
enum WindFrontGroup : int
{
    WIND_FRONT_GUSTS, WIND_FRONT_RIPPLES
};

// The thirteen fronts by name, as Chapter 53's grass table held them: a row is the member's own name (stringized), the
// member, the field of shared::WindFronts it publishes into (named by the same token), its range, the decimals it prints
// with, its label and its group. Publish copies from it, the panel draws from it, `--wind-fronts <name>=<value>` looks a
// setting up in it, and the "Log values" line prints from it. Every row holds a typed value inside its range.
using WindFrontSetting = debug_panels::SettingRow<WorldWindSettings, shared::WindFronts, WindFrontGroup>;

// Designated, so a member added to the row later cannot shift the fields after it.
#define PF_WIND_FRONT_ROW(M, RANGE, DECIMALS, LABEL, GROUP) \
    { .name = #M, .member = &WorldWindSettings::M, .field = &shared::WindFronts::M, .range = RANGE, .decimals = DECIMALS, \
      .label = LABEL, .group = GROUP, .flags = debug_panels::SETTING_HOLDS }
inline constexpr auto WIND_FRONT_ROWS = std::to_array<WindFrontSetting>({
    // Gusts: where the big fronts are
    PF_WIND_FRONT_ROW(frontSpeed, FRONT_SPEED_RANGE, 2, "Front speed (x wind)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustSpacing, GUST_SPACING_RANGE, 1, "Gust spacing (m)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustJitter, GUST_JITTER_RANGE, 2, "Gust jitter (spacings)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustCrestLength, GUST_CREST_LENGTH_RANGE, 1, "Gust crest length (m)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustCrestBend, GUST_CREST_BEND_RANGE, 2, "Gust crest bend (spacings)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustOccupancy, GUST_OCCUPANCY_RANGE, 2, "Gust occupancy", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustLengthMin, GUST_LENGTH_RANGE, 1, "Gust length min (m)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(gustLengthMax, GUST_LENGTH_RANGE, 1, "Gust length max (m)", WIND_FRONT_GUSTS),
    PF_WIND_FRONT_ROW(frontSizeFloor, FRONT_SIZE_FLOOR_RANGE, 2, "Front size floor", WIND_FRONT_GUSTS),
    // Ripples: the small layer
    PF_WIND_FRONT_ROW(rippleSpacing, RIPPLE_SPACING_RANGE, 2, "Ripple spacing (m)", WIND_FRONT_RIPPLES),
    PF_WIND_FRONT_ROW(rippleJitter, RIPPLE_JITTER_RANGE, 2, "Ripple jitter (spacings)", WIND_FRONT_RIPPLES),
    PF_WIND_FRONT_ROW(rippleOccupancy, RIPPLE_OCCUPANCY_RANGE, 2, "Ripple occupancy", WIND_FRONT_RIPPLES),
    PF_WIND_FRONT_ROW(rippleBaseline, RIPPLE_BASELINE_RANGE, 2, "Ripple baseline", WIND_FRONT_RIPPLES),
});
static_assert(WIND_FRONT_ROWS.size() == 13, "one row per front setting");
static_assert(debug_panels::settingRowsValid(WIND_FRONT_ROWS));
#undef PF_WIND_FRONT_ROW

// Applies "name=value" (`--wind-fronts`) to `settings`, the value clamped to the row's range. Fails and changes nothing, with
// a message that lists the valid names, when the name is unknown or the number malformed or not finite.
InitializationResult applyWindFronts(WorldWindSettings& settings, std::string_view assignment, float& used, bool& clamped);

// The "Log values" line for the fronts, without its log prefix: every front from the table, in order.
std::string windFrontsLine(const WorldWindSettings& settings);
```

**One clamp, at the owner.** Chapter 53 held the fronts inside their ranges when the grass packed its block. A tree
reads `FrameData`, not the grass's block, and would read a typed value as it stands. So `Publish` holds all thirteen
once, and the longest push to no less than the shortest as published: every reader gets the same numbers, and the
grass's packing becomes a copy. In `WorldWind.cpp`, add `#include <algorithm>` above `#include <cmath>`. In `Publish`,
below the line that sets `m_state.gust`, add, with a blank line between:

```cpp
    // Chapter 56 section 1: the fronts, each held inside its range here, once, so every reader gets the same values (the
    // grass held them at packing, the trees would otherwise read a typed value as it stands). The longest push is never
    // shorter than the shortest: it is held to its own range first, then to no less than the minimum as published.
    debug_panels::packSettingRows(WIND_FRONT_ROWS, m_settings, m_state.fronts, true);
    m_state.fronts.gustLengthMax = std::clamp(m_settings.gustLengthMax, m_state.fronts.gustLengthMin, GUST_LENGTH_RANGE.max);
```

A clamp cannot hold a NaN, which has no side to be held on, so `Configure` refuses one, as it refuses a bad speed.
Replace the three-line statement that starts `const bool finite =` with:

```cpp
    bool finite = std::isfinite(settings.towardDegrees) && std::isfinite(settings.speed) &&
                  std::isfinite(settings.strength) && std::isfinite(settings.gustSize) &&
                  std::isfinite(settings.turnRate);
    // Chapter 56 section 1: the thirteen fronts too. Publish holds each inside its range, but a NaN has no side to be held on.
    for (const WindFrontSetting& row : WIND_FRONT_ROWS) { finite = finite && std::isfinite(settings.*(row.member)); }
```

**The walkers.** Chapter 53 wrote four functions in `GrassField.cpp` that walk the grass's table: a row by its name, the
list of names, `name=value` applied with its clamp and its messages, and the **Log values** line. The fronts are a
second table, so the four become templates over any table, in `SettingRows.h` beside `packSettingRows`, with the flag's
name and what a row is called as arguments for the messages. Applying and printing need a float, so they refuse, or
skip, a row that has none, as the particles' tables have (the reflection lesson, section 5). In `SettingRows.h`, replace
the four includes below `#pragma once` with:

```cpp
#include "PillowFort/ErrorReporting/InitializationResult.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <format>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>
```

Below `packSettingRows`' closing brace, above the comment that starts `// Copies each SETTING_KEPT row`, add, with a
blank line on each side:

```cpp
// Chapter 56 section 1: the four walkers over any table of rows. Applying and printing need a float, so they fail on, or
// skip, a row that has none. Chapter 53 wrote them for the grass's one table,
// and the world wind's fronts are the second, so they take the table, the command-line option that names it ("--grass-response")
// and what a row is called in a message ("wind-response setting").

// The row of this name, or null.
template <class Settings, class Block, class Group, std::size_t Count>
const SettingRow<Settings, Block, Group>* findSettingRow(const std::array<SettingRow<Settings, Block, Group>, Count>& rows,
                                                         std::string_view name)
{
    const auto found = std::find_if(rows.begin(), rows.end(), [&](const SettingRow<Settings, Block, Group>& row) { return name == row.name; });
    return found != rows.end() ? &*found : nullptr;
}

// Every row's name, in table order, separated by ", ".
template <class Settings, class Block, class Group, std::size_t Count>
std::string settingRowNames(const std::array<SettingRow<Settings, Block, Group>, Count>& rows)
{
    std::string names;
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if (!names.empty()) { names += ", "; }
        names += row.name;
    }
    return names;
}

// Applies "name=value" to `settings`, the value clamped to the row's range. Fails, and changes nothing, with a message that
// names the problem and lists the valid names when the name is unknown or the number malformed or not finite. `used` is the
// value stored, and `clamped` is whether the range changed it.
template <class Settings, class Block, class Group, std::size_t Count>
InitializationResult applySettingAssignment(const std::array<SettingRow<Settings, Block, Group>, Count>& rows, Settings& settings,
                                            std::string_view option, std::string_view what, std::string_view assignment,
                                            float& used, bool& clamped)
{
    const std::size_t equals = assignment.find('=');
    const std::string_view name  = assignment.substr(0, equals);
    const std::string_view value = equals == std::string_view::npos ? std::string_view{} : assignment.substr(equals + 1);
    const SettingRow<Settings, Block, Group>* row = findSettingRow(rows, name);
    if (!row)
    {
        return InitializationResult::failure(std::format("{}: \"{}\" is not a {}. Valid names: {}.", option, name, what, settingRowNames(rows)));
    }
    if (row->member == nullptr)
    {
        return InitializationResult::failure(std::format("{}: \"{}\" is not a float setting, so it cannot be typed. Valid names: {}.",
                                                         option, row->name, settingRowNames(rows)));
    }
    float number = 0.0f;
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), number);
    if (equals != std::string_view::npos && error == std::errc::result_out_of_range)
    {
        return InitializationResult::failure(std::format("{}: \"{}\" is out of range for a number; got \"{}\". Valid names: {}.",
                                                         option, row->name, assignment, settingRowNames(rows)));
    }
    if (equals == std::string_view::npos || error != std::errc{} || end != value.data() + value.size() || !std::isfinite(number))
    {
        return InitializationResult::failure(std::format("{}: \"{}\" needs a finite number as name=value; got \"{}\". Valid names: {}.",
                                                         option, row->name, assignment, settingRowNames(rows)));
    }
    used    = std::clamp(number, row->range.min, row->range.max) + 0.0f;   // + 0.0f turns -0 into 0
    clamped = used != number;
    settings.*(row->member) = used;
    return InitializationResult::success();
}

// "<title> name=value name=value ...": every row from the table, in order, each with its own decimals.
template <class Settings, class Block, class Group, std::size_t Count>
std::string settingRowsLine(const std::array<SettingRow<Settings, Block, Group>, Count>& rows, std::string_view title,
                            const Settings& settings)
{
    std::string line(title);
    for (const SettingRow<Settings, Block, Group>& row : rows)
    {
        if (row.member == nullptr) { continue; }   // only a float row has a value to print
        line += std::format(" {}={:.{}f}", row.name, settings.*(row.member), row.decimals);
    }
    return line;
}
```

The world wind's own two, `applyWindFronts` for `--wind-fronts` and `windFrontsLine` for **Log values**, hand the
walkers its table. In `WorldWind.cpp`, replace the comment line
`// No slider clamps a typed value: Configure turns a bad one away, and the demo puts the old one back.` with:

```cpp
InitializationResult applyWindFronts(WorldWindSettings& settings, std::string_view assignment, float& used, bool& clamped)
{
    return debug_panels::applySettingAssignment(WIND_FRONT_ROWS, settings, "--wind-fronts", "wind-front setting", assignment, used, clamped);
}

std::string windFrontsLine(const WorldWindSettings& settings)
{
    return debug_panels::settingRowsLine(WIND_FRONT_ROWS, "Wind fronts:", settings);
}

// No slider clamps a typed value: Configure turns a bad one away, and the demo puts the old one back. Chapter 56 section 1:
// the fronts' rows hold a typed value inside their ranges, under a collapsed "Fronts" node.
```

The panel draws the rows under a **Fronts** header, which starts collapsed, one node for each group. In
`drawWorldWindPanel`, below the **Wind paused** checkbox, add:

```cpp
    if (ImGui::CollapsingHeader("Fronts"))
    {
        if (ImGui::TreeNode("Gusts"))
        {
            changed |= debug_panels::drawSettingRows(WIND_FRONT_ROWS, WIND_FRONT_GUSTS, settings);
            ImGui::TreePop();
        }
        if (ImGui::TreeNode("Ripples"))
        {
            changed |= debug_panels::drawSettingRows(WIND_FRONT_ROWS, WIND_FRONT_RIPPLES, settings);
            ImGui::TreePop();
        }
    }
```

Last, `applyWorldWind` in `FrameData.h` copies the block with the rest. Below its `frame.windGust` line, add:

```cpp
    frame.windFronts    = wind.fronts;   // Chapter 56 section 1: the fronts, with the wind that owns them
```

**The grass reads it.** The grass's compute pass cannot read `FrameData`
([Chapter 42, section 1](42-One-Wind.md#1-four-winds-in-one-frame)), so `GrassParameters` keeps its thirteen front
floats where they were and stays 720 bytes, and the kernel's arithmetic does not change. Only who fills them changes:
`PackParameters` copies them from the state in `GrassFrame::wind`, a plain copy, since the wind has held them already.
Two free floats of the block carry the travel correction, which the kernel reads at the end of this section. In
`GrassTypes.h`, replace the lines of `padding3` and `padding4` with:

```cpp
    float travelCorrectionX; /* Chapter 56 section 1: the world wind's correction to the fronts' frame, metres of travel (the swell ignores it) */
    float travelCorrectionY;
```

`GrassField.h` loses the thirteen settings, their ranges, their two groups and their rows, and its comments say where
they went: six edits, top to bottom. In `GrassSettings`, replace the lines from
`    // panel's "Wind response" section edits these.` down to the `rippleBaseline` member with:

```cpp
    // panel's "Wind response" section edits these. Chapter 56 section 1: where the fronts are (thirteen of Chapter 53's
    // settings) is a fact of the island and lives in WorldWindSettings; what is left is how this grass answers them.
    // Answer: how this grass takes the fronts
    float     swellWeight      = 0.35f;  // how much the slow swell lifts and lowers the gusts and breathes the steady lean
    float     rippleStrength   = 0.2f;   // the ripples' answer as a share of a gust's
```

Replace the lines from `using WindRange = debug_panels::SettingRange;` down to the `RIPPLE_BASELINE_RANGE` line with
these: the alias now names the wind's, and the two ranges left before `SPRING_FREQUENCY_RANGE` are the grass's answer's:

```cpp
// Chapter 56 section 1: the fronts' ranges went with them, into WorldWind.h.
using vulkan_graphics::WindRange;

// The wind-response settings' ranges, in the settings' order.
inline constexpr WindRange SWELL_WEIGHT_RANGE        { 0.0f, 1.0f };
inline constexpr WindRange RIPPLE_STRENGTH_RANGE     { 0.0f, 0.6f };
```

Replace the lines from the enum's one line down to the comment line that starts
`// The wind-response settings by name, in the panel's six tree nodes` with these; the `};` and the blank line between
stay as they are:

```cpp
    WIND_ANSWER, WIND_SPRING, WIND_LEAN, WIND_BLADES, WIND_SHADING, WIND_SHADING_LEGACY
};

// The wind-response settings by name, in the panel's tree nodes: the one place the names exist. A row is the
```

In `WIND_RESPONSE_SETTINGS`, replace the rows from `    // Gusts: where the big fronts are` down to the `rippleBaseline`
row with these three lines, and below the table make the count
`static_assert(WIND_RESPONSE_SETTINGS.size() == 19, "one row per wind-response setting");`:

```cpp
    // Answer: how this grass takes the fronts (where they are is the world wind's, Chapter 56 section 1)
    PF_WIND_RESPONSE_ROW(swellWeight, SWELL_WEIGHT_RANGE, 2, "Swell weight", WIND_ANSWER),
    PF_WIND_RESPONSE_ROW(rippleStrength, RIPPLE_STRENGTH_RANGE, 2, "Ripple strength (x gust lean)", WIND_ANSWER),
```

Replace the comments of `applyWindResponse` and `windResponseLine`, from the line that starts
``// Applies "name=value" to `settings` `` down to the comment line above `windResponseLine`, with:

```cpp
// Applies "name=value" (`--grass-response`) to `settings`, the value clamped to the row's range. Fails (and changes nothing) with a
// message that names the problem and lists the valid names when the name is unknown or the number malformed or not finite.
// `used` is the value stored; `clamped` is whether the range changed it. Chapter 56 section 1: the walker is
// debug_panels::applySettingAssignment, which the world wind's fronts use too.
InitializationResult applyWindResponse(GrassSettings& settings, std::string_view assignment, float& used, bool& clamped);

// The "Log values" line, without its log prefix: every wind-response setting from the table, then the world wind (the fronts
// have their own line, vulkan_graphics::windFrontsLine).
```

In `GrassField.cpp`, Chapter 53's three file-scope helpers go, `applyWindResponse` and `windResponseLine` call the
walkers, `packWindResponse` loses its hold on the longest push (the wind holds it now), and `packWindFronts` copies the
block. `applyWindResponse` also refuses a front's name with a message that names the new flag, so Chapter 53's printed
control, `--grass-response gustJitter=0`, says where it went. Replace everything from
`// File scope, above PackParameters: the setting held inside its slider's range.` down to the blank line below
`packWindResponse`'s closing brace with these lines; `PackParameters` follows the last brace directly, with no blank
line between:

```cpp
InitializationResult applyWindResponse(GrassSettings& settings, std::string_view assignment, float& used, bool& clamped)
{
    // Chapter 53's command line named the fronts here; they are the world wind's rows now (Chapter 56 section 1).
    const std::size_t equals = assignment.find('=');
    const std::string_view name = assignment.substr(0, equals);
    if (debug_panels::findSettingRow(WIND_FRONT_ROWS, name) != nullptr)
    {
        return InitializationResult::failure(std::format("--grass-response: '{}' is the world wind's now: use --wind-fronts {}=<value>", name, name));
    }
    return debug_panels::applySettingAssignment(WIND_RESPONSE_SETTINGS, settings, "--grass-response", "wind-response setting", assignment, used, clamped);
}

std::string windResponseLine(const GrassSettings& settings, const WorldWindSettings& wind)
{
    std::string line = debug_panels::settingRowsLine(WIND_RESPONSE_SETTINGS, "Wind response:", settings);
    line += std::format(" | world wind: speed={:.1f}m/s strength={:.2f} gustSize={:.1f}m", wind.speed, wind.strength, wind.gustSize);
    return line;
}

// File scope, above PackParameters: the 19 wind settings into their fields, each held inside its slider's range. The
// thirteen fronts are not among them (Chapter 56 section 1): the world wind publishes them already held inside their ranges,
// and PackParameters copies them from its state.
static void packWindResponse(const GrassSettings& settings, GrassParameters& parameters)
{
    debug_panels::packSettingRows(WIND_RESPONSE_SETTINGS, settings, parameters, true);
}

// File scope, above PackParameters: the world wind's fronts into the grass's block, a plain copy. The grass's compute pass
// cannot read FrameData (Chapter 42 section 1), so it keeps its own thirteen floats, at the same places as ever.
static void packWindFronts(const shared::WindFronts& fronts, GrassParameters& parameters)
{
    parameters.frontSpeed       = fronts.frontSpeed;
    parameters.gustSpacing      = fronts.gustSpacing;
    parameters.gustJitter       = fronts.gustJitter;
    parameters.gustCrestLength  = fronts.gustCrestLength;
    parameters.gustCrestBend    = fronts.gustCrestBend;
    parameters.gustOccupancy    = fronts.gustOccupancy;
    parameters.gustLengthMin    = fronts.gustLengthMin;
    parameters.gustLengthMax    = fronts.gustLengthMax;
    parameters.frontSizeFloor   = fronts.frontSizeFloor;
    parameters.rippleSpacing    = fronts.rippleSpacing;
    parameters.rippleJitter     = fronts.rippleJitter;
    parameters.rippleOccupancy  = fronts.rippleOccupancy;
    parameters.rippleBaseline   = fronts.rippleBaseline;
    parameters.travelCorrectionX = fronts.travelCorrectionX;   // Chapter 56 section 1: the fronts' frame pivots about the viewer
    parameters.travelCorrectionY = fronts.travelCorrectionY;
}
```

In `PackParameters`, below the line `packWindResponse(settings, parameters);   // Chapter 53: the wind response`, add:

```cpp
    packWindFronts(frame.wind.fronts, parameters);   // Chapter 56 section 1: where the fronts are
```

The grass's panel keeps one node for its two answers. In `GrassDemo.cpp`'s `drawWindResponse`, replace the **Gusts** and
**Ripples** nodes, from `    if (ImGui::TreeNode("Gusts"))` to the `}` that closes **Ripples**, with the first listing;
below `Log::info(windResponseLine(settings, wind).c_str());`, add the second:

```cpp
    if (ImGui::TreeNode("Answer"))   // Chapter 56 section 1: the fronts themselves are the wind's, under Wind > Fronts
    {
        pf::debug_panels::drawSettingRows(WIND_RESPONSE_SETTINGS, WIND_ANSWER, settings);
        ImGui::TreePop();
    }
```

```cpp
                Log::info(windFrontsLine(wind).c_str());   // Chapter 56 section 1: where the fronts are, the wind's own
```

`--wind-fronts` reaches the Grass demo's and Horizon's `WorldWind`, each the demo's own, through a setter, as
`--grass-response` does. Add the first below the closing brace of `SetWindResponse` in `GrassDemo.h`, and the second
below `SetWindSpeed` in `HorizonDemo.h`, each directly against the lines above and below it, with no blank line, as the
setters around it sit:

```cpp
    // --wind-fronts name=value, already checked by Main (a bad one changes nothing): where this demo's world wind has its fronts.
    void SetWindFront(std::string_view assignment)
    {
        float used = 0.0f;
        bool clamped = false;
        (void)vulkan_graphics::applyWindFronts(m_windSettings, assignment, used, clamped);
    }
```

```cpp
    // --wind-fronts name=value, already checked by Main (a bad one changes nothing): where Horizon's world wind has its fronts.
    void SetWindFront(std::string_view assignment)
    {
        float used = 0.0f;
        bool clamped = false;
        (void)vulkan_graphics::applyWindFronts(m_windSettings, assignment, used, clamped);
    }
```

**Horizon's grass takes the whole state.** `CoastalArea::Prepare` built the grass's wind from `FrameData`'s two vectors
with a brace list, `{ data.windDirection, data.windGust }`. That still compiles with `WorldWindState` at 96 bytes and
leaves the fronts at zero: no gusts at Coast, and no error. `FrameData` holds no `WorldWindState` to copy, so `Prepare`
takes the state itself, and a field the wind gains later reaches the grass without another line. In `CoastalArea.h`,
replace the first line of `Prepare`'s declaration with:

```cpp
    // Chapter 56 section 1: `wind` is the demo's whole world wind as it publishes it, so the grass answers the same fronts as
    // everything else, and a field the wind gains later reaches it without another line here.
    InitializationResult Prepare(const RecordContext& frame, const shared::FrameData& data, const vulkan_graphics::WorldWindState& wind,
```

In `CoastalArea.cpp`, end the first line of `Prepare`'s definition with
`const shared::FrameData& data, const vulkan_graphics::WorldWindState& wind,` and replace its `.wind` line with the
listing below. In `HorizonDemo.cpp`'s `Record`, the call to `m_coastal.Prepare` passes `m_wind.State()` as its third
argument, after `frameData`.

```cpp
            .wind = wind,   // Chapter 42 section 1: Horizon's wind, as published; Chapter 56 section 1: the whole state, fronts too
```

**The flag.** `Main.cpp` checks every `--wind-fronts` against a scratch copy before any demo starts, as it checks
`--grass-response`, and the warning about a longest push below the shortest moves with the fronts. In each pair below,
the first line is there already and the second is new: the list in `LaunchSettings`, and its parse:

```cpp
    std::vector<std::string>          grassResponse;         // --grass-response name=value, repeatable (Chapter 53)
    std::vector<std::string>          windFronts;            // --wind-fronts name=value, repeatable (Chapter 56): the Grass and Horizon demos' world wind
```

```cpp
        else if (key == "--grass-response") { settings.grassResponse.emplace_back(value); }
        else if (key == "--wind-fronts") { settings.windFronts.emplace_back(value); }
```

Replace the block that checks `settings.grassResponse`, from its `{` to its `}`, with these two blocks:

```cpp
    {
        // Checked against a scratch copy here; the Grass demo and Horizon's coast apply the same assignments to their own settings.
        demos::grass::GrassSettings scratch;
        for (const std::string& assignment : settings.grassResponse)
        {
            float used = 0.0f;
            bool clamped = false;
            if (auto result = demos::grass::applyWindResponse(scratch, assignment, used, clamped); !result)
            {
                Log::error(result.message());
                return 1;
            }
            if (clamped)
            {
                Log::warning(std::format("--grass-response {}: outside its range; using {}.", assignment, used).c_str());
            }
        }
    }
    {
        // Chapter 56 section 1: the thirteen fronts left the grass. They are the world wind's, and every demo that owns one takes
        // them; checked here against a scratch copy, as --grass-response is.
        vulkan_graphics::WorldWindSettings scratch;
        for (const std::string& assignment : settings.windFronts)
        {
            float used = 0.0f;
            bool clamped = false;
            if (auto result = vulkan_graphics::applyWindFronts(scratch, assignment, used, clamped); !result)
            {
                Log::error(result.message());
                return 1;
            }
            if (clamped)
            {
                Log::warning(std::format("--wind-fronts {}: outside its range; using {}.", assignment, used).c_str());
            }
        }
        if (scratch.gustLengthMax < scratch.gustLengthMin)
        {
            Log::warning(std::format("--wind-fronts: gustLengthMax {} is below gustLengthMin {}; the wind publishes {}.",
                                     scratch.gustLengthMax, scratch.gustLengthMin, scratch.gustLengthMin).c_str());
        }
    }
```

and hand the list to both demos, each below its demo's `settings.grassResponse` loop:

```cpp
    for (const std::string& assignment : settings.grassResponse) { grassDemo.SetWindResponse(assignment); }
    for (const std::string& assignment : settings.windFronts) { grassDemo.SetWindFront(assignment); }
```

```cpp
    for (const std::string& assignment : settings.grassResponse) { horizonDemo.SetGrassWindResponse(assignment); }
    for (const std::string& assignment : settings.windFronts) { horizonDemo.SetWindFront(assignment); }
```

**The copy retires.** The reflection lesson's supplied test compared the rows with `SettingsByHand.h`, the copy of your
own code you made before anything moved
([its section 2](SettingsAsRows.md#2-before-you-change-anything-keep-what-your-code-does)). This chapter changes those
settings, so the code in the copy no longer exists anywhere in your tree. The copy retires whole, as the lesson said it
would, and from stage 4 the test checks the row tables themselves (the Jump above **When the wind turns**).

`SettingRowsTests.cpp` ships on `start` as it is after this chapter, at stage 0. If the comment above its
`#define PF_TEST_STAGE` line does not mention Chapter 56, your copy is older: replace the file with
`Tests/TutorialHarness/SettingRowsTests.cpp` from `start` or `reference-main`. Then replace the line that starts
`#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 4   // raised in sections 3, 5 and 6 of the lesson, and in section 1 of Chapter 56
```

From stage 4 `PF_TEST_COPY` is 0 and the test no longer includes the copy. In `premake5.lua`, the
`TutorialSettingRowsTests` project's comment and its `files` line change; the five lines become:

```lua
    -- The settings lesson's supplied test: what the rows pack, draw, type into and keep, then Chapter 56's row tables.
    project "TutorialSettingRowsTests"
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/SettingRowsTests.cpp" }
```

Then delete `Tests/TutorialHarness/SettingsByHand.h`. A deleted file means `GenerateProjects.bat` again, then a build;
the checkpoint below does both.

**Your Chapter 53 test.** `GrassWindTests.cpp` checks the grass's table and its **Log values** line, and both lost
thirteen rows; its `gustJitter` checks now go through the fronts' table and `--wind-fronts`. Below
`using pf::vulkan_graphics::WorldWindSettings;`, add the first listing. Replace the last three lines of the comment
above `size_t offsetOf(float GrassSettings::* member)` with the second:

```cpp
using pf::vulkan_graphics::applyWindFronts;
using pf::vulkan_graphics::windFrontsLine;
```

```cpp
// cannot disagree; what a hand-kept list would add is the order. GrassSettings keeps the 19 floats contiguous in group
// order (2 answer, 4 spring, 5 lean, 4 blades, 4 shading), so the check is that consecutive rows' offsets rise by exactly 4
// bytes. The other 13 of Chapter 53's 32 are the world wind's since Chapter 56 section 1; their rows are SettingRowsTests'.
```

Replace everything from `// The "Log values" output (after its "[INFO] " prefix)` down to the blank line above
`void checkNameTable()` with these lines; `void checkNameTable()` follows the last one directly, with no blank line
between:

```cpp
// The "Log values" output (after its "[INFO] " prefix) for default GrassSettings under the Grass demo's default world wind
// (GrassDemo.h: 5.5 m/s, strength 0.6, gust size 10 m), recorded when Chapter 56 section 1 moved the fronts out of the table.
const char* const EXPECTED_DEFAULT_LINE =
    "Wind response: swellWeight=0.35 rippleStrength=0.20 springFrequency=0.80 springDamping=0.20 springSpread=0.15 "
    "tipLag=0.25 steadyLean=0.350 gustLean=1.500 dragKnee=9.0 leanLimit=0.80 impostorLean=1.20 bladeLagSpread=0.10 "
    "bladeFlutter=0.010 crosswindShrink=0.60 swingStraighten=0.70 gustBrightness=0.40 layLight=2.00 rootRoughness=1.50 "
    "farHighlight=0.50 | world wind: speed=5.5m/s strength=0.60 gustSize=10.0m";

// The second line "Log values" prints, from the world wind's own table: the 13 fronts at Chapter 53's defaults.
const char* const EXPECTED_FRONTS_LINE =
    "Wind fronts: frontSpeed=1.00 gustSpacing=17.0 gustJitter=0.45 gustCrestLength=16.0 gustCrestBend=0.40 gustOccupancy=0.95 "
    "gustLengthMin=3.0 gustLengthMax=6.0 frontSizeFloor=0.15 rippleSpacing=3.75 rippleJitter=0.45 rippleOccupancy=0.55 "
    "rippleBaseline=0.20";
```

In `checkNameTable`, replace everything from `    GrassSettings edited;` down to the line in `EXPECTED_BOUNDS` that
starts `        { "rippleBaseline",` with these lines. The blank line that stood above `// Each row's range` goes:

```cpp
    // Chapter 56 section 1: the fronts are the world wind's, so the gustJitter checks run through its table and `--wind-fronts`.
    const std::string frontsLine = windFrontsLine(WorldWindSettings{});
    if (frontsLine != EXPECTED_FRONTS_LINE) { std::cout << "      got: " << frontsLine << '\n'; }
    check(frontsLine == EXPECTED_FRONTS_LINE, "the \"Log values\" fronts line for the default world wind is byte-identical to the recorded output");

    WorldWindSettings edited;
    float used = -1.0f;
    bool clamped = true;
    const auto applied = applyWindFronts(edited, "gustJitter=0", used, clamped);
    const std::string editedLine = windFrontsLine(edited);
    check(static_cast<bool>(applied) && used == 0.0f && !clamped && editedLine.find(" gustJitter=0.00 ") != std::string::npos,
          "gustJitter=0 through the fronts' lookup shows gustJitter=0.00 in the line");

    WorldWindSettings over;
    check(static_cast<bool>(applyWindFronts(over, "gustJitter=5", used, clamped)) && clamped && used == 0.45f && over.gustJitter == 0.45f,
          "a front value past the range is clamped to it and reported");
    GrassSettings grassOver;
    check(static_cast<bool>(applyWindResponse(grassOver, "swellWeight=5", used, clamped)) && clamped && used == 1.0f && grassOver.swellWeight == 1.0f,
          "a grass value past the range is clamped to it and reported");
    GrassSettings bad;
    WorldWindSettings badFronts;
    const auto unknown = applyWindResponse(bad, "nosuch=1", used, clamped);
    const auto unknownFront = applyWindFronts(badFronts, "nosuch=1", used, clamped);
    const auto malformed = applyWindFronts(badFronts, "gustJitter=abc", used, clamped);
    const auto missing = applyWindFronts(badFronts, "gustJitter", used, clamped);
    check(!unknown && std::string(unknown.message()).find("swellWeight") != std::string::npos && std::string(unknown.message()).find("--grass-response") != std::string::npos &&
          !unknownFront && std::string(unknownFront.message()).find("frontSpeed") != std::string::npos && std::string(unknownFront.message()).find("--wind-fronts") != std::string::npos &&
          !malformed && !missing && badFronts.gustJitter == WorldWindSettings{}.gustJitter,
          "an unknown name or malformed number fails, lists that table's names, and changes nothing");
    // Chapter 53's printed control names a front; it is the world wind's row now, and the message says where it went.
    const auto movedFront = applyWindResponse(bad, "gustJitter=0", used, clamped);
    check(!movedFront && std::string(movedFront.message()).find("world wind's now: use --wind-fronts gustJitter=") != std::string::npos,
          "--grass-response gustJitter=0 fails and says to use --wind-fronts");

    // Edge cases: each must fail with a message and leave the settings alone.
    const char* const BAD_ASSIGNMENTS[] = { "gustJitter=nan", "gustJitter=inf", "gustJitter=", "=1", "gustJitter=1x", " gustJitter=1", "gustJitter= 1" };
    bool edgeFailuresHold = true;
    for (const char* assignment : BAD_ASSIGNMENTS)
    {
        WorldWindSettings untouched;
        const auto result = applyWindFronts(untouched, assignment, used, clamped);
        const bool held = !result && !std::string(result.message()).empty() && untouched.gustJitter == WorldWindSettings{}.gustJitter;
        if (!held) { std::cout << "      bad assignment not refused cleanly: " << assignment << '\n'; }
        edgeFailuresHold = edgeFailuresHold && held;
    }
    check(edgeFailuresHold, "nan, inf, an empty value, an empty name, trailing text and stray spaces all fail and change nothing");
    // Each row's range: a huge value stores its max, a hugely negative one its min, against a hand-written list.
    struct Bounds { const char* name; float min; float max; };
    const Bounds EXPECTED_BOUNDS[] = {
        { "swellWeight", SWELL_WEIGHT_RANGE.min, SWELL_WEIGHT_RANGE.max }, { "rippleStrength", RIPPLE_STRENGTH_RANGE.min, RIPPLE_STRENGTH_RANGE.max },
        { "springFrequency", SPRING_FREQUENCY_RANGE.min, SPRING_FREQUENCY_RANGE.max },
```

**`FrameData`'s size, in your tests.** `WorldWindTests.cpp` and `RendererConvergenceTests.cpp` hold 448 bytes since
Chapter 42; without these edits the build stops on a `static_assert`, and RendererConvergence fails when it runs. In
`WorldWindTests.cpp`, replace the six lines from `// The state is FrameData's two wind vectors` down to the
`static_assert` on `WorldWindState` with the first listing, and the line that sets `grassFrame.wind` with the second,
which builds the grass's frame as `Prepare` now does. In `RendererConvergenceTests.cpp`, replace the two-line `check`
that starts `check(sizeof(frame) == 448` with the third:

```cpp
// The state is FrameData's two wind vectors and its thirteen fronts, field for field, so applyWorldWind is three copies.
static_assert(sizeof(shared::FrameData) == 512, "FrameData must be 512 bytes from Chapter 56 section 1.");
static_assert(offsetof(shared::FrameData, windDirection) == 416 && offsetof(shared::FrameData, windGust) == 432,
              "The wind must be appended after Chapter 51's atmosphere.");
static_assert(sizeof(WorldWindState) == 96 && offsetof(WorldWindState, gust) == 16 && offsetof(WorldWindState, fronts) == 32,
              "WorldWindState must mirror FrameData's windDirection, windGust and windFronts.");
```

```cpp
        grassFrame.wind = wind.State();   // as CoastalArea::Prepare takes it: the whole state, fronts too
```

```cpp
            check(sizeof(frame) == 512 && frame.haze == glm::vec4(0.0f) && frame.hazeSky == 0,
                  "FAIL: FrameData is 512 bytes (haze, wind and fronts) and its haze is off by default");
```

**The cure.** The turn you watched with the kept build, and the second prediction's answer. Turn F about p by the same
angle: F′ = p − R(dθ)(p − F), R(dθ) the turn by dθ. The world wind keeps a correction C, in metres of travel and in
double, so that the frame starts at F = frontSpeed (travel + C); on a frame whose published direction turns, `Advance`
computes F′ and keeps the C that puts the origin there, C = F′ / frontSpeed − travel. The viewer's own place in the
pattern does not move; a clump D away still sweeps D × dθ, as any pattern that turns with the wind must. C changes only
on a frame that turns, and nothing resets it. Only the fronts read it: the published offset, `windDirection.zw`, keeps
the true travel, so Chapter 42's contract holds, and so does the grass's slow swell, which reads `windTravel` on a line
of its own.

`Advance` reads the angle from the old and the new published vectors, the floats every reader sees, so one function,
`publishedAlong`, gives `Advance` and `Publish` the same floats for an angle. In `WorldWind.cpp`, below
`shortestTurnDegrees`, add, with a blank line on each side:

```cpp
// File scope, above the namespace block. The floats Publish writes for a blows-toward angle.
static glm::vec2 publishedAlong(float towardDegrees)
{
    const float toward = glm::radians(towardDegrees);
    return glm::vec2{ std::sin(toward), -std::cos(toward) };
}
```

In `Advance`, between the line that sets `m_towardDegrees` and `Publish();`, add, with a blank line above:

```cpp
    // Chapter 56 section 1: when the published direction turned this frame and a pivot is set, turn the fronts' frame about the
    // pivot by the same angle, so a foot at the pivot does not move through the pattern and one D away sweeps D x dtheta. The
    // angle is read from the old and the new published vectors in double (a front's reader sees exactly those floats). With
    // no turn, or no pivot, the correction is left as it was: 0 unless a turn has moved it.
    const glm::vec2 oldAlong{ m_state.direction.x, m_state.direction.y };
    const glm::vec2 newAlong = publishedAlong(m_towardDegrees);
    if (m_hasPivot && newAlong != oldAlong && m_state.fronts.frontSpeed > 0.0f)
    {
        const double cross  = static_cast<double>(oldAlong.x) * newAlong.y - static_cast<double>(oldAlong.y) * newAlong.x;
        const double dot    = static_cast<double>(oldAlong.x) * newAlong.x + static_cast<double>(oldAlong.y) * newAlong.y;
        const double dtheta = std::atan2(cross, dot);
        const double c      = std::cos(dtheta);
        const double s      = std::sin(dtheta);
        const double speed  = static_cast<double>(m_state.fronts.frontSpeed);
        const glm::dvec2 origin = speed * (m_offset + m_travelCorrection);   // F, with this frame's travel already in the offset
        const glm::dvec2 arm    = m_pivot - origin;
        const glm::dvec2 turned{ c * arm.x - s * arm.y, s * arm.x + c * arm.y };
        const glm::dvec2 moved  = m_pivot - turned;                          // F'
        m_travelCorrection      = moved / speed - m_offset;
    }
    if (m_hasPendingPivot) { m_pivot = m_pendingPivot; m_hasPivot = true; }   // the pivot of the next turn step
```

In `Publish`, replace the two lines that compute `toward` and `along` with
`const glm::vec2 along = publishedAlong(m_towardDegrees);`, indented as they were, and below the `gustLengthMax` line
you added before, add:

```cpp
    m_state.fronts.travelCorrectionX = static_cast<float>(m_travelCorrection.x);   // Chapter 56 section 1: only the fronts read it
    m_state.fronts.travelCorrectionY = static_cast<float>(m_travelCorrection.y);
```

A pivot handed to `SetPivot` before one `Advance` is used from the next, so moving the camera changes nothing published
on the frame it moves. A non-finite pivot is ignored: nothing resets C, so one NaN would stay in every reader's fronts.
In `WorldWind.h`, add the first listing below `State()` and the second below `m_offset`:

```cpp
    // Chapter 56 section 1: where the viewer stands (world x and z). A demo calls it each frame before Advance; never called,
    // there is no pivot. It takes effect from the next Advance on (this frame's turn step uses the pivot of the frame before),
    // so moving it changes no published value on the frame it moves. When the published direction turns, the fronts' frame
    // turns about it, so the pattern does not sweep past the viewer. A non-finite xz is ignored: nothing resets the
    // correction, so one NaN would stay in every reader's fronts for the rest of the run.
    void                     SetPivot(glm::vec2 xz)
    {
        if (!std::isfinite(xz.x) || !std::isfinite(xz.y)) { return; }
        m_pendingPivot    = glm::dvec2(xz);
        m_hasPendingPivot = true;
    }
    // The correction to the fronts' origin, in metres of travel: the fronts sit at frontSpeed * (travel + correction).
    // 0 at construction; Configure leaves it as it is (it never resets the offset either); nothing else resets it.
    glm::dvec2               TravelCorrection() const { return m_travelCorrection; }
```

```cpp
    glm::dvec2        m_travelCorrection{ 0.0 };   // Chapter 56 section 1: read only by the fronts, published as fronts.travelCorrection
    glm::dvec2        m_pivot{ 0.0 };
    glm::dvec2        m_pendingPivot{ 0.0 };
    bool              m_hasPivot        = false;
    bool              m_hasPendingPivot = false;
```

Both demos hand the wind their camera every frame. In `GrassDemo.cpp`'s `Update` and in `HorizonDemo.cpp`'s, above
`m_wind.Advance(input.deltaSeconds);`, add:

```cpp
    m_wind.SetPivot({ m_cameraTransform.translation.x, m_cameraTransform.translation.z });   // Chapter 56 section 1: the fronts pivot about the viewer
```

Last, the kernel: its front-frame line adds the correction, and the swell, a few lines below, keeps `windTravel`. In
`GrassGenerateKernel.glsl`, replace the line that starts `vec2  frontFrame = xz - grass.frontSpeed * windTravel;` with:

```glsl
    vec2  frontFrame = xz - grass.frontSpeed * (windTravel + vec2(grass.travelCorrectionX, grass.travelCorrectionY));   // the frame the fronts keep still in (Chapter 56 section 1: the swell keeps windTravel)
```

Without a turn C stays exactly 0. Measured on the reference RTX 5090, the steady wind at Wind edge drew the same frame,
byte for byte, with the correction and without it, and the checkpoint below captures Coast. One edit still moves the
whole pattern, as it did before: changing **Front speed** after turns moves it by the change times |travel + C|.

**The supplied test.** `TutorialPlantWindTests` checks the plants' wind on the CPU, through the headers the shaders
include; it opens no window and makes no device. Its first stage can run now, and each later section raises it.

**`premake5.lua`.** Inside the `if _OPTIONS["tutorial-tests"] then` block, below the `TutorialGrassWindTests` project
and its blank line, add, with a blank line below it:

```lua
    project "TutorialPlantWindTests"   -- Chapter 56: the plants' wind, on the CPU, one stage per section
        kind "ConsoleApp"
        apply_common_cpp_settings()
        files { "Tests/TutorialHarness/PlantWindTests.cpp" }
        includedirs { "Vendor/GLFW/include" }   -- GrassField.h reaches GlfwWindow.h through Demo.h
        links { "PillowFortEngine", "GLFW", "ImGui", "TinyUSDZ" }
```

**`PlantWindTests.cpp`, supplied.** It is `Tests/TutorialHarness/PlantWindTests.cpp`. A learning branch made from
`start` has it at stage 0; otherwise copy it there from a `reference-main` checkout
([Which checkout](../VulkanTutorial.md#choose-your-checkout)); a new file means regenerating, then building, which the
checkpoint does. Replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 1   // raised in each section of Chapter 56
```

Stage 1 checks `Publish`'s clamp of each front at both ends of its range, an in-range value published bit for bit, a NaN
or an infinity refused, and the real `PackParameters` on a default `GrassField` packing Chapter 53's 720 bytes, which
the test holds, non-finite inputs included. Then the pivot: with no turn the correction is exactly 0; with no pivot ever
set it stays 0 through a 187-degree turn; across a turn the pivot's own place in the pattern does not move, at 0 and
5.5 m/s, and a foot D away sweeps D × dθ; a pivot moved mid-turn changes nothing that frame; a non-finite one is
ignored. Each check has a control the test computes itself, such as the turn's sense flipped or no correction at all,
and it prints how far each lands from its tolerance. From stage 7 it also turns the wind a thousand times with the pivot
10 km away.

**Answer to the transfer.** No. How much of the ripples a reader takes is its answer, not where the ripples are, and a
row of `WindFronts` would give every reader one share. Section 2 puts the trees' share, `rippleWeight`, in their own
block, `PlantWind`, beside their spring, as the grass keeps `rippleStrength` among its own settings.

</details>

### Checkpoint

The test file is new and `SettingsByHand.h` is gone, so generate again with the test projects. Build the game in
Release, the build every capture here uses, and the tests in Debug with the serial flags of the shell build in
[Building PillowFort](../Premake.md#the-everyday-path), as Chapter 53's checkpoints did; then run the tests from the
repository root:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The game build failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:TutorialPlantWindTests;TutorialSettingRowsTests;TutorialGrassWindTests;TutorialWorldWindTests;TutorialRendererConvergenceTests'
if ($LASTEXITCODE -ne 0) { throw 'The test build failed.' }
foreach ($test in 'PlantWind', 'SettingRows', 'GrassWind', 'WorldWind', 'RendererConvergence')
{
    & ".\Build\Artifacts\Debug\Tutorial${test}Tests\Tutorial${test}Tests.exe"
    if ($LASTEXITCODE -ne 0) { throw "Tutorial${test}Tests failed." }
}
```

The supplied test prints a line about the pivot for each of its two wind speeds, then
`PASS: plant wind, stage 1 (26 checks)`; the settings test ends `PASS: settings rows, stage 4 (138 checks)`; the other
three each end in a line that starts `PASS:`.

**The frame.** Horizon at Coast, the sky off, captured at a fixed clock with the kept build and with this one:

```powershell
& ..\SandboxGame-before-56\SandboxGame.exe `
    --demo Horizon --horizon-view Coast --sky off --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output coast-before-56.bmp
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --demo Horizon --horizon-view Coast --sky off --msaa 4 `
    --width 1600 --height 900 --fixed-dt 0.016666667 --frames 120 --capture-output coast-56-1.bmp
Get-FileHash coast-before-56.bmp, coast-56-1.bmp
```

On the reference RTX 5090 the two are equal, byte for byte: the grass reads its fronts from the world wind and draws the
same frame. The frame holds the coastal grass, which draws in the order the GPU's atomics hand out slots; if yours
differ, judge them as Chapter 42, section 1 judges the grass. A `Prepare` that still built its wind from the two vectors
differs here: Coast's grass has no gusts.

- Run the Grass demo and open **Wind**, then **Fronts** and **Gusts**. Drag **Gust spacing (m)**: the bands move apart
  or together, as Chapter 53's slider moved them. Horizon has **Fronts** of its own, because each demo owns its wind.
- Chapter 53's positive control is `--wind-fronts gustJitter=0` now: the fronts become a metronome. Given as
  `--grass-response gustJitter=0`, it stops at the start with the message
  `--grass-response: 'gustJitter' is the world wind's now: use --wind-fronts gustJitter=<value>`.
- Run the turn again with this build: the command under **When the wind turns**, with
  `./Build/Artifacts/Release/SandboxGame/SandboxGame.exe` in place of the kept build. The bands turn where they stand.
  On the reference's RTX 5090, in the command's default 1280 × 720 window with a capture every second frame through the
  turn, the grass's steps between captures were 0, 2 and 9 pixels (median, 90th percentile, largest) without the
  correction and 0, 0 and 2 with it.

The fronts are the island's now, and still nothing but the grass answers them. Section 2 bends a tree on them.

Next in this chapter: [Section 2 — A tree bends from its foot](EverythingBendsATree.md).
