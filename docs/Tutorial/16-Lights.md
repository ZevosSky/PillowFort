# 16 — Lights

**Goal:** a USD file's lights — a sun, point and spot lights, rectangular and
disk panels, a sky — light the scene: imported as nodes, edited live in the
inspector, uploaded every frame into a light buffer the mesh shader loops over,
and brought onto the screen by an exposure control and a tone curve instead of
clipping to white.

**ROADMAP:** step 17.

**Module:**

- `Source/PillowFort/Scene/`, `pf::scene` — `Light` (a node component, plain
  data), `LightItem` (one light resolved to world space), and the scene's light
  list. Vulkan-free.
- `Source/PillowFort/UsdImport/UsdImport.cpp`, `pf::usd_import` — UsdLux prims
  to lights.
- `Source/PillowFort/VulkanGraphics/`, `pf::vulkan_graphics` — `SceneRenderer`'s
  light buffer at set 0 binding 1, and `VulkanRenderer`'s composite pass, which
  gains exposure and a tone curve.

Shaders: `Shaders/Include/Lights.glsl` (new), `Shaders/Scene/Mesh.frag.glsl`
(the light loop), `Shaders/Composite/Composite.frag.glsl` (tone mapping).

**Math:** taught here — solid angle, and the four light quantities it connects:
radiance, irradiance, radiant intensity, and power (section 2); the
inverse-square law (section 2); a smooth window to zero at a light's range,
and `smoothstep` for a spot's edge (section 5); exposure in stops, powers of
two (section 6). Assumed: Chapter 15 section 9's radiance, irradiance, and
Lambert's 1/π, the dot product as a cosine, and `exp2`.

**Prerequisites:**

- Chapter 07 sections 9 and 10 — a settings struct with its own panel
  function, the shape `ToneMappingSettings` copies.
- Chapter 08 sections 4, 5, 6, and 8 — the composite pass this chapter grows,
  push constants, the per-frame-copies rule, and `std430`.
- Chapter 09 — the demo's `Update`/`Record` split: lights are gathered in
  `Record`, after the frame's fence wait.
- Chapter 10 — `SceneRenderer`'s set 0 (`CreateFrameResources`,
  `WriteFrameData`), which gains binding 1; section 2's projection and divide
  by w, which the light gizmos repeat on the CPU; and section 7's rule that
  host writes made before `vkQueueSubmit2` need no barrier.
- Chapter 11 — the sun and ambient color in `FrameData`, which this chapter
  replaces as the source of light, and section 14's `ColorSpace.h`, for the
  inspector's color swatch.
- Chapter 12 — `Scene`, `Node`, `CollectDraws`, and the inspector
  (`drawNodeInspector`).
- Chapter 14 — `UsdImport.cpp`'s `importPrim` dispatch and `asXformable`, and
  the file node that converts the stage's axes and units.
- Chapter 15 sections 9 and 11 — `evaluatePreviewSurface` and its BRDF switch,
  which this chapter calls once per light; the mesh fragment shader; and
  section 9's radiance, irradiance, and "a sky lights a surface with π times
  its radiance".

---

## What you are actually writing

The route a light takes is the material's from Chapter 15, with one
difference: a light is **re-gathered every frame**, because moving it — or the
node above it — must move the light.

```text
 USD file                UsdImport.cpp (section 3)          Scene (section 2)
 DistantLight ─┐
 SphereLight  ─┼──▶ importLight ──▶ scene::Light, on a node ──┐  authored values,
 RectLight    ─┤                                              │  in the light's own space
 DiskLight    ─┤                                              │
 DomeLight    ─┘                                              ▼
 ──────────────────────────────────────── every frame, in the demo's Record ───────────
   Scene::CollectLights ──▶ resolveLight(light, node.world) ──▶ LightItem[] + ambient
   SceneRenderer::WriteLights ──▶ this frame's light buffer (section 4), set 0 binding 1
 ───────────────────────────────────────────────────────────────────────────────────────
 Mesh.frag.glsl (section 5): for each light, evaluatePreviewSurface; plus the ambient
 Composite.frag.glsl (section 6): exposure, tone curve, encode
```

The files, and what each section adds:

```text
Scene/Light.h/.cpp          LightType, Light, LightItem, resolveLight,              section 2
                            colorTemperatureToRgb
Scene/Scene.h/.cpp          Node::light, AddLight, SetLight, GetLight,              section 2
                            LightCount, CollectLights
UsdImport/UsdImport.cpp     importLight, domeTextureAverage, the dispatch branch,   section 3
                            asXformable's light types
Shaders/Include/SharedShaderTypes.h   LightData, LightBufferHeader, ToneMapping     sections 4, 6
VulkanGraphics/SceneRenderer.h/.cpp   binding 1, m_lightBuffers, WriteLights        section 4
Shaders/Include/Lights.glsl           the buffer, lightIrradiance                   section 5
Shaders/Scene/Mesh.frag.glsl          the light loop                                section 5
Shaders/Composite/Composite.frag.glsl exposure and tone curve                       section 6
VulkanGraphics/ToneMapping.h/.cpp     ToneMappingSettings, drawToneMappingPanel     section 6
VulkanGraphics/VulkanRenderer.h/.cpp  push constant, m_toneMapping                  section 6
Scene/ScenePanels.cpp                 the light inspector, drawLightGizmos          section 7
Demos/UsdViewer, Meshes, SceneGraph   WriteLights in Record                         sections 4, 7
```

### What `SceneRenderer` gains

```cpp
// Source/PillowFort/VulkanGraphics/SceneRenderer.h - Chapter 16's additions. The header gains
// #include "PillowFort/Scene/Light.h" (LightItem) and <optional>; SceneRenderer.cpp gains <algorithm>.
inline constexpr uint32_t MAX_LIGHTS = 256;   // per frame; more are dropped with a warning

class SceneRenderer
{
public:
    // ...Chapters 10, 11, and 15 unchanged...

    // In Record only, after the frame's fence wait - like WriteFrameData. Fills this frame's
    // light buffer: `lights` in order (the first Distant one becomes the sun, section 4),
    // `ambient` as the constant light from every direction.
    void WriteLights(uint32_t frameIndex, std::span<const scene::LightItem> lights, glm::vec3 ambient);

    // The direction the sun's light travels (world, unit) as WriteLights last wrote it for this
    // frame slot, or nullopt when the list had no Distant light. Chapter 17 fits its shadow
    // cascades to it, after WriteLights in the same Record.
    std::optional<glm::vec3> SunDirection(uint32_t frameIndex) const { return m_sunDirection[frameIndex]; }

private:
    // Chapter 16: binding 1, one buffer per frame in flight, persistently mapped.
    std::array<AllocatedBuffer, FRAMES_IN_FLIGHT>          m_lightBuffers;
    std::array<std::optional<glm::vec3>, FRAMES_IN_FLIGHT> m_sunDirection{};
    bool                                                   m_warnedTooManyLights = false;
};
```

> **Jump:** until now everything the GPU read about the scene was either fixed
> at load (meshes, materials) or one small block rewritten per frame
> (`FrameData`). Lights are a **variable-length list** rewritten every frame —
> how many depends on the scene, and which are visible changes as you edit it.
> That is a different kind of data, and it gets a different kind of buffer: a
> *storage* buffer with a count at the front, which the shader loops over.
> Keep the shape in mind — a header, then an array — because Chapter 19's
> instance buffer and Chapter 21's particles are the same idea at larger
> scale.

---

## 1. UsdLux, and what each light becomes here

A USD light is a prim with UsdLux's `LightAPI`. It has a transform like any
other prim, and **emits along its local −Z axis** — the same convention as a
USD camera, which looks down −Z. Its common inputs:

| Input | Default | Meaning |
| --- | --- | --- |
| `intensity` | 1 | Brightness, in nits: a light of intensity 1 seen head-on produces a pixel value of 1.0 at exposure 0 |
| `exposure` | 0 | More brightness, in stops: the light is `intensity × 2^exposure` |
| `color` | (1, 1, 1) | Linear RGB, multiplying the above |
| `enableColorTemperature`, `colorTemperature` | off, 6500 | A blackbody tint in kelvin, multiplying `color`; 6500 is white |
| `normalize` | off | Divide by the light's size, so resizing it keeps its total power (section 2) |
| `diffuse`, `specular` | 1 | Non-physical multipliers on each lobe — not implemented here |

And the types, with what this renderer does with each:

| Type | What it is | Here |
| --- | --- | --- |
| `DistantLight` | A light infinitely far away, along −Z: the sun. `angle` is its angular diameter, 0.53° for the real sun | **Directional light.** Its angle only changes its brightness through `normalize`; soft shadows are Chapter 17's business |
| `SphereLight` | A glowing ball of `radius`. `treatAsPoint` is a hint that it can be shaded as a point | **Point light** with inverse-square falloff, the radius keeping it finite up close. With `ShapingAPI` — which is how Blender exports a spot — **a spot light** |
| `RectLight` | A `width` × `height` rectangle emitting from its −Z face | **Approximated** as a point at its centre emitting mostly forward (section 5). The right answer, LTC, is named there |
| `DiskLight` | A disk of `radius`, the same | The rect light's approximation, with the disk's area |
| `DomeLight` | Light from an infinitely distant sphere around everything: a sky, or an HDR environment image | **Constant ambient light**: its color, times the average of its image. A sky you can see is Chapter 23's; its light by direction, reflections included, is Chapter 24's |
| `CylinderLight`, `GeometryLight`, `PortalLight` | — | Skipped with a warning |

`ShapingAPI` — an API schema a light can have applied — narrows a light into a
cone: `shaping:cone:angle` is the cone's half-angle in degrees,
`shaping:cone:softness` the fraction of it that fades. Its focus and IES
profile inputs are not implemented.

---

## 2. Light units, and lights as scene data

> **Jump:** until now a color was a number from 0 to 1, and white meant 1. From
> here, light values are physical and unbounded: a lamp-lit floor reflects 2.2,
> and sunshine delivers 100000 lux. The numbers stop meaning "how bright on
> screen" and start meaning "how much light", and the screen becomes a camera
> that needs an exposure to turn one into the other — section 6 gives it one.
> Until then, expect a correctly lit scene to clip to white.

### What `intensity` measures

UsdLux defines its units by what a camera sees, which is what makes them
usable: **a light of intensity 1 and exposure 0, seen head-on, produces a pixel
value of 1.0.** Formally that is 1 nit of luminance: how bright the light's
surface looks. The shader does not need that, though. It needs how much light
*arrives* at the surface it is shading, and getting from one to the other is a
little geometry built on one idea, the solid angle.

A **solid angle** is to a sphere what an angle is to a circle: how much of your
surroundings something covers, measured as the area it covers on a sphere of
radius 1 around you. The whole sky around you is 4π (the unit sphere's area);
the half above a floor is 2π; and a ball of radius *r* at distance *d* covers
about π*r*² / *d*² — its silhouette, a disc of area π*r*², shrunk by the
distance squared:

```text
    ball, radius r                                  shaded point, inside a sphere of radius 1
       .---.                                           .---.
      /     \ ─────────── light from the ball ──────▶ / ▓   \
      \     / ───────────────────────────────────────▶\ ▓ ● /
       '---'                                           '---'
      |◀─────────────────────── d ────────────────────────▶|

   ▓: the patch of the unit sphere the ball covers. Its area, about π r² / d², is
      the ball's solid angle: the silhouette's area, π r², shrunk by the distance squared.
```

Four quantities follow, under two sets of names. Photometry (nits, lux,
candelas) weighs light by how bright it looks to an eye; radiometry (radiance,
irradiance, watts) by its power. USD, and this chapter, use either word for the
same RGB numbers:

| Quantity | Plain meaning | Unit here | Who uses it |
| --- | --- | --- | --- |
| luminance / radiance | how bright a surface looks, from one direction | nit | `intensity`; the pixel |
| irradiance (illuminance) | how much light arrives on a surface | lux | distant lights; the BRDF's *E* (Chapter 15 section 9) |
| radiant intensity | what a small source sends in one direction | candela | sphere, rect, and disk lights |
| power | all the light a source sends out | watt | Blender's lamps only (section 8) |

Two relations connect them, and both are the solid angle at work:

- **Radiance to irradiance.** A source of radiance *L* covering a small solid
  angle Ω, straight ahead, delivers *E* = *L* Ω.
- **Radiant intensity to irradiance.** A small source of intensity *I*
  delivers *E* = *I* / *d*² to a surface facing it at distance *d* — the
  inverse-square law: the same light spread over a sphere whose area grows as
  *d*².

The shader wants irradiance from a distant light, and radiant intensity from a
local one, because it divides by *d*² itself. So `resolveLight` converts each
light's authored radiance into one of those two.

**A sphere of radius r and luminance L**, seen from far away, covers a solid
angle of π r² / d², so it delivers `E = L π r² / d²` — which is `I / d²` with
`I = L π r²`. The radiant intensity of a sphere light is its luminance times
its silhouette's area. Worked: a bulb of radius 5 cm and intensity 1000,
without `normalize` (which comes next), has `I = 1000 × π × 0.05² = 7.9`, and a
floor 2 m below it receives 7.9 / 4 = 2.0.

**`normalize`** divides the luminance by the light's surface area — 4π r² for
a sphere — "so that the power of the light remains constant while altering
its size". With it on, `I = (intensity / 4π r²) × π r² = intensity / 4`,
independent of the radius. This matters in practice: **Blender exports every
light with `normalize = 1`**, so a Blender point light's intensity does not
depend on its radius, as in Blender.

**A dome** of luminance L lights a surface from a whole hemisphere. Adding up
that half-sky, each direction weighted by the cosine at which it arrives, gives
an irradiance of πL — the same sum Chapter 15 section 9 does to explain
Lambert's 1/π — and a matte surface reflects `albedo / π × πL = albedo × L`.
That is exactly what Chapter 11 called the ambient color, so the dome's
luminance *is* the ambient term.

**Next to a sphere light** the same fact sets a limit. When the shaded point is
closer than the radius, `I / d²` blows up, but the true answer stops growing:
right at an emitter you see half a sky of luminance L, which delivers πL — and
that is `I / r²`. So **clamping the distance to at least the radius** gives the
physically right limit for free. And a sphere of radius zero without
`normalize` has no surface, so it emits nothing — USD's own math says so. The
importer warns about such a light rather than inventing a brightness for it.

**The other three types** follow the same pattern, one line each in the table
below. A rectangle or disk of area A emits `I = L A` along its axis, falling
off as the cosine of the angle off the axis: it is a flat emitter, and edge-on
it has no area. A distant light of angular diameter θ is a disc of sky so
small that all of it arrives at nearly the same angle, so what it delivers is
`L` times its solid angle, about π (θ/2)² for a small θ; `π sin²(θ/2)` is the
exact form — the solid angle with each part weighted by the cosine at which it
arrives — that stays right all the way up to a hemisphere. So
`E = L π sin²(θ/2)`. With
`normalize`, a rect or disk has `I = intensity`, and a distant light
`E = intensity` exactly — "intensity becomes a measure of the illuminance,
expressed in lux". That is why USD's schema gives `DistantLight` a default
intensity of **50000**: 50000 nits over the sun's 0.53° is an irradiance of
about 3.4.

All of this goes into one function, `resolveLight`, below. Here is the table it
implements:

| Type | The shader receives | normalize off | normalize on |
| --- | --- | --- | --- |
| Distant | irradiance E | `I0 × π sin²(angle/2)` | `I0` |
| Sphere | radiant intensity I | `I0 × π r²` | `I0 / 4` |
| Rect | intensity along its axis | `I0 × w h` | `I0` |
| Disk | intensity along its axis | `I0 × π r²` | `I0` |
| Dome | ambient luminance | `I0 × image average` | (ignored, per UsdLux) |

where `I0 = intensity × 2^exposure × color × temperature tint`, and r, w, h
are in **world** metres — a light under a scaled node is a bigger light.

### How bright is that on screen?

Not "between 0 and 1". A Blender 1000 W point light exports as intensity 318,
which is `I = 79.6`; a white floor 3 m below it receives `E = 8.8` and reflects
`0.8 × 8.8 / π ≈ 2.2` — more than twice what the display can show. A real
sunny day is around 100000 lux. Light values are physical, and physical light
covers a range no display has. Chapter 08's composite pass clamps everything
above 1 to white, which is right for a triangle and wrong for a scene lit
like this one: section 6 gives the composite pass a camera's two tools,
**exposure** and a **tone curve**.

### Color temperature

Blender writes `enableColorTemperature = 1` on every light it exports, with its
light's temperature setting — so a "warm" 2700 K Blender lamp arrives as white
light with a temperature, not as an orange color. The tint is the color of a
*blackbody* — an ideal glowing object, like a heated filament — at that
temperature: deep red at 1000 K, orange around 2700 K
(incandescent), white at 6500 K (daylight, by definition here), blue above.

The next two functions are a published curve fit, worth treating as a black
box: kelvin in, an RGB tint out, normalized so that 6500 K is white and the
tint changes the light's color, not its brightness. The fit's source is in the
code's comment. The output multiplies `color`.

```cpp
// Source/PillowFort/Scene/Light.cpp - file scope, above the namespace block. The chromaticity
// (x, y) of a blackbody at `kelvin`: Kang et al. 2002's fit to the Planckian locus, valid
// 1667 K to 25000 K.
static glm::vec2 planckianChromaticity(float kelvin)
{
    const double t  = std::clamp(static_cast<double>(kelvin), 1667.0, 25000.0);
    const double t2 = t * t;
    const double t3 = t2 * t;
    const double x  = t <= 4000.0
        ? -0.2661239e9 / t3 - 0.2343589e6 / t2 + 0.8776956e3 / t + 0.179910
        : -3.0258469e9 / t3 + 2.1070379e6 / t2 + 0.2226347e3 / t + 0.240390;
    const double x2 = x * x;
    const double x3 = x2 * x;
    const double y  = t <= 2222.0 ? -1.1063814 * x3 - 1.34811020 * x2 + 2.18555832 * x - 0.20219683
                    : t <= 4000.0 ? -0.9549476 * x3 - 1.37418593 * x2 + 2.09137015 * x - 0.16748867
                    :                3.0817580 * x3 - 5.87338670 * x2 + 3.75112997 * x - 0.37001483;
    return glm::vec2(static_cast<float>(x), static_cast<float>(y));
}

// File scope, above the namespace block. Chromaticity at luminance 1 -> linear Rec. 709 (sRGB's
// primaries, D65 white): xyY -> XYZ, then the standard XYZ -> RGB matrix.
static glm::vec3 chromaticityToLinearRgb(glm::vec2 xy)
{
    const glm::vec3 xyz(xy.x / xy.y, 1.0f, (1.0f - xy.x - xy.y) / xy.y);
    return glm::vec3( 3.2404542f * xyz.x - 1.5371385f * xyz.y - 0.4985314f * xyz.z,
                     -0.9692660f * xyz.x + 1.8760108f * xyz.y + 0.0415560f * xyz.z,
                      0.0556434f * xyz.x - 0.2040259f * xyz.y + 1.0572252f * xyz.z);
}
```

```cpp
// Light.cpp, inside namespace pf::scene.
glm::vec3 colorTemperatureToRgb(float kelvin)
{
    const glm::vec3 white = chromaticityToLinearRgb(planckianChromaticity(6500.0f));
    const glm::vec3 tint  = glm::max(chromaticityToLinearRgb(planckianChromaticity(kelvin)) / white,
                                     glm::vec3(0.0f));
    const float luminance = glm::dot(tint, glm::vec3(0.2126f, 0.7152f, 0.0722f));   // Rec. 709 luma
    return tint / luminance;
}
```

At 2700 K that gives (1.87, 0.83, 0.19) — the orange of a tungsten bulb at the
same brightness. USD's own implementation interpolates a table instead; the
two agree to within what you could see.

### `Light`, the component

The component keeps what the file said, in the light's own space, exactly as
`Material` keeps UsdPreviewSurface's inputs. That is what the inspector edits,
and editing the authored values — "intensity", "radius" — is what makes it
feel like editing the scene rather than editing a shader.

```cpp
// Source/PillowFort/Scene/Light.h
#pragma once

#include <glm/glm.hpp>

#include <cstdint>

namespace pf::scene {

enum class LightType : uint32_t { Distant = 0, Sphere = 1, Rect = 2, Disk = 3, Dome = 4 };

// A UsdLux light, as authored: the node's transform places it, and it emits along the
// node's local -Z. Lengths are in the light's local units; resolveLight scales them by the
// node's world scale.
struct Light
{
    LightType type      = LightType::Sphere;
    glm::vec3 color     { 1.0f };      // linear
    float     intensity = 1.0f;        // nits
    float     exposure  = 0.0f;        // stops: brightness * 2^exposure
    bool      normalize = false;       // divide by the light's size (section 2)
    bool      enableColorTemperature = false;
    float     colorTemperature       = 6500.0f;   // kelvin; 6500 is white

    float angle  = 0.53f;              // Distant: angular diameter, degrees
    float radius = 0.5f;               // Sphere, Disk
    float width  = 1.0f;               // Rect, local X
    float height = 1.0f;               // Rect, local Y

    bool  shaping      = false;        // ShapingAPI: a cone
    float coneAngle    = 90.0f;        // half-angle, degrees
    float coneSoftness = 0.0f;         // fraction of the cone that fades, 0-1

    glm::vec3 domeTextureAverage{ 1.0f };   // Dome: the image's mean, multiplying color

    float range = 0.0f;                // where the light's reach ends, metres; 0 = automatic
};

// One light resolved to world space and to the quantities the shader uses (section 2's table).
// Plain data, so a demo without a Scene can build one by hand.
struct LightItem
{
    LightType type      = LightType::Distant;
    glm::vec3 position  { 0.0f };               // world; unused by Distant
    glm::vec3 direction { 0.0f, -1.0f, 0.0f };  // world, unit: the way the light travels (node -Z)
    glm::vec3 emission  { 0.0f };               // Distant: irradiance. Sphere: radiant intensity.
                                                // Rect, Disk: intensity along `direction`. Dome: luminance
    float     radius    = 0.0f;                 // Sphere: radius. Rect, Disk: sqrt(area / pi)
    float     range     = 0.0f;                 // the falloff window's end; unused by Distant
    float     cosOuter  = -2.0f;                // spot cone, as cosines: -2 and -1 mean "no cone"
    float     cosInner  = -1.0f;
};

LightItem resolveLight(const Light& light, const glm::mat4& world);
glm::vec3 colorTemperatureToRgb(float kelvin);   // linear Rec. 709 tint, luminance 1, white at 6500 K

} // namespace pf::scene
```

**`range`** is not a UsdLux input. A physical point light lights the whole
universe, just very weakly far away, and a forward renderer that loops over
every light for every pixel pays for that. A range bounds it — the light's
contribution is faded smoothly to zero there (section 5) — and Chapter 22,
which sorts lights into screen tiles, needs it to know which tiles a light
touches. Automatic means "where the irradiance falls to 0.01", which is a
few hundredths of a display unit after a white surface reflects it.

**This is `resolveLight`** — section 2's table, plus the cone and the range. The
node's world matrix supplies position (column 3), direction (−column 2,
normalized, because world matrices can carry a scale: Chapter 14's file node
scales a centimetre stage by 0.01), and the scale that lengths are multiplied
by.

```cpp
// Light.cpp, inside namespace pf::scene. Includes Light.h, <glm/gtc/constants.hpp>, <algorithm>,
// and <cmath>.
LightItem resolveLight(const Light& light, const glm::mat4& world)
{
    const float pi = glm::pi<float>();
    const glm::vec3 scale(glm::length(glm::vec3(world[0])), glm::length(glm::vec3(world[1])),
                          glm::length(glm::vec3(world[2])));

    glm::vec3 base = light.color * light.intensity * std::exp2(light.exposure);
    if (light.enableColorTemperature) { base *= colorTemperatureToRgb(light.colorTemperature); }

    LightItem item{
        .type      = light.type,
        .position  = glm::vec3(world[3]),
        .direction = glm::normalize(-glm::vec3(world[2])),
    };

    switch (light.type)
    {
    case LightType::Distant:
    {
        // The sun's disk: a cosine-weighted solid angle of pi sin^2(angle / 2), at most a hemisphere.
        const float sinHalf = std::sin(glm::radians(std::clamp(light.angle, 0.0f, 180.0f)) * 0.5f);
        item.emission = (light.normalize || sinHalf == 0.0f) ? base : base * pi * sinHalf * sinHalf;
        return item;   // no position, range, or cone
    }
    case LightType::Sphere:
    {
        const float radius = light.radius * (scale.x + scale.y + scale.z) / 3.0f;
        item.radius   = radius;
        item.emission = light.normalize ? base * 0.25f : base * pi * radius * radius;
        if (light.shaping)
        {
            // Blender's (and Cycles') spot blend: the cone fades over the inner `softness`
            // fraction of its cosine range.
            const float cosOuter = std::cos(glm::radians(std::clamp(light.coneAngle, 0.0f, 180.0f)));
            item.cosOuter = cosOuter;
            item.cosInner = std::max(cosOuter + (1.0f - cosOuter) * light.coneSoftness, cosOuter + 1e-4f);
        }
        break;
    }
    case LightType::Rect:
    {
        const float area = light.width * scale.x * light.height * scale.y;
        item.radius   = std::sqrt(area / pi);
        item.emission = light.normalize ? base : base * area;
        break;
    }
    case LightType::Disk:
    {
        const float radius = light.radius * (scale.x + scale.y) * 0.5f;
        item.radius   = radius;
        item.emission = light.normalize ? base : base * pi * radius * radius;
        break;
    }
    case LightType::Dome:
        item.emission = base * light.domeTextureAverage;   // luminance from every direction
        return item;
    }

    // Automatic range: where I / d^2 falls to 0.01.
    const float strongest = std::max({ item.emission.r, item.emission.g, item.emission.b });
    item.range = light.range > 0.0f ? light.range : std::sqrt(std::max(strongest, 0.0f) / 0.01f);
    return item;
}
```

A distant light's angle of exactly zero means a perfectly parallel light,
which UsdLux defines as having size factor 1 — hence the `sinHalf == 0` case.
The angle is clamped to 180°, a hemisphere of sky; the inspector's slider stops
there too.

### Lights in the scene graph

Lights become a node component, alongside meshes and cameras — Chapter 12's
`Node` reserved the line:

```cpp
// Scene/Scene.h, in struct Node (Chapter 16):
uint32_t light = NO_COMPONENT;   // index into the Scene's lights
```

```cpp
// Scene/Scene.h, added to Scene's public section after the materials (Chapter 16). Written like
// Chapter 12's camera functions. Scene.h gains #include "PillowFort/Scene/Light.h".
uint32_t     AddLight(const Light& light);
void         SetLight(NodeIndex node, uint32_t light);
std::size_t  LightCount() const { return m_lights.size(); }
Light&       GetLight(uint32_t light);
const Light& GetLight(uint32_t light) const;

// Every visible light, resolved with its node's world matrix: the frame's light list.
// Visible dome lights are summed into `ambient` instead. Returns false when the scene has no
// dome light at all - visible or hidden - so the caller can supply its own ambient light.
bool CollectLights(std::vector<LightItem>& out, glm::vec3& ambient) const;
```

```cpp
// Scene.h, private, after m_materials (Chapter 16).
std::vector<Light> m_lights;
```

```cpp
// Scene.cpp, inside namespace pf::scene (Chapter 16): the component functions, as for cameras.
uint32_t Scene::AddLight(const Light& light)
{
    m_lights.push_back(light);
    return static_cast<uint32_t>(m_lights.size() - 1);
}

void Scene::SetLight(NodeIndex node, uint32_t light)
{
    assert(node < m_nodes.size() && (light == NO_COMPONENT || light < m_lights.size()));
    m_nodes[node].light = light;
}

Light&       Scene::GetLight(uint32_t light)       { return m_lights.at(light); }
const Light& Scene::GetLight(uint32_t light) const { return m_lights.at(light); }
```

`CollectLights` walks the tree the way Chapter 12's `CollectDraws` does — from
the root, skipping the subtree under an invisible node — so hiding a light in
the hierarchy turns it off:

```cpp
// Scene.cpp, inside namespace pf::scene (Chapter 16): the frame's light list.
bool Scene::CollectLights(std::vector<LightItem>& out, glm::vec3& ambient) const
{
    out.clear();
    ambient = glm::vec3(0.0f);

    std::vector<NodeIndex> stack{ ROOT_NODE };
    while (!stack.empty())
    {
        const Node& node = m_nodes[stack.back()];
        stack.pop_back();
        if (!node.visible) { continue; }   // the whole subtree is hidden

        if (node.light != NO_COMPONENT)
        {
            const LightItem item = resolveLight(m_lights[node.light], node.world);
            if (item.type == LightType::Dome) { ambient += item.emission; }
            else                              { out.push_back(item); }
        }
        // Reversed, so children come out of the stack in authored order: the first
        // DistantLight in the file stays first, which makes it the sun (section 4).
        stack.insert(stack.end(), node.children.rbegin(), node.children.rend());
    }

    // Whether the scene HAS a sky, visible or not: hiding the dome means "no ambient light",
    // not "use the demo's default".
    return std::any_of(m_lights.begin(), m_lights.end(),
                       [](const Light& light) { return light.type == LightType::Dome; });
}
```

It must run after `UpdateWorldTransforms`, like `CollectDraws`, so that
`node.world` is this frame's.

---

## 3. Importing UsdLux

**This is `importLight`** and the two places it plugs into Chapter 14's
`UsdImport.cpp`. Its two helpers and it go just above `asXformable`, after
Chapter 15's material functions (`domeTextureAverage` uses Chapter 15's
`readAssetBytes`); `UsdImport.cpp` gains `<glm/gtc/constants.hpp>` for
`glm::pi`. Lights are `Xformable`, so the first is `asXformable`, which
lists the prim types whose transform the importer reads — without it, a light
would sit at its parent's origin:

```cpp
// UsdImport.cpp, in asXformable (Chapter 16): the light types join Chapter 14's list.
if (const auto* light = prim.as<tinyusdz::DistantLight>()) { return light; }
if (const auto* light = prim.as<tinyusdz::SphereLight>())  { return light; }
if (const auto* light = prim.as<tinyusdz::RectLight>())    { return light; }
if (const auto* light = prim.as<tinyusdz::DiskLight>())    { return light; }
if (const auto* light = prim.as<tinyusdz::DomeLight>())    { return light; }
```

All UsdLux types in TinyUSDZ inherit one `LightAPI` with the common inputs, so
one helper reads them — with a detour, because of a gap in TinyUSDZ v0.9.4.
Its parser fills `LightAPI`'s typed attributes from a per-type table, and the
tables are uneven: `DistantLight` and `DiskLight` list every common input, but
`SphereLight` and `RectLight` list only `color` and `intensity` (plus their
sizes), and `DomeLight` lacks `exposure`, `normalize`, and
`enableColorTemperature`. An input missing from the table is not lost: it is
kept, unparsed, in the prim's `props` map under its full name. Read only the
typed attribute and a Blender point light — always `normalize = 1` — arrives
with `normalize` false, so section 2's size factor multiplies its intensity
instead of being divided out: a 10 cm bulb comes in eight times too dim, and
its color temperature silently white.

So every input is read the same way: the typed attribute if the parser filled
it, else the raw property of the same name, else the schema's fallback (which
`scene::Light`'s defaults already are). `get_value().get_default(...)` reads a
typed attribute at the default time, as Chapter 14 reads every attribute; a
raw property's `Attribute` has `get_value` directly.

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 16). One UsdLux input: the
// typed attribute when TinyUSDZ parsed it, else the property it left in the prim's `props`.
// `value` keeps its default when neither is authored.
template <typename T>
static void readLightInput(const tinyusdz::TypedAttributeWithFallback<tinyusdz::Animatable<T>>& attribute,
                           const std::map<std::string, tinyusdz::Property>& props, const char* name, T& value)
{
    if (attribute.authored())
    {
        attribute.get_value().get_default(&value);
        return;
    }
    const auto found = props.find(name);
    if (found != props.end() && found->second.is_attribute())
    {
        found->second.get_attribute().get_value(&value);
    }
}
```

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 16). The inputs every UsdLux
// light shares. `props` is the light prim's own: BoundableLight's and NonboundableLight's.
static void readLightApi(const tinyusdz::LightAPI& api, const std::map<std::string, tinyusdz::Property>& props,
                         pf::scene::Light& light)
{
    tinyusdz::value::color3f color{ 1.0f, 1.0f, 1.0f };
    readLightInput(api.color, props, "inputs:color", color);
    light.color = glm::vec3(color.r, color.g, color.b);
    readLightInput(api.intensity, props, "inputs:intensity", light.intensity);
    readLightInput(api.exposure, props, "inputs:exposure", light.exposure);
    readLightInput(api.normalize, props, "inputs:normalize", light.normalize);
    readLightInput(api.enableColorTemperature, props, "inputs:enableColorTemperature", light.enableColorTemperature);
    readLightInput(api.colorTemperature, props, "inputs:colorTemperature", light.colorTemperature);

    // ShapingAPI's cone, when authored (every type that can have one parses it). An unauthored
    // cone is 90 degrees, which would cut away the light's back half - so "not authored" means
    // "no cone", not "90".
    if (api.shapingConeAngle.authored())
    {
        light.shaping = true;
        api.shapingConeAngle.get_value().get_default(&light.coneAngle);
        api.shapingConeSoftness.get_value().get_default(&light.coneSoftness);
    }
}
```

**A trap in TinyUSDZ v0.9.4:** its `DistantLight` inherits `LightAPI`'s
default intensity of 1, not the 50000 the USD schema overrides it with for
distant lights. A file that authors no intensity on its sun — legal, and it
means "the sun" — would import a light 50000 times too dim. The importer
applies the schema's value itself.

**The dome's image.** Blender exports its World as a `DomeLight` whose
`texture:file` is an HDR image: a tiny 4×4 one filled with the background
color when the World is a plain color, or the actual environment map. This
chapter treats a dome as constant light, so it needs one color out of that
image: its **average radiance over the sphere**. An environment image is a
lat-long map — rows are latitudes — and a row near a pole covers far less of
the sphere than a row at the equator, so each row is weighted by the sine of
its angle from the pole. For Blender's constant image every texel is the same
and the weighting changes nothing; for a real HDRI it keeps the sun and the
sky from being over-counted near the top of the image. (A dome whose image
cannot be read is the same as one with none: its color alone.)

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 16). The mean of a lat-long
// HDR environment over the sphere, each row weighted by the solid angle it covers. (1, 1, 1)
// when there is no usable image. Uses Chapter 15's readAssetBytes.
static glm::vec3 domeTextureAverage(const ImportContext& context, const tinyusdz::DomeLight& dome)
{
    tinyusdz::value::AssetPath asset;
    const auto file = dome.file.get_value();
    if (!file || !file.value().get_default(&asset) || asset.GetAssetPath().empty()) { return glm::vec3(1.0f); }

    const std::vector<uint8_t> bytes = readAssetBytes(context, asset.GetAssetPath());
    auto decoded = tinyusdz::image::LoadImageFromMemory(bytes.data(), bytes.size(), asset.GetAssetPath());
    if (bytes.empty() || !decoded || decoded.value().image.format != tinyusdz::Image::PixelFormat::Float ||
        decoded.value().image.channels != 4)
    {
        Log::warning(std::format("Dome light image {} is not a readable HDR image; using its color alone.",
                                 asset.GetAssetPath()).c_str());
        return glm::vec3(1.0f);
    }
    const tinyusdz::Image& image = decoded.value().image;
    const float* texels = reinterpret_cast<const float*>(image.data.data());

    glm::dvec3 sum(0.0);
    double     weightSum = 0.0;
    for (int y = 0; y < image.height; ++y)
    {
        const double weight = std::sin(glm::pi<double>() * (y + 0.5) / image.height);   // the row's share of the sphere
        for (int x = 0; x < image.width; ++x)
        {
            const float* texel = texels + (static_cast<size_t>(y) * image.width + x) * 4;
            sum       += weight * glm::dvec3(texel[0], texel[1], texel[2]);
            weightSum += weight;
        }
    }
    return glm::vec3(sum / weightSum);
}
```

The decoder returns Radiance `.hdr` files as 32-bit float RGBA — Chapter 15
skipped them as surface textures for exactly this reason. OpenEXR environment
maps depend on whether Chapter 13 compiled TinyUSDZ's EXR support; without it
they hit the warning above.

```cpp
// UsdImport.cpp - file scope, above the namespace block (Chapter 16). One UsdLux prim -> a
// pf::scene::Light on `node`. Returns false for light types this renderer does not draw.
static bool importLight(ImportContext& context, const tinyusdz::Prim& prim, pf::scene::NodeIndex node)
{
    pf::scene::Light light;
    if (const auto* distant = prim.as<tinyusdz::DistantLight>())
    {
        readLightApi(*distant, distant->props, light);
        light.type = pf::scene::LightType::Distant;
        if (!distant->intensity.authored()) { light.intensity = 50000.0f; }   // the schema's default; see above
        distant->angle.get_value().get_default(&light.angle);
    }
    else if (const auto* sphere = prim.as<tinyusdz::SphereLight>())
    {
        readLightApi(*sphere, sphere->props, light);
        light.type = pf::scene::LightType::Sphere;
        sphere->radius.get_value().get_default(&light.radius);
        if (light.radius <= 0.0f && !light.normalize)
        {
            Log::warning(std::format("{}: a sphere light of radius 0 without normalize emits nothing.",
                                     prim.absolute_path().full_path_name()).c_str());
        }
    }
    else if (const auto* rect = prim.as<tinyusdz::RectLight>())
    {
        readLightApi(*rect, rect->props, light);
        light.type = pf::scene::LightType::Rect;
        rect->width.get_value().get_default(&light.width);
        rect->height.get_value().get_default(&light.height);
    }
    else if (const auto* disk = prim.as<tinyusdz::DiskLight>())
    {
        readLightApi(*disk, disk->props, light);
        light.type = pf::scene::LightType::Disk;
        disk->radius.get_value().get_default(&light.radius);
    }
    else if (const auto* dome = prim.as<tinyusdz::DomeLight>())
    {
        readLightApi(*dome, dome->props, light);
        light.type               = pf::scene::LightType::Dome;
        light.domeTextureAverage = domeTextureAverage(context, *dome);
    }
    else
    {
        return false;
    }
    context.scene.SetLight(node, context.scene.AddLight(light));
    return true;
}
```

The dispatch: after Chapter 14's camera branch in `importPrim`, the node for
the prim already exists — `importPrim` creates it, with its transform, before
dispatching — so the light only attaches a component:

```cpp
// UsdImport.cpp, in importPrim's dispatch, after the camera branch (Chapter 16).
else if (importLight(context, prim, node))
{
    // a light component on this prim's node
}
```

`CylinderLight`, `GeometryLight`, and `PortalLight` fall through to Chapter
14's "skipped" branch and its warning.

Nothing here converts units or axes, because Chapter 14's file node already
does: a light's direction is its node's world −Z, and a Z-up, centimetre file's
node rotates and scales it into Y-up metres like any geometry. Radiance is per
unit area *and* per unit solid angle, so the same file in centimetres or metres
has the same `intensity`; only lengths change, and `resolveLight` takes those
from the world matrix.

---

## 4. The light buffer

Set 0, binding 1 — the index contract's slot since Chapter 10. One buffer per
frame in flight, persistently mapped, rewritten every frame in `Record`
(Chapter 08 section 6's rule: never write what an in-flight frame may read).

**Why a storage buffer and not a uniform buffer.** Three reasons, in order of
how much they matter. A storage buffer can end in a **runtime-sized array**,
`lights[]`, whose length the shader learns from the count in front of it; a
uniform block's arrays are fixed-size. Its layout is **`std430`**, which packs
arrays without rounding every element up to 16 bytes. And its size limit is
far larger: `maxUniformBufferRange` is only guaranteed 16 KB, where a storage
buffer is guaranteed 128 MB. Uniform buffers can be faster for small data read
uniformly by every invocation — which lights are — but at a few hundred lights
the difference does not show.

The C++/GLSL twins go in `SharedShaderTypes.h` after Chapter 15's
`MaterialParameters` asserts, built from `vec4`, `uint`, and `int` only, so
`std430` and C++ agree. Their own asserts follow them, and the closing brace of
`namespace pf::shared` moves below those — Chapter 11's pattern:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 16. LightData::type values: scene::LightType's. */
#define LIGHT_DISTANT 0u
#define LIGHT_SPHERE  1u   /* point lights, and spot lights: a sphere with a cone */
#define LIGHT_RECT    2u
#define LIGHT_DISK    3u

/* One light, std430, in the set 0 binding 1 storage buffer. A LightItem, packed. */
struct LightData
{
    vec4 position;    /*  0  xyz world position; unused by distant lights */
    vec4 direction;   /* 16  xyz unit world direction the light travels: the node's -Z */
    vec4 emission;    /* 32  rgb: irradiance (distant), intensity (sphere, rect, disk) */
    vec4 shape;       /* 48  x radius, y range, z cos(cone outer), w cos(cone inner) */
    uint type;        /* 64  LIGHT_* */
    uint padding0;    /* 68  keeps the size a multiple of 16 */
    uint padding1;    /* 72 */
    uint padding2;    /* 76 */
};                    /* 80 */

/* The front of the light buffer. */
struct LightBufferHeader
{
    vec4 ambient;     /*  0  rgb: constant light from every direction (dome lights) */
    uint count;       /* 16  how many LightData follow */
    int  sunIndex;    /* 20  the first distant light, or -1: Chapter 17 shadows it */
    uint padding0;    /* 24 */
    uint padding1;    /* 28 */
};                    /* 32 */

#ifdef __cplusplus
    static_assert(sizeof(LightData) == 80, "LightData layout drifted.");
    static_assert(offsetof(LightData, type) == 64, "LightData alignment drifted.");
    static_assert(sizeof(LightBufferHeader) == 32, "LightBufferHeader layout drifted.");
    }
#endif
```

In `std430` a struct's alignment is its largest member's, which here is a
`vec4`, so `lights[]` starts 32 bytes in and each element is 80 bytes apart —
exactly C++'s layout of a header followed by an array, which is what lets the
C++ side write them with two `memcpy`s.

**"The sun."** One distant light is special: Chapter 17 gives it a shadow map,
because one shadowed directional light covers most outdoor scenes. The header
names it, and the rule is simple enough to predict from the file: **the first
distant light in the list**, which `CollectLights` returns in the file's
order. `sunIndex` is in the header rather than found by the shader so that
the CPU — which fits the shadow cascades in Chapter 17 — and the GPU agree.

### Binding 1 in `CreateFrameResources`

Chapter 10's `CreateFrameResources` builds a binding array, a pool, and one
buffer and set per frame in flight. Binding 1 extends each of those:

```cpp
// SceneRenderer.cpp, CreateFrameResources (Chapter 16): binding 1 joins the set 0 layout's
// binding array, after Chapter 10's binding 0.
{ .binding         = 1,
  .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
  .descriptorCount = 1,
  .stageFlags      = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT },
```

Fragment shaders are the readers today. The vertex stage is listed for Chapter
22, whose light glows read the buffer in a vertex shader, and a stage that is
listed but never reads costs nothing.

```cpp
// The pool gains one storage buffer descriptor per frame in flight (Chapter 16):
{ VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, FRAMES_IN_FLIGHT },
```

```cpp
// At the end of CreateFrameResources, after Chapter 10's loop over the frames (Chapter 16): each
// frame's light buffer, sized for a full header and MAX_LIGHTS lights, starting empty, and
// written into that frame's set.
constexpr VkDeviceSize lightBufferSize = sizeof(shared::LightBufferHeader) + MAX_LIGHTS * sizeof(shared::LightData);
for (uint32_t i = 0; i < FRAMES_IN_FLIGHT; ++i)
{
    m_lightBuffers[i] = createBuffer(m_context, lightBufferSize, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, true);
    if (m_lightBuffers[i].buffer == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating a light buffer failed.");
    }
    // An empty list until the first WriteLights: a demo that never calls it draws unlit, not garbage.
    const shared::LightBufferHeader empty{ .ambient = glm::vec4(0.0f), .count = 0, .sunIndex = -1,
                                           .padding0 = 0, .padding1 = 0 };
    std::memcpy(m_lightBuffers[i].mapped, &empty, sizeof(empty));
    vmaFlushAllocation(m_context.allocator, m_lightBuffers[i].allocation, 0, VK_WHOLE_SIZE);

    const VkDescriptorBufferInfo lightInfo{
        .buffer = m_lightBuffers[i].buffer,
        .offset = 0,
        .range  = lightBufferSize,
    };
    const VkWriteDescriptorSet write{
        .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
        .dstSet          = m_frameSets[i],
        .dstBinding      = 1,
        .descriptorCount = 1,
        .descriptorType  = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        .pBufferInfo     = &lightInfo,
    };
    vkUpdateDescriptorSets(m_context.device, 1, &write, 0, nullptr);
}
```

`DestroyFrameResources` destroys them after the frame buffers:

```cpp
// DestroyFrameResources, after Chapter 10's loop over m_frameBuffers (Chapter 16).
for (AllocatedBuffer& buffer : m_lightBuffers)
{
    destroyBuffer(m_context, buffer);
}
m_sunDirection = {};
```

**This is `WriteLights`.** It packs each `LightItem` into a `LightData`, picks
the sun, and writes the header last. No barrier is needed afterwards, by
Chapter 10 section 7's rule for host writes.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 16).
void SceneRenderer::WriteLights(uint32_t frameIndex, std::span<const scene::LightItem> lights,
                                glm::vec3 ambient)
{
    if (lights.size() > MAX_LIGHTS && !m_warnedTooManyLights)
    {
        Log::warning(std::format("{} lights; only the first {} are drawn.", lights.size(), MAX_LIGHTS).c_str());
        m_warnedTooManyLights = true;
    }
    const uint32_t count = static_cast<uint32_t>(std::min<size_t>(lights.size(), MAX_LIGHTS));

    auto* bytes = static_cast<std::byte*>(m_lightBuffers[frameIndex].mapped);
    auto* data  = reinterpret_cast<shared::LightData*>(bytes + sizeof(shared::LightBufferHeader));
    int32_t sunIndex = -1;
    for (uint32_t i = 0; i < count; ++i)
    {
        const scene::LightItem& light = lights[i];
        if (sunIndex < 0 && light.type == scene::LightType::Distant) { sunIndex = static_cast<int32_t>(i); }
        data[i] = shared::LightData{
            .position    = glm::vec4(light.position, 1.0f),
            .direction   = glm::vec4(light.direction, 0.0f),
            .emission    = glm::vec4(light.emission, 0.0f),
            .shape       = glm::vec4(light.radius, light.range, light.cosOuter, light.cosInner),
            .type        = static_cast<uint32_t>(light.type),
            .padding0    = 0,
            .padding1    = 0,
            .padding2    = 0,
        };
    }

    const shared::LightBufferHeader header{
        .ambient  = glm::vec4(ambient, 0.0f),
        .count    = count,
        .sunIndex = sunIndex,
        .padding0 = 0,
        .padding1 = 0,
    };
    std::memcpy(bytes, &header, sizeof(header));
    vmaFlushAllocation(m_context.allocator, m_lightBuffers[frameIndex].allocation, 0, VK_WHOLE_SIZE);

    // The CPU's copy of the same choice, for Chapter 17's cascade fitting.
    m_sunDirection[frameIndex] = sunIndex >= 0 ? std::optional<glm::vec3>(lights[sunIndex].direction)
                                               : std::nullopt;
}
```

A `DomeLight` is never passed here — `CollectLights` turned it into `ambient` —
so `LightType::Dome` never reaches the buffer, and the shader has no case for
it.

### Every scene demo writes its lights

Chapters 11 and 12's demos lit their meshes with the sun in `FrameData`, which
the mesh shader no longer reads (section 5). Their sun panel stays; what it
edits becomes the one light they write. A `LightItem` is plain data, so no
`Scene` is needed — the grass demos build theirs the same way. Chapter 11
defined its sun color as "what a white surface facing the sun reflects", which
is irradiance divided by π, so the irradiance is π times it:

```cpp
// Demos/Meshes/MeshesDemo.cpp and Demos/SceneGraph/SceneGraphDemo.cpp, in Record, right after
// WriteFrameData(frame.frameIndex, frameData) (Chapter 16): the sun panel, as a light.
// glm::pi comes from <glm/gtc/constants.hpp>.
const scene::LightItem sun{
    .type      = scene::LightType::Distant,
    .direction = glm::vec3(frameData.sunDirection),
    .emission  = glm::pi<float>() * glm::vec3(frameData.sunColor),
};
m_sceneRenderer.WriteLights(frame.frameIndex, std::span(&sun, 1), glm::vec3(frameData.ambientColor));
```

`FrameData`'s three sun fields stay where they are — it is append-only — and
these demos keep filling them, for the panel's sake.

`UsdViewerDemo::Record` gathers the file's lights instead, and keeps its sun
panel for files that have none. Two fallbacks, each decided by what the
*scene* holds rather than by what is visible: a file with no lights at all —
Chapter 14's and 15's test scenes — is lit by the panel's sun, exactly as
before this chapter; a file with no dome gets the panel's ambient. A file whose
lights are all hidden in the hierarchy stays dark, because that is what hiding
them asked for.

```cpp
// Demos/UsdViewer/UsdViewerDemo.h, private, with the scene's other per-frame lists (Chapter 16).
std::vector<scene::LightItem> m_lights;   // rebuilt every Record; a member so its storage is reused
```

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, in Record, after WriteFrameData (Chapter 16). glm::pi comes
// from <glm/gtc/constants.hpp>.
glm::vec3 ambient{ 0.0f };
if (!m_scene.CollectLights(m_lights, ambient))
{
    ambient = m_ambientColor;   // no dome in the file: the panel's ambient, as in Chapter 11
}
if (m_scene.LightCount() == 0)
{
    // No lights in the file at all: the panel's sun, as the Meshes demo builds it.
    m_lights.push_back(scene::LightItem{
        .type      = scene::LightType::Distant,
        .direction = glm::vec3(frameData.sunDirection),
        .emission  = glm::pi<float>() * glm::vec3(frameData.sunColor),
    });
}
m_sceneRenderer.WriteLights(frame.frameIndex, m_lights, ambient);
```

---

## 5. Forward shading: one loop over the lights

The mesh fragment shader now does, for every pixel, what Chapter 15 did for
the sun: for each light, ask how much light arrives and from where, and hand
both to `evaluatePreviewSurface`. That is **forward shading** — lighting
computed while drawing each surface — and its cost is pixels × lights. For the
tens of lights a hand-built or exported scene has, that is nothing. For
thousands — a city at night — renderers sort lights into screen tiles or
view-space clusters first, so each pixel loops only over the lights near it.
Chapter 22 builds exactly that, and the `range` from section 2 is what it
needs.

### How much light arrives: `lightIrradiance`

For a local light, the irradiance on a surface facing it is its intensity over
the squared distance — with three refinements, each one line:

- **The distance is clamped to the light's radius**, which section 2 showed is
  the physically right limit, and which keeps a point light from dividing by
  zero when a surface touches it.
- **A window fades the light to exactly zero at its range**, smoothly enough
  that you cannot see where:

  ```text
  window(d) = clamp(1 − (d / range)⁴, 0, 1)²
  ```

  The fourth power keeps it near 1 almost all the way out — the light obeys the
  inverse-square law where it matters — and the square makes it meet zero with
  zero slope, so there is no visible edge. This is the window Unreal Engine
  popularized (Karis, 2013).
- **The light's shape**: a spot's cone fades between its two cosines with
  `smoothstep(a, b, x)`, which is 0 below a, 1 above b, and an S-curve between:
  with `s = (x − a) / (b − a)` it is `3s² − 2s³`, which leaves 0 and arrives at
  1 flat, so the edge has no visible line. Worked, for the test scene's spot (a
  20° cone, softness 0.3): a = cos 20° = 0.940 and b = 0.958, the cosine of
  16.7°. A floor point 18° off the axis has x = 0.951, so s = 0.63 and the spot
  delivers 69% of its light there; at 19°, 24%; inside 16.7°, all of it.
  The cone is stored as cosines because `dot(-L, direction)` already *is* the
  cosine of the angle off the axis, so no `acos` is needed. A rect or disk
  emits as a flat (Lambertian) surface does, its intensity falling as the
  cosine of the angle off its axis, and nothing behind it. A sphere without a
  cone has `cosOuter = −2`, and since no cosine is below −1,
  `smoothstep(−2, −1, x)` is 1 for every one: no branch needed.

```glsl
// Shaders/Include/Lights.glsl - Chapter 16. Set 0 binding 1, and how much light arrives from
// one of its lights. Included, never compiled on its own.
#ifndef PF_LIGHTS_GLSL
#define PF_LIGHTS_GLSL

#include "SharedShaderTypes.h"

layout(std430, set = 0, binding = 1) readonly buffer LightBuffer
{
    LightBufferHeader lightHeader;
    LightData         lights[];
};

// The irradiance `light` delivers to a surface at `worldPosition` facing it, and the unit
// direction L from the surface toward the light.
vec3 lightIrradiance(LightData light, vec3 worldPosition, out vec3 L)
{
    if (light.type == LIGHT_DISTANT)
    {
        L = -light.direction.xyz;
        return light.emission.rgb;
    }

    vec3  toLight         = light.position.xyz - worldPosition;
    float distanceSquared = max(dot(toLight, toLight), 1e-8);
    L = toLight * inversesqrt(distanceSquared);

    float radius  = light.shape.x;
    float range   = light.shape.y;
    float falloff = 1.0 / max(distanceSquared, radius * radius);       // inverse square, finite inside the light
    float x       = distanceSquared / (range * range);                 // (d / range)^2
    float window  = clamp(1.0 - x * x, 0.0, 1.0);
    window *= window;                                                  // reaches 0 at the range, smoothly

    float cosAxis = dot(-L, light.direction.xyz);                      // the angle off the light's -Z
    float shape   = light.type == LIGHT_SPHERE
                  ? smoothstep(light.shape.z, light.shape.w, cosAxis)  // a spot's cone; 1 with none
                  : max(cosAxis, 0.0);                                 // rect, disk: a flat emitter, one-sided
    return light.emission.rgb * (falloff * window * shape);
}

#endif
```

**What the rect and disk approximation gets wrong.** Shading a panel light as a
point at its centre is right far away and wrong up close: its light does not
wrap around a surface beside it the way a broad source does, and its
reflection in a smooth surface is a dot instead of a rectangle. The upgrade
that fixes both is *Linearly Transformed Cosines* (Heitz, Dupuy, Hill, and
Neubelt, 2016), a self-contained change to `lightIrradiance` for these two
light types.

### The loop

The mesh fragment shader from Chapter 15 changes in one place — the lighting.
The ambient light now comes from the light buffer's header (the dome, or the
demo's own ambient), and the sun from `FrameData` is replaced by the loop:

```glsl
// Shaders/Scene/Mesh.frag.glsl - Chapter 16 adds this include, after Chapter 15's PreviewSurface.glsl:
#include "Lights.glsl"
```

```glsl
    // Mesh.frag.glsl, main() - Chapter 16: replaces Chapter 15's single sun. Every light in the
    // buffer, then the constant ambient light, then emission.
    vec3 V = normalize(frame.cameraPosition.xyz - worldPosition);
    vec3 color = evaluateAmbient(s, lightHeader.ambient.rgb, occlusion) + emissive;
    for (uint i = 0u; i < lightHeader.count; ++i)
    {
        vec3 L;
        vec3 irradiance = lightIrradiance(lights[i], worldPosition, L);
        color += evaluatePreviewSurface(s, N, V, L, irradiance);
    }
```

These lines replace exactly the three that computed `V`, `L`, and `color` from
`frame.sunDirection`. Everything before them — the material, the normal map —
and after them — the debug views and the clamp — is Chapter 15's.

Each light is shaded by whichever BRDF Chapter 15 section 9's switch selects,
because the choice lives in `evaluatePreviewSurface`, not in the loop.

`evaluatePreviewSurface` already returns zero for a light behind the surface,
so the loop needs no test of its own.

> **Shadows are not here.** Every light shines through every object: a point
> light inside a closed box lights the floor outside it. That is the next
> chapter's subject. Chapter 17 gives the sun — `lights[lightHeader.sunIndex]` —
> a cascaded shadow map, and multiplies only that light's contribution by
> it. Point and spot shadows need a shadow map per light (a cube map for a
> point light), which is the same technique more times, and is left there.

## Checkpoint

Build, and run the viewer on `LightTest.usda`: copy it from Appendix A into
`Assets/Scenes/` first (section 9 says what is in it). With every light on, you
can now see:

- [ ] **Every light, in its own color**: an orange pool on the floor under the
      bulb, at the left; the spot's pale blue disc in the middle; the panel's
      orange on the spheres' fronts; the disk's green on the underside of
      `SphereC`; and small highlights on every sphere. Select a light's node
      in the Scene panel and untick **Visible** in the inspector: that light
      goes out.
- [ ] **Clipping where the light is strongest.** `SphereA`'s side toward the
      bulb is a flat peach — its red channel is at 255 — and every highlight is
      a hard white dot. Those are correct light values, clipped by Chapter 08's
      composite; section 6 brings them into range.
- [ ] Chapters 11 and 12's demos look as they did, lit by their sun panels.

---

## 6. Exposure and the tone curve

Section 2 ended with a white floor reflecting 2.2 under an ordinary exported
lamp. The scene target holds that fine — it is `R16G16B16A16_SFLOAT`, good to
65504 — but the display shows 0 to 1, and Chapter 08's composite pass clamps:
2.2 becomes 1, and so does 1.5, and so does 40. Everything brighter than white
turns into the same white, and a lit scene looks burnt out. A camera has the
same problem and two tools for it, and the composite pass gets both:

- **Exposure** scales the whole image, as a camera's shutter and aperture do.
  It is measured in **stops**: +1 doubles every value, −1 halves it. Lowering
  it brings the bright parts into range and leaves the dark parts dark. It is
  the same `2^exposure` UsdLux uses for a light's `exposure` input.
- **A tone curve** maps the unbounded result into [0, 1] *gradually*. Values
  well below 1 pass almost unchanged; values approaching and beyond 1 are
  compressed, so a highlight at 4 is still brighter than one at 2 instead of
  both being white. Film does this chemically, and its "shoulder" is why a
  photograph of a lamp does not look clipped.

The composite pass from Chapter 08 grows exactly this — the block below is the
one Chapter 33's path tracer relies on — and it stays the engine's pass, so
every demo gets it:

```glsl
// Shaders/Composite/Composite.frag.glsl, grown from Chapter 08 (Chapter 16).
#version 450

layout(location = 0) in  vec2 uv;
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D sceneImage;

layout(push_constant) uniform ToneMappingBlock
{
    float exposure;     // a multiplier: 2^stops
    int   mode;         // 0 = Reinhard, 1 = ACES, 2 = raw
} settings;

// Unchanged from Chapter 08.
layout(constant_id = 0) const bool encodeSrgb = true;

vec3 linearToSrgb(vec3 linear)
{
    vec3 low  = linear * 12.92;
    vec3 high = 1.055 * pow(linear, vec3(1.0 / 2.4)) - 0.055;
    return mix(high, low, lessThanEqual(linear, vec3(0.0031308)));
}

// Krzysztof Narkowicz's fit of the ACES filmic curve: a toe, a soft shoulder, slightly more
// contrast than Reinhard.
vec3 acesApproximation(vec3 x)
{
    const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main()
{
    vec3 color = texture(sceneImage, uv).rgb * settings.exposure;

    if      (settings.mode == 0) { color = color / (color + 1.0); }   // Reinhard
    else if (settings.mode == 1) { color = acesApproximation(color); }

    // Raw mode can exceed 1.0; the tone curves already stay below it.
    color    = clamp(color, 0.0, 1.0);
    outColor = vec4(encodeSrgb ? linearToSrgb(color) : color, 1.0);
}
```

**The defaults are exposure 1 (0 stops) and raw**, which is Chapter 08's
clamp-and-encode exactly: a demo whose values already sit in [0, 1] — the
triangle, the gradient — looks as it did, and Chapter 15's byte-exact
`GreyBands` check still holds. A lit scene picks a curve.

What the curves do, in numbers computed from the shader's own formulas:

| scene value | 0.1 | 0.5 | 1 | 2 | 4 | 10 |
| --- | --- | --- | --- | --- | --- | --- |
| raw (clamp) | 0.10 | 0.50 | 1 | 1 | 1 | 1 |
| Reinhard | 0.09 | 0.33 | 0.50 | 0.67 | 0.80 | 0.91 |
| ACES (Narkowicz) | 0.13 | 0.62 | 0.80 | 0.92 | 0.97 | 1.0 |

Raw keeps everything below 1 exact and loses everything above it. **Reinhard**,
`x / (1 + x)`, never reaches white and maps 1.0, the old white, to 0.5, which
looks flat; it also compresses each channel separately, so a bright saturated
light drifts toward its own primaries rather than toward white. **ACES** (here
as Narkowicz's one-line fit) darkens the deepest shadows — 0.01 becomes 0.004,
its *toe* — and rolls highlights smoothly into white by about 10, its
*shoulder*; most real-time renderers ship something like it. Neither is what
Blender shows: Blender's viewport defaults to its *AgX* view transform, so
match against a Blender render with an exposure tweak, not number for number.

### The C++ side

The push-constant block gets its twin in `SharedShaderTypes.h`, after the light
structs' asserts, with the namespace's closing brace moving below it again:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 16. The composite pass's push constant. */
struct ToneMapping
{
    float exposure;   /* multiplier, 2^stops */
    int   mode;       /* 0 Reinhard, 1 ACES, 2 raw */
};

#ifdef __cplusplus
    static_assert(sizeof(ToneMapping) == 8, "ToneMapping layout drifted.");
    }
#endif
```

The settings a person edits are stops and a curve, not a multiplier and an
integer, so they get their own small struct and panel, beside the renderer that
owns the composite — the same shape as Chapter 07's `ShaderParameters` and its
panel:

```cpp
// Source/PillowFort/VulkanGraphics/ToneMapping.h
#pragma once

#include <cstdint>

namespace pf::vulkan_graphics {

enum class ToneCurve : int32_t { Reinhard = 0, Aces = 1, Raw = 2 };   // the shader's `mode`

struct ToneMappingSettings
{
    float     exposureStops = 0.0f;           // 0 = Chapter 08's brightness
    ToneCurve curve         = ToneCurve::Raw; // Raw = Chapter 08's clamp
};

// The "Tone mapping" panel. Defined in ToneMapping.cpp; true if anything changed.
bool drawToneMappingPanel(ToneMappingSettings& settings);

} // namespace pf::vulkan_graphics
```

```cpp
// Source/PillowFort/VulkanGraphics/ToneMapping.cpp, inside namespace pf::vulkan_graphics.
// Includes ToneMapping.h and <imgui.h>.
bool drawToneMappingPanel(ToneMappingSettings& settings)
{
    bool changed = false;
    // Top right, left of Chapter 09's demo picker.
    ImGui::SetNextWindowPos(ImVec2(ImGui::GetIO().DisplaySize.x - 600.0f, 10.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Tone mapping", nullptr, ImGuiWindowFlags_AlwaysAutoResize))
    {
        changed |= ImGui::SliderFloat("Exposure (stops)", &settings.exposureStops, -10.0f, 10.0f, "%.1f");
        int curve = static_cast<int>(settings.curve);
        changed |= ImGui::Combo("Curve", &curve, "Reinhard\0ACES\0Raw (clamp)\0");
        settings.curve = static_cast<ToneCurve>(curve);
        if (ImGui::Button("Reset")) { settings = {}; changed = true; }
    }
    ImGui::End();
    return changed;
}
```

`VulkanRenderer` holds the settings and pushes them. Its composite pipeline
layout, built in Chapter 08's `createCompositeObjects`, gains a fragment-stage
push-constant range:

```cpp
// VulkanRenderer.cpp, createCompositeObjects (Chapter 16): the pipeline layout gets a push range.
const VkPushConstantRange toneMappingRange{
    .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT,
    .offset     = 0,
    .size       = sizeof(shared::ToneMapping),
};
const VkPipelineLayoutCreateInfo layoutInfo{
    .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    .setLayoutCount         = 1,
    .pSetLayouts            = &m_compositeSetLayout,
    .pushConstantRangeCount = 1,
    .pPushConstantRanges    = &toneMappingRange,
};
```

```cpp
// VulkanRenderer.h (Chapter 16): the settings, and how main reaches them.
public:
    ToneMappingSettings& toneMapping() { return m_toneMapping; }
private:
    ToneMappingSettings m_toneMapping;
```

```cpp
// VulkanRenderer.cpp, recordFrame: between binding the composite set and its vkCmdDraw
// (Chapter 16).
const shared::ToneMapping toneMapping{
    .exposure = std::exp2(m_toneMapping.exposureStops),
    .mode     = static_cast<int32_t>(m_toneMapping.curve),
};
vkCmdPushConstants(commandBuffer, m_compositeLayout, VK_SHADER_STAGE_FRAGMENT_BIT,
                   0, sizeof(toneMapping), &toneMapping);
```

`VulkanRenderer.h` includes `"PillowFort/VulkanGraphics/ToneMapping.h"`;
`VulkanRenderer.cpp` gains `"SharedShaderTypes.h"` (for `shared::ToneMapping`)
and `<cmath>`. And `main` shows the panel with the
engine's others, after the demo picker:

```cpp
// Source/SandboxGame/Main.cpp, in the frame loop after the demo picker (Chapter 16).
vulkan_graphics::drawToneMappingPanel(renderer.toneMapping());
```

Changing exposure does not touch the scene target, only how the composite
reads it — which is why, in Chapter 33, it does not restart the path tracer's
accumulation.

**Run it again.** Pick ACES in the new Tone mapping panel. The image brightens
and flattens, because ACES lifts the middle tones (0.5 becomes 0.62 in the table
above), and `SphereA`'s peach side becomes a gradient. Pull Exposure down to
−1: every value halves before the curve, the colors come back, and the
highlights roll off into white instead of ending at an edge. Reset returns to
raw at 0 stops, which is section 5's picture exactly.

---

## 7. Editing lights

### The inspector

Chapter 12's `drawNodeInspector` shows a node's name, visibility, transform,
and camera. A light node gains a section for its light — the authored values,
so dragging "Intensity" means what it says in the file. Moving and aiming a
light is the node's transform, which the inspector already edits: a distant
light's position does nothing, its rotation everything.

Two details need care. **Light colors are linear**, but ImGui's color picker
shows its numbers as sRGB (Chapter 08 section 4's rule), so the inspector
converts for display and back on edit with Chapter 11's `ColorSpace.h` —
otherwise picking a mid-orange in the swatch gives a light noticeably lighter
and less saturated than the swatch. And **intensities span orders of
magnitude** — a sun's 50000, a bulb's 30 — so the slider is logarithmic.

```cpp
// Source/PillowFort/Scene/ScenePanels.cpp - file scope, above the namespace block (Chapter 16).
// The authored values of one light.
static void drawLightInspector(pf::scene::Light& light)
{
    using pf::scene::LightType;
    static const char* const typeNames[] = { "Distant", "Sphere", "Rect", "Disk", "Dome" };
    ImGui::SeparatorText(std::format("Light: {}", typeNames[static_cast<uint32_t>(light.type)]).c_str());

    // Linear in the light, sRGB in the swatch.
    glm::vec3 swatch = pf::scene::linearToSrgb(light.color);
    if (ImGui::ColorEdit3("Color", &swatch.x)) { light.color = pf::scene::srgbToLinear(swatch); }
    ImGui::DragFloat("Intensity", &light.intensity, 0.01f, 0.0f, 1.0e6f, "%.3g", ImGuiSliderFlags_Logarithmic);
    ImGui::DragFloat("Exposure (stops)", &light.exposure, 0.05f, -20.0f, 20.0f);
    ImGui::Checkbox("Normalize", &light.normalize);
    ImGui::Checkbox("Color temperature", &light.enableColorTemperature);
    if (light.enableColorTemperature)
    {
        ImGui::SliderFloat("Kelvin", &light.colorTemperature, 1000.0f, 10000.0f, "%.0f");
    }

    switch (light.type)
    {
    case LightType::Distant: ImGui::DragFloat("Angle (deg)", &light.angle, 0.01f, 0.0f, 180.0f); break;
    case LightType::Sphere:
    case LightType::Disk:    ImGui::DragFloat("Radius", &light.radius, 0.01f, 0.0f, 100.0f); break;
    case LightType::Rect:
        ImGui::DragFloat("Width", &light.width, 0.01f, 0.0f, 100.0f);
        ImGui::DragFloat("Height", &light.height, 0.01f, 0.0f, 100.0f);
        break;
    case LightType::Dome:    break;
    }
    if (light.type == LightType::Sphere)
    {
        ImGui::Checkbox("Cone (spot)", &light.shaping);
        if (light.shaping)
        {
            ImGui::SliderFloat("Cone angle", &light.coneAngle, 0.0f, 180.0f, "%.1f deg");
            ImGui::SliderFloat("Softness", &light.coneSoftness, 0.0f, 1.0f);
        }
    }
    if (light.type != LightType::Distant && light.type != LightType::Dome)
    {
        ImGui::DragFloat("Range (0 = auto)", &light.range, 0.1f, 0.0f, 10000.0f);
    }
}
```

```cpp
            // In drawNodeInspector, after Chapter 12's camera section (Chapter 16).
            if (node.light != NO_COMPONENT)
            {
                drawLightInspector(scene.GetLight(node.light));
            }
```

`ScenePanels.cpp` gains `#include "PillowFort/Scene/ColorSpace.h"` and
`<format>`; `Light` arrives through `Scene.h`. Nothing needs telling that a
light changed: `CollectLights` re-resolves every light every frame.

### Gizmos: seeing where the lights are

A light is invisible — it lights things, but you cannot see *it* — which makes
"which of these is the spot, and where is it pointing" guesswork. A gizmo
answers that: a small marker drawn at each light's position, with a line
showing which way it points. ImGui can draw it. Its **background draw list**
is drawn under every ImGui window but over the composited scene, in screen
coordinates, so a gizmo is a circle and a line at the light's projected
position — no pipeline, no depth test.

Projecting a point onto the screen is the vertex shader's job done on the CPU:
multiply by the view-projection, divide by w, and map Vulkan's clip-space
[−1, 1] — whose +Y points **down** — onto ImGui's display size, whose +Y also
points down. A point behind the camera (`w ≤ 0`) would project to a mirrored
position, so it is skipped.

```cpp
// Scene/ScenePanels.h (Chapter 16):
// Markers at every visible light: a circle in the light's color at its position, and a line
// along its direction (1 m). Distant lights draw at their node's position, which does not
// affect their light. Call between beginUiFrame and drawFrame, like any panel.
void drawLightGizmos(const Scene& scene, const glm::mat4& viewProjection);
```

```cpp
// ScenePanels.cpp, inside namespace pf::scene (Chapter 16).
void drawLightGizmos(const Scene& scene, const glm::mat4& viewProjection)
{
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    ImDrawList*  draw    = ImGui::GetBackgroundDrawList();

    // World -> ImGui's screen coordinates; false behind the camera.
    auto project = [&](glm::vec3 world, ImVec2& screen) {
        const glm::vec4 clip = viewProjection * glm::vec4(world, 1.0f);
        if (clip.w <= 1e-4f) { return false; }
        const glm::vec2 ndc = glm::vec2(clip) / clip.w;   // Vulkan: +y is down, like ImGui
        screen = ImVec2((ndc.x * 0.5f + 0.5f) * display.x, (ndc.y * 0.5f + 0.5f) * display.y);
        return true;
    };

    for (NodeIndex index = 0; index < scene.NodeCount(); ++index)
    {
        const Node& node = scene.GetNode(index);
        if (node.light == NO_COMPONENT || !node.visible) { continue; }
        const Light& light = scene.GetLight(node.light);
        if (light.type == LightType::Dome) { continue; }   // everywhere at once: nothing to mark

        const glm::vec3 position  = glm::vec3(node.world[3]);
        const glm::vec3 direction = glm::normalize(-glm::vec3(node.world[2]));
        const glm::vec3 color     = linearToSrgb(glm::clamp(light.color, 0.0f, 1.0f));   // ImGui draws sRGB
        const ImU32     imColor   = ImGui::ColorConvertFloat4ToU32(ImVec4(color.r, color.g, color.b, 1.0f));

        ImVec2 center;
        ImVec2 tip;
        if (!project(position, center)) { continue; }
        draw->AddCircle(center, 8.0f, imColor, 0, 2.0f);
        if (light.type != LightType::Sphere || light.shaping)   // everything that points somewhere
        {
            if (project(position + direction, tip)) { draw->AddLine(center, tip, imColor, 2.0f); }
        }
    }
}
```

The node's own `visible` flag is checked, not its ancestors': a gizmo for a
light under a hidden parent still draws, which is a reasonable way to find a
light you turned off.

The viewer calls it in `Update`, after Chapter 12's code has updated the world
transforms and built the frustum — with the view-projection it built the
frustum from, which is the one this frame's `FrameData` will carry — behind a
checkbox in its panel:

```cpp
// Demos/UsdViewer/UsdViewerDemo.h, private (Chapter 16).
bool m_showLightGizmos = true;
```

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, DrawPanel, after Chapter 14's checkboxes (Chapter 16).
ImGui::Checkbox("Light gizmos", &m_showLightGizmos);
```

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, Update, right after the draw list is collected (Chapter 16).
// viewer, camera, and aspect are the locals Chapter 12's code declared for the frustum.
if (m_showLightGizmos)
{
    scene::drawLightGizmos(m_scene, camera.Projection(aspect) * scene::viewMatrix(viewer.world));
}
```

---

## 8. Lights from Blender

Export with **File → Export → Universal Scene Description**, with *Lights*
ticked (and *World Dome Light* for the sky, which Blender 4.5 writes by
default). Here is what Blender 4.5 writes:

| Blender | USD | Notes |
| --- | --- | --- |
| Sun, Strength S, Angle α | `DistantLight`, `intensity = S / 4`, `angle = α / 2`, `normalize = 1` | See below for the 4. The angle is halved too: UsdLux's `angle` is the full angular diameter, as Blender's is, and Blender's importer doubles it back. With `normalize` it changes nothing here |
| Point, Power P watts, Radius r | `SphereLight`, `intensity = P / π`, `radius = r`, `normalize = 1` | So `I = P / 4π` — exactly Cycles' radiant intensity for a point light of power P |
| Spot, Power P, Size θ, Blend b | `SphereLight` with `ShapingAPI`: `cone:angle = θ / 2`, `cone:softness = b`; `treatAsPoint = 1` when the radius is 0 | The same brightness as a point light of the same power, as in Cycles; section 2's spot formula is Cycles' blend |
| Area, Power P, Rectangle / Square | `RectLight`, `intensity = P / π`, `width`, `height`, `normalize = 1` | |
| Area, Disk / Ellipse | `DiskLight`, `intensity = P / π`, `radius` (an ellipse's average), `normalize = 1` | |
| Any light's Temperature | `enableColorTemperature = 1` **always**, `colorTemperature` | Blender 4.x lights have a temperature that defaults to white |
| World, plain color C, Strength S | `DomeLight` at `intensity = S`, with a 4×4 `.hdr` of color C beside the file | Section 3's average recovers C exactly |
| World with an environment texture | `DomeLight` with that image | Its sphere-weighted average becomes the ambient light |

Every intensity is written with `normalize = 1`, so a light's brightness does
not change when you resize it in Blender, and section 2's normalized formulas
are the ones in use.

**The sun is four times dimmer than in Blender.** A Sun of Strength 3 is an
irradiance of 3 in Cycles. Blender's exporter writes `intensity = 3 / 4` —
its source says *"unclear why, but approximately matches Karma"* — and with
`normalize` that is an irradiance of 0.75 here, and in any renderer that
follows UsdLux. Blender's own importer multiplies by four again, so Blender
round-trips its files; every other reader sees a weaker sun. Points, spots, and
areas are not affected. So an exported rig balanced in Blender arrives with its
local lights four times too strong *relative to the sun*. It is worth knowing
before you start tuning materials; the fix belongs in the scene (raise the
sun's Strength by four, or its exposure by two stops in the inspector), not in
the importer, which should read what the file says.

**How bright the result is.** A Blender scene lit for Cycles typically comes
in two to four stops brighter than the display range — the 1000 W lamp from
section 2 is three. Start with the ACES curve and pull exposure down until the
brightest surfaces stop clipping; Blender's viewport is doing the same thing
with its AgX transform.

---

## 9. The test scene

`Assets/Scenes/LightTest.usda`, the scene section 5's checkpoint runs: a floor
and a row of grey spheres, lit by one of each light type. Every light is a separate prim, so the hierarchy's
visibility toggle turns each one on and off on its own — which is how the exit
check isolates them. All the lights are `normalize = 1`, as Blender writes
them, so their intensities read directly as section 2's quantities: the sun's
2 is an irradiance of 2, the point light's 40 is a radiant intensity of 10.

The scene is printed in full in Appendix A, to copy.

The rect light needs no rotation: it emits along its −Z, and the spheres are
at −Z from it. The spot and disk do: a rotation of −90° about X turns −Z into
−Y (straight down), and +90° turns it into +Y.

---
## Exit check

Run `UsdViewerDemo` on `LightTest.usda` with validation on, the composite in
raw mode at 0 stops unless a step says otherwise.

- [ ] **The sun, by the numbers.** Hide every light but `Sun` (the hidden
      `Sky` means no ambient light at all). The sun's rotation tilts its −Z
      30° from straight down, so the floor receives `2 × cos 30° = 1.73` and
      reflects about `(1 − 0.04) × 0.5 / π × 1.73 ≈ 0.26` — about 140/255
      after the encode, away from the specular highlight (a few units either
      way: the Fresnel term depends on where you look from). Rotating the sun
      node in the inspector moves the shading and the highlights together.
- [ ] **The point light** (only `Bulb` visible) makes an orange pool on the
      floor that falls off with distance and is brightest under it, and a
      small highlight on `SphereA`. Moving it in the inspector moves both;
      doubling its height roughly quarters the brightness under it.
- [ ] **The spot** (only `Spot`) is a soft-edged blue disc on the floor —
      sharp-edged with Softness 0 in the inspector, wider with a larger cone
      angle.
- [ ] **The panel** (only `Panel`) lights the fronts of the spheres orange and
      nothing behind its plane. **The disk** (only `Disk`) lights the
      underside of `SphereC` green.
- [ ] **The dome** (only `Sky`) lights everything evenly and dimly blue, with no
      direction at all.
- [ ] **The inspector edits live**: color (the light's hue matches the
      swatch), intensity, exposure, temperature, size, cone, and range each
      change the image the frame they are dragged. Gizmos mark every light but
      the dome, and the spot's and panel's lines point the way they shine.
- [ ] **Tone mapping.** With everything on, raw mode clips `SphereA`'s side
      toward the bulb to a flat peach and every highlight to a hard white dot.
      ACES keeps a gradient on both, and at −1 stop the colors come back with
      the highlights rolled off; Reset returns to raw at 0 stops, and Chapter
      15's `GreyBands` check still reads its exact bytes.
- [ ] **A Blender-exported light rig** (a sun, a spot, an area light, a
      point light with a temperature, and a World color) renders without
      clipping under ACES at some exposure, each light where Blender put it,
      the warm light warm, and the sky as ambient. The sun is weaker relative
      to the others than in Blender — section 8 says why.
- [ ] Chapters 11 and 12's demos look as they did, lit by their sun panels.
- [ ] Validation is silent, with synchronization validation proven on by
      Chapter 05's positive control.

Shadows come next: [17 — Shadows](17-Shadows.md) gives the sun —
`lights[lightHeader.sunIndex]` — a cascaded shadow map.

---

## Sources

- The UsdLux schema's own documentation: units, `normalize`, `ShapingAPI`.
- Blender 4.5's USD exporter, read in its source and checked against a real
  export (section 8's table and the sun's factor of four).
- Kang et al. 2002, the color-temperature fit; Karis 2013, the range window;
  Heitz, Dupuy, Hill, and Neubelt 2016, Linearly Transformed Cosines;
  Narkowicz 2015, the ACES fit.

---

## Appendix A — `LightTest.usda`

Reference, to copy: section 9's test scene, `Assets/Scenes/LightTest.usda`.

```usda
#usda 1.0
(
    defaultPrim = "LightTest"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "LightTest"
{
    def Scope "Materials"
    {
        def Material "Grey"
        {
            token outputs:surface.connect = </LightTest/Materials/Grey/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.5, 0.5, 0.5)
                float inputs:roughness = 0.6
                token outputs:surface
            }
        }

        def Material "Polished"
        {
            token outputs:surface.connect = </LightTest/Materials/Polished/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.5, 0.5, 0.5)
                float inputs:roughness = 0.15
                token outputs:surface
            }
        }
    }

    def Mesh "Floor" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-10, 0, 10), (10, 0, 10), (10, 0, -10), (-10, 0, -10)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </LightTest/Materials/Grey>
    }

    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 100)
        double3 xformOp:translate = (0, 3, 9)
        float xformOp:rotateX = -15
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }

    def Sphere "SphereA" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        double radius = 0.75
        double3 xformOp:translate = (-3, 0.75, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </LightTest/Materials/Polished>
    }

    def Sphere "SphereB" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        double radius = 0.75
        double3 xformOp:translate = (0, 0.75, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </LightTest/Materials/Polished>
    }

    def Sphere "SphereC" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        double radius = 0.75
        double3 xformOp:translate = (3, 0.75, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </LightTest/Materials/Polished>
    }

    # The sun: irradiance 2, from above and to the right, travelling along its -Z.
    def DistantLight "Sun"
    {
        float inputs:intensity = 2
        bool inputs:normalize = 1
        float3 xformOp:rotateXYZ = (-60, 30, 0)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }

    # A warm point light: radiant intensity 40 / 4 = 10, at 2700 K.
    def SphereLight "Bulb"
    {
        float inputs:intensity = 40
        bool inputs:normalize = 1
        float inputs:radius = 0.1
        bool inputs:enableColorTemperature = 1
        float inputs:colorTemperature = 2700
        double3 xformOp:translate = (-3, 2.5, 1.5)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    # A blue spot pointing straight down at the floor: a 20-degree cone, softened by 30%.
    def SphereLight "Spot" (
        prepend apiSchemas = ["ShapingAPI"]
    )
    {
        color3f inputs:color = (0.4, 0.6, 1)
        float inputs:intensity = 200
        bool inputs:normalize = 1
        float inputs:radius = 0.05
        float inputs:shaping:cone:angle = 20
        float inputs:shaping:cone:softness = 0.3
        float3 xformOp:rotateXYZ = (-90, 0, 0)
        double3 xformOp:translate = (0, 4, 3)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }

    # A 2 x 1 m panel facing the spheres from the front, warm orange.
    def RectLight "Panel"
    {
        color3f inputs:color = (1, 0.55, 0.3)
        float inputs:intensity = 12
        bool inputs:normalize = 1
        float inputs:width = 2
        float inputs:height = 1
        double3 xformOp:translate = (3, 1.5, 4)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    # A disk light lying on its back below SphereC's front right, shining up at its underside.
    def DiskLight "Disk"
    {
        color3f inputs:color = (0.5, 1, 0.5)
        float inputs:intensity = 5
        bool inputs:normalize = 1
        float inputs:radius = 0.3
        float3 xformOp:rotateXYZ = (90, 0, 0)
        double3 xformOp:translate = (3.9, 0.05, 0.6)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
    }

    # A dim blue sky: ambient luminance about 0.06.
    def DomeLight "Sky"
    {
        color3f inputs:color = (0.6, 0.75, 1)
        float inputs:intensity = 0.08
    }
}
```

Next: [17 — Shadows](17-Shadows.md)
