# 22 — Deferred Shading

**Goal:** the USD viewer draws its opaque scene two ways and switches between
them live. *Forward*, as since Chapter 11: each fragment runs its material and
then every light. *Deferred*: one pass writes what every visible surface is
into a few window-sized images, the **G-buffer**, and a compute pass then
lights each pixel once, with only the lights that can reach its 8 x 8 tile of
the screen. Debug views show what the G-buffer holds and how many lights each
tile kept, and per-pass GPU timings say which path wins on the scene in front of
you.

**ROADMAP:** step 21+. There is no new demo: `SceneRenderer` gains the deferred
path, and the USD viewer (Chapter 14) gains the switch.

**Module:** `Source/PillowFort/VulkanGraphics/`, namespace `pf::vulkan_graphics`
— a new `DeferredShading.h/.cpp`, additions to `SceneRenderer`, and two stage
bits in `ShadowMaps.cpp`. Shaders: `Shaders/Scene/GBuffer.frag.glsl`,
`Shaders/Scene/DeferredLighting.comp.glsl`, `Shaders/Include/Octahedral.glsl`,
and this chapter's block in `SharedShaderTypes.h`. The viewer:
`Demos/UsdViewer/` and `Shaders/UsdViewer/LightGlow.*`. A test scene:
`Assets/Scenes/make_many_lights.py` (Appendix A).

**Prerequisites:**

- Chapter 04 section 5 — the three questions, what "before" and "after" a
  barrier cover, and the appendix of later rows, which this chapter adds to.
- Chapter 08 sections 3 and 4 — the scene target has `STORAGE` usage, and its
  contract with the composite pass.
- Chapter 10 sections 1, 2, 4, and 9 — a matrix acting on a point with `w = 1`,
  the projection and its divide by `w`, depth's uneven spacing, the inverse of a
  matrix, and the depth buffer, created with `SAMPLED` usage for later readers.
- Chapter 12 section 9 — a plane as four numbers, and planes read from a
  matrix's rows. Section 8 does the same for one tile.
- Chapter 15 sections 5 (pixels are shaded in 2 x 2 quads, which a compute
  shader does not have), 9 (`SurfaceSample`, the three BRDFs, and the switch in
  `FrameData`), and 11 (the mesh shaders and their pipelines).
- Chapter 16 sections 2 and 5 (a light's range, and the window that makes it
  exact), 4 (the light buffer), and 6 (tone mapping: read the debug views in
  Raw at 0 stops).
- Chapter 17 sections 5 (the shadow map's two barriers, which gain a stage), 7
  (why shadows use the geometric normal), and 9 (`sunShadow`, for the sun only).
- Chapter 18 sections 2, 5, 7, 8, and 9 — what MSAA stores and resolves, a
  sample-count change setting the demo up again, alpha-to-coverage, and why
  temporal anti-aliasing is the next step.
- Chapter 19 section 5 — `RecordBatches` and its runs, which the G-buffer pass
  reuses.
- Chapter 20 sections 3 (workgroups and the bounds guard), 5 (barriers between
  dispatches, and what synchronization validation can see), 6 (shared memory and
  `barrier()`), 8 (atomics), and 10 (a compute pass that writes the scene target).
- Chapter 21 sections 5 (a second rendering scope after the scene pass, and the
  chain its return trip makes) and 8 (timestamp queries: timing each pass).

---

## What you are actually writing

The frame changes only between the shadow pass and the hand-back:

```text
 forward (Chapters 11-21)                        deferred (this chapter)
 ───────────────────────────────────────         ──────────────────────────────────────────────────
 shadow pass                                     shadow pass
 scene pass: per fragment, the material          G-buffer pass: per fragment, the material only;
   and then every light; writes color, depth       writes the G-buffer, the depth, and the light
                                                   that needs no light list (ambient, emission)
                                                 lighting pass, compute: per pixel, the lights near
                                                   its tile, added to what the G-buffer pass wrote
 second scope: blended things (section 10)       second scope: the same blended things, unchanged
 hand back to the composite (Chapter 08)         hand back to the composite (Chapter 08)
```

Both columns leave the scene color and depth in exactly the state
`endScenePass` documents, so whatever a demo draws after them — Chapter 21's
particles, this chapter's light glows — does not know which path ran.

The files, and what each section adds:

```text
Shaders/Include/SharedShaderTypes.h        FrameData::inverseViewProjection; the deferred block   sections 5, 6
Shaders/Include/Octahedral.glsl            a unit normal in two numbers                            section 3
Shaders/Scene/GBuffer.frag.glsl            the material, written down instead of lit              section 4
Shaders/Scene/DeferredLighting.comp.glsl   the lighting pass; tiles in Part 2                      sections 5, 6, 8
VulkanGraphics/DeferredShading.h/.cpp      the G-buffer images, the lighting set, pipeline, pass  sections 4, 6
VulkanGraphics/SceneRenderer.h/.cpp        EnableDeferred, Resize, RecordGBufferPass, ...          sections 4, 6, 9
VulkanGraphics/ShadowMaps.cpp              the shadow map's barriers name the compute stage        section 6
Demos/UsdViewer/UsdViewerDemo.h/.cpp       the switch, the views, the glows, the timings           sections 5, 7, 10, 11
Shaders/UsdViewer/LightGlow.vert/.frag     blended glows, drawn forward after either path          section 10
Assets/Scenes/make_many_lights.py          ManyLights.usda: 256 lights                             section 11, Appendix A
```

### The class map

`DeferredShading` is to the deferred path what Chapter 17's `ShadowMaps` is to
shadows: a class with its own images and pipeline, which `SceneRenderer` owns
and drives. It owns the G-buffer images, which follow the window,
and the lighting pass. The G-buffer pass's *pipelines* stay in `SceneRenderer`,
beside the mesh pipelines they are copies of.

**This is `Source/PillowFort/VulkanGraphics/DeferredShading.h`**, whole:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  The G-buffer, and the tiled lighting pass that reads it (Chapter 22)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/DeferredShading.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "SharedShaderTypes.h"   // DeferredParameters

#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>
#include <span>

namespace pf::vulkan_graphics {

// The G-buffer's images, in attachment order after the scene target (section 2).
enum GBufferImage : uint32_t
{
    GBufferBaseColorMetallic, GBufferNormal, GBufferSurface,
    GBUFFER_IMAGE_COUNT,
};

// One frame in flight's buffers, which the lighting set shares with set 0 (section 6).
struct LightingInputs
{
    VkDescriptorBufferInfo frame;     // binding 0: FrameData
    VkDescriptorBufferInfo lights;    // binding 1: the light buffer
    VkDescriptorBufferInfo shadows;   // binding 3: ShadowData
};

// SceneRenderer owns one, as it owns ShadowMaps. Everything in it is single-sample (section 9).
class DeferredShading
{
public:
    // The sampler, and the lighting pass's set, layout, and pipeline. The images come in Resize.
    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                    VkFormat sceneColorFormat,
                                    std::span<const LightingInputs, FRAMES_IN_FLIGHT> inputs,
                                    const VkDescriptorImageInfo& shadowMap);                  // section 6
    void Shutdown();                                     // device idle; safe after a partial Initialize
    bool IsReady() const { return m_lightingPipeline != VK_NULL_HANDLE; }

    // From the demo's Resize, after every Setup and swapchain recreation: the G-buffer at the window's
    // size, and the lighting set pointed at it and at the engine's color and depth (section 6).
    InitializationResult Resize(const SceneTargets& targets);

    // What a G-buffer pipeline declares: the scene target's format, then the G-buffer's three (section 4).
    std::span<const VkFormat> PassColorFormats() const { return m_passColorFormats; }

    // Section 4: the barriers into the pass, then a rendering scope over the scene target, the
    // G-buffer, and the depth, with the viewport and scissor set. The caller draws, then ends it.
    void BeginGBufferPass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                          const VkClearColorValue& clearColor);

    // Section 6: the dispatch, with its barriers in and out. Leaves the scene color and depth
    // exactly as endScenePass does, so whatever the demo records next needs no change.
    void RecordLighting(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SceneTargets& targets,
                        const shared::DeferredParameters& parameters);

private:
    void DestroyImages();

    VulkanContext   m_context;                         // copies of borrowed handles
    VkPipelineCache m_pipelineCache = VK_NULL_HANDLE;  // borrowed

    std::array<VkFormat, 1 + GBUFFER_IMAGE_COUNT>  m_passColorFormats{};
    std::array<VkImage, GBUFFER_IMAGE_COUNT>       m_images{};        // window-sized: Resize
    std::array<VmaAllocation, GBUFFER_IMAGE_COUNT> m_allocations{};
    std::array<VkImageView, GBUFFER_IMAGE_COUNT>   m_views{};
    VkSampler                                      m_sampler = VK_NULL_HANDLE;   // nearest: texelFetch

    VkDescriptorSetLayout                         m_setLayout        = VK_NULL_HANDLE;
    VkDescriptorPool                              m_pool             = VK_NULL_HANDLE;   // frees the sets with it
    std::array<VkDescriptorSet, FRAMES_IN_FLIGHT> m_sets{};
    VkPipelineLayout                              m_lightingLayout   = VK_NULL_HANDLE;
    VkPipeline                                    m_lightingPipeline = VK_NULL_HANDLE;
};

} // namespace pf::vulkan_graphics
```

And `SceneRenderer.h` gains one include, one enum, and these members:

```cpp
// SceneRenderer.h - Chapter 22's additions. After the other VulkanGraphics includes:
#include "PillowFort/VulkanGraphics/DeferredShading.h"

// Chapter 22: how a demo that offers both draws its opaque scene. The renderer does not decide; it
// offers both, and the demo records one or the other.
enum class RenderPath : uint32_t { Forward = 0, Deferred = 1 };

public:
    // Chapter 22. Optional: a demo that offers the deferred path calls it in Setup, after Initialize.
    // At more than one sample it builds nothing and DeferredAvailable() stays false (section 9).
    InitializationResult EnableDeferred();
    bool                 DeferredAvailable() const { return m_deferred.IsReady(); }
    // Chapter 22: from the demo's Resize. The G-buffer follows the window, like the engine's targets.
    InitializationResult Resize(const SceneTargets& targets);
    // Chapter 22. In Record, in place of beginScenePass, RecordDraws, and endScenePass: the G-buffer pass
    // (a rendering scope of its own), then the lighting pass, which leaves the targets as endScenePass does.
    void RecordGBufferPass(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SceneTargets& targets,
                           const VkClearColorValue& clearColor);
    void RecordLighting(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SceneTargets& targets);
    void     SetDeferredView(uint32_t view) { m_deferredView = view; }   // DEFERRED_VIEW_* (section 7)
    uint32_t GetDeferredView() const        { return m_deferredView; }

private:
    InitializationResult CreateGBufferPipelines();                       // Chapter 22 section 4

    // Chapter 22: the G-buffer pass's pipelines, one per pair as the mesh pipelines are, and the rest.
    std::array<std::array<VkPipeline, 2>, SHADING_MODE_COUNT> m_gbufferPipelines{};   // [ShadingMode][cutout]
    DeferredShading                                           m_deferred;
    uint32_t                                                  m_deferredView = DEFERRED_VIEW_LIT;
```

The order things happen in:

```text
UsdViewerDemo::Setup
    SceneRenderer::Initialize                          Chapters 10-19, unchanged
    SceneRenderer::EnableDeferred                      section 6; at one sample only (section 9)
        DeferredShading::Initialize                    section 6: sampler, lighting set, pipeline
        SceneRenderer::CreateGBufferPipelines          section 4
UsdViewerDemo::Resize, after every Setup and recreation
    SceneRenderer::Resize -> DeferredShading::Resize   section 4: the images; section 6: the set
UsdViewerDemo::Record, deferred
    RecordShadows                                      Chapter 17
    RecordGBufferPass                                  section 4
        DeferredShading::BeginGBufferPass              its barriers and rendering scope
        RecordBatches, with the G-buffer pipelines     Chapter 19
    RecordLighting                                     sections 6 and 8
        DeferredShading::RecordLighting                barriers in, the dispatch, barriers out
    RecordLightGlows                                   section 10, on both paths
    handBackSceneTarget                                Chapter 08
```

> **Jump:** until now a pixel's color was decided in one place, the fragment
> shader, at the moment a triangle covered it. From here it is decided in two
> passes that never see each other's variables: the first writes *what is
> here* into images, and the second, a compute shader that has never seen a
> triangle, reads those images back and decides *how it is lit*. Everything the
> second pass knows about a surface is what the first pass chose to write down,
> at the precision it chose. Keep that in mind whenever the two paths disagree:
> the question is always which number did not survive the trip through the
> G-buffer.

---

# Part 1 — Deferred shading, every light at every pixel (sections 1-7)

Part 1 builds a complete deferred renderer: the G-buffer, the pass that writes
it, the pass that lights from it, and the switch. Its lighting pass still loops
over every light for every pixel, like the forward one. At the end the two
paths draw the same picture, and the G-buffer's contents are on screen.

---

## 1. Forward and deferred: where the time goes

Since Chapter 11 the scene pass computes a pixel's color at the moment a
triangle covers it — Chapter 16 section 5 named this **forward shading**. Each
**fragment** (Chapter 10 section 9: one triangle's claim on one pixel) samples
its material's textures and then runs the light loop over every light in the
buffer. Two things multiply that work.

**Overdraw.** A pixel can receive several fragments, one from each triangle
that covers it. The depth test throws away a fragment that is behind what is
already there *before* its shader runs (Chapter 15 section 11's early depth
test), but a fragment drawn first and covered later was shaded for nothing.
`SceneRenderer` sorts its draws by material (Chapter 19 section 5), not by
distance, so how much is wasted depends on the scene and the camera. Call the
average number of fragments shaded per pixel the **overdraw**, *o*: 1 means
every pixel was shaded once, 2 means twice.

**Lights.** Every fragment loops over all *L* lights. Most lights reach only a
small part of the scene — Chapter 16 section 5's window makes a light's
contribution exactly zero past its range — but the loop has to evaluate a light
to find that out.

For a frame of *P* pixels, the light loop runs

$$
W_{\text{forward}} = P \cdot o \cdot L
$$

times. At 1440p, *P* = 2560 × 1440 = 3,686,400. With *o* = 1.5 and Chapter 16's
`LightTest.usda`, five lights, that is 27.6 million light evaluations a frame.
With this chapter's `ManyLights.usda`, 256 lights, it is 1.4 *billion* — 85
billion a second at 60 frames a second, each one tens of instructions and, for
the sun, a shadow lookup.

**Deferred shading** splits the work in two:

1. **The G-buffer pass** draws the scene as before, but its fragment shader
   stops where the light loop would start. It writes what the loop would have
   needed — the surface's base color, roughness, normal — into a few
   window-sized images, the **G-buffer** (geometry buffer). Overdraw still
   happens, but an overdrawn fragment costs only its material.
2. **The lighting pass** runs once per pixel. It reads that pixel's G-buffer
   and runs the light loop. Only the surface that ended up visible is lit.

$$
W_{\text{deferred}} = P \cdot L \qquad \text{(plus } P \cdot o \text{ material evaluations)}
$$

That removes *o* from the expensive part. The second win is bigger, and it is
Part 2's subject: the lighting pass sees the whole screen at once, so it can
first work out which lights reach each small square of it — a **tile** — and
loop over only those. With an average of $\bar{L}_{\text{tile}}$ lights per tile:

$$
W_{\text{tiled}} = P \cdot \bar{L}_{\text{tile}}
$$

In `ManyLights.usda` a tile keeps about 25 of the 256 lights on average
(section 8 measures it), so the same 1440p frame needs 3,686,400 × 25 = 92
million light evaluations instead of 1.4 billion: fifteen times fewer.

### The price: bytes

Deferred shading pays in memory traffic. Every pixel's G-buffer is written once
and read once per frame, however many lights there are. Section 2 settles on 12
bytes of G-buffer per pixel; with the depth and the scene target, the G-buffer
pass writes about 24 bytes per pixel and the lighting pass reads 24 and writes
8 — about 56 bytes per pixel, or 206 MB per 1440p frame. At 60 frames a second
that is 12 GB/s before a single texture is read. A forward pass writes 12 bytes
per fragment: the color and the depth.

Whether 12 GB/s matters depends on the GPU. A discrete GPU has its own memory,
moving 300 to 1000 GB/s. An **integrated** GPU, such as a laptop's, shares the
system memory with the CPU, and that memory moves roughly 90 to 120 GB/s in
total, depending on what is fitted. On it, a G-buffer's traffic
is a tenth of everything the machine can move — which is why the answer to
"which is faster" is not a rule but a measurement (section 11).

### When each wins

| | Forward | Deferred, tiled |
| --- | --- | --- |
| Light loop runs | fragments × every light | pixels × the lights near the tile |
| Fixed cost per frame | none | the G-buffer, written and read: about 56 bytes per pixel |
| MSAA (Chapter 18) | nearly free | four times the G-buffer, and lighting per sample at edges (section 9) |
| Transparent surfaces | blended in the same frame | drawn forward afterwards: the G-buffer holds one surface per pixel (section 10) |
| Material models | each draw can run its own shader | one lighting shader for every pixel |
| Wins when | few lights, MSAA, little memory bandwidth | many lights, much overdraw |

There is a middle path, **Forward+** (tiled forward): build the same per-tile
light lists from a depth-only pass, then shade forward with them. It keeps
MSAA and transparency and has no G-buffer, at the price of drawing the scene
twice. It is named here and not built; Part 2's tile lists are the half it
shares with this chapter.

---

## 2. What the light loop reads: the G-buffer

**This is the G-buffer's layout**, decided from what Chapter 17's light loop in
`Mesh.frag.glsl` actually reads. Everything it reads has to reach the lighting
pass somehow:

| The loop reads | Mesh.frag.glsl gets it from | The lighting pass gets it from |
| --- | --- | --- |
| `s.baseColor`, `s.metallic`, `s.roughness`, `s.ior` | textures times constants (Chapter 15) | the G-buffer |
| `s.brdf` | `frame.brdf` | `frame.brdf`: `FrameData` is set 0 binding 0, and the lighting pass reads it too |
| `N`, the normal-mapped normal, flipped for back faces | the tangent frame | the G-buffer |
| `geometricNormal`, for the shadow lookup's offset | `worldNormal` | the G-buffer |
| `worldPosition` | the vertex shader | rebuilt from the depth buffer (section 5) |
| `viewDepth` and `V` | computed from `worldPosition` | computed the same way |
| `occlusion` and `emissive` | textures | nowhere: see below |

**The light that needs no light list.** `occlusion` darkens only the ambient
light, and `emissive` is light the surface makes itself. Neither depends on the
lights in the buffer, so neither has to wait for the lighting pass. The G-buffer
pass computes `evaluateAmbient(...) + emissive` where the material is known and
writes it straight into the scene target, and the lighting pass adds the loop's
result to what is there. The G-buffer then needs no occlusion and no emission —
an HDR color that would cost 4 to 8 bytes a pixel on its own. Chapter 24's
light from the sky is the same kind, and goes in the same place.

**Spend bits where the eye notices.** Chapter 03 section 2 showed why 8-bit
color is stored sRGB-encoded: the encoding spends its 256 steps where eyes tell
shades apart, in the darks. The same argument decides each field:

- **Base color**, `R8G8B8A8_SRGB`, the same encoding as the textures it came
  from. Stored linear in 8 bits, two dark values such as 0.002 and 0.005 would
  both round to 1/255 and become one shade; stored sRGB, they land on 7/255 and
  16/255, nine steps apart. **Metallic** goes in the alpha channel, which an
  `_SRGB` format keeps linear. Most materials are 0 or 1 anyway.
- **The normal**, two 16-bit floats, `R16G16_SFLOAT`, in the octahedral
  encoding of section 3. Sixteen bits because highlights are narrow: under GGX
  at roughness 0.2 the highlight is a few degrees wide, and an 8-bit normal moves
  in steps of about one degree, which bands it. A half float's step near 1 is
  2⁻¹¹, about 0.03°. Why `SFLOAT` and not the evenly spaced `R16G16_UNORM`:
  Vulkan's list of formats every device must be able to render to includes
  `R16G16_SFLOAT` and not `R16G16_UNORM`, so this choice needs no check.
- **Roughness** in 8 bits, *as authored*: perceptual roughness, squared only
  inside the BRDF (Chapter 15 section 9). Storing it before squaring is the sRGB
  argument again: the 256 steps are spread the way the slider is, which is how
  the eye sees the change.
- **ior** as (ior − 1) / 2 in 8 bits: index 1 to 3 in 255 steps. The usual 1.5
  is stored as 64/255, which reads back as 1.502, and moves the head-on
  reflectance F0 from 0.0400 to 0.04025.
- **The geometric normal** in 8 + 8 bits, octahedral. It only chooses the
  direction of Chapter 17 section 7's one-texel nudge before the shadow lookup,
  so an error of a degree or so is invisible.

Roughness, ior, and the geometric normal share one `R8G8B8A8_UNORM` image.

**The budget.** At 1440p, *P* = 3,686,400 pixels:

| Image | Format | Bytes per pixel | MB at 1440p | |
| --- | --- | --- | --- | --- |
| Base color, metallic | `R8G8B8A8_SRGB` | 4 | 14.7 | new |
| Normal | `R16G16_SFLOAT` | 4 | 14.7 | new |
| Roughness, ior, geometric normal | `R8G8B8A8_UNORM` | 4 | 14.7 | new |
| Depth | `D32_SFLOAT` | 4 | 14.7 | Chapter 10's |
| Scene target: ambient and emission, then the lit result | `R16G16B16A16_SFLOAT` | 8 | 29.5 | Chapter 08's |
| Total | | 24 | 88.5 | 44 MB new |

This is a small G-buffer because UsdPreviewSurface needs little. Engines with
more material features — subsurface scattering, clear coat, velocity for
temporal anti-aliasing — run 20 to 30 bytes before the depth.

`DeferredShading.cpp` includes `DeferredShading.h`, `GraphicsPipeline.h` (for
`createComputePipeline` and `groupCount`), and `VulkanBarriers.h` (for
`transitionImage`). In the files, the three formats are a table at the top of
`DeferredShading.cpp`,
above the namespace block:

```cpp
// File scope, above the namespace block. Section 2's G-buffer, in attachment order. All three are on
// Vulkan's list of formats every device must render to and sample.
static constexpr VkFormat GBUFFER_FORMATS[pf::vulkan_graphics::GBUFFER_IMAGE_COUNT] = {
    VK_FORMAT_R8G8B8A8_SRGB,    // base color, stored as its textures were; metallic in alpha (linear)
    VK_FORMAT_R16G16_SFLOAT,    // the shading normal, octahedral
    VK_FORMAT_R8G8B8A8_UNORM,   // roughness, (ior - 1) / 2, the geometric normal (octahedral, 0..1)
};
```

---

## 3. A normal in two numbers

**This is `Shaders/Include/Octahedral.glsl`.**

A unit normal has three components, but only two of them are free: once *x*
and *y* are known, *z* is fixed up to its sign, because the length is 1. So two
numbers should do. The obvious two — store *x* and *y*, rebuild
*z* = √(1 − *x*² − *y*²) — lose the sign of *z*, which in world space can be
either, and spend their precision badly: near the equator *z* changes fast while
*x* and *y* barely move.

The **octahedral encoding** keeps the sign and spreads the precision almost
evenly. Its idea in three steps:

1. Squash the sphere of directions onto an **octahedron** — the eight-sided
   shape whose points satisfy |*x*| + |*y*| + |*z*| = 1 — by dividing the
   vector by |*x*| + |*y*| + |*z*|.
2. Look at it from above, down the *z* axis. The upper half (*z* ≥ 0) covers
   the diamond |*x*| + |*y*| ≤ 1, with +*z* at the centre and the equator on
   its edges. Its *x* and *y* are the encoding.
3. The lower half would land on the same diamond. Instead, fold each of its four
   quarters outward across the diamond's edge, into the matching corner of the
   square: the whole sphere then fills the square −1..1, with −*z* at its four
   corners.

```text
  (-1, 1) ┌───────┬───────┐ (1, 1)
          │ lower╱ ╲lower │
          │    ╱     ╲    │      inside the diamond |x| + |y| <= 1: the upper half (z >= 0),
          │  ╱  upper  ╲  │      +z at the centre, the equator on the diamond's edges
          ├─<    half   >─┤
          │  ╲   (+z)  ╱  │      the four corner triangles: the lower half (z < 0), each
          │    ╲     ╱    │      quarter folded out across the edge it touches;
          │ lower╲ ╱lower │      -z at the four corners
 (-1, -1) └───────┴───────┘ (1, -1)
```

In symbols, with $p = (n_x, n_y) \,/\, (|n_x| + |n_y| + |n_z|)$:

$$
e = \begin{cases} p & n_z \ge 0 \\ \big(1 - |p_y|,\; 1 - |p_x|\big) \cdot \operatorname{sign}(p) & n_z < 0 \end{cases}
$$

Decoding runs it backwards: $z = 1 - |e_x| - |e_y|$; if that is negative, the
point came from a corner, so unfold it with the same swap; then normalize.

**Worked, twice.** The normal (0.6, 0, 0.8): the sum of the absolute values is
1.4, so *p* = (0.4286, 0). *z* is positive, so *e* = (0.4286, 0). Decoding,
*z* = 1 − 0.4286 − 0 = 0.5714, and (0.4286, 0, 0.5714) normalized is
(0.6, 0, 0.8) again.

The normal (0.6, 0, −0.8), its mirror below the equator, has the same *p*. *z* is
negative, so the folded form is ((1 − 0)·1, (1 − 0.4286)·1) = (1, 0.5714): the
right-hand edge of the square, in the upper-right corner triangle. Decoding,
*z* = 1 − 1 − 0.5714 = −0.5714, negative, so unfold:
*x* = (1 − 0.5714)·1 = 0.4286 and *y* = (1 − 1)·1 = 0, giving
(0.4286, 0, −0.5714), which normalizes to (0.6, 0, −0.8).

That second example is why `sign` is replaced by `signNotZero`: GLSL's
`sign(0.0)` is 0, and the fold would have multiplied *y*'s 0.5714 by it.

```glsl
// Shaders/Include/Octahedral.glsl - Chapter 22. A unit vector in two numbers, and back. Included,
// never compiled on its own.
#ifndef PF_OCTAHEDRAL_GLSL
#define PF_OCTAHEDRAL_GLSL

// +1 or -1 per component, never 0: GLSL's sign(0.0) is 0, which would fold an edge onto the centre.
vec2 signNotZero(vec2 v)
{
    return vec2(v.x >= 0.0 ? 1.0 : -1.0, v.y >= 0.0 ? 1.0 : -1.0);
}

// The unit vector n as a point in the square -1..1: onto the octahedron |x| + |y| + |z| = 1, then
// seen from above, with the lower half folded out over the four corners (section 3).
vec2 encodeOctahedral(vec3 n)
{
    vec2 p = n.xy / (abs(n.x) + abs(n.y) + abs(n.z));
    return n.z >= 0.0 ? p : (1.0 - abs(p.yx)) * signNotZero(p);
}

// The inverse: unfold the corners back under the octahedron, then normalize.
vec3 decodeOctahedral(vec2 e)
{
    vec3 n = vec3(e, 1.0 - abs(e.x) - abs(e.y));
    if (n.z < 0.0) { n.xy = (1.0 - abs(n.yx)) * signNotZero(n.xy); }
    return normalize(n);
}

#endif
```

`encodeOctahedral` returns values in −1..1. The `R16G16_SFLOAT` normal stores
them as they are; the 8-bit geometric normal stores `e * 0.5 + 0.5`, because a
UNORM channel holds 0..1, and the reader undoes it with `* 2.0 - 1.0`.

That completes the design: sections 1-3 decided why to defer, what to store,
and how to store a normal in two numbers, and only `Octahedral.glsl` has been
written. From section 4 on you write the rest of Part 1, and section 7 runs it.

---

## 4. The G-buffer pass

**This is `Shaders/Scene/GBuffer.frag.glsl`, the G-buffer images in
`DeferredShading::Resize`, `BeginGBufferPass`, and `SceneRenderer`'s G-buffer
pipelines.**

### The shader

The G-buffer pass draws exactly what the forward pass draws, with the same
vertex shader, `Mesh.vert.glsl`, so the same pixels are covered. Only the
fragment shader differs. It is Chapter 15's `Mesh.frag.glsl` up to the line
before its light loop, followed by writes instead of the loop. Its top declares
four outputs instead of one — **one output per color attachment**, matched by
`location` — and keeps Chapter 15's two specialization constants, so the same
eight shading-mode and cutout combinations exist:

```glsl
// Shaders/Scene/GBuffer.frag.glsl - Chapter 22: Mesh.frag.glsl up to its light loop, with what the
// loop would have read written down instead. Mesh.vert.glsl is its vertex shader.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Color.glsl"        // srgbToLinear, for the normals view
#include "FrameBlock.glsl"
#include "MaterialSet.glsl"
#include "PreviewSurface.glsl"
#include "Lights.glsl"       // only lightHeader.ambient: the light that does not depend on the list
#include "Octahedral.glsl"

layout(location = 0) in vec3 worldPosition;
layout(location = 1) in vec3 worldNormal;
layout(location = 2) in vec2 uv;
layout(location = 3) in vec4 worldTangent;

// The G-buffer pass's four color attachments (section 2).
layout(location = 0) out vec4 outColor;               // the scene target: ambient light and emission
layout(location = 1) out vec4 outBaseColorMetallic;   // R8G8B8A8_SRGB: rgb base color, a metallic
layout(location = 2) out vec2 outNormal;              // R16G16_SFLOAT: the shading normal, octahedral
layout(location = 3) out vec4 outSurface;             // R8G8B8A8_UNORM: roughness, ior, geometric normal

layout(constant_id = 0) const uint shadingMode = 0;     // ShadingMode, as in Mesh.frag.glsl
layout(constant_id = 1) const bool alphaCutout = false; // the material's pipeline

const uint SHADING_NORMALS                 = 1u;
const uint SHADING_MIP_LEVEL               = 2u;
const uint SHADING_LIT_WITHOUT_NORMAL_MAPS = 3u;

// Mesh.frag.glsl's, unchanged.
vec3 mipLevelColor(float level)
{
    const vec3 colors[7] = vec3[](vec3(1.0, 0.0, 0.0), vec3(1.0, 0.5, 0.0), vec3(1.0, 1.0, 0.0),
                                  vec3(0.0, 1.0, 0.0), vec3(0.0, 1.0, 1.0), vec3(0.0, 0.0, 1.0),
                                  vec3(0.6, 0.0, 1.0));
    return colors[clamp(int(level + 0.5), 0, 6)];
}
```

**`main()` is `Mesh.frag.glsl`'s, edited.** Copy that function, then make three
changes. First, its cutout block loses alpha-to-coverage, because the G-buffer
pass always draws at one sample (section 9), so the block becomes two lines:

```glsl
    // Mesh.frag.glsl's main() up to its light loop, but for alpha-to-coverage: the G-buffer pass has one
    // sample per pixel (section 9), so a cutout always discards.
    float opacity = materialOpacity(uv);
    if (alphaCutout && opacity < material.opacityThreshold) { discard; }
```

Second, everything from `SurfaceSample s;` down to
`if (!gl_FrontFacing) { N = -N; }` stays exactly as it is: the material's
inputs and the shading normal. Third, everything after that line goes — the
view vector, the light loop, and the end of the function — and in its place
come the geometric normal and the two halves of the split this chapter is
about:

```glsl
    vec3 geometricNormal = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);

    // The light that needs no light list goes straight into the scene target; the lighting pass adds
    // the rest to it. Chapter 15's two debug views are written here, and the lighting pass leaves them.
    vec3 color = evaluateAmbient(s, lightHeader.ambient.rgb, occlusion) + emissive;
    if (shadingMode == SHADING_NORMALS)   { color = srgbToLinear(N * 0.5 + 0.5); }
    if (shadingMode == SHADING_MIP_LEVEL) { color = mipLevelColor(textureQueryLod(baseColorTexture, uv).x); }
    outColor = vec4(min(color, vec3(64000.0)), 1.0);

    // What the light loop reads, packed (section 2). The unorm targets clamp to 0..1 on their own.
    outBaseColorMetallic = vec4(s.baseColor, s.metallic);
    outNormal            = encodeOctahedral(N);
    outSurface           = vec4(s.roughness, (s.ior - 1.0) * 0.5,
                                encodeOctahedral(geometricNormal) * 0.5 + 0.5);
}
```

Three details:

- **Location 0 is the scene target**, the same `R16G16B16A16_SFLOAT` image the
  forward pass draws into, and it receives the light that needs no light list
  (section 2). Chapter 15's Normals and Mip level views are written there too,
  because a mip level can only be measured here: it needs the 2 x 2 quad's
  derivatives (Chapter 15 section 5), and a compute shader has no quads.
- **The packing is section 2's table, line for line.** Writing a value above 1
  into a UNORM channel clamps it, so a roughness above 1 — which no material
  should have — is stored as 1 rather than wrapping.
- **This is the second copy of the material code**, after `Mesh.frag.glsl`'s.
  ROADMAP's guardrail is to write a pattern twice before automating it; a third
  shader that needs a `SurfaceSample` from a material is the time to move these
  lines into an include.

### The images

The G-buffer is sized to the window, like the engine's scene target and depth,
so it is rebuilt whenever they are. The engine tells a demo through `Resize`
(Chapter 09 section 2), after every `Setup` and every swapchain recreation, and
the viewer passes it on to `SceneRenderer::Resize`:

```cpp
InitializationResult SceneRenderer::Resize(const SceneTargets& targets)
{
    return DeferredAvailable() ? m_deferred.Resize(targets) : InitializationResult::success();
}
```

**This is `DeferredShading::Resize`, first half**: the three images, created
exactly as Chapter 08 section 4 creates the scene target — a dedicated VMA
allocation, because they are large and replaced on every resize — with the
usages the two passes need, `COLOR_ATTACHMENT` to be drawn into and `SAMPLED` to
be read:

```cpp
InitializationResult DeferredShading::Resize(const SceneTargets& targets)
{
    // Chapter 09 calls Resize behind a vkDeviceWaitIdle, so nothing still uses the old images or sets.
    DestroyImages();

    const VmaAllocationCreateInfo allocationInfo{
        .flags = VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT,   // window-sized, rebuilt on resize: Chapter 08's choice
        .usage = VMA_MEMORY_USAGE_AUTO,
    };
    for (uint32_t i = 0; i < GBUFFER_IMAGE_COUNT; ++i)
    {
        // Drawn into by the G-buffer pass, then sampled by the lighting pass.
        const VkImageCreateInfo imageInfo{
            .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
            .imageType     = VK_IMAGE_TYPE_2D,
            .format        = GBUFFER_FORMATS[i],
            .extent        = { targets.extent.width, targets.extent.height, 1 },
            .mipLevels     = 1,
            .arrayLayers   = 1,
            .samples       = VK_SAMPLE_COUNT_1_BIT,
            .tiling        = VK_IMAGE_TILING_OPTIMAL,
            .usage         = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
            .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
            .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
        };
        if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo,
                           &m_images[i], &m_allocations[i], nullptr) != VK_SUCCESS)
        {
            return InitializationResult::failure("vmaCreateImage failed for the G-buffer.");
        }
        const VkImageViewCreateInfo viewInfo{
            .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
            .image            = m_images[i],
            .viewType         = VK_IMAGE_VIEW_TYPE_2D,
            .format           = GBUFFER_FORMATS[i],
            .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
        };
        if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_views[i]) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkCreateImageView failed for the G-buffer.");
        }
    }
```

The second half, from `// Bindings 5 to 9`, points the lighting set at the new
images; section 6 shows it. `DestroyImages` is Chapter 08's
`destroySceneTarget` three times over (Appendix B).

### Into the pass

**This is `BeginGBufferPass`.** `beginScenePass` cannot open this pass: it
opens a scope over one color attachment, and this one has four. So
`DeferredShading` opens its own, with five barriers in front.

Two of them are `beginScenePass`'s own at one sample, Chapter 04's
"Offscreen target, start of frame" and "Depth attachment, start of frame" rows.
The other three are new, one per G-buffer image, and answer the three
questions like this:

- **Q1, execution.** The last thing to touch a G-buffer image was *last*
  frame's lighting pass, which sampled it in a compute shader. This frame's
  attachment writes must not start until it has finished: source
  `COMPUTE_SHADER`, destination `COLOR_ATTACHMENT_OUTPUT`.
- **Q2, memory.** A write after a read leaves nothing to flush: source access
  `NONE`, destination `COLOR_ATTACHMENT_WRITE`.
- **Q3, layout.** `UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL`. The old contents
  are not needed: every texel the lighting pass will read is drawn again this
  frame.

Then the scope. The scene target is cleared, as the forward pass clears it,
because pixels where nothing is drawn keep the clear color. The G-buffer is **not** cleared —
`LOAD_OP_DONT_CARE` — because nothing reads a G-buffer texel where nothing was
drawn: the lighting pass checks the depth first, and a depth still at its clear
value of 1.0 means "no surface here". Clearing would be three full-screen
writes for nothing.

```cpp
void DeferredShading::BeginGBufferPass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                                       const VkClearColorValue& clearColor)
{
    // The scene target and the depth: beginScenePass's two barriers at one sample, Chapter 04's rows.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);

    // The G-buffer: last frame's lighting pass sampled it in a compute shader. A write after a read, and
    // every texel the lighting pass will read is drawn again, so UNDEFINED.
    for (const VkImage image : m_images)
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    }

    // Location 0 is the scene target, cleared as the forward pass clears it. The G-buffer is not cleared:
    // the lighting pass reads it only where the depth says something was drawn.
    std::array<VkRenderingAttachmentInfo, 1 + GBUFFER_IMAGE_COUNT> colorAttachments{};
    colorAttachments[0] = {
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue  = { .color = clearColor },
    };
    for (uint32_t i = 0; i < GBUFFER_IMAGE_COUNT; ++i)
    {
        colorAttachments[1 + i] = {
            .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
            .imageView   = m_views[i],
            .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
            .resolveMode = VK_RESOLVE_MODE_NONE,
            .loadOp      = VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
        };
    }
    const VkRenderingAttachmentInfo depthAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.depthView,
        .imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
        .clearValue  = { .depthStencil = { 1.0f, 0 } },
    };
    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, targets.extent },
        .layerCount           = 1,
        .colorAttachmentCount = static_cast<uint32_t>(colorAttachments.size()),
        .pColorAttachments    = colorAttachments.data(),
        .pDepthAttachment     = &depthAttachment,
    };
    vkCmdBeginRendering(commandBuffer, &renderingInfo);

    const VkViewport viewport{ 0.0f, 0.0f,
                               static_cast<float>(targets.extent.width),
                               static_cast<float>(targets.extent.height),
                               0.0f, 1.0f };
    const VkRect2D scissor{ { 0, 0 }, targets.extent };
    vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
    vkCmdSetScissor(commandBuffer, 0, 1, &scissor);
}
```

### The pipelines and the draws

**This is `SceneRenderer::CreateGBufferPipelines`.** It is Chapter 15
section 11's `CreatePipelines` loop — two specialization constants, a pipeline
for every shading mode and cutout pair — writing into `m_gbufferPipelines`, with
Chapter 18's third constant gone. Inside the loop the description changes in
three fields: the fragment shader, the four color formats `PassColorFormats()`
returns, and one sample. It keeps the mesh pipelines' layout, `m_meshLayout` —
sets 0 and 1 — because its shaders read exactly what theirs do. Appendix B has
the whole function; this is the part that differs:

```cpp
            // In CreateGBufferPipelines' loop (Chapter 22): the mesh pipelines' description, three fields changed.
            const GraphicsPipelineDesc desc{
                .vertexShader           = "Scene/Mesh.vert.spv",
                .fragmentShader         = "Scene/GBuffer.frag.spv",
                .vertexBindings         = meshVertexBindings(),
                .vertexAttributes       = meshVertexAttributes(),
                .colorFormats           = m_deferred.PassColorFormats(),
                .depthFormat            = m_formats.depth,
                .depthTest              = true,
                .depthWrite             = true,
                .depthCompare           = VK_COMPARE_OP_LESS,
                .cullMode               = VK_CULL_MODE_BACK_BIT,
                .frontFace              = VK_FRONT_FACE_COUNTER_CLOCKWISE,
                .dynamicStates          = dynamicStates,
                .fragmentSpecialization = &specialization,
                .layout                 = m_meshLayout,
                .samples                = VK_SAMPLE_COUNT_1_BIT,
            };
```

`DestroyPipelines` destroys them first, before the mesh pipelines and the layout
they share. Until `EnableDeferred` runs they are null, and destroying a null
pipeline does nothing:

```cpp
for (std::array<VkPipeline, 2>& pipelines : m_gbufferPipelines)   // Chapter 22: none unless EnableDeferred ran
{
    for (VkPipeline& pipeline : pipelines)
    {
        vkDestroyPipeline(m_context.device, pipeline, nullptr);
        pipeline = VK_NULL_HANDLE;
    }
}
```

**This is `SceneRenderer::RecordGBufferPass`.** `RecordDraws` from Chapter 19,
between `BeginGBufferPass` and the end of the scope, with the G-buffer pipelines
bound instead of the mesh pipelines:

```cpp
void SceneRenderer::RecordGBufferPass(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                      const SceneTargets& targets, const VkClearColorValue& clearColor)
{
    m_deferred.BeginGBufferPass(commandBuffer, targets, clearColor);

    // RecordDraws, with the G-buffer pipelines in place of the mesh pipelines.
    BindFrameSet(commandBuffer, m_meshLayout, frameIndex);
    vkCmdSetFrontFace(commandBuffer, m_frontFaceFlipped ? VK_FRONT_FACE_CLOCKWISE
                                                        : VK_FRONT_FACE_COUNTER_CLOCKWISE);
    const uint32_t shading = static_cast<uint32_t>(m_shading);
    RecordBatches(commandBuffer, frameIndex, DrawList::Scene, [&](VkCommandBuffer cb, const DrawRun& run) {
        const GpuMaterial& material = m_gpuMaterials[run.material];
        vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_gbufferPipelines[shading][material.cutout ? 1 : 0]);
        vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
        vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_meshLayout, 1, 1, &material.set, 0, nullptr);
    });

    vkCmdEndRendering(commandBuffer);
}
```

---

## 5. Where a pixel is: position from depth

**This is `worldFromDepth`, and the `FrameData` field it reads.**

The forward fragment shader knows where it is: the vertex shader hands it
`worldPosition`, interpolated across the triangle. The lighting pass has no
triangle. It knows a pixel and, from the depth buffer, that pixel's depth. That
is enough, because the depth buffer stores exactly what the projection
computed, and the projection can be undone.

Chapter 10 section 2 built the projection: the matrix puts the distance in front
of the camera into `w`, and the GPU divides *x*, *y*, and *z* by it. What comes
out — **normalized device coordinates**, NDC — has *x* and *y* from −1 to 1
across the screen (*y* down) and *z* from 0 at the near plane to 1 at the far
plane. That *z* is what the depth buffer stores. So for a pixel the lighting pass
can rebuild the whole NDC point:

- *x* and *y* from the pixel's position: its centre, `pixel + 0.5`, divided by
  the image size, gives 0..1, and `* 2 - 1` gives −1..1. The viewport (Chapter
  06 section 4) maps NDC to pixels with *y* down, and NDC's *y* is down too, so
  no flip is needed.
- *z* from the depth buffer.

Now undo the two steps that made it. The view-projection matrix took a world
point to clip space; its **inverse** (Chapter 10 section 4) takes clip space
back. But the NDC point is the clip point *divided by w*, and multiplying a
divided point by the inverse gives a divided result (a matrix treats a scaled
vector the way it treats the vector: scaling first or after gives the same
answer): the world point, divided by that same *w*, with 1/*w* in its fourth
component. Dividing by the fourth
component undoes it:

$$
\begin{pmatrix} X \\ Y \\ Z \\ W \end{pmatrix} = (P\,V)^{-1} \begin{pmatrix} x_{\text{ndc}} \\ y_{\text{ndc}} \\ \text{depth} \\ 1 \end{pmatrix},
\qquad
\text{world} = \left( \frac{X}{W},\ \frac{Y}{W},\ \frac{Z}{W} \right)
$$

**Worked, with Chapter 10's matrix.** Chapter 10 section 2's example camera: a
90° field of view, a square window, near plane 1, far plane 2. Put the camera
at the origin looking down −Z, so the view matrix is the identity and world
space is view space. Take the point (0.5, 0.75, −1.5). Forward, the projection
gives clip (0.5, −0.75, 1, 1.5) — `w` is the distance, 1.5 — and dividing by
1.5 gives NDC (0.333, −0.5, 0.667). On a 600 x 600 target that is pixel
(400, 150), and the depth buffer there holds 0.667, the 0.67 Chapter 10 found
for a point at 1.5 m.

Backwards: for this projection the inverse works out to
(*x*, *y*, *z*, *w*) → (*x*, −*y*, −*w*, *w* − *z*/2) — multiply it by the
matrix in Chapter 10 to check. Applied to (0.333, −0.5, 0.667, 1) it gives
(0.333, 0.5, −1, 0.667). The fourth component, 0.667, is 1/1.5: one over the
distance, as promised. Dividing by it gives (0.5, 0.75, −1.5), the point we
started from.

**Where the inverse comes from.** It is the same for every pixel in the frame,
so it is computed once, on the CPU, and it goes where per-frame camera data
already lives: `FrameData`, appended at its end as Chapter 10 section 7's
append-only rule asks. In `SharedShaderTypes.h`, after Chapter 15's `padding4`:

```c
    uint  padding4;         /* 284 */
    /* Chapter 22: clip space back to world space, for a pass that knows only a pixel and its depth. */
    mat4  inverseViewProjection;   /* 288  inverse(viewProjection) */
};
```

The size check becomes 352, and one offset check joins the others:

```c
#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 352, "FrameData layout drifted.");
    static_assert(offsetof(FrameData, cameraPosition) == 192, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, time) == 208, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, sunDirection) == 224, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, brdf) == 272, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, inverseViewProjection) == 288, "FrameData alignment drifted.");
#endif
```

The viewer fills it in `Record`, right after Chapter 15's `brdf` line.
`glm::inverse` is the general inverse; unlike Chapter 10's view matrix, a
projection has no shortcut such as `lookAt`:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, Record: after Chapter 15's frameData.brdf (Chapter 22).
frameData.inverseViewProjection = glm::inverse(frameData.viewProjection);   // Chapter 22 section 5
```

Other demos leave it zero, which is harmless: only the lighting pass reads it.
The function that uses it goes in the lighting shader, above `main()`:

```glsl
// Section 5: a pixel's centre and its depth, back to world space.
vec3 worldFromDepth(ivec2 pixel, float depth, ivec2 size)
{
    vec2 ndc   = (vec2(pixel) + 0.5) / vec2(size) * 2.0 - 1.0;   // -1..1, y down like Vulkan's
    vec4 world = frame.inverseViewProjection * vec4(ndc, depth, 1.0);
    return world.xyz / world.w;
}
```

**How exact is it?** As exact as the depth: `D32_SFLOAT` tells surfaces 6 mm
apart at 100 m (Chapter 10 section 2), and the rebuilt position is that close
to the interpolated one. For shading that is nothing. For shadows it can move a
lookup across a shadow-map texel's edge at a distant shadow boundary, which is
one of the places section 7 finds the two paths differing by a few levels.

---

## 6. The lighting pass

**This is the lighting set, `DeferredShading::Initialize`, `EnableDeferred`,
the lighting shader's first version, and `RecordLighting` with its barriers.**

### A descriptor set of its own

The lighting shader needs four things set 0 already holds — `FrameData`, the
light buffer, the shadow data, and the shadow map — and five images set 0 does
not. It cannot simply bind set 0: a descriptor set layout lists, per binding,
which shader stages may read it, and set 0's say vertex and fragment. Adding
the compute stage there would change the layout every scene pipeline since
Chapter 10 was built against, for the sake of one reader.

So the lighting pass gets a set of its own that points at **the same buffers**,
and it reuses **set 0's binding numbers** for them. That is the trick that keeps
the shader short: `FrameBlock.glsl`, `Lights.glsl`, and `Shadows.glsl` declare
`set = 0, binding = 0`, `1`, `3`, and `4`, and the lighting pipeline's layout
puts this set at set number 0, so all three includes work unchanged in a compute
shader. Binding 2, the instance buffer, is simply absent: a layout may skip
numbers. The pass's own images take the numbers after:

| Binding | Type | Holds | Written |
| --- | --- | --- | --- |
| 0 | uniform buffer | `FrameData` | once per set, in `Initialize` |
| 1 | storage buffer | the light buffer | once per set |
| 3 | uniform buffer | `ShadowData` | once per set |
| 4 | combined image sampler | the cascaded shadow map, with its comparison sampler | once |
| 5, 6, 7 | combined image sampler | the three G-buffer images | every `Resize` |
| 8 | combined image sampler | the scene depth | every `Resize` |
| 9 | storage image | the scene target, read and then written | every `Resize` |

There is one set per frame in flight, like set 0, because bindings 0, 1, and 3
are per-frame buffers.

**Why samplers for the G-buffer, and a storage image for the target.** An
`_SRGB` format can never be a storage image (Chapter 20 section 4), so the base
color has to be read through a sampler; the others follow for uniformity.
`texelFetch(sampler, ivec2, 0)` reads exactly one texel at integer coordinates,
with no filtering and no mip selection, so the sampler's settings never matter
— `Initialize` creates a nearest, clamp-to-edge one that says so. The sRGB decode
still happens: it belongs to the format, not to filtering. The scene target is
written, so it is a storage image in `GENERAL`, as Chapter 20 section 10's
display pass wrote it.

### The shared definitions

The lighting pass's push constant is a view to draw — section 7's debug views —
and its constants are a tile size and a list size, which Part 2 uses. They join
`SharedShaderTypes.h` after Chapter 21's indirect command structs, and the
namespace's closing brace moves below them, as each chapter's block has done:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 22: deferred shading. The lighting pass's
   workgroup is one tile of TILE x TILE pixels; 8 x 8 is Chapter 20's 64 invocations. */
#define DEFERRED_TILE_SIZE 8

/* The most lights one tile's list can hold: every light the buffer can (SceneRenderer's MAX_LIGHTS). */
#define DEFERRED_MAX_TILE_LIGHTS 256

/* What the lighting pass writes: the lit image, or one of the G-buffer's debug views. */
#define DEFERRED_VIEW_LIT         0u
#define DEFERRED_VIEW_BASE_COLOR  1u
#define DEFERRED_VIEW_NORMAL      2u
#define DEFERRED_VIEW_ROUGH_METAL 3u   /* roughness in red, metallic in green */
#define DEFERRED_VIEW_DEPTH       4u
#define DEFERRED_VIEW_LIGHT_COUNT 5u   /* lights per tile, as a heat map */
#define DEFERRED_VIEW_UNLIT       6u   /* the G-buffer pass's own color: Chapter 15's Normals and Mip level */

/* The lighting pass's push constant. */
struct DeferredParameters
{
    uint view;       /* DEFERRED_VIEW_* */
    uint padding0;
    uint padding1;
    uint padding2;
};

#ifdef __cplusplus
    static_assert(sizeof(DeferredParameters) == 16, "DeferredParameters layout drifted.");
    }
#endif
```

**This is `DeferredShading::Initialize`.** In order: the nearest sampler, the
set layout, a pool and one set per frame in flight, the four bindings that never
change, then the pipeline layout — the one set and the push constant — and the
compute pipeline. Most of it is Chapter 20 section 4's descriptor pattern, and
Appendix B has the whole function. Two parts are this chapter's. The layout's
binding array, which is the table above in code:

```cpp
    // DeferredShading::Initialize, after the sampler (Chapter 22).
    // The lighting set: set 0's bindings 0, 1, 3, and 4 under their own numbers, so Chapters 10, 16,
    // and 17's includes work unchanged in a compute shader; then this chapter's five images.
    const VkShaderStageFlags compute = VK_SHADER_STAGE_COMPUTE_BIT;
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 3, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 4, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 5, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 6, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 7, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 8, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 9, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          .descriptorCount = 1, .stageFlags = compute },
    };
```

and, once the sets exist, the writes that point bindings 0 to 4 at set 0's own
buffers and shadow map. `LightingInputs` carries one frame in flight's three
buffers; the shadow map is one image for both frames, so it is passed once:

```cpp
    // Bindings 0 to 4 never change: the same buffers and shadow map that set 0 points at.
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        const VkWriteDescriptorSet writes[] = {
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 0,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .pBufferInfo = &inputs[i].frame },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 1,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &inputs[i].lights },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 3,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .pBufferInfo = &inputs[i].shadows },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 4,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &shadowMap },
        };
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(std::size(writes)), writes, 0, nullptr);
    }
```

The function builds its pipeline with Chapter 20 section 2's `createComputePipeline`:

```cpp
    m_lightingPipeline = createComputePipeline(m_context.device, m_pipelineCache,
                                               "Scene/DeferredLighting.comp.spv", m_lightingLayout);
```

**This is `DeferredShading::Resize`, second half**: bindings 5 to 9, rewritten
for the new images and the engine's new targets. Each descriptor names the
layout its image will be in *while the lighting pass runs* — read-only for the
four sampled ones, `GENERAL` for the storage image — which is what the barriers
below arrange:

```cpp
    // Bindings 5 to 9: the layouts each image is in while the lighting pass runs (section 6).
    const VkDescriptorImageInfo images[] = {
        { .sampler = m_sampler, .imageView = m_views[GBufferBaseColorMetallic], .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = m_sampler, .imageView = m_views[GBufferNormal],            .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = m_sampler, .imageView = m_views[GBufferSurface],           .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = m_sampler, .imageView = targets.depthView,                 .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = VK_NULL_HANDLE, .imageView = targets.colorView,            .imageLayout = VK_IMAGE_LAYOUT_GENERAL },
    };
    for (const VkDescriptorSet set : m_sets)
    {
        std::array<VkWriteDescriptorSet, std::size(images)> writes{};
        for (uint32_t i = 0; i < writes.size(); ++i)
        {
            writes[i] = {
                .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                .dstSet          = set,
                .dstBinding      = 5 + i,
                .descriptorCount = 1,
                .descriptorType  = i == 4 ? VK_DESCRIPTOR_TYPE_STORAGE_IMAGE : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                .pImageInfo      = &images[i],
            };
        }
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    }
    return InitializationResult::success();
}
```

`Resize` runs behind a `vkDeviceWaitIdle` (Chapter 09 section 2), so rewriting
a set no frame is using is safe. `Shutdown` destroys everything in reverse
(Appendix B).

**This is `SceneRenderer::EnableDeferred`.** A demo that offers the deferred
path calls it once, in `Setup`, after `Initialize`; a demo that does not pays
nothing. It hands `DeferredShading` the buffers set 0 already points at, then
builds section 4's pipelines. Its first lines are section 9's decision, at more
than one sample; the `static_assert` ties the shader's list size, section 8's,
to the light buffer's:

```cpp
InitializationResult SceneRenderer::EnableDeferred()
{
    // Section 9: the deferred path is single-sample. At more than one sample, offer only forward.
    if (m_formats.samples != VK_SAMPLE_COUNT_1_BIT)
    {
        Log::info("Deferred shading needs MSAA at 1x; this scene draws forward.");
        return InitializationResult::success();
    }

    // The lighting set points at set 0's own buffers and shadow map (section 6).
    static_assert(DEFERRED_MAX_TILE_LIGHTS >= MAX_LIGHTS, "A tile's list must be able to hold every light.");
    std::array<LightingInputs, FRAMES_IN_FLIGHT> inputs{};
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        inputs[i] = LightingInputs{
            .frame   = { .buffer = m_frameBuffers[i].buffer, .offset = 0, .range = sizeof(shared::FrameData) },
            .lights  = { .buffer = m_lightBuffers[i].buffer, .offset = 0, .range = VK_WHOLE_SIZE },
            .shadows = m_shadows.DataBufferInfo(i),
        };
    }
    if (auto result = m_deferred.Initialize(m_context, m_pipelineCache, m_formats.color, inputs,
                                            m_shadows.MapImageInfo());
        !result)
    {
        return result;
    }
    return CreateGBufferPipelines();
}
```

`Shutdown`, after Chapter 11's `DestroyPipelines()` line, shuts it down:

```cpp
m_deferred.Shutdown();        // Chapter 22: the G-buffer and the lighting pass, if EnableDeferred ran
```

### The shader, first version

**This is `Shaders/Scene/DeferredLighting.comp.glsl`** as Part 1 writes it: one
invocation per pixel, in workgroups of 8 x 8, which Part 2 turns into tiles.
Each invocation finds its surface from the depth, reads its G-buffer back into a
`SurfaceSample` — undoing section 2's packing field by field — and runs
`Mesh.frag.glsl`'s light loop, unchanged, starting from what the G-buffer pass
already wrote into the scene target:

```glsl
// Shaders/Scene/DeferredLighting.comp.glsl - Chapter 22, Part 1: lights each pixel from the G-buffer,
// with every light, as the forward pass does.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Color.glsl"           // srgbToLinear, for the debug views
#include "FrameBlock.glsl"      // binding 0, as in set 0
#include "PreviewSurface.glsl"
#include "Lights.glsl"          // binding 1, as in set 0
#include "Shadows.glsl"         // bindings 3 and 4, as in set 0
#include "Octahedral.glsl"

layout(local_size_x = DEFERRED_TILE_SIZE, local_size_y = DEFERRED_TILE_SIZE, local_size_z = 1) in;

// The lighting set's own bindings, after set 0's numbers (section 6).
layout(set = 0, binding = 5) uniform sampler2D gbufferBaseColorMetallic;
layout(set = 0, binding = 6) uniform sampler2D gbufferNormal;
layout(set = 0, binding = 7) uniform sampler2D gbufferSurface;
layout(set = 0, binding = 8) uniform sampler2D sceneDepth;
layout(set = 0, binding = 9, rgba16f) uniform image2D sceneColor;   // read, then written

layout(push_constant) uniform PushConstants
{
    DeferredParameters parameters;
};

// Section 5's worldFromDepth goes here, above main().

void main()
{
    ivec2 pixel = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size  = imageSize(sceneColor);
    if (pixel.x >= size.x || pixel.y >= size.y) { return; }   // the dispatch rounds up (Chapter 20 section 3)

    // Is there a surface here? 1.0 is the depth's clear value: nothing was drawn, and the clear color stays.
    float depth = texelFetch(sceneDepth, pixel, 0).r;
    if (depth == 1.0 || parameters.view == DEFERRED_VIEW_UNLIT) { return; }
    vec3  worldPosition = worldFromDepth(pixel, depth, size);
    float viewDepth     = -(frame.view * vec4(worldPosition, 1.0)).z;

    vec4 baseColorMetallic = texelFetch(gbufferBaseColorMetallic, pixel, 0);   // the sRGB format decodes
    vec4 packedSurface     = texelFetch(gbufferSurface, pixel, 0);
    SurfaceSample s;
    s.baseColor = baseColorMetallic.rgb;
    s.metallic  = baseColorMetallic.a;
    s.roughness = packedSurface.r;
    s.ior       = 1.0 + packedSurface.g * 2.0;
    s.brdf      = frame.brdf;   // the same switch as the forward path's
    vec3 N               = decodeOctahedral(texelFetch(gbufferNormal, pixel, 0).xy);
    vec3 geometricNormal = decodeOctahedral(packedSurface.ba * 2.0 - 1.0);
    vec3 V               = normalize(frame.cameraPosition.xyz - worldPosition);

    // Mesh.frag.glsl's loop, unchanged: every light in the buffer.
    vec3 color = imageLoad(sceneColor, pixel).rgb;   // the G-buffer pass's ambient light and emission
    for (uint i = 0u; i < lightHeader.count; ++i)
    {
        vec3 L;
        vec3 irradiance = lightIrradiance(lights[i], worldPosition, L);
        if (int(i) == lightHeader.sunIndex)
        {
            irradiance *= sunShadow(worldPosition, geometricNormal, viewDepth);
        }
        color += evaluatePreviewSurface(s, N, V, L, irradiance);
    }
    color *= cascadeDebugColor(viewDepth);

    // Section 7's views: what the G-buffer holds, as Chapter 15's normals view shows a normal.
    switch (parameters.view)
    {
    case DEFERRED_VIEW_BASE_COLOR:  color = s.baseColor;                                          break;
    case DEFERRED_VIEW_NORMAL:      color = srgbToLinear(N * 0.5 + 0.5);                           break;
    case DEFERRED_VIEW_ROUGH_METAL: color = srgbToLinear(vec3(s.roughness, s.metallic, 0.0));      break;
    case DEFERRED_VIEW_DEPTH:       color = srgbToLinear(vec3(viewDepth / (viewDepth + 10.0)));     break;
    default:                                                                                       break;
    }
    imageStore(sceneColor, pixel, vec4(min(color, vec3(64000.0)), 1.0));
}
```

What to notice:

- **`frame.brdf` is read here as it is in `Mesh.frag.glsl`**, so Chapter 15
  section 9's BRDF switch works on both paths. That is why the switch lives in
  `FrameData` rather than in a specialization constant baked into the mesh
  pipelines.
- **The sun's shadow and the cascade tint are applied exactly as in Chapter 17
  section 9**: only the sun's irradiance is multiplied by `sunShadow`, along the
  geometric normal, and the tint multiplies the total.
- **`imageLoad` before `imageStore` on the same pixel** is safe without any
  barrier: one invocation reads and writes its own texel, and no other
  invocation touches it.
- **The final clamp** is `Mesh.frag.glsl`'s: half float holds 65504 at most.

### The barriers in and out

**This is `DeferredShading::RecordLighting`.** Five barriers before the dispatch,
two after:

```cpp
void DeferredShading::RecordLighting(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SceneTargets& targets,
                                     const shared::DeferredParameters& parameters)
{
    // In (section 6): the G-buffer and the depth, drawn by the G-buffer pass, about to be sampled by the
    // lighting pass; the scene target, about to be read and rewritten by it as a storage image.
    for (const VkImage image : m_images)
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // One workgroup per tile; the last row and column of tiles may hang off the image (Chapter 20 section 3).
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_lightingPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_lightingLayout,
                            0, 1, &m_sets[frameIndex], 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_lightingLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);
    vkCmdDispatch(commandBuffer, groupCount(targets.extent.width, DEFERRED_TILE_SIZE),
                  groupCount(targets.extent.height, DEFERRED_TILE_SIZE), 1);

    // Out (section 6): back to what endScenePass leaves. The color's next user loads it as an attachment;
    // the depth's is a depth test, after this pass's reads.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

The ones in, through the three questions:

| Image | Q1: what finishes, then what waits | Q2: flushed, then made visible | Q3: layout |
| --- | --- | --- | --- |
| G-buffer, each of three | the G-buffer pass's attachment writes, `COLOR_ATTACHMENT_OUTPUT`; then the lighting pass, `COMPUTE_SHADER` | `COLOR_ATTACHMENT_WRITE`; then `SHADER_SAMPLED_READ` | `COLOR_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Scene depth | the depth tests, `EARLY_ \| LATE_FRAGMENT_TESTS`; then `COMPUTE_SHADER` | `DEPTH_STENCIL_ATTACHMENT_WRITE`; then `SHADER_SAMPLED_READ` | `DEPTH_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL` |
| Scene target | the G-buffer pass's writes to location 0, `COLOR_ATTACHMENT_OUTPUT`; then `COMPUTE_SHADER` | `COLOR_ATTACHMENT_WRITE`; then `SHADER_STORAGE_READ \| SHADER_STORAGE_WRITE`: the pass reads what is there and writes the sum | `COLOR_ATTACHMENT_OPTIMAL` to `GENERAL`, the storage layout |

The depth row is Chapter 04's "Scene depth sampled by compute" row without the
resolve stage in its source: the G-buffer pass is always one sample, so its
depth was last written by the depth tests, never by a resolve.

The two out exist for the contract in "What you are actually writing": after
`RecordLighting`, the scene color and depth are where `endScenePass` leaves
them — color in `COLOR_ATTACHMENT_OPTIMAL`, depth in `DEPTH_ATTACHMENT_OPTIMAL`.

| Image | Q1 | Q2 | Q3 |
| --- | --- | --- | --- |
| Scene target | the lighting pass, `COMPUTE_SHADER`; then whatever loads it as an attachment, `COLOR_ATTACHMENT_OUTPUT` | `SHADER_STORAGE_WRITE`; then `COLOR_ATTACHMENT_READ \| COLOR_ATTACHMENT_WRITE` | `GENERAL` to `COLOR_ATTACHMENT_OPTIMAL` |
| Scene depth | the lighting pass's reads, `COMPUTE_SHADER`; then the next depth tests | `NONE`, a read leaves nothing; then `DEPTH_STENCIL_ATTACHMENT_READ \| WRITE` | `SHADER_READ_ONLY_OPTIMAL` to `DEPTH_ATTACHMENT_OPTIMAL` |

Whatever comes next starts its own barrier from `COLOR_ATTACHMENT_OUTPUT` with
`COLOR_ATTACHMENT_WRITE`, as if a rendering scope had last written the image —
`handBackSceneTarget`'s defaults, or section 10's second scope. That is
correct because the two barriers **chain**: the next barrier's source stage,
`COLOR_ATTACHMENT_OUTPUT`, is this one's destination stage, so it is ordered
after this one, and this one after the compute writes (Chapter 21 section 5
draws the same chain for the depth). The depth's barrier is the return trip of
Chapter 04's "Scene depth sampled by compute" row, unchanged.

The dispatch is one workgroup per 8 x 8 block of pixels, rounded up with
Chapter 20's `groupCount`; the shader's guard skips the invocations past the
right and bottom edges.

**This is `SceneRenderer::RecordLighting`.** It turns the renderer's state into
the push constant: the debug view the demo asked for, unless Chapter 15's
Normals or Mip level view is on — those were finished in the G-buffer pass, and
`DEFERRED_VIEW_UNLIT` tells the lighting pass to leave them alone:

```cpp
void SceneRenderer::RecordLighting(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SceneTargets& targets)
{
    // Chapter 15's Normals and Mip level views are finished in the G-buffer pass; the lighting pass leaves them.
    const bool finished = m_shading == ShadingMode::Normals || m_shading == ShadingMode::MipLevel;
    const shared::DeferredParameters parameters{
        .view     = finished ? DEFERRED_VIEW_UNLIT : m_deferredView,
        .padding0 = 0,
        .padding1 = 0,
        .padding2 = 0,
    };
    m_deferred.RecordLighting(commandBuffer, frameIndex, targets, parameters);
}
```

### The shadow map has a second reader

Chapter 17 section 5 gave the shadow map two barriers, and both name the one
stage that read it: the scene pass's `FRAGMENT_SHADER`. The lighting pass now
samples it from `COMPUTE_SHADER`, which neither covers. A compute shader is not
"after" the fragment shader in any pipeline, so naming one does not cover the
other (Chapter 04 section 5). Both barriers gain the stage, in `ShadowMaps::Record`. The one before the
shadow pass:

```cpp
    // ---- GPU. Section 5's first barrier: last frame's scene pass sampled every layer in its fragment
    // shader. Overwriting needs only an execution dependency on that read; UNDEFINED discards. ----
    // Chapter 22: or its deferred lighting pass sampled it, in a compute shader.
    transitionImage(commandBuffer, m_image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
```

and the one after it:

```cpp
    // Section 5's second barrier: every layer's depth writes, visible to the scene pass's fragment shader
    // and, from Chapter 22, to the deferred lighting pass's compute shader.
    transitionImage(commandBuffer, m_image,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
```

Q2 and Q3 are unchanged; only Q1 grows. In a forward frame no compute shader
ran, so the extra stage waits for nothing. This is a barrier the layer can
check: with the shader-access setting on (Chapter 20 section 5's table), leaving
`COMPUTE_SHADER` out of the second one is reported as a
`SYNC-HAZARD-READ-AFTER-WRITE` at the lighting pass's `vkCmdDispatch`, for
binding 4, on the first deferred frame with a sun.

---

## 7. The switch, and seeing the G-buffer

**This is the viewer's half: its members, `Setup`, `Resize`, `SwitchToFile`,
`Record`, and the "Rendering" panel.**

The choice of path is CPU state, like Chapter 15's BRDF: it lives in the demo
object and survives a re-`Setup`. So does the debug view.

```cpp
// Demos/UsdViewer/UsdViewerDemo.h - Chapter 22's first additions. Private, after DrawPanel:
    void DrawRenderingPanel();   // section 7

// Beside m_extent:
    vulkan_graphics::SceneTargets m_targets;   // Chapter 22: the last Resize's, for SwitchToFile

// At the end of the members. CPU state: the choices survive a re-Setup.
    vulkan_graphics::RenderPath m_renderPath   = vulkan_graphics::RenderPath::Forward;
    uint32_t                    m_deferredView = DEFERRED_VIEW_LIT;
```

`Setup` asks for the deferred path right after the scene renderer is
initialized:

```cpp
    // UsdViewerDemo::Setup (Chapter 22): right after SceneRenderer::Initialize succeeds.
    if (auto result = m_sceneRenderer.EnableDeferred(); !result) { return result; }
```

`Resize` passes the targets on, and keeps a copy:

```cpp
InitializationResult UsdViewerDemo::Resize(const vulkan_graphics::SceneTargets& targets)
{
    m_extent  = targets.extent;   // Update builds the culling frustum before Record sees the targets
    m_targets = targets;          // Chapter 22: SwitchToFile resizes too
    return m_sceneRenderer.Resize(targets);   // Chapter 22: the G-buffer follows the window
}
```

The copy is for `SwitchToFile`, Chapter 14's own Teardown-then-Setup. Until now
nothing the viewer owned depended on the window, so it never called `Resize`;
the G-buffer does, and without the call the first deferred frame after a file
switch would draw into images that no longer exist. The function's last lines
become Chapter 09's order, `Setup` then `Resize`:

```cpp
    // Chapter 22: Setup, then Resize, the order Chapter 09's switchDemo uses: the G-buffer is window-sized.
    InitializationResult result = Setup(m_context);
    if (result) { result = Resize(m_targets); }
    if (!result)
    {
        Log::error(result.message());
        m_status = result.message();
        m_ready  = false;   // Record then only clears, as after a failed Setup
    }
}
```

**`Record`.** Chapter 11's three lines that drew the scene become a choice
between them and the two deferred calls. The deferred path is used only if the
demo asked for it *and* the renderer could build it:

```cpp
    // UsdViewerDemo::Record (Chapter 22). After SetFrontFaceFlipped:
    m_sceneRenderer.SetDeferredView(m_deferredView);

    // In place of Chapter 11's beginScenePass, RecordDraws, and endScenePass. Both paths leave the scene
    // color and depth the way endScenePass does, so everything after this block is the same for both.
    const bool deferred = m_renderPath == vulkan_graphics::RenderPath::Deferred && m_sceneRenderer.DeferredAvailable();
    if (deferred)
    {
        m_sceneRenderer.RecordGBufferPass(commandBuffer, frame.frameIndex, frame.targets, clearColor);
        m_sceneRenderer.RecordLighting(commandBuffer, frame.frameIndex, frame.targets);
    }
    else
    {
        vulkan_graphics::beginScenePass(commandBuffer, frame.targets, &clearColor);
        m_sceneRenderer.RecordDraws(commandBuffer, frame.frameIndex);
        vulkan_graphics::endScenePass(commandBuffer);
    }
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
```

Switching needs nothing else. Both paths' pipelines exist from `Setup` on, the
G-buffer's barriers start from `UNDEFINED`, and every image's first barrier in
a frame names whatever stage last touched it on either path, so the next frame
may take the other path.

### The panel

**This is `DrawRenderingPanel`**, called from `Update` beside Chapter 19's
`drawInstancingPanel(m_sceneRenderer, m_lastFrameIndex);`:

```cpp
    DrawRenderingPanel();   // Chapter 22
```

It is a member rather than a free function because it reads the scene
renderer's `DeferredAvailable()`:

```cpp
// Chapter 22 section 7: the path, and the G-buffer views.
void UsdViewerDemo::DrawRenderingPanel()
{
    ImGui::SetNextWindowPos(ImVec2(360.0f, 225.0f), ImGuiCond_FirstUseEver);   // under "Instancing"
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until you open it
    if (ImGui::Begin("Rendering", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        // The choice is kept even while MSAA is on; it applies again at 1x (section 9).
        const bool available = m_sceneRenderer.DeferredAvailable();
        int path = static_cast<int>(m_renderPath);
        ImGui::RadioButton("Forward", &path, 0);
        ImGui::SameLine();
        ImGui::BeginDisabled(!available);
        ImGui::RadioButton("Deferred", &path, 1);
        ImGui::EndDisabled();
        m_renderPath = static_cast<vulkan_graphics::RenderPath>(path);
        if (!available)
        {
            ImGui::TextDisabled("Deferred shading needs MSAA at 1x: drawing forward.");
        }

        // What the lighting pass writes. Only the deferred path has a G-buffer to show.
        ImGui::BeginDisabled(!available || m_renderPath != vulkan_graphics::RenderPath::Deferred);
        int view = static_cast<int>(m_deferredView);
        ImGui::RadioButton("Lit", &view, DEFERRED_VIEW_LIT);
        ImGui::SameLine();
        ImGui::RadioButton("Base color", &view, DEFERRED_VIEW_BASE_COLOR);
        ImGui::SameLine();
        ImGui::RadioButton("Normal", &view, DEFERRED_VIEW_NORMAL);
        ImGui::RadioButton("Roughness, metallic", &view, DEFERRED_VIEW_ROUGH_METAL);
        ImGui::SameLine();
        ImGui::RadioButton("Depth", &view, DEFERRED_VIEW_DEPTH);
        m_deferredView = static_cast<uint32_t>(view);
        ImGui::EndDisabled();
    }
    ImGui::End();
}
```

Like "Shadows" and "Instancing", the window opens as a title bar; click the title to open it.

`BeginDisabled` greys a widget out and ignores clicks on it, so the deferred
button cannot be picked when the renderer did not build the path.

### Reading the debug views

Each view replaces the lit color with one field of the G-buffer, chosen in the
shader's `switch`. They are made to be read with the composite pass in Raw mode
at 0 stops (Chapter 16 section 6), which encodes linear values to sRGB:

- **Base color** writes the linear base color, so the screen shows it as
  authored — a texture looks like the texture.
- **Normal** writes `srgbToLinear(N * 0.5 + 0.5)`, Chapter 15's normals view:
  after the encode, the screen shows the normal's components mapped from −1..1
  to 0..1. A floor facing up is (0.5, 1, 0.5), pale green; a wall facing +Z is
  lavender.
- **Roughness, metallic** shows roughness in red and metallic in green, also
  decoded first, so a byte on screen is the stored value: a floor at roughness
  0.9 reads about 230 in red.
- **Depth** shows *view* depth, not the depth buffer's value. The stored depth is
  0.99 for everything past 10 m (Chapter 10 section 2's table), so a picture of
  it is white. `d / (d + 10)` maps 0 m to black, 10 m to mid grey, and 90 m to
  0.9, whatever the scene's size.

On `MaterialTest.usda` the base color view shows the checkerboard and the
leaf's green with no shading at all; the normal view shows the sixteen bumps of
`BumpsPanel` and a flat green floor; the roughness-metallic view shows the floor
red (230: roughness 0.9) and the grey-band panel yellow-green (128 and 255:
roughness 0.5, metallic 1), a black metal that only emits.

### Do the two paths agree?

They should draw the same picture, and they do, to within rounding. If you take
a screenshot of each path from the same camera, with the panels hidden, and
compare them pixel by pixel, most pixels match exactly; where they differ, it is
by a level or two out of 255, except at a handful of pixels on smooth
silhouettes. Each difference has a reason in section 2's table:

- **One level everywhere**, in bands: the base color stored in 8 bits and the
  ambient light rounded to half float before the light loop adds to it, then
  rounded again to 8 bits on screen.
- **A few levels along distant shadow edges** in `ShadowTest.usda`: the position
  rebuilt from depth (section 5) and the 8-bit geometric normal move a shadow
  lookup by a fraction of a texel, and near an edge that flips a filter tap.
- **A handful of pixels on sphere silhouettes** in `ManyLights.usda`: where
  N · V approaches 0, GGX's specular term (Chapter 15's line `(c)`) divides by
  it, and on a smooth surface its geometry term cancels little of that, so the
  normal's 0.03° rounding is magnified into a visible change. Chapter 15's
  Blinn-Phong at roughness 0 shows the same thing in `MaterialSweep.usda`,
  where its shininess of hundreds of thousands turns the same rounding into
  many levels at the pinpoint highlight.

Chapter 15's own debug views, Normals and Mip level, and the Lambert BRDF match
exactly or to one level.

---

## Checkpoint

Run the USD viewer with validation on.

- [ ] The "Rendering" panel switches between **Forward** and **Deferred** on
      `MaterialTest.usda`, `LightTest.usda`, and `ShadowTest.usda`, and the
      picture does not visibly change — including under each of Chapter 15's
      three BRDFs and its four shading views.
- [ ] In Deferred, the **Base color**, **Normal**, **Roughness, metallic**, and
      **Depth** views show what the reading guide above describes on
      `MaterialTest.usda`.
- [ ] Resizing the window, and picking another file, keep drawing in Deferred,
      without validation messages.
- [ ] Synchronization validation is silent in both paths, with the
      shader-access setting on (Chapter 02 section 2).

---

# Part 2 — Tiles, and what each path costs (sections 8-12)

Part 1's lighting pass does the forward pass's work in a different place: every
pixel still loops over every light. On `ManyLights.usda` that makes the two
paths cost about the same. Part 2 gives each 8 x 8 tile of the screen its own
short list of lights, which is where deferred shading earns its G-buffer; then
it settles what happens under MSAA, draws something forward on top of the
deferred image, and times both paths.

---

## 8. Tiled light culling

**This is the tile half of `DeferredLighting.comp.glsl`, and the "Lights per
tile" view.**

A light whose range does not reach a part of the world contributes exactly zero
there: Chapter 16 section 5's window makes `lightIrradiance` return 0 beyond
`range`. So if a tile's pixels all show surfaces out of a light's reach, the
light can be skipped for the whole tile — and the decision is made once per tile
instead of once per pixel.

> **Jump:** Part 1's invocations were independent: each lit its own pixel. Now
> the 64 invocations of a workgroup cooperate on one tile, as Chapter 20 section
> 6's Life step cooperated on one block of cells: they build two numbers and a
> list together in shared memory, wait for each other with `barrier()`, and only
> then light their own pixels from the shared list. Keep the three phases
> apart — measure the tile, list its lights, light the pixels — and remember
> that nobody may return before the last `barrier()`.

### What a tile sees

From the camera, an 8 x 8 tile of pixels shows a thin four-sided pyramid of the
world, with its tip at the eye. Its four sides are planes through the eye. Its
near and far ends are not the camera's near and far planes but the nearest and
farthest *surfaces* the tile's pixels actually show, because nothing nearer or
farther is lit in this tile. A light's reach is a sphere of radius `range`
around it. The light can matter to the tile only if its sphere is not wholly
outside any of those six walls.

```text
 seen from the side: the tile's pixels look out between two of its four side planes

                                    │                    │
                            ╱───────┼────────────────────┼──── one side plane
                       ╱            │░░░░░░░░░░░░░░░░░░░░│
                  ╱                 │░░░░░░░░░░░░░░░░░░░░│
             ╱                      │░░ what the tile ░░░│
   eye ●                            │░░ can light ░░░░░░░│
             ╲                      │░░░░░░░░░░░░░░░░░░░░│
                  ╲                 │░░░░░░░░░░░░░░░░░░░░│
                       ╲            │░░░░░░░░░░░░░░░░░░░░│
                            ╲───────┼────────────────────┼──── the opposite one
                                    │                    │
                           nearest surface    farthest surface
```

### Phase 1: the tile's depth range

Each invocation computes its pixel's view depth, as Part 1 did, and the tile's
nearest and farthest are the minimum and maximum over its 64 pixels. Shared
`uint` variables and `atomicMin`/`atomicMax` find them (Chapter 20 section 8:
atomics work on shared variables too), with one trick: atomics act on integers,
and these are floats.

**Positive floats sort like their bit patterns.** A 32-bit float stores its
exponent above its fraction, so for positive values a larger float is also a
larger integer when its bits are read as one: 0.75 is `0x3F400000`, 2.5 is
`0x40200000`, 10.0 is `0x41200000`. `floatBitsToUint` reads the bits,
`atomicMin` on them finds the smallest float, and `uintBitsToFloat` turns it
back. View depths are positive — everything visible is in front of the camera —
so the trick holds. Pixels where nothing was drawn do not vote.

### Phase 2: the tile's four side planes

Chapter 12 section 9 read the camera's frustum out of the view-projection
matrix's rows: the condition *x* ≥ −*w* is the plane `row3 + row0`. A tile's
left edge is not at −1 but at some *x*<sub>min</sub> in normalized device
coordinates, and the same reasoning gives its plane: *x*/*w* ≥ *x*<sub>min</sub>
is *x* − *x*<sub>min</sub>·*w* ≥ 0, which is the plane
`row0 − xmin · row3`.

Work in view space, so the matrix is the projection alone. Chapter 10 section
2's projection has only two entries in those rows: `row0` is
(*P*<sub>00</sub>, 0, 0, 0) and `row3` is (0, 0, −1, 0). So the four planes are

$$
\text{left: } (P_{00},\ 0,\ x_{\min},\ 0) \qquad
\text{right: } (-P_{00},\ 0,\ -x_{\max},\ 0) \qquad
\text{top: } (0,\ P_{11},\ y_{\min},\ 0) \qquad
\text{bottom: } (0,\ -P_{11},\ -y_{\max},\ 0)
$$

Their fourth number is 0: each passes through the eye, as the picture says.
Normalized, so that `dot(normal, centre)` is a distance in metres (Chapter 12
section 9 said a radius test needs that), a sphere is outside a plane when that
distance is less than minus its radius.

**Worked.** A 1280-pixel-wide window with Chapter 10's 60° vertical field of
view: *t* = tan 30° = 0.577, the aspect is 1.778, so *P*<sub>00</sub> = 1 /
(1.778 × 0.577) = 0.974. The tile in column 80 covers pixels 640 to 647, edges at 640 and 648, so
*x*<sub>min</sub> = 2 · 640/1280 − 1 = 0 and *x*<sub>max</sub> = 2 · 648/1280 − 1
= 0.0125.

- The left plane is (0.974, 0, 0), normalized (1, 0, 0): "*x* ≥ 0", everything
  right of the screen's centre line.
- The right plane is (−0.974, 0, −0.0125), normalized (−0.9999, 0, −0.0128).

A light at view position (0.5, 0.2, −10) with a range of 1 m: against the left
plane, 0.5 ≥ −1, inside. Against the right plane,
−0.9999 · 0.5 − 0.0128 · (−10) = −0.37: its centre is 0.37 m beyond the tile's
right wall (it projects to *x* = 0.974 · 0.5 / 10 = 0.049, right of 0.0125), but
its 1 m reach crosses back over it, so it stays. With a range of 0.3 m it would
be culled.

The depth test is simpler: the light's view depth *d* = −*z*, and it can reach
the tile's slice if *d* + range ≥ nearest and *d* − range ≤ farthest.

**Never wrong, sometimes generous.** Testing the sphere against each plane on
its own can keep a sphere that sits just outside a *corner* of the pyramid,
within reach of two walls but of neither face. That costs a little lighting
work and never changes the picture. What the test never does is drop a light
that reaches the tile — so the image is exactly Part 1's.

### Phase 3: the list

Every invocation tests every 64th light — invocation 5 tests lights 5, 69, 133,
and 197 — and appends the ones that pass. `atomicAdd` on the shared count
returns the slot to write (Chapter 20 section 8), so two invocations appending
at once never collide. The list's capacity is `DEFERRED_MAX_TILE_LIGHTS`, every
light the buffer can hold, so it cannot overflow; `EnableDeferred`'s
`static_assert` keeps the two equal. 256 `uint`s are 1 KB of shared memory, far
under the guaranteed 16 KB (Chapter 20 section 3).

The order of the list is whatever order the atomics ran in. Adding the same
lights in a different order changes a float sum in its last bits, which the
half-float scene target cannot even store.

### The code

Above `worldFromDepth`, the tile's shared state:

```glsl
const uint TILE_INVOCATIONS = DEFERRED_TILE_SIZE * DEFERRED_TILE_SIZE;

// Shared by the tile's 64 invocations (Chapter 20 section 6).
shared uint tileNearest;              // the tile's nearest and farthest view depth, as uint bits
shared uint tileFarthest;
shared uint tileLightCount;
shared uint tileLights[DEFERRED_MAX_TILE_LIGHTS];
```

After it, the test:

```glsl
// Section 8: can `light` reach anything in the tile? Distant lights reach everything. A local light's
// reach is a sphere of its range, tested against the tile's four side planes (through the eye, in view
// space) and its depth span. Never false for a light that reaches the tile; sometimes true for one
// that does not.
bool lightTouchesTile(LightData light, vec4 sidePlanes[4], float nearest, float farthest)
{
    if (light.type == LIGHT_DISTANT) { return true; }

    vec3  centre = (frame.view * vec4(light.position.xyz, 1.0)).xyz;
    float radius = light.shape.y;   // the range: the window in lightIrradiance is 0 beyond it
    for (int i = 0; i < 4; ++i)
    {
        if (dot(sidePlanes[i].xyz, centre) < -radius) { return false; }
    }
    float depth = -centre.z;
    return depth + radius >= nearest && depth - radius <= farthest;
}
```

In `main()`, everything from the first line through `float viewDepth = ...`
— Part 1's guard, depth read, early return, and position — is replaced by the
three phases. The guard becomes a flag, because an invocation past the image's
edge must still reach every `barrier()` (Chapter 20 section 6), and the early
return moves to after the last one:

```glsl
    ivec2 pixel  = ivec2(gl_GlobalInvocationID.xy);
    ivec2 size   = imageSize(sceneColor);
    bool  inside = pixel.x < size.x && pixel.y < size.y;   // no early return: barrier() comes below

    if (gl_LocalInvocationIndex == 0u)
    {
        tileNearest    = floatBitsToUint(3.0e38);
        tileFarthest   = 0u;
        tileLightCount = 0u;
    }
    barrier();

    // 1. This pixel: is there a surface, where is it, and how far in front of the camera.
    float depth         = inside ? texelFetch(sceneDepth, pixel, 0).r : 1.0;
    bool  surface       = depth < 1.0;   // 1.0 is the clear value: nothing was drawn here
    vec3  worldPosition = worldFromDepth(pixel, depth, size);
    float viewDepth     = -(frame.view * vec4(worldPosition, 1.0)).z;
    if (surface)
    {
        // Positive floats sort like their bit patterns, so integer atomics find the float range.
        atomicMin(tileNearest, floatBitsToUint(viewDepth));
        atomicMax(tileFarthest, floatBitsToUint(viewDepth));
    }
    barrier();

    // 2. The tile's lights. Its four side planes come from the projection's rows (Chapter 12 section 9);
    //    every invocation tests every 64th light and appends the ones that pass.
    if (tileFarthest != 0u)   // at least one pixel of the tile has a surface
    {
        vec2  tileMin = vec2(gl_WorkGroupID.xy * DEFERRED_TILE_SIZE) / vec2(size) * 2.0 - 1.0;
        vec2  tileMax = vec2((gl_WorkGroupID.xy + 1u) * DEFERRED_TILE_SIZE) / vec2(size) * 2.0 - 1.0;
        float px      = frame.projection[0][0];
        float py      = frame.projection[1][1];
        vec4  sidePlanes[4] = vec4[](vec4( px, 0.0,  tileMin.x, 0.0),    // x >= tileMin.x
                                     vec4(-px, 0.0, -tileMax.x, 0.0),    // x <= tileMax.x
                                     vec4(0.0,  py,  tileMin.y, 0.0),    // y >= tileMin.y
                                     vec4(0.0, -py, -tileMax.y, 0.0));   // y <= tileMax.y
        for (int i = 0; i < 4; ++i) { sidePlanes[i] /= length(sidePlanes[i].xyz); }

        float nearest  = uintBitsToFloat(tileNearest);
        float farthest = uintBitsToFloat(tileFarthest);
        for (uint i = gl_LocalInvocationIndex; i < lightHeader.count; i += TILE_INVOCATIONS)
        {
            if (lightTouchesTile(lights[i], sidePlanes, nearest, farthest))
            {
                tileLights[atomicAdd(tileLightCount, 1u)] = i;
            }
        }
    }
    barrier();

    // 3. This pixel, lit by the tile's lights. Returning is safe from here: no barrier() follows.
    if (!inside || !surface || parameters.view == DEFERRED_VIEW_UNLIT) { return; }
```

`gl_LocalInvocationIndex == 0u` gives the starting values to one invocation, and
the first `barrier()` makes everyone wait for them. The nearest depth starts at
3 × 10³⁸, close to the largest float, so any real depth is smaller.

Last, the loop walks the tile's list instead of the whole buffer. Its first two
lines become three:

```glsl
    // Mesh.frag.glsl's loop, over the tile's list instead of every light.
    for (uint t = 0u; t < tileLightCount; ++t)
    {
        uint i = tileLights[t];
```

The rest of the loop body is unchanged, `i` included.

### Seeing the tiles

A sixth view colors each tile by its list's length. The color ramp goes after
`lightTouchesTile`, just above `main`:

```glsl
// Section 8: blue for one light, through green, to red at 32 or more; black for none.
vec3 heatColor(uint count)
{
    if (count == 0u) { return vec3(0.0); }
    float t = clamp(float(count) / 32.0, 0.0, 1.0);
    return t < 0.5 ? mix(vec3(0.0, 0.0, 1.0), vec3(0.0, 1.0, 0.0), t * 2.0)
                   : mix(vec3(0.0, 1.0, 0.0), vec3(1.0, 0.0, 0.0), t * 2.0 - 1.0);
}
```

The `switch` gains its case, after `DEFERRED_VIEW_DEPTH`'s:

```glsl
    case DEFERRED_VIEW_LIGHT_COUNT: color = heatColor(tileLightCount);                             break;
```

and the panel its button, after "Depth":

```cpp
        ImGui::SameLine();
        ImGui::RadioButton("Lights per tile", &view, DEFERRED_VIEW_LIGHT_COUNT);
```

On `ManyLights.usda` from the starting camera, the ground near the camera is
green: tiles there keep about 18 lights. Towards the horizon the tiles turn red,
32 or more. Averaged over every pixel that shows a surface, a tile keeps about
25 of the 256 lights — the number section 1 used.

The red band shows the method's weakness. A tile near the horizon contains the
edge of a pillar 10 m away *and* the ground 60 m behind it, so its depth range
is 50 m long, and every light along that whole line of sight passes the test.
Two well-known refinements split that range: **2.5D culling** keeps a bitmask
of which depths in the range actually hold a surface (Harada, 2012), and
**clustered shading** cuts the view into depth slices as well as tiles, a 3D
grid of small boxes each with its own list (Olsson, Billeter, and Assarsson,
2012). Both are the next step, not this chapter's.

Measured on one machine, the tiles cut the lighting pass on `ManyLights.usda`
to about a sixth of what Part 1's every-light loop cost. Section 11 shows the
numbers and says what they are and are not worth.

---

## 9. MSAA, and why the deferred path stays at one sample

**This is `EnableDeferred`'s first lines (section 6), and the panel's
disabled button.**

Chapter 18's MSAA keeps several samples per pixel and runs the fragment shader
once per pixel per triangle; the resolve averages the samples at the end of the
pass. A deferred renderer at 4x would need two things.

**A multisampled G-buffer.** Each sample needs its own surface, because at a
geometric edge the samples of one pixel belong to two different surfaces. At
1440p that is four times section 2's budget: 4 × 16 bytes of G-buffer and depth
per pixel, 236 MB, plus 118 MB for the multisampled scene target — written and
read every frame, on a GPU that section 1 found short of bandwidth already.

**Lighting per sample, at least at edges.** Lighting a pixel once, from sample
0's surface, and writing the result to every sample paints the foreground's
light onto the background's samples at every silhouette — after the resolve, a
bright or dark fringe along every edge, exactly where MSAA was meant to help.
Doing it right means finding the pixels whose samples differ and lighting those
per sample, typically with a second list of edge pixels and a second dispatch.

That is a large amount of machinery for edges, and engines that render deferred
mostly do not build it. They pair deferred shading with **temporal
anti-aliasing** instead (Chapter 18 section 9): one sample per pixel, a slightly
different sub-pixel offset every frame, and a blend with the previous frames.
TAA works on the final lit image, so the G-buffer stays one sample per pixel.

**What this renderer does at more than one sample.** `EnableDeferred` builds
nothing and logs why; `DeferredAvailable()` stays false; the viewer draws
forward, greys out the Deferred button, and says so under it. The choice itself
is kept: set MSAA back to 1x, the demo is set up again (Chapter 18 section 7),
and the deferred path returns. The panel does not force 1x itself: a demo's
button must not change the engine's sample count, and 4x forward against 1x
deferred would compare anti-aliasing, not shading. To compare the two paths,
compare them at 1x.

---

## 10. What stays forward

**This is the hybrid: the light glows, drawn forward after either path, and why
some things are always drawn that way.**

A deferred renderer still draws some things forward, after the lighting pass,
into the same color and depth:

- **Anything blended.** A blended pixel's color depends on what is *behind* it,
  and the G-buffer holds one surface per pixel. Glass, smoke, and Chapter 21's
  particles have to be drawn over the lit image, with depth testing against the
  G-buffer pass's depth so that opaque surfaces still hide them, and without
  depth writes (Chapter 21 section 5). Chapter 15 section 12's transparent
  materials would go here too, if this renderer drew them.
- **Anything with its own way of being lit.** The lighting pass applies one
  model, `evaluatePreviewSurface`, to every pixel. The grass chapters (25-27)
  shade blades with light passing through them and their own highlight, in their
  own pipelines; a deferred engine either stores a material ID in the G-buffer
  and branches on it, or draws such things forward.
- **Anything drawn behind everything.** The sky (Chapter 23) belongs where the
  G-buffer pass drew nothing. On the deferred path those pixels keep the clear
  color through the lighting pass, so the sky goes in a forward pass after
  lighting, with a depth test that passes only where the depth is still its
  clear value of 1.0.
- **Anything that needs samples.** Chapter 18 section 8's alpha-to-coverage
  turns a cutout's edge into coverage; a one-sample G-buffer cannot. Cutout
  leaves in the G-buffer have hard edges, exactly as in a forward pass at 1x.

**The contract makes it free.** `RecordLighting` leaves the scene color and
depth as `endScenePass` does (section 6), so Chapter 21's second rendering
scope works after it unchanged: it starts with the same two barriers whichever
path drew the opaque scene, and the depth it tests against is complete, because
the G-buffer pass wrote all of it.

### Light glows

The viewer gets one blended thing of its own, so that the hybrid exists in this
chapter's code and not only in its prose: a soft glow in each local light's
color, where the light is. They make `ManyLights.usda`'s lights visible, and on
`LightTest.usda` the disk light, lying on the floor, shows half a glow — its
lower half fails the depth test against the floor the G-buffer pass drew.

The shaders are Chapter 21's particle shaders with a light in place of a
particle. Instance *i* is light *i* of the light buffer, read through set 0
binding 1, whose layout lists the vertex stage for exactly this kind of reader
(Chapter 16 section 4):

```glsl
// Shaders/UsdViewer/LightGlow.vert.glsl - Chapter 22: a camera-facing quad at every local light, built
// from gl_VertexIndex and gl_InstanceIndex as Chapter 21 builds a particle. No vertex buffer.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"   // frame.view, frame.projection
#include "Lights.glsl"       // set 0 binding 1: instance i draws lights[i]

layout(location = 0) out vec2 corner;   // -1..1 across the quad
layout(location = 1) out vec3 color;    // linear

const float GLOW_RADIUS     = 0.25;   // metres
const float GLOW_BRIGHTNESS = 2.0;    // at the centre: the light's hue, about as bright as a lit bulb

const vec2 corners[6] = vec2[](vec2(-1.0, -1.0), vec2( 1.0, -1.0), vec2( 1.0,  1.0),
                               vec2(-1.0, -1.0), vec2( 1.0,  1.0), vec2(-1.0,  1.0));

void main()
{
    LightData light = lights[gl_InstanceIndex];
    corner = corners[gl_VertexIndex];

    // The light's color, scaled so its brightest channel is GLOW_BRIGHTNESS: a dim lamp still shows.
    vec3 emission = light.emission.rgb;
    color = emission / max(max(emission.r, emission.g), max(emission.b, 1e-6)) * GLOW_BRIGHTNESS;

    // A sun is everywhere and nowhere: put its quad past the far plane, where clipping removes it.
    if (light.type == LIGHT_DISTANT)
    {
        gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
        return;
    }

    // Offset in view space, where the camera's right and up are +X and +Y (Chapter 21 section 5).
    vec4 centre = frame.view * vec4(light.position.xyz, 1.0);
    centre.xy  += corner * GLOW_RADIUS;
    gl_Position = frame.projection * centre;
}
```

```glsl
// Shaders/UsdViewer/LightGlow.frag.glsl - Chapter 22: a soft round glow, added to what is there.
#version 450

layout(location = 0) in  vec2 corner;
layout(location = 1) in  vec3 color;
layout(location = 0) out vec4 outColor;

void main()
{
    // 1 at the centre, 0 at the circle's edge and beyond, as Chapter 21's particles fade.
    float falloff = max(1.0 - dot(corner, corner), 0.0);
    outColor = vec4(color * falloff * falloff, 0.0);   // additive blending: alpha is not used
}
```

A distant light has no position, so its quad is put where clipping removes it:
*z* = 2 with *w* = 1 is past the far plane. That keeps the draw one call for every
light, without the CPU picking out the local ones.

The pipeline: set 0 alone, additive blending, depth tested and not written, and
**one sample**, because it draws after the scene pass, on the resolved images,
as Chapter 21's particles do:

```cpp
// Demos/UsdViewer/UsdViewerDemo.h - Chapter 22, the glows. Private, after DrawRenderingPanel:
    InitializationResult CreateGlowPipeline();                                           // section 10
    void                 RecordLightGlows(VkCommandBuffer commandBuffer, const RecordContext& frame);   // section 10

// With the other Chapter 22 members. CPU state:
    bool             m_lightGlows   = true;
// GPU objects: Setup to Teardown.
    VkPipelineLayout m_glowLayout   = VK_NULL_HANDLE;   // set 0 only
    VkPipeline       m_glowPipeline = VK_NULL_HANDLE;
```

```cpp
InitializationResult UsdViewerDemo::CreateGlowPipeline()
{
    const VkDescriptorSetLayout frameSetLayout = m_sceneRenderer.FrameSetLayout();
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType          = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 1,
        .pSetLayouts    = &frameSetLayout,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_glowLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the light glows.");
    }
    const vulkan_graphics::GraphicsPipelineDesc desc{
        .vertexShader   = "UsdViewer/LightGlow.vert.spv",
        .fragmentShader = "UsdViewer/LightGlow.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = false,
        .depthCompare   = VK_COMPARE_OP_LESS,
        .blend          = vulkan_graphics::BlendMode::Additive,
        .layout         = m_glowLayout,
    };
    m_glowPipeline = vulkan_graphics::createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
    if (m_glowPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the light glow pipeline failed.");
    }
    return InitializationResult::success();
}
```

`Setup` builds it after `EnableDeferred`:

```cpp
    if (auto result = CreateGlowPipeline(); !result)            { return result; }
```

`UsdViewerDemo.cpp` gains `GraphicsPipeline.h` and `VulkanBarriers.h` among its
includes.

**This is `RecordLightGlows`**: Chapter 21 section 5's `RecordParticles` with
the glows' draw in place of the particles'. Everything else — the color's
barrier from one scope into the next, the depth's into
`DEPTH_READ_ONLY_OPTIMAL` and back, the attachments with `LOAD`, and the
viewport — is that section's, line for line, and Appendix B has the whole
function. Where `RecordParticles` binds its pipeline, sets, and push constant
and draws indirectly, this draws one quad per light:

```cpp
    // A quad per light in the buffer; the vertex shader throws away the distant ones.
    const uint32_t lightCount = static_cast<uint32_t>(std::min<size_t>(m_lights.size(), vulkan_graphics::MAX_LIGHTS));
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_glowPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_glowLayout, frame.frameIndex);
    vkCmdDraw(commandBuffer, 6, lightCount, 0, 0);
```

The instance count is the number of lights `WriteLights` wrote this frame, the
same clamp to `MAX_LIGHTS`.

In `Record`, the glows go after the opaque scene's `if`/`else` and before the
hand-back, so they are drawn on both paths:

```cpp
    // The hybrid's forward half: blended light glows over the lit scene, on either path (section 10).
    if (m_lightGlows)
    {
        RecordLightGlows(commandBuffer, frame);
    }
```

and the panel gets a checkbox, after the views' `EndDisabled()`:

```cpp
        ImGui::Checkbox("Light glows (forward, after either path)", &m_lightGlows);
```

---

## 11. Measuring both

**This is the viewer's timestamps, the panel's table, and what they say.**

Section 1's arithmetic says which path *should* win. Only a measurement says
which does, on this GPU, at this window size, on this scene. Chapter 21 section
8 timed its passes with timestamp queries; the viewer does the same with five
timestamps a frame:

| Timestamp | Written after | So the difference to the previous one is |
| --- | --- | --- |
| 0 | nothing: the start | — |
| 1 | `RecordShadows` | the shadow pass |
| 2 | the forward scene pass, or the G-buffer pass | the opaque scene's drawing |
| 3 | the lighting pass (forward: right after 2) | the lighting pass, 0 when forward |
| 4 | the glows | the blended pass |

Each slot's results are read after its fence, as in Chapter 21, and filed
under the path that slot ran, so switching paths fills both columns of the
table and the last measurement of each stays on screen.

The pieces are Chapter 21's. `timestampValidBits` is copied above the namespace
block in `UsdViewerDemo.cpp`, unchanged — its second copy, after the particles';
a third user would be the time to move it into `VulkanGraphics`. Beside it, the
count:

```cpp
static constexpr uint32_t TIMESTAMP_COUNT = 5;
```

In the header, the results' shape above the class, and the state with the other
Chapter 22 members:

```cpp
// Chapter 22 section 11: GPU milliseconds per pass, from timestamp queries.
struct PassTimings
{
    float shadows  = 0.0f;
    float opaque   = 0.0f;   // forward: the scene pass; deferred: the G-buffer pass
    float lighting = 0.0f;   // deferred only
    float glows    = 0.0f;   // the blended light glows, drawn forward on both paths
};
```

```cpp
// Demos/UsdViewer/UsdViewerDemo.h - Chapter 22, the timings. Private, after RecordLightGlows:
    InitializationResult CreateTimestamps();                                             // section 11
    void                 WriteTimestamp(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t which);
    void                 ReadTimings(uint32_t frameIndex);

// CPU state:
    std::array<PassTimings, 2>  m_timings{};   // [RenderPath]: the last measurement of each path
// GPU objects:
    VkQueryPool      m_queryPool       = VK_NULL_HANDLE;
    double           m_timestampPeriod = 0.0;   // nanoseconds per tick
    uint64_t         m_timestampMask   = 0;
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>                        m_timestampsPending{};
    std::array<vulkan_graphics::RenderPath, vulkan_graphics::FRAMES_IN_FLIGHT> m_timedPath{};   // which path each slot timed
```

`Setup` creates the pool last:

```cpp
    if (auto result = CreateTimestamps(); !result)              { return result; }
```

`CreateTimestamps` and `WriteTimestamp` are Chapter 21's with this demo's
names and five timestamps instead of six (Appendix B). `ReadTimings` differs in
one way: it files the results under the path the slot ran, and records no
lighting time for a forward frame, whose timestamps 2 and 3 are written one
after the other:

```cpp
// After this slot's fence: what it timed the last time it ran, filed under the path it ran.
void UsdViewerDemo::ReadTimings(uint32_t frameIndex)
{
    if (!m_timestampsPending[frameIndex]) { return; }
    m_timestampsPending[frameIndex] = false;

    uint64_t ticks[TIMESTAMP_COUNT]{};
    if (vkGetQueryPoolResults(m_context.vulkan.device, m_queryPool, frameIndex * TIMESTAMP_COUNT, TIMESTAMP_COUNT,
                              sizeof(ticks), ticks, sizeof(uint64_t), VK_QUERY_RESULT_64_BIT) != VK_SUCCESS)
    {
        return;
    }
    const auto milliseconds = [&](uint32_t from, uint32_t to) {
        return static_cast<float>(static_cast<double>((ticks[to] - ticks[from]) & m_timestampMask)
                                  * m_timestampPeriod * 1e-6);
    };
    const bool deferred = m_timedPath[frameIndex] == vulkan_graphics::RenderPath::Deferred;
    m_timings[static_cast<uint32_t>(m_timedPath[frameIndex])] = PassTimings{
        .shadows  = milliseconds(0, 1),
        .opaque   = milliseconds(1, 2),
        .lighting = deferred ? milliseconds(2, 3) : 0.0f,   // forward has none: timestamps 2 and 3 are adjacent
        .glows    = milliseconds(3, 4),
    };
}
```

`Teardown` destroys the pool and the glow pipeline before the scene renderer:

```cpp
void UsdViewerDemo::Teardown()
{
    m_ready = false;
    if (m_context.vulkan.device != VK_NULL_HANDLE)   // Chapter 22's objects, if Setup made them
    {
        vkDestroyQueryPool(m_context.vulkan.device, m_queryPool, nullptr);
        vkDestroyPipeline(m_context.vulkan.device, m_glowPipeline, nullptr);
        vkDestroyPipelineLayout(m_context.vulkan.device, m_glowLayout, nullptr);
    }
    m_queryPool    = VK_NULL_HANDLE;
    m_glowPipeline = VK_NULL_HANDLE;
    m_glowLayout   = VK_NULL_HANDLE;
    m_timestampsPending.fill(false);
    m_sceneRenderer.Shutdown();
}
```

**`Record`** gains the timestamps around what it already records. Right after
Chapter 19's `PrepareDraws`, before `RecordShadows`: last time's results for
this slot, the reset of its block, and the first timestamp.

```cpp
    // Chapter 22 section 11: last time's timings for this slot, then this frame's five timestamps.
    ReadTimings(frame.frameIndex);
    if (m_queryPool != VK_NULL_HANDLE)
    {
        vkCmdResetQueryPool(commandBuffer, m_queryPool, frame.frameIndex * TIMESTAMP_COUNT, TIMESTAMP_COUNT);
    }
    WriteTimestamp(commandBuffer, frame.frameIndex, 0);
```

The other four are one line each, `WriteTimestamp(commandBuffer,
frame.frameIndex, n);`, at the places the table above names:

- **1** after `m_lastFrameIndex = frame.frameIndex;`, the line that follows
  `RecordShadows`.
- **2** inside each branch of section 7's `if`: in the deferred branch between
  `RecordGBufferPass` and `RecordLighting`, so that the lighting pass falls
  between 2 and 3; in the forward branch after `endScenePass`.
- **3** right after the `if`/`else`, so the forward branch writes 2 and 3 back
  to back. That is why `ReadTimings` records no lighting time for it.
- **4** after section 10's `if (m_lightGlows)` block.

After timestamp 4, before `handBackSceneTarget`, the slot remembers which path
it timed and that its results are coming:

```cpp
    m_timedPath[frame.frameIndex]         = deferred ? vulkan_graphics::RenderPath::Deferred
                                                     : vulkan_graphics::RenderPath::Forward;
    m_timestampsPending[frame.frameIndex] = m_queryPool != VK_NULL_HANDLE;
```

The panel's table goes last in `DrawRenderingPanel`, after the glows' checkbox:

```cpp
        // Each path's last measurement stays, so switching shows both.
        if (m_queryPool != VK_NULL_HANDLE && ImGui::BeginTable("timings", 3, ImGuiTableFlags_Borders))
        {
            ImGui::TableSetupColumn("GPU ms");
            ImGui::TableSetupColumn("Forward");
            ImGui::TableSetupColumn("Deferred");
            ImGui::TableHeadersRow();
            const PassTimings& forward  = m_timings[0];
            const PassTimings& deferred = m_timings[1];
            const auto row = [](const char* name, float a, float b) {
                ImGui::TableNextRow();
                ImGui::TableNextColumn(); ImGui::TextUnformatted(name);
                ImGui::TableNextColumn(); ImGui::Text("%.3f", a);
                ImGui::TableNextColumn(); ImGui::Text("%.3f", b);
            };
            row("Shadows", forward.shadows, deferred.shadows);
            row("Scene / G-buffer", forward.opaque, deferred.opaque);
            row("Lighting", forward.lighting, deferred.lighting);
            row("Glows", forward.glows, deferred.glows);
            row("Total", forward.shadows + forward.opaque + forward.lighting + forward.glows,
                deferred.shadows + deferred.opaque + deferred.lighting + deferred.glows);
            ImGui::EndTable();
        }
```

### What the numbers say

Here is what the table showed on one machine: a software renderer (Mesa's
lavapipe, which runs Vulkan on the CPU), at 1280 x 720, from the starting
camera, averaged over many frames, in milliseconds.

| Scene | Path | Shadows | Scene or G-buffer | Lighting | Glows | Total |
| --- | --- | --- | --- | --- | --- | --- |
| `LightTest.usda`: 5 lights, one a shadowed sun | Forward | 10.0 | 33.8 | — | 0.4 | 44.2 |
| | Deferred | 10.6 | 12.3 | 68.3 | 0.5 | 91.7 |
| `ManyLights.usda`: 256 lights, no sun | Forward | 0.1 | 556.1 | — | 0.7 | 556.8 |
| | Deferred, Part 1's every-light loop | 0.1 | 20.1 | 659.5 | 0.7 | 680.4 |
| | Deferred, tiled | 0.1 | 19.6 | 104.4 | 0.7 | 124.7 |

**A software renderer is a CPU pretending to be a GPU**, so none of these is a
GPU's number; read the ratios. They say three things:

- **With a handful of lights, deferred loses.** The G-buffer pass costs about a
  third of the forward pass — the material without the lights — but the lighting
  pass costs more than the forward pass saved, because a full-screen pass is
  paid whatever the light count, and here it also does the sun's shadow lookups.
- **Without tiles, deferred buys nothing.** Part 1's lighting pass costs more
  than the forward pass, because in this scene overdraw is low: the light count,
  not wasted fragments, is the bill, and the deferred path adds the G-buffer's
  traffic on top.
- **With tiles and many lights, deferred wins**, four and a half times over,
  because each pixel evaluates about 25 lights instead of 256.

**Where they cross** — how many lights a scene needs before deferred pays for
its G-buffer — is the number worth finding. `make_many_lights.py` takes the
number of lights per side (Appendix A), and the same field with fewer lights
gives two more points:

| `ManyLights.usda` written with | Forward total | Deferred total |
| --- | --- | --- |
| 4 per side: 16 lights | 81.9 | 59.6 |
| 8 per side: 64 lights | 168.2 | 67.0 |
| 16 per side: 256 lights | 556.8 | 124.7 |

So on that machine the crossover lies somewhere between `LightTest.usda`'s five
lights and this field's sixteen. Forward's cost grows with the light count;
deferred's barely moves until the tiles fill up. On a GPU the crossover depends
most on memory bandwidth, which is why it has to be measured on the machine
that matters: on an integrated GPU, expect it at more lights than on a discrete
one.

---

## 12. Every barrier in a deferred frame

**This is the frame's synchronization, in one place.** A deferred frame adds
these barriers to Chapter 17's shadow pass and Chapter 08's hand-back, in
recording order:

| Where | Image | From | To |
| --- | --- | --- | --- |
| `ShadowMaps::Record`, start (section 6) | shadow map | last frame's sampling, now `FRAGMENT_SHADER \| COMPUTE_SHADER` | the shadow pass's depth tests |
| `ShadowMaps::Record`, end (section 6) | shadow map | the depth tests | sampling, now `FRAGMENT_SHADER \| COMPUTE_SHADER` |
| `BeginGBufferPass` (section 4) | scene target | last frame's composite | the G-buffer pass's location 0 |
| `BeginGBufferPass` | scene depth | last frame's depth tests | this frame's |
| `BeginGBufferPass` | G-buffer, three | last frame's lighting pass, `COMPUTE_SHADER` | the G-buffer pass's attachments |
| `RecordLighting`, in (section 6) | G-buffer, three | the attachments | sampled by the lighting pass |
| `RecordLighting`, in | scene depth | the depth tests | sampled by the lighting pass |
| `RecordLighting`, in | scene target | the G-buffer pass's location 0 | storage read and write by the lighting pass |
| `RecordLighting`, out | scene target | the lighting pass's writes | an attachment again: `endScenePass`'s state |
| `RecordLighting`, out | scene depth | the lighting pass's reads | the depth tests: `endScenePass`'s state |
| `RecordLightGlows` (section 10) | color, depth | Chapter 21 section 5's three, unchanged | |

Of the new ones, the layer can check every barrier on a G-buffer image and on
the scene target, because each is an attachment access on one side and a shader
access through a descriptor on the other — the middle row of Chapter 20 section
5's table, with the shader-access setting on. The exit check proves that it
does, by breaking the G-buffer's barrier into the lighting pass.

Chapter 04's appendix lists this chapter's four new rows under "Deferred
shading"; its shadow-map rows already name `COMPUTE_SHADER` beside
`FRAGMENT_SHADER`, and its "Scene depth sampled by compute" row and that row's
return trip are the scene depth's two rows here, where at one sample the first
one's source needs only the depth tests.

---

## When it does not work

| Symptom | Likely cause |
| --- | --- |
| Deferred shows only ambient light and emission | The lighting pass sees no lights: its set is not at set number 0 in the pipeline layout, or binding 1 is not the light buffer |
| The deferred image's lighting slides when the camera moves | `inverseViewProjection` is stale or zero: the demo does not fill it, or fills it before `viewProjection` |
| Lighting upside down, or offset by half a pixel | `worldFromDepth` flips *y* (Vulkan's NDC is already *y* down) or omits the `+ 0.5` |
| Banded highlights in Deferred only | The normal stored in 8 bits, or the octahedral encode and decode disagree |
| Dark colors too dark, or banded, in Deferred only | The base color image is `UNORM` instead of `_SRGB`, or the shader decodes it a second time |
| Dark square tiles where a light should reach | `lightTouchesTile` drops it: a plane's sign is wrong, the planes are not normalized, or the radius is not the range |
| Garbage or a hang in the last row or column of tiles | An invocation returned before a `barrier()` |
| Validation: image layout at `vkCmdDispatch` | `RecordLighting`'s barriers in are missing, or a descriptor names another layout |
| `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`, binding 4 | The shadow map's second barrier lacks `COMPUTE_SHADER` (section 6) |
| Deferred breaks right after choosing another file | `SwitchToFile` does not call `Resize`, so the G-buffer was never rebuilt |
| The Deferred button is greyed out | MSAA is above 1x (section 9) |
| Glows show through walls | The glow pipeline's depth test is off |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat` — `DeferredShading.cpp`, four shaders, and `Octahedral.glsl` are
      new — build, and open the USD viewer. Part 1's checkpoint still holds.
- [ ] Generate `ManyLights.usda` (Appendix A) and open it. **Forward** and
      **Deferred** draw the same picture. The timings table, after switching
      once each way, shows the deferred total far below the forward one.
- [ ] **Lights per tile** on `ManyLights.usda`: the ground near the camera is
      green, the band towards the horizon red, and pixels where nothing was
      drawn stay the clear color.
- [ ] With MSAA at 4x in the MSAA window, the Deferred button is greyed out,
      the panel says why, and the scene draws forward; back at 1x, the path you
      chose before returns.
- [ ] **Light glows**: each local light glows in its color on both paths; on
      `LightTest.usda` the disk light's glow is cut in half by the floor.
      Unticking the box removes them.
- [ ] **Measure on your GPU.** Fill the table for `LightTest.usda` and
      `ManyLights.usda`, then regenerate the field with 4 and 8 lights per side.
      Which path wins on each, and where do they cross?
- [ ] **The G-buffer barrier is proven.** In `RecordLighting`, change the
      G-buffer images' barrier destination from `COMPUTE_SHADER` to
      `FRAGMENT_SHADER` — the composite pass's row, an easy copy to make — and
      run Deferred: synchronization validation must report
      `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`, for bindings 5, 6, and
      7, every frame. If it reports nothing, the shader-access setting is off
      (Chapter 20 section 5). Put it back.
- [ ] Validation is silent through switching paths, views, files, MSAA, and the
      window's size, and quitting reports no leaked VMA allocation.

Next: [23 — The Sky](23-The-Sky.md), drawn behind everything, after the
opaque scene on either path.

---

## Appendix A — `make_many_lights.py`

Reference: the script that writes `ManyLights.usda`, in the style of Chapter 19's
`make_forest.py`. The pillars and spheres sit between the lights, so that some
surfaces hide others and every light has something near it to light.

```python
# Assets/Scenes/make_many_lights.py
# Writes ManyLights.usda: Chapter 22's night scene. 256 small coloured lights - SceneRenderer's
# MAX_LIGHTS - over a field of pillars and spheres, each light reaching about 10 m. Run once, from
# Assets/Scenes/:
#     python make_many_lights.py [lights per side]
# A smaller side, such as 4 or 8, writes the same field with 16 or 64 lights, for finding where forward
# and deferred cross over (section 11). Plain Python 3, standard library only. Not part of the build:
# commit what it writes.
import colorsys, random, sys

random.seed(22)
SIDE    = int(sys.argv[1]) if len(sys.argv) > 1 else 16   # 16 x 16 = 256 lights
SPACING = 64.0 / SIDE   # metres between lights: the grid always spans the same 64 m
# A sphere light with normalize = 1 has radiant intensity intensity / 4 (Chapter 16 section 2), so 4 is
# an intensity of 1, and Chapter 16's automatic range, where I / d^2 falls to 0.01, is 10 m.
INTENSITY = 4.0

prims = []

def material(name, color, roughness, metallic=0.0):
    return f"""
        def Material "{name}"
        {{
            token outputs:surface.connect = </ManyLights/Materials/{name}/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {color}
                float inputs:roughness = {roughness}
                float inputs:metallic = {metallic}
                token outputs:surface
            }}
        }}"""

# The ground: 80 m square, the lights' grid with a margin.
prims.append("""
    def Mesh "Ground" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-40, 0, 40), (40, 0, 40), (40, 0, -40), (-40, 0, -40)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        rel material:binding = </ManyLights/Materials/Ground>
    }""")

# Pillars and spheres on an 8 m grid, between the lights: things to light, and things in front of
# other things, so the forward pass shades some pixels more than once.
for row in range(8):
    for column in range(8):
        x = (column - 3.5) * 8.0
        z = (row - 3.5) * 8.0
        height = 2.0 + (row * 5 + column * 3) % 4
        prims.append(f"""
    def Cube "Pillar_{row}_{column}" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        double size = 1
        double3 xformOp:translate = ({x:.1f}, {height / 2:.1f}, {z:.1f})
        float3 xformOp:scale = (0.8, {height:.1f}, 0.8)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
        rel material:binding = </ManyLights/Materials/Clay>
    }}""")
        prims.append(f"""
    def Sphere "Ball_{row}_{column}" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        double radius = 0.7
        double3 xformOp:translate = ({x + 4.0:.1f}, 0.7, {z + 4.0:.1f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </ManyLights/Materials/{'Gold' if (row + column) % 3 == 0 else 'Polished'}>
    }}""")

# The lights: a jittered grid, each at its own height and in its own hue.
for row in range(SIDE):
    for column in range(SIDE):
        x = (column - (SIDE - 1) / 2) * SPACING + random.uniform(-1.0, 1.0)
        z = (row - (SIDE - 1) / 2) * SPACING + random.uniform(-1.0, 1.0)
        y = random.uniform(0.4, 1.6)
        r, g, b = colorsys.hsv_to_rgb(random.random(), 0.65, 1.0)
        prims.append(f"""
    def SphereLight "Light_{row}_{column}"
    {{
        color3f inputs:color = ({r:.3f}, {g:.3f}, {b:.3f})
        float inputs:intensity = {INTENSITY}
        bool inputs:normalize = 1
        float inputs:radius = 0.05
        double3 xformOp:translate = ({x:.2f}, {y:.2f}, {z:.2f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}""")

header = f"""#usda 1.0
(
    defaultPrim = "ManyLights"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "ManyLights"
{{
    def Scope "Materials"
    {{{material("Ground", "(0.5, 0.5, 0.5)", 0.7)}{material("Clay", "(0.6, 0.5, 0.42)", 0.5)}{material("Polished", "(0.8, 0.8, 0.8)", 0.2)}{material("Gold", "(1.0, 0.78, 0.34)", 0.3, 1.0)}
    }}

    # Low over the field, looking along it: near lights large, far ones packed together.
    def Camera "Camera"
    {{
        float focalLength = 18
        float verticalAperture = 24
        float2 clippingRange = (0.1, 200)
        double3 xformOp:translate = (0, 5, 38)
        float xformOp:rotateX = -10
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }}

    # Night: a faint blue sky, so nothing is pure black.
    def DomeLight "Sky"
    {{
        color3f inputs:color = (0.5, 0.6, 1)
        float inputs:intensity = 0.02
    }}
"""
with open("ManyLights.usda", "w") as out:
    out.write(header + "".join(prims) + "\n}\n")
print(f"ManyLights.usda: {SIDE * SIDE} lights")
```

---

## Appendix B — The rest of the code

Reference: the functions the sections above describe but show only in part,
whole, in the files they belong to.

`DeferredShading.cpp` — `Initialize` (section 6), `DestroyImages` (section 4),
and `Shutdown` (section 6):

```cpp
InitializationResult DeferredShading::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                                 VkFormat sceneColorFormat,
                                                 std::span<const LightingInputs, FRAMES_IN_FLIGHT> inputs,
                                                 const VkDescriptorImageInfo& shadowMap)
{
    m_context          = context;
    m_pipelineCache    = pipelineCache;
    m_passColorFormats = { sceneColorFormat, GBUFFER_FORMATS[0], GBUFFER_FORMATS[1], GBUFFER_FORMATS[2] };

    // texelFetch reads exactly one texel, so filtering never happens; nearest and clamp say so.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_NEAREST,
        .minFilter    = VK_FILTER_NEAREST,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_sampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the G-buffer.");
    }

    // The lighting set: set 0's bindings 0, 1, 3, and 4 under their own numbers, so Chapters 10, 16,
    // and 17's includes work unchanged in a compute shader; then this chapter's five images.
    const VkShaderStageFlags compute = VK_SHADER_STAGE_COMPUTE_BIT;
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 3, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         .descriptorCount = 1, .stageFlags = compute },
        { .binding = 4, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 5, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 6, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 7, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 8, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1, .stageFlags = compute },
        { .binding = 9, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          .descriptorCount = 1, .stageFlags = compute },
    };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(std::size(bindings)),
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &setLayoutInfo, nullptr, &m_setLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the lighting set.");
    }

    // One set per frame in flight, like set 0, because bindings 0, 1, and 3 are per-frame buffers.
    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         2 * FRAMES_IN_FLIGHT },
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         1 * FRAMES_IN_FLIGHT },
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 5 * FRAMES_IN_FLIGHT },
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,          1 * FRAMES_IN_FLIGHT },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = FRAMES_IN_FLIGHT,
        .poolSizeCount = static_cast<uint32_t>(std::size(poolSizes)),
        .pPoolSizes    = poolSizes,
    };
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &m_pool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the lighting set.");
    }
    std::array<VkDescriptorSetLayout, FRAMES_IN_FLIGHT> layouts;
    layouts.fill(m_setLayout);
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_pool,
        .descriptorSetCount = FRAMES_IN_FLIGHT,
        .pSetLayouts        = layouts.data(),
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, m_sets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the lighting set.");
    }

    // Bindings 0 to 4 never change: the same buffers and shadow map that set 0 points at.
    for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
    {
        const VkWriteDescriptorSet writes[] = {
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 0,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .pBufferInfo = &inputs[i].frame },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 1,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &inputs[i].lights },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 3,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .pBufferInfo = &inputs[i].shadows },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_sets[i], .dstBinding = 4,
              .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &shadowMap },
        };
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(std::size(writes)), writes, 0, nullptr);
    }

    // The lighting set and the view to write, and one compute shader.
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(shared::DeferredParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_lightingLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the lighting pass.");
    }
    m_lightingPipeline = createComputePipeline(m_context.device, m_pipelineCache,
                                               "Scene/DeferredLighting.comp.spv", m_lightingLayout);
    if (m_lightingPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the deferred lighting pipeline failed.");
    }
    return InitializationResult::success();
}
```

```cpp
void DeferredShading::DestroyImages()
{
    for (uint32_t i = 0; i < GBUFFER_IMAGE_COUNT; ++i)
    {
        vkDestroyImageView(m_context.device, m_views[i], nullptr);   // null is a no-op
        if (m_context.allocator != VK_NULL_HANDLE)                    // VMA's destroy is not null-safe here
        {
            vmaDestroyImage(m_context.allocator, m_images[i], m_allocations[i]);
        }
        m_views[i]       = VK_NULL_HANDLE;
        m_images[i]      = VK_NULL_HANDLE;
        m_allocations[i] = VK_NULL_HANDLE;
    }
}
```

```cpp
void DeferredShading::Shutdown()
{
    if (m_context.device == VK_NULL_HANDLE) { return; }   // never initialized

    DestroyImages();
    vkDestroyPipeline(m_context.device, m_lightingPipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_lightingLayout, nullptr);
    vkDestroyDescriptorPool(m_context.device, m_pool, nullptr);        // frees the sets too
    vkDestroyDescriptorSetLayout(m_context.device, m_setLayout, nullptr);
    vkDestroySampler(m_context.device, m_sampler, nullptr);
    m_lightingPipeline = VK_NULL_HANDLE;
    m_lightingLayout   = VK_NULL_HANDLE;
    m_pool             = VK_NULL_HANDLE;
    m_sets             = {};
    m_setLayout        = VK_NULL_HANDLE;
    m_sampler          = VK_NULL_HANDLE;
    m_context          = {};
}
```

`SceneRenderer.cpp` — `CreateGBufferPipelines` (section 4):

```cpp
InitializationResult SceneRenderer::CreateGBufferPipelines()
{
    // The mesh pipelines' description with another fragment shader and four color attachments.
    // Chapter 15's two specialization constants; no alpha-to-coverage, because there is one sample.
    struct GBufferSpecialization
    {
        uint32_t shadingMode = 0;          // constant_id 0
        VkBool32 alphaCutout = VK_FALSE;   // constant_id 1
    };
    const VkSpecializationMapEntry entries[] = {
        { .constantID = 0, .offset = offsetof(GBufferSpecialization, shadingMode), .size = sizeof(uint32_t) },
        { .constantID = 1, .offset = offsetof(GBufferSpecialization, alphaCutout), .size = sizeof(VkBool32) },
    };
    const VkDynamicState dynamicStates[] = { VK_DYNAMIC_STATE_CULL_MODE, VK_DYNAMIC_STATE_FRONT_FACE };

    for (uint32_t mode = 0; mode < SHADING_MODE_COUNT; ++mode)
    {
        for (uint32_t cutout = 0; cutout < 2; ++cutout)
        {
            const GBufferSpecialization values{ .shadingMode = mode, .alphaCutout = cutout ? VK_TRUE : VK_FALSE };
            const VkSpecializationInfo specialization{
                .mapEntryCount = 2,
                .pMapEntries   = entries,
                .dataSize      = sizeof(values),
                .pData         = &values,
            };
            const GraphicsPipelineDesc desc{
                .vertexShader           = "Scene/Mesh.vert.spv",
                .fragmentShader         = "Scene/GBuffer.frag.spv",
                .vertexBindings         = meshVertexBindings(),
                .vertexAttributes       = meshVertexAttributes(),
                .colorFormats           = m_deferred.PassColorFormats(),
                .depthFormat            = m_formats.depth,
                .depthTest              = true,
                .depthWrite             = true,
                .depthCompare           = VK_COMPARE_OP_LESS,
                .cullMode               = VK_CULL_MODE_BACK_BIT,
                .frontFace              = VK_FRONT_FACE_COUNTER_CLOCKWISE,
                .dynamicStates          = dynamicStates,
                .fragmentSpecialization = &specialization,
                .layout                 = m_meshLayout,
                .samples                = VK_SAMPLE_COUNT_1_BIT,
            };
            m_gbufferPipelines[mode][cutout] = createGraphicsPipeline(m_context.device, m_pipelineCache, desc);
            if (m_gbufferPipelines[mode][cutout] == VK_NULL_HANDLE)
            {
                return InitializationResult::failure("Creating a G-buffer pipeline failed.");
            }
        }
    }
    return InitializationResult::success();
}
```

`UsdViewerDemo.cpp` — `RecordLightGlows` (section 10), `CreateTimestamps` and
`WriteTimestamp` (section 11):

```cpp
void UsdViewerDemo::RecordLightGlows(VkCommandBuffer commandBuffer, const RecordContext& frame)
{
    const vulkan_graphics::SceneTargets& targets = frame.targets;

    vulkan_graphics::transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    vulkan_graphics::transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                        | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);

    const VkRenderingAttachmentInfo colorAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.colorView,
        .imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_LOAD,
        .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
    };
    const VkRenderingAttachmentInfo depthAttachment{
        .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
        .imageView   = targets.depthView,
        .imageLayout = VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL,
        .resolveMode = VK_RESOLVE_MODE_NONE,
        .loadOp      = VK_ATTACHMENT_LOAD_OP_LOAD,
        .storeOp     = VK_ATTACHMENT_STORE_OP_NONE,
    };
    const VkRenderingInfo renderingInfo{
        .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
        .renderArea           = { { 0, 0 }, targets.extent },
        .layerCount           = 1,
        .colorAttachmentCount = 1,
        .pColorAttachments    = &colorAttachment,
        .pDepthAttachment     = &depthAttachment,
    };
    vkCmdBeginRendering(commandBuffer, &renderingInfo);

    const VkViewport viewport{ 0.0f, 0.0f,
                               static_cast<float>(targets.extent.width),
                               static_cast<float>(targets.extent.height),
                               0.0f, 1.0f };
    const VkRect2D scissor{ { 0, 0 }, targets.extent };
    vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
    vkCmdSetScissor(commandBuffer, 0, 1, &scissor);

    // A quad per light in the buffer; the vertex shader throws away the distant ones.
    const uint32_t lightCount = static_cast<uint32_t>(std::min<size_t>(m_lights.size(), vulkan_graphics::MAX_LIGHTS));
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_glowPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_glowLayout, frame.frameIndex);
    vkCmdDraw(commandBuffer, 6, lightCount, 0, 0);

    vkCmdEndRendering(commandBuffer);

    // The depth's return trip, as in Chapter 21.
    vulkan_graphics::transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

```cpp
// Chapter 22 section 11: Chapter 21's CreateTimestamps, with five timestamps a frame.
InitializationResult UsdViewerDemo::CreateTimestamps()
{
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &properties);
    m_timestampPeriod = static_cast<double>(properties.limits.timestampPeriod);

    const uint32_t validBits = timestampValidBits(m_context.vulkan.physicalDevice);
    if (validBits == 0)
    {
        return InitializationResult::success();   // no timestamps here: the panel omits the timings
    }
    m_timestampMask = validBits >= 64 ? ~0ull : (1ull << validBits) - 1ull;

    const VkQueryPoolCreateInfo queryPoolInfo{
        .sType      = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
        .queryType  = VK_QUERY_TYPE_TIMESTAMP,
        .queryCount = TIMESTAMP_COUNT * vulkan_graphics::FRAMES_IN_FLIGHT,
    };
    if (vkCreateQueryPool(m_context.vulkan.device, &queryPoolInfo, nullptr, &m_queryPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateQueryPool failed for the viewer's timings.");
    }
    return InitializationResult::success();
}
```

```cpp
void UsdViewerDemo::WriteTimestamp(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t which)
{
    if (m_queryPool == VK_NULL_HANDLE) { return; }
    vkCmdWriteTimestamp2(commandBuffer, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, m_queryPool,
                         frameIndex * TIMESTAMP_COUNT + which);
}
```

---

## Sources

- **Deferred shading and the G-buffer.** Michael Deering et al., "The Triangle
  Processor and Normal Vector Shader", SIGGRAPH 1988; Takafumi Saito and Tokiichiro
  Takahashi, "Comprehensible Rendering of 3-D Shapes", SIGGRAPH 1990, which
  named the G-buffer.
- **Tiled light culling in compute.** Johan Andersson, "DirectX 11 Rendering in
  Battlefield 3", GDC 2011; Andrew Lauritzen, "Deferred Rendering for Current
  and Future Rendering Pipelines", SIGGRAPH 2010 course *Beyond Programmable
  Shading*.
- **Forward+ and 2.5D culling.** Takahiro Harada, Jay McKee, and Jason C. Yang,
  "Forward+: Bringing Deferred Lighting to the Next Level", Eurographics 2012;
  Takahiro Harada, "A 2.5D Culling for Forward+", SIGGRAPH Asia 2012.
- **Clustered shading.** Ola Olsson, Markus Billeter, and Ulf Assarsson,
  "Clustered Deferred and Forward Shading", High-Performance Graphics 2012.
- **Octahedral normals.** Zina H. Cigolle, Sam Donow, Daniel Evangelakos, Michael
  Mara, Morgan McGuire, and Quirin Meyer, "A Survey of Efficient
  Representations for Independent Unit Vectors", JCGT 3(2), 2014.
- **Which formats every device supports.** The Vulkan specification's
  "Required Format Support" tables.
