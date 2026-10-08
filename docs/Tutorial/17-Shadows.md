# 17 — Shadows

**Goal:** the sun casts shadows across a USD scene. They hold still while you
fly the camera, sit on the ground without speckles or gaps, are sharp near you
and still present a hundred metres away, and a debug view shows which of four
shadow maps each pixel used. The chapter has two parts. **Part 1, Shadow maps**
(sections 1-10), draws one shadow map from the sun and uses it, with every
trick a single map needs. **Part 2, Cascaded shadow maps** (sections 11-14),
splits the view into four maps so shadows are sharp near you and still there
far away, and holds them still as the camera moves.

**ROADMAP:** step 18.

**Module:** `Source/PillowFort/VulkanGraphics/`, namespace
`pf::vulkan_graphics`: a new `ShadowMaps` class, plus additions to
`SceneRenderer` and `createGraphicsPipeline`. Shaders: a new
`Shaders/Shadows/` folder and a new include, `Shaders/Include/Shadows.glsl`.
The mesh fragment shader gains one multiplication, and `UsdViewerDemo` one call.

**Math:** taught here — an orthographic box fitted around a slice of the view,
seen from the sun (section 2); normalized device coordinates as texture
coordinates (section 6); the depth-bias formula, with a worked number (section
7); uniform and logarithmic splits (section 11); the smallest sphere around a
frustum slice, and snapping to whole texels (section 12, the algebra
optional). Assumed: Chapter 10's view and projection matrices and the divide
by w, and `tan`, `pow`, `round`.

**Prerequisites:**

- Chapter 04 section 5 — the three questions every barrier answers,
  `transitionImage`, and the cookbook's note that **every per-frame cycle needs
  both directions**. This chapter adds one such cycle.
- Chapter 06 sections 4 and 8 — the pipeline's fixed-function state,
  `GraphicsPipelineDesc`, and `createGraphicsPipeline`, which this chapter
  teaches to build a pipeline with no fragment shader.
- Chapter 08 sections 3, 6, 7, and 8 — images and samplers, descriptor sets and
  the rule against touching what the GPU may still read, VMA, and
  `SharedShaderTypes.h`.
- Chapter 09 — the demo's `Record`, and the contract that everything before
  `beginScenePass` is the demo's business.
- Chapter 10 — `Camera::Projection` and its negated `[1][1]`, `viewMatrix`,
  `glm::lookAt`'s view space (looking down −Z), section 1's spaces (the divide
  by w, which section 6 here uses), `FrameData`, section 7's rule for host
  writes, and the depth buffer's "start of frame" barrier.
- Chapter 11 — `GpuMesh`, `meshVertexBindings()` and `meshVertexAttributes()`,
  and `SceneRenderer`'s pipelines.
- Chapter 12 — `DrawItem` and `Scene::CollectDraws`, including its frustum
  culling.
- Chapter 15 sections 7 and 11 — the material set layout, `MaterialSet.glsl`'s
  `materialOpacity`, cutout materials, and `shaderDemoteToHelperInvocation`,
  enabled there for `discard`.
- Chapter 16 sections 4 and 5 — the light buffer, `lightHeader.sunIndex`,
  `SceneRenderer::SunDirection`, and the light loop in `Mesh.frag.glsl`.

---

## What you are actually writing

A shadow is a question one point asks: *can the sun see me?* Answering it
directly — trace a ray from every pixel towards the sun through every triangle
— is what a ray tracer does (Chapter 33's path tracer finds its shadows by
following rays), and it costs a ray per pixel. The
rasterizer's answer is older and cheaper. Draw the scene once **from the
sun**, keeping only depth: for every direction the sun shines, that image
records how far the light got before it hit something. Then, while shading
each pixel from the camera, work out where that pixel sits in the sun's image
and compare: if the sun's image says something nearer was hit first, the pixel
is in shadow.

That turns the frame into two passes over the same geometry, from two
cameras, with an image handed from one to the other:

```text
 demo Record (Chapter 09)
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ WriteFrameData, WriteLights            host writes, as in Chapter 16              │
 │ RecordShadows ── ShadowMaps::Record:                                              │
 │     fit each cascade to the camera (CPU) ──▶ ShadowData, set 0 binding 3          │
 │     barrier: last frame's sampling ──▶ depth writes                               │
 │     for each cascade: depth-only pass from the sun into one layer of the map      │
 │     barrier: depth writes ──▶ fragment-shader sampling                            │
 │ beginScenePass                                                                    │
 │     RecordDraws: Mesh.frag.glsl samples the map (set 0 binding 4) and dims        │
 │                  only the sun's light where the map says something is in the way  │
 │ endScenePass, handBackSceneTarget                                                 │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

The files, and what each section adds:

```text
Shaders/Include/SharedShaderTypes.h    ShadowData, ShadowDrawData                       sections 2, 4
VulkanGraphics/GraphicsPipeline.h/.cpp no fragment stage; one blend state per attachment section 4
VulkanGraphics/ShadowMaps.h/.cpp       ShadowSettings, ShadowMaps, drawShadowPanel      sections 2-9; 11-13
Shaders/Shadows/ShadowDepth.vert.glsl  the shadow pass's vertex shader                  section 4
Shaders/Shadows/ShadowCutout.frag.glsl the cutout casters' discard                      section 4
Shaders/Include/Shadows.glsl           sunShadow; cascade selection, cascadeDebugColor  sections 6-8; 13
VulkanGraphics/SceneRenderer.h/.cpp    m_shadows, set 0 bindings 3-4, RecordShadows     sections 6, 9
Shaders/Scene/Mesh.frag.glsl           the sun's light times sunShadow; the cascade tint sections 9; 13
Demos/UsdViewer/UsdViewerDemo.h/.cpp   ShadowSettings, the panel, RecordShadows         section 9
Assets/Scenes/make_shadow_test.py      writes ShadowTest.usda, the test scene           section 10
```

### The class map

`ShadowMaps` owns everything the technique needs on the GPU: the depth image
with one layer per cascade, a view to render each layer through and one to
sample all of them, the comparison sampler, one `ShadowData` uniform buffer per
frame in flight, and the two pipelines that draw casters. It does **not** own
what it draws. The meshes and materials are `SceneRenderer`'s, and so is the
descriptor set the map is read through; `SceneRenderer` owns one `ShadowMaps`
the way it owns its meshes, and hands it a callback that draws them (section
9). That split keeps `ShadowMaps` about the *pass* — when it runs, into which
layer, with which barriers — and leaves *what* is drawn to the class that
knows: Chapter 19 replaces the drawing with instanced batches without
touching `ShadowMaps` at all.

`ShadowSettings` lists Part 2's five settings last, under their own comment;
Part 1 leaves them out, and section 11 adds them.

```cpp
// Source/PillowFort/VulkanGraphics/ShadowMaps.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "SharedShaderTypes.h"

#include <glm/glm.hpp>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <functional>
#include <optional>

namespace pf::vulkan_graphics {

// Everything an ImGui panel tunes live. CPU state: the demo owns it, so it survives a re-Setup.
struct ShadowSettings
{
    bool  enabled       = true;
    float maxDistance   = 120.0f;   // metres of view depth that receive shadows (section 2)
    float casterReach   = 200.0f;   // metres towards the sun, past each cascade, that still cast (section 2)
    float biasConstant  = 2.0f;     // rasterizer depth bias, in units of the format's smallest step (section 7)
    float biasSlope     = 2.0f;     // rasterizer depth bias, times the polygon's depth slope (section 7)
    float normalOffset  = 1.0f;     // receiver offset along its normal, in shadow texels (section 7)
    int   filterRadius  = 1;        // PCF: 0 = one hardware 2x2 tap, 1 = 3x3 taps (section 8)
    // Part 2: cascades.
    int   cascadeCount  = SHADOW_CASCADE_COUNT;   // 1 to 4 (section 11); 1 is Part 1's single map
    float splitLambda   = 0.8f;     // 0 = uniform splits, 1 = logarithmic (section 11)
    bool  stabilize     = true;     // bounding spheres and texel snapping (section 12); off shows the shimmer
    float blendFraction = 0.1f;     // fraction of each cascade blended into the next (section 13)
    bool  showCascades  = false;    // tint by cascade (section 13)
};

// The "Shadows" window. True if anything changed.
bool drawShadowPanel(ShadowSettings& settings);

// Draws casters into one cascade. Record calls it inside that cascade's rendering scope, with the
// viewport, scissor, and depth bias set and set 0 bound with CasterLayout(false). Two are passed:
// the scene's casters (SceneRenderer's loop, section 9) and optional extra ones - Chapter 27 draws a
// terrain impostor through that one. A callback binds CasterPipeline(cutout) or a depth-only pipeline
// of its own (DepthFormat(), one sample, no color attachments, VK_DYNAMIC_STATE_DEPTH_BIAS_ENABLE and
// VK_DYNAMIC_STATE_DEPTH_BIAS); one whose layout differs from CasterLayout's rebinds set 0 itself.
using ShadowCasterCallback = std::function<void(VkCommandBuffer commandBuffer, uint32_t cascade)>;

class ShadowMaps
{
public:
    // Image, views, sampler, and the per-frame ShadowData buffers. Leaves the map in
    // SHADER_READ_ONLY_OPTIMAL with shadows off, so a demo that never records shadows still draws.
    InitializationResult Initialize(const VulkanContext& context, uint32_t resolution = 2048);   // sections 3, 6
    InitializationResult CreatePipelines(VkPipelineCache cache, VkDescriptorSetLayout frameSetLayout,
                                         VkDescriptorSetLayout materialSetLayout);              // section 4
    void DestroyPipelines();
    void Shutdown();                                     // device idle; safe after a partial Initialize

    // In the demo's Record, after the fence wait and before the scene pass: fit the cascades, write this
    // frame's ShadowData, draw every cascade, and leave the map ready for the fragment shader.
    void Record(VkCommandBuffer commandBuffer, uint32_t frameIndex, VkDescriptorSet frameSet,
                const scene::Camera& camera, const glm::mat4& view, float aspect,
                std::optional<glm::vec3> sunDirection,             // the direction sunlight travels
                const ShadowSettings& settings,
                const ShadowCasterCallback& drawCasters,           // the scene's casters (section 9)
                const ShadowCasterCallback& extraCasters);         // anything else; empty for none (section 5)

    VkDescriptorBufferInfo DataBufferInfo(uint32_t frameIndex) const;   // for set 0 binding 3
    VkDescriptorImageInfo  MapImageInfo() const;                         // for set 0 binding 4
    VkFormat               DepthFormat() const { return SHADOW_FORMAT; }
    VkPipeline             CasterPipeline(bool cutout) const { return cutout ? m_cutoutPipeline : m_opaquePipeline; }
    VkPipelineLayout       CasterLayout(bool cutout) const   { return cutout ? m_cutoutLayout : m_opaqueLayout; }

private:
    // Section 3 says why 16 bits.
    static constexpr VkFormat SHADOW_FORMAT = VK_FORMAT_D16_UNORM;

    void FitCascades(const scene::Camera& camera, const glm::mat4& view, float aspect,
                     const glm::vec3& sunDirection, const ShadowSettings& settings);            // sections 2, 11, 12

    VulkanContext   m_context;                                  // a copy of borrowed handles
    uint32_t        m_resolution      = 0;
    bool            m_linearFiltering = false;                  // section 6: hardware 2x2 PCF available

    VkImage                                       m_image      = VK_NULL_HANDLE;
    VmaAllocation                                 m_allocation = VK_NULL_HANDLE;
    VkImageView                                   m_arrayView  = VK_NULL_HANDLE;   // all layers: sampled
    std::array<VkImageView, SHADOW_CASCADE_COUNT> m_layerViews{};                  // one layer: rendered
    VkSampler                                     m_sampler    = VK_NULL_HANDLE;
    std::array<AllocatedBuffer, FRAMES_IN_FLIGHT> m_dataBuffers;

    VkPipelineLayout m_opaqueLayout   = VK_NULL_HANDLE;   // set 0 + ShadowDrawData
    VkPipelineLayout m_cutoutLayout   = VK_NULL_HANDLE;   // set 0 + set 1 (material) + ShadowDrawData
    VkPipeline       m_opaquePipeline = VK_NULL_HANDLE;   // vertex stage only
    VkPipeline       m_cutoutPipeline = VK_NULL_HANDLE;   // plus a fragment shader that discards

    shared::ShadowData m_data{};                          // what the last Record fitted and wrote
};

} // namespace pf::vulkan_graphics
```

`Initialize` and `CreatePipelines` are separate because they need different
things at different times. The image and the buffers must exist **before**
`SceneRenderer` writes set 0, which points at them; the pipelines need set 0's
layout and the material set layout, which exist only **after** that. So
`SceneRenderer::Initialize` becomes, with this chapter's two lines marked:

```text
SceneRenderer::Initialize
    m_shadows.Initialize(m_context)          Chapter 17, section 3 - the image, buffers, sampler
    CreateFrameResources()                   Chapter 10; gains bindings 3 and 4 (section 6)
    CreateMaterialResources()                Chapter 15
    CreatePipelines()                        Chapter 11; ends with m_shadows.CreatePipelines (section 4)

SceneRenderer::Shutdown
    DestroyPipelines()                       ends with m_shadows.DestroyPipelines()
    DestroyMaterialResources()
    DestroyFrameResources()
    m_shadows.Shutdown()                     Chapter 17
```

In code, the two lines in `Initialize` and `Shutdown` are:

```cpp
    // SceneRenderer::Initialize (Chapter 17): after the members are stored, before CreateFrameResources.
    if (auto result = m_shadows.Initialize(m_context); !result) { return result; }
```

```cpp
    // SceneRenderer::Shutdown (Chapter 17): its last line, after DestroyFrameResources.
    m_shadows.Shutdown();
```

The pipeline pair is section 4's.

### Where everything lands in `ShadowMaps.cpp`

The fitting math needs nothing from the class, so it lives in file-scope
functions above the namespace, as Chapter 03's `choose*` functions do:

```text
ShadowMaps.cpp
  includes
  static cascadeSplits(count, near, far, lambda)        section 11
  struct CascadeFit                                     section 2
  static lightUp(sunDirection)                          section 2
  static fitTight(camera, slice, sun, reach)            section 2
  static fitStable(camera, slice, sun, reach)           section 12
  namespace pf::vulkan_graphics {
      ShadowMaps::Initialize                            sections 3, 6
      ShadowMaps::CreatePipelines                       section 4
      ShadowMaps::DestroyPipelines                      section 4
      ShadowMaps::Shutdown                              section 3
      ShadowMaps::FitCascades                           section 2; grown in sections 11, 12
      ShadowMaps::Record                                sections 5, 6; grown in section 13
      ShadowMaps::DataBufferInfo, MapImageInfo          section 6
      drawShadowPanel                                   section 9; grown in section 11
  }
```

`ShadowMaps.cpp` includes `ShadowMaps.h`, `Log.h`, `GpuMesh.h` (for Chapter
11's vertex descriptions), `GraphicsPipeline.h`, `VulkanBarriers.h`,
`<glm/gtc/matrix_transform.hpp>`, `<imgui.h>`,
`<algorithm>`, `<cmath>`, `<cstring>`, and `<limits>`.

> **Jump:** every pass so far has looked through one camera — the one the
> player flies. This chapter adds a second, the sun's, which nobody looks
> through and whose only job is to answer questions for the first. Hold two
> spaces in your head at once from here on: **view space**, where "near" and
> "far" mean distance from the player, and **light space**, where they mean
> distance from the sun. The light's camera is *fitted* to the player's view
> every frame (section 2, and in Part 2 sections 11 and 12), so it moves whenever
> the player does — and
> most of this chapter's artifacts come from that movement.

---

# Part 1 — Shadow maps (sections 1-10)

Part 1 builds one shadow map and everything it needs: the light's camera, the
depth image, a pipeline that writes only depth, the pass and its two barriers,
the lookup, and the two fixes every shadow map needs, bias and filtering. It
ends with the shadows in the scene and a test scene to judge them. One map
covers the whole 120 m in front of the camera, which is enough to see every
artifact this part fixes, and blocky enough near the camera to motivate Part 2.

## 1. The idea, and where it goes wrong

Draw the scene from the sun into a depth-only image — the **shadow map**. For
each of its texels, the depth test leaves the distance along the sunlight to
the nearest surface. Later, shading a pixel from the camera, transform its
world position by the same light matrix, read the shadow map at the resulting
texture coordinate, and compare depths:

```text
 light-space depth of this pixel  >  depth stored in the shadow map  ⇒  something nearer the sun → in shadow
 light-space depth of this pixel  ≤  depth stored in the shadow map  ⇒  this pixel is what the sun hit → lit
```

The sun is so far away that its rays are parallel, so the light's camera has
no perspective: it is an **orthographic** projection — a box, not a pyramid.
That makes everything simpler than for a spot light: no near plane to fight,
and a depth value that is simply distance along the light.

Everything else in this chapter is about the two ways the comparison is only
approximate:

- **Resolution.** One shadow-map texel covers some patch of the world. Every
  pixel inside that patch gets the same answer, so shadow edges come out as
  staircases the size of a texel (sections 8, 11, and 12).
- **Precision and sampling.** The shadow map stores the depth of the sun's
  sample at the *centre* of each texel; the camera asks about points anywhere
  inside it. On a surface tilted away from the sun those disagree, and a
  surface ends up shadowing itself (section 7).

---

## 2. The light's camera: fitted to what you can see

**This is `fitTight` and `FitCascades`.** Before any
image exists, decide what the sun's camera looks at. A shadow map has a fixed
number of texels — 2048 × 2048 here — so the smaller the area it covers, the
sharper the shadows. The area that matters is the part of the world **the
player can see**, out to some distance: shadows outside the view are wasted
texels.

So, every frame, the light's box is fitted to the player's view:

1. Take the slice of the camera's frustum that should receive shadows — from
   the near plane to `maxDistance`, 120 m by default, which is far less than a
   USD camera's far plane (often kilometres). Its eight corners, in view space,
   follow from the field of view: at depth `d` the frustum is
   `2 · d · tan(fov/2)` tall and `aspect` times that wide.
2. Move the corners to world space with the inverse of the view matrix.
3. Look at them from the sun: a `glm::lookAt` pointing along the sunlight,
   centred on the slice.
4. Box the corners in that light view space. The box's x and y extent is the
   orthographic projection's left/right/bottom/top; its z extent is the depth
   range.

```text
   sun ─────▶ ─────▶ ─────▶            light space (seen from the side)
          ┌───────────────────┐
  caster  │      ╱╲  slice    │       the box: tight around the slice in x and y,
  reach ◀─┤     ╱  ╲ of the   │       its near plane pulled back towards the sun
          │    ╱    ╲ view    │       by casterReach so that a tree outside the
          │   ╱ cam  ╲        │       slice still shades the ground inside it
          └───────────────────┘
```

Step 4 has one trap. A **caster** does not have to be inside the slice to
shadow something that is: a tower behind you, between you and a low sun, puts
its shadow right in front of you. In light space those casters are *nearer the
sun* than the slice, so the near plane is pulled back towards the sun by
`casterReach` (200 m by default). Casters beyond the far plane need nothing:
they are behind every receiver from the sun's point of view.

> An alternative to pulling the near plane back is **depth clamping**
> (`depthClampEnable`, a Vulkan 1.0 feature): casters in front of the near
> plane are not clipped, they are flattened onto it at depth 0, which still
> occludes everything behind them. It keeps all the depth precision for the
> slice, at the cost of a device feature. This tutorial pulls the plane back
> and spends the precision instead, which section 3's format has to spare.

The orthographic matrix follows the tutorial's one convention from Chapter 10:
`GLM_FORCE_DEPTH_ZERO_TO_ONE` gives depth `[0, 1]`, and `[1][1]` is negated. A
shadow map would work without the flip — it is only ever sampled with the same
matrix it was drawn with — but keeping it means the image is the right way up
if you ever display it, and triangles keep their winding. Section 6 shows that
no flip is needed when sampling either.

```cpp
// File scope, above the namespace block. One cascade's light camera, and the world-space width of one
// of its texels.
struct CascadeFit
{
    glm::mat4 viewProjection{ 1.0f };
    float     texelSize = 0.0f;
};

// File scope. Any up vector not parallel to the light works, as long as it is the same every frame.
static glm::vec3 lightUp(const glm::vec3& sunDirection)
{
    return std::abs(sunDirection.y) > 0.99f ? glm::vec3(0.0f, 0.0f, 1.0f) : glm::vec3(0.0f, 1.0f, 0.0f);
}

// File scope. Section 2: the tightest box around the slice of the view between sliceNear and
// sliceFar, seen from the sun. Wastes nothing, and shimmers as the camera moves (section 12).
static CascadeFit fitTight(const glm::mat4& cameraToWorld, float tanHalfFovY, float aspect,
                           float sliceNear, float sliceFar, const glm::vec3& sunDirection,
                           uint32_t resolution, float casterReach)
{
    // The slice's eight corners: view space, where the camera looks down -Z, then world space.
    const float tanHalfFovX = tanHalfFovY * aspect;
    std::array<glm::vec3, 8> corners;
    glm::vec3 centre(0.0f);
    for (uint32_t i = 0; i < 8; ++i)
    {
        const float     depth = (i & 4) ? sliceFar : sliceNear;
        const glm::vec4 corner((i & 1 ? 1.0f : -1.0f) * depth * tanHalfFovX,
                               (i & 2 ? 1.0f : -1.0f) * depth * tanHalfFovY, -depth, 1.0f);
        corners[i] = glm::vec3(cameraToWorld * corner);
        centre    += corners[i] / 8.0f;
    }

    // Look at the slice along the sunlight, and box the corners in that light's view space.
    const glm::mat4 lightView = glm::lookAt(centre - sunDirection, centre, lightUp(sunDirection));
    glm::vec3 low(std::numeric_limits<float>::max());
    glm::vec3 high(std::numeric_limits<float>::lowest());
    for (const glm::vec3& corner : corners)
    {
        const glm::vec3 p = glm::vec3(lightView * glm::vec4(corner, 1.0f));
        low  = glm::min(low, p);
        high = glm::max(high, p);
    }

    // View space looks down -Z, so the corner nearest the sun has the largest z, and the near plane
    // sits at distance -high.z. Pull it casterReach further towards the sun: a tree outside the
    // slice can still shade the ground inside it.
    glm::mat4 projection = glm::ortho(low.x, high.x, low.y, high.y, -high.z - casterReach, -low.z);
    projection[1][1] *= -1.0f;   // the tutorial's one Y flip, as in Chapter 10's camera

    const float width = std::max(high.x - low.x, high.y - low.y);
    return { projection * lightView, width / static_cast<float>(resolution) };
}
```

The near plane's sign, in numbers: if the corners' light-view z runs from −5 to
−95, the box spans distances 5 to 95 in front of the light's camera. The near
plane goes at 5 − `casterReach` — negative, which an orthographic box allows —
and the far plane at 95.

`texelSize` — how many metres one shadow-map texel covers — is not needed to
draw the map. It is what section 7's normal offset is measured in, and it is
the number to watch when judging any fit: at 120 m with one map it is about
eight centimetres a texel, which is why Part 2 exists.

### What the fit produces: `ShadowData`

Everything the fit computes ends in one struct, `ShadowData`, which the shaders
read at set 0 binding 3 (section 6 binds it): each cascade's light matrix,
where the cascade ends, and the width of its texels, plus the settings the
lookup needs. `ShadowMaps` keeps its CPU copy in `m_data`, and `FitCascades`
below fills the fit's half of it, so the struct comes first. It goes in
`SharedShaderTypes.h` after Chapter 16's `ToneMapping` asserts, and the
namespace's closing brace moves below it once more:

```c
/* Chapter 17: the sun's cascaded shadow maps. */
#define SHADOW_CASCADE_COUNT 4          /* layers in the shadow map; ShadowData::cascadeCount uses 1 to 4 of them */

#define SHADOW_FLAG_ENABLED       1u    /* off: sunShadow() returns 1 and nothing reads the map */
#define SHADOW_FLAG_SHOW_CASCADES 2u    /* cascadeDebugColor() tints each cascade */

struct ShadowData                       /* GLSL: ShadowBlock, std140, set 0 binding 3 */
{
    mat4  cascadeViewProjection[SHADOW_CASCADE_COUNT];   /*   0  world -> the cascade's light clip space */
    vec4  cascadeSplits;                /* 256  view depth where each cascade ends, metres */
    vec4  cascadeTexelSize;             /* 272  world-space width of one texel of each cascade, metres */
    vec4  sunDirection;                 /* 288  xyz the direction sunlight travels (unit); w unused */
    float normalOffset;                 /* 304  receiver offset along its normal, in texels */
    float blendFraction;                /* 308  fraction of each cascade blended into the next */
    float maxDistance;                  /* 312  view depth where shadows end */
    uint  flags;                        /* 316  SHADOW_FLAG_* */
    int   filterRadius;                 /* 320  PCF taps either side: 0 is one tap, 1 is 3 x 3 */
    uint  cascadeCount;                 /* 324  cascades in use, 1 to SHADOW_CASCADE_COUNT */
    uint  padding0;
    uint  padding1;
};
```

Part 1 fills one entry of each per-cascade array, cascade 0; Part 2 uses up to
four. The fields after `sunDirection` come from the panel's settings, which
`Record` copies in (sections 6 and 13), and each is explained where it is used:
`normalOffset` in section 7, `filterRadius` in section 8, and `blendFraction`
and the second flag, the debug view, in section 13.

Per-cascade scalars are packed four to a `vec4` rather than declared as
`float[4]`: in a std140 uniform block every array element is padded to 16
bytes, so a `float[4]` would take 64 bytes and not match a C++ `float[4]`.
Chapter 08 section 8's habits otherwise — no `vec3`, and `static_assert`s on
the size and on the offsets either side of the arrays and the `vec4`s, in the
struct's own `#ifdef __cplusplus` block, which ends the namespace:

```c
#ifdef __cplusplus
    static_assert(sizeof(ShadowData) == 336, "ShadowData layout drifted.");
    static_assert(offsetof(ShadowData, cascadeSplits) == 256, "ShadowData alignment drifted.");
    static_assert(offsetof(ShadowData, normalOffset) == 304, "ShadowData alignment drifted.");
    static_assert(offsetof(ShadowData, filterRadius) == 320, "ShadowData alignment drifted.");
    static_assert(offsetof(ShadowData, cascadeCount) == 324, "ShadowData alignment drifted.");
    }
#endif
```

**This is `FitCascades`**, Part 1's version: one cascade, the whole range from
the near plane to `maxDistance`, fitted with `fitTight`. Part 2 splits the
range into slices and fits each one (section 11), and adds a steadier fit
(section 12); both land in this function.

```cpp
// ShadowMaps.cpp, inside namespace pf::vulkan_graphics. Part 1: one cascade, from the near plane
// to maxDistance. Section 11 splits the range; section 12 adds the stable fit.
void ShadowMaps::FitCascades(const scene::Camera& camera, const glm::mat4& view, float aspect,
                             const glm::vec3& sunDirection, const ShadowSettings& settings)
{
    const glm::mat4 cameraToWorld = glm::inverse(view);
    const float     tanHalfFovY   = std::tan(camera.verticalFov * 0.5f);
    const float     farDistance   = std::min(settings.maxDistance, camera.farPlane);

    const CascadeFit fit = fitTight(cameraToWorld, tanHalfFovY, aspect, camera.nearPlane, farDistance,
                                    sunDirection, m_resolution, settings.casterReach);
    m_data.cascadeViewProjection[0] = fit.viewProjection;
    m_data.cascadeSplits[0]         = farDistance;
    m_data.cascadeTexelSize[0]      = fit.texelSize;
    m_data.cascadeCount = 1;
    m_data.sunDirection = glm::vec4(sunDirection, 0.0f);
    m_data.maxDistance  = farDistance;
}
```

The camera's inverse view matrix is the camera's own world matrix (rigid, so
the inverse is exact). Taking it from `view` rather than from the camera node
means a demo without a scene graph — the grass, which has only a `Camera` and a
`Transform` — calls this the same way.

---

## 3. The shadow image

**This is the first half of `ShadowMaps::Initialize`.** One depth image, square,
with one **array layer** per cascade. There are four layers from the start, one
for each cascade Part 2 will use; Part 1 draws only layer 0, and section 11 says
why an array beats the alternatives.

The format is **`D16_UNORM`**, not the `D32_SFLOAT` Chapter 10 chose for the
scene's depth. Three reasons here, and a fourth that matters most, about depth
bias, which section 7 gives once bias has been explained — keep it in mind
before ever "upgrading" this to 32 bits:

1. **Orthographic depth is linear.** A perspective depth buffer crams most of
   its precision near the camera, which is why Chapter 10 wanted floating point
   there. An orthographic projection maps distance to depth in a straight line,
   so 16 evenly spaced bits are evenly useful: over a 500 m depth range, one
   step is 7.6 mm.
2. **It is the one depth format the spec guarantees for both uses.** Every
   Vulkan device must support `D16_UNORM` as a depth attachment *and* as a
   sampled image. `D32_SFLOAT` is only guaranteed sampled; as an attachment the
   guarantee is "it or `X8_D24_UNORM_PACK32`".
3. **Half the memory and bandwidth.** 2048 × 2048 × 4 layers is 32 MB at 16
   bits, 64 MB at 32, and the shadow pass writes all of it every frame.

```cpp
InitializationResult ShadowMaps::Initialize(const VulkanContext& context, uint32_t resolution)
{
    m_context    = context;
    m_resolution = resolution;

    // Section 3. D16_UNORM is mandatory as a sampled depth attachment; linear filtering of it is not.
    VkFormatProperties formatProperties{};
    vkGetPhysicalDeviceFormatProperties(m_context.physicalDevice, SHADOW_FORMAT, &formatProperties);
    m_linearFiltering = (formatProperties.optimalTilingFeatures
                         & VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT) != 0;
    if (!m_linearFiltering)
    {
        Log::warning("D16_UNORM cannot be filtered linearly here; shadow taps fall back to NEAREST.");
    }

    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = SHADOW_FORMAT,
        .extent        = { resolution, resolution, 1 },
        .mipLevels     = 1,
        .arrayLayers   = SHADOW_CASCADE_COUNT,               // one layer per cascade
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT   // the shadow pass draws into it
                       | VK_IMAGE_USAGE_SAMPLED_BIT,                   // the scene pass compares against it
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{
        .flags = VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT,
        .usage = VMA_MEMORY_USAGE_AUTO,
    };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &m_image, &m_allocation, nullptr)
        != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the shadow map.");
    }
```

What is checked and what is not follows from reason 2: being renderable and
sampleable is guaranteed for this format, so it is not queried; filtering it
linearly is not guaranteed, and section 6 depends on it, so it is — and its
absence is reported and worked around, not asserted.

The image needs **two kinds of view**. Rendering needs one layer at a time: a
rendering attachment is a single 2D image. Sampling wants all of them at once,
as a 2D *array*, so the shader can pick a layer per pixel:

```cpp
    // One view of every layer for sampling, and one view per layer to render each cascade into.
    VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_image,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D_ARRAY,
        .format           = SHADOW_FORMAT,
        .subresourceRange = { VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, 0, SHADOW_CASCADE_COUNT },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_arrayView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the shadow map array.");
    }
    for (uint32_t layer = 0; layer < SHADOW_CASCADE_COUNT; ++layer)
    {
        viewInfo.viewType         = VK_IMAGE_VIEW_TYPE_2D;
        viewInfo.subresourceRange = { VK_IMAGE_ASPECT_DEPTH_BIT, 0, 1, layer, 1 };
        if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_layerViews[layer]) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkCreateImageView failed for a shadow cascade.");
        }
    }
```

`Initialize` continues in section 6 with the sampler and the buffers. The
shadow map is not sized by the window, so nothing here is rebuilt on resize —
and, like Chapter 10's depth buffer, **one** image serves both frames in
flight. That is safe because the queue runs frames in order and the barriers
in section 5 order each frame's writes after the previous frame's reads.

**This is `Shutdown`.** Reverse order, every handle checked by Vulkan's own
null-is-a-no-op rule. VMA's destroy asserts on a null allocator, so the
function returns early when `Initialize` never ran:

```cpp
void ShadowMaps::Shutdown()
{
    if (m_context.device == VK_NULL_HANDLE) { return; }   // never initialized

    DestroyPipelines();
    for (AllocatedBuffer& buffer : m_dataBuffers)
    {
        if (buffer.buffer != VK_NULL_HANDLE) { destroyBuffer(m_context, buffer); }
    }
    vkDestroySampler(m_context.device, m_sampler, nullptr);
    for (VkImageView& view : m_layerViews)
    {
        vkDestroyImageView(m_context.device, view, nullptr);
        view = VK_NULL_HANDLE;
    }
    vkDestroyImageView(m_context.device, m_arrayView, nullptr);
    vmaDestroyImage(m_context.allocator, m_image, m_allocation);   // a null image is a no-op
    m_sampler    = VK_NULL_HANDLE;
    m_arrayView  = VK_NULL_HANDLE;
    m_image      = VK_NULL_HANDLE;
    m_allocation = VK_NULL_HANDLE;
    m_context    = {};
}
```

---

## 4. A pipeline that only writes depth

**This is `ShadowMaps::CreatePipelines`**, and two small changes to Chapter 06's
`createGraphicsPipeline` that it needs.

The shadow pass wants exactly one thing from each triangle: its depth from the
sun. No color is written, so under dynamic rendering the pass has **no color
attachments**, and its pipelines declare none. And for an opaque caster there
is nothing for a fragment shader to do — the rasterizer produces depth without
one — so the pipeline has **no fragment stage at all**. That is legal, and it
is the fastest way to draw depth: no shader invocations per pixel, and early
depth testing for everything.

Chapter 06's `createGraphicsPipeline` assumed both a fragment shader and one
color attachment. `GraphicsPipelineDesc` itself does not change — an empty
`fragmentShader` path and an empty `colorFormats` span already say "none", and
its comment should say so:

```cpp
    std::filesystem::path       fragmentShader;   // Chapter 17: empty for a depth-only pipeline
```

Two edits to the function make it accept both:

```cpp
    // Chapter 17: a depth-only pipeline has no fragment stage at all.
    const bool hasFragmentStage = !desc.fragmentShader.empty();

    const std::vector<uint32_t> vertexSpirv   = readSpirv(desc.vertexShader);     // logs if missing
    const std::vector<uint32_t> fragmentSpirv = hasFragmentStage ? readSpirv(desc.fragmentShader)
                                                                 : std::vector<uint32_t>{};
    if (vertexSpirv.empty() || (hasFragmentStage && fragmentSpirv.empty())) { return VK_NULL_HANDLE; }

    const VkShaderModule vertexModule   = createShaderModule(device, vertexSpirv);
    const VkShaderModule fragmentModule = hasFragmentStage ? createShaderModule(device, fragmentSpirv)
                                                           : VK_NULL_HANDLE;
```

and, where the create info counts its stages, `.stageCount = hasFragmentStage ?
2u : 1u` — the vertex stage is first in the `stages` array, so a count of one
simply leaves the fragment entry out. Destroying a null `fragmentModule`
afterwards is a no-op.

```cpp
    // One blend state per color attachment; a depth-only pipeline has none (Chapter 17).
    const std::vector<VkPipelineColorBlendAttachmentState> blendAttachments(desc.colorFormats.size(),
                                                                            blendAttachment);
    const VkPipelineColorBlendStateCreateInfo colorBlend{
        .sType           = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
        .attachmentCount = static_cast<uint32_t>(blendAttachments.size()),
        .pAttachments    = blendAttachments.data(),
    };
```

That replaces Chapter 06's `.attachmentCount = 1`. Under dynamic rendering the
blend state's attachment count must equal `VkPipelineRenderingCreateInfo`'s
color attachment count, so a hard-coded 1 is a validation error the first time
a pipeline has zero (or two).

Now the shadow pass's own shaders. The vertex shader is the mesh vertex shader
reduced to its first line — the position — transformed by the **cascade's**
light matrix instead of the camera's. The matrix comes from `ShadowData` (set 0
binding 3, section 6), indexed by a cascade number pushed with the model matrix,
so one pipeline draws every cascade:

```glsl
// Shaders/Shadows/ShadowDepth.vert.glsl - Chapter 17. Every shadow caster goes through this; opaque
// casters have no fragment shader at all.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SharedShaderTypes.h"

layout(location = 0) in  vec3 position;   // scene::Vertex, Chapter 11's vertex input
layout(location = 2) in  vec2 uv;
layout(location = 0) out vec2 outUv;      // read only by ShadowCutout.frag

layout(std140, set = 0, binding = 3) uniform ShadowBlock { ShadowData shadowData; };
layout(push_constant) uniform ShadowDrawBlock { ShadowDrawData draw; };

void main()
{
    gl_Position = shadowData.cascadeViewProjection[draw.cascade] * draw.model * vec4(position, 1.0);
    outUv       = uv;
}
```

The push constants get a twin in `SharedShaderTypes.h`, the second of the two
shared structs this chapter adds (section 2's `ShadowData` is the first). 80
bytes, well inside Chapter 08's 128-byte budget. It goes between Chapter 16's
`ToneMapping` asserts and section 2's `ShadowData`, with asserts of its own:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 17. GLSL: ShadowDrawBlock, the shadow pass's push constants. */
struct ShadowDrawData
{
    mat4 model;                         /*  0  local -> world */
    uint cascade;                       /* 64  which cascadeViewProjection to draw with */
    uint padding0;
    uint padding1;
    uint padding2;
};

#ifdef __cplusplus
    static_assert(sizeof(ShadowDrawData) == 80, "ShadowDrawData layout drifted.");
#endif
```

The shader also reads section 2's `ShadowData`, through set 0 binding 3, which
section 6 adds to the descriptor set layout.

**Cutouts cast cutout shadows.** A leaf from Chapter 15 is a quad whose texture
says where the leaf is. Drawn with no fragment shader, it would cast a solid
rectangle. Cutout materials get a second pipeline with a fragment shader that
performs the same test as the mesh shader — `materialOpacity`, from Chapter 15's
`MaterialSet.glsl`, so the two cannot disagree — and discards. It writes no
color; it exists only to discard:

```glsl
// Shaders/Shadows/ShadowCutout.frag.glsl - Chapter 17. Cutout materials cast cutout shadows: the same
// test as Mesh.frag.glsl's, against the same set 1. No color output; depth comes from the rasterizer.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "MaterialSet.glsl"

layout(location = 0) in vec2 uv;

void main()
{
    if (materialOpacity(uv) < material.opacityThreshold) { discard; }
}
```

`discard` compiles to `OpDemoteToHelperInvocation` for Vulkan 1.3, which needs
the `shaderDemoteToHelperInvocation` feature — enabled in Chapter 15 section 11
for exactly this kind of shader. Without it, creating the module fails
validation.

The two pipeline layouts differ only in set 1. Both start with the scene's set 0
layout and declare the **same** push-constant range, so a set 0 bound through
one stays valid for a pipeline built with the other — Vulkan calls such layouts
*compatible* up to set 0, and it requires identical push-constant ranges for
that, not just identical set layouts.

Four choices in the pipeline itself, each worth a sentence:

- **Only the attributes the shader reads.** The shadow vertex shader reads
  locations 0 and 2. Describing all four of `meshVertexAttributes()` would work,
  with a `WARNING-Shader-OutputNotConsumed` per pipeline for the two nobody
  reads. The binding's 48-byte stride already skips them.
- **No culling.** A common trick culls *front* faces in the shadow pass, so only
  back faces — which are away from the sun and never lit anyway — write depth,
  and lit surfaces cannot shadow themselves. It fails for anything single-sided:
  a USD ground plane, a leaf, a sign. Those are everywhere in imported scenes,
  so this pass culls nothing and section 7 handles self-shadowing instead.
- **Depth bias is dynamic.** Both its switch (`VK_DYNAMIC_STATE_DEPTH_BIAS_ENABLE`,
  core in 1.3) and its values (`VK_DYNAMIC_STATE_DEPTH_BIAS`, core since 1.0)
  are set while recording, so section 7's sliders work without rebuilding a
  pipeline.
- **One sample**, whatever Chapter 18 later sets for the scene. The shadow map
  is its own attachment; the scene's sample count has nothing to do with it.

```cpp
InitializationResult ShadowMaps::CreatePipelines(VkPipelineCache cache, VkDescriptorSetLayout frameSetLayout,
                                                 VkDescriptorSetLayout materialSetLayout)
{
    // Section 4. Both layouts start with the scene's set 0 and the same push range, so set 0 bound with
    // one stays valid for a pipeline built with the other.
    const VkPushConstantRange pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT,
        .offset     = 0,
        .size       = sizeof(shared::ShadowDrawData),
    };
    const VkDescriptorSetLayout cutoutSets[] = { frameSetLayout, materialSetLayout };
    const VkPipelineLayoutCreateInfo opaqueLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &frameSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    const VkPipelineLayoutCreateInfo cutoutLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 2,
        .pSetLayouts            = cutoutSets,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &opaqueLayoutInfo, nullptr, &m_opaqueLayout) != VK_SUCCESS ||
        vkCreatePipelineLayout(m_context.device, &cutoutLayoutInfo, nullptr, &m_cutoutLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the shadow pass.");
    }

    // Depth only: no color attachments, no fragment shader for opaque casters, one sample whatever the
    // scene uses. Depth bias is dynamic so the panel can tune it; culling is off (section 4).
    const VkDynamicState biasStates[] = { VK_DYNAMIC_STATE_DEPTH_BIAS_ENABLE, VK_DYNAMIC_STATE_DEPTH_BIAS };

    // The shadow vertex shader reads only position (location 0) and uv (location 2) of scene::Vertex.
    // Describing the other two would work, with a warning per pipeline that nothing consumes them.
    const std::array<VkVertexInputAttributeDescription, 2> attributes = {
        meshVertexAttributes()[0], meshVertexAttributes()[2],
    };
    GraphicsPipelineDesc desc{
        .vertexShader     = "Shadows/ShadowDepth.vert.spv",
        .vertexBindings   = meshVertexBindings(),
        .vertexAttributes = attributes,
        .depthFormat      = SHADOW_FORMAT,
        .depthTest        = true,
        .depthWrite       = true,
        .depthCompare     = VK_COMPARE_OP_LESS,
        .cullMode         = VK_CULL_MODE_NONE,
        .dynamicStates    = biasStates,
        .layout           = m_opaqueLayout,
    };
    m_opaquePipeline = createGraphicsPipeline(m_context.device, cache, desc);

    desc.fragmentShader = "Shadows/ShadowCutout.frag.spv";
    desc.layout         = m_cutoutLayout;
    m_cutoutPipeline    = createGraphicsPipeline(m_context.device, cache, desc);

    if (m_opaquePipeline == VK_NULL_HANDLE || m_cutoutPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the shadow caster pipelines failed.");
    }
    return InitializationResult::success();
}

void ShadowMaps::DestroyPipelines()
{
    vkDestroyPipeline(m_context.device, m_cutoutPipeline, nullptr);
    vkDestroyPipeline(m_context.device, m_opaquePipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_cutoutLayout, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_opaqueLayout, nullptr);
    m_cutoutPipeline = m_opaquePipeline = VK_NULL_HANDLE;
    m_cutoutLayout   = m_opaqueLayout   = VK_NULL_HANDLE;
}
```

`SceneRenderer` builds and destroys them alongside its own. `CreatePipelines`
ends by returning their result instead of success, and `DestroyPipelines` ends
with their destruction:

```cpp
    // SceneRenderer::CreatePipelines (Chapter 17): its last line, in place of `return InitializationResult::success();`.
    return m_shadows.CreatePipelines(m_pipelineCache, m_frameSetLayout, m_materialSetLayout);
```

```cpp
    // SceneRenderer::DestroyPipelines (Chapter 17): its last line.
    m_shadows.DestroyPipelines();
```

Because Chapter 18 rebuilds pipelines by re-running a demo's `Setup`, these two
follow along without any code of their own.

---

## 5. Recording the shadow pass, and its two barriers

**This is `ShadowMaps::Record`**, the GPU half. (Its first lines fill this
frame's `ShadowData`; section 6 shows them.)

The shadow map is a resource **written by one pass and read by another every
frame**, which Chapter 04's cookbook says needs two barriers: one in each
direction. Take them through the three questions.

**Before the shadow pass** — the map was last *read*, by the previous frame's
scene pass, in its fragment shader. Now it will be *written* by depth tests.

- Q1, execution: the previous fragment-shader reads must finish before this
  frame's depth tests start. Source `FRAGMENT_SHADER`, destination
  `EARLY_FRAGMENT_TESTS | LATE_FRAGMENT_TESTS` (the clear and the depth writes
  happen in both).
- Q2, memory: a write after a read leaves nothing to flush, so the source access
  is `NONE`; the destination is the depth attachment's read and write.
- Q3, layout: `UNDEFINED` to `DEPTH_ATTACHMENT_OPTIMAL`. Every layer is cleared,
  so the old contents do not matter.

**After the shadow pass** — written by depth tests, about to be *sampled* by the
scene pass's fragment shader.

- Q1: depth tests before fragment shading. Source
  `EARLY_FRAGMENT_TESTS | LATE_FRAGMENT_TESTS`, destination `FRAGMENT_SHADER`.
- Q2: the depth writes made available, and visible to sampled reads:
  `DEPTH_STENCIL_ATTACHMENT_WRITE` to `SHADER_SAMPLED_READ`.
- Q3: `DEPTH_ATTACHMENT_OPTIMAL` to `SHADER_READ_ONLY_OPTIMAL`, which is valid
  for sampling a depth-only image.

`transitionImage` covers every layer (`VK_REMAINING_ARRAY_LAYERS`), so one call
each way handles all four cascades. Pass `VK_IMAGE_ASPECT_DEPTH_BIT`, as for
Chapter 10's depth buffer.

```cpp
    // ---- GPU. Section 5's first barrier: last frame's scene pass sampled every layer in its fragment
    // shader. Overwriting needs only an execution dependency on that read; UNDEFINED discards. ----
    transitionImage(commandBuffer, m_image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT | VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
```

Then one **rendering scope per cascade**, each over one layer's view: cleared to
1.0 (as far from the sun as the box goes), stored (the scene pass reads it), no
color attachments. The viewport is the shadow map's size, not the window's.
Depth bias is set here because it is dynamic state (section 7 says what the
numbers mean); set 0 is bound once per scope, since a new rendering scope does
not disturb bound sets but binding here keeps each scope self-contained:

```cpp
    const float      size = static_cast<float>(m_resolution);
    const VkViewport viewport{ 0.0f, 0.0f, size, size, 0.0f, 1.0f };
    const VkRect2D   scissor{ { 0, 0 }, { m_resolution, m_resolution } };

    for (uint32_t cascade = 0; cascade < m_data.cascadeCount; ++cascade)
    {
        const VkRenderingAttachmentInfo depthAttachment{
            .sType       = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO,
            .imageView   = m_layerViews[cascade],
            .imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
            .resolveMode = VK_RESOLVE_MODE_NONE,
            .loadOp      = VK_ATTACHMENT_LOAD_OP_CLEAR,
            .storeOp     = VK_ATTACHMENT_STORE_OP_STORE,
            .clearValue  = { .depthStencil = { 1.0f, 0 } },
        };
        const VkRenderingInfo renderingInfo{
            .sType                = VK_STRUCTURE_TYPE_RENDERING_INFO,
            .renderArea           = scissor,
            .layerCount           = 1,
            .colorAttachmentCount = 0,                       // depth only
            .pDepthAttachment     = &depthAttachment,
        };
        vkCmdBeginRendering(commandBuffer, &renderingInfo);

        vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
        vkCmdSetScissor(commandBuffer, 0, 1, &scissor);
        vkCmdSetDepthBiasEnable(commandBuffer, VK_TRUE);
        vkCmdSetDepthBias(commandBuffer, settings.biasConstant, 0.0f, settings.biasSlope);   // clamp 0: no feature needed
        vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_opaqueLayout,
                                0, 1, &frameSet, 0, nullptr);
```

Inside the scope, the pass hands over to the two callbacks: first the scene's
casters, which `SceneRenderer` draws (section 9 shows its loop), then any extra
ones the demo supplied. Each draws into the cascade it is told, with everything
the scope set up still in place:

```cpp
        drawCasters(commandBuffer, cascade);
        if (extraCasters) { extraCasters(commandBuffer, cascade); }

        vkCmdEndRendering(commandBuffer);
    }

    // Section 5's second barrier: every layer's depth writes, visible to the scene pass's fragment shader.
    transitionImage(commandBuffer, m_image,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
}
```

These two barriers are the shadow-map rows of Chapter 04's appendix, "Barriers
the later chapters add".

`extraCasters` is the door for casters that are not meshes in the draw list —
Chapter 27 draws a raised, dithered terrain impostor through it so that grass
appears to shade the ground. A demo that has none passes nothing.

Each cascade draws **every** caster. With Part 2's four cascades that is four times the
draws of the scene pass, which is the first thing to cut when this gets slow:
cull each cascade's casters against that cascade's light box (Chapter 12's
`frustumFromViewProjection` on its matrix, `m_data.cascadeViewProjection[i]`,
extended back by the caster reach), so the near cascade, which covers a few
metres, draws only what is near. Chapter 19's instancing cuts the per-draw cost itself.

> A frame that has **no sun** — `Record` is told `nullopt` — skips both
> barriers and every pass, and writes `flags = 0`. The map then stays in
> `SHADER_READ_ONLY_OPTIMAL` from the last frame that had one, which is still a
> valid layout for the descriptor, and the shader never reads it. That is also
> why section 6's `Initialize` puts the map in that layout once, before any
> frame exists.

---

## 6. Sampling it: set 0 bindings 3 and 4, and a comparison sampler

**This is the rest of `ShadowMaps::Initialize`, the top of `Record`, and the
first part of `Shadows.glsl`.**

### What the scene shader needs

Two things, and the index's set 0 table already reserves their slots:

| Binding | Type | Stages | Contents |
| --- | --- | --- | --- |
| 3 | uniform buffer, one per frame in flight | vertex, fragment | `ShadowData`: each cascade's light matrix, where the cascades split, settings |
| 4 | combined image sampler | fragment | the shadow map, all layers, through a **comparison** sampler |

Binding 2 is Chapter 19's per-instance buffer. Leaving a gap in binding numbers
is legal; the layout simply does not mention 2 until then.

`ShadowData` changes every frame — the camera moves, so the fit does — which
puts it under Chapter 08's rule: never write what the GPU might still be
reading. So it gets one buffer per frame in flight, exactly like `FrameData`,
and `Record` writes `m_dataBuffers[frameIndex]`, whose previous reader finished
before the fence the renderer waited on. The image, written by the GPU itself
in order, needs only one copy.

Binding 3 holds section 2's `ShadowData`, already in `SharedShaderTypes.h`.

### The comparison sampler

A shadow lookup does not want the stored depth; it wants the answer to *is my
depth ≤ the stored one?* Vulkan can do that comparison in the sampler. With
`compareEnable` set, sampling through a `sampler2DArrayShadow` takes a
**reference depth** alongside the coordinates and returns the comparison's
result — 1.0 for pass, 0.0 for fail — instead of the texel.

That alone saves an instruction. What makes it worth having is what happens
with `LINEAR` filtering: the hardware compares each of the **four** texels in
the bilinear footprint against the reference and then filters the four
*results*. A pixel straddling a shadow edge gets 0.25, 0.5, or 0.75 instead of
a hard 0 or 1 — a 2×2 percentage-closer filter for the price of one tap
(section 8 builds on it).

The alternative — sample the depth with an ordinary sampler and compare in the
shader — can only do that by fetching four texels and comparing each itself.
And filtering the **depths** first and comparing once is simply wrong: the
average of a near caster's depth and the far ground's depth is a depth where
nothing exists, and the comparison against it is meaningless.

The rest of the sampler's settings each answer one question:

- `compareOp = LESS_OR_EQUAL`: the result is `reference <= stored` — lit when
  this point is at or before the first surface the sun hit.
- `CLAMP_TO_BORDER` with an opaque white border: outside the map the stored
  depth reads as 1.0, the far end of the box, so anything the map does not cover
  counts as lit rather than repeating the map's edge across the world.
- One mip level, `maxLod = 0`.
- `NEAREST` if the format cannot filter linearly — rare, but then the result is a
  plain 0 or 1 per tap and section 8's loop does all the filtering.

```cpp
    // Section 6. A comparison sampler: texture() returns how much of the footprint passes
    // "reference <= stored", not the stored depth. Outside the map counts as lit.
    const VkFilter filter = m_linearFiltering ? VK_FILTER_LINEAR : VK_FILTER_NEAREST;
    const VkSamplerCreateInfo samplerInfo{
        .sType         = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter     = filter,
        .minFilter     = filter,
        .mipmapMode    = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU  = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER,
        .addressModeV  = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER,
        .addressModeW  = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER,
        .compareEnable = VK_TRUE,
        .compareOp     = VK_COMPARE_OP_LESS_OR_EQUAL,
        .maxLod        = 0.0f,
        .borderColor   = VK_BORDER_COLOR_FLOAT_OPAQUE_WHITE,   // depth 1.0: nothing in front, lit
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_sampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the shadow map.");
    }
```

`Initialize` ends with the per-frame buffers, zeroed — `flags` 0 means "no
shadows" — and a one-time transition into the layout the descriptor names, so
that set 0 is valid to bind before any shadow pass has run:

```cpp
    // One ShadowData per frame in flight, like FrameData. Zeroed: flags 0 means "no shadows".
    for (AllocatedBuffer& buffer : m_dataBuffers)
    {
        buffer = createBuffer(m_context, sizeof(shared::ShadowData), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        if (buffer.buffer == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a ShadowData buffer failed.");
        }
        std::memset(buffer.mapped, 0, sizeof(shared::ShadowData));
        vmaFlushAllocation(m_context.allocator, buffer.allocation, 0, VK_WHOLE_SIZE);
    }

    // Give the map the layout the scene pass samples it in, once, so that it is valid to bind even in a
    // frame that records no shadow pass. Its contents are undefined, and flags 0 means no shader reads them.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                        VK_IMAGE_ASPECT_DEPTH_BIT);
    });
    return InitializationResult::success();
}

VkDescriptorBufferInfo ShadowMaps::DataBufferInfo(uint32_t frameIndex) const
{
    return { m_dataBuffers[frameIndex].buffer, 0, sizeof(shared::ShadowData) };
}

VkDescriptorImageInfo ShadowMaps::MapImageInfo() const
{
    return { m_sampler, m_arrayView, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
}
```

The `NONE` source on that transition is the one case Chapter 04 allows it: a
freshly created image with no earlier use. `immediateSubmit` waits on its fence,
so nothing later needs ordering against it.

### Bindings 3 and 4 in `CreateFrameResources`

Chapter 16 showed the pattern for binding 1; these two follow it. The layout's
binding array gains:

```cpp
// SceneRenderer.cpp, CreateFrameResources (Chapter 17): bindings 3 and 4 join set 0's binding array.
{ .binding         = 3,
  .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
  .descriptorCount = 1,
  .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT },
{ .binding         = 4,
  .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
  .descriptorCount = 1,
  .stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT },
```

Binding 3 is read by the shadow pass's *vertex* shader as well as by the scene's
fragment shaders, so it lists both stages. The pool gains one uniform buffer and
one combined image sampler per frame in flight:

```cpp
// The pool, Chapter 17: one more uniform buffer and one combined image sampler per set.
{ VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         FRAMES_IN_FLIGHT },
{ VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, FRAMES_IN_FLIGHT },
```

Add the uniform-buffer count to Chapter 10's existing `UNIFORM_BUFFER` entry if
you prefer one entry per type; a pool accepts either. And each frame's set gets
two writes, in the same loop that writes binding 1 — set `i` points at
`ShadowData` buffer `i`, and every set at the same image:

```cpp
// CreateFrameResources, in the per-frame loop after binding 1's write (Chapter 17).
const VkDescriptorBufferInfo shadowDataInfo = m_shadows.DataBufferInfo(i);
const VkDescriptorImageInfo  shadowMapInfo  = m_shadows.MapImageInfo();
const VkWriteDescriptorSet shadowWrites[] = {
    { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
      .dstSet          = m_frameSets[i],
      .dstBinding      = 3,
      .descriptorCount = 1,
      .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
      .pBufferInfo     = &shadowDataInfo },
    { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
      .dstSet          = m_frameSets[i],
      .dstBinding      = 4,
      .descriptorCount = 1,
      .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
      .pImageInfo      = &shadowMapInfo },
};
vkUpdateDescriptorSets(m_context.device, 2, shadowWrites, 0, nullptr);
```

That is why `m_shadows.Initialize` runs before `CreateFrameResources`: the
handles these writes point at must exist. The sets are written once and never
again.

### Writing `ShadowData` each frame

**This is the top of `ShadowMaps::Record`**, before section 5's barrier. The
fence for `frameIndex` has been waited on, so this frame's buffer is free:

```cpp
void ShadowMaps::Record(VkCommandBuffer commandBuffer, uint32_t frameIndex, VkDescriptorSet frameSet,
                        const scene::Camera& camera, const glm::mat4& view, float aspect,
                        std::optional<glm::vec3> sunDirection, const ShadowSettings& settings,
                        const ShadowCasterCallback& drawCasters, const ShadowCasterCallback& extraCasters)
{
    // ---- CPU: this frame's ShadowData. The fence for frameIndex has been waited on. ----
    const bool active = settings.enabled && sunDirection.has_value();
    if (active)
    {
        FitCascades(camera, view, aspect, glm::normalize(*sunDirection), settings);
    }
    m_data.normalOffset  = settings.normalOffset;
    m_data.filterRadius  = settings.filterRadius;
    m_data.flags         = active ? SHADOW_FLAG_ENABLED : 0u;   // section 13 adds the debug view's flag
    std::memcpy(m_dataBuffers[frameIndex].mapped, &m_data, sizeof(m_data));
    vmaFlushAllocation(m_context.allocator, m_dataBuffers[frameIndex].allocation, 0, VK_WHOLE_SIZE);

    // No sun: the map stays in SHADER_READ_ONLY_OPTIMAL from the last frame, and flags tell the shader not
    // to read it.
    if (!active) { return; }
```

No barrier is needed after the `memcpy`: Chapter 10 section 7's rule for host
writes covers it, as it does `FrameData` and the light buffer.

### Looking a point up

**This is `Shadows.glsl`**, Part 1's version. It declares the two bindings
itself, so any fragment shader that includes it — the mesh shader here, the
grass in Chapter 25 — gets them.

To look a point up, transform it by the cascade's light matrix. That gives
clip space, and the GPU's next step for any clip-space position is the divide
by w, which gives **normalized device coordinates** (NDC): x and y in
`[-1, 1]` across the image, depth in `[0, 1]` — the last arrow of Chapter 10
section 1's diagram. The projection is orthographic, so w is 1 and clip space
is already NDC. The texture coordinate is `xy * 0.5 + 0.5`, with **no Y flip**.
That looks suspicious after Chapter 10's `[1][1]` and Chapter 14's `v = 1 - v`,
so be precise about why: when the shadow pass rasterized, NDC y = −1 landed on
the *first row* of the image; texture coordinate v = 0 *is* the first row.
Whatever sign the light matrix puts on y, rasterizing and sampling apply the
same mapping, so they agree. The depth is the reference value for the
comparison, and the lookup is the comparison sampler's one call, with the layer
and the reference packed into the coordinate:

```glsl
// Shaders/Include/Shadows.glsl - Chapter 17. The sun's shadows, for any fragment shader that
// draws into the scene. Included, never compiled on its own. Declares set 0 bindings 3 and 4.
#ifndef PF_SHADOWS_GLSL
#define PF_SHADOWS_GLSL

#include "SharedShaderTypes.h"

layout(std140, set = 0, binding = 3) uniform ShadowBlock { ShadowData shadowData; };
layout(set = 0, binding = 4) uniform sampler2DArrayShadow shadowMap;

// How lit one point is by one cascade: 1.0 lit, 0.0 in shadow, in between at a filtered edge.
float sampleCascade(vec3 worldPosition, vec3 worldNormal, int cascade)
{
    // Orthographic: w is 1, so clip space is already normalized device coordinates.
    vec4  lightClip = shadowData.cascadeViewProjection[cascade] * vec4(worldPosition, 1.0);   // section 7 offsets it
    vec2  uv        = lightClip.xy * 0.5 + 0.5;    // NDC -1..1 to texture 0..1, no flip (section 6)
    float depth     = lightClip.z;                 // what the shadow pass would have written here
    return texture(shadowMap, vec4(uv, float(cascade), depth));   // section 8 filters it
}

// 1.0 where the sun reaches this point, 0.0 where something blocks it. Multiply the SUN's
// direct light by it and nothing else - not other lights, not ambient.
//   worldNormal: unit length, facing the side being shaded (already flipped for back faces)
//   viewDepth:   distance in front of the camera, -(frame.view * vec4(worldPosition, 1.0)).z
float sunShadow(vec3 worldPosition, vec3 worldNormal, float viewDepth)
{
    if ((shadowData.flags & SHADOW_FLAG_ENABLED) == 0u || viewDepth >= shadowData.maxDistance)
    {
        return 1.0;
    }
    return sampleCascade(worldPosition, worldNormal, 0);   // Part 1: one cascade; section 13 chooses
}

#endif
```

`worldNormal` is not used yet; section 7 needs it.

> **Read sections 9 and 10 next, then come back to 7 and 8.** Sections 7 and 8
> are experiments on a running scene: they open by moving the Shadows panel's
> sliders and looking at boxes in section 10's test scene. Section 9 needs only
> `sunShadow` as it stands, so build sections 9 and 10 now, load
> `ShadowTest.usda`, and see the sun's first shadows. They are clean already —
> section 5's `vkCmdSetDepthBias` applies the panel's two depth-bias rows — and
> hard at their edges, from the comparison sampler's one 2×2 tap. The panel's
> **Normal offset** and **Filter radius** rows do nothing yet: sections 7 and 8
> write the code behind them.

---

## 7. Shadow acne, peter-panning, and bias

Turn **Bias constant**, **Bias slope**, and **Normal offset** all to zero on the
panel. Lit surfaces fill with stripes and moiré rings — every lit surface,
the ground worst of all where it faces the sun at a slant. That is the classic
*shadow acne*.

**Why.** The shadow map stores one depth per texel — the depth of the surface
at that texel's centre. A pixel of the ground compares *its own* depth against
that. On a surface tilted away from the sun, the surface's depth changes across
the texel: points on one side of the centre are nearer the sun than the stored
value, points on the other side are farther. The farther ones fail the test —
the surface shadows itself — and since that happens in every texel, the failures
make a pattern at the shadow map's resolution. Depth quantization (one 16-bit
step) adds to it, and on a surface facing the sun that alone is enough.

```text
 sun ↘                        stored depth per texel (flat steps)
        ___                    ___
           ‾‾‾___  ← surface      ‾‾‾  each texel's samples on the far half
                 ‾‾‾___               of the step test "behind" the stored
                       ‾‾‾            value: self-shadowed
```

Two fixes, which do different jobs, and the defaults use both.

**Slope-scaled depth bias, at the caster.** Push the depth *written into the
shadow map* away from the sun by an amount that grows with the surface's slope
in light space. That is exactly what the rasterizer's depth bias computes:

```text
 bias = depthBiasConstantFactor × r  +  depthBiasSlopeFactor × m
```

In words: **r** is the depth format's smallest step, for `D16_UNORM` one
65536th of the box's depth range, or up to twice that: the spec leaves
the exact value to the driver. **m** is how much the triangle's depth
changes from one shadow-map texel to the next, in its steepest direction. A
floor facing the sun straight on has the same depth at every texel, so its m is
0 and only the constant term applies — enough to cover the rounding to 16 bits.
A floor tilted 45° to the sun gets one texel-width deeper with every texel, so
its m is one texel's width: the slope term pushes a tilted surface back by
exactly the amount its depth changes inside a texel, which is what the acne
was. Worked, with one map over 120 m, a texel about 8 cm wide: the default
slope factor of 2 pushes a 45° floor's stored depth 16 cm away from the sun.

Both come from `vkCmdSetDepthBias` in section 5, with these defaults: constant
2, slope 2. Its middle argument, the clamp, stays 0; any other value needs the
`depthBiasClamp` device feature, and a clamp exists mainly to stop the slope
term exploding at near-grazing angles, which the next fix handles more gently.

This is also the reason section 3 chose a UNORM format, the one that matters
most. In a 16-bit UNORM format, r is one fixed step, the same everywhere
in the image. For a float format the spec defines r from the exponent of each
triangle's own depth values, so the same bias setting is a different distance
at every depth — a slider that cures acne at one distance and detaches shadows
at another.

**Normal offset, at the receiver.** Instead of — or as well as — moving what
the map stores, move the point that asks: look the pixel up from a spot pushed
slightly *off* its surface, along its normal. Pushed by about one shadow texel,
the point is clear of its own texel's stored depth, so it cannot shadow itself.
The offset is measured in **texels of the cascade being sampled** — which is
what `cascadeTexelSize` in `ShadowData` is for — so it is small in the sharp near
cascade and larger in the coarse far one, always the right size. It is scaled by
the sine of the angle between the normal and the sunlight: a surface facing the
sun needs no offset, a grazing one the most.

In `sampleCascade`, the `lightClip` line and its comment become the offset
position and the lookup from it:

```glsl
    // Normal offset (section 7): look the point up from slightly off its surface, by a fixed
    // number of this cascade's texels, most at grazing light, none facing it.
    float cosine         = clamp(dot(worldNormal, -shadowData.sunDirection.xyz), 0.0, 1.0);
    float sine           = sqrt(1.0 - cosine * cosine);
    float offset         = shadowData.normalOffset * shadowData.cascadeTexelSize[cascade] * sine;
    vec3  offsetPosition = worldPosition + worldNormal * offset;

    // Orthographic: w is 1, so clip space is already normalized device coordinates.
    vec4  lightClip = shadowData.cascadeViewProjection[cascade] * vec4(offsetPosition, 1.0);
```

The normal here should be the **geometric** normal — the interpolated vertex
normal — not Chapter 15's normal-mapped one. A normal map's bumps would move
each pixel's lookup by a different amount, and the shadow edge would inherit
their pattern. Section 9 passes the right one.

**Peter-panning: too much of either.** Bias pushes the shadow *away* from its
caster. A little is invisible; a lot detaches the shadow from the object's
base, and the object seems to float — named after the boy whose shadow came
loose. Push **Bias constant** to its maximum and **Normal offset** to 4 to see
the gap open at the foot of every box: a strip of lit ground between the box
and its shadow, widest where the box meets the ground at a slant to the sun.

So the job is the *smallest* bias that removes acne. Normal offset scales with
texel size and the slope bias with slope, so the defaults stay small where
little is needed — which is why this chapter uses both instead of one large
constant. If acne reappears on some surface, raise the slope factor first;
peter-panning that remains on thin geometry (a wall thinner than a texel's
worth of bias) is the price of any shadow map and is reduced only by more
resolution — which is what Part 2's cascades buy.

---

## 8. Hard edges, and filtering them

With bias set, shadows are correct and **hard**: each shadow-map texel is lit or
not, so edges are staircases of texels, magnified wherever a texel covers many
pixels. Real sunlight shadows are a little soft, because the sun is a disc, not
a point — a penumbra a few centimetres wide behind a fence post.

**Percentage-closer filtering** (PCF) softens them where the *depth comparison*
happens, which is the only place it can: compare against several neighbouring
texels and average the *results*. A pixel near an edge, where some neighbours
pass and some fail, gets a fraction. Section 6's comparison sampler already does
this for a 2×2 footprint in hardware; this section's loop does it for a square
of those, `filterRadius` taps either side. In `sampleCascade`, the single
`return texture(...)` line becomes:

```glsl
    // Percentage-closer filtering (section 8): the same comparison at a square of neighbouring
    // texels, averaged. Each tap is itself a 2x2 comparison, filtered by the hardware.
    vec2  texel = 1.0 / vec2(textureSize(shadowMap, 0).xy);
    int   r     = shadowData.filterRadius;
    float lit   = 0.0;
    for (int y = -r; y <= r; ++y)
    {
        for (int x = -r; x <= r; ++x)
        {
            lit += texture(shadowMap, vec4(uv + vec2(x, y) * texel, float(cascade), depth));
        }
    }
    return lit / float((2 * r + 1) * (2 * r + 1));
```

The default radius 1 is nine hardware taps, which together cover a 4 × 4 texel
area with smooth weights. Radius 0 is a single 2×2 tap — already far better than
point sampling, and the cheapest acceptable setting. Each step up costs taps as
the square of the radius, in every shaded pixel, so this is a slider to watch on
the frame-time graph.

The penumbra is a fixed number of *texels* wide, so it is narrow in the near
cascade and wide in the far one — the opposite of a real penumbra, which widens
with distance from the caster. Varying the filter width with that distance is
*percentage-closer soft shadows* (PCSS): a first search for blockers estimates
how far the caster is, then the filter radius follows. It is the natural next
step and is not built here.

Note also what Chapter 18's MSAA will **not** do: it anti-aliases geometric
edges, and a shadow edge is not one — it is a change in shading across a
surface. Only this filtering softens shadow edges.

---

## 9. How shadows reach the shading

**This is `SceneRenderer::RecordShadows`, the mesh shader's change, and the
demo's call.**

### Only the sun, only its direct light

Chapter 16's light loop adds every light's contribution. The shadow map
describes one light — the sun, `lights[lightHeader.sunIndex]` — so only that
light's irradiance is multiplied by `sunShadow`. The other lights stay
unshadowed (section 14), and the **ambient** term must stay untouched: ambient
stands for light arriving from the whole sky, which a sun shadow does not block.
Darkening it too is the classic mistake that makes shadows pitch black.

Three lines join `Mesh.frag.glsl`. The include, beside Chapter 16's:

```glsl
// Shaders/Scene/Mesh.frag.glsl - Chapter 17 adds this include, beside Chapter 16's:
#include "Shadows.glsl"
```

Before the loop, the two inputs `sunShadow` needs. The **geometric** normal is
`worldNormal` as interpolated, normalized and flipped for back faces — not `N`,
which is Chapter 15's normal-mapped one (section 7 says why):

```glsl
    // Mesh.frag.glsl, main(), before Chapter 16's light loop (Chapter 17): the view depth that picks a
    // cascade, and the geometric normal the lookup is offset along.
    float viewDepth       = -(frame.view * vec4(worldPosition, 1.0)).z;
    vec3  geometricNormal = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
```

Inside the loop, between computing the irradiance and using it:

```glsl
        if (int(i) == lightHeader.sunIndex)
        {
            irradiance *= sunShadow(worldPosition, geometricNormal, viewDepth);   // Chapter 17
        }
```
### `RecordShadows`

`ShadowMaps::Record` asks for a callback that draws the casters into a given
cascade; `SceneRenderer`, which owns the meshes and materials a `DrawItem`
indexes, supplies it. The callback's loop is `RecordDraws`' loop from Chapters
11 and 15 with less in it: the caster pipeline instead of a mesh pipeline, set 1
only for cutout materials (their fragment shader reads it), no normal matrix, and
the cascade number in the push constant. Its pipelines bake `CULL_MODE_NONE`
(section 4), so unlike `RecordDraws` it sets no cull mode.

```cpp
// SceneRenderer.h - Chapter 17's additions.
#include "PillowFort/VulkanGraphics/ShadowMaps.h"

public:
    // In Record, after WriteFrameData and WriteLights, before beginScenePass. `casters` should NOT be
    // culled against the camera: something outside the view can still shade what is inside it.
    void RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                       const scene::Camera& camera, const glm::mat4& view, float aspect,
                       std::optional<glm::vec3> sunDirection,       // direction the light travels; nullopt = no sun
                       std::span<const scene::DrawItem> casters,
                       const ShadowSettings& settings,
                       const ShadowCasterCallback& extraCasters = {});
    const ShadowMaps& Shadows() const { return m_shadows; }

private:
    ShadowMaps m_shadows;   // Chapter 17
```

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 17).
void SceneRenderer::RecordShadows(VkCommandBuffer commandBuffer, uint32_t frameIndex,
                                  const scene::Camera& camera, const glm::mat4& view, float aspect,
                                  std::optional<glm::vec3> sunDirection,
                                  std::span<const scene::DrawItem> casters,
                                  const ShadowSettings& settings,
                                  const ShadowCasterCallback& extraCasters)
{
    // Called once per cascade, inside its rendering scope, with set 0 already bound.
    const ShadowCasterCallback drawCasters = [&](VkCommandBuffer cb, uint32_t cascade) {
        VkPipeline     boundPipeline = VK_NULL_HANDLE;
        const GpuMesh* boundMesh     = nullptr;
        for (const scene::DrawItem& item : casters)
        {
            const GpuMaterial&     material = m_gpuMaterials[item.material];
            const VkPipeline       pipeline = m_shadows.CasterPipeline(material.cutout);
            const VkPipelineLayout layout   = m_shadows.CasterLayout(material.cutout);
            if (pipeline != boundPipeline)
            {
                vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
                boundPipeline = pipeline;
            }
            if (material.cutout)   // its fragment shader reads the material: set 1
            {
                vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, layout,
                                        1, 1, &material.set, 0, nullptr);
            }
            const GpuMesh& mesh = m_meshes[item.mesh];
            if (&mesh != boundMesh)
            {
                const VkDeviceSize offset = 0;
                vkCmdBindVertexBuffers(cb, 0, 1, &mesh.vertexBuffer.buffer, &offset);
                vkCmdBindIndexBuffer(cb, mesh.indexBuffer.buffer, 0, VK_INDEX_TYPE_UINT32);
                boundMesh = &mesh;
            }

            const shared::ShadowDrawData push{
                .model    = item.world,
                .cascade  = cascade,
                .padding0 = 0,
                .padding1 = 0,
                .padding2 = 0,
            };
            vkCmdPushConstants(cb, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
            const scene::Submesh& submesh = mesh.submeshes[item.submesh];
            vkCmdDrawIndexed(cb, submesh.indexCount, 1, submesh.firstIndex, 0, 0);
        }
    };
    m_shadows.Record(commandBuffer, frameIndex, m_frameSets[frameIndex], camera, view, aspect,
                     sunDirection, settings, drawCasters, extraCasters);
}
```

The lambda captures by reference: it runs inside `m_shadows.Record`, before
`RecordShadows` returns, so nothing it refers to can go away first. The push
constant goes through the layout of the pipeline just bound; the two caster
layouts have identical push ranges (section 4), and pushing through the bound
one is the rule that never needs that fact.

### The demo's part

`UsdViewerDemo` owns the settings — CPU state, so they survive a re-`Setup` the
way Chapter 14's imported scene does — and a second draw list for the casters:

```cpp
// Demos/UsdViewer/UsdViewerDemo.h, private members (Chapter 17).
vulkan_graphics::ShadowSettings m_shadowSettings;
std::vector<scene::DrawItem>    m_shadowCasters;   // every visible submesh, not culled to the view
```

**Why a second list.** The scene pass draws Chapter 12's list culled to the
camera's frustum. Shadow casters must not be culled that way: a building behind
the camera, between you and the sun, shades the street in front of you.
`CollectDraws(out, nullptr)` gathers every visible submesh, unculled. It is the
simple answer, not the cheap one — section 5 says how to cull per cascade
instead.

The panel goes in `Update`, with the demo's other panels:

```cpp
// UsdViewerDemo::Update (Chapter 17), beside the scene panels.
vulkan_graphics::drawShadowPanel(m_shadowSettings);
```

and the shadow pass in `Record`, after Chapter 16's `WriteLights` — which is what
makes `SunDirection` valid for this frame — and before `beginScenePass`. The
camera, view matrix, and aspect are the ones `Record` just put in `FrameData`
(Chapter 12's locals `camera` and `aspect`, and `frameData.view`):

```cpp
// UsdViewerDemo::Record (Chapter 17): after WriteLights, before beginScenePass.
m_scene.CollectDraws(m_shadowCasters, nullptr);
m_sceneRenderer.RecordShadows(commandBuffer, frame.frameIndex, camera, frameData.view, aspect,
                              m_sceneRenderer.SunDirection(frame.frameIndex), m_shadowCasters,
                              m_shadowSettings);
```

`drawShadowPanel` is the last function in `ShadowMaps.cpp`. A free function, as
Chapter 07's `drawShaderParameters` is: it edits the settings and knows nothing
about Vulkan. Part 1's has a row per setting so far; section 11 adds Part 2's:

```cpp
bool drawShadowPanel(ShadowSettings& settings)
{
    bool changed = false;
    ImGui::SetNextWindowPos(ImVec2(360.0f, 175.0f), ImGuiCond_FirstUseEver);   // right of Frame, below where Chapter 18's MSAA window will sit
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until you open it
    if (ImGui::Begin("Shadows", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        changed |= ImGui::Checkbox("Enabled", &settings.enabled);
        changed |= ImGui::SliderFloat("Distance (m)", &settings.maxDistance, 10.0f, 500.0f);
        changed |= ImGui::SliderFloat("Caster reach (m)", &settings.casterReach, 0.0f, 500.0f);
        changed |= ImGui::SliderFloat("Bias constant", &settings.biasConstant, 0.0f, 16.0f);
        changed |= ImGui::SliderFloat("Bias slope", &settings.biasSlope, 0.0f, 8.0f);
        changed |= ImGui::SliderFloat("Normal offset", &settings.normalOffset, 0.0f, 4.0f);
        changed |= ImGui::SliderInt("Filter radius", &settings.filterRadius, 0, 3);
    }
    ImGui::End();
    return changed;
}
```

The window opens as a title bar, so it does not cover the scene; click the title to open it. ImGui remembers that in `imgui.ini`, and so does every window's position once you drag it.

The Meshes and SceneGraph demos from Chapters 11 and 12 can do the same: they
write one sun with `WriteLights` (Chapter 16), so `SunDirection` already returns
it, and their draw lists are `DrawItem`s. A demo with no `Scene` at all — the
grass — builds its `DrawItem` span itself, or passes an empty one and draws its
own casters through `extraCasters`.

---

## 10. The test scene

Chapter 16's `LightTest.usda` is a 20 m room: too small for cascades to show
anything. `ShadowTest.usda` is outdoors, 400 m across, with something in every
cascade and one object for each artifact:

| Object | Tests | What to see |
| --- | --- | --- |
| `Pillar_*`, 84 boxes out to 150 m | Cascades, splits, seams, fade-out | Shadows near and far; four bands in the debug view; no line where they meet |
| `Ball`, a 2 m sphere | Acne, bias | A clean terminator at the default bias; stripes at zero |
| `Pole_*`, `Wire_*`: 3 cm poles, 2 cm wires | Thin casters, peter-panning | Shadows thinner than a texel, which a shadow map loses: the wires' are faint lines, the poles' hardly show; in Chapter 18, edges that crawl at 1x |
| `LeafFence`, Chapter 15's leaf ×16, facing the camera | Alpha-to-coverage, in Chapter 18 | Soft leaf edges at 4×, staircases at 1× |
| `LeafRoof`, the same leaves lying flat at 3.5 m | Cutout casters | Leaf-shaped shadows on the ground ahead and to the right, not a rectangle |
| `Sun`, a `DistantLight` | The one shadowed light | Light travelling towards (−0.63, −0.57, −0.53): long shadows to the back left |
| `Camera` | A useful start | 3 m up, 30 m back, looking down the rows |

Like Chapter 15's `MaterialSweep.usda`, it is repetitive — 84 pillars that
differ in one number — so a script writes it; Appendix A has it in full, to
copy. Run it once from `Assets/Scenes/` (`python make_shadow_test.py`), after
Chapter 15's `make_test_assets.py`, because the fence uses its
`Textures/Leaf.png`, and commit the `.usda`; the script is not part of the
build. Boxes are `Mesh` prims with no authored normals, so Chapter 14's
importer gives each face its own; their quads run counter-clockwise seen from
outside, as everything here does. Every `Mesh` says `subdivisionScheme =
"none"`: USD's default is Catmull-Clark, and Chapter 14's importer warns about
each mesh that leaves it out.

Load it in the USD viewer (`Assets/Scenes/ShadowTest.usda`). It has no dome
light, so the ambient term is the panel's, as Chapter 16 arranged.

With one map, a texel here is several centimetres wide: the leaf shadows under
`LeafRoof` come out as soft blobs, and shadow edges near the camera are blocky.
Part 2 sharpens both.

If you came here from the box at the end of section 6, go back to section 7
now; the checkpoint below assumes all of Part 1.

## Checkpoint

Run `UsdViewerDemo` with validation on. You can now check:

- [ ] `ShadowTest.usda` shows shadows from the sun, and Chapter 16's
      `LightTest.usda` shows them from its sun only: the other lights add
      light without shadowing, and shadowed areas keep their ambient light
      rather than going black.
- [ ] With every bias control at zero, lit surfaces show acne; at the defaults
      they are clean; with excessive bias, shadows detach from their casters'
      bases. Take a screenshot of each.
- [ ] Cutout leaves cast leaf-shaped shadows, not rectangles.
- [ ] **Synchronization validation is proven on for this barrier.** The scene
      pass reads the shadow map through a descriptor, and the validation layer
      tracks such reads only with `syncval_shader_accesses_heuristic`, which
      Chapter 02's layer settings request. Temporarily change the second
      barrier's destination stage in `ShadowMaps::Record` from
      `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT` to
      `VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT`: the layer must report
      `SYNC-HAZARD-READ-AFTER-WRITE` on the first frame. Put it back. (The
      first barrier has its own control: a source stage of `NONE` reports
      `SYNC-HAZARD-WRITE-AFTER-READ` from the second frame on.)
- [ ] Then: no validation messages while flying, changing every slider, and
      resizing.

---

# Part 2 — Cascaded shadow maps (sections 11-14)

Part 1's one map spends its texels evenly over 120 m of view. Part 2 spends
them where the camera can see them: several maps, each covering one stretch of
depth (section 11), fitted so they hold still as the camera moves (section 12),
chosen per pixel and blended at their seams (section 13).

---

## 11. Cascaded shadow maps

Fly close to something in Part 1's scene. With one 2048-texel map over 120 m
of view, a texel is several centimetres to tens of centimetres wide — fine for
a building at a hundred metres, blocky for the chair next to you. The problem
is **perspective**: near the camera a metre covers hundreds of screen pixels,
far away a few, but one shadow map spends its texels evenly across both.

The fix is several shadow maps, each covering one depth range of the view —
**cascades**. The first covers the few metres in front of the camera at high
density; each next one covers a longer range at lower density; together they
reach `maxDistance`. A pixel uses the cascade its depth falls in.

> **Jump:** the shader now has a decision to make **per pixel**: which of four
> light matrices and which of four layers to use. Until now every pixel of a
> draw did the same thing with the same bindings. Keep in mind that the
> decision is made in *view* space — by the pixel's distance from the camera —
> while the lookup it selects happens in *light* space. Section 13 writes the
> decision; the debug view there shows it, and is the first thing to turn on
> whenever cascades misbehave.

### The settings Part 2 adds

Five settings, all used in this part: how many cascades and where they split
(this section), the stable fit (section 12), and the seam blend and debug view
(section 13). They go at the end of `ShadowSettings`:

```cpp
    // Part 2: cascades.
    int   cascadeCount  = SHADOW_CASCADE_COUNT;   // 1 to 4 (section 11); 1 is Part 1's single map
    float splitLambda   = 0.8f;     // 0 = uniform splits, 1 = logarithmic (section 11)
    bool  stabilize     = true;     // bounding spheres and texel snapping (section 12); off shows the shimmer
    float blendFraction = 0.1f;     // fraction of each cascade blended into the next (section 13)
    bool  showCascades  = false;    // tint by cascade (section 13)
```

and at the end of `drawShadowPanel`'s window, after "Filter radius":

```cpp
        // Part 2: cascades.
        changed |= ImGui::SliderInt("Cascades", &settings.cascadeCount, 1, SHADOW_CASCADE_COUNT);
        changed |= ImGui::SliderFloat("Split lambda", &settings.splitLambda, 0.0f, 1.0f);
        changed |= ImGui::Checkbox("Stabilize", &settings.stabilize);
        changed |= ImGui::SliderFloat("Cascade blend", &settings.blendFraction, 0.0f, 0.5f);
        changed |= ImGui::Checkbox("Show cascades", &settings.showCascades);
```

With `SHADOW_CASCADE_COUNT` layers allocated since section 3, the number in
use is a runtime value, `cascadeCount`, which travels to the shader in
`ShadowData::cascadeCount`. One cascade is Part 1's single map; the
**Cascades** slider switches between them live.

### Where to split

How long should each cascade be? Two classic schemes, for `N` cascades between
the near plane `n` and the far distance `f`:

```text
 uniform:      split_i = n + (f - n) · i / N         equal lengths: the near cascade wastes texels on
                                                     the distance, the far ones are fine
 logarithmic:  split_i = n · (f / n)^(i / N)         each cascade a fixed multiple of the last: texel
                                                     density follows perspective exactly
```

Why logarithmic is the right shape: something twice as far away looks half as
big, so every doubling of distance deserves the same number of texels. A split
where each cascade is a fixed multiple of the last gives exactly that.

Logarithmic is the theoretically right one, and in practice too aggressive: with
a 0.1 m near plane and 120 m, its first cascade ends at 0.6 m, wasting a whole
map on the camera's nose. The **practical split scheme** (from Zhang et al.'s
parallel-split shadow maps) blends the two with a weight λ:

```text
 split_i = λ · logarithmic_i + (1 - λ) · uniform_i
```

λ = 0.8 is the default: at 0.1 m to 120 m the four cascades end at about 6.5,
15, 34, and 120 m. The **Split lambda** slider moves them live — watch the
debug view while dragging it.

```cpp
// File scope, above the namespace block. Section 11: where each cascade ends, as a view depth in
// metres, for `count` cascades covering [nearPlane, farDistance]. lambda blends a logarithmic split
// (each cascade the same multiple of the last, as perspective needs) with a uniform one.
static std::array<float, SHADOW_CASCADE_COUNT> cascadeSplits(uint32_t count, float nearPlane,
                                                             float farDistance, float lambda)
{
    std::array<float, SHADOW_CASCADE_COUNT> splits{};
    for (uint32_t i = 0; i < count; ++i)
    {
        const float fraction    = static_cast<float>(i + 1) / static_cast<float>(count);
        const float logarithmic = nearPlane * std::pow(farDistance / nearPlane, fraction);
        const float uniform     = nearPlane + (farDistance - nearPlane) * fraction;
        splits[i] = lambda * logarithmic + (1.0f - lambda) * uniform;
    }
    return splits;
}
```

**`FitCascades` grows.** Part 1's version fitted one slice; this one computes
the splits and fits a light box per slice `[split_{i-1}, split_i]` — which is
all a cascade is: section 2's fit, applied to a shorter slice. The last split
is always exactly `farDistance`. It replaces Part 1's function:

```cpp
void ShadowMaps::FitCascades(const scene::Camera& camera, const glm::mat4& view, float aspect,
                             const glm::vec3& sunDirection, const ShadowSettings& settings)
{
    const uint32_t  count         = static_cast<uint32_t>(std::clamp(settings.cascadeCount, 1, SHADOW_CASCADE_COUNT));
    const glm::mat4 cameraToWorld = glm::inverse(view);
    const float     tanHalfFovY   = std::tan(camera.verticalFov * 0.5f);
    const float     farDistance   = std::min(settings.maxDistance, camera.farPlane);
    const std::array<float, SHADOW_CASCADE_COUNT> splits =
        cascadeSplits(count, camera.nearPlane, farDistance, settings.splitLambda);

    for (uint32_t i = 0; i < count; ++i)
    {
        const float      sliceNear = (i == 0) ? camera.nearPlane : splits[i - 1];
        const CascadeFit fit       = fitTight(cameraToWorld, tanHalfFovY, aspect, sliceNear, splits[i],
                                              sunDirection, m_resolution, settings.casterReach);
        m_data.cascadeViewProjection[i] = fit.viewProjection;
        m_data.cascadeSplits[i]         = splits[i];
        m_data.cascadeTexelSize[i]      = fit.texelSize;
    }
    m_data.cascadeCount = count;
    m_data.sunDirection = glm::vec4(sunDirection, 0.0f);
    m_data.maxDistance  = farDistance;
}
```

### One image array, not an atlas

The four maps are the four layers of section 3's image array: the layer is one
more coordinate to `sampler2DArrayShadow`, each layer has its own
clamp-to-border edge, and each is rendered through its own single-layer view.
The other standard choice, an **atlas** — one large image with a cascade in each
quadrant — pays off only when many lights of different sizes share one budget
(section 14).

---

## 12. Shimmering, and holding the shadow still

Turn **Stabilize** off and fly, or just rotate in place. Every shadow edge
crawls and flickers — *shimmering* — even though nothing in the scene moved.

**Why.** `fitTight` refits the light's box to the view every frame. When the
camera moves, the box moves with it by some fraction of a texel; when the camera
turns, the box changes *size*, because a frustum slice viewed from the sun has a
different footprint at every orientation. Either way the grid of shadow-map
texels slides across the world, and a staircase edge drawn on that grid is
redrawn with its steps in different places every frame. The numbers, from
flying a camera 200 frames through a slice 14-34 m out: with the tight fit the
texel size varies between 2.8 and 3.3 cm, and a fixed point on the ground lands
anywhere within its texel — up to half a texel from where it started.

Stabilizing takes away both kinds of motion:

1. **Fix the size.** Fit a **sphere** around the slice instead of a box. A
   sphere looks the same from every direction, and the smallest sphere around a
   frustum slice depends only on the slice's shape — field of view, aspect,
   near and far — never on the camera's orientation. Its square in the shadow
   map, `2r` wide, is the same every frame, so the texel size is constant.
2. **Fix the grid.** Move the light camera only in **whole texels**. Find where
   the world origin lands in shadow-map texels, round that to a whole number,
   and shift the projection by the difference. Every world point then sits at
   the same place inside its texel, frame after frame, and an edge's staircase
   stays where it is in the world.

Seen from the side, with the camera off to the left, the slice and its sphere
look like this:

```text
                 ___________
            .-‾‾‾           ‾‾‾-.
         .‾                  ____● far corner
       /             ____---‾      \
      |  near ●--‾‾‾‾               |
   ───┼───────────────────── ✕ ─────┼───  the view axis
      |  near ●--____               |
       \             ‾‾‾‾---____   /
         ‾.                      ‾● far corner
            ‾-.___________.-‾
   the smallest circle around the slice's corners is the sphere; its centre ✕ is on the axis
```

*Optional, the algebra behind the code:* the smallest sphere's centre lies on
the view axis. For a slice between depths `n` and `f`, a corner at depth `d` is
`d·k` from the axis, where `k² = tan²(fovX/2) + tan²(fovY/2)`; the centre at
depth `z` is equally far from the near and far corners when

```text
 (f - z)² + f²k²  =  (z - n)² + n²k²      ⇒      z = (n + f)(1 + k²) / 2
```

and if that lands beyond `f` — wide fields of view and short slices — the
sphere centred on the far plane is the smallest.

```cpp
// File scope. Section 12: the same slice inside a sphere, whose size never changes as the camera
// turns, with the light camera moved in whole texels so the shadow map's grid stays put in the world.
static CascadeFit fitStable(const glm::mat4& cameraToWorld, float tanHalfFovY, float aspect,
                            float sliceNear, float sliceFar, const glm::vec3& sunDirection,
                            uint32_t resolution, float casterReach)
{
    // The smallest sphere around the slice. Its centre is on the view axis, at the depth equally
    // far from the near corners and the far ones; k2 is a corner's squared distance from the axis
    // per unit of depth. Past the far plane it would leave the slice, so it stops there.
    const float tanHalfFovX = tanHalfFovY * aspect;
    const float k2     = tanHalfFovX * tanHalfFovX + tanHalfFovY * tanHalfFovY;
    const float centre = std::min(0.5f * (sliceNear + sliceFar) * (1.0f + k2), sliceFar);
    const float farSq  = (sliceFar - centre) * (sliceFar - centre) + sliceFar * sliceFar * k2;
    const float nearSq = (centre - sliceNear) * (centre - sliceNear) + sliceNear * sliceNear * k2;
    const float radius = std::sqrt(std::max(farSq, nearSq));
    const glm::vec3 centreWorld = glm::vec3(cameraToWorld * glm::vec4(0.0f, 0.0f, -centre, 1.0f));

    // A square exactly the sphere's width; depth from the sun side of the sphere, plus the reach.
    const glm::mat4 lightView = glm::lookAt(centreWorld - sunDirection * (radius + casterReach),
                                            centreWorld, lightUp(sunDirection));
    glm::mat4 projection = glm::ortho(-radius, radius, -radius, radius, 0.0f, 2.0f * radius + casterReach);
    projection[1][1] *= -1.0f;

    // Snap. Find where the world origin lands, in texels, and shift the projection by the fraction
    // that puts it exactly on a texel corner. Every world point then sits at the same place inside
    // its texel, frame after frame.
    const float     texelsPerUnit = static_cast<float>(resolution) * 0.5f;   // NDC is 2 units wide
    const glm::vec4 origin        = projection * lightView * glm::vec4(0.0f, 0.0f, 0.0f, 1.0f);
    const glm::vec2 originTexels  = glm::vec2(origin) * texelsPerUnit;
    const glm::vec2 snap          = (glm::round(originTexels) - originTexels) / texelsPerUnit;
    projection[3][0] += snap.x;
    projection[3][1] += snap.y;

    return { projection * lightView, 2.0f * radius / static_cast<float>(resolution) };
}
```

**`FitCascades` chooses.** In its loop, the `fitTight` call becomes a choice
between the two fits, so **Stabilize** can switch them live:

```cpp
        const CascadeFit fit       = settings.stabilize
            ? fitStable(cameraToWorld, tanHalfFovY, aspect, sliceNear, splits[i], sunDirection,
                        m_resolution, settings.casterReach)
            : fitTight(cameraToWorld, tanHalfFovY, aspect, sliceNear, splits[i], sunDirection,
                       m_resolution, settings.casterReach);
```

Why snapping the *origin* is enough: the light's view is a rotation (fixed while
the sun does not move) plus a translation, and the orthographic projection only
scales and shifts. So every world point's texel coordinate is the origin's plus
a fixed, frame-independent offset. Put the origin on a texel corner and every
point keeps its sub-texel position. `projection[3][0]` and `[3][1]` are the
projection's x and y translation (GLM is column-major: column 3 is the
translation column), and a shift there moves the image without rotating or
scaling it.

The same 200-frame flight with `fitStable`: the texel size is 3.91 cm on every
frame, and the fixed point's position inside its texel moves by one ten-thousandth
of a texel — floating-point noise.

**The price** is resolution. A sphere around a long thin slice wastes the
corners of its square, so texels are about 20-40% larger than the tight fit's
(3.9 cm against 2.8-3.3 cm above). That is the standard trade, and almost every
shipped engine takes it: a slightly softer shadow that holds still is far less
visible than a sharper one that crawls. It is also why `fitTight` stays: switch
**Stabilize** off to see the shimmer, and back on to see it go.

Two motions stabilization cannot remove. When the **sun** moves, the light's
rotation changes and the grid turns with it; a slow time-of-day sun shimmers a
little, and engines update it in small steps for that reason. And the **depth**
range moves with the sphere, so stored depths change frame to frame — harmless,
because both the shadow pass and the lookup use the same frame's matrix.

---

## 13. Choosing a cascade per pixel, and hiding the seams

**This is the rest of `Shadows.glsl`**, and its two callers' last lines. A pixel
knows its view depth — the distance in front of the camera,
`-(view × position).z` — and the splits are view depths, so choosing a cascade
is a walk along them. `selectCascade` goes above `sunShadow`:

```glsl
// Which cascade a view depth falls in (section 13), and how far it is into the band at that
// cascade's far end where it fades into the next one: 0 before the band, 1 at the split.
int selectCascade(float viewDepth, out float blend)
{
    int last    = int(shadowData.cascadeCount) - 1;
    int cascade = 0;
    while (cascade < last && viewDepth > shadowData.cascadeSplits[cascade]) { ++cascade; }

    float near  = (cascade == 0) ? 0.0 : shadowData.cascadeSplits[cascade - 1];
    float far   = shadowData.cascadeSplits[cascade];
    float start = far - (far - near) * shadowData.blendFraction;
    blend = clamp((viewDepth - start) / max(far - start, 1e-4), 0.0, 1.0);
    return cascade;
}
```

Selecting by depth is the simple choice, and the one the debug view can show as
clean bands.

**Seams.** Where one cascade hands over to the next, texel size jumps — by about
2.5× with the default splits — and a soft shadow edge suddenly gets blockier
along a line across the ground. The fix is to blend: in the last
`blendFraction` (10%) of each cascade's range, sample *both* cascades and mix by
how far into the band the pixel is. The seam becomes a gradient a few metres
long. It costs a second lookup in those bands only. (A cheaper alternative
dithers: pick one cascade or the other per pixel with a noise threshold. That
needs temporal anti-aliasing to smooth the noise, which is Chapter 18's "next
step", not built here.)

The last cascade blends into *no shadow*, so shadows fade out at `maxDistance`
instead of stopping at a line.

In `sunShadow`, Part 1's last line — `return sampleCascade(worldPosition,
worldNormal, 0);` — becomes the choice and the blend:

```glsl
    float blend;
    int   cascade = selectCascade(viewDepth, blend);
    float lit     = sampleCascade(worldPosition, worldNormal, cascade);

    // Across a seam, fade into the next cascade. Past the last one, fade to lit, so shadows end
    // gradually at maxDistance instead of at a line.
    if (blend > 0.0)
    {
        float next = (cascade + 1 < int(shadowData.cascadeCount))
                   ? sampleCascade(worldPosition, worldNormal, cascade + 1)
                   : 1.0;
        lit = mix(lit, next, blend);
    }
    return lit;
```

`ShadowMaps::Record` hands the shader the blend and the debug view's flag. Its
`flags` line becomes two, with the blend before them:

```cpp
    m_data.blendFraction = settings.blendFraction;
    m_data.flags         = (active ? SHADOW_FLAG_ENABLED : 0u)
                         | (active && settings.showCascades ? SHADOW_FLAG_SHOW_CASCADES : 0u);
```

**The debug view.** **Show cascades** tints everything by the cascade it reads —
red, green, blue, yellow from near to far — with the same blend bands. The
tint is one more function, after `sunShadow`, before the `#endif`:

```glsl
// White, unless the debug view is on: then a tint per cascade - red, green, blue, yellow -
// mixed across the same blend bands sunShadow uses. Multiply the final color by it.
vec3 cascadeDebugColor(float viewDepth)
{
    if ((shadowData.flags & SHADOW_FLAG_SHOW_CASCADES) == 0u || viewDepth >= shadowData.maxDistance)
    {
        return vec3(1.0);
    }
    const vec3 tints[SHADOW_CASCADE_COUNT] = vec3[](vec3(1.0, 0.25, 0.25), vec3(0.25, 1.0, 0.25),
                                                    vec3(0.3, 0.45, 1.0),  vec3(1.0, 1.0, 0.25));
    float blend;
    int   cascade = selectCascade(viewDepth, blend);
    vec3  next    = (cascade + 1 < int(shadowData.cascadeCount)) ? tints[cascade + 1] : vec3(1.0);
    return mix(tints[cascade], next, blend);
}
```

and the mesh fragment shader multiplies by it after Chapter 16's light loop,
before Chapter 15's debug views and clamp:

```glsl
    color *= cascadeDebugColor(viewDepth);   // Chapter 17: white unless "Show cascades" is on
```

What to look for: four bands; each band about as long as the split scheme says
(drag **Split lambda** and watch them move); soft transitions where the blending
happens; no tint past `maxDistance`. A band that jumps when the camera turns
means the splits are being computed from something that changes with
orientation — they must depend on view *depth* only.

`textureSize`, the loop bound `filterRadius`, and `cascadeCount` come from a
uniform buffer and the image, so the compiler cannot unroll or specialize on
them. That is deliberate — they are live sliders. A shipping renderer would make
the filter radius a specialization constant and the cascade count fixed.

---

## 14. Other lights: further work

Only the sun casts shadows here. The other UsdLux lights need the same
technique in different shapes, each a project of its own:

- **Spot lights** (Chapter 16's sphere lights with shaping): one *perspective*
  shadow map per light, along its cone. The closest relative of this chapter.
- **Point lights:** light leaves in every direction, so one map is not enough —
  a **cube map** of six 90° perspective views, sampled by direction with
  `samplerCubeShadow`. Six passes per light, or one with multiview or layered
  rendering.
- **Rect and disk lights:** area lights cast genuinely soft shadows whose
  penumbra depends on the light's size; PCSS (section 8) approximates them, ray
  tracing (Chapter 33) gets them right.
- **Many lights:** an **atlas** sized by importance (section 11's other choice),
  shadows only for the nearest few, and caching for lights and casters that do
  not move.

A renderer that shadows several lights would also give `LightData` a
shadow-map index, so the shader knows which map belongs to which light.

---

## Exit check

Run `UsdViewerDemo` on `ShadowTest.usda` with validation on. Part 1's checkpoint
still holds; Part 2 adds:

- [ ] **Show cascades** shows four bands with soft blends; **Split lambda**
      moves them; with the tint off, no seam is visible across the ground.
- [ ] Flying and turning the camera, shadow edges hold still. With
      **Stabilize** off they crawl; on again, they stop.
- [ ] **Cascades** at 1 shows Part 1's blocky near shadows; at 4 they are sharp
      near the camera — the leaf shadows under `LeafRoof` turn from soft blobs
      into crisp leaves — and still present at `maxDistance`, where they fade
      out instead of ending at a line.
- [ ] No validation messages while flying, changing every slider, and
      resizing.

Next: [18 — Anti-Aliasing](18-Anti-Aliasing.md)

---

## Sources

- L. Williams, "Casting Curved Shadows on Curved Surfaces", SIGGRAPH 1978: the
  shadow map.
- W. T. Reeves, D. H. Salesin, and R. L. Cook, "Rendering Antialiased Shadows
  with Depth Maps", SIGGRAPH 1987: percentage-closer filtering (section 8).
- F. Zhang, H. Sun, L. Xu, and L. K. Lun, "Parallel-Split Shadow Maps for
  Large-scale Virtual Environments", VRCIA 2006: the practical split scheme
  (section 11).
- R. Fernando, "Percentage-Closer Soft Shadows", SIGGRAPH 2005 sketch: PCSS
  (section 8).
- Microsoft, "Common Techniques to Improve Shadow Depth Maps", DirectX
  documentation: slope-scaled bias, and cascades stabilized by bounding spheres
  and texel snapping (sections 7 and 12).
- The Khronos Group, *Vulkan Specification*, "Depth Bias": the bias formula of
  section 7, and why r differs between UNORM and floating-point formats.

---

## Appendix A — `make_shadow_test.py`

Reference, to copy: writes section 10's `ShadowTest.usda`.

```python
# Assets/Scenes/make_shadow_test.py
# Writes ShadowTest.usda: Chapter 17's shadow scene, which Chapter 18 reuses for anti-aliasing.
# Run once, from Assets/Scenes/, after Chapter 15's make_test_assets.py (it uses Textures/Leaf.png):
#     python make_shadow_test.py
# Plain Python 3, standard library only. Not part of the build: what it writes is committed.

prims = []

def material(name, color, roughness, extra=""):
    return f"""
        def Material "{name}"
        {{
            token outputs:surface.connect = </ShadowTest/Materials/{name}/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {color}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}"""

# A unit cube centred on the origin, as a Mesh: 8 corners, 6 counter-clockwise quads. No normals are
# authored, so the importer gives each face its own (Chapter 14).
CUBE_POINTS = "[(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)]"
CUBE_INDICES = "[0, 1, 2, 3, 5, 4, 7, 6, 4, 0, 3, 7, 1, 5, 6, 2, 3, 2, 6, 7, 4, 5, 1, 0]"

def box(name, centre, size, materialName, rotateZ=0.0):
    ops = '"xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"'
    prims.append(f"""
    def Mesh "{name}" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = {CUBE_INDICES}
        point3f[] points = {CUBE_POINTS}
        double3 xformOp:translate = {centre}
        float3 xformOp:rotateXYZ = (0, 0, {rotateZ})
        float3 xformOp:scale = {size}
        uniform token[] xformOpOrder = [{ops}]
        rel material:binding = </ShadowTest/Materials/{materialName}>
    }}""")

# The ground: 400 m square, so the last cascade (120 m) has something to fall on.
prims.append("""
    def Mesh "Ground" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-200, 0, 200), (200, 0, 200), (200, 0, -200), (-200, 0, -200)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        rel material:binding = </ShadowTest/Materials/Ground>
    }""")

# Pillars from the camera out to about 150 m: every cascade gets shadows to show.
for row in range(12):
    for column in range(-3, 4):
        height = 1 + (column * 7 + row * 13) % 5
        box(f"Pillar_{row}_{column + 3}", (column * 9.0, height / 2.0, -row * 13.0),
            (2, height, 2), "Clay")

# Thin geometry near the camera: poles 3 cm wide and wires 2 cm thick, slightly tilted so their
# edges cross pixel rows - Chapter 18's aliasing test, and thin casters for this chapter's bias.
for i in range(12):
    box(f"Pole_{i}", (-6 + i * 1.1, 2.5, 12), (0.03, 5, 0.03), "White")
for i in range(6):
    box(f"Wire_{i}", (0, 1 + i * 0.7, 12), (14, 0.02, 0.02), "White", rotateZ=4.0)

# A sphere: a curved shadow terminator, where bias and acne are easiest to judge.
prims.append("""
    def Sphere "Ball" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        double radius = 2
        double3 xformOp:translate = (8, 2, 6)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </ShadowTest/Materials/White>
    }""")

# A leaf fence: Chapter 15's leaf texture repeated 4 x 4 on a double-sided quad, facing the camera.
# In Chapter 18 its edges are the alpha-to-coverage test. Its shadow falls behind it.
prims.append("""
    def Mesh "LeafFence" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform bool doubleSided = 1
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-12, 0, 8), (-6, 0, 8), (-6, 4, 8), (-12, 4, 8)]
        texCoord2f[] primvars:st = [(0, 0), (4, 0), (4, 4), (0, 4)] (
            interpolation = "vertex"
        )
        rel material:binding = </ShadowTest/Materials/LeafRepeat>
    }""")

# A leaf roof: the same leaves, flat at 3.5 m, so that their shadows land on open ground in front of
# the starting camera. They must be leaves, not a rectangle.
prims.append("""
    def Mesh "LeafRoof" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform bool doubleSided = 1
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(2, 3.5, 20), (8, 3.5, 20), (8, 3.5, 14), (2, 3.5, 14)]
        texCoord2f[] primvars:st = [(0, 0), (4, 0), (4, 4), (0, 4)] (
            interpolation = "vertex"
        )
        rel material:binding = </ShadowTest/Materials/LeafRepeat>
    }""")

LEAF = """
        def Material "LeafRepeat"
        {
            token outputs:surface.connect = </ShadowTest/Materials/LeafRepeat/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </ShadowTest/Materials/LeafRepeat/Image.outputs:rgb>
                float inputs:opacity.connect = </ShadowTest/Materials/LeafRepeat/Image.outputs:a>
                float inputs:opacityThreshold = 0.5
                token outputs:surface
            }

            def Shader "Image"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/Leaf.png@
                token inputs:sourceColorSpace = "sRGB"
                token inputs:wrapS = "repeat"
                token inputs:wrapT = "repeat"
                float2 inputs:st.connect = </ShadowTest/Materials/LeafRepeat/TexCoord.outputs:result>
                float3 outputs:rgb
                float outputs:a
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }"""

# The sun, low enough for long shadows: light travels towards (-0.63, -0.57, -0.53).
prims.append("""
    def DistantLight "Sun"
    {
        float inputs:intensity = 3
        bool inputs:normalize = 1
        float3 xformOp:rotateXYZ = (-35, 50, 0)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }""")

# Where to start: 3 m up, 30 m back, looking a little down the rows. 20 mm on a 23 mm-tall gate
# is a 60 degree vertical field of view.
prims.append("""
    def Camera "Camera"
    {
        float focalLength = 20
        float verticalAperture = 23
        float2 clippingRange = (0.1, 1000)
        double3 xformOp:translate = (0, 3, 30)
        float3 xformOp:rotateXYZ = (-8, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }""")

with open("ShadowTest.usda", "w") as f:
    f.write('#usda 1.0\n(\n    defaultPrim = "ShadowTest"\n    metersPerUnit = 1\n    upAxis = "Y"\n)\n\n')
    f.write('def Xform "ShadowTest"\n{\n    def Scope "Materials"\n    {')
    f.write(material("Ground", "(0.45, 0.45, 0.45)", 0.9))
    f.write(material("Clay", "(0.7, 0.45, 0.3)", 0.7))
    f.write(material("White", "(0.85, 0.85, 0.85)", 0.5))
    f.write(LEAF)
    f.write("\n    }\n")
    f.write("".join(prims))
    f.write("\n}\n")
```
