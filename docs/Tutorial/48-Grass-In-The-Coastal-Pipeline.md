# 48 — Grass In The Coastal Pipeline

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Goal:** bring the captured grass and its handover to the island's coast
inside Horizon's one frame, keeping habitat, shoreline state and shadows, and
measure the trade instead of assuming it.

The standalone field now has a smaller representation. Transfer it to the
coast without copying a renderer, losing habitat constraints or calling a
smaller triangle count a performance result.

**ROADMAP:** step 21+ — the `Horizon` demo grows.

**Prerequisites:** Chapter 47's identity, projected handover, coverage,
deformation and reconstructed-depth contracts; Chapter 41, sections
[1](41-Grass-On-The-Island.md#1-one-frame-several-systems)–[3](41-Grass-On-The-Island.md#3-habitat-before-density)
(shared coastal owners, rendered-triangle roots and habitat); and Chapter 43,
sections
[1](43-Waves-To-The-Shore.md#1-a-bed-that-does-not-move-with-the-camera),
[3](43-Waves-To-The-Shore.md#3-the-same-water-at-different-frame-rates) and
[5](43-Waves-To-The-Shore.md#5-remember-where-water-has-been) (the fixed bed,
physical clock and wet-history state that the opening bookmark exercise must
preserve). Reuse steps 1–3 of [Renderer convergence](RendererConvergence.md) for
shared geometry, separate camera/cascade visibility and fallible frames, and
Chapter 17, sections
[11](17-Shadows.md#11-cascaded-shadow-maps)–[13](17-Shadows.md#13-choosing-a-cascade-per-pixel-and-hiding-the-seams)
for cascade projection and blending.

**Start here:** read the persistent-world problem below, then prepare its
`ch48-persistent-world` pair through the
[stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md). Work one declared
omission at a time, keeping source identity, coverage, appearance and timing
as separate checks. The accepted profile below is a comparison checkpoint;
each later problem names its own source pair or worked-source support.

From the outer reference checkout, in PowerShell 7, each line prepares,
builds, checks and smokes one variant in Release:

```powershell
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch48-persistent-world -Variant Starter -Configuration Release -ExpectIncomplete -ReuseNativeDependencies -BuildWorkers 1 -MinimumAvailableMemoryMiB 4100 -MemoryFloorMiB 3072
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch48-persistent-world -Variant Solution -Configuration Release -ReuseNativeDependencies -BuildWorkers 1 -MinimumAvailableMemoryMiB 4100 -MemoryFloorMiB 3072
```

This Starter's one intended failure is
`FAIL: camera bookmarks preserve world systems and shoreline state`, reported
by a native tour of six bookmarks, so its check needs the full launch gate
above. For a later problem with a pair, substitute that problem's stage ID;
[Reference solutions](ReferenceSolutions.md) lists them, and each Starter may
fail only its own declared check. How to run it:
[Working a prepared exercise](ReferenceSolutions.md#working-a-prepared-exercise).

### Choose one work block

The problems below form four passes. Complete the current problem's
acceptance check before moving to the next; each problem names whether its
support is a prepared pair or worked source. Keep that source tree and its
last passing check when pausing, so returning does not mean preparing a
different exercise over your edits.

| Work block | Problems, in order |
| --- | --- |
| [World and appearance](#coast-grass-world) | [Persistent world](#ch48-persistent-world) → [grass appearance](#ch48-grass-appearance) → [population and reach](#ch48-population-reach) |
| [Surface attachment](#coast-grass-surface) | [Rendered standalone surface](#ch48-rendered-standalone-surface) → [terrain budget](#ch48-terrain-budget) |
| [Source and placement](#coast-grass-source) | [Coarse work](#ch48-coarse-work) → [canonical source](#ch48-canonical-source) → [terrain frame](#ch48-terrain-frame) |
| [Frame, lighting and cost](#coast-grass-frame) | [Shared frame](#ch48-shared-frame) → [caster ownership](#ch48-caster-ownership) → [capture facing](#ch48-capture-facing) → [filtered lighting](#ch48-filtered-blade-lighting) → [measured budget](#ch48-measured-budget) |

Start with [Persistent world](#ch48-persistent-world). The accepted-profile
record below is a reference for later comparisons, not extra setup to finish
before that first problem.

<details>
<summary>Optional comparison: accepted profile and historical source evidence</summary>

**Accepted stopping point (2026-10-19):** Gary inspected the current RTX
Horizon build and accepted its appearance/performance balance. CPU/actual-GPU
contracts and native coverage, shadows, motion, recreation, scaled UI and 4K
controls pass on RTX/Radeon. The independent appearance Starter/Solution
builds, intended-failure checks and coastal smokes also pass. This does not
certify exact spatial-mip lighting or complete the original island-wide plan.
The [accepted checkpoint](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md#accepted-horizon-grass-checkpoint-2026-10-19)
preserves source/tag, local native payload, launch settings, measured cost and
unfinished work. Worked answers remain separate from actually running checks.

The inspected profile is explicit: `patches`, `blades`, 180 m reach, 32/24-pixel
selection, 4x MSAA, grass shadows on, sun sky and clouds off. Blade lighting is
the current default; source/reach/selection defaults remain legacy/42 m/32-12
in Horizon. This command reproduces the requested startup settings, not a
performance benchmark or a guaranteed window size after manual resizing:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe `
    --gpu RTX --demo Horizon --horizon-view "Forest floor" `
    --grass-source patches --grass-surface blades --coast-grass-reach 180 `
    --grass-impostors 1 --grass-geometry-pixels 32 --grass-proxy-pixels 24 `
    --grass-shadows 1 --sky sun --clouds 0 --msaa 4 --present mailbox `
    --width 1920 --height 1080 --ui-scale 1.5
```

Every flag is listed in [SandboxGame's command line](../VulkanTutorial.md#sandboxgames-command-line).

Use the existing native launch/memory guards and do not overlap it with a
build or GPU test. `Forest floor` contains a space; output filenames that
replace it with a hyphen are not valid bookmark names. Non-tiling ground
detail and tree-option changes are subsequent work in Chapters 38/39, not
additional changes to this accepted build.

The paired `ch48-grass-terrain` stage omits the projected terrain-height
budget. Independent Starter/Solution builds and exact-omission acceptance
checks and native scene smokes pass on both GPUs.
The shared-frame and measured-budget problems have worked answers, not
separate reconstructed starters. The [stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
explains preparation and the complete separate Solution tree.

The later final-scene follow-up adds the camera/world problem below. Its
source and verification status are tracked separately in `REFERENCE.md`;
it does not change the immutable earlier terrain-budget pair.
The terrain-frame and coarse-work exercises pin the later `b2db2ad` follow-up.
Their independent verification is separate from the historical pair above.
These focus on camera-space terrain fit and source-preserving scheduling;
sun-view eligibility, shadow-space error and separate caster ownership are
taught and checked by the later caster-ownership problem, not proved by
these earlier camera checks. Historical source pairs are not repinned.

</details>

The [forest-floor reference image](ReferenceImages.md#compose-the-field-with-the-world)
shows a historical composition check. Its diagnostic settings differ from the
accepted profile above; use the current problem's checks for your own changes.

<a id="coast-grass-world"></a>

# Part 1 — World and appearance (sections 1–3)

## 1. Move The Camera, Not The World

<a id="ch48-persistent-world"></a>

### Attempt CH48-persistent-world: keep a coastline alive while changing views

Start at Coast, then visit Meadow, Aerial, Village, the original Viewpoint
and Coast shore without recreating the demo. Which changes belong to the
camera, and which are changes to the world? Predict what happens to wet-sand
history if the solver is reinitialized when a bookmark is selected.

**Acceptance:** The same configured grass, sea, stable bed and shoreline
remain active throughout the tour. The bed fingerprint stays identical and
physical ticks never go backwards; with sea/flow enabled, they advance while
the camera is inland. Explicit sea-off/grass-off controls remain independent.
An explicitly selected legacy world stays legacy across every bookmark.
Inspect the ground-level Stream view too: the starter loses the nearby field,
while the solution keeps grass among the understory without changing camera.
Resize and target recreation retain valid descriptors. This problem does not
promise persistent GPU simulation state across full demo/MSAA teardown.

**Transfer:** Run the same tour with only the sea draw disabled. Should this
reinstate the old flat-water material? Explain why a water-rendering toggle
and the terrain's external-water mode are different decisions.

<details>
<summary>Hint 1: identify the hidden side effect</summary>

Compare `HorizonDemo::SelectView` with `Setup`. A bookmark should identify a
pose, not infer which scene systems exist from the spelling of its label.

</details>

<details>
<summary>Hint 2: give the world an explicit lifetime</summary>

Initialize the composed owners in Setup, after the borrowed renderer, sky
and terrain. Set the terrain's external-water and stable-bed policy from
world configuration there. Keep target-sized resources in Resize.

</details>

<details>
<summary>Hint 3: observe more than the final image</summary>

Record activation flags, bed identity and physical tick count at every
bookmark. A last photograph can look correct even if the world disappeared
inland or the shoreline reset between the first and last photograph.

</details>

<details>
<summary>Worked solution: separate world configuration from camera bookmarks</summary>

`HorizonDemo` starts with the integrated world enabled. Setup assigns
`externalWater` and `stableCoast` from that configuration, initializes the
shared coastal owners, and binds their wetness/water inputs. Resize binds
the current opaque targets. `SelectView` and `ReturnToViewpoint` now change
only camera/navigation state; they neither disable those owners nor reset
the shoreline clock. Ordinary inland views therefore consume the same world
as the coastal views. The current short-range grass representation is still
a separate unresolved landscape-LOD problem, not fixed by this lifetime change.

`--horizon-world legacy` explicitly retains the older isolated world for
comparisons. Unlike the old name-based shortcut, choosing Coast in this mode
does not silently change world configuration. `--coast-sea 0` hides/stops the
sea owner without switching the terrain back to its old flat-water branch.

The bounded diagnostic tour uses `--horizon-view-cycle-every 60 --frames 361`
with `--demo Horizon --fixed-dt 0.016666667`. It visits all six bookmarks and
checks actual observations from the running demo, including the original
Viewpoint. `VerifyWorldContinuity` rejects changed activation/terrain policy,
bed identity or a backwards/non-advancing enabled clock. The native program
prints one named `PASS:` or `FAIL:` assertion. Capture frames 1, 61, 121, 181,
241, 301 and 361 as well; passing the state contract alone does not certify
visual quality, shoreline calibration or performance.

Full demo/MSAA teardown currently reconstructs GPU simulation state. That is
a separate lifetime boundary and must not be disguised as camera continuity.
The paired starter deliberately restores the bookmark-dependent activation
mistake while leaving the renderer runnable; its complete solution is the
separate immutable Solution tree, not a disabled verification check.

</details>

## 2. Diagnose Ghosts And Bright Bands

<a id="ch48-grass-appearance"></a>

### Attempt CH48-grass-appearance: separate missing plants from translucent plants

At Shore, some full-sized blades look transparent against the sand. Inland,
a bright strip appears near the mesh/impostor handoff. Predict whether these
must be the same bug. Start with geometry-only rendering at a fixed camera,
time and population. Compare Coverage, Albedo, Occlusion and Specular views
before changing a colour, distance threshold or roughness.

**Acceptance:** Habitat changes the number of admitted clumps, not the opacity
of every admitted near clump. Preserve the exact `cut < density * habitat`
admission set. Distance thinning may still transition, and subpixel blade and
atlas silhouettes must retain their real fractional coverage at 1x/4x.
The Coverage diagnostic must be pixel-identical when only the lighting policy
changes: display the final production area, not a squared or per-view average.
Blade lighting must not rotate normals toward the ground or remove root
occlusion across the old 25-42 m interval. Compare the same source with meshes
and impostors at Shore, Forest floor and Stream, including backlighting,
shadows, motion and 4K. Passing a policy oracle is not visual acceptance.

**Transfer:** A clump has habitat probability 0.04, a blade covers 30% of a
pixel, and its representation is halfway through handoff. Which quantities
choose source existence, physical sample coverage and representation ownership?
Why would multiplying all three into the material alpha create the wrong plant?

The paired `ch48-grass-appearance` Starter deliberately conflates habitat with
opacity and restores the distance-lighting policy. The separate Solution tree
contains the complete reference implementation. Use the stage guide to prepare,
build, check and smoke each variant; `REFERENCE.md` owns their actual status.

<details>
<summary>Hint 1: make two independent controls</summary>

Disable impostors without changing source placement. A band that remains in
geometry is not exclusively an atlas bug. Inspect the generator's `fade`
separately from the fragment shader's ground-normal and root-occlusion fade.
MSAA can make a sample-masked silhouette look translucent even with blending
disabled, because uncovered samples still contain the sand behind it.

</details>

<details>
<summary>Hint 2: condition the existing random rank</summary>

Keep admission `cut < density * habitat`. For an admitted source with positive
habitat, `cut / habitat` is the rank used by distance thinning. Use that rank
for the transition, not the habitat-scaled margin. Full near density must give
full clump coverage, including ranks near one. Keep silhouette coverage separate.

</details>

<details>
<summary>Hint 3: interpolate appearance, not an invented surface orientation</summary>

Neither distance nor an LOD label physically turns a blade into horizontal
ground. For captured view interpolation, evaluate each view's material,
normal, transmission and highlight before averaging its covered radiance.
This still cannot recover the normal distribution already lost within a
spatial mip. Treat that residual and its cost as another measured problem.

</details>

<details>
<summary>Worked solution: preserve source admission and retain blade lighting</summary>

`grassPopulationCoverage` rejects the same source set as before. At full near
density it returns one. Otherwise, it divides the admitted rank by habitat and
computes a distance-transition margin, limiting the band by `1 - rank` so the
transition reaches full coverage at full density. `GrassGenerateKernel.glsl`
uses this one value for both mesh and captured camera/caster records. Do not
fix only the visible pass and leave ghost casters behind.

This changes resolved covered area, intentionally, without adding plants.
For a pure-sand, flat, canopy-free example at 1 m elevation, the old policy
admits about 7.93% of clumps but gives those clumps about 49.6% coverage on
average. The corrected near field keeps those same clumps solid. This is an
analytic example, not a measurement of a particular screenshot's bed height.

`--grass-surface blades` retains blade-oriented normals, root occlusion and
material highlights instead of the legacy distance-lighting fade. The proxy
evaluates the shared grass shader once per contributing captured view, then
averages colours with `viewWeight * coverage` and divides by total coverage.
The normal-variance specular filter is applied separately to each captured
view, before this interpolation; meshes use their pre-discard derivatives.
The per-view lighting can run inside coverage-dependent control flow. Sample
the already-convolved diffuse sky at its base level and the single-mip shadow
map with explicit gradients, rather than asking those calls for implicit
derivatives from an incomplete fragment quad.
Coverage is not radiance: after applying the shared sample mask, display its
final `area` through the common diagnostic path. Do not light or average that
diagnostic once per view. The native comparison rejects a former implementation
that accidentally displayed a coverage-weighted average of per-view alpha.
There is no second alpha blend or brightness compensation band. The old
`legacy` and rejected `filtered` experiments remain explicit comparisons.
Ambient, Diffuse, Transmission, Specular and Occlusion debug views isolate
the terms without changing the source or coverage rules.

The CPU checks separately cover unchanged source admission, solid near clumps,
bounded conditional distance fades and blade-lighting policy. The actual GPU
oracle reads 1x/4x coverage and a separate lighting-policy region; its healthy
source/capture/generation/capacity tests remain active in both variants.
The oracle does not establish exact BRDF integration or a performance win.
Spatial mip normals remain a mean-field approximation, and lighting four
captured views costs more than lighting their averaged attributes once.
Measure that additional draw cost and inspect moving foliage before acceptance.
In the checked Release 1080p/4x Stream fixture, two opposite-order repeats
cost about 2.12 ms more on RTX and 1.38 ms more on Radeon, with identical
plant/draw counters. These are fixture-specific GPU-render medians, not a
Debug/4K frame-rate guarantee or a speedup. See `REFERENCE.md` for provenance
and the remaining spatial-mip and far-field appearance limitations.

Run this healthy diagnostic control on either built variant, using fresh output
names. The supplied comparator checks identical executable/shader identities,
GPU, source, camera and time before comparing every pixel:

```powershell
$common = @{ Configuration='Release'; Suite='Benchmark'; Gpu=@('RTX');
    View=@('Coast'); GrassSource='patches'; GrassReach=180; GrassImpostors=1;
    GrassGeometryPixels=32; GrassProxyPixels=24; GrassDebugView='coverage';
    GrassShadows=0; BenchmarkSky='sun'; BenchmarkMsaa=4;
    BenchmarkWidth=1280; BenchmarkHeight=720; Frames=65; Warmup=30;
    RequireIdle=$true; MinimumAvailableMemoryMiB=4100; MemoryFloorMiB=3072 }
.\Tests\TutorialHarness\VerifyCapstone.ps1 @common -GrassSurface legacy -OutputName Coverage-Legacy
.\Tests\TutorialHarness\VerifyCapstone.ps1 @common -GrassSurface blades -OutputName Coverage-Blades
.\Tests\TutorialHarness\Compare-GrassCoverageView.ps1 `
    -FirstResults Build/CapstoneVerification/Coverage-Legacy/results.json `
    -SecondResults Build/CapstoneVerification/Coverage-Blades/results.json `
    -Output Build/Coverage-Comparison.json
```

</details>

## 3. Separate Population From Reach

<a id="ch48-population-reach"></a>

### Attempt CH48-population-reach: move a field boundary without planting more grass

The old density interpolation divides by `maxDistance - densityStart`.
Predict what happens to a root 30 m away when reach changes from 80 m to
1,600 m. Then fly vertically: should an aerial camera delete a meadow simply
because its height exceeds the field's ground radius?

**Acceptance:** With the same thinning interval and far density, changing
representation reach does not change population density at an interior root.
Any terminal fade is a separate factor. Camera height may change projected
representation, but not the ground population decision. Invalid inputs or
exhausted CPU work/storage budgets cannot publish a truncated tile list.

**Transfer:** Why should the current fine-grid scheduler reject 1,600 m rather
than increase its buffer capacity until that setting appears to work? Identify
which work still scales with ground area and how a coarse hierarchy would
change the scheduling unit without making a sixteen-blade capture wider.

This follow-up currently has the shared production helpers and CPU/GPU
acceptance checks, with the complete worked answer below. Its implementation
and verification checkpoint is recorded in `REFERENCE.md`. It is not yet an
additional packaged Starter/Solution pair or the completed landscape hierarchy.

<details>
<summary>Hint 1: look for a rendering setting inside the population rule</summary>

Give thinning its own endpoint. At a fixed interior position, the population
function should not need the distance at which the last representation ends.

</details>

<details>
<summary>Hint 2: two distances answer different questions</summary>

Ground distance selects the local population and its reach. View depth and
the lens determine projected size. Keep the latter for representation/error
tests rather than using the camera's altitude to remove valid roots.

</details>

<details>
<summary>Hint 3: a full buffer is not a complete field</summary>

Both hosts should call the same bounded selector. Count examined cells as well
as accepted records, reject excessive work before looping, and publish a count
only if the whole selection succeeds. A zero count with an explicit error is
different from silently retaining whichever side of a field was visited first.

</details>

<details>
<summary>Worked solution: independent thinning and atomic tile publication</summary>

`GrassSettings::densityEnd` is packed separately from `maxDistance`. The
shared helper in [GrassClumpSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpSource.h),
used by the actual generator and shadow diagnostic, is:

```cpp
float grassPopulationDensity(GrassParameters grass, float groundDistance)
{
    float end = grass.densityEnd > 0.0f ? grass.densityEnd : grass.maxDistance;
    float along = clamp((groundDistance - grass.densityStart) /
                        max(end - grass.densityStart, 0.01f), 0.0f, 1.0f);
    return mix(1.0f, clamp(grass.farDensity, 0.0f, 1.0f), along);
}
```

The zero endpoint is an explicit compatibility contract for older diagnostic
callers, not the new live setting: `PackParameters` supplies a positive endpoint
after the start. Existing defaults retain 50 m in Grass and 42 m in Horizon.
`grassPopulationReach` separately supplies the terminal smooth fade. Generation
uses `distance(xz, grass.cullPosition.xz)` for those two decisions, retaining
view-depth projection for captured-clump error/LOD. The actual GPU generation
test raises its camera to 500 m while retaining the same bounded ground roots.

`selectGrassTiles` is the common CPU owner in `GrassBounds.h`. It uses floor
for signed world cells, includes moved-root bounds, validates finite/range-safe
coordinates, and rejects a candidate rectangle larger than its bounded work
budget before visiting it. Visibility remains a caller policy: the standalone
host supplies its camera/caster test, and Horizon retains its current conservative
caster union. Storage overflow returns no publishable count. Both hosts prepare
their GPU list only after the selector returns Complete.

Run `TutorialGrassClumpTests`, `TutorialGrassBoundsTests` and the actual
`TutorialGrassImpostorGpuTests` on each GPU. These establish population,
scheduling and source contracts; they do not prove kilometre-scale rendering.
The current fine-grid limit, terminal fade and short default reach remain until
the macro capture, coarse hierarchy and canopy transfer have passed their own
functional and visual checks.

</details>

<a id="coast-grass-surface"></a>

# Part 2 — Surface attachment (sections 4–5)

## 4. Sample What Was Drawn

<a id="ch48-rendered-standalone-surface"></a>

### Attempt CH48-rendered-standalone-surface: sharing a height formula is not enough

The Grass vertex shader evaluates the hill at mesh vertices. Generation
evaluates that same formula at each root. Are those surfaces identical between
the vertices? Increase the hill amplitude and shorten its wavelength, then
inspect roots near a triangle diagonal and a negative world-cell boundary.

**Acceptance:** Roots and the diagnostic ball use the actual emitted triangle,
not the continuous hill. CPU tests construct planes from the emitted corner
topology and compare both height and normal. Actual GPU root readback agrees
within 0.2 mm. Ground coverage includes the captured source's root footprint,
deformation and screen widening, including an elevated/frozen camera. Culling
bounds include the observed root-height residual before rejecting a group.

**Transfer:** What new data must the sampler receive when a coarse terrain ring
replaces this uniform grid? Why would sampling the finest grid everywhere no
longer keep distant roots attached to the rendered ground?

This follow-up has a complete worked answer and production checks, but no
additional packaged pair yet. Its build/verification status is in `REFERENCE.md`.
It does not implement the planned bounded terrain rings or landscape grass.

<details>
<summary>Hint 1: look between the vertices</summary>

A curved height function and the planar triangle joining three samples agree
at their vertices, not generally inside. Sharing the original function only
proves that those vertex samples agree.

</details>

<details>
<summary>Hint 2: make the diagonal part of the contract</summary>

Find the cell with floor, then choose the same triangle as the emitted corner
order. Interpolate three heights. Share the corner topology too: a test with
its own unconnected copy of the old diagonal could keep passing after the
renderer's topology changes.

</details>

<details>
<summary>Hint 3: attached roots still need conservative bounds</summary>

A group centre's distance does not bound all of its roots or the camera's
altitude. Include source footprint in ground coverage, actual height residual
in the culling sphere, and projected minimum-width expansion before rejection.

</details>

<details>
<summary>Worked solution: vertices, triangle sampling and root readback share one source</summary>

[GrassTerrainSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassTerrainSource.h) owns
`grassTerrainCorner`, `grassTerrainVertexHeight` and `grassTerrainSurface`.
The first two feed the real terrain vertex shader. For cell-local coordinates
`along`, the lower triangle uses `(0,0), (0,1), (1,0)`; the upper triangle
uses `(1,0), (0,1), (1,1)`. Their plane interpolation is:

```glsl
if (along.x + along.y <= 1.0)
{
    surface.height = h00 + along.x * (h10 - h00) + along.y * (h01 - h00);
    surface.normal = normalize(vec3(h00 - h10, cellSize, h00 - h01));
}
else
{
    surface.height = h11 + (1.0 - along.x) * (h01 - h11) + (1.0 - along.y) * (h10 - h11);
    surface.normal = normalize(vec3(h01 - h11, cellSize, h10 - h11));
}
```

For a concrete mismatch, take `h00=h10=h01=0`, `h11=1 m` and a root at
`along=(0.25,0.25)`. It lies in the lower, completely flat triangle, so its
drawn ground height is zero. Bilinear interpolation of all four corners
instead gives `0.25*0.25=0.0625 m`: a root floating 6.25 cm above that
triangle, even though both samplers agree at every corner. Matching the
diagonal and triangle interpolation is the missing contract.

`GrassGenerateKernel.glsl` calls that sampler at the centre and every actual
root; `GrassDemo` calls it for the ball. Both use the shared 0.5 m cell size.
The CPU plane test constructs its vertices using `grassTerrainCorner`, the
same topology the vertex shader consumes. The GPU generation probe reads
real emitted root positions over nonflat terrain and checks their height.

`capturedClumpFootprint` bounds the rotated/scaled source-root offsets.
`GrassDemo::PixelWidthReach` includes that footprint and the culling camera's
vertical separation from the bounded hills; its ground mesh includes the
footprint too. GPU projection padding additionally uses actual centre distance.
Group culling follows root sampling and includes the measured height residual,
so a small flat-source sphere cannot hide taller roots on a steep surface.
This may cost additional height reads when shadows are disabled. Measure that
cost; the forthcoming cached/coarse hierarchy, not an invalid early bound,
must recover it. The current uniform ground grid is still not the planned
bounded landscape terrain representation.

</details>

## 5. Put The Same Roots On The Island

<a id="ch48-terrain-budget"></a>

### Attempt CH48-terrain-budget: decide when a flat clump is no longer valid

Place a sixteen-blade captured clump beside sloping ground and the wet beach.
Its centre is on grass, but some roots may lie on sand or below the dry-height
threshold. Decide how group admission and representation error should be
measured before drawing any proxy.

**Acceptance:** Every source root queries the actual rendered terrain and
habitat. No proxy sneaks rejected beach blades back into the field. Geometric
roots stay on their sampled triangles. A proxy with more than .75 projected
pixels of root-height error stays geometric. Verify positive and negative
tiles, the shoreline edge, low grazing views and terrain-ring boundaries.

**Transfer:** What would need rebaking or additional geometry if the design
allowed a separate steeply sloping source clump instead of rejecting it?

<details>
<summary>Hint 1: a centre sample cannot certify sixteen roots</summary>

Transform all sixteen template root offsets before testing habitat. A centre
on suitable soil does not prove that every corner is suitable too.

</details>

<details>
<summary>Hint 2: separate admission from approximation</summary>

Both representations need the same population decision. Actual geometry can
put each root at a different height; the captured source has one flat root
plane. Test that additional error separately from habitat.

</details>

<details>
<summary>Hint 3: measure the error where it is seen</summary>

Find the largest root-height difference from the proxy plane, then multiply
by pixels per metre at the clump. Force geometry when it exceeds the budget.
The capture fitting its own texture does not prove it fits this terrain.

</details>

<details>
<summary>Worked solution: common admission with a geometric fallback</summary>

The island branch of
[GrassGenerateKernel.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassGenerateKernel.glsl) asks
`renderedTerrainSurface` at every transformed source root. It also evaluates
ground-material weights, slope, height above sea and canopy there using the
existing island habitat rule. The group's minimum habitat density multiplies
the common distance-density decision, so representation changes do not alter
which beach plants exist.

Geometric blades store their actual sampled root and normal. The proxy's
single plane uses the centre height. `grassClumpTerrainFits(error, ppm)`
returns `error * ppm <= .75`; otherwise proxy weight is zero and geometry
continues. That means a steep region may gain little impostor acceleration.
This is an intentional quality cost to measure, not a reason to delete the
fallback for a more impressive benchmark.

Whole-group admission is conservative and can leave gaps at habitat edges.
It does not reproduce independently admitted individual blades exactly.
More template variants, terrain-aligned capture groups or selectively baked
edge groups are possible later extensions, each with storage and invalidation
costs. Do not describe the four flat templates as those completed features.

</details>

<a id="coast-grass-source"></a>

# Part 3 — Source and placement (sections 6–8)

## 6. Bound The Work Without Changing The Field

<a id="ch48-coarse-work"></a>

### Attempt CH48-coarse-work: give every fine cell one owner

Increase Horizon's test reach to 180 m. Predict the upload count for 4 m work
tiles and compare it with the 4,096-record budget. Design a larger work record
for the far field while preserving the same small physical clumps. The starter
omits coarse records, so only the local fine region survives. Restore complete
ownership without publishing parents alongside their children.

**Acceptance:** Cover every fine source cell once at negative and positive
world positions. Refinement must not change roots, seeds, shape, density,
material blending or physical clump scale. Bound CPU traversal, storage and
the padded GPU dispatch independently. Reject invalid spans/coordinates and
overflow before publishing a partial field. Compare complete generated GPU
records for one coarse patch versus its fine children, not just image colour.

**Transfer:** Does a smaller upload prove less GPU work? What representation
would let a coarse owner avoid enumerating each of its physical clumps?

<details>
<summary>Hint 1: distinguish a work record from a captured surface</summary>

A record can schedule a 4-by-4 array of fine tiles without stretching a blade
or changing capture dimensions. Its origin stays on the fine world grid.
World identity follows from that origin plus an integer local index.

</details>

<details>
<summary>Hint 2: refine ownership, not population</summary>

Visit aligned coarse parents. Near the camera, publish their fine children;
elsewhere, publish the parent alone. Include moved-root bounds in both tests.
The shader's existing root-distance/habitat tests remain authoritative at the
outer boundary, including partially intersecting coarse records.

</details>

<details>
<summary>Hint 3: padded dispatch is a separate budget</summary>

One rectangular dispatch must accommodate its largest record. Smaller records
return from unused invocations, but those slots still exist. Bound the product
of record count and maximum clumps per record, not only the logical candidates.
Keep scratch selection unpublished if traversal or capacity fails.

</details>

<details>
<summary>Worked solution: bounded scheduling with unchanged physical sources</summary>

[selectGrassPatches](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassBounds.h) is the
complete CPU solution shared by Grass and Horizon. It visits aligned parents
with a four-tile side. Parents intersecting the 32 m fine region publish only
their children; other accepted parents publish a single record. Signed floor,
moved-root bounds, checked integer ranges and independent traversal/storage
limits preserve world identity and fail with zero publishable records.

The 16-byte `GrassTile` uses a previously unused word for its work span.
Zero/one means a historical fine record. Generation multiplies the integer
invocation domain by this span, not the dimensions of a physical clump. The
same `grassClumpCell` maps every invocation back to the original fine source.
The owner validates alignment and bounds the padded dispatch at two million
clump slots before uploading. Its panel reports work records separately from
logical blade candidates; neither count is a GPU-time measurement.

Use `--grass-work-span 1` and `4` as equal-content controls at the original
reach. `--coast-grass-reach 180` exercises the larger Horizon domain with
coarse scheduling. The default reach is intentionally unchanged at this
checkpoint: the missing macro capture and canopy cannot be accepted by simply
raising a radius. Surface-normal blending now uses the independent thinning
endpoint rather than the representation reach, preserving near-field shading.

The CPU test expands coarse owners and checks that all fine cells are covered
once. The actual GPU test sorts and compares all 1,024 generated blade records
from a negative-coordinate coarse patch with its sixteen fine children,
including canaries. It does not substitute a second procedural mock for the
production shader. The independent starter must fail only the CPU ownership
assertion; its healthy GPU source checks and complete solution remain runnable.
This reduces upload/traversal records, not the number of represented clumps.
Macro sources, subpixel canopy and matched performance remain separate work.

</details>

## 7. Author A Source You Can Aggregate

<a id="ch48-canonical-source"></a>

### Attempt CH48-canonical-source: make a large capture out of the same small plants

A distant card cannot recover missing grass merely by changing its lighting.
The current Horizon source also thins to 15% by 42 m. Before replacing that
policy, make a source hierarchy that a larger capture can reproduce exactly.
Compose nine actual 16-blade clumps into one patch, and sixteen patches into
one parent. At Horizon's 24 blades per 4 m tile these widths are 2 m and 8 m.
Other blade densities change the physical widths, not the number of children.

How will a fine world cell find its source when the parent has a quarter-turn?
What happens at cell -1, at the world origin, and when coarse scheduling or
the camera changes? Work out those mappings before opening the implementation.

**Acceptance:** Every parent has exactly 144 fine clump children, each with
16 actual source blades. The inverse world lookup must equal independently
forward-composing those children, including negative coordinates and all four
rotations. Geometry and fine proxies retain the same position, scale, yaw,
source variation and dryness. Camera altitude, representation reach and fine/
coarse scheduling cannot change source identity. Existing terrain, coverage,
caster and buffer-canary checks stay active. Keep legacy as a control.

**Transfer:** Why is hashing every world-space child independently convenient
for near grass but insufficient for a finite atlas of exact parent captures?
Which variation belongs in the captured source, and which can remain an
invertible runtime transform?

<details>
<summary>Hint 1: separate authoring from representation</summary>

Define local child poses in a finite set of templates. Derive a parent kind
and orientation from its signed world-cell identity. The camera chooses a
representation of that source; it must not choose which plants exist.

</details>

<details>
<summary>Hint 2: invert both rotations before selecting a child</summary>

Locate the world cell inside its 12-by-12 parent, undo the parent's turn,
then locate the 3-by-3 patch and undo its turn. Only then select its fine
clump. A positive quarter-turn maps `(x,z)` to `(z,side-1-x)`, matching the
engine's positive yaw. Ordinary C++/GLSL integer division truncates toward
zero; parent lookup needs floor division instead.

</details>

<details>
<summary>Hint 3: check the inverse using a different route</summary>

Enumerate all authored patch/child pairs forward into world space. Find the
fine world cell that contains each resulting centre, then ask the production
inverse for its pose. This catches a wrong inverse instead of repeating it
in the expected answer. Protect signed division with widened reconstruction,
including `INT_MIN`, rather than computing a potentially overflowing
`parent * 12` in the runtime remainder.

</details>

<details>
<summary>Worked solution: a deterministic nested source with independent identity checks</summary>

The complete shared implementation is
[GrassLandscapeSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassLandscapeSource.h).
`grassPatchChildPose` composes the actual fine source variants with local
jitter, yaw and height variation. `grassParentPatchPose` selects patch kind
and quarter-turn. `grassLandscapeLeafPose` performs the inverse lookup,
then composes both transforms back into a world pose. Its signed primitives
are:

```cpp
int grassSourceFloorDiv(int value, int divisor)
{
    if (value >= 0) { return value / divisor; }
    return -1 - (-(value + 1)) / divisor;
}

int grassSourceRemainder(int value, int divisor)
{
    if (value >= 0) { return value % divisor; }
    return divisor - 1 - (-(value + 1)) % divisor;
}
```

Divisors here are the fixed positive 3, 4 and 12. The remainder deliberately
does not multiply the floor quotient by the divisor, which can overflow at
the extreme negative integer. With parent width 12, world cell `-1` belongs
to parent `-1`, local cell `11`; cell `-12` belongs to parent `-1`, local
cell `0`; cell `-13` belongs to parent `-2`, local cell `11`. Each reconstructs
as `parent*12+local` with `local` in `[0,11]`. Truncation would assign `-1`
to parent zero and produce an invalid negative local index. Work these small
cases before combining the parent and patch rotations.

The whole source, drawn: one parent and its patches, one patch before and
after a quarter-turn (an example; each parent and patch draws its own kind and
turn from its world cell), and the cells around the origin with the parent
and local cell floor division gives each:

![Above left, one parent: 12 by 12 fine clump cells in 16 patches of 3 by 3, one patch shaded. Above right, that patch's nine clumps as authored and after one positive quarter-turn, which moves the clump at (x, z) to (z, 2 - x). Below, world cells -13 to 0 along one axis with the parent and local cell that floor division gives each: cell -13 is parent -2, local 11; cells -12 to -1 are parent -1, local 0 to 11; cell 0 is parent 0, local 0.](images/nested-grass-source.svg)

Do not copy the common C++ negative-remainder
correction into GLSL: [the GLSL operator rules](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.60.html#operators)
do not guarantee its result for negative operands. The first source experiment
passed CPU tests but failed the actual RTX source oracle; its bytecode used
`OpSMod`, so the negative-remainder sign test did not correct truncation.
The replacement above uses nonnegative division/modulo operands and never
negates `INT_MIN`. Integer quarter-turns choose indices; float
rotations transform physical poses only after source selection.

The production [generator](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassGenerateKernel.glsl)
selects this authoring mode with `--grass-source patches`; `legacy` remains
the default. Both modes retain the same population policy, blade dimensions,
lighting and representation thresholds. The patch mode shares parent dryness,
sway phase and an 8 m Horizon wind anchor, an explicit first affine authoring
choice rather than a claim of independently animated blades. Fine geometry
and fine captures use identical leaf poses. The existing capture need not
rebake: its rest source is still the same 16 blades, transformed by each pose.

Run `TutorialGrassClumpTests` for signed boundaries, integer rotations and
forward/inverse composition. `TutorialGrassImpostorGpuTests` dispatches the
actual generator and compares it with a separately floor-partitioned,
forward-enumerated CPU source. It also checks camera/reach independence,
proxy material/scale identity and bit-identical fine/coarse work records.
The native Grass/Horizon harness accepts `-GrassSource patches` and verifies
the successfully uploaded mode in its log; inspect the corresponding images
too, since an upload witness is not a shader-pixel oracle.

The registered `ch48-canonical-source` pair pins this source independently.
Prepare its `Starter` and `Solution` with the stage runner, then build each
in Release with one worker. The Starter deliberately truncates signed parent
division: CPU partition/composition checks and the actual GPU source/proxy
checks must reject it, while healthy coverage, capture, caster and canary
checks continue to pass. Run its Check phase with `-ExpectIncomplete`; the
Solution receives no expected-failure allowance. Smoke uses the actual Grass
demo in patch-source mode. See the
[stage commands](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md) for the separate
Prepare/Build/Check/Smoke steps and resource guards. Registration/preparation
is not proof that independent build/check/smoke phases have passed; their
measured status belongs in `REFERENCE.md`.

Both smoke images can look plausibly grassy while the Starter assigns the
wrong plants around negative world boundaries. Visual smoke proves it runs;
the independently composed source checks determine whether it is the right
field. Do not use a convincing screenshot to waive those failures.

The immutable floor-division pair retains its verified `4339c2e` source.
A later local authoring cleanup gives parent kind/quarter-turn metadata its
own `GrassPatchPose`, rather than packing a turn into a leaf phase slot.
It changes neither the leaf-pose contract nor the GPU buffer ABI. The signed
lookup problem and its complete floor/remainder repair are unchanged.

This first slice is source authoring, not a finished far renderer. No
144-blade aggregate capture or coarse canopy is drawn yet, and the 15%
population policy is not changed. Mixed habitat, terrain residual, independent
camera/caster ownership, exact nested overlap masks, capacity and matched
content timing must be solved before promoting larger captures or full density.
Do not confuse a runnable mode with a verified learning-stage export or an
accepted distant appearance.

</details>

## 8. Carry A Clump Across A Slope

<a id="ch48-terrain-frame"></a>

### Attempt CH48-terrain-frame: follow the hill without moving the roots

Place the same clump on a tilted plane, first as individual blades and then
as a captured surface. Turn on wind, move the camera slightly below the clump,
and inspect normals as well as silhouettes. The starter deliberately leaves
the terrain-following position transform unfinished. Predict why testing
only a flat field cannot expose that omission before running its checks.

**Acceptance:** Geometric vertices and the reconstructed capture use the same
root-pinned transform on planar slopes. Its inverse recovers source-space
rays; its inverse transpose gives the same normals. Actual triangle roots
stay attached. Test positive/negative slopes, yaw, scale and wind together.
Measure nonplanar residual against a pixel budget and keep geometric fallback
at ridges. Reject camera directions outside the baked elevations, not every
uphill clump. Sun-view eligibility needs its own subsequent caster contract.

**Transfer:** A taller plant has stiffer stems and flexible leaves. Which part
of this affine model would you replace, and which ownership/error tests remain?

<details>
<summary>Hint 1: write the plane equation</summary>

Represent height relative to the clump anchor as two horizontal derivatives.
Changing only height can keep horizontal roots fixed. Compare actual root
heights with that plane, rather than with the anchor's constant height.

</details>

<details>
<summary>Hint 2: order matters</summary>

Wind leans a blade relative to its root. Apply the terrain frame afterwards.
Invert those operations in reverse order when reconstructing the local eye.
Moving normals with the position matrix does not preserve perpendicularity.

</details>

<details>
<summary>Hint 3: a plane is not a ridge</summary>

An exact plane has zero residual even when its height changes substantially
across the clump. A ridge can have a small centre slope but large residual.
Also ask whether the resulting local camera direction has an actual capture;
the atlas starts at -15 degrees, not at the bottom pole.

</details>

<details>
<summary>Worked solution: one invertible terrain frame, plus measured residual</summary>

[GrassClumpSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpSource.h) provides the complete
shared CPU/GLSL solution. For gradient `g`, its height-field shear is
`S(p) = (p.x, p.y + dot(g, p.xz), p.z)`. Its inverse uses `-g`. Normals use
`S^-T(n) = (n.x - g.x*n.y, n.y, n.z - g.y*n.y)`, then normalization. The
gradient's magnitude is bounded by two, so CPU/GPU deformation bounds include
a factor of three. This is an explicit grass surface model, not selective
tree-branch animation or a free rotation of the whole plant.

Generation queries the rendered triangle at every root and measures
`abs(actualHeight - anchorHeight - dot(g, rootOffset.xz))`. The existing
0.75-pixel budget now tests that residual. Geometric roots keep their exact
heights; the capture has the same plane, source yaw/scale and root-pinned wind.
The geometric record stores the shared gradient. Visible and shadow vertices,
capture depth, rounded normals and inverse camera rays use the same order.
No illumination or terrain is baked into the reusable atlas.

The capture remains invalid outside its real elevation range, at an interactor,
or where root residual is visible. A camera below a distant uphill anchor can
still have a valid local capture; the previous blanket rejection lost this
case. None of this establishes a macro source, canopy material or performance
win. Those need separate representation and timing checks.

`TutorialGrassClumpTests` compares production transformed vertices, normals
and inverse rays across slopes, wind, yaw and scale, then rejects a ridge.
The actual GPU generation check also retains its rendered-root and capacity
canaries. The paired exercise is registered only after its runtime source is
pinned; its deliberate omission must fail only the terrain-frame assertion.

</details>

<a id="coast-grass-frame"></a>

# Part 4 — Frame, lighting and cost (sections 9–11)

## 9. Borrow A Frame, Not A Second Renderer

<a id="ch48-shared-frame"></a>

### Attempt CH48-shared-frame: integrate before the water takes its snapshot

Reuse the Grass implementation inside Horizon. Identify who owns the camera,
light buffers, shadow maps, scene targets and ocean simulation. Insert grass
generation, shadows and opaque drawing without an extra clear or a second
scene renderer. Then consider a grass caster outside the camera frustum.

**Acceptance:** Both demos use the same `GrassField` and material kernels.
Horizon supplies its frame, terrain and lighting; opaque grass colour/depth
is complete before water's opaque-input snapshot. Camera-only culling cannot
erase a needed offscreen caster. Grass-off leaves the ocean functioning;
sea-off leaves the same grass field functioning. Resize, 1x/4x recreation,
demo switching and teardown produce no Vulkan or synchronization errors.

**Transfer:** If a later deferred pipeline owns opaque lighting, which
representation decisions stay the same and which render-target interfaces
must change?

<details>
<summary>Hint 1: representation is not a lighting architecture</summary>

An impostor says how a surface is represented. Forward or deferred says
where its material is lit. Neither implies that the other has been changed.

</details>

<details>
<summary>Hint 2: write down the read/write order</summary>

Compute writes blade/clump records and indirect commands. Shadow/camera draws
read them. Water later reads opaque colour/depth snapshots. Explicit barriers
and rendering scopes must preserve that dependency order.

</details>

<details>
<summary>Hint 3: visible and shadow candidate sets differ</summary>

An offscreen blade can cast onto a visible receiver. Previous camera Hi-Z
proves camera occlusion, not that the blade is irrelevant to the sun. Keep a
bounded union or maintain separate lists; do not reuse a camera-pruned list
as if it certified every shadow view.

</details>

<details>
<summary>Worked solution: one owner and explicit borrowed contracts</summary>

[GrassField](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassField.cpp) owns the atlas,
bounded blade/clump buffers, descriptors, pipelines and indirect commands.
`GrassDemo` owns its standalone scene. `CoastalArea` borrows Horizon's
`SceneRenderer`, frame and terrain set and calls the same owner's island
preparation/generation path before shared shadow recording.
In the current reference, these GPU owners delete copying and supply no move
operation; composition borrows their stable objects rather than transferring
their Vulkan handles. This is the written continuation's ownership policy;
leave sealed checkpoints' pinned protected headers unchanged.

Opaque grass draws within Horizon's opaque scene scope. Only afterwards does
the existing coastal path record opaque water inputs and draw water in its
loaded scope. Grass is still forward, depth-writing foliage; this feature
does not migrate Horizon to deferred shading. The BRDF remains live and shared
between grass geometry/proxies regardless of that representation choice.

When grass shadows are enabled, the standalone candidate list includes the
bounded camera/caster union and does not apply camera-only frustum/Hi-Z
rejection to it. The island path already supplies a bounded union. Geometry
and sun-view captures replace the old raised shadow sheet. This keeps the
visibility contract clear but can cost more generation and shadow work;
measure it before claiming the impostor stage is an optimization everywhere.

</details>

## 10. Give The Camera And Sun Separate Decisions

<a id="ch48-caster-ownership"></a>

### Attempt CH48-caster-ownership: keep a caster the camera cannot see

Keep a receiver in view and move its grass caster outside the camera frustum.
Then use a low sun on sloping ground: the camera has a valid captured view,
but the light does not. Predict which geometry/capture records each pass needs
before inspecting the actual GPU test's four per-view counters.

The runnable pair starts at `grazing` with sun elevation 5 degrees and azimuth
180 degrees, behind the camera. Before changing code, find a shadow entering
the image from grass outside it. What should happen to that shadow as its
source crosses the camera edge? Keep the lens and time fixed when comparing
your prediction with the complete solution.

**Acceptance:** Keep offscreen-needed casters; discard groups outside both
camera and light volumes. Select camera and shadow weights independently,
using the actual current light direction, cascade projections and map size.
An unsupported sun capture retains the camera proxy but uses geometric
shadows. Light-depth intersections retain geometry rather than clipping a
reconstructed surface at the card's depth. Bounds, capacities and complementary
ownership still hold. Prove these with actual generated records and canaries,
not only an image with the sun above the camera.

**Transfer:** A point light has several shadow views. Which decisions can share
a source record, and which must remain specific to each required view?

<details>
<summary>Hint 1: camera occlusion proves only one thing</summary>

Previous camera depth cannot certify that a clump is irrelevant to a sun
receiver. Form a bounded union of required domains before discarding the
source. Check the light in the same inverse terrain/wind frame as the camera.

</details>

<details>
<summary>Hint 2: one proxy weight is not enough</summary>

A valid camera proxy may need geometric shadows. Keep a weight for each pass,
emit geometry if either needs it, and suppress that geometry in the other
pass when its proxy owns the pixels. Measure approximation error in the
intersecting shadow maps' projection, not in camera pixels.

</details>

<details>
<summary>Hint 3: command recording is not GPU execution</summary>

Draw preparation can grow buffers and update descriptors. Finish those updates
before binding the shared set. The current frame's shadow uniform contents
must be flushed before submission, and its frame slot must no longer be in
flight. Moving a descriptor update after a bind is not the same as writing
the contents of an already-described buffer.

</details>

<details>
<summary>Worked solution: a bounded union with per-pass ownership</summary>

The production [generator](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassGenerateKernel.glsl) tests
camera visibility and each actual light clip volume independently. It uses
`ShadowData`'s matrices, direction and exact map resolution. Binding 3 is
visible to compute; `GrassField` binds the renderer's real frame set rather
than copying a previous frame's fit. The shadow owner writes and flushes data
before queue submission, even though its draw commands are recorded later.
This follows [Vulkan's host-write submission ordering](https://docs.vulkan.org/spec/latest/chapters/synchronization.html#synchronization-submission-host-writes).

Each clump retains camera and shadow weights. Geometry is emitted if either
needs it. Visible and shadow vertex kernels consume their own weight and
visibility bit; a fully owned or unused representation is clipped before
fragment work. Exhausting clump storage restores geometric fallback for both
required passes. Source phase still determines wind before record publication;
its previously unused stored copy now carries the shadow weight instead.

The light tests the terrain residual against the finest intersecting cascade's
projection scale. Unsupported elevations and light-depth boundary intersections
fall back to geometry. Camera and light also respect source-atlas texel limits;
a tiny blade in a wide clump does not justify magnifying a 128-texel capture.
Margins transition before the view/root-error limits. The 592-byte parameters,
80/96-byte blade records and 64-byte clump records stay fixed. The counter
record grows to 32 bytes so shared storage and each view's records can be
reported without calling shadow-only geometry camera work.

Standalone prop draw preparation precedes generation's frame-set binding.
Otherwise a capacity-driven descriptor update could invalidate the recorded
compute work. See the distinct [descriptor-update rule](https://docs.vulkan.org/refpages/latest/refpages/source/vkUpdateDescriptorSets.html).
This is an ordering/ownership change, not a request for update-after-bind
features or a second renderer. Existing geometric curve LOD remains a separate
quality choice; these root-error tests do not establish a universal silhouette
error bound for the low-segment curve.

`GrassGenerationProbe` drives the actual shader with camera-only, offscreen
caster, outside-both, light-depth-edge and unsupported-low-sun fixtures. It
checks the per-view weights, counters, geometry fallback and canaries. The
complete source and its independent exercise are pinned only after build and
native verification; pending results remain in `REFERENCE.md`.

For matched native geometry/proxy runs, use the source-count control too:

```powershell
./Tests/TutorialHarness/Compare-GrassOwnership.ps1 `
    -GeometryResults Build/CapstoneVerification/Geometry/results.json `
    -ProxyResults Build/CapstoneVerification/Proxy/results.json `
    -Output Build/ownership.json
```

Keep each report beside its original completed `run.json`; executable and
shader bytecode hashes must match. Use fresh output and the same case names
in both reports. For each view, let
`G` be geometry-only blades, `R` retained proxy-mode blades and `C` proxy
groups. The overlapping source groups are `(R + 16*C - G)/16`, which must be
an integer between zero and `min(R/16, C)`. A transition can legitimately keep
both records; summing them without accounting for overlap overstates the
population. The helper also rejects different settings, devices or binaries.
Passing this test does not establish matching pixels or faster rendering.

</details>

<a id="ch48-capture-facing"></a>

### Attempt CH48-capture-facing: reconcile the side before blending views

The runnable `ch48-capture-facing` Starter and Solution pin the same source.
Prepare them with the [learning-stage runner](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md).
Starter deliberately omits only the rounded-normal orientation correction;
the scene and the healthy capture/generation checks remain runnable. Make
your prediction before comparing with Solution. Current independent build,
check and smoke status is recorded in `REFERENCE.md`.

Two neighboring captures see opposite sides of a nearly edge-on blade. Both
encode a normal pointing toward their own bake camera. Predict the normal
their interpolation gives when the runtime eye crosses between them. Then
draw a rounded blade cross-section: should changing sides reverse its edge
rounding too? Try the correction before opening the worked answer.

**Acceptance:** Orient each captured face toward the current source-space ray
before combining views. Preserve the rounded edge offset and the length of
coverage-weighted normal vectors. Check both sides, rounding signs, all source
variants and fractional coverage against independently reconstructed physical
normals. Exercise the compiled helper at 1x/4x, then compare actual runtime
normal/albedo/coverage/shaded views at fixed camera and time. Keep density,
geometry, atlas source, colours and ownership unchanged. A helper-only pass
does not establish that the runtime interpolation is wired correctly.

**Transfer:** What information is lost when several different blade normals
have already been averaged into one mip texel? Why does correcting its face
orientation not make all nonlinear lighting terms exact?

<details>
<summary>Hint 1: a bake camera is not the current eye</summary>

Inspect each view's face normal before its interpolation weight is applied.
Use the runtime ray in the same inverse wind/terrain frame as the captured
normal, rather than the atlas view direction used to make that capture.

</details>

<details>
<summary>Hint 2: separate the face from its rounding</summary>

The rounded source normal comes from a face normal plus an offset along the
blade's width. Those components are perpendicular. Negating their sum reverses
both; changing the visible physical side should reverse only the first.

</details>

<details>
<summary>Hint 3: reflect one component</summary>

For a unit face vector `F`, reflection across its tangent plane subtracts
`2 * dot(R, F) * F` from a rounded vector `R`. Account for a sampled face
vector that carries fractional coverage and is no longer unit length.

</details>

<details>
<summary>Worked solution: orient the face and preserve the edge</summary>

Write the unfiltered rounded normal as `R = normalize(F + E)`, where unit
`F` is the baked face and `E` is its perpendicular edge-rounding offset.
If `dot(F, ray)` is negative, the current eye sees the opposite side. Its
physical normal is `normalize(-F + E)`, not `-R`. Since `F` and `E` are
perpendicular, reflecting only `R`'s face component gives that result without
recovering the original offset magnitude:

```cpp
vec3 grassClumpOrientNormal(vec3 rounded, vec3 face, vec3 ray)
{
    float square = dot(face, face);
    if (square <= 1e-12f || dot(face, ray) >= 0.0f) { return rounded; }
    return rounded - face * (2.0f * dot(rounded, face) / square);
}
```

The cross-section you were asked to draw, from both sides:

![A blade's cross-section, twice. Left, the eye on the captured side: the face normal F, the edge offset E along the blade's width, and the rounded normal R = normalize(F + E) leaning toward the edge. Right, the eye on the other side: the physical normal is normalize(-F + E), which is R reflected across the blade's plane, with the same lean toward the edge; -R would also reverse the rounding.](images/rounded-blade-face-and-edge.svg)

The runtime applies this to each sampled rounded normal, flips its sampled
face when necessary, then accumulates both with that capture's view weight.
The division handles nonunit coverage-weighted face vectors; the reflection
preserves normal-vector length. Normalization and deformation follow the
existing shared runtime path. Atlas contents and population do not change.

The CPU oracle reconstructs `normalize(actualFace + edgeOffset)` directly.
The GPU oracle does the same independently of the reflection helper and
checks actual resolved RGB values at 1x/4x. The image comparison still matters:
filtering has already mixed potentially different source surfaces, so a mean
face/normal pair is an approximation, not a complete normal distribution.
This correction cannot certify unchanged silhouette, perfect translucency or
the absence of a separate density/outer-reach band. Build, paired-stage and
native acceptance status belong in `REFERENCE.md`; the candidate is not
declared verified merely because the derivation is available here.

</details>

<a id="ch48-filtered-blade-lighting"></a>

### Attempt CH48-filtered-blade-lighting: filter the lobe, not the blade identity

Chapter 27 blends distant blade normals toward the ground, removes root
darkening and fades highlights. Predict what happens when those distance
thresholds stay fixed but the viewport resolution doubles. Does a resolved
blade cease to have a blade normal just because it passed 42 metres?
Compare `--grass-surface legacy` with `--grass-surface filtered` before
choosing a policy. Keep source, density, light, camera and time fixed.

**Acceptance:** The filtered path retains the blade normal and root material
terms in both mesh and proxy shading. A resolved unit normal with zero
footprint variance preserves the authored specular lobe; increasing lost
normal variance broadens it monotonically without infinities or an alpha
outside [0,1]. Evaluate geometry derivatives before ownership/coverage
discards. A proxy uses its premultiplied mean-normal length, not derivatives
after its divergent capture discards. Check actual 1x/4x lobe pixels, capture
invalidation, mode upload, normal/albedo/coverage/shaded images, low sun,
motion and recreation. Do not advertise mathematical helper tests as proof
of a convincing distant field.

**Transfer:** Why is evaluating a BRDF once at the normalized mean normal
not equivalent to averaging the BRDF over all source normals? Which
diffuse/transmission information is still missing after this specular repair?

<details>
<summary>Hint 1: separate an approximation from the material</summary>

The existing distance policy changes normals, root occlusion and highlights
together. First make that an explicit comparison mode. The replacement must
not change albedo, source membership or coverage to conceal a lighting error.

</details>

<details>
<summary>Hint 2: keep the length before normalizing</summary>

Unit normals averaged across differently oriented surfaces produce a vector
shorter than one. Divide the premultiplied vector length by its coverage
before normalizing it for lighting. Its lost length is useful approximate
angular-variance information, not a new diffuse brightness multiplier.

</details>

<details>
<summary>Hint 3: combine variance with the squared lobe width</summary>

For authored perceptual roughness `r`, GGX alpha is `r*r`. One bounded
approximation uses `variance = (1-L)/max(L,.001)` for mean-normal length `L`,
then adds a nonnegative footprint variance to alpha squared. A unit-width box
footprint has variance 1/12 along each derivative axis.

</details>

<details>
<summary>Worked solution: retain blade shading and broaden filtered highlights</summary>

The explicit filtered mode leaves `normal` unchanged by the legacy ground
fade and keeps `mix(rootOcclusion,1,bladeT)` at every distance. It does not
fade the specular response to zero by radius. Instead:

```cpp
float grassFilteredAlpha(float roughness, float normalLength, float gradientVariance)
{
    float alpha = roughness * roughness;
    float meanLength = clamp(normalLength, 0.0f, 1.0f);
    float variance = (1.0f - meanLength) / max(meanLength, 1e-3f) + max(gradientVariance, 0.0f);
    return sqrt(clamp(alpha * alpha + variance, 0.0f, 1.0f));
}
```

Geometric shading supplies unit normal length and
`(dot(dFdx(N),dFdx(N)) + dot(dFdy(N),dFdy(N))) / 12`, calculated before its
discards. The captured path supplies `length(accumulatedNormal)/coverage`;
its mip and view filtering have already averaged normals. It does not ask
for quad derivatives after empty/invalid view samples were discarded. The
same resulting alpha drives the existing GGX or normalized Blinn-Phong lobe.

This is a bounded specular-filtering approximation, not a complete normal
distribution, exact transformed covariance or energy-exact foliage BRDF.
The underlying information is discussed in [Toksvig's normal-map filtering paper](https://developer.download.nvidia.com/assets/gamedev/docs/Mipmapping_Normal_Maps.pdf)
and [Tokuyoshi and Kaplanyan's geometric specular-antialiasing paper](https://yusuketokuyoshi.com/papers/2019/ImprovedGeometricSpecularAA.pdf).
The compact formula above is not an implementation of either paper's full method.
Nonlinear diffuse/transmission averaging and macro-scale canopy appearance
remain separate work. This `filtered` experiment was not selected as the
accepted default: its bounded specular helper did not establish good whole-
field mesh/proxy matching. Keep it and `legacy` as explicit comparison modes.
The later `blades` policy combines per-view radiance interpolation with
per-view specular filtering and is the current default; see
[the appearance problem](#ch48-grass-appearance) for its remaining limits and
measured cost. The compact panel combo and CLI select the same uploaded
parameter. The native harness records that witness and actual images;
neither replaces the other.
See `REFERENCE.md` for build, paired-stage and visual acceptance status.

</details>

## 11. Measure The Whole Trade

Use `--grass-debug-view albedo` to keep the production coverage but inspect
unlit root/tip colour and blade variation. Compare it with `normals`,
`coverage`, the shaded view and `--grass-shadows 0` at the same lens, time,
population and representation settings. A nonblank albedo view does not
prove material continuity: retain the matched geometric/proxy images. A band
that remains unlit cannot be explained only by direct-light smoothing.

<a id="ch48-measured-budget"></a>

### Attempt CH48-measured-budget: prove or reject the optimization

Compare geometry-only and clump-impostor modes on the same field. Predict
which passes get cheaper and which can get more expensive. Design a test that
would reject the change if it saves triangles but increases GPU frame time
or loses visible grass.

**Acceptance:** Match source, device, lens, extent, MSAA, population, route,
sun, wind and shadows. Separate warmup and capture stalls from timing. Retain
CPU/GPU distributions, per-pass times, counts, buffer/atlas bytes and source/
executable/shader identities. Inspect both modes and their motion sequences.
Exercise clump and blade capacity exhaustion independently without out-of-bounds
writes or an unclamped indirect count. Report slower workloads honestly.

**Transfer:** Why might a grass impostor be slower at 4K near the camera yet
useful for a sparse, very distant field on the same GPU?

<details>
<summary>Hint 1: count work the card adds</summary>

The card covers empty space too. Four views and parallax add texture lookups,
fragment depth can limit early rejection, and shadow captures add another
cost. Reduced vertex count is only one part of the trade.

</details>

<details>
<summary>Hint 2: preserve a fair control</summary>

Use `--grass-impostors 0` on the same source. Do not compare against an older
field with a different seed, density fade, wind or caster population and call
all differences an impostor speedup.

</details>

<details>
<summary>Hint 3: distinguish functional and timing evidence</summary>

Validation and frame capture are valuable functional diagnostics but perturb
timing. For a performance claim, verify actual loader chains, run unlayered
Release windows, exclude capture stalls and keep resource/idle/power evidence.
Do not terminate a user's apps or weaken memory guards to finish a matrix.

</details>

<details>
<summary>Worked solution: matched native runs and bounded readback contracts</summary>

The shared [native harness](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/VerifyCapstone.ps1)
has a Grass suite for ground/grazing/aerial/transition views, two moving
routes, target recreation and scaled UI. Its Benchmark suite accepts
`-BenchmarkDemo Grass`, a `-View`, and `-GrassImpostors 0` or `1`; Horizon uses
the same switch with coastal views. Select fresh evidence directories and
run devices/modes serially. `-GrassFlat 1` is an explicit flat-ground fixture,
not a substitute for the normal hills or island slope checks.

The panel reports clump capacity, draw time and atlas rebuild count. Grass
benchmark metrics include generation, both geometric LOD draws, the clump
draw, triangles and persistent storage. The historical four-elevation
three-attachment atlas consumes 67,107,840 bytes (about 64 MiB), including
distinct geometric/shading normals. The seven-elevation experiment in
[Chapter 46](46-Capturing-Grass-Clumps.md#ch46-horizon-capture-grid) increases
that payload to 117,438,720 bytes (about 112 MiB), with no extra source blades;
100,000 64-byte clump records cost another 6,400,000. The original 64-byte blade
representation added 12,800,000 bytes to the old 800,000-blade allocation.
The terrain-frame follow-up uses 80-byte standalone blades (64,000,000 bytes
for that allocation) and 96-byte island blades including their ground normal.
Both comparison modes retain these allocations and a ready capture for live
toggling. This is a draw-work comparison, not evidence of memory savings.
The reported payload bytes are not total driver-resident VRAM or process RAM.

The small GPU probe dispatches the actual production generator with tiny
capacities. A full clump buffer forces the remaining groups back to geometry;
the indirect clump draw is clamped. A full blade region also clamps its draw
without writing past its logical boundary. Canaries protect records, counters
and commands. These checks prove bounded behaviour, not acceptable production
density: normal scenes must still stay within their reported capacities.

The first final-material RTX aerial/1080p/4x count comparison at the
conservative 32/12-pixel thresholds reports 214,880 geometric blades in BOTH
modes; enabling impostors adds 6,316 clumps. Most eligible groups remain in
overlap rather than completing the handover. That rejects the prediction
that this profile removes geometric instances in this view. Complementary
masks can still reduce geometric fragment shading, so the counts alone prove
neither a speedup nor a slowdown.

Those counts belong to the earlier material checkpoint, not the accepted
profile. Subsequent 32/24-pixel controls, motion and shadowed 4K captures
were inspected on both devices; Gary accepted that explicit visual profile
with canonical source and 180 m reach. Global selection defaults stay 32/12.
Do not infer a geometry-versus-impostor speedup from this acceptance.

The later timing experiment instead isolates `legacy` versus `blades`
lighting on the same proxy-enabled field: Release Stream, 1080p/4x, 180 m,
32/24 pixels, grass casters off, actual empty loader chains, no screenshot
sequences, two opposite-order windows per policy/device. Frame IDs and all
recorded population/draw/upload/storage counters match. GPU-render medians
increase from 10.812 to 12.932 ms on RTX and 32.332 to 33.709 ms on Radeon.
Retain the complete distribution/provenance in `F2BandRepair-Timing-1`, not
just these rounded aggregates. This is an accepted lighting-cost trade-off,
not certified Debug/4K FPS, certified thermals or a claim that impostors are
faster. Keep the failed appearance experiments too: a mathematically bounded
helper and clean logs did not predict which complete field looked better.

</details>

This is the current accepted grass checkpoint, with the limitations and
evidence described above. Return to the [series routes](../VulkanTutorial.md#routes)
to choose another branch. The rest of the world wind (42), surf (44), full procedural-world scene
authoring and the remaining measured improvements are further work; reaching
this chapter does not establish them.
