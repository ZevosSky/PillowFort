# 27 — Grass, Part III: The Look

**Goal:** from a field of green strips to grass that reads as *Ghost of
Tsushima*'s: blades growing in clumps that share a height, a lean, and a color;
wind that rolls across the field in gusts; blades that stay solid seen edge-on
and never thinner than a pixel; rounded shading, light shining through the
blades when you look toward the sun, and a far field that settles into one
surface. The grass shades the ground beneath it through the shadow map, and a
ball rolling through the field pushes the blades aside. Each section is one
idea, and each is a slider or a toggle you can see.

**ROADMAP:** step 21+ — the same demo, `Source/PillowFort/Demos/Grass/`, shaders
under `Shaders/Grass/`.

**Module:** `pf::demos::grass`. New shaders: `Noise.glsl`, `GrassShadow.vert.glsl`,
`GrassShadow.frag.glsl`. Nothing outside the demo's two folders changes.

**Prerequisites:**

- Chapters 25 and 26. Chapter 26's Part 2 is optional here too: everything in
  this chapter works with or without it, and where its code shows through, the
  text says what to leave out.
- Chapter 18 sections 8 (alpha-to-coverage) and 9 (what MSAA cannot fix).
- Chapter 17 sections 4 (a depth-only caster pipeline, dynamic depth bias), 5
  (`ShadowMaps::Record` and its `extraCasters` callback), 8 (the filter that
  averages several texels), 9 (`RecordShadows`), and 12 (cascades that move
  only in whole texels); and `cascadeTexelSize` in section 2's `ShadowData`.
- Chapter 16 section 5 — `lightIrradiance`, which every lighting term here
  multiplies.
- Chapter 15 section 9 — the three BRDFs, and the GGX helpers in
  `PreviewSurface.glsl` that section 7's highlight calls; and section 11, the
  `shaderDemoteToHelperInvocation` feature that `discard` needs, which section
  8's shader uses.
- Chapter 11 sections 4 (`makeUvSphere`, for section 9's ball) and 13 (a
  rotation's inverse is its transpose; `mat3(...)` keeps only the rotation).
- Chapter 10 sections 1 and 2 — view space, and the projection's `[1][1]`,
  which section 4 turns into pixels per metre.
- Chapter 21 section 3 — `Random.glsl`'s `pcgHash` and `randomFloat`.

---

## What makes it look like grass

Chapters 25 and 26 built the machinery; this chapter spends it. Chapter 25's
table, "Where each technique comes from", says which of these are the game's
and which are this tutorial's:

| Section | Idea | What you see change |
| --- | --- | --- |
| 1 | Clumps | the even lawn breaks into tufts with their own height, lean, and tint |
| 2 | Wind | gusts roll across the field; every blade sways on its own |
| 3 | Edge-on blades widened | the field stays solid at grazing angles |
| 4 | A minimum width, as coverage | far blades stop breaking into dashes |
| 5 | Rounded normals | each blade shades light-to-dark across its width |
| 6 | The far field | the distance settles into one surface instead of sparkling |
| 7 | Light through the blade, highlights, darker roots | back-lit grass glows; a sheen runs along the blades; the field gets depth |
| 8 | Grass shadows from an impostor | the ground and the lower blades darken under the grass |
| 9 | A ball the blades get out of the way of | a ring of parted grass follows the ball |

None of them is more than a few lines of shader. The work is in knowing *which*
few lines, and why.

### What you are actually writing

**This is what `GrassDemo.h` gains.** Chapter 26's header is the map; this
chapter adds to it in five places. Comments in the header that name another
chapter's section say so; a bare "section N" is this chapter's.

The panel's numbers, at the end of `GrassSettings`, each group naming its
section:

```cpp
    // Chapter 27
    float     clumpSize         = 1.5f;     // section 1: metres between clump centres
    float     clumpPull         = 0.35f;    // 0..1: how far blades move toward their clump's centre
    float     clumpFacing       = 0.6f;     // 0..1: how far blades turn toward their clump's facing
    float     clumpHeight       = 0.4f;     // 0..1: how much clumps differ in height
    float     clumpDryness      = 0.5f;     // 0..1: how far a clump's tips can turn toward dryColor
    glm::vec3 dryColor   { 0.70f, 0.62f, 0.33f };   // sRGB: straw
    float     windAngle         = 20.0f;    // section 2: degrees, turning from -Z toward +X, where the wind blows to
    float     windSpeed         = 3.0f;     // metres per second the gusts travel
    float     windStrength      = 0.6f;     // 0..1
    float     gustScale         = 15.0f;    // metres across one gust
    float     gustLean          = 0.35f;    // how far a full gust leans a blade, in blade heights
    float     swayFrequency     = 0.8f;     // hertz
    float     swayAmount        = 0.06f;    // in blade heights
    float     thicken           = 0.6f;     // section 3: 0..1
    float     minimumPixels     = 1.0f;     // section 4: used only when the scene is multisampled
    float     roundness         = 0.5f;     // section 5: 0..1
    float     translucency      = 1.0f;     // section 7
    int       highlightModel    = 0;        // GRASS_HIGHLIGHT_*: GGX, Chapter 15's
    float     roughness         = 0.43f;    // 0..1, for either highlight
    float     specular          = 0.08f;
    float     rootOcclusion     = 0.3f;     // 0..1: the light that reaches the root
    float     farBlendStart     = 25.0f;    // section 6: metres
    bool      grassShadows      = true;     // section 8: the impostor in the shadow map
    float     impostorHeight    = 0.6f;     // in mean blade heights
    float     impostorDensity   = 0.6f;     // the fraction that casts where the field is full
    bool      interactor        = true;     // section 9: the ball
    float     interactorRadius  = 0.4f;     // metres
```

Two private functions, after Chapter 26's:

```cpp
    void RecordImpostor(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t cascade);              // Chapter 27 section 8
    void CreateBall();                                                                                      // Chapter 27 section 9
```

Three constants, after `TERRAIN_CELLS`:

```cpp
    // Chapter 27 section 8: the shadow impostor is coarser; it floats over the ground, nobody sees it.
    static constexpr float    IMPOSTOR_CELL = 1.0f;
    // Chapter 27 section 9: the ball rolls round this circle.
    static constexpr float    BALL_ORBIT_RADIUS = 2.0f;    // metres
    static constexpr float    BALL_ORBIT_SPEED  = 0.4f;    // radians per second
```

The impostor's pipeline, after the other pipelines:

```cpp
    VkPipeline       m_impostorPipeline   = VK_NULL_HANDLE;   // Chapter 27 section 8
```

and three members: the ball's `DrawItem` beside the stones', and at the end of
the CPU state the viewport's height and the ball's centre:

```cpp
    scene::DrawItem              m_ball;
```

```cpp
    float                           m_viewportHeight = 1.0f;          // Chapter 27 section 4, from Resize
    glm::vec3                       m_ballCenter{ 0.0f };             // Chapter 27 section 9, from Update
```

### Where everything lands

```text
Shaders/Grass/
  GrassTypes.h              GrassBlade gains a third vec4; GrassParameters grows   all sections
  Noise.glsl                gradient noise                                        section 2
  GrassGenerate.comp.glsl   + clumps, gusts, a bigger culling sphere               sections 1, 2
  Grass.vert.glsl           + wind, widening, the width clamp, the ball            sections 1-5, 9
  Grass.frag.glsl           + dry tips, coverage, rounding, the far field, light   sections 1, 4-7
  Terrain.frag.glsl         + the ground takes the field's color far away         section 6
  GrassShadow.vert.glsl     the impostor, in a cascade                            section 8
  GrassShadow.frag.glsl     its dither                                            section 8
Source/PillowFort/Demos/Grass/
  GrassDemo.h/.cpp          the settings, the impostor, the ball
```

```text
GrassDemo.cpp - only what this chapter adds to or changes; the rest is Chapter 26's
  static terrainHeight(xz, amplitude, wavelength)       section 9 (new)
  namespace pf::demos::grass {
      static drawGrassPanel(settings, statistics, caps)   every section
      GrassDemo::Setup                                    section 9
      GrassDemo::CreatePipelines                          sections 4 and 8
      GrassDemo::CreateBall                               section 9 (new)
      GrassDemo::Resize                                   section 4
      GrassDemo::Update                                   section 9
      GrassDemo::CollectTiles                             section 1
      GrassDemo::WriteFrameBuffers                        every section
      GrassDemo::Record                                   sections 8 and 9
      GrassDemo::RecordImpostor                           section 8 (new)
      GrassDemo::Teardown                                 sections 8 and 9
  }
```

Add `Noise.glsl`, `GrassShadow.vert.glsl`, and `GrassShadow.frag.glsl`, and
rerun `GenerateProjects.bat`.

### The numbers, all at once

Every section reads a few new parameters, and it is simpler to grow the twin
struct once than nine times. Type these in now and skim the comments: each
section explains its own numbers when it uses them. **This is what
`GrassTypes.h` gains.** Four debug
views after Chapter 26's two, and the two highlights section 7 switches
between:

```c
#define GRASS_VIEW_CLUMPS   5u   /* Chapter 27: a color per clump */
#define GRASS_VIEW_WIND     6u   /* Chapter 27: gust strength, blue calm to red */
#define GRASS_VIEW_EDGE_ON  7u   /* Chapter 27: how edge-on the blade is, black to yellow */
#define GRASS_VIEW_COVERAGE 8u   /* Chapter 27: the coverage alpha-to-coverage gets */

/* Chapter 27 section 7: which highlight the blades get (GrassParameters::highlightModel). */
#define GRASS_HIGHLIGHT_GGX         0u   /* Chapter 15's microfacet lobe */
#define GRASS_HIGHLIGHT_BLINN_PHONG 1u   /* the older normalized Blinn-Phong lobe, to compare */
```

**`GrassBlade` grows a third `vec4`, `variation`**, after `shape`: per-blade
numbers the generation pass works out once and the shaders read. The blade is
48 bytes; the blade buffer grows to about 38 MB at the default capacities.

```c
    vec4 variation;       /* Chapter 27. x: the blade's own random number, 0..1; y: gust strength
                             where it stands, 0..1; z: its clump's dryness, 0..1; w: its clump's
                             random number, 0..1 */
```

**`GrassParameters` grows a block for this chapter** at its end, after Chapter
26 section 9's two occlusion fields. If you skipped Chapter 26's Part 2, add
those two fields anyway, after `padding4` — `mat4 occlusionViewProjection;`
and `vec4 occlusionPyramid;` — because the offsets below count them; nothing
writes them, and their zeros mean "no occlusion test". The colors are
`vec4`s first, then the wind's direction and the interactor's sphere, then the
scalars, so that std140 packs them without holes:

```c
    /* Chapter 27: the look. */
    vec4  dryColor;         /* linear rgb: the color dry clumps' tips drift toward */
    vec4  windDirection;    /* xy: unit vector the wind blows along, in world xz; zw unused */
    vec4  interactor;       /* section 9: xyz centre of a sphere that pushes blades aside; w radius, 0 = none */
    float windSpeed;        /* metres per second the gusts travel */
    float windStrength;     /* 0..1: scales every gust */
    float gustScale;        /* metres across one gust */
    float gustLean;         /* how far a full gust leans a blade, in blade heights */
    float swayFrequency;    /* hertz */
    float swayAmount;       /* how far the sway leans a blade, in blade heights */
    float clumpSize;        /* metres between clump centres */
    float clumpPull;        /* 0..1: how far blades move toward their clump's centre */
    float clumpFacing;      /* 0..1: how far blades turn to face their clump's way */
    float clumpHeight;      /* 0..1: how much clumps differ in height */
    float clumpDryness;     /* 0..1: how far a clump's tips can drift toward dryColor */
    float thicken;          /* 0..1: how much of its lost width an edge-on blade gets back */
    float roundness;        /* 0..1: how far the normals tilt outward across the blade */
    float translucency;     /* how much sunlight comes through a blade */
    float roughness;        /* 0..1: Chapter 15's perceptual roughness; both highlights read it */
    float specular;         /* the highlight's reflectance head-on: Chapter 15's F0 */
    float rootOcclusion;    /* 0..1: the light that reaches the root */
    float farBlendStart;    /* metres: from here normals and occlusion fade toward the ground's */
    float minimumPixels;    /* the narrowest a blade is drawn, in pixels; 0 = no clamp */
    float viewportHeight;   /* pixels */
    float time;             /* seconds */
    float impostorHeight;   /* section 8: how high the shadow stand-in floats, in mean blade heights */
    float impostorDensity;  /* section 8: the fraction of it that casts where the grass is full */
    uint  highlightModel;   /* section 7: GRASS_HIGHLIGHT_* */
```

**`GrassPush`'s first padding word becomes `cascade`** (section 8):

```c
    uint cascade;         /* Chapter 27 section 8: the shadow cascade the impostor is drawn into */
```

The size checks change for the bigger structs, and two offsets in the middle of
the new block are pinned to catch a mistake early:

```c
    static_assert(sizeof(GrassBlade) == 48, "GrassBlade layout drifted.");
    static_assert(sizeof(GrassParameters) == 496, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, occlusionViewProjection) == 272, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, dryColor) == 352, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, windSpeed) == 400, "GrassParameters alignment drifted.");
```

The whole file is in the Appendix.

**This is the Chapter 27 block of `WriteFrameBuffers`**, at the end of the
designated initializer:

```cpp
        // Chapter 27.
        .dryColor        = glm::vec4(scene::srgbToLinear(m_settings.dryColor), 1.0f),
        .windDirection   = { std::sin(windAngle), -std::cos(windAngle), 0.0f, 0.0f },
        .interactor      = m_settings.interactor ? glm::vec4(m_ballCenter, m_settings.interactorRadius) : glm::vec4(0.0f),
        .windSpeed       = m_settings.windSpeed,
        .windStrength    = m_settings.windStrength,
        .gustScale       = m_settings.gustScale,
        .gustLean        = m_settings.gustLean,
        .swayFrequency   = m_settings.swayFrequency,
        .swayAmount      = m_settings.swayAmount,
        .clumpSize       = m_settings.clumpSize,
        .clumpPull       = m_settings.clumpPull,
        .clumpFacing     = m_settings.clumpFacing,
        .clumpHeight     = m_settings.clumpHeight,
        .clumpDryness    = m_settings.clumpDryness,
        .thicken         = m_settings.thicken,
        .roundness       = m_settings.roundness,
        .translucency    = m_settings.translucency,
        .roughness       = m_settings.roughness,
        .specular        = m_settings.specular,
        .rootOcclusion   = m_settings.rootOcclusion,
        .farBlendStart   = std::min(m_settings.farBlendStart, m_settings.maxDistance - 0.01f),
        // Chapter 27 section 4: the clamp needs samples to turn coverage into; at 1x it stays off.
        .minimumPixels   = m_context.formats.samples > VK_SAMPLE_COUNT_1_BIT ? m_settings.minimumPixels : 0.0f,
        .viewportHeight  = m_viewportHeight,
        .time            = m_time,
        .impostorHeight  = m_settings.impostorHeight,
        .impostorDensity = m_settings.impostorDensity,
        .highlightModel  = static_cast<uint>(m_settings.highlightModel),
```

and the line it needs at the top of the function:

```cpp
    const float     windAngle = glm::radians(m_settings.windAngle);   // the sun's azimuth convention
```

The colors are linearized like Chapter 25's. The wind's angle uses the sun's
convention, degrees from −Z toward +X, so 0 blows straight away from the
starting camera. Each section explains its own numbers.

**The panel** grows with the sections: each one adds its sliders where you try
them. The new groups go after "Generation", in the order the sections add
them. One line changes now — the combo gets four more debug views:

```cpp
            ImGui::Combo("View", &settings.debugView,
                         "Shaded\0Strip\0Normals\0LOD\0Tiles\0Clumps\0Wind\0Edge-on\0Coverage\0");
```

---

## 1. Clumps

Real grass does not grow evenly. It comes up in tufts, each from one root system,
and the blades of a tuft are about the same height, lean the same way, and are
the same shade, while the next tuft over is taller, or drier, or leaning the
other way. Chapter 26's field is uniform noise at every scale, which reads as a
lawn or a carpet; a field needs structure in between.

*Ghost of Tsushima* gets that structure from **clumps**: the ground
is divided into Voronoi cells, each blade belongs to the cell it stands in, and
the cell sets its height, its facing, and its color, and pulls its blades
toward its centre.

> **Jump:** a **Voronoi diagram** divides the plane by "which of a set of points
> is nearest". With the points scattered at random it looks like cells of a
> honeycomb drawn by hand, which is what clumps look like from above. The trick
> that makes it cheap is to put **exactly one point in each square of a coarse
> grid**, jittered inside its square by a hash of the square's coordinates — the
> same idea as Chapter 25's jittered blades, a size up. Then the nearest point to
> any position is almost always in the position's own square or one of the
> eight around it, so finding a blade's clump is nine distance checks, and,
> because the hash depends only on the square, every blade of the field agrees
> about where every clump is without anything being stored. Keep in mind that
> the clump is found again by every blade, every frame — like everything else
> about a blade since Chapter 26, it is a function of position.

**This is `nearestClump`**, in `GrassGenerate.comp.glsl` after `sphereInFrustum`:

```glsl
// Chapter 27 section 1: the clump this point belongs to. One centre per cell of a coarse
// grid, jittered inside its cell. The nearest centre is almost always in the
// point's own cell or one of the eight around it; searching those nine is the
// usual compromise, and a rare miss only gives a blade the second-nearest clump.
void nearestClump(vec2 xz, out vec2 center, out uint clumpHash)
{
    ivec2 home = ivec2(floor(xz / grass.clumpSize));
    float best = 1e30;
    for (int dz = -1; dz <= 1; ++dz)
    {
        for (int dx = -1; dx <= 1; ++dx)
        {
            ivec2 cell  = home + ivec2(dx, dz);
            uint  hash  = pcgHash(uint(cell.x) ^ pcgHash(uint(cell.y) ^ 0x9E3779B9u));
            uint  state = hash;
            vec2  point = (vec2(cell) + vec2(randomFloat(state), randomFloat(state))) * grass.clumpSize;
            float d     = dot(xz - point, xz - point);
            if (d < best)
            {
                best      = d;
                center    = point;
                clumpHash = hash;
            }
        }
    }
}
```

The squares are `clumpSize` metres across, 1.5 m by default. The hash mixes in
a constant, `0x9E3779B9`, so that a clump's square and a blade's cell with the
same integer coordinates do not draw the same random numbers. Nine squares is
the usual compromise: in a rare arrangement the true nearest point is two
squares away, and the blade joins the second-nearest clump instead, which no one
can see. Searching 5 × 5 squares would be exact and cost almost three times as
much.

**In `main`**, after the jittered position and before the ground's height:

```glsl
    // Chapter 27 section 1. Clumps: belong to the nearest centre, move part of the
    // way toward it, and take the clump's height, facing, and dryness as well as
    // your own. The root's height is found after the move.
    vec2 clumpCenter;
    uint clumpHash;
    nearestClump(xz, clumpCenter, clumpHash);
    xz = mix(xz, clumpCenter, grass.clumpPull * randomFloat(state));

    uint  clumpState     = clumpHash;
    float clumpHeight    = 1.0 + grass.clumpHeight * (2.0 * randomFloat(clumpState) - 1.0);
    float clumpFacing    = randomFloat(clumpState) * 6.2831853;
    float clumpDryness   = randomFloat(clumpState) * grass.clumpDryness;
    float clumpVariation = randomFloat(clumpState);
```

- **The pull** moves the blade part of the way toward its clump's centre, by a
  random fraction of `clumpPull`, so the tufts gather without becoming points.
  It happens before the root's height is looked up — the blade moved — and
  `root` is now declared after this block rather than beside `xz`.
- **The clump's own random stream**, from its hash, gives every blade of a clump
  the same height factor (within `±clumpHeight`), the same facing, the same
  dryness, and the same random number for its tint and the debug view.

The height factor is applied to the shape:

```glsl
    shape.x  *= clumpHeight;   // Chapter 27 section 1
```

and the facing is turned toward the clump's, by `clumpFacing`, replacing
Chapter 26's random facing:

```glsl
    // Chapter 27 section 1. Facing: the blade's own, turned part of the way toward its clump's.
    float ownFacing = randomFloat(state) * 6.2831853;
    vec2  facingDir = mix(vec2(sin(ownFacing), cos(ownFacing)), vec2(sin(clumpFacing), cos(clumpFacing)), grass.clumpFacing);
    float facing    = dot(facingDir, facingDir) > 1e-6 ? atan(facingDir.x, facingDir.y) : clumpFacing;
```

Blending two angles directly would go wrong across the wrap from 2π to 0 (the
average of 350° and 10° is 180°), so the two facings are blended as direction
vectors and the angle is read back with `atan`. The one degenerate case, two
opposite directions blended half and half, falls back to the clump's facing.

The blade then records what the shaders will want, in its new `vec4`:

```glsl
    blade.rootAndFacing = vec4(root, facing);
    blade.shape         = shape;
    blade.variation     = vec4(randomFloat(state), 0.0, clumpDryness, clumpVariation);
```

The `0.0` is section 2's gust; it becomes `gustStrength(xz)` there.

### The tile box

Clumps make blades taller than `shapeMax` — up to `1 + clumpHeight` times — so
Chapter 26's tile boxes must grow, or a tall clump at the edge of the view is
culled with its tile. **In `CollectTiles`:**

```cpp
    // Every blade of a tile fits in this box: its roots are inside the square, and
    // nothing of a blade is further from its root than twice its height plus its
    // width - Chapter 27 section 2's wind and section 9's ball lean a blade that far -
    // for the tallest clump Chapter 27 section 1 can make. So: the square
    // grown by that much, from the lowest the ground can be to the highest.
    const float tallest    = m_settings.shapeMax.x * (1.0f + m_settings.clumpHeight);
    const float bladeReach = 2.0f * tallest + m_settings.shapeMax.y;
```

The factor of 2 is section 2's: the wind leans blades further from their roots
than their height, and the box is written once for both.

### Color: dry tips and blade-to-blade variation

In `Grass.vert.glsl`, a new output carries the blade's `variation` to the
fragment shader:

```glsl
layout(location = 6) out vec4  bladeData;      // x: the blade's random number, y: gust, z: dryness, w: coverage
```

```glsl
    bladeData       = vec4(blade.variation.xyz, 1.0);
```

(the `1.0` becomes section 4's coverage). In `Grass.frag.glsl`, the matching
input,

```glsl
layout(location = 6) in  vec4  bladeData;
```

and the color, replacing Chapter 25's root-to-tip mix:

```glsl
    // Root to tip, each blade a little lighter or darker, and dry clumps' tips
    // drifting toward straw (section 1). Less light reaches the root (section 7).
    vec3  tip       = mix(grass.tipColor.rgb, grass.dryColor.rgb, bladeData.z);
    vec3  albedo    = mix(grass.rootColor.rgb, tip, bladeT) * (0.85 + 0.3 * bladeData.x);
```

A dry clump's tips drift toward straw, by its dryness, up to `clumpDryness`:
whole tufts turn tawny together, which is what the eye picks out in a real
field. On top of that each blade is up to 15% lighter or darker than its
neighbours, from its own random number, so even within a tuft no two blades
match.

### The Clumps group, and the Clumps view

**On the panel**, the "Clumps" group goes after "Generation":

```cpp
        if (ImGui::CollapsingHeader("Clumps"))
        {
            ImGui::SliderFloat("Clump size (m)", &settings.clumpSize, 0.3f, 6.0f);
            ImGui::SliderFloat("Pull to centre", &settings.clumpPull, 0.0f, 1.0f);
            ImGui::SliderFloat("Shared facing", &settings.clumpFacing, 0.0f, 1.0f);
            ImGui::SliderFloat("Height variation", &settings.clumpHeight, 0.0f, 0.9f);
            ImGui::SliderFloat("Dryness", &settings.clumpDryness, 0.0f, 1.0f);
        }
```

and the "Color" group gains the dry tip's swatch after "Tip":

```cpp
            ImGui::ColorEdit3("Dry tip", &settings.dryColor.x);
```

In the vertex shader, beside the tile view's color:

```glsl
    else if (grass.debugView == GRASS_VIEW_CLUMPS)
    {
        uint hash  = pcgHash(uint(blade.variation.w * 16777215.0));
        debugColor = vec3(hash & 255u, (hash >> 8) & 255u, (hash >> 16) & 255u) / 255.0;
    }
```

`16777215` is 2²⁴ − 1: it turns the clump's random number, 0 to 1, back into an
integer, which `pcgHash` scrambles again so that each clump gets a color of its
own, one byte per channel. And in the fragment shader, the clumps, wind, and edge-on views are drawn
unlit, so the numbers they show are not mixed with the lighting:

```glsl
    if (grass.debugView >= GRASS_VIEW_CLUMPS)   // clumps, wind, edge-on: unlit, to read the numbers
    {
        outColor = vec4(debugColor, 1.0);
        return;
    }
```

Set View to **Clumps** and fly up: patches of color a metre or two across, each
a tuft, their edges the straight lines of a Voronoi diagram. Back on **Shaded**,
the field has texture: taller and shorter patches, swirls where neighbouring
clumps face different ways, and drier tufts scattered through it. Drag "Pull to
centre" to 1 and the tufts tighten into separate bunches with bare ground
between; drag "Shared facing" to 0 and they lose their swirl.

---

## 2. Wind

Grass is the most visible thing wind touches. *Ghost of Tsushima*'s grass
samples a **scrolling 2D noise field**: a pattern of stronger and weaker wind,
moving across the world in the wind's direction, read by each blade where it
stands and fed into a sway that every blade runs on its own phase. Here the
wind's direction is a slider.

> **Jump:** **gradient noise** (Ken Perlin's) is a smooth random function: put a
> random unit vector — a *gradient* — at every integer point of a grid; at any
> position, each of the four surrounding grid points contributes its gradient
> dotted with the offset to the position (a little ramp centred on that point),
> and the four ramps are blended with a smooth curve. The result rises and falls
> continuously, with features about one grid square across, and never repeats
> visibly. Two copies at different scales, added (*octaves*), give big gusts with
> smaller variation inside. To make it **move**, sample it at `position - wind
> velocity × time`: the pattern slides across the world downwind, which is what
> a gust front does. Keep in mind that the noise is only the *strength* of the
> wind at a point; the blade's response to it is a separate, simple function.

Gradient noise in one dimension, worked by hand. Put a gradient of +1 at
`x = 0` and −1 at `x = 1`. Each gradient makes a ramp through its own point:
the one at 0 is `+1 × (x − 0)`, the one at 1 is `−1 × (x − 1)`. Both ramps are
zero at their own point, so the noise is 0 at every grid point. At `x = 0.5`
the first ramp gives +0.5 and the second −1 × (−0.5) = +0.5; blended half and
half, the noise is 0.5 — a hump between the two points. With equal gradients,
say +1 at both, the second ramp gives −0.5 there and the two cancel to 0: the
noise crosses zero instead. Random gradients make random humps and dips, about
one grid step across, and that is the pattern of gusts:

```text
   gradients +1 and -1            gradients +1 and +1

         .------.                     .-.
       .'        '.                  /   \
   ---'------------'---           --'-----\-------.---
                                           \     /
                                            '---'
   x=0     0.5       1            x=0      0.5      1
```

**This is `Shaders/Grass/Noise.glsl`:**

```glsl
// Shaders/Grass/Noise.glsl - two-dimensional gradient noise ("Perlin noise"), Chapter 27.
// Include Random.glsl first: the gradients come from pcgHash.
#ifndef PF_GRASS_NOISE_GLSL
#define PF_GRASS_NOISE_GLSL

// A random unit vector for each integer lattice point, the same every time.
vec2 latticeGradient(ivec2 point)
{
    uint  hash  = pcgHash(uint(point.x) ^ pcgHash(uint(point.y)));
    float angle = float(hash) * (6.2831853 / 4294967296.0);
    return vec2(cos(angle), sin(angle));
}

// Smooth noise in about [-0.7, 0.7]. Each corner of the lattice cell holding p
// contributes its gradient dotted with the offset to p - a little slope - and the
// four are blended with a quintic, so the result and its slope are continuous.
float gradientNoise(vec2 p)
{
    ivec2 cell = ivec2(floor(p));
    vec2  f    = fract(p);
    vec2  u    = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);

    float a = dot(latticeGradient(cell + ivec2(0, 0)), f - vec2(0.0, 0.0));
    float b = dot(latticeGradient(cell + ivec2(1, 0)), f - vec2(1.0, 0.0));
    float c = dot(latticeGradient(cell + ivec2(0, 1)), f - vec2(0.0, 1.0));
    float d = dot(latticeGradient(cell + ivec2(1, 1)), f - vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

#endif
```

The gradients come from `pcgHash` of the grid point, so they are the same
everywhere and every frame without a table; the angle is the hash scaled to a
full turn. The ramps are blended with the quintic `6t⁵ − 15t⁴ + 10t³`, Perlin's
improved fade curve, rather than a straight line: it is flat at both ends, so
neighbouring cells meet without a crease.

**This is `gustStrength`**, in `GrassGenerate.comp.glsl` after `nearestClump`
(include `Noise.glsl` after `Random.glsl`):

```glsl
// Chapter 27 section 2: gust strength where a blade stands, 0 calm to 1 a full gust. Two
// octaves of noise, the whole field sliding downwind at windSpeed.
float gustStrength(vec2 xz)
{
    vec2  drift = grass.windDirection.xy * grass.windSpeed * grass.time;
    vec2  p     = (xz - drift) / grass.gustScale;
    float n     = gradientNoise(p) + 0.5 * gradientNoise(p * 2.03 + vec2(17.0, 31.0));
    return clamp(0.5 + n, 0.0, 1.0) * grass.windStrength;
}
```

Two octaves, the second at about twice the frequency and half the weight, offset
so that the two do not line up. The sum is roughly ±1; mapped to 0 to 1 and
scaled by `windStrength`, it becomes the gust where the blade stands. `gustScale`
is how many metres one gust spans. The blade's record gets it:

```glsl
    blade.variation     = vec4(randomFloat(state), gustStrength(xz), clumpDryness, clumpVariation);   // Chapter 27
```

The gust is sampled **once per blade**, in compute, not per vertex: the noise is
a few dozen instructions, and every vertex of a blade would compute the same
value.

### The blade's response

**This is `applyWind`**, in `Grass.vert.glsl` before `main`:

```glsl
// Section 2. The upper control points move downwind, then the tip is pulled back
// to the blade's length: it leans, it does not stretch.
void applyWind(inout BladeCurve curve, GrassBlade blade)
{
    float height   = blade.shape.x;
    float gust     = blade.variation.y;
    vec3  downwind = vec3(grass.windDirection.x, 0.0, grass.windDirection.y);

    // Every blade sways on its own phase, so neighbours never move in step; gusts
    // lean it further and make it sway harder.
    float phase = 6.2831853 * (blade.variation.x + grass.swayFrequency * grass.time);
    float lean  = gust * grass.gustLean + sin(phase) * grass.swayAmount * (0.3 + gust);

    float bladeLength = distance(curve.p3, curve.p0);
    curve.p2 += downwind * height * lean * 0.5;
    curve.p3 += downwind * height * lean;
    curve.p3  = curve.p0 + normalize(curve.p3 - curve.p0) * bladeLength;
}
```

and it is applied to the curve before anything evaluates it:

```glsl
    BladeCurve curve = bladeCurve(blade);
    applyWind(curve, blade);          // section 2
```

- **The lean** has two parts. The gust leans the blade steadily downwind, by up
  to `gustLean` of its height in a full gust. On top of it, every blade sways
  back and forth, `sin` of a phase that advances at `swayFrequency`; the blade's
  own random number offsets the phase, so neighbours never sway in step, and the
  gust scales the sway, so blades in a gust thrash while blades in a lull barely
  move.
- **Only the upper control points move**: `P2` by half the lean, the tip `P3` by
  all of it. The root stays planted and the curve bends over, rather than the
  whole blade sliding sideways.
- **The tip is pulled back to the blade's length.** Moving `P3` sideways would
  stretch the blade; normalizing the root-to-tip vector and restoring its
  length makes it *lean* instead, the tip swinging on an arc around the root, as
  a real blade does.

### Culling a leaning blade

A blade that leans no longer fits Chapter 26's culling sphere. Its tip stays at
its height from the root, but `P2` can be pushed out further, and with section
9's ball further still; every control point stays within **twice** the height of
the root. **In `GrassGenerate.comp.glsl`**, the sphere doubles:

```glsl
    // Every point of the blade is within its height of the root, and its edges
    // within half its width more. Chapter 27: the wind and the ball lean a blade
    // but keep its length (sections 2 and 9); its control points then stay within
    // twice its height of the root, so the sphere doubles.
    if (!sphereInFrustum(root, 2.0 * shape.x + shape.y)) { return; }
```

and if you did Chapter 26's Part 2, the occlusion test takes the same radius:

```glsl
    if (occluded(root, 2.0 * shape.x + shape.y))
```

Section 1 already grew the CPU's tile box to match.

### The Wind group, and the Wind view

**On the panel**, the "Wind" group goes after "Clumps":

```cpp
        if (ImGui::CollapsingHeader("Wind"))
        {
            ImGui::SliderFloat("Blows toward", &settings.windAngle, 0.0f, 360.0f, "%.0f deg");
            ImGui::SliderFloat("Strength", &settings.windStrength, 0.0f, 1.0f);
            ImGui::SliderFloat("Gust speed (m/s)", &settings.windSpeed, 0.0f, 15.0f);
            ImGui::SliderFloat("Gust size (m)", &settings.gustScale, 2.0f, 60.0f);
            ImGui::SliderFloat("Gust lean", &settings.gustLean, 0.0f, 1.0f);
            ImGui::SliderFloat("Sway (Hz)", &settings.swayFrequency, 0.0f, 3.0f);
            ImGui::SliderFloat("Sway amount", &settings.swayAmount, 0.0f, 0.3f);
        }
```

The view colors each blade by its gust:

```glsl
    else if (grass.debugView == GRASS_VIEW_WIND)
    {
        debugColor = mix(vec3(0.1, 0.2, 0.9), vec3(1.0, 0.3, 0.1), blade.variation.y);
    }
```

Set View to **Wind** and fly up: blotches about fifteen metres across, blue in
the lulls and pinker in the gusts, drifting across the field in the wind's
direction at three metres a second. At the default strength of 0.6 no gust
reaches full red; drag "Strength" to 1 and the strongest do.

Back on **Shaded**, the gusts are visible as waves of leaning grass rolling
across the hills, and the grass in a lull still moves, a little, each blade on
its own.

---

## 3. Edge-on blades

A blade is a ribbon. Seen face-on it is as wide as it is; seen edge-on it is a
line, and the pixels behind it show through. Look across a field at a low angle
and a large fraction of the blades are close to edge-on, so the field thins out
exactly where it should look thickest, and as the camera turns, blades flick
between wide and invisible. *Ghost of Tsushima* widens edge-on blades in view
space: the more edge-on a blade is, the more it is spread sideways
**on screen**.

> **Jump:** until now every vertex position has been worked out in world space
> and only transformed at the end. This section measures and moves the vertex
> **in view space** — the camera's own frame, where the camera is at the origin
> looking down −Z, x is right on screen and y is up on screen. Two questions are
> easy to ask there and awkward anywhere else: "how much does this surface face
> the camera?" (the normal against the direction to the camera) and "which way is
> *across the blade, on screen*?" (perpendicular to the blade's direction, in x
> and y, ignoring depth). The offset is then turned back into world space with
> the transpose of the view matrix's rotation, which for a rotation is its
> inverse (Chapter 11 section 13): the rotation's axes are **orthonormal** — unit
> length, at right angles to each other — and for such a matrix, swapping rows
> and columns undoes it. `mat3(frame.view)` keeps only that rotation, which is
> all a direction needs: directions ignore translation. Keep in mind that this
> changes only where the vertex is drawn, not the blade's normal: lighting still
> sees the true blade.

**In `Grass.vert.glsl`**, after the morph:

```glsl
    // Section 3. In view space, "how edge-on" and "how wide on screen" are easy to ask.
    vec3  viewPosition = (frame.view * vec4(position, 1.0)).xyz;
    vec3  viewNormal   = mat3(frame.view) * normal;
    vec3  viewTangent  = mat3(frame.view) * bezierDerivative(curve, t);
    vec3  viewRight    = mat3(frame.view) * curve.right;
    float edgeOn       = 1.0 - abs(dot(viewNormal, normalize(-viewPosition)));

    // Across the blade as the screen sees it: perpendicular to its projected
    // tangent, pointing the way its right edge does.
    vec2 across = vec2(viewTangent.y, -viewTangent.x);
    across = dot(across, across) > 1e-12 ? normalize(across) : vec2(1.0, 0.0);
    if (dot(across, viewRight.xy) < 0.0) { across = -across; }

    float halfWidth = 0.5 * curve.width * (1.0 - t * t);
    float widen     = grass.thicken * edgeOn * halfWidth;
```

- **`edgeOn`** is 0 when the blade faces the camera and 1 when it is exactly
  edge-on: one minus the absolute cosine between the blade's normal and the
  direction to the camera. The camera is at the origin of view space, so the
  direction from the vertex to it is `-viewPosition`. Absolute, because either
  face may be the one seen.
- **`across`** is perpendicular to the blade's direction as projected on screen
  — the tangent's x and y, rotated a quarter turn — and flipped if needed to
  point the same way as the blade's right edge, so that the left edge (`side`
  −1) moves left and the right edge right, and the strip widens instead of
  twisting. A blade pointing straight at the camera has no screen direction at
  all; the guard picks any direction rather than normalizing zero.
- **`widen`** is how far each edge moves: `thicken` times how edge-on it is,
  times the blade's own half-width at that height. A fully edge-on blade with
  `thicken = 1` is drawn as wide as it would be face-on.

The output then uses the widened position, and `gl_Position` with it:

```glsl
    // The view matrix's rotation is orthonormal, so its transpose takes the
    // offset back to world space.
    vec3 viewOffset = vec3(across * side * widen, 0.0);
    worldPosition   = position + transpose(mat3(frame.view)) * viewOffset;
```

```glsl
    gl_Position = frame.viewProjection * vec4(worldPosition, 1.0);
```

The offset has no z: it moves the vertex across the screen, not toward or away
from the camera, so the blade's depth is unchanged and it still sorts correctly
against the ground and its neighbours.

**On the panel**, a "Look" group goes after "Wind", and this section's slider
opens it:

```cpp
        if (ImGui::CollapsingHeader("Look"))
        {
            ImGui::SliderFloat("Thicken edge-on", &settings.thicken, 0.0f, 1.0f);
        }
```

**The Edge-on view** colors each vertex by `edgeOn`, grey face-on to yellow
edge-on:

```glsl
    else if (grass.debugView == GRASS_VIEW_EDGE_ON)
    {
        debugColor = mix(vec3(0.15), vec3(1.0, 0.9, 0.1), edgeOn);
    }
```

Fly low over the field with View on **Edge-on**: yellow blades everywhere you
look across the field, grey where you look down into it. On **Shaded**, drag
"Thicken edge-on" between 0 and 1 while looking across the field at a low
angle: at 0 the far half of the field is visibly thinner, and blades blink as
the camera turns; at the default 0.6 it holds together.

---

## 4. A minimum width, as coverage

Fifty metres away a 4 cm blade is a fraction of a pixel wide. Chapter 18
section 9 described what happens then: MSAA's four samples a pixel are a grid,
and a line narrower than their spacing falls between them most of the time —
the blade breaks into dashes that crawl as anything moves. Making far blades
wider would fix the dashes and make the far field too dense, as if each blade
were a pixel wide.

The answer is to draw the blade **at least a set number of pixels wide**, and
have it cover only the **fraction** of that width it really occupies. With
alpha-to-coverage (Chapter 18 section 8), a fragment's alpha decides what
fraction of the pixel's samples it writes: a blade drawn two pixels wide with
alpha 0.25 covers, on average, half a pixel's worth of samples — what the real
blade would — but it can no longer slip between them. The sources do not say
how *Ghost of Tsushima* keeps its far blades steady; this is the standard
technique for thin geometry under MSAA, used for hair and power lines as well
as grass.

> **Jump:** Chapter 18 section 8 used alpha-to-coverage to cut a texture's
> edge: alpha came from the texture, and the geometry was the right size. Here
> it is the other way round. The geometry is deliberately drawn **too wide**,
> and alpha is computed to say how much of it is real: the real width divided
> by the drawn width. Keep in mind that it only works with samples to share out — at 1×
> there is nothing for alpha to choose between — so at 1× it is switched off.

**In `Grass.vert.glsl`**, after the widening:

```glsl
    // Section 4. A blade narrower than minimumPixels is drawn that wide, and its
    // fragments carry the fraction of it that is really blade.
    float pixelsPerMetre = abs(frame.projection[1][1]) * 0.5 * grass.viewportHeight / max(-viewPosition.z, 1e-3);
    float drawnWidth     = 2.0 * (halfWidth + widen) * pixelsPerMetre;
    float coverage       = 1.0;
    if (grass.minimumPixels > 0.0 && halfWidth > 0.0 && drawnWidth < grass.minimumPixels)
    {
        coverage = drawnWidth / grass.minimumPixels;
        widen    = 0.5 * grass.minimumPixels / pixelsPerMetre - halfWidth;
    }
```

- **`pixelsPerMetre`** at this vertex's distance: the projection's `[1][1]` is
  the cotangent of half the vertical field of view, so `viewportHeight / 2`
  times it, divided by the depth, is how many pixels a metre spans there. The
  absolute value, because the projection negates `[1][1]` for Vulkan's Y-down
  (Chapter 10 section 2). In numbers: with a 60° field of view, `[1][1]` is
  cot 30° ≈ 1.73; on a 720-pixel-tall window at 50 m, a metre is
  1.73 × 360 / 50 ≈ 12.5 pixels, so a 4 cm blade is half a pixel wide. With
  "Narrowest" at 1 it is drawn one pixel wide, with a coverage of 0.5.
- **`drawnWidth`** is the blade's width on screen, approximately: its own width
  as if face-on plus the widening. A blade narrower than `minimumPixels` gets a
  new `widen` that makes it exactly that wide, and `coverage` is the fraction of
  that width that is really blade.
- The tip's half-width is zero and its coverage stays 1: the clamp is skipped
  there, or every blade would end in a `minimumPixels`-wide stub.

`bladeData`'s fourth component carries the coverage:

```glsl
    bladeData       = vec4(blade.variation.xyz, coverage);
```

and the fragment shader writes it as alpha:

```glsl
    // Section 4: alpha is the coverage the width clamp left; alpha-to-coverage
    // turns it into samples at 2x and up, and nothing reads it at 1x.
    outColor = vec4(color * cascadeDebugColor(viewDepth), bladeData.w);
```

**The pipeline** turns alpha-to-coverage on when the scene is multisampled:

```cpp
        .alphaToCoverage = m_context.formats.samples > VK_SAMPLE_COUNT_1_BIT,   // Chapter 27 section 4
```

The blend mode stays opaque: alpha-to-coverage does not blend, it chooses
samples, so the blades still need no sorting and still write depth. Chapter 18
section 8 sharpened a texture's alpha into a crisp edge for cutouts; here the
alpha *is* the answer — a fraction of a pixel — and goes to the hardware as it
is.

**At 1× there are no samples to share**, so a widened blade would simply be
drawn too wide. `WriteFrameBuffers` sets `minimumPixels` to 0 unless the scene
has more than one sample (the "Chapter 27 section 4" line in its block), and
the shader's clamp is then off. A sample-count change runs `Setup` again
(Chapter 18 section 7), so the pipeline's flag and the parameter always agree.

The clamp needs the viewport's height, which only `Resize` knows. **This is
`Resize`**:

```cpp
// The depth pyramid is the one window-sized thing the grass owns (Chapter 26 section 9);
// the viewport's height is Chapter 27 section 4's. Resize runs after a
// vkDeviceWaitIdle, so the old pyramid can go at once.
InitializationResult GrassDemo::Resize(const SceneTargets& targets)
{
    m_viewportHeight = static_cast<float>(targets.extent.height);
    DestroyPyramid();
    return CreatePyramid(targets);
}
```

(If you did not do Chapter 26's Part 2, `Resize` is that first line and
`return InitializationResult::success();`.)

**On the panel**, after "Thicken edge-on":

```cpp
            ImGui::SliderFloat("Narrowest (px)", &settings.minimumPixels, 0.0f, 3.0f);   // multisampled only
```

**The Coverage view** shows the coverage as grey, white for whole blades:

```glsl
    if (grass.debugView == GRASS_VIEW_COVERAGE)
    {
        outColor = vec4(vec3(bladeData.w), 1.0);
        return;
    }
```

At 4× with View on **Coverage**: white near the camera, turning grey toward the
horizon, where blades are drawn a pixel wide and cover a fraction of it. The
grey is lighter than the number suggests — the composite pass encodes the view
as if it were light, so a coverage of 0.5 shows as a light grey.

On **Shaded**, walk slowly forward and watch the far field: with "Narrowest
(px)" at 0 it crawls; at 1 it is calm. At 1× the slider does nothing, by design.

---

## 5. Rounded normals

A blade is flat, and Chapter 25 shaded it flat: one normal across its width, so
a blade is one shade from edge to edge at any height. A real leaf is a little
cupped, and its two halves face slightly different ways. *Ghost of Tsushima*
tilts each blade's normals outward across its width, so the blade
shades as if it were rounded, at no cost in vertices.

**In `Grass.vert.glsl`**, a new output,

```glsl
layout(location = 5) out vec3  roundOffset;    // section 5: added to the normal after the flip
```

set from the edge's side:

```glsl
    roundOffset     = curve.right * side * grass.roundness;              // section 5
```

The left edge's vertices get `-right × roundness`, the right edge's
`+right × roundness`, and the rasterizer interpolates between them, so the
offset runs smoothly from one side to the other through zero in the middle.

**In `Grass.frag.glsl`**, the input, and the normal is now built in two steps:

```glsl
layout(location = 5) in  vec3  roundOffset;
```

```glsl
    // One triangle, two faces: light the face you are looking at - then, section 5,
    // tilt it across the blade so the blade shades as if it were rounded.
    vec3  faceNormal   = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
    vec3  normal       = normalize(faceNormal + roundOffset);
    vec3  toCamera     = normalize(frame.cameraPosition.xyz - worldPosition);
    float viewDistance = distance(frame.cameraPosition.xyz, worldPosition);
```

**The offset is added after the flip**, not before. The flip turns the face's
normal toward the camera; adding the same `right × side` to either face makes
both faces bulge the same way, out of the side being looked at — the blade looks
rounded from both sides. Adding it before the flip would round the back face
inward. `faceNormal`, the flat normal, is kept: section 7's translucency and
Chapter 17's shadow lookup want the true face. `viewDistance` is for section 6,
and `toCamera` for section 7.

**On the panel**, after "Narrowest (px)":

```cpp
            ImGui::SliderFloat("Roundness", &settings.roundness, 0.0f, 1.0f);
```

View **Normals** shows each blade shading from one color to another across its
width. On **Shaded**, with the sun to the side, every blade has a lit half and a
darker half, and the field gains a fine texture of highlights it did not have.

---

## 6. The far field

Far away, a blade is a pixel or less, and the normals of the blades sharing a
pixel point every which way. Each frame's pixel takes whichever blade won the
depth test, so as anything moves its shading jumps between them: the distance
sparkles. *Ghost of Tsushima* blends distant blades' normals toward the
terrain's normal, so the far field shades as one surface, as it does to the eye.

**In `Grass.frag.glsl`**, `Terrain.glsl` is included for `terrainNormal`:

```glsl
#include "Terrain.glsl"          // section 6: the ground's normal
```

and before anything uses the normal, right after section 5's `viewDistance`:

```glsl
    // Section 6. Far away a blade is a pixel or less: it takes the ground's normal,
    // and the dark at its root fades, so the field reads as one surface.
    float far = smoothstep(grass.farBlendStart, grass.maxDistance, viewDistance);
    normal    = normalize(mix(normal, terrainNormal(worldPosition.xz, grass.terrainShape), far));
```

`far` is 0 nearer than `farBlendStart` and 1 at `maxDistance`, where the grass
ends, with Chapter 16 section 5's `smoothstep` between. Here it turns the
normal into the ground's. Section 7 uses it twice more: the darkening toward
the root fades out with it, because a pixel of far field averages roots and
tips, and so does the highlight, because a highlight on a pixel-sized blade is
exactly the sparkle being removed.

**The ground takes the field's color.** Section 7 of Chapter 26 thins the far
field, and the bare ground between the blades shows through as brown. A real
field seen from far away does not look brown between its blades: the gaps are
too small to see. **In `Terrain.frag.glsl`**, Chapter 25's
`vec3 albedo = grass.groundColor.rgb;` becomes:

```glsl
    // Where the field thins out, the ground stands in for the blades it lost.
    float viewDistance = distance(frame.cameraPosition.xyz, worldPosition);
    float far          = smoothstep(grass.densityStart, grass.maxDistance, viewDistance);
    vec3  fieldColor   = mix(grass.rootColor.rgb, grass.tipColor.rgb, 0.7);
    vec3  albedo       = mix(grass.groundColor.rgb, fieldColor, far);
```

Where the field thins, from `densityStart` to `maxDistance`, the ground's
albedo moves from its own color to the grass's — a mix toward the tip color, as
the field reads from a distance — so the fewer blades there are, the more the
ground stands in for them, and at `maxDistance`, where the last blade ends, the
ground is the field. The edge of the grass disappears.

**On the panel**, after "Roundness":

```cpp
            ImGui::SliderFloat("Far blend from (m)", &settings.farBlendStart, 0.0f, 100.0f);
```

Look toward the horizon and slide "Far blend from (m)" between 5 and 50: at 50
the far field shimmers as the camera moves; at the default 25 it is calm, and
the place where the blades end is hard to find.

---

## 7. Light through the blade, highlights, and darker roots

Three effects the sources name for *Ghost of Tsushima*'s grass: light passing
through the blades, a highlight, and occlusion that darkens them toward the
root. How the game computes them they do not say; these are common models,
chosen so each term has one slider. The highlight comes in two models side by
side, because comparing them teaches something.

**In `Grass.frag.glsl`**, occlusion joins the color block from section 1,
faded by section 6's `far`:

```glsl
    float occlusion = mix(mix(grass.rootOcclusion, 1.0, bladeT), 1.0, far);
```

and the lighting gains it — the ambient line of Chapter 25 section 8's switch
becomes `albedo * occlusion * ambient` — and the light through the blade:

```glsl
    vec3 color   = albedo * occlusion * ambient;
    if (lightHeader.sunIndex >= 0)
    {
        vec3  L;
        vec3  irradiance = lightIrradiance(lights[lightHeader.sunIndex], worldPosition, L);
        float shadow     = sunShadow(worldPosition, faceNormal, viewDepth);

        float diffuse = max(dot(normal, L), 0.0);

        // Light through the blade: the sun on the face we cannot see, strongest
        // when we look toward the sun.
        float through = max(dot(-faceNormal, L), 0.0)
                      * (0.25 + 0.75 * pow(max(dot(-toCamera, L), 0.0), 4.0));
```

**Occlusion.** Down among the stems, a blade is surrounded by other blades that
block the sky and the sun. `rootOcclusion` is the fraction of light that reaches
the root; it rises to 1 at the tip, and multiplies the ambient and the sun's
diffuse light alike. It is the single biggest step from "green strips" toward
"grass": the field gets depth.

**Light through the blade.** A blade is thin enough that sunlight falling on one
face lights the other. The term is the sun's cosine on the face the camera does
*not* see — `-faceNormal` — so it is zero when the sun is on your side of the
blade and largest when it is behind it. It is weighted toward looking into the
sun, `pow(max(dot(-toCamera, L), 0), 4)`: light comes through most strongly in
the direction it was already travelling, which is why a field glows when you
look toward a low sun and not when the sun is behind you. A quarter of it is
always there, so a back-lit blade seen from the side still has some. It uses
the **flat** face normal, because the blade's thinness, not its rounding, is
what the light passes through. And it is multiplied by the shadow, because a
blade in shadow has no sun to pass through it.

### The highlight, in two models

A blade's waxy skin reflects a little of the sun the way a mirror does: a
highlight. Chapter 15 section 9 built two highlight models and a switch between
them; the grass uses both, with a switch of its own on the panel, and GGX by
default. Both are measured with the **half vector** H, halfway between the
directions to the light, L, and to the camera, V, against the blade's normal
N — the rounded one of section 5 — and both are multiplied, as every BRDF is,
by N·L and the light's irradiance. As a reminder, the two lobes are:

$$
f_{\text{Blinn-Phong}} = F \, \frac{n + 8}{8\pi} \, (N \cdot H)^n,
\qquad
f_{\text{GGX}} = \frac{F \, D \, G}{4\,(N \cdot L)(N \cdot V)}
$$

Chapter 15 section 9 derived both, with worked numbers: why the factor
(n + 8)/8π keeps the total light the same as n narrows the lobe, and the match
n ≈ 2/α² − 2 between the two widths. `PreviewSurface.glsl`'s `blinnPhongLobe`,
`ggxDistribution`, `smithGeometry`, and `schlickFresnel` apply them, and the
grass includes the file and calls them. Here Fresnel's F0 is the panel's
"Specular", and α = roughness², from the panel's "Roughness". For a blade,
roughness is how blurred the sun's reflection in its waxy skin is: near 0, a
pinpoint glint; at 1, a dull sheen across the whole lit side. **One slider
drives both**: `blinnPhongLobe` derives n from the same roughness, so the
switch changes the shape of the lobe but not its width. The default roughness,
0.43, is α = 0.185 and n ≈ 56: a medium-tight highlight.

**Two switches, kept apart.** Chapter 15's switch is `FrameData`'s `brdf`,
which the USD viewer's panel sets and every mesh shader reads through
`evaluatePreviewSurface`. The grass leaves it at 0, so the stones and the ball
are always GGX. The blades have their own shader, and their own switch:
`highlightModel` in `GrassParameters`, which only they read.

**In `Grass.frag.glsl`**, `PreviewSurface.glsl` is included after
`Shadows.glsl`. It also defines `PI`, so the shader's own `const float PI`
line goes:

```glsl
#include "PreviewSurface.glsl"   // section 7: Chapter 15's specular terms, and PI
```

and the highlight follows the light through the blade:

```glsl
        // The highlight: Chapter 15's specular term, GGX or normalized Blinn-Phong, at the
        // rounded normal. One roughness drives both; every invocation takes the same branch.
        vec3  halfway   = normalize(L + toCamera);
        float NdotH     = max(dot(normal, halfway), 0.0);
        float roughness = max(grass.roughness, MIN_ROUGHNESS);
        float alpha     = roughness * roughness;
        vec3  fresnel   = schlickFresnel(vec3(grass.specular), vec3(1.0), max(dot(toCamera, halfway), 0.0));
        vec3  highlight;
        if (grass.highlightModel == GRASS_HIGHLIGHT_GGX)
        {
            float NdotL = max(diffuse, 1e-4);
            float NdotV = max(dot(normal, toCamera), 1e-4);
            highlight = fresnel * ggxDistribution(NdotH, alpha) * smithGeometry(NdotV, NdotL, alpha)
                      / (4.0 * NdotL * NdotV);
        }
        else
        {
            highlight = fresnel * blinnPhongLobe(NdotH, alpha);   // n = 2 / alpha^2 - 2: as wide as GGX's
        }
        highlight *= 1.0 - far;   // section 6: a pixel-sized blade's highlight is sparkle
```

- **`fresnel`** is Chapter 15's `schlickFresnel`, from `specular` head-on to 1
  at grazing angles.
- **The GGX branch** keeps N·L and N·V away from zero, as Chapter 15's
  `evaluatePreviewSurface` does; Smith's G falls to zero with them, so the
  quotient stays finite.
- **The Blinn-Phong branch** is Chapter 15's `blinnPhongLobe`, which works out
  n from α by the match above, and keeps it above 0 because GLSL leaves
  `pow(0, 0)` undefined and roughness 1 gives n = 0.
- **The switch is a uniform branch.** `highlightModel` comes from the uniform
  buffer, so every invocation of the draw reads the same value and takes the
  same side of the `if`. A GPU runs invocations in groups, in step, and a
  branch costs extra only when a group disagrees about it; here no group ever
  does, so the switch costs one comparison.
- **`1.0 - far`** fades the highlight out in the distance (section 6).

The sum closes the block:

```glsl
        color += irradiance * shadow
               * (albedo * occlusion / PI * (diffuse + grass.translucency * through) + highlight * diffuse);
    }
```

It is still Chapter 16's units: everything is multiplied by the sun's
irradiance and the shadow, and the Lambert terms by `albedo / π`. The highlight
is multiplied by `diffuse`, which is N·L: the cosine every BRDF is multiplied
by, and the reason a highlight cannot appear on a face the sun does not reach.
The default `specular` is low, 0.08: blades are waxy, not wet, and a strong
highlight on thousands of blades reads as noise. Translucency adds light that a
strictly energy-conserving model would take from the front face; on grass,
nobody can tell, and the slider exists to turn it down.

**On the panel**, the rest of the "Look" group, after "Far blend from (m)":

```cpp
            ImGui::SliderFloat("Translucency", &settings.translucency, 0.0f, 2.0f);
            ImGui::Combo("Highlight", &settings.highlightModel, "GGX\0Blinn-Phong\0");
            ImGui::SliderFloat("Roughness", &settings.roughness, 0.05f, 1.0f);
            ImGui::SliderFloat("Specular", &settings.specular, 0.0f, 1.0f);
            ImGui::SliderFloat("Root light", &settings.rootOcclusion, 0.0f, 1.0f);
```

### What to look for

**The default view**, with the sun behind you over your left shoulder (Chapter
25 section 3). Both models draw a pale streak along each lit blade, where the
rounding turns the normal toward H: a line, not a spot. GGX's streaks are a
little broader and softer at their edges — its distribution has a long tail,
and Blinn-Phong's falls off faster away from the peak — and switching between
them barely changes the field, which is what matching their widths was for.

**Facing a low sun.** Drop the sun's elevation to about 12° and turn round to
face it. Now the two differ. Under GGX, blades seen nearly edge-on into the
light flare white: its 1 / (N·V) and its Fresnel term both grow at grazing
angles, which is the silver sheen a real field has when you look toward the
sun. In the middle distance, where blades are a pixel wide, the flare breaks
into glints; raise "Roughness" toward 0.65 and they soften into a haze.
Blinn-Phong has the Fresnel term but no 1 / (N·V), and the same view stays
green, with a faint sheen.

In that same view the blades glow yellow-green against the darker ground: the
light through them. With "Translucency" at 0 it is flat and dark. At the
default 35° the glow is there but faint, because looking level puts the sun
well above the line of sight, where the `pow` term is small. With "Root light"
at 1 the field looks like painted cardboard.

---

## 8. Grass shadows from an impostor

The grass receives shadows — the stones', the ball's — but casts none, and a real
field is darker underneath than on top: the blades shade the ground and each
other's lower halves. Drawing the blades into Chapter 17's shadow map would cost
four more passes over a hundred thousand blades a frame, each blade thinner than
a shadow-map texel, so it would mostly alias anyway.

A summary of the *Ghost of Tsushima* talk describes what the game does
instead: it draws
the **terrain** into the shadow map, **raised to the grass's height**, writing
depth in a **dithered** pattern, so that the shadow filter averages the pattern
into a partial shadow; screen-space shadows then add the fine detail. The first
half is built here.

> **Jump:** a shadow map stores one depth per texel, so on its own it can only
> say "in shadow" or "lit". What makes partial shadow possible is Chapter 17
> section 8's filter, which averages several texels around each lookup. Keep in
> mind that the impostor does not cast a *light* shadow; it casts a full shadow
> through some texels and none through the rest, and the filter turns the
> pattern into the fraction you see.

The idea, concretely:

- **A sheet of ground, lifted.** Chapter 25's grid, drawn into each cascade at
  the terrain's height plus a fraction of the mean blade height: a surface
  floating in the grass. The ground below it is in its shadow, and so are the
  parts of blades below it; blade tips above it are not.
- **Full of holes.** Only some of the sheet writes depth. Where it does not, the
  sun gets through. Chapter 17's filter averages several texels per lookup, so a
  sheet that writes 60% of its texels casts, on average, 60% shadow — light
  dappled by grass rather than a solid roof.
- **As full as the field.** The fraction that casts is `impostorDensity` times
  Chapter 26's density at that distance: where the field thins, so does its
  shadow, and past `maxDistance` there is none.

### The shaders

**This is `Shaders/Grass/GrassShadow.vert.glsl`:**

```glsl
// Shaders/Grass/GrassShadow.vert.glsl - Chapter 27 section 8. The grass's stand-in in the shadow
// map: the ground's grid, lifted part of the way up the blades, seen from a cascade's light.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "GrassTypes.h"
#include "Terrain.glsl"

layout(std140, set = 0, binding = 3) uniform ShadowBlock { ShadowData shadowData; };   // Chapter 17's
layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };
layout(push_constant) uniform GrassPushBlock { GrassPush push; };

layout(location = 0) out vec3 worldPosition;
layout(location = 1) flat out uint cascade;

// Terrain.vert.glsl's two triangles per cell. Culling is off in the shadow pass,
// so their winding does not matter here.
const vec2 corners[6] = vec2[](
    vec2(0.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 0.0),
    vec2(1.0, 0.0), vec2(0.0, 1.0), vec2(1.0, 1.0));

void main()
{
    uint cellsPerSide = uint(push.terrainGrid.w);
    uint cell         = uint(gl_VertexIndex) / 6u;
    vec2 cellXZ       = vec2(cell % cellsPerSide, cell / cellsPerSide);
    vec2 xz           = push.terrainGrid.xy + (cellXZ + corners[gl_VertexIndex % 6]) * push.terrainGrid.z;

    float meanHeight = 0.5 * (grass.shapeMin.x + grass.shapeMax.x);
    float lift       = grass.impostorHeight * meanHeight;

    worldPosition = vec3(xz.x, terrainHeight(xz, grass.terrainShape) + lift, xz.y);
    cascade       = push.cascade;
    gl_Position   = shadowData.cascadeViewProjection[push.cascade] * vec4(worldPosition, 1.0);
}
```

It is `Terrain.vert.glsl`'s grid with two changes. The height is lifted by
`impostorHeight` times the mean blade height, and the position goes through the
cascade's matrix from Chapter 17's `ShadowData` instead of the camera's, the
way Chapter 17's `ShadowDepth.vert.glsl` does — the cascade comes from the push
constant, through `GrassPush`'s new `cascade` field. The grid's corners appear a
second time here rather than in a shared include: it is the second use, and the
rule Chapter 09 applied to `srgbToLinear` holds here too — write a pattern twice
before generalizing it.

**This is `Shaders/Grass/GrassShadow.frag.glsl`:**

```glsl
// Shaders/Grass/GrassShadow.frag.glsl - Chapter 27 section 8. Writes depth only where an ordered
// dither says so: the fraction that casts is the fraction of light the grass would stop.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "GrassTypes.h"

layout(std140, set = 0, binding = 3) uniform ShadowBlock { ShadowData shadowData; };
layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };

layout(location = 0) in vec3 worldPosition;
layout(location = 1) flat in uint cascade;

// A 4 x 4 Bayer matrix: each threshold once, ordered so that the first n of them
// are spread as evenly as n of 16 cells can be.
const float BAYER[16] = float[](
     0.0,  8.0,  2.0, 10.0,
    12.0,  4.0, 14.0,  6.0,
     3.0, 11.0,  1.0,  9.0,
    15.0,  7.0, 13.0,  5.0);

void main()
{
    // As full as the field is here: Chapter 26's density by distance, the same
    // expression the generation pass thins the blades with.
    float distanceToCamera = distance(worldPosition, grass.cullPosition.xyz);
    float along   = clamp((distanceToCamera - grass.densityStart) / (grass.maxDistance - grass.densityStart), 0.0, 1.0);
    float density = distanceToCamera > grass.maxDistance ? 0.0 : mix(1.0, grass.farDensity, along);
    float cover   = grass.impostorDensity * density;

    // Cells one shadow-map texel wide, fixed to the world rather than to the map,
    // so the pattern does not crawl when a cascade moves with the camera.
    ivec2 cell  = ivec2(floor(worldPosition.xz / shadowData.cascadeTexelSize[cascade]));
    uint  index = uint(cell.x & 3) + 4u * uint(cell.y & 3);
    if ((BAYER[index] + 0.5) / 16.0 > cover)
    {
        discard;   // Chapter 15 enabled what this needs: shaderDemoteToHelperInvocation
    }
}
```

- **The density** is Chapter 26 section 7's expression, from the same
  parameters, so the shadow thins exactly as the blades do.
- **The dither is ordered**, a 4 × 4 Bayer matrix. Each of the sixteen cells has a
  different threshold, arranged so that any number of them that pass are spread
  as evenly as possible; the cells whose threshold is below the coverage write
  depth, the rest `discard`. At a coverage of 0.25, the four cells with
  thresholds 0 to 3 pass, and they are one in each 2 × 2 corner of the
  4 × 4 block. `& 3` keeps a cell's low two bits, which tiles the 4 × 4 matrix
  across the world, negative cells included. White noise would do the same on average and look
  worse: its clusters and gaps survive the shadow filter as blotches.
- **The cells are fixed to the world**, one shadow-map texel across in each
  cascade (`cascadeTexelSize`, in Chapter 17 section 2's `ShadowData`).
  Chapter 17 section 12 keeps the cascades from shimmering by moving them only
  in whole texels; a pattern tied to the world moves with the ground under that
  snapping, and stays still on screen. A pattern tied to the shadow map's own
  pixels would crawl across the ground every time a cascade snapped.
- **`discard`** in a shader needs `shaderDemoteToHelperInvocation`, which Chapter
  15 section 11 enabled for cutouts (and Chapter 17's cutout casters use). It
  writes no color — the pass has no color attachment — only depth, or nothing.

### The pipeline and the callback

**In `CreatePipelines`**, beside the grass's other pipelines:

```cpp
    // Chapter 27 section 8: depth only, into Chapter 17's shadow map - its format, one sample
    // whatever the scene uses, and the depth bias the shadow pass sets while recording.
    const VkDynamicState biasStates[] = { VK_DYNAMIC_STATE_DEPTH_BIAS_ENABLE, VK_DYNAMIC_STATE_DEPTH_BIAS };
    const GraphicsPipelineDesc impostor{
        .vertexShader   = "Grass/GrassShadow.vert.spv",
        .fragmentShader = "Grass/GrassShadow.frag.spv",
        .depthFormat    = m_sceneRenderer.Shadows().DepthFormat(),
        .depthTest      = true,
        .depthWrite     = true,
        .depthCompare   = VK_COMPARE_OP_LESS,
        .cullMode       = VK_CULL_MODE_NONE,
        .dynamicStates  = biasStates,
        .layout         = m_pipelineLayout,
    };
```

```cpp
    m_impostorPipeline = createGraphicsPipeline(device, cache, impostor);
```

and `m_impostorPipeline` joins the null check after it. It is everything Chapter
17 section 4 asks of a caster pipeline: the shadow map's format from
`Shadows().DepthFormat()`, one sample whatever the scene uses, no color
attachments, culling off, and the two depth-bias states dynamic, because Chapter
17's pass sets them for each cascade before calling the casters. Its layout is
the grass's own: set 0, set 1, and `GrassPush`.

Chapter 17 section 5 calls `extraCasters` inside each cascade's rendering scope,
after the scene's casters. **This is `RecordImpostor`**, the grass's caster:

```cpp
// Chapter 27 section 8: called by Chapter 17's shadow pass inside each cascade's rendering
// scope, with the viewport, scissor, and depth bias already set.
void GrassDemo::RecordImpostor(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t cascade)
{
    // The pass bound set 0 through its own layout, whose push range is not ours, so
    // set 0 is bound again through the grass's (Chapter 17 section 5), then set 1.
    m_sceneRenderer.BindFrameSet(commandBuffer, m_pipelineLayout, frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipelineLayout,
                            1, 1, &m_grassSets[frameIndex], 0, nullptr);

    // A square of coarse cells reaching maxDistance from the culling camera in every
    // direction, snapped to whole cells like the ground so the dither does not swim.
    const uint32_t cells   = static_cast<uint32_t>(std::ceil(2.0f * m_settings.maxDistance / IMPOSTOR_CELL)) + 2;
    const float    side    = IMPOSTOR_CELL * static_cast<float>(cells);
    const float    cornerX = std::floor(m_frozenPosition.x / IMPOSTOR_CELL) * IMPOSTOR_CELL - 0.5f * side;
    const float    cornerZ = std::floor(m_frozenPosition.z / IMPOSTOR_CELL) * IMPOSTOR_CELL - 0.5f * side;
    const GrassPush push{
        .terrainGrid = { cornerX, cornerZ, IMPOSTOR_CELL, static_cast<float>(cells) },
        .cascade     = cascade,
    };
    vkCmdPushConstants(commandBuffer, m_pipelineLayout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_impostorPipeline);
    vkCmdDraw(commandBuffer, 6 * cells * cells, 1, 0, 0);
}
```

- **Set 0 is bound again.** The shadow pass bound it through its caster layout,
  whose push-constant range is `ShadowDrawData`'s; the grass's layout has a
  different range, and two pipeline layouts are compatible for a set only if
  their push-constant ranges are identical too (Chapter 17 section 4). So the
  set bound by the pass is not usable with this pipeline, and `BindFrameSet`
  binds it again through the grass's layout. Then set 1.
- **The grid reaches `maxDistance`** around the culling camera in 1 m cells — four
  times coarser than the ground's, since nobody sees the sheet, only its shadow —
  snapped to whole cells like the ground, for the same reason.
- **No new barriers.** The impostor reads the grass's parameters (host-written
  before the submission) and Chapter 17's `ShadowData`, and writes the shadow map
  inside the pass, whose two barriers Chapter 17 section 5 already provides.

**In `Record`**, the callback is passed to `RecordShadows`:

```cpp
    // Chapter 27 section 8: the grass's stand-in joins the scene's casters in every cascade.
    ShadowCasterCallback impostor;
    if (m_settings.grassShadows)
    {
        impostor = [this, frameIndex](VkCommandBuffer cb, uint32_t cascade) { RecordImpostor(cb, frameIndex, cascade); };
    }
    m_sceneRenderer.RecordShadows(commandBuffer, frameIndex, m_camera, view, aspect,
                                  m_sceneRenderer.SunDirection(frameIndex), m_shadowSettings, impostor);
```

An empty `std::function` is how "no extra casters" is said (Chapter 17 section
5 checks it), so the panel's checkbox simply leaves it empty. The lambda captures
`this` and the frame index; `RecordShadows` calls it before returning, so
nothing it refers to can go away first.

**In `Teardown`**, the pipeline goes with the others:

```cpp
    vkDestroyPipeline(device, m_impostorPipeline, nullptr);
```

```cpp
    m_impostorPipeline = VK_NULL_HANDLE;
```

**On the panel**, a group of its own after "Color":

```cpp
        if (ImGui::CollapsingHeader("Shadows from the grass"))
        {
            ImGui::Checkbox("Impostor", &settings.grassShadows);
            ImGui::SliderFloat("Impostor height", &settings.impostorHeight, 0.0f, 1.5f);
            ImGui::SliderFloat("Impostor density", &settings.impostorDensity, 0.0f, 1.0f);
        }
```

Look down at the field near your feet and toggle "Impostor": with it on, the
ground between the blades is darker and dappled, and the lower part of every
blade is in partial shade; the stones' and the ball's shadows still cut sharply
across it. "Impostor height" moves the sheet up and down the blades: at 0 it
lies on the ground and shades only the ground; at 1.5 it floats above the tallest
blades and shades everything. Chapter 17's cascade tint shows the impostor's
shadow in every cascade, thinning with the field.

What it does not do is let a blade shadow its neighbour in detail — that is
screen-space shadows' job in the game, and not built here. The sheet's height
also makes a faint line on the blades: below it they are partly shadowed, above
it not. Root occlusion (section 7) hides most of it. And the dither's sixteen
levels can show: past `densityStart` the coverage falls with distance, so it
steps from one level to the next at fixed distances from the camera, and on bare
ground seen from above the steps are faint rings around you. Chapter 17's filter
radius at 2 softens them.

---

## 9. A ball the blades get out of the way of

The last effect makes the field respond. A ball rolls through the grass, and the
blades around it bend away, the same way the wind bends them. The sources do
not say how *Ghost of Tsushima* lets characters push through its grass; this is
the simplest version, one sphere passed to the vertex shader.

**This is `applyInteractor`**, in `Grass.vert.glsl` after `applyWind`:

```glsl
// Section 9. Blades near the ball are pushed away from it, the way the wind pushes
// them: control points out, then the length restored.
void applyInteractor(inout BladeCurve curve, GrassBlade blade)
{
    float radius = grass.interactor.w;
    if (radius <= 0.0) { return; }

    vec2  away = curve.p0.xz - grass.interactor.xz;
    float gap  = length(away);
    float push = clamp(1.0 - gap / (radius + blade.shape.x), 0.0, 1.0);
    if (push <= 0.0) { return; }

    vec3  outward     = vec3(away.x, 0.0, away.y) / max(gap, 1e-4);
    float bladeLength = distance(curve.p3, curve.p0);
    curve.p2 += outward * blade.shape.x * push * 0.5;
    curve.p3 += outward * blade.shape.x * push * 1.5;
    curve.p3  = curve.p0 + normalize(curve.p3 - curve.p0) * bladeLength;
}
```

and it runs after the wind, so the ball's push adds to the gust's lean:

```glsl
    applyInteractor(curve, blade);    // section 9
```

- **How hard** depends on how far the root is from the ball's centre on the
  ground: fully pushed at the centre, not at all once the root is the ball's
  radius plus the blade's height away. A taller blade can reach the ball from
  further away, so it is pushed from further away.
- **Which way** is straight out from the ball, horizontally.
- **Then the length is restored**, as the wind's lean was: the blade leans out
  of the way rather than stretching. `P3` moves three times as far as `P2`, so
  the blade bends over at its top instead of tilting stiffly from its root.

The culling sphere already allows for it: section 2 doubled it for "the wind and
the ball".

### The ball

The ball needs to sit on the ground, and this is the one place the CPU must know
the ground's height. **This is `terrainHeight`**, at file scope above the
namespace block, the CPU's copy of `Terrain.glsl`'s:

```cpp
// File scope, above the namespace block. Terrain.glsl's terrainHeight, on the CPU,
// for the one thing the CPU has to stand on the ground: Chapter 27 section 9's ball. Change
// one and you must change the other.
static float terrainHeight(glm::vec2 xz, float amplitude, float wavelength)
{
    const glm::vec2 p = xz * (6.2831853f / wavelength);
    const float     h = std::sin(p.x) * std::cos(0.8f * p.y)
                      + 0.50f * std::sin(1.7f * p.x + 1.3f * p.y + 1.0f)
                      + 0.25f * std::sin(-2.9f * p.x + 3.1f * p.y + 2.0f);
    return amplitude * h / 1.75f;
}
```

It is the same expression as the shader's, line for line. Two copies of one
function must be changed together; if this one ever drifts, the ball floats or
sinks while the grass stays put. Chapter 25 avoided this for the stones by
making them tall enough not to care; a ball cannot do that.

**This is `CreateBall`**, called from `Setup` after `CreateStones`:

```cpp
// Chapter 27 section 9: a ball for the blades to get out of the way of. Chapter 11's sphere,
// one metre across, scaled to the panel's radius every frame.
void GrassDemo::CreateBall()
{
    const uint32_t material = m_sceneRenderer.AddMaterial(scene::Material{
        .name = "Ball", .baseColor = { 0.55f, 0.10f, 0.05f, 1.0f }, .roughness = 0.4f });
    const uint32_t mesh = m_sceneRenderer.AddMesh(scene::makeUvSphere(1.0f));
    m_ball = scene::DrawItem{ .world = glm::mat4(1.0f), .mesh = mesh, .submesh = 0, .material = material };
}
```

```cpp
    CreateBall();                                                        // Chapter 27 section 9
```

A unit sphere from Chapter 11 section 4, in a red with a little gloss, drawn by
the scene renderer like the stones. Its transform is set every frame.

**In `Update`**, after the time is kept:

```cpp
    // Chapter 27 section 9: the ball rolls round a circle in front of where the camera starts,
    // sitting on the ground - the one place the CPU needs the ground's height.
    const float     angle  = BALL_ORBIT_SPEED * m_time;
    const glm::vec2 ballXZ = glm::vec2(0.0f, 3.5f) + BALL_ORBIT_RADIUS * glm::vec2(std::cos(angle), std::sin(angle));
    const float     radius = m_settings.interactorRadius;
    m_ballCenter = glm::vec3(ballXZ.x, terrainHeight(ballXZ, m_settings.terrainAmplitude, m_settings.terrainWavelength) + radius,
                             ballXZ.y);
    m_ball.world = glm::translate(glm::mat4(1.0f), m_ballCenter) * glm::scale(glm::mat4(1.0f), glm::vec3(radius));
```

The ball circles a point 3.5 m in front of the origin, 2 m out, a full turn
every sixteen seconds — in view of the starting camera, clear of the stones.
Its centre is the ground's height plus its radius, so it sits on the ground on
any hill. This is CPU state, computed in `Update` like the camera's.

**In `Record`**, the stones' list becomes the stones plus the ball:

```cpp
    // The stones, and Chapter 27 section 9's ball when it is on: drawn and casting.
    std::vector<scene::DrawItem> draws = m_stones;
    if (m_settings.interactor) { draws.push_back(m_ball); }
    m_sceneRenderer.PrepareDraws(frameIndex, draws, draws);
```

so the ball is drawn and casts a shadow, and `WriteFrameBuffers` passes its
centre and radius as `interactor` (a radius of 0 when the panel turns it off,
which `applyInteractor` checks first). The two constants are in the header:

```cpp
    // Chapter 27 section 9: the ball rolls round this circle.
    static constexpr float    BALL_ORBIT_RADIUS = 2.0f;    // metres
    static constexpr float    BALL_ORBIT_SPEED  = 0.4f;    // radians per second
```

**And in `Teardown`**, beside clearing the stones, the ball's `DrawItem` is
reset for the same reason — it names a mesh the scene renderer is about to
release:

```cpp
    m_ball = {};
```

**On the panel**, a last group after "Shadows from the grass":

```cpp
        if (ImGui::CollapsingHeader("Interaction"))
        {
            ImGui::Checkbox("Ball", &settings.interactor);
            ImGui::SliderFloat("Ball radius (m)", &settings.interactorRadius, 0.1f, 1.5f);
        }
```

A red ball rolls in a circle in front of you, and the grass parts around it: a
ring of blades leaning outward, closing up again behind it as it passes. Turn the
wind up and the push adds to the gusts; make the ball bigger and the ring
widens.

---

## If something goes wrong

- **The field is striped or banded in the Clumps view.** The clump hash and the
  blade hash coincide; the clump's must mix in a different constant.
- **Blades stretch in the wind instead of leaning.** The tip is not pulled back
  to the blade's length after moving.
- **The whole field sways in step.** The sway's phase is missing the blade's
  random number.
- **Blades at grazing angles twist into bow ties.** `across` is not flipped to
  agree with the blade's right edge.
- **At 1× the far field is too dense.** The minimum width is on without samples
  to turn coverage into: `minimumPixels` must be 0 at 1×.
- **At 4× the far field is still dashed.** Alpha-to-coverage is not enabled on the
  blade pipeline, or the fragment shader's alpha is not the coverage.
- **One face of every blade is dark when rounded.** The rounding offset is added
  before the flip instead of after it.
- **No grass shadow, or a solid one.** The impostor's density is 0 (or the
  checkbox is off) or 1; or the dither's cells are not one texel across, so the
  filter sees whole blocks. A validation error naming
  `VUID-VkShaderModuleCreateInfo-pCode-08740` means Chapter 15's
  `shaderDemoteToHelperInvocation` is not enabled.
- **A validation error about incompatible descriptor sets in the shadow pass.**
  `RecordImpostor` must bind set 0 again through the grass's layout.
- **The ball floats or sinks.** The CPU's `terrainHeight` has drifted from
  `Terrain.glsl`'s.

---

## Exit check

- [ ] View **Clumps**: tufts of one color, a metre or two across, in a Voronoi
      pattern; on **Shaded**, tufts of different heights, facings, and dryness.
- [ ] View **Wind**: blotches of pink gust and blue lull drifting across the field
      in the wind's direction; on **Shaded**, waves of leaning grass, and every
      blade swaying on its own.
- [ ] View **Edge-on**: blades seen side-on are yellow; "Thicken edge-on" at 0
      makes the field visibly thinner at grazing angles.
- [ ] At 4×, View **Coverage** turns grey toward the horizon, and the far field does
      not crawl when the camera moves slowly; at 1× "Narrowest (px)" changes
      nothing.
- [ ] With the sun at about 12° and in front of you, the grass glows where light
      comes through; "Translucency" at 0 removes the glow.
- [ ] In the default view, "Highlight" switches between GGX and Blinn-Phong
      with little change: a pale streak along each lit blade either way. Facing
      the low sun, GGX flares white along edge-on blades and Blinn-Phong does
      not.
- [ ] "Impostor" on darkens and dapples the ground under the grass and the lower
      blades; off, the ground is evenly lit outside the stones' and the ball's
      shadows.
- [ ] The ball rolls through the field on the ground, and the blades around it
      lean away and recover behind it; it casts a shadow.
- [ ] Changing the sample count, switching demos, and resizing the window all
      work, with no validation messages, synchronization validation on.

---

## Where to go from here

Two things the game does that these chapters do not:

- **Short grass folds its blade in two**: fifteen vertices are more
  than a short blade needs, so the spare vertices make a second blade from the
  same instance. It doubles the density of short grass for the same instance
  count.
- **Screen-space shadows** add the fine, blade-on-blade shadowing that the
  impostor cannot.

And one thing every chapter since Chapter 18 has pointed at: **temporal
anti-aliasing**. MSAA and the coverage trick of section 4 keep blades from
breaking up within a frame; the shimmer of a hundred thousand moving blades
across frames is TAA's job.

One more is left open for you, as Chapter 21 leaves its emitters: **the
blade's color as a ramp.** Today a blade's albedo comes from three colors and
two mixes. Chapter 25's `rootColor` runs up the blade to `tipColor`. Section 1
lets the tip drift toward `dryColor` by the clump's dryness. The blade's random
number brightens or darkens the result. An artist would usually paint this as a
gradient map instead: a small image whose horizontal axis is how far up the
blade (`bladeT`) and whose vertical axis is a per-blade choice. That choice
could be the clump's dryness, a field-wide noise for patches of a different
grass, or the blade's random number picking one of a few painted rows. The
shader's color becomes one texture read at (`bladeT`, row), and the three
colors and both mixes go.

The same image carries more than color:
- **Roughness in the alpha.** Every blade shares one roughness today (section
  7). With a ramp, a dry tip can be rougher than a fresh base.
- **Translucency** could be a second ramp, or a second image.

In a format such as `R8G8B8A8_SRGB`, only the color is sRGB-encoded and the
alpha is stored linearly, which is what a roughness wants. Linear filtering
across the colors gives the blend the two `mix` calls give now. Use
`CLAMP_TO_EDGE`, so that the tip's color does not bleed into the root's when
`bladeT` reaches 1.

Where it goes is the same as for Chapter 21's color ramp:
- **The image:** a combined image sampler at a new binding in the grass's set
  1, beside binding 1's `GrassParameters`. Build it from keys edited in the
  panel and upload it with Chapter 08's `uploadToImage`. A live edit has the
  same waiting rule as there: the device must be idle, or each frame in flight
  needs its own image.
- **Or no image:** for a handful of keys, an array of them in
  `GrassParameters` is simpler. The shader walks the keys, and nothing new is
  bound. The image earns its keep once someone paints the ramp rather than
  typing it.

Next, Chapter 28 takes section 1's Voronoi cells and section 2's gradient noise
into three dimensions, for clouds.

---

## Sources

- Eric Wohllaib, "Procedural Grass in *Ghost of Tsushima*", GDC 2021, and the
  summaries and implementations listed in Chapter 25. Its table, "Where each
  technique comes from", says which of this chapter's techniques are the game's,
  which come from one summary only, and which are this tutorial's.
- Bill Rockenbeck, "Blowing from the West: Simulating Wind in *Ghost of
  Tsushima*", GDC 2021 — the game's wind simulation, which supplies the grass's
  wind direction.
- Jasmin Patry, "Real-Time Samurai Cinema: Lighting, Atmosphere, and Tonemapping
  in *Ghost of Tsushima*", SIGGRAPH 2021 Advances in Real-Time Rendering — the
  game's lighting, for context.
- Ken Perlin, "Improving Noise", SIGGRAPH 2002 — gradient noise and the quintic
  fade curve.
- Steven Worley, "A Cellular Texture Basis Function", SIGGRAPH 1996 — Voronoi
  cells from one jittered point per grid square.
- Cain Rademan, *Unity-Grass*, and 2Retr0, *GodotGrass* (GitHub) — open
  implementations of the clumps, wind, thickening, and rounding described in the
  talk, read to check how the pieces fit.

---

## Appendix: complete listings

For reference: the files this chapter changed a few lines at a time, as it
leaves them. Read the sections for why; use these to check your files, or when
your build disagrees with the text.

**`Shaders/Grass/GrassTypes.h`:**

```c
/* Shaders/Grass/GrassTypes.h - the grass demo's C++/GLSL twins. GLSL includes it as
   "GrassTypes.h", C++ as "Grass/GrassTypes.h". */
#ifndef PF_GRASS_TYPES_H
#define PF_GRASS_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::grass {
    using shared::mat4;
    using shared::vec4;
    using shared::uint;
#endif

/* What the fragment shaders draw instead of the lit color (GrassParameters::debugView). */
#define GRASS_VIEW_SHADED   0u
#define GRASS_VIEW_STRIP    1u   /* segments as bands, left edge red, right edge green */
#define GRASS_VIEW_NORMALS  2u   /* the normal the light sees, as a color */
#define GRASS_VIEW_LOD      3u   /* Chapter 26: LOD 0 green, morphing yellow, LOD 1 blue */
#define GRASS_VIEW_TILES    4u   /* Chapter 26: a color per tile */
#define GRASS_VIEW_CLUMPS   5u   /* Chapter 27: a color per clump */
#define GRASS_VIEW_WIND     6u   /* Chapter 27: gust strength, blue calm to red */
#define GRASS_VIEW_EDGE_ON  7u   /* Chapter 27: how edge-on the blade is, black to yellow */
#define GRASS_VIEW_COVERAGE 8u   /* Chapter 27: the coverage alpha-to-coverage gets */

/* Chapter 27 section 7: which highlight the blades get (GrassParameters::highlightModel). */
#define GRASS_HIGHLIGHT_GGX         0u   /* Chapter 15's microfacet lobe */
#define GRASS_HIGHLIGHT_BLINN_PHONG 1u   /* the older normalized Blinn-Phong lobe, to compare */

/* One blade. std430, set 1 binding 0, read by the vertex shader with gl_InstanceIndex. */
struct GrassBlade
{
    vec4 rootAndFacing;   /* xyz: the root on the ground, world metres (Chapter 26: the generation
                             pass fills y); w: facing, radians about +Y */
    vec4 shape;           /* x height (m), y width at the root (m), z tilt 0..1, w bend 0..1 */
    vec4 variation;       /* Chapter 27. x: the blade's own random number, 0..1; y: gust strength
                             where it stands, 0..1; z: its clump's dryness, 0..1; w: its clump's
                             random number, 0..1 */
};

/* Everything the panel edits. std140, set 1 binding 1, one buffer per frame in flight. */
struct GrassParameters
{
    vec4 rootColor;       /* linear rgb: the panel's sRGB, converted on the CPU */
    vec4 tipColor;        /* linear rgb */
    vec4 groundColor;     /* linear rgb */
    vec4 terrainShape;    /* x amplitude (m), y wavelength (m), zw unused */
    uint debugView;       /* GRASS_VIEW_* */
    uint padding0;
    uint padding1;
    uint padding2;
    /* Chapter 26: generation, culling, and LOD. */
    vec4  frustumPlanes[6]; /* the culling camera's planes: xyz inward unit normal, w distance */
    vec4  cullPosition;     /* xyz: the culling camera's position; w unused */
    vec4  shapeMin;         /* the smallest height, width, tilt, and bend a blade is given */
    vec4  shapeMax;         /* and the largest */
    float tileSize;         /* metres */
    uint  bladesPerSide;    /* candidates per tile: bladesPerSide * bladesPerSide */
    uint  capacity0;        /* blades LOD 0's region holds; LOD 1's region starts here */
    uint  capacity1;        /* blades LOD 1's region holds */
    float lodDistance;      /* metres: LOD 0 nearer than this, LOD 1 beyond */
    float morphBand;        /* metres: LOD 0 turns into LOD 1's shape over this last stretch */
    float densityStart;     /* metres: every candidate grows nearer than this */
    float maxDistance;      /* metres: none grows beyond this */
    float farDensity;       /* the fraction of candidates still growing at maxDistance */
    float fadeBand;         /* how far below its cut a blade's size starts shrinking, 0..1 */
    uint  padding3;
    uint  padding4;
    /* Chapter 26 section 9 (optional): occlusion against last frame's depth. Zero without it. */
    mat4  occlusionViewProjection;  /* last frame's viewProjection: the one its depth was drawn with */
    vec4  occlusionPyramid;         /* xy: level 0's size in texels, z: its level count, w: 1 to test */
    /* Chapter 27: the look. */
    vec4  dryColor;         /* linear rgb: the color dry clumps' tips drift toward */
    vec4  windDirection;    /* xy: unit vector the wind blows along, in world xz; zw unused */
    vec4  interactor;       /* section 9: xyz centre of a sphere that pushes blades aside; w radius, 0 = none */
    float windSpeed;        /* metres per second the gusts travel */
    float windStrength;     /* 0..1: scales every gust */
    float gustScale;        /* metres across one gust */
    float gustLean;         /* how far a full gust leans a blade, in blade heights */
    float swayFrequency;    /* hertz */
    float swayAmount;       /* how far the sway leans a blade, in blade heights */
    float clumpSize;        /* metres between clump centres */
    float clumpPull;        /* 0..1: how far blades move toward their clump's centre */
    float clumpFacing;      /* 0..1: how far blades turn to face their clump's way */
    float clumpHeight;      /* 0..1: how much clumps differ in height */
    float clumpDryness;     /* 0..1: how far a clump's tips can drift toward dryColor */
    float thicken;          /* 0..1: how much of its lost width an edge-on blade gets back */
    float roundness;        /* 0..1: how far the normals tilt outward across the blade */
    float translucency;     /* how much sunlight comes through a blade */
    float roughness;        /* 0..1: Chapter 15's perceptual roughness; both highlights read it */
    float specular;         /* the highlight's reflectance head-on: Chapter 15's F0 */
    float rootOcclusion;    /* 0..1: the light that reaches the root */
    float farBlendStart;    /* metres: from here normals and occlusion fade toward the ground's */
    float minimumPixels;    /* the narrowest a blade is drawn, in pixels; 0 = no clamp */
    float viewportHeight;   /* pixels */
    float time;             /* seconds */
    float impostorHeight;   /* section 8: how high the shadow stand-in floats, in mean blade heights */
    float impostorDensity;  /* section 8: the fraction of it that casts where the grass is full */
    uint  highlightModel;   /* section 7: GRASS_HIGHLIGHT_* */
};

/* Chapter 26: one visible tile, written by the CPU each frame. std430, set 1 binding 2. */
struct GrassTile
{
    int  x;               /* the tile covers [x, x + 1) * tileSize in world x */
    int  z;               /* and [z, z + 1) * tileSize in world z */
    uint padding0;
    uint padding1;
};

/* Chapter 26: what the generation pass counts. std430, set 1 binding 3. */
struct GrassCounters
{
    uint lodCount[2];     /* blades appended to each LOD's region; may run past its capacity */
    uint occluded;        /* Chapter 26 section 9: candidates the depth pyramid hid */
    uint padding0;
};

/* Push constants, vertex stage, shared by every grass pipeline; each reads what it needs. */
struct GrassPush
{
    vec4 terrainGrid;     /* xy: world xz of the grid's corner, z: cell size (m), w: cells per side */
    uint segmentCount;    /* Chapter 26: 7 for LOD 0, 3 for LOD 1 */
    uint cascade;         /* Chapter 27 section 8: the shadow cascade the impostor is drawn into */
    uint padding1;
    uint padding2;
};

#ifdef __cplusplus
    static_assert(sizeof(GrassBlade) == 48, "GrassBlade layout drifted.");
    static_assert(sizeof(GrassParameters) == 496, "GrassParameters layout drifted.");
    static_assert(offsetof(GrassParameters, occlusionViewProjection) == 272, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, dryColor) == 352, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, windSpeed) == 400, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, debugView) == 64, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, frustumPlanes) == 80, "GrassParameters alignment drifted.");
    static_assert(offsetof(GrassParameters, tileSize) == 224, "GrassParameters alignment drifted.");
    static_assert(sizeof(GrassTile) == 16, "GrassTile layout drifted.");
    static_assert(sizeof(GrassCounters) == 16, "GrassCounters layout drifted.");
    static_assert(sizeof(GrassPush) == 32, "GrassPush layout drifted.");
    }
#endif

#endif
```

**`Shaders/Grass/Grass.vert.glsl`:**

```glsl
// Shaders/Grass/Grass.vert.glsl - Chapter 27's version: the wind and the ball bend the curve,
// edge-on blades are widened, thin ones are clamped, and the normals are rounded.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "Random.glsl"
#include "GrassTypes.h"
#include "BladeShape.glsl"

layout(set = 1, binding = 0, std430) readonly buffer BladeBlock { GrassBlade blades[]; };
layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };
layout(push_constant) uniform GrassPushBlock { GrassPush push; };

layout(location = 0) out vec3  worldPosition;
layout(location = 1) out vec3  worldNormal;    // the front face's; the fragment shader flips it for the back
layout(location = 2) out float bladeT;
layout(location = 3) out float bladeSide;
layout(location = 4) out vec3  debugColor;     // what the LOD, tile, clump, wind, and edge-on views show
layout(location = 5) out vec3  roundOffset;    // section 5: added to the normal after the flip
layout(location = 6) out vec4  bladeData;      // x: the blade's random number, y: gust, z: dryness, w: coverage

// Section 2. The upper control points move downwind, then the tip is pulled back
// to the blade's length: it leans, it does not stretch.
void applyWind(inout BladeCurve curve, GrassBlade blade)
{
    float height   = blade.shape.x;
    float gust     = blade.variation.y;
    vec3  downwind = vec3(grass.windDirection.x, 0.0, grass.windDirection.y);

    // Every blade sways on its own phase, so neighbours never move in step; gusts
    // lean it further and make it sway harder.
    float phase = 6.2831853 * (blade.variation.x + grass.swayFrequency * grass.time);
    float lean  = gust * grass.gustLean + sin(phase) * grass.swayAmount * (0.3 + gust);

    float bladeLength = distance(curve.p3, curve.p0);
    curve.p2 += downwind * height * lean * 0.5;
    curve.p3 += downwind * height * lean;
    curve.p3  = curve.p0 + normalize(curve.p3 - curve.p0) * bladeLength;
}

// Section 9. Blades near the ball are pushed away from it, the way the wind pushes
// them: control points out, then the length restored.
void applyInteractor(inout BladeCurve curve, GrassBlade blade)
{
    float radius = grass.interactor.w;
    if (radius <= 0.0) { return; }

    vec2  away = curve.p0.xz - grass.interactor.xz;
    float gap  = length(away);
    float push = clamp(1.0 - gap / (radius + blade.shape.x), 0.0, 1.0);
    if (push <= 0.0) { return; }

    vec3  outward     = vec3(away.x, 0.0, away.y) / max(gap, 1e-4);
    float bladeLength = distance(curve.p3, curve.p0);
    curve.p2 += outward * blade.shape.x * push * 0.5;
    curve.p3 += outward * blade.shape.x * push * 1.5;
    curve.p3  = curve.p0 + normalize(curve.p3 - curve.p0) * bladeLength;
}

void main()
{
    // gl_InstanceIndex includes the draw's firstInstance: LOD 1's draw starts at
    // capacity0, so it reads LOD 1's region without knowing it has one.
    GrassBlade blade = blades[gl_InstanceIndex];
    BladeCurve curve = bladeCurve(blade);
    applyWind(curve, blade);          // section 2
    applyInteractor(curve, blade);    // section 9

    uint  segment     = uint(gl_VertexIndex) / 2u;           // 0 .. push.segmentCount
    float side        = (gl_VertexIndex & 1) == 0 ? -1.0 : 1.0;
    bool  lowLod      = push.segmentCount == LOW_SEGMENTS;
    uint  highSegment = lowLod ? LOW_TO_HIGH[segment] : segment;
    float t           = segmentT(highSegment);

    vec3 position = bladeEdge(curve, t, side);
    vec3 normal   = bladeNormal(curve, t);

    // LOD 0 near the switch distance slides its vertices onto LOD 1's straight
    // segments; at the switch the two are the same shape and nothing pops.
    float morph = 0.0;
    if (!lowLod)
    {
        float distanceToCamera = distance(blade.rootAndFacing.xyz, grass.cullPosition.xyz);
        morph = smoothstep(grass.lodDistance - grass.morphBand, grass.lodDistance, distanceToCamera);

        uint  low = highSegment < LOW_TO_HIGH[1] ? 0u : (highSegment < LOW_TO_HIGH[2] ? 1u : 2u);
        float ta  = segmentT(LOW_TO_HIGH[low]);
        float tb  = segmentT(LOW_TO_HIGH[low + 1u]);
        float f   = (t - ta) / (tb - ta);
        vec3  onLowLod   = mix(bladeEdge(curve, ta, side), bladeEdge(curve, tb, side), f);
        vec3  lowLodNormal = normalize(mix(bladeNormal(curve, ta), bladeNormal(curve, tb), f));
        position = mix(position, onLowLod, morph);
        normal   = normalize(mix(normal, lowLodNormal, morph));
    }

    // Section 3. In view space, "how edge-on" and "how wide on screen" are easy to ask.
    vec3  viewPosition = (frame.view * vec4(position, 1.0)).xyz;
    vec3  viewNormal   = mat3(frame.view) * normal;
    vec3  viewTangent  = mat3(frame.view) * bezierDerivative(curve, t);
    vec3  viewRight    = mat3(frame.view) * curve.right;
    float edgeOn       = 1.0 - abs(dot(viewNormal, normalize(-viewPosition)));

    // Across the blade as the screen sees it: perpendicular to its projected
    // tangent, pointing the way its right edge does.
    vec2 across = vec2(viewTangent.y, -viewTangent.x);
    across = dot(across, across) > 1e-12 ? normalize(across) : vec2(1.0, 0.0);
    if (dot(across, viewRight.xy) < 0.0) { across = -across; }

    float halfWidth = 0.5 * curve.width * (1.0 - t * t);
    float widen     = grass.thicken * edgeOn * halfWidth;

    // Section 4. A blade narrower than minimumPixels is drawn that wide, and its
    // fragments carry the fraction of it that is really blade.
    float pixelsPerMetre = abs(frame.projection[1][1]) * 0.5 * grass.viewportHeight / max(-viewPosition.z, 1e-3);
    float drawnWidth     = 2.0 * (halfWidth + widen) * pixelsPerMetre;
    float coverage       = 1.0;
    if (grass.minimumPixels > 0.0 && halfWidth > 0.0 && drawnWidth < grass.minimumPixels)
    {
        coverage = drawnWidth / grass.minimumPixels;
        widen    = 0.5 * grass.minimumPixels / pixelsPerMetre - halfWidth;
    }

    // The view matrix's rotation is orthonormal, so its transpose takes the
    // offset back to world space.
    vec3 viewOffset = vec3(across * side * widen, 0.0);
    worldPosition   = position + transpose(mat3(frame.view)) * viewOffset;
    worldNormal     = normal;
    bladeT          = t;
    bladeSide       = side;
    roundOffset     = curve.right * side * grass.roundness;              // section 5
    bladeData       = vec4(blade.variation.xyz, coverage);

    if (grass.debugView == GRASS_VIEW_TILES)
    {
        ivec2 tile = ivec2(floor(blade.rootAndFacing.xz / grass.tileSize));
        uint  hash = pcgHash(uint(tile.x) ^ pcgHash(uint(tile.y)));
        debugColor = vec3(hash & 255u, (hash >> 8) & 255u, (hash >> 16) & 255u) / 255.0;
    }
    else if (grass.debugView == GRASS_VIEW_CLUMPS)
    {
        uint hash  = pcgHash(uint(blade.variation.w * 16777215.0));
        debugColor = vec3(hash & 255u, (hash >> 8) & 255u, (hash >> 16) & 255u) / 255.0;
    }
    else if (grass.debugView == GRASS_VIEW_WIND)
    {
        debugColor = mix(vec3(0.1, 0.2, 0.9), vec3(1.0, 0.3, 0.1), blade.variation.y);
    }
    else if (grass.debugView == GRASS_VIEW_EDGE_ON)
    {
        debugColor = mix(vec3(0.15), vec3(1.0, 0.9, 0.1), edgeOn);
    }
    else
    {
        debugColor = lowLod ? vec3(0.1, 0.3, 0.9) : mix(vec3(0.1, 0.8, 0.1), vec3(0.9, 0.8, 0.1), morph);
    }

    gl_Position = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

**`Shaders/Grass/Grass.frag.glsl`:**

```glsl
// Shaders/Grass/Grass.frag.glsl - Chapter 27's version: rounded normals, light through the blades,
// highlights, occlusion, variation, and the far field.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"
#include "Lights.glsl"
#include "Shadows.glsl"
#include "PreviewSurface.glsl"   // section 7: Chapter 15's specular terms, and PI
#include "GrassTypes.h"
#include "Terrain.glsl"          // section 6: the ground's normal

layout(set = 1, binding = 1) uniform GrassBlock { GrassParameters grass; };
layout(set = 0, binding = 10) uniform samplerCube skyDiffuse;   // Chapter 25 section 8: Chapter 24's sky light, E / pi

layout(location = 0) in  vec3  worldPosition;
layout(location = 1) in  vec3  worldNormal;
layout(location = 2) in  float bladeT;
layout(location = 3) in  float bladeSide;
layout(location = 4) in  vec3  debugColor;
layout(location = 5) in  vec3  roundOffset;
layout(location = 6) in  vec4  bladeData;
layout(location = 0) out vec4  outColor;

void main()
{
    // One triangle, two faces: light the face you are looking at - then, section 5,
    // tilt it across the blade so the blade shades as if it were rounded.
    vec3  faceNormal   = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
    vec3  normal       = normalize(faceNormal + roundOffset);
    vec3  toCamera     = normalize(frame.cameraPosition.xyz - worldPosition);
    float viewDistance = distance(frame.cameraPosition.xyz, worldPosition);

    // Section 6. Far away a blade is a pixel or less: it takes the ground's normal,
    // and the dark at its root fades, so the field reads as one surface.
    float far = smoothstep(grass.farBlendStart, grass.maxDistance, viewDistance);
    normal    = normalize(mix(normal, terrainNormal(worldPosition.xz, grass.terrainShape), far));

    if (grass.debugView == GRASS_VIEW_STRIP)
    {
        float band = fract(bladeT * 7.0 + 0.001) < 0.5 ? 1.0 : 0.6;
        outColor = vec4(band * (bladeSide < 0.0 ? vec3(0.9, 0.1, 0.1) : vec3(0.1, 0.9, 0.1)), 1.0);
        return;
    }
    if (grass.debugView == GRASS_VIEW_NORMALS)
    {
        outColor = vec4(normal * 0.5 + 0.5, 1.0);
        return;
    }
    if (grass.debugView == GRASS_VIEW_COVERAGE)
    {
        outColor = vec4(vec3(bladeData.w), 1.0);
        return;
    }
    if (grass.debugView >= GRASS_VIEW_CLUMPS)   // clumps, wind, edge-on: unlit, to read the numbers
    {
        outColor = vec4(debugColor, 1.0);
        return;
    }

    // Root to tip, each blade a little lighter or darker, and dry clumps' tips
    // drifting toward straw (section 1). Less light reaches the root (section 7).
    vec3  tip       = mix(grass.tipColor.rgb, grass.dryColor.rgb, bladeData.z);
    vec3  albedo    = mix(grass.rootColor.rgb, tip, bladeT) * (0.85 + 0.3 * bladeData.x);
    float occlusion = mix(mix(grass.rootOcclusion, 1.0, bladeT), 1.0, far);
    if (grass.debugView == GRASS_VIEW_LOD || grass.debugView == GRASS_VIEW_TILES)
    {
        albedo = debugColor * (0.35 + 0.65 * bladeT);   // still lit, so the shapes stay readable
    }

    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;   // Chapter 17's cascade choice
    // Chapter 25 section 8: Chapter 24's switch - the sky's light around the normal, or Chapter 16's constant.
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? texture(skyDiffuse, normal).rgb : lightHeader.ambient.rgb;
    vec3 color   = albedo * occlusion * ambient;
    if (lightHeader.sunIndex >= 0)
    {
        vec3  L;
        vec3  irradiance = lightIrradiance(lights[lightHeader.sunIndex], worldPosition, L);
        float shadow     = sunShadow(worldPosition, faceNormal, viewDepth);

        float diffuse = max(dot(normal, L), 0.0);

        // Light through the blade: the sun on the face we cannot see, strongest
        // when we look toward the sun.
        float through = max(dot(-faceNormal, L), 0.0)
                      * (0.25 + 0.75 * pow(max(dot(-toCamera, L), 0.0), 4.0));

        // The highlight: Chapter 15's specular term, GGX or normalized Blinn-Phong, at the
        // rounded normal. One roughness drives both; every invocation takes the same branch.
        vec3  halfway   = normalize(L + toCamera);
        float NdotH     = max(dot(normal, halfway), 0.0);
        float roughness = max(grass.roughness, MIN_ROUGHNESS);
        float alpha     = roughness * roughness;
        vec3  fresnel   = schlickFresnel(vec3(grass.specular), vec3(1.0), max(dot(toCamera, halfway), 0.0));
        vec3  highlight;
        if (grass.highlightModel == GRASS_HIGHLIGHT_GGX)
        {
            float NdotL = max(diffuse, 1e-4);
            float NdotV = max(dot(normal, toCamera), 1e-4);
            highlight = fresnel * ggxDistribution(NdotH, alpha) * smithGeometry(NdotV, NdotL, alpha)
                      / (4.0 * NdotL * NdotV);
        }
        else
        {
            highlight = fresnel * blinnPhongLobe(NdotH, alpha);   // n = 2 / alpha^2 - 2: as wide as GGX's
        }
        highlight *= 1.0 - far;   // section 6: a pixel-sized blade's highlight is sparkle

        color += irradiance * shadow
               * (albedo * occlusion / PI * (diffuse + grass.translucency * through) + highlight * diffuse);
    }

    // Section 4: alpha is the coverage the width clamp left; alpha-to-coverage
    // turns it into samples at 2x and up, and nothing reads it at 1x.
    outColor = vec4(color * cascadeDebugColor(viewDepth), bladeData.w);
}
```

**`Shaders/Grass/GrassGenerate.comp.glsl`**, with Chapter 26 Part 2's
`occluded`. If you did not do Part 2, leave out that function and the four lines
of `main` that call it, and `GrassCompute.glsl` has no binding 5:

```glsl
// Shaders/Grass/GrassGenerate.comp.glsl - place, cull, and append every candidate blade (Chapter 26),
// grouped into clumps and given a gust (Chapter 27).
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Random.glsl"
#include "GrassTypes.h"
#include "GrassCompute.glsl"
#include "Noise.glsl"         // Chapter 27 section 2
#include "Terrain.glsl"

layout(local_size_x = 64) in;

// A sphere is outside when it is wholly behind any one of the six planes.
bool sphereInFrustum(vec3 center, float radius)
{
    for (int i = 0; i < 6; ++i)
    {
        vec4 plane = grass.frustumPlanes[i];
        if (dot(plane.xyz, center) + plane.w < -radius) { return false; }
    }
    return true;
}

// Chapter 27 section 1: the clump this point belongs to. One centre per cell of a coarse
// grid, jittered inside its cell. The nearest centre is almost always in the
// point's own cell or one of the eight around it; searching those nine is the
// usual compromise, and a rare miss only gives a blade the second-nearest clump.
void nearestClump(vec2 xz, out vec2 center, out uint clumpHash)
{
    ivec2 home = ivec2(floor(xz / grass.clumpSize));
    float best = 1e30;
    for (int dz = -1; dz <= 1; ++dz)
    {
        for (int dx = -1; dx <= 1; ++dx)
        {
            ivec2 cell  = home + ivec2(dx, dz);
            uint  hash  = pcgHash(uint(cell.x) ^ pcgHash(uint(cell.y) ^ 0x9E3779B9u));
            uint  state = hash;
            vec2  point = (vec2(cell) + vec2(randomFloat(state), randomFloat(state))) * grass.clumpSize;
            float d     = dot(xz - point, xz - point);
            if (d < best)
            {
                best      = d;
                center    = point;
                clumpHash = hash;
            }
        }
    }
}

// Chapter 27 section 2: gust strength where a blade stands, 0 calm to 1 a full gust. Two
// octaves of noise, the whole field sliding downwind at windSpeed.
float gustStrength(vec2 xz)
{
    vec2  drift = grass.windDirection.xy * grass.windSpeed * grass.time;
    vec2  p     = (xz - drift) / grass.gustScale;
    float n     = gradientNoise(p) + 0.5 * gradientNoise(p * 2.03 + vec2(17.0, 31.0));
    return clamp(0.5 + n, 0.0, 1.0) * grass.windStrength;
}

// Chapter 26 section 9 (optional): is a sphere hidden behind last frame's depth? Project its
// bounding box with last frame's camera, find the pyramid level where that
// rectangle spans at most 2x2 texels, and compare its nearest depth with the
// farthest those texels saw.
bool occluded(vec3 center, float radius)
{
    if (grass.occlusionPyramid.w == 0.0) { return false; }

    vec2  low     = vec2(1.0);
    vec2  high    = vec2(0.0);
    float nearest = 1.0;
    for (int corner = 0; corner < 8; ++corner)
    {
        vec3 offset = vec3((corner & 1) != 0 ? radius : -radius,
                           (corner & 2) != 0 ? radius : -radius,
                           (corner & 4) != 0 ? radius : -radius);
        vec4 clip = grass.occlusionViewProjection * vec4(center + offset, 1.0);
        if (clip.w <= 0.0) { return false; }   // reaches behind last frame's camera: keep it
        vec3 ndc = clip.xyz / clip.w;
        low      = min(low, ndc.xy * 0.5 + 0.5);
        high     = max(high, ndc.xy * 0.5 + 0.5);
        nearest  = min(nearest, ndc.z);
    }
    // Partly off last frame's screen: no depth there to hide behind.
    if (any(lessThan(low, vec2(0.0))) || any(greaterThan(high, vec2(1.0)))) { return false; }

    // In level 0's texels, then shifted down to the level where the rectangle is
    // at most one texel wide. A level's last texel holds the remainder, so clamp.
    // (The level's size is Vulkan's mip rule, computed rather than asked with
    // textureSize: cheaper, and a level that differs between invocations is a corner
    // some drivers get wrong.)
    vec2  span  = (high - low) * grass.occlusionPyramid.xy;
    int   level = int(min(ceil(log2(max(max(span.x, span.y), 1.0))), grass.occlusionPyramid.z - 1.0));
    ivec2 size  = max(ivec2(grass.occlusionPyramid.xy) >> level, ivec2(1));
    ivec2 a     = min(ivec2(low * grass.occlusionPyramid.xy) >> level, size - 1);
    ivec2 b     = min(ivec2(high * grass.occlusionPyramid.xy) >> level, size - 1);

    float farthest = max(max(texelFetch(depthPyramid, a, level).r, texelFetch(depthPyramid, ivec2(b.x, a.y), level).r),
                         max(texelFetch(depthPyramid, ivec2(a.x, b.y), level).r, texelFetch(depthPyramid, b, level).r));
    return nearest > farthest;
}

void main()
{
    // x: which candidate in the tile; y: which tile.
    uint perSide   = grass.bladesPerSide;
    uint candidate = gl_GlobalInvocationID.x;
    if (candidate >= perSide * perSide) { return; }
    GrassTile tile = tiles[gl_WorkGroupID.y];

    // The cell's WORLD coordinates name the blade, so the same blade grows in the
    // same place whichever tile list, frame, or invocation produced it.
    ivec2 cell  = ivec2(tile.x, tile.z) * int(perSide) + ivec2(candidate % perSide, candidate / perSide);
    uint  state = pcgHash(uint(cell.x) ^ pcgHash(uint(cell.y)));

    float spacing = grass.tileSize / float(perSide);
    vec2  xz      = (vec2(cell) + vec2(randomFloat(state), randomFloat(state))) * spacing;

    // Chapter 27 section 1. Clumps: belong to the nearest centre, move part of the
    // way toward it, and take the clump's height, facing, and dryness as well as
    // your own. The root's height is found after the move.
    vec2 clumpCenter;
    uint clumpHash;
    nearestClump(xz, clumpCenter, clumpHash);
    xz = mix(xz, clumpCenter, grass.clumpPull * randomFloat(state));

    uint  clumpState     = clumpHash;
    float clumpHeight    = 1.0 + grass.clumpHeight * (2.0 * randomFloat(clumpState) - 1.0);
    float clumpFacing    = randomFloat(clumpState) * 6.2831853;
    float clumpDryness   = randomFloat(clumpState) * grass.clumpDryness;
    float clumpVariation = randomFloat(clumpState);

    vec3 root = vec3(xz.x, terrainHeight(xz, grass.terrainShape), xz.y);

    // Thinning: each blade draws its own cut once, and grows while the density
    // where it stands is above it. Just above the cut it shrinks instead of popping.
    float distanceToCamera = distance(root, grass.cullPosition.xyz);
    float along   = clamp((distanceToCamera - grass.densityStart) / (grass.maxDistance - grass.densityStart), 0.0, 1.0);
    float density = distanceToCamera > grass.maxDistance ? 0.0 : mix(1.0, grass.farDensity, along);
    float cut     = randomFloat(state);
    if (cut >= density) { return; }
    float grow    = clamp((density - cut) / grass.fadeBand, 0.0, 1.0);

    vec4 shape = mix(grass.shapeMin, grass.shapeMax,
                     vec4(randomFloat(state), randomFloat(state), randomFloat(state), randomFloat(state)));
    shape.x  *= clumpHeight;   // Chapter 27 section 1
    shape.xy *= grow;

    // Every point of the blade is within its height of the root, and its edges
    // within half its width more. Chapter 27: the wind and the ball lean a blade
    // but keep its length (sections 2 and 9); its control points then stay within
    // twice its height of the root, so the sphere doubles.
    if (!sphereInFrustum(root, 2.0 * shape.x + shape.y)) { return; }
    if (occluded(root, 2.0 * shape.x + shape.y))
    {
        atomicAdd(counters.occluded, 1u);
        return;
    }

    // Chapter 27 section 1. Facing: the blade's own, turned part of the way toward its clump's.
    float ownFacing = randomFloat(state) * 6.2831853;
    vec2  facingDir = mix(vec2(sin(ownFacing), cos(ownFacing)), vec2(sin(clumpFacing), cos(clumpFacing)), grass.clumpFacing);
    float facing    = dot(facingDir, facingDir) > 1e-6 ? atan(facingDir.x, facingDir.y) : clumpFacing;

    GrassBlade blade;
    blade.rootAndFacing = vec4(root, facing);
    blade.shape         = shape;
    blade.variation     = vec4(randomFloat(state), gustStrength(xz), clumpDryness, clumpVariation);   // Chapter 27

    // Append to the LOD's region. Check-and-skip: the count may run past the
    // capacity, the write may not (Chapter 21).
    uint lod      = distanceToCamera < grass.lodDistance ? 0u : 1u;
    uint capacity = lod == 0u ? grass.capacity0 : grass.capacity1;
    uint slot     = atomicAdd(counters.lodCount[lod], 1u);
    if (slot < capacity)
    {
        blades[(lod == 0u ? 0u : grass.capacity0) + slot] = blade;
    }
}
```

Next: [28 — Clouds](28-Clouds.md)
