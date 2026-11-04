# 46. Capturing Grass Clumps

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

You already have a field of curved blades. The next task is to replace many
of those blades with a smaller representation without turning the grass into
a photograph that only works under the sun used to make it.

Start in the Grass demo. Horizon will consume the same owner later. This is
an extension after Chapters 27 and 41, not a replacement for their historical
steps. Chapters 42 and 44 retain their separate planned scope; Chapter 45
adds CPU scene documents and properties without changing this grass contract.

**Prerequisites:** Chapter 25, sections 4 and 6–8 (blade strips, curves,
normals and shadow draws); Chapter 27, sections 4, 5 and 7 (coverage, rounded
normals and lighting); Chapter 40, section 1 (relightable multi-view surface
data); and Chapter 41, sections 1–2 (the shared grass owner and its terrain
contract). Reuse Chapter 15, section 5's mip filtering and Chapter 18,
section 8's distinction between alpha and sample coverage.

**Start here:** read the capture problem below, then prepare
`ch46-grass-capture` through the
[stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md). Its Starter
already renders; repair the declared normal-capture omission before moving
to view placement and mip filtering. Those latter problems use the worked
answers and linked source rather than additional packaged starters.

**Accepted reference, historical exercises:** Gary accepted the current
Horizon appearance/performance balance on 2026-10-19. Actual capture/generation,
1x/4x coverage, shadow, motion/recreation and 4K checks pass on RTX/Radeon;
matched lighting-cost windows are recorded, not advertised as a speedup.
The packaged capture variants remain pinned to their historical source: both
build, Starter fails only its declared assertion, and Solution and paired
native smokes pass on both GPUs. Acceptance does not finish larger patch
captures, within-mip normal distributions, far canopy or shrubs. Consult the
[accepted checkpoint](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md#accepted-horizon-grass-checkpoint-2026-10-19)
for the exact profile, source pins, evidence and continuation boundary.
The paired `ch46-grass-capture` stage omits rounded shading-normal capture.
The later `ch46-last-visual-source` pair tests which geometric LOD supplies
the capture and where proxy eligibility starts. The capture-grid and mip
problems have complete worked answers below, without separate packaged
starters. These pairs retain their own source checkpoints. See the
[runnable-stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md).

## A Source You Can Compare Against

The source files are [GrassClumpSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpSource.h)
and [BladeShape.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/BladeShape.glsl). Both are compiled
by C++ and GLSL. A template has sixteen blades and a stable variant ID; its
vertices use the existing curve and its nested mesh LODs. A capture is derived data,
not an artist-painted substitute for those vertices.

The [material and normal atlas previews](ReferenceImages.md#capture-surface-data-before-lighting)
show the two kinds of output side by side. Inspect the same tile in both:
its shape stays paired while its stored surface direction differs from its
material color. The previews are historical diagnostics, not raw channel dumps.

<a id="ch46-capture-a-relightable-clump"></a>

### Attempt CH46-capture-a-relightable-clump: keep the sun out of the capture

Capture a source clump from several azimuths and elevations, including the
view straight down. Decide what information the runtime needs to recover
material colour, surface orientation and front-surface depth. Predict what
would fail if the capture instead stored its final lit RGB value.
Also decide whether a rounded shading normal can replace the unrounded
geometric normal in every lighting and shadow-offset calculation.

**Acceptance:** Every captured view has nonzero coverage and finite values.
Interior samples agree with an independent CPU projection/rasterization of
the actual source triangles, including their material coordinates, normals
and metric depth. A changed colour, sun or animation time does not require a
new rest-source capture. A changed source shape does. Rejected source data
does not partially replace the last valid source metadata.

**Transfer:** Turn the sun behind the clump without rebaking it. Then change
the blade bend. Explain why these two edits have different invalidation rules.

<details>
<summary>Hint 1: distinguish surface data from illumination</summary>

The blade's root-to-tip coordinate and variation can reconstruct its colour
under the current material settings. Neither needs a sun direction. A normal
and depth describe the captured surface, not how bright it looked that day.

</details>

<details>
<summary>Hint 2: a stable capture frame</summary>

At the aerial pole, crossing an up vector with the view direction produces
a zero vector. Construct the right vector from azimuth first, then derive
the capture up vector from that right vector and the view direction.
Use a framing bound calculated from the actual source vertices.

</details>

<details>
<summary>Hint 3: distinguish the consumers of a normal</summary>

One RGBA16F attachment can store the root-to-tip coordinate, random variation
and coverage. Another stores a signed rounded normal and normalized metric
depth. Preserve the unrounded geometric normal too: the reference uses it
for translucency and shadow normal offset. An ordinary depth attachment
selects the nearest source triangle for all outputs.
Clear unused pixels to zero; keep capture layout transitions explicit.

</details>

<details>
<summary>Worked solution: rasterize the actual source</summary>

[GrassClumpBake.vert.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpBake.vert.glsl)
calls the same `grassClumpPrototype`, `bladeCurve`, `bladeEdge` and
`bladeNormal` functions as the source checks. The pushed view index selects
the variant, azimuth and elevation. Each position is measured relative to
the source bound's centre. Its dot products with the capture's right and up
vectors produce orthographic XY; the view-direction dot product produces
metric depth divided by the framing diameter.

The [fragment shader](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpBake.frag.glsl) writes:

```glsl
vec3 face = normalize(normal);
if (dot(face, direction) < 0.0) { face = -face; }
materialData = vec4(attributes, 1.0);
normalDepth = vec4(normalize(face + roundOffset), attributes.z);
faceData = vec4(face, 1.0);
```

`attributes.xy` is the interpolated blade-height coordinate and source
variation. `attributes.z` is signed capture depth normalized into [0,1].
There is no light lookup. Covered pixels have alpha one; clear pixels have
alpha zero and zero-valued attributes.
The depth is mirrored into `materialData.z`, pairing it with coverage for
parallax steps that need only one texture lookup. A separate all-pixel check
requires both depth copies to remain identical through every mip. This uses
an otherwise spare channel; it does not increase the atlas allocation.
The separate geometric-normal attachment does increase it. This avoids
feeding a fake rounded normal into a term that expects geometric orientation.
All three attachments store zero outside coverage and use the same mip policy.

[GrassClumpAtlas](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Grass/GrassClumpAtlas.cpp)
owns the texture arrays, views, scratch depth image and sampler. It opens
small offscreen rendering scopes before the scene, draws sixteen instances
of the last visual mesh strip into each view, then builds the mip chain. Its source
key includes geometry-dependent settings, not the current colour or time.
Bounds are prepared transactionally before updating the accepted key.
In the current reference, the owner deletes copying and supplies no move
operation: keep the atlas inside `GrassField`, and recreate its resources
through `Initialize`/`Shutdown`. This ownership policy belongs to the written
continuation; leave sealed checkpoints' pinned protected headers unchanged.

[GrassImpostorGpuTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/GrassImpostorGpuTests.cpp)
reads the actual attachments. Its CPU oracle constructs source triangles,
projects them independently, selects the frontmost intersection and compares
interior pixels. The point must be separated from every competing triangle's
edge, not just the floating-point winner's edge: subpixel rasterization can
change which primitive wins there. The guard is derived from the device's
reported [`subPixelPrecisionBits`](https://docs.vulkan.org/spec/latest/chapters/limits.html).
The test reports exclusions, requires substantial samples in every view and
retains its attribute-error thresholds. Coverage checks still use every pixel
of every view, including those excluded from exact attribute comparison.
For thin triangles the interpolation reference also accounts for the
device's subpixel grid. At a half-grid boundary, the explicit CPU/shader
projection roundoff guard may permit either adjacent coordinate. Every
channel must jointly match the same source triangle and grid choice within
.003; the test also rejects deliberately inverted normals at every compared
point. It does not increase the normal tolerance until an image passes.
The [rasterization rules](https://docs.vulkan.org/spec/latest/chapters/primsrast.html)
explain why an infinite-precision CPU projection is not a bit-exact GPU oracle.

`--replay <capture-directory> <subpixel-bits>` checks retained `capture.u16`
and `source.bin` without initializing Vulkan. It is useful for diagnosing
the reference model, but does not rerun capture, synchronization or cache
invalidation. Keep that distinction in the evidence.
Replay with the matching source checkpoint: a later attachment-channel layout
must not silently reinterpret an earlier capture as new-format evidence.

</details>

## Put Views Where The Eye Goes

<a id="ch46-horizon-capture-grid"></a>

### Attempt CH46-horizon-capture-grid: reconstruct a ground-level silhouette

The first atlas used elevations -15, 20, 55 and 90 degrees. Predict which
captures a horizontal eye blends and how much of each it uses. Sketch two
overlapping blades viewed from those angles. Does correct interpolation of
their stored attributes imply the same visible silhouette as a horizontal
capture? Design a view grid that spends more of its budget near the horizon.

**Acceptance:** Include a real zero-elevation capture. Bake and runtime must
agree on every nonuniform interval, its midpoint and both endpoints, with
bounded selection outside the supported range. Verify the compiled selection
at 1x/4x against an independent knot table, then retain matched geometry/old/
new shaded, normal, albedo and coverage images at fixed source and time.
Inspect traversal, slopes and aerial views. Report atlas bytes and bake cost.
Do not change density or stretch source blades to make the experiment pass.

**Transfer:** Why can adding elevations reduce angular blur without fixing
azimuth interpolation, disocclusion or the loss of a normal distribution in
a coarse mip? Would doubling every dimension be an efficient use of memory?

<details>
<summary>Hint 1: angle and row number are different coordinates</summary>

A uniform grid can map an angle to a row with one division. A nonuniform grid
first needs the neighboring angles. The interpolation fraction belongs to
that interval, not to the full -15-to-90-degree range.

</details>

<details>
<summary>Hint 2: spend samples around the common view</summary>

Try -15, 0, 15, 30, 45, 65 and 90 degrees. Keep the pole and the below-horizon
fallback range. Four source variants and eight azimuths now require 224
array layers; increasing azimuths too would exceed this 256-layer budget.

</details>

<details>
<summary>Hint 3: test an independent knot table</summary>

For angles `a[i] <= a <= a[i+1]`, the fractional row is
`i + (a - a[i]) / (a[i+1] - a[i])`. Clamp the overall range first. The last
coordinate selects the last interval with fraction one, not an extra layer.

</details>

<details>
<summary>Worked solution: share forward angles and inverse intervals</summary>

`grassClumpElevationAngle` defines the bake angles; the runtime converts its
rest-space view angle through `grassClumpElevationCoordinate`:

```cpp
float grassClumpElevationCoordinate(float angle)
{
    if (angle <= 45.0f) { return clamp((angle + 15.0f) / 15.0f, 0.0f, 4.0f); }
    if (angle <= 65.0f) { return 4.0f + (angle - 45.0f) / 20.0f; }
    return 5.0f + (min(angle, 90.0f) - 65.0f) / 25.0f;
}
```

The four-view reconstruction still uses two azimuths and two elevations;
only the capture grid and its inverse change. The CPU checks use an explicit
seven-angle table rather than deriving the expected answer from the inverse
function. `GrassCaptureViewOracle.frag.glsl` exercises the compiled functions
over 1,024 angles, including out-of-range endpoints, through actual 1x/4x
render/resolve/readback. The existing source-attribute oracle checks every new
capture against independently rasterized source triangles.

At RGBA16F with three attachments and eight mips, 224 layers consume
117,438,720 payload bytes, about 112 MiB, versus 67,107,840 bytes before.
The extra 48 MiB buys angular resolution, not additional grass. This remains
an experiment until the native comparisons justify that cost. It does not
restore the field's deliberately thinned population or supply a far canopy.
Build, native and independent source-pair status is recorded in `REFERENCE.md`;
the original pinned capture lesson keeps its historical four-elevation atlas.

</details>

<a id="ch46-last-visual-source"></a>

### Attempt CH46-last-visual-source: capture what the handoff actually replaces

The runnable `ch46-last-visual-source` pair pins one source checkpoint. Starter
contains the detailed-strip/source-ownership mistakes; Solution is the complete
separate source tree. Use the [stage runner](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
from the outer checkout. `REFERENCE.md` records which independent gates have
actually run; registration alone is not verification.

The first bake sampled seven segments of each curve. The final mesh LOD
samples three. Predict where their silhouettes, interpolated normals and
depth differ, even though both call `bladeCurve`. Which should the capture
replace? Also consider a small blade whose projected size requests an
impostor before its geometric LOD switch has completed.

**Acceptance:** Capture the last visual mesh's actual vertex sequence,
including its tip, material coordinates and interpolated normals. Keep the
full-curve bounds conservative. No camera or shadow proxy may own a group
while that group still uses the detailed mesh. Fade ownership in after the
last mesh switch rather than introducing a new hard ownership jump. Check
the actual capture against an independent last-LOD triangle rasterizer,
exercise both camera/caster eligibility, and retain both high/low mesh
capacity-overflow checks. Inspect old/new handoff silhouettes at fixed time.

**Transfer:** Why does using the same procedural curve fail to guarantee
that two discretizations shade identically? What further information does a
single mip-filtered normal still lose after the geometry sequence matches?

<details>
<summary>Hint 1: inspect the actual draw, not its generator's name</summary>

The low mesh uses high-curve node indices 0, 2, 4 and 7. Its three chords are
not the seven high mesh segments. The final tip needs only one vertex because
its width is zero.

</details>

<details>
<summary>Hint 2: match count and index mapping together</summary>

Push `LOW_SEGMENTS`, draw `2*LOW_SEGMENTS+1` vertices and map each vertex pair
through `LOW_TO_HIGH` before evaluating its curve parameter. Merely reducing
the vertex count would capture only the bottom of the blade.

</details>

<details>
<summary>Hint 3: source eligibility is independent of projected size</summary>

Generation chooses one geometric LOD for the entire group using its centre's
camera distance. Both proxy ownership weights need that same source-state
guard, including an offscreen group needed only by a light volume.

</details>

<details>
<summary>Worked solution: match the final strip and guard its ownership</summary>

In `GrassClumpAtlas::Record`, push `LOW_SEGMENTS` and draw
`LOW_SEGMENTS*2+1` vertices per source blade. The bake vertex shader uses:

```glsl
uint segment = uint(gl_VertexIndex) / 2u;
uint highSegment = push.segmentCount == LOW_SEGMENTS ? LOW_TO_HIGH[segment] : segment;
float t = segmentT(highSegment);
```

The remaining position, normal, rounding and material calculations use the
same source functions as before. Bounds still contain the higher-resolution
curve; a chord between contained endpoints remains inside the conservative
bound. The independent CPU raster oracle explicitly builds the low strip,
not whichever segment count the production bake happens to request.

`grassClumpMeshSourceWeight` is zero through `lodDistance`, then rises over
`max(morphBand,.001)`. Generation takes the minimum of this guard and each
camera/light proxy weight. The group already draws the low strip throughout
that overlap, so the capture is not replacing a partially morphed high strip.
This does not move roots or thin the population. GPU tests explicitly retain
the high mesh for a near-source fixture, allow far proxies, and repeat the
same check for offscreen shadow casters. Overflow fixtures independently
exhaust both geometric storage regions without changing the expected source
population. Native acceptance and runnable-pair status live in `REFERENCE.md`.

</details>

## A Mip Is Not A New Material

<a id="ch46-preserve-covered-area"></a>

### Attempt CH46-preserve-covered-area: reduce the clump without fattening it

Build the capture's mip chain. A narrow blade surrounded by empty pixels
will soon share a texel with the background. Decide how to average its
coverage, material coordinates, normal and depth. Explain what goes wrong
if empty pixels contribute an arbitrary normal or ground colour.

**Acceptance:** For every view, average alpha remains within the specified
floating-point tolerance across the whole mip chain. Attributes remain
finite. The runtime can recover attributes conditioned on covered area
without a coloured fringe around empty texels. Do not replace fractional
coverage with a binary test in the data merely to make distant grass thicker.

**Transfer:** Reduce a blade covering one of four texels to one texel. Predict
the stored alpha and the reconstructed material coordinate. Which part of
this result still cannot be represented by a single binary visibility sample?

<details>
<summary>Hint 1: area and surface properties are different quantities</summary>

The new texel covers one quarter blade and three quarters empty space.
Its coverage should change. The blade's own material coordinate should not
turn into one quarter of its old value after reconstruction.

</details>

<details>
<summary>Hint 2: filter premultiplied attributes</summary>

Store zero attributes outside coverage. Filtering then averages the product
of coverage and each attribute. Divide by filtered coverage when reading a
nonempty result; normalize the recovered normal afterwards.

</details>

<details>
<summary>Hint 3: make the visibility choice later</summary>

Keep raw fractional area in alpha. Mask thresholds or alpha-to-coverage are
runtime visibility policies, not reasons to overwrite that measured area.
Check the mean alpha independently for every layer and mip.

</details>

<details>
<summary>Worked solution: premultiplied data, explicit limitations</summary>

At full resolution a covered fragment stores its attributes with coverage
one, and every empty pixel stores zero. Linear downsampling therefore
produces premultiplied attributes automatically. `GrassClumpAtlas::Record`
blits each layer independently into the next mip, with a write-to-read
barrier before that level becomes the next source. Once complete, it hands
the full texture arrays to fragment sampling in read-only layout.

At a nonempty filtered sample, reconstruct an attribute as
`premultipliedAttribute / coverage`. Do this for all attachments using the
material attachment's alpha. Normalize the resulting normal before lighting.
Do not divide an empty sample; reject it first.

For the one-in-four example, alpha becomes .25 and the stored coordinate
becomes .25 times the old coordinate. Dividing restores the blade's original
coordinate. The GPU test measures the actual mean alpha at all eight mips,
not a reimplementation of the downsampler.

Fractional area is not identical to a binary cutout silhouette. A one-sample
depth buffer cannot represent all partially covered surfaces at a pixel.
Likewise, averaged depth and normal describe an aggregate, not an exact new
geometric surface. The subsequent field stage must test its visibility,
parallax and depth policy in motion; a passed capture test alone does not
certify those choices.

Filtering attributes and filtering lighting are different operations. The
accepted runtime evaluates each contributing captured view's lighting before
averaging covered radiance, with a per-view specular-variance approximation.
This avoids lighting one cross-view average normal, but cannot recover the
distribution already lost inside each spatial mip. See
[the appearance problem](48-Grass-In-The-Coastal-Pipeline.md#ch48-grass-appearance)
for controls, failure cases and the measured additional cost.

</details>

## Check The Capture Before The Field

After generating projects with `GenerateProjects.bat --tutorial-tests`, build `TutorialGrassClumpTests` and
`TutorialGrassImpostorGpuTests` with one compiler worker. Run the CPU test
first. Run the GPU test separately, for example:

```powershell
& ./Build/Artifacts/Release/TutorialGrassImpostorGpuTests/TutorialGrassImpostorGpuTests.exe `
    RTX Build/GrassImpostors/Atlas-RTX
```

Repeat on Radeon with a fresh evidence directory. Inspect both generated
atlas sheets: material coordinates reconstructed as colour, rounded shading
normals and geometric normals. Check low, oblique and straight-down rows, not just the most flattering
front view. Vulkan errors, missing layers and blank views are failures, not
acceptable starter omissions. Run within the repository's memory and idle
guards; do not overlap this process with a build.

Next: [47 — Grass Representation Handover](47-Grass-Representation-Handover.md).
Keep this chapter's captured source, coordinates and coverage contract when
choosing which representation owns a plant.
