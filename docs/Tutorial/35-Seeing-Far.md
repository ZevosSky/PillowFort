# 35 — Seeing Far

**Goal:** a camera that sees 200 km. A new demo, `Horizon`, with a lens of its
own (near plane 0.1 m, far plane 200 km), a fly camera at 50 m/s that stays
within 5 km of the origin and under the clouds, and four pairs of test plates,
each pair 1 m deep, at 1, 5, 10, and 30 km. Drawn with the engine's depth, the
three far pairs flicker through each other, and on some GPUs the 1 km pair
speckles too; drawn with reversed depth, which this chapter builds inside the
demo, all four hold. It is the first of the chapters that fill this view; the
index lists them.

**ROADMAP:** step 21+ — a demo, in `Source/PillowFort/Demos/Horizon/` with
shaders under `Shaders/Horizon/`. Chapters 36-42 grow it.

**Module:** the demo is `pf::demos::horizon` (`HorizonDemo`). It adds nothing
to the engine and changes none of it. Reversed depth lives inside this demo;
the index's depth contract (`D32_SFLOAT`, cleared to 1.0, compared with
`LESS`) stays exactly as it is for every other demo. Outside its two new
folders, `Main.cpp` gains two lines.

**Math:** taught where it is first used and listed in the index's [The math,
chapter by chapter](../VulkanTutorial.md#the-math-chapter-by-chapter): the
ground you can see and how large a far thing looks (Where this is going), float
spacing (section 4), the smallest depth step, stored either way round (section
5), and counting steps between floats from their bits (section 6). It assumes
Chapter 10 section 2's projection matrix and depth formula.

**Prerequisites:** builds on the engine as the earlier chapters leave it, built
and running (Chapter 34 is a toolbox, not a step). From earlier chapters, one
line each:

- Chapter 09 sections 2 (the `Demo` interface and `Resize`), 4
  (`beginScenePass`, `endScenePass`, and `handBackSceneTarget`), 6
  (`beginDemoPanel` and its two slots), and 7 (registering a demo).
- Chapter 10 sections 2 (the projection matrix, the depth formula
  `f/(f-n) · (1 - n/d)`, the precision table, and the aside on reverse-Z), 3
  (`Transform`), 4 (the view matrix's last column), 6 (yaw: positive turns
  left), 7 (writing the camera into set 0 each frame), 8 (C++/GLSL twin
  headers), 9 (the depth buffer: `D32_SFLOAT`, cleared to 1.0, `LESS`), 10
  (which input reaches the demo while ImGui has the keyboard), 11 (the fly
  controller), and 12 (`CameraControls`, and the Camera window
  `drawCameraPanel` draws).
- Chapter 11 sections 2 (the 48-byte `Vertex`), 4 (`makePlane`), and 8 (what a
  dynamic state is); Chapter 19 sections 3 (the instance buffer at set 0,
  binding 2), 5 (`PrepareDraws` and its sort key), and 6 (`RecordBatches`, and
  the cull mode set per run).
- Chapter 04 section 5 (the three questions a barrier answers), and Chapter 22
  section 8 (positive floats sort like their bit patterns).
- Chapter 23 sections 1 (the sky's vertex shader: depth 1.0, and a direction
  per pixel from the un-projected matrix), 6 (the plain ground below the
  horizon), 7 (`Sky::Update` outside the scene pass, `Sky::Draw` at depth 1.0
  with `LESS_OR_EQUAL`, and why it goes last), and 8 (one sky setting for the
  whole engine); Chapter 24 section 4 (`SetImageBasedLighting` in `Setup`);
  Chapter 25 section 2 (`sunTravelDirection`); Chapter 15 section 9 (why the
  sun's irradiance is π times Chapter 11's `sunColor`); Chapter 28 sections 1
  (the eye is kept below the cloud base) and 3 (the cloud layer, from 1,500 m).
- Chapter 18 sections 4 (the multisampled depth the pass tests) and 6 (every
  scene pipeline declares the pass's sample count); Chapter 08 section 4
  (ImGui's colours are sRGB); Chapter 02 section 3 (validation messages and
  their IDs).

---

## Where this is going

Most 3D demos so far end at Chapter 10's far plane, 500 m from the camera. The
ocean and the sea reach 5 km, and the sea's skirt (Chapter 30 section 9)
carries water to the horizon. This chapter and the ones after it reach the
horizon with land on it: a 33 km map with an island of mountains about 21 km
across inside it, a sea around it, towns, landmarks, and forests, seen from
near its middle out to 65 km and beyond.

**Why distance is expensive.** Stand on flat ground and look all the way round.
Everything you can see out to a distance *R* lies in a disc, and a disc's area
grows with the square of its radius:

$$
A = \pi R^2
$$

Double the distance and there is four times as much ground. From 500 m to 64 km
the distance grows 128 times and the ground 128² = 16,384 times: about 0.8 km²
becomes about 12,900 km². Drawn as finely as the first 500 m, the view to 64 km
would cost about 16,000 times as much.

It does not need to be drawn that finely, because far things are small. A
thing of size *s* at distance *d* spans about *s*/*d* radians of the view. At
1440p with Chapter 10's 60° field of view, the 720 pixels from the centre of
the screen to its top edge span a height of tan 30° one unit in front of the
camera, so near the centre one radian is about 720 / tan 30° ≈ 1,250 pixels.
A 1 m bush at 30 km spans 1/30,000 of a radian: 1/24 of a pixel. **Level of
detail (LOD)** is the idea behind all these chapters: draw each thing only as
finely as its size on screen needs.

**Layers by distance.** The ground is cut into rings around the camera. Each ring
reaches twice as far as the one inside it and is drawn twice as coarsely, so
every ring costs the same: twelve rings reach 65 km for about twelve times the
cost of the first, not 16,000 times. Objects do the same with simpler copies of
themselves (*Skyrim* draws its distant trees as pictures on two crossed
quads), and then disappear into the colour of the ground they stand on. Haze,
distant things fading toward the colour of the sky, hides the seams between
the layers, and it is also what makes distance read as distance (*Ghost of
Tsushima* hazes everything from 10 cm out to 100 km).

| Distance | What is drawn there | Built in |
| --- | --- | --- |
| 0-150 m | The finest terrain rings, with noise added to the heightmap for detail; objects at full detail; trees as meshes; shadows | 36, 37 |
| 150 m-1 km | Coarser rings; objects at their simpler levels, picked by their height on screen; the mesh trees hand over to flat pictures of trees | 37, 40 |
| 1-8 km | Houses gone, landmarks at their coarsest; forests as tree pictures; haze begins | 37, 40 |
| 8-65 km | The outer rings, over the heightmap's coarsest levels; landmarks; heavy haze | 36 |
| Beyond | The sea, out to the horizon, and the sky | 36 |

**Seeing far is cheap; travelling far is what costs.** Everything this arc draws
stays in memory: one heightmap, a few models, and forests generated from
them. Twelve rings of the same grid, a few thousand objects, and haze are not
much work, wherever the far plane is. Moving the camera far is another matter:
a world too big for memory has to be loaded in pieces as the camera travels,
and, as section 4 shows, the camera's own coordinates lose precision the
further it goes from the origin. So in this arc the camera stays within 5 km of
the origin, and the view reaches 65 km and past it.

**What this chapter builds** is everything the far view needs before there is
anything to see: the demo, a lens that reaches 200 km, a camera fast enough to
fly over an island, depth that can tell a near thing from a far one at every
distance, and the engine's sky behind it all. The test plates show the depth
problem first, then the fix, in two parts. **Part 1** (sections 1-3) builds the
demo, the plates and a pipeline of the demo's own, all with the engine's depth,
and ends with the far pairs striped white where the back plate shows through
the front one. **Part 2** (sections 4-8) is how far apart floats are and how
far that lets the camera go, why the far pairs fight, depth stored the other
way round, the sky (which the reversal breaks until it is drawn first), and
what reversing depth means for the rest of the engine; it ends with all four
pairs holding under the sky.

### What you are actually writing

**This is `HorizonDemo.h`**, the map of the chapter. Every private function
names the section that writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 35: a camera that sees 200 km, and depth that keeps up with it
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/HorizonDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Transform.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"
#include "PillowFort/VulkanGraphics/Sky.h"

#include <glm/glm.hpp>

#include <cstdint>
#include <vector>

namespace pf::demos::horizon {

class HorizonDemo final : public Demo
{
public:
    HorizonDemo();   // CPU only: the lens, the speed, and where the camera starts (section 1)

    const char*          Name() const override { return "Horizon"; }
    InitializationResult Setup(const DemoContext& context) override;                    // sections 1-3, 7
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override; // nothing sized to the window
    void                 Update(const FrameInput& input) override;                      // sections 1, 4
    void                 Record(const RecordContext& frame) override;                   // sections 1, 3, 6, 7
    void                 Teardown() override;                                           // section 1
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    void                 ReturnToViewpoint();                                  // section 1
    void                 DrawPanel();                                          // section 1, grown in 6
    void                 DrawCameraControls();                                 // section 1, grown in 4
    uint32_t             AddFlatMaterial(const char* name, glm::vec3 color);   // section 2
    void                 CreatePlates();                                       // section 2
    InitializationResult CreateFlatPipeline();                                 // section 3, one line in 6
    glm::mat4            Projection(float aspect) const;                       // section 3, rewritten in 6
    void                 KeepCameraInBounds();                                 // section 4, grown in 7
    void                 DrawDepthReadout();                                   // section 6

    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;   // set 0, and the plates' mesh, materials, and batches
    vulkan_graphics::Sky           m_sky;             // section 7: Chapter 23's, with Chapter 28's clouds

    // Sections 2 and 3: what the demo draws, and its own pipeline to draw it with.
    std::vector<scene::DrawItem> m_plates;           // eight: a white back plate and a colored front one per pair
    std::vector<glm::vec4>       m_materialColors;   // by material index: what each run pushes
    VkPipelineLayout             m_flatLayout   = VK_NULL_HANDLE;
    VkPipeline                   m_flatPipeline = VK_NULL_HANDLE;

    // CPU state: survives Teardown, so switching back finds everything as it was.
    scene::Camera         m_camera;
    scene::Transform      m_cameraTransform;
    scene::CameraControls m_controls;
    float                 m_time = 0.0f;
};

} // namespace pf::demos::horizon
```

The camera, its controller, and the time are CPU state, kept across `Teardown`
as every demo's settings are. The plates are `DrawItem`s, batched by the
`SceneRenderer` and drawn through a pipeline of the demo's own, which is why the
demo keeps `m_materialColors` (section 2).

### Where everything lands

```text
Source/PillowFort/Demos/Horizon/
  HorizonDemo.h            the class, above
  HorizonDemo.cpp          top to bottom:
      the banner, the path line, the includes          section 1
      clearDepth, stepsApart                           file scope, above the namespace block (section 6)
      namespace pf::demos::horizon {
          using namespace vulkan_graphics;             section 1
          the constants                                sections 1, 2, 4, 7, in that order
          pairDirection, storedDepth                   sections 2 and 6, in that order
          the member functions                         in the order the sections write them
          Record                                       last, though section 1 starts it: every section grows it
      }
Shaders/Horizon/
  HorizonTypes.h           C++/GLSL twin: FlatDraw, the flat pipeline's push    section 3
  Flat.vert.glsl           the position, through Chapter 19's instances        section 3
  Flat.frag.glsl           one color, no light                                 section 3
Source/SandboxGame/Main.cpp                                                    section 1
  two lines: the include, and the demo in the list
```

Section 1 shows the top of `HorizonDemo.cpp`, and each section after it says
where its code goes in this order.

---

# Part 1 — The problem on screen (sections 1-3)

Part 1 builds the demo with the engine's depth exactly as Chapter 10 set it up,
and puts the problem on screen.

## 1. The demo and its lens

**This is the top of `HorizonDemo.cpp`, the constructor, `Setup`, `Resize`,
`Teardown`, `Update`, the panel, `ReturnToViewpoint`, and a first `Record`.**

The far view gets a demo of its own because it needs things no other demo
wants: a far plane 400 times further out, a camera fast enough to cross an
island, and, from section 6, depth stored the other way round. Keeping all
three inside one demo keeps every other demo, and the engine, exactly as it
was. The chapters after it grow this demo.

**The lens.** The near plane stays at Chapter 10's 0.1 m, so the camera can
still come close to things. The far plane goes out to 200 km: past the 65 km
the terrain will reach, with room for the sea beyond it. A far
plane can even be infinitely far away, which some engines do; 200 km is
further than anything this arc draws, and a finite one keeps every matrix in
the chapter an ordinary one. Section 5 shows that, with depth reversed, the
far plane's distance hardly matters to precision.

**The speed.** Chapter 10's fly controller moves at 5 m/s, a walk; crossing the
10 km disc the camera may fly in (section 4) would take half an hour. This
demo flies at 50 m/s, 180 km/h, and with Shift at the controller's four times
that, 200 m/s: across the disc in under a minute.

**Where it starts.** 100 m up at the origin, looking along -Z. Section 2 puts
the test plates in front of that point.

`HorizonDemo.cpp` begins as every demo's file does, with the house banner
(Chapter 02 section 0), the path line, and its includes. The standard headers
are all listed, because MSVC's standard library does not bring them in through
the others. `Horizon/HorizonTypes.h` arrives with its file in section 3 (its
path starts at `Horizon/` because Chapter 09 section 8 put `Shaders/` on the
include path). The block ends by opening the namespace, which stays open to the
end of the file, where `} // namespace pf::demos::horizon` closes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 35: a camera that sees 200 km, and depth that keeps up with it
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/HorizonDemo.cpp
#include "PillowFort/Demos/Horizon/HorizonDemo.h"

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/Scene/ColorSpace.h"
#include "PillowFort/Scene/MeshGenerators.h"
#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"

#include <glm/gtc/constants.hpp>
#include <glm/gtc/matrix_transform.hpp>   // glm::perspective, translate, rotate, scale
#include <imgui.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <limits>

namespace pf::demos::horizon {

using namespace vulkan_graphics;
```

The constants and the constructor, which sets them, as Chapter 09 section 2
asks of every demo, without touching the GPU. The constants go inside the
namespace, below `using namespace vulkan_graphics;`, and the constructor below
them:

```cpp
// Section 1: the lens, how fast the camera flies, and where it starts, looking along -Z.
constexpr float     NEAR_PLANE = 0.1f;        // metres
constexpr float     FAR_PLANE  = 200000.0f;   // metres: 200 km
constexpr float     FLY_SPEED  = 50.0f;       // metres per second; Shift multiplies it by 4
constexpr glm::vec3 VIEWPOINT{ 0.0f, 100.0f, 0.0f };
```

```cpp
// CPU state only (Chapter 09): the lens, the speed, and the camera at its viewpoint, looking along -Z.
HorizonDemo::HorizonDemo()
{
    m_camera.nearPlane            = NEAR_PLANE;
    m_camera.farPlane             = FAR_PLANE;
    m_controls.active             = scene::ControllerKind::Fly;
    m_controls.fly.moveSpeed      = FLY_SPEED;
    m_cameraTransform.translation = VIEWPOINT;
}
```

`Setup` builds what the demo draws with. For now that is only the
`SceneRenderer`, which owns set 0: the camera's per-frame buffer, and the
instance buffer Chapter 19 batches into. Sections 2, 3, and 7 each add a step
before the `return`. `Resize` has nothing to do: the only window-sized images
are the engine's, which it rebuilds itself (Chapter 09 section 2):

```cpp
InitializationResult HorizonDemo::Setup(const DemoContext& context)
{
    m_context = context;   // first, so Teardown works however far this gets

    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }

    return InitializationResult::success();
}
```

```cpp
// Nothing of this demo's is sized to the window: the engine rebuilds its own targets.
InitializationResult HorizonDemo::Resize(const SceneTargets& /*targets*/)
{
    return InitializationResult::success();
}
```

`Teardown` destroys in reverse and keeps the CPU state. It is written whole
now, ahead of the steps it undoes, because undoing a step that never ran does
nothing, as its comment says; the same is what makes it safe after a `Setup`
that stopped partway:

```cpp
// Safe after a partial Setup, or one that has not grown its later steps yet: a null handle destroys
// nothing, and Sky::Shutdown returns at once if Initialize never ran. GPU objects only: the camera stays.
void HorizonDemo::Teardown()
{
    m_sky.Shutdown();                                                            // section 7
    vkDestroyPipeline(m_context.vulkan.device, m_flatPipeline, nullptr);         // section 3
    vkDestroyPipelineLayout(m_context.vulkan.device, m_flatLayout, nullptr);
    m_flatPipeline = VK_NULL_HANDLE;
    m_flatLayout   = VK_NULL_HANDLE;
    m_plates.clear();           // section 2: they name meshes and materials of the scene renderer below
    m_materialColors.clear();
    m_sceneRenderer.Shutdown();
}
```

**The camera's window.** Every camera demo so far draws Chapter 10's "Camera"
window by calling `drawCameraPanel`. Its Far slider runs from 10 m to 5 km, and
ImGui puts a value back inside a slider's range the moment the slider is
dragged: one touch, and this demo's 200 km would become 5 km. Widening the
slider would change the window for every camera demo, so this demo does not
call `drawCameraPanel` and draws a Camera group of its own instead: the keys,
a button back to the start, and where the camera is.

That also decides where the panel goes. `beginDemoPanel`'s `BelowCamera` slot
is for a demo with a camera, under Chapter 10's window; with no such window,
the `BelowFrame` slot puts the panel where that window would be, at y = 220
under Frame (Chapter 09 section 6). There it has 490 pixels of height at
1280 x 720, the room down to the bottom of the screen less a 10-pixel margin,
where under the Camera window, at y = 470, it would have 240.

`Update` hands the input to the controller, as every camera demo does, then
draws the panel:

```cpp
void HorizonDemo::Update(const FrameInput& input)
{
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    DrawPanel();
    m_time = input.elapsedSeconds;
}
```

```cpp
void HorizonDemo::DrawPanel()
{
    // Horizon draws no Camera window (section 1), so its panel takes that window's place, under Frame.
    if (debug_panels::beginDemoPanel("Horizon", debug_panels::DemoPanelSlot::BelowFrame))
    {
        DrawCameraControls();   // sections 1, 4
    }
    ImGui::End();
}
```

The panel is one function per group, so a section that adds a group adds one
line here; section 6 adds the other one. The camera's group, as this section
writes it (section 4 adds three lines at its end):

```cpp
// Section 1: in place of Chapter 10's Camera window, whose Far slider stops at 5 km.
void HorizonDemo::DrawCameraControls()
{
    ImGui::SeparatorText("Camera");
    ImGui::TextUnformatted("WASD move, Q/E down/up, Shift x4");
    ImGui::TextUnformatted("Hold the right mouse button to look");
    if (ImGui::Button("Back to the viewpoint")) { ReturnToViewpoint(); }
    const glm::vec3& position = m_cameraTransform.translation;
    ImGui::Text("Position  %.1f, %.1f, %.1f", position.x, position.y, position.z);
}
```

The button puts the camera back where it started. Section 2's plates are set
out to be seen from there:

```cpp
// Where the camera starts, looking along -Z: section 2 stands the plates in front of it.
void HorizonDemo::ReturnToViewpoint()
{
    m_cameraTransform.translation = VIEWPOINT;
    m_cameraTransform.rotation    = glm::identity<glm::quat>();
}
```

**A first `Record`.** `Record` is part of the `Demo` interface, so the demo
needs one before it builds. The smallest that is correct opens the engine's
scene pass with a clear colour, a pale horizon blue, closes it, and hands the
scene target back to the engine (Chapter 09 section 4). Sections 3, 6, and 7
grow it, so write it at the end of the file, below everything else, and the
other functions stay in the order the sections write them:

```cpp
void HorizonDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;

    // Section 1: a pale horizon blue where nothing is drawn.
    const VkClearColorValue clearColor{ { 0.45f, 0.60f, 0.80f, 1.0f } };
    beginScenePass(commandBuffer, frame.targets, &clearColor);

    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
}
```

**Registering it** is Chapter 09 section 7's two lines in
`Source/SandboxGame/Main.cpp`: the include, with the others in alphabetical
order,

```cpp
#include "PillowFort/Demos/Horizon/HorizonDemo.h"
```

and the demo at the end of the list, so it is last in the picker:

```cpp
    demoList.push_back(std::make_unique<demos::horizon::HorizonDemo>());         // Chapter 35
```

The demo adds files, so rerun `GenerateProjects.bat` before you build. Run
with `--demo Horizon`: a pale blue window, and the Horizon panel with its
Camera group. Click once on the empty scene, so that ImGui lets go of the
keyboard (Chapter 10 section 10), and fly with WASD: the position on the panel
changes, and nothing else does, because there is nothing to see yet.

**Running `Horizon`, from here to Chapter 45.** Every later chapter runs it the
same way, so it is said once, here. Start it with `--demo Horizon`. Click the
scene once after any click on a panel, or the keys stay with ImGui. Hold the
right mouse button and drag to look: mouse-look turns 0.003 radians for every
pixel of drag, so about 385 pixels is 66 degrees, about 665 is 114, and about
1,050 a half turn. From section 7 on the sky is drawn, and the chapters'
pictures are taken with it on: the sky starts **Off** on every run, and
section 7 says where to set it to **Sun sky**.

## 2. Test plates

**This is the plates' constants, `pairDirection`, `AddFlatMaterial`, and
`CreatePlates`.**

### What the plates test

Depth has a limited number of values to give out, so two surfaces close
together far away can end up with the same one. To see where that happens, the
demo puts up pairs of plates: a coloured plate in front, and a white plate
exactly 1 m behind it and a little larger, so a pair that works is a coloured
square in a white frame. The pairs stand 1, 5, 10, and 30 km from the
viewpoint, red, yellow, green, and blue.

```text
  One pair, along its line from the camera, seen from above (not to scale):

  camera ----------------------------- | ----- 1 m ----- |
                                     front             back
                                  (coloured)    (white, a little wider)
```

Three choices make the failure easy to see:

- **Every pair looks the same size.** A plate's side is a fixed fraction of its
  distance, a tenth for the front plate: 100 m across at 1 km, 3 km across at
  30 km. Each covers about 6° of the view, around 60 pixels at 720p.
- **Each pair is seen a little from the side.** The pairs face the viewpoint
  but stand off to either side of straight ahead: the 1 km pair 18° to the
  left, the 5 km pair 6° to the left, the 10 km pair 6° to the right, and the
  30 km pair 18° to the right, so left to right on the screen they are red,
  yellow, green, and blue. From where the camera starts, looking along -Z, each
  plate's depth changes from one edge to the other. Where depth runs out of
  precision, that change turns into stripes.
- **The white plates are drawn first.** A fragment passes `LESS` only if it is
  nearer than what is there; at exactly the same depth it fails. So where the
  front and back plates store the same depth, whichever was drawn first stays.
  Drawing the back plate first makes a tie show white, the wrong answer, where
  you can see it. Drawn the other way, a tie would show the right colour by
  luck and hide the problem. `PrepareDraws` sorts by whether a material is a
  cutout, then by whether a mesh is double-sided, then by material, lowest
  index first (Chapter 19 section 5). Every plate has the same answer to the
  first two, so registering the white material before the four colours is all
  it takes.

The plates' constants go below section 1's, inside the namespace: the gap, the
sizes, and a table with one row per pair (GLM's vectors are `constexpr`, as
Chapter 32 section 1's `BOAT_START` already relies on):

```cpp
// Section 2: the test plates. Every pair faces VIEWPOINT, where the camera starts.
constexpr float     PLATE_GAP  = 1.0f;    // metres from a front plate to its back plate
constexpr float     FRONT_SIZE = 0.10f;   // a plate's side, as a fraction of its distance: every pair
constexpr float     BACK_SIZE  = 0.12f;   // looks the same size, the back plate a frame round the front one

struct PlatePair
{
    float       distance;   // metres from VIEWPOINT to the front plate
    float       azimuth;    // degrees, turning from -Z toward +X
    glm::vec3   color;      // the front plate's, linear
    const char* label;
};
constexpr std::array<PlatePair, 4> PLATE_PAIRS{ {
    { 1000.0f,  -18.0f, { 0.80f, 0.04f, 0.04f }, "1 km"  },   // red
    { 5000.0f,   -6.0f, { 0.80f, 0.55f, 0.02f }, "5 km"  },   // yellow
    { 10000.0f,   6.0f, { 0.04f, 0.50f, 0.06f }, "10 km" },   // green
    { 30000.0f,  18.0f, { 0.04f, 0.12f, 0.80f }, "30 km" },   // blue
} };
constexpr glm::vec3 BACK_COLOR{ 0.85f, 0.85f, 0.85f };   // white, behind every pair
```

A pair's azimuth turns from -Z toward +X, the way the sea's sun and wind
angles do (Chapter 30). That is the opposite sign to Chapter 10's yaw, where a
positive angle turns left (Chapter 10 section 6): the blue pair, at +18°, is
on the right. `pairDirection` goes below the constants, still inside the
namespace:

```cpp
// Section 2: the unit direction from VIEWPOINT toward a pair.
static glm::vec3 pairDirection(const PlatePair& pair)
{
    const float azimuth = glm::radians(pair.azimuth);
    return { std::sin(azimuth), 0.0f, -std::cos(azimuth) };
}
```

### The plates

Section 3 draws the plates through a pipeline of the demo's own, which takes
each material's colour as a push constant. Two things follow. The
`SceneRenderer` still needs a material for every `DrawItem`, because it
batches by material, and it builds that material's set 1 even though the
demo's pipeline never binds it. And the demo keeps each colour in a table of
its own, under the same index, for the push constant. `AddFlatMaterial` does
both:

```cpp
// A material the flat pipeline can draw: registered with the scene renderer, which batches by material,
// and its color kept here, under the same index, for the run's push constant.
uint32_t HorizonDemo::AddFlatMaterial(const char* name, glm::vec3 color)
{
    const uint32_t index = m_sceneRenderer.AddMaterial(scene::Material{ .name = name, .baseColor = glm::vec4(color, 1.0f) });
    m_materialColors.resize(std::max<std::size_t>(m_materialColors.size(), index + 1));
    m_materialColors[index] = glm::vec4(color, 1.0f);
    return index;
}
```

`CreatePlates` makes one 1 m square, double-sided, and scales it for every
plate. `makePlane` lies flat in XZ facing +Y (Chapter 11 section 4): a quarter
turn about X stands it up facing +Z, and a turn of minus the pair's azimuth
about Y faces it back along the line to the viewpoint. The back plate sits 1 m
further out along that same line, so the two are parallel and exactly a metre
apart:

```cpp
void HorizonDemo::CreatePlates()
{
    // One square, 1 m on a side, drawn from both sides; each plate scales it.
    scene::MeshData square = scene::makePlane(1.0f, 1.0f, 1);
    square.doubleSided     = true;
    const uint32_t mesh    = m_sceneRenderer.AddMesh(square);

    // The white material first. PrepareDraws sorts by material once cutout and double-sidedness, which every
    // plate shares, are equal (Chapter 19 section 5), so every back plate is drawn before every front one,
    // and where the two store the same depth, LESS keeps the back one.
    const uint32_t back = AddFlatMaterial("Back plate", BACK_COLOR);

    m_plates.clear();
    for (const PlatePair& pair : PLATE_PAIRS)
    {
        const uint32_t  front     = AddFlatMaterial(pair.label, pair.color);
        const glm::vec3 direction = pairDirection(pair);

        // makePlane lies in XZ, facing +Y. Stood up, it faces +Z; turned by -azimuth about Y, it faces
        // back along `direction`, toward VIEWPOINT.
        const glm::mat4 facing = glm::rotate(glm::mat4(1.0f), glm::radians(-pair.azimuth), glm::vec3(0.0f, 1.0f, 0.0f))
                               * glm::rotate(glm::mat4(1.0f), glm::half_pi<float>(), glm::vec3(1.0f, 0.0f, 0.0f));
        auto plate = [&](float distance, float size) {
            return glm::translate(glm::mat4(1.0f), VIEWPOINT + direction * distance) * facing
                 * glm::scale(glm::mat4(1.0f), glm::vec3(size));
        };
        m_plates.push_back({ .world = plate(pair.distance + PLATE_GAP, BACK_SIZE * pair.distance),
                             .mesh = mesh, .material = back });
        m_plates.push_back({ .world = plate(pair.distance, FRONT_SIZE * pair.distance),
                             .mesh = mesh, .material = front });
    }
}
```

`Setup` gains one line, after the `SceneRenderer`'s `Initialize`:

```cpp
    CreatePlates();                                                        // section 2
```

## 3. A pipeline of the demo's own, and the frame

**This is `HorizonTypes.h`, the flat shaders, `CreateFlatPipeline`, the first
`Projection`, and the plates in `Record`.**

### Why a pipeline of its own

The plates could go through the `SceneRenderer`'s mesh pipelines, but those
light and texture what they draw, and here a plate should read as exactly its
colour in a screenshot. The engine's mesh shaders have debug views
(`ShadingMode`), and a fifth one, "flat", would do it; but then the colour rule would live in the engine's
shader, and this demo's later chapters change it: Chapter 37 adds the sun and
haze to it. So the demo draws through a pipeline of its own, the *flat*
pipeline, which is the demo's to grow.

It still uses everything else the `SceneRenderer` does for a mesh: the shared
vertex and index buffers, `PrepareDraws`' batching, and `RecordBatches`, which
binds the geometry and calls back once per run of draws that share a material
(Chapter 19 sections 5 and 6). What a demo's pipeline can use is set 0, which
the `SceneRenderer` hands out with `FrameSetLayout` and `BindFrameSet`, and push
constants: each material's set 1 is the `SceneRenderer`'s own. So the colour
travels as a push constant, one per run, from the table `AddFlatMaterial`
fills.

The push constant is one `vec4`, in a C++/GLSL twin header as every demo's are
(Chapter 10 section 8). It starts small; the next chapters add the terrain's
parameters to the same file. Add its include to `HorizonDemo.cpp` now:

```c
/* Shaders/Horizon/HorizonTypes.h - the Horizon demo's C++/GLSL twins (Chapter 35). GLSL includes it as
   "HorizonTypes.h", C++ as "Horizon/HorizonTypes.h". */
#ifndef PF_HORIZON_TYPES_H
#define PF_HORIZON_TYPES_H

#include "SharedShaderTypes.h"   /* the vec4 alias, on the C++ side */

#ifdef __cplusplus
    namespace pf::demos::horizon {
    using shared::vec4;
#endif

/* The flat pipeline's push constants: one material's color, for one run of draws (section 3). */
struct FlatDraw
{
    vec4 baseColor;   /*  0  linear rgb; alpha unused */
};

#ifdef __cplusplus
    static_assert(sizeof(FlatDraw) == 16, "FlatDraw layout drifted.");
    }
#endif

#endif
```

The vertex shader is Chapter 19's mesh vertex shader cut down to the position:
the model matrix from the instance buffer at set 0 binding 2, which
`PrepareDraws` fills, and the camera's view-projection from binding 0. The
fragment shader writes the colour as it is, with no light:

```glsl
// Shaders/Horizon/Flat.vert.glsl - Chapter 35 section 3: Chapter 19's mesh vertex shader, cut down to the
// position.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // set 0 binding 0: frame.viewProjection

layout(location = 0) in vec3 inPosition;   // the first 12 bytes of Chapter 11's 48-byte Vertex

// Set 0 binding 2: every instance PrepareDraws wrote this frame (Chapter 19 section 3).
layout(std430, set = 0, binding = 2) readonly buffer InstanceBuffer { InstanceData instances[]; };

void main()
{
    vec4 world  = instances[gl_InstanceIndex].model * vec4(inPosition, 1.0);
    gl_Position = frame.viewProjection * world;
}
```

```glsl
// Shaders/Horizon/Flat.frag.glsl - Chapter 35 section 3: one color per material and no light, so a plate
// reads as exactly its color in a screenshot.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "HorizonTypes.h"   // FlatDraw

layout(push_constant) uniform FlatBlock
{
    FlatDraw draw;
};

layout(location = 0) out vec4 outColor;

void main()
{
    outColor = vec4(draw.baseColor.rgb, 1.0);
}
```

### The pipeline

The pipeline reads only the position out of Chapter 11's 48-byte `Vertex`, so
it declares one attribute on the full stride. It takes the cull mode per run, as
the `SceneRenderer`'s own pipelines do: `RecordBatches` leaves the cull mode to
its callback, and a plate is double-sided, so its runs cull nothing. It tests
and writes depth with `GraphicsPipelineDesc`'s default compare, `LESS`,
Chapter 10's (section 6 changes that one line), and declares the pass's sample
count (Chapter 18 section 6):

```cpp
InitializationResult HorizonDemo::CreateFlatPipeline()
{
    // Set 0 is the scene renderer's: the camera, and the instance buffer PrepareDraws fills.
    // The push constant is one run's color.
    const VkDescriptorSetLayout setLayout = m_sceneRenderer.FrameSetLayout();
    const VkPushConstantRange   pushRange{
        .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT,
        .offset     = 0,
        .size       = sizeof(FlatDraw),
    };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 1,
        .pSetLayouts            = &setLayout,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_flatLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the flat pipeline.");
    }

    // Chapter 11's vertex buffer, of which the shader reads only the position.
    const VkVertexInputBindingDescription binding{
        .binding   = 0,
        .stride    = sizeof(scene::Vertex),
        .inputRate = VK_VERTEX_INPUT_RATE_VERTEX,
    };
    const VkVertexInputAttributeDescription position{
        .location = 0,
        .binding  = 0,
        .format   = VK_FORMAT_R32G32B32_SFLOAT,
        .offset   = offsetof(scene::Vertex, position),
    };

    // The cull mode per run, as SceneRenderer's own pipelines take it (Chapter 19 section 6).
    const VkDynamicState dynamicStates[] = { VK_DYNAMIC_STATE_CULL_MODE };
    const GraphicsPipelineDesc desc{
        .vertexShader     = "Horizon/Flat.vert.spv",
        .fragmentShader   = "Horizon/Flat.frag.spv",
        .vertexBindings   = { &binding, 1 },
        .vertexAttributes = { &position, 1 },
        .colorFormats     = { &m_context.formats.color, 1 },
        .depthFormat      = m_context.formats.depth,
        .depthTest        = true,
        .depthWrite       = true,
        .frontFace        = VK_FRONT_FACE_COUNTER_CLOCKWISE,
        .dynamicStates    = dynamicStates,
        .layout           = m_flatLayout,
        .samples          = m_context.formats.samples,
    };
    m_flatPipeline = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
    if (m_flatPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the flat pipeline failed.");
    }
    return InitializationResult::success();
}
```

`Setup` gains its second line, under `CreatePlates();`:

```cpp
    if (auto result = CreateFlatPipeline(); !result) { return result; }   // section 3
```

### The frame

`Record` takes its projection from a function of the demo's own. For now that
function returns Chapter 10's lens; section 6 rewrites its body:

```cpp
// Section 3. Record takes its projection from here: Chapter 10's lens, until section 6 rewrites it.
glm::mat4 HorizonDemo::Projection(float aspect) const
{
    return m_camera.Projection(aspect);
}
```

`Record` gains two steps before the pass and one inside it. The first two go
at the top, between the `commandBuffer` line and section 1's clear colour: the
camera goes into this frame slot's buffer, as Chapter 10 section 7 does (the
block also declares `extent` and `frameData`, which sections 6 and 7 use), and
`PrepareDraws` sorts and batches the plates into this slot's instance buffer,
before anything binds set 0 (Chapter 19 section 5):

```cpp
    // Section 3: the camera, written now: after the fence wait, into this slot's buffer (Chapter 10 section 7).
    const VkExtent2D extent = frame.targets.extent;
    const float      aspect = static_cast<float>(extent.width) / static_cast<float>(extent.height);
    shared::FrameData frameData{};
    frameData.view           = scene::viewMatrix(m_cameraTransform.Matrix());
    frameData.projection     = Projection(aspect);
    frameData.viewProjection = frameData.projection * frameData.view;
    frameData.cameraPosition = glm::vec4(m_cameraTransform.translation, 1.0f);
    frameData.time           = m_time;
    m_sceneRenderer.WriteFrameData(frame.frameIndex, frameData);

    // Section 3: the plates, sorted and batched into this slot's instance buffer, before anything binds set 0.
    m_sceneRenderer.PrepareDraws(frame.frameIndex, m_plates);
```

Between `beginScenePass` and `endScenePass`, the plates: the flat pipeline, set
0 bound with the flat layout, and `RecordBatches` with a callback that sets
each run's cull mode and pushes its colour:

```cpp
    // Section 3: the plates, through Chapter 19's batches, with this demo's pipeline.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_flatPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_flatLayout, frame.frameIndex);
    m_sceneRenderer.RecordBatches(commandBuffer, frame.frameIndex, DrawList::Scene,
                                  [&](VkCommandBuffer cb, const DrawRun& run) {
        vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
        const FlatDraw draw{ .baseColor = m_materialColors[run.material] };
        vkCmdPushConstants(cb, m_flatLayout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(draw), &draw);
    });
```

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Horizon`. Four pairs
stand against the pale blue, left to right:

- **1 km, red:** a red square in a white frame, with or without thin white
  stripes down one side.
- **5 km, yellow:** yellow with white stripes running through it, top to bottom.
- **10 km, green:** green with a broad white stripe.
- **30 km, blue:** about half white.

The exact pattern depends on how your GPU rounds (section 5), so it differs
from GPU to GPU; these are what one GPU shows. The 1 km pair can differ in
kind: a clean red square on some GPUs, speckled on others. The three far pairs
fight on every GPU, from stripes to solid white. Click once on the scene, then
fly a little with WASD and watch them: they jump and crawl as the camera
moves. That is z-fighting, two surfaces taking turns to win the depth
test, and the depth buffer cannot tell the far pairs apart: past about 1.3 km
it cannot tell apart two surfaces a metre from each other. Part 2 works out
why, and fixes it for good. Keep this state: the Exit check at the end of the
chapter runs this build beside the finished demo, and Part 2 rewrites
`Projection`, `CreateFlatPipeline`, and `Record` in place. Commit the source as
it stands (`git add` the new files, then `git commit`), and a checkout of that
commit gets this build back.

---

# Part 2 — Floats, and reversed depth (sections 4-8)

Part 2 starts with how a computer stores a number like 4,817.25, which limits
both where the camera may go and what depth can tell apart. Then it stores
depth the other way round inside this demo, brings the sky back, and lists what
reversed depth means for code this demo does not use yet.

## 4. Floats, and how far the camera may go

**This is `KeepCameraInBounds`, its call in `Update`, and the end of
`DrawCameraControls`.**

### How far apart floats are

A `float` stores a number as 24 binary digits times a power of two. The first
of those digits is always 1 for a normal float, so it is not stored: 23 stored
bits give 2²³ values between each pair of powers of two. Between 4,096 (2¹²)
and 8,192 (2¹³) those 2²³ floats are evenly spaced, so the gap between
neighbours there is 4,096 / 2²³ = 2⁻¹¹ m, about half a millimetre. Every float
between 4,096 and 8,192 is a multiple of half a millimetre, and anything in
between is rounded to the nearest one. In general, for a number *x* between 2ᵏ
and 2ᵏ⁺¹:

$$
\text{spacing}(x) = 2^{k-23}
$$

A worked example: 10,000 lies between 8,192 (2¹³) and 16,384 (2¹⁴), so the
spacing there is 2¹³⁻²³ = 2⁻¹⁰ m, 0.98 mm. At 1 m it is 2⁻²³ m, a tenth of a
micrometre. The spacing is always between 2⁻²⁴ and 2⁻²³ of the number itself,
about six to twelve parts in a hundred million. Floats keep the same *relative*
precision at every size; the absolute gap grows with the number.

### What that does to positions

Every position in the engine is a float in world coordinates: a `Transform`'s
translation, the model matrix in the instance buffer, and the view matrix,
whose last column holds the camera's position, negated and turned into view
space, so that multiplying by it subtracts the camera's position (Chapter 10
section 4). The vertex shader multiplies one by the other. For a vertex one
metre in front of a camera 5 km from the origin, that multiplication subtracts
two numbers near 5,000, each known only to the nearest half millimetre, to get
a number near 1. The answer carries the rounding of both: errors of about half
a millimetre, in a distance of one metre. On a 1440p screen, one metre seen
from one metre away spans about 1,250 pixels, so half a millimetre is over half
a pixel. And the errors change as the camera moves, so close geometry shakes.

The table is the worst of 20,000 random cameras per row, each looking at a
vertex a metre ahead: the view and projection built and multiplied in `float`,
as the CPU and the vertex shader do, against the same steps in `double`, the
difference scaled to pixels at 1440 rows (`REFERENCE.md`'s row 35 has the
method whole):

| Camera's largest coordinate | Spacing there | Worst error |
| --- | --- | --- |
| 1 km | 0.06 mm | 0.2 px |
| 5 km | 0.49 mm | 1.1 px |
| 10 km | 0.98 mm | 2.2 px |

That is about twice the half-pixel above, because the worst case over many
directions also collects the rounding of the matrix product itself; the error
doubles again with every doubling of the distance.

Far geometry has the same problem and does not care. A vertex 30 km away is
stored to the nearest 2 mm, and 2 mm at 30 km is a fifteen-millionth of the
distance: nothing on any screen. What matters is an error compared with the
distance from the camera, which is why distance costs the far view no position
precision, while a far-travelled camera does: it is the *near* things that
shake. Depth precision is another matter, and section 5's.

### The travel limit

So the camera stays within 5 km of the origin, measured across the ground.
Inside that disc every coordinate of the camera, and of anything close to it,
is below 8,192, where the spacing is half a millimetre and close geometry is
off by at most about a pixel at 1440p. One step past 8,192 m the spacing
doubles. Any limit between 4,096 and 8,192 m gives the same precision, since
the spacing is the same throughout that range; 5 km is a round number that
leaves about 3 km of room for the things around the camera, which stand
further out than the camera itself. Travelling further needs a floating origin,
which "Where to go from here" describes. The limit is a constant, below the
plates' and above `pairDirection`:

```cpp
// Section 4: how far the camera may go from the origin, across the ground.
constexpr float TRAVEL_LIMIT = 5000.0f;   // metres
```

`KeepCameraInBounds` runs after the controller has moved the camera, every
frame. Outside the disc, it scales the camera's horizontal position back onto
its edge along the same line through the origin, so flying into the edge slides
along it rather than stopping dead (section 7 adds a ceiling at its end):

```cpp
// Section 4. Back inside the disc where float positions stay precise; section 7: and under the clouds.
void HorizonDemo::KeepCameraInBounds()
{
    glm::vec3& position = m_cameraTransform.translation;
    const float fromOrigin = std::sqrt(position.x * position.x + position.z * position.z);
    if (fromOrigin > TRAVEL_LIMIT)
    {
        const float pullBack = TRAVEL_LIMIT / fromOrigin;   // back onto the circle, along the same line
        position.x *= pullBack;
        position.z *= pullBack;
    }
}
```

`Update` calls it straight after the controller:

```cpp
    m_controls.Update(input.deltaSeconds, m_cameraTransform);
    KeepCameraInBounds();   // section 4
```

The panel shows how far out the camera is, and the spacing at its largest
coordinate, so you can watch the half millimetre arrive as you fly out past
4,096 m. At the end of `DrawCameraControls`:

```cpp
    // Section 4: how far out the camera is, and the gap between its largest coordinate and the next float.
    const float fromOrigin = std::sqrt(position.x * position.x + position.z * position.z);
    ImGui::Text("From the origin  %.0f of %.0f m", fromOrigin, TRAVEL_LIMIT);
    const float largest = std::max({ std::abs(position.x), std::abs(position.y), std::abs(position.z) });
    const float spacing = std::nextafter(largest, std::numeric_limits<float>::infinity()) - largest;
    ImGui::Text("Float spacing here  %.3f mm", static_cast<double>(spacing) * 1000.0);
```

`std::nextafter` returns the next float after its first argument in the
direction of its second; minus the number itself, that is the spacing.

## 5. Why the far plates fight

### How much depth changes per metre

Chapter 10 section 2 worked out the depth a surface at distance *d* gets, with
near plane *n* and far plane *f*:

$$
\text{depth} = \frac{f}{f-n}\left(1 - \frac{n}{d}\right) \approx 1 - \frac{n}{d}
$$

This lens has *n* = 0.1 m and *f* = 200 km, not Chapter 10's 500 m. Here
*f*/(*f* - *n*) is 1.0000005, so the depth is 1 - *n*/*d* to six decimal
places: 0.9999 at 1 km, 0.99999 at 10 km. Move the surface a little further
away, by Δ, and the depth goes up by

$$
\frac{n}{d} - \frac{n}{d+\Delta} = \frac{n\,\Delta}{d\,(d+\Delta)} \approx \frac{n}{d^2}\,\Delta
$$

A worked example: at 10 km, moving 1 m changes the depth by
0.1 / 10,000² = 10⁻⁹, one billionth.

### Floats near 1

Section 4's rule says how far apart floats are just under 1: between 0.5 and 1
the spacing is 2⁻²⁴, about 6 × 10⁻⁸. A surface has to move until its depth
changes by 2⁻²⁴ before the depth buffer stores anything different, and from the
change per metre above, that is

$$
\Delta_{\min} \approx \frac{d^2 \cdot 2^{-24}}{n}
$$

A worked example: at 10 km, 10,000² × 6 × 10⁻⁸ / 0.1 = **60 m**. Two plates a
metre apart at 10 km store the same depth: a tie. For the four pairs:

| Pair | Smallest step the depth can show | Against a 1 m gap |
| --- | --- | --- |
| 1 km | 0.6 m | separate, with little to spare |
| 5 km | 15 m | a tie |
| 10 km | 60 m | a tie |
| 30 km | 536 m | a tie |

The step reaches 1 m at about 1.3 km. Chapter 10 section 2 found 6 mm at 100 m,
and that was the same formula: precision falls with the *square* of the
distance, and the far view lives where it has fallen furthest.

In a tie, the white plate, drawn first, stays (section 2). But the GPU works out
each depth with rounding of its own, in the matrix multiply, the divide by *w*,
and the interpolation across the triangle, so whether the two plates come out
equal, or the front one a step nearer, changes from pixel to pixel and from one
camera position to the next. That is the stripes, and the flicker.

The pattern is the GPU's rounding, so it differs from one GPU to the next. The
table's 1 km row is the borderline: a 1 m gap is about one step there, little
enough that the GPU's rounding can take it back, so the pair may stay a clean
red square or speckle, depending on the GPU. One software GPU left it red; a
desktop RTX card speckled it. The three far pairs have no room at all, and
fight on every GPU.

Chapter 10's lever was the near plane, since the step is proportional to 1/*n*.
A near plane at 10 m would make it a hundred times smaller, 60 cm at 10 km, and
cut away everything within 10 m of the camera: no good for a camera that flies
down to the ground.

### Floats near 0

The trouble is where the far view's depths land: near 1, where the gap between
floats is a fixed 6 × 10⁻⁸. Near 0, floats are far denser, because their gap
shrinks with the number (section 4). Chapter 10's aside on reverse-Z named the
fix: store depth the other way round, the near plane at 1 and the far plane at
0, so that distant surfaces land near 0. Swapping the roles of *n* and *f* in
the projection gives the reversed depth:

$$
\text{depth}_{\text{rev}} = \frac{n}{f-n}\left(\frac{f}{d} - 1\right) \approx \frac{n}{d}
$$

It is exactly 1 minus the standard depth; nothing about the geometry changed,
and depth still changes by about *n*/*d*² per metre. What changed is the gap
between floats where the far view's depths now fall. At 10 km:

| | Depth stored | Change per metre | Gap to the next float there | Smallest step |
| --- | --- | --- | --- | --- |
| Standard | 0.99999 | 10⁻⁹ | 2⁻²⁴ ≈ 6 × 10⁻⁸ | 60 m |
| Reversed | about 0.00001 | 10⁻⁹ | 2⁻⁴⁰ ≈ 9 × 10⁻¹³ | 0.9 mm |

The same change per metre, and a gap 2¹⁶, about 65,000, times smaller.
Because a float's gap is at most 2⁻²³ of the number itself, and the depth is
about *n*/*d*, the step is at most

$$
\Delta_{\min} \approx \frac{(n/d) \cdot 2^{-23}}{n/d^2} = d \cdot 2^{-23}
$$

A worked example: at 10 km, 10,000 × 1.2 × 10⁻⁷ = **1.2 mm** at most. The
table's 0.9 mm is the exact figure there; the bound is the one to remember,
because it holds at every distance. The 1/*d* curve that squeezed the standard
depth toward 1 and the float's density near 0 cancel, and what is left is a
step that grows only in proportion to the distance, as the float's own
precision does. For the four pairs the steps are
0.07, 0.45, 0.91, and 2.05 mm, so a metre between two plates is 13,730, 2,199,
1,100, and 488 steps. With the standard depth the same metre is 1, 0, 0, and 0
steps.

Two things this depends on:

- **A floating-point depth format.** The engine's depth is `D32_SFLOAT`
  (Chapter 10 section 9). An integer format such as `D24` spaces its values
  evenly from 0 to 1, so it has no dense end to put the far view in, and
  reversing it gains almost nothing. *Just Cause 2* reversed its depth, but
  only its console versions had a floating-point depth buffer to gain from it
  (Persson, in Sources).
- **Computing the reversed depth directly.** 1 minus the standard depth would
  throw the precision away again: worked in float, 1 - 0.99999 is only as
  precise as the 0.99999 was, to within 6 × 10⁻⁸, which at 10 km is a 60 m step
  all over again. The reversed projection computes *n*/*d* straight from the
  matrix, small and precise.

> **Jump:** everything in the engine assumes depth runs from 0 near to 1 far:
> the clear to 1.0, `LESS` meaning "nearer", the sky at depth 1.0 meaning
> "nothing drawn here". From the next section on, inside this demo, all of
> that runs backwards: the far plane is 0, `GREATER` means nearer, and 1.0 is
> the near plane. The demo does not go back. Keep both pictures in mind, for
> the engine's code is still built on the old one: section 7 meets the first
> piece of it, the sky, and section 8 lists the rest.

## 6. Reversed depth in the frame

**This is `Projection` rewritten, one line in `CreateFlatPipeline`,
`clearDepth` and its call in `Record`, and the depth readout (`stepsApart`,
`storedDepth`, `DrawDepthReadout`).**

Three things change in the frame: the projection, the compare, and the value
depth starts from. They change for good: from here the demo draws with reversed
depth, and the Part 1 build you kept is the only place in this demo where the
engine's depth is still on screen.

### The projection

`glm::perspective` maps whatever it is given as the near distance to depth 0 and
the far distance to depth 1. Given the two the other way round, 200 km first and
0.1 m second, it maps 200 km to 0 and 0.1 m to 1: section 5's reversed depth,
from the same function. Then the Y flip that `Camera::Projection` would have
made (Chapter 10 section 2), because this matrix does not come from there.
`Projection` becomes:

```cpp
// Section 3. Record takes its projection from here. Section 6: the same lens with near and far swapped, so
// near lands on depth 1 and far on 0; then Chapter 10 section 2's Y flip, which Camera::Projection would
// have made.
glm::mat4 HorizonDemo::Projection(float aspect) const
{
    glm::mat4 projection = glm::perspective(m_camera.verticalFov, aspect, m_camera.farPlane, m_camera.nearPlane);
    projection[1][1]     = -projection[1][1];
    return projection;
}
```

Here is section 5's depth coming out of it. The matrix's third row (index 2)
holds *n*/(*f* - *n*) = 5 × 10⁻⁷ in the column that multiplies *z*, and
*n f*/(*f* - *n*) = 0.1 in the last one, which multiplies 1. View space looks
along -Z, so a point 10 km ahead has *z* = -10,000, and its clip-space *z* is
5 × 10⁻⁷ × (-10,000) + 0.1 = 0.095. Its *w* is the distance, 10,000, so its
depth is 0.095 / 10,000 = 9.5 × 10⁻⁶. That is section 5's *n*/*d* = 0.00001
times (1 - *d*/*f*) = 0.95, the factor the approximation left out: close to 1
while the far plane is twenty times further away than the point.

### The compare

Nearer is now larger, so a fragment should pass when its depth is *greater*
than what is there. `GraphicsPipelineDesc` has a field for the compare,
`depthCompare`, which section 3 left at its default, `LESS`. This pipeline only
ever draws with reversed depth, so the compare is plain pipeline state, set
once, under `.depthWrite` in `CreateFlatPipeline`; the cull mode stays the
dynamic state it was. The sky is not affected: it is a pipeline of its own,
with a compare of its own (section 7).

```cpp
        .depthCompare     = VK_COMPARE_OP_GREATER,   // section 6: depth runs the other way, so nearer is larger
```

Leave the line out and nothing complains. A `LESS` test against a depth buffer
cleared to 0 fails for every fragment, which is legal Vulkan: the plates are
simply never drawn, and validation has nothing to report. The Exit check at the
end of the chapter does this on purpose, so that you have seen what the
mistake looks like.

### The clear

The far plane is now depth 0, so the depth buffer should read 0 wherever
nothing has been drawn, for the plates to be tested against, and the engine's
scene pass clears it to 1.0. That clear is the engine's
contract with every other demo (Chapter 10 section 9), and `beginScenePass` is
the engine's, so the demo leaves it alone and clears again, inside the pass,
with `vkCmdClearAttachments`: a clear recorded among the draws, which sets an
attachment, here the depth, to one value over a rectangle, here the whole
target. It goes at file scope, above the `namespace` line, as its comment says:

```cpp
// File scope, above the namespace block. Section 6: the depth attachment set to one value everywhere,
// from inside the rendering scope.
static void clearDepth(VkCommandBuffer commandBuffer, VkExtent2D extent, float depth)
{
    const VkClearAttachment attachment{
        .aspectMask = VK_IMAGE_ASPECT_DEPTH_BIT,
        .clearValue = { .depthStencil = { depth, 0 } },
    };
    const VkClearRect rect{ .rect = { { 0, 0 }, extent }, .baseArrayLayer = 0, .layerCount = 1 };
    vkCmdClearAttachments(commandBuffer, 1, &attachment, 1, &rect);
}
```

In `Record`, right after `beginScenePass`, above the plates:

```cpp
    // Section 6: the far plane is depth 0. One clear inside the scope, and everything drawn after it is
    // tested against 0.
    clearDepth(commandBuffer, extent, 0.0f);
```

**No barrier.** Inside one rendering scope, depth is tested and written in the
order the draws were recorded: that is *rasterization order*.
`vkCmdClearAttachments` is not a transfer command like
`vkCmdClearDepthStencilImage`; the specification puts its depth writes in that
same order, as if a draw had made them. Chapter 04 section 5's three questions
agree. What is written: the depth, by the clear. Who reads it next: the
plates' depth tests, later in the same order. Does the layout change: no. So
no barrier is needed. At 4x MSAA the depth the pass tests is the multisampled
attachment (Chapter 18 section 4), and the clear sets every sample of it.

### The steps between the plates

The panel gains a group at its top, above the Camera group. For each pair it
shows how many steps apart the front and back plates store their depths: the
numbers from the end of section 5, worked out by the program. They belong to
the pairs as set out from the viewpoint, so they do not change as the camera
moves.

**Counting steps.** A float's 32 bits are its sign, then its power of two, then
its 23 fraction bits, in that order, from the top. For positive floats, reading
the same bits as a whole number gives numbers that grow as the floats do, one
at a time: the next float after 1.0 (bits `0x3F800000`) has the bits
`0x3F800001`. Chapter 22 section 8 used the same fact to find a float range
with integer atomics. So the difference of the two bit patterns, read as whole
numbers, counts the steps from one float to the other: 1 for two neighbours, 0
for a tie. `std::bit_cast` (C++20, `<bit>`) reads them. Like `clearDepth`,
this goes at file scope, above the `namespace` line, as its comment says:

```cpp
// File scope, above the namespace block. Section 6: how many steps apart two depths are. Positive floats
// are ordered like their bit patterns read as whole numbers, so the difference counts the steps.
static uint32_t stepsApart(float a, float b)
{
    const uint32_t bitsA = std::bit_cast<uint32_t>(a);
    const uint32_t bitsB = std::bit_cast<uint32_t>(b);
    return bitsA > bitsB ? bitsA - bitsB : bitsB - bitsA;
}
```

The depths it compares are worked out on the CPU for a surface `distance`
metres straight ahead: section 5's reversed formula in `double`, then rounded
once to `float`, the format's own rounding. It goes inside the namespace, below
`pairDirection`:

```cpp
// Section 6: the depth a surface `distance` metres in front of the camera stores: section 5's reversed
// formula, worked in double so that the only rounding is the float's own.
static float storedDepth(double distance)
{
    const double n = NEAR_PLANE;
    const double f = FAR_PLANE;
    return static_cast<float>(n / (f - n) * (f / distance - 1.0));
}
```

The group is one line per pair, in the pair's colour. ImGui's colours are sRGB,
so the linear colour is converted first (Chapter 08 section 4):

```cpp
// Section 6: how many steps apart each pair's two plates store their depths.
void HorizonDemo::DrawDepthReadout()
{
    ImGui::SeparatorText("Depth");
    ImGui::TextUnformatted("Steps apart, front plate to back:");
    for (const PlatePair& pair : PLATE_PAIRS)
    {
        const uint32_t  steps = stepsApart(storedDepth(pair.distance), storedDepth(pair.distance + PLATE_GAP));
        const glm::vec3 shown = scene::linearToSrgb(pair.color);   // ImGui's colors are sRGB
        ImGui::TextColored(ImVec4(shown.r, shown.g, shown.b, 1.0f), "  %-5s  %u", pair.label, steps);
    }
}
```

`DrawPanel` calls it first, above `DrawCameraControls();`:

```cpp
        DrawDepthReadout();     // section 6
```

The readout counts each pair as if it stood straight ahead, which is what
section 5's numbers are. The real pairs stand off to the side, where the depth
is the distance along the line times the cosine of the angle (0.95 at 18°), so
what the depth buffer holds for them differs from the readout's counts by about
5% at most: the same story.

Run it: the stripes of Part 1 are gone, and the readout shows 13,730, 2,199,
1,100, and 488 steps. The engine's depth, counted the same way, gave the four
pairs 1, 0, 0, and 0, which is Part 1's picture (section 5).

## 7. The sky comes back

**This is the sky in `Setup` and `Record`, the sun it is baked with, and the
camera's ceiling.**

The far view needs a sky behind it, and the engine has one: Chapter 23's `Sky`,
with Chapter 28's clouds in it. The demo has held one since the header,
`m_sky`, and `Teardown` already shuts it down. `Setup` initializes it after the
flat pipeline, and hands its image-based light to set 0, bindings 10 to 12, as
every demo with the sky does (Chapter 24 section 4). The flat shaders do not
read that light yet; the next chapter's haze does:

```cpp
    // Section 7: the sky, and its light in set 0 for the shaders that will read it (Chapter 24).
    if (auto result = m_sky.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats); !result)
    {
        return result;
    }
    m_sceneRenderer.SetImageBasedLighting(m_sky.Lighting());
```

### The sun

The sky is baked from a sun. This demo needs one fixed sun, so it is a
constant: the direction sunlight travels from a sun 35° above the horizon,
behind the camera's right shoulder at the start, so the view along -Z is open
sky. It is what Chapter 25 section 2's `sunTravelDirection(35.0f, 160.0f)`
returns, written out. Its irradiance, which `Record` passes beside it, is π
times Chapter 11's `sunColor`, (0.90, 0.85, 0.80), because that colour was
defined as irradiance divided by π (Chapter 15 section 9). The direction is the
constant, at the end of the constants, above `pairDirection`:

```cpp
// Section 7: the direction sunlight travels, from 35 degrees above the horizon, behind the camera's right
// shoulder at the start. Chapter 25 section 2's sunTravelDirection(35.0f, 160.0f), worked out.
constexpr glm::vec3 SUN_TRAVEL{ -0.280166566f, -0.57357645f, -0.769751132f };
```

### Drawn where Chapter 23 draws it

`Sky::Update` bakes the sky again only when something changed, outside the
scene pass (Chapter 23 section 7). It takes what the chapters since have given
it: the command buffer; the frame index, which picks the filter's timer slot
(Chapter 24 section 4); the sky's settings, `frame.sky`, which the engine keeps
(Chapter 23 section 8); and a `SkyInputs`, which carries the sun and, from
Chapter 28, the camera's position and the time that the clouds need. In
`Record`, below `PrepareDraws` and above the clear colour:

```cpp
    // Section 7: Chapter 23's sky, baked again only if it changed, before the scene pass. Chapter 28's
    // clouds in it need the camera and the time.
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
                 { .sunDirection   = SUN_TRAVEL,
                   .sunIrradiance  = glm::pi<float>() * glm::vec3(0.90f, 0.85f, 0.80f),
                   .cameraPosition = m_cameraTransform.translation,
                   .time           = m_time });
```

Which sky shows is one setting for the whole engine (Chapter 23 section 8), and
it starts **Off** on every run. In the Tone mapping window, open the **Sky**
header, set **Mode** to **Sun sky**, and close the header again: open, the
window grows down over the right of the screen at 1280 x 720, where the 10 and
30 km pairs are. Then draw the sky where Chapter 23 section 7 draws it in every
other demo, last, just above `endScenePass(commandBuffer);`:

```cpp
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);
```

Run it, with Sun sky on. The plates hold, and there is no sky: the pale blue
clear colour shows everywhere around them.

The sky is drawn at depth 1.0 and tested with `LESS_OR_EQUAL`, which with the
engine's depth means "wherever nothing nearer was drawn". Here, by the time it
is drawn last the depth buffer holds 0 where nothing was drawn, and the plates'
depths where they were: 1.0 is not less than or equal to 0, nor to any plate's
depth. It passes nowhere.

### Drawn first

So the sky goes **first**, right after `beginScenePass`, while the depth buffer
still holds the pass's 1.0 everywhere: it passes at every pixel, writes no
depth, and paints the whole target. Then the clear to 0, then the plates with
`GREATER`. Move the line up, to just under `beginScenePass`, above section 6's
`clearDepth` call:

```cpp
    // Section 7: the sky first, while the depth is still the 1.0 the pass cleared it to. Its vertex shader puts
    // it at depth 1.0 and it tests LESS_OR_EQUAL, so it passes at every pixel; it writes no depth.
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);
```

Run it again: the sky and its clouds are back, behind the four plates.

Drawing it first costs what Chapter 23 section 7 avoided by drawing it last:
its fragment shader now runs for every pixel, including the ones the scene then
covers. It is one cube lookup per pixel, and one more for the clouds: small
beside what the next chapters draw, and Chapter 24 section 9's GPU timers
measure it when it matters.

The sky is handed the frame's projection, the reversed one. It uses that matrix
only to turn each pixel into a direction, by un-projecting the pixel at depth 0
(Chapter 23 section 1). Under this matrix depth 0 is the far plane, 200 km out;
under the engine's own it is the near plane. Either way the point lies on the
same line from the camera through that pixel, so the direction is the same. The
sky's depth does not come from the matrix: its vertex shader puts every pixel
at depth 1.0 (Chapter 23 section 1), and its pipeline tests that with
`LESS_OR_EQUAL` against what the pass cleared, and writes no depth of its own.

The sky's tests join section 6's rasterization order, before the clear, so
there is still no barrier, and the clear stays inside the scope for a second
reason: the sky must test against 1.0 first, in the same pass.

```text
 depth, in the order the scope records it:
   the pass clears it to 1.0
   the sky tests LESS_OR_EQUAL against 1.0, and writes nothing
   vkCmdClearAttachments sets it to 0
   the plates test GREATER against 0, and write their own
```

### The ceiling

Chapter 28's clouds are a layer from 1,500 m up (its section 3), and the cube
they are drawn into shows the layer from underneath: section 1 of that chapter
keeps the eye below the base, and section 5's march assumes it. A camera above
1,500 m would see clouds drawn as if from below. Staying under 1,400 m keeps
them right, and the island's peaks in the next chapter stay under it too. The
constant goes right after `TRAVEL_LIMIT`, and `KeepCameraInBounds` gains its
last line, after the `if` block, at the end of the function:

```cpp
// Section 7: how high it may go: under Chapter 28's cloud layer, which starts at 1,500 m.
constexpr float CEILING = 1400.0f;   // metres
```

```cpp
    position.y = std::min(position.y, CEILING);   // section 7
```

Fly up and look around: the camera's height stops at 1,400 m.

### The frame, as this chapter leaves it

```text
 FrameData: view, Projection() (sec. 3, 6), viewProjection, camera     WriteFrameData
 the plates, batched into this slot's instance buffer (sec. 3)          PrepareDraws
 the sky's bake, if anything changed (sec. 7, Chapter 23)               Sky::Update
 beginScenePass: color cleared, depth cleared to 1.0 (sec. 1)           (Chapter 10, 18)
     the sky, at depth 1.0, LESS_OR_EQUAL, writing none (sec. 7)        Sky::Draw
     depth to 0, in rasterization order (sec. 6)                        vkCmdClearAttachments
     the plates: flat pipeline, set 0, GREATER (sec. 3, 6)              RecordBatches
 endScenePass; the scene target to the composite (Chapter 08)           handBackSceneTarget
```

## 8. What reversed depth means for everything else

The engine did not change, so everything that knows about depth still assumes
the standard convention. Inside this demo, that is a list of things to watch:

- **Every pipeline that draws after the clear** needs the reversed projection
  and a compare of `GREATER`, or `GREATER_OR_EQUAL`: the flat pipeline's
  `depthCompare`. The `SceneRenderer`'s own mesh pipelines compare with `LESS`
  and would draw nothing here, so the next chapters' pipelines are written like
  the flat one.
- **The sky** needs no change, only its place: before the clear (section 7).
- **Code that reads depth and takes 1.0 to mean "nothing here"** must not be
  borrowed as it is: Chapter 22 section 6's lighting pass skips pixels at 1.0,
  Chapter 26 section 9's occlusion culling keeps the *largest* depth of a block
  as its farthest, and Chapter 18 section 3's depth resolve with `MAX` keeps
  the *nearest* sample once depth is reversed. Nothing in this demo reads depth
  after the scene pass; a later reader would flip its test, or resolve with
  `MIN` where the GPU offers it.
- **Shadows** (Chapter 17) fit their cascades from the near plane to
  `std::min(settings.maxDistance, camera.farPlane)` (Chapter 17 section 2's
  `FitCascades`), and `maxDistance` is 120 m by default, so a 200 km far plane
  never stretches them. They
  write standard depth into images of their own, which this demo's reversal
  does not touch; Chapter 37 brings them to this demo.
- **Frustum culling** (Chapter 12 section 9) needs nothing. Its near plane is
  "depth above 0" and its far plane "depth below 1"; reversed, the two
  conditions trade places, and the six planes are the same six.

## Checkpoint

Run with `--demo Horizon`, with the sky on (section 7: **Sun sky**, then close
the Sky header). All four pairs are coloured squares in white frames under the
sky, and the readout shows hundreds or thousands of steps between the plates of
every pair. Click once on the scene, then fly to the
edge of the disc and up: the camera slides along the edge 5 km from the origin,
and stops climbing at 1,400 m. The Exit check below has the exact numbers, and
sets this run beside Part 1's.

---

## If something goes wrong

| Symptom | Cause |
| --- | --- |
| The sky is gone, and the clear colour shows behind the plates | The sky is drawn after the clear to 0, or last, where Chapter 23 draws it (section 7) |
| Only the sky, no plates | The clear to 0 is missing: nothing passes `GREATER` against the pass's 1.0 |
| No plates, and validation is silent | The flat pipeline's compare is still `LESS`, the default: `CreateFlatPipeline` lost its `.depthCompare` line. Nothing is less than the cleared 0, and no rule is broken, so there is no message (section 6) |
| Every pair white, or nearly | `Projection` passes near and far in Chapter 10's order: the depth is standard, and `GREATER` keeps the *farthest* surface, the back plates |
| The whole picture upside down, the sky's ground colour at the top | `Projection` lost the Y flip, which `Camera::Projection` makes for the standard one. The sky turns over too, because it is handed the same matrix |
| WASD does nothing | ImGui has the keyboard since a panel was last used: click once on the scene (Chapter 10 section 10) |
| The camera stops in mid-air | The ceiling, 1,400 m (section 7). At the travel limit it does not stop: it slides along the edge (section 4) |
| The clouds look wrong, seen from above | The ceiling was raised past the cloud base, 1,500 m (section 7) |
| A link error for `Horizon` symbols, or the demo missing from the picker | `GenerateProjects.bat` was not rerun after adding the files, or `Main.cpp`'s two lines are missing (section 1) |

## Exit check

Run the finished demo under the [hygiene every exit check assumes](../VulkanTutorial.md#conventions-every-chapter-uses),
with the sky on (**Sun sky** in the Tone mapping window, whose Sky header is
closed again), beside the build you kept at Part 1's checkpoint. Then:

- [ ] At the viewpoint the Part 1 build still shows white inside the 5, 10, and
      30 km squares (section 5 explains the 1 km pair), and the finished demo
      none: all four pairs are coloured squares in white frames, and the
      readout shows 13,730, 2,199, 1,100, and 488 steps.
- [ ] Click once on the scene, then fly straight ahead with Shift held: "Float
      spacing here" goes from 0.244 mm to 0.488 mm as you pass 4,096 m, and
      "From the origin" stops at 5000; turn, or strafe with A or D, and the
      camera slides along the edge. Climb with E: the height stops at 1,400 m.
- [ ] Run with `--msaa 4` (Chapter 18 section 3): the same picture, because the
      clear sets every sample of the multisampled depth.
- [ ] **The positive control.** In `CreateFlatPipeline`, delete the
      `.depthCompare` line, build, and run a few frames. Expect no plates: the
      sky and the clouds, the readout unchanged, and no validation message
      about any frame, because nothing is less than the 0 the depth was cleared
      to and no rule is broken. A silent validation layer says nothing about
      whether the picture is right, so the picture is the check. Put the line
      back.
- [ ] **Two experiments you can see.** Delete the clear (the `clearDepth` call
      in `Record`): only the sky shows, because nothing passes `GREATER`
      against 1.0. MSVC at `/W4` also reports C4505, "'clearDepth': unreferenced
      function with internal linkage has been removed"; that is expected,
      because the helper is now unused, and it goes away when the line is put
      back. Move `m_sky.Draw` back to the end, just above `endScenePass`, as
      section 7 first had it: the sky disappears. Put both back.

---

## Where to go from here

The chapters after it fill this view; the index lists them. What this chapter
did not build, and when it becomes worth building:

- **A floating origin**, when the camera must travel further than the 5 km
  limit allows. Positions are kept in `double` on the CPU, and the world is
  drawn relative to a point near the camera, moved now and then, so every float
  the GPU sees stays small. *Unreal Engine 5* does this as "large world
  coordinates": doubles on the CPU, and for shaders a tile position plus float
  offsets. In this engine it touches every position the GPU reads: the
  instances, the sky's and the clouds' camera, and anything hashed by position.
- **Tiles and streaming**, when the world no longer fits in memory: tiles loaded
  around the camera as it moves, with uploads that do not stall the frame.
  This engine's uploads wait for the GPU, and the ROADMAP defers multiple
  queues and timeline semaphores.
- **Reversed depth for the whole engine**, when a second demo needs it. A
  setting in the scene targets, honoured by the clear, the sky, the resolve,
  and every pipeline's compare, and a change to the index's depth contract.
- **An infinite far plane**, when the view must reach past 200 km. Reversed
  depth makes it nearly free in precision; the sky's un-projection would need
  care.
- **Logarithmic depth**, never at these distances: it writes `gl_FragDepth` from
  the fragment shader, which turns off early depth testing (Chapter 15 section
  11), and reversed float depth already gives a millimetre at 10 km.
- **A physical atmosphere**, when the haze cannot match the sky at sunset or
  from high up.

The far view's other items are kept where each first matters: far shadows,
merged far objects, culling on the GPU and distant lights (Chapter 37), and
temporal anti-aliasing for ridges that shimmer (Chapter 18 section 9).

---

## Sources

- Emil Persson, *Creating Vast Game Worlds: Experiences from Avalanche Studios*,
  SIGGRAPH 2012. *Just Cause 2*'s reversed depth, its landmark models kept
  loaded, and its 50 km view.
- Nathan Reed, *Depth Precision Visualized*, 2015
  (reedbeta.com/blog/depth-precision-visualized). Standard and reversed depth,
  integer and float, side by side; the step of about 1 mm at 10 km.
- Outerra, *Maximizing Depth Buffer Range and Precision*, 2012
  (outerra.blogspot.com). Reversed floating-point depth, rated "very
  effective" in a renderer of whole planets.
- The Vulkan specification, "Clear Commands": `vkCmdClearAttachments` writes
  depth in rasterization order, as the draws around it do.
- IEEE 754, the floating-point standard: why the spacing of floats grows with
  their size.
- DynDOLOD's "How LOD works" (*Skyrim*'s distant trees, two crossed quads);
  Jasmin Patry, SIGGRAPH 2021 Advances in Real-Time Rendering (*Ghost of
  Tsushima*'s haze, from 10 cm to 100 km).
- Epic Games, *Large World Coordinates in Unreal Engine 5* (documentation).

Next: [36 — Terrain to the Horizon](36-Terrain-To-The-Horizon.md)
