# 29 — The FFT Ocean

**Goal:** an ocean that runs to the horizon, its waves computed every frame on
the GPU from a statistical description of the sea and an inverse FFT —
Tessendorf's method — with sharp crests, foam where they are squeezed, the
sun's glint, and every parameter on a panel. On the way you build a GPU FFT
and test it on its own, before any water exists.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Ocean/` with
shaders under `Shaders/Ocean/`.

**Module:** the demo is `pf::demos::ocean` (`OceanDemo`). It adds nothing to
the engine.

**Math:** four ideas the earlier chapters did not need, each taught where it is
first used: complex numbers (section 1), the Fourier transform and the FFT
(section 2), random numbers with a bell-shaped spread (section 7), and the
derivatives of waves and the Jacobian (sections 8 and 9). The chapter assumes
sine, cosine, angles in radians, and vectors as arrows with a dot product
(Chapter 10 section 1), and `exp` and its inverse `ln` as calculator buttons
(Chapter 21 section 3 uses `exp` for drag; Chapter 28 section 2 says what `e^-x`
does). Read sections 1 and 2 before any code: everything after them leans on
them.

**Prerequisites:**

- Chapter 20, nearly all of it: sections 2 (`createComputePipeline`), 3
  (workgroups, `groupCount`, the bounds guard, the limits table), 4 (storage
  images, their format qualifiers, `GENERAL`, and ping-pong between two sets
  built once), 5 (`computeToComputeBarrier`, why its destination is read *and*
  write, and the table of what sync validation can see), and 10 (a compute
  result read by graphics, and the return trip).
- Chapter 21 section 3 — `seedRandom` and `randomFloat` in `Random.glsl`.
- Chapter 09 — the `Demo` interface and `Setup`'s and `Teardown`'s contract
  (section 2), the scene part of the frame (section 4), registering a demo
  (section 7), and what runs when (section 9).
- Chapter 10 sections 2 (depth precision and the near plane), 6
  (`rotationFromYawPitch`), 7 (`FrameData`, `FrameBlock.glsl`, and
  `SceneRenderer`'s set 0), 9 (the depth buffer every scene pipeline declares),
  and 12 (`CameraControls` and the "Camera" panel).
- Chapter 07 section 2 — `ImGui_ImplVulkan_AddTexture`, which shows your own
  image in a panel.
- Chapter 08 sections 4 (the scene's colors are linear; an image shown with
  `ImGui::Image` holds display bytes; a color picked in ImGui is sRGB) and 8
  (C++/GLSL twin structs).
- Chapter 18 section 6 — every pipeline drawn in the scene pass takes the
  scene's sample count.
- Chapter 04 section 5 (the three questions) and its appendix, "Barriers the
  later chapters add", whose compute table already lists this chapter's rows.

Chapter 11 section 14 (Lambert's dot product) and Chapter 15 section 9
(Fresnel) teach the surface's shading in full. Section 10 here says what it
uses of them, so neither is required.

---

## Where this is going

Look at the sea from a cliff and it is not one wave but thousands: long swells
from far away, shorter waves the local wind is raising, ripples on those, all
moving at once, each at its own speed. Jerry Tessendorf's method, written up as
SIGGRAPH course notes in 1999 and used in film and games since, takes that
literally. It describes the sea as tens of thousands of simple waves, chooses
their sizes from what oceanographers measured on real seas, and adds them all
up at every point of a grid, every frame.

Adding 65,536 waves at each of 65,536 points is four billion multiply-adds a
frame, too many even for a GPU. The **fast Fourier transform** (FFT) does the
same sum in about a million. Half of this chapter is that trick; the other half
is what feeds it and what it feeds.

One frame, end to end:

```text
 wind -> [ spectrum, sec. 7 ] -> h0: the starting waves   (only when a setting changes)
                                  |
 time -> [ animate, sec. 8 ]  <---+
              |  eight spectra, packed into two images
              v
         [ FFT, sec. 5 ]  16 dispatches at N = 256: waves -> heights
              |
              v
         [ assemble, sec. 9 ] --> displacement map --> surface vertex shader   (sec. 10)
              |               --> normals + foam  --> surface fragment shader  (sec. 10)
              v
         [ preview, sec. 6 ]  --> a picture of any of these, in a panel
```

The chapter is in three parts:

- **Part 1, "An FFT on the GPU"** (sections 1-6): the math of waves and of the
  transform, then a compute pass that runs the FFT, tested on single waves in a
  preview window. It ends with pictures you can check against the worked
  examples of section 2.
- **Part 2, "The ocean's maps"** (sections 7-9): the sea's spectrum, its
  motion, sharp crests and foam, all as images in the preview.
- **Part 3, "The surface"** (sections 10-12): the water those maps move and
  light, and the panel that edits it all.

This demo keeps a simple sky and sun of its own: a gradient for the water to
reflect, and two sliders for the sun. That way it needs only Chapters 01-10,
18 section 6, 20, and 21 section 3, and a reader can come here straight from
the compute chapters. The engine's sky (Chapter 23) and clouds (Chapter 28) do
not draw here, although their Sky header in the "Tone mapping" window still
shows; Chapter 30 puts them into the water.

### What you are actually writing

**This is `OceanDemo.h`**, the map of the chapter. Every private function names
the section that writes it.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 29: a Tessendorf ocean - an FFT on the GPU, and the sea it moves
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Ocean/OceanDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"
#include "Ocean/OceanTypes.h"

#include <glm/glm.hpp>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <bit>
#include <cstdint>

namespace pf::demos::ocean {

// What the two panels edit (sections 6 and 11). CPU state: it survives Teardown and Setup.
// Colors are sRGB, as the swatches show them; PackParameters converts them.
struct OceanSettings
{
    // Part 1: the test wave and the preview (section 6).
    bool  testWave    = false;              // transform the test wave instead of the ocean
    int   testWaveX   = 3;                  // waves across one patch, in x
    int   testWaveZ   = 0;                  // ...and in z
    bool  testMirror  = false;              // add the mirror wave at -k
    bool  skipSignFix = false;              // see what the (-1)^(x+y) fixes
    int   view        = OCEAN_VIEW_HEIGHT;  // what the preview shows
    float previewGain = 1.0f;               // the preview's brightness

    // The spectrum: changing any of these rebuilds h0 (section 7).
    float windSpeed   = 12.0f;              // m/s
    float windAzimuth = 0.0f;               // degrees the wind blows toward, turning from -Z toward +X
    float amplitude   = 0.002f;             // Phillips A
    float patchSize   = 300.0f;             // L, metres
    float suppression = 0.5f;               // l, metres
    int   seed        = 1;                  // which random ocean

    // Per frame, free (sections 8-10).
    float choppiness    = 1.0f;             // lambda
    float timeScale     = 1.0f;
    float loopPeriod    = 0.0f;             // seconds; 0 never repeats
    float foamThreshold = 0.7f;             // a Jacobian below this is foam
    glm::vec3 waterColor { 0.03f, 0.16f, 0.20f };   // sRGB
    glm::vec3 skyColor   { 0.70f, 0.80f, 0.90f };   // sRGB, at the horizon
    float sunElevation  = 15.0f;            // degrees above the horizon
    float sunAzimuth    = 0.0f;             // degrees, turning from -Z toward +X
    float sunIntensity  = 20.0f;            // how bright its reflection is
    float hazeDistance  = 900.0f;           // metres
    int   tileRadius    = 1;                // patches drawn on each side of the camera's
};

// One image the passes read and write, with its view.
struct OceanImage
{
    VkImage       image      = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    VkImageView   view       = VK_NULL_HANDLE;
};

class OceanDemo final : public Demo
{
public:
    OceanDemo();   // CPU only: where the camera starts

    const char*          Name() const override { return "Ocean"; }
    InitializationResult Setup(const DemoContext& context) override;                    // sections 3-10
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // section 3
    void                 Update(const FrameInput& input) override;                      // sections 3, 6, 10, 11
    void                 Record(const RecordContext& frame) override;                   // sections 3-10
    void                 Teardown() override;                                           // section 6
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    InitializationResult CreateImages();             // section 4
    InitializationResult CreateDescriptors();        // section 4
    InitializationResult CreateComputePipelines();   // section 5, grown in 6-9
    InitializationResult CreateSurface();            // section 10
    OceanParameters      PackParameters() const;     // section 6, whole in 7
    void RecordFft(VkCommandBuffer commandBuffer);   // section 5
    void RecordSurface(VkCommandBuffer commandBuffer, const RecordContext& frame,
                       const OceanParameters& parameters);   // section 10

    // N, the FFT's size: 256 x 256 waves and heights. 512 is the usual choice on a GPU.
    static constexpr uint32_t FFT_SIZE   = 256;
    static constexpr uint32_t FFT_STAGES = std::countr_zero(FFT_SIZE);   // log2(N)
    static_assert(std::has_single_bit(FFT_SIZE), "The FFT needs a power of two.");

    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;   // section 10: set 0, the camera

    // Section 4. The FFT works on A and B together, ping-ponging between [0] and [1].
    OceanImage                m_h0;                   // rg32f: the starting waves
    std::array<OceanImage, 2> m_spectrumA;            // rgba32f: two complex numbers per texel
    std::array<OceanImage, 2> m_spectrumB;            // rgba32f: two more
    OceanImage                m_displacement;         // rgba16f: what moves the grid
    OceanImage                m_normals;              // rgba16f: normal xyz, Jacobian w
    OceanImage                m_preview;              // rgba8: the panel's picture
    VkDescriptorSet           m_previewTexture = VK_NULL_HANDLE;   // ImGui's name for m_preview

    // Section 4. The FFT's two sets are its ping-pong; one set serves every other pass.
    VkDescriptorSetLayout          m_fftSetLayout   = VK_NULL_HANDLE;
    VkDescriptorSetLayout          m_oceanSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool               m_descriptorPool = VK_NULL_HANDLE;
    std::array<VkDescriptorSet, 2> m_fftSets{};
    VkDescriptorSet                m_oceanSet = VK_NULL_HANDLE;

    // Sections 5-9: the compute passes.
    VkPipelineLayout m_fftLayout        = VK_NULL_HANDLE;
    VkPipelineLayout m_oceanLayout      = VK_NULL_HANDLE;
    VkPipeline       m_fftPipeline      = VK_NULL_HANDLE;   // section 5
    VkPipeline       m_testWavePipeline = VK_NULL_HANDLE;   // section 6
    VkPipeline       m_previewPipeline  = VK_NULL_HANDLE;   // section 6
    VkPipeline       m_spectrumPipeline = VK_NULL_HANDLE;   // section 7
    VkPipeline       m_animatePipeline  = VK_NULL_HANDLE;   // section 8
    VkPipeline       m_assemblePipeline = VK_NULL_HANDLE;   // section 9

    // Section 10: the surface.
    VkSampler             m_sampler          = VK_NULL_HANDLE;
    VkDescriptorSetLayout m_surfaceSetLayout = VK_NULL_HANDLE;
    VkDescriptorPool      m_surfacePool      = VK_NULL_HANDLE;
    VkDescriptorSet       m_surfaceSet       = VK_NULL_HANDLE;
    VkPipelineLayout      m_surfaceLayout    = VK_NULL_HANDLE;
    VkPipeline            m_surfacePipeline  = VK_NULL_HANDLE;

    // CPU state: survives Teardown, so switching back finds everything as it was.
    OceanSettings         m_settings;
    scene::Camera         m_camera;
    scene::Transform      m_cameraTransform;
    scene::CameraControls m_controls;
    float                 m_time          = 0.0f;   // ocean seconds: scaled by timeScale
    bool                  m_spectrumDirty = true;   // h0 must be rebuilt before it is next read
};

} // namespace pf::demos::ocean
```

Everything the panels edit lives in `OceanSettings`, and the camera lives in
the demo object, so switching to another demo and back keeps both (Chapter 09
section 2). The images get a small struct of their own, `OceanImage`, because
there are eight of them and each needs the same three handles. `FFT_SIZE` is
the one number that sets the FFT's resolution; `FFT_STAGES` follows from it
(`std::countr_zero(256)` is 8, from `<bit>`), and every shader asks its images
for their size rather than being told.

### Where everything lands

```text
Shaders/Ocean/
  OceanTypes.h              C++/GLSL twins: FftParameters, OceanParameters  section 5
  Ocean.glsl                complex numbers and spectrum texels              sections 5 and 7
  FftStage.comp.glsl        one stage of the FFT                             section 5
  FftTestWave.comp.glsl     Part 1's input: one wave                         section 6
  OceanPreview.comp.glsl    the preview's picture                            sections 6 and 9
  OceanSpectrum.comp.glsl   the starting waves, h0                           section 7
  OceanAnimate.comp.glsl    the waves at this moment, and their derivatives  section 8
  OceanAssemble.comp.glsl   displacement, normal, Jacobian                   section 9
  OceanSurface.vert.glsl    the grid, moved                                  section 10
  OceanSurface.frag.glsl    water                                            section 10
Source/PillowFort/Demos/Ocean/
  OceanDemo.h/.cpp          the demo
Source/SandboxGame/Main.cpp + one registration line                          section 3
```

```text
OceanDemo.cpp
  includes
  static sunTravelDirection(elevation, azimuth)            section 7
  namespace pf::demos::ocean {
      using namespace vulkan_graphics;
      static createOceanImage, destroyOceanImage           section 4
      static VIEW_NAMES                                    section 6, grown in 7 and 9
      static drawPreviewPanel(settings, preview)           section 6
      static drawOceanPanel(settings, shaderTime)          section 11
      OceanDemo::OceanDemo                                 section 3
      OceanDemo::Setup                                     section 3, grown in 4-7 and 10
      OceanDemo::CreateImages                              section 4
      OceanDemo::CreateDescriptors                         section 4
      OceanDemo::CreateComputePipelines                    section 5, grown in 6-9
      OceanDemo::CreateSurface                             section 10
      OceanDemo::Resize                                    section 3
      OceanDemo::Update                                    section 3, grown in 6, 10, 11
      OceanDemo::PackParameters                            section 6, whole in 7
      OceanDemo::RecordFft                                 section 5
      OceanDemo::RecordSurface                             section 10
      OceanDemo::Record                                    section 3, grown in 5-10; Appendix A
      OceanDemo::Teardown                                  section 3, whole in 6
  }
```

`OceanDemo.cpp` includes `OceanDemo.h`, `PillowFort/DebugPanels/DemoPanel.h`,
`PillowFort/Scene/ColorSpace.h`, `PillowFort/VulkanGraphics/GraphicsPipeline.h`,
`PillowFort/VulkanGraphics/VulkanBarriers.h`, `<imgui.h>`,
`<imgui_impl_vulkan.h>`, and `<cmath>`.

> **Rerun `GenerateProjects.bat`** after creating these files, and again
> whenever a later section adds one. Premake expands both the C++ and the
> shader globs when it generates the projects; a shader added afterwards is
> not built, and `Setup` then fails on a missing `.spv`.

---

# Part 1 — An FFT on the GPU (sections 1-6)

Sections 1 and 2 have no code. They are the idea everything else is built on,
and they are the longest stretch of new math in the tutorial, so every formula
in them comes with numbers small enough to check by hand. Sections 3-6 then
build the demo's skeleton, the images, the FFT pass, and a preview that shows
whether the FFT does what section 2 says it does.

## 1. Waves as numbers

> **Jump:** until now every number a shader handled was a position, a color, a
> direction, or a count. This chapter's central object is a *wave*, and the
> natural way to hold one is a **complex number**: two numbers that behave like
> an arrow you can turn. Keep in mind from here that a complex number is a
> `vec2`, and that multiplying by one turns and stretches an arrow. Nothing
> more mysterious than that is needed.

### What describes a wave

Take a wave running along a line, `h(x) = A cos(k x + φ)`. Three numbers
describe it:

- **A**, the amplitude: how far the surface rises above its mean and sinks
  below it, in metres.
- **k**, the wave number: how many radians the wave turns through per metre.
  One wavelength is one whole turn, `2π`, so `k = 2π / wavelength`. A 100 m
  wave has `k = 0.0628`, a 10 m wave `k = 0.628`.
- **φ**, the phase: where in its cycle the wave is at `x = 0`.

On a surface the wave runs in a direction, so `k` becomes a vector, the **wave
vector**. It points the way the wave travels, its length `|k|` is
`2π / wavelength`, and the height at a point `p` on the surface is
`A cos(k · p + φ)`. The crests are lines across `k`:

```text
       crest         crest         crest
      /     \       /     \       /
  ---/-------\-----/-------\-----/----   mean level      k  ---->
              \___/         \___/
             trough        trough
      |<-- wavelength -->|
```

### Amplitude and phase as one arrow

Amplitude and phase belong together. Draw an arrow of length `A` at angle `φ`
from the horizontal: its shadow on the horizontal axis, `A cos φ`, is the
wave's height at `x = 0`. Walk along the wave by `x` and the arrow turns by
`k x`; its shadow is still the height. **A wave is an arrow that turns as you
move along it** — and, from section 8, as time passes.

A **complex number** is such an arrow, written as two numbers: `a + ib`, where
`a` is how far the arrow reaches along the horizontal axis (the *real part*)
and `b` how far up (the *imaginary part*). In a shader it is a `vec2(a, b)`.
The arrow of length 1 at angle `θ` is `cos θ + i sin θ`, and is written
`e^(iθ)`. Read `e^(iθ)` as a name, "the unit arrow at angle θ"; nothing here
needs any other property of `e`.

Adding complex numbers adds arrows, component by component, as `vec2`s do.
**Multiplying** is the new part. It follows from one rule, `i · i = −1`:

```text
(a + ib)(c + id) = (ac − bd) + i(ad + bc)
```

What it does is easier to see than the formula: **the lengths multiply, and the
angles add.** Multiplying by `e^(iθ)`, whose length is 1, only turns an arrow
by `θ`. Multiplying by `i` — length 1, angle 90° — turns it a quarter turn:
`i(a + ib) = −b + ia`.

A worked example. An arrow of length 2 at 30° is `2 cos 30° + i 2 sin 30° =
1.732 + 1i`. Turning it by 60° should give length 2 at 90°, which is `2i`.
Multiply by `e^(i60°) = 0.5 + 0.866i`:

```text
(1.732 + 1i)(0.5 + 0.866i) = (1.732 × 0.5 − 1 × 0.866) + i(1.732 × 0.866 + 1 × 0.5)
                           = (0.866 − 0.866)          + i(1.5 + 0.5)
                           = 0 + 2i
```

`complexMultiply`, in section 5's `Ocean.glsl`, is that formula with `a.x`,
`a.y`, `b.x`, `b.y` for `a`, `b`, `c`, `d`.

One more operation. The **conjugate** of `a + ib` is `a − ib`: the same arrow
reflected in the horizontal axis, its angle negated. Section 2 shows why the
ocean cannot do without it.

So a wave with amplitude `A` and phase `φ` is described by one complex number,
`c = A e^(iφ)`, and its height at `x` is the real part of `c` turned by `k x`.
The sum in section 2 is a sum of waves written that way.

## 2. A sum of waves, and the fast way to add it up

> **Jump:** before this chapter, every image you made held values at *places*:
> heights, colors, cells. A **spectrum** holds values at *wave vectors*: a
> texel is not a place but one wave, and its complex number is that wave's
> amplitude and phase. The inverse Fourier transform turns a spectrum into an
> image of places by adding up all its waves. Keep the two kinds of image
> apart; this chapter always says which one an image is.

### The inverse transform, in one dimension

Take `N` samples of a height, equally spaced across a patch that repeats. The
only waves that fit a repeating patch are those with a whole number of cycles
across it: 0, 1, 2, ... up to `N − 1`. A list of one complex number per wave,
`X[w]`, is a spectrum, and the **inverse discrete Fourier transform** turns it
into the samples:

```text
x[n] = sum over w = 0 .. N−1 of   X[w] · e^(2πi · w · n / N)
```

In words: at sample `n`, wave `w` has turned through `2π · w · n / N`. Take its
arrow `X[w]`, turn it by that much, and add all `N` arrows.

A worked example with `N = 4`. Let the spectrum be `X = [0, 1, 0, 0]`: only
wave 1, amplitude 1, phase 0. At samples 0, 1, 2, 3 it has turned 0°, 90°,
180°, 270°, so

```text
x = [1, i, −1, −i]
```

That is not a list of heights. Heights are real numbers, and half of these are
imaginary: the real parts `[1, 0, −1, 0]` are a cosine, the imaginary parts
`[0, 1, 0, −1]` a sine.

Now add wave 3, with the conjugate of wave 1's amplitude: `X = [0, 1, 0, 1]`.
Wave 3 turns 270° per sample, which is the same as −90°: it is wave 1 turning
the other way, wave −1. At every sample its arrow is wave 1's reflected, so the
imaginary parts cancel:

```text
x = [1 + 1,  i − i,  −1 − 1,  −i + i] = [2, 0, −2, 0]
```

A real cosine. That is the rule the whole ocean rests on: **the transform gives
real heights exactly when every wave `w` has its mirror, `−w`, holding the
conjugate of its amplitude.** Section 8 builds the ocean's spectrum that way,
and section 6's first test shows both cases on screen.

Wave `−w` and wave `N − w` are the same wave, because turning 270° per sample
is turning −90°. In a 4-point spectrum 3 is −1, and 2 is both +2 and −2: wave
`N/2`, the fastest wave the samples can show, is its own mirror.

### Where −k sits in the images

The ocean's spectrum images are **centred**, so that the long waves, which carry
most of the height, sit in the middle of the preview where you can see them.
Texel `n` holds wave number `n − N/2`, and wave 0 is texel `N/2`. With `N = 4`,
texels 0, 1, 2, 3 hold waves −2, −1, 0, 1.

In two dimensions texel `(n, m)` holds wave numbers `(n − N/2, m − N/2)`: that
many cycles across the patch in x and in z. For a patch `L` metres wide its
wave vector is

```text
k = 2π (n − N/2, m − N/2) / L         radians per metre
```

and **the mirror wave, `−k`, is in texel `((N − n) mod N, (N − m) mod N)`**: the
texel reflected through the centre. One row and one column are the exception.
Texel 0 holds wave `−N/2`, and `(N − 0) mod N` is 0 again: it is its own mirror,
with no partner to cancel its imaginary part. The ocean leaves row 0 and column
0 of its spectrum empty (section 7), which costs it only the very shortest
waves.

### Two dimensions, and why it must be fast

In two dimensions the sum runs over all `N²` waves at each of `N²` texels. That
is separable: transform every row as a one-dimensional transform, then every
column of the result, and you get the two-dimensional answer.

Done directly, it is `N²` outputs times `N²` terms, `N⁴` complex multiply-adds.
At `N = 256` that is 4.3 billion, every frame. The **fast Fourier transform**
(Cooley and Tukey, 1965) gets the same result in `2 · N² · log2 N`, about one
million at `N = 256`.

### The FFT: split, transform, combine

The trick is to split the sum into the even-numbered waves and the odd-numbered
ones. The even waves `X[0], X[2], X[4]`, and so on, are a spectrum of `N/2`
waves on their own, with an inverse transform `E[n]`. The odd ones are too,
`O[n]`, except that each odd wave turns one extra step, `e^(2πi n / N)`, per
sample. Here is why. Wave `2m + 1` at sample `n` has turned
`2π (2m + 1) n / N = 2π m n / (N/2) + 2π n / N`. The first part is wave `m` of
a transform of `N/2` samples; the second is the same extra turn for every odd
wave, so it comes outside the sum as one factor. And a transform of `N/2`
samples repeats every `N/2` samples, so `E[n + N/2] = E[n]` and
`O[n + N/2] = O[n]`: half a patch further on, only the extra turn has changed,
by half a turn. So

```text
x[n]       = E[n] + e^(2πi n / N) · O[n]
x[n + N/2] = E[n] − e^(2πi n / N) · O[n]          (half a turn further: e^(iπ) = −1)
```

Two half-size transforms and `N` cheap combinations give the full one. Each
half splits the same way, down to transforms of size 1, which are just their
input. That is `log2 N` levels, and each level combines pairs of numbers into
pairs of numbers: `a` and `b` become `a + w b` and `a − w b`. That combination is
called a **butterfly**, and the turns `w` are the **twiddle factors**.

Check it on the same `X = [0, 1, 0, 0]`. The evens are `[X0, X2] = [0, 0]`, so
`E = [0, 0]`. The odds are `[X1, X3] = [1, 0]`, and a two-point transform is
`[a + b, a − b]`, so `O = [1, 1]`. Combine, with twiddles `1` and `i` for
`n = 0` and `1`:

```text
x[0] = E[0] + 1 · O[0] =  1          x[2] = E[0] − 1 · O[0] = −1
x[1] = E[1] + i · O[1] =  i          x[3] = E[1] − i · O[1] = −i
```

`[1, i, −1, −i]`, as before.

### Bottom-up, and bit reversal

A GPU runs the levels in order, smallest first. **Stage 0** combines pairs of
neighbours, stage 1 pairs two apart, stage `s` pairs `span = 2^s` apart, in
groups of `2 · span`. Each stage needs the whole previous stage finished, so
each stage is one dispatch, with a barrier after it.

Which inputs does stage 0 pair? The splitting put evens before odds at every
level. For `N = 4` the order is `X0 X2 | X1 X3`; for `N = 8` it is
`X0 X4 X2 X6 X1 X5 X3 X7`. That order is each position's index with its bits
written backwards: position 3 is `011`, reversed `110`, so it holds `X6`. So
stage 0 reads its inputs in **bit-reversed** order, and then the last stage
writes its outputs in natural order with no extra pass.

Here is the whole `N = 4` inverse transform. Each row is one output position of
a stage, which in section 5 is one invocation of the shader:

```text
          stage 0: span 1, groups of 2          stage 1: span 2, groups of 4
          reads X in bit-reversed order         reads stage 0's s0 .. s3
position  pairs (X0, X2) and (X1, X3)           pairs (s0, s2) and (s1, s3)

   0      s0 = X0 + 1 · X2                      x0 = s0 + 1 · s2
   1      s1 = X0 − 1 · X2                      x1 = s1 + i · s3
   2      s2 = X1 + 1 · X3                      x2 = s0 − 1 · s2
   3      s3 = X1 − 1 · X3                      x3 = s1 − i · s3

          twiddles 1, −1                        twiddles 1, i, −1, −i
```

With `X = [0, 1, 0, 0]`, stage 0 gives `s = [0, 0, 1, 1]` and stage 1
`x = [1, i, −1, −i]`.

Notice that every output is "top plus twiddle times bottom": the outputs that
section 2's formula writes as `a − w b` are `a + (−w) b`, and `−w` is the twiddle
for a position half a group further on. Position `j` in a group of size `G`
uses `e^(2πi j / G)` — 1 and −1 in stage 0, then 1, `i`, −1, `−i` in stage 1 — so
the shader computes the same expression for every output and never asks
whether it is in the top or the bottom half.

One last detail. The forward transform, places to waves, uses `e^(−2πi ...)`.
This chapter only ever goes from waves to heights, so it only needs the
inverse, and it does not divide by anything: a wave of amplitude 1 comes out
with height 1, as in the examples above.

## 3. The demo, empty

Before any image or shader, the demo needs to exist: registered, picked in the
"Demos" window, and filling the scene target. Everything in this section is
Chapter 09's pattern, so it goes quickly.

**This is the constructor.** A demo's constructor holds CPU state only — no
device exists yet (Chapter 09 section 2) — and all this one does is say where
the camera of Part 2 starts:

```cpp
OceanDemo::OceanDemo()
{
    m_controls.active             = scene::ControllerKind::Fly;
    m_controls.fly.moveSpeed      = 20.0f;
    m_camera.nearPlane            = 0.5f;
    m_camera.farPlane             = 5000.0f;
    m_cameraTransform.translation = glm::vec3(0.0f, 12.0f, 0.0f);
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = glm::radians(-8.0f) });
}
```

Part 1 draws nothing in 3D, but the header declares the constructor, so it is
written now. The numbers are for section 10: Chapter 10's fly controller, 12 m
above the water and pitched 8° down so the horizon sits a little above the
middle of the view, moving at 20 m/s because the sea is big. The far plane is 5 km
because the water runs out to the haze, and the near plane moves out to 0.5 m
because depth precision depends on the ratio of the two (Chapter 10 section 2).

**This is `Setup`, as it starts.** Sections 4 to 7 and 10 each add a line or
two:

```cpp
InitializationResult OceanDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    return InitializationResult::success();
}
```

**This is `Resize`.** The FFT's images are `N x N` whatever the window is, and
the scene's color and depth targets belong to the renderer, so there is nothing
to do:

```cpp
// Nothing here is sized to the window: the FFT's images are N x N, and the
// scene's color and depth targets are the renderer's.
InitializationResult OceanDemo::Resize(const SceneTargets& /*targets*/)
{
    return InitializationResult::success();
}
```

**This is `Update`, as it starts:** it keeps the ocean's clock. Part 1 has no
use for time yet, and the time scale is Part 2's, but the line is the same
then:

```cpp
void OceanDemo::Update(const FrameInput& input)
{
    m_time += input.deltaSeconds * m_settings.timeScale;
}
```

Adding up scaled frame times, rather than scaling `elapsedSeconds`, means that
moving the "Time scale" slider changes how fast the sea moves from now on,
instead of jumping it to a different moment.

**This is `Record`, as it starts:** clear the scene target to a sky blue and
hand it back, Chapter 09 section 4's contract.

```cpp
void OceanDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    const VkClearColorValue sky{ { 0.41f, 0.60f, 0.80f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &sky);
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

**This is `Teardown`, as it starts:** empty, because `Setup` made nothing.
Section 6 writes it whole.

```cpp
void OceanDemo::Teardown()
{
}
```

**And this is the registration**, in `Source/SandboxGame/Main.cpp`, after the
grass (Chapter 09 section 7):

```cpp
#include "PillowFort/Demos/Ocean/OceanDemo.h"
```

```cpp
    demoList.push_back(std::make_unique<demos::ocean::OceanDemo>());             // Chapter 29
```

Rerun `GenerateProjects.bat`, build, and run with `--demo Ocean`. You should
see an empty blue sky, and "Ocean" selected in the "Demos" window.

---

## 4. The images, and the sets that name them

**This is `CreateImages`, and the eight images it makes.** Each holds `N x N`
texels, and each has one job:

| Image | Format | Holds | Written by | Read by |
| --- | --- | --- | --- | --- |
| `m_h0` | `R32G32_SFLOAT` | the starting waves: one complex number per wave (a spectrum) | the spectrum pass (7), when a setting changes | the animate pass (8), the preview |
| `m_spectrumA[0]`, `[1]` | `R32G32B32A32_SFLOAT` | two complex numbers per texel: waves before the FFT, heights after | the animate pass or the test wave, then each FFT stage | each FFT stage, the assemble pass (9), the preview |
| `m_spectrumB[0]`, `[1]` | `R32G32B32A32_SFLOAT` | two more | as A | as A |
| `m_displacement` | `R16G16B16A16_SFLOAT` | how far each point of the grid moves, in metres | the assemble pass (9) | the surface's vertex shader (10), the preview |
| `m_normals` | `R16G16B16A16_SFLOAT` | the surface's normal, and in `w` the Jacobian that says where the foam is | the assemble pass (9) | the surface's fragment shader (10), the preview |
| `m_preview` | `R8G8B8A8_UNORM` | a picture of any of the above, as display bytes | the preview pass (6) | ImGui |

Why two images of two complex numbers each: the ocean needs eight real fields
— the height, two sideways displacements, two slopes, and three derivatives for
the foam — and section 8 shows that one complex transform can carry two real
ones. Four complex transforms, two per texel, in two images. Part 1 uses only
the first complex number of A.

Why each has two copies, `[0]` and `[1]`: a stage of the FFT reads every texel
of the previous stage's output, so it cannot write in place. Chapter 20 section
4's ping-pong: each stage reads one copy and writes the other.

Why the formats differ. The FFT adds up 65,536 terms, so it works in 32-bit
floats; a 16-bit float keeps only about three decimal digits. The two maps the
surface samples are 16-bit, because a sampler may only filter
`R32G32B32A32_SFLOAT` where the device says it can, while
`R16G16B16A16_SFLOAT` is filterable everywhere — and 16 bits hold a height of
10 m to within a centimetre. Every format here is on Chapter 20 section 4's
list of formats guaranteed to work as storage images. The preview is
`R8G8B8A8_UNORM` because ImGui shows an image's bytes as they are (Chapter 08
section 4's table): the preview pass writes the colors you should see, not
linear light.

`createOceanImage` is a `static` function inside the namespace, because it
names the demo's `OceanImage`. It is Chapter 20's image creation with the
format and usage as parameters, `createOceanImage(vulkan, format, size, usage,
image)`: one `size × size` 2D image with one mip level, made with VMA, and a 2D
view of it, returning false if either fails. Nothing in it is new, so it is in
Appendix B. Its partner, beside it, is short enough to read here:

```cpp
// Section 4, for Teardown (section 6). Null handles are no-ops, so this is safe on an
// image that was never made.
static void destroyOceanImage(VulkanContext& vulkan, OceanImage& image)
{
    vkDestroyImageView(vulkan.device, image.view, nullptr);
    vmaDestroyImage(vulkan.allocator, image.image, image.allocation);
    image = OceanImage{};
}
```

And `CreateImages` itself, which makes the eight and moves them to the layout
their first user needs:

```cpp
InitializationResult OceanDemo::CreateImages()
{
    // Every image is N x N. The FFT's are 32-bit floats; the maps the surface
    // samples are 16-bit, which every GPU can filter; the preview is display bytes.
    const VkImageUsageFlags storage           = VK_IMAGE_USAGE_STORAGE_BIT;
    const VkImageUsageFlags storageAndSampled = VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    const struct
    {
        OceanImage*       image;
        VkFormat          format;
        VkImageUsageFlags usage;
    } images[] = {
        { &m_h0,           VK_FORMAT_R32G32_SFLOAT,       storage },
        { &m_spectrumA[0], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
        { &m_spectrumA[1], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
        { &m_spectrumB[0], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
        { &m_spectrumB[1], VK_FORMAT_R32G32B32A32_SFLOAT, storage },
        { &m_displacement, VK_FORMAT_R16G16B16A16_SFLOAT, storageAndSampled },
        { &m_normals,      VK_FORMAT_R16G16B16A16_SFLOAT, storageAndSampled },
        { &m_preview,      VK_FORMAT_R8G8B8A8_UNORM,      storageAndSampled },
    };
    for (const auto& entry : images)
    {
        if (!createOceanImage(m_context.vulkan, entry.format, FFT_SIZE, entry.usage, *entry.image))
        {
            return InitializationResult::failure("Creating an ocean image failed.");
        }
    }

    // Every image is first touched by a compute shader, in GENERAL. Move them all
    // there once (Chapter 20 section 4); Record moves the three that are sampled
    // out of GENERAL and back every frame (sections 6 and 10).
    immediateSubmit(m_context.vulkan, [&](VkCommandBuffer commandBuffer) {
        for (const auto& entry : images)
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

The transition at the end answers Chapter 04's three questions the way Chapter
20 section 4 did for Life's cells: nothing came before (`NONE`), the first user
is a compute shader that reads and writes, and the layout goes from
`UNDEFINED` to `GENERAL`, the only layout storage images can be used in. The
three images that are also sampled leave `GENERAL` every frame and come back
(section 10); the others never leave it.

**This is `CreateDescriptors`.** Two set layouts, both only storage images. The
FFT's set has four bindings — two images in, two out — and is allocated twice,
for the ping-pong. The ocean's set has six, one per image the other passes
touch, and is allocated once:

| Binding | FFT set 0 | FFT set 1 | Ocean set |
| --- | --- | --- | --- |
| 0 | `m_spectrumA[0]`, read | `m_spectrumA[1]`, read | `m_h0` |
| 1 | `m_spectrumB[0]`, read | `m_spectrumB[1]`, read | `m_spectrumA[0]` |
| 2 | `m_spectrumA[1]`, written | `m_spectrumA[0]`, written | `m_spectrumB[0]` |
| 3 | `m_spectrumB[1]`, written | `m_spectrumB[0]`, written | `m_displacement` |
| 4 | | | `m_normals` |
| 5 | | | `m_preview` |

Each shader declares only the bindings it uses (Chapter 20 section 4), so one
ocean set serves the test wave, the spectrum, animate, assemble, and preview
passes alike.

```cpp
InitializationResult OceanDemo::CreateDescriptors()
{
    // The ocean's set holds six storage images, and Vulkan guarantees only four
    // per shader stage. Every desktop GPU has thousands; ask rather than assume.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &properties);
    if (properties.limits.maxPerStageDescriptorStorageImages < 6)
    {
        return InitializationResult::failure("The ocean needs six storage images per shader stage.");
    }
```

Then come the two set layouts (every binding a storage image for compute; the
FFT's are the first four of the ocean's six), a pool for three sets and
4 + 4 + 6 storage images, and the three sets, which is Chapter 20 section 4's
pattern; Appendix B has the function whole. It ends by writing the table above
into the sets, fourteen descriptors through one small lambda:

```cpp
    // Every descriptor is a storage image in GENERAL; only the set, the binding,
    // and the image differ. The infos live until vkUpdateDescriptorSets returns.
    std::array<VkDescriptorImageInfo, 14> infos{};
    std::array<VkWriteDescriptorSet, 14>  writes{};
    uint32_t count = 0;
    const auto add = [&](VkDescriptorSet set, uint32_t binding, const OceanImage& image) {
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

    // FFT set s reads copy s of A and B and writes copy 1 - s: the ping-pong is
    // two sets built once, never an update per dispatch (Chapter 20 section 4).
    for (uint32_t s = 0; s < 2; ++s)
    {
        add(m_fftSets[s], 0, m_spectrumA[s]);
        add(m_fftSets[s], 1, m_spectrumB[s]);
        add(m_fftSets[s], 2, m_spectrumA[1 - s]);
        add(m_fftSets[s], 3, m_spectrumB[1 - s]);
    }
    add(m_oceanSet, 0, m_h0);
    add(m_oceanSet, 1, m_spectrumA[0]);   // the FFT's input, and its output (section 5)
    add(m_oceanSet, 2, m_spectrumB[0]);
    add(m_oceanSet, 3, m_displacement);
    add(m_oceanSet, 4, m_normals);
    add(m_oceanSet, 5, m_preview);
    vkUpdateDescriptorSets(m_context.vulkan.device, count, writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

Two things in it are worth a second look.

- **The limit check at the top.** A pipeline layout may give a shader stage at
  most `maxPerStageDescriptorStorageImages` storage images, counted over every
  set in the layout, and Vulkan guarantees only 4, as it does storage buffers
  (Chapter 21 section 1). The FFT's set is exactly 4; the ocean's is 6. Desktop
  GPUs report far more than six, but it is a requirement the demo adds, so it
  is checked and reported, not assumed.
- **Why the ocean's set names only copy `[0]` of A and B.** The animate pass
  and the test wave write copy 0, the FFT ping-pongs, and after an even number
  of stages its result is back in copy 0 (section 5). Everything outside the
  FFT only ever sees copy 0.

`Setup` gains the first two steps, after `m_context = context;`:

```cpp
    if (auto result = CreateImages(); !result)           { return result; }   // section 4
    if (auto result = CreateDescriptors(); !result)      { return result; }   // section 4
```

---

## 5. The FFT pass

### The twin structs

**This is `Shaders/Ocean/OceanTypes.h`**, in Chapter 20's `<Name>Types.h`
shape: GLSL includes it as `"OceanTypes.h"`, C++ as `"Ocean/OceanTypes.h"`.
It is written whole here, so that it changes once. `FftParameters` is this
section's; `OceanParameters` is everything else's, and each later section says
which of its fields it reads.

```c
/* Shaders/Ocean/OceanTypes.h - Chapter 29's C++/GLSL twins. GLSL includes it as
   "OceanTypes.h", C++ as "Ocean/OceanTypes.h". */
#ifndef PF_OCEAN_TYPES_H
#define PF_OCEAN_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 and uint aliases, on the C++ side */

/* Every compute pass is 8 x 8 (Chapter 20 section 3): local_size in GLSL, the
   groupCount divisor in C++. One number for both languages. */
#define OCEAN_GROUP_SIZE 8

/* The surface: quads along each side of one patch (section 10). */
#define OCEAN_GRID_CELLS 128

/* OceanParameters::view - what the panel's preview shows. */
#define OCEAN_VIEW_FFT_REAL      0u   /* section 6: the FFT's first output, real part */
#define OCEAN_VIEW_FFT_IMAGINARY 1u   /* ...and its imaginary part */
#define OCEAN_VIEW_SPECTRUM      2u   /* section 7: |h0|, the starting waves */
#define OCEAN_VIEW_HEIGHT        3u   /* section 9: the height field */
#define OCEAN_VIEW_NORMAL        4u   /* section 9: the normal, as a color */
#define OCEAN_VIEW_JACOBIAN      5u   /* section 9: the Jacobian; white where it is foam */

/* OceanParameters::flags */
#define OCEAN_FLAG_TEST_MIRROR 1u     /* section 6: the test wave gets its mirror at -k */
#define OCEAN_FLAG_NO_SIGN_FIX 2u     /* section 6: skip the (-1)^(x+y), to see what it fixes */

#ifdef __cplusplus
    namespace pf::demos::ocean {
    using shared::vec4;
    using shared::uint;
#endif

/* The FFT pass's push constants (section 5). */
struct FftParameters
{
    uint stage;               /* 0 .. log2(N) - 1 */
    uint direction;           /* 0: along rows (x), 1: along columns (y) */
};

/* Everything else's push constants: every ocean compute pass and the surface's
   two shaders. Each reads the fields it needs. Exactly the 128 bytes Vulkan
   guarantees for push constants. */
struct OceanParameters
{
    vec4  wind;               /*   0  xy: unit direction the wind blows toward, in x and z; z: speed, m/s; w unused */
    vec4  sun;                /*  16  xyz: unit direction sunlight travels; w: its intensity */
    vec4  waterColor;         /*  32  rgb linear: the light the water sends back up; a unused */
    vec4  skyColor;           /*  48  rgb linear: the sky at the horizon; a unused */
    float amplitude;          /*  64  Phillips A, a plain number (section 7) */
    float patchSize;          /*  68  L: one patch's side, metres */
    float suppression;        /*  72  l, metres: waves shorter than this fade out */
    float choppiness;         /*  76  lambda: how far the surface moves sideways */
    float time;               /*  80  seconds: scaled, and wrapped at loopPeriod */
    float loopPeriod;         /*  84  seconds; 0 = never repeats */
    float foamThreshold;      /*  88  a Jacobian below this is foam */
    float hazeDistance;       /*  92  metres: how far you see before the sky's color takes over */
    float previewGain;        /*  96  brightness of the panel's preview */
    uint  seed;               /* 100  which random ocean */
    uint  view;               /* 104  OCEAN_VIEW_* */
    uint  flags;              /* 108  OCEAN_FLAG_* */
    int   testWaveX;          /* 112  section 6's test wave: waves across the patch in x */
    int   testWaveZ;          /* 116  ...and in z */
    uint  tiles;              /* 120  patches drawn along each side, an odd number */
    uint  padding0;           /* 124 */
};

#ifdef __cplusplus
    static_assert(sizeof(FftParameters) == 8, "FftParameters layout drifted.");
    static_assert(sizeof(OceanParameters) == 128, "OceanParameters layout drifted.");
    static_assert(offsetof(OceanParameters, amplitude) == 64, "OceanParameters alignment drifted.");
    static_assert(offsetof(OceanParameters, testWaveX) == 112, "OceanParameters alignment drifted.");
    }
#endif

#endif
```

`OceanParameters` is the push-constant block of every pass but the FFT, and of
both of the surface's shaders. It is exactly 128 bytes, the most Vulkan
guarantees for push constants (Chapter 08 section 5): four `vec4`s, then
sixteen 4-byte scalars, in an order that needs no padding in C++ or in GLSL.
The macros are shared the same way as the structs: `OCEAN_GROUP_SIZE` is both
the shaders' `local_size` and C++'s divisor for `groupCount`, so the two can
not disagree.

### Complex numbers in GLSL

**This is the first half of `Shaders/Ocean/Ocean.glsl`**, an include every
ocean shader shares. It has no stage in its name, so Chapter 06's glob compiles
it only through the shaders that include it:

```glsl
// Shaders/Ocean/Ocean.glsl - complex numbers and spectrum texels, for the ocean's shaders.
// An include, not a stage: no .comp in its name, so Chapter 06's glob skips it.
#ifndef PF_OCEAN_GLSL
#define PF_OCEAN_GLSL

const float PI = 3.14159265358979;

// A complex number is a vec2: x the real part, y the imaginary part.
// (a.x + i a.y)(b.x + i b.y), with i * i = -1.
vec2 complexMultiply(vec2 a, vec2 b)
{
    return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x);
}

// e^(i angle) = cos(angle) + i sin(angle): the unit complex number at that angle.
vec2 complexExp(float angle)
{
    return vec2(cos(angle), sin(angle));
}

// The spectrum is centred: texel (N/2, N/2) holds wave number 0. The texel
// holding the mirror wave, -k, is the texel reflected through it (section 2).
ivec2 mirrorTexel(ivec2 texel, int n)
{
    return (ivec2(n) - texel) % n;
}

// (-1)^(x + y): what turns a plain inverse FFT of a centred spectrum into the
// right answer (section 6). OCEAN_FLAG_NO_SIGN_FIX turns it off, to show why.
float centringSign(ivec2 texel, uint flags)
{
    if ((flags & OCEAN_FLAG_NO_SIGN_FIX) != 0u) { return 1.0; }
    return ((texel.x + texel.y) & 1) == 0 ? 1.0 : -1.0;
}

#endif
```

`complexMultiply` is section 1's formula. `complexExp` is the unit arrow at an
angle. `mirrorTexel` is section 2's `−k`, and `centringSign` is section 6's.
Section 7 adds three more functions before the `#endif`.

### One stage

**This is `Shaders/Ocean/FftStage.comp.glsl`.** One invocation per output
texel, one dispatch per stage. It is section 2's table in code:

```glsl
// Shaders/Ocean/FftStage.comp.glsl - one stage of the inverse FFT, along rows or
// columns, on both images at once (section 5).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

// Two complex numbers per texel (.xy and .zw), in two images: four transforms.
layout(set = 0, binding = 0, rgba32f) uniform readonly  image2D inputA;
layout(set = 0, binding = 1, rgba32f) uniform readonly  image2D inputB;
layout(set = 0, binding = 2, rgba32f) uniform writeonly image2D outputA;
layout(set = 0, binding = 3, rgba32f) uniform writeonly image2D outputB;

layout(push_constant) uniform PushConstants
{
    FftParameters fft;
};

// The lowest `bits` bits of value, in reverse order: 3 bits of 001 is 100.
int reverseBits(int value, int bits)
{
    return int(bitfieldReverse(uint(value)) >> uint(32 - bits));
}

// w times each of the two complex numbers in a texel.
vec4 twiddleBoth(vec2 w, vec4 pair)
{
    return vec4(complexMultiply(w, pair.xy), complexMultiply(w, pair.zw));
}

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(inputA).x;   // N: the images are square
    if (texel.x >= n || texel.y >= n) { return; }

    // Rows first, then columns: i is this output's place along the line being transformed.
    int i = (fft.direction == 0u) ? texel.x : texel.y;

    // The butterfly (section 2): groups of 2 * span entries, each output is
    // top + w * bottom, where top and bottom are span apart.
    int span  = 1 << fft.stage;
    int group = 2 * span;
    int j     = i % group;                  // place inside the group
    int top   = (j < span) ? i : i - span;
    int bottom = top + span;
    if (fft.stage == 0u)
    {
        // Stage 0 reads in bit-reversed order, so the last stage writes in natural order.
        int bits = findMSB(n);              // log2(N)
        top    = reverseBits(top, bits);
        bottom = reverseBits(bottom, bits);
    }

    // The twiddle: e^(+2 pi i j / group). The plus sign makes it the inverse transform.
    vec2 w = complexExp(2.0 * PI * float(j) / float(group));

    ivec2 topTexel    = (fft.direction == 0u) ? ivec2(top, texel.y)    : ivec2(texel.x, top);
    ivec2 bottomTexel = (fft.direction == 0u) ? ivec2(bottom, texel.y) : ivec2(texel.x, bottom);

    imageStore(outputA, texel, imageLoad(inputA, topTexel) + twiddleBoth(w, imageLoad(inputA, bottomTexel)));
    imageStore(outputB, texel, imageLoad(inputB, topTexel) + twiddleBoth(w, imageLoad(inputB, bottomTexel)));
}
```

Reading it against section 2:

- **Rows, then columns.** `direction` 0 transforms along x, every row at once:
  invocation `(x, y)` is position `x` of row `y`'s transform. Direction 1 does
  the same down the columns. Rows first and columns second, eight stages each
  at `N = 256`, is the two-dimensional transform.
- **The butterfly's arithmetic.** `j` is the output's place in its group, and
  its pair is `top` and `bottom`, `span` apart. Whether the output is in the
  top or the bottom half of its group, it is `top + w · bottom` with
  `w = e^(2πi j / group)`: section 2's observation, which saves a branch.
- **Bit reversal, only in stage 0.** `findMSB(N)` is `log2 N` for a power of
  two, and `bitfieldReverse` reverses all 32 bits, so shifting right by
  `32 − log2 N` leaves the reversed low bits. Reading stage 0's inputs in that
  order is what makes the last stage's outputs come out in natural order.
- **The sign of the twiddle** is `+`, the inverse transform's.
- **Four transforms at once.** Each texel holds two complex numbers, `.xy` and
  `.zw`, and there are two images, so each invocation does four butterflies
  with the same twiddle. `twiddleBoth` multiplies both halves of a texel.
- **The bounds guard** returns early, which is safe: the shader has no
  `barrier()` (Chapter 20 section 6). At `N = 256` and 8 x 8 groups there is
  nothing to guard, but the dispatch size comes from `groupCount`, which rounds
  up, and the check costs nothing.

### The pipelines

**This is `CreateComputePipelines`, as Part 1 has it.** It makes two pipeline
layouts, because the FFT binds a different set and pushes a different block
from every other pass. The FFT's has the FFT's set and an 8-byte
`FftParameters` range; the ocean's has the ocean's set and the 128-byte
`OceanParameters` range, both for the compute stage. That is Chapter 20 section
2's pattern twice, and Appendix B has it. Then comes the part that grows, a
table of passes with one row per section, and a loop that makes each pipeline:

```cpp
    const struct
    {
        VkPipeline*      pipeline;
        const char*      shader;
        VkPipelineLayout layout;
    } passes[] = {
        { &m_fftPipeline,      "Ocean/FftStage.comp.spv",      m_fftLayout },     // section 5
        { &m_testWavePipeline, "Ocean/FftTestWave.comp.spv",   m_oceanLayout },   // section 6
        { &m_previewPipeline,  "Ocean/OceanPreview.comp.spv",  m_oceanLayout },   // section 6
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_context.vulkan.device, m_context.pipelineCache,
                                               pass.shader, pass.layout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating an ocean compute pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

The two section 6 rows are there because section 6 writes their shaders next;
with them in the table, `Setup` fails on a missing `.spv` until it does. Add
the step to `Setup`, after the descriptors:

```cpp
    if (auto result = CreateComputePipelines(); !result) { return result; }   // sections 5-9
```

### The loop, and the barrier in it

**This is `RecordFft`.** Sixteen dispatches at `N = 256`: eight stages along
the rows, eight down the columns, each reading the copy the last one wrote:

```cpp
void OceanDemo::RecordFft(VkCommandBuffer commandBuffer)
{
    const uint32_t groups = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fftPipeline);

    uint32_t source = 0;   // which copy the next stage reads: m_fftSets[source]
    for (uint32_t direction = 0; direction < 2; ++direction)   // rows, then columns
    {
        for (uint32_t stage = 0; stage < FFT_STAGES; ++stage)
        {
            const FftParameters fft{ .stage = stage, .direction = direction };
            vkCmdPushConstants(commandBuffer, m_fftLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(fft), &fft);
            vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fftLayout,
                                    0, 1, &m_fftSets[source], 0, nullptr);
            vkCmdDispatch(commandBuffer, groups, groups, 1);

            // The next stage reads what this one wrote, and overwrites what it read.
            computeToComputeBarrier(commandBuffer);
            source = 1 - source;
        }
    }
    // 2 x log2(N) stages is an even number: the result is back in copy 0.
}
```

The barrier after every dispatch is Chapter 20 section 5's
`computeToComputeBarrier`, and its reasons are that section's, with the
ping-pong making both of them bite:

- **Q1 (execution):** stage `s + 1` reads every texel stage `s` wrote, in the
  same `COMPUTE_SHADER` stage, so it must not start until stage `s` finishes.
- **Q2 (memory):** stage `s`'s `SHADER_STORAGE_WRITE`s must be visible to
  stage `s + 1`'s `SHADER_STORAGE_READ`s — and to stage `s + 2`'s
  `SHADER_STORAGE_WRITE`s, because stage `s + 2` writes the very copy stage `s`
  wrote. That is why the destination access is read *and* write. Sync
  validation checks the read half: delete the barrier and it reports
  `SYNC-HAZARD-READ-AFTER-WRITE` (the exit check has you see it). It does not
  check the write half here. Weaken the destination to `READ` alone and it
  stays quiet, because stage `s + 1`'s read sits between the two writes and the
  layer takes the read's ordering as enough. The spec does not, so that half is
  argued from this question, not from a quiet layer.
- **Q3 (layout):** none; every image stays in `GENERAL`, so it is a memory
  barrier, not an image barrier.

Chapter 04's appendix has this as "Storage image ping-pong between dispatches".
Sixteen barriers is not free, and section 12 says how a faster FFT drops most
of them. This one is the one to write first, because **every intermediate stage
is a real image you could look at**, and an FFT that is wrong is far easier to
find that way.

After `2 · log2 N` stages — always an even number — the result is back in copy
0, where the ocean's set expects it. The FFT's descriptor sets were written once
in `CreateDescriptors`: nothing is updated per dispatch, only which of the two
sets is bound.

---

## 6. Seeing it: a test wave, the sign, and a preview

An FFT that compiles and runs proves nothing. Before any ocean, feed it the
simplest spectrum there is — one wave — and look at what comes out.

### One wave in

**This is `Shaders/Ocean/FftTestWave.comp.glsl`.** It writes a spectrum of
zeros with a 1 in one texel, and, if asked, a 1 in its mirror texel too:

```glsl
// Shaders/Ocean/FftTestWave.comp.glsl - Part 1's input: one wave, and if asked
// its mirror, in an otherwise empty spectrum (section 6).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 1, rgba32f) uniform writeonly image2D spectrumA;
layout(set = 0, binding = 2, rgba32f) uniform writeonly image2D spectrumB;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(spectrumA).x;
    if (texel.x >= n || texel.y >= n) { return; }

    // Wave number (x, z) lives at texel (N/2 + x, N/2 + z): the spectrum is centred.
    ivec2 wave = ivec2(parameters.testWaveX, parameters.testWaveZ) + n / 2;

    // Amplitude 1, phase 0: the complex number 1 + 0i. Its mirror gets the
    // conjugate of that, which is 1 again.
    vec2 value = vec2(0.0);
    if (texel == wave) { value += vec2(1.0, 0.0); }
    if ((parameters.flags & OCEAN_FLAG_TEST_MIRROR) != 0u && texel == mirrorTexel(wave, n))
    {
        value += vec2(1.0, 0.0);
    }

    // Only A's first complex number carries the wave; the other three transforms get zeros.
    imageStore(spectrumA, texel, vec4(value, 0.0, 0.0));
    imageStore(spectrumB, texel, vec4(0.0));
}
```

The test wave is given in cycles across the patch, `(x, z)`, so it lives in
texel `(N/2 + x, N/2 + z)` of the centred spectrum, and its mirror in
`mirrorTexel` of that: section 2's `−k`. The mirror's amplitude is the
conjugate of `1 + 0i`, which is `1 + 0i` again. With the mirror, the input is
section 2's second example; without it, its first.

### The sign the centring costs

The FFT of section 2 assumes texel `n` holds wave `n`. The images hold wave
`n − N/2` there. Feeding the FFT a centred spectrum therefore transforms every
wave `N/2` too high, and a wave `N/2` higher turns an extra half turn per
sample: at sample `x` it has turned an extra `π x`, which is a factor of
`e^(iπx) = (−1)^x`. In two dimensions, `(−1)^(x + y)`. So **multiply every
output texel by `(−1)^(x + y)`** and the centring is undone.

With `N = 4`: wave 1 is in texel 3, and the plain transform of `[0, 0, 0, 1]`
is `[1, −i, −1, i]`. Multiply by `(−1)^x = [1, −1, 1, −1]` and you get
`[1, i, −1, −i]`, which is wave 1. `centringSign` is that factor, and every
shader that reads the FFT's output applies it. Forget it and every other texel
is upside down — a fine checkerboard laid over the result, which this section's
checkpoint shows you on purpose.

### A preview

To see the result you need a picture of an image, in a panel. **This is
`Shaders/Ocean/OceanPreview.comp.glsl`, as Part 1 has it**: one invocation per
texel, turning a number into a color.

```glsl
// Shaders/Ocean/OceanPreview.comp.glsl - turns one of the ocean's images into
// colors for the panel's preview (section 6; Part 2 adds views in sections 7 and 9).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 0, rg32f)   uniform readonly  image2D h0;
layout(set = 0, binding = 1, rgba32f) uniform readonly  image2D spectrumA;
layout(set = 0, binding = 3, rgba16f) uniform readonly  image2D displacementMap;
layout(set = 0, binding = 4, rgba16f) uniform readonly  image2D normalMap;
layout(set = 0, binding = 5, rgba8)   uniform writeonly image2D preview;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

// Display values, not linear ones: ImGui shows the preview's bytes as they are
// (Chapter 08 section 4). Above zero is orange, below zero blue, zero black.
vec3 signedColor(float value)
{
    float t = clamp(value * parameters.previewGain, -1.0, 1.0);
    return t >= 0.0 ? t * vec3(1.0, 0.65, 0.2) : -t * vec3(0.25, 0.55, 1.0);
}

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    if (any(greaterThanEqual(texel, imageSize(preview)))) { return; }

    vec3 color = vec3(0.0);
    switch (parameters.view)
    {
    case OCEAN_VIEW_FFT_REAL:   // amplitude 2 is full brightness
        color = signedColor(0.5 * centringSign(texel, parameters.flags) * imageLoad(spectrumA, texel).x);
        break;
    case OCEAN_VIEW_FFT_IMAGINARY:
        color = signedColor(0.5 * centringSign(texel, parameters.flags) * imageLoad(spectrumA, texel).y);
        break;
    }
    imageStore(preview, texel, vec4(color, 1.0));
}
```

It declares the bindings for `h0` and the two maps although Part 1 does not
read them yet: Part 2's views do, and declaring a binding a shader does not use
costs nothing. Signed values get a color for each sign and black for zero,
because "zero" is what you will be looking for: the imaginary part that should
vanish, the centre texel that should be empty.

`PackParameters` turns the settings into the block the shaders read. **This is
`PackParameters`, as Part 1 has it**; section 7 completes it, and every field
it does not name is zero until then:

```cpp
OceanParameters OceanDemo::PackParameters() const
{
    uint32_t flags = 0;
    if (m_settings.testMirror)  { flags |= OCEAN_FLAG_TEST_MIRROR; }
    if (m_settings.skipSignFix) { flags |= OCEAN_FLAG_NO_SIGN_FIX; }

    return OceanParameters{
        .previewGain   = m_settings.previewGain,
        .view          = static_cast<uint32_t>(m_settings.view),
        .flags         = flags,
        .testWaveX     = m_settings.testWaveX,
        .testWaveZ     = m_settings.testWaveZ,
    };
}
```

### Showing an image in ImGui

`ImGui_ImplVulkan_AddTexture` (Chapter 07 section 2) makes a descriptor set in
ImGui's own pool that points at your image view, and returns it; passed to
`ImGui::Image` as an `ImTextureID`, it draws the image in a window. The layout
you give it is the one the image will be in *when ImGui draws*, so here it is
`SHADER_READ_ONLY_OPTIMAL`, not the `GENERAL` the preview pass writes in. Add
this to `Setup`, last:

```cpp
    // ImGui draws the preview through a descriptor set of its own (Chapter 07
    // section 2), made for the layout the image will be in when ImGui draws it.
    m_previewTexture = ImGui_ImplVulkan_AddTexture(m_preview.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
```

ImGui keeps that set until it is told otherwise, so `Teardown` gives it back
first (below).

**This is `drawPreviewPanel`**, a `static` function in the namespace like every
demo's panel, and the list of views it offers. The preview is the demo's second
window, at the right under the picker; it is taller than the room left below it
at 720 pixels, so it takes Chapter 09 section 6's height limit on its own:

```cpp
// Section 6, grown in sections 7 and 9: the preview's choices, in OCEAN_VIEW_* order.
static const char* const VIEW_NAMES[] = {
    "FFT output, real part",
    "FFT output, imaginary part",
};
```

```cpp
// Section 6. The preview, and Part 1's test wave. ImGui shows the image through
// the handle ImGui_ImplVulkan_AddTexture returned.
static void drawPreviewPanel(OceanSettings& settings, ImTextureID preview)
{
    ImGui::SetNextWindowPos(ImVec2(990.0f, 280.0f), ImGuiCond_FirstUseEver);   // below the demo picker
    debug_panels::stopNextWindowAtScreenBottom();                              // taller than the room left
    if (ImGui::Begin("Ocean preview"))
    {
        ImGui::Combo("Show", &settings.view, VIEW_NAMES, IM_ARRAYSIZE(VIEW_NAMES));
        ImGui::SliderFloat("Brightness", &settings.previewGain, 0.01f, 100.0f, "%.2f", ImGuiSliderFlags_Logarithmic);
        ImGui::Image(preview, ImVec2(256.0f, 256.0f));

        ImGui::SeparatorText("Test wave");
        ImGui::Checkbox("Instead of the ocean", &settings.testWave);   // Part 1 always uses the test wave
        ImGui::SliderInt("Waves in x", &settings.testWaveX, -16, 16);
        ImGui::SliderInt("Waves in z", &settings.testWaveZ, -16, 16);
        ImGui::Checkbox("Add its mirror at -k", &settings.testMirror);
        ImGui::Checkbox("Skip the sign fix", &settings.skipSignFix);
    }
    ImGui::End();
}
```

"Instead of the ocean" does nothing yet: until Part 2 there is no ocean, and
`Record` always uses the test wave. Call it from `Update`, before the clock:

```cpp
void OceanDemo::Update(const FrameInput& input)
{
    drawPreviewPanel(m_settings, reinterpret_cast<ImTextureID>(m_previewTexture));
    m_time += input.deltaSeconds * m_settings.timeScale;
}
```

The cast is needed because a `VkDescriptorSet` is a pointer type and
`ImTextureID` is a 64-bit integer.

### The preview's barriers

The preview image is written by a compute shader and read by ImGui's fragment
shader later in the same frame, then written again next frame. That is Chapter
20 section 10's situation, a compute result sampled by graphics, with both
directions:

- **Into ImGui**, after the preview pass:
  - **Q1:** the preview's `COMPUTE_SHADER` work before ImGui's
    `FRAGMENT_SHADER`.
  - **Q2:** `SHADER_STORAGE_WRITE` made visible to `SHADER_SAMPLED_READ`.
  - **Q3:** `GENERAL` to `SHADER_READ_ONLY_OPTIMAL`, the layout ImGui's
    descriptor names.
- **Back to compute**, at the top of the next frame's `Record`:
  - **Q1:** last frame's ImGui `FRAGMENT_SHADER` reads before this frame's
    `COMPUTE_SHADER` writes.
  - **Q2:** a read leaves nothing to flush: source access `NONE`.
  - **Q3:** `UNDEFINED` to `GENERAL`. `UNDEFINED` lets the driver drop the old
    contents, which is right because the preview pass writes every texel.

Both are rows of Chapter 04's appendix: "Compute result sampled by a later
shader", and "Sampled result handed back to compute, next frame".

### The frame, at the end of Part 1

**This is `Record`, as Part 1 leaves it.** Appendix A shows the final one; the
numbers in its comments are the same, and Part 2 fills in the missing steps:

```cpp
void OceanDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const OceanParameters parameters    = PackParameters();
    const uint32_t        groups        = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);

    // 1. Return trips. Last frame's dispatches finish before this frame's write
    //    over what they read and wrote; the preview comes back from ImGui.
    computeToComputeBarrier(commandBuffer);
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // Every pass but the FFT binds the ocean's set and reads OceanParameters.
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_oceanLayout,
                            0, 1, &m_oceanSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_oceanLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);

    // 3. The FFT's input: the test wave.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_testWavePipeline);
    vkCmdDispatch(commandBuffer, groups, groups, 1);
    computeToComputeBarrier(commandBuffer);

    // 4. Section 5: the inverse FFT.
    RecordFft(commandBuffer);

    // The FFT's layout is not the ocean's, so its binds displaced the ocean's set
    // and push constants: bind them again.
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_oceanLayout,
                            0, 1, &m_oceanSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_oceanLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);

    // 6. The panel's picture.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_previewPipeline);
    vkCmdDispatch(commandBuffer, groups, groups, 1);

    // 7. Hand the preview to ImGui's fragment shader.
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    const VkClearColorValue sky{ { 0.41f, 0.60f, 0.80f, 1.0f } };   // linear
    beginScenePass(commandBuffer, frame.targets, &sky);
    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

Three things in it are new.

- **The return trip comes first.** The `computeToComputeBarrier` at the top
  orders this frame's writes after last frame's reads and writes of the same
  images — the test wave overwrites copy 0, which last frame's preview read.
  Chapter 20 section 5's "return trip".
- **Binding twice.** The FFT's pipeline layout differs from the ocean's in both
  its set layout and its push-constant range. Sets stay bound only across
  compatible layouts (Chapter 08 section 6), and push constants only across
  layouts with the same push-constant ranges; binding the FFT's set at set 0
  displaced the ocean's, and pushing the FFT's 8 bytes left the ocean's 128
  undefined. So after `RecordFft`, the ocean's set and constants are bound
  again before the next pass.
- **All of the compute runs before `beginScenePass`.** A dispatch inside a
  rendering scope is an error (Chapter 20 section 1).

The pipelines and the descriptor sets stay bound across `vkCmdBindPipeline`
calls as long as the layouts are the same, which is why steps 3 and 6 bind only
a pipeline.

### Teardown, whole

**This is `Teardown`.** Chapter 09 waited for the device before calling it. It
gives ImGui its descriptor set back first, then undoes `Setup` in reverse, and
resets every handle so that the next `Setup` starts clean; the settings and the
camera are kept, as Chapter 09 asks:

```cpp
void OceanDemo::Teardown()
{
    // Chapter 09 waited for the device. Reverse order of Setup; null handles are
    // no-ops, so a partial Setup is safe. The CPU state is kept.
    if (m_previewTexture != VK_NULL_HANDLE)
    {
        ImGui_ImplVulkan_RemoveTexture(m_previewTexture);
        m_previewTexture = VK_NULL_HANDLE;
    }

    const VkDevice device = m_context.vulkan.device;
    VkPipeline* pipelines[] = { &m_surfacePipeline, &m_assemblePipeline, &m_animatePipeline, &m_spectrumPipeline,
                                &m_previewPipeline, &m_testWavePipeline, &m_fftPipeline };
    for (VkPipeline* pipeline : pipelines)
    {
        vkDestroyPipeline(device, *pipeline, nullptr);
        *pipeline = VK_NULL_HANDLE;
    }
    vkDestroyPipelineLayout(device, m_surfaceLayout, nullptr);
    vkDestroyDescriptorPool(device, m_surfacePool, nullptr);   // frees the surface's set
    vkDestroyDescriptorSetLayout(device, m_surfaceSetLayout, nullptr);
    vkDestroySampler(device, m_sampler, nullptr);
    vkDestroyPipelineLayout(device, m_oceanLayout, nullptr);
    vkDestroyPipelineLayout(device, m_fftLayout, nullptr);
    vkDestroyDescriptorPool(device, m_descriptorPool, nullptr);   // frees the three compute sets
    vkDestroyDescriptorSetLayout(device, m_oceanSetLayout, nullptr);
    vkDestroyDescriptorSetLayout(device, m_fftSetLayout, nullptr);

    OceanImage* images[] = { &m_preview, &m_normals, &m_displacement, &m_spectrumB[1], &m_spectrumB[0],
                             &m_spectrumA[1], &m_spectrumA[0], &m_h0 };
    for (OceanImage* image : images)
    {
        destroyOceanImage(m_context.vulkan, *image);
    }
    m_sceneRenderer.Shutdown();

    m_surfaceLayout  = m_oceanLayout = m_fftLayout = VK_NULL_HANDLE;
    m_surfacePool    = m_descriptorPool = VK_NULL_HANDLE;
    m_surfaceSetLayout = m_oceanSetLayout = m_fftSetLayout = VK_NULL_HANDLE;
    m_sampler        = VK_NULL_HANDLE;
    m_surfaceSet     = m_oceanSet = VK_NULL_HANDLE;
    m_fftSets        = {};
}
```

It already names Part 2's objects — the sampler, the surface's set and
pipeline, the scene renderer. Each is a null handle until Part 2 creates it,
and every Vulkan destroy call, `vmaDestroyImage`, and `SceneRenderer::Shutdown`
do nothing with a null, so this is correct at every stage of the chapter, and
after a `Setup` that failed halfway. Switching to another demo and back, then
quitting, is a free leak check: VMA asserts at shutdown if an allocation is
left.

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Ocean`. The sky is
still empty; the "Ocean preview" window is the point. Every picture below is
section 2's arithmetic, so a wrong one names its own bug:

- **"FFT output, real part", waves in x = 3, z = 0:** three orange and three
  blue vertical bands across the square, orange at the left edge. A cosine,
  three cycles across.
- **"FFT output, imaginary part":** the same bands moved right by a quarter of
  a wave (half a band), black at the left edge: the sine. Together they are section 2's
  `[1, i, −1, −i]`, stretched to 256 samples.
- **Tick "Add its mirror at −k":** the imaginary part goes black everywhere,
  and the real bands become twice as bright. That is `[2, 0, −2, 0]`: the
  mirror wave cancelling the imaginary part, which is what the ocean's heights
  will depend on.
- **Waves in z instead:** horizontal bands. Both at once, say `(3, 2)`:
  diagonal stripes, three cycles across and two down, running at right angles
  to the wave vector.
- **Tick "Skip the sign fix":** the bands break up into a fine checkerboard of
  orange and blue texels. That is what every result of this chapter looks like
  without `centringSign`.

If the bands are in the wrong place, or the mirror does not cancel, the FFT is
wrong; nothing in Part 2 can be right until these are.

---

# Part 2 — The ocean's maps (sections 7-9)

Part 1's FFT turns any spectrum into heights. Part 2 makes the spectrum a sea:
which waves, how big (section 7), how they move (section 8), and what the
surface needs besides heights (section 9). Everything it makes is an image, and
the preview shows each one before Part 3 draws any water.

## 7. The starting waves

> **Jump:** nobody designs an ocean wave by wave. The spectrum here is
> *statistical*: for each wave vector it says how big waves of that length and
> direction are **on average** in a sea under a given wind, and each actual
> amplitude is a random number drawn around that average. Keep in mind that the
> spectrum fixes the sea's character — how rough, which way, how long the
> waves — and the seed only picks one sea out of the many with that character.

### What a sea's spectrum looks like

Oceanographers measured how a sea's energy is shared among wave lengths and
directions. Tessendorf's notes use the **Phillips spectrum**, a simple formula
with the right shape:

```text
P(k) = A · exp(−1 / (|k| L)²) / |k|⁴ · (k̂ · ŵ)²          L = V² / g
```

One factor at a time:

- **`L = V² / g`**, with `V` the wind speed and `g = 9.81 m/s²`, is the scale
  of the largest waves that wind can raise: 14.7 m at 12 m/s, 41 m at 20 m/s.
- **`exp(−1 / (|k| L)²)`** is nearly 0 for waves much longer than `L` (small
  `|k|`) and nearly 1 for shorter ones: the wind cannot build waves far longer
  than its own scale.
- **`1 / |k|⁴`**: shorter waves carry far less energy. Halve the wavelength and
  the energy drops sixteen-fold.
- **`(k̂ · ŵ)²`**, with `k̂` the wave's direction and `ŵ` the wind's, is the
  squared cosine of the angle between them: waves running along the wind get
  everything, waves running across it nothing.
- **`A`** scales the whole thing. More below.

The first two factors pull in opposite directions, so the energy rises and then
falls, with its peak at a wavelength of about `8.9 L` — 130 m for a 12 m/s
wind. Along the wind, relative to that peak:

```text
wavelength   P(k) / peak
   1000 m    0.000
    300 m    0.005
    200 m    0.371  ###############
    130 m    1.000  ########################################
    100 m    0.788  ################################
     70 m    0.345  ##############
     50 m    0.119  #####
     30 m    0.019  #
     10 m    0.000
```

Three adjustments make it work in an image:

- **Suppress the tiniest waves.** Multiply by `exp(−|k|² l²)`, with `l` a
  length of half a metre or so: waves much shorter than `l` fade out. Without it
  the shortest waves the grid can hold — about two texels, 2.3 m in a 300 m
  patch at `N = 256` — come out as noise.
- **Damp the waves running against the wind.** `(k̂ · ŵ)²` is the same for a
  wave and its opposite, which would send as much sea upwind as downwind. This
  chapter keeps 5% for the upwind half, and then the sea visibly travels with
  the wind.
- **`k = 0` gets nothing.** Wave vector 0 is no wave at all, and `1 / |k|⁴` is
  infinite there. Computed, it is a NaN, and because every output of an FFT
  depends on every input, one NaN in the spectrum is a NaN at every texel of
  the result: the ocean comes out black. **This is the most common way an FFT
  ocean fails.** Return 0 for `k = 0` before anything divides by `|k|`.

**Why `A` is a plain number.** `P` is a density: energy per unit of
wave-vector area. One texel of the spectrum covers a square `Δk` on a side,
with `Δk = 2π / L_patch`: a 300 m patch has `Δk = 2π / 300 ≈ 0.021` rad/m, so
each texel stands for a square 0.021 rad/m on a side. The energy one texel
stands for is therefore `P(k) · Δk²`.
Multiplying by `Δk²` does two things. The heights stop depending on the patch
size, which is now only how often the pattern repeats. And `A` loses its units —
`P` has metres to the fourth, `Δk²` one over metres squared, and the result is
a height squared — so `A` is just a number. With `A = 0.002` and a 12 m/s wind
the heights spread about 0.8 m either side of the mean, and the larger waves
are about 3 m from trough to crest — the size the Beaufort scale gives for a
sea that a wind of that speed has fully raised (force 6, "large waves", about
3 m). Stronger winds want a larger patch: the peak wavelength, `8.9 L`, grows
with `V²` too, and a wave longer than the patch cannot exist in it.

### Random numbers with a bell curve

In a real sea, two waves of the same length and direction are not the same
size. Measured at one spot over time, the sea's height follows the **normal**,
or **Gaussian**, distribution: values cluster around the average, and the
further from it, the rarer. About 68% fall within one *standard deviation* of
the average, 95% within two, and almost none beyond three:

```text
 how often
     |                  ***
     |              ****   ****
     |           ***           ***
     |        ***                 ***
     |    ****                       ****
     |****                               ****
     +--------+--------+-----+-----+--------+--------> value
             -2       -1     0     1        2
```

Tessendorf draws each wave's complex amplitude as

```text
h0(k) = (ξ1 + i ξ2) · sqrt(P(k) / 2)
```

with `ξ1` and `ξ2` independent Gaussian numbers of average 0 and standard
deviation 1. Their squares average 1 each, so `|h0|²` averages `P(k)`: the
spectrum is the average, and the random numbers scatter each wave around it.
The angle of `ξ1 + i ξ2` is random too, which gives every wave a random phase.
A sum of many waves with Gaussian amplitudes is itself Gaussian, so the sea's
height comes out with the measured spread.

Chapter 21's `randomFloat` is **uniform**: every value in `[0, 1)` equally
likely. The **Box-Muller transform** turns two uniform numbers `u1` and `u2`
into two Gaussian ones:

```text
r = sqrt(−2 ln u1)          θ = 2π u2          (ξ1, ξ2) = (r cos θ, r sin θ)
```

`θ` picks a direction, all equally likely. `r` picks how far out, and
`−2 ln u1` is exactly the spread of distances a two-dimensional bell curve has:
most `u1` give a modest `r`, and only rare ones a large `r`. Some numbers:

| `u1` | `u2` | `r` | `(ξ1, ξ2)` |
| --- | --- | --- | --- |
| 0.9 | 0.0 | 0.46 | (0.46, 0) |
| 0.5 | 0.25 | 1.18 | (0, 1.18) |
| 0.01 | 0.5 | 3.03 | (−3.03, 0) |

A `u1` of 0.01 happens one time in a hundred, and gives a value three standard
deviations out: the rare big wave. `u1` must never be 0, whose logarithm is
minus infinity, so the shader uses `1 − randomFloat`, which lies in `(0, 1]`.
The other end needs a guard too. In exact arithmetic `−2 ln u1` is never
negative, but Vulkan lets a GPU's `log` be off by up to 2⁻²¹ between 0.5
and 2, so for a `u1` at or just below 1 the logarithm can come out a hair
above 0, and the square root of the negative product is a NaN. One NaN in
`h0` is a NaN at every texel once the FFT has run, as with `k = 0` above, so
the shader clamps the product at 0 with `max`.

Each texel needs its own random numbers, different for a different seed, and
the same every time for the same seed: Chapter 21 section 3's
`seedRandom(index, frame)`, with the panel's seed where a frame number would
go.

### The code

**This is the second half of `Ocean.glsl`**, before its `#endif`. `GRAVITY`
and `waveVector` are this section's: section 2's wave vector of a texel, in
radians per metre. `timesI` is section 8's:

```glsl
// Part 2, from section 7.
const float GRAVITY = 9.81;   // m/s^2

// The wave vector texel (n, m) stands for, in radians per metre: wave number
// (n - N/2, m - N/2) across a patch of patchSize metres.
vec2 waveVector(ivec2 texel, int n, float patchSize)
{
    return 2.0 * PI * vec2(texel - n / 2) / patchSize;
}

// i * z: a quarter turn (section 8).
vec2 timesI(vec2 z)
{
    return vec2(-z.y, z.x);
}

#endif
```

**This is `Shaders/Ocean/OceanSpectrum.comp.glsl`.** One invocation per wave:

```glsl
// Shaders/Ocean/OceanSpectrum.comp.glsl - the starting waves, h0(k): one random
// complex number per wave, sized by the Phillips spectrum (section 7). Runs
// when a spectrum setting changes, not every frame.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"
#include "Random.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 0, rg32f) uniform writeonly image2D h0;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

// Two independent Gaussian random numbers - average 0, spread 1 - from two
// uniform ones: the Box-Muller transform.
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

// The Phillips spectrum: how much energy the sea puts in the wave k, for this
// wind. Already multiplied by dk^2, the area one texel covers in k, so the
// heights do not change with the patch size.
float phillips(vec2 k)
{
    float kLength = length(k);
    if (kLength < 1e-6) { return 0.0; }    // k = 0 is no wave, and 1 / |k|^4 is infinite

    float windSpeed   = parameters.wind.z;
    float largestWave = windSpeed * windSpeed / GRAVITY;   // L = V^2 / g
    float k2          = kLength * kLength;
    float alignment   = dot(k / kLength, parameters.wind.xy);

    float spectrum = parameters.amplitude
                   * exp(-1.0 / (k2 * largestWave * largestWave)) / (k2 * k2)   // the shape
                   * alignment * alignment                                      // along the wind
                   * exp(-k2 * parameters.suppression * parameters.suppression); // no tiny ripples
    if (alignment < 0.0) { spectrum *= 0.05; }   // little runs against the wind

    float dk = 2.0 * PI / parameters.patchSize;
    return spectrum * dk * dk;
}

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(h0).x;
    if (texel.x >= n || texel.y >= n) { return; }

    // Row 0 and column 0 hold wave number -N/2, whose mirror is itself: it has
    // no partner to pair with (section 2), so it stays empty.
    vec2 value = vec2(0.0);
    if (texel.x != 0 && texel.y != 0)
    {
        // A random stream per texel, chosen by the seed (Chapter 21's seedRandom).
        uint state = seedRandom(uint(texel.y * n + texel.x), parameters.seed);
        vec2 k     = waveVector(texel, n, parameters.patchSize);
        value      = gaussianPair(state) * sqrt(phillips(k) / 2.0);
    }
    imageStore(h0, texel, vec4(value, 0.0, 0.0));
}
```

Everything in it is above, in order: Box-Muller, the Phillips spectrum with
its three adjustments and `Δk²`, and section 2's empty row and column. The
`alignment < 0` test is the upwind damping: a wave whose direction is more
than 90° from the wind's keeps 5% of its energy.

It reads five fields of `OceanParameters` that Part 1 left at zero, so
**`PackParameters` is now written whole.** Most of it is conversion: the panel
edits angles and sRGB colors, the shaders want directions and linear colors
(Chapter 08 section 4), and the clock is wrapped at the loop period, which
section 8 explains. The sun's fields are section 10's.

```cpp
OceanParameters OceanDemo::PackParameters() const
{
    uint32_t flags = 0;
    if (m_settings.testMirror)  { flags |= OCEAN_FLAG_TEST_MIRROR; }
    if (m_settings.skipSignFix) { flags |= OCEAN_FLAG_NO_SIGN_FIX; }

    // Part 2: directions from angles, linear colors from the swatches, and the
    // clock, wrapped at the loop period so a long run keeps its precision.
    const float     windAzimuth = glm::radians(m_settings.windAzimuth);
    const glm::vec2 windToward { std::sin(windAzimuth), -std::cos(windAzimuth) };   // x and z, like the sun's azimuth
    const glm::vec3 sunTravel  = sunTravelDirection(m_settings.sunElevation, m_settings.sunAzimuth);
    const float     shaderTime = m_settings.loopPeriod > 0.0f ? std::fmod(m_time, m_settings.loopPeriod) : m_time;

    return OceanParameters{
        .wind          = glm::vec4(windToward, m_settings.windSpeed, 0.0f),
        .sun           = glm::vec4(sunTravel, m_settings.sunIntensity),
        .waterColor    = glm::vec4(scene::srgbToLinear(m_settings.waterColor), 0.0f),
        .skyColor      = glm::vec4(scene::srgbToLinear(m_settings.skyColor), 0.0f),
        .amplitude     = m_settings.amplitude,
        .patchSize     = m_settings.patchSize,
        .suppression   = m_settings.suppression,
        .choppiness    = m_settings.choppiness,
        .time          = shaderTime,
        .loopPeriod    = m_settings.loopPeriod,
        .foamThreshold = m_settings.foamThreshold,
        .hazeDistance  = m_settings.hazeDistance,
        .previewGain   = m_settings.previewGain,
        .seed          = static_cast<uint32_t>(m_settings.seed),
        .view          = static_cast<uint32_t>(m_settings.view),
        .flags         = flags,
        .testWaveX     = m_settings.testWaveX,
        .testWaveZ     = m_settings.testWaveZ,
        .tiles         = static_cast<uint32_t>(2 * m_settings.tileRadius + 1),
    };
}
```

The two angles follow one convention, so the wind and the sun are set the same
way: azimuth 0 is toward −Z, the way the camera starts out looking, and
positive turns toward +X. It is the convention the grass uses (Chapter 25), but
you need nothing from that chapter: the sun's direction comes from this
file-scope helper:

```cpp
// File scope, above the namespace block. The direction sunlight travels, from the
// panel's two angles: Chapter 25's convention, the reverse of "toward the sun".
static glm::vec3 sunTravelDirection(float elevationDegrees, float azimuthDegrees)
{
    const float elevation = glm::radians(elevationDegrees);
    const float azimuth   = glm::radians(azimuthDegrees);
    const glm::vec3 towardSun{ std::cos(elevation) * std::sin(azimuth),
                               std::sin(elevation),
                               -std::cos(elevation) * std::cos(azimuth) };
    return -towardSun;
}
```

### Running it, once

`h0` changes only when the wind, the amplitude, the patch size, the
suppression, or the seed does, and a 256 x 256 dispatch every frame for an
unchanged result is waste. So it runs when `m_spectrumDirty` says so: once
after `Setup`, and again whenever section 11's panel moves a spectrum setting.
Add the pipeline's row to `CreateComputePipelines`' table:

```cpp
        { &m_spectrumPipeline, "Ocean/OceanSpectrum.comp.spv", m_oceanLayout },   // section 7
```

the flag to the end of `Setup`, after `ImGui_ImplVulkan_AddTexture`:

```cpp
    m_spectrumDirty  = true;   // h0 holds garbage until the spectrum pass has run
```

and step 2 to `Record`, between the ocean set's bind and step 3:

```cpp
    // 2. Section 7: the starting waves, only after a spectrum setting changed.
    if (m_spectrumDirty)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_spectrumPipeline);
        vkCmdDispatch(commandBuffer, groups, groups, 1);
        computeToComputeBarrier(commandBuffer);
        m_spectrumDirty = false;
    }
```

The barrier is Q1 and Q2 again: the animate pass of section 8 reads `h0`, which
this pass just wrote. The flag is cleared at record time, which is safe because
the commands run in the order recorded.

The preview gains its third view, a row in `VIEW_NAMES`:

```cpp
    "Spectrum |h0|",            // section 7
```

and a case in `OceanPreview.comp.glsl`'s switch:

```glsl
    // Part 2, section 7.
    case OCEAN_VIEW_SPECTRUM:
    {
        // |h0| spans several powers of ten, so show its logarithm: 1 is white,
        // 0.0001 and below black. log10(x) = log2(x) / log2(10).
        float magnitude = max(length(imageLoad(h0, texel).xy) * parameters.previewGain, 1e-8);
        color = vec3(clamp(1.0 + 0.25 * log2(magnitude) / log2(10.0), 0.0, 1.0));
        break;
    }
```

`|h0|` runs from about 0.1 for the biggest waves down to nothing, so the view
shows its logarithm: each quarter of the brightness range is a factor of ten.
Pick "Spectrum |h0|". You should see **a noisy blob centred on the square,
spread up and down — along the wind, which blows toward −Z, the preview's up —
bright above the centre and dim below it, where the upwind waves were damped,
with a dark line across the middle where waves run across the wind, and black
at the exact centre**, `k = 0`. (A NaN at `k = 0` would show here as one odd
texel; it is the FFT, in the next sections, that spreads it to every texel.)

---

## 8. Waves in motion

> **Jump:** so far a wave has been a fixed shape. Now it moves, and the
> surface needs more than heights: slopes, for lighting, and the sideways
> motion that sharpens crests. All of it comes from one fact about waves in a
> spectrum: **differentiating a wave multiplies its amplitude by `i k`**. Keep
> that sentence in mind; this section uses it four times.

### How fast each wave moves

On deep water a wave's speed depends on its length, and long waves outrun
short ones. The relation, the **dispersion relation**, says how fast a wave
turns in time:

```text
ω(k) = sqrt(g · |k|)          radians per second
```

`ω` (omega) is an **angular frequency** here: how many radians a wave turns
through per second, as `k` is how many it turns through per metre. (Chapter 24
used `ω` for a direction on the sphere; this is another letter's job.) A 100 m
wave has `|k| = 0.0628`, so `ω = 0.785`: it repeats every
`2π / ω = 8.0` seconds and its crests travel `ω / |k| = 12.5` m/s. A 10 m
wave turns faster, every 2.5 s, but travels only 4 m/s. On a beach you can
check the first: ocean swell arriving every eight seconds or so is about
100 m long.

A wave that turns by `ω` every second is an arrow multiplied by `e^(−iωt)`
at time `t`. The minus sign decides the direction it travels: `e^(i(k·p − ωt))`
has a crest where `k·p = ωt`, which moves along `k` as `t` grows.

### The waves at time t, still real

Turning every wave of `h0` by its own `e^(−iωt)` breaks section 2's rule: the
mirror wave turns the same way, so its amplitude is no longer the conjugate.
Tessendorf's fix builds each texel from both its own wave and its mirror's:

```text
h(k, t) = h0(k) · e^(−iωt)  +  conj(h0(−k)) · e^(+iωt)
```

The first term is this texel's wave, running along `k`. The second is the
mirror texel's wave, the one running along `−k`, as this texel must hold it:
its amplitude conjugated, turning the other way. Check the rule: at `−k` the
formula gives `h0(−k) e^(−iωt) + conj(h0(k)) e^(+iωt)`, which is exactly the
conjugate of `h(k, t)`. So the heights stay real at every moment, and every pair
of texels `k` and `−k` holds two real waves, one running each way, sized by
`h0(k)` and `h0(−k)`. **Drop the second term and every output gains an
imaginary part**: the waves come out at half height, and with this section's
packing (below) that imaginary part lands in the neighbouring field — heights
leak into displacements, slopes into derivatives — which looks wrong in a way
no slider fixes.

### Looping

The ocean never repeats: its `ω`s are irrational multiples of each other. For
something that must loop — a baked texture, a video — round every `ω` down to a
whole number of turns per loop period `T`:

```text
ω0 = 2π / T          ω = floor(sqrt(g |k|) / ω0) · ω0
```

Every wave then turns a whole number of times in `T` seconds, and so does the
whole sea. With `T = 20` s, `ω0 = 0.314`, and the 100 m wave's 0.785 becomes
0.628: two turns per loop instead of 2.5, so it moves 20% slower than it
should. Short waves turn many times per loop and barely change; a wave whose
`ω` is below `ω0` rounds to 0 and stands still. Long periods keep the error
small. The panel's "Loop period" turns it on (0 is off), and `PackParameters`
wraps the clock at `T`, so `time` jumps from `T` back to 0 — invisibly, if the
rounding is right.

### Slopes: differentiating is multiplying by i k

The surface needs its slope at every point, to light it. Differentiating a
wave is easy in a spectrum. In one dimension, `cos(k x)` is
`½ e^(ikx) + ½ e^(−ikx)`: amplitude ½ at `+k` and at `−k`. That is section
2's mirror pair: added, the two arrows' imaginary parts cancel and leave
`2 cos`; subtracted, the real parts cancel and leave `2i sin`, which the
second step below uses. Its derivative is
`−k sin(k x)`. Multiply each amplitude by `i` times its own wave number:

```text
i k · ½ e^(ikx) + i(−k) · ½ e^(−ikx) = (i k / 2)(e^(ikx) − e^(−ikx)) = (i k / 2)(2i sin kx) = −k sin(kx)
```

It works for every wave, so it works for any sum of them. **The slope along x
is the inverse transform of `i kx h(k, t)`**, and along z of `i kz h(k, t)`.
No finite differences between neighbouring texels, and no error from them.

### Sharp crests: moving the surface sideways

Real crests are sharp and troughs broad. A sum of cosines has round crests and
round troughs. Tessendorf sharpens them by moving each point of the surface
sideways, toward the nearest crest:

```text
choppiness 0:   .   .   .   .   .   .   .   .   .     evenly spaced
                 ~~~~~~        ~~~~~~        ~~~~
choppiness 1:  .  .  .     .     .  .  .     .        bunched at the crests
                  /\            /\            /
               __/  \__________/  \__________/
```

For one wave `h = A cos(k x)`, a crest at `x = 0` gathers its neighbours if
the point at `x` moves by `−A sin(k x)`: points just right of the crest move
left, points just left move right. In the spectrum, that displacement is the
slope `i k h` divided by `|k|`:

```text
D(k, t) = i (k / |k|) · h(k, t)          moved position = p + λ D(p)
```

`λ` is the **choppiness**, the slider you will move most: 0 gives smooth swells,
1 sharp wind-driven crests. The two components, `i (kx/|k|) h` and
`i (kz/|k|) h`, are two more fields to transform. Papers and implementations
disagree about the sign in front, because they define the transform with
different signs; with this chapter's transform, `+i` is the sign that bunches
points at the crests. If foam (section 9) sits in the troughs instead of on the
crests, the sign is flipped.

`k / |k|` is `0 / 0` at `k = 0`, which is a NaN, and a NaN times the zero that
`h(0, t)` is, is still a NaN. **The same texel bites a second time**: guard the
direction with `|k| > 1e-6` before dividing. The slopes need no guard; `i k h`
is simply 0 there.

### Three more derivatives, for foam

Section 9 finds the foam from how much the sideways motion squeezes the
surface, which takes three derivatives of `D`: how `Dx` changes along x, how
`Dz` changes along z, and how `Dz` changes along x (which equals how `Dx`
changes along z). The first is written `∂Dx/∂x`: the change in `Dx` along x,
with z held still. Each is the multiply-by-`i k` rule again:

```text
∂Dx/∂x = i kx · i (kx/|k|) h = −(kx²/|k|) h
∂Dz/∂z = −(kz²/|k|) h
∂Dz/∂x = −(kx kz/|k|) h
```

### Eight real fields, four transforms

That is eight fields: the height, two displacements, two slopes, three
derivatives. Each is real: each is `h(k, t)` times a factor whose value at `−k`
is the conjugate of its value at `k` — `i kx` becomes `−i kx` — so the mirror
rule survives the multiplication. Eight transforms is twice what is needed.

A complex transform of a real field wastes half its output: the imaginary part
is zero. Put a second real field's spectrum there. If `X` transforms to the
real field `a` and `Y` to the real field `b`, then by adding the sums term by
term, `X + iY` transforms to `a + ib`: `a` in the real part, `b` in the
imaginary part. With section 2's numbers: `X = [0, 1, 0, 1]` gives
`a = [2, 0, −2, 0]`, and `Y = [0, −i, 0, i]` gives `b = [0, 2, 0, −2]`. Their
combination is `X + iY = [0, 2, 0, 0]`, which transforms to
`[2, 2i, −2, −2i]` — real part `a`, imaginary part `b`.

So eight real fields need four complex transforms, two per texel, in two images.
`timesI` makes the `i Y`:

| Image | `.xy` holds | `.zw` holds | After the FFT, `.xyzw` is |
| --- | --- | --- | --- |
| A | `Dx + i h` | `Dz + i ∂h/∂x` | `Dx, h, Dz, ∂h/∂x` |
| B | `∂h/∂z + i ∂Dx/∂x` | `∂Dz/∂z + i ∂Dz/∂x` | `∂h/∂z, ∂Dx/∂x, ∂Dz/∂z, ∂Dz/∂x` |

A's first three outputs are the displacement vector, in order.

This is also why section 2's empty row and column matter here. A field packed
into the imaginary half is recovered exactly only if both fields' spectra keep
the mirror rule. Row 0's wave is its own mirror, and multiplying it by `i k`
breaks the rule; its imaginary part would leak into the field packed beside it.
With row 0 and column 0 empty, nothing leaks.

### The code

**This is `Shaders/Ocean/OceanAnimate.comp.glsl`.** One invocation per wave,
every frame:

```glsl
// Shaders/Ocean/OceanAnimate.comp.glsl - every frame: the waves at this
// moment, h(k, t), and the seven spectra derived from it, packed four complex
// numbers to a texel for the FFT (section 8).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 0, rg32f)   uniform readonly  image2D h0;
layout(set = 0, binding = 1, rgba32f) uniform writeonly image2D spectrumA;
layout(set = 0, binding = 2, rgba32f) uniform writeonly image2D spectrumB;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(h0).x;
    if (texel.x >= n || texel.y >= n) { return; }

    vec2  k       = waveVector(texel, n, parameters.patchSize);
    float kLength = length(k);

    // How fast this wave turns: deep water's dispersion, w = sqrt(g |k|). To
    // loop, every w is rounded down to a whole number of turns per period.
    float omega = sqrt(GRAVITY * kLength);
    if (parameters.loopPeriod > 0.0)
    {
        float omega0 = 2.0 * PI / parameters.loopPeriod;
        omega = floor(omega / omega0) * omega0;
    }

    // h(k, t) = h0(k) e^(-iwt) + conj(h0(-k)) e^(+iwt): this wave, carried
    // along k, plus its mirror's conjugate, which keeps the heights real.
    vec2 forward  = complexExp(-omega * parameters.time);
    vec2 h0k      = imageLoad(h0, texel).xy;
    vec2 h0Mirror = imageLoad(h0, mirrorTexel(texel, n)).xy;
    vec2 h        = complexMultiply(h0k, forward)
                  + complexMultiply(vec2(h0Mirror.x, -h0Mirror.y), vec2(forward.x, -forward.y));

    // Everything else is h times something. A slope is a derivative, and a
    // derivative is a multiplication by i k (section 8). The sideways
    // displacement is the slope divided by |k|. k = 0 has no direction: guard it.
    vec2 unitK = kLength > 1e-6 ? k / kLength : vec2(0.0);
    vec2 ih    = timesI(h);
    vec2 dx    = ih * unitK.x;           // sideways displacement, x:  i (kx / |k|) h
    vec2 dz    = ih * unitK.y;           // ...and z
    vec2 sx    = ih * k.x;               // slope dh/dx:               i kx h
    vec2 sz    = ih * k.y;               // slope dh/dz
    vec2 dxx   = -h * k.x * unitK.x;     // d(dx)/dx = i kx (i kx / |k|) h
    vec2 dzz   = -h * k.y * unitK.y;     // d(dz)/dz
    vec2 dxz   = -h * k.x * unitK.y;     // d(dz)/dx, which equals d(dx)/dz

    // Two real fields per complex FFT: first + i * second (section 8).
    imageStore(spectrumA, texel, vec4(dx + timesI(h),   dz  + timesI(sx)));
    imageStore(spectrumB, texel, vec4(sz + timesI(dxx), dzz + timesI(dxz)));
}
```

It reads `h0` at its own texel and at its mirror, so it is the one place that
needs section 2's `−k` texel. `forward` is `e^(−iωt)`, and its conjugate,
`(forward.x, −forward.y)`, is `e^(+iωt)`.

Add its row to `CreateComputePipelines`:

```cpp
        { &m_animatePipeline,  "Ocean/OceanAnimate.comp.spv",  m_oceanLayout },   // section 8
```

and make step 3 of `Record` a choice between it and Part 1's test wave, which
the preview's "Instead of the ocean" box now controls:

```cpp
    // 3. The FFT's input: this moment's ocean (section 8), or Part 1's test wave.
    if (m_settings.testWave)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_testWavePipeline);
    }
    else
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_animatePipeline);
    }
    vkCmdDispatch(commandBuffer, groups, groups, 1);
    computeToComputeBarrier(commandBuffer);
```

With "FFT output, imaginary part" in the preview you now see the height field,
and with "real part" the sideways displacement along x — A's first complex
number, transformed. They move.

---

## 9. Assembling the maps

The FFT leaves eight fields in two images, centred and packed. One more pass
turns them into the two maps the surface samples.

### The sign, the fields, and the normal

Every texel is multiplied by section 6's `(−1)^(x + y)`, and the fields are read
out of the packing of section 8. The displacement map gets
`(λ Dx, h, λ Dz)`: the choppiness is applied here, once, so the vertex shader
only adds. The normal comes from the two slopes: a surface rising by `∂h/∂x`
per metre along x has a normal tipped back against that rise, and normalizing
`(−∂h/∂x, 1, −∂h/∂z)` gives it.

### The Jacobian: how squeezed the surface is

Picture the flat grid as small squares, and move every corner sideways by
`λ D`. Near a crest the corners crowd together and the squares shrink; in a
trough they spread out and the squares grow:

```text
   flat grid          after the sideways move
  +--+--+--+--+       +---+-+.+-+---+
  |  |  |  |  |       |   | |.| |   |
  +--+--+--+--+  ->   +---+-+.+-+---+
  |  |  |  |  |       |   | |.| |   |
  +--+--+--+--+       +---+-+.+-+---+
                       trough crest trough
```

The **Jacobian**, `J`, is how much the area of one small square is scaled. 1 is
unchanged, 0.5 is squeezed to half, and below 0 the square has been pushed so
far that it is turned inside out: the surface has folded over itself, the way a
breaking crest does. For a sideways move `(λ Dx, λ Dz)` it is

```text
J = (1 + λ ∂Dx/∂x) · (1 + λ ∂Dz/∂z) − (λ ∂Dz/∂x)²
```

Each bracket is how much one side of the square is stretched (a derivative of
`−0.5` with `λ = 1` halves that side), and the last term is the shear that
turns the square into a diamond. For the single wave of section 8,
`J = 1 − λ A k cos(k x)`: smallest at the crest, largest in the trough. With
`A = 1` m and a 63 m wave (`k = 0.1`), `J` is 0.9 at the crest and 1.1 in the
trough; the crest folds when `λ A k` passes 1. `J` is the determinant of
Chapter 12 section 5, for the two-dimensional move: a negative one there meant
a mirror, and here it means a fold.

Breaking waves leave **foam**, and they break where the surface is squeezed. So
foam is wherever `J` is below a threshold. At the defaults — 12 m/s,
choppiness 1 — `J` ranges from about 0.5 to 1.5 and reaches 0 nowhere, so the
default threshold, 0.7, marks the most squeezed 1% of the surface. Push the
choppiness to 2.5 and the crests start to fold.

### The code

**This is `Shaders/Ocean/OceanAssemble.comp.glsl`:**

```glsl
// Shaders/Ocean/OceanAssemble.comp.glsl - after the FFT: undo the centring,
// unpack the eight fields, and write the two maps the surface samples (section 9).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "OceanTypes.h"
#include "Ocean.glsl"

layout(local_size_x = OCEAN_GROUP_SIZE, local_size_y = OCEAN_GROUP_SIZE) in;

layout(set = 0, binding = 1, rgba32f) uniform readonly  image2D spectrumA;
layout(set = 0, binding = 2, rgba32f) uniform readonly  image2D spectrumB;
layout(set = 0, binding = 3, rgba16f) uniform writeonly image2D displacementMap;
layout(set = 0, binding = 4, rgba16f) uniform writeonly image2D normalMap;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

void main()
{
    ivec2 texel = ivec2(gl_GlobalInvocationID.xy);
    int   n     = imageSize(spectrumA).x;
    if (texel.x >= n || texel.y >= n) { return; }

    // Section 6's sign, then section 8's packing, read back out.
    float sign = centringSign(texel, parameters.flags);
    vec4  a    = sign * imageLoad(spectrumA, texel);   // dx, h, dz, slope x
    vec4  b    = sign * imageLoad(spectrumB, texel);   // slope z, d(dx)/dx, d(dz)/dz, d(dz)/dx

    float lambda = parameters.choppiness;
    vec3  displacement = vec3(lambda * a.x, a.y, lambda * a.z);

    // Up, tipped against each slope.
    vec3 normal = normalize(vec3(-a.w, 1.0, -b.x));

    // How a small square of the grid is stretched by the sideways move:
    // 1 unchanged, below 1 squeezed, below 0 folded over itself.
    float jacobian = (1.0 + lambda * b.y) * (1.0 + lambda * b.z) - (lambda * b.w) * (lambda * b.w);

    imageStore(displacementMap, texel, vec4(displacement, 0.0));
    imageStore(normalMap, texel, vec4(normal, jacobian));
}
```

The Jacobian rides in the normal map's `w`, since the fragment shader that
needs the normal also needs the foam. Add the pipeline's row:

```cpp
        { &m_assemblePipeline, "Ocean/OceanAssemble.comp.spv", m_oceanLayout },   // section 9
```

and step 5 to `Record`, after the ocean set is bound again following
`RecordFft`:

```cpp
    // 5. Section 9: unpack into the two maps the surface samples.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_assemblePipeline);
    vkCmdDispatch(commandBuffer, groups, groups, 1);
    computeToComputeBarrier(commandBuffer);
```

The barrier is for the preview pass, which reads both maps.

### Three more views

`VIEW_NAMES` gains its last three rows:

```cpp
    "Height",                   // section 9
    "Normal",
    "Jacobian (white: foam)",
```

and the preview's switch its last three cases:

```glsl
    // Part 2, section 9.
    case OCEAN_VIEW_HEIGHT:
        color = signedColor(0.25 * imageLoad(displacementMap, texel).y);   // +-4 m at brightness 1
        break;
    case OCEAN_VIEW_NORMAL:
        color = 0.5 + 0.5 * imageLoad(normalMap, texel).xyz;
        break;
    case OCEAN_VIEW_JACOBIAN:
    {
        // Stretched orange, squeezed blue, foam white.
        float jacobian = imageLoad(normalMap, texel).w;
        color = jacobian < parameters.foamThreshold ? vec3(1.0) : signedColor(2.0 * (jacobian - 1.0));
        break;
    }
```

With the defaults you should see:

- **Height:** orange crests and blue troughs in bands across the wind —
  horizontal, since the wind blows up the preview — irregular, a few long
  waves with shorter ones on them, and moving up the square.
- **Normal:** nearly flat green — the up vector `(0, 1, 0)` shows as
  `(0.5, 1, 0.5)` — with faint streaks across the wind. Ocean slopes are
  gentle.
- **Jacobian:** orange where the surface is stretched, blue where it is
  squeezed, and white specks of foam among the blue. Section 11's panel moves
  the choppiness up, and then the specks grow into streaks.

## Checkpoint

Build and run with `--demo Ocean`. The scene is still Part 1's clear blue; the
"Ocean preview" holds everything Part 2 made, at the default settings, with
"Instead of the ocean" unticked:

- **"Spectrum |h0|"** is section 7's noisy blob: centred on the square, spread
  up and down along the wind, bright above the centre and dim below it, with a
  dark line across the middle and black at the exact centre.
- **"FFT output, imaginary part"** is the height field, and "real part" the
  sideways displacement along x (section 8). Both move.
- **"Height", "Normal", and "Jacobian"** are the three views above: bands
  across the wind moving up the square, a nearly flat green, and orange and
  blue with white specks of foam.
- **"Instead of the ocean"** brings back Part 1's test wave, and every item of
  Part 1's checkpoint still holds.

If the Height view is one colour, or black, the spectrum has a NaN at `k = 0`
(section 7) or the displacement's direction is unguarded there (section 8).

---

# Part 3 — The surface (sections 10-12)

Part 2's maps are right in the preview. Part 3 draws them: a grid moved by the
displacement map and lit with the normals (section 10), a panel for every
number (section 11), and the frame in order, with what comes next (section 12).

## 10. The surface

Everything so far happened in images. This section draws the sea: a flat grid
of quads, moved by the displacement map in the vertex shader and shaded as
water in the fragment shader.

### A grid from `gl_VertexIndex`

The grid needs no vertex buffer. Its vertices are evenly spaced, so the vertex
index alone says where each one is — the way Chapter 06's triangle took its
corners from `gl_VertexIndex`, and Chapter 25's blades their shape. Each quad
is two triangles, six vertices, so vertex `v` belongs to quad `v / 6` and is
corner `v % 6` of it; the quad is `(quad % cells, quad / cells)` in the grid.
`OCEAN_GRID_CELLS`, 128, is the quads along one side of a patch, so one patch
is `6 · 128²` vertices.

The grid's resolution and the FFT's are independent. 128 quads across a
256-texel map means each vertex lands on every other texel, and the fragment
shader still reads the normals at full resolution between them.

### Patches to the horizon

The FFT's output repeats: the waves all fit a whole number of times across the
patch, so the right edge of the height field continues into the left edge. Draw
the same patch side by side and the seams vanish — as long as the sampler wraps
(`REPEAT`), so that a texture coordinate of 1.2 reads the texel 0.2 would.

The surface is drawn **instanced**, one instance per patch: `tiles x tiles`
patches, with instance `i` at `(i % tiles, i / tiles)`. They are centred on the
patch under the camera, recomputed from `frame.cameraPosition` every frame, so
the sea follows you wherever you fly. `tiles` is odd — `2 r + 1`, with `r` the
panel's "Patches each side" — so that there is a middle patch.

One detail of addressing. Texel `t` of a map belongs to the point `t · L / N`
of the patch, but a texture coordinate reaches texel `t`'s centre at
`(t + 0.5) / N`. The vertex shader adds that half texel, so that a vertex
exactly on a texel reads that texel and not the average of two.

**This is `Shaders/Ocean/OceanSurface.vert.glsl`:**

```glsl
// Shaders/Ocean/OceanSurface.vert.glsl - a flat grid, built from gl_VertexIndex,
// moved by the displacement map (section 10).
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"   // set 0: frame.viewProjection, frame.cameraPosition
#include "OceanTypes.h"

layout(set = 1, binding = 0) uniform sampler2D displacementMap;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec2 surfaceUv;

void main()
{
    // Which quad, and which of its six corners. Two triangles, counter-clockwise
    // seen from above (+Y): Chapter 11's frontFace.
    const uvec2 corners[6] = uvec2[](uvec2(0, 0), uvec2(0, 1), uvec2(1, 1),
                                     uvec2(0, 0), uvec2(1, 1), uvec2(1, 0));
    uint  quad   = uint(gl_VertexIndex) / 6u;
    uvec2 corner = uvec2(quad % OCEAN_GRID_CELLS, quad / OCEAN_GRID_CELLS) + corners[gl_VertexIndex % 6];
    vec2  inPatch = vec2(corner) / float(OCEAN_GRID_CELLS) * parameters.patchSize;   // 0 .. L metres

    // Which patch: tiles x tiles of them, one per instance, centred on the patch
    // under the camera, so the sea follows you wherever you fly.
    int   tiles = int(parameters.tiles);
    ivec2 tile  = ivec2(gl_InstanceIndex % tiles, gl_InstanceIndex / tiles) - tiles / 2;
    vec2  cameraPatch = floor(frame.cameraPosition.xz / parameters.patchSize);
    vec2  gridPosition = (cameraPatch + vec2(tile)) * parameters.patchSize + inPatch;

    // Texel t of the maps belongs to the point t * L / N, and a texel's centre is
    // at texture coordinate (t + 0.5) / N. The sampler repeats, so every patch
    // reads the same maps. textureLod: a vertex shader has no derivatives to pick a level with.
    vec2 uv = gridPosition / parameters.patchSize + 0.5 / vec2(textureSize(displacementMap, 0));
    vec3 displacement = textureLod(displacementMap, uv, 0.0).xyz;

    worldPosition = vec3(gridPosition.x, 0.0, gridPosition.y) + displacement;
    surfaceUv     = uv;
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

### Shading water

Water is almost all reflection. What you see of the sea is mostly the sky
reflected in it, plus the sun reflected in it, plus a little light that went
into the water and came back out. If you have read Chapters 11 and 15, steps 1
and 2 below are their Fresnel and Lambert, said again briefly for a reader who
came here from Chapter 20. **This is
`Shaders/Ocean/OceanSurface.frag.glsl`**, and its four numbered steps are
those, then foam, then haze over all of it:

1. **Reflection.** How much a surface reflects depends on the angle you see it
   at — the **Fresnel** effect: look straight down into a lake and you see the
   bottom, look across it and you see the far shore mirrored. Schlick's
   approximation is `F = F0 + (1 − F0)(1 − cos θ)^5`, with `θ` between the
   normal and the direction to the eye, and `F0 = 0.02` for water:

   | Angle from straight down | 0° | 45° | 60° | 70° | 80° | 85° | 89° |
   | --- | --- | --- | --- | --- | --- | --- | --- |
   | Reflected | 2% | 2% | 5% | 14% | 40% | 64% | 92% |

   So most of the sea, seen from a ship, is the sky (Chapter 15 section 9 has
   Fresnel in full). What is reflected is the sky in the mirror direction,
   `reflect(−toEye, normal)`: here a simple gradient, the horizon color at the
   horizon and a darker blue overhead. The sun is in that mirror too, a small,
   very bright disc: `pow(max(dot(reflected, toSun), 0), 800)` is 1 when the
   mirror direction points straight at the sun and falls to nothing within a
   few degrees. Times the panel's "Sun glint", it is the glittering path toward
   a low sun.
2. **The water's own color.** Light that refracts into the water scatters, and
   some comes back out: `waterColor`, brighter where the surface faces the sun
   — Lambert's `max(dot(normal, toSun), 0)`, from Chapter 11 section 14 — and
   never fully dark. It fills in what the reflection does not, `1 − F`.
3. **Foam**, where section 9's Jacobian is below the threshold, fading in over
   0.3 of `J` so that it has soft edges, lit like the water's body.
4. **Haze.** Far water fades into the horizon color by `1 − exp(−range / haze)`:
   63% of the way at the haze distance, 95% at three times it. The scene pass is
   cleared to the same color, so the sea runs into the sky with no line, and the
   edge of the farthest patch is hidden.

The fragment shader's distance is called `range` because `distance` is a GLSL
function, which a variable must not shadow.

```glsl
// Shaders/Ocean/OceanSurface.frag.glsl - water: the sky it reflects, the color
// it sends back up, the sun's glint, foam, and haze (section 10). Linear values.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"
#include "OceanTypes.h"

layout(set = 1, binding = 1) uniform sampler2D normalMap;

layout(push_constant) uniform PushConstants
{
    OceanParameters parameters;
};

layout(location = 0) in vec3 worldPosition;
layout(location = 1) in vec2 surfaceUv;

layout(location = 0) out vec4 outColor;

// The sky in a direction: the horizon color, darker and bluer toward the top.
vec3 skyColor(vec3 direction)
{
    float up = clamp(direction.y, 0.0, 1.0);
    return parameters.skyColor.rgb * mix(vec3(1.0), vec3(0.45, 0.6, 0.85), up);
}

void main()
{
    vec4  surface  = texture(normalMap, surfaceUv);
    vec3  normal   = normalize(surface.xyz);
    float jacobian = surface.w;

    vec3  toEye        = normalize(frame.cameraPosition.xyz - worldPosition);
    vec3  toSun        = -parameters.sun.xyz;
    float sunIntensity = parameters.sun.w;

    // 1. Reflection. Water reflects 2% of the light looking straight down and
    //    nearly all of it at a grazing angle: Schlick's approximation of Fresnel.
    vec3  reflected = reflect(-toEye, normal);
    float facing    = clamp(dot(normal, toEye), 0.0, 1.0);
    float fresnel   = 0.02 + 0.98 * pow(1.0 - facing, 5.0);
    vec3  mirror    = skyColor(reflected)
                    + sunIntensity * pow(max(dot(reflected, toSun), 0.0), 800.0) * vec3(1.0, 0.95, 0.85);

    // 2. The water's own color, the light that went in and came back out:
    //    brighter where the surface faces the sun (Lambert, Chapter 11 section 14).
    float lit   = max(dot(normal, toSun), 0.0);
    vec3  body  = parameters.waterColor.rgb * (0.4 + 0.6 * lit);
    vec3  color = mix(body, mirror, fresnel);

    // 3. Foam where the surface is squeezed (section 9), fading in over 0.3 of
    //    Jacobian below the threshold.
    float foam = clamp((parameters.foamThreshold - jacobian) / 0.3, 0.0, 1.0);
    color = mix(color, vec3(0.8) * (0.5 + 0.5 * lit), foam);

    // 4. Haze: far water fades into the horizon, which hides where the patches end.
    float range = length(frame.cameraPosition.xyz - worldPosition);
    color = mix(color, parameters.skyColor.rgb, 1.0 - exp(-range / parameters.hazeDistance));

    outColor = vec4(color, 1.0);
}
```

Every color here is linear (Chapter 08 section 4): `waterColor` and `skyColor`
were converted from the swatches' sRGB in `PackParameters`, and the composite
pass encodes the result. The glint can go well above 1; Chapter 16's tone
curve, if you turn it on, rolls it off instead of clipping it.

### The pipeline, its set, and the sampler

**This is `CreateSurface`.** Most of it is the pattern every scene pipeline
since Chapter 10 has followed: a sampler, a set layout, a pool and one set, the
set's two writes, a pipeline layout with the scene renderer's set 0 for the
camera (Chapter 10 section 7) and the demo's own set 1, and a graphics pipeline
with the scene's formats and sample count. Appendix B has it whole. Four parts of it are this chapter's
choices. It starts with the sampler, which repeats:

```cpp
InitializationResult OceanDemo::CreateSurface()
{
    // Linear filtering between texels, and REPEAT: the maps tile, so every patch
    // reads the same texels and the edges meet.
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
        return InitializationResult::failure("vkCreateSampler failed for the ocean surface.");
    }
```

Set 1's two bindings name different stages:

```cpp
    // Set 1: the displacement for the vertex shader, the normals for the fragment shader.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT },
        { .binding         = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT },
    };
```

The descriptors name the layout the maps are in while the surface draws:

```cpp
    // The layout the maps are in while the surface draws: Record moves them there.
    const VkDescriptorImageInfo maps[] = {
        { .sampler = m_sampler, .imageView = m_displacement.view, .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = m_sampler, .imageView = m_normals.view,      .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
    };
```

And the pipeline draws with depth and without culling:

```cpp
    // Depth on, like every scene pipeline (Chapter 10 section 9), at the scene's
    // sample count (Chapter 18). No culling: where a crest folds over, its
    // triangles face down, and culling them would punch holes in the crest.
    const GraphicsPipelineDesc desc{
        .vertexShader   = "Ocean/OceanSurface.vert.spv",
        .fragmentShader = "Ocean/OceanSurface.frag.spv",
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
```

Why each:

- **The sampler repeats.** The maps tile, so a texture coordinate of 1.2 must
  read the texel 0.2 would, and every patch reads the same texels.
- **The set's two bindings name different stages.** The displacement is read in
  the vertex shader, the normals in the fragment shader, and the set layout
  says so. The barriers below follow the same split.
- **The descriptors name `SHADER_READ_ONLY_OPTIMAL`**, the layout the maps are
  in when the surface draws, not the `GENERAL` they are written in.
- **No culling.** The grid is counter-clockwise seen from above, like Chapter
  11's meshes, so `BACK` culling would hide the water from below at no cost.
  But where a crest folds over (section 9), its triangles are turned upside
  down, and culling would punch holes in exactly the crests. The depth test
  sorts the fold out instead.

The surface is drawn with depth, like every scene pipeline from Chapter 10 on,
and it is the first in the tutorial that hides parts of *itself*: at a grazing
angle near waves hide far ones, and only a per-pixel depth test gets that right.
Its far plane is far, so the near plane matters more than usual (Chapter 10
section 2); that is why the constructor moved it out to 0.5 m.

`CreateSurface` needs the scene renderer's set 0 layout, so the scene renderer
is initialized first. `Setup` gains its first and its last creation steps:

```cpp
    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }
```

```cpp
    if (auto result = CreateSurface(); !result)          { return result; }   // section 10
```

### The barriers between compute and the surface

The two maps are written by the assemble pass and read by the surface in the
same frame, then written again next frame. Each needs both directions, and each
names **the stage that actually reads it**:

| | Displacement map | Normal map |
| --- | --- | --- |
| Into the surface: srcStage / srcAccess | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` |
| dstStage / dstAccess | `VERTEX_SHADER` / `SHADER_SAMPLED_READ` | `FRAGMENT_SHADER` / `SHADER_SAMPLED_READ` |
| Layout | `GENERAL` to `SHADER_READ_ONLY_OPTIMAL` | same |
| Back to compute, next frame: srcStage / srcAccess | `VERTEX_SHADER` / `NONE` | `FRAGMENT_SHADER` / `NONE` |
| dstStage / dstAccess | `COMPUTE_SHADER` / `SHADER_STORAGE_WRITE` | same |
| Layout | `UNDEFINED` to `GENERAL` | same |

These are Chapter 20 section 10's rows for a compute result read by graphics,
and Chapter 04's appendix has them as "Compute result sampled by a later
shader" and "Sampled result handed back to compute".

**`VERTEX_SHADER`, not `FRAGMENT_SHADER`, for the displacement.** The vertex
shader runs before the fragment shader, so a barrier that waits only until the
fragment stage lets the vertex shader read the map while the assemble pass may
still be writing it. That is a race that usually works, which is the worst
kind. Sync validation catches it, with the shader-access setting on.

**The return trip is the half that gets forgotten**, because the first frame
does not need it. From the second frame on, the assemble pass writes maps the
previous frame's surface may still be reading. `UNDEFINED` as the old layout is
right because the assemble pass rewrites every texel.

In `Record`, step 1 gains the two return trips, after the preview's:

```cpp
    transitionImage(commandBuffer, m_displacement.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    transitionImage(commandBuffer, m_normals.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
```

and step 7 the two hand-overs, before the preview's:

```cpp
    transitionImage(commandBuffer, m_displacement.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    transitionImage(commandBuffer, m_normals.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
```

The preview pass, step 6, reads both maps as storage images in `GENERAL`, so
the hand-overs come after it, and their `COMPUTE_SHADER` source stage covers the
preview's reads as well as the assemble pass's writes.

### Drawing it

**This is `RecordSurface`.** The camera goes into set 0's buffer for this frame
slot (Chapter 10 section 7), the scene pass is cleared to the horizon's color,
and one draw makes every patch:

```cpp
void OceanDemo::RecordSurface(VkCommandBuffer commandBuffer, const RecordContext& frame,
                              const OceanParameters& parameters)
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

    // Cleared to the horizon's color, so the haze runs into the sky without a line.
    const VkClearColorValue sky{ { parameters.skyColor.r, parameters.skyColor.g, parameters.skyColor.b, 1.0f } };
    beginScenePass(commandBuffer, frame.targets, &sky);

    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_surfacePipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_surfaceLayout, frame.frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_surfaceLayout,
                            1, 1, &m_surfaceSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_surfaceLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(parameters), &parameters);

    // Six vertices per quad, one instance per patch, no vertex buffer.
    vkCmdDraw(commandBuffer, 6 * OCEAN_GRID_CELLS * OCEAN_GRID_CELLS, parameters.tiles * parameters.tiles, 0, 0);

    endScenePass(commandBuffer);
}
```

The push constants go to both stages in one call, because the surface's layout
gave both stages the same range. In `Record`, step 8 replaces Part 1's clear:

```cpp
    // 8. Section 10: the sea, then the scene target goes back to the engine.
    RecordSurface(commandBuffer, frame, parameters);
    handBackSceneTarget(commandBuffer, frame.targets);
```

Finally, the camera needs input, and the "Camera" panel. Add to the top of
`Update`, as every camera demo since Chapter 10 has it:

```cpp
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    scene::drawCameraPanel(m_camera, m_controls, m_cameraTransform);
```

Run it. You should see the sea under a pale sky, 12 m below you, running out
to a hazy horizon, with a glittering path of sunlight toward the low sun ahead,
and waves moving away from you, downwind. Hold the right mouse button to look
around, and W, A, S, D to fly.

---

## 11. The panel

**This is `drawOceanPanel`**, the second window, beside the preview:

```cpp
// Section 11. The ocean's settings. True when a spectrum setting changed, so h0
// must be rebuilt. `shaderTime` is the time the shaders see, wrapped at the loop period.
static bool drawOceanPanel(OceanSettings& settings, float shaderTime)
{
    bool spectrumChanged = false;
    if (debug_panels::beginDemoPanel("Ocean", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::SeparatorText("Spectrum (rebuilds h0)");
        spectrumChanged |= ImGui::SliderFloat("Wind speed (m/s)", &settings.windSpeed, 1.0f, 30.0f);
        spectrumChanged |= ImGui::SliderFloat("Wind toward (deg)", &settings.windAzimuth, -180.0f, 180.0f);
        // AlwaysClamp: a value typed with Ctrl+click stays in range too. A negative amplitude or a
        // 0 m patch would put a NaN in h0, and the FFT would spread it over the whole sea (section 7).
        spectrumChanged |= ImGui::SliderFloat("Amplitude", &settings.amplitude, 0.0001f, 0.01f, "%.4f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
        spectrumChanged |= ImGui::SliderFloat("Patch size (m)", &settings.patchSize, 50.0f, 2000.0f, "%.0f",
                                              ImGuiSliderFlags_Logarithmic | ImGuiSliderFlags_AlwaysClamp);
        spectrumChanged |= ImGui::SliderFloat("Suppression (m)", &settings.suppression, 0.0f, 5.0f);
        spectrumChanged |= ImGui::InputInt("Seed", &settings.seed);

        ImGui::SeparatorText("Every frame (free)");
        ImGui::SliderFloat("Choppiness", &settings.choppiness, 0.0f, 2.5f);
        ImGui::SliderFloat("Time scale", &settings.timeScale, 0.0f, 4.0f);
        ImGui::SliderFloat("Loop period (s)", &settings.loopPeriod, 0.0f, 120.0f, "%.1f");   // 0: never loops
        ImGui::Text("Clock %.1f s", shaderTime);
        ImGui::SliderFloat("Foam threshold", &settings.foamThreshold, -1.0f, 1.0f);
        ImGui::ColorEdit3("Water", &settings.waterColor.x);
        ImGui::ColorEdit3("Sky", &settings.skyColor.x);
        ImGui::SliderFloat("Sun elevation", &settings.sunElevation, 0.0f, 90.0f);
        ImGui::SliderFloat("Sun azimuth", &settings.sunAzimuth, -180.0f, 180.0f);
        ImGui::SliderFloat("Sun glint", &settings.sunIntensity, 0.0f, 100.0f);
        ImGui::SliderFloat("Haze (m)", &settings.hazeDistance, 50.0f, 5000.0f, "%.0f", ImGuiSliderFlags_Logarithmic);
        ImGui::SliderInt("Patches each side", &settings.tileRadius, 0, 4);
    }
    ImGui::End();
    return spectrumChanged;
}
```

The useful thing about it is that it is split by **cost**, not by topic. The
first group rebuilds `h0`, so each of its widgets reports a change, and any
change sets `m_spectrumDirty` for the next `Record`. Dragging a spectrum slider
re-runs the spectrum pass every frame of the drag, which is one dispatch and
cheap, but it is not free, and it reseeds nothing: the same seed gives the same
random numbers, so the sea changes shape smoothly as the wind changes. The
second group is read by the per-frame passes and costs nothing to change.

"Clock" shows the time the shaders see. With a loop period set, it counts up to
the period and wraps to 0, and section 8's rounding is what makes that wrap
invisible.

`Update` calls it after the preview's panel, and before the clock moves on:

```cpp
    drawPreviewPanel(m_settings, reinterpret_cast<ImTextureID>(m_previewTexture));
    m_spectrumDirty |= drawOceanPanel(m_settings, PackParameters().time);
    m_time += input.deltaSeconds * m_settings.timeScale;
```

`Update` runs before the frame's fence wait (Chapter 09 section 9), so it only
edits CPU state; `Record` packs it and records the work.

---

## 12. The frame, in order, and what comes next

`Record` is now complete; Appendix A prints it whole. Read top to bottom, its
numbered comments are the chapter:

1. the return trips — last frame's compute, the two maps from the surface, the
   preview from ImGui — then the ocean's set and constants bound;
2. the spectrum, if a setting changed (section 7);
3. this moment's waves, or the test wave (sections 6 and 8);
4. sixteen FFT stages (section 5), then the ocean's set and constants bound
   again;
5. the two maps (section 9);
6. the preview (section 6);
7. the hand-overs: the displacement to the vertex shader, the normals and the
   preview to fragment shaders (sections 6 and 10);
8. the sea, and the scene target handed back (section 10).

Every image is written with a barrier before its first reader and before its
next writer. Nothing waits on the swapchain: all of the compute runs before the
scene pass, so it can run before the swapchain image is even acquired (Chapter
20 section 11).

`Teardown` needs nothing more: section 6 wrote it whole.

### Going faster

At `N = 256` the FFT is sixteen dispatches and sixteen barriers, and each
stage reads and writes two 1 MB images. That is the arrangement to write
first, because every stage's output is an image you can inspect. Once it is
right, two improvements are standard:

- **One workgroup per row, in shared memory.** A workgroup of 128 invocations
  loads a whole row of 256 complex numbers into `shared` memory, runs all eight
  stages there with a `barrier()` between them (Chapter 20 section 6), and
  writes the row once: two dispatches instead of sixteen. Its limits are the
  workgroup size, `N / 2` invocations against a guarantee of 128, and
  `maxComputeSharedMemorySize`, 16 KB guaranteed.
- **Subgroup shuffles.** The last `log2(subgroupSize)` stages pair invocations
  in the same subgroup, and `subgroupShuffleXor` exchanges their values without
  shared memory at all, at the cost of code for each subgroup size the hardware
  may pick (Chapter 20 section 7).

Measure before doing either: timestamps around `RecordFft` (Chapter 21 section
8, or Chapter 24 section 9's `GpuTimestamps`) say what it costs, at `N = 256`
and at `N = 512`, the usual choice on a GPU.

### What the engine could learn from this

The ocean is a chain of compute passes feeding a draw, each with its own
images and barriers, all written by hand. Get it working, and *then* look at
what it needed from the engine: probably a named image whose size and format
the demo chooses, a compute pass with a dispatch size and a parameter block,
and an ordering between passes. That is a small render graph, and it can only
be designed with examples like this in hand — which is why ROADMAP parks it.
The same goes for **timeline semaphores** (core since Vulkan 1.2): with a chain
of compute work feeding graphics, one semaphore with an increasing value
expresses "after step N" more simply than binary semaphores and fences
(Chapter 04 section 3 notes why the tutorial has not needed them). Neither is
needed here, because everything runs on one queue, in order.

### What comes next

Fly up and look down at a 100 m patch, and the sea is a tiled floor: the same
pattern, foam and all, every 100 m (the exit check has you see it). Chapter 30
takes the repeat away with three patches of different sizes, gives the waves a
spectrum measured on real seas, keeps foam where the crests broke, and puts
the engine's sky and clouds in the water.

## Checkpoint

Run `SandboxGame --demo Ocean`. You can now see:

- the sea to a hazy horizon under a pale sky, a glittering path toward the low
  sun, and waves travelling away from you, downwind;
- the "Ocean" panel changing the sea as you drag: the wind and amplitude
  reshape it, choppiness sharpens it, the foam threshold spreads or removes the
  foam, and the colors, sun, and haze change the look;
- the "Ocean preview" showing any stage of it: the spectrum, the height, the
  normals, the foam — and Part 1's test wave, which still works;
- the camera flying anywhere, with the sea following.

---

## When it does not work

| Symptom | Cause |
| --- | --- |
| Entirely black, or NaN everywhere | Division by `\|k\| = 0` at the centre texel — in the Phillips spectrum, or in the displacement's `k / \|k\|` (sections 7 and 8). Guard both. For some seeds only, or on one GPU and not another: Box-Muller's `sqrt(−2 ln u1)` without its `max`, because a GPU's `log` can return a hair above 0 for a `u1` at or just below 1 (section 7). |
| Fine checkerboard of spikes everywhere | The `(−1)^(x + y)` sign is missing after the inverse FFT (section 6). "Skip the sign fix" shows exactly this. |
| Part 1's test wave in the wrong place, or the mirror does not cancel the imaginary part | The FFT itself: a wrong bit reversal, twiddle sign, or `top`/`bottom` pair (section 5). Nothing in Part 2 can be right until Part 1's checkpoint is. |
| Flat surface, no motion | `time` never reaches the shader (`PackParameters`), or the time scale is 0 |
| Correct shape, wrong scale | A missing `2π` in `waveVector`, or the patch size differing between the spectrum and the surface |
| Seams between patches | The sampler is `CLAMP_TO_EDGE`; it must be `REPEAT` (section 10) |
| Mirrored or transposed | The row and column passes swapped, or `direction` inverted |
| Subtly wrong, complex-looking waves | The `conj(h0(−k))` term is missing from `h(k, t)` (section 8) |
| Foam in the troughs, not on the crests | The displacement's sign is flipped: it should be `+i (k / \|k\|) h` with this chapter's transform (section 8) |
| Holes along the crests at high choppiness | Back-face culling on the surface (section 10) |
| Flickers, or differs between runs | A missing barrier between FFT stages. Sync validation finds it (exit check). |
| Correct on the first frame, flickers after | A missing return trip from the surface back to compute (section 10) |
| The sea jumps every few seconds with a loop period set | `ω` not rounded to multiples of `2π / T` (section 8), while the clock wraps |
| `Setup` fails: "six storage images per shader stage" | The device reports fewer than six in `maxPerStageDescriptorStorageImages` (section 4) |

---

## Exit check

- [ ] Rerun `GenerateProjects.bat`, build, and pick **Ocean** in the demo
      picker. Tick "Instead of the ocean": every item of Part 1's checkpoint
      still holds.
- [ ] Untick it and show "Spectrum |h0|": a noisy blob centred on the square,
      spread up and down along the wind, bright above the centre and dim below,
      a dark line across the middle, black at the exact centre. Change the wind
      direction and the blob turns with it.
- [ ] The sea: waves to a hazy horizon with no visible edge, a glittering path
      toward the sun, and waves travelling away from you, downwind. In the
      "Height" preview the bands move up the square.
- [ ] Move "Choppiness" from 0 to 2. In the "Jacobian" preview, black — 1
      everywhere, nothing squeezed — turns to orange and blue with white foam on
      the crests. On the surface, seen from 3 m up looking along the water, the
      crests narrow and foam appears on them.
- [ ] Foam appears on the crests, not uniformly: the white specks of the
      "Jacobian" preview sit on the orange crests of "Height", and on the
      surface the foam is on the wave tops. Raising "Foam threshold" spreads it.
- [ ] Set "Patch size" to 100 and "Patches each side" to 4, fly up to 400 m,
      and look straight down: the same pattern, foam specks and all, repeats
      every 100 m in a grid, with no seam where the patches meet.
- [ ] Set "Loop period" to 10: "Clock" counts to 10 and wraps to 0 without the
      sea jumping. (Delete the `floor` line in `OceanAnimate.comp.glsl` and it
      jumps at every wrap; put it back.)
- [ ] The same at 4x MSAA (Chapter 18's picker), and after resizing the window.
- [ ] Synchronization validation, with the shader-access setting on (Chapter 20
      section 5), is silent through all of the above, through switching to
      another demo and back — which keeps the settings and the camera — and
      quitting reports no leaked VMA allocation.
- [ ] **Positive control.** Delete the `computeToComputeBarrier(commandBuffer)`
      in `RecordFft`'s loop. The first frame must report
      `SYNC-HAZARD-READ-AFTER-WRITE` on a `vkCmdDispatch`: a stage reading the
      image the previous stage wrote. If it reports nothing, the shader-access
      setting is off, and every "silent" above proves nothing. Restore the
      barrier.
- [ ] **A second control, for the surface.** In `Record`'s step 7, change the
      displacement map's destination stage from `VERTEX_SHADER` to
      `FRAGMENT_SHADER`. It must report `SYNC-HAZARD-READ-AFTER-WRITE` on the
      `vkCmdDraw`, saying the access must be allowed at `VERTEX_SHADER`. Put it
      back.

## Sources

- Jerry Tessendorf, "Simulating Ocean Water", SIGGRAPH course notes (1999;
  revised editions through 2004): the spectrum, `h(k, t)` with the conjugate term, the
  dispersion relation and the loop period, the choppy displacement, and the
  Jacobian for foam.
- J. W. Cooley and J. W. Tukey, "An Algorithm for the Machine Calculation of
  Complex Fourier Series", *Mathematics of Computation* 19 (1965): the FFT.
- G. E. P. Box and M. E. Muller, "A Note on the Generation of Random Normal
  Deviates", *Annals of Mathematical Statistics* 29 (1958).
- Christophe Schlick, "An Inexpensive BRDF Model for Physically-based
  Rendering", *Computer Graphics Forum* 13 (1994): the Fresnel approximation.
- The Beaufort wind scale's table of probable wave heights, for the size of a
  12 m/s sea.

## Appendix A — `Setup` and `Record`, whole

Reference: the two functions sections 3 to 10 built up, as they stand at the
end.

```cpp
InitializationResult OceanDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }
    if (auto result = CreateImages(); !result)           { return result; }   // section 4
    if (auto result = CreateDescriptors(); !result)      { return result; }   // section 4
    if (auto result = CreateComputePipelines(); !result) { return result; }   // sections 5-9
    if (auto result = CreateSurface(); !result)          { return result; }   // section 10

    // ImGui draws the preview through a descriptor set of its own (Chapter 07
    // section 2), made for the layout the image will be in when ImGui draws it.
    m_previewTexture = ImGui_ImplVulkan_AddTexture(m_preview.view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
    m_spectrumDirty  = true;   // h0 holds garbage until the spectrum pass has run
    return InitializationResult::success();
}
```

```cpp
void OceanDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const OceanParameters parameters    = PackParameters();
    const uint32_t        groups        = groupCount(FFT_SIZE, OCEAN_GROUP_SIZE);

    // 1. Return trips. Last frame's dispatches finish before this frame's write
    //    over what they read and wrote; the three sampled images come back from
    //    their readers to GENERAL. UNDEFINED: every texel is about to be rewritten.
    computeToComputeBarrier(commandBuffer);
    transitionImage(commandBuffer, m_displacement.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    transitionImage(commandBuffer, m_normals.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // Every pass but the FFT binds the ocean's set and reads OceanParameters.
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_oceanLayout,
                            0, 1, &m_oceanSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_oceanLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);

    // 2. Section 7: the starting waves, only after a spectrum setting changed.
    if (m_spectrumDirty)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_spectrumPipeline);
        vkCmdDispatch(commandBuffer, groups, groups, 1);
        computeToComputeBarrier(commandBuffer);
        m_spectrumDirty = false;
    }

    // 3. The FFT's input: this moment's ocean (section 8), or Part 1's test wave.
    if (m_settings.testWave)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_testWavePipeline);
    }
    else
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_animatePipeline);
    }
    vkCmdDispatch(commandBuffer, groups, groups, 1);
    computeToComputeBarrier(commandBuffer);

    // 4. Section 5: the inverse FFT, in place as far as anyone outside can tell.
    RecordFft(commandBuffer);

    // The FFT's layout is not the ocean's, so its binds displaced the ocean's set
    // and push constants: bind them again.
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_oceanLayout,
                            0, 1, &m_oceanSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_oceanLayout, VK_SHADER_STAGE_COMPUTE_BIT,
                       0, sizeof(parameters), &parameters);

    // 5. Section 9: unpack into the two maps the surface samples.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_assemblePipeline);
    vkCmdDispatch(commandBuffer, groups, groups, 1);
    computeToComputeBarrier(commandBuffer);

    // 6. Section 6: the panel's picture of whichever image it asks for.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_previewPipeline);
    vkCmdDispatch(commandBuffer, groups, groups, 1);

    // 7. Hand the three sampled images to the stages that sample them: the
    //    displacement to the surface's vertex shader, the normals to its
    //    fragment shader, the preview to ImGui's fragment shader.
    transitionImage(commandBuffer, m_displacement.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    transitionImage(commandBuffer, m_normals.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    transitionImage(commandBuffer, m_preview.image,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

    // 8. Section 10: the sea, then the scene target goes back to the engine.
    RecordSurface(commandBuffer, frame, parameters);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

## Appendix B — The set-up functions, whole

Code to type in: the functions sections 4, 5, and 10 describe in part, because
most of each repeats a pattern of Chapter 20 or Chapter 10. The sections say
what in them is this chapter's own.

**`createOceanImage`** (section 4), a `static` function in the namespace,
before `destroyOceanImage`:

```cpp
// Section 4. One FFT_SIZE x FFT_SIZE image and its view. False if either fails.
static bool createOceanImage(VulkanContext& vulkan, VkFormat format, uint32_t size,
                             VkImageUsageFlags usage, OceanImage& image)
{
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = format,
        .extent        = { size, size, 1 },
        .mipLevels     = 1,
        .arrayLayers   = 1,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = usage,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{
        .usage = VMA_MEMORY_USAGE_AUTO,
    };
    if (vmaCreateImage(vulkan.allocator, &imageInfo, &allocationInfo,
                       &image.image, &image.allocation, nullptr) != VK_SUCCESS)
    {
        return false;
    }

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = image.image,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 },
    };
    return vkCreateImageView(vulkan.device, &viewInfo, nullptr, &image.view) == VK_SUCCESS;
}
```

**`CreateDescriptors`** (section 4):

```cpp
InitializationResult OceanDemo::CreateDescriptors()
{
    // The ocean's set holds six storage images, and Vulkan guarantees only four
    // per shader stage. Every desktop GPU has thousands; ask rather than assume.
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &properties);
    if (properties.limits.maxPerStageDescriptorStorageImages < 6)
    {
        return InitializationResult::failure("The ocean needs six storage images per shader stage.");
    }

    // Every binding is a storage image, read or written by compute. The FFT's set
    // uses the first four bindings, the ocean's set all six.
    std::array<VkDescriptorSetLayoutBinding, 6> bindings{};
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
    layoutInfo.bindingCount = 6;
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_oceanSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the ocean.");
    }

    // Three sets: the FFT's two, and the ocean's one. 4 + 4 + 6 storage images.
    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_IMAGE, 4 + 4 + 6 };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 3,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_descriptorPool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the ocean.");
    }

    const VkDescriptorSetLayout layouts[] = { m_fftSetLayout, m_fftSetLayout, m_oceanSetLayout };
    VkDescriptorSet             sets[3]{};
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_descriptorPool,
        .descriptorSetCount = 3,
        .pSetLayouts        = layouts,
    };
    if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, sets) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the ocean.");
    }
    m_fftSets  = { sets[0], sets[1] };
    m_oceanSet = sets[2];

    // Every descriptor is a storage image in GENERAL; only the set, the binding,
    // and the image differ. The infos live until vkUpdateDescriptorSets returns.
    std::array<VkDescriptorImageInfo, 14> infos{};
    std::array<VkWriteDescriptorSet, 14>  writes{};
    uint32_t count = 0;
    const auto add = [&](VkDescriptorSet set, uint32_t binding, const OceanImage& image) {
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

    // FFT set s reads copy s of A and B and writes copy 1 - s: the ping-pong is
    // two sets built once, never an update per dispatch (Chapter 20 section 4).
    for (uint32_t s = 0; s < 2; ++s)
    {
        add(m_fftSets[s], 0, m_spectrumA[s]);
        add(m_fftSets[s], 1, m_spectrumB[s]);
        add(m_fftSets[s], 2, m_spectrumA[1 - s]);
        add(m_fftSets[s], 3, m_spectrumB[1 - s]);
    }
    add(m_oceanSet, 0, m_h0);
    add(m_oceanSet, 1, m_spectrumA[0]);   // the FFT's input, and its output (section 5)
    add(m_oceanSet, 2, m_spectrumB[0]);
    add(m_oceanSet, 3, m_displacement);
    add(m_oceanSet, 4, m_normals);
    add(m_oceanSet, 5, m_preview);
    vkUpdateDescriptorSets(m_context.vulkan.device, count, writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

**`CreateComputePipelines`**, as Part 1 has it (section 5). Sections 7, 8, and
9 each add a row to `passes`:

```cpp
InitializationResult OceanDemo::CreateComputePipelines()
{
    // Two layouts. The FFT binds its own set and pushes 8 bytes; every other
    // pass binds the ocean's set and pushes OceanParameters.
    const VkPushConstantRange fftRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(FftParameters),
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

    const VkPushConstantRange oceanRange{
        .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT,
        .offset     = 0,
        .size       = sizeof(OceanParameters),
    };
    const VkPipelineLayoutCreateInfo oceanLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &m_oceanSetLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &oceanRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &oceanLayoutInfo, nullptr, &m_oceanLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the ocean.");
    }

    const struct
    {
        VkPipeline*      pipeline;
        const char*      shader;
        VkPipelineLayout layout;
    } passes[] = {
        { &m_fftPipeline,      "Ocean/FftStage.comp.spv",      m_fftLayout },     // section 5
        { &m_testWavePipeline, "Ocean/FftTestWave.comp.spv",   m_oceanLayout },   // section 6
        { &m_previewPipeline,  "Ocean/OceanPreview.comp.spv",  m_oceanLayout },   // section 6
    };
    for (const auto& pass : passes)
    {
        *pass.pipeline = createComputePipeline(m_context.vulkan.device, m_context.pipelineCache,
                                               pass.shader, pass.layout);
        if (*pass.pipeline == VK_NULL_HANDLE)
        {
            return InitializationResult::failure("Creating an ocean compute pipeline failed.");
        }
    }
    return InitializationResult::success();
}
```

**`CreateSurface`** (section 10):

```cpp
InitializationResult OceanDemo::CreateSurface()
{
    // Linear filtering between texels, and REPEAT: the maps tile, so every patch
    // reads the same texels and the edges meet.
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
        return InitializationResult::failure("vkCreateSampler failed for the ocean surface.");
    }

    // Set 1: the displacement for the vertex shader, the normals for the fragment shader.
    const VkDescriptorSetLayoutBinding bindings[] = {
        { .binding         = 0,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT },
        { .binding         = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .descriptorCount = 1,
          .stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT },
    };
    const VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = 2,
        .pBindings    = bindings,
    };
    if (vkCreateDescriptorSetLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_surfaceSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for the ocean surface.");
    }

    const VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 2 };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = 1,
        .poolSizeCount = 1,
        .pPoolSizes    = &poolSize,
    };
    if (vkCreateDescriptorPool(m_context.vulkan.device, &poolInfo, nullptr, &m_surfacePool) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorPool failed for the ocean surface.");
    }
    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = m_surfacePool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_surfaceSetLayout,
    };
    if (vkAllocateDescriptorSets(m_context.vulkan.device, &allocateInfo, &m_surfaceSet) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkAllocateDescriptorSets failed for the ocean surface.");
    }

    // The layout the maps are in while the surface draws: Record moves them there.
    const VkDescriptorImageInfo maps[] = {
        { .sampler = m_sampler, .imageView = m_displacement.view, .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { .sampler = m_sampler, .imageView = m_normals.view,      .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
    };
    const VkWriteDescriptorSet writes[] = {
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_surfaceSet,
          .dstBinding      = 0,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .pImageInfo      = &maps[0] },
        { .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
          .dstSet          = m_surfaceSet,
          .dstBinding      = 1,
          .descriptorCount = 1,
          .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
          .pImageInfo      = &maps[1] },
    };
    vkUpdateDescriptorSets(m_context.vulkan.device, 2, writes, 0, nullptr);

    // Set 0 is the scene renderer's camera (Chapter 10 section 7), set 1 the maps;
    // both shaders read OceanParameters.
    const VkDescriptorSetLayout setLayouts[] = { m_sceneRenderer.FrameSetLayout(), m_surfaceSetLayout };
    const VkPushConstantRange   pushRange{
        .stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(OceanParameters),
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
        return InitializationResult::failure("vkCreatePipelineLayout failed for the ocean surface.");
    }

    // Depth on, like every scene pipeline (Chapter 10 section 9), at the scene's
    // sample count (Chapter 18). No culling: where a crest folds over, its
    // triangles face down, and culling them would punch holes in the crest.
    const GraphicsPipelineDesc desc{
        .vertexShader   = "Ocean/OceanSurface.vert.spv",
        .fragmentShader = "Ocean/OceanSurface.frag.spv",
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
        return InitializationResult::failure("Creating the ocean surface pipeline failed.");
    }
    return InitializationResult::success();
}
```

Next: [30 — A Rougher Sea](30-A-Rougher-Sea.md)
