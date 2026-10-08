# 24 — Image-Based Lighting

**Goal:** the scene is lit by the sky it shows. A floor under a blue sky turns
blue, the underside of a ball turns the color of the ground, a wall facing a
sunset glows orange, and a polished sphere reflects the sky, blurred as much as
its roughness says. Chapter 23's cube is filtered into two small cubes and a
table whenever the sky is baked again. The mesh shaders read them in place of
Chapter 16's single ambient color, under each of Chapter 15's three BRDFs and
on both of Chapter 22's paths. One checkbox switches between the two kinds of
ambient light, so you can see what each costs and what each gets wrong.

**ROADMAP:** step 21+. Engine code, not a demo: an `ImageBasedLighting` class
in `VulkanGraphics` that Chapter 23's `Sky` owns. `SceneRenderer`'s set 0
gains three bindings. Meshes, the scene graph, and the USD viewer light their
scenes with it, and from Chapter 25 the grass.

**Module:**

- `Source/PillowFort/VulkanGraphics/`, `pf::vulkan_graphics` —
  `ImageBasedLighting.h/.cpp` (new); `Sky` owns one; `SkySettings` gains a
  checkbox; `SceneRenderer` gains set 0's bindings 10-12; `GpuTimestamps.h/.cpp`
  (new), timestamp queries made into a class.
- Shaders: `Shaders/Sky/SkyDownsample.comp.glsl`, `SkyConvolve.comp.glsl`,
  `SpecularLut.comp.glsl`; `Shaders/Include/ImageBasedLighting.glsl` and
  `ImageBasedLightingTypes.h`; one line each in `Mesh.frag.glsl` and
  `GBuffer.frag.glsl`; `FrameData` gains a field.

**Math:** taught here — the light arriving on a surface as a sum over the whole
sky, each direction weighted by its cosine (section 1); the solid angle of one
texel of a cube (section 2); weighting by GGX's distribution, and splitting one
sum into two (section 5); placing directions by equal shares of a lobe rather
than evenly, which is importance sampling without random numbers (section 7).
Assumed: solid angle, radiance, and irradiance (Chapter 16 section 2), the three
BRDFs and their symbols (Chapter 15 section 9), and the cube's face table
(Chapter 23 section 2).

**Prerequisites:**

- Chapter 04 section 5 — the three questions a barrier answers, and that a
  barrier covers last frame's commands too.
- Chapter 08 sections 6 (descriptor sets) and 8 (structs shared by C++ and
  GLSL).
- Chapter 10 section 7 — `FrameData` grows only at its end.
- Chapter 15 sections 5 (mip levels; `textureLod`) and 9 (`SurfaceSample`, the
  three BRDFs, `fresnelEndpoints`, `schlickFresnel`, `evaluateAmbient`, and
  `FrameData::brdf`).
- Chapter 16 section 2 — solid angle; `E = L Ω`; a dome of radiance L delivers
  πL, which is why a dome's luminance is the ambient color.
- Chapter 20 sections 2 to 5 — compute pipelines, dispatch sizes, storage
  images, and barriers between dispatches.
- Chapter 21 section 5 — two barriers that *chain*.
- Chapter 22 sections 2 and 4 — on the deferred path the G-buffer pass, not the
  lighting pass, adds the ambient light.
- Chapter 23 sections 2 (the face table and `cubeTexelDirection`), 3 (the cube
  is readable from `Initialize` on), 7 (`Update` bakes only on a change, and its
  two barriers), and 8 (`SkySettings` and the Sky panel).
- For section 9 only: Chapter 21 section 8 — timestamp queries, which the
  particles time their passes with — and Chapter 22 section 11, which copies
  them for the USD viewer.

---

## Where this is going

Open `MaterialSweep.usda` (Chapter 15 section 13) in the USD viewer with the
sky in **Environment** mode. The camera faces −Z, so behind the spheres is the
test image's yellow disc with its **−Z** label. Until now the spheres' ambient
light was one grey color. With this chapter, the gold sphere of roughness 0 is
a mirror: it shows the green **+Y** disc above it and the red **+X** disc to its
side. The next one shows them blurred, and the roughest is a smooth wash of the
colors around it. The grey plastic spheres pick up a pale green on top and a
violet underneath, the colors of the sky above and below them. Untick
**Light the scene with the sky** in the Sky section, and they are grey again.

Chapter 23's `Sky::Update` gains one call, and the mesh shaders one line:

```text
 Sky::Update
   bake the sky cube                   only when the sky changed (Chapter 23)
   ImageBasedLighting::Update          every frame; filters only when the sky was just baked     sections 4, 9
     Filter                            compute, sections 3, 4, 6
       downsample: the sky into small copies, each texel the average of the sky texels it covers
       convolve:   the diffuse cube (32 x 32), and the specular cube's levels 1-4
 scene pass, or the G-buffer pass
   Mesh.frag / GBuffer.frag            evaluateAmbientLight: Chapter 16's constant, or the sky   sections 4, 8
```

### The class map

**This is `Source/PillowFort/VulkanGraphics/ImageBasedLighting.h`**, whole.
`Sky` owns one the way `SceneRenderer` owns Chapter 17's `ShadowMaps`: created
in `Sky::Initialize`, updated by every `Sky::Update`, which filters again
whenever the sky was just baked, and destroyed in `Sky::Shutdown`. Each private
function names the section that writes it.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  The sky's light: its cube filtered for diffuse and specular shading (Chapter 24)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/ImageBasedLighting.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "ImageBasedLightingTypes.h"   // IBL_SPECULAR_LEVELS, IBL_SOURCE_LEVELS

#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>

namespace pf::vulkan_graphics {

// One cube image and the views the filter and the shaders need of it.
struct IblCube
{
    VkImage       image      = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    VkImageView   sampled    = VK_NULL_HANDLE;   // every level: a samplerCube, or the source's sampler2DArray
    std::array<VkImageView, IBL_SPECULAR_LEVELS> levels{};   // one CUBE view per level, for imageStore
};

// The light the sky gives a scene, for the mesh shaders' ambient term. The Sky owns one: Initialize from
// Sky::Initialize, Update from Sky::Update every frame the sky is on, Shutdown from Sky::Shutdown.
class ImageBasedLighting
{
public:
    // The images and the filter's pipelines; the lookup table is computed here, once (section 7).
    // `sky` and `skySampler` are the Sky's cube, which Filter reads. From here on the three images that
    // set 0 names are in SHADER_READ_ONLY_OPTIMAL; their contents are defined after the first Filter.
    InitializationResult Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                    VkImageView sky, VkSampler skySampler);
    void Shutdown();   // device idle first; safe after a partial Initialize

    // Every frame the sky is on, from Sky::Update, after its bake, outside any rendering scope. When the sky
    // was just baked, filters it again (sections 4 and 6), timed in frameIndex's slot (section 9); either
    // way, both cubes are left readable by fragment and compute shaders.
    void Update(VkCommandBuffer commandBuffer, uint32_t frameIndex, bool skyBaked);

    // Set 0's bindings 10, 11, and 12 (section 4).
    VkDescriptorImageInfo DiffuseInfo() const;
    VkDescriptorImageInfo SpecularInfo() const;
    VkDescriptorImageInfo LutInfo() const;

    // Section 9: the GPU time the last filter took, once the GPU has finished it; 0 until then.
    float LastFilterMilliseconds() const { return m_lastMilliseconds; }

private:
    InitializationResult CreateCube(IblCube& cube, uint32_t size, uint32_t levels, VkImageViewType sampledType,
                                    const char* name);                                                // section 3
    InitializationResult CreateLut();                                                                 // section 7
    InitializationResult CreatePipelines();                                                           // section 3
    InitializationResult CreateSets();                                                                // section 3
    InitializationResult ComputeLut();                                                                // section 7
    void                 Filter(VkCommandBuffer commandBuffer);                                       // sections 4, 6
    VkDescriptorSet      AllocateSet(VkImageView read, VkImageLayout readLayout, VkSampler sampler,
                                     VkImageView write);
    void Dispatch(VkCommandBuffer commandBuffer, VkPipeline pipeline, VkDescriptorSet set,
                  const shared::IblFilterParameters& parameters, uint32_t layers = 6);
    void DestroyCube(IblCube& cube);

    VulkanContext   m_context;                          // copies of borrowed handles
    VkPipelineCache m_pipelineCache = VK_NULL_HANDLE;   // borrowed
    VkImageView     m_sky           = VK_NULL_HANDLE;   // borrowed: the Sky's cube
    VkSampler       m_skySampler    = VK_NULL_HANDLE;   // borrowed

    // Section 3: what the shaders sample, and the small copies of the sky the filter sums.
    IblCube       m_diffuse;                            // IBL_DIFFUSE_SIZE, one level: E / pi
    IblCube       m_specular;                           // IBL_SPECULAR_SIZE, IBL_SPECULAR_LEVELS levels
    IblCube       m_source;                             // IBL_SOURCE_SIZE, IBL_SOURCE_LEVELS levels, box-filtered
    VkImage       m_lut           = VK_NULL_HANDLE;     // section 7: IBL_LUT_SIZE squared, two numbers a texel
    VmaAllocation m_lutAllocation = VK_NULL_HANDLE;
    VkImageView   m_lutView       = VK_NULL_HANDLE;
    VkSampler     m_sampler       = VK_NULL_HANDLE;     // linear, between levels too; clamped

    // One set layout and one pipeline layout serve all three shaders: binding 0 what is read, binding 1
    // the image written, and IblFilterParameters as push constants.
    VkDescriptorSetLayout m_setLayout          = VK_NULL_HANDLE;
    VkDescriptorPool      m_pool               = VK_NULL_HANDLE;   // frees every set with it
    VkPipelineLayout      m_layout             = VK_NULL_HANDLE;
    VkPipeline            m_downsamplePipeline = VK_NULL_HANDLE;
    VkPipeline            m_convolvePipeline   = VK_NULL_HANDLE;
    VkPipeline            m_lutPipeline        = VK_NULL_HANDLE;

    VkDescriptorSet                                m_specularBaseSet = VK_NULL_HANDLE;   // sky -> specular level 0
    std::array<VkDescriptorSet, IBL_SOURCE_LEVELS> m_sourceSets{};                       // sky -> each source level
    VkDescriptorSet                                m_diffuseSet = VK_NULL_HANDLE;        // source -> diffuse
    std::array<VkDescriptorSet, IBL_SPECULAR_LEVELS> m_specularSets{};                   // source -> levels 1 to 4; [0] unused

    // Section 9: two timestamps around each filter, and what the last one measured.
    GpuTimestamps m_timestamps;
    float         m_lastMilliseconds = 0.0f;
};

} // namespace pf::vulkan_graphics
```

The files, and what each section adds:

```text
Shaders/Include/ImageBasedLightingTypes.h  the sizes, and the filter's push constants          sections 3, 4
Shaders/Sky/SkyDownsample.comp.glsl        small copies of the sky, by averaging               section 3
Shaders/Sky/SkyConvolve.comp.glsl          the weighted sums: diffuse, then specular           sections 4, 6
Shaders/Sky/SpecularLut.comp.glsl          the lookup table, once                              section 7
Shaders/Include/ImageBasedLighting.glsl    set 0's bindings 10-12, the ambient term            sections 4, 6, 8
VulkanGraphics/ImageBasedLighting.h/.cpp   the class above                                     sections 3, 4, 6, 7, 9
VulkanGraphics/GpuTimestamps.h/.cpp        timestamp queries, as a class                       section 9
VulkanGraphics/Sky.h/.cpp                  owns one; filters after each bake; Update takes     section 4
                                           the frame index
VulkanGraphics/SkySettings.h/.cpp          "Light the scene with the sky"                      section 4
VulkanGraphics/SceneRenderer.h/.cpp        set 0's bindings 10-12                              sections 4, 6
Shaders/Include/SharedShaderTypes.h        FrameData::ambientMode                              section 4
Shaders/Scene/Mesh.frag, GBuffer.frag      one line each                                       section 4
Demos/Meshes, SceneGraph, UsdViewer        bind the sky's light, and ask for it                sections 4, 9
Demos/Cubes, Particles                     pass the frame index to the sky                     section 4
```

> **Jump:** until now a surface's light came from a list of lights, each from
> one direction, plus one constant for "everything else". From here,
> everything else is a whole sky, a different color in every direction. A
> shader cannot add up a whole sky for every pixel, so the adding is done ahead
> of time, once per way a surface can face, and stored in a cube. What a pixel
> does is look up its answer by direction, as Chapter 23's sky did: by the
> normal for the matte part of its light, and by the mirror direction for the
> shiny part. Keep that split in mind: everything in this chapter is either
> adding up the sky ahead of time, or looking the answer up.

---

# Part 1 — Light from the whole sky (sections 1-4)

Part 1 lights matte surfaces with the sky: the theory, the class, the small
copies of the sky the sums read, the diffuse cube, and the switch that lets
the mesh shaders use it. Part 2 adds reflections.

## 1. Why one ambient color is wrong

**This section has no code.** It says what Chapter 16's ambient light gets
wrong, and what to compute instead.

Chapter 16 section 2 lit a surface under a dome of radiance *L* with an
irradiance of π*L*. Every direction above the surface sends the same *L*, each
arriving at its own slant, and the cosine-weighted sum over the half of the sky
above a surface is π. Dividing by π, the white surface reflects *L*, and that
*L* became the ambient color. For a dome that is the same brightness in every
direction this is exact. For an image it is not: Chapter 16 used the image's
average, as if the sky were one color.

A real sky is not one color. Take a simple one: a blue sky above, dark ground
below, and a sunset low down on one side.

```text
                 blue sky above: (0.10, 0.20, 0.40)
               .-----------------------------.
             /                                 \
   horizon  |  sunset: a patch of 0.2 sr, just  |
   ---------|  above the horizon toward +X,     |---------
            |  (3.0, 1.2, 0.3)                  |
             \                                 /
               '-----------------------------'
                 dark ground below: (0.04, 0.03, 0.02)
```

A floor sees only the upper half: blue sky, and the sunset at a grazing angle
where its cosine is small. The underside of a ball sees only the ground. A wall
facing the sunset sees half sky, half ground, and the sunset head-on. Adding up
what each one receives gives these numbers, written as Chapter 16's ambient
color would be, the light divided by π:

| Surface | What it receives, ÷ π | The flat average |
| --- | --- | --- |
| A floor, facing up | (0.12, 0.21, 0.40): blue | (0.12, 0.13, 0.21) for every surface |
| The underside of a ball | (0.04, 0.03, 0.02): almost nothing | |
| A wall facing the sunset | (0.25, 0.18, 0.20): warm | |
| A wall facing away | (0.07, 0.12, 0.21): cool | |

The flat average gets every surface wrong. The floor should be twice as blue,
the underside of the ball should be about a quarter as bright, and a wall facing
the sunset should be warm while the one facing away should be cool. The
average loses direction, and direction is most of what makes outdoor light look
like outdoor light.

**The sum, in words:** the light arriving on a surface facing a direction **n**
is the light from every direction **l** above it, each weighted by the cosine of
its angle to **n**, which is Chapter 11's Lambert slant. (Directions are bold
lowercase letters, as in Chapter 15 section 9; *L* is always radiance.) Each
direction counts in proportion to the small patch of sky it covers, its solid
angle d*ω*. As an equation:

$$
E(\mathbf{n}) = \int_{\text{sky}} L(\mathbf{l})\, \max(\mathbf{n} \cdot \mathbf{l},\ 0)\, d\omega
$$

Two symbols here are new to this tutorial. **Σ** (a capital Greek sigma)
means "add up the term after it, once for every piece": Σ over the six faces
of a cube is six terms added together. **∫** is the same thing when the pieces
are infinitely many and infinitely small, and d*ω* is the size of one piece,
here a tiny patch of sky. So the equation reads: for every direction **l** in the
sky, take its radiance, times its cosine, times the size of its patch, and add
them all up. The `max` drops the directions behind the surface. Under a sky of
one radiance *L* it gives π*L*, Chapter 16's answer. **Worked:** the floor
above. The blue sky
covers the upper half, so it contributes π × (0.10, 0.20, 0.40). The sunset
patch covers 0.2 steradians, arriving 5° above the horizon, where the cosine is
0.087, so it adds about (3.0, 1.2, 0.3) × 0.2 × 0.087 = (0.05, 0.02, 0.005),
minus the blue sky it hides. Divided by π, that is the table's
(0.12, 0.21, 0.40).

The cosine is the BRDF's business, not the sky's: a Lambert surface reflects
`albedo / π × E(n)`. Divided by π, *E* becomes a radiance, the one a sky of a
single color would need to deliver the same light. That is the number Chapter
16 called the ambient color, so this chapter stores **E / π** for every **n**. A
shader that used to multiply by the ambient color multiplies by a lookup
instead, and under a one-color sky the two agree exactly.

---

## 2. Adding up a sky, texel by texel

**This is the sum the diffuse cube is filled with, written so a computer can
do it.**

A sky in a cube is a finite list of texels, each a little patch of directions
with one radiance. The integral becomes a sum over them:

$$
E(\mathbf{n}) \approx \sum_{\text{texels } i} L_i\, \max(\mathbf{n} \cdot \mathbf{l}_i,\ 0)\, \Delta\omega_i
$$

where **l**ᵢ is the direction through texel *i*'s centre and Δωᵢ is its solid
angle, the size of the patch of sky it covers. Chapter 23 section 2 gives the
direction. The solid angle is the one new piece.

**A cube texel's solid angle.** Chapter 16 section 2's ball covered its
silhouette's area divided by its distance squared. A texel is a small square on
a face of the cube, and the cube runs from −1 to 1, so a face is 2 units wide
and a texel of an *M* × *M* face has area (2/*M*)². Two things shrink what it
covers, seen from the centre:

- **Its distance** *d*. The face's centre is 1 away; a corner is √3 away. For
  a texel at position (*u*, *v*) on the face, *d*² = 1 + *u*² + *v*².
- **Its slant.** Away from the face's centre, the line of sight meets the face
  at an angle, so the texel is seen edge-on a little, and looks smaller by the
  cosine of that angle, as a slanted beam spreads out in Chapter 11. That
  cosine is 1/*d*, the face's distance (1) over the texel's.

```text
            texel, area (2/M)^2, tilted by the angle a
               |\
               | \  <- seen from the centre it looks (2/M)^2 cos(a) big,
               |  \    and it is d away
       centre  *-------- face, 1 unit from the centre
                \  a
                 \
                  \ d = sqrt(1 + u^2 + v^2),  cos(a) = 1 / d
```

So the texel covers area × cos / *d*², which is

$$
\Delta\omega = \frac{(2/M)^2}{d^{\,3}}, \qquad d^2 = 1 + u^2 + v^2
$$

**Worked, on a 16 × 16 face.** The area is (2/16)² = 0.0156. A texel at the
middle of the face has *d* ≈ 1 and covers 0.0154 steradians. The corner texel,
centred at *u* = *v* = 0.9375, has *d*² = 2.76, *d*³ = 4.58, and covers
0.0034 steradians, under a quarter as much. The whole cube must cover the
whole sphere of directions, 4π = 12.566 steradians, and adding up all
6 × 16 × 16 texels' Δω gives 12.578: within 0.1%.

**How large a copy of the sky.** The sum touches every texel of the sky for
every direction it is computed for, so its cost is (directions written) ×
(texels read). Chapter 23's sky has 6 × 512 × 512 = 1.6 million texels. Light
from a whole half of the sky changes slowly with direction, so the sum can read
a much smaller copy of it: 16 × 16 per face, 1536 texels, each the average of a
32 × 32 block of the sky's. Averaging keeps every bit of light: a sun in a
photograph that covers four sky texels becomes a quarter of one small texel,
with the same total, so it still lights the scene as much. The diffuse cube
itself is 32 × 32 per face, 6144 directions, so the sum is 6144 × 1536 = 9.4
million terms. Even a slow GPU does that in well under a millisecond.

**How exact.** On `SkyTest.usda` (Chapter 23 section 10), whose sky is
`0.5 + 0.5 d` in every direction *d*, the exact answer is known: worked out
with calculus (not needed here), the light on a surface facing **n**, divided by
π, is `0.5 + n / 3`. Facing up, that is (0.5, 0.833, 0.5). The 16 × 16 sum
gives (0.501, 0.835, 0.501).

**The other route.** Most engines store diffuse light as nine numbers per
color, *spherical harmonics*, instead of a cube: far smaller, but a page of
formulas to build, and faint rings of too much and too little light around a
bright sun. Ramamoorthi and Hanrahan's paper (Sources) is where to go for it.

---

## 3. The class, its images, and a smaller sky

**This is `ImageBasedLighting::Initialize`, `CreateCube`, and
`SkyDownsample.comp.glsl`.**

**The images.** Four, all half floats like the sky, so they hold the same HDR
radiance in the same units:

| Image | Faces | Levels | Holds | Read by |
| --- | --- | --- | --- | --- |
| diffuse cube | 32 × 32 | 1 | E / π for every way a surface can face | the mesh shaders: set 0, binding 10 |
| source chain | 32, 16, 8, 4 | 4 | the sky, each texel the average of the sky texels it covers | the sums, this section and section 6 |
| specular cube | 128 down to 8 | 5 | the sky blurred for roughness 0, 0.25, 0.5, 0.75, 1 | the mesh shaders: binding 11 (section 6) |
| lookup table | 64 × 64, not a cube | 1 | GGX's share of the sky it reflects (section 7) | the mesh shaders: binding 12 |

Together they are about 1.2 MB, a tenth of the sky's cube. The sizes are
constants in a header both languages include, `ImageBasedLightingTypes.h`,
beside the filter's push constants (whole in Appendix A).

`ImageBasedLighting.cpp` includes `ImageBasedLighting.h`,
`PillowFort/VulkanGraphics/GraphicsPipeline.h` (`createComputePipeline`,
`groupCount`), `PillowFort/VulkanGraphics/VulkanBarriers.h`, `"SkyTypes.h"`
(Chapter 23's `SKY_FACE_SIZE`), `<array>`, `<format>`, and `<string>`.

**This is `Initialize`.** It follows `Sky::Initialize`'s shape: copy the
borrowed handles, then one function per group of objects. Part 1 writes all of
it but the lines marked for sections 6, 7, and 9; until Part 2, `Initialize`
ends with `CreateSets` and `return InitializationResult::success();`.

```cpp
InitializationResult ImageBasedLighting::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                                    VkImageView sky, VkSampler skySampler)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    m_sky           = sky;
    m_skySampler    = skySampler;

    // Section 3: the cube the diffuse light is summed into, and the small copies of the sky it reads. The
    // copies are read texel by texel with texelFetch, which takes no direction, so their readers see six
    // layers (a 2D array); the cubes the mesh shaders sample are seen as cubes.
    if (auto result = CreateCube(m_diffuse, IBL_DIFFUSE_SIZE, 1, VK_IMAGE_VIEW_TYPE_CUBE, "diffuse"); !result)
    {
        return result;
    }
    if (auto result = CreateCube(m_source, IBL_SOURCE_SIZE, IBL_SOURCE_LEVELS, VK_IMAGE_VIEW_TYPE_2D_ARRAY, "source");
        !result)
    {
        return result;
    }
    // Section 6: the specular cube, a level per roughness.
    if (auto result = CreateCube(m_specular, IBL_SPECULAR_SIZE, IBL_SPECULAR_LEVELS, VK_IMAGE_VIEW_TYPE_CUBE, "specular");
        !result)
    {
        return result;
    }
    if (auto result = CreatePipelines(); !result)  { return result; }   // section 3
    if (auto result = CreateSets(); !result)       { return result; }   // sections 3 and 6
    if (auto result = CreateLut(); !result)        { return result; }   // section 7
    if (auto result = ComputeLut(); !result)       { return result; }   // section 7: once, and never again
    return m_timestamps.Initialize(m_context, 2);                      // section 9: before and after a filter
}
```

The two handles at the top are the sky's cube and its sampler, which the
filter reads. `Sky::Initialize` passes them, right after it makes them
(section 4).

**This is `CreateCube`.** Each of the three cubes is one image with six layers
and some mip levels, as Chapter 23's cube was, with two kinds of view:

- **One view of every level, for reading.** The mesh shaders read the
  diffuse and specular cubes by direction, so their view is a `CUBE`. The
  sums read the source chain one texel at a time, by face and position, with
  `texelFetch`, which takes integer coordinates, not a direction; a cube view
  cannot be read that way, so the source chain is viewed as a `2D_ARRAY` of
  six layers.
- **One view per level, for writing.** A storage image names exactly one mip
  level, so each level the filter writes has a `CUBE` view of its own. As in
  Chapter 23, a cube view used as a storage image is an `imageCube`, written
  with the face as the third coordinate.

The image itself is Chapter 23's cube with `mipLevels = levels` (Appendix A has
the whole function). After it come the views, then Chapter 23 section 3's rule
for any image a set names: it starts readable, with nothing in it until the
first filter.

```cpp
    // The view its readers sample, every level.
    VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = cube.image,
        .viewType         = sampledType,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, 6 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &cube.sampled) != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vkCreateImageView failed for the sky's {} cube.", name));
    }

    // One view per level for the filter to write: a storage image names exactly one mip level.
    viewInfo.viewType = VK_IMAGE_VIEW_TYPE_CUBE;
    for (uint32_t level = 0; level < levels; ++level)
    {
        viewInfo.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, level, 1, 0, 6 };
        if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &cube.levels[level]) != VK_SUCCESS)
        {
            return InitializationResult::failure(std::format("vkCreateImageView failed for a level of the sky's {} cube.", name));
        }
    }

    // Readable from the start, like the sky's own cube (Chapter 23 section 3): set 0 names these images in
    // every demo that draws meshes, while the sky is off and nothing has been filtered, and validation
    // checks the layout of every image a pipeline's sets name. The contents mean something after a Filter.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, cube.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    return InitializationResult::success();
}
```

**The downsample.** The source chain is made by averaging. Each texel of a
small copy covers a block of sky texels: a 32 × 32 face covers the sky's
512 × 512 in blocks of 16 × 16. Reading 256 texels one at a time would work,
but linear filtering does part of it for free: a lookup exactly on the corner
four sky texels share returns their average. So a block of 16 × 16 needs only
8 × 8 lookups, each at the corner of its own 2 × 2 group. In general a texel
of a face of size *S* covers 512/*S* sky texels along each side and needs
`taps` = 512 / (2*S*) lookups along each side:

```text
  one texel of the small copy, over 4 x 4 sky texels (taps = 2):
  +----+----+----+----+
  |    |    |    |    |
  +----X----+----X----+     X: a lookup on the corner four sky texels share.
  |    |    |    |    |        Linear filtering returns their average;
  +----+----+----+----+        the four lookups together average all sixteen.
  |    |    |    |    |
  +----X----+----X----+
  |    |    |    |    |
  +----+----+----+----+
```

**Worked:** the source chain's 4 × 4 level has `taps` = 512 / 8 = 64, so each
of its 96 texels makes 64 × 64 = 4096 lookups, and averages a 128 × 128 block
of the sky. A lookup is placed by direction, with Chapter 23's
`cubeTexelDirection`, at a fraction of the way across the small texel, so it
lands exactly on the corner the sky texels share:

```glsl
// Shaders/Sky/SkyDownsample.comp.glsl - Chapter 24: a smaller copy of the sky, each texel the average of every
// sky texel it covers. One invocation per texel written; the dispatch's z is the face.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "CubeMap.glsl"                  // cubeTexelDirection
#include "ImageBasedLightingTypes.h"     // IblFilterParameters, IBL_GROUP_SIZE

layout(local_size_x = IBL_GROUP_SIZE, local_size_y = IBL_GROUP_SIZE, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform samplerCube sky;                           // Chapter 23's cube
layout(set = 0, binding = 1, rgba16f) uniform writeonly imageCube destination;   // one level of a smaller cube

layout(push_constant) uniform FilterBlock
{
    IblFilterParameters ibl;
};

void main()
{
    ivec3 texel = ivec3(gl_GlobalInvocationID);   // x and y across one face; z which face
    if (texel.x >= int(ibl.size) || texel.y >= int(ibl.size)) { return; }

    // Section 3: taps x taps lookups spread evenly over the texel. Each lands on the corner four sky texels
    // share, where linear filtering averages those four, so together they average every sky texel inside.
    vec3 sum = vec3(0.0);
    for (uint j = 0u; j < ibl.taps; ++j)
    {
        for (uint i = 0u; i < ibl.taps; ++i)
        {
            vec2 uv = (vec2(texel.xy) + (vec2(i, j) + 0.5) / float(ibl.taps)) / float(ibl.size);
            sum += textureLod(sky, cubeTexelDirection(uint(texel.z), uv), 0.0).rgb;
        }
    }
    imageStore(destination, texel, vec4(sum / float(ibl.taps * ibl.taps), 1.0));
}
```

The filter's three shaders share one descriptor set layout — binding 0 what is
read, binding 1 the image written — one pipeline layout with
`IblFilterParameters` as push constants, and one pool, sized for every set the
chapter makes. A pool is counted by layout: every set takes one descriptor of
each binding, the lookup table's too, though its binding 0 is never written.
`CreatePipelines` and `CreateSets` are Chapter 20's pattern
again and are in Appendix A. `CreateSets` gives every dispatch a set of its
own, because each reads and writes a different pair of images: the four
downsamples read the sky's cube with the sky's sampler, and the diffuse sum
reads the source chain:

```cpp
    constexpr VkImageLayout readOnly = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    for (uint32_t level = 0; level < IBL_SOURCE_LEVELS; ++level)
    {
        m_sourceSets[level] = AllocateSet(m_sky, readOnly, m_skySampler, m_source.levels[level]);
    }
    m_diffuseSet = AllocateSet(m_source.sampled, readOnly, m_sampler, m_diffuse.levels[0]);
```

`AllocateSet` (Appendix A) allocates one set and writes its two bindings: the
image read, in `SHADER_READ_ONLY_OPTIMAL`, and the image written, in
`GENERAL`, the layout a storage image is written in.

---

## 4. The diffuse cube, and the switch

**This is `SkyConvolve.comp.glsl`, `Filter`, the sky's part, set 0's binding
10, `FrameData::ambientMode`, and the ambient term in the mesh shaders.**

### The sum

`SkyConvolve` is section 2's sum, one invocation per texel of the diffuse
cube. Each invocation turns its texel into the direction **n** a surface faces,
then walks every texel of the 16 × 16 source level: its direction **l**, its
solid angle, the cosine, and the radiance. The two lines inside
`if (ibl.kind == IBL_KIND_SPECULAR)` are section 6's, and Part 1 never asks for
them:

```glsl
// Shaders/Sky/SkyConvolve.comp.glsl - Chapter 24: the sky's light, as a weighted sum over every texel of a small
// copy of the sky. For the diffuse cube each texel weighs its solid angle times the cosine (section 2); for a
// specular level, times GGX's D as well (section 6). One invocation per texel written; z is the face.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "CubeMap.glsl"                  // CUBE_FACE_CENTRE, _RIGHT, _DOWN; cubeTexelDirection
#include "ImageBasedLightingTypes.h"     // IblFilterParameters, IBL_KIND_*
#include "PreviewSurface.glsl"           // PI, ggxDistribution (Chapter 15 section 9)

layout(local_size_x = IBL_GROUP_SIZE, local_size_y = IBL_GROUP_SIZE, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2DArray source;                     // the box-filtered chain: x, y, face
layout(set = 0, binding = 1, rgba16f) uniform writeonly imageCube destination;   // the diffuse cube, or one level

layout(push_constant) uniform FilterBlock
{
    IblFilterParameters ibl;
};

void main()
{
    ivec3 texel = ivec3(gl_GlobalInvocationID);
    if (texel.x >= int(ibl.size) || texel.y >= int(ibl.size)) { return; }

    // The direction this texel stands for: the way a surface faces (diffuse), or the mirror direction R
    // around which a rough reflection gathers (specular, with N = V = R: section 5's simplification).
    vec3  N     = cubeTexelDirection(uint(texel.z), (vec2(texel.xy) + 0.5) / float(ibl.size));
    float alpha = ibl.roughness * ibl.roughness;

    // Section 2: one source texel's area on its face, which runs -1 to 1. Seen from the centre it covers that
    // area, shrunk by its distance squared and by the cosine of its slant: area / d^3 in all.
    float texelArea = (2.0 / float(ibl.sourceSize)) * (2.0 / float(ibl.sourceSize));

    vec3  sum         = vec3(0.0);
    float totalWeight = 0.0;
    for (uint face = 0u; face < 6u; ++face)
    {
        for (uint y = 0u; y < ibl.sourceSize; ++y)
        {
            for (uint x = 0u; x < ibl.sourceSize; ++x)
            {
                vec2  p           = (vec2(x, y) + 0.5) / float(ibl.sourceSize) * 2.0 - 1.0;   // -1 to 1 across the face
                vec3  onFace      = CUBE_FACE_CENTRE[face] + p.x * CUBE_FACE_RIGHT[face] + p.y * CUBE_FACE_DOWN[face];
                float d2          = dot(onFace, onFace);                                       // distance squared
                vec3  L           = onFace * inversesqrt(d2);
                float NdotL       = dot(N, L);
                if (NdotL <= 0.0) { continue; }                                                // behind the surface

                float solidAngle = texelArea / (d2 * sqrt(d2));
                float weight     = solidAngle * NdotL;
                if (ibl.kind == IBL_KIND_SPECULAR)
                {
                    weight *= ggxDistribution(dot(N, normalize(N + L)), alpha);   // how much of the lobe points here
                }
                sum         += weight * texelFetch(source, ivec3(x, y, face), int(ibl.sourceLevel)).rgb;
                totalWeight += weight;
            }
        }
    }

    // Diffuse: the sum is the irradiance E; the cube keeps E / pi, the radiance of an even sky that would
    // deliver it, which is what Chapter 16's ambient color meant. Specular: an average, weighted by the lobe.
    vec3 result = ibl.kind == IBL_KIND_DIFFUSE ? sum / PI : sum / max(totalWeight, 1e-20);
    imageStore(destination, texel, vec4(result, 1.0));
}
```

The direction and the solid angle are computed together: the point `onFace`
on the cube's surface is *d* away from the centre, so normalizing it gives **l**,
and the same *d*² gives Δω. `texelFetch` reads one texel of one level, with no
filtering, and the level is a push constant: 1, the 16 × 16 one.

### `Filter`, first version

`Filter` runs right after the sky is baked. It downsamples the sky into the
source chain, then sums the diffuse cube from it, with three barriers:

```cpp
void ImageBasedLighting::Filter(VkCommandBuffer commandBuffer)
{
    // Before: a write after a read. Last frame's draws sampled the diffuse cube, perhaps still running; the
    // last Filter's sums sampled the source chain. Every texel is written again, so UNDEFINED.
    for (const VkImage image : { m_source.image, m_diffuse.image })
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }

    // Section 3: the four small copies the sums read, each straight from the sky. Each dispatch writes its
    // own level and reads only the sky, so none waits for another: no barrier between them.
    for (uint32_t level = 0; level < IBL_SOURCE_LEVELS; ++level)
    {
        const uint32_t size = IBL_SOURCE_SIZE >> level;   // 32, 16, 8, 4
        Dispatch(commandBuffer, m_downsamplePipeline, m_sourceSets[level], { .size = size, .taps = SKY_FACE_SIZE / (2 * size) });
    }

    // Between: a read after a write. The sums below sample what the downsamples just wrote.
    transitionImage(commandBuffer, m_source.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    // Section 4: the diffuse cube, summed over the 16 x 16 source level.
    Dispatch(commandBuffer, m_convolvePipeline, m_diffuseSet,
             { .size = IBL_DIFFUSE_SIZE, .sourceSize = IBL_SOURCE_SIZE >> 1, .sourceLevel = 1, .kind = IBL_KIND_DIFFUSE });

    // After: a read after a write. The mesh shaders sample the diffuse cube in their fragment stage; a later
    // chapter's compute shader may too.
    for (const VkImage image : { m_diffuse.image })
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
}
```

The two lists are loops because section 6 adds the specular cube to both.
`Dispatch` (Appendix A) binds a pipeline and a set, pushes the parameters, and
dispatches one invocation per texel of the face size it is given, with *z*
covering the six faces.

The three barriers, through Chapter 04 section 5's three questions:

| | Q1: what finishes, then what waits | Q2: flushed, then made visible | Q3: layout |
| --- | --- | --- | --- |
| Before | Whatever read these images last: the mesh shaders' fragment stage, last frame's draws perhaps still running, for the diffuse cube; the last `Filter`'s sums, compute, for the source chain. Then the downsamples and sums (`COMPUTE_SHADER`) | Reads leave nothing to flush: `NONE`; then `SHADER_STORAGE_WRITE` | `UNDEFINED` to `GENERAL`: every texel is written again |
| Between | The downsamples' writes (`COMPUTE_SHADER`), then the sums that read them (`COMPUTE_SHADER`) | `SHADER_STORAGE_WRITE`; then `SHADER_SAMPLED_READ` | The source chain, `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |
| After | The diffuse sum's writes, then every reader: the mesh shaders' fragment stage, and a later chapter's compute shader | `SHADER_STORAGE_WRITE`; then `SHADER_SAMPLED_READ` | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` |

The downsamples read the sky's cube, and the sky's own second barrier
(Chapter 23 section 7) already made the bake's writes visible to compute
shaders, which is why Chapter 23 put `COMPUTE_SHADER` there. And the next bake
waits for these reads, because the sky's first barrier lists `COMPUTE_SHADER`
as a source.

**The first barrier's `FRAGMENT_SHADER` is there twice over.** The sky's own
first barrier, just before the bake, already makes every earlier fragment
shader finish before the compute stage, and this barrier's compute source
*chains* onto it (Chapter 21 section 5), so removing it here would still be
correct, and validation could not tell. It stays: `Filter` should be right on
its own, whatever its caller recorded before it.

### The sky's part

`Sky` owns one `ImageBasedLighting`, beside its cube (`Sky.h`, after
`m_cubeSampler`, with `#include "PillowFort/VulkanGraphics/ImageBasedLighting.h"`
after `Light.h`):

```cpp
    ImageBasedLighting m_lighting;                     // Chapter 24: the cube, filtered for the mesh shaders
```

and hands it out, after `DrawInOwnPass`:

```cpp
    // Chapter 24: the sky's light, filtered from the cube every time it is baked, for set 0's bindings
    // 10-12. From Initialize on its images are readable; once the sky is on and Update has run, they hold
    // the light of the sky as it is now.
    const ImageBasedLighting& Lighting() const { return m_lighting; }
```

`Sky::Initialize` creates it right after the cube, because it reads the cube:

```cpp
    if (auto result = m_lighting.Initialize(m_context, m_pipelineCache, m_cubeView, m_cubeSampler); !result)
    {
        return result;   // Chapter 24: it reads the cube, so it comes right after it
    }
```

`Sky::Update` calls the light's `Update` right after its `if (changed)` block,
every frame the sky is on, and tells it whether the sky was just baked:

```cpp
    // Chapter 24: the sky's light, filtered again from the sky just baked - and only then.
    m_lighting.Update(commandBuffer, frameIndex, changed);
```

That is the whole of "refilter when the sky changes": the bake already runs
only on a change, so the filter does too. Why a call every frame, rather than a
`Filter` inside the `if`? Section 9 times the filter, and reads the timing back
a frame or two later, in the same frame slot, so it needs a call on those
frames, and needs to know which frame slot is being recorded: the `frameIndex`
every demo's `Record` is handed. `Sky::Update` is not told it yet, so it gains
it as its second parameter, in `Sky.h` and `Sky.cpp`:

```cpp
    void Update(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SkySettings& settings,
                const SkyInputs& inputs);
```

and each of the five demos with a sky passes its own as the second argument of
its `m_sky.Update` call; in Meshes:

```cpp
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
```

Until section 9, `Update` is two lines, and leaves the frame index unnamed,
which is how C++ says "not used yet" without a warning:

```cpp
void ImageBasedLighting::Update(VkCommandBuffer commandBuffer, uint32_t /* frameIndex: section 9 */, bool skyBaked)
{
    if (!skyBaked) { return; }   // the cubes still hold this sky's light
    Filter(commandBuffer);
}
```

And `Sky::Shutdown` shuts it down just before it destroys the cube's view:

```cpp
    m_lighting.Shutdown();   // Chapter 24: its sets point at the cube, so before the cube goes
```

### Set 0, binding 10

The mesh shaders read set 0, so the diffuse cube joins it. The numbering
starts at 10, not 5, because of Chapter 22: its lighting set reuses set 0's
numbers for the buffers they share, so that `FrameBlock.glsl` and its siblings
work unchanged in its compute shader, and it puts its own images at 5 to 9. Set
0's new bindings take numbers the lighting set does not use, so every number
still means one thing in both sets. A layout may skip numbers.

In `SceneRenderer::CreateFrameResources`, the binding joins the array after
Chapter 17's binding 4 (sections 6 and 7 add 11 and 12 below it), and the pool
gains room for all three:

```cpp
        // Chapter 24: the sky's light - the diffuse cube, the specular cube, the lookup table. Numbered from
        // 10 so that no number means one thing here and another in Chapter 22's lighting set (5 to 9).
        { .binding = 10, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT },
```

```cpp
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 3 * FRAMES_IN_FLIGHT },   // Chapter 24: bindings 10-12
```

The images belong to the sky, which `SceneRenderer` does not know about, so a
demo connects the two in `Setup`. `SetImageBasedLighting` (declared in
`SceneRenderer.h` after `WriteLights`, which gains
`#include "PillowFort/VulkanGraphics/ImageBasedLighting.h"`) writes the
binding in every frame in flight's set. Its first version:

```cpp
// Chapter 24: set 0's bindings 10, 11, and 12, in every frame in flight's set. In Setup, after Initialize
// and after the sky's: they never change afterwards, because Filter rewrites the images, not the views.
void SceneRenderer::SetImageBasedLighting(const ImageBasedLighting& lighting)
{
    const VkDescriptorImageInfo diffuse  = lighting.DiffuseInfo();
    for (const VkDescriptorSet set : m_frameSets)
    {
        const VkWriteDescriptorSet writes[] = {
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 10, .descriptorCount = 1,
              .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &diffuse },
        };
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(std::size(writes)), writes, 0, nullptr);
    }
}
```

`DiffuseInfo` returns the cube's sampled view, the class's linear sampler, and
`SHADER_READ_ONLY_OPTIMAL`, the layout `Filter` leaves it in (Appendix A).

**Every demo that draws meshes must call it**, because the mesh shader names
binding 10 whether or not the sky is on, and validation requires every
descriptor a pipeline names to be written. Meshes, the scene graph, and the
USD viewer call it in `Setup`, right after the sky's `Initialize`; so do the
grass chapters' `Setup`, whose stones are drawn with the mesh pipelines:

```cpp
    m_sceneRenderer.SetImageBasedLighting(m_sky.Lighting());   // Chapter 24: set 0's bindings 10-12
```

### The switch

Which ambient light a pixel gets is decided once per frame, so it goes where
Chapter 15's BRDF switch went: `FrameData`. It grows only at its end
(Chapter 10 section 7), and the new field is padded to a whole 16 bytes, so the
size check becomes 368. In `SharedShaderTypes.h`, after Chapter 22's
`inverseViewProjection`:

```c
    /* Chapter 24: the ambient light's source, the same for every pixel. */
    uint  ambientMode;      /* 352  AMBIENT_*; 0 is Chapter 16's constant */
    uint  padding5;         /* 356  keeps the size a multiple of 16 */
    uint  padding6;         /* 360 */
    uint  padding7;         /* 364 */
```

with its values beside Chapter 15's `BRDF_*`, zero for the old behavior so a
demo that never mentions it is unchanged:

```c
/* Chapter 24: FrameData::ambientMode, where the light from everywhere at once comes from. 0 is Chapter 16's
   constant, so a demo that never mentions it draws exactly as before. */
#define AMBIENT_FLAT 0u
#define AMBIENT_SKY  1u
```

and the size checks:

```c
    static_assert(sizeof(FrameData) == 368, "FrameData layout drifted.");
```

```c
    static_assert(offsetof(FrameData, ambientMode) == 352, "FrameData alignment drifted.");
```

**The setting** is the engine's, like the sky's mode: a checkbox in the Sky
section, on by default, so that turning a sky on lights the scene with it. In
`SkySettings`, after `mode`:

```cpp
    bool    lightsScene   = true;   // Chapter 24: the sky, not one constant, is the scene's ambient light
```

in `drawSkyPanel`, after the mode's combo:

```cpp
        changed |= ImGui::Checkbox("Light the scene with the sky", &settings.lightsScene);   // Chapter 24
```

and, after `drawSkyPanel`'s declaration, the rule every demo applies: the sky
lights the scene when it is asked to and there is a sky.

```cpp
// Chapter 24: whether the scene's ambient light comes from the sky - asked for, and a sky to give it.
// A demo turns the answer into FrameData::ambientMode.
inline bool skyLightsScene(const SkySettings& settings)
{
    return settings.lightsScene && settings.mode != SkyMode::Off;
}
```

A demo turns that into `FrameData`. Meshes and the scene graph, after
`frameData.ambientColor`, and the USD viewer, after Chapter 22's
`inverseViewProjection`:

```cpp
    frameData.ambientMode    = vulkan_graphics::skyLightsScene(frame.sky) ? AMBIENT_SKY : AMBIENT_FLAT;   // Chapter 24
```

### The shader side

The three bindings and the code that reads them go in an include of their
own, `ImageBasedLighting.glsl`, and not in Chapter 15's `PreviewSurface.glsl`.
That file is pure functions, and two shaders include it that must not see set
0's new bindings: Chapter 22's lighting pass, whose set 0 is its own, and the
grass, whose shaders declare only the one binding they read (Chapter 25
section 8). The include's first version:

```glsl
// Shaders/Include/ImageBasedLighting.glsl - Chapter 24. Set 0's bindings 10-12, the sky's light, and the
// ambient term that reads them. Included by the two shaders that shade a material: Mesh.frag.glsl and
// GBuffer.frag.glsl. Never compiled on its own.
#ifndef PF_IMAGE_BASED_LIGHTING_GLSL
#define PF_IMAGE_BASED_LIGHTING_GLSL

#include "ImageBasedLightingTypes.h"   // IBL_SPECULAR_LEVELS
#include "PreviewSurface.glsl"         // SurfaceSample, fresnelEndpoints, schlickFresnel, evaluateAmbient

layout(set = 0, binding = 10) uniform samplerCube skyDiffuse;    // E / pi, for each way a surface can face

vec3 evaluateSkyAmbient(SurfaceSample s, vec3 N, vec3 V, float occlusion)
{
    vec3 diffuseLight = texture(skyDiffuse, N).rgb;   // E / pi from the hemisphere around N (section 1)

    // (a) Lambert: what a white matte surface would show, tinted by the albedo. No reflection at its surface.
    if (s.brdf == BRDF_LAMBERT) { return diffuseLight * occlusion * s.baseColor; }

    // Until section 8: Chapter 15's flat formula, with the sky's light for the surface's normal in place
    // of the one constant.
    return evaluateAmbient(s, diffuseLight, occlusion);
}
```

Lambert's line is the whole of the matte case: the cube holds E/π, and a
Lambert surface reflects albedo × E/π, exactly as it reflected albedo × the
ambient color before. The other two BRDFs need reflections, which Part 2 adds;
until then they use Chapter 15's formula with the looked-up light.

**The switch** is one function after it, and the include's last:

```glsl
// Section 4: the ambient term, by the frame's choice. AMBIENT_FLAT is Chapter 16's constant, through Chapter
// 15's evaluateAmbient, unchanged; AMBIENT_SKY is the sky. `mode` is FrameData's, the same for every pixel.
vec3 evaluateAmbientLight(SurfaceSample s, vec3 N, vec3 V, vec3 flatAmbient, float occlusion, uint mode)
{
    if (mode == AMBIENT_SKY) { return evaluateSkyAmbient(s, N, V, occlusion); }
    return evaluateAmbient(s, flatAmbient, occlusion);
}

#endif
```

Chapter 15's `evaluateAmbient` stays as it was, and is still what
`AMBIENT_FLAT` runs. Like the BRDF switch, the mode is the same for every pixel,
so the branch costs one comparison (Chapter 15 section 9).

**Both paths.** Two shaders add the ambient light: the forward mesh shader,
and on Chapter 22's deferred path the G-buffer pass, which writes "the light
that needs no light list" into the scene target before the lighting pass adds
the rest (Chapter 22 section 2). The sky's light needs no list either, so it
goes in the same place, and the lighting pass does not change at all; that is
lucky as well as tidy, because the G-buffer does not store occlusion, which
the ambient light needs. Each shader includes the file after its other
includes:

```glsl
#include "ImageBasedLighting.glsl"   // Chapter 24: set 0 bindings 10-12, evaluateAmbientLight
```

and its ambient line becomes a call to the switch. In `Mesh.frag.glsl`, `V` is
already there:

```glsl
    vec3 color = evaluateAmbientLight(s, N, V, lightHeader.ambient.rgb, occlusion, frame.ambientMode) + emissive;   // Chapter 24
```

In `GBuffer.frag.glsl` it is not, so it is computed first, the way the lighting
pass computes it:

```glsl
    vec3 V     = normalize(frame.cameraPosition.xyz - worldPosition);   // Chapter 24: the sky's light needs the eye
    vec3 color = evaluateAmbientLight(s, N, V, lightHeader.ambient.rgb, occlusion, frame.ambientMode) + emissive;
```

## Checkpoint

Rerun `GenerateProjects.bat` — the class, two shaders, and two includes are
new — and build. In the USD viewer, open `SkyTest.usda`, set the Sky's mode to
**Environment**, the BRDF to **Lambert**, and the tone mapping to Raw at 0
stops.

- **The floor** reads (169, 213, 169): the 0.8 albedo a prim gets without a
  material, times E/π = (0.5, 0.833, 0.5), section 2's exact answer for a
  surface facing up under this sky. Read each channel as within 1. A 0.4 on
  its own displays as 169.6, but these do not land on 0.4 exactly: section
  2's sum gives 0.501 for 0.5, and `make_sky_test.py` cuts each RGBE mantissa
  down (`int()`), leaving the sky about 1/512 under `0.5 + 0.5 d`. Together
  they put every 0.4 here at about 169.5, on the line between 169 and 170, so
  a GPU may read 170 where this says 169.
- **The box**: its front face, facing +Z, reads (169, 169, 213), and its
  left face, facing −X, (102, 169, 169), which is 0.8 × (0.5 − 1/3) in red.
  The ball is every color, smoothly: each point shows the sky around its
  normal.
- **Untick "Light the scene with the sky"**: the floor, the box, and the ball
  all read about (169, 169, 169), Chapter 16's dome average of 0.5 times 0.8.
- **Meshes, Sun sky**: the floor turns from grey to the blue-grey of the sky
  above it, and the shaded sides of the shapes pick up the blue too. Lower
  the sun's elevation toward 10°: the sky dims (Chapter 23 section 6), and its
  light with it. With the box unticked the floor only loses some sunlight,
  because the panel's constant does not know the sun went down.

---

# Part 2 — Reflections (sections 5-9)

Part 1's light is the matte part. Part 2 adds the shiny part: the sky
reflected, sharp on a polished surface and blurred on a rough one, for each of
Chapter 15's three BRDFs, and then checks both paths, a dome light's image, and
what all of it costs.

## 5. What a rough surface reflects: the split sum

**This section has no code.** It turns the reflected sky into two things that
can each be computed ahead of time.

A mirror reflects the sky from one direction, **r**: the direction toward the
eye, **v**, mirrored about the normal **n** (GLSL's `reflect(-V, N)`). Each
point of a polished sphere shows the sky behind you along its own **r**. A rough
surface, in Chapter 15's microfacet picture, is countless tiny mirrors whose
normals spread around **n**. Each reflects the sky from its own direction, so
the point shows the sky *around* **r**, blurred over the lobe. In the form of
section 1's sum, with Chapter 15's GGX highlight as the weight:

$$
L_{\text{reflected}} = \int_{\text{sky}} L(\mathbf{l})\; f_{\text{spec}}(\mathbf{l}, \mathbf{v})\; (\mathbf{n} \cdot \mathbf{l})\; d\omega,
\qquad f_{\text{spec}} = \frac{D\,G\,F}{4\,(\mathbf{n} \cdot \mathbf{l})(\mathbf{n} \cdot \mathbf{v})}
$$

The diffuse sum depended on **n** alone, so one cube held every answer. This one
depends on **n**, on **v**, on the roughness, and on the material's f0: far too many
combinations to compute ahead of time. **The split-sum approximation** (Karis,
2013) splits it into two factors with fewer inputs each:

$$
L_{\text{reflected}} \approx
\underbrace{\frac{\int L(\mathbf{l})\, D\, (\mathbf{n} \cdot \mathbf{l})\, d\omega}{\int D\, (\mathbf{n} \cdot \mathbf{l})\, d\omega}}_{\text{the sky, averaged over the lobe}}
\;\times\;
\underbrace{\int f_{\text{spec}}(\mathbf{l}, \mathbf{v})\, (\mathbf{n} \cdot \mathbf{l})\, d\omega}_{\text{how much of a white sky the surface reflects}}
$$

- **The first factor is the sky blurred by the lobe**: a weighted average of
  the sky, each direction weighted by how much of the lobe points at it (D) and
  by its cosine. To make it depend on as little as possible, it pretends the
  surface is seen head-on, **n** = **v** = **r**. Then the lobe is round around
  **r**, its shape depends only on the roughness, and the whole factor is one
  cube per roughness, looked up by **r**. That is the specular cube (section 6).
- **The second factor has no sky in it at all**: it is how much light the BRDF
  sends back from a sky that is white everywhere. It depends on **n**·**v** and the
  roughness, and on f0 and f90 only as `f0 × A + f90 × B` for two numbers A and
  B, so it is a small 2D table (section 7).

**Why it is an approximation.** The sum of products is not the product of the
sums. It is exact when one of the two things being multiplied is constant over
the lobe: under a sky of one color, the first factor is that color, and the
result is exactly right. It is wrong where the sky changes inside the lobe
*and* the BRDF weighs the two sides of the lobe differently.

**What it gets wrong that you can see** comes from **n** = **v** = **r**. Seen
head-on, a rough reflection really is a round blur around **r**. Seen at a
grazing angle — a rough floor toward the horizon, or a wet street toward a low
sun — the real lobe is stretched: long in the direction toward the viewer,
narrow across it, and leaning from **r** toward **n**. That is why the lights of
a city reflected in a wet road are tall streaks. The cube's lobe is always
round, so the streak comes out a round blob:

```text
   a light reflected in a rough floor, seen at a low angle

   the real reflection          the split sum's
         |                           .-.
         |                          (   )
         |                           '-'
         |
   a tall streak               a round blob around r
```

Engines live with it, or bend the lookup direction from **r** toward **n** for rough
surfaces (Lagarde and de Rousiers, in Sources), which recovers some of the
lean but none of the stretch.

---

## 6. The specular cube: a level per roughness

**This is the specular half of `SkyConvolve`, the specular cube in
`CreateSets` and `Filter`, and set 0's binding 11.**

The first factor of section 5 is section 2's sum with one more weight. The
diffuse cube weighs each sky texel by its solid angle and cosine; a specular
level also weighs it by how much of the lobe points at it, GGX's D, which
Chapter 15 wrote as `ggxDistribution(N·H, α)`. With **n** = **v**, the half
vector of a direction **l** is **n** + **l**, normalized. And because the factor
is an *average* of the sky, the sum is divided by the total weight, so a uniform
sky comes back unchanged. These are the two lines Part 1 left aside in
`SkyConvolve`:

```glsl
                if (ibl.kind == IBL_KIND_SPECULAR)
                {
                    weight *= ggxDistribution(dot(N, normalize(N + L)), alpha);   // how much of the lobe points here
                }
```

and its last lines divide by `totalWeight` for this kind.

**Levels.** The specular cube is a mip chain, and each level is filtered for
one roughness. Rougher means blurrier, and a blurrier image needs fewer
texels, so the levels' sizes halve as the roughness grows, which is exactly the
shape of a mip chain. Each level sums over the source level half its own size,
so the lobe still spans a few source texels:

| Level | Face | Roughness | Half of the lobe within | Reads | Terms |
| --- | --- | --- | --- | --- | --- |
| 0 | 128 | 0 | a mirror: none | the sky, averaged in 4 × 4 blocks | — |
| 1 | 64 | 0.25 | 7° of **r** | source 32 (3.6° a texel) | 151 million |
| 2 | 32 | 0.5 | 28° | source 16 | 9.4 million |
| 3 | 16 | 0.75 | 59° | source 8 | 0.6 million |
| 4 | 8 | 1 | 90° | source 4 | 37 thousand |

"Half of the lobe within": with **n** = **v**, a facet tilted by an angle *t*
reflects from 2*t* away from **r**, and half of GGX's D lies within tan *t* = α
of the normal (section 7 gives the formula this comes from). For roughness
0.25, α = 0.0625, *t* = 3.6°, and half the lobe is within 7.2° of **r**.

Level 1 is nine-tenths of the terms, because sharp reflections need both a
large output and a fine source. Level 0, the mirror, is not a sum at all: a
lobe of zero width picks one direction, so it is a plain copy of the sky,
averaged down to 128 × 128 by the same downsample as the source chain.

Between levels, the sampler blends: `CreateSets` makes it with
`VK_SAMPLER_MIPMAP_MODE_LINEAR` (Appendix A), so roughness 0.375 reads halfway
between levels 1 and 2. A shader picks the level from the roughness with one
line, in `ImageBasedLighting.glsl` after the binding:

```glsl
// Section 6: the specular cube's level for a roughness. Level k was filtered for roughness k / 4; between two
// levels the sampler blends them.
float specularLevel(float roughness)
{
    return roughness * float(IBL_SPECULAR_LEVELS - 1u);
}
```

**The code grows in four places.** `Initialize` creates the cube, the lines
marked section 6 in section 3's listing. `CreateSets` gives the copy and the
four sums their sets, after the diffuse one:

```cpp
    // Section 6: level 0 of the specular cube from the sky, and levels 1-4 from the source chain.
    m_specularBaseSet = AllocateSet(m_sky, readOnly, m_skySampler, m_specular.levels[0]);
    for (uint32_t level = 1; level < IBL_SPECULAR_LEVELS; ++level)
    {
        m_specularSets[level] = AllocateSet(m_source.sampled, readOnly, m_sampler, m_specular.levels[level]);
    }
```

In `Filter`, the specular cube joins both barrier lists — `{ m_source.image,
m_diffuse.image, m_specular.image }` before, `{ m_diffuse.image,
m_specular.image }` after — so it gets exactly the diffuse cube's two
barriers, for the same reasons. Its level 0 is copied after the source chain's
loop:

```cpp
    // Section 6: the specular cube's level 0, the mirror, is a copy too.
    Dispatch(commandBuffer, m_downsamplePipeline, m_specularBaseSet,
             { .size = IBL_SPECULAR_SIZE, .taps = SKY_FACE_SIZE / (2 * IBL_SPECULAR_SIZE) });
```

and its levels are summed after the diffuse cube:

```cpp
    // Section 6: each specular level, summed over the source level half its size, for its own roughness.
    for (uint32_t level = 1; level < IBL_SPECULAR_LEVELS; ++level)
    {
        const uint32_t size = IBL_SPECULAR_SIZE >> level;   // 64, 32, 16, 8
        Dispatch(commandBuffer, m_convolvePipeline, m_specularSets[level],
                 { .size        = size,
                   .sourceSize  = size / 2,
                   .sourceLevel = level - 1,
                   .kind        = IBL_KIND_SPECULAR,
                   .roughness   = static_cast<float>(level) / static_cast<float>(IBL_SPECULAR_LEVELS - 1) });
    }
```

Level 0 needs no barrier before the sums, because no sum reads it: they read
the source chain, which already has one.

And set 0 gains binding 11, exactly as it gained 10: a line in
`CreateFrameResources`' array after binding 10's, an image info from
`lighting.SpecularInfo()` in `SetImageBasedLighting`, and its write after
binding 10's (Appendix A has the function whole). In the include, after
binding 10:

```glsl
layout(set = 0, binding = 11) uniform samplerCube skySpecular;   // the sky blurred for each roughness, a level each
```

---

## 7. The lookup table: equal shares of a lobe

**This is `SpecularLut.comp.glsl`, `CreateLut`, and `ComputeLut`.**

Section 5's second factor is the BRDF's own total: for a sky that is 1 in every
direction, how much light the GGX highlight sends toward **v**. Chapter 15's
Schlick Fresnel is a blend, F = f0 (1 − w) + f90 w with w = (1 − **v**·**h**)⁵, so
the total splits into a part multiplied by f0 and a part multiplied by f90:

$$
\int f_{\text{spec}}\,(\mathbf{n} \cdot \mathbf{l})\,d\omega = f_0\,A + f_{90}\,B,
\qquad
A = \int \frac{D\,G\,(1 - w)}{4\,(\mathbf{n} \cdot \mathbf{v})}\,d\omega, \quad
B = \int \frac{D\,G\,w}{4\,(\mathbf{n} \cdot \mathbf{v})}\,d\omega
$$

A and B depend on **n**·**v** and the roughness only, so they are a 2D table,
64 × 64, computed once in `Initialize` and never again: **n**·**v** across,
roughness down.

**An even grid does not work here.** Adding up over directions evenly spaced,
as section 2 did, wastes nearly every term on a sharp lobe: at roughness 0.2,
half of GGX's D lies within 2.3° of the normal, and a grid fine enough to put a
few points inside that would need millions of them. The fix is to place the
points where the lobe is.

GGX's D comes with a property that makes that easy: weighted by the cosine,
it adds up to exactly 1 over all facet directions, and the share of it within
an angle *t* of the normal has a closed form:

$$
\text{share}(t) = \frac{\tan^2 t}{\alpha^2 + \tan^2 t}
$$

Take it as given, and check it: at *t* = 0 the share is 0; as *t* approaches
90°, tan *t* grows without limit and the share approaches 1; and half the
lobe lies within the angle whose tangent is α. **Worked:** at roughness 0.5,
α = 0.25: half of D lies within atan(0.25) = 14° of the normal, 90% within 37°,
and 99% within 68°.

So split the lobe into 64 rings that each hold an equal share, 1/64 of it, and
put a ring of points in the middle of each: for the share *s* = (*i* + ½)/64,
solve the formula for the angle, tan² *t* = α² *s* / (1 − *s*). Spread 64
points around each ring, and each of the 4096 points stands for the same share
of D. The sum needs no D weight any more, because the points' crowding already
is one: each point counts 1/4096, and what is left to add up is the rest of
the BRDF. One more factor goes with D. It is D *times the facet's cosine*,
**n**·**h**, that adds up to 1 and that `share(t)` measures, so each point
stands for D × (**n**·**h**) of the lobe; with D gone, the **n**·**h** has to be
divided back out. That is the (**n**·**h**) below the line:

$$
A \approx \frac{1}{4096} \sum_{\text{points}} \frac{G\,(\mathbf{v} \cdot \mathbf{h})}{(\mathbf{n} \cdot \mathbf{v})(\mathbf{n} \cdot \mathbf{h})}\,(1 - w),
\qquad
B \approx \frac{1}{4096} \sum_{\text{points}} \frac{G\,(\mathbf{v} \cdot \mathbf{h})}{(\mathbf{n} \cdot \mathbf{v})(\mathbf{n} \cdot \mathbf{h})}\,w
$$

The points are facet normals **h**, and each reflects **v** into a direction
**l**. Chapter 15's 4 (**n**·**l**)(**n**·**v**) below the highlight is where
the 4 went: a small patch of facet normals reflects into a patch of directions
4 (**v**·**h**) times as large, which is the factor that turns "per facet
direction" into "per light direction", and it is the 4 in that denominator. A
point whose **l** falls below the surface counts zero.

Placing points in proportion to what is being added up, and then counting
each one equally, is called **importance sampling**. The path tracer does it
with random points; here the points are a regular pattern of rings, so the
table is the same every time it is computed.

**Worked:** roughness 0.5, seen at **n**·**v** = 0.5 (60° from head-on). The
table holds A = 0.73 and B = 0.019. A dielectric, f0 = 0.04 and f90 = 1,
reflects 0.04 × 0.73 + 0.019 = 0.048 of the sky around **r**. Chapter 15's
Schlick at **n**·**v** instead, which ignores the lobe and G, would say
0.04 + 0.96 × 0.5⁵ = 0.07.
At the same angle a roughness-1 surface keeps only A = 0.41, B = 0.003: at full
roughness most of what the facets reflect is hidden by other facets (G) or
goes below the surface.

```glsl
// Shaders/Sky/SpecularLut.comp.glsl - Chapter 24: GGX's specular, added up over every direction light can arrive
// from, for each N.V and roughness: the second half of the split sum (section 7). Run once, in Initialize.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "ImageBasedLightingTypes.h"     // IBL_LUT_SIZE, IBL_GROUP_SIZE
#include "PreviewSurface.glsl"           // PI, MIN_ROUGHNESS, smithGeometry (Chapter 15 section 9)

layout(local_size_x = IBL_GROUP_SIZE, local_size_y = IBL_GROUP_SIZE, local_size_z = 1) in;

layout(set = 0, binding = 1, rgba16f) uniform writeonly image2D lut;   // r: the scale on f0; g: on f90; b, a unused

const uint RINGS  = 64u;   // rings around the normal, each holding an equal share of D
const uint SLICES = 64u;   // directions around each ring

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (texel.x >= int(IBL_LUT_SIZE) || texel.y >= int(IBL_LUT_SIZE)) { return; }

    // Across: N.V, at the texel's centre, so never exactly 0. Down: roughness, floored as the shaders floor it.
    float NdotV     = (float(texel.x) + 0.5) / float(IBL_LUT_SIZE);
    float roughness = max((float(texel.y) + 0.5) / float(IBL_LUT_SIZE), MIN_ROUGHNESS);
    float alpha     = roughness * roughness;

    // Any V with that N.V will do: the answer depends only on the angle. N is +Z, V leans toward +X.
    vec3 V = vec3(sqrt(1.0 - NdotV * NdotV), 0.0, NdotV);

    vec2 sum = vec2(0.0);
    for (uint ring = 0u; ring < RINGS; ++ring)
    {
        // Section 7: the angle from the normal inside which a share s of D lies is tan^2 = alpha^2 s / (1 - s).
        // Taking s at the middle of each of RINGS equal shares puts every ring where the lobe is.
        float share    = (float(ring) + 0.5) / float(RINGS);
        float cosTheta = sqrt((1.0 - share) / (1.0 + (alpha * alpha - 1.0) * share));
        // The max: at the lowest roughness the first ring's cosTheta is within an ulp of 1 even in exact
        // arithmetic. A GPU's approximate divide and square root can land it a hair above 1, and the square
        // root of a negative number is NaN, which every texel in the table's smoothest rows would hold.
        float sinTheta = sqrt(max(1.0 - cosTheta * cosTheta, 0.0));
        for (uint slice = 0u; slice < SLICES; ++slice)
        {
            float phi   = 2.0 * PI * (float(slice) + 0.5) / float(SLICES);
            vec3  H     = vec3(sinTheta * cos(phi), sinTheta * sin(phi), cosTheta);   // a facet's normal
            float VdotH = dot(V, H);
            vec3  L     = 2.0 * VdotH * H - V;                                         // V reflected in it
            if (L.z <= 0.0 || VdotH <= 0.0) { continue; }                              // below the surface

            // What is left of the BRDF x cos once D is accounted for by where the rings are (section 7).
            float g       = smithGeometry(NdotV, L.z, alpha) * VdotH / (NdotV * H.z);
            float fresnel = pow(1.0 - VdotH, 5.0);                                     // Schlick's weight on f90
            sum += vec2((1.0 - fresnel) * g, fresnel * g);
        }
    }
    imageStore(lut, texel, vec4(sum / float(RINGS * SLICES), 0.0, 0.0));
}
```

**The table's format** is `R16G16B16A16_SFLOAT`, though it holds two numbers:
four-channel half floats are the format every GPU must both write as a storage
image and filter linearly, and the cost of the two spare channels is 32 KB.
`CreateLut` (Appendix A) makes the image, its view, and its pipeline in the
shared layout. **This is `ComputeLut`**, which runs it once, through
`immediateSubmit`:

```cpp
InitializationResult ImageBasedLighting::ComputeLut()
{
    const VkDescriptorSet set = AllocateSet(VK_NULL_HANDLE, VK_IMAGE_LAYOUT_UNDEFINED, VK_NULL_HANDLE, m_lutView);
    if (set == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the specular lookup table.");
    }

    // Section 7: written once by compute, then sampled by fragment shaders forever after. The fence that
    // immediateSubmit waits on keeps the CPU from racing ahead; the second barrier is what makes the
    // writes visible to every fragment shader submitted later.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, m_lut,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        Dispatch(commandBuffer, m_lutPipeline, set, { .size = IBL_LUT_SIZE }, 1);
        transitionImage(commandBuffer, m_lut,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    return InitializationResult::success();
}
```

Its two barriers are the shape of Chapter 08's upload: `UNDEFINED` to `GENERAL`
before the write, nothing having touched the table; and after it, the write
made visible to every fragment shader submitted later, which is what a barrier's
second half covers (Chapter 04 section 5).

Set 0 gains binding 12 the same way, from `lighting.LutInfo()`. In the
include:

```glsl
layout(set = 0, binding = 12) uniform sampler2D   specularLut;   // GGX's scale on f0 and on f90, by N.V and roughness
```

---

## 8. Three BRDFs, side by side

**This is `evaluateSkyAmbient`, finished.**

Chapter 15 section 9 kept three BRDFs side by side, behind one switch in
`FrameData`. The sky's light keeps them side by side too. All three share the
diffuse cube, looked up by **n**; they differ in what they reflect at the
surface, and in how they look up and weigh the reflection. With Diff(**n**) the
diffuse cube, Spec(**r**, level) the specular cube, *m* the metallic input, and
*k* the occlusion:

$$
\begin{aligned}
\text{(a) Lambert:}\quad & L = k\;\text{albedo}\;\text{Diff}(\mathbf{n}) \\
\text{(b) Blinn-Phong:}\quad & L = k\,\big[(1 - F)(1 - m)\,\text{albedo}\;\text{Diff}(\mathbf{n}) + F\;\text{Spec}(\mathbf{r},\ \text{level}(\text{roughness}))\big],
  \quad F = \text{Schlick}(f_0, f_{90}, \mathbf{n} \cdot \mathbf{v}) \\
\text{(c) GGX:}\quad & L = k\,\big[(1 - \bar F)(1 - m)\,\text{albedo}\;\text{Diff}(\mathbf{n}) + \bar F\;\text{Spec}(\mathbf{r},\ \text{level}(\text{roughness}))\big],
  \quad \bar F = f_0 A + f_{90} B
\end{aligned}
$$

**(a) Lambert** reflects nothing at its surface, so it gets the diffuse cube
alone: Part 1's line, unchanged.

**(b) Blinn-Phong** reads the specular cube at the same level as GGX, the one
for its roughness. The levels were filtered for GGX lobes, and Chapter 15
section 9 matched Blinn-Phong's exponent to GGX's α (`n = 2/α² − 2`) so that
the two lobes are about as wide. A material authored with an exponent *n*
instead of a roughness would find its level by running that match backwards.

For its Fresnel, Blinn-Phong uses Chapter 15's Schlick, but there is no single
half vector **h** for a whole lobe of facets. The facet that reflects **v** into
**r** is the one facing **n** itself, so **v**·**h** becomes **n**·**v**: the
classic choice, and the **simple Fresnel for the ambient specular**. What it
gets wrong is visible at grazing angles: (1 − **n**·**v**)⁵ goes to 1 at the rim
of every sphere, rough or not, so rough surfaces get a bright rim, and nothing
hides any of their reflection, because Blinn-Phong has no G.

**(c) GGX** is section 5's split sum: the specular cube at the roughness's
level, times the table's `f0 A + f90 B`. The table already contains the
Fresnel and G, averaged over the lobe.

**Metallic and roughness**, UsdPreviewSurface's two inputs, enter exactly as
in Chapter 15. `metallic` blends f0 and f90 toward the base color and takes
away the diffuse part (`1 − m`): a gold sphere is nothing but its tinted
reflection of the sky. `roughness` picks the level: how blurred that
reflection is. In all three, what the top of the surface reflects
(`reflectance`) does not reach the diffuse part below it, Chapter 15's
`(1 − F)` again.

**This is `evaluateSkyAmbient`, finished.** Part 1's last line, the flat
formula's stand-in, is replaced by everything after the Lambert line:

```glsl
// Section 8: the light from the whole sky, reflected toward V, by whichever BRDF s.brdf names. N and V are
// unit world vectors, V toward the eye. `occlusion` darkens it all, as in Chapter 15.
vec3 evaluateSkyAmbient(SurfaceSample s, vec3 N, vec3 V, float occlusion)
{
    vec3 diffuseLight = texture(skyDiffuse, N).rgb;   // E / pi from the hemisphere around N (section 1)

    // (a) Lambert: what a white matte surface would show, tinted by the albedo. No reflection at its surface.
    if (s.brdf == BRDF_LAMBERT) { return diffuseLight * occlusion * s.baseColor; }

    float NdotV     = max(dot(N, V), 1e-4);
    vec3  R         = reflect(-V, N);                    // the mirror direction: where the reflection gathers
    float roughness = max(s.roughness, MIN_ROUGHNESS);
    vec3  f0;
    vec3  f90;
    fresnelEndpoints(s, f0, f90);

    vec3 reflectance;     // how much of the sky the surface reflects at its top
    vec3 specularLight;   // the sky as that reflection sees it: blurred for the surface's roughness
    if (s.brdf == BRDF_BLINN_PHONG)
    {
        // (b) Blinn-Phong: the level for its roughness, as GGX, and Schlick's Fresnel at N.V (section 8).
        specularLight = textureLod(skySpecular, R, specularLevel(roughness)).rgb;
        reflectance   = schlickFresnel(f0, f90, NdotV);
    }
    else
    {
        // (c) GGX: the split sum (section 5). The level for its roughness, times the table's scale and bias.
        specularLight   = textureLod(skySpecular, R, specularLevel(roughness)).rgb;
        vec2 scaleBias  = texture(specularLut, vec2(NdotV, roughness)).rg;
        reflectance     = f0 * scaleBias.x + f90 * scaleBias.y;
    }

    // What the top of the surface reflects does not reach the diffuse part below it; metals have none.
    vec3 diffuse = (1.0 - reflectance) * (1.0 - s.metallic) * s.baseColor * diffuseLight;
    return occlusion * (diffuse + reflectance * specularLight);
}
```

**What you should see**, on `MaterialSweep.usda` in Environment mode, under
each BRDF:

- **GGX**: the gold sphere of roughness 0 mirrors the green **+Y** disc above
  it and the red **+X** disc to its right, labels and all; the next one blurs
  them; the last three are a smooth wash of green above and yellow and red
  around. The rough gold spheres are darker than the smooth ones: at roughness
  1 the table's A + B is only about 0.4, the light G hides.
- **Blinn-Phong**: the same blur at each roughness, but the rough gold spheres
  are brighter and paler, and every sphere has a brighter rim: Schlick at **n**·**v**
  with nothing hidden.
- **Lambert**: no reflection anywhere; gold is yellow paint, lit by the colors
  of the sky around each point.

Real rough metals are not as dark as GGX's: light hidden by one facet is
reflected again by another, which a single-bounce model leaves out. The fix
scales the specular term up by what the table says is missing (Kulla and
Conty, 2017; Fdez-Agüera, 2019; in Sources), and is a few lines in this
function. It is named here, not built.

---

## 9. Both paths, dome lights, and the cost

**This is where the sky's light is checked, and timed: `GpuTimestamps`,
`Update`, finished, and the viewer's line.**

### Forward and deferred

Section 4 put the same call in both shaders that add ambient light, so the two
paths agree by construction: on `SkyTest.usda` under Lambert, Chapter 22's
**Deferred** draws the same picture as **Forward**, pixel for pixel. On
`MaterialSweep.usda` under GGX in Environment mode, the largest difference is
a few levels, at a handful of pixels on the sphere silhouettes Chapter 22 section 7
explains: the ambient term is computed from the same material values on both
paths, and only the light loop reads the G-buffer. MSAA changes nothing either:
the lookups run in the fragment shader like the rest of the material, at 1x and
4x.

### Dome lights

In Environment mode the sky's cube is the dome light's own image, turned and
scaled as the dome is (Chapter 23 section 10), and the filter reads the cube.
So a USD scene lit by an HDR image now gets that image's light, by direction,
and its reflections: `SkyTest.usda` is the proof, because its answer is known.
Rotate the **Sky** node 90° about Y in the inspector: the sky turns, the bake
runs, the filter runs, and the box's front face, which received the light of
the image's +Z half, now receives its −X half's and reads (102, 169, 169)
within 1, what its left face read before.

Two rules decide which ambient light a scene gets. With the checkbox on and the
sky on, the sky's light replaces Chapter 16's constant entirely, the dome's
average included, so the dome is never counted twice. In **Sun sky** mode a
file's dome is ignored: the sky shown is the sun's, and so is its light. And
the sun's own disk is not in the cube (Chapter 23 section 6), so a reflection of
the sky never counts the sun a second time on top of the distant light's
highlight. An HDR image with a sun in it is different: that sun is in the cube,
and it lights the scene through the filter like the rest of the image.

### What it costs

`Filter` runs only when the sky is baked, and the sky is baked only when
something about it changed (Chapter 23 section 7). A scene whose sky holds
still pays nothing per frame for any of this but three texture lookups per
pixel. While you drag the sun, every frame pays the bake and the filter.

How much, the GPU can say itself, with the timestamp queries Chapter 21
section 8 taught for the particles. Chapter 22 section 11 copied that code for
the viewer. This is the third time it is needed, and ROADMAP's rule is to
write a pattern twice and automate it the third time, so here it becomes a
class, `GpuTimestamps`, that any pass can use; the grass (Chapter 26) and the
clouds (Chapter 28) use it too. Chapters 21 and 22 keep their copies:
switching them to the class is a good exercise. The rest of this section is
that utility, not lighting. If you only want the picture, skip to the exit
check, and come back before Chapter 26.

**This is `Source/PillowFort/VulkanGraphics/GpuTimestamps.h`**:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  GPU timings: Chapter 21 section 8's timestamp queries, written a third time and made a class (Chapter 24)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/GpuTimestamps.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"   // VulkanContext, FRAMES_IN_FLIGHT

#include <vulkan/vulkan.h>

#include <array>
#include <cstdint>
#include <vector>

namespace pf::vulkan_graphics {

// `count` timestamps a frame, in one query pool per frame in flight. A frame reads what its slot measured
// last time, resets the pool, and writes it again; by then that slot's fence has been waited, so the
// numbers are final and reading them never stalls.
class GpuTimestamps
{
public:
    // Success with Available() false on a device whose graphics queue cannot time anything.
    InitializationResult Initialize(const VulkanContext& context, uint32_t count);
    void Shutdown();
    bool Available() const { return m_pools[0] != VK_NULL_HANDLE; }

    // After the slot's fence, before its Reset: fetches what that slot measured last time. False when it
    // measured nothing yet, or when any of its `count` timestamps is not ready - one never written never is.
    bool   Read(uint32_t frameIndex);
    double Milliseconds(uint32_t from, uint32_t to) const;   // between two timestamps of the last Read

    // In Record, outside any rendering scope, before the frame's first Write.
    void Reset(VkCommandBuffer commandBuffer, uint32_t frameIndex);
    // The time at which everything recorded before this point has finished.
    void Write(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t timestamp) const;

private:
    VkDevice                                  m_device = VK_NULL_HANDLE;
    std::array<VkQueryPool, FRAMES_IN_FLIGHT> m_pools{};
    std::array<bool, FRAMES_IN_FLIGHT>        m_reset{};           // reset since the last Read: something to read
    uint32_t                                  m_count  = 0;
    double                                    m_period = 1.0;      // nanoseconds per tick
    uint64_t                                  m_mask   = ~0ull;    // the bits a timestamp actually has
    std::vector<uint64_t>                     m_stamps;            // the last Read
};

} // namespace pf::vulkan_graphics
```

Everything in it is Chapter 21 section 8's, which taught each piece, now kept
in one place: a frame reads its own queries only after its fence has been
waited, so `Read` never asks to wait, and returns false when a result is not
ready; `Milliseconds` masks every difference to the valid bits, so a counter
that wraps still gives the right time; and every `Write` is at `ALL_COMMANDS`,
so two timestamps bracket the work recorded between them. `GpuTimestamps.cpp`
is Chapter 21's code rearranged into these six functions (Appendix A). Three
details are new:

- **A pool per frame in flight**, instead of one pool with a base query per
  frame slot, so the frame index picks the pool and no offset is computed.
- **`Read` consumes what it reads**, so the same numbers are never returned
  twice and a pool never written is never read.
- **A device without timestamps is not an error**, just a class whose
  functions do nothing.

**This is `Update`, finished.** The light keeps a `GpuTimestamps` of two,
initialized as `Initialize`'s last line. A frame's timestamps go in its own
frame slot's pool, which is what section 4's `frameIndex` is for; it gets its
name now. The filter does not run every frame, but `Update` does, which is
what makes the slots work: each frame first reads what its slot timed last
time, `FRAMES_IN_FLIGHT` frames ago, behind a fence that has been waited. A
slot that timed nothing reads false, and the last number stands:

```cpp
void ImageBasedLighting::Update(VkCommandBuffer commandBuffer, uint32_t frameIndex, bool skyBaked)
{
    // This frame slot's fence has been waited, so what the slot timed last time is final. A slot that
    // timed nothing since its last Read reads false, and the last number stands.
    if (m_timestamps.Read(frameIndex))
    {
        m_lastMilliseconds = static_cast<float>(m_timestamps.Milliseconds(0, 1));
    }
    if (!skyBaked) { return; }   // the cubes still hold this sky's light

    m_timestamps.Reset(commandBuffer, frameIndex);
    m_timestamps.Write(commandBuffer, frameIndex, 0);
    Filter(commandBuffer);
    m_timestamps.Write(commandBuffer, frameIndex, 1);
}
```

The USD viewer shows the result in its "Rendering" panel, under Chapter 22's
timings:

```cpp
        // Chapter 24 section 9: the sky's light is filtered only when the sky is baked again. Its last cost:
        ImGui::Text("Sky light filter: %.2f GPU ms", m_sky.Lighting().LastFilterMilliseconds());
```

**The numbers.** The filter adds up about 170 million terms, nine-tenths of
them for the specular cube's level 1 (section 6's table). A desktop GPU does
that in a few milliseconds; a software Vulkan driver, running it on the CPU,
takes about half a second. Read yours from the panel, then drag the sun in
Meshes and watch the "Frame" panel's time rise while the slider moves and fall
back when it stops.

**What an engine with a moving sun does.** A few milliseconds once, when a
level loads or the weather changes, is nothing. A few milliseconds every frame
of a day-night cycle is too much, so engines spread the work:

- **Filter only on a change.** This chapter already does, by riding on the
  bake.
- **Time-slice.** Filter one face, or one level, per frame, and switch to the
  new cubes when all are done, a few frames later. The light lags the sky by
  those frames, which nobody sees at the speed a sun moves.
- **Sum fewer terms.** The sharp levels could use a smaller source and lean on
  the sampler's blend, or place their terms by equal shares of the lobe, as the
  table does, with a mip of the source chosen per term so a few hundred terms
  stand in for thousands. That is how most engines filter, and what section 7
  prepares.

Chapter 28's clouds will make the case sharper. They are drawn into a cube of
their own, which this filter does not read, so they neither dim nor tint the
sky's light; filtering them in would mean filtering every frame, time-sliced.

---

## When it does not work

| Symptom | Likely cause |
| --- | --- |
| Every demo with a sky fails in `Setup`, on some GPUs only: the picker says `vkAllocateDescriptorSets failed for the specular lookup table.`, and validation says nothing | The pool is a combined image sampler short. A pool is counted by layout, so the table's set takes one though it never writes binding 0: eleven sets, eleven samplers (section 3). Some drivers let a pool overfill; AMD's returns `VK_ERROR_OUT_OF_POOL_MEMORY` |
| Validation: a descriptor at set 0, binding 10, 11, or 12 was never written, at the first mesh draw | The demo did not call `SetImageBasedLighting` in `Setup` (section 4) |
| Validation: image layout at a draw, for binding 10 or 11 | A cube was not made readable in `CreateCube`, or `Filter`'s last barrier does not leave it in `SHADER_READ_ONLY_OPTIMAL` |
| Everything ambient is black with the checkbox on | Sun sky in a scene with no sun: the sky is black, so is its light. Or the filter never ran: the light's `Update` must follow the bake, and be told `changed` |
| The diffuse light is about a fifth too bright, most toward the cube's edges | The texel's solid angle is missing its slant: `d²` below the line instead of `d³` (section 2) |
| The diffuse light is π times too bright | The sum was stored as E, not E / π |
| Reflections come out mirrored or turned | The direction of a source texel and the cube's face table disagree: use `CUBE_FACE_*` from `CubeMap.glsl` (Chapter 23 section 2) |
| Rough reflections are blocky | A level sums over a source too coarse for its lobe; each level reads the source level half its own size |
| Smooth spheres look right, rough ones too bright at the rim | Blinn-Phong's Schlick at **n**·**v** (section 8): expected for that model, not for GGX |
| Rough gold is noticeably darker than smooth gold under GGX | Expected: single-bounce GGX loses that light (section 8) |
| The panel's filter time stays at 0 | The device has no timestamps (`GpuTimestamps::Available()` is false), or the sky has not been baked since the demo started |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and open `SkyTest.usda` in the USD
      viewer with the sky in **Environment**, the BRDF on **Lambert**, and the
      tone mapping at Raw and 0 stops. The floor reads **(169, 213, 169)**, the
      box's front face (169, 169, 213), and its left face (102, 169, 169):
      0.8 × (0.5 + n/3) for each face's normal n, each channel within 1 (a 169
      may read 170; Part 1's checkpoint says why). Untick **Light the scene with
      the sky**: all three read about (169, 169, 169).
- [ ] Rotate the **Sky** node 90° about Y in the inspector: the image turns,
      the bake and the filter run again, and the box's front face now reads
      (102, 169, 169) and its left face (169, 169, 102), within 1.
- [ ] Switch **Forward** and **Deferred** on `SkyTest.usda`: the same three
      readings on both.
- [ ] Open `MaterialSweep.usda` in Environment mode and flip the BRDF through
      GGX, Blinn-Phong, and Lambert: section 8's three descriptions. Then set
      MSAA to 4x: the same, with smooth sphere edges, and validation silent.
- [ ] In **Meshes**, Sun sky: at 25° of sun elevation
      the floor near the bottom-left corner reads about (109, 116, 142) with
      the checkbox on and (111, 110, 111) with it off; at 10°, (75, 84, 113)
      and (81, 82, 86).
- [ ] Read **Sky light filter** in the viewer's "Rendering" panel after
      switching the sky's mode (each switch bakes and filters), then drag the
      sun in Meshes and watch the "Frame" panel's time follow.
- [ ] **The last and middle barriers are proven.** In `Filter`, drop
      `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT` from the *after* barrier's
      destination, and turn the sky on in the USD viewer: synchronization
      validation reports `SYNC-HAZARD-READ-AFTER-WRITE` at the first mesh draw,
      its fragment shader reading binding 10 or 11, which the sums just wrote.
      Put it back. Then change the *between* barrier's destination stage from
      `COMPUTE_SHADER` to `FRAGMENT_SHADER`: it reports
      `SYNC-HAZARD-READ-AFTER-WRITE` at the diffuse sum's `vkCmdDispatch`. Put
      it back. If neither fires, the shader-access setting is off (Chapter 20
      section 5).
- [ ] Validation is silent through mode switches, the checkbox, demo switches,
      file switches, resizes, and 1x/4x, and quitting reports no leaked VMA
      allocation.

Next: [25 — Grass, Part I: Blades](25-Grass-Blades.md)

---

## Sources

- B. Karis, "Real Shading in Unreal Engine 4", SIGGRAPH 2013 course notes:
  the split sum, the prefiltered levels per roughness, and the lookup table
  (sections 5-7).
- R. Ramamoorthi, P. Hanrahan, "An Efficient Representation for Irradiance
  Environment Maps", SIGGRAPH 2001: the nine spherical harmonics named in
  section 2.
- S. Lagarde, C. de Rousiers, "Moving Frostbite to Physically Based
  Rendering", SIGGRAPH 2014 course notes: the dominant direction for rough
  reflections (section 5), and a careful treatment of filtering cubes.
- B. Walter, S. Marschner, H. Li, K. Torrance, "Microfacet Models for
  Refraction through Rough Surfaces", EGSR 2007: the GGX distribution, its
  share within an angle, and the 4 (**v**·**h**) between half vectors and light
  directions (section 7).
- C. Kulla, A. Conty, "Revisiting Physically Based Shading at Imageworks",
  SIGGRAPH 2017 course notes; C. Fdez-Agüera, "A Multiple-Scattering
  Microfacet Model for Real-Time Image-based Lighting", JCGT 2019: the energy
  GGX loses at high roughness (section 8).
- J. Kautz, M. McCool, "Approximation of Glossy Reflection with Prefiltered
  Environment Maps", Graphics Interface 2000: prefiltered cubes for Phong-style
  lobes, the older idea behind section 6's level per lobe width.

---

## Appendix A — The rest of the code

Reference: the parts of `ImageBasedLighting` the sections described without
listing, and the shared header.

**`ImageBasedLightingTypes.h`** (sections 3 and 4), whole:

```c
/* Shaders/Include/ImageBasedLightingTypes.h - Chapter 24: the sizes of the sky's light, and the filter's push
   constants, in both languages. GLSL and C++ both include it as "ImageBasedLightingTypes.h". */
#ifndef PF_IMAGE_BASED_LIGHTING_TYPES_H
#define PF_IMAGE_BASED_LIGHTING_TYPES_H

#include "SharedShaderTypes.h"   /* uint, on the C++ side */

#define IBL_DIFFUSE_SIZE    32u   /* the diffuse cube's faces: light from a whole hemisphere changes slowly */
#define IBL_SPECULAR_SIZE   128u  /* the specular cube's level 0, the mirror; each level after it is half */
#define IBL_SPECULAR_LEVELS 5u    /* 128, 64, 32, 16, 8: roughness 0, 0.25, 0.5, 0.75, 1 */
#define IBL_SOURCE_SIZE     32u   /* the box-filtered copies of the sky the sums read: 32, 16, 8, 4 */
#define IBL_SOURCE_LEVELS   4u
#define IBL_LUT_SIZE        64u   /* the lookup table: N.V across, roughness down */
#define IBL_GROUP_SIZE      8u    /* every filter shader's local_size_x and _y */

/* IblFilterParameters::kind: what SkyConvolve's sum weighs each texel by (sections 3 and 6). */
#define IBL_KIND_DIFFUSE  0u
#define IBL_KIND_SPECULAR 1u

#ifdef __cplusplus
    namespace pf::shared {
#endif

/* The filter's push constants (std430), one block for all three shaders; each reads what it needs. */
struct IblFilterParameters
{
    uint  size;          /*  0  the face size being written, in texels */
    uint  taps;          /*  4  SkyDownsample: lookups along each side of one texel */
    uint  sourceSize;    /*  8  SkyConvolve: the face size of the source level it sums */
    uint  sourceLevel;   /* 12  SkyConvolve: which level of the source chain that is */
    uint  kind;          /* 16  SkyConvolve: IBL_KIND_* */
    float roughness;     /* 20  SkyConvolve, specular: the level's roughness, as authored */
    uint  padding0;      /* 24 */
    uint  padding1;      /* 28 */
};                       /* 32 */

#ifdef __cplusplus
    static_assert(sizeof(IblFilterParameters) == 32, "IblFilterParameters layout drifted.");
    }
#endif

#endif
```

**`CreateCube`** (section 3), whole:

```cpp
InitializationResult ImageBasedLighting::CreateCube(IblCube& cube, uint32_t size, uint32_t levels,
                                                    VkImageViewType sampledType, const char* name)
{
    // Six square layers, `levels` mip levels, half-float HDR like the sky. STORAGE: the filter writes it.
    // SAMPLED: the mesh shaders, or the filter's own sums, read it.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .flags         = VK_IMAGE_CREATE_CUBE_COMPATIBLE_BIT,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent        = { size, size, 1 },
        .mipLevels     = levels,
        .arrayLayers   = 6,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &cube.image, &cube.allocation, nullptr) !=
        VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vmaCreateImage failed for the sky's {} cube.", name));
    }

    // The view its readers sample, every level.
    VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = cube.image,
        .viewType         = sampledType,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, 6 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &cube.sampled) != VK_SUCCESS)
    {
        return InitializationResult::failure(std::format("vkCreateImageView failed for the sky's {} cube.", name));
    }

    // One view per level for the filter to write: a storage image names exactly one mip level.
    viewInfo.viewType = VK_IMAGE_VIEW_TYPE_CUBE;
    for (uint32_t level = 0; level < levels; ++level)
    {
        viewInfo.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, level, 1, 0, 6 };
        if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &cube.levels[level]) != VK_SUCCESS)
        {
            return InitializationResult::failure(std::format("vkCreateImageView failed for a level of the sky's {} cube.", name));
        }
    }

    // Readable from the start, like the sky's own cube (Chapter 23 section 3): set 0 names these images in
    // every demo that draws meshes, while the sky is off and nothing has been filtered, and validation
    // checks the layout of every image a pipeline's sets name. The contents mean something after a Filter.
    immediateSubmit(m_context, [&](VkCommandBuffer commandBuffer) {
        transitionImage(commandBuffer, cube.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    return InitializationResult::success();
}
```

**`CreatePipelines`** (section 3):

```cpp
InitializationResult ImageBasedLighting::CreatePipelines()
{
    // Every filter shader reads one thing at binding 0 and writes one image at binding 1.
    const std::array<VkDescriptorSetLayoutBinding, 2> bindings{ {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    } };
    const VkDescriptorSetLayoutCreateInfo setLayoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(bindings.size()),
        .pBindings    = bindings.data(),
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &setLayoutInfo, nullptr, &m_setLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the sky's light.");
    }

    const VkPushConstantRange range{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(shared::IblFilterParameters),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &range,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_layout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sky's light.");
    }

    m_downsamplePipeline = createComputePipeline(m_context.device, m_pipelineCache, "Sky/SkyDownsample.comp.spv", m_layout);
    m_convolvePipeline   = createComputePipeline(m_context.device, m_pipelineCache, "Sky/SkyConvolve.comp.spv", m_layout);
    if (m_downsamplePipeline == VK_NULL_HANDLE || m_convolvePipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sky's light pipelines failed.");
    }
    return InitializationResult::success();
}
```

**`CreateSets`** (sections 3 and 6), whole:

```cpp
InitializationResult ImageBasedLighting::CreateSets()
{
    // One sampler for everything the mesh shaders read here: linear within a level and between levels,
    // which is what blends two roughness steps of the specular cube (section 6). Clamped at the edges.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_LINEAR,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE,
        .maxLod       = static_cast<float>(IBL_SPECULAR_LEVELS - 1),
    };
    if (vkCreateSampler(m_context.device, &samplerInfo, nullptr, &m_sampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the sky's light.");
    }

    // One set per dispatch, because each reads and writes its own pair of images: five downsamples, five
    // sums, and the lookup table, Part 2's included. Ten of them read something and all eleven write, but a
    // pool counts each set's layout, not what is written: the table's set takes a sampler too. Some drivers
    // let a pool overfill; AMD's fails the eleventh set.
    const std::array<VkDescriptorPoolSize, 2> poolSizes{ {
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 11 },
        { VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 11 },
    } };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 11,
        .poolSizeCount = static_cast<uint32_t>(poolSizes.size()),
        .pPoolSizes    = poolSizes.data(),
    };
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &m_pool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the sky's light.");
    }

    // The downsamples read the sky; the sums read the source chain, which Filter leaves in
    // SHADER_READ_ONLY_OPTIMAL before they run (section 4).
    constexpr VkImageLayout readOnly = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    for (uint32_t level = 0; level < IBL_SOURCE_LEVELS; ++level)
    {
        m_sourceSets[level] = AllocateSet(m_sky, readOnly, m_skySampler, m_source.levels[level]);
    }
    m_diffuseSet = AllocateSet(m_source.sampled, readOnly, m_sampler, m_diffuse.levels[0]);

    // Section 6: level 0 of the specular cube from the sky, and levels 1-4 from the source chain.
    m_specularBaseSet = AllocateSet(m_sky, readOnly, m_skySampler, m_specular.levels[0]);
    for (uint32_t level = 1; level < IBL_SPECULAR_LEVELS; ++level)
    {
        m_specularSets[level] = AllocateSet(m_source.sampled, readOnly, m_sampler, m_specular.levels[level]);
    }
    if (m_diffuseSet == VK_NULL_HANDLE || m_specularBaseSet == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the sky's light.");
    }
    return InitializationResult::success();
}
```

**`AllocateSet` and `Dispatch`** (section 3):

```cpp
// A set from m_pool: binding 0 `read` (none for the lookup table), binding 1 `write` in GENERAL, the
// layout a storage image is written in.
VkDescriptorSet ImageBasedLighting::AllocateSet(VkImageView read, VkImageLayout readLayout, VkSampler sampler,
                                                VkImageView write)
{
    VkDescriptorSet set = VK_NULL_HANDLE;
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_pool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_setLayout,
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, &set) != VK_SUCCESS) { return VK_NULL_HANDLE; }

    const VkDescriptorImageInfo readInfo{ .sampler = sampler, .imageView = read, .imageLayout = readLayout };
    const VkDescriptorImageInfo writeInfo{ .imageView = write, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
    const std::array<VkWriteDescriptorSet, 2> writes{ {
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 1, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, .pImageInfo = &writeInfo },
        { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 0, .descriptorCount = 1,
          .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &readInfo },
    } };
    vkUpdateDescriptorSets(m_context.device, read != VK_NULL_HANDLE ? 2 : 1, writes.data(), 0, nullptr);
    return set;
}
```

```cpp
// One dispatch: an invocation per texel written, over `layers` faces (6 for a cube, 1 for the table).
void ImageBasedLighting::Dispatch(VkCommandBuffer commandBuffer, VkPipeline pipeline, VkDescriptorSet set,
                                  const shared::IblFilterParameters& parameters, uint32_t layers)
{
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_layout, 0, 1, &set, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(parameters), &parameters);
    const uint32_t groups = groupCount(parameters.size, IBL_GROUP_SIZE);
    vkCmdDispatch(commandBuffer, groups, groups, layers);
}
```

**`CreateLut`** (section 7):

```cpp
InitializationResult ImageBasedLighting::CreateLut()
{
    // Section 7: two numbers per texel, but R16G16B16A16_SFLOAT: the four-channel half-float format is one
    // every GPU must both write as a storage image and filter linearly. 32 KB, with two channels unused.
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = VK_FORMAT_R16G16B16A16_SFLOAT,
        .extent        = { IBL_LUT_SIZE, IBL_LUT_SIZE, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(m_context.allocator, &imageInfo, &allocationInfo, &m_lut, &m_lutAllocation, nullptr) !=
        VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for the specular lookup table.");
    }
    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = m_lut,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = imageInfo.format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    if (vkCreateImageView(m_context.device, &viewInfo, nullptr, &m_lutView) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for the specular lookup table.");
    }


    // Its shader, in the layout the other two share: it writes binding 1 and reads nothing.
    m_lutPipeline = createComputePipeline(m_context.device, m_pipelineCache, "Sky/SpecularLut.comp.spv", m_layout);
    if (m_lutPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the specular lookup table's pipeline failed.");
    }
    return InitializationResult::success();
}
```

**`Filter`** (sections 4 and 6), whole:

```cpp
void ImageBasedLighting::Filter(VkCommandBuffer commandBuffer)
{
    // Before: a write after a read. Last frame's draws sampled the two cubes, perhaps still running; the
    // last Filter's sums sampled the source chain. Every texel is written again, so UNDEFINED.
    for (const VkImage image : { m_source.image, m_diffuse.image, m_specular.image })
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }

    // Section 3: the four small copies the sums read, each straight from the sky. Each dispatch writes its
    // own level and reads only the sky, so none waits for another: no barrier between them.
    for (uint32_t level = 0; level < IBL_SOURCE_LEVELS; ++level)
    {
        const uint32_t size = IBL_SOURCE_SIZE >> level;   // 32, 16, 8, 4
        Dispatch(commandBuffer, m_downsamplePipeline, m_sourceSets[level], { .size = size, .taps = SKY_FACE_SIZE / (2 * size) });
    }
    // Section 6: the specular cube's level 0, the mirror, is a copy too.
    Dispatch(commandBuffer, m_downsamplePipeline, m_specularBaseSet,
             { .size = IBL_SPECULAR_SIZE, .taps = SKY_FACE_SIZE / (2 * IBL_SPECULAR_SIZE) });

    // Between: a read after a write. The sums below sample what the downsamples just wrote.
    transitionImage(commandBuffer, m_source.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    // Section 4: the diffuse cube, summed over the 16 x 16 source level.
    Dispatch(commandBuffer, m_convolvePipeline, m_diffuseSet,
             { .size = IBL_DIFFUSE_SIZE, .sourceSize = IBL_SOURCE_SIZE >> 1, .sourceLevel = 1, .kind = IBL_KIND_DIFFUSE });

    // Section 6: each specular level, summed over the source level half its size, for its own roughness.
    for (uint32_t level = 1; level < IBL_SPECULAR_LEVELS; ++level)
    {
        const uint32_t size = IBL_SPECULAR_SIZE >> level;   // 64, 32, 16, 8
        Dispatch(commandBuffer, m_convolvePipeline, m_specularSets[level],
                 { .size        = size,
                   .sourceSize  = size / 2,
                   .sourceLevel = level - 1,
                   .kind        = IBL_KIND_SPECULAR,
                   .roughness   = static_cast<float>(level) / static_cast<float>(IBL_SPECULAR_LEVELS - 1) });
    }

    // After: a read after a write. The mesh shaders sample both cubes in their fragment stage; a later
    // chapter's compute shader may too.
    for (const VkImage image : { m_diffuse.image, m_specular.image })
    {
        transitionImage(commandBuffer, image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
}
```

**The three `Info` accessors, `DestroyCube`, and `Shutdown`:**

```cpp
VkDescriptorImageInfo ImageBasedLighting::DiffuseInfo() const
{
    return { .sampler = m_sampler, .imageView = m_diffuse.sampled, .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
}

VkDescriptorImageInfo ImageBasedLighting::SpecularInfo() const
{
    return { .sampler = m_sampler, .imageView = m_specular.sampled, .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
}

VkDescriptorImageInfo ImageBasedLighting::LutInfo() const
{
    return { .sampler = m_sampler, .imageView = m_lutView, .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL };
}

void ImageBasedLighting::DestroyCube(IblCube& cube)
{
    for (VkImageView& view : cube.levels)
    {
        vkDestroyImageView(m_context.device, view, nullptr);   // null is a no-op
        view = VK_NULL_HANDLE;
    }
    vkDestroyImageView(m_context.device, cube.sampled, nullptr);
    if (m_context.allocator != VK_NULL_HANDLE)                  // VMA asserts on a null allocator
    {
        vmaDestroyImage(m_context.allocator, cube.image, cube.allocation);
    }
    cube = {};
}

void ImageBasedLighting::Shutdown()
{
    // Initialize never ran: nothing to destroy. Otherwise null handles are no-ops, so a partial Initialize
    // is safe. The pool frees every set.
    if (m_context.device == VK_NULL_HANDLE) { return; }
    m_timestamps.Shutdown();
    vkDestroyPipeline(m_context.device, m_lutPipeline, nullptr);
    vkDestroyPipeline(m_context.device, m_convolvePipeline, nullptr);
    vkDestroyPipeline(m_context.device, m_downsamplePipeline, nullptr);
    vkDestroyPipelineLayout(m_context.device, m_layout, nullptr);
    vkDestroyDescriptorPool(m_context.device, m_pool, nullptr);
    vkDestroyDescriptorSetLayout(m_context.device, m_setLayout, nullptr);
    vkDestroySampler(m_context.device, m_sampler, nullptr);
    vkDestroyImageView(m_context.device, m_lutView, nullptr);
    if (m_context.allocator != VK_NULL_HANDLE)
    {
        vmaDestroyImage(m_context.allocator, m_lut, m_lutAllocation);
    }
    DestroyCube(m_source);
    DestroyCube(m_specular);
    DestroyCube(m_diffuse);
    *this = ImageBasedLighting{};   // every handle null again, for the next Initialize
}

} // namespace pf::vulkan_graphics
```

**`GpuTimestamps.cpp`** (section 9), whole:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  GPU timings: Chapter 21 section 8's timestamp queries, written a third time and made a class (Chapter 24)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/VulkanGraphics/GpuTimestamps.cpp
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"

#include <algorithm>

// File scope, above the namespace block. Chapter 21 section 8's check: the fewest valid bits of any
// graphics queue family, 0 when that family cannot write timestamps at all.
static uint32_t timestampValidBits(VkPhysicalDevice physicalDevice)
{
    uint32_t familyCount = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physicalDevice, &familyCount, nullptr);
    std::vector<VkQueueFamilyProperties> families(familyCount);
    vkGetPhysicalDeviceQueueFamilyProperties(physicalDevice, &familyCount, families.data());

    uint32_t bits = 64;
    for (const VkQueueFamilyProperties& family : families)
    {
        if ((family.queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0)
        {
            bits = std::min(bits, family.timestampValidBits);
        }
    }
    return bits;
}

namespace pf::vulkan_graphics {

InitializationResult GpuTimestamps::Initialize(const VulkanContext& context, uint32_t count)
{
    m_device = context.device;
    m_count  = count;
    m_stamps.assign(count, 0);
    m_reset.fill(false);

    // Chapter 21 section 8: the period turns ticks into nanoseconds, and the valid bits give the mask.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(context.physicalDevice, &properties);
    m_period = static_cast<double>(properties.limits.timestampPeriod);

    const uint32_t validBits = timestampValidBits(context.physicalDevice);
    if (validBits == 0) { return InitializationResult::success(); }   // nothing to time with
    m_mask = validBits >= 64 ? ~0ull : (1ull << validBits) - 1ull;

    const VkQueryPoolCreateInfo poolInfo{
        .sType      = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO,
        .queryType  = VK_QUERY_TYPE_TIMESTAMP,
        .queryCount = count,
    };
    for (VkQueryPool& pool : m_pools)
    {
        if (vkCreateQueryPool(m_device, &poolInfo, nullptr, &pool) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkCreateQueryPool failed for GPU timestamps.");
        }
    }
    return InitializationResult::success();
}

void GpuTimestamps::Shutdown()
{
    if (m_device == VK_NULL_HANDLE) { return; }   // never initialized
    for (VkQueryPool& pool : m_pools)
    {
        vkDestroyQueryPool(m_device, pool, nullptr);   // null is a no-op
        pool = VK_NULL_HANDLE;
    }
    m_reset.fill(false);
}

bool GpuTimestamps::Read(uint32_t frameIndex)
{
    if (!Available() || !m_reset[frameIndex]) { return false; }
    m_reset[frameIndex] = false;   // one Read per Reset: the same numbers are never returned twice

    // No WAIT flag: a result that is not ready is skipped rather than waited for.
    return vkGetQueryPoolResults(m_device, m_pools[frameIndex], 0, m_count, m_count * sizeof(uint64_t),
                                 m_stamps.data(), sizeof(uint64_t), VK_QUERY_RESULT_64_BIT) == VK_SUCCESS;
}

double GpuTimestamps::Milliseconds(uint32_t from, uint32_t to) const
{
    // Masked, so a counter that wrapped between the two still gives the right difference.
    return static_cast<double>((m_stamps[to] - m_stamps[from]) & m_mask) * m_period * 1e-6;
}

void GpuTimestamps::Reset(VkCommandBuffer commandBuffer, uint32_t frameIndex)
{
    if (!Available()) { return; }
    vkCmdResetQueryPool(commandBuffer, m_pools[frameIndex], 0, m_count);
    m_reset[frameIndex] = true;
}

void GpuTimestamps::Write(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t timestamp) const
{
    if (!Available()) { return; }
    vkCmdWriteTimestamp2(commandBuffer, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, m_pools[frameIndex], timestamp);
}

} // namespace pf::vulkan_graphics
```

**`SetImageBasedLighting`** (sections 4, 6, and 7), whole:

```cpp
// Chapter 24: set 0's bindings 10, 11, and 12, in every frame in flight's set. In Setup, after Initialize
// and after the sky's: they never change afterwards, because Filter rewrites the images, not the views.
void SceneRenderer::SetImageBasedLighting(const ImageBasedLighting& lighting)
{
    const VkDescriptorImageInfo diffuse  = lighting.DiffuseInfo();
    const VkDescriptorImageInfo specular = lighting.SpecularInfo();   // section 6
    const VkDescriptorImageInfo lut      = lighting.LutInfo();        // section 7
    for (const VkDescriptorSet set : m_frameSets)
    {
        const VkWriteDescriptorSet writes[] = {
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 10, .descriptorCount = 1,
              .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &diffuse },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 11, .descriptorCount = 1,
              .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &specular },
            { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set, .dstBinding = 12, .descriptorCount = 1,
              .descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, .pImageInfo = &lut },
        };
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(std::size(writes)), writes, 0, nullptr);
    }
}
```

