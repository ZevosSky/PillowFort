# 30 — A Rougher Sea

**Goal:** Chapter 29's ocean with long swells and fine ripples at once, and no
grid of repeats seen from above: three FFT patches of different sizes, each
holding only its own band of waves. The waves come from JONSWAP, a spectrum
fitted to measured seas, with the wind's waves spread over directions and a
second swell crossing them from a distant storm; Chapter 29's Phillips spectrum
stays one click away to compare. Foam stays behind where a crest broke and fades
over seconds. The water reflects the engine's sky and its clouds, and the sun's
glint goes dark under a cloud.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Sea/` with shaders
under `Shaders/Sea/`.

**Module:** the demo is `pf::demos::sea` (`SeaDemo`). It adds nothing to the
engine, and it changes nothing of Chapter 29's: it runs four of Chapter 29's
compute shaders exactly as they are, and copies two small helpers. Chapters 31
and 32 grow this demo.

**Math:** taught where it is first used — a repeat distance as a common
multiple (section 1); wave numbers, wavelengths, and texels per wave (section
2); a spectrum measured over frequencies turned into one over wave vectors, and
the area under a curve added up in strips (section 5); a function of direction
that adds up to one (section 6); a narrow peak sampled by a grid (section 7);
exponential decay and its half-life (section 8). It assumes Chapter 29's primer
— complex numbers, the spectrum, `Δk`, the dispersion relation — and does not
teach it again.

**Prerequisites:**

- Chapter 29, all of it, built and running. Above all: section 2 (a centred
  spectrum, and a wave vector per texel), 4 (the eight images and the sets that
  name them), 5 (the FFT pass and its barrier), 7 (the Phillips spectrum,
  Box-Muller, and why each texel holds `P(k) Δk²`), 8 (`h(k, t)` with its
  conjugate term, and the dispersion relation), 9 (the Jacobian), 10 (the
  surface, its tiles, and the barriers between the maps and the surface), and 11
  (a panel split by cost).
- Chapter 20 sections 4 (the storage formats every GPU supports, and which of
  them a sampler may filter) and 5 (`computeToComputeBarrier`, and what sync
  validation can and cannot see).
- Chapter 21 sections 1 (state the GPU carries from frame to frame: one copy,
  and a return trip) and 3 (drag as an exponential, which section 8 reuses for
  foam).
- Chapter 24 section 9's `GpuTimestamps`, for what the cascades cost
  (section 4), and Chapter 21 section 8 behind it.
- Chapter 23, the `Sky` a 3D demo owns: section 3 (the cube, readable from
  `Initialize` on), 6 (the sun's disk is not in the cube; the ground below the
  horizon), 7 (`Update` outside a rendering scope, `Draw` at depth 1.0), and 8
  (one setting for the whole engine). And Chapter 28 sections 4 and 5, the
  clouds' cube (premultiplied, and readable from the start) and the barrier
  after the march, for Part 4.
- Chapter 15 section 9, a highlight lobe divided by its own total, for section
  10's glint; and Chapter 28 section 11, a color's luminance.
- Chapter 08 section 4 — a color picked in ImGui is sRGB.

The sea owns a Chapter 23 `Sky` from Part 1 on, with Chapter 28's clouds in
it, because the surface's descriptor set names both cubes. It reflects them
only from Part 4; until then the water reflects Chapter 29's gradient.

---

## Where this is going

From a ship's deck, Chapter 29's sea is right. From higher up it is not, and the
reason is in its numbers: 256 texels across one patch. A 300 m patch holds waves
from 300 m down to about 2 m and nothing smaller, so up close the water is
smooth; a 40 m patch has ripples down to 30 cm but repeats every 40 m, and from
a hundred metres up the repeats make a grid you cannot miss. This chapter keeps
256 texels and uses three patches, a big one for the swell and two small ones
for the chop and the ripples, adds them up, and gives each one only the waves
the others do not have.

```text
   cascade 0, 250 m          cascade 1, 37 m          cascade 2, 7 m
   waves 250 m to 6.2 m      waves 6.2 m to 1.2 m     waves 1.2 m and shorter
   ~~~~~~~~~~~~~~~~~~~~  +   ^v^v^v^v^v^v^v^v^v^  +   ''''''''''''''''''''   =   the sea
   the swell and the sea     the chop on it           the ripples on that
```

One frame, end to end. Every box with `x3` is Chapter 29's pass, run once per
cascade:

```text
 settings -> [ spectrum x3, sec. 3, 5-7 ] -> h0 per cascade, its band only   (when a setting changes)
                                |
 time ----> [ animate x3 ] <----+       Chapter 29 section 8, unchanged
                |
            [ FFT x3 ]                  Chapter 29 section 5, unchanged: 16 stages, three dispatches each
                |
            [ assemble x3 ]             Chapter 29 section 9, unchanged: displacement, normal, Jacobian
                |
            [ foam x3, sec. 8 ]         new: the Jacobian's foam, added to what is left of last frame's
                |
            [ surface, sec. 4 ]         new: every cascade's displacement, slopes, and foam, added up
                |                       Part 4: the engine's sky and clouds, reflected
```

The chapter is in four parts:

- **Part 1, "Cascades"** (sections 1-4): why one patch is not enough, how to
  split the waves between three, the demo, and the surface that adds them up.
  It ends with one cascade against three, seen from above.
- **Part 2, "A measured sea"** (sections 5-7): JONSWAP beside Phillips, waves
  spread over directions, and a swell. It ends with the two spectra side by side.
- **Part 3, "Foam that lingers"** (section 8): foam with a memory, and the one
  barrier in the tutorial whose old layout must not be `UNDEFINED`.
- **Part 4, "The sky in the water"** (sections 9-11): the engine's sky behind
  the sea and in it, the clouds' shadow on the sun's glint, and the whole frame
  in order.

### What you are actually writing

**This is `SeaDemo.h`**, the map of the chapter. Every private function names
the section that writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 30: a rougher sea - cascades of Chapter 29's ocean, a measured spectrum, lasting foam
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Sea/SeaDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/Sky.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Ocean/OceanTypes.h"   // Chapter 29's FftParameters and OceanParameters, as they are
#include "Sea/SeaTypes.h"

#include <glm/glm.hpp>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <bit>
#include <cstdint>

namespace pf::demos::sea {

// What the panels edit. CPU state: it survives Teardown and Setup.
// Colors are sRGB, as the swatches show them; PackSurface converts them.
struct SeaSettings
{
    // The cascades (sections 2-4). Changing any of these rebuilds the spectra.
    std::array<float, SEA_CASCADE_COUNT> patchSizes{ 250.0f, 37.0f, 7.0f };   // metres, largest first
    int solo = -1;                          // -1: every cascade, each its own band; c: cascade c alone, every wave it holds

    // The spectrum (sections 5-7). Changing any of these rebuilds the spectra too.
    int   model             = static_cast<int>(SEA_SPECTRUM_JONSWAP);
    float windSpeed         = 12.0f;        // m/s
    float windAzimuth       = 0.0f;         // degrees the wind blows toward, turning from -Z toward +X
    float fetch             = 100.0f;       // km of open water the wind has blown across
    float peakEnhancement   = 3.3f;         // JONSWAP's gamma
    float spread            = 4.0f;         // s: higher keeps the waves closer to the wind's direction
    float phillipsAmplitude = 0.002f;       // Chapter 29's A
    float suppression       = 0.02f;        // metres: waves shorter than this fade out
    bool  swell             = true;
    float swellHeight       = 1.5f;         // metres, significant wave height
    float swellWavelength   = 200.0f;       // metres, at its peak
    float swellAzimuth      = 70.0f;        // degrees it travels toward
    float swellSpread       = 40.0f;        // s
    int   seed              = 1;

    // Every frame, free (sections 4 and 8).
    float choppiness    = 1.0f;             // lambda, the same for every cascade
    float timeScale     = 1.0f;
    float foamThreshold = 0.75f;            // a cascade's Jacobian below this makes foam
    float foamFade      = 3.0f;             // seconds for old foam to fade to 37%
    glm::vec3 waterColor { 0.03f, 0.16f, 0.20f };   // sRGB
    glm::vec3 skyColor   { 0.70f, 0.80f, 0.90f };   // sRGB: Chapter 29's horizon, for when the sky is off
    float sunElevation  = 15.0f;            // degrees above the horizon
    float sunAzimuth    = 0.0f;             // degrees, turning from -Z toward +X
    float sunStrength   = 1.0f;             // section 10: times Chapter 11's sun, pi (0.90, 0.85, 0.80)
    float hazeDistance  = 900.0f;           // metres
    int   tileRadius    = 1;                // largest-cascade patches drawn on each side of the camera's

    // Chapter 29's preview, of one cascade at a time.
    int   previewCascade = 0;
    int   view           = static_cast<int>(OCEAN_VIEW_SPECTRUM);
    float previewGain    = 1.0f;
};

// The spectrum's numbers that are worked out on the CPU (sections 5-7): the shader
// needs some, and the panel shows the rest.
struct SpectrumConstants
{
    float alpha              = 0.0f;   // JONSWAP's scale, from the wind and the fetch
    float peakOmega          = 0.0f;   // rad/s, from the wind and the fetch
    float windNormalization  = 0.0f;   // makes the wind sea's spreading add up to 1
    float significantHeight  = 0.0f;   // metres: the wind sea's Hs, for the panel
    float swellAlpha         = 0.0f;   // chosen so the swell's Hs is the panel's height
    float swellOmega         = 0.0f;   // rad/s, from its wavelength
    float swellNormalization = 0.0f;
};

// Chapter 29's OceanImage, under this demo's name: one image the passes read and write, with its view.
struct SeaImage
{
    VkImage       image      = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    VkImageView   view       = VK_NULL_HANDLE;
};

// Section 3. One cascade is Chapter 29's ocean: the same images and the same sets,
// plus a foam map that remembers (section 8).
struct Cascade
{
    SeaImage                       h0;            // rg32f
    std::array<SeaImage, 2>        spectrumA;     // rgba32f, the FFT's ping-pong
    std::array<SeaImage, 2>        spectrumB;     // rgba32f
    SeaImage                       displacement;  // rgba16f
    SeaImage                       normals;       // rgba16f: normal xyz, Jacobian w
    SeaImage                       foam;          // rgba16f, r used: section 8, kept from frame to frame
    std::array<VkDescriptorSet, 2> fftSets{};
    VkDescriptorSet                set = VK_NULL_HANDLE;   // Chapter 29's ocean set, plus binding 6, the foam
};

// GPU milliseconds per stage of the frame (section 4).
struct SeaTimings
{
    double waves    = 0.0;   // the spectra, if rebuilt, and animate
    double fft      = 0.0;
    double maps     = 0.0;   // assemble, foam, the preview, and the hand-overs
    double surface  = 0.0;
};

class SeaDemo final : public Demo
{
public:
    SeaDemo();   // CPU only: where the camera starts

    const char*          Name() const override { return "Sea"; }
    InitializationResult Setup(const DemoContext& context) override;                    // sections 3, 4, 9
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // nothing sized to the window
    void                 Update(const FrameInput& input) override;                      // sections 3, 5
    void                 Record(const RecordContext& frame) override;                   // sections 3, 4, 8, 9
    void                 Teardown() override;                                           // section 3
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult   CreateImages();                             // section 3
    InitializationResult   CreateDescriptors();                        // section 3
    InitializationResult   CreateComputePipelines();                   // section 3, grown in 8
    InitializationResult   CreateSurface();                            // section 4, grown in 9
    glm::vec2              Band(uint32_t cascade) const;               // section 2
    SeaSpectrumParameters  PackSpectrum(uint32_t cascade) const;       // section 3, grown in 5-7
    ocean::OceanParameters PackCascade(uint32_t cascade) const;        // section 3
    SeaParameters          PackSurface() const;                        // section 4, grown in 8 and 10
    void RecordWaves(VkCommandBuffer commandBuffer, uint32_t frameIndex);   // section 3, grown in 8
    void RecordFft(VkCommandBuffer commandBuffer);                          // section 3
    void RecordSurface(VkCommandBuffer commandBuffer, const RecordContext& frame,
                       const SeaParameters& parameters);                    // section 4

    // Chapter 29's N, for every cascade.
    static constexpr uint32_t FFT_SIZE   = 256;
    static constexpr uint32_t FFT_STAGES = std::countr_zero(FFT_SIZE);   // log2(N)
    static_assert(std::has_single_bit(FFT_SIZE), "The FFT needs a power of two.");

    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;   // set 0, the camera

    // Section 3: three of Chapter 29's oceans, and one preview they share.
    std::array<Cascade, SEA_CASCADE_COUNT> m_cascades;
    SeaImage                       m_preview;                          // rgba8
    VkDescriptorSet                m_previewTexture = VK_NULL_HANDLE;  // ImGui's name for m_preview

    VkDescriptorSetLayout m_fftSetLayout     = VK_NULL_HANDLE;
    VkDescriptorSetLayout m_cascadeSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool      m_descriptorPool   = VK_NULL_HANDLE;

    VkPipelineLayout m_fftLayout        = VK_NULL_HANDLE;
    VkPipelineLayout m_cascadeLayout    = VK_NULL_HANDLE;
    VkPipeline       m_fftPipeline      = VK_NULL_HANDLE;   // Chapter 29's
    VkPipeline       m_spectrumPipeline = VK_NULL_HANDLE;   // section 3
    VkPipeline       m_animatePipeline  = VK_NULL_HANDLE;   // Chapter 29's
    VkPipeline       m_assemblePipeline = VK_NULL_HANDLE;   // Chapter 29's
    VkPipeline       m_previewPipeline  = VK_NULL_HANDLE;   // Chapter 29's
    VkPipeline       m_foamPipeline     = VK_NULL_HANDLE;   // section 8

    // Section 4: the surface.
    VkSampler             m_sampler          = VK_NULL_HANDLE;
    VkDescriptorSetLayout m_surfaceSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool      m_surfacePool      = VK_NULL_HANDLE;
    VkDescriptorSet       m_surfaceSet       = VK_NULL_HANDLE;
    VkPipelineLayout      m_surfaceLayout    = VK_NULL_HANDLE;
    VkPipeline            m_surfacePipeline  = VK_NULL_HANDLE;

    // Section 4: what each stage costs.
    vulkan_graphics::GpuTimestamps m_timestamps;

    // Section 9: the engine's sky, behind the sea and in it (Chapter 23).
    vulkan_graphics::Sky m_sky;

    // CPU state: survives Teardown, so switching back finds everything as it was.
    SeaSettings           m_settings;
    SpectrumConstants     m_constants;
    SeaTimings            m_timings;
    scene::Camera         m_camera;
    scene::Transform      m_cameraTransform;
    scene::CameraControls m_controls;
    float                 m_time          = 0.0f;   // ocean seconds: scaled by timeScale
    float                 m_deltaTime     = 0.0f;   // ocean seconds since the last frame
    bool                  m_spectrumDirty = true;   // the spectra must be rebuilt before they are next read
    bool                  m_foamHistory   = false;  // section 8: the foam maps hold foam worth keeping
    bool                  m_skyOn         = false;  // section 9: this frame's sky setting is not Off
    bool                  m_cloudsOn      = false;  // section 10: and it has clouds
};

} // namespace pf::demos::sea
```

Three structs before the class are new. `SeaSettings` is what the panel edits,
split by cost as Chapter 29's is. `SpectrumConstants` holds the numbers section
5 works out on the CPU, once per change. `Cascade` is the heart of it: one
cascade is *all* of Chapter 29's images and sets, plus a foam map. `SeaImage` is
Chapter 29's `OceanImage` under this demo's name.

### Where everything lands

```text
Shaders/Sea/
  SeaTypes.h                C++/GLSL twins: SeaSpectrumParameters, SeaParameters    section 3
  SeaSpectrum.comp.glsl     one cascade's starting waves, its band only            sections 3, 5-7
  SeaFoam.comp.glsl         foam that remembers                                    section 8
  SeaSurface.vert.glsl      Chapter 29's grid, moved by every cascade              section 4
  SeaSurface.frag.glsl      water, from every cascade's slopes and foam            sections 4, 8, 10
Shaders/Ocean/              Chapter 29's, used as they are:
  FftStage.comp.glsl, OceanAnimate.comp.glsl, OceanAssemble.comp.glsl,
  OceanPreview.comp.glsl, Ocean.glsl, OceanTypes.h
Source/PillowFort/Demos/Sea/
  SeaDemo.h/.cpp            the demo
Source/SandboxGame/Main.cpp + one registration line                                section 3
```

```text
SeaDemo.cpp
  includes
  static sunTravelDirection, azimuthDirection                  Chapter 29's, and one more
  namespace pf::demos::sea {
      using namespace vulkan_graphics;
      PI, GRAVITY, BAND_WAVES, SWELL_PEAK_ENHANCEMENT          sections 2, 5, 7
      static jonswapEnergy, jonswapVariance                    section 5
      static spreadNormalization                               section 6
      static spectrumConstants                                 sections 5-7
      static createSeaImage, destroySeaImage                   Chapter 29's, copied
      static VIEW_NAMES, drawPreviewPanel                      Chapter 29's, for one cascade
      static drawSeaPanel                                      section 3, grown in 5-8
      SeaDemo::SeaDemo                                         section 3
      SeaDemo::Setup                                           sections 3 and 4
      SeaDemo::CreateImages, CreateDescriptors                 section 3
      SeaDemo::CreateComputePipelines                          section 3, grown in 8
      SeaDemo::CreateSurface                                   section 4
      SeaDemo::Resize                                          (nothing)
      SeaDemo::Update                                          sections 3, 5
      SeaDemo::Band                                            section 2
      SeaDemo::PackSpectrum                                    section 3, whole in 5-7
      SeaDemo::PackCascade                                     section 3
      SeaDemo::PackSurface                                     section 4, grown in 8
      SeaDemo::RecordFft                                       section 3
      SeaDemo::RecordWaves                                     section 3, grown in 8
      SeaDemo::RecordSurface                                   section 4
      SeaDemo::Record                                          section 3, grown in 4 and 8; Appendix A
      SeaDemo::Teardown                                        section 3
  }
```

`SeaDemo.cpp` includes `SeaDemo.h`, `PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/Scene/ColorSpace.h`, `PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<imgui.h>`,
`<imgui_impl_vulkan.h>`, `<algorithm>`, `<cmath>`, `<string>`, and `<vector>`.

> **Rerun `GenerateProjects.bat`** after creating these files, and again
> whenever a later section adds one.

---
# Part 1 — Cascades (sections 1-4)

Sections 1 and 2 have no code: they are why one patch is not enough, and how
to share the waves between three. Section 3 builds the three cascades out of
Chapter 29's passes and shows their bands in the preview, and section 4 adds
them up into one surface.

## 1. Why one patch is not enough

A patch of `N` texels across `L` metres holds the waves that fit a whole number
of times across it (Chapter 29 section 2). The longest is the patch itself, one
wave across. The shortest is two texels long, `2L / N`, because a wave needs a
crest and a trough. At `N = 256`:

| Patch `L` | Longest wave | Shortest wave | Repeats every |
| --- | --- | --- | --- |
| 300 m (Chapter 29) | 300 m | 2.3 m | 300 m |
| 37 m | 37 m | 29 cm | 37 m |
| 7 m | 7 m | 5.5 cm | 7 m |

Every row is a trade. A big patch has the long swells and nothing smaller than
a couple of metres, so the water near the camera is smooth, as if under oil. A
small patch has the ripples, but the whole pattern comes back every `L` metres,
and from a hundred metres up the repeats line up into a grid you see at once.
More texels move both ends together: `N = 512` has twice the range for four
times the texels and a little more than four times the FFT's work, and covering
250 m to 5 cm in one patch would take `N` near 10,000, a hundred million texels.

The way out is to use several patches of different sizes and **add them up**.
Each is a complete Chapter 29 ocean with its own `L`, and the vertex shader
moves the grid by the sum of their displacements. These patches are called
**cascades**.

### When does the sum repeat?

Each cascade still repeats, every `L` metres of its own. The sum of two repeats
only where both do at once, at the shortest distance that is a whole number of
each: their **least common multiple**. For 250 m and 40 m that is 1000 m,
because `4 × 250 = 25 × 40`. For 250 m and 37 m it is 9250 m: 37 is a prime that
does not divide 250, so the two patterns line up only after `37 × 250` metres. So
pick sizes whose ratio is not a simple fraction, and the combined pattern does
not repeat anywhere you can see.

That is not the whole story, and it is worth being exact about it. The largest
cascade on its own still repeats every 250 m, and so does its pattern of big
waves. What the eye locks onto in Chapter 29's grid is *everything* repeating
at once — the same ripples on the same swell. With cascades the 37 m detail
lands on a different part of the 250 m swell each time, and the repeats stop
looking like repeats. From a few hundred metres up the 250 m one can still be
found if you look for it; at a grazing angle, which is how a sea is usually seen,
the haze hides it.

## 2. Bands: each wave in exactly one cascade

If cascade 0 and cascade 1 both held the 10 m waves, the sum would hold them
twice: twice their energy, and `√2` times their height. So every wave has to
belong to exactly one cascade. Each cascade gets a **band** of wavelengths, and
the bands meet without overlapping: cascade 0 the longest waves, cascade 2 the
shortest.

Where should cascade 1 take over from cascade 0? Two things limit the choice.

- **Not near cascade 1's own patch size.** A wave as long as its patch *is* the
  repeating pattern: one crest per 37 m, every 37 m. A cascade's longest waves
  are the ones that give its repeat away, so cascade 1 keeps only waves that fit
  at least 6 times across its patch: its longest is `37 / 6 = 6.2` m. Longer
  waves belong to cascade 0.
- **Not near cascade 0's shortest wave.** A wave two texels long is drawn as a
  zigzag, and the sampler's blending between texels cannot round it off. Waves
  look like waves from about 6 texels up. Cascade 0's texels are
  `250 / 256 = 0.98` m, so its shortest wave should be at least 5.9 m.

The first rule puts the boundary at `L1 / 6`; the second needs `L1 / 6` to be at
least 6 texels of cascade 0, `6 L0 / N`. Both hold when

```text
L1 / 6  >=  6 L0 / N          so          L0 / L1  <=  N / 36  =  7.1   at N = 256
```

**Neighbouring cascades can be at most about 7 times apart in size.** Six is a
choice, not a law: four lets more of each repeat show, eight leaves fewer
wavelengths per cascade and needs more cascades for the same range.

The worked example, with the sizes this chapter uses:

| Cascade | Patch | Texel | Band of wavelengths | Shortest, in its texels | Longest, per its patch |
| --- | --- | --- | --- | --- | --- |
| 0 | 250 m | 98 cm | 250 m to 6.2 m | 6.3 | 1 (it has no larger cascade above it) |
| 1 | 37 m | 14 cm | 6.2 m to 1.17 m | 8.1 | 1/6 |
| 2 | 7 m | 2.7 cm | 1.17 m to 5.5 cm | 2 (its last waves are as fine as it can hold) | 1/6 |

`250 / 37 = 6.8` and `37 / 7 = 5.3`, both under 7.1.

The shaders think in wave numbers, `|k| = 2π / wavelength`, so the boundaries
become `6 · 2π / 37 = 1.02` and `6 · 2π / 7 = 5.39` radians per metre. Cascade 0
starts at 0 — it takes every wave too long for the others, down to its own
`2π / 250` — and cascade 2 has no upper end: whatever its texels can hold is
its. **This is `Band`**:

```cpp
glm::vec2 SeaDemo::Band(uint32_t cascade) const
{
    constexpr float NO_LIMIT = 1.0e9f;
    if (m_settings.solo >= 0)
    {
        return { 0.0f, NO_LIMIT };
    }
    const auto& sizes   = m_settings.patchSizes;
    const float lowest  = cascade == 0 ? 0.0f : BAND_WAVES * 2.0f * PI / sizes[cascade];
    const float highest = cascade + 1 == SEA_CASCADE_COUNT ? NO_LIMIT : BAND_WAVES * 2.0f * PI / sizes[cascade + 1];
    return { lowest, highest };
}
```

with its constant, inside the namespace near the top of `SeaDemo.cpp`:

```cpp
// Section 2. Each cascade starts where its own patch holds BAND_WAVES waves across.
constexpr float BAND_WAVES = 6.0f;
```

The panel's **Solo** gives one cascade every wave it can hold, alone, so that
you can compare the sea with a single Chapter 29 patch of the same size.

Does it work — is every wave counted once? Section 5 has the measure for it, a
sea's significant wave height. Computed from the spectrum's formula it is
2.51 m; added up from the three cascades' texels it is 2.51 m too.

## 3. A cascade is Chapter 29's ocean

> **Jump:** until now an ocean was a set of images and passes you had one of.
> Here it is a value you have three of. Keep in mind from this section on that
> every one of Chapter 29's passes runs three times, each time with one
> cascade's descriptor set bound and that cascade's patch size pushed, and that
> nothing in the shaders knows there are three.

### What is reused, and how

Four of Chapter 29's compute shaders do exactly what a cascade needs, given its
patch size, so they are used as they are:

| Shader | Its job here | What it reads from `OceanParameters` |
| --- | --- | --- |
| `Ocean/FftStage.comp` | one FFT stage | nothing: it pushes `FftParameters` |
| `Ocean/OceanAnimate.comp` | the waves at this moment | `patchSize`, `time`, `loopPeriod` (left at 0) |
| `Ocean/OceanAssemble.comp` | displacement, normal, Jacobian | `choppiness`, `flags` (left at 0) |
| `Ocean/OceanPreview.comp` | the panel's picture | `view`, `previewGain`, `foamThreshold` |

Chapter 29's spectrum pass is not reused: it fills every texel, and a cascade
must fill only its band. This section's own spectrum pass replaces it.

Using another demo's shaders takes three things, none of them new. The C++ names
the compiled file by its path under `Shaders/`, `"Ocean/OceanAnimate.comp.spv"`,
which Chapter 06's glob already builds. It includes `Ocean/OceanTypes.h` for
`OceanParameters` and `FftParameters`, and fills them in. And the new shaders
include Chapter 29's GLSL by a path relative to their own folder,
`#include "../Ocean/Ocean.glsl"`, which `GL_GOOGLE_include_directive` resolves
from the file that does the including.

Two helpers are copied rather than shared: Chapter 29's `OceanImage` becomes
`SeaImage` in the class map above, and its file-scope `createOceanImage` and
`destroyOceanImage` become `createSeaImage` and `destroySeaImage` in
`SeaDemo.cpp`, unchanged but for the names. They are `static` in
`OceanDemo.cpp`, and this is their second user. The tutorial's rule is to write a
pattern twice before making it shared; a third user should move them into
`VulkanResources`.

### The twin structs

**This is `Shaders/Sea/SeaTypes.h`**, whole. The sections that read each field
explain it:

```c
/* Shaders/Sea/SeaTypes.h - Chapter 30's C++/GLSL twins. GLSL includes it as
   "SeaTypes.h", C++ as "Sea/SeaTypes.h". The FFT's own types are Chapter 29's
   OceanTypes.h, used as they are. */
#ifndef PF_SEA_TYPES_H
#define PF_SEA_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

/* Patches of different sizes, each holding its own band of waves (section 2). */
#define SEA_CASCADE_COUNT 3

/* SeaSpectrumParameters::model (section 5). */
#define SEA_SPECTRUM_PHILLIPS 0u   /* Chapter 29's */
#define SEA_SPECTRUM_JONSWAP  1u

/* SeaParameters::flags */
#define SEA_FLAG_FOAM_RESET 1u     /* section 8: the foam maps hold nothing worth keeping */
#define SEA_FLAG_SKY        2u     /* section 9: the engine's sky is on, and its cube can be sampled */
#define SEA_FLAG_CLOUDS     4u     /* section 10: and its clouds are on, so their cube is worth reading */

#ifdef __cplusplus
    namespace pf::demos::sea {
    using shared::vec4;
    using shared::uint;
#endif

/* The spectrum pass's push constants, one cascade at a time (sections 3-7). */
struct SeaSpectrumParameters
{
    vec4  wind;               /*  0  xy: unit direction the wind blows toward, in x and z; z: speed, m/s; w: JONSWAP's alpha */
    vec4  windShape;          /* 16  x: the peak's angular frequency, rad/s; y: gamma; z: spread s; w: the spread's normalization */
    vec4  swell;              /* 32  xy: unit direction the swell travels; z: its peak frequency, rad/s; w: its alpha, 0 = none */
    vec4  swellShape;         /* 48  x: gamma; y: spread s; z: the spread's normalization; w unused */
    vec4  band;               /* 64  x, y: the lowest and highest |k| this cascade holds, rad/m; z: patch size, m; w: suppression, m */
    float phillipsAmplitude;  /* 80  Chapter 29's A */
    uint  model;              /* 84  SEA_SPECTRUM_* */
    uint  seed;               /* 88  which random sea */
    uint  cascade;            /* 92  which cascade: each draws its own random numbers */
};

/* The surface's push constants, and the foam pass's (sections 4, 8, and 10). */
struct SeaParameters
{
    vec4  patchSizes;         /*   0  xyz: each cascade's patch side, metres; w unused */
    vec4  weights;            /*  16  xyz: 1 where a cascade is drawn, 0 where it is not (the panel's "Solo"); w unused */
    vec4  sunDirection;       /*  32  xyz: unit direction sunlight travels; w unused */
    vec4  sunIrradiance;      /*  48  rgb: the sun's irradiance, in the scene's units (Chapter 16); w unused */
    vec4  waterColor;         /*  64  rgb linear: the fraction of light the water sends back up; a unused */
    vec4  skyColor;           /*  80  rgb linear: Chapter 29's horizon, when the engine's sky is off; a unused */
    float hazeDistance;       /*  96  metres */
    float foamThreshold;      /* 100  a Jacobian below this makes foam */
    float foamFade;           /* 104  seconds for old foam to fade to 37% */
    float deltaTime;          /* 108  ocean seconds since the last frame */
    uint  tiles;              /* 112  patches drawn along each side, an odd number */
    uint  flags;              /* 116  SEA_FLAG_* */
    uint  padding0;           /* 120 */
    uint  padding1;           /* 124 */
};

#ifdef __cplusplus
    static_assert(sizeof(SeaSpectrumParameters) == 96, "SeaSpectrumParameters layout drifted.");
    static_assert(offsetof(SeaSpectrumParameters, phillipsAmplitude) == 80, "SeaSpectrumParameters alignment drifted.");
    static_assert(sizeof(SeaParameters) == 128, "SeaParameters layout drifted.");
    static_assert(offsetof(SeaParameters, hazeDistance) == 96, "SeaParameters alignment drifted.");
    }
#endif

#endif
```

Two push-constant blocks. `SeaSpectrumParameters` is the spectrum pass's, one
cascade at a time; most of it is Part 2's. `SeaParameters` is the surface's,
and the foam pass's in section 8. Both are under Chapter 08 section 5's 128
bytes, and both are made of `vec4`s and 4-byte scalars in an order that needs no
padding.

### Three sets of images

**This is `CreateImages`.** It is Chapter 29's, run for each cascade, with one
more image per cascade that section 8 explains:

```cpp
InitializationResult SeaDemo::CreateImages()
{
    // Chapter 29's images for every cascade, all but the preview, and the foam map
    // that section 8 adds. One preview serves them all.
    const VkImageUsageFlags storage           = VK_IMAGE_USAGE_STORAGE_BIT;
    const VkImageUsageFlags storageAndSampled = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    struct Entry
    {
        SeaImage*         image;
        VkFormat          format;
        VkImageUsageFlags usage;
    };
    std::vector<Entry> images;
    for (Cascade& cascade : m_cascades)
    {
        images.insert(images.end(), {
            { &cascade.h0,           VK_FORMAT_R32G32_SFLOAT,       storage },
            { &cascade.spectrumA[0], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
            { &cascade.spectrumA[1], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
            { &cascade.spectrumB[0], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
            { &cascade.spectrumB[1], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
            { &cascade.displacement, VK_FORMAT_R16G16B16A16_SFLOAT, storageAndSampled },
            { &cascade.normals,      VK_FORMAT_R16G16B16A16_SFLOAT, storageAndSampled },
            { &cascade.foam,         VK_FORMAT_R16G16B16A16_SFLOAT, storageAndSampled },   // section 8
        });
    }
    images.push_back({ &m_preview, VK_FORMAT_R8G8B8A8_UNORM, storageAndSampled });

    for (const Entry& entry : images)
    {
        if (!createSeaImage(m_context.vulkan, entry.format, FFT_SIZE, entry.usage, *entry.image))
        {
            return InitializationResult::failure("Creating a sea image failed.");
        }
    }

    // Every image is first touched by a compute shader, in GENERAL (Chapter 29 section 4).
    immediateSubmit(m_context.vulkan, [&](VkCommandBuffer commandBuffer) {
        for (const Entry& entry : images)
        {
            transitionImage(commandBuffer, entry.image->image,
                            VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                            VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                            VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                            VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        }
    });
    return InitializationResult::success();
}
```

Twenty-five images: Chapter 29's seven per cascade, a foam map per cascade, and
one preview, which shows whichever cascade the panel picks. Chapter 29's
list was a fixed array; here it is built in a loop, so it is a `std::vector`.
Every image starts in `GENERAL`, as Chapter 29's did.

**This is `CreateDescriptors`.** It is Chapter 29's too, with the allocation
and the writes inside a loop over the cascades:

```cpp
InitializationResult SeaDemo::CreateDescriptors()
{
    // A cascade's set is Chapter 29's six storage images plus the foam: seven per
    // shader stage, where Vulkan guarantees four.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &properties);
    if (properties.limits.maxPerStageDescriptorStorageImages < 7)
    {
        return InitializationResult::failure("The sea needs seven storage images per shader stage.");
    }

    // Chapter 29's two layouts, the cascade's one binding longer: the FFT's set uses
    // bindings 0-3, a cascade's set all seven.
    std::array<VkDescriptorSetLayoutBinding, 7> bindings{};
    for (uint32_t i = 0; i < bindings.size(); ++i)
    {
        bindings[i] = VkDescriptorSetLayoutBinding{
            .binding         = i,
            .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            .descriptorCount = 1,
            .stageFlags      = VK_SHADER_STAGE_COMPUTE_BIT,
        };
    }
    VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 4,
        .pBindings    = bindings.data(),
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_fftSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the FFT.");
    }
    layoutInfo.bindingCount = 7;
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_cascadeSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the cascades.");
    }

    // Three sets per cascade: the FFT's two and its own. 4 + 4 + 7 storage images.
    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, (4 + 4 + 7) * SEA_CASCADE_COUNT };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 3 * SEA_CASCADE_COUNT,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the sea.");
    }

    std::array<VkDescriptorImageInfo, 15 * SEA_CASCADE_COUNT> infos{};
    std::array<VkWriteDescriptorSet, 15 * SEA_CASCADE_COUNT>  writes{};
    uint32_t count = 0;
    const auto add = [&](VkDescriptorSet set, uint32_t binding, const SeaImage& image) {
        infos[count]  = VkDescriptorImageInfo{ .imageView = image.view, .imageLayout = VK_IMAGE_LAYOUT_GENERAL };
        writes[count] = VkWriteDescriptorSet{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = set,
            .dstBinding      = binding,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_IMAGE,
            .pImageInfo      = &infos[count],
        };
        ++count;
    };

    for (Cascade& cascade : m_cascades)
    {
        const VkDescriptorSetLayout layouts[] = { m_fftSetLayout, m_fftSetLayout, m_cascadeSetLayout };
        VkDescriptorSet             sets[3]{};
        const VkDescriptorSetAllocateInfo allocateInfo{
            .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            .descriptorPool     = m_descriptorPool,
            .descriptorSetCount = 3,
            .pSetLayouts        = layouts,
        };
        if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, sets) != VK_SUCCESS)
        {
            return InitializationResult::failure("vkAllocateDescriptorSets failed for the sea.");
        }
        cascade.fftSets = { sets[0], sets[1] };
        cascade.set     = sets[2];

        // Chapter 29's table, for this cascade's images.
        for (uint32_t s = 0; s < 2; ++s)
        {
            add(cascade.fftSets[s], 0, cascade.spectrumA[s]);
            add(cascade.fftSets[s], 1, cascade.spectrumB[s]);
            add(cascade.fftSets[s], 2, cascade.spectrumA[1 - s]);
            add(cascade.fftSets[s], 3, cascade.spectrumB[1 - s]);
        }
        add(cascade.set, 0, cascade.h0);
        add(cascade.set, 1, cascade.spectrumA[0]);
        add(cascade.set, 2, cascade.spectrumB[0]);
        add(cascade.set, 3, cascade.displacement);
        add(cascade.set, 4, cascade.normals);
        add(cascade.set, 5, m_preview);        // every cascade's set names the one preview
        add(cascade.set, 6, cascade.foam);     // section 8
    }
    vkUpdateDescriptorSets(m_context.vulkan.device, count, writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

What changed from Chapter 29, and why:

- **Each cascade gets three sets**: the FFT's two, which ping-pong, and its own,
  which every other pass binds. The pool holds nine sets and 45 storage images.
- **A cascade's set has a seventh binding**, the foam map (section 8). Chapter
  29's shaders declare only bindings 0 to 5, and a shader may use a subset of
  its set's bindings, so they do not notice. The limit check asks for seven.
- **Every cascade's binding 5 is the same image**, the one preview. The preview
  pass binds the set of the cascade it shows.

### The pipelines

**This is `CreateComputePipelines`.** Chapter 29's two layouts, and a table
of passes in which four of five rows load Chapter 29's shaders:

```cpp
InitializationResult SeaDemo::CreateComputePipelines()
{
    // Chapter 29's two layouts. Every pass but the FFT binds a cascade's set and
    // pushes up to 128 bytes: Chapter 29's passes an OceanParameters, the spectrum a
    // SeaSpectrumParameters, the foam a SeaParameters. Each reads its own struct.
    const VkPushConstantRange fftRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(ocean::FftParameters),
    };
    const VkPipelineLayoutCreateInfo fftLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_fftSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &fftRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &fftLayoutInfo, nullptr, &m_fftLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the FFT.");
    }

    const VkPushConstantRange cascadeRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(ocean::OceanParameters),   // 128, the largest of the three
    };
    const VkPipelineLayoutCreateInfo cascadeLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_cascadeSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &cascadeRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &cascadeLayoutInfo, nullptr, &m_cascadeLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the cascades.");
    }

    // Four of the six are Chapter 29's shaders, loaded as they are.
    const struct
    {
        VkPipeline*      pipeline;
        const char*      shader;
        VkPipelineLayout layout;
    } passes[] = {
        { &m_fftPipeline,      "Ocean/FftStage.comp.spv",      m_fftLayout },       // Chapter 29 section 5
        { &m_spectrumPipeline, "Sea/SeaSpectrum.comp.spv",     m_cascadeLayout },   // section 3
        { &m_animatePipeline,  "Ocean/OceanAnimate.comp.spv",  m_cascadeLayout },   // Chapter 29 section 8
        { &m_assemblePipeline, "Ocean/OceanAssemble.comp.spv", m_cascadeLayout },   // Chapter 29 section 9
        { &m_previewPipeline,  "Ocean/OceanPreview.comp.spv",  m_cascadeLayout },   // Chapter 29 section 6
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_context.vulkan.device, m_context.pipelineCache,
                                               pass.shader, pass.layout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating a sea compute pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

One layout serves the cascade passes, and they push three different structs: an
`OceanParameters` for Chapter 29's passes, a `SeaSpectrumParameters` for the
spectrum, and in section 8 a `SeaParameters` for the foam. A push constant is
only bytes, and each shader reads the struct it declares from the start of the
range, so one range of 128 bytes — the largest of the three — serves all of
them, as long as each pass pushes its struct before its dispatch.

### The spectrum, one band at a time

**This is `Shaders/Sea/SeaSpectrum.comp.glsl`, as Part 1 has it.** Its top
includes Chapter 29's types and complex-number helpers by a path relative to
its own folder:

```glsl
// Shaders/Sea/SeaSpectrum.comp.glsl - one cascade's starting waves, h0(k): Chapter 29's
// random amplitudes, sized by Phillips or by JONSWAP with a swell, for the waves in this
// cascade's band only (sections 3-7). Runs when a spectrum setting changes.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SeaTypes.h"
#include "../Ocean/OceanTypes.h"   // OCEAN_GROUP_SIZE. The path is relative to this file.
#include "../Ocean/Ocean.glsl"     // PI, GRAVITY, waveVector
#include "Random.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 0, rg32f) uniform writeonly image2D h0;

layout(push_constant) uniform PushConstants
{
    SeaSpectrumParameters spectrum;
};
```

Then two of Chapter 29's functions, copied from its `OceanSpectrum.comp.glsl`.
`gaussianPair` is unchanged. `phillips` now takes `|k|` from its caller, which
has already kept `k = 0` out, and leaves the suppression and `Δk²` to `main`,
because they now apply to every spectrum the shader knows:

```glsl
// Chapter 29 section 7, unchanged: two Gaussian random numbers from two uniform ones.
vec2 gaussianPair(inout uint state)
{
    float u1 = 1.0 - randomFloat(state);   // (0, 1]: log(0) would be minus infinity
    float u2 = randomFloat(state);         // [0, 1)
    // The max: -2 ln u1 is never negative in exact arithmetic, but Vulkan lets a GPU's
    // log be off by up to 2^-21 near 1, so for u1 at or just below 1 the product can be
    // a hair below 0. Its square root is a NaN, which the FFT spreads over every texel.
    float radius = sqrt(max(-2.0 * log(u1), 0.0));
    float angle  = 2.0 * PI * u2;
    return radius * vec2(cos(angle), sin(angle));
}
```

```glsl
// Chapter 29 section 7's Phillips spectrum: energy per unit of wave-vector area, m^4.
// The caller has already kept k = 0 out.
float phillips(vec2 k, float kLength)
{
    float windSpeed   = spectrum.wind.z;
    float largestWave = windSpeed * windSpeed / GRAVITY;   // L = V^2 / g
    float k2          = kLength * kLength;
    float alignment   = dot(k / kLength, spectrum.wind.xy);

    float density = spectrum.phillipsAmplitude
                  * exp(-1.0 / (k2 * largestWave * largestWave)) / (k2 * k2)   // the shape
                  * alignment * alignment;                                     // along the wind
    if (alignment < 0.0) { density *= 0.05; }   // little runs against the wind
    return density;
}
```

`seaDensity` is the one place that decides which spectrum the sea has. For Part
1 it is Chapter 29's, and section 5 writes it whole:

```glsl
// Sections 5-7: the energy this sea puts in the wave k, per unit of wave-vector area.
float seaDensity(vec2 k, float kLength)
{
    return phillips(k, kLength);   // Part 1: Chapter 29's spectrum. Section 5 replaces this.
}
```

And `main`, which is final as it stands:

```glsl
void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(h0).x;
    if (texel.x >= n || texel.y >= n) { return; }

    vec2  k       = waveVector(texel, n, spectrum.band.z);
    float kLength = length(k);

    // Section 3: only the waves in this cascade's band. Chapter 29's empty row and
    // column, and k = 0, which is no wave, stay empty too.
    bool inBand = kLength > 1e-6 && kLength >= spectrum.band.x && kLength < spectrum.band.y;
    vec2 value  = vec2(0.0);
    if (inBand && texel.x != 0 && texel.y != 0)
    {
        float density = seaDensity(k, kLength)
                      * exp(-kLength * kLength * spectrum.band.w * spectrum.band.w);   // no tiny ripples

        // One texel stands for dk^2 of wave-vector area, and this cascade's dk is its own.
        float dk = 2.0 * PI / spectrum.band.z;

        // Each cascade draws its own random numbers: the same seed must not give
        // three cascades the same waves.
        uint state = seedRandom(uint(texel.y * n + texel.x) + spectrum.cascade * uint(n * n), spectrum.seed);
        value      = gaussianPair(state) * sqrt(density * dk * dk / 2.0);
    }
    imageStore(h0, texel, vec4(value, 0.0, 0.0));
}
```

Against Chapter 29's `main`, three lines matter:

- **The band test.** `band.x` and `band.y` are `Band`'s two numbers. A texel
  outside them stays zero, so this cascade's spectrum has a hole where the
  longer waves are and nothing past its upper end. The preview shows it.
- **`dk` is this cascade's.** Chapter 29 section 7's `Δk = 2π / L`, with the
  cascade's own `L`. Cascade 1's texels are each `2π / 37 = 0.17` rad/m wide,
  cascade 0's `2π / 250 = 0.025`, so a texel of cascade 1 stands for 46 times
  as much wave-vector area. That is how three grids of different spacing add up
  to one spectrum, each wave counted once with the right weight.
- **The seed.** Each cascade adds `cascade · N²` to its texel's index before
  hashing, so that one seed gives three different sets of random numbers.
  Without it, texel `(n, m)` would get the same random phase in every cascade.

### Packing, per cascade

`PackCascade` is what Chapter 29's passes read, filled in for one cascade:
its patch size, and the settings every cascade shares.

```cpp
ocean::OceanParameters SeaDemo::PackCascade(uint32_t cascade) const
{
    return ocean::OceanParameters{
        .patchSize     = m_settings.patchSizes[cascade],
        .choppiness    = m_settings.choppiness,
        .time          = m_time,
        .foamThreshold = m_settings.foamThreshold,
        .previewGain   = m_settings.previewGain,
        .view          = static_cast<uint32_t>(m_settings.view),
    };
}
```

**This is `PackSpectrum`, as Part 1 has it**, with the fields Phillips reads.
Section 5 adds the rest; `m_constants` holds what section 5 works out, and is all
zeros until then, which Phillips never reads:

```cpp
SeaSpectrumParameters SeaDemo::PackSpectrum(uint32_t cascade) const
{
    const SeaSettings&       s = m_settings;
    const SpectrumConstants& k = m_constants;
    return SeaSpectrumParameters{
        .wind              = glm::vec4(azimuthDirection(s.windAzimuth), s.windSpeed, k.alpha),
        .band              = glm::vec4(Band(cascade), s.patchSizes[cascade], s.suppression),
        .phillipsAmplitude = s.phillipsAmplitude,
        .model             = static_cast<uint32_t>(s.model),
        .seed              = static_cast<uint32_t>(s.seed),
        .cascade           = cascade,
    };
}
```

`azimuthDirection` is a file-scope helper above the namespace, beside Chapter
29's `sunTravelDirection`: the wind's direction on the water, from its azimuth,
the way Chapter 29's `PackParameters` worked it out inline.

```cpp
// File scope. A direction on the water from an azimuth: 0 is toward -Z, positive turns toward +X.
static glm::vec2 azimuthDirection(float azimuthDegrees)
{
    const float azimuth = glm::radians(azimuthDegrees);
    return { std::sin(azimuth), -std::cos(azimuth) };
}
```

### The loop over cascades

**This is `RecordFft`.** Chapter 29's, with one change that is worth a
paragraph:

```cpp
void SeaDemo::RecordFft(VkCommandBuffer commandBuffer)
{
    const uint32_t groups = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fftPipeline);

    uint32_t source = 0;
    for (uint32_t direction = 0; direction < 2; ++direction)
    {
        for (uint32_t stage = 0; stage < FFT_STAGES; ++stage)
        {
            const ocean::FftParameters fft{ .stage = stage, .direction = direction };
            vkCmdPushConstants(commandBuffer, m_fftLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(fft), &fft);

            // The same stage for every cascade, each through its own pair of sets.
            for (const Cascade& cascade : m_cascades)
            {
                vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fftLayout,
                                        0, 1, &cascade.fftSets[source], 0, nullptr);
                vkCmdDispatch(commandBuffer, groups, groups, 1);
            }

            // One barrier for all of them: the cascades touch different images, so
            // they need no order among themselves, only before the next stage.
            computeToComputeBarrier(commandBuffer);
            source = 1 - source;
        }
    }
}
```

Every stage dispatches all three cascades and then has **one** barrier. A
barrier orders everything recorded before it against everything after it, in
the stages it names (Chapter 04 section 5), so one barrier after three
dispatches makes all three stage `s` results visible to all three stage `s + 1`
reads. The three dispatches of one stage need nothing between them: each reads
and writes only its own cascade's images, so they may run in any order, or at
once. Sixteen barriers for three cascades, the same as for one. The push
constants go once per stage, because binding another set with the same layout
does not disturb them.

**This is `RecordWaves`, as Part 1 has it** — Chapter 29's `Record` steps 2 to 6,
each looping over the cascades. Section 8 puts its foam pass in as step 6, so the
preview is step 7:

```cpp
void SeaDemo::RecordWaves(VkCommandBuffer commandBuffer, uint32_t frameIndex)
{
    const uint32_t groups = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);

    // Binds cascade c's set and pushes its constants for the next dispatch.
    const auto bindCascade = [&](uint32_t c, const void* constants, uint32_t size) {
        vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_cascadeLayout,
                                0, 1, &m_cascades[c].set, 0, nullptr);
        vkCmdPushConstants(commandBuffer, m_cascadeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, size, constants);
    };

    // 2. The starting waves, after a spectrum setting changed: each cascade its band.
    if (m_spectrumDirty)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_spectrumPipeline);
        for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
        {
            const SeaSpectrumParameters spectrum = PackSpectrum(c);
            bindCascade(c, &spectrum, sizeof(spectrum));
            vkCmdDispatch(commandBuffer, groups, groups, 1);
        }
        computeToComputeBarrier(commandBuffer);
        m_spectrumDirty = false;
    }

    // 3. This moment's waves: Chapter 29's animate pass, once per cascade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_animatePipeline);
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        const ocean::OceanParameters parameters = PackCascade(c);
        bindCascade(c, &parameters, sizeof(parameters));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }
    computeToComputeBarrier(commandBuffer);
    m_timestamps.Write(commandBuffer, frameIndex, 1);

    // 4. Chapter 29's FFT, for every cascade.
    RecordFft(commandBuffer);
    m_timestamps.Write(commandBuffer, frameIndex, 2);

    // 5. Chapter 29's maps, once per cascade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_assemblePipeline);
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        const ocean::OceanParameters parameters = PackCascade(c);
        bindCascade(c, &parameters, sizeof(parameters));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }
    computeToComputeBarrier(commandBuffer);

    // 7. Chapter 29's preview, of the cascade the panel picked.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_previewPipeline);
    const uint32_t               shown   = static_cast<uint32_t>(m_settings.previewCascade);
    const ocean::OceanParameters preview = PackCascade(shown);
    bindCascade(shown, &preview, sizeof(preview));
    vkCmdDispatch(commandBuffer, groups, groups, 1);
}
```

`bindCascade` binds one cascade's set and pushes one struct, the two lines
every dispatch here needs. The barriers are Chapter 29's, one per step rather
than one per cascade, for the same reason as in the FFT. The two
`m_timestamps.Write` calls are section 4's. Step 7 runs the preview once, for
the cascade the panel picked.

`Setup` is Chapter 29's, in the same order:

```cpp
InitializationResult SeaDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }
    if (auto result = CreateImages(); !result)           { return result; }   // section 3
    if (auto result = CreateDescriptors(); !result)      { return result; }   // section 3
    if (auto result = CreateComputePipelines(); !result) { return result; }   // sections 3 and 8

    m_previewTexture = ImGui_ImplVulkan_AddTexture(m_preview.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
    m_spectrumDirty  = true;    // h0 holds garbage until the spectrum pass has run
    m_foamHistory    = false;   // and so do the foam maps (section 8)
    return InitializationResult::success();
}
```

Section 4 adds three steps after the pipelines: the engine's sky, the surface,
and the timestamps. The constructor is Chapter 29's, with one more line for
section 5's numbers:

```cpp
SeaDemo::SeaDemo()
{
    m_controls.active             = scene::ControllerKind::Fly;
    m_controls.fly.moveSpeed      = 20.0f;
    m_camera.nearPlane            = 0.5f;
    m_camera.farPlane             = 5000.0f;
    m_cameraTransform.translation = glm::vec3(0.0f, 12.0f, 0.0f);
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = glm::radians(-8.0f) });
    m_constants                   = spectrumConstants(m_settings);
}
```

and the registration goes after the ocean's in `Source/SandboxGame/Main.cpp`:

```cpp
#include "PillowFort/Demos/Sea/SeaDemo.h"
```

```cpp
    demoList.push_back(std::make_unique<demos::sea::SeaDemo>());                 // Chapter 30
```

**This is `Teardown`**, whole. It is Chapter 29's, with a loop over the
cascades' images, and the timestamps given back after ImGui's set:

```cpp
void SeaDemo::Teardown()
{
    // Chapter 09 waited for the device. Reverse order of Setup; null handles are
    // no-ops, so a partial Setup is safe. The CPU state is kept.
    if (m_previewTexture != VK_NULL_HANDLE)
    {
        ImGui_ImplVulkan_RemoveTexture(m_previewTexture);
        m_previewTexture = VK_NULL_HANDLE;
    }
    m_timestamps.Shutdown();

    const VkDevice device = m_context.vulkan.device;
    VkPipeline* pipelines[] = { &m_surfacePipeline, &m_foamPipeline, &m_previewPipeline, &m_assemblePipeline,
                                &m_animatePipeline, &m_spectrumPipeline, &m_fftPipeline };
    for (VkPipeline* pipeline : pipelines)
    {
        vkDestroyPipeline(device, *pipeline, nullptr);
        *pipeline = VK_NULL_HANDLE;
    }
    vkDestroyPipelineLayout(device, m_surfaceLayout, nullptr);
    vkDestroyDescriptorPool(device, m_surfacePool, nullptr);
    vkDestroyDescriptorSetLayout(device, m_surfaceSetLayout, nullptr);
    vkDestroySampler(device, m_sampler, nullptr);
    vkDestroyPipelineLayout(device, m_cascadeLayout, nullptr);
    vkDestroyPipelineLayout(device, m_fftLayout, nullptr);
    vkDestroyDescriptorPool(device, m_descriptorPool, nullptr);   // frees every cascade's sets
    vkDestroyDescriptorSetLayout(device, m_cascadeSetLayout, nullptr);
    vkDestroyDescriptorSetLayout(device, m_fftSetLayout, nullptr);

    for (Cascade& cascade : m_cascades)
    {
        SeaImage* images[] = { &cascade.foam, &cascade.normals, &cascade.displacement, &cascade.spectrumB[1],
                               &cascade.spectrumB[0], &cascade.spectrumA[1], &cascade.spectrumA[0], &cascade.h0 };
        for (SeaImage* image : images)
        {
            destroySeaImage(m_context.vulkan, *image);
        }
        cascade.fftSets = {};
        cascade.set     = VK_NULL_HANDLE;
    }
    destroySeaImage(m_context.vulkan, m_preview);
    m_sky.Shutdown();   // section 9
    m_sceneRenderer.Shutdown();

    m_surfaceLayout    = m_cascadeLayout = m_fftLayout = VK_NULL_HANDLE;
    m_surfacePool      = m_descriptorPool = VK_NULL_HANDLE;
    m_surfaceSetLayout = m_cascadeSetLayout = m_fftSetLayout = VK_NULL_HANDLE;
    m_sampler          = VK_NULL_HANDLE;
    m_surfaceSet       = VK_NULL_HANDLE;
}
```

`Resize` has nothing to do, as in Chapter 29: every image is `N × N`.

### The panel

**This is `drawSeaPanel`, as Part 1 has it**: the cascades, then Chapter 29's
per-frame settings, then the timings. Parts 2 and 3 add their groups. The
timings are section 4's; until it creates them, `timed` is false and their
group stays hidden. Nothing reads `constants` before section 5's "Spectrum"
group, so until then its name is commented out, as Chapter 24's `Update` does
with its frame index: an unused named parameter is `C4100` at `/W4`. With five
groups it folds them, as Chapter 21's particles do (Chapter 09 section 6): each
is a collapsing header, closed until clicked, and the timings stay in view.

```cpp
static bool drawSeaPanel(SeaSettings& settings, const SpectrumConstants& /* constants: section 5 */,
                         const SeaTimings& timings, bool timed)
{
    bool changed = false;
    if (debug_panels::beginDemoPanel("Sea", debug_panels::DemoPanelSlot::BelowCamera))
    {
        // Each group of controls folds away under its name (Chapter 09 section 6); the timings stay in view.
        if (ImGui::CollapsingHeader("Cascades (rebuild the spectra)"))
        {
            for (int c = 0; c < SEA_CASCADE_COUNT; ++c)
            {
                const std::string label = "Cascade " + std::to_string(c) + " patch (m)";
                changed |= ImGui::SliderFloat(label.c_str(), &settings.patchSizes[c], 2.0f, 2000.0f, "%.1f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
                // Section 2: the band it holds, as wavelengths.
                const bool  first   = c == 0 || settings.solo == c;
                const bool  last    = c + 1 == SEA_CASCADE_COUNT || settings.solo == c;
                const float longest = first ? settings.patchSizes[c] : settings.patchSizes[c] / BAND_WAVES;
                if (last)
                {
                    ImGui::TextDisabled("    waves %.1f m and shorter", longest);
                }
                else
                {
                    ImGui::TextDisabled("    waves %.1f m to %.2f m", longest, settings.patchSizes[c + 1] / BAND_WAVES);
                }
            }
            // The combo counts from 0; solo counts from -1, "off".
            int solo = settings.solo + 1;
            changed |= ImGui::Combo("Solo", &solo, "Off: every cascade, each its band\0"
                                                   "Cascade 0 alone, every wave it holds\0"
                                                   "Cascade 1 alone, every wave it holds\0"
                                                   "Cascade 2 alone, every wave it holds\0");
            settings.solo = solo - 1;
        }

        if (ImGui::CollapsingHeader("Every frame (free)"))
        {
            ImGui::SliderFloat("Choppiness", &settings.choppiness, 0.0f, 2.5f);
            ImGui::SliderFloat("Time scale", &settings.timeScale, 0.0f, 4.0f);
            ImGui::ColorEdit3("Water", &settings.waterColor.x);
            ImGui::ColorEdit3("Sky", &settings.skyColor.x);
            ImGui::SliderFloat("Sun elevation", &settings.sunElevation, 0.0f, 90.0f);
            ImGui::SliderFloat("Sun azimuth", &settings.sunAzimuth, -180.0f, 180.0f);
            ImGui::SliderFloat("Sun strength", &settings.sunStrength, 0.0f, 4.0f);
            ImGui::SliderFloat("Haze (m)", &settings.hazeDistance, 50.0f, 5000.0f, "%.0f", ImGuiSliderFlags_Logarithmic);
            ImGui::SliderInt("Patches each side", &settings.tileRadius, 1, 4);   // section 9's skirt needs a ring of patches
        }

        if (timed)
        {
            ImGui::SeparatorText("GPU milliseconds (section 4)");
            ImGui::Text("waves %.2f  FFT %.2f", timings.waves, timings.fft);
            ImGui::Text("maps %.2f  surface %.2f", timings.maps, timings.surface);
        }
    }
    ImGui::End();
    return changed;
}
```

Under each cascade's size it shows the band that size gives, in wavelengths,
which is section 2's table, live. Make cascade 1 more than 7.1 times smaller
than cascade 0 and you can watch cascade 0's shortest waves drop below six
texels.

The preview's panel is Chapter 29's, with a choice of cascade and only the
views that mean something for one cascade of a sea:

```cpp
// Chapter 29's preview, with the views that make sense for one cascade of a sea.
static const char* const VIEW_NAMES[] = {
    "Spectrum |h0|",
    "Height",
    "Normal",
    "Jacobian (white: foam)",
};

static void drawPreviewPanel(SeaSettings& settings, ImTextureID preview)
{
    ImGui::SetNextWindowPos(ImVec2(360.0f, 250.0f), ImGuiCond_FirstUseEver);   // under the engine's title bars
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until clicked
    if (ImGui::Begin("Sea preview"))
    {
        ImGui::Combo("Cascade", &settings.previewCascade, "0 (largest)\0" "1\0" "2 (smallest)\0");
        int view = settings.view - static_cast<int>(OCEAN_VIEW_SPECTRUM);
        ImGui::Combo("Show", &view, VIEW_NAMES, IM_ARRAYSIZE(VIEW_NAMES));
        settings.view = view + static_cast<int>(OCEAN_VIEW_SPECTRUM);
        ImGui::SliderFloat("Brightness", &settings.previewGain, 0.01f, 100.0f, "%.2f", ImGuiSliderFlags_Logarithmic);
        ImGui::Image(preview, ImVec2(256.0f, 256.0f));
    }
    ImGui::End();
}
```

The views are Chapter 29's from "Spectrum |h0|" on, so the panel's choice is
offset by `OCEAN_VIEW_SPECTRUM`. The sea itself is what this demo shows, so the
preview opens as a title bar, stacked under the engine's own; a click on it
opens it. **This is `Update`, as Part 1 has it**:

```cpp
void SeaDemo::Update(const FrameInput& input)
{
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);

    drawPreviewPanel(m_settings, reinterpret_cast<ImTextureID>(m_previewTexture));
    m_spectrumDirty |= drawSeaPanel(m_settings, m_constants, m_timings, m_timestamps.Available());

    m_deltaTime = input.deltaSeconds * m_settings.timeScale;
    m_time     += m_deltaTime;
}
```

### The frame, for now

Everything a cascade needs exists now except a `Record`, and section 4's
surface is a long way off. So, as Chapter 29's Part 1 did, `Record` starts
with the compute alone and clears the scene to the sky's color. Steps 1 and 8
are the preview's two barriers from Chapter 29 section 6; section 4 replaces
this function with one that draws the sea:

```cpp
void SeaDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // 1. Return trips: last frame's dispatches, and the preview from ImGui.
    computeToComputeBarrier(commandBuffer);
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // 2-7. Every cascade's waves and maps, and the preview.
    RecordWaves(commandBuffer, frame.frameIndex);

    // 8. The preview, to ImGui's fragment shader.
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    // Until section 4: no sea yet, only the sky's color.
    const VkClearColorValue sky{ { 0.41f, 0.60f, 0.80f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &sky);
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

The two `m_timestamps.Write` calls in `RecordWaves` do nothing yet: a
`GpuTimestamps` that was never initialized has nothing to write to.

Build and run with `--demo Sea`, and click the "Sea preview" title bar to open
it. The scene is plain blue; the preview is the point. With "Spectrum |h0|":

- **Cascade 0** is Chapter 29's round blob, its dark line across the wind
  included, cut off at a circle: section 2's boundary, beyond which the waves
  shorter than 6.2 m are not this cascade's.
- **Cascade 1** is a ring, dark in the middle where cascade 0's waves are, and
  **cascade 2** a ring further out, dimmer still (raise "Brightness").
- **Solo** one cascade on the "Sea" panel, and its hole fills in: alone, it
  holds every wave it can.
- "Height" shows each cascade's waves at its own scale, moving.

If two cascades' spectra overlap, section 2's bands are wrong, and the sum in
section 4 would count those waves twice.

## 4. Adding the cascades up

### The vertex shader: displacements add

Each cascade's displacement map says how far a point of the flat sea moves, so
the sea's displacement is their sum. Each cascade's map is read at that
cascade's own scale: the point at `x` metres reads texture coordinate `x / L`,
and the sampler's `REPEAT` wraps it, so cascade 2 repeats every 7 m while
cascade 0 repeats every 250 m, both inside the same tile.

The tiles are now just pieces of grid. Chapter 29 made them one patch wide
because there was one patch; here they stay the largest cascade's size, 250 m
and 128 quads, so that the grid is Chapter 29's.

**This is `Shaders/Sea/SeaSurface.vert.glsl`, as Part 1 has it**; section 9
adds a few lines at the edge of the grid:

```glsl
// Shaders/Sea/SeaSurface.vert.glsl - Chapter 29's grid, moved by every cascade at once (section 4).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"             // set 0: frame.viewProjection, frame.cameraPosition
#include "SeaTypes.h"
#include "../Ocean/OceanTypes.h"       // OCEAN_GRID_CELLS

// One binding per cascade, not an array of three: synchronization validation does not follow
// a shader's reads through an array of descriptors, and the barriers on these maps are worth checking.
layout(set = 1, binding = 0) uniform sampler2D displacementMap0;
layout(set = 1, binding = 1) uniform sampler2D displacementMap1;
layout(set = 1, binding = 2) uniform sampler2D displacementMap2;

layout(push_constant) uniform PushConstants
{
    SeaParameters sea;
};

layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec2 gridPosition;   // where on the flat sea this point started, metres

// One cascade's displacement at a point of the flat sea. Texel t of its maps
// belongs to the point t * L / N, and the sampler repeats them (Chapter 29 section 10).
vec3 cascadeDisplacement(sampler2D map, vec2 position, float patchSize)
{
    vec2 uv = position / patchSize + 0.5 / vec2(textureSize(map, 0));
    return textureLod(map, uv, 0.0).xyz;
}

void main()
{
    // Chapter 29's grid: which quad, and which of its six corners.
    const uvec2 corners[6] = uvec2[](uvec2(0, 0), uvec2(0, 1), uvec2(1, 1),
                                     uvec2(0, 0), uvec2(1, 1), uvec2(1, 0));
    uint  quad   = uint(gl_VertexIndex) / 6u;
    uvec2 corner = uvec2(quad % OCEAN_GRID_CELLS, quad / OCEAN_GRID_CELLS) + corners[gl_VertexIndex % 6];

    // The tiles are the largest cascade's patch. Each smaller cascade repeats inside
    // them on its own, because its sampler repeats.
    float tileSize    = sea.patchSizes.x;
    int   tiles       = int(sea.tiles);
    ivec2 tile        = ivec2(gl_InstanceIndex % tiles, gl_InstanceIndex / tiles) - tiles / 2;
    vec2  cameraPatch = floor(frame.cameraPosition.xz / tileSize);
    gridPosition      = (cameraPatch + vec2(tile)) * tileSize + vec2(corner) / float(OCEAN_GRID_CELLS) * tileSize;

    // Every cascade moves the point by its own map, read at its own scale; the sum is the sea.
    vec3 displacement = sea.weights.x * cascadeDisplacement(displacementMap0, gridPosition, sea.patchSizes.x)
                      + sea.weights.y * cascadeDisplacement(displacementMap1, gridPosition, sea.patchSizes.y)
                      + sea.weights.z * cascadeDisplacement(displacementMap2, gridPosition, sea.patchSizes.z);

    worldPosition = vec3(gridPosition.x, 0.0, gridPosition.y) + displacement;
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

The three maps are three bindings, read in three written-out lines. An array of
three textures in one binding, `sampler2D displacementMaps[3]`, would look
neater, and it is what most engines do, but it has a cost for a learner:
**synchronization validation does not follow a shader's reads through an array
of descriptors.** With one binding per map, the exit check's positive control on
the displacement's barrier fires; with the same maps in an array, the same
mistake is silent. The barriers on these maps are the part of this chapter most
worth checking, so each map gets its own binding. (A loop over an array would
also need a device feature, `shaderSampledImageArrayDynamicIndexing`, which the
tutorial does not turn on; constant indices would not.) `sea.weights` is the
panel's Solo: 1 for a cascade that is drawn, 0 for one that is not.

The grid is not denser than Chapter 29's, two metres from vertex to vertex,
and the small cascades' waves are far shorter than that. Their displacement is
centimetres, though, so what the grid misses of them cannot be seen; their
slopes are not small, and the fragment shader reads those at every pixel.

### The fragment shader: slopes add, normals do not

Two tilted surfaces on top of each other do not make the average of their
normals. What adds is **slope**: if one cascade rises 0.1 m per metre and
another 0.05 m per metre at the same spot, the sea rises 0.15 m per metre
there. Chapter 29's normal map holds `normalize(−∂h/∂x, 1, −∂h/∂z)`. Divide it
by its `y`, and the slopes come back: a normal of `(−0.0995, 0.995, 0)`, divided
by 0.995, is `(−0.1, 1, 0)`, a slope of 0.1. So each cascade's normal is turned
back into slopes, the slopes are added, and the sum is turned into a normal.

**This is `Shaders/Sea/SeaSurface.frag.glsl`, as Part 1 has it**:

```glsl
// Shaders/Sea/SeaSurface.frag.glsl - water lit from every cascade's slopes and foam, reflecting
// the engine's sky (sections 4, 8, and 10). Linear values.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"
#include "SeaTypes.h"

// One binding per cascade, as in the vertex shader.
layout(set = 1, binding = 3) uniform sampler2D normalMap0;
layout(set = 1, binding = 4) uniform sampler2D normalMap1;
layout(set = 1, binding = 5) uniform sampler2D normalMap2;

layout(push_constant) uniform PushConstants
{
    SeaParameters sea;
};

layout(location = 0) in vec3 worldPosition;
layout(location = 1) in vec2 gridPosition;

layout(location = 0) out vec4 outColor;

// Where a point of the flat sea reads a cascade's maps (as the vertex shader does).
vec2 cascadeUv(sampler2D map, vec2 position, float patchSize)
{
    return position / patchSize + 0.5 / vec2(textureSize(map, 0));
}

// A cascade's slopes, dh/dx and dh/dz. Its normal map holds normalize(-dh/dx, 1, -dh/dz)
// (Chapter 29 section 9), so dividing by y gives the slopes back.
vec2 cascadeSlope(sampler2D map, vec2 position, float patchSize)
{
    vec3 normal = texture(map, cascadeUv(map, position, patchSize)).xyz;
    return -normal.xz / normal.y;
}

// Chapter 29's sky: the horizon color, darker and bluer toward the top. When the
// engine's sky is off, this is what the water reflects (Part 4).
vec3 skyGradient(vec3 direction)
{
    float up = clamp(direction.y, 0.0, 1.0);
    return sea.skyColor.rgb * mix(vec3(1.0), vec3(0.45, 0.6, 0.85), up);
}

// What the water reflects in a direction. A reflection that points below the horizon would find
// the sky's ground; on the open sea it would find more water, about as bright as the horizon, so it
// is lifted to the horizon. Chapter 29's gradient, unless the engine's sky is on (section 10): a cube
// that was never baked holds nothing worth reading.
vec3 skyReflection(vec3 direction)
{
    direction = normalize(vec3(direction.x, max(direction.y, 0.0), direction.z));
    vec3 sky  = skyGradient(direction);
    return sky;
}

const float PI          = 3.14159265358979;
const float GLINT_POWER = 800.0;   // how tight the sun's glint is: Chapter 29's

void main()
{
    vec3 weights = sea.weights.xyz;   // the panel's "Solo"

    // Slopes add, where normals do not: the sea's slope is the sum of the cascades'.
    vec2 slope = weights.x * cascadeSlope(normalMap0, gridPosition, sea.patchSizes.x)
               + weights.y * cascadeSlope(normalMap1, gridPosition, sea.patchSizes.y)
               + weights.z * cascadeSlope(normalMap2, gridPosition, sea.patchSizes.z);
    vec3 normal = normalize(vec3(-slope.x, 1.0, -slope.y));

    vec3 toEye = normalize(frame.cameraPosition.xyz - worldPosition);
    vec3 toSun = -sea.sunDirection.xyz;
    vec3 sun   = sea.sunIrradiance.rgb;   // section 10: in the sky's units

    // 1. Reflection, with Schlick's Fresnel (Chapter 29 section 10): the sky, and the sun's glint.
    vec3  reflected = reflect(-toEye, normal);
    float facing    = clamp(dot(normal, toEye), 0.0, 1.0);
    float fresnel   = 0.02 + 0.98 * pow(1.0 - facing, 5.0);
    float lobe      = pow(max(dot(reflected, toSun), 0.0), GLINT_POWER);   // Part 1: Chapter 29's glint
    vec3  mirror    = skyReflection(reflected) + sun * lobe;

    // 2. The water's own color: the light that went in and came back out, in the sun's units. At
    //    the default sun, E / pi is (0.90, 0.85, 0.80), so this is Chapter 29's.
    float lit   = max(dot(normal, toSun), 0.0);
    vec3  body  = sea.waterColor.rgb * sun / PI * (0.4 + 0.6 * lit);
    vec3  color = mix(body, mirror, fresnel);

    // 3. Haze: far water fades into what the sky shows at the horizon straight ahead.
    float range   = length(frame.cameraPosition.xyz - worldPosition);
    vec3  horizon = skyReflection(-toEye);
    color = mix(color, horizon, 1.0 - exp(-range / sea.hazeDistance));

    outColor = vec4(color, 1.0);
}
```

The shading is Chapter 29's section 10, the same steps, with two changes:

- **The sun is an irradiance**, the panel's "Sun strength" times Chapter 11's
  sun, `π (0.90, 0.85, 0.80)`, where Chapter 29 had a color and a glint slider.
  The water's own color is Chapter 11's convention: a white surface facing a
  sun of irradiance `E` sends back `E / π`, which at the default sun is
  `(0.90, 0.85, 0.80)`, so the water looks as it did in Chapter 29. The glint is
  still Chapter 29's lobe, `cos^800`, times the sun; section 10 gives it the
  size that makes it deliver exactly the sun's light, once the water reflects a
  sky in the same units.
- **`skyReflection` lifts a direction that points below the horizon** up to the
  horizon, before it looks the sky up. A steep wave near the camera can reflect
  a direction pointing down, and the open sea has no ground to show there.

`skyGradient` is Chapter 29's `skyColor`, renamed; Part 4 puts the engine's sky
in its place whenever that sky is on.

### The surface's pipeline and set

**This is `CreateSurface`.** Chapter 29's, with eleven bindings instead of two:

```cpp
InitializationResult SeaDemo::CreateSurface()
{
    // Chapter 29's sampler: linear, and REPEAT, so each cascade's maps tile at their own size.
    const VkSamplerCreateInfo samplerInfo{
        .sType        = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter    = VK_FILTER_LINEAR,
        .minFilter    = VK_FILTER_LINEAR,
        .mipmapMode   = VK_SAMPLER_MIPMAP_MODE_NEAREST,
        .addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT,
        .addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT,
    };
    if (vkCreateSampler(m_context.vulkan.device, &samplerInfo, nullptr, &m_sampler) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateSampler failed for the sea surface.");
    }

    // Set 1: one binding per cascade and map. Displacement at 0-2 for the vertex shader; normals at
    // 3-5, foam at 6-8 (section 8), the sky's cube at 9 (section 9), and its clouds' at 10 (section
    // 10) for the fragment shader.
    std::array<VkDescriptorSetLayoutBinding, 3 * SEA_CASCADE_COUNT + 2> bindings{};
    for (uint32_t i = 0; i < bindings.size(); ++i)
    {
        bindings[i] = VkDescriptorSetLayoutBinding{
            .binding         = i,
            .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            .descriptorCount = 1,
            // The cast: ?: has the enum's type, which MSVC makes int, and braces refuse to
            // narrow an int that is not a constant (C2397).
            .stageFlags      = static_cast<VkShaderStageFlags>(i < SEA_CASCADE_COUNT ? VK_SHADER_STAGE_VERTEX_BIT
                                                                                     : VK_SHADER_STAGE_FRAGMENT_BIT),
        };
    }
    const VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(bindings.size()),
        .pBindings    = bindings.data(),
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_surfaceSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the sea surface.");
    }

    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                                         static_cast<uint32_t>(bindings.size()) };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_surfacePool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the sea surface.");
    }
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_surfacePool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_surfaceSetLayout,
    };
    if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, &m_surfaceSet) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the sea surface.");
    }

    // Each map in the layout Record moves it to before the surface draws; the sky's cube in the layout
    // Sky::Update leaves it in, with the sky's own sampler.
    const VkImageLayout readOnly = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    std::array<VkDescriptorImageInfo, bindings.size()> infos{};
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        infos[c]                         = { m_sampler, m_cascades[c].displacement.view, readOnly };
        infos[SEA_CASCADE_COUNT + c]     = { m_sampler, m_cascades[c].normals.view,      readOnly };
        infos[2 * SEA_CASCADE_COUNT + c] = { m_sampler, m_cascades[c].foam.view,         readOnly };
    }
    infos[3 * SEA_CASCADE_COUNT]     = { m_sky.CubeSampler(), m_sky.CubeView(), readOnly };
    infos[3 * SEA_CASCADE_COUNT + 1] = { m_sky.CubeSampler(), m_sky.CloudCubeView(), readOnly };   // section 10

    std::array<VkWriteDescriptorSet, bindings.size()> writes{};
    for (uint32_t i = 0; i < writes.size(); ++i)
    {
        writes[i] = VkWriteDescriptorSet{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_surfaceSet,
            .dstBinding      = i,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            .pImageInfo      = &infos[i],
        };
    }
    vkUpdateDescriptorSets(m_context.vulkan.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);

    // Set 0 the camera, set 1 the maps, SeaParameters for both shaders.
    const VkDescriptorSetLayout setLayouts[] = { m_sceneRenderer.FrameSetLayout(), m_surfaceSetLayout };
    const VkPushConstantRange   pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(SeaParameters),
    };
    const VkPipelineLayoutCreateInfo pipelineLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 2,
        .pSetLayouts            = setLayouts,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &pipelineLayoutInfo, nullptr, &m_surfaceLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the sea surface.");
    }

    // Chapter 29's pipeline: depth on, the scene's sample count, no culling.
    const GraphicsPipelineDesc desc{
        .vertexShader   = "Sea/SeaSurface.vert.spv",
        .fragmentShader = "Sea/SeaSurface.frag.spv",
        .colorFormats   = { &m_context.formats.color, 1 },
        .depthFormat    = m_context.formats.depth,
        .depthTest      = true,
        .depthWrite     = true,
        .depthCompare   = VK_COMPARE_OP_LESS,
        .cullMode       = VK_CULL_MODE_NONE,
        .frontFace      = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .layout         = m_surfaceLayout,
        .samples        = m_context.formats.samples,
    };
    m_surfacePipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
    if (m_surfacePipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the sea surface pipeline failed.");
    }
    return InitializationResult::success();
}
```

The bindings are numbered by map, then cascade: displacement 0 to 2 for the
vertex shader, normals 3 to 5 and foam 6 to 8 for the fragment shader. The foam
is section 8's, and bindings 9 and 10 are the sky's cube and its clouds' cube,
which Part 4 reads. All of them can be written now, because the foam maps exist
from `CreateImages` on and both cubes from `m_sky.Initialize`, which `Setup`
calls first. Chapters 23 and 28 leave both cubes in `SHADER_READ_ONLY_OPTIMAL`
from `Initialize` on, so naming them here is valid even while the sky is off.
The sky's own sampler goes with both views.

Because the surface's set names the sky's cubes, the sky must exist first.
`Setup` gains three steps, after `CreateComputePipelines`: the sky, the
surface, and the timestamps, which "What three cascades cost" below uses:

```cpp
    if (auto result = m_sky.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats); !result)
    {
        return result;   // section 9: before the surface, whose set names the sky's cube
    }
    if (auto result = CreateSurface(); !result)          { return result; }   // section 4
    if (auto result = m_timestamps.Initialize(m_context.vulkan, 5); !result) { return result; }   // section 4
```

`m_sky` is Chapter 23's `Sky`, which every 3D demo owns, with Chapter 28's
clouds in it. It costs nothing while the engine's sky setting is Off, and Part 4
puts it to work.

`PackSurface` fills `SeaParameters`. The sun comes from a file-scope helper
inside the namespace, after `spectrumConstants`:

```cpp
// Sections 4 and 10. The sun's irradiance, in the units the sky and the lit demos use: Chapter 11's
// sun, pi (0.90, 0.85, 0.80), so that a white surface facing it reflects (0.90, 0.85, 0.80).
static glm::vec3 sunIrradiance(const SeaSettings& settings)
{
    return settings.sunStrength * PI * glm::vec3(0.90f, 0.85f, 0.80f);
}
```

**This is `PackSurface`, as Part 1 has it**; section 8 adds three fields and
section 9 the flags:

```cpp
SeaParameters SeaDemo::PackSurface() const
{
    const auto& sizes = m_settings.patchSizes;
    glm::vec4 weights(1.0f, 1.0f, 1.0f, 0.0f);
    if (m_settings.solo >= 0)
    {
        weights = glm::vec4(0.0f);
        weights[m_settings.solo] = 1.0f;
    }
    return SeaParameters{
        .patchSizes    = glm::vec4(sizes[0], sizes[1], sizes[2], 0.0f),
        .weights       = weights,
        .sunDirection  = glm::vec4(sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth), 0.0f),
        .sunIrradiance = glm::vec4(sunIrradiance(m_settings), 0.0f),
        .waterColor    = glm::vec4(scene::srgbToLinear(m_settings.waterColor), 0.0f),
        .skyColor      = glm::vec4(scene::srgbToLinear(m_settings.skyColor), 0.0f),
        .hazeDistance  = m_settings.hazeDistance,
        .tiles         = static_cast<uint32_t>(2 * m_settings.tileRadius + 1),
    };
}
```

**This is `RecordSurface`, as Part 1 has it**: Chapter 29's, with the sea's
push constants. Section 9 draws the sky after the water.

```cpp
void SeaDemo::RecordSurface(VkCommandBuffer commandBuffer, const RecordContext& frame,
                            const SeaParameters& parameters)
{
    // The camera, into this slot's frame buffer (Chapter 10 section 7).
    const VkExtent2D extent = frame.targets.extent;
    const float      aspect = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    shared::FrameData frameData{};
    frameData.view           = scene::viewMatrix(m_cameraTransform.Matrix());
    frameData.projection     = m_camera.Projection(aspect);
    frameData.viewProjection = frameData.projection * frameData.view;
    frameData.cameraPosition = glm::vec4(m_cameraTransform.translation, 1.0f);
    frameData.time           = m_time;
    m_sceneRenderer.WriteFrameData(frame.frameIndex, frameData);

    const VkClearColorValue sky{ { parameters.skyColor.r, parameters.skyColor.g, parameters.skyColor.b, 1.0f } };
    beginScenePass(commandBuffer, frame.targets, &sky);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_surfacePipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_surfaceLayout, frame.frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_surfaceLayout,
                            1, 1, &m_surfaceSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_surfaceLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(parameters), &parameters);
    vkCmdDraw(commandBuffer, 6 * OCEAN_GRID_CELLS * OCEAN_GRID_CELLS, parameters.tiles * parameters.tiles, 0, 0);

    endScenePass(commandBuffer);
}
```

### The frame

**This is `Record`, as Part 1 leaves it**, in place of section 3's. Its steps
are Chapter 29's, numbered the same way; the return trips and hand-overs loop
over the cascades, the sea is drawn where section 3 only cleared, and the
timestamps (below) measure it:

```cpp
void SeaDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // Section 4: what this slot measured last time, then this frame's first timestamp.
    if (m_timestamps.Read(frame.frameIndex))
    {
        m_timings = SeaTimings{
            .waves   = m_timestamps.Milliseconds(0, 1),
            .fft     = m_timestamps.Milliseconds(1, 2),
            .maps    = m_timestamps.Milliseconds(2, 3),
            .surface = m_timestamps.Milliseconds(3, 4),
        };
    }
    m_timestamps.Reset(commandBuffer, frame.frameIndex);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 0);

    // 1. Return trips, as in Chapter 29, for every cascade.
    computeToComputeBarrier(commandBuffer);
    for (const Cascade& cascade : m_cascades)
    {
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        transitionImage(commandBuffer, cascade.normals.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // 2-7. Every cascade's waves, maps, and foam, and the preview.
    RecordWaves(commandBuffer, frame.frameIndex);

    // 8. Hand-overs, as in Chapter 29, for every cascade.
    for (const Cascade& cascade : m_cascades)
    {
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        transitionImage(commandBuffer, cascade.normals.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 3);

    // 10. The sea, then the scene target goes back to the engine.
    RecordSurface(commandBuffer, frame, PackSurface());
    m_timestamps.Write(commandBuffer, frame.frameIndex, 4);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

Every barrier in it is one of Chapter 29's, done once per cascade: the return
trips at step 1 and the hand-overs at step 8 name the same stages, and nothing
about them changes when there are three of each image. Chapter 04's appendix
already has them.

### What three cascades cost

Three cascades are three times Chapter 29's compute. To see what that is on
your GPU, the demo times four stretches of its frame with Chapter 24's
`GpuTimestamps`: the starting waves and the animation, the FFT, the rest of the
compute with the hand-overs, and the surface. The struct for the numbers is in
the class map, `SeaTimings`. `Setup` creates five timestamps a frame, and the
first lines of `Record` above read what this slot measured last time and write
this frame's first timestamp before anything else.

The other four `Write`s are already in `RecordWaves` and `Record`, after the
animation, after the FFT, after the hand-overs, and after the surface. Each
reads the time once everything recorded before it has finished, so each
difference is the cost of what lies between. All five are written every frame,
none behind an `if`: a slot that was not written is never ready, and `Read`
then returns false for the whole frame (Chapter 24 section 9).

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Sea`. You can now see:

- the sea of Chapter 29, rougher up close: ripples on the chop on the swell;
- **one cascade against three, from above.** Fly up to about 160 m (Q rises)
  and look straight down. Set **Solo** to "Cascade 1 alone": the 37 m patch's
  pattern repeats in a grid as plainly as Chapter 29's did. Set it back to
  "Off": the grid is gone, and nothing in view repeats;
- the **Sea preview**'s bands, as section 3 showed them, now under a sea you
  can see them in: Solo a cascade, and both its preview and the water change;
- the panel's GPU milliseconds: the FFT is by far the largest of the compute
  steps, because it is three of Chapter 29's;
- the sun's glint, Chapter 29's lobe at the sun's color: a narrow path of
  sparkles toward the low sun. Section 10 gives it its proper size.

---
# Part 2 — A measured sea (sections 5-7)

Chapter 29's Phillips spectrum has the right general shape, and its size, `A`,
is a number chosen by eye. This part replaces it with a spectrum fitted to
measurements of real seas, spreads its waves over directions in a way you can
tune, and adds a swell that arrived from somewhere else. Phillips stays, behind
a switch, so the two can be compared.

## 5. JONSWAP: a spectrum fitted to real seas

> **Jump:** Chapter 29's spectrum was a function of the wave vector `k`. The
> measurements oceanographers publish are a function of **frequency**, `ω`:
> a buoy rides the waves and records its height over time, and the spectrum
> of that record says how much of the bobbing happens at each frequency. Keep in
> mind that the two describe the same waves, linked by Chapter 29's dispersion
> relation `ω = sqrt(g |k|)`, and that this section's job is to turn one into
> the other without losing or gaining energy.

### What a buoy measures

Record a buoy's height for twenty minutes. The **variance** of the record — the
average of `h²`, with `h` measured from the mean level — says how rough the sea
is. Its square root is the standard deviation, `σ`. Sailors and forecasts speak
of the **significant wave height**, `Hs = 4σ`: it is close to the average
trough-to-crest height of the highest third of the waves, which is what an
observer on deck reports as "the waves".

The **frequency spectrum** `S(ω)` splits that variance by frequency: the
variance in the waves whose angular frequency lies in a thin strip from `ω` to
`ω + δω` is `S(ω) δω`. Its unit is m² s. The total variance is the whole area
under the curve, and is called `m0`.

### The formula

In 1968 and 1969 the Joint North Sea Wave Project, **JONSWAP**, measured waves
along a line of buoys reaching 160 km out from the island of Sylt, in winds
blowing offshore, so that each buoy saw the wind's waves at a different
distance from where they started. The fit, published by Hasselmann and others
in 1973, is

$$
S(\omega) = \frac{\alpha g^2}{\omega^5}
            \exp\!\left(-\frac{5}{4}\left(\frac{\omega_p}{\omega}\right)^4\right)
            \gamma^{\,r},
\qquad
r = \exp\!\left(-\frac{(\omega - \omega_p)^2}{2\sigma_p^2\omega_p^2}\right)
$$

with `σp = 0.07` below the peak and `0.09` above it. This `σp` is the peak's
width, as a fraction of `ωp`, not the standard deviation `σ` of a moment ago;
the code calls it `sigma`. One factor at a time:

- **`α g² / ω⁵`** is the high-frequency tail: energy falls with the fifth power
  of frequency. In wave numbers it is the same `1 / |k|⁴` as Chapter 29's
  Phillips. `α` sets how much energy there is.
- **`exp(−5/4 (ωp/ω)⁴)`** is nearly zero for frequencies well below the peak
  `ωp`, the waves too long for this wind to have built. Without the last factor,
  these two are the spectrum of a sea the wind has fully raised, measured by
  Pierson and Moskowitz in 1964.
- **`γ^r`** is what the North Sea added: a young sea has a sharper peak than a
  fully grown one. `r` is 1 at the peak and falls to 0 a few widths `σp` away,
  so the peak is raised `γ` times and the rest is left alone. The mean `γ` measured was
  3.3, the panel's default.

Relative to its own peak, with the defaults (`ωp` is below):

| `ω / ωp` | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 | 1.5 | 2.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| JONSWAP, m² s | 0.20 | 0.53 | 1.29 | 0.69 | 0.33 | 0.14 | 0.04 |
| without `γ^r` | 0.20 | 0.34 | 0.39 | 0.36 | 0.30 | 0.14 | 0.04 |

Away from the peak the two agree; at it, JONSWAP is 3.3 times as tall.

### Fetch

What makes the measurements useful is that `α` and `ωp` are not free: they
follow from the wind speed `U` (m/s) and the **fetch** `F` (metres), the
distance of open water the wind has blown across:

$$
\alpha = 0.076\left(\frac{U^2}{F g}\right)^{0.22}
\qquad
\omega_p = 22\left(\frac{g^2}{U F}\right)^{1/3}
$$

A longer fetch gives a lower peak frequency — longer waves — and a smaller `α`.
It cannot go on forever: past a few hundred kilometres the sea is fully grown,
and the waves stop getting longer. Pierson and Moskowitz measured where that
is, `ωp = 0.855 g / U` and `α = 0.0081`, so the code takes whichever is larger.

The worked numbers, at Chapter 29's 12 m/s. The peak's wavelength follows from
the dispersion relation, `λ = 2π g / ωp²`, and its period is `2π / ωp`:

| Fetch | `α` | `ωp` | Peak wavelength | Peak period | `Hs` |
| --- | --- | --- | --- | --- | --- |
| 10 km (a lake, a bay) | 0.018 | 2.04 | 15 m | 3.1 s | 0.7 m |
| 100 km (the default) | 0.011 | 0.95 | 68 m | 6.6 s | 2.5 m |
| 250 km and more (fully grown) | 0.0081 | 0.70 | 126 m | 9.0 s | 4.0 m |

The panel prints the middle row's numbers for whatever you set.

### Adding up the area

`Hs` needs `m0`, the area under `S`. There is no tidy formula for JONSWAP's
area, so the CPU adds it up: cut the frequencies from 0 to ten times the peak
into 2000 thin strips, take each strip's height at its middle, multiply by its
width, and add. Past ten times the peak the tail holds less than a ten-thousandth
of the total. With the defaults the sum is `m0 = 0.394` m², so `σ = 0.63` m and
`Hs = 2.51` m.

**These are `jonswapEnergy` and `jonswapVariance`**, at the top of the
namespace in `SeaDemo.cpp`, with the two constants they need. `jonswapEnergy`
is the shader's formula, written again in C++, because the CPU adds it up:

```cpp
constexpr float PI      = 3.14159265358979f;
constexpr float GRAVITY = 9.81f;   // m/s^2
```

```cpp
// Section 5. JONSWAP, as SeaSpectrum.comp.glsl has it: energy per unit of angular frequency.
static float jonswapEnergy(float omega, float alpha, float peakOmega, float gamma)
{
    const float sigma  = omega <= peakOmega ? 0.07f : 0.09f;
    const float offset = (omega - peakOmega) / (sigma * peakOmega);
    const float ratio  = peakOmega / omega;
    return alpha * GRAVITY * GRAVITY / std::pow(omega, 5.0f)
         * std::exp(-1.25f * ratio * ratio * ratio * ratio)
         * std::pow(gamma, std::exp(-0.5f * offset * offset));
}
```

```cpp
// Section 5. The area under S(omega), added up in thin strips: the variance of the
// sea's height, m0. The significant wave height is 4 sqrt(m0).
static float jonswapVariance(float alpha, float peakOmega, float gamma)
{
    const float steps = 2000.0f;
    const float width = 10.0f * peakOmega / steps;   // past ten times the peak, nothing is left to add
    float sum = 0.0f;
    for (float i = 0.5f; i < steps; i += 1.0f)
    {
        sum += jonswapEnergy(i * width, alpha, peakOmega, gamma) * width;   // a strip at its middle
    }
    return sum;
}
```

### From frequencies to wave vectors

The FFT wants energy per texel of wave vectors, and a texel is a small square
of `k`, `Δk` on a side. The buoy's `S(ω)` knows nothing about direction, so two
things are needed: how the energy at one frequency is shared among directions,
which is section 6's **spreading function** `D(θ)` (it adds up to 1 around the
circle), and how a strip of frequencies maps onto an area of wave vectors.

Count the same waves both ways. The waves with frequency between `ω` and
`ω + δω`, travelling at an angle between `θ` and `θ + δθ`, hold variance
`S(ω) δω · D(θ) δθ`. Those same waves fill a small patch of the wave-vector
plane: between the rings at `|k|` and `|k| + δk`, and between the two angles.
That patch is `δk` deep and `|k| δθ` wide, an area of `|k| δk δθ`. Call the
energy per unit of that area `E(k)`; then the same variance is
`E(k) |k| δk δθ`. Set the two equal and divide:

$$
E(\mathbf{k}) = S(\omega)\, D(\theta)\, \frac{\delta\omega}{\delta k}\, \frac{1}{|\mathbf{k}|}
$$

`δω / δk` is how fast `ω` changes as `|k|` changes. From `ω² = g |k|`: grow `k`
by a little, `δk`, and `ω²` grows by `g δk`; `ω²` grows by `2ω δω` when `ω`
grows by `δω`. So `2ω δω = g δk`, and `δω / δk = g / (2ω)`. It is a speed, and
a famous one: the speed at which groups of waves travel, half the speed of
their crests.

A worked number, at the default peak, straight downwind. `ωp = 0.949` rad/s,
so `|k| = ωp² / g = 0.0918` rad/m. `S(ωp) = 1.29` m² s from the table above,
`D = 0.58` with section 6's defaults, and `δω/δk = 9.81 / (2 × 0.949) = 5.17`
m/s:

```text
E = 1.29 × 0.58 × 5.17 / 0.0918 = 42 m⁴
```

One texel of cascade 0 covers `Δk² = (2π / 250)² = 0.00063` rad²/m², so that
texel holds `42 × 0.00063 = 0.027` m² of variance: a wave of about 23 cm
amplitude, since a wave of amplitude `a` has variance `a² / 2`.

### Counting each wave once more

One more factor, and it is easy to miss. Chapter 29 section 8 built each texel
from two terms, `h0(k) e^(−iωt)` and `conj(h0(−k)) e^(+iωt)`: every starting
wave `h0(k)` is used twice, once in its own texel and once, conjugated, in its
mirror's. Each use carries the full `|h0(k)|²` into the height's variance. So
the sea's variance is *twice* the sum of `|h0|²` over the texels.

For Phillips that did not matter: `A` was chosen by looking at the result, and
it absorbed the factor of two. A measured spectrum's energy is real, so it has
to be halved before it becomes `h0`, or every height comes out `√2` too large.
With the half, the three cascades' texels add up to `Hs = 2.51` m, the same as
the formula; without it they give 3.55 m.

### The code

**These are `jonswap` and `jonswapDensity`** in `SeaSpectrum.comp.glsl`,
after `phillips`. `jonswapDensity` takes the direction and the shape as
arguments, because section 7 calls it a second time for the swell:

```glsl
// JONSWAP (section 5): energy per unit of angular frequency, m^2 s. The
// Pierson-Moskowitz shape of a fully grown sea, with its peak raised gamma times.
float jonswap(float omega, float alpha, float peakOmega, float gamma)
{
    float sigma  = omega <= peakOmega ? 0.07 : 0.09;          // the peak's width, each side
    float offset = (omega - peakOmega) / (sigma * peakOmega);
    float raise  = pow(gamma, exp(-0.5 * offset * offset));   // gamma at the peak, 1 far from it
    float ratio  = peakOmega / omega;
    return alpha * GRAVITY * GRAVITY / pow(omega, 5.0)
         * exp(-1.25 * ratio * ratio * ratio * ratio)
         * raise;
}
```

```glsl
// One JONSWAP sea, the wind's or the swell's, as energy per unit of wave-vector
// area (section 5): E(k) = S(omega) D(angle) (d omega / dk) / k, with d omega / dk = g / (2 omega).
float jonswapDensity(vec2 k, float kLength, vec2 direction, float alpha, float peakOmega,
                     float gamma, float s, float normalization)
{
    float omega = sqrt(GRAVITY * kLength);   // Chapter 29 section 8's dispersion
    return jonswap(omega, alpha, peakOmega, gamma)
         * spreading(k / kLength, direction, s, normalization)
         * GRAVITY / (2.0 * omega * kLength);
}
```

`spreading` is section 6's; write it now too, before `jonswapDensity`. And
**this is `seaDensity`**, replacing Part 1's: the switch between the two models,
and the half:

```glsl
// Sections 5-7: the energy this sea puts in the wave k, per unit of wave-vector area.
float seaDensity(vec2 k, float kLength)
{
    // JONSWAP and the swell are measured: their energy is the sea's real variance.
    float measured = 0.0;
    if (spectrum.model == SEA_SPECTRUM_JONSWAP)
    {
        measured += jonswapDensity(k, kLength, spectrum.wind.xy, spectrum.wind.w,
                                   spectrum.windShape.x, spectrum.windShape.y,
                                   spectrum.windShape.z, spectrum.windShape.w);
    }

    // Chapter 29's h(k, t) puts every wave in twice: in its own texel, and again as
    // its mirror's conjugate. Phillips's A was chosen by eye and absorbs that; a
    // measured spectrum gives each half its energy (section 5).
    float density = 0.5 * measured;
    if (spectrum.model == SEA_SPECTRUM_PHILLIPS)
    {
        density += phillips(k, kLength);
    }
    return density;
}
```

The panel's "Model" sets `spectrum.model`; Phillips reads `phillipsAmplitude`
and the wind, JONSWAP the wind and the numbers `spectrumConstants` works out on
the CPU. **This is `spectrumConstants`**, as this section has it; sections 6 and
7 add their lines:

```cpp
// Sections 5-7. Everything about the spectrum that is a formula of the settings alone.
static SpectrumConstants spectrumConstants(const SeaSettings& settings)
{
    const float windSpeed = std::max(settings.windSpeed, 0.1f);
    const float fetch     = settings.fetch * 1000.0f;   // metres

    SpectrumConstants constants;
    // JONSWAP's two fits to the measurements: a longer fetch makes the sea older,
    // with a longer peak, and less steep for its height. Past a few hundred km it is
    // fully grown, and Pierson and Moskowitz's values are where it stops.
    constants.alpha     = std::max(0.076f * std::pow(windSpeed * windSpeed / (fetch * GRAVITY), 0.22f), 0.0081f);
    constants.peakOmega = std::max(22.0f * std::pow(GRAVITY * GRAVITY / (windSpeed * fetch), 1.0f / 3.0f),
                                   0.855f * GRAVITY / windSpeed);
    constants.significantHeight =
        4.0f * std::sqrt(jonswapVariance(constants.alpha, constants.peakOmega, settings.peakEnhancement));

    return constants;
}
```

It is a function of the settings alone, a few thousand `exp` and `pow` calls,
so `Update` calls it every frame, after the panel, rather than keeping track of
which setting changed:

```cpp
    m_spectrumDirty |= drawSeaPanel(m_settings, m_constants, m_timings, m_timestamps.Available());
    m_constants = spectrumConstants(m_settings);   // a few thousand exp() calls: cheap enough every frame
```

**`PackSpectrum`** gains the three fields JONSWAP and the swell read, after
`.wind` in section 3's initializer. The spread's numbers and the swell are
sections 6 and 7's:

```cpp
        .windShape         = glm::vec4(k.peakOmega, s.peakEnhancement, s.spread, k.windNormalization),
        .swell             = glm::vec4(azimuthDirection(s.swellAzimuth), k.swellOmega, s.swell ? k.swellAlpha : 0.0f),
        .swellShape        = glm::vec4(SWELL_PEAK_ENHANCEMENT, s.swellSpread, k.swellNormalization, 0.0f),
```

And the panel's "Spectrum" group, after the cascades' in `drawSeaPanel`, which
now reads `constants`: put the parameter's name back. Its
`Spread s` slider is section 6's:

```cpp
        if (ImGui::CollapsingHeader("Spectrum (rebuilds)"))
        {
            changed |= ImGui::Combo("Model", &settings.model, "Phillips (Chapter 29)\0JONSWAP\0");
            changed |= ImGui::SliderFloat("Wind speed (m/s)", &settings.windSpeed, 1.0f, 30.0f);
            changed |= ImGui::SliderFloat("Wind toward (deg)", &settings.windAzimuth, -180.0f, 180.0f);
            if (settings.model == static_cast<int>(SEA_SPECTRUM_JONSWAP))
            {
                changed |= ImGui::SliderFloat("Fetch (km)", &settings.fetch, 1.0f, 1000.0f, "%.0f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
                changed |= ImGui::SliderFloat("Peak enhancement", &settings.peakEnhancement, 1.0f, 7.0f, "%.3f",
                                              ImGuiSliderFlags_AlwaysClamp);
                // Clamped even when typed (Ctrl+click). Upwind, spreading's max leaves a base of exactly 0, and
                // pow(0, s) for s <= 0 is a NaN or an infinity on a GPU, which the FFT spreads (section 6).
                changed |= ImGui::SliderFloat("Spread s", &settings.spread, 0.5f, 32.0f, "%.1f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
                const float peakWavelength = 2.0f * PI * GRAVITY / (constants.peakOmega * constants.peakOmega);
                ImGui::Text("Peak %.0f m, every %.1f s; Hs %.2f m", peakWavelength, 2.0f * PI / constants.peakOmega,
                            constants.significantHeight);
            }
            else
            {
                changed |= ImGui::SliderFloat("Amplitude", &settings.phillipsAmplitude, 0.0001f, 0.01f, "%.4f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
            }
            changed |= ImGui::SliderFloat("Suppression (m)", &settings.suppression, 0.0f, 1.0f, "%.3f");
            changed |= ImGui::InputInt("Seed", &settings.seed);
        }
```

## 6. Waves spread over directions

Not every wave runs straight downwind. The wind gusts and veers, and the waves
it raises spread around its direction, more so the further a wave is from the
peak. The **spreading function** `D(θ)` says how the energy at one frequency is
shared among directions, `θ` being the angle between a wave's direction and the
wind's. It moves energy around without making any, so it must add up to 1 around
the circle.

Chapter 29 used Phillips's `cos² θ` and cut the upwind half to 5% by hand. A
form with a knob is better:

$$
D(\theta) = N(s) \left(\frac{1 + \cos\theta}{2}\right)^{s}
$$

`(1 + cos θ) / 2` is 1 downwind, ½ across the wind, and 0 upwind, with no
special case. Raising it to the power `s` narrows it:

| `s` | across the wind (90°) | 45° off | `N(s)` |
| --- | --- | --- | --- |
| 1 | 0.5 | 0.85 | 0.318 |
| 4 (the default) | 0.0625 | 0.53 | 0.582 |
| 16 | 0.000015 | 0.079 | 1.137 |

**`N(s)` is found the way `m0` was, by adding up.** It must make the whole
circle's sum 1, so it is 1 divided by the sum of `((1 + cos θ)/2)^s` over 720
thin slices of the circle. For `s = 1` it can be checked by hand: the average of
`cos θ` around a circle is 0, so the average of `(1 + cos θ)/2` is ½, and over
the circle's `2π` radians it adds up to `π`. `N(1) = 1/π = 0.318`.

`dot(k̂, ŵ)` is `cos θ` (Chapter 11 section 14), so the shader never computes an
angle. **This is `spreading`**, before `jonswapDensity`:

```glsl
// Directional spreading (section 6): ((1 + cos angle) / 2)^s - 1 along `direction`,
// 0 against it - scaled by `normalization` so that it adds up to 1 around the circle.
// The max: against the wind the base is 0 only in exact arithmetic. A GPU normalizes k
// with an approximate reciprocal, the dot can come out a hair below -1, and pow of a
// negative number is NaN, which the FFT then spreads over the whole cascade.
float spreading(vec2 kDirection, vec2 direction, float s, float normalization)
{
    return normalization * pow(max(0.5 + 0.5 * dot(kDirection, direction), 0.0), s);
}
```

**This is `spreadNormalization`**, after `jonswapVariance` in `SeaDemo.cpp`:

```cpp
// Section 6. What ((1 + cos angle) / 2)^s must be multiplied by to add up to 1 around
// the circle, found by adding it up.
static float spreadNormalization(float s)
{
    const float steps = 720.0f;
    const float width = 2.0f * PI / steps;
    float sum = 0.0f;
    for (float i = 0.5f; i < steps; i += 1.0f)
    {
        sum += std::pow(0.5f + 0.5f * std::cos(-PI + i * width), s) * width;
    }
    return 1.0f / sum;
}
```

and its line in `spectrumConstants`, after `peakOmega`:

```cpp
    constants.windNormalization = spreadNormalization(settings.spread);
```

Real seas spread more at frequencies far from the peak; Hasselmann's
measurements give an `s` that falls off on both sides of `ωp`. A constant `s` is
the simple version, and the panel's slider shows what it does.

## 7. A swell from a distant storm

Waves outlive the wind that raised them. A storm a thousand kilometres away
sends out long waves that travel for days, sorting themselves by speed on the
way — long waves are faster, Chapter 29 section 8 — until what arrives is a
train of long, regular crests from one direction: **swell**. Where swell meets a
local wind sea from another direction, you get crossing seas, two patterns of
crests at an angle.

A swell's spectrum is a narrow one. Its energy sits near one frequency, so its
`γ` is large — this chapter uses 7 — and near one direction, so its `s` is large,
40 by default. The same `jonswapDensity` draws it, with its own direction, peak,
and shape; `seaDensity` adds it to whichever model the wind's sea uses:

```glsl
    if (spectrum.swell.w > 0.0)   // section 7: a swell from a distant storm, added to either model
    {
        measured += jonswapDensity(k, kLength, spectrum.swell.xy, spectrum.swell.w,
                                   spectrum.swell.z, spectrum.swellShape.x,
                                   spectrum.swellShape.y, spectrum.swellShape.z);
    }
```

Its numbers come from the panel's wavelength and height. The peak frequency
follows from the wavelength by the dispersion relation, `ω = sqrt(g · 2π / λ)`:
a 200 m swell has `ω = 0.555` rad/s, a period of 11.3 s. For the height there is
no fetch to give `α`, but none is needed: `m0` is proportional to `α`, so add up
the spectrum once with `α = 1`, and the `α` that gives a height `H` is
`(H / 4)² / m0`. **These are the swell's lines of `spectrumConstants`**, at its
end:

```cpp
    // The swell: its peak from its wavelength (deep water: omega^2 = g k), and its
    // alpha chosen so that its significant height is the panel's.
    constants.swellOmega = std::sqrt(GRAVITY * 2.0f * PI / settings.swellWavelength);
    const float heightPerAlpha = jonswapVariance(1.0f, constants.swellOmega, SWELL_PEAK_ENHANCEMENT);
    const float quarterHeight  = settings.swellHeight / 4.0f;
    constants.swellAlpha         = quarterHeight * quarterHeight / heightPerAlpha;
    constants.swellNormalization = spreadNormalization(settings.swellSpread);
```

with its constant beside `BAND_WAVES`:

```cpp
// Section 7. A swell is old: its energy sits in a narrow peak.
constexpr float SWELL_PEAK_ENHANCEMENT = 7.0f;
```

and its group on the panel, after the spectrum's:

```cpp
        if (ImGui::CollapsingHeader("Swell (rebuilds)"))
        {
            changed |= ImGui::Checkbox("Swell", &settings.swell);
            changed |= ImGui::SliderFloat("Swell height (m)", &settings.swellHeight, 0.0f, 5.0f);
            changed |= ImGui::SliderFloat("Swell wavelength (m)", &settings.swellWavelength, 30.0f, 600.0f, "%.0f");
            changed |= ImGui::SliderFloat("Swell toward (deg)", &settings.swellAzimuth, -180.0f, 180.0f);
            changed |= ImGui::SliderFloat("Swell spread s", &settings.swellSpread, 1.0f, 200.0f, "%.0f",
                                          ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
            ImGui::Text("Swell period %.1f s", 2.0f * PI / constants.swellOmega);
        }
```

### A narrow peak on a coarse grid

A narrow spectrum meets a limit of the grid. Cascade 0's texels are
`Δk = 2π / 250 = 0.025` rad/m apart. The default swell's peak is at
`k = 2π / 200 = 0.031`, and its `σp` of 0.07 keeps its energy within about 7% of
the peak frequency — within 14% of the peak wave number, since `k` grows as
`ω²` — so the peak is about `0.0044` rad/m wide: narrower than one texel. Added
up over cascade 0's texels, the swell keeps about two thirds of its variance, 90%
of it in just 7 texels. On screen it is a handful of long waves that repeat every
250 m, which is what a swell looks like anyway. A longer swell, or a narrower
one, needs a larger first cascade: a 1 km cascade 0 keeps all of it in about 60
texels, and the band rule of section 2 then says what the other cascades must be.

## Checkpoint

Run with `--demo Sea`. You can now see:

- **JONSWAP against Phillips.** In the Sea preview, cascade 0, "Spectrum |h0|":
  Phillips is a round blob with a dark line across it, the waves across the wind,
  and a dim lower half, the 5% upwind; JONSWAP is a half disc, bright at its
  peak and fading smoothly to nothing upwind. On the surface, at the same wind,
  JONSWAP's sea is lower: `Hs` 2.5 m against Phillips's 3.4 m;
- **fetch.** Drag "Fetch (km)" from 10 to 300: the printed peak goes from 15 m to
  126 m and `Hs` from 0.7 m to 4 m, and the sea grows from a choppy bay to long
  rollers. Past about 250 km nothing changes: the sea is fully grown;
- **spread.** "Spread s" at 1 sends waves every way but upwind; at 32 the crests
  run straight across the wind, long and parallel;
- **the swell.** Set the wind to 5 m/s, so that the swell dominates, and pick
  "Height" in the preview: long crests at an angle to the wind's short ones.
  Untick "Swell" and they are gone.

---
# Part 3 — Foam that lingers (section 8)

## 8. Foam with a memory

Chapter 29's foam is wherever the surface is squeezed *this frame*. A crest
folds, its texels turn white, and as the crest moves on they turn back: the
foam rides along with the crest and blinks out behind it. Real foam stays
behind. A breaking crest leaves a patch of white where it broke, the wave runs
on, and the patch thins out over several seconds into streaks.

So each texel gets a memory: a foam map that holds how much foam is there, kept
from one frame to the next. Every frame, two things happen to it. **Old foam
fades**, and **new foam is added** where the surface is squeezed now.

### Fading, and its half-life

Foam fades the way Chapter 21's particles slow down: the same *fraction* goes
every instant, so the decay over a step of `dt` seconds is a multiplication by
`exp(−dt / τ)`, where `τ` is the panel's "Foam fade". After `τ` seconds,
`exp(−1) = 37%` is left. With `τ = 3` s, at 60 frames a second:

| After | one frame | 1 s | 2.1 s | 3 s | 6 s |
| --- | --- | --- | --- | --- | --- |
| Foam left | 99.45% | 72% | 50% | 37% | 14% |

The time to lose half, the **half-life**, is `τ ln 2 = 0.69 τ`: 2.1 s here. As
with Chapter 21's drag, the exponential does not care how the time is cut into
frames — two frames of `dt` multiply to one of `2 dt` — so foam fades at the same
rate at 30 and at 144 frames a second, and a long frame cannot make it negative.

### Adding, without piling up

New foam is Chapter 29's whitecap: 0 above the threshold, fading in over 0.3 of
Jacobian below it. Old and new are combined with `max`, not `+`. A crest takes
several frames to cross a texel, and adding its whitecap every frame would pile
up far past "fully white". With `max`, a crest that breaks again over old foam
tops it back up to full, and never beyond.

### Where the foam is

A texel of the foam map is a point of Chapter 29's flat grid, moved by the
displacement like every other. Crests travel through the grid points, so the
foam stays where it was made while the crest moves on, and leaves a trail. That
happens to be right for the sea: water does not travel with a wave, it goes
round in a circle as the wave passes, so foam stays roughly where the crest broke.

Each cascade has its own foam map, made from its own Jacobian, and tiled with
it. Strictly, foam belongs to the squeeze of the whole sea, which multiplies the
cascades' stretches together; each cascade's squeeze is small, so treating them
separately is close, and it is what real-time oceans do. A cascade's Jacobian
moves less than Chapter 29's single patch did — about ±0.1 at choppiness 1,
where Chapter 29's spread from 0.5 to 1.5 — so the default threshold is 0.75.

### The image

One number per texel, but the format is `R16G16B16A16_SFLOAT`, with three
channels unused. Chapter 20 section 4's list is the reason: of the one-channel
formats, `R32_SFLOAT` is guaranteed as a storage image but not guaranteed to be
filtered by a sampler, and `R16_SFLOAT` the other way round. `rgba16f` is
guaranteed both ways, and the surface samples the foam with filtering. A 16-bit
float keeps about three digits, plenty for a fade of half a percent a frame.

The foam map is the tutorial's second piece of state that the GPU writes and
carries from frame to frame, after Chapter 21's particles, and the same rule
applies (Chapter 21 section 1): **one copy, and a return trip**. It was already
created in `CreateImages`, named at binding 6 of each cascade's set, and at
bindings 6 to 8 of the surface's.

### The shader

**This is `Shaders/Sea/SeaFoam.comp.glsl`:**

```glsl
// Shaders/Sea/SeaFoam.comp.glsl - one cascade's foam, remembered (section 8): new
// whitecaps where the surface is squeezed, and old foam fading, never blinking out.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SeaTypes.h"
#include "../Ocean/OceanTypes.h"   // OCEAN_GROUP_SIZE

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 4, rgba16f) uniform readonly image2D normalMap;   // w: the Jacobian
layout(set = 0, binding = 6, rgba16f) uniform image2D foamMap;              // r: foam. Read, then written

layout(push_constant) uniform PushConstants
{
    SeaParameters sea;
};

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (any(greaterThanEqual(texel, imageSize(foamMap)))) { return; }

    // New foam: Chapter 29's whitecap, fading in over 0.3 of Jacobian below the threshold.
    float jacobian = imageLoad(normalMap, texel).w;
    float whitecap = clamp((sea.foamThreshold - jacobian) / 0.3, 0.0, 1.0);

    // Old foam: what this texel held last frame, fading like Chapter 21's drag.
    // After a reset the image holds garbage, so nothing is read from it.
    float old = 0.0;
    if ((sea.flags & SEA_FLAG_FOAM_RESET) == 0u)
    {
        old = imageLoad(foamMap, texel).r * exp(-sea.deltaTime / sea.foamFade);
    }

    // A crest that breaks again tops the foam back up; it never adds past full.
    imageStore(foamMap, texel, vec4(max(old, whitecap)));
}
```

It reads the Jacobian Chapter 29's assemble pass left in the normal map's `w`,
and its own map. The `foamMap` binding has no `readonly` or `writeonly`: it is
read, then written, by the same invocation, at the same texel, so no invocation
reads what another wrote, and no barrier is needed inside the pass.

**After `Setup`, or after the spectrum changes, the old foam is garbage**, or
the foam of a sea that no longer exists. `SEA_FLAG_FOAM_RESET` tells the pass to
ignore it for one frame. `m_foamHistory` is that flag's source: `Setup` clears
it, step 2 of `RecordWaves` clears it again when the spectrum is rebuilt —

```cpp
        m_foamHistory   = false;   // section 8: the old foam belongs to another sea
```

— and `PackSurface` turns it into the flag, with the pass's three other fields.
The flag's line goes on with the sky's flags, which are section 9's:

```cpp
        .foamThreshold = m_settings.foamThreshold,
        .foamFade      = m_settings.foamFade,
        .deltaTime     = m_deltaTime,
        .tiles         = static_cast<uint32_t>(2 * m_settings.tileRadius + 1),
        .flags         = (m_foamHistory ? 0u : SEA_FLAG_FOAM_RESET) | (m_skyOn ? SEA_FLAG_SKY : 0u)
```

### Running it

The pipeline's row goes last in `CreateComputePipelines`' table:

```cpp
        { &m_foamPipeline,     "Sea/SeaFoam.comp.spv",         m_cascadeLayout },   // section 8
```

and the pass is step 6 of `RecordWaves`, between Chapter 29's maps and the
preview:

```cpp
    // 6. Section 8: each cascade's foam, from its Jacobian and its own last frame.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_foamPipeline);
    const SeaParameters sea = PackSurface();
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        bindCascade(c, &sea, sizeof(sea));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }
```

It needs no barrier after it in `RecordWaves`: the preview does not read the
foam, and step 8's hand-over is the foam's next barrier. The barrier before it,
after step 5, already makes the Jacobian visible to it.

### The barriers: an image that must keep its contents

The foam map is read and written by compute, then sampled by the surface's
fragment shader, every frame. Its hand-over to the fragment shader is the same
as the normal map's, in `Record`'s step 8:

```cpp
        // Section 8: the foam, to the fragment shader.
        transitionImage(commandBuffer, cascade.foam.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
```

followed, after the loop and the preview's hand-over, just before timestamp 3,
by the line that says the maps now hold something:

```cpp
    m_foamHistory = true;   // from now on the foam maps hold foam worth keeping
```

The return trip, in step 1, is where it differs from everything in Chapter 29:

```cpp
    const VkImageLayout foamLayout = m_foamHistory ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                                   : VK_IMAGE_LAYOUT_UNDEFINED;
```

```cpp
        // Section 8: the foam, back to the foam pass, which reads it and writes it.
        transitionImage(commandBuffer, cascade.foam.image,
                        foamLayout, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

The three questions:

- **Q1:** last frame's `FRAGMENT_SHADER` reads finish before this frame's
  `COMPUTE_SHADER` reads and writes.
- **Q2:** a read leaves nothing to flush, so the source access is `NONE`. The
  destination is `SHADER_STORAGE_READ` *and* `WRITE`, because the foam pass
  reads the map before it writes it. The layout change is itself a write, and
  without `READ` the pass's read would not be ordered after it.
- **Q3:** `SHADER_READ_ONLY_OPTIMAL` to `GENERAL` — and the old layout is the
  real one.

**Chapter 29 used `UNDEFINED` as the old layout of every return trip, and it
must not here.** `UNDEFINED` tells the driver that the image's contents may be
thrown away, which was true for Chapter 29's maps: the assemble pass rewrote
every texel. A driver is allowed to act on it. On a GPU that compresses images,
a transition from `UNDEFINED` can leave the memory holding anything at all. For
the foam map that would wipe last frame's foam, and the foam would blink like
Chapter 29's — or show garbage. Nothing reports it, because throwing contents
away is legal: the old layout here is right because of what it means, not
because a tool checks it.

`UNDEFINED` is still the right old layout when there is nothing to keep, and on
the first frame it is the only right one: `CreateImages` left the map in
`GENERAL`, and an old layout must be either the image's real layout or
`UNDEFINED`. Hence `foamLayout`. After a spectrum change the map *is* in
`SHADER_READ_ONLY_OPTIMAL`, so that frame's return trip keeps the old contents
and the reset flag tells the pass to ignore them.

Chapter 04's appendix gains this as "Foam map kept across frames, written by
compute, sampled by fragment: its return trip".

### Drawing it

The surface reads every cascade's foam map and combines them. Foam from any
cascade covers the water, so a point stays clear only if every cascade leaves
it clear: the clear fractions multiply. Two cascades at 50% each leave
`0.5 × 0.5 = 25%` clear, 75% foam — more than either, and never more than all.
**These are the foam's lines in `SeaSurface.frag.glsl`**: its three bindings,
after the normal maps',

```glsl
layout(set = 1, binding = 6) uniform sampler2D foamMap0;   // section 8
layout(set = 1, binding = 7) uniform sampler2D foamMap1;
layout(set = 1, binding = 8) uniform sampler2D foamMap2;
```

a helper after `cascadeSlope`,

```glsl
float cascadeFoam(sampler2D map, vec2 position, float patchSize)
{
    return texture(map, cascadeUv(map, position, patchSize)).r;
}
```

the combination, after the normal,

```glsl
    // Foam from any cascade covers the water: a point is clear only if every
    // cascade leaves it clear.
    float clear = (1.0 - weights.x * cascadeFoam(foamMap0, gridPosition, sea.patchSizes.x))
                * (1.0 - weights.y * cascadeFoam(foamMap1, gridPosition, sea.patchSizes.y))
                * (1.0 - weights.z * cascadeFoam(foamMap2, gridPosition, sea.patchSizes.z));
    float foam = 1.0 - clear;
```

and Chapter 29's foam color, between the water's color and the haze:

```glsl
    // Section 8: foam, lit like the water's body.
    color = mix(color, vec3(0.8) * sun / PI * (0.5 + 0.5 * lit), foam);
```

The panel's "Every frame" group gains two sliders, after "Time scale":

```cpp
            ImGui::SliderFloat("Foam threshold", &settings.foamThreshold, -1.0f, 1.0f);
            ImGui::SliderFloat("Foam fade (s)", &settings.foamFade, 0.1f, 20.0f, "%.1f", ImGuiSliderFlags_Logarithmic);
```

## Checkpoint

Run with `--demo Sea`, from Chapter 29's camera 12 m up. You can now see:

- **foam that lingers.** Set "Foam fade" to 0.1 s: foam only on the crests,
  appearing and vanishing with them, as in Chapter 29. Set it to 3 s: patches
  stay where crests broke, trail behind the moving waves, and thin out over a
  few seconds. At 10 s the sea is streaked with old foam;
- "Foam threshold" still decides how much new foam there is: 0.65 almost none,
  0.85 a lot;
- after changing the wind, the old foam is gone at once: the reset flag.

---
# Part 4 — The sky in the water (sections 9-11)

Water is mostly reflection (Chapter 29 section 10), so it can only look as good
as what it reflects. Until now that was Chapter 29's two-color gradient. This
part puts Chapter 23's sky behind the sea and in it, and Chapter 28's clouds
over both.

## 9. The sea under the engine's sky

> **Jump:** so far the sea demo drew everything itself — the clear color was
> its sky. From here the sky is the engine's: one setting for every demo
> (Chapter 23 section 8), which this demo does not choose, only reads. Keep in
> mind that the sea must look right in all three of the setting's states,
> including Off, and that what it reflects must match what is drawn behind it,
> or the horizon shows a seam.

### Three calls

The sea owns a `Sky` like every 3D demo since Chapter 23. Two of its three calls
are already in place: `Initialize` in `Setup`, before the surface whose set
names the cube, and `Shutdown` in `Teardown`. The third pair goes in `Record`.
**`Update` is step 9**, after the hand-overs and `m_foamHistory = true;`, just
before timestamp 3, and so before the scene pass: a bake is a compute dispatch
and must be outside any rendering scope:

```cpp
    // 9. Section 9: the engine's sky, baked again only if it changed (Chapter 23 section 7). After this
    //    its cube can be sampled by the surface's fragment shader.
    //    Section 10: Chapter 28's clouds come with it; they need the camera and the time.
    m_skyOn    = frame.sky.mode != SkyMode::Off;
    m_cloudsOn = m_skyOn && frame.sky.clouds.enabled;
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
                 { .sunDirection   = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth),
                   .sunIrradiance  = sunIrradiance(m_settings),
                   .cameraPosition = m_cameraTransform.translation,
                   .time           = m_time });
```

The sky gets the panel's sun: its direction, and the same irradiance that lights
the water. Chapter 28's clouds need two more things: where the camera is,
because their cube is seen from there (Chapter 28 section 1), and the time,
which carries them on their wind. The time is the sea's own, so "Time scale" at
0 stops the clouds with the waves. In "Sun sky" mode the sky's brightness is a
fraction of that sun's (Chapter 23 section 6), so the sky, the water's own
color, and the glint all scale together when "Sun strength" moves. After `Update` both cubes are in
`SHADER_READ_ONLY_OPTIMAL`, their writes visible to fragment shaders, which is
exactly what the surface's bindings 9 and 10 need; Chapters 23 and 28's barriers
cover them, and the sea adds none.

**`Draw` goes after the water**, inside the scene pass, in `RecordSurface`:

```cpp
    // Section 9: the sky, wherever the sea did not reach (Chapter 23 section 7). Nothing when it is off.
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);
```

It draws at depth 1.0 with `LESS_OR_EQUAL`, so it lands only where the water
did not (Chapter 23 section 7). With the setting Off it draws nothing, and the
clear color — Chapter 29's horizon — shows, as before.

`m_skyOn` and `m_cloudsOn` tell the shader which sky to reflect. They are set
in step 9 from the frame's setting, and `PackSurface` turns them into flags:

```cpp
        .flags         = (m_foamHistory ? 0u : SEA_FLAG_FOAM_RESET) | (m_skyOn ? SEA_FLAG_SKY : 0u)
                       | (m_cloudsOn ? SEA_FLAG_CLOUDS : 0u),
```

The flag is needed because the cube's *contents* mean nothing until the sky has
been baked. Its *layout* is right from `Initialize` on (Chapter 23 section 3) —
validation checks the layout of every image a pipeline's sets name, even one
behind a branch the shader never takes — but reading it while the sky is off
would reflect whatever was in memory. The clouds' cube is the same, with one
difference: it starts cleared, no light and no opacity (Chapter 28 section 4),
but once the clouds have been on, it keeps its last picture while they are off.
A sea that read it then would reflect clouds that are no longer in the sky, so
the clouds have a flag of their own.

### The edge of the sea

Turn the sky on and a dark brown band appears between the water and the
horizon. The water ends where the tiles end, 375 to 625 m from the camera. In
Chapter 29 the gap beyond was the clear color, Chapter 29's horizon, so nobody
saw it. Now the sky is drawn there, and the sky below the horizon is ground
(Chapter 23 section 6).

The numbers say how much is missing. From 12 m up, water 625 m away is seen
`12 / 625 = 0.019` radians, 1.1°, below the horizontal, and the sky's ground has
fully faded in by `h = −0.02`, 1.15° down. Everything between the water's edge
and the true horizon — 12 km away at that height — is ground.

The fix is a **skirt**: the grid's outermost vertices are pulled out along the
line from the camera to 4 km. The last ring of quads stretches into long strips
that reach toward the horizon, and the haze, with its 900 m distance, has left
`exp(−4000 / 900) = 1%` of the water's own color out there: the strips are the
horizon's color. 4 km is inside the camera's far plane of 5 km.

Pulled out flat, at sea level, the strips would still stop short. From 12 m up,
water 4 km away is `12 / 4000` radians, 0.17°, below the horizontal, where the
sky's ground has barely begun to blend in; but from 60 m it is 0.86°, a dark
line under the horizon. So the skirt's vertices are also **lifted to the
camera's own height**. A point at the height of your eye lies exactly on the
horizon, however far away it is, so the water now reaches the horizon from any
height. The strips slope up by the camera's height over a few kilometres, an
angle nobody can see under the haze. **These are the skirt's lines** in
`SeaSurface.vert.glsl`, the constant before `cascadeDisplacement`,

```glsl
// Section 9: how far the skirt reaches, metres. Inside the camera's far plane, 5 km.
const float SKIRT_DISTANCE = 4000.0;
```

and the test, after the displacement is added up:

```glsl
    // Section 9: the skirt. The grid's outermost vertices are pulled out to SKIRT_DISTANCE and up to
    // the camera's own height, where any distance lies exactly on the horizon: the last ring of quads
    // reaches it from any height, and the sky's ground never shows below it.
    int  edge   = tiles / 2;
    bool outerX = (tile.x == -edge && corner.x == 0u) || (tile.x == edge && corner.x == uint(OCEAN_GRID_CELLS));
    bool outerZ = (tile.y == -edge && corner.y == 0u) || (tile.y == edge && corner.y == uint(OCEAN_GRID_CELLS));
    if (outerX || outerZ)
    {
        gridPosition = frame.cameraPosition.xz + normalize(gridPosition - frame.cameraPosition.xz) * SKIRT_DISTANCE;
        displacement = vec3(0.0, frame.cameraPosition.y, 0.0);   // no wave: from that far, none is a pixel
    }
```

A vertex is on the outer edge when it is the first column of the leftmost
tiles, the last column of the rightmost, and the same for rows. The skirt gets
no wave's displacement, only the lift: four kilometres away, no wave is bigger
than a pixel.

That is why the panel's "Patches each side" starts at 1 here, where Chapter
29's starts at 0. With no patch on either side, the outer edge is the edge of
the camera's own patch, and the camera can stand on it: it starts right above
(0, 0), a corner of its patch, where the line from the camera to that vertex
has no direction and `normalize` of a zero vector is NaN. One ring of patches
keeps every outer vertex at least a patch away.

## 10. What the water reflects

### The sky and the sun, each counted once

**`skyReflection` reads the cube when the sky is on.** These are its lines, the
cube's binding first:

```glsl
layout(set = 1, binding = 9) uniform samplerCube skyCube;     // section 9: Chapter 23's sky, without its sun
```

```glsl
vec3 skyReflection(vec3 direction)
{
    direction = normalize(vec3(direction.x, max(direction.y, 0.0), direction.z));
    vec3 sky  = skyGradient(direction);
    if ((sea.flags & SEA_FLAG_SKY) != 0u)
    {
        sky = texture(skyCube, direction).rgb;
    }
    return sky;
}
```

The cube holds the sky **without the sun's disk** (Chapter 23 section 6). That
is what lets the water add the sun's own reflection, the glint, on top: a cube
that held the sun as well would put two suns in a calm sea, one sampled from the
cube and one from the glint.

A smooth sea needs only this mirror lookup; rough water would sample Chapter
24's specular cube at the level for its roughness (Chapter 24 section 6).

### The glint, in the sun's units

Chapter 29's glint, which Part 1 kept, is the sun times `pow(cos, 800)`: the
right shape, at a size chosen by eye. Next to a sky whose brightness is a fraction of the sun's, it has to be
the sun's own light reflected. A perfectly flat mirror would reflect the sun's
disk exactly, a tiny spot of radiance `E / Ω` (Chapter 23 section 6). A real
sea's pixel holds thousands of tiny facets tilted every way, which spread that
light into a lobe around the mirror direction. The lobe `cos^p` of the angle
from the mirror direction is Chapter 29's shape; what was missing is its size.

Spread over all directions, the lobe must deliver exactly the sun's irradiance,
no more and no less, so it is divided by its own total. Over the half of the
sphere in front of it, `cos^p` adds up to `2π / (p + 1)`. Two values make that
believable: `p = 0` is a lobe that is 1 everywhere, and it adds up to `2π`, the
half sphere's solid angle; `p = 1` adds up to `π`, the same π Chapter 15
section 9 divides Lambert's reflection by. So the lobe is

$$
\text{glint} = E \; \frac{p + 1}{2\pi} \cos^p\theta
$$

It is the same idea as Chapter 15 section 9's `(n + 8) / 8π` for Blinn-Phong,
a lobe divided by its own total, but not the same lobe: that one is a lobe of
facets around the half vector, and this one a lobe of light around the mirror
direction, so the constant differs. With `p = 800` the factor is
`801 / 2π = 127.5` per steradian. At the default sun, whose irradiance has a
luminance of 2.69 (its brightness as one number, Chapter 28 section 11), and a
grazing reflection where Fresnel is 0.1, the center of the glint is
`2.69 × 127.5 × 0.1 = 34`: far past 1, which is what Chapter 16's tone curve is
for. Step 1 of `main` becomes this; the comment says why, and only the `lobe`
line changes:

```glsl
    // 1. Reflection, with Schlick's Fresnel (Chapter 29 section 10): the sky, and the sun's glint. The
    //    glint is Chapter 29's lobe, scaled by (p + 1) / 2 pi so that it adds up to the sun's irradiance
    //    (Chapter 15 section 9's idea, for a different lobe). The cube holds no sun, so it is counted once.
    vec3  reflected = reflect(-toEye, normal);
    float facing    = clamp(dot(normal, toEye), 0.0, 1.0);
    float fresnel   = 0.02 + 0.98 * pow(1.0 - facing, 5.0);
    float lobe      = (GLINT_POWER + 1.0) / (2.0 * PI) * pow(max(dot(reflected, toSun), 0.0), GLINT_POWER);
    vec3  mirror    = skyReflection(reflected) + sun * lobe;
```

The water's own color already follows the same sun, `E / π` for a white
surface (section 4), so with this line the glint, the water, and the sky all
dim and brighten together.

The glint does not include the sky's exposure setting. Exposure brightens the
sky alone (Chapter 23 section 8), and the glint is the sun's light on the scene,
like any lit surface.

### The clouds, over both

Chapter 28 marches its clouds into a cube of their own, seen from the camera
like the sky's, and draws it over the sky. The water does the same with what it
reflects: the sky's cube first, then the clouds' over it. **The clouds' cube is
binding 10**, beside the sky's, read with the sky's sampler:

```glsl
layout(set = 1, binding = 10) uniform samplerCube cloudCube;  // section 10: Chapter 28's clouds, premultiplied
```

Each texel of that cube holds **premultiplied** color (Chapter 21 section 5):
the light the cloud sends toward the camera, and in alpha its opacity, how much
of what lies behind it the cloud hides. The light is already multiplied by the
opacity, so putting a cloud over the sky is one multiply and one add:
`sky × (1 − a) + cloud`. A thick cloud texel holding `(0.60, 0.60, 0.65)` with
opacity 0.8, over a sky of `(0.30, 0.45, 0.80)`, gives
`0.2 × (0.30, 0.45, 0.80) + (0.60, 0.60, 0.65) = (0.66, 0.69, 0.81)`: mostly
the cloud, with a fifth of the sky's blue through it. **These are the lines** in
`skyReflection`, after the sky's own `if`:

```glsl
    if ((sea.flags & SEA_FLAG_CLOUDS) != 0u)
    {
        // Premultiplied, as Chapter 28 draws them: their own light, and in alpha how much of the sky
        // behind they hide.
        vec4 clouds = texture(cloudCube, direction);
        sky = sky * (1.0 - clouds.a) + clouds.rgb;
    }
```

The sun's glint is the one thing the cube cannot carry, since neither cube
holds the sun. A cloud between the water and the sun dims the sunlight that
makes the glint, by the same opacity it hides the sun's disk with. So the lobe
is multiplied by `1 − a` read in the direction of the sun: a cloud of opacity
0.8 leaves a fifth of the glint, an overcast sky none. **These are the lines**,
in `main` after the lobe:

```glsl
    if ((sea.flags & SEA_FLAG_CLOUDS) != 0u)
    {
        lobe *= 1.0 - texture(cloudCube, toSun).a;   // section 10: under a cloud, the glint goes dark
    }
```

This reads the cube once for the whole sun, as if the sun were a point: the
glint follows whatever covers the middle of the disk. The disk is about half a
degree across and a texel of the 256-wide cube about a third of a degree, so
the two are close to the same size anyway.

Only fragment shaders read the clouds' cube here, and that is what Chapter 28's
barrier after the march names as the reader (Chapter 28 section 5). A compute
shader that read it, say to dim the foam under a cloud, would have to be added
to that barrier's destination in `Clouds::Update`, which Chapter 28 leaves out
on purpose: every later compute dispatch would then wait for the march.

### The haze meets the sky

Chapter 29 faded far water into its horizon color, which was also its clear
color. Now the haze fades it into **what the sky shows at the horizon straight
ahead**: `skyReflection` of the direction from the eye to the water, which the
function lifts to the horizon. Far water and the sky just above it are then the
same color, the band of brightness Chapter 23 put at the horizon included, and
the skirt makes the water reach it.

```glsl
    // 3. Haze: far water fades into what the sky shows at the horizon straight ahead.
    float range   = length(frame.cameraPosition.xyz - worldPosition);
    vec3  horizon = skyReflection(-toEye);
    color = mix(color, horizon, 1.0 - exp(-range / sea.hazeDistance));
```

## 11. The frame, in order, and what comes next

`Record` is complete; Appendix A prints it whole, with `RecordWaves`. Read top
to bottom, its numbered steps are the chapter:

1. the return trips, for every cascade: Chapter 29's, and the foam's, which keeps
   its contents (section 8);
2. the starting waves, each cascade its band, after a setting changed (sections
   3 and 5-7);
3. this moment's waves, Chapter 29's animate pass three times;
4. Chapter 29's FFT, three dispatches per stage and one barrier;
5. Chapter 29's maps, three times;
6. the foam, three times (section 8);
7. the preview, of one cascade;
8. the hand-overs, for every cascade;
9. the engine's sky, baked only if it changed (section 9);
10. the sea, the sky behind it, and the scene target handed back.

What it costs is on the panel. Look for the FFT at about three times Chapter
29's, as it should be, three cascades with the same work each, and the largest
of the compute steps. On a desktop GPU every one of these is a small fraction
of a millisecond; what is worth checking there is that the FFT still dominates
the compute, and how it grows at `N = 512`.

### Going further

- **Mipmaps for the small cascades.** Far away, one pixel covers many texels of
  the 7 m cascade, and its slopes alias into a fine shimmer. A texture that holds
  still has a mip chain for this (Chapter 15 section 5); these change every
  frame, so each would need its chain rebuilt every frame, or its slopes turned
  into a rougher glint where a pixel cannot show them.
- **A denser grid near the camera.** Every vertex is 2 m from the next, at any
  distance. Rings of grid around the camera, each twice as coarse as the one
  inside it, put the vertices where the eye is; their edges must be stitched so
  that no cracks open between them.
- **Better foam.** Foam here is a coverage, drawn as a flat color. A foam
  texture, scrolled by the waves and thresholded against the coverage, gives
  it the bubbly, streaky look of the real thing.
- **Shallow water.** JONSWAP is for deep water. Near a coast the waves slow
  down, steepen, and turn toward the shore; the TMA spectrum and a depth in the
  dispersion relation are the first step.

Chapter 31 puts a rock in this sea for the waves to break on, with spray from
Chapter 21's particles, and Chapter 32 floats a boat on it.

## Checkpoint

Run with `--demo Sea`, and pick "Sun sky" in the Tone mapping window's Sky
section. You can now see:

- the sea under a blue sky, the sun's disk above the glittering path, and no
  seam at the horizon: far water fades into the sky's bright band;
- **the edge.** Comment out the skirt's `if` block in the vertex shader: the
  brown band appears between the water and the horizon. Put it back;
- the reflection follow the sky: lower "Sun elevation" to 5° and the sky and the
  water's reflection of it turn orange and dim together. The glint keeps the
  panel's sun color, which does not redden as it sets;
- **the clouds.** Chapter 28's clouds are on by default with the sky. Under a
  bank of cloud the water turns grey, and far water fades into the clouds at the
  horizon. Turn "Sun azimuth" until a cloud covers the sun's disk: the glint
  goes out. Untick "Clouds" in the Sky section and it comes back;
- "Off": Chapter 29's gradient and clear color, as at the end of Part 3.

---

## When it does not work

| Symptom | Cause |
| --- | --- |
| A grid of repeats from above, with three cascades | Two cascades hold the same waves: check `Band` (section 2), and that each cascade's spectrum preview has a hole where the larger cascade's waves are |
| The sea far too rough, heights about 1.4 times the panel's `Hs` | The measured spectrum not halved: Chapter 29's `h(k, t)` uses every wave twice (section 5) |
| Every cascade has the same pattern, at three sizes | The seed is not offset per cascade (section 3) |
| One cascade much too strong or weak | `dk` from the wrong patch size: each cascade's `Δk` is `2π / L` with its own `L` (section 3) |
| JONSWAP's sea flat, or `NaN` black | `α` or `ωp` zero: `m_constants` never computed, the `spectrumConstants` line missing from `Update` (section 5) |
| The sea's surface gone, only the sky or the clear color where the water was, with JONSWAP or the swell on | `spreading` without its `max`: straight upwind its base is 0 only in exact arithmetic, a GPU's approximate reciprocal leaves it a hair below, `pow` of a negative number is `NaN`, and the FFT spreads it over the whole cascade (section 6) |
| No swell visible | The wind sea hides it: drop the wind to 5 m/s; or the swell's peak falls between texels (section 7) |
| Foam blinks with the crests, as in Chapter 29 | The foam pass is not reading its old value: the reset flag stuck on, or the return trip's old layout `UNDEFINED` on a GPU that discards (section 8) |
| Foam fills the whole sea and never fades | `max` replaced by `+`, or a fade of 0 |
| Garbage or flashes in the foam after a spectrum change | The reset flag is not set when the spectrum is rebuilt (section 8) |
| Validation: an image "expects layout SHADER_READ_ONLY_OPTIMAL, instead UNDEFINED" at submit | A map or the sky's cube is named in a set but not yet in that layout: the hand-overs (step 8), or a `Sky` older than Chapter 23's `Initialize` transition |
| A brown band below the horizon with the sky on | The skirt is missing (section 9) |
| A light seam where the water meets the sky | The haze fades to a fixed color instead of `skyReflection(-toEye)` (section 10) |
| Two suns in calm water | The cube holds the sun as well as the glint adding it: it must not (section 10) |
| A positive control below stays silent | Its maps are in an array of descriptors: the layer does not follow them (section 4) |

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and pick **Sea** in the demo picker:
      Chapter 29's sea, rougher up close, with the sky Off.
- [ ] **One cascade against three.** Fly up to about 160 m and look straight
      down. Solo "Cascade 1 alone": a grid of 37 m repeats. Solo off: no grid.
- [ ] **The bands.** In the Sea preview, "Spectrum |h0|": cascade 0 a disc,
      cascade 1 a ring with a dark middle. Solo cascade 1 and the middle fills in.
      The panel's text under each size shows section 2's table: 250 m to 6.2 m,
      6.2 m to 1.17 m, 1.2 m and shorter.
- [ ] **JONSWAP against Phillips.** Switch "Model": the spectrum changes from
      Phillips's round blob with a dark line across it to JONSWAP's half disc,
      and the sea from `Hs` 3.4 m to the printed 2.51 m.
- [ ] **Fetch.** 10 km prints a 15 m, 3.1 s peak and `Hs` 0.7 m; 300 km the
      fully grown 126 m, 9.0 s, about 4 m.
- [ ] **Crossing seas.** Wind 5 m/s, "Height" view, cascade 0: long swell crests
      at an angle to the short wind waves; untick "Swell" and they go.
- [ ] **Foam that lingers.** Fade 0.1 s: foam only on crests. Fade 3 s: patches
      left behind where crests broke, thinning over a few seconds.
- [ ] **The sky.** "Sun sky": the water reflects it, the glint sits under the
      sun's disk, and the far water meets the horizon with no seam and no brown
      band. "Environment": the test image's colors in the reflection, the right
      way up. "Off": Chapter 29's look.
- [ ] The panel's GPU milliseconds: the FFT is by far the largest of the
      compute steps — three cascades of Chapter 29's sixteen stages.
- [ ] The same at 4x MSAA, after resizing the window, and after switching to
      another demo and back, which keeps the settings and the camera.
      Synchronization validation, with the shader-access setting on, is silent
      through all of it, and quitting reports no leaked VMA allocation.
- [ ] **Positive control: the displacement's hand-over.** In `Record`'s step 8,
      change the displacement maps' destination stage from `VERTEX_SHADER` to
      `FRAGMENT_SHADER`. The first frame reports `SYNC-HAZARD-READ-AFTER-WRITE`
      at `vkCmdDraw`: the vertex shader reads binding 0 of set 1, which must be
      allowed at `VERTEX_SHADER`. Put it back. (With the three maps in one array
      binding, this control is silent — section 4.) Run it at this chapter's
      state: once Chapters 31 and 32 are built it is silent too, because their
      compute passes run between step 8 and the surface's draw and end in
      barriers to the vertex stage. On the Windows pass, deleting the boat's
      barrier alone did not bring it back; removing the `RecordSimulation`
      call did. From Chapter 31 on, that chapter's own controls cover this
      hand-over.
- [ ] **Positive control: the foam's return trip.** In step 1, change the foam's
      source stage from `FRAGMENT_SHADER` to `NONE`. From the second frame,
      `vkQueueSubmit2` reports `SYNC-HAZARD-WRITE-AFTER-READ`: the layout change
      would run while last frame's draw may still be reading the foam. Put it
      back.
- [ ] **Positive control: the foam's hand-over.** In step 8, change the foam's
      destination stage from `FRAGMENT_SHADER` to `COMPUTE_SHADER`: the first
      frame reports `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDraw`, for binding 6.
      Put it back.

## Sources

- K. Hasselmann et al., "Measurements of wind-wave growth and swell decay during
  the Joint North Sea Wave Project (JONSWAP)", *Deutsche Hydrographische
  Zeitschrift*, Reihe A, 12 (1973): the spectrum, its fetch laws, and `γ = 3.3`.
- W. J. Pierson and L. Moskowitz, "A proposed spectral form for fully developed
  wind seas", *Journal of Geophysical Research* 69 (1964): the fully grown sea.
- H. Mitsuyasu et al., "Observations of the directional spectrum of ocean waves
  using a cloverleaf buoy", *Journal of Physical Oceanography* 5 (1975), and
  D. E. Hasselmann et al. (1980): the `cos^(2s)` spreading and how `s` varies.
- C. J. Horvath, "Empirical directional wave spectra for computer graphics",
  DigiPro 2015: JONSWAP, spreading, and swell, put together for rendering.
- Jerry Tessendorf, "Simulating Ocean Water" (1999-2004): everything Chapter 29
  took from it.
- Cascades of FFT patches with bands that do not overlap are the common practice
  of real-time ocean renderers; the six-waves-per-patch boundary follows Ivan
  Pensionerov's open-source FFT ocean (2020).

## Appendix A — `Record` and `RecordWaves`, whole

Reference: the two functions sections 3 to 9 built up, as they stand at the
end.

```cpp
void SeaDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // Section 4: what this slot measured last time, then this frame's first timestamp.
    if (m_timestamps.Read(frame.frameIndex))
    {
        m_timings = SeaTimings{
            .waves   = m_timestamps.Milliseconds(0, 1),
            .fft     = m_timestamps.Milliseconds(1, 2),
            .maps    = m_timestamps.Milliseconds(2, 3),
            .surface = m_timestamps.Milliseconds(3, 4),
        };
    }
    m_timestamps.Reset(commandBuffer, frame.frameIndex);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 0);

    // 1. Return trips, as in Chapter 29, for every cascade.
    //    The foam is the exception (section 8): its contents must survive, so its old
    //    layout is the one it is really in, unless nothing in it is worth keeping yet.
    computeToComputeBarrier(commandBuffer);
    const VkImageLayout foamLayout = m_foamHistory ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
                                                   : VK_IMAGE_LAYOUT_UNDEFINED;
    for (const Cascade& cascade : m_cascades)
    {
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        transitionImage(commandBuffer, cascade.normals.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
        // Section 8: the foam, back to the foam pass, which reads it and writes it.
        transitionImage(commandBuffer, cascade.foam.image,
                        foamLayout, VK_IMAGE_LAYOUT_GENERAL,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                        VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    }
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // 2-7. Every cascade's waves, maps, and foam, and the preview.
    RecordWaves(commandBuffer, frame.frameIndex);

    // 8. Hand-overs, as in Chapter 29, for every cascade.
    for (const Cascade& cascade : m_cascades)
    {
        transitionImage(commandBuffer, cascade.displacement.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        transitionImage(commandBuffer, cascade.normals.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        // Section 8: the foam, to the fragment shader.
        transitionImage(commandBuffer, cascade.foam.image,
                        VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                        VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                        VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    }
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    m_foamHistory = true;   // from now on the foam maps hold foam worth keeping

    // 9. Section 9: the engine's sky, baked again only if it changed (Chapter 23 section 7). After this
    //    its cube can be sampled by the surface's fragment shader.
    //    Section 10: Chapter 28's clouds come with it; they need the camera and the time.
    m_skyOn    = frame.sky.mode != SkyMode::Off;
    m_cloudsOn = m_skyOn && frame.sky.clouds.enabled;
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
                 { .sunDirection   = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth),
                   .sunIrradiance  = sunIrradiance(m_settings),
                   .cameraPosition = m_cameraTransform.translation,
                   .time           = m_time });
    m_timestamps.Write(commandBuffer, frame.frameIndex, 3);

    // 10. The sea, then the scene target goes back to the engine.
    RecordSurface(commandBuffer, frame, PackSurface());
    m_timestamps.Write(commandBuffer, frame.frameIndex, 4);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

```cpp
void SeaDemo::RecordWaves(VkCommandBuffer commandBuffer, uint32_t frameIndex)
{
    const uint32_t groups = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);

    // Binds cascade c's set and pushes its constants for the next dispatch.
    const auto bindCascade = [&](uint32_t c, const void* constants, uint32_t size) {
        vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_cascadeLayout,
                                0, 1, &m_cascades[c].set, 0, nullptr);
        vkCmdPushConstants(commandBuffer, m_cascadeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, size, constants);
    };

    // 2. The starting waves, after a spectrum setting changed: each cascade its band.
    if (m_spectrumDirty)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_spectrumPipeline);
        for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
        {
            const SeaSpectrumParameters spectrum = PackSpectrum(c);
            bindCascade(c, &spectrum, sizeof(spectrum));
            vkCmdDispatch(commandBuffer, groups, groups, 1);
        }
        computeToComputeBarrier(commandBuffer);
        m_spectrumDirty = false;
        m_foamHistory   = false;   // section 8: the old foam belongs to another sea
    }

    // 3. This moment's waves: Chapter 29's animate pass, once per cascade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_animatePipeline);
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        const ocean::OceanParameters parameters = PackCascade(c);
        bindCascade(c, &parameters, sizeof(parameters));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }
    computeToComputeBarrier(commandBuffer);
    m_timestamps.Write(commandBuffer, frameIndex, 1);

    // 4. Chapter 29's FFT, for every cascade.
    RecordFft(commandBuffer);
    m_timestamps.Write(commandBuffer, frameIndex, 2);

    // 5. Chapter 29's maps, once per cascade.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_assemblePipeline);
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        const ocean::OceanParameters parameters = PackCascade(c);
        bindCascade(c, &parameters, sizeof(parameters));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }
    computeToComputeBarrier(commandBuffer);

    // 6. Section 8: each cascade's foam, from its Jacobian and its own last frame.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_foamPipeline);
    const SeaParameters sea = PackSurface();
    for (uint32_t c = 0; c < SEA_CASCADE_COUNT; ++c)
    {
        bindCascade(c, &sea, sizeof(sea));
        vkCmdDispatch(commandBuffer, groups, groups, 1);
    }

    // 7. Chapter 29's preview, of the cascade the panel picked.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_previewPipeline);
    const uint32_t               shown   = static_cast<uint32_t>(m_settings.previewCascade);
    const ocean::OceanParameters preview = PackCascade(shown);
    bindCascade(shown, &preview, sizeof(preview));
    vkCmdDispatch(commandBuffer, groups, groups, 1);
}
```

Next: [31 — Spray](31-Spray.md)
