# 23 — The Sky

**Goal:** every 3D demo can show a sky behind its scene, picked in one engine
setting: off, a daylight sky computed from the demo's own sun, or an HDR
environment image — a USD dome light's when the file has one, otherwise a
built-in test image whose labelled axes prove that every direction lands where
it should. The sky lives in a cube map that a compute pass fills only when
something changes, and one full-screen triangle draws it after the opaque scene,
touching only the pixels nothing else covered: at any MSAA sample count, and on
both of Chapter 22's paths.

**ROADMAP:** step 21+. Engine code, not a demo: a `Sky` class in
`VulkanGraphics` that Cubes, Meshes, the scene graph, the USD viewer, and the
particles each own one of. The grass picks it up in Chapter 25.

**Module:**

- `Source/PillowFort/VulkanGraphics/`, `pf::vulkan_graphics` — `Sky.h/.cpp` and
  `SkySettings.h/.cpp` (new); `VulkanRenderer` keeps the settings and hands
  them to the demo.
- `Source/PillowFort/Demos/Demo.h` — `RecordContext` gains the settings.
- `Source/PillowFort/Scene/`, `pf::scene` — `EnvironmentImage`, which `Scene`
  keeps for dome lights; `UsdImport.cpp` reads it from the file.
- Shaders: `Shaders/Sky/SkyBake.comp.glsl`, `Sky.vert.glsl`, `Sky.frag.glsl`;
  `Shaders/Include/SkyTypes.h` and `Shaders/Include/CubeMap.glsl`.
- A test scene: `Assets/Scenes/make_sky_test.py` writes `SkyTest.usda` and
  `Textures/SkyDirections.hdr` (Appendix A).

**Math:** taught here — why a sky depends on direction alone, and turning a
pixel back into a direction with an inverse matrix (section 1); how a cube map
turns a direction into a face and a texel (section 2); a direction's latitude
and longitude, both ways (section 4); laying a flat label onto a sphere
(section 5); the radiance a disk of sky needs to deliver a given irradiance
(section 6). Assumed: vectors, the dot product as a cosine (Chapter 11
section 14), and `sin`, `cos`, `asin`, `atan2`.

**Prerequisites:**

- Chapter 04 section 5 — the three questions a barrier answers, and that a
  barrier orders everything submitted before it on the queue, last frame's
  commands included.
- Chapter 08 sections 4 (the scene target is linear HDR; the composite pass
  encodes), 5 (push constants), and 6 (descriptor sets).
- Chapter 10 sections 1 (`w = 0` directions and `w = 1` points), 2 (the
  projection and the divide by `w`), 4 (the inverse of a matrix), and 8 (the
  depth buffer: cleared to 1.0, tested with `LESS`).
- Chapter 12 section 5 — a matrix's columns are its axes.
- Chapter 15 section 5 — `fwidth`.
- Chapter 16 sections 2 (solid angle, `E = L Ω`, a distant light's irradiance,
  a dome's luminance as the ambient light), 3 (the dome's image and
  `domeTextureAverage`), and 6 (exposure and the tone curve).
- Chapter 18 sections 2 and 6 — what MSAA resolves, and that every pipeline in
  the scene pass declares its sample count.
- Chapter 20 sections 2 to 5 and 10 — compute pipelines, dispatch sizes,
  storage images, and barriers between compute and graphics.
- For section 10 only: Chapter 21 section 5 (a second rendering scope after the
  scene pass) and Chapter 22 sections 6 and 10 (what `RecordLighting` leaves,
  and what stays forward).

---

## Where this is going

Until now a demo cleared its scene target to one color, and wherever nothing
was drawn, that color showed. This chapter puts a sky there. Pick **Sun sky**
in the new "Sky" section of the "Tone mapping" window, and the Meshes demo sits
under a blue sky that pales toward a bright horizon band, with a glow and a
small, very bright disk where its sun is; lower the sun and the glow turns
orange and the sky darkens. Pick **Environment**, and the sky is an image: on
`SkyTest.usda` the dome light's, everywhere else a test pattern with a colored,
labelled disc at each of the six axes — **+X** red, **+Y** green, **+Z** blue,
and their opposites in cyan, magenta, and yellow.

Each demo's frame gains two calls:

```text
 the demo's Record
   ... compute, shadows ...
   Sky::Update        compute, outside any rendering scope: fill the cube again,  sections 4-7
                      but only if the mode, the sun, or the image changed
   beginScenePass
     opaque draws
     Sky::Draw        one triangle at depth 1.0, tested LESS_OR_EQUAL:           section 7
                      it lands only where the depth buffer is still clear
   endScenePass
   ... blended things, hand back ...
```

### The class map

**This is `Source/PillowFort/VulkanGraphics/Sky.h`**, whole. A demo owns a
`Sky` exactly as it owns a `SceneRenderer`: `Initialize` in `Setup`,
`Shutdown` in `Teardown`, and per frame an `Update` before the scene pass and a
`Draw` inside it. Each private function names the section that writes it.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  The sky: a cube of radiance, filled by compute and drawn behind a scene (Chapter 23)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/Sky.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/Scene/Light.h"
#include "PillowFort/VulkanGraphics/SceneTargets.h"
#include "PillowFort/VulkanGraphics/SkySettings.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "SkyTypes.h"   // SkyBakeParameters, SKY_FACE_SIZE

#include <glm/glm.hpp>
#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

namespace pf::vulkan_graphics {

// What a demo tells its sky each frame. Most demos fill in only the sun.
struct SkyInputs
{
    glm::vec3 sunDirection{ 0.0f, -1.0f, 0.0f };   // the way sunlight travels (Chapter 16), world, unit
    glm::vec3 sunIrradiance{ 0.0f };               // a Distant LightItem's emission; zero: no sun, no daylight
    glm::mat3 worldToEnvironment{ 1.0f };          // Environment: world direction -> the image's own frame
    glm::vec3 environmentRadiance{ 1.0f };         // Environment: multiplies the image
};

// The sky behind a 3D scene. A demo owns one, as it owns a SceneRenderer: Initialize in Setup, Shutdown
// in Teardown, Update before the scene pass and Draw inside it.
class Sky
{
public:
    // The cube, its view and samplers, the bake and draw pipelines, and the built-in test environment
    // (section 5). The draw pipeline is built for `formats`, so it fits the scene pass at any sample count.
    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                    const SceneFormats& formats);
    void Shutdown();   // device idle first; safe after a partial Initialize

    // Section 4. Optional, after Initialize: the image Environment mode shows, replacing the test image.
    InitializationResult SetEnvironment(const scene::EnvironmentImage& image);

    // In Record, before the scene pass. Fills the cube again only when the settings or the inputs changed,
    // and leaves it ready to be sampled by fragment and compute shaders (section 7).
    void Update(VkCommandBuffer commandBuffer, const SkySettings& settings, const SkyInputs& inputs);

    // Inside the scene pass, after the opaque draws: the sky wherever nothing was drawn (section 7).
    // Nothing at all when the sky is off.
    void Draw(VkCommandBuffer commandBuffer, const glm::mat4& view, const glm::mat4& projection) const;

    // Section 10: Draw in a rendering scope of its own, for a demo whose scene pass is already over -
    // Chapter 22's deferred path, after its lighting pass. One sample only. Leaves the scene color and
    // depth as endScenePass does.
    void DrawInOwnPass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                       const glm::mat4& view, const glm::mat4& projection) const;

    // For a later chapter's shader that samples the sky, such as water reflecting it. From Initialize on
    // the cube is in SHADER_READ_ONLY_OPTIMAL (section 3); once the sky is on and Update has run, it holds
    // world-space radiance, exposure included, without the sun's disk (section 7).
    VkImageView CubeView() const    { return m_cubeView; }      // VK_IMAGE_VIEW_TYPE_CUBE
    VkSampler   CubeSampler() const { return m_cubeSampler; }

private:
    InitializationResult CreateCube();                  // section 3
    InitializationResult CreateDescriptors();           // section 3
    InitializationResult CreatePipelines();             // sections 3 and 7
    void                 DestroyEnvironment();
    void                 WriteEnvironmentDescriptor();  // the bake set's binding 1

    VulkanContext   m_context;                          // copies of borrowed handles
    VkPipelineCache m_pipelineCache = VK_NULL_HANDLE;   // borrowed
    SceneFormats    m_formats;

    // Section 3: the cube.
    VkImage       m_cube           = VK_NULL_HANDLE;
    VmaAllocation m_cubeAllocation = VK_NULL_HANDLE;
    VkImageView   m_cubeView       = VK_NULL_HANDLE;   // CUBE: the bake writes it, the draw samples it
    VkSampler     m_cubeSampler    = VK_NULL_HANDLE;

    // Section 4: the lat-long image Environment mode reads.
    VkImage       m_environment           = VK_NULL_HANDLE;
    VmaAllocation m_environmentAllocation = VK_NULL_HANDLE;
    VkImageView   m_environmentView       = VK_NULL_HANDLE;
    VkSampler     m_environmentSampler    = VK_NULL_HANDLE;   // repeats across the seam, clamps at the poles

    VkDescriptorSetLayout m_bakeSetLayout = VK_NULL_HANDLE;   // binding 0 the cube to write, 1 the environment
    VkDescriptorSetLayout m_drawSetLayout = VK_NULL_HANDLE;   // binding 0 the cube
    VkDescriptorPool      m_pool          = VK_NULL_HANDLE;   // frees both sets with it
    VkDescriptorSet       m_bakeSet       = VK_NULL_HANDLE;
    VkDescriptorSet       m_drawSet       = VK_NULL_HANDLE;
    VkPipelineLayout      m_bakeLayout    = VK_NULL_HANDLE;
    VkPipeline            m_bakePipeline  = VK_NULL_HANDLE;
    VkPipelineLayout      m_drawLayout    = VK_NULL_HANDLE;
    VkPipeline            m_drawPipeline  = VK_NULL_HANDLE;

    // What the cube holds now, so Update can tell whether anything changed (section 7).
    shared::SkyBakeParameters m_baked{};
    bool                      m_cubeValid = false;   // false until the first bake, and after SetEnvironment
    SkyMode                   m_mode      = SkyMode::Off;
    shared::SkyDrawParameters m_draw{};              // the sun's disk, for Draw
};

} // namespace pf::vulkan_graphics
```

`SkyInputs` is what changes from demo to demo: where the sun is and how strong,
and — for the USD viewer — how its dome light is turned and how bright it is.
Everything about *which* sky to show comes from the engine instead, in
`SkySettings` (section 8).

The files, and what each section adds:

```text
Shaders/Include/CubeMap.glsl            a cube face's texel, and a lat-long texel, as a direction   sections 2, 4
Shaders/Include/SkyTypes.h              the draw's and the bake's push constants                     sections 1, 3
Shaders/Sky/SkyBake.comp.glsl           fills the cube: from an image, or from the sun               sections 4, 6
Shaders/Sky/Sky.vert.glsl, Sky.frag.glsl  the sky behind everything, and the sun's disk               sections 1, 6, 7
VulkanGraphics/Sky.h/.cpp               the class above                                              sections 1, 3-7, 10
VulkanGraphics/SkySettings.h/.cpp       Off / Sun sky / Environment, and the panel                   section 8
VulkanGraphics/VulkanRenderer.h/.cpp, Demos/Demo.h, SandboxGame/Main.cpp   the setting's route   section 8
Demos/Cubes, Meshes, SceneGraph, Particles   one Sky each                                             sections 1, 8, 9
Scene/Light.h, Scene/Scene.h/.cpp, UsdImport/UsdImport.cpp   a dome light's image, kept              section 10
Demos/UsdViewer                         the dome's image, and the deferred path                      section 10
Assets/Scenes/make_sky_test.py          SkyTest.usda and Textures/SkyDirections.hdr                  Appendix A
```

> **Jump:** every image so far was looked up by a position on it — a texture
> coordinate, or a pixel. A sky is looked up by a **direction**, and the whole
> chapter is about turning one into the other: a pixel into the direction it
> looks along (section 1), a direction into a face and a texel of a cube
> (section 2), and a direction into a place on a flat image of the whole sky
> (section 4). Keep that in mind and the rest is plumbing you have built
> before: a compute pass that writes an image, a barrier, and a pipeline.

---

# Part 1 — A sky behind the cubes (sections 1-8)

Part 1 builds the class and shows it in the Cubes demo. Part 2 puts it in every
other 3D demo, reads a USD dome light's image, and covers the deferred path.

## 1. What a sky is: light that arrives from a direction

**This is the idea behind the whole chapter, and `Sky.vert.glsl`.**

Stand in a field and walk ten metres. The tree beside you moves across your
view; the clouds do not. A mountain 10 km away shifts by atan(10 / 10000), about
0.06° — less than one pixel of a 1280-pixel-wide view that spans 100°. The sky
is farther still. For drawing, it is **infinitely far away**: what you see
of it depends on the *direction* you look in, never on where you stand.

In Chapter 16's words, the sky is radiance arriving at the camera from each
direction. A function of direction alone — no position — is the whole
definition, and it has two consequences:

- **The camera's position does not matter, only its rotation.** Chapter 10
  section 1 met the same fact for directions written with `w = 0`: a matrix's
  translation does not touch them. For the sky, we take the view matrix and
  keep only its rotation. `glm::mat3(view)` is its upper-left 3 × 3, the
  rotation; `glm::mat4` of that puts back a zero translation.
- **Every pixel needs the direction it looks along.** A pixel is a point on the
  screen, and Chapter 10 section 2's projection is how a point in the world
  became that pixel. Run it backwards — Chapter 10 section 4's inverse — and the
  pixel becomes a point in the world again, on the ray from the camera through
  it. With the translation removed, the camera sits at the origin, so that point
  *is* the direction, once it is divided by its `w` and made unit length.

Which point on the ray? Any: every depth along the ray lands on the same pixel.
This chapter un-projects at depth 0, the near plane, because the near plane is
always at a sensible distance; a far plane can be a million metres away (USD's
default clipping range), where the arithmetic in 32-bit floats falls apart.

**A worked example.** A square view with a 90° vertical field: Chapter 10
section 2's projection then has `[0][0] = 1` and `[1][1] = −1` (the minus is
Vulkan's Y-down flip). Take the top-right corner of the screen, clip-space
`(x, y) = (1, −1)` — top is −1 in Vulkan. On the near plane, at distance `n`,
the clip-space `w` is that distance, so before the divide the corner is
`(n, −n, 0, n)`. Undoing the projection divides `x` by `[0][0] = 1` and `y` by
`[1][1] = −1`: the view-space point `(n, n, −n)`, and the direction
`(1, 1, −1) / √3`. That is 45° to the right and 45°
up from straight ahead, which is exactly where a 90° view's corner should point.
Rotate it by the camera's rotation and you have the world direction.

So the sky needs one matrix, `clipToWorld = inverse(projection × rotation)`,
and `Sky::Draw` builds it every frame from the demo's view and projection
(section 7). The vertex shader draws Chapter 08's full-screen triangle and
un-projects its three corners:

```glsl
// Shaders/Sky/Sky.vert.glsl - Chapter 23: Chapter 08's full-screen triangle, pushed to the far plane, with
// each corner's view direction for the fragment shader.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "SkyTypes.h"   // SkyDrawParameters

layout(push_constant) uniform DrawBlock
{
    SkyDrawParameters draw;
};

layout(location = 0) out vec3 viewDirection;   // world space, not unit length: the fragment shader normalizes

void main()
{
    // vertexIndex 0 -> (-1,-1), 1 -> (3,-1), 2 -> (-1,3): one triangle that covers the screen.
    vec2 uv   = vec2((gl_VertexIndex << 1) & 2, gl_VertexIndex & 2);
    vec2 clip = uv * 2.0 - 1.0;

    // Section 1: un-project the corner. Every depth along its ray lands on the same pixel; depth 0, the
    // near plane, keeps the numbers well-behaved however far away the far plane is.
    vec4 point    = draw.clipToWorld * vec4(clip, 0.0, 1.0);
    viewDirection = point.xyz / point.w;   // the camera sits at the origin of this space

    // z = w = 1: depth 1.0, exactly what the depth buffer was cleared to. LESS_OR_EQUAL passes only
    // where nothing nearer was drawn (section 7).
    gl_Position = vec4(clip, 1.0, 1.0);
}
```

The direction is computed at three corners and the rasterizer blends it across
the triangle. That gives the right direction at every pixel, because the
un-projected points all lie on one plane — the near plane — and points on a
plane slide across the screen at a steady rate. The blend shortens the vector,
so the fragment shader makes it unit length again. `gl_Position`'s
`z = w = 1` puts the triangle at depth 1.0; the next subsection says why.

### A first sky, before there is a cube

The rest of the chapter fills a cube to look each direction up in. Before any
of that, the direction itself can go on screen, as a color: `0.5 + 0.5 d`,
which turns each component's −1 to 1 into 0 to 1, so every direction has a
color of its own. (Section 5's test environment uses the same colors as its
background.) It checks the vertex shader and the trick that puts the sky
behind the scene, and it needs only four pieces of the class, written as they
will stay, plus a fragment shader that section 6 replaces.

**The push constants.** The matrix reaches the vertex shader as a push
constant (Chapter 08 section 5). The struct is declared once for C++ and GLSL,
like `SharedShaderTypes.h` (Chapter 08 section 8), in a header of its own,
`Shaders/Include/SkyTypes.h`. Its two sun fields are section 6's; until then
they are zero.

```c
/* Shaders/Include/SkyTypes.h - Chapter 23: the sky's push constants, in both languages. GLSL and C++
   both include it as "SkyTypes.h": Shaders/Include is on both include paths. */
#ifndef PF_SKY_TYPES_H
#define PF_SKY_TYPES_H

#include "SharedShaderTypes.h"   /* vec4, mat3, mat4, uint */

#ifdef __cplusplus
    namespace pf::shared {
#endif

/* The draw's push constants (std430). */
struct SkyDrawParameters
{
    mat4 clipToWorld;            /*  0  inverse(projection * view-without-translation) */
    vec4 toSun;                  /* 64  xyz: toward the sun; w: cos of the disk's angular radius, 2 = no disk */
    vec4 sunRadiance;            /* 80  rgb: the disk's radiance, exposure included; w unused */
};                               /* 96 */

#ifdef __cplusplus
    static_assert(sizeof(SkyDrawParameters) == 96, "SkyDrawParameters layout drifted.");
    }
#endif

#endif
```

**The first fragment shader**, `Shaders/Sky/Sky.frag.glsl`:

```glsl
// Shaders/Sky/Sky.frag.glsl - section 1's first version: the view direction as a color. Section 6
// replaces it with the cube and the sun.
#version 450

layout(location = 0) in  vec3 viewDirection;
layout(location = 0) out vec4 outColor;

void main()
{
    outColor = vec4(0.5 + 0.5 * normalize(viewDirection), 1.0);   // each axis its own color
}
```

**The class.** `Sky.h` starts as the part of the class map these four
functions use: its includes except `Light.h` and `SkySettings.h`, whose types
sections 8 and 10 add; `Initialize`, `Shutdown`, `Draw`, and the private
`CreatePipelines`; and the members `m_context`, `m_pipelineCache`, `m_formats`,
`m_drawLayout`, and `m_drawPipeline`. The rest of the class map goes in as the
sections reach it. **This is `Initialize`, as it starts**, in `Sky.cpp`, which
includes `Sky.h` and, for `createGraphicsPipeline`, `GraphicsPipeline.h`
(Appendix B lists every include the finished file has):

```cpp
InitializationResult Sky::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                     const SceneFormats& formats)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;
    return CreatePipelines();   // for now, the draw pipeline alone
}
```

**This is `CreatePipelines`, as it starts**: the draw's layout, with no
descriptor set yet, and its pipeline.

```cpp
InitializationResult Sky::CreatePipelines()
{
    // For now, the draw alone: no descriptor set yet, and SkyDrawParameters as push constants. The vertex
    // shader reads the matrix; from section 6 the fragment shader reads the sun.
    const VkPushConstantRange drawRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(shared::SkyDrawParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &drawRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_drawLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sky's draw.");
    }

    // Section 7: tested against the depth the scene drew, never written; LESS_OR_EQUAL, because the sky
    // sits exactly at the depth buffer's clear value, 1.0. The scene pass's formats and sample count.
    const GraphicsPipelineDesc desc{
        .vertexShader   = "Sky/Sky.vert.spv",
        .fragmentShader = "Sky/Sky.frag.spv",
        .colorFormats   = { &m_formats.color, 1 },
        .depthFormat    = m_formats.depth,
        .depthTest      = true,
        .depthWrite     = false,
        .depthCompare   = VK_COMPARE_OP_LESS_OR_EQUAL,
        .layout         = m_drawLayout,
        .samples        = m_formats.samples,
    };
    m_drawPipeline = createGraphicsPipeline(m_context.device, m_pipelineCache, desc);
    if (m_drawPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sky's draw pipeline failed.");
    }
    return InitializationResult::success();
}
```

The trick is in the depth settings. The depth buffer is cleared to 1.0 at the
start of the scene pass (Chapter 10 section 9), and every surface drawn writes
its own depth, smaller than 1.0. The sky's triangle sits at depth exactly 1.0.
Tested with `LESS_OR_EQUAL`, it passes where the depth is still 1.0 — where
nothing was drawn — and fails everywhere else. It writes no depth: it is
farther than everything by definition, so there is nothing to record, and
anything drawn after it, such as Chapter 21's particles, still tests against
the scene's own depth. Section 7 says why it is drawn last, and what MSAA
changes.

**This is `Draw`, as it starts.** It builds the matrix this section derived —
the projection times the view without its translation, inverted — and draws
the full-screen triangle:

```cpp
void Sky::Draw(VkCommandBuffer commandBuffer, const glm::mat4& view, const glm::mat4& projection) const
{
    // Section 1: only which way the camera faces matters, so the view loses its translation -
    // mat3(view) keeps the rotation, and mat4 of that puts back a zero translation.
    shared::SkyDrawParameters draw{};
    draw.clipToWorld = glm::inverse(projection * glm::mat4(glm::mat3(view)));

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawPipeline);
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(draw), &draw);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);   // the full-screen triangle
}
```

**`Shutdown`** destroys what `Initialize` made, in reverse, and returns at once
if `Initialize` never ran (Chapter 09 section 2: a `Setup` that failed early
is still torn down). It grows with the class; Appendix B has it whole. For
now:

```cpp
void Sky::Shutdown()
{
    if (m_context.device == VK_NULL_HANDLE) { return; }   // Initialize never ran
    vkDestroyPipeline(m_context.device, m_drawPipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_drawLayout, nullptr);
    m_drawPipeline = VK_NULL_HANDLE;
    m_drawLayout   = VK_NULL_HANDLE;
    m_context      = {};
}
```

**The Cubes demo's part.** Part 1 uses Cubes because it has no lights and no
second path to get in the way; the other demos, the USD viewer, and Chapter
22's deferred path come in Part 2. A demo owns a `Sky` the way it owns a
`SceneRenderer`: a member, built in `Setup` for the demo's own formats, shut
down in `Teardown`, and drawn in `Record`. `CubesDemo.h` gains
`#include "PillowFort/VulkanGraphics/Sky.h"` and the member:

```cpp
    vulkan_graphics::Sky           m_sky;                           // Chapter 23
```

In `Setup`, after the cube pipelines, before the final `return`:

```cpp
    if (auto result = m_sky.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats); !result)
    {
        return result;   // Chapter 23
    }
```

`Initialize` builds the draw pipeline for `m_context.formats`, so after an MSAA
change — which runs `Teardown` and `Setup` again (Chapter 18 section 7) — the
sky matches the new sample count, like the cubes' pipelines. `Draw` goes after
the last cube, before `endScenePass`:

```cpp
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);   // Chapter 23: after everything opaque
```

And `Teardown` begins with:

```cpp
    m_sky.Shutdown();   // Chapter 23
```

### Checkpoint: the direction as a color

Rerun `GenerateProjects.bat` — `Sky.cpp`, two shaders, and `SkyTypes.h` are
new — build, and open **Cubes**. Where the dark clear color was, the
background is now the direction each pixel looks along, as a color: pale green
straight up (+Y), magenta straight down (−Y), pink-red toward +X, teal toward
−X, lavender-blue toward +Z, and olive-yellow toward −Z. The starting camera
looks down toward −Z from the +X side, so the top of the view is green, the
bottom magenta, the left edge blue, and the right edge orange.

- **Orbit the camera**: the colors stay with the world's directions, not with
  the screen, and the cubes always stand in front of them.
- **Untick the Cubes panel's Depth test**: the sky paints over every cube.
  With the test off, the cubes write no depth, the depth buffer stays at 1.0
  everywhere, and the sky passes everywhere. The sky depends on the scene
  writing its depth.

From here the class grows a piece at a time: the cube (section 3), what fills
it (sections 4-6), and the final `Draw` and the bake that keeps it current
(section 7). The next build is Part 1's checkpoint, after section 8.

---

## 2. Cube maps: six faces, one direction

**This is `Shaders/Include/CubeMap.glsl`'s face table.**

A sky has to be stored somehow, and looked up by direction. A **cube map** is
six square images on the faces of a cube centred on the camera. A direction
leaves the centre, hits one face, and the texel there is the answer. The GPU
does the lookup itself: sample a cube with a direction and it picks the face and
the texel. You only need to know how it does so when *you* write the faces.

**Picking the face.** The face is the direction's **largest component**:
`(0.2, 0.5, −0.8)` is mostly −Z, so it hits the −Z face. Dividing the other two
components by that largest one says where on the face: −1 at one edge, +1 at
the other.

**Where on the face.** Each face has a direction its columns run in (its
*right*) and a direction its rows run in (its *down*). Vulkan fixes them, face
by face, in this order of the image's six layers:

| Layer | Face | Centre | Right (column grows) | Down (row grows) |
| --- | --- | --- | --- | --- |
| 0 | +X | (1, 0, 0) | −Z | −Y |
| 1 | −X | (−1, 0, 0) | +Z | −Y |
| 2 | +Y | (0, 1, 0) | +X | +Z |
| 3 | −Y | (0, −1, 0) | +X | −Z |
| 4 | +Z | (0, 0, 1) | +X | −Y |
| 5 | −Z | (0, 0, −1) | −X | −Y |

Worked: `(0.2, 0.5, −0.8)` on the −Z face. Its right is −X and its down is −Y,
so across the face it is `−0.2 / 0.8 = −0.25` and down it is
`−0.5 / 0.8 = −0.625`. From −1..1 to 0..1: 0.375 across and 0.19 down — upper
left of the middle, as you would expect for a direction a little to the right of
−Z and well above it, seen from behind the −Z face.

That last phrase is the trap. Unfold the cube flat, each face as its image is
stored:

```text
                  +-------+
                  |  +Y   |  right +X, down +Z
                  |   2   |
          +-------+-------+-------+-------+
          |  -X   |  +Z   |  +X   |  -Z   |   each of these four:
          |   1   |   4   |   0   |   5   |   down -Y
          +-------+-------+-------+-------+   right: -X face +Z, +Z face +X,
                  |  -Y   |                          +X face -Z, -Z face -X
                  |   3   |  right +X, down -Z
                  +-------+
```

Every face is stored as you would see it **from outside the cube**, printed on
its surface. Stand outside the +Z face looking back at it, head up: your right
is +X, as the table says. But the camera is *inside*. Looking out through the
+Z face, your right is −X — so to the camera, every face is a mirror image.
(The convention is RenderMan's, older than the right-handed worlds that use it
now.) Nothing goes wrong while the GPU both writes and reads the cube by
direction. It goes wrong when you fill a face by hand: render it with an ordinary
camera, or load six images made for another convention, and that face comes out
mirrored. Section 5 shows what one mirrored face looks like.

The bake never makes that mistake, because it never thinks in terms of a camera:
it takes the table as data and runs it backwards. For a point `(u, v)` on face
`f`, with `u` across and `v` down, from 0 to 1, the direction is the face's
centre plus `u` and `v`, stretched to −1..1, along its right and down:

```glsl
// Shaders/Include/CubeMap.glsl - Chapter 23: where a cube face's texel, or a lat-long image's texel,
// points. Any shader that writes or reads the sky's cube by direction includes it.
#ifndef PF_CUBE_MAP_GLSL
#define PF_CUBE_MAP_GLSL

// Vulkan's cube faces, in layer order +X, -X, +Y, -Y, +Z, -Z (section 2's table). For each face: the
// direction through its centre, and the directions its columns (right) and rows (down) run in.
const vec3 CUBE_FACE_CENTRE[6] = vec3[](vec3( 1, 0, 0), vec3(-1, 0, 0), vec3(0, 1, 0),
                                        vec3( 0,-1, 0), vec3( 0, 0, 1), vec3(0, 0,-1));
const vec3 CUBE_FACE_RIGHT[6]  = vec3[](vec3( 0, 0,-1), vec3( 0, 0, 1), vec3(1, 0, 0),
                                        vec3( 1, 0, 0), vec3( 1, 0, 0), vec3(-1, 0, 0));
const vec3 CUBE_FACE_DOWN[6]   = vec3[](vec3( 0,-1, 0), vec3( 0,-1, 0), vec3(0, 0, 1),
                                        vec3( 0, 0,-1), vec3( 0,-1, 0), vec3(0,-1, 0));

// The unit world direction through point uv of a face: uv runs 0 to 1, x to the right, y down the rows.
vec3 cubeTexelDirection(uint face, vec2 uv)
{
    vec2 p = 2.0 * uv - 1.0;   // -1 to 1 across the face
    return normalize(CUBE_FACE_CENTRE[face] + p.x * CUBE_FACE_RIGHT[face] + p.y * CUBE_FACE_DOWN[face]);
}
```

Check it against the worked example: face 5, `p = (−0.25, −0.625)`, gives
`(0, 0, −1) − 0.25 (−1, 0, 0) − 0.625 (0, −1, 0) = (0.25, 0.625, −1)`,
which is `(0.2, 0.5, −0.8)` scaled by 1.25. Normalizing removes the scale.

---

## 3. The cube on the GPU

**This is `Sky::Initialize`, finished, and `Sky::CreateCube`.**

`Initialize` takes the shape of every class so far: copy the borrowed handles,
then one function per group of objects, each returning on failure. Section 1's
`return CreatePipelines();` becomes the cube, its descriptors, the pipelines,
and section 5's test image:

```cpp
InitializationResult Sky::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                     const SceneFormats& formats)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_formats       = formats;

    if (auto result = CreateCube(); !result)        { return result; }   // section 3
    if (auto result = CreateDescriptors(); !result) { return result; }   // section 3
    if (auto result = CreatePipelines(); !result)   { return result; }   // sections 3 and 7

    // Section 5: until a demo supplies an image of its own, Environment mode shows the test image.
    return SetEnvironment(makeTestEnvironment(1024, 512));
}
```

**The cube** is one image with six layers. Three choices make it a sky:

- **`VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT`** permits a cube view of it. Without
  the flag, six layers are only an array.
- **`R16G16B16A16_SFLOAT`**, the scene target's format: a sky is HDR radiance
  like any light, in the scene's linear units (Chapter 16).
- **512 × 512 per face.** A face covers 90°, so that is about 5.7 texels per
  degree. A 1280 × 720 view with a 60° field shows 12 pixels per degree, so each
  texel is stretched over about two pixels. A smooth sky does not mind; a
  detailed photograph would want 1024. It is 12 MB.

`STORAGE` usage lets the bake write it, `SAMPLED` lets the draw read it. One
**cube view** serves both: sampled, it is GLSL's `samplerCube`, which takes a
direction; as a storage image it is an `imageCube`, written one texel at a time
with the face as the third coordinate.

```cpp
InitializationResult Sky::CreateCube()
{
    // Six square layers, and permission to view them as a cube. STORAGE: the bake writes it.
    // SAMPLED: the draw, and later chapters, read it by direction.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .flags         = VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,   // HDR, like the scene target
        .extent        = { SKY_FACE_SIZE, SKY_FACE_SIZE, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 6,                               // one per face, in Vulkan's order
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &m_cube, &m_cubeAllocation, nullptr) !=
        VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the sky's cube.");
    }

    // A CUBE view of all six layers. Sampled, it is a samplerCube: the sampler picks the face from the
    // direction. As a storage image it is an imageCube, written texel by texel with the face as the
    // third coordinate - the same view serves the bake and the draw.
    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_cube,
        .viewType         = VK_IMAGE_VIEW_TYPE_CUBE,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 6 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_cubeView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the sky's cube.");
    }
```

The rest of `CreateCube` (Appendix B) first puts the cube into
`SHADER_READ_ONLY_OPTIMAL` with one `immediateSubmit`, before anything is baked
into it. Validation checks the layout of every image a pipeline's descriptor
sets name, even one the shader reads only on a branch it never takes, so a later
chapter whose set names the cube while the sky is off — Chapter 30's water, for
one — must find it in the layout its descriptor promises. Until the first bake
its contents mean nothing, and a reader samples it only while the sky is on.
Then `CreateCube` makes two samplers, both linear. The
cube's address mode hardly matters, because Vulkan always filters a cube's faces
across their edges ("seamless"); the second is for section 4's image.

The two descriptor sets and the two pipelines are Chapters 08 and 20 again:
the bake's set has binding 0, the cube as a storage image, and binding 1, the
environment image; the draw's set has binding 0, the cube as a sampled image.
Both descriptors that point at the cube name the layout it will be in when the
shader runs — `GENERAL` for the bake, `SHADER_READ_ONLY_OPTIMAL` for the draw —
and section 7's barriers keep that promise. `CreateDescriptors` is in
Appendix B. `CreatePipelines` grows from section 1's: the bake's layout and
pipeline come first, and the draw's layout now names the draw's set; Appendix B
has it whole.

**The bake's push constants.** Everything the bake needs fits in 112 bytes, so
it goes in push constants too, in `SkyTypes.h` before section 1's draw struct,
with the face size and the mode numbers (the whole header is in Appendix B):

```c
/* The bake's push constants (std430). Everything that decides what the cube holds. */
struct SkyBakeParameters
{
    mat3  worldToEnvironment;    /*   0  world direction -> the environment image's own frame */
    vec4  environmentRadiance;   /*  48  rgb: multiplies the image (a dome light's color x intensity) */
    vec4  toSun;                 /*  64  xyz: unit direction from the scene TOWARD the sun; w unused */
    vec4  sunIrradiance;         /*  80  rgb: what the sun delivers, in the scene's light units */
    uint  mode;                  /*  96  SKY_MODE_* */
    float exposure;              /* 100  2^stops, from the Sky panel */
    uint  padding0;              /* 104 */
    uint  padding1;              /* 108 */
};                               /* 112 */
```

`worldToEnvironment` is a `mat3`: in a block, GLSL stores a `mat3`'s three
columns 16 bytes apart, which is `glm::mat3x4`'s layout — the `shared::mat3`
alias Chapter 11 set up for exactly this.

---

## 4. From an environment image

**This is `SetEnvironment`, `latLongUv`, and the bake's first half.**

Photographers capture whole skies as **HDR environment images**, and a USD
`DomeLight`'s `inputs:texture:file` is one (Chapter 16 section 3 averaged it).
They are almost always stored **latitude-longitude** ("lat-long", or
equirectangular): the sphere of directions unrolled like a world map, twice as
wide as it is tall. Columns are longitude, the angle around the vertical; rows
are latitude, the angle above or below the horizon.

**The convention.** UsdLux follows OpenEXR's, and so does this engine:

```text
   u = 0          0.25           0.5           0.75          1
   +-------------+-------------+-------------+-------------+    v = 0     straight up (+Y)
   |             |             |             |             |
   |    -Z       |     +X      |     +Z      |     -X      |    v = 0.5   the horizon
   |             |             |             |             |
   +-------------+-------------+-------------+-------------+    v = 1     straight down (-Y)
  longitude +180°    +90°            0°          -90°        -180°
```

**Longitude** is 0 toward +Z and +90° toward +X; it falls from +180° at the
left edge to −180° at the right, which is the same direction, so the image wraps
around left to right. **Latitude** is +90° at the top row and −90° at the bottom,
and does not wrap. From a unit direction `d`:

$$ \text{longitude} = \operatorname{atan2}(d_x, d_z), \qquad \text{latitude} = \arcsin(d_y) $$

$$ u = \tfrac{1}{2} - \frac{\text{longitude}}{2\pi}, \qquad v = \tfrac{1}{2} - \frac{\text{latitude}}{\pi} $$

**Worked example.** `d = (1, 1, 0) / √2`, up and toward +X. Longitude is
`atan2(0.707, 0) = 90°`, so `u = 0.5 − 0.25 = 0.25`, the +X column. Latitude
is `asin(0.707) = 45°`, so `v = 0.5 − 0.25 = 0.25`, halfway from the horizon to
the top. In a 2048 × 1024 image, that is pixel (512, 256).

Backwards — the direction through a point `(u, v)` — undo each step: the
longitude and latitude from `u` and `v`, then the point on the unit sphere at
those two angles, which is plain trigonometry:

$$ d = (\cos(\text{lat}) \sin(\text{lon}),\ \sin(\text{lat}),\ \cos(\text{lat}) \cos(\text{lon})) $$

The bake needs the first direction, from a direction to the image; section 5's
test image needs the second. The first is GLSL, beside the face table:

```glsl
// Where a unit direction lands in a lat-long image (section 4): OpenEXR's convention, which UsdLux's
// DomeLight uses. u is 0.5 toward +Z and 0.25 toward +X; v is 0 straight up and 1 straight down.
vec2 latLongUv(vec3 direction)
{
    float longitude = atan(direction.x, direction.z);              // 0 toward +Z, +pi/2 toward +X
    float latitude  = asin(clamp(direction.y, -1.0, 1.0));         // +pi/2 straight up
    return vec2(0.5 - longitude / 6.28318530718, 0.5 - latitude / 3.14159265359);
}
```

and the second is C++, at the top of `Sky.cpp`:

```cpp
// File scope, above the namespace block. Section 4's mapping run backwards: the unit direction through
// point (u, v) of a lat-long image. The bake shader's latLongUv is its inverse.
static glm::vec3 latLongDirection(float u, float v)
{
    const float longitude = (0.5f - u) * glm::two_pi<float>();   // +pi at the left edge, 0 in the middle
    const float latitude  = (0.5f - v) * glm::pi<float>();       // +pi/2 at the top
    return { std::cos(latitude) * std::sin(longitude), std::sin(latitude), std::cos(latitude) * std::cos(longitude) };
}
```

**The image on the GPU.** `SetEnvironment` takes an `EnvironmentImage` —
linear RGBA floats, rows top to bottom, the way TinyUSDZ decodes an `.hdr` file
(section 10) — and uploads it as a `R16G16B16A16_SFLOAT` image. Half floats are
enough for a sky, take half the memory, and every GPU can filter them linearly,
which 32-bit float images do not promise. Their largest value is 65504; a
photographed sun can be brighter than that, and anything past the largest half
float would become infinity, so the conversion clamps:

```cpp
// File scope, above the namespace block. Section 4: 32-bit floats to the 16-bit ones the image stores.
// Anything brighter than the largest half float (65504) would become infinity; it is clamped instead.
static std::vector<uint16_t> toHalfFloats(const std::vector<float>& values)
{
    std::vector<uint16_t> halves(values.size());
    for (size_t i = 0; i < values.size(); ++i)
    {
        halves[i] = glm::packHalf1x16(std::clamp(values[i], 0.0f, 65504.0f));
    }
    return halves;
}
```

The upload is Chapter 08's `uploadToImage` and one more barrier. Its own last
barrier made the copy visible to *fragment* shaders, where every image so far
was read; the bake reads this one in a *compute* shader. The second barrier
works although it is submitted separately, because a barrier's "before" is
everything submitted before it on the queue (Chapter 04 section 5):

```cpp
    const std::vector<uint16_t> halves = toHalfFloats(image.pixels);
    uploadToImage(m_context, m_environment, { image.width, image.height }, halves.data(),
                  halves.size() * sizeof(uint16_t));

    // Chapter 08's uploadToImage made the copy visible to FRAGMENT shaders. The bake samples this image
    // in a COMPUTE shader, which that barrier does not cover. A second barrier, submitted later on the
    // same queue, still waits for the copy: a barrier covers everything submitted before it.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_environment,
                        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });

    WriteEnvironmentDescriptor();
    m_cubeValid = false;   // whatever else Update sees, the next one bakes
    return InitializationResult::success();
```

The rest of `SetEnvironment` creates the image and its view, and is in
Appendix B. It is called only from a demo's `Setup`, when no frame in flight can
still be reading the old image.

**Sampling it.** The environment sampler is `CreateCube`'s second: it
**repeats** across `u`, so a lookup at the seam blends the right edge with the
left, and **clamps** in `v`, because the top row and the bottom row are
opposite poles and must not blend.

**The bake, first half.** One invocation per texel of the cube: the dispatch
covers a 512 × 512 face in 8 × 8 workgroups, and its `z` is the face, so one
dispatch fills all six. Each invocation turns its texel into a direction with
section 2's table, asks for that direction's radiance, and stores it:

```glsl
void main()
{
    ivec3 texel = ivec3(gl_GlobalInvocationID);   // x and y across one face; z which face
    if (texel.x >= SKY_FACE_SIZE || texel.y >= SKY_FACE_SIZE) { return; }

    vec2 uv        = (vec2(texel.xy) + 0.5) / float(SKY_FACE_SIZE);   // the texel's centre, 0 to 1
    vec3 direction = cubeTexelDirection(uint(texel.z), uv);
    vec3 radiance  = bake.mode == SKY_MODE_ENVIRONMENT ? environmentSky(direction) : sunSky(direction);
    // Half float holds 65504 at most; past it is infinity. The upload clamped the image, but the dome's
    // brightness and the exposure (up to 2^10) multiply in after that, so the result is clamped again.
    imageStore(cube, texel, vec4(min(radiance * bake.exposure, vec3(65504.0)), 1.0));
}
```

For Environment mode, "that direction's radiance" is a lookup in the image.
The direction is turned into the image's own frame first — a dome light can be
rotated, and section 10 supplies its rotation — then section 4's mapping gives
the point, and the dome's brightness scales it. `textureLod` names the mip level
outright, because a compute shader has no neighbouring pixels to work one out
from (Chapter 15 section 5):

```glsl
// Section 4: the environment image, turned into the world by the dome's rotation.
vec3 environmentSky(vec3 direction)
{
    vec2 uv = latLongUv(bake.worldToEnvironment * direction);
    return textureLod(environment, uv, 0.0).rgb * bake.environmentRadiance.rgb;   // compute has no implicit LOD
}
```

---

## 5. A test environment you can read

**This is the test image: `testEnvironmentRadiance`, and `Initialize`'s last
line.**

A sky that is wrong in orientation still looks like a sky. Mirror it, turn it,
swap two faces, and a blue gradient is still a blue gradient. So before trusting
any of this, the chapter makes an environment that cannot hide a mistake:

- **The background is the direction itself, as a color:** `0.5 + 0.5 d`.
  Looking toward +X you see `(1, 0.5, 0.5)`, a pink-red; toward −Z
  `(0.5, 0.5, 0)`, an olive yellow; straight up `(0.5, 1, 0.5)`, a pale green.
  Every direction has its own color, so any mapping that sends a direction to
  the wrong place shows the wrong color there.
- **Each axis has a disc**, reaching 25° from the axis, in its own color — +X red, +Y green,
  +Z blue, −X cyan, −Y magenta, −Z yellow — with its name written on a dark
  plate: **+X**, **−Z**, and so on. Text is the best mirror detector there is:
  a mirrored "+Z" reads "Z+", with the Z backwards.
- **A line every 30°** of latitude and longitude, the horizon darker.

**Writing a flat label onto a sphere.** The label is a flat grid of cells, and
the sky is a sphere. To place one on the other, imagine a flat sheet touching
the unit sphere at the axis, like a sticker on a ball. A direction `d` near the
axis `a` passes through the sheet at some point; that point's coordinates on
the sheet, along the label's right `r` and up `w`, are

$$ x = \frac{d \cdot r}{d \cdot a}, \qquad y = \frac{d \cdot w}{d \cdot a} $$

— how far the direction leans right and up, divided by how far it goes forward.
(Dividing by the forward amount is what a camera's projection does too, which is
why the label looks flat in any view.) Worked: looking along +X, with the
label's up +Y and its right `r = a × w = +Z`, the direction `(1, 0.035, 0)`
gives `x = 0`, `y = 0.035`, one cell above the centre: the label's cells are
0.035 wide, about 2°.

The six labels' "up" is +Y around the horizon. For the two poles there is no
horizon to stand on; the code uses the up a camera has after tilting to them
from facing −Z, so they read upright when you look up or down from the start.

The six axes are a table of `TestAxis` — where it points, the label's up, the
disc's color, and its two glyphs — and the glyphs are bitmaps, five cells by
seven. Both are in Appendix B. The function:

```cpp
// File scope, above the namespace block. Section 5: the test environment's radiance in one direction.
// The background is the direction itself as a color, 0.5 + 0.5 d; around each axis, a disc in the axis's
// color with its name on a dark plate; and a line every 30 degrees of latitude and longitude.
static glm::vec3 testEnvironmentRadiance(const glm::vec3& direction)
{
    for (const TestAxis& axis : TEST_AXES)
    {
        const float facing = glm::dot(direction, axis.axis);   // cos of the angle to the axis
        if (facing < std::cos(glm::radians(25.0f))) { continue; }

        // Where the direction meets the plane that touches the unit sphere at the axis: x to the
        // label's right, y up it. This is how a flat label is laid onto the sphere.
        const glm::vec3 right = glm::cross(axis.axis, axis.up);
        const float     x     = glm::dot(direction, right) / facing;
        const float     y     = glm::dot(direction, axis.up) / facing;

        // The label: two glyphs and a one-cell gap, 11 x 7 cells, on a plate one cell larger all round.
        const float cell   = 0.035f;                              // one glyph cell, in plane units
        const int   column = static_cast<int>(std::floor(x / cell + 5.5f));
        const int   row    = static_cast<int>(std::floor(-y / cell + 3.5f));   // rows count downward
        if (column < -1 || column > 11 || row < -1 || row > 7) { return axis.color; }   // the disc
        if (column < 0 || column > 10 || row < 0 || row > 6 || column == 5) { return glm::vec3(0.02f); }

        const int glyph = column < 5 ? axis.sign : axis.letter;
        const int bit   = 4 - (column < 5 ? column : column - 6);
        const bool lit  = (TEST_GLYPHS[glyph][row] >> bit) & 1u;
        return lit ? glm::vec3(1.0f) : glm::vec3(0.02f);
    }

    glm::vec3 radiance = 0.5f + 0.5f * direction;

    // The grid: latitude and longitude in degrees, darkened within a quarter degree of each 30.
    const float latitude  = glm::degrees(std::asin(std::clamp(direction.y, -1.0f, 1.0f)));
    const float longitude = glm::degrees(std::atan2(direction.x, direction.z));
    const float toLatitudeLine  = std::abs(latitude - 30.0f * std::round(latitude / 30.0f));
    const float toLongitudeLine = std::abs(longitude - 30.0f * std::round(longitude / 30.0f));
    if (toLatitudeLine < 0.25f || toLongitudeLine * std::cos(glm::radians(latitude)) < 0.25f)
    {
        radiance *= latitude > -0.5f && latitude < 0.5f ? 0.2f : 0.6f;   // the horizon darker than the rest
    }
    return radiance;
}
```

`makeTestEnvironment` (Appendix B) runs it over a 1024 × 512 lat-long image,
with `latLongDirection` giving each texel's direction. The test image is generated as a
lat-long *image*, not straight into the cube, on purpose: then it reaches the cube
by the same road a dome light's file does, through section 4's mapping, and the
test proves that road. `Initialize` ends by setting it (section 3's listing,
its last line), so Environment mode always has something to show.

**What you should see**, in Environment mode, turning to face each axis:
a disc in its color with its label reading normally, never backwards — **+X**
red, **−X** cyan, **+Y** green overhead, **−Y** magenta underfoot, **+Z** blue,
**−Z** yellow — and between them the background color drifting toward the color
of the nearer disc. Looking along +X, with the camera upright, the −Z yellow is
to your left and the +Z blue to your right.

**What a mirrored face looks like.** Change one entry of the face table — make
the +Z face's right `(-1, 0, 0)` instead of `(1, 0, 0)` — and look at +Z: the
label reads "Z+" with its Z backwards. Turn toward the corner between +Z and +X,
and a hard seam runs down the edge of the face, the grid lines breaking across
it. Put the table back.

---

## 6. A sky computed from the sun

**This is `sunSky` in the bake shader, the sun's disk in `Update`, and
`Sky.frag.glsl`.**

A demo with a sun can have a daylight sky without any image: compute it from the
sun. Real skies come from sunlight scattering in the air, and four things a
clear sky does are enough to make one that reads as daylight:

- **It is blue overhead.** Air scatters short wavelengths far more than long
  ones, so the light reaching you from a patch of empty sky is mostly blue.
- **It is paler toward the horizon**, and brightest in a thin band right at it.
  A line of sight near the horizon crosses far more air, scattered light piles
  up from all colors, and the blue washes out toward white.
- **It glows around the sun.** Larger particles — haze, dust, droplets — scatter
  light only a little off its path, so much of it still arrives from near the
  sun: a wide soft glow, and a tight bright one.
- **Its colors follow the sun.** A low sun's light has crossed so much air that
  most of its blue is scattered away before it arrives; the glow turns orange,
  and as the sun sets the whole sky dims.

**Units.** The scene's sun arrives as an **irradiance** `E`, in whatever units
the scene uses (Chapter 16 section 2). For the sky to sit beside the lit scene
it must be in the same units, so every term below is a color *times the sun's
strength*, the luminance of `E`: a sun twice as strong, a sky twice as bright,
and Chapter 16's exposure treats both alike. A clear sky delivers roughly a
tenth to a fifth of what the sun does; the colors are chosen by eye to land
there.

Write `h` for the sine of a direction's height above the horizon (`d.y`), `s`
for the same of the sun, and `c` for the cosine of the angle between the
direction and the sun (`dot(d, toSun)`). Then, for a direction above the
horizon:

$$ L = E_{\text{lum}} \cdot \text{daylight}(s) \cdot \Big[ \underbrace{\operatorname{mix}(Z, H, e^{-5h})}_{\text{gradient}} + \underbrace{0.5\, H\, e^{-30|h|}}_{\text{horizon band}} + \underbrace{G(s)\,(0.12\, c^{5} + 2\, c^{300})}_{\text{glow}} \Big] $$

where `Z` is the zenith color, `H` the horizon color, and `G` the glow's color,
orange for a low sun and nearly white for a high one. Each term is one line of
the shader:

- `e^{−5h}` is 1 at the horizon and falls to 0.007 straight up, so the gradient
  is the horizon color low down and the zenith color overhead.
- `e^{−30|h|}` is 1 at the horizon and already 0.04 at 6° up: a thin band.
- `c^5` and `c^{300}` are 1 looking at the sun. The first is still 0.5 at 30°
  away, the wide glow; the second is 0.5 at 3.9° away, the tight one.
- `daylight(s)` is a `smoothstep`, Chapter 16 section 5's fade: full above
  about 17° of sun height, gone at 6° below the horizon.

Below the horizon there is ground: a dim brown, lit by the sun when the sun is
up, blended in over the first degree so the horizon has no hard edge.

**Worked example**, Chapter 11's default sun in the Meshes demo: sun color
`π (0.90, 0.85, 0.80)`, whose luminance is 2.69; its height is 63°, so
`s = 0.894` and `daylight = 1`. Straight up, `h = 1`, and `c = s = 0.894`,
because looking straight up the sun is 90° − 63° away. The gradient is
`Z = (0.012, 0.040, 0.150)` (its `e^{−5}` share of the horizon color is
negligible), the band is nothing, and the wide glow adds
`G · 0.12 · 0.894^5 = (0.25, 0.23, 0.19) · 0.069 = (0.017, 0.016, 0.013)`.
Times 2.69: zenith radiance `(0.08, 0.15, 0.44)`. With Chapter 16's tone curve
at Raw and 0 stops, that displays as about (80, 109, 177) in 8-bit sRGB: a mid blue, darker than a white
surface in the sun, which is what real skies are.

```glsl
// Section 6: a daylight sky from the sun alone. Every color is a fraction of the sun's irradiance,
// so the sky is as bright as the scene's own sun says, in the scene's own units.
const vec3 ZENITH_COLOR  = vec3(0.012, 0.040, 0.150);   // straight up: a deep blue
const vec3 HORIZON_COLOR = vec3(0.090, 0.120, 0.160);   // low down: paler, more air in the way
const vec3 GROUND_COLOR  = vec3(0.060, 0.050, 0.040);   // below the horizon: lit earth, albedo 0.2 over pi
const vec3 DAY_GLOW      = vec3(0.250, 0.230, 0.190);   // around a high sun: nearly white
const vec3 SUNSET_GLOW   = vec3(0.400, 0.170, 0.050);   // around a low sun: orange

vec3 sunSky(vec3 direction)
{
    vec3  toSun     = bake.toSun.xyz;
    float strength  = dot(bake.sunIrradiance.rgb, vec3(0.2126, 0.7152, 0.0722));   // the sun's luminance
    float height    = direction.y;   // sine of how far this direction is above the horizon
    float sunHeight = toSun.y;       // the same for the sun

    // 1. The gradient: blue overhead, fading to the paler horizon color in the lowest part of the sky.
    vec3 sky = mix(ZENITH_COLOR, HORIZON_COLOR, exp(-5.0 * max(height, 0.0)));

    // 2. The horizon: a bright band right at it, where a line of sight crosses the most air.
    sky += 0.5 * HORIZON_COLOR * exp(-30.0 * abs(height));

    // 3. The glow: light scattered only a little on its way, so it still arrives from near the sun.
    //    A wide soft part and a tight bright part. Orange when the sun is low, nearly white when high.
    float towardSun = max(dot(direction, toSun), 0.0);   // cos of the angle to the sun
    vec3  glowColor = mix(SUNSET_GLOW, DAY_GLOW, smoothstep(0.0, 0.5, sunHeight));
    sky += glowColor * (0.12 * pow(towardSun, 5.0) + 2.0 * pow(towardSun, 300.0));

    // Below the horizon: the ground, lit by the sun when it is up, blended over a degree or so.
    vec3 ground = GROUND_COLOR * (max(sunHeight, 0.0) + 0.2);
    sky = mix(sky, ground, 1.0 - smoothstep(-0.02, 0.0, height));   // smoothstep needs edge0 < edge1

    // The sun going down takes the daylight with it: full above about 17 degrees, none 6 below.
    float daylight = smoothstep(-0.1, 0.3, sunHeight);
    return strength * daylight * sky;
}
```

This is a model shaped to look right, not a simulation. Where to go for one,
in order of ambition: **Preetham, Shirley, and Smits** (1999) fit a formula to
simulations of real skies, with one "turbidity" number for haze; **Hosek and
Wilkie** (2012) fit a better one, much better near the horizon; and
**Hillaire** (2020) simulates the atmosphere itself — the scattering of air and
haze, the light scattered more than once — into small lookup images in compute,
fast enough for every frame. Each would replace `sunSky` and nothing else.

### The sun's disk

The sky above has a glow around the sun but no sun. The disk is drawn
separately, by the draw's fragment shader, not baked into the cube, for two
reasons. It is tiny — the real sun is 0.53° across, about three texels of the
cube — and would be blocky; drawn per pixel, it is sharp at any size. And a
later chapter that reflects the cube in water adds the sun's own highlight from
the distant light: a cube that held the sun too would count it twice.

How bright? Chapter 16 section 2: a source of radiance `L` covering a small solid
angle `Ω` delivers an irradiance `E = L Ω`. Here `E` is known — the scene's sun
— and `L` is wanted, so `L = E / Ω`. A disk of angular radius `r` covers

$$ \Omega = 2\pi\,(1 - \cos r) \approx \pi r^2 $$

steradians (the area of a small circle of radius `r` on the unit sphere).
**Worked:** the real sun's `r` is 0.265° = 0.004625 radians, so
`Ω = 6.72 × 10⁻⁵`. USD's default `DistantLight` has intensity 50000 and angle
0.53°, which Chapter 16 turned into an irradiance of `50000 × 6.72 × 10⁻⁵ = 3.36`.
The disk's radiance is then `3.36 / 6.72 × 10⁻⁵ = 50000` — exactly the intensity
the file wrote. The sky shows the sun the file describes.

That is close to the largest half float, 65504; a sun of 100000 lux would need
over a billion. Past the limit the scene target would hold infinity, which the
tone curve turns into "not a number", so the disk is clamped at 60000. The tone
curve draws it white either way.

`Update` works out the disk once per frame and keeps it for `Draw`. The `w` of
`toSun` carries the cosine of the disk's radius, or 2 — larger than any cosine —
for no disk:

```cpp
    // Section 6: the sun's disk, for Draw. A source of radiance L covering a solid angle Omega delivers
    // E = L Omega (Chapter 16 section 2), so the disk that delivers the sun's irradiance has
    // L = E / Omega. Clamped below the largest half float, which the scene target can hold.
    m_draw.toSun       = glm::vec4(toSun, 2.0f);   // w = 2: no disk (no cosine is that large)
    m_draw.sunRadiance = glm::vec4(0.0f);
    if (m_mode == SkyMode::SunSky)
    {
        const float solidAngle = glm::two_pi<float>() * (1.0f - std::cos(SUN_ANGULAR_RADIUS));
        m_draw.toSun.w         = std::cos(SUN_ANGULAR_RADIUS);
        m_draw.sunRadiance     = glm::vec4(glm::min(inputs.sunIrradiance / solidAngle * exposure,
                                                    glm::vec3(60000.0f)), 0.0f);
    }
```

**This is `Sky.frag.glsl`, replacing section 1's first version.** It looks
the direction up in the cube, through the draw's set (section 3), and adds the
disk. The disk's edge is softened over one pixel with `fwidth` (Chapter 15
section 5), which says how much the cosine changes from one pixel to the next.
The file opens as Appendix B shows, including `SkyTypes.h`; then:

```glsl
layout(location = 0) in  vec3 viewDirection;
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform samplerCube sky;

layout(push_constant) uniform DrawBlock
{
    SkyDrawParameters draw;
};

void main()
{
    vec3 direction = normalize(viewDirection);
    vec3 radiance  = texture(sky, direction).rgb;

    // Section 6: the sun's disk, drawn here rather than baked, so it is sharp at any cube size. Its edge
    // is softened over about one pixel: fwidth says how much the cosine changes from pixel to pixel.
    float cosAngle = dot(direction, draw.toSun.xyz);
    float edge     = max(fwidth(cosAngle), 1e-7);   // never zero: smoothstep needs two different edges
    float disk     = smoothstep(draw.toSun.w - edge, draw.toSun.w + edge, cosAngle);
    radiance += disk * draw.sunRadiance.rgb;

    outColor = vec4(radiance, 1.0);
}
```

---

## 7. Behind everything: `Update` and `Draw`

**This is `Sky::Update`, and `Sky::Draw` finished.**

### `Update`: bake only when something changed

Filling the cube is 1.5 million invocations. That is nothing for a GPU once,
and a waste every frame when nothing changed — and most frames, nothing has: the
same mode, the same sun, the same image. So `Update` builds the bake's push
constants, which are *everything the cube depends on*, and compares them with
the last bake's. Only a difference — or a cube that was never baked, or a new
image from `SetEnvironment` — runs the bake. The sky's exposure is baked in, so
the cube holds exactly what the sky shows, which is what a later chapter that
reflects the sky in water will want.

`Update` starts by keeping the mode, for `Draw`, and returning at once when the
sky is off; then it works out the exposure as a multiplier, `2^stops`, turns the
sun's travel direction around to point *toward* the sun, and fills in the
disk (section 6). Then the bake:

```cpp
    // Everything the cube depends on. A bake runs only when one of them changed since the last bake.
    const shared::SkyBakeParameters bake{
        .worldToEnvironment  = shared::mat3(inputs.worldToEnvironment),
        .environmentRadiance = glm::vec4(inputs.environmentRadiance, 0.0f),
        .toSun               = glm::vec4(toSun, 0.0f),
        .sunIrradiance       = glm::vec4(inputs.sunIrradiance, 0.0f),
        .mode                = static_cast<uint32_t>(m_mode),
        .exposure            = exposure,
        .padding0            = 0,
        .padding1            = 0,
    };
    const bool changed = !m_cubeValid || std::memcmp(&bake, &m_baked, sizeof(bake)) != 0;
    if (changed)
    {
        // Section 7, before: a write after a read. The last reader was a draw's fragment shader - last
        // frame's, perhaps still running - or a later chapter's compute shader. Every texel is rewritten,
        // so the old contents can go: UNDEFINED.
        transitionImage(commandBuffer, m_cube,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_bakePipeline);
        vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_bakeLayout, 0, 1, &m_bakeSet, 0, nullptr);
        vkCmdPushConstants(commandBuffer, m_bakeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(bake), &bake);
        const uint32_t groups = groupCount(SKY_FACE_SIZE, SKY_BAKE_GROUP_SIZE);
        vkCmdDispatch(commandBuffer, groups, groups, 6);   // z: one slice of workgroups per face

        // Section 7, after: a read after a write. The draw samples the cube in its fragment shader; a later
        // chapter may sample it in a compute shader. Both wait, and both see the bake's writes.
        transitionImage(commandBuffer, m_cube,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

        m_baked     = bake;
        m_cubeValid = true;
    }
}
```

`memcmp` is safe here because every byte of the struct was written: the padding
fields are named and zeroed, and `shared::mat3(...)` zeroes the fourth row of
each column. A struct with gaps the compiler made would compare garbage.

**The two barriers**, through Chapter 04 section 5's three questions:

| | Q1: what finishes, then what waits | Q2: flushed, then made visible | Q3: layout |
| --- | --- | --- | --- |
| Before the bake | Everything that sampled the cube before — last frame's sky draw (`FRAGMENT_SHADER`), and any later chapter's compute shader — then the bake (`COMPUTE_SHADER`) | A read leaves nothing to flush: `NONE`; then `SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL`: every texel is rewritten, so the old ones can go |
| After the bake | The bake's writes (`COMPUTE_SHADER`), then every sampler of the cube (`FRAGMENT_SHADER \| COMPUTE_SHADER`) | `SHADER_STORAGE_WRITE`; then `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |

"Last frame's sky draw" is not a figure of speech. With two frames in flight,
frame N+1's bake can be recorded while frame N's draw is still running on the
GPU. Both are on one queue, and the first barrier's "before" reaches back into
frame N's command buffer (Chapter 04 section 5), so the bake waits for that draw
to finish reading. `COMPUTE_SHADER` in both barriers looks ahead: nothing in
this chapter samples the cube from compute, but the next chapter does (its
filter, Chapter 24 section 4), and it costs nothing.

Both barriers are tested in the exit check: drop `FRAGMENT_SHADER` from either,
and synchronization validation reports the hazard.

### `Draw`, finished: last, at depth 1.0

Section 1's `Draw` gains two things. It returns at once when the sky is off,
so a demo can call it every frame; and it binds the draw's set, whose cube
section 6's fragment shader now samples:

```cpp
void Sky::Draw(VkCommandBuffer commandBuffer, const glm::mat4& view, const glm::mat4& projection) const
{
    if (m_mode == SkyMode::Off) { return; }

    // Section 1: only which way the camera faces matters, so the view loses its translation -
    // mat3(view) keeps the rotation, and mat4 of that puts back a zero translation.
    shared::SkyDrawParameters draw = m_draw;
    draw.clipToWorld = glm::inverse(projection * glm::mat4(glm::mat3(view)));

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawPipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_drawLayout, 0, 1, &m_drawSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_drawLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(draw), &draw);
    vkCmdDraw(commandBuffer, 3, 1, 0, 0);   // the full-screen triangle
}
```

The push constants now start from `m_draw`, the sun's disk `Update` worked out
(section 6). The pipeline is section 1's, with its depth settings: tested
`LESS_OR_EQUAL` against the depth the scene drew, never written, at depth 1.0.

**Why after the scene, not first?** Drawn first, the sky would run its fragment
shader for every pixel of the screen, and the scene would then paint over most
of them: work thrown away. Drawn last, the depth test runs *before* the fragment
shader — GPUs test depth early whenever the shader does not write depth
itself — so a pixel the scene covered never runs the sky's shader at all. The
sky costs only the pixels where it shows.

**Why `LESS_OR_EQUAL` and not `LESS`?** The scene's `LESS` would fail: 1.0 is
not less than 1.0.

**MSAA.** At 4x, the scene pass draws into a multisampled image and resolves
it at the end (Chapter 18 section 2). The sky's pipeline declares the pass's
sample count, like every pipeline in the pass, and is drawn *inside* it, before
the resolve. At the edge of a cube against the sky, a pixel's samples hold some
cube and some sky, and the resolve averages them: a smooth edge. A sky drawn
after the resolve, into the one-sample image, could not do that — the pixel
would already hold the cube averaged with the clear color, and the edge would
keep a dark fringe.

---

## 8. One setting, and the first demo

**This is `SkySettings.h/.cpp`, the setting's route to the demo, and the Cubes
demo's part.**

Which sky to show is not a demo's decision: it is a look the engine offers to
every 3D demo, like Chapter 16's exposure. So it is one setting, edited in one
place:

```cpp
// The values match SKY_MODE_* in SkyTypes.h, which the bake shader reads.
enum class SkyMode : int32_t
{
    Off         = 0,   // no sky: each demo's clear color, as before this chapter
    SunSky      = 1,   // section 6: computed from the demo's sun
    Environment = 2,   // section 4: an HDR image - a USD dome light's, or the built-in test image
};

// One for the whole engine: VulkanRenderer keeps it, Main draws its panel, and every demo's Record
// receives a copy in RecordContext::sky.
struct SkySettings
{
    SkyMode mode          = SkyMode::Off;
    float   exposureStops = 0.0f;   // brightens or darkens the sky alone, by 2^stops
};

// The sky's controls: a "Sky" section of Chapter 16's "Tone mapping" window, so call it after
// drawToneMappingPanel. Defined in SkySettings.cpp; true if anything changed.
bool drawSkyPanel(SkySettings& settings);
```

The header includes only `<cstdint>`, so the demo interface can include it
without pulling in Vulkan. `SkySettings.cpp` includes `SkySettings.h` and
`<imgui.h>`.

The controls are not a window of their own but a section of Chapter 16's, behind
a header that starts closed; the comment says how:

```cpp
bool drawSkyPanel(SkySettings& settings)
{
    bool changed = false;
    // A second Begin with the same name adds to the window the first one made: the sky's controls go in
    // Chapter 16's "Tone mapping" window, under a header that starts closed. Both are how the engine
    // turns the scene's light into the picture; neither belongs to a demo.
    if (ImGui::Begin("Tone mapping") && ImGui::CollapsingHeader("Sky"))
    {
        int mode = static_cast<int>(settings.mode);
        changed |= ImGui::Combo("Mode", &mode, "Off\0Sun sky\0Environment\0");
        settings.mode = static_cast<SkyMode>(mode);
        // AlwaysClamp: a value typed with Ctrl+click stays in range too; 2^20 overflows the half-float cube.
        changed |= ImGui::SliderFloat("Sky exposure", &settings.exposureStops, -10.0f, 10.0f, "%.1f stops",
                                      ImGuiSliderFlags_AlwaysClamp);
    }
    ImGui::End();
    return changed;
}
```

**The route.** `VulkanRenderer` keeps the settings beside the tone mapping's
(`VulkanRenderer.h`, Chapter 16's pattern):

```cpp
    // Chapter 23: what every demo's sky shows. Kept here, like the tone mapping, and handed to the
    // active demo in each frame's RecordContext.
    SkySettings& skySettings() { return m_skySettings; }
```

```cpp
    SkySettings           m_skySettings;                  // Chapter 23
```

and hands a copy to the demo in every frame's `RecordContext` (`Demo.h`, after
`targets`):

```cpp
    vulkan_graphics::SkySettings  sky;                              // Chapter 23: the Sky panel's choice
```

```cpp
// VulkanRenderer::recordFrame, in the call to m_demo->Record, after .targets:
            .sky           = m_skySettings,    // Chapter 23
```

`VulkanRenderer.h` and `Demo.h` each include `SkySettings.h`, which includes
nothing from Vulkan. `Main.cpp` draws the section right after the tone
mapping's window, which it must come after:

```cpp
        vulkan_graphics::drawSkyPanel(renderer.skySettings());   // Chapter 23
```

**A demo's part.** Cubes already owns its `Sky`, builds it in `Setup`, draws
it after the cubes, and shuts it down (section 1). What it gains now is the
second call in `Record`, `Update`, which keeps the cube current, and the
setting, which `Update` reads from `frame.sky`.

The cubes are not lit, so the demo has no sun of its own; the sky gets Chapter
11's. `Update` goes in `Record` after `WriteFrameData` and before the scene
pass, because a bake is a compute dispatch, which cannot run inside a rendering
scope. `CubesDemo.cpp` gains `#include <glm/gtc/constants.hpp>` for `glm::pi`:

```cpp
    // Chapter 23: the cubes are not lit, so the sky gets a sun of its own - Chapter 11's, as the scene
    // graph has it. Before the scene pass: a bake is a compute dispatch.
    const glm::vec3 toSun = glm::normalize(glm::vec3(0.4f, 1.0f, 0.3f));
    m_sky.Update(commandBuffer, frame.sky,
                 { .sunDirection   = -toSun,
                   .sunIrradiance  = glm::pi<float>() * glm::vec3(0.90f, 0.85f, 0.80f) });
```

With the sky Off, `Update` and `Draw` both return at once, and the demo looks
as it did before this chapter.

## Checkpoint

Rerun `GenerateProjects.bat` — `SkySettings.cpp`, the bake shader, and
`CubeMap.glsl` are new since section 1 — build, and open **Cubes**. Open the
**Sky** section of the "Tone mapping" window.

- **Off**: the cubes on their dark clear color, exactly as before.
- **Sun sky**: a blue sky above a bright horizon band, brown ground below it,
  and, if you orbit round to face the sun — high, and behind the starting
  camera a little to its right — a glow and a small white disk.
- **Environment**: the test image. Each axis's disc reads correctly (section 5),
  and the cubes stand in front of it. Its background is section 1's first sky:
  the same colors, now arriving through the cube.

---

# Part 2 — Every scene (sections 9-11)

Part 2 gives the sky to the other 3D demos, shows a USD dome light's own image,
and draws the sky on Chapter 22's deferred path, where the scene pass is over
before the sky's turn comes.

## 9. The other demos

**This is the same five additions in Meshes, the scene graph, and the
particles.**

Each demo gains the include, the member, and `Initialize` and `Shutdown`
exactly as Cubes did (section 1). Only the two calls in `Record` differ, by which sun they
pass and where the opaque drawing ends.

**Meshes and the scene graph** already build their sun as a Chapter 16
`LightItem` for `WriteLights`. Its `direction` is the way the light travels and
its `emission` is the irradiance — exactly `SkyInputs`' two sun fields — so the
sky gets the same sun that lights the scene. In each `Record`, after
`PrepareDraws`:

```cpp
    m_sky.Update(commandBuffer, frame.sky,
                 { .sunDirection   = sun.direction,                          // Chapter 23
                   .sunIrradiance  = sun.emission });
```

and after `RecordDraws`, before `endScenePass`:

```cpp
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);   // Chapter 23: after the opaque draws
```

Move the Meshes panel's sun and the sky follows: the glow and the disk move with
it, the bake runs again on every frame the slider changes, and below about 17° of
elevation the sky dims and the glow turns orange.

**The particles** are not lit, so they get Chapter 11's sun, as the cubes did.
The order is what matters here. The sky is opaque, so it is drawn in the scene
pass, after the ground; the particles blend over whatever is behind them, so
they come after it, in their own scope (Chapter 21 section 5), and blend over
the sky as well:

```cpp
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);   // Chapter 23: after the ground, before the particles
```

Additive particles over a bright sky add little to it, so the fountain is
harder to see at noon than at night, as a real one would be.

**The grass** gets its sky in Chapter 25, the same way, with its panel's sun.

**Not every demo.** The triangle, the gradient, and Life are not 3D. The ocean
(Chapter 29) has a sky function of its own until Chapter 30 replaces it with
this one, and the path tracer (Chapter 33) has no scene pass at all: its compute
shader gives every ray that escapes the scene a sky of its own.

---

## 10. The USD viewer: a dome's image, and the deferred path

**This is `EnvironmentImage`, `importDomeEnvironment`, and the viewer's
additions, including `Sky::DrawInOwnPass`.**

### Keeping the dome's image

Chapter 16 decoded a `DomeLight`'s image only to average it. Environment mode
needs the image itself. TinyUSDZ v0.9.4 parses `inputs:texture:file` into the
typed `DomeLight::file`, which is how Chapter 16 found it. The image becomes an
`EnvironmentImage` in `Light.h`:

```cpp
// Chapter 23: a dome light's lat-long HDR image, kept for the sky. Linear RGBA floats, rows top to
// bottom, tightly packed - what TinyUSDZ decodes an .hdr into.
struct EnvironmentImage
{
    std::string        name;          // the asset path it came from - for log messages
    uint32_t           width  = 0;
    uint32_t           height = 0;
    std::vector<float> pixels;        // width * height * 4
};
inline constexpr uint32_t NO_ENVIRONMENT = UINT32_MAX;   // a dome light without a usable image
```

`Light` gains its index, after `domeTextureAverage`:

```cpp
    uint32_t  environment = NO_ENVIRONMENT;  // Dome (Chapter 23): the image itself, in the Scene's list
```

and `Scene` keeps the images as it keeps Chapter 15's textures — `Scene.h`,
before `AddLight`, and a member after `m_lights`; the two definitions, in the
style of `AddTexture`, are in Appendix B:

```cpp
    // Chapter 23: dome lights' images. A Light refers to one by index (Light::environment).
    uint32_t                AddEnvironment(EnvironmentImage image);   // returns its index
    const EnvironmentImage& GetEnvironment(uint32_t environment) const;
```

```cpp
    std::vector<EnvironmentImage> m_environments;   // Chapter 23: decoded, CPU-side, like m_textures
```

**The importer** reads the same file `domeTextureAverage` read, once more,
leaving Chapter 16's average as it was. One input is not parsed: TinyUSDZ
leaves `inputs:texture:format` in the prim's `props` (Chapter 16 section 3's
"typed, else props"), and the sky understands only lat-long images. A dome that
says `mirroredBall` or `angular` would show as nonsense, so it is refused with a
warning; `automatic` means "the file decides", and an `.hdr` is lat-long.
`importDomeEnvironment` (Appendix B) is `domeTextureAverage`'s first half —
find the asset, read it, decode it — with this check in front and a copy into
an `EnvironmentImage` at the end:

```cpp
    // inputs:texture:format stays in the prim's props in TinyUSDZ v0.9.4 (Chapter 16 section 3). The
    // sky reads lat-long images only; "automatic" means the file decides, and an .hdr is lat-long.
    const auto format = dome.props.find("inputs:texture:format");
    tinyusdz::value::token formatName;
    if (format != dome.props.end() && format->second.is_attribute() &&
        format->second.get_attribute().get_value(&formatName) &&
        formatName.str() != "latlong" && formatName.str() != "automatic")
    {
        Log::warning(std::format("Dome light image {} is {}, not lat-long; the sky will not show it.",
                                 asset.GetAssetPath(), formatName.str()).c_str());
        return pf::scene::NO_ENVIRONMENT;
    }
```

`importLight`'s dome branch gains one line, after the average:

```cpp
        light.environment        = importDomeEnvironment(context, *dome);   // Chapter 23: for the sky
```

`UsdImport.cpp` gains `#include <cstring>` for `std::memcpy`, and `Light.h`
gains `<string>` and `<vector>`.

### Showing it

The viewer finds the dome in `Setup`, and gives its image to the sky. Two small
helpers go at file scope, above the namespace block: `findDomeNode`, the first
node whose light is a dome that kept an image (Appendix B), and `isShown` —
Chapter 12's rule, that a hidden node hides everything below it:

```cpp
// File scope, above the namespace block (Chapter 23). Whether a node is shown: it and every node above
// it visible, the rule Chapter 12's CollectDraws and Chapter 16's CollectLights apply by skipping subtrees.
static bool isShown(const pf::scene::Scene& scene, pf::scene::NodeIndex node)
{
    for (; node != pf::scene::INVALID_NODE; node = scene.GetNode(node).parent)
    {
        if (!scene.GetNode(node).visible) { return false; }
    }
    return true;
}
```

The viewer gains a `Sky m_sky` and a `scene::NodeIndex m_domeNode` beside
`m_ready`, and `Setup`, at its end, before `m_ready = true`:

```cpp
    // Chapter 23: the sky, and the file's dome image for its Environment mode, when there is one.
    if (auto result = m_sky.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats); !result)
    {
        return result;
    }
    m_domeNode = findDomeNode(m_scene);
    if (m_domeNode != scene::INVALID_NODE)
    {
        const scene::Light& dome = m_scene.GetLight(m_scene.GetNode(m_domeNode).light);
        if (auto result = m_sky.SetEnvironment(m_scene.GetEnvironment(dome.environment)); !result)
        {
            return result;
        }
    }
```

Every frame, after `WriteLights`, `Record` tells the sky two things. The
**sun** is the scene's first distant light, the one Chapter 16 made the sun; a
file without one has no daylight, and its sun sky is black. The **dome** is a
node, so it can be turned, and its image turns with it: the first three columns
of its world matrix, normalized, are its rotation (Chapter 12 section 5), and
the bake wants the inverse, world into the dome's frame, which for a rotation
is the transpose (Chapter 11 section 13). Its brightness is `resolveLight`'s without the image's
average; a hidden dome gives none, as in Chapter 16:

```cpp
    // Chapter 23: the sky's sun is the scene's - the first distant light, the one Chapter 16 made the sun.
    vulkan_graphics::SkyInputs skyInputs{};
    const auto sun = std::find_if(m_lights.begin(), m_lights.end(), [](const scene::LightItem& light) {
        return light.type == scene::LightType::Distant;
    });
    if (sun != m_lights.end())
    {
        skyInputs.sunDirection  = sun->direction;
        skyInputs.sunIrradiance = sun->emission;
    }
    // Its environment is the dome's image, turned as the dome's node is turned and as bright as the dome:
    // resolveLight's dome radiance, with Chapter 16's image average left out. A hidden dome gives no light.
    if (m_domeNode != scene::INVALID_NODE)
    {
        const scene::Node& dome = m_scene.GetNode(m_domeNode);
        scene::Light unaveraged = m_scene.GetLight(dome.light);
        unaveraged.domeTextureAverage = glm::vec3(1.0f);
        const glm::mat3 domeToWorld(glm::normalize(glm::vec3(dome.world[0])), glm::normalize(glm::vec3(dome.world[1])),
                                    glm::normalize(glm::vec3(dome.world[2])));   // the columns are its axes (Chapter 12)
        skyInputs.worldToEnvironment  = glm::transpose(domeToWorld);              // a rotation's inverse
        skyInputs.environmentRadiance = isShown(m_scene, m_domeNode) ? scene::resolveLight(unaveraged, dome.world).emission
                                                                     : glm::vec3(0.0f);
    }
    m_sky.Update(commandBuffer, frame.sky, skyInputs);
```

The viewer's panel says which image the sky shows, under "Light gizmos":

```cpp
        ImGui::Text("Sky image: %s", m_domeNode != scene::INVALID_NODE    // Chapter 23
                        ? m_scene.GetEnvironment(m_scene.GetLight(m_scene.GetNode(m_domeNode).light).environment).name.c_str()
                        : "none in this file (the test image)");
```

**`SkyTest.usda`** (Appendix A) is a small scene under a dome whose image is
`Textures/SkyDirections.hdr`: section 5's background, `0.5 + 0.5 d`, written by a
Python script. It proves the whole road from a file: open it in Environment mode
and every direction must show its own color, exactly as the built-in test
image's background does. The script also writes the scene, with the dome
unturned; rotate the **Sky** node 90° about Y in the inspector and the colors
turn with it — looking along −Z you then see +X's pink-red.

### The deferred path

On the forward path the sky goes inside the scene pass, after `RecordDraws`, as
in every demo. Chapter 22's deferred path has no scene pass left by then: the
lighting pass runs in compute and finishes the image outside any rendering
scope, leaving the background with the clear color and the depth at 1.0.
`DrawInOwnPass` opens one — Chapter 21 section 5's second scope, loading the
color and the depth — draws, and closes it. Its two barriers are Chapter 21's,
with one difference: the depth is only tested, so it stays
`DEPTH_ATTACHMENT_OPTIMAL` and needs no return trip:

```cpp
    // Chapter 21's second scope: whatever drew the color last - an earlier scope, or Chapter 22's
    // lighting pass, which leaves it as if one had - must finish before this one loads and writes it.
    transitionImage(commandBuffer, targets.colorImage,
                    VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    // The depth is only tested, never written, so it keeps its layout and needs no return trip; the
    // source is Chapter 04's three-part depth source, as in Chapter 21.
    transitionImage(commandBuffer, targets.depthImage,
                    VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL, VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT
                        | VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_EARLY_FRAGMENT_TESTS_BIT | VK_PIPELINE_STAGE_2_LATE_FRAGMENT_TESTS_BIT,
                    VK_ACCESS_2_DEPTH_STENCIL_ATTACHMENT_READ_BIT,
                    VK_IMAGE_ASPECT_DEPTH_BIT);
```

The rest — the rendering scope with both attachments loaded, the color stored
and the depth left as it was (`STORE_OP_NONE`), the viewport, and a call to
`Draw` — is in Appendix B. After
`RecordLighting`, Chapter 22 left both images exactly as `endScenePass` does,
so these barriers chain from it. The deferred path is one sample only (Chapter 22
section 9), so the pipeline built for the scene's sample count fits this
one-sample scope; the `assert` is there for a programmer who calls it at 4x.

In the viewer's `Record`, the deferred branch calls it after `RecordLighting`,
and the forward branch draws inside its pass:

```cpp
        m_sky.DrawInOwnPass(commandBuffer, frame.targets, frameData.view, frameData.projection);   // Chapter 23
```

```cpp
        m_sky.Draw(commandBuffer, frameData.view, frameData.projection);   // Chapter 23: after the opaque draws
```

Chapter 22's glows come after either, so they blend over the sky as they
blended over the clear color. Forward and Deferred draw the same sky: compare
them in Environment mode and the sky's pixels are identical.

---

## 11. The sky as light, and what comes next

**This section has no code.** It says what the sky does not yet do, and why.

The sky you see should be the light the scene gets. For one case it already is.
Chapter 16 made a dome light's luminance the ambient light, with its image's
average over the sphere — and the sky now shows that same image, at that same
brightness. On `SkyTest.usda` the ambient light is the average of the
directions' colors, a grey of 0.5, and the floor shows it.

For the sun sky it is not: Meshes, the scene graph, and the grass keep their
panels' fixed ambient colors, which do not dim as the sun sets. Using the sun
sky's average instead is not cheap — the CPU would need its own copy of
`sunSky`, or a readback of the GPU's average frames late (Chapter 20 section 9)
— and one color is a poor answer anyway: the light from above is blue, from
below it is the ground's.

The real answer starts from exactly this cube, and the next chapter turns it
into the scene's light.

Chapter 28 puts clouds in this sky: `Sky` gains a `Clouds`, `SkySettings` a
`CloudSettings`, and `SkyInputs` the camera's position and the time.

---

## When it does not work

| Symptom | Likely cause |
| --- | --- |
| The sky covers the whole scene | The scene does not write depth (Cubes with "Depth test" off), or the sky's pipeline writes depth or tests `ALWAYS` |
| No sky anywhere; the clear color shows | The mode is Off, `Draw` is outside the scene pass or before the opaque draws' depth was written, or the triangle's depth is not exactly 1.0 (`gl_Position.z` must equal `w`) |
| No sky with Sun sky, only black | The demo passed no sun: `sunIrradiance` is zero. A USD file with no distant light has no daylight; use Environment |
| One face's label reads backwards, with seams at that face's edges | A row of the face table is wrong (section 2) |
| Every label is mirrored, or the whole sky is turned | The lat-long mapping disagrees with the image's convention (section 4): `u` running the wrong way, or longitude measured from the wrong axis |
| A vertical seam straight behind you, on an environment image | The environment sampler clamps `u` instead of repeating it |
| The sky slides as the camera moves, rather than turning with it | The view's translation reached `clipToWorld`: `mat3(view)` was not used |
| The sky is right, then wrong after moving the sun once | The bake's push constants changed but the cube was not re-baked, or `Draw` reads it before the barrier |
| A bright speck flickers to black, or the sun turns into a dark hole | A value past 65504 became infinity: the disk, the environment image, or the bake's result (after the dome's brightness and the Sky exposure multiplied it) was not clamped |
| A dark fringe around everything against the sky at 4x | The sky was drawn after the resolve, not in the multisampled pass |
| Validation: image layout at `vkCmdDraw` or `vkCmdDispatch` | `Draw` before any `Update`, or a descriptor names a layout the barriers do not leave the cube in |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and run Part 1's checkpoint in
      Cubes again. Then open the **Sky** section in each 3D demo — Meshes, the
      scene graph, the USD viewer, and the particles — and switch Off, Sun sky,
      and Environment. Each switch takes effect at once, and switching demos
      keeps the choice.
- [ ] **Orientation.** In Cubes, Environment, orbit to face each axis: six
      discs in the right colors, every label reading normally (section 5). In
      the USD viewer, open `SkyTest.usda` (run `make_sky_test.py` first): the
      panel's "Sky image" names `Textures/SkyDirections.hdr`, and looking
      straight ahead (−Z) the middle of the screen is olive, `(0.5, 0.5, 0)`,
      which displays as about (187, 187, 0) with the tone mapping at Raw and 0
      stops (a shade under 0.5's 188: the script rounds the file's values
      down). Turn the **Sky** node 90° about Y in the inspector: the middle
      becomes pink-red, `(1, 0.5, 0.5)`.
- [ ] **Break the face table, then fix it.** Make the +Z face's right
      `(-1, 0, 0)` (section 5): its label reads "Z+" backwards, and seams
      appear at its edges. Put it back.
- [ ] **Sun.** In Meshes, Sun sky: drag the sun's elevation from 90° down to
      0°. The disk and glow follow it; under about 17° the sky darkens and the
      glow turns orange. Looking straight up at the default sun, the sky reads
      about (80, 109, 177) at Raw and 0 stops (section 6's worked example).
      The **Sky exposure** slider brightens and darkens the sky alone; the
      tone mapping's exposure, both sky and scene.
- [ ] **MSAA.** Set 4x in the MSAA window, in Cubes and in Meshes, with Sun
      sky: the edges of the cubes and spheres against the sky are smooth, with
      no dark outline, and validation stays silent.
- [ ] **Deferred.** In the USD viewer on `ShadowTest.usda`, Sun sky, switch
      Forward and Deferred: the sky is the same on both.
- [ ] **Both barriers are proven.** In `Update`, drop
      `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT` from the *second* barrier's
      destination and switch to Sun sky: synchronization validation reports
      `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDraw`, the fragment shader
      reading the cube. Put it back, drop it from the *first* barrier's source
      instead, and switch Sun sky, then Environment: it reports
      `SYNC-HAZARD-WRITE-AFTER-READ`, the bake's layout change overwriting
      what the last frame's draw read. If neither fires, the shader-access
      setting is off (Chapter 20 section 5). Put both back. Run these at this
      chapter's state: once Chapters 24 and 28 are built, the *second*
      barrier's edit is silent. Each puts compute work between the bake and
      the sky's draw (24's filter, 28's clouds) whose own barriers end at the
      fragment stage, and on the Windows pass either one alone was enough to
      hide the hazard; it was reported again only with both of their `Update`
      calls taken out of `Sky::Update`. The *first* barrier's edit still fires.
- [ ] Validation is silent through mode switches, demo switches, file
      switches, resizes, and 1x/4x, and quitting reports no leaked VMA
      allocation.

Next: [24 — Image-Based Lighting](24-Image-Based-Lighting.md)

---

## Sources

- The Khronos Group, *Vulkan Specification*, "Cube Map Face Selection" (the
  face table of section 2) and "Image Views".
- OpenEXR, "Latitude-Longitude Map" in its environment-map documentation, and
  Pixar, *UsdLux DomeLight* schema documentation, which adopts it (section 4).
- A. J. Preetham, P. Shirley, B. Smits, "A Practical Analytic Model for
  Daylight", SIGGRAPH 1999.
- L. Hosek, A. Wilkie, "An Analytic Model for Full Spectral Sky-Dome
  Radiance", SIGGRAPH 2012.
- S. Hillaire, "A Scalable and Production Ready Sky and Atmosphere Rendering
  Technique", Eurographics Symposium on Rendering 2020.
- B. Karis, "Real Shading in Unreal Engine 4", SIGGRAPH 2013 course notes —
  the split-sum approximation, named in Chapter 24 section 5.

---

## Appendix A — `make_sky_test.py`

Reference. It writes `Textures/SkyDirections.hdr`, a 512 × 256 lat-long image
in Radiance's `.hdr` format, whose color in every direction is `0.5 + 0.5 d`,
and `SkyTest.usda`, which puts it on a dome light. Run it once from
`Assets/Scenes/`. The direction function is section 4's, in Python.

```python
# Assets/Scenes/make_sky_test.py
# Writes Chapter 23's sky test: Textures/SkyDirections.hdr, a lat-long HDR image whose color in every
# direction d is 0.5 + 0.5 d, and SkyTest.usda, a small scene under a DomeLight that shows it. Run once,
# from Assets/Scenes/:
#     python make_sky_test.py
# Plain Python 3, standard library only. Not part of the build: what it writes is committed.

import math

WIDTH, HEIGHT = 512, 256

# Chapter 23 section 4: the direction through the centre of texel (x, y) of a lat-long image, in
# OpenEXR's convention, which UsdLux's DomeLight uses: longitude +pi at the left edge, 0 in the middle;
# latitude +pi/2 at the top.
def direction(x, y):
    longitude = (0.5 - (x + 0.5) / WIDTH) * 2.0 * math.pi
    latitude = (0.5 - (y + 0.5) / HEIGHT) * math.pi
    return (math.cos(latitude) * math.sin(longitude), math.sin(latitude), math.cos(latitude) * math.cos(longitude))

# Radiance's RGBE: three 8-bit mantissas sharing one exponent, the brightest channel's.
def rgbe(r, g, b):
    brightest = max(r, g, b)
    if brightest < 1e-32:
        return (0, 0, 0, 0)
    mantissa, exponent = math.frexp(brightest)   # brightest = mantissa * 2^exponent, mantissa in [0.5, 1)
    scale = mantissa * 256.0 / brightest
    return (int(r * scale), int(g * scale), int(b * scale), exponent + 128)

# One scanline in the run-length format every .hdr reader expects: a 4-byte marker, then each of the
# four channels in turn, as packets of at most 128 bytes copied as they are (no runs: simple, and valid).
def scanline(pixels):
    out = bytearray([2, 2, WIDTH >> 8, WIDTH & 255])
    for channel in range(4):
        values = [pixel[channel] for pixel in pixels]
        for start in range(0, WIDTH, 128):
            chunk = values[start:start + 128]
            out.append(len(chunk))
            out.extend(chunk)
    return out

with open("Textures/SkyDirections.hdr", "wb") as image:
    image.write(f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {HEIGHT} +X {WIDTH}\n".encode("ascii"))
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            d = direction(x, y)
            row.append(rgbe(0.5 + 0.5 * d[0], 0.5 + 0.5 * d[1], 0.5 + 0.5 * d[2]))
        image.write(scanline(row))

# The scene: a small floor, a ball and a box to see the dome light on, a camera at eye height looking
# down -Z, and the dome. Y-up and in metres, so the dome's +Y pole is the world's up.
SCENE = """#usda 1.0
(
    defaultPrim = "SkyTest"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "SkyTest"
{
    def Camera "Camera"
    {
        float focalLength = 18
        float verticalAperture = 24
        float2 clippingRange = (0.1, 1000)
        double3 xformOp:translate = (0, 1.6, 4)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    def Cube "Floor"
    {
        double size = 1
        double3 xformOp:translate = (0, -0.05, 0)
        float3 xformOp:scale = (6, 0.1, 6)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }

    def Sphere "Ball"
    {
        double radius = 0.6
        double3 xformOp:translate = (-1, 0.6, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    def Cube "Box"
    {
        double size = 1
        double3 xformOp:translate = (1, 0.5, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    # The sky: the image above, unturned, at intensity 1 - so the background shows its values as they are.
    def DomeLight "Sky"
    {
        asset inputs:texture:file = @Textures/SkyDirections.hdr@
        token inputs:texture:format = "latlong"
        float inputs:intensity = 1
    }
}
"""

with open("SkyTest.usda", "w") as scene:
    scene.write(SCENE)
```

## Appendix B — The rest of the code

Reference: the parts of `Sky.cpp` the sections described without listing.
Where a function was partly listed in a section, that part is named, not
printed again.

**`Sky.cpp`'s includes**, as the finished file has them:

```cpp
#include "PillowFort/VulkanGraphics/Sky.h"

#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"
#include "PillowFort/VulkanGraphics/VulkanBarriers.h"

#include <glm/gtc/constants.hpp>
#include <glm/gtc/packing.hpp>   // packHalf1x16

#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
```

**The glyphs and `makeTestEnvironment`** (section 5), at file scope:

```cpp
// File scope, above the namespace block. Section 5's five glyphs, 5 x 7 cells each: one byte per row,
// top row first, the leftmost cell in bit 4.
static constexpr std::array<std::array<uint8_t, 7>, 5> TEST_GLYPHS{ {
    { 0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00 },   // +
    { 0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00 },   // -
    { 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11 },   // X
    { 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04 },   // Y
    { 0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F },   // Z
} };
```

```cpp
// File scope, above the namespace block. Section 5: the whole test environment, as a lat-long image -
// the same shape as a dome light's file, so it reaches the cube by the same road.
static pf::scene::EnvironmentImage makeTestEnvironment(uint32_t width, uint32_t height)
{
    pf::scene::EnvironmentImage image{
        .name   = "built-in test environment",
        .width  = width,
        .height = height,
        .pixels = std::vector<float>(static_cast<size_t>(width) * height * 4),
    };
    for (uint32_t y = 0; y < height; ++y)
    {
        for (uint32_t x = 0; x < width; ++x)
        {
            const glm::vec3 direction = latLongDirection((static_cast<float>(x) + 0.5f) / static_cast<float>(width),
                                                         (static_cast<float>(y) + 0.5f) / static_cast<float>(height));
            const glm::vec3 radiance  = testEnvironmentRadiance(direction);
            float* texel = &image.pixels[(static_cast<size_t>(y) * width + x) * 4];
            texel[0] = radiance.r;
            texel[1] = radiance.g;
            texel[2] = radiance.b;
            texel[3] = 1.0f;
        }
    }
    return image;
}
```

**`TestAxis` and the six axes** (section 5), at file scope:

```cpp
// File scope, above the namespace block. One axis of the test environment: where it points, which way
// is up on its label, its disc's color, and its label as two glyph indices.
struct TestAxis
{
    glm::vec3 axis;
    glm::vec3 up;
    glm::vec3 color;
    int       sign;     // 0 '+', 1 '-'
    int       letter;   // 2 'X', 3 'Y', 4 'Z'
};

// The six axes. Positive axes red, green, blue; negative ones the opposite colors. A label's up is +Y
// for the four around the horizon; for +Y and -Y it is what a camera facing -Z sees as up after
// tilting to look at them.
static const std::array<TestAxis, 6> TEST_AXES{ {
    { {  1, 0, 0 }, { 0, 1, 0 }, { 1, 0, 0 }, 0, 2 },
    { { -1, 0, 0 }, { 0, 1, 0 }, { 0, 1, 1 }, 1, 2 },
    { { 0,  1, 0 }, { 0, 0, 1 }, { 0, 1, 0 }, 0, 3 },
    { { 0, -1, 0 }, { 0, 0,-1 }, { 1, 0, 1 }, 1, 3 },
    { { 0, 0,  1 }, { 0, 1, 0 }, { 0, 0, 1 }, 0, 4 },
    { { 0, 0, -1 }, { 0, 1, 0 }, { 1, 1, 0 }, 1, 4 },
} };
```

**The rest of `CreateCube`** (section 3), after the view:

```cpp
    // Readable from the start. A later chapter's set may name the cube while the sky is off and nothing
    // has been baked, and validation checks the layout of every image a pipeline's sets name, even on a
    // branch the shader never takes. Until the first bake the contents mean nothing - a reader samples
    // the cube only while the sky is on - but the layout must already be the one its descriptor names.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_cube,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });

    // Linear filtering, one level. A cube's faces are filtered across their edges automatically (Vulkan
    // has no non-seamless cubes without an extension), so the address mode matters only inside a face.
    VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .maxLod       = 0.0f,
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_cubeSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the sky's cube.");
    }

    // Section 4: a lat-long image wraps around left to right - longitude -pi is +pi - but not top to
    // bottom, where the rows end at the poles.
    samplerInfo.addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_environmentSampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the sky's environment image.");
    }
    return InitializationResult::success();
}
```

**`CreateDescriptors`** (section 3):

```cpp
InitializationResult Sky::CreateDescriptors()
{
    // The bake's set: the cube's faces to write, and the environment image to read.
    const std::array<VkDescriptorSetLayoutBinding, 2> bakeBindings{ {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    } };
    // The draw's set: the cube, sampled by direction.
    const VkDescriptorSetLayoutBinding drawBinding{
        .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,
        .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT,
    };
    VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(bakeBindings.size()),
        .pBindings    = bakeBindings.data(),
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &layoutInfo, nullptr, &m_bakeSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the sky's bake.");
    }
    layoutInfo.bindingCount = 1;
    layoutInfo.pBindings    = &drawBinding;
    if (vkCreateDescriptorSetLayout(m_context.device, &layoutInfo, nullptr, &m_drawSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the sky's draw.");
    }

    const std::array<VkDescriptorPoolSize, 2> poolSizes{ {
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 1 },
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 2 },
    } };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 2,
        .poolSizeCount = static_cast<uint32_t>(poolSizes.size()),
        .pPoolSizes    = poolSizes.data(),
    };
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &m_pool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the sky.");
    }

    const std::array<VkDescriptorSetLayout, 2> setLayouts{ m_bakeSetLayout, m_drawSetLayout };
    std::array<VkDescriptorSet, 2>             sets{};
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_pool,
        .descriptorSetCount = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts        = setLayouts.data(),
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, sets.data()) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the sky.");
    }
    m_bakeSet = sets[0];
    m_drawSet = sets[1];

    // The two that never change. The environment image (bake binding 1) is written by SetEnvironment.
    // Each names the layout the image will be in when the shader runs (section 7).
    const VkDescriptorImageInfo storageInfo{
        .imageView   = m_cubeView,
        .imageLayout = VK_IMAGE_LAYOUT_GENERAL,
    };
    const VkDescriptorImageInfo cubeInfo{
        .sampler     = m_cubeSampler,
        .imageView   = m_cubeView,
        .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
    };
    const std::array<VkWriteDescriptorSet, 2> writes{ {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_bakeSet, .dstBinding = 0,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .pImageInfo = &storageInfo },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = m_drawSet, .dstBinding = 0,
          .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &cubeInfo },
    } };
    vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

**`CreatePipelines`**, as section 3 grows it from section 1's:

```cpp
InitializationResult Sky::CreatePipelines()
{
    // The bake: its set, and SkyBakeParameters as push constants.
    const VkPushConstantRange bakeRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(shared::SkyBakeParameters),
    };
    VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_bakeSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &bakeRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_bakeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sky's bake.");
    }
    m_bakePipeline = createComputePipeline(m_context.device, m_pipelineCache, "Sky/SkyBake.comp.spv", m_bakeLayout);
    if (m_bakePipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sky's bake pipeline failed.");
    }

    // The draw: its set, and SkyDrawParameters, which the vertex shader reads (the matrix) as well as
    // the fragment shader (the sun).
    const VkPushConstantRange drawRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(shared::SkyDrawParameters),
    };
    layoutInfo.pSetLayouts         = &m_drawSetLayout;
    layoutInfo.pPushConstantRanges = &drawRange;
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_drawLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sky's draw.");
    }

    // Then section 1's lines, as listed there: the GraphicsPipelineDesc with its depth settings,
    // createGraphicsPipeline, and the return.
}
```

**`SetEnvironment`, the part section 4 did not list, and
`WriteEnvironmentDescriptor`**:

```cpp
InitializationResult Sky::SetEnvironment(const scene::EnvironmentImage& image)
{
    // From Setup only: nothing in flight is reading the old image yet.
    DestroyEnvironment();

    // Half floats, as the cube: enough range for a sky, half the memory of 32-bit floats, and every
    // GPU can filter them linearly - which 32-bit float images do not promise.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent        = { image.width, image.height, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo,
                       &m_environment, &m_environmentAllocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the sky's environment image.");
    }
    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_environment,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_environmentView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the sky's environment image.");
    }

    // Then section 4's lines, as listed there: the upload, its second barrier, WriteEnvironmentDescriptor,
    // m_cubeValid = false, and the return.
}
```

```cpp
void Sky::WriteEnvironmentDescriptor()
{
    const VkDescriptorImageInfo imageInfo{
        .sampler     = m_environmentSampler,
        .imageView   = m_environmentView,
        .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
    };
    const VkWriteDescriptorSet write{
        .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
        .dstSet          = m_bakeSet,
        .dstBinding      = 1,
        .descriptorCount = 1,
        .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
        .pImageInfo      = &imageInfo,
    };
    vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
}
```

**`DrawInOwnPass`**, with section 10's barriers left out:

```cpp
void Sky::DrawInOwnPass(VkCommandBuffer commandBuffer, const SceneTargets& targets,
                        const glm::mat4& view, const glm::mat4& projection) const
{
    if (m_mode == SkyMode::Off) { return; }
    assert(targets.formats.samples == VK_SAMPLE_COUNT_1_BIT);   // a programmer's mistake: section 10

    // Section 10's two barriers, as listed there: the color, and the depth, which keeps its layout.

    // Load both, store the color; the depth is left exactly as it was (STORE_OP_NONE).
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
        .imageLayout = VK_IMAGE_LAYOUT_DEPTH_ATTACHMENT_OPTIMAL,
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

    Draw(commandBuffer, view, projection);
    vkCmdEndRendering(commandBuffer);
}
```

**`importDomeEnvironment`** (section 10), in `UsdImport.cpp` at file scope, above
`importLight`:

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 23). A dome light's lat-long image,
// decoded into the scene for the sky to show; NO_ENVIRONMENT when it has none that can be used. It
// reads the same file domeTextureAverage does, once more: that average stays Chapter 16's ambient.
static uint32_t importDomeEnvironment(ImportContext& context, const tinyusdz::DomeLight& dome)
{
    tinyusdz::value::AssetPath asset;
    const auto file = dome.file.get_value();
    if (!file || !file.value().get_default(&asset) || asset.GetAssetPath().empty()) { return pf::scene::NO_ENVIRONMENT; }

    // Section 10's format check, as listed there: anything but lat-long or "automatic" is refused.

    const std::vector<uint8_t> bytes = readAssetBytes(context, asset.GetAssetPath());
    auto decoded = tinyusdz::image::LoadImageFromMemory(bytes.data(), bytes.size(), asset.GetAssetPath());
    if (bytes.empty() || !decoded || decoded.value().image.format != tinyusdz::Image::PixelFormat::Float ||
        decoded.value().image.channels != 4)
    {
        return pf::scene::NO_ENVIRONMENT;   // domeTextureAverage has already said why
    }
    const tinyusdz::Image& image = decoded.value().image;
    pf::scene::EnvironmentImage environment{
        .name   = asset.GetAssetPath(),
        .width  = static_cast<uint32_t>(image.width),
        .height = static_cast<uint32_t>(image.height),
        .pixels = std::vector<float>(static_cast<size_t>(image.width) * image.height * 4),
    };
    std::memcpy(environment.pixels.data(), image.data.data(), environment.pixels.size() * sizeof(float));
    return context.scene.AddEnvironment(std::move(environment));
}
```

**`Scene::AddEnvironment` and `GetEnvironment`** (section 10), in `Scene.cpp`:

```cpp
uint32_t Scene::AddEnvironment(EnvironmentImage image)
{
    m_environments.push_back(std::move(image));   // tens of megabytes of floats: moved, not copied
    return static_cast<uint32_t>(m_environments.size() - 1);
}

const EnvironmentImage& Scene::GetEnvironment(uint32_t environment) const { return m_environments.at(environment); }
```

**`findDomeNode`** (section 10), in `UsdViewerDemo.cpp` at file scope:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp - file scope, above the namespace block (Chapter 23). The first dome
// light that kept an image: the one the sky's Environment mode shows. INVALID_NODE when there is none.
static pf::scene::NodeIndex findDomeNode(const pf::scene::Scene& scene)
{
    for (pf::scene::NodeIndex node = 0; node < scene.NodeCount(); ++node)
    {
        const uint32_t light = scene.GetNode(node).light;
        if (light != pf::scene::NO_COMPONENT && scene.GetLight(light).type == pf::scene::LightType::Dome &&
            scene.GetLight(light).environment != pf::scene::NO_ENVIRONMENT)
        {
            return node;
        }
    }
    return pf::scene::INVALID_NODE;
}
```

**`DestroyEnvironment` and `Shutdown`:**

```cpp
void Sky::DestroyEnvironment()
{
    vkDestroyImageView(m_context.device, m_environmentView, nullptr);   // null is a no-op
    if (m_context.allocator != VK_NULL_HANDLE)                          // VMA asserts on a null allocator
    {
        vmaDestroyImage(m_context.allocator, m_environment, m_environmentAllocation);
    }
    m_environmentView       = VK_NULL_HANDLE;
    m_environment           = VK_NULL_HANDLE;
    m_environmentAllocation = VK_NULL_HANDLE;
}
```

```cpp
void Sky::Shutdown()
{
    // Initialize never ran: there is no device to destroy anything with. Otherwise null handles are
    // no-ops, so a partial Initialize is safe. The pool frees both sets.
    if (m_context.device == VK_NULL_HANDLE) { return; }
    vkDestroyPipeline(m_context.device, m_drawPipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_drawLayout, nullptr);
    vkDestroyPipeline(m_context.device, m_bakePipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_bakeLayout, nullptr);
    vkDestroyDescriptorPool(m_context.device, m_pool, nullptr);
    vkDestroyDescriptorSetLayout(m_context.device, m_drawSetLayout, nullptr);
    vkDestroyDescriptorSetLayout(m_context.device, m_bakeSetLayout, nullptr);
    DestroyEnvironment();
    vkDestroySampler(m_context.device, m_environmentSampler, nullptr);
    vkDestroySampler(m_context.device, m_cubeSampler, nullptr);
    vkDestroyImageView(m_context.device, m_cubeView, nullptr);
    if (m_context.allocator != VK_NULL_HANDLE)
    {
        vmaDestroyImage(m_context.allocator, m_cube, m_cubeAllocation);
    }

    m_drawPipeline = m_bakePipeline = VK_NULL_HANDLE;
    m_drawLayout   = m_bakeLayout   = VK_NULL_HANDLE;
    m_pool         = VK_NULL_HANDLE;
    m_bakeSet      = m_drawSet      = VK_NULL_HANDLE;
    m_drawSetLayout = m_bakeSetLayout = VK_NULL_HANDLE;
    m_environmentSampler = m_cubeSampler = VK_NULL_HANDLE;
    m_cubeView           = VK_NULL_HANDLE;
    m_cube           = VK_NULL_HANDLE;
    m_cubeAllocation = VK_NULL_HANDLE;
    m_cubeValid      = false;
    m_mode           = SkyMode::Off;
    m_context        = {};
}
```

**`SkyTypes.h`**, whole (section 3):

```c
/* Shaders/Include/SkyTypes.h - Chapter 23: the sky's push constants, in both languages. GLSL and C++
   both include it as "SkyTypes.h": Shaders/Include is on both include paths. */
#ifndef PF_SKY_TYPES_H
#define PF_SKY_TYPES_H

#include "SharedShaderTypes.h"   /* vec4, mat3, mat4, uint */

#define SKY_FACE_SIZE       512  /* texels along each side of each of the cube's six faces */
#define SKY_BAKE_GROUP_SIZE 8    /* the bake's local_size_x and _y, and the C++ side's groupCount divisor */

/* SkyBakeParameters::mode. The values are SkyMode's (SkySettings.h); Off never bakes. */
#define SKY_MODE_SUN_SKY     1u
#define SKY_MODE_ENVIRONMENT 2u

#ifdef __cplusplus
    namespace pf::shared {
#endif

/* Section 3's SkyBakeParameters, then section 1's SkyDrawParameters, as listed there. */

#ifdef __cplusplus
    static_assert(sizeof(SkyBakeParameters) == 112, "SkyBakeParameters layout drifted.");
    static_assert(offsetof(SkyBakeParameters, toSun) == 64, "SkyBakeParameters alignment drifted.");
    static_assert(offsetof(SkyBakeParameters, mode) == 96, "SkyBakeParameters alignment drifted.");
    static_assert(sizeof(SkyDrawParameters) == 96, "SkyDrawParameters layout drifted.");
    }
#endif

#endif
```

**`Sky.frag.glsl`'s opening** (section 6):

```glsl
// Shaders/Sky/Sky.frag.glsl - Chapter 23: the sky behind everything. Each pixel looks up its own view
// direction in the cube, and the sun's disk is added on top.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "SkyTypes.h"   // SkyDrawParameters
```

**The bake shader's opening**, before the two functions sections 4 and 6
showed:

```glsl
// Shaders/Sky/SkyBake.comp.glsl - Chapter 23: fills the sky's cube. One invocation per texel; the
// dispatch's z is the face, so one dispatch covers all six.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "CubeMap.glsl"   // cubeTexelDirection, latLongUv
#include "SkyTypes.h"     // SkyBakeParameters, SKY_FACE_SIZE

layout(local_size_x = SKY_BAKE_GROUP_SIZE, local_size_y = SKY_BAKE_GROUP_SIZE, local_size_z = 1) in;

layout(set = 0, binding = 0, rgba16f) uniform writeonly imageCube cube;   // texel (x, y) of face z
layout(set = 0, binding = 1) uniform sampler2D environment;                   // lat-long, linear radiance

layout(push_constant) uniform BakeBlock
{
    SkyBakeParameters bake;
};
```

