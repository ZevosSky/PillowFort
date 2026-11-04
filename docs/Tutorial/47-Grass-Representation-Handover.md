# 47. Grass Representation Handover

Chapter 46 gives you captured surface data. Now make it replace geometry in
a running field. Begin in Grass, not Horizon: a smaller scene makes a wrong
plant, depth value or transition easier to isolate.

**Prerequisites:** Chapter 46's source, capture and mip contracts, especially
“A Source You Can Compare Against” and “A Mip Is Not A New Material”; Chapter
27, sections 2–5 (wind, projected width, coverage and rounded normals); Chapter
37, section 5 (projected size and hysteresis); and Chapter 40, section 2
(representation ownership). For reconstructed depth, reuse Chapter 10,
section 2's projection and divide by `w`, Chapter 38, section 6's explicit
texture gradients, and Chapter 41, section 1's camera/shadow depth boundary.

**Start here:** work through stable identity first, then use
`ch47-grass-handover` for projected selection and `ch47-explicit-coverage`
for sample coverage. The [stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
prepares separate Starter/Solution trees. Identity, deformation and depth
are problems over the assembled source with worked answers; they have no
separate packaged starters.

**Accepted checkpoint:** The current shared renderer passes CPU and actual
GPU contracts on RTX/Radeon, plus native 1x/4x, low-sun, motion, recreation,
scaled UI and 4K controls. Gary accepted its current appearance/performance
balance, not exact mesh/proxy lighting equivalence or an island-wide canopy.
The [checkpoint record](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md#accepted-horizon-grass-checkpoint-2026-10-19)
separates historical lesson pins, measured lighting cost, failed experiments
and unfinished larger captures/shrub work. These tests do not turn a smaller
triangle count into a performance win.

The paired `ch47-grass-handover` stage omits the projected-size weight. Its
Starter still renders geometry; its Solution is a separate complete source
tree. The later `ch47-explicit-coverage` pair fills every MSAA sample instead
of preserving captured area. Each pair retains its own source checkpoint.
Independent builds and exact-omission acceptance checks pass for both pairs;
their native scene smokes pass on RTX and Radeon. The identity, deformation
and depth problems have worked answers, without separate packaged starters. Use the
[stage guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md) from the outer checkout.

## Keep The Plants

<a id="ch47-stable-clump-identity"></a>

### Attempt CH47-stable-clump-identity: change representation, not population

Generate a geometric field and an impostor field from the same seed. A plant
must keep its location, shape, facing, dryness and animation phase when the
camera crosses the transition. Include tiles left of and behind the origin.
Decide which values name a clump and which are only temporary buffer slots.

**Acceptance:** Changing representation does not change source identity.
The last group of tile -1 and the first group of tile 0 have consecutive,
distinct world-cell IDs. Actual GPU readback reconstructs all sixteen blades
of every proxy group from the corresponding geometric run. Reordering GPU
append slots must not become a new random seed.

**Transfer:** Reverse the tile list. Which bytes may change order, and which
world-space properties must stay the same?

<details>
<summary>Hint 1: a draw slot is not an identity</summary>

Atomic append order is scheduling-dependent. Name the group before appending
it, from its integer world cell, then derive its properties from that name.

</details>

<details>
<summary>Hint 2: partition the existing lattice</summary>

Use a four-by-four group of candidate positions. Require the tile's side
count to be divisible by four. Multiplying a signed tile coordinate by the
number of groups per tile works on both sides of zero without truncating a
negative floating-point position toward zero.

</details>

<details>
<summary>Hint 3: one template function</summary>

The baker and generator should both call `grassClumpPrototype`. Keep random
state updates in explicit sequence: several mutating calls used as constructor
arguments can have different evaluation orders in C++ and GLSL.

</details>

<details>
<summary>Worked solution: world cells select a shared source</summary>

[GrassClumpSource.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpSource.h) defines
`grassClumpCell(tile, local, bladesPerSide) = tile * (bladesPerSide / 4) + local`.
The [generator](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassGenerateKernel.glsl) hashes that signed
world cell, chooses one of four deterministic source variants and establishes
its centre, yaw, scale, dryness and phase before any atomic append.

Both paths use the same source blade function. Geometry writes sixteen
transformed blades; the far path stores the transform and variant in one
64-byte `GrassClump`. The CPU owner rounds the editable side count to a
multiple of four explicitly. It does not change source density silently in a
shader while the panel reports a different value.

[GrassGenerationProbe.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/GrassGenerationProbe.h)
dispatches the production begin/generate/end shaders on a negative tile,
reads actual buffers and matches the proxy's reconstructed source against
the geometric run. It also tests draw bounds and canaries. This is stronger
than checking that two screenshots both contain something green.

</details>

## Spend An Error Budget

Projected height gets **smaller** as a clump recedes, while its proxy weight
must get **larger**. With full geometry at 32 pixels and full proxy at 12,
the 22-pixel midpoint has proxy weight `0.5`; at 40 pixels the weight is zero,
and at 8 it is one. Doubling viewport height doubles the same clump's pixel
height, so a former midpoint needs geometry again. Keep that direction of
change clear before implementing the smooth transition.

<a id="ch47-projected-handover"></a>

### Attempt CH47-projected-handover: replace only what has become small

Make the field choose representation from projected size. Double the window
height without moving the camera, then narrow its field of view. Predict
which change should keep geometry farther away. During the transition, avoid
both a missing band and two fully opaque copies of the same clump.

**Acceptance:** The proxy weight is zero at the full-geometry threshold, one
at the full-proxy threshold, bounded and monotonic between them. Both modes
use the same population. At each transition pixel, exactly one representation
is selected. Inspect moving ground-level and aerial captures at 1x and 4x.
Disabling impostors must produce a useful geometric comparison, not an empty
or differently seeded field.

**Transfer:** Compare a 1080p and 4K view with the same lens. Why is an unchanged
metre-based switching distance an unfair quality comparison?

<details>
<summary>Hint 1: turn metres into pixels</summary>

For a vertical length, a useful conservative selector is
`height * (.5 * viewportHeight * abs(projection[1][1])) / viewDepth`.
Keep the two pixel thresholds ordered and separated.
Radial distance underestimates projected size toward the edge of the view.

</details>

<details>
<summary>Hint 2: the same decision at the same pixel</summary>

Independent random discards can reject both representations or retain both.
Use a common ordered threshold and opposite comparisons. Do not change the
source itself to make the overlap look denser.

</details>

<details>
<summary>Hint 3: transition and coverage are separate</summary>

The transition chooses a representation. Its coverage still describes how
much blade occupies a pixel. Preserve fractional area through filtered mips
and MSAA; a single-sample depth buffer needs an explicitly approximate binary
visibility policy.

</details>

<details>
<summary>Worked solution: projected weight and complementary masks</summary>

The production selector is:

```glsl
float grassClumpWeight(float pixels, float fullGeometryPixels, float fullProxyPixels)
{
    return 1.0 - smoothstep(fullProxyPixels, fullGeometryPixels, pixels);
}
```

The defaults are 32 and 12 projected maximum-blade-height pixels, including
the group's scale. The owner supplies focal pixels from the actual lens and
viewport. This is a conservative selection heuristic, not a proof that every
curved silhouette has exactly that screen error.

The accepted interactive profile explicitly uses 32/24 pixels, canonical
`patches` and 180 m reach; those are not silently promoted global defaults.
Do not widen a handoff or change density to conceal mismatched shading.
Keep source existence, physical covered area and representation ownership
separate; [Chapter 48](48-Grass-In-The-Coastal-Pipeline.md#ch48-grass-appearance)
uses that distinction to diagnose both bright bands and beach ghosts.

[GrassCoverage.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassCoverage.glsl) uses a 4x4 ordered
threshold. Geometry keeps pixels whose threshold is at least the proxy
weight; the proxy keeps the complement. Whole-clump reach/density fading is
separate from that choice. At 4x its fractional coverage becomes sample
coverage. At 1x an ordered binary approximation remains visible as a quality
limit, not evidence of equivalent antialiasing.

`--grass-impostors 0` disables only representation selection in either host.
It does not restore a different historical placement algorithm. Inspect
`--grass-view near`, `grazing`, `aerial` and `transition`, then the `traverse`
and `orbit` routes. The CPU selector test is necessary but cannot certify
temporal quality. The panel's LOD view colours clump proxies magenta.

</details>

## Make Coverage Observable

<a id="ch47-explicit-sample-coverage"></a>

### Attempt CH47-explicit-sample-coverage: explain a field that fills out on another GPU

A captured clump has fractional area coverage. Its source readback agrees
with the geometric blades, yet the four-sample field looks much fuller on
another device. First separate material/normal errors from coverage errors:
compare 1x/4x, then use flat ground, no wind, no shadows and the normal view.
What is still not proven by reading the atlas alone?

**Acceptance:** The actual shader renders sixteen known area levels at 1x
and 4x. Each resolved RGBA pixel agrees with the production sample mask within
one 8-bit UNORM quantum. Zero area writes no samples; full area keeps every
raster-covered sample. Across a 4x4 pixel block the four-sample mean area is
within half a sample out of 64. Retain single-sample ordered ownership and
one-sample shadows. Compare actual field silhouettes on both devices too.

**Transfer:** What additional mask representation, coverage tests and renderer
policy would an 8x target need? Why is silently using four bits on that target
not a supported extension? Explain why the representation-selection mask and
the captured surface's fractional area are different quantities.

The paired `ch47-explicit-coverage` follow-up pins source `f106fe8`, whose
actual raster tests pass on both GPUs. Its Starter deliberately fills all
four samples rather than transporting fractional area; the CPU math remains
healthy, so only the real 4x resolve assertion should fail. The separate
complete Solution restores the production mask. Both independent builds,
acceptance and visual smokes now pass on RTX and Radeon, with all four
captures inspected. Consult `REFERENCE.md` for source and evidence details.

<details>
<summary>Hint 1: test what reaches the multisample target</summary>

An atlas alpha value does not specify a portable hardware alpha-to-coverage
transfer function. Render white into a cleared multisample target, resolve it,
and read it back. A normal-only beauty image can still hide a coverage error.

</details>

<details>
<summary>Hint 2: separate sample count from sample identity</summary>

For area `a`, start with `floor(4*a)` samples. Distribute the remaining
fraction with an ordered threshold, then rotate a bounded prefix mask to avoid
always favoring the same sample. Check the count independently of bit order.

</details>

<details>
<summary>Hint 3: do not apply area twice</summary>

The explicit output sample mask already intersects raster coverage. Disable
hardware alpha-to-coverage and write colour alpha one. Keep physical area in
the debug data rather than confusing that presentation alpha with the area
that selected the samples. Shadow targets still use their own one-sample policy.

</details>

<details>
<summary>Worked solution: a shared mask rule with actual resolved-pixel checks</summary>

[GrassCoverageRules.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassCoverageRules.h) supplies the
same ordered rank, rounded sample count and rotated mask to C++ and GLSL.
For 4x, the prefixes contain 0/1/2/3/4 samples; the two-sample prefix uses
opposite bits before rotation. The rule retains the earlier signed-pixel
4x4 Bayer order for 1x. The production fragment wrapper in
[GrassCoverage.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassCoverage.glsl) is:

```glsl
float grassCoverage(float area, uint samples)
{
    ivec2 pixel = ivec2(gl_FragCoord.yx) + ivec2(1, 2);
    uint mask = grassCoverageMask(area, samples, pixel.x, pixel.y);
    gl_SampleMask[0] = int(mask);
    if (mask == 0u) { discard; }
    return 1.0;
}
```

`GrassField` packs the real sample count and disables `alphaToCoverage` on
the grass pipelines. Geometry and reconstructed clumps call this wrapper
after computing their area and representation ownership. Clump data keeps
the physical area for the coverage debug view; presentation alpha stays one.
Shadow fragments explicitly pass one, irrespective of the scene sample count.
The current owner accepts only 1x/4x; unsupported counts produce a normal
initialization error. No optional alpha-to-one feature is needed.

`TutorialGrassClumpTests` checks 1,025 areas, mask bounds, signed-pixel rank,
single-sample compatibility and integrated area. That still does not prove
the graphics pipeline uses those masks. `GrassCoverageProbe.h` renders the
actual wrapper through `GrassCoverageOracle.frag.glsl`, resolves real 1x/4x
attachments, and compares every readback channel with the shared expected
count. Its small `coverage-1x.rgba` and `coverage-4x.rgba` evidence files are
64x16 RGBA8. Run `TutorialGrassImpostorGpuTests` on RTX and Radeon, then repeat
the geometric/proxy field controls with identical source, camera and lighting.
These checks establish portable area transport, not exact per-pixel equality
between differently sampled geometric and reconstructed surfaces.

</details>

## Animate Derived Data

<a id="ch47-live-deformation"></a>

### Attempt CH47-live-deformation: keep roots attached while the wind changes

Animate the captured clump without baking a new image every frame. The
geometric comparison must use the same deformation. Decide what approximation
you can share between a stored front surface and live curves, and what to do
when the interaction ball reaches a proxy.

**Acceptance:** Zero rest-height stays fixed. The deformation has a stable
inverse over its allowed range; normals remain perpendicular to transformed
tangents. Wind and colour changes do not invalidate rest captures. An
interactor overlap uses actual geometry. Inspect both calm and strong wind
while crossing the transition; a static far field is not accepted as animated
just because the nearby blades move.

**Transfer:** What extra data would independent blade flutter require beyond
one group's phase and one captured front surface?

<details>
<summary>Hint 1: begin with a shared transform you can invert</summary>

A stored rest surface can pass through a known invertible deformation.
That does not mean it can represent arbitrary newly revealed, intersecting
or independently moving surfaces.

</details>

<details>
<summary>Hint 2: vectors and normals are different</summary>

Use the inverse transform to choose a capture view in rest space. Transform
the recovered surface forward. Normals require the inverse transpose, not
the position transform.

</details>

<details>
<summary>Hint 3: keep the difficult local case geometric</summary>

The ball deforms individual blade curves. Force overlapping groups to
geometry rather than pretending that one rest capture contains their new
occlusion relationships.

</details>

<details>
<summary>Worked solution: a bounded coherent canopy lean</summary>

`grassClumpLean` applies horizontal displacement `wind * sin(angle) * y` and
vertical scale `cos(angle)` to a root-relative point. Its angle combines the
group's gust and phase and is clamped to +/- .8 radians, keeping the vertical
scale positive and its inverse bounded. It pins roots but is an affine canopy
approximation, not an elastic or arc-length-preserving blade solver.

Geometry transforms all upper control points relative to each actual root;
the proxy transforms the rest-space view plane and reconstructed surface.
`grassClumpUnlean` takes view vectors back to rest space, and
`grassClumpLeanNormal` implements the inverse-transpose normal transform.
The rounded normal is captured before illumination; the current shared grass
shader still evaluates colour, GGX or Blinn-Phong, translucency, ambient light
and shadows at runtime.
The geometric normal is captured separately so translucency and shadow
receiver offset retain the same kind of input as the geometric path. Rounded
and geometric normals are not interchangeable simply because both are unit
vectors.

This changes Chapter 27's independent control-point animation into coherent
group motion. It does not claim arbitrary individual flutter or exact
near/far curved-normal equivalence. Validate the visible approximation and
document its limits. An interaction overlap disables proxies for that group,
then uses the actual geometric interactor.

</details>

## Reconstruct The Surface

<a id="ch47-surface-depth"></a>

### Attempt CH47-surface-depth: a view plane must not become the occluder

Walk around a clump with a stone behind it. Then look straight down. Recover
surface depth and orientation from neighbouring captured views without a
pole singularity, dark empty-pixel fringes or the rectangular card's depth
covering the background.

**Acceptance:** Empty coverage never writes colour or depth. Nonempty
attributes are conditioned on covered area. Camera depth follows the
reconstructed surface, including the host's conventional/reversed convention;
shadow depth uses the conventional light projection. Inspect silhouettes,
stones, grass self-shadowing and aerial movement, not just a front-facing
still. Reject out-of-clip reconstructed points instead of clamping them onto
the near plane.

**Transfer:** Explain why averaging two captured front depths is an aggregate
approximation, not proof that a real surface exists at the resulting point.

<details>
<summary>Hint 1: choose views in source space</summary>

Undo the group's scale, yaw and lean before computing azimuth/elevation.
At the aerial pole use a deterministic right vector rather than normalizing
a zero cross product.

</details>

<details>
<summary>Hint 2: depth moves the lookup too</summary>

Project the current ray point into a capture. Its stored metric depth gives
a new point on that ray, which changes the texture lookup. A small fixed
number of such steps approximates parallax without treating the card plane
as the front surface.

</details>

<details>
<summary>Hint 3: derivatives must survive the loop</summary>

Compute UV gradients from the original plane before sampling. Supply those
gradients explicitly while iterating; view selection and discarded fragments
must not silently make mip selection undefined.

</details>

<details>
<summary>Worked solution: four views, covered attributes, current projection</summary>

[GrassClumpFragmentKernel.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassClumpFragmentKernel.glsl)
selects the two azimuths and elevations around the rest-space direction. Each
view performs two metric-depth fixed-point steps with `textureGrad`. Depth
is divided by the sampled coverage before interpreting its normalized value.
Out-of-bounds/empty samples contribute nothing. The four premultiplied
attributes and covered surface positions are weighted consistently.

After rejecting empty results, recover material coordinates, normalize the
covered normal and transform the surface into world space. Project that
surface through the actual camera or cascade matrix and write `gl_FragDepth`.
The camera's matrix supplies its depth convention; the shadow path uses the
host's conventional light matrix. The colour path calls `shadeGrass` in
[the shared material kernel](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassFragmentKernel.glsl),
not a second copied BRDF.
The conventional shadow variant samples only the coverage/depth attachment:
it does not fetch either normal texture or evaluate lighting it cannot use.

This has finite angular/depth resolution and stores only front surfaces.
Four-view blending and coarse depth mips cannot reproduce every disocclusion.
Fragment-written shadow depth uses an explicit policy for the owner's
D16_UNORM maps: the host's constant factor times two 16-bit quanta, plus its
slope factor times the maximum reconstructed-depth derivative. This is a
declared conservative policy, not a claim of matching every implementation's
fixed-function rounding. Derivatives are evaluated before divergent discards;
the owner refuses an incompatible shadow format until its policy is updated.
The [Vulkan depth-bias rules](https://docs.vulkan.org/spec/latest/chapters/primsrast.html)
describe that implementation dependence. Do not assume card-plane bias fixes
a fragment-written surface depth. These remain visual/error-budget checks,
not exceptions to validation or reasons to call a blank output successful.

</details>

Next: [48 — Grass In The Coastal Pipeline](48-Grass-In-The-Coastal-Pipeline.md).
That chapter combines the shared grass owner with the coast and shoreline;
the handover rules here remain in force.
