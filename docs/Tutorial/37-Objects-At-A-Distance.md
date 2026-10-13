# 37 — Objects at a Distance

**Goal:** things standing on the island, each drawn only as finely as its size
on screen needs. A script writes small USD assets (a pine, a broadleaf tree, a
rock, a house, a lighthouse, a watchtower and a keep), each with three versions
of itself, `LOD0` to `LOD2`, the last a box or a cone in the asset's average
colour. Villages stand in clearings, the landmarks on the shore, on a hilltop
and on the highest summit, and a pool of a few thousand trees grows within
600 m of the camera wherever a forest-density function says. Every frame each
object takes the level its height on screen in pixels asks for, with a margin
so that it never flickers between two; landmarks keep their coarsest level
however far away they are; and everything stands on the ground as the rings
draw it at its distance. Near the camera the objects cast Chapter 17's
shadows, timers say what each pass costs the GPU and what the objects cost the
CPU, and a real model, a CC0 tree from Kenney, is converted and planted in
place of the procedural broadleaf.

**ROADMAP:** step 21+ — the `Horizon` demo grows. A class of its own, `Props`,
in `Source/PillowFort/Demos/Horizon/`; two shader includes in
`Shaders/Horizon/`; the assets in `Assets/Scenes/Horizon/`, written by
`Assets/Scenes/make_horizon_props.py` (on `start`; appendix A); a converted model
and its converter in `ThirdPartyScenes/` (on `start`; appendix B).

**Module:** `pf::demos::horizon` (`Props`, owned by `HorizonDemo`; `Terrain`
grows). No engine module changes.

**Math:** taught where it is first used, and listed in the index's [The math,
chapter by chapter](../VulkanTutorial.md#the-math-chapter-by-chapter): the mip
levels of a heightmap as averages and a blend between two of them (section 4);
an object's height on screen in pixels, and a band of hysteresis around each
threshold (section 5); value noise (section 6); a remainder that is never
negative, for a pool that wraps round, and the smallest move worth making, in
pixels (section 7).

**Prerequisites:**

- Builds on Chapter 36, built and running; this chapter leans hardest on its
  cell size (section 3), `HeightAt` and the ring centre it takes (section 6), the
  heightmap's mip levels (section 8), and `mapHeight`'s level, `MapHeight`,
  `MAP_ORIGIN` and the viewpoint (section 9).
- Chapter 35: the flat pipeline, `FlatDraw` and `AddFlatMaterial` (sections 2
  and 3), the 5 km disc (section 4), reversed depth, `GREATER` and
  `stepsApart` (section 6), the sky drawn first and `SUN_TRAVEL` (section 7),
  section 8 on what reversed depth means for shadows, and "Where this is going"
  (a thing of size *s* at distance *d* spans about *s*/*d* radians).
- Chapter 12 sections 2 to 4 (nodes as indices, `AddNode`, `SetMesh`,
  `SetVisible` hiding a whole subtree, `EditLocal` and the world transforms it
  marks for recomputing, and `Aabb`, section 2), 6 (`CollectDraws`) and 9
  (frustum culling with `frustumFromViewProjection`).
- Chapter 13 section 11 (TinyUSDZ drops variant sets); Chapter 14 sections 7
  (`ImportUsdFile`: a node for the file and one per prim), 9 (the viewer
  registers a scene's meshes and materials in index order) and 13 (GeomSubsets
  become submeshes); Chapter 06 section 1 (`executableDirectory`).
- Chapter 11 sections 2 (the 48-byte `Vertex`), 7 (double-sided meshes and
  `gl_FrontFacing`), 8 (`GraphicsPipelineDesc`) and 13 (the normal matrix);
  Chapter 19 sections 3, 5 and 6 (the instance buffer, `PrepareDraws`,
  `RecordBatches`) and 8 (the shadow casters' list).
- Chapter 10 sections 4 (view space, and depth along the view) and 10 (which
  input reaches the demo while ImGui has the keyboard); Chapter 16 section 5
  (`smoothstep`); Chapter 17 sections 2 (`FitCascades`, from the camera's near
  plane to `maxDistance`, and `casterReach`), 5 (the shadow pass's two barriers)
  and 9 (`sunShadow`).
- Chapter 21 sections 3 (`randomFloat`) and 8 (timestamp queries); Chapter 24
  section 9 (`GpuTimestamps`).
- Chapter 25 section 8 (the standing stones that reach below the ground);
  Chapter 04 section 5 (the three questions a barrier answers); Chapter 09
  sections 2 (CPU state across `Teardown`) and 6 (`beginDemoPanel`).

---

## Where this is going

Chapter 36 put an island in the view, 33 km of heightmap in a sea that reaches
the horizon. It is bare. This chapter stands things on it: villages, a
lighthouse on the shore, a watchtower on a hill, a keep on the highest summit,
rocks, and trees round the camera wherever it flies.

It is the first of the chapters, 37 to 45, that make the island one open world
in the `Horizon` demo; the index lists them.

The ground could be drawn to 65 km for the cost of twelve rings because every
ring is drawn as coarsely as its distance allows. Objects need the same idea,
**level of detail**, done another way: an object cannot be a ring of a grid, so
it carries simpler versions of itself, and each frame it shows the one its size
on screen calls for. (Chapter 26 gave grass blades two levels, sections 5 and
6, and slid one shape into the other; a house's levels are different meshes,
and switch whole.) A house needs its door and windows when it is close; a few
hundred metres off, a box and a roof are all the eye can take in; at a few
kilometres it is a pixel or two, and not worth drawing at all, unless it is a
landmark, which is drawn however small it gets, because that one silhouette on
the skyline is what tells you where you are. Section 5 puts numbers on it.

Three facts shape the chapter:

- **The levels are authored, not computed.** Each asset is a USD file with
  three children, the detailed mesh and two simpler ones. Authoring them, here
  in a script, is the per-asset work of LOD; everything else here is a few
  global numbers.
- **The choice is made by height on screen in pixels**, not by distance, so it
  stays right when the window, the field of view or the asset's size changes.
- **The ground under a far object is coarser than the ground under a near
  one.** The rings sample the heightmap's smaller mip levels further out, so an
  object placed on the true height floats over far ridges or sinks into far
  valleys. Everything stands on the ground as it is drawn now.

The chapter is in four parts:

- **Part 1, "Objects on the ground"** (sections 1-4): the assets and the script
  that writes them; a scene graph of the demo's own, a first house drawn
  through it, and the flat pipeline lit like the terrain; villages and
  landmarks placed on the island; and the objects standing on the ground as it
  is drawn at their distance. It ends with a village to fly over and a tower on
  its hill, every object at its finest.
- **Part 2, "Levels of detail"** (section 5): the height on screen, the three
  thresholds and the margin round them, a bias, the debug views, and the rule
  that keeps landmarks. It ends with the levels in colour, in bands by distance.
- **Part 3, "Trees"** (sections 6-7): a forest density written once, in GLSL,
  with an exact copy in C++, and a pool of tree nodes reused as the camera
  moves, shrinking out at 600 m where Chapter 40's far forest will take over.
- **Part 4, "Shadows, timers, and a real model"** (sections 8-10): Chapter 17's
  shadows near the camera, with a lens of their own beside the reversed one;
  what each pass costs the GPU and the objects the CPU; and a downloaded tree,
  converted and planted in place of the procedural broadleaf.

> **Jump:** Chapters 35 and 36 drew everything with pipelines and buffers of
> the demo's own. This one hands its objects to Chapter 12's scene graph and
> Chapter 19's batches again, with the demo's pipeline drawing what they
> collect. Keep in mind the path a draw takes there: nodes, `CollectDraws`
> into `DrawItem`s, `PrepareDraws` sorting them into runs, `RecordBatches`
> calling the demo once per run.

### What you are actually writing

Every frame, `Props::Update` walks the objects, and this is what it does to
each, with the section that writes each part:

```text
 an empty slot of the pool: skip                                section 7
 the ground under it, as the rings draw it now                  sections 3, 4
 its distance; a tree near the pool's edge shrinks              sections 5, 7
 its node moved, only if the move shows: a quarter pixel        sections 3, 7
 its level: the height on screen, the margins, the bias;        section 5
   a landmark keeps its last; a tree shrunk to nothing hides    sections 5, 7
 one level shown, and counted                                   section 5
```

**This is `Props.h`**, the map of the chapter. The props are a class of their
own, as the terrain is, but CPU state only: a scene graph, the objects placed
in it, and the levels they show. The demo keeps it across `Teardown`, as it
keeps the camera, and hands its meshes to the scene renderer in every `Setup`.
Every function names the section that writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 37: objects on the ground, each drawn at the level of detail its size on screen asks for
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Props.h
#pragma once

#include "PillowFort/Demos/Horizon/Terrain.h"
#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Scene.h"

#include <glm/glm.hpp>

#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace pf::demos::horizon {

// Section 5: the "level" past the last line, which is not drawn.
inline constexpr uint32_t LOD_HIDDEN = 3;

// What the panel changes. The demo keeps it, so it survives Teardown.
struct PropSettings
{
    float lodBias     = 1.0f;    // section 5: every height on screen is multiplied by it
    bool  freezeLod   = false;   // section 5: every object keeps its level
    bool  showLevels  = false;   // section 5: a color per level, which the demo draws
    bool  drawObjects = true;    // section 9: off, the frame without them, to compare the timers with
};

// What the last Update found, for the panel.
struct PropCounts
{
    std::array<uint32_t, 4> levels{};   // section 5: objects at LOD0, LOD1, LOD2, and hidden
    uint32_t                trees = 0;  // section 7: slots of the pool holding a tree
};

// Everything that stands on the terrain, in a scene graph of its own (Chapter 12). CPU state only: the demo
// keeps it across Teardown, as it keeps the camera, and registers its meshes and materials in every Setup.
class Props
{
public:
    // Section 2: once per demo object. Every asset file into the scene as a hidden prototype.
    InitializationResult Load(const std::filesystem::path& folder);
    bool                 Loaded() const { return !m_assets.empty(); }
    const scene::Scene&  World() const { return m_scene; }   // section 2: its meshes and materials, to register

    // Once, after the terrain has loaded its heightmap. Section 2: one house, for a first look; section 3:
    // the villages and the landmarks in its place; section 7: and the pool's slots.
    void Place(const Terrain& terrain, const TerrainSettings& terrainSettings);

    // Every frame, before CollectDraws. Section 3: every object stands on the ground; section 4: as the rings
    // draw it now. Section 5: every object takes the level its height on screen asks for. Section 7: the pool
    // follows the camera. `screenScale` is the viewport's height in pixels over tan(fov / 2): something
    // r metres in radius and d metres away is r * screenScale / d pixels tall (section 5).
    void Update(const Terrain& terrain, const TerrainSettings& terrainSettings, glm::vec2 ringCenter,
                glm::vec3 camera, float screenScale, const PropSettings& settings);

    // Section 2: what the camera sees, culled (Chapter 12 section 9). Section 8 adds the shadow casters.
    void CollectDraws(const scene::Frustum& frustum, std::vector<scene::DrawItem>& draws) const;

    uint32_t          MeshLevel(uint32_t mesh) const { return m_meshLevels[mesh]; }   // section 5: 0 to 2
    const PropCounts& Counts() const { return m_counts; }

private:
    static constexpr uint32_t NO_ASSET = UINT32_MAX;

    // Section 2: one imported file. Its three levels' meshes, and the sphere around LOD0 in its own space.
    struct Asset
    {
        std::string             name;
        std::array<uint32_t, 3> meshes{};
        glm::vec3               centre{ 0.0f };
        float                   radius   = 0.0f;
        bool                    landmark = false;   // section 5: its name begins with Landmark_
    };

    // Section 2: one object in the world: a node where it stands, a child node per level, and the level
    // shown (section 5). Section 7: a slot of the tree pool is one too, with the cell it holds.
    struct Object
    {
        scene::NodeIndex                node = scene::INVALID_NODE;
        std::array<scene::NodeIndex, 3> levels{};
        uint32_t                        asset = NO_ASSET;   // NO_ASSET: an empty slot of the pool
        glm::vec2                       xz{ 0.0f };
        float                           scale = 1.0f;
        uint32_t                        level = LOD_HIDDEN;
    };

    uint32_t LoadAsset(const std::filesystem::path& file);                              // section 2
    uint32_t FindAsset(const std::string& name) const;                                  // section 2
    Object&  AddObject(uint32_t asset, glm::vec2 xz, float turn, float scale);          // section 2
    void     SetAsset(Object& object, uint32_t asset);                                  // section 2
    void     PlantTrees(const Terrain& terrain, glm::vec3 camera);                      // section 7

    scene::Scene            m_scene;
    std::vector<Asset>      m_assets;
    std::vector<uint32_t>   m_meshLevels;   // section 5: by mesh index, the level it belongs to
    std::vector<Object>     m_objects;      // section 2's, then section 7's slots
    PropCounts              m_counts;       // section 5
};

} // namespace pf::demos::horizon
```

An `Asset` is one file as the scene holds it; an `Object` is one thing in the
world, a node with a child node per level. `PropSettings` is the panel's, and
`PropCounts` what the panel shows. Write this much now: a declared function
that is never called needs no body, so the file builds at every step, and each
section fills in what it names. The numbers that belong above the class come
with the sections that explain them: the villages' and landmarks' places in
section 3, the level of detail's thresholds in section 5, the pool's size and
the smallest move in section 7. Two fields of `Object` and two of the class
come in section 7 too, and section 8 gives `CollectDraws` the shadow casters.

`HorizonDemo.h` gains the props, the lists they draw, and what Part 4 adds.
Here and in every later block from it, only the lines this chapter adds are
shown, each tagged with its section. The include goes with the others, and
`GpuTimestamps.h` beside `SceneRenderer.h`:

```cpp
#include "PillowFort/Demos/Horizon/Props.h"
#include "PillowFort/VulkanGraphics/GpuTimestamps.h"
```

and `<array>` joins the standard headers. Three private functions go after
`DrawTerrainControls`:

```cpp
    void                 RegisterProps();                                      // Chapter 37: section 2
    void                 DrawPropControls();                                   // Chapter 37: sections 3, 5, 6, 7, 9
    void                 GoTo(glm::vec2 xz, float height, float yaw, float pitch);   // Chapter 37: section 3
```

The members come in two blocks. The first, the draw lists and Part 4's GPU
objects, goes below `m_flatPipeline`:

```cpp
    // Chapter 37: what the props draw this frame and what casts shadows (sections 2, 8), the colors of the
    // levels (section 5), and the GPU timers (section 9).
    std::vector<scene::DrawItem>   m_draws;
    std::vector<scene::DrawItem>   m_casters;
    std::array<uint32_t, 3>        m_levelMaterials{};
    vulkan_graphics::GpuTimestamps m_timestamps;
```

The second, the CPU state, goes at the end of the class, after `m_showPlates`:

```cpp
    // Chapter 37: the props and their settings (sections 2-7), the shadows with their own lens (section 8),
    // and the GPU's and the CPU's times (section 9).
    Props                           m_props;
    PropSettings                    m_propSettings;
    scene::Camera                   m_shadowCamera;
    vulkan_graphics::ShadowSettings m_shadowSettings;
    std::array<double, 4>           m_timings{};               // milliseconds: shadows, sky, terrain, objects
    double                          m_propsMilliseconds = 0.0; // Props::Update and CollectDraws, on the CPU
```

### Where everything lands

```text
Source/PillowFort/Demos/Horizon/
  Props.h                  the class, above; the constants above it come in
                           sections 3, 5 and 7
  Props.cpp                top to bottom:
      the banner, the path line, the includes                section 2
      findNode, utf8                                         file scope (section 2)
      namespace pf::demos::horizon {
          ASSET_FILES                                        section 2
          chooseLevel                                        section 5
          Load, LoadAsset                                    section 2
          FindAsset, AddObject, SetAsset                     section 2
          Place                                              section 2, rewritten in 3, grown in 7
          PlantTrees                                         section 7
          Update                                             section 3, grown in 4, 5 and 7
          CollectDraws                                       section 2, grown in 8
      }
  HorizonDemo.h, .cpp      Chapters 35 and 36's, grown: the props in Setup, Update
                           and Record, the flat pipeline's light, the views, the
                           panel's Objects group, the shadows, the timers
  Terrain.h, .cpp          Chapter 36's, grown: FALLBACK_SKY moved (section 2), the
                           heightmap's mip levels on the CPU (section 4), the
                           forest and its texelOf (section 6)
Shaders/Horizon/
  HorizonTypes.h           FlatDraw grows; FLAT_*; TERRAIN_SHOW_FOREST; TREE_CELL
  HorizonShading.glsl      the light and the haze, the terrain's and the objects'   section 2
  Flat.vert.glsl           the normal                                               section 2
  Flat.frag.glsl           lit, hazed (section 2), shadowed (section 8)
  Terrain.frag.glsl        the shared include (2), the forest (6), shadows (8)
  Terrain.vert.glsl        the forest's density (section 6)
  ForestDensity.glsl       where the forest grows, an include                       section 6
Assets/Scenes/
  make_horizon_props.py    the props script                                         section 1
  Horizon/*.usda           what it writes: seven assets                             section 1
ThirdPartyScenes/
  convert_glb.py           a glTF model to a USD asset with three levels            section 10, appendix B
  Kenney/                  the download it comes from, in source/, and the tree
                           converted from it                                        section 10
```

---

# Part 1 — Objects on the ground (sections 1-4)

Every object shows its finest level until Part 2. The first picture comes at the
end of section 2's first half: one house, in the air in front of the camera.

Every run in this chapter is with the engine's sky on, unless it says
otherwise, as in Chapter 36: **Sun sky**, with the Sky header closed again.

## 1. Assets with three levels

**This is `Assets/Scenes/make_horizon_props.py` and the seven files it writes.**

### Three children, not a variant set

USD has a way to say "these are alternatives, show one": a **variant set** on
a prim, with a variant for each level. TinyUSDZ, as Chapter 13 section 11 found,
drops variant sets, and the prims inside a variant never reach the importer. So
the levels are plain siblings: each asset is an `Xform` with three children,
named exactly `LOD0`, `LOD1` and `LOD2`, each a `Mesh`. Nothing in the file
says only one of them should show; the demo does that (section 5), and until
it does, it shows `LOD0` alone. The names are the whole convention: a model
from anywhere that has those three children can stand in the world here, which
section 10 relies on.

Each asset needs its three levels made by someone, one shape each. That is the
one piece of level of detail that is work per asset, and here a script does
it:

- **`LOD0`**, the asset as it is: every part, every material.
- **`LOD1`**, the same silhouette from fewer triangles: a third of them, or
  fewer. Small parts (a door, a window, a chimney) go, because by the time it
  shows, they would be a pixel or two.
- **`LOD2`**, a **proxy**: a box, a cone or two cones base to base, six to ten
  triangles, in one colour. The colour is the asset's **average colour**: each
  face of `LOD0`'s colour weighted by its area, because from far away the eye
  sees nothing but the mix. A house's white walls and red roof average to a
  muted pink; a pine's needles and bark to a dark green.

Two more rules make them stand well:

- **`y = 0` is where the asset meets the ground, and everything below it is a
  plinth.** Chapter 25 section 8's standing stones reached two metres below the
  lowest the ground could be, so they stood on any hill. Here a house has a
  stone base 2 m deep, a tree's trunk goes 1 m down, the lighthouse's base 6 m,
  the watchtower's foundation 8 m and the keep's 12 m: on a slope, the downhill
  side shows plinth, not a gap.
- **A landmark's name begins with `Landmark_`.** Section 5 keeps such an asset
  at its coarsest level however small it gets.

### The script

The script is on the `start` branch at `Assets/Scenes/make_horizon_props.py`,
with the seven files it writes in `Assets/Scenes/Horizon/`; appendix A says what
is in it. The excerpts below are cut from it, and use helpers they do not repeat
(`OUT`, the folder it writes to; `materialText` and `meshText`, which write a
material and a mesh as USD text; `moved`, which shifts the points a builder has
just added). It is plain Python with no imports beyond `math` and `os`, as
Chapter 36's heightmap script is. A `Shape` is a list of points and of faces,
each face naming its material; the asset's average colour is worked out from
them:

```python
class Shape:
    """Points, and faces that each name a material."""

    def __init__(self):
        self.points = []
        self.faces = []   # (material, [point indices])

    def point(self, p):
        self.points.append(p)
        return len(self.points) - 1

    def face(self, material, indices):
        self.faces.append((material, list(indices)))

    def polygon(self, material, indices):
        # Polygons of more than four sides as a fan of triangles, so the importer never has to.
        if len(indices) <= 4:
            self.face(material, indices)
        else:
            for i in range(1, len(indices) - 1):
                self.face(material, [indices[0], indices[i], indices[i + 1]])

    def triangles(self):
        return sum(len(indices) - 2 for _, indices in self.faces)

    def average(self, colors):
        # The colour the whole shape reads as from far away: every face's colour weighted by its area.
        total, weight = [0.0, 0.0, 0.0], 0.0
        for material, indices in self.faces:
            a = self.points[indices[0]]
            for i in range(1, len(indices) - 1):
                b, c = self.points[indices[i]], self.points[indices[i + 1]]
                u = [b[k] - a[k] for k in range(3)]
                v = [c[k] - a[k] for k in range(3)]
                cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
                area = 0.5 * math.sqrt(sum(x * x for x in cross))
                total = [total[k] + area * colors[material][k] for k in range(3)]
                weight += area
        return tuple(round(t / weight, 3) for t in total)
```

A handful of builders add parts to a shape. The one most assets are made of is
`frustum(shape, material, r0, r1, y0, y1, sides, top=True, bottom=True,
turn=0.0)`: a cone around +Y with `sides` faces round it, of radius `r0` at
height `y0` and `r1` at `y1`, cut flat or, with `r1` 0, to a point, which makes
trunks, crowns and towers. `top` and `bottom` say whether its ends are closed,
which a trunk's, hidden inside a crown and under the ground, need not be; and
`turn` turns it about +Y, so that a four-sided proxy can stand square to its
asset rather than corner on. The others are `box`; `gable`, a roof; `lumpy`, a
sphere pushed in and out by a few waves, for rocks and leafy crowns; and
`diamond`, two cones base to base, for proxies. Every face is listed
counter-clockwise seen from outside, and no normals are written, so the
importer gives every face its own (Chapter 14 section 12), which suits shapes
this faceted.

`write` turns three shapes into one file. `LOD2` gets a material of its own,
`Far`, in `LOD0`'s average colour; each level becomes one `Mesh` whose faces
are grouped by material into GeomSubsets, which Chapter 14 section 13 turns
into one submesh each. The first run makes the `Horizon/` folder:

```python
def write(root, colors, levels):
    """levels: LOD0, LOD1 and LOD2, each a Shape. LOD2 is drawn in a material of its own, Far, the
    area-weighted average of LOD0's colours."""
    colors = dict(colors)
    colors["Far"] = levels[0].average(colors)
    levels[2].faces = [("Far", f) for _, f in levels[2].faces]
    used = []
    for shape in levels:
        for material, _ in shape.faces:
            if material not in used:
                used.append(material)
    os.makedirs(OUT, exist_ok=True)   # the first run makes the folder
    path = os.path.join(OUT, root + ".usda")
    with open(path, "w") as f:
        f.write(f'#usda 1.0\n(\n    defaultPrim = "{root}"\n    metersPerUnit = 1\n    upAxis = "Y"\n)\n\n')
        f.write(f'def Xform "{root}"\n{{\n    def Scope "Materials"\n    {{')
        f.write("".join(materialText(root, m, colors[m]) for m in used))
        f.write("\n    }\n")
        f.write("".join(meshText(root, f"LOD{i}", shape) for i, shape in enumerate(levels)))
        f.write("\n}\n")
    print(f"{path}: {', '.join(str(s.triangles()) for s in levels)} triangles; far colour {colors['Far']}")
```

The pine shows the pattern every asset follows. Three cones on a trunk; two
cones and a four-sided trunk; one four-sided pyramid from the ground to the
top:

```python
# A pine, 12 m tall: a trunk and three stacked cones; then two; then one four-sided pyramid.
PINE = {"Bark": (0.16, 0.10, 0.06), "Needles": (0.04, 0.11, 0.04)}
pine = [Shape(), Shape(), Shape()]
frustum(pine[0], "Bark", 0.35, 0.20, -1.0, 4.0, 8, top=False, bottom=False)
for r, y0, y1 in [(3.2, 2.5, 7.0), (2.5, 5.0, 9.5), (1.7, 7.5, 12.0)]:
    frustum(pine[0], "Needles", r, 0.0, y0, y1, 12)
frustum(pine[1], "Bark", 0.35, 0.20, -1.0, 4.0, 4, top=False, bottom=False)
for r, y0, y1 in [(3.2, 2.5, 8.5), (2.3, 6.0, 12.0)]:
    frustum(pine[1], "Needles", r, 0.0, y0, y1, 7)
frustum(pine[2], "Needles", 3.0, 0.0, -1.0, 12.0, 4)
write("Pine", PINE, pine)
```

The other six assets follow the same pattern, in the script. Running it is
optional, because the files it writes are on `start`; to see the triangles per
level, run it once from `Assets/Scenes/`:

```text
python make_horizon_props.py
```

It writes `Assets/Scenes/Horizon/` again and prints the triangles per level. The
folder is one below `Assets/Scenes/`, so the USD viewer's file list, which
shows that folder's top level only, does not fill up with them:

| Asset | `LOD0` | `LOD1` | `LOD2` | What `LOD2` is |
| --- | --- | --- | --- | --- |
| `Pine` | 82 | 32 | 6 | a four-sided pyramid, 13 m |
| `Broadleaf` | 160 | 44 | 8 | two four-sided cones base to base |
| `Rock` | 144 | 36 | 8 | the same, small |
| `House` | 86 | 16 | 10 | one box |
| `Landmark_Lighthouse` | 360 | 128 | 10 | a tapering four-sided tower, 58 m |
| `Landmark_Tower` | 126 | 52 | 10 | the same, 70 m |
| `Landmark_Keep` | 534 | 14 | 10 | the same, 98 m: a keep 24 m square |

The heights in the last column count the plinths: the lighthouse stands 52 m
above the ground, the watchtower 62 m and the keep 86 m. All three are far
bigger than real ones. A landmark is drawn to be seen from kilometres away, and
section 5 works out what that takes.

To see why the demo must show one level at a time, open a file in Chapter 14's
viewer, which shows every node: run with
`--demo USD --scene Assets/Scenes/Horizon/House.usda` (a path with a folder in
it opens any file, Chapter 14 section 9). The three levels stand inside each
other, the proxy's box poking through the roof.

## 2. A scene of the demo's own

**This is the top of `Props.cpp`, `Load`, `LoadAsset`, `RegisterProps`,
`FindAsset`, `AddObject`, `SetAsset`, a first `CollectDraws` and `Place`, the
props in `Setup` and `Record`; then the flat pipeline's light and
`HorizonShading.glsl`.**

### Why a scene graph

Chapter 35's plates were eight `DrawItem`s in a vector. The props are thousands,
each with three levels, of which one shows. Chapter 12's scene graph already
does what they need: a node per object, a child per level, a flag that hides a
node and everything under it, and `CollectDraws`, which walks the visible nodes
into `DrawItem`s and leaves out what the camera cannot see. And Chapter 14's
importer appends a USD file to a scene as nodes, so the assets arrive in the
form the objects need.

The scene is the props' own: a `scene::Scene` inside `Props`, which nothing else
in the demo uses. Each file is imported once, as a **prototype**: hidden, never
drawn itself, and kept only for its meshes, which every copy shares.

### `Props.cpp`

The file begins as every file here does, with the includes this section needs;
sections 3 and 7 add the rest. Two helpers go at file scope: `findNode`, a
small search the scene does not have, for the first node with a name anywhere
below a node; and `utf8`, a path's last part as UTF-8 for names and messages,
because `path::string()` would turn it into the Windows code page. It is the
third copy of Chapter 13's `toUtf8`, after the importer's and the USD viewer's:
small enough that a shared header for it would cost more than it saves. The
rest of the file follows the order of "Where everything lands": `ASSET_FILES`,
`Load`, `LoadAsset`, `FindAsset`, `AddObject`, `SetAsset` and `Place`, then
`PlantTrees`, `Update` and `CollectDraws` as sections 3 and 7 write them.

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 37: objects on the ground, each drawn at the level of detail its size on screen asks for
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Props.cpp
#include "PillowFort/Demos/Horizon/Props.h"

#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/UsdImport/UsdImport.h"

#include <glm/gtc/quaternion.hpp>

#include <format>

// File scope, above the namespace block. Section 2: the first node named `name` below `node`, depth first.
static pf::scene::NodeIndex findNode(const pf::scene::Scene& scene, pf::scene::NodeIndex node, const std::string& name)
{
    for (const pf::scene::NodeIndex child : scene.GetNode(node).children)
    {
        if (scene.GetNode(child).name == name)
        {
            return child;
        }
        if (const pf::scene::NodeIndex found = findNode(scene, child, name); found != pf::scene::INVALID_NODE)
        {
            return found;
        }
    }
    return pf::scene::INVALID_NODE;
}

// File scope, above the namespace block. Section 2: a path's last part as UTF-8, for names and messages:
// path::string() would convert it to the ANSI code page on Windows. The third copy of Chapter 13 section
// 13's toUtf8, after UsdImport.cpp's and the USD viewer's.
static std::string utf8(const std::filesystem::path& path)
{
    const std::u8string text = path.u8string();
    return std::string(text.begin(), text.end());
}

namespace pf::demos::horizon {
```

`Load` imports the seven files the script wrote. A file that is missing or has
no levels is reported, and the props are emptied, so the demo runs on without
them, as it runs without a heightmap (Chapter 36 section 8):

```cpp
// Section 2: the files make_horizon_props.py writes, in Assets/Scenes/Horizon/.
constexpr std::array<const char*, 7> ASSET_FILES{
    "Pine.usda", "Broadleaf.usda", "Rock.usda", "House.usda",
    "Landmark_Lighthouse.usda", "Landmark_Tower.usda", "Landmark_Keep.usda",
};

InitializationResult Props::Load(const std::filesystem::path& folder)
{
    for (const char* file : ASSET_FILES)
    {
        if (LoadAsset(folder / file) == NO_ASSET)
        {
            *this = Props{};
            return InitializationResult::failure(std::format("{} is missing, or has no LOD0 to LOD2.", file));
        }
    }
    return InitializationResult::success();
}
```

`LoadAsset` imports one file. `ImportUsdFile` appends it under a new node, the
root's last child, which is hidden: the prototype. Below it the importer has made
a node per prim (Chapter 14 section 7): the asset's `Xform`, its `Materials`
scope, and `LOD0` to `LOD2`, each holding a mesh. Their mesh indices are what
the asset keeps. `m_meshLevels` remembers, for every mesh, which level it is,
for section 5's colours.

What section 5 measures on screen is the **sphere round `LOD0`**: its centre,
and its radius, half the diagonal of the mesh's box (Chapter 12 section 2's
`Aabb`). A sphere is the same size from every side, so the measure does not
change as the camera goes round an object:

```cpp
// Section 2: one file, appended to the scene under a node of its own, which is hidden: a prototype, whose
// levels' meshes every copy shares. It must have children LOD0, LOD1, and LOD2, each with a mesh.
uint32_t Props::LoadAsset(const std::filesystem::path& file)
{
    if (auto result = usd_import::ImportUsdFile(file, m_scene); !result)
    {
        Log::warning(std::format("Props: {}", result.message()).c_str());
        return NO_ASSET;
    }
    const scene::NodeIndex prototype = m_scene.GetNode(scene::ROOT_NODE).children.back();   // the file's node
    m_scene.SetVisible(prototype, false);

    Asset asset{ .name = utf8(file.stem()) };
    m_meshLevels.resize(m_scene.MeshCount(), 0);
    for (uint32_t level = 0; level < 3; ++level)
    {
        const scene::NodeIndex node = findNode(m_scene, prototype, std::format("LOD{}", level));
        if (node == scene::INVALID_NODE || m_scene.GetNode(node).mesh == scene::NO_COMPONENT)
        {
            Log::warning(std::format("Props: {} has no mesh named LOD{}.", utf8(file.filename()), level).c_str());
            return NO_ASSET;
        }
        asset.meshes[level]               = m_scene.GetNode(node).mesh;
        m_meshLevels[asset.meshes[level]] = level;   // section 5's colors
    }

    // The sphere around LOD0's box: what section 5 measures on screen.
    const scene::Aabb& box = m_scene.GetMesh(asset.meshes[0]).bounds;
    asset.centre   = 0.5f * (box.min + box.max);
    asset.radius   = 0.5f * glm::length(box.max - box.min);
    asset.landmark = asset.name.starts_with("Landmark_");   // section 5
    m_assets.push_back(asset);
    return static_cast<uint32_t>(m_assets.size() - 1);
}
```

### Into the scene renderer

The scene's meshes and materials have indices, and a `DrawItem` names its mesh
and material by them. The scene renderer gives out its own indices as things
are added. The USD viewer makes the two agree by adding the scene's meshes and
materials first, in index order (Chapter 14 section 9), and so does this demo:
before the plates, so the plates' materials come after the props'. The props
themselves are imported only once per demo object, like the viewer's scene,
because they are CPU state that a `Teardown` keeps. In `Setup`, after the scene
renderer's `Initialize` and before `CreatePlates`:

```cpp
    // Chapter 37 section 2: the props, imported once per demo object; then their meshes and materials, before
    // anything else, so that the scene's indices are the scene renderer's too. Missing files are reported,
    // and the demo runs without props.
    if (!m_props.Loaded())
    {
        const std::filesystem::path folder = executableDirectory() / "Assets" / "Scenes" / "Horizon";
        if (auto result = m_props.Load(folder); !result)
        {
            Log::warning(std::format("No props: {}", result.message()).c_str());
        }
    }
    RegisterProps();
    CreatePlates();                                                        // Chapter 35 section 2
```

The lines need `PillowFort/ErrorReporting/Log.h` and
`PillowFort/VulkanGraphics/ExecutableFiles.h` (Chapter 06 section 1's
`executableDirectory`) at the top of `HorizonDemo.cpp`, with
`PillowFort/Scene/Bounds.h` for the frustum below, and `<filesystem>` and
`<format>` with the standard headers.

`RegisterProps` goes at the end of the file. Every material goes through
`AddFlatMaterial`, as the plates' do, so `m_materialColors` has its colour under
the same index. Chapter 35's `AddFlatMaterial` takes a name and a colour, which
is all this first version passes; "Lit like the ground" below gives it a third
argument and says which line of this function changes:

```cpp
// Chapter 37 section 2: the props' meshes and materials, in index order, as the USD viewer registers its scene
// (Chapter 14 section 9): a DrawItem from the props' scene then means the same mesh and material here. Every
// material is drawn in its base color.
void HorizonDemo::RegisterProps()
{
    const scene::Scene& world = m_props.World();
    for (uint32_t mesh = 0; mesh < world.MeshCount(); ++mesh)
    {
        m_sceneRenderer.AddMesh(world.GetMesh(mesh).data);
    }
    for (uint32_t material = 0; material < world.MaterialCount(); ++material)
    {
        const scene::Material& source = world.GetMaterial(material);
        AddFlatMaterial(source.name.c_str(), glm::vec3(source.baseColor));
    }
}
```

### An object, and its levels

`AddObject` makes one thing in the world: a node where it stands, turned about
+Y and scaled, and under it one node per level, each showing the asset's mesh
for that level. Every object of an asset shares its three meshes, so a thousand
pines are a thousand nodes and no new geometry. Until section 5 chooses a level
a frame, only `LOD0` shows. `FindAsset` finds an asset by its file's name, and
`SetAsset` is separate from `AddObject` because section 7 gives an object
another asset after it is made:

```cpp
uint32_t Props::FindAsset(const std::string& name) const
{
    for (uint32_t asset = 0; asset < m_assets.size(); ++asset)
    {
        if (m_assets[asset].name == name)
        {
            return asset;
        }
    }
    return NO_ASSET;
}

// Section 2: a node where the object stands, turned and scaled, and under it one node per level, each showing
// the asset's mesh for that level. Section 5 shows one of them at a time.
Props::Object& Props::AddObject(uint32_t asset, glm::vec2 xz, float turn, float scale)
{
    Object object{ .xz = xz, .scale = scale };
    object.node = m_scene.AddNode(std::format("Prop {}", m_objects.size()), scene::ROOT_NODE,
                                  scene::Transform{ .translation = { xz.x, 0.0f, xz.y },
                                                    .rotation    = glm::angleAxis(turn, glm::vec3(0.0f, 1.0f, 0.0f)),
                                                    .scale       = glm::vec3(scale) });
    for (uint32_t level = 0; level < 3; ++level)
    {
        object.levels[level] = m_scene.AddNode(std::format("LOD{}", level), object.node);
    }
    m_scene.SetVisible(object.levels[1], false);   // section 5 shows one level at a time; until then, LOD0
    m_scene.SetVisible(object.levels[2], false);
    SetAsset(object, asset);
    m_objects.push_back(object);
    return m_objects.back();
}

// Section 2: what an object draws, at each level: the asset's three meshes. Section 7: a slot of the pool
// changes asset when it is given another tree.
void Props::SetAsset(Object& object, uint32_t asset)
{
    object.asset = asset;
    if (asset == NO_ASSET)
    {
        return;
    }
    for (uint32_t level = 0; level < 3; ++level)
    {
        m_scene.SetMesh(object.levels[level], m_assets[asset].meshes[level]);
    }
}
```

### What the camera sees

`CollectDraws` goes last in the namespace, after everything else the file gets
(sections 3 and 7 put `Update` and `PlantTrees` before it). It is the scene's
own, with the camera's frustum (Chapter 12 section 9). Like the scene's, it
clears the list it is given before it fills it, so `m_draws` does not grow from
frame to frame. Section 8 replaces this version with one that also collects the
shadow casters:

```cpp
void Props::CollectDraws(const scene::Frustum& frustum, std::vector<scene::DrawItem>& draws) const
{
    m_scene.CollectDraws(draws, &frustum);   // Chapter 12: each shown level's mesh, culled by its box
}
```

`Record`, after `WriteFrameData`, collects what the camera sees into `m_draws`,
and puts the plates after them when they show. Section 3 adds a call above these
lines and section 8 changes this one's arguments; section 9 shows the whole
stretch of `Record` finished, to check your own against:

```cpp
    // Chapter 37 section 2: what the camera sees of the props.
    m_props.CollectDraws(scene::frustumFromViewProjection(frameData.viewProjection), m_draws);
    if (m_showPlates)                // Chapter 36 section 1: the plates, while the panel shows them
    {
        m_draws.insert(m_draws.end(), m_plates.begin(), m_plates.end());
    }
```

Chapter 36's `Record` called `m_sceneRenderer.PrepareDraws(frame.frameIndex,
m_plates);` under a comment of its own, and wrapped the draw that ends the scene
pass in `if (m_showPlates)`. Both change. `PrepareDraws` takes the whole list in
place of `m_plates`; the new comment and call replace the old pair:

```cpp
    // Chapter 35 section 3: the plates, sorted and batched into this slot's instance buffer, before anything
    // binds set 0. Chapter 37: the props with them.
    m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws);
```

and the draw at the end of the scene pass is no longer only the plates': its
`if (m_showPlates)` and the braces round the draw go (the test moved up, to
where the plates join `m_draws`), and the draw runs every frame, with whatever
`m_draws` holds. Its comment gains "Chapter 37: and the props, in the same
batches."

### One house, for a first look

Section 3 places the villages, which takes a few more pieces. To see that the
path works before then, `Place` goes after `SetAsset` and starts as one house,
hung in the air 40 m in front of the viewpoint, a little below eye level.
`AddObject` stands everything at height 0, so the house is lifted by hand, and
its world transform brought up to date once, since nothing else does yet:

```cpp
// Section 2, for a first look: one house, hung in the air 40 m in front of the viewpoint, where the camera
// starts. Section 3 gives Place its real body.
void Props::Place(const Terrain& /*terrain*/, const TerrainSettings& /*terrainSettings*/)
{
    if (!Loaded() || !m_objects.empty())
    {
        return;   // nothing to place, or placed already
    }
    const Object& house = AddObject(FindAsset("House"), { 0.0f, -40.0f }, glm::radians(30.0f), 1.0f);
    m_scene.EditLocal(house.node).translation.y = 988.0f;   // the viewpoint is at 1,000 m
    m_scene.UpdateWorldTransforms();
}
```

`Setup` calls it once the terrain is initialized, before the sky, because
section 3's `Place` will ask the ground where houses can stand:

```cpp
    // Chapter 37 section 2: the props, placed once, now that the terrain has its heightmap.
    m_props.Place(m_terrain, m_terrainSettings);
```

`Props.cpp` is a new file, so rerun `GenerateProjects.bat`; then build and run.
The log says what was imported:

```text
[INFO] /Pine/LOD0: 2 submeshes: Bark Needles
[INFO] /Pine/LOD1: 2 submeshes: Bark Needles
[INFO] Pine.usda: imported 6 nodes, 3 meshes (120 triangles), 0 cameras.
```

and the same for the other six: six nodes each, the file's node, the asset's,
its `Materials` scope and the three levels. And in the middle of the view, 40 m
off, a house hangs in the air: cream walls, a red roof, a grey stone plinth,
dark door and windows, `LOD0` alone. Every face of a material is the same flat
colour, the walls in the sun no brighter than the wall in shade, because the
flat pipeline draws a material's colour and nothing else, as it drew the
plates. With **Show the plates** on, the plates are their exact colours still.

### Lit like the ground

The objects must look as if they stand in the same light and the same air as
the ground: the sun, the sky's light from every direction, and the same haze,
or a house far off would stand out, crisp, against hazed hills. Chapter 36's
terrain shader already has all three, in `lightAt`, `skyColor` and its haze
line. Writing them a second time for the objects would make two copies to keep
in step; they move into an include that both shaders use.

The flat pipeline's push constants grow to carry what the terrain's carry for
the same purpose: the sky's colour when it is off, the haze distance, and
flags. In `HorizonTypes.h`, `FlatDraw` becomes:

```c
/* The flat pipeline's push constants: one material's color, for one run of draws (section 3). Chapter 37
   section 2: and how to light it. */
struct FlatDraw
{
    vec4 baseColor;   /*  0  linear rgb; alpha unused */
    vec4 sky;         /* 16  Chapter 37: TerrainDraw::sky, the sky's color when it is off and the haze distance */
    uint flags;       /* 32  Chapter 37: FLAT_* */
    uint padding0;    /* 36  keeps the size a multiple of 16 */
    uint padding1;    /* 40 */
    uint padding2;    /* 44 */
};

/* Chapter 37: bits of FlatDraw::flags. With none, a plate's color exactly, as Chapter 35 drew it. */
#define FLAT_LIT      1u   /* section 2: lit by the sun and the sky, shadowed and hazed, as the terrain is */
#define FLAT_SKY      2u   /* section 2: the engine's sky is on (TERRAIN_SKY's twin) */
```

and the `static_assert` for it, in the C++ block at the end of `HorizonTypes.h`,
says 48 bytes, not 16:

```c
    static_assert(sizeof(FlatDraw) == 48, "FlatDraw layout drifted.");
```

With no flags, a draw is a plate's colour, as before.

**`HorizonShading.glsl`** is the terrain's three functions, made to take what
they read from `TerrainDraw` as arguments, so any shader can include them. It
goes in `Shaders/Horizon/`, and declares the two sky bindings the terrain
shader declared. The flat pipeline's layout is the scene renderer's set 0, as
the terrain's is, and `Setup` already hands the sky's light to that set (Chapter
35 section 7's `SetImageBasedLighting`), so the flat shader finds bindings 10
and 11 filled:

```glsl
// Shaders/Horizon/HorizonShading.glsl - Chapter 37 section 2: the light and the haze every surface of the
// Horizon demo shares: Chapter 36's ground and sea, and the objects that stand on them. An include: the
// including shader has included FrameBlock.glsl first. Declares set 0 bindings 10 and 11.
#ifndef PF_HORIZON_SHADING_GLSL
#define PF_HORIZON_SHADING_GLSL

layout(set = 0, binding = 10) uniform samplerCube skyDiffuse;    // Chapter 24's light, E / pi
layout(set = 0, binding = 11) uniform samplerCube skySpecular;   // level 0 is the sky itself

// Chapter 36 section 4: Chapter 11's light, for a matte surface facing N: the sun, whose sunColor is already
// E / pi, and the light from everywhere else, which is Chapter 24's sky when it lights the scene.
vec3 lightAt(vec3 N)
{
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? texture(skyDiffuse, N).rgb : frame.ambientColor.rgb;
    return frame.sunColor.rgb * max(dot(N, -frame.sunDirection.xyz), 0.0) + ambient;
}

// Chapter 36 section 10: the sky in a direction, lifted to the horizon if it points below it (on the open
// sea, that is more sea, about as bright as the horizon). With the engine's sky off, `fallback`: the demo's
// clear color.
vec3 skyColor(vec3 direction, bool skyOn, vec3 fallback)
{
    if (!skyOn)
    {
        return fallback;
    }
    direction = normalize(vec3(direction.x, max(direction.y, 0.0), direction.z));
    return textureLod(skySpecular, direction, 0.0).rgb;
}

// Chapter 36 section 11: haze. A surface `range` metres away along -V (V is unit, toward the eye) fades into
// the sky behind it: the fraction left is exp(-range / hazeDistance). `sky` is TerrainDraw::sky: rgb the
// fallback, w the haze distance.
vec3 hazed(vec3 color, vec3 V, float range, bool skyOn, vec4 sky)
{
    return mix(color, skyColor(-V, skyOn, sky.rgb), 1.0 - exp(-range / sky.w));
}

#endif
```

In `Terrain.frag.glsl`, the two `layout(set = 0, binding = 10)` and `11`
lines, `lightAt` and `skyColor` go, and the include takes their place, after
the push-constant block:

```glsl
#include "HorizonShading.glsl"   // Chapter 37 section 2: lightAt, skyColor and hazed, the objects' too
```

In `waterColor`, the call of `skyColor` passes what the function now asks for,
whether the sky is on and the fallback, which it read from `TerrainDraw`
before. A line before it works out whether the sky is on, and the `mirror` line
changes; everything else in the function, the `R`, `lobe` and `PI` round it
included, is Chapter 36 section 10's as it was:

```glsl
    bool  skyOn     = (terrain.flags & TERRAIN_SKY) != 0u;
    vec3  mirror    = skyColor(R, skyOn, terrain.sky.rgb) + PI * frame.sunColor.rgb * lobe;   // the sun's irradiance, E
```

and the haze line in `main` becomes a call:

```glsl
    color = hazed(color, V, range, (terrain.flags & TERRAIN_SKY) != 0u, terrain.sky);
```

The terrain draws exactly as before. Now the objects, in three steps that must
land together: a vertex shader that reads the normal, a pipeline that describes
it, and a fragment shader that uses it. A shader input the pipeline does not
describe is a validation error (`VUID-VkGraphicsPipelineCreateInfo-Input-07904`),
so build only after the pipeline's attribute below. **`Flat.vert.glsl`** reads
the normal, the next 12 bytes of Chapter 11's `Vertex`, and hands the fragment
shader the world position and the world normal. The normal goes
through the instance's normal matrix, which `PrepareDraws` writes beside the
model matrix (Chapter 19 section 3):

```glsl
layout(location = 1) in vec3 inNormal;     // Chapter 37: the next 12

layout(location = 0) out vec3 worldPosition;   // Chapter 37
layout(location = 1) out vec3 worldNormal;     // Chapter 37
```

```glsl
    InstanceData instance = instances[gl_InstanceIndex];
    vec4 world    = instance.model * vec4(inPosition, 1.0);
    worldPosition = world.xyz;
    worldNormal   = instance.normalMatrix * inNormal;   // Chapter 11's normal matrix, which PrepareDraws wrote
    gl_Position   = frame.viewProjection * world;
```

`CreateFlatPipeline` describes the second attribute. Chapter 35 declared one,
`const VkVertexInputAttributeDescription position{ ... }`, and passed it as
`.vertexAttributes = { &position, 1 }` (Chapter 11 section 8). The declaration
becomes an array of two, and the `vertexAttributes` line points at the array:

```cpp
    // Chapter 11's vertex buffer, of which the shader reads only the position. Chapter 37: and the normal.
    const VkVertexInputBindingDescription binding{
        .binding   = 0,
        .stride    = sizeof(scene::Vertex),
        .inputRate = VK_VERTEX_INPUT_RATE_VERTEX,
    };
    const std::array<VkVertexInputAttributeDescription, 2> attributes{ {
        { .location = 0, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, position) },
        { .location = 1, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, normal) },
    } };
```

```cpp
        .vertexAttributes = attributes,
```

**`Flat.frag.glsl`** is rewritten. A plate is still its colour. A lit material
is its colour times the light, and then hazed. The normal is flipped to face
the side being drawn, as Chapter 11 section 7's mesh shader does for a
double-sided mesh, whose back faces would otherwise be lit from behind:

```glsl
// Shaders/Horizon/Flat.frag.glsl - Chapter 35 section 3: one color per material and no light, so a plate
// reads as exactly its color in a screenshot. Chapter 37 section 2: and for the objects, the same color lit
// and hazed as the ground around them is.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // Chapter 37: the camera, the sun, the ambient light
#include "HorizonTypes.h"    // FlatDraw

layout(push_constant) uniform FlatBlock
{
    FlatDraw draw;
};

#include "HorizonShading.glsl"   // Chapter 37: the terrain's lightAt and hazed

layout(location = 0) in vec3 worldPosition;   // Chapter 37
layout(location = 1) in vec3 worldNormal;     // Chapter 37

layout(location = 0) out vec4 outColor;

void main()
{
    vec3 color = draw.baseColor.rgb;
    if ((draw.flags & FLAT_LIT) != 0u)
    {
        // Chapter 37 section 2: the terrain's light and haze. The normal faces the side being drawn: a
        // double-sided mesh shows its back faces too (Chapter 11).
        vec3  N         = normalize(worldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
        color *= lightAt(N);

        vec3  toEye = frame.cameraPosition.xyz - worldPosition;
        float range = length(toEye);
        color = hazed(color, toEye / range, range, (draw.flags & FLAT_SKY) != 0u, draw.sky);
    }
    outColor = vec4(color, 1.0);
}
```

The plates read as exactly their colour in a screenshot (Chapter 35 section 3),
and they should keep doing so. So a material says whether it is lit, and
`AddFlatMaterial` keeps that beside its colour, as a flag for the shader. Its
declaration in `HorizonDemo.h` gains `lit`, with a default of `false`, so
`CreatePlates` stays as it is, and a vector of flags goes after
`m_materialColors`. The declaration replaces Chapter 35's, which had two
parameters:

```cpp
    uint32_t             AddFlatMaterial(const char* name, glm::vec3 color, bool lit = false);   // section 2; Chapter 37 section 2: lit

    std::vector<uint32_t>        m_materialFlags;    // Chapter 37: by material index, FLAT_LIT or not
```

The definition replaces Chapter 35's, which stored the colour alone, and
records the flag beside it:

```cpp
// A material the flat pipeline can draw: registered with the scene renderer, which batches by material,
// and its color kept here, under the same index, for the run's push constant. Chapter 37 section 2: and
// whether it is lit, which the plates are not.
uint32_t HorizonDemo::AddFlatMaterial(const char* name, glm::vec3 color, bool lit)
{
    const uint32_t index = m_sceneRenderer.AddMaterial(scene::Material{ .name = name, .baseColor = glm::vec4(color, 1.0f) });
    m_materialColors.resize(std::max<std::size_t>(m_materialColors.size(), index + 1));
    m_materialColors[index] = glm::vec4(color, 1.0f);
    m_materialFlags.resize(m_materialColors.size());
    m_materialFlags[index] = lit ? FLAT_LIT : 0u;
    return index;
}
```

`Teardown` clears the flags with the colours, after `m_materialColors.clear()`:

```cpp
    m_materialFlags.clear();    // Chapter 37
```

In `RegisterProps`, the call to `AddFlatMaterial` that this section's first half
wrote with two arguments, `AddFlatMaterial(source.name.c_str(),
glm::vec3(source.baseColor))`, becomes this one, with `true` for lit:

```cpp
        AddFlatMaterial(source.name.c_str(), glm::vec3(source.baseColor), true);
```

`FALLBACK_SKY`, the sky's colour with the engine's sky off, is in
`Terrain.cpp`. The objects' haze needs it too, so it moves to `Terrain.h`,
after `TERRAIN_RINGS`, as an `inline constexpr`, and its lines in
`Terrain.cpp` go:

```cpp
// Chapter 36 section 10: what the sky is with the engine's sky off: the demo's clear color (Chapter 35
// section 1), so the haze fades far ground into the background. Chapter 37: here, so the objects' haze
// reads it too.
inline constexpr glm::vec3 FALLBACK_SKY{ 0.45f, 0.60f, 0.80f };
```

Last, the lambda that `Record` passes to `RecordBatches`, below the terrain's
call, fills the new push constants: the material's flag, the
sky's colour and the terrain's haze distance, so an object fades exactly as the
ground behind it does, and whether the sky is on. That is also the terrain's
last argument, so it becomes a variable, before the terrain's `Record`:

```cpp
    const bool skyOn = frame.sky.mode != SkyMode::Off;
    m_terrain.Record(commandBuffer, m_sceneRenderer, frame.frameIndex, m_terrainSettings, m_ringCenter, skyOn);
```

and in the callback the push constant becomes:

```cpp
        const FlatDraw draw{
            .baseColor = m_materialColors[run.material],
            .sky       = glm::vec4(FALLBACK_SKY, m_terrainSettings.hazeDistance),   // Chapter 37: the terrain's
            .flags     = m_materialFlags[run.material] | (skyOn ? FLAT_SKY : 0u),
        };
```

Build and run: the same house, lit. The gable end, facing you, takes the sun,
which comes from behind your right shoulder; the side wall on the left, turned
away from it, is in shade and shows only the sky's light, and so does that side
of the plinth. It looks like part of the island now, not cut out and laid over
it.

## 3. Villages and landmarks

**This is the villages and landmarks in `Props.h`, `Place`, a first `Update`,
the props in `Record` before `CollectDraws`, the views, and the panel.**

### Where things stand

The places are numbers above the class in `Props.h`: five villages and three
landmarks, all inside the 5 km disc the camera may roam (Chapter 35 section 4).
They go inside the namespace, above `LOD_HIDDEN`:

```cpp
// Section 3: where the villages and the landmarks stand, metres from the origin, picked by hand from the
// heightmap. Each village is a clearing on a gentle slope; its houses face along `turn` (degrees), which runs
// along the slope, or across it.
struct Village
{
    glm::vec2 centre;
    uint32_t  houses;
    float     turn;
};
inline constexpr std::array<Village, 5> VILLAGES{ {
    { { 72.0f, -1128.0f }, 14, 23.0f },       // 1.1 km from the viewpoint, straight ahead, below the tower's hill
    { { 1384.0f, -1816.0f }, 12, 54.0f },     // 2.3 km, ahead and to the right
    { { -2040.0f, -2808.0f }, 10, 72.0f },    // 3.5 km, ahead and to the left, on a shelf 335 m up
    { { 2040.0f, 1000.0f }, 14, 49.0f },      // 2.3 km, behind and to the right, by the lighthouse
    { { -4392.0f, 520.0f }, 10, -6.0f },      // 4.4 km, to the left, in the mountains 600 m up
} };
struct Landmark
{
    const char* asset;
    glm::vec2   position;
    float       turn;   // degrees
};
inline constexpr std::array<Landmark, 3> LANDMARKS{ {
    { "Landmark_Lighthouse", { 2339.0f, 1041.0f }, 0.0f },   // on the shore nearest the viewpoint, 2.6 km
    { "Landmark_Tower", { 88.0f, -2600.0f }, 0.0f },         // on a hilltop straight ahead of the viewpoint
    { "Landmark_Keep", { -2328.0f, -1044.0f }, 30.0f },      // on the island's highest ground, 954 m
} };
```

They were picked by hand from the heightmap, laid under the origin as
`MAP_ORIGIN` lays it (Chapter 36 section 9): each village in a clearing, on
ground that slopes gently, above the sea, 1.1 to 4.4 km from the viewpoint (the
comments say which way). Each village's `turn` runs along its slope, so its
houses stand along the hillside, not across it.

The landmarks stand where each is worth seeing from:

- **The lighthouse**, on the shore nearest the viewpoint, 114 degrees to the
  right of the start heading, where Chapter 36 section 10 turned to find the
  sea; 30 m inland, on ground 1 m above the water.
- **The watchtower**, on a hilltop 516 m high, in the middle of the start view.
- **The keep**, on the summit Chapter 36's exit check turns to, 66 degrees to
  the left.

### Placing them

`Place` gets its real body, in place of section 2's one house: replace the
whole function, its comment too. It runs once, after the terrain has loaded its
heightmap, because it asks the ground where houses can stand. Each village's
houses are scattered at random within 75 m of its centre, 14 m apart at least.
The point is drawn at a random angle and at the square root of a random
fraction of the radius, because a disc has more area near its rim than near its
centre, and the square root spreads the points evenly over that area instead of
crowding them in the middle.

A spot is passed over if its ground is less than 2 m above the sea, or if the
ground's drop across the house's 8 m and its drop along its 6 m add up to more
than 2 m, the depth of the plinth. Every height comes from `HeightAt` with the
spot itself as the rings' centre, its second argument: the ground as the rings
draw it when they are centred there, which is the heightmap's finest mip level,
level 0, with all three noise octaves (Chapter 36 section 6), the true ground.
A house is turned along the village's `turn` or across it, by a whole number of
quarter turns, 0 to 3, with a little play.

A random generator with a fixed seed makes the same villages every run, and
every one of the five gets all its houses. Eight rocks ring each village, the
three landmarks go on their sites, and ten rocks lie round the keep. The
includes this needs join the top of `Props.cpp`: `<glm/gtc/constants.hpp>`
beside the quaternion header, and `<algorithm>`, `<cmath>` and `<random>` with
`<format>`:

```cpp
void Props::Place(const Terrain& terrain, const TerrainSettings& terrainSettings)
{
    if (!Loaded() || !m_objects.empty())
    {
        return;   // nothing to place, or placed already
    }
    const uint32_t house = FindAsset("House");
    const uint32_t rock  = FindAsset("Rock");
    std::mt19937   random(37);   // the same villages every run
    std::uniform_real_distribution<float> unit(0.0f, 1.0f);

    // Section 3: each village's houses, at random within 75 m of its centre, no two closer than 14 m. A spot
    // less than 2 m above the sea is passed over, and so is one where the ground's drop across the house's
    // 8 m and its drop along its 6 m add up to more than 2 m, the depth of its plinth. Some rocks round it.
    for (const Village& village : VILLAGES)
    {
        std::vector<glm::vec2> placed;
        for (uint32_t attempt = 0; attempt < 200 && placed.size() < village.houses; ++attempt)
        {
            // The square root spreads the spots evenly over the disc's area, not crowded at its centre.
            const float     angle = glm::two_pi<float>() * unit(random);
            const glm::vec2 xz    = village.centre + 75.0f * std::sqrt(unit(random)) * glm::vec2(std::cos(angle), std::sin(angle));
            const bool crowded = std::any_of(placed.begin(), placed.end(),
                                             [&](glm::vec2 other) { return glm::distance(xz, other) < 14.0f; });
            auto ground = [&](glm::vec2 offset) { return terrain.HeightAt(xz + offset, xz, terrainSettings); };
            const float drops = std::abs(ground({ 4.0f, 0.0f }) - ground({ -4.0f, 0.0f }))
                              + std::abs(ground({ 0.0f, 3.0f }) - ground({ 0.0f, -3.0f }));
            if (crowded || ground({ 0.0f, 0.0f }) < 2.0f || drops > 2.0f)
            {
                continue;
            }
            const float quarter = static_cast<float>(static_cast<int>(4.0f * unit(random)));   // 0 to 3 quarter turns
            const float turn    = glm::radians(village.turn + 90.0f * quarter + 16.0f * (unit(random) - 0.5f));
            AddObject(house, xz, turn, 1.0f);
            placed.push_back(xz);
        }
        for (uint32_t i = 0; i < 8; ++i)
        {
            const float     angle = glm::two_pi<float>() * unit(random);
            const glm::vec2 xz    = village.centre + (90.0f + 40.0f * unit(random)) * glm::vec2(std::cos(angle), std::sin(angle));
            AddObject(rock, xz, glm::two_pi<float>() * unit(random), 0.8f + 1.6f * unit(random));
        }
    }

    // Section 3: the landmarks, and rocks round the keep on its summit.
    for (const Landmark& landmark : LANDMARKS)
    {
        AddObject(FindAsset(landmark.asset), landmark.position, glm::radians(landmark.turn), 1.0f);
    }
    for (uint32_t i = 0; i < 10; ++i)
    {
        const float     angle = glm::two_pi<float>() * unit(random);
        const glm::vec2 xz    = LANDMARKS[2].position + (16.0f + 25.0f * unit(random)) * glm::vec2(std::cos(angle), std::sin(angle));
        AddObject(rock, xz, glm::two_pi<float>() * unit(random), 1.0f + 2.0f * unit(random));
    }
}
```

### Standing on the ground

`AddObject` put every object at height 0. `Update`, which goes after `Place`,
stands each on the ground every frame, for now on the true ground right under
it. It marks every node
every frame with `EditLocal`, which flags a node for `UpdateWorldTransforms` to
recompute, with everything below it (Chapter 12 section 4); a few hundred
objects make that nothing, and section 7, with thousands of trees, marks only
the moves that would show. Then the world transforms are brought up to date
once for all:

```cpp
void Props::Update(const Terrain& terrain, const TerrainSettings& terrainSettings, glm::vec2 /*ringCenter*/,
                   glm::vec3 /*camera*/, float /*screenScale*/, const PropSettings& /*settings*/)
{
    if (!Loaded())
    {
        return;
    }

    for (Object& object : m_objects)
    {
        // Section 3: on the ground right under it, as the rings draw it when they are centred there.
        const glm::vec3 base(object.xz.x, terrain.HeightAt(object.xz, object.xz, terrainSettings), object.xz.y);

        // Section 3: EditLocal marks the node, and UpdateWorldTransforms recomputes every node marked, with
        // everything below it. Every object, every frame, for now: section 7 moves only what would show.
        m_scene.EditLocal(object.node).translation.y = base.y;
    }
    m_scene.UpdateWorldTransforms();
}
```

The parameters with their names commented out are later sections'. Running it
every frame looks like waste while the ground under an object never changes;
section 4 finds that it does.

In `Record`, the comment above section 2's `CollectDraws` call is replaced by
the one below, and `Update` goes before that call. `screenScale` is section 5's
(it derives it there). This block ends where the `CollectDraws` call begins, so
that call stays as it is:

```cpp
    // Chapter 37: the props. The pool follows the camera, each takes its level and stands on the ground as it
    // is drawn now (sections 3, 4, 5, 7); then what the camera sees, and what casts shadows (sections 2, 8).
    const float screenScale = static_cast<float>(extent.height) / std::tan(0.5f * m_camera.verticalFov);
    m_props.Update(m_terrain, m_terrainSettings, m_ringCenter, m_cameraTransform.translation, screenScale,
                   m_propSettings);
```

### Places to look from

The props are small from 1,000 m up, and the nearest village is 1.1 km away. A
few buttons put the camera where there is something to see: over a point, so
many metres above the ground there, turned and tipped. The views go among the
constants at the top of `HorizonDemo.cpp`, after `GROUND_CLEARANCE`:
**Village** looks at the nearest village from its south-east; **Wood** stands
at the edge of a wood, looking in; **Tower** looks up at the watchtower from
800 m south of it and about 230 m below its hilltop; **Far side** sees the keep
from the sea, 7.5 km off on the far side of the disc, standing on the island's
skyline; and **Edge** stands in a clearing with a wood 540 to 750 m ahead, for
section 7:

```cpp
// Chapter 37 section 3: places to look at the props from: over a point, so many metres above the ground there,
// turned (yaw, degrees: positive turns left from -Z) and tipped (pitch, degrees: positive looks up).
struct View
{
    const char* label;
    glm::vec2   xz;
    float       height;
    float       yaw;
    float       pitch;
};
constexpr std::array<View, 5> VIEWS{ {
    { "Village", VILLAGES[0].centre + glm::vec2(110.0f, 110.0f), 20.0f, 45.0f, -4.0f },   // from its south-east
    { "Wood", { 808.0f, -112.0f }, 12.0f, 105.0f, -3.0f },                                // at its edge, looking in
    { "Tower", LANDMARKS[1].position + glm::vec2(0.0f, 800.0f), 60.0f, 0.0f, 15.0f },    // 800 m off, below it
    { "Far side", { 4651.0f, 1693.0f }, 30.0f, 69.0f, 5.0f },                             // the keep, 7.5 km off
    { "Edge", { 2028.0f, -311.0f }, 10.0f, -15.0f, -1.0f },                               // a wood 540-750 m ahead
} };
```

`GoTo` stands the camera on the ground there with Chapter 36's `HeightAt`, at
the end of the file. The `std::max` with 0 is the sea: over water the ground is
below 0, and the camera stands on the water's surface instead:

```cpp
// Chapter 37 section 3: the camera over a point, `height` metres above the ground there, turned and tipped.
void HorizonDemo::GoTo(glm::vec2 xz, float height, float yaw, float pitch)
{
    const float ground = std::max(m_terrain.HeightAt(xz, xz, m_terrainSettings), 0.0f);
    m_cameraTransform.translation = { xz.x, ground + height, xz.y };
    m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = glm::radians(yaw), .pitch = glm::radians(pitch) });
}
```

The panel gains a group under the terrain's, **Objects**, which every later
section adds to. `DrawPanel` calls it after `DrawTerrainControls`:

```cpp
        DrawPropControls();      // Chapter 37 section 3
```

`DrawPropControls` goes after `GoTo`, at the end of the file, and for now it
holds the buttons:

```cpp
// Chapter 37: the props' group, under the terrain's.
void HorizonDemo::DrawPropControls()
{
    ImGui::SeparatorText("Objects");

    // Section 3: places to look from.
    for (const View& view : VIEWS)
    {
        if (ImGui::Button(view.label)) { GoTo(view.xz, view.height, view.yaw, view.pitch); }
        ImGui::SameLine();
    }
    ImGui::NewLine();
}
```

Build and run, and click **Village**: houses with red roofs in a clearing, rocks
round them, every house in full detail. **Tower**: the watchtower, 800 m off and
above you, a white shaft with a red cap. Look at its foot. It does not stand on
its hill: there is sky between the two, some 60 pixels of it, and the tower
floats. Section 4 says why.

**Back to the viewpoint** shows it from 2.6 km too: the watchtower floats about
40 pixels above its hilltop. Turn to the keep on the summit with a right-button
drag left of about 385 pixels, the pointer on the scene (66 degrees; Chapter 35
section 1): it hangs in the sky too, with sky between its foot and the ridge.

## 4. The ground, as it is drawn

**This is the heightmap's mip levels on the CPU, `MapHeight` at any mip level,
`HeightAt` at the mip level the rings read, and `Update` standing everything on
the ground the rings draw now.**

### Why the tower floats

The watchtower stands where `HeightAt` says the ground is, with the rings
centred on the tower itself: the true hilltop, 516 m. But that is not what is
drawn there from the viewpoint. Chapter 36 section 9 has each ring read the
heightmap's mip level whose texels are two of its cells across, so that it
never draws a hill too narrow for its cells. The hilltop is 2.6 km off, where
the cells are big and the mip level is small.

> **Jump:** until now the CPU's copy of the ground only had to be right under
> the camera, where the rings read the finest mip level. From here on it must
> be right anywhere the camera can see: the CPU works out, for each object, the
> mip level the GPU reads at that distance, from mip levels the CPU makes
> itself the way the GPU's blits made them. Keep both halves in mind, the
> choice of level and the levels themselves.

The cell size is Chapter 36 section 3's, and the mip level its section 9's,
for a texel of the finest level 8 m across (its section 7):

$$
c = \frac{d}{N/4 - 1}, \qquad \text{level} = \log_2 \frac{2c}{8\,\text{m}}
$$

with *d* the distance from the rings' centre along x or z, whichever is
further, and *N* the cells across a ring. From the viewpoint the hilltop is
2,600 m off along z. With the Low preset's 64 cells, *c* = 2,600 / 15 = 173 m,
and the mip level is log₂(43.3) ≈ 5.4: between level 5, whose texels are 256 m
across, each the average of 1,024 of level 0's, and level 6, whose texels are
512 m across. A hilltop averaged over a few hundred metres is a low hump.
Sampled there, the hilltop is drawn 178 m lower than it is, and the tower
stands on air 178 m above it. With the Full preset's 128 cells, *c* is 84 m and
the mip level 4.4, and the gap is smaller. The keep's summit is a sharper peak,
and from the viewpoint it is drawn lower still. Fly toward the tower and it
seems to sink, because the cells under it shrink and the hilltop grows back up
to it.

Villages are wrong on a smaller scale. On a gentle slope the averages hardly
change the ground, but round a hollow or a knoll they do: from the viewpoint,
the ground under the villages' houses is drawn several metres above the true
ground in places, which buries a house past its eaves, and a metre or two below
it in others, which its plinth covers.

The ground the rings draw depends on where the rings are centred, which is the
camera. An object must stand on that ground, so its height comes from the same
mip level the shader reads, every frame, as the camera moves.

### The mip levels on the CPU

`HeightAt` reads only mip level 0, from `m_heights`, the CPU's copy of the
file. The GPU makes the other levels with blits, each texel the average of the
2 × 2 above it (Chapter 36 section 8), and rounds each to 16 bits, because the
image is `R16_UNORM`. The CPU makes the same levels the same way. In
`Terrain.h`, beside `m_heights`:

```cpp
    std::vector<std::vector<uint16_t>> m_mips;       // Chapter 37 section 4: mip levels 1 and down, as the blits make them
```

and in `LoadHeightmap`, where a file was loaded, after its `Log::info` and
before the `return`:

```cpp
        // Chapter 37 section 4: the mip levels below, as UploadHeightmap's blits make them on the GPU: each
        // texel the average of the 2 x 2 above it, rounded to 16 bits again. HeightAt reads the ones the rings
        // read.
        m_mips.clear();
        uint32_t above = m_heightmapSize;   // the side of the level above
        while (above > 1)
        {
            const std::vector<uint16_t>& source = m_mips.empty() ? m_heights : m_mips.back();
            const uint32_t               side   = above / 2;
            std::vector<uint16_t>        level(static_cast<size_t>(side) * side);
            for (uint32_t z = 0; z < side; ++z)
            {
                for (uint32_t x = 0; x < side; ++x)
                {
                    const size_t   corner = static_cast<size_t>(2 * z) * above + 2 * x;   // the 2 x 2's top left
                    const uint32_t sum    = source[corner] + source[corner + 1] + source[corner + above]
                                          + source[corner + above + 1];
                    level[static_cast<size_t>(z) * side + x] = static_cast<uint16_t>((sum + 2) / 4);
                }
            }
            m_mips.push_back(std::move(level));
            above = side;
        }
```

The sum of four 16-bit values fits a 32-bit one, and adding 2 before dividing by
4 rounds to the nearest. The mip levels together take a third of level 0's
memory again: 11 MB for this map, beside level 0's 33.5 MB.

`MapHeight` takes the mip level to read. It is Chapter 36's function with the
level's texels and its size in place of level 0's: its signature changes, two
lines are new, and three change. The declaration in `Terrain.h` gains the
parameter:

```cpp
    float                MapHeight(glm::vec2 xz, uint32_t level) const;          // section 9; Chapter 37 section 4: the mip level
```

and in `Terrain.cpp`:

```cpp
// In place of the comment above the function and its signature, with two new lines after the brace:
// Chapter 36 section 9: the shader's mapHeight at mip level 0, the level under the camera: a bilinear sample
// of the same 16-bit values, with the texel centres where the GPU puts them, half a texel in from each edge.
// Chapter 37 section 4: at any whole mip level, from the CPU's copy of it.
float Terrain::MapHeight(glm::vec2 xz, uint32_t level) const
{
    const std::vector<uint16_t>& heights = level == 0 ? m_heights : m_mips[level - 1];
    const uint32_t               size    = std::max(m_heightmapSize >> level, 1u);

// In place of the `last` line and the `texel` line:
    const int       last  = static_cast<int>(size) - 1;
    const glm::vec2 texel = ((xz + MAP_ORIGIN) / MAP_SIZE + 0.5f) * static_cast<float>(size) - 0.5f;

// In place of the line in the lambda that returns the texel:
        return static_cast<float>(heights[static_cast<size_t>(z) * size + static_cast<size_t>(x)]) / 65535.0f;
```

`HeightAt` then reads at the mip level the shader's `mapHeight` reads at, the
same `log2` of the same cell. The level is rarely a whole number, and the
sampler blends the two whole levels round it by the fraction
(`MIPMAP_MODE_LINEAR`, Chapter 15 section 5); `HeightAt` does the same, and
stops at the last level:

$$
h = (1 - f)\, h_{\lfloor \ell \rfloor} + f\, h_{\lfloor \ell \rfloor + 1},
\qquad f = \ell - \lfloor \ell \rfloor
$$

At the watchtower's hilltop, from the viewpoint with the Full preset, ℓ is
4.39: *f* = 0.39, and the ground is 0.61 of level 4's height there plus 0.39
of level 5's. This function replaces Chapter 36's `HeightAt` in full, comment
and all; its declaration in `Terrain.h` does not change:

```cpp
// Chapter 36 section 6: terrainHeight on the CPU, for rings centred on ringCenter: the octaves fade by the
// same cell as in the shader. Its section 9 adds the heightmap. Chapter 37 section 4: from the mip level the
// shader's mapHeight reads there, blended between the two whole levels around it as the sampler blends them,
// so this is the ground as it is drawn at any distance, not only under the camera.
float Terrain::HeightAt(glm::vec2 xz, glm::vec2 ringCenter, const TerrainSettings& settings) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
    const float          cell   = cellSizeAt(xz, ringCenter, preset.finestCell, static_cast<float>(preset.cells));
    if (!m_hasHeightmap)
    {
        return noiseOctaves(xz, cell, 8192.0f, 13);
    }
    const float    texel = MAP_SIZE / static_cast<float>(m_heightmapSize);
    const float    level = std::log2(std::max(2.0f * cell / texel, 1.0f));
    const uint32_t last  = static_cast<uint32_t>(m_mips.size());
    const uint32_t below = std::min(static_cast<uint32_t>(level), last);
    const uint32_t upper = std::min(below + 1, last);
    const float    map   = glm::mix(MapHeight(xz, below), MapHeight(xz, upper), std::min(level - static_cast<float>(below), 1.0f));
    return map + noiseOctaves(xz, cell, 8.0f, 3);
}
```

Under the camera, with the rings centred on it, the cell is ring 0's and the
mip level is 0, so the camera's ground clamp (Chapter 36 section 6) is exactly
what it was. Under a camera flown away from frozen rings it is not: Chapter
36's `HeightAt` read mip level 0 there while the frozen rings drew the coarser
levels, so over the heightmap the clamp could stop the camera on ground that
was not drawn (Chapter 36 section 9). Now `HeightAt` is the ground the frozen
rings draw there.

The GPU and the CPU do the same arithmetic on the same 16-bit values, but not
quite in the same order: the GPU filters with a few bits fewer of precision
than a float (Chapter 36 section 9), and blends between the triangles' corners,
where `HeightAt` samples the point itself. The two agree to a fraction of a
metre near the camera, and to a metre or two where the cells are hundreds of
metres across, which the plinths cover.

### Standing on it

In `Update`, the object's ground comes from rings centred where they are now:
`ringCenter`, in place of the object's own position, and the parameter gets its
name back. The two lines below, a comment and the `base` declaration, replace
the pair at the top of the loop's body that section 3 wrote:

```cpp
        // Section 4: on the ground as the rings draw it now, from where they are centred.
        const glm::vec3 base(object.xz.x, terrain.HeightAt(object.xz, ringCenter, terrainSettings), object.xz.y);
```

That is why `Update` runs every frame: as the camera moves, the mip level
under a far object changes, and the object moves up or down with the ground it
stands on.

## Checkpoint

Rerun `GenerateProjects.bat` if you have not since section 2, build, and run
with `--demo Horizon`. From the viewpoint the watchtower stands on its hilltop,
straight ahead; turn left toward the summit, and the keep stands on it. Fly
toward the tower with Shift and W: the hill rises as you close in, and the
tower rides up with it. **Village** shows the houses in their clearing,
**Wood** a field and the trees section 7 will plant, none yet, and **Far side**
the keep on the island's skyline 7.5 km away, with the lighthouse on the shore
below it to the left.

Turn on **Freeze rings**, click **Tower**, and look: with the rings left at the
viewpoint, the hill is drawn as from 2.6 km away, low and round, and the tower
stands on that. (Without Freeze rings, a view button shows one odd frame of
this too: the camera moves in `DrawPanel`, which `HorizonDemo::Update` calls
after it has centred the rings on the camera, so for one frame the rings are
still where you were, and the ground at the new place is drawn as from far
away; the next frame they follow.)

---

# Part 2 — Levels of detail (section 5)

Every object so far shows `LOD0`, whether it is 30 m away or 3 km; Part 2 gives
each the level its size on screen asks for.

## 5. Height on screen

**This is the thresholds in `Props.h`, `chooseLevel`, the levels in `Update`,
the level controls in the panel, the levels' colours, and the rule for
landmarks.**

### How tall a thing looks

Chapter 35 worked out how large a far thing looks: a thing of size *s* at
distance *d* spans about *s*/*d* radians, and near the middle of the screen one
radian is (*H*/2) / tan(θ/2) pixels, where *H* is the window's height in pixels
and θ the vertical field of view. The thing measured here is the sphere round
`LOD0`, of radius *r*, so *s* is 2*r*, and its height on screen in pixels is

$$
p = \frac{2r}{d} \cdot \frac{H / 2}{\tan(\theta / 2)} = \frac{r \, H}{d \, \tan(\theta / 2)}
$$

with *d* from the camera to the sphere's centre. The house's sphere has a
radius of 7.6 m. Seen from 200 m in a window 720 pixels tall with the 60° lens:

$$
p = \frac{7.6 \times 720}{200 \times \tan 30^\circ} = \frac{5472}{115.5} \approx 47 \text{ pixels}
$$

It is a measure, not a drawing: the house itself, 7 m from the ground to its
ridge, is about 22 pixels of it. Using the sphere makes the number the same
from every side and at every angle, and the same for a tall thin tower and a
low wide house of the same size.

*H* / tan(θ/2) is the same for every object in a frame, so `Record` works it
out once, from the window's height and the camera's field of view, as
`screenScale` (section 3 already passes it). A bigger window or a narrower lens
makes everything taller on screen, and every object moves to a finer level by
itself: the rule needs no retuning when either changes. *Unity*'s LOD Group
works the same way, by an object's height as a fraction of the screen's.

### Three lines

Three numbers, in pixels, are the whole of the level of detail. They go in
`Props.h`, above `LOD_HIDDEN`:

```cpp
// Section 5: the height on screen, in pixels, below which each level gives way to the next: LOD0 above 150,
// LOD1 down to 40, LOD2 down to 4, nothing below that. A change needs the height past the line by
// LOD_HYSTERESIS, 15 % of the line, in the direction it goes, so an object close to a line does not flicker.
inline constexpr std::array<float, 3> LOD_PIXELS{ 150.0f, 40.0f, 4.0f };
inline constexpr float                LOD_HYSTERESIS = 0.15f;
```

Above 150 pixels an object shows `LOD0`; down to 40, `LOD1`; down to 4,
`LOD2`; below 4, nothing. At 150 pixels the house is about 70 pixels from the
ground to its ridge, and its windows, the smallest detail `LOD0` has over
`LOD1`, are a dozen pixels tall; at 40 the silhouette is all that reads, and
the proxy has it; at 4 an object is a speck, and not drawing it saves the draw
and loses almost nothing. For four of the assets, in this 720-pixel window with
the 60° lens (at 1440 pixels, the distances double):

| Asset | *r* | `LOD0` to | `LOD1` to | `LOD2` to |
| --- | --- | --- | --- | --- |
| `House` | 7.6 m | 63 m | 236 m | 2.4 km |
| `Pine` | 7.9 m | 66 m | 247 m | 2.5 km |
| `Landmark_Tower` | 36.5 m | 304 m | 1.1 km | 11.4 km |
| `Landmark_Keep` | 51.9 m | 431 m | 1.6 km | 16 km |

### A margin round each line

A house exactly 236 m away sits on the line between `LOD1` and `LOD2`. The
camera moves a hand's width, the ground under the house moves a centimetre
(section 4), and the house changes level; back, and it changes again. Every
change is a visible pop, and an object near a line can pop every frame.

The cure is **hysteresis**: the line an object crosses depends on which side it
is on. Going coarser, it must fall 15 % below the line; coming back, it must
rise 15 % above it. For the house at the 40-pixel line, it goes to `LOD2` below
34 pixels, at 278 m, and comes back to `LOD1` above 46 pixels, at 206 m.
Anywhere between 206 and 278 m it keeps the level it had, so wobbling there
changes nothing. *Elden Ring* does the same by distance: each level of a map
part has a switch distance and a "play" band round it (`lv01_BorderDist` and
`lv01_PlayDist` in its `PartsDrawParam`).

`chooseLevel` walks down the lines from the finest. Line *k*,
`LOD_PIXELS[k]`, separates level *k* from level *k* + 1, and for each line the
object's current level says which side of it the object is on. If its level is
past line *k*, coarser than *k*, it must reach 1.15 times the line to come
back; if its level is *k* or finer, it stays until it falls below 0.85 times
the line. The first line the height clears is the level; clearing none is
hidden. It goes inside the namespace, after `ASSET_FILES`: it reads
`LOD_PIXELS`, which is the namespace's, where `findNode` and `utf8`, above the
namespace, read nothing of it:

```cpp
// Section 5: the level for an object `pixels` tall on screen that is at `current` now. Each line moves
// LOD_HYSTERESIS away from the side the object is on: past a line (coarser), it needs 15 % more to come back;
// at or before it, 15 % less to go.
static uint32_t chooseLevel(float pixels, uint32_t current)
{
    uint32_t level = 0;
    while (level < LOD_HIDDEN)
    {
        const float margin = current > level ? 1.0f + LOD_HYSTERESIS : 1.0f - LOD_HYSTERESIS;
        if (pixels >= LOD_PIXELS[level] * margin)
        {
            break;
        }
        ++level;
    }
    return level;
}
```

### Choosing, every frame

`Update` gains the level, after the object is placed. It needs the distance
from the camera to the sphere's centre, the asset's centre scaled with the
object (and not turned with it: every asset here is centred on its y axis to
within a few decimetres, so a turn moves the centre by less than that), so the
asset goes into a variable at the top of the loop's body, and the
distance after `base`:

```cpp
        const Asset& asset = m_assets[object.asset];

        const float     distance = glm::distance(base + asset.centre * object.scale, camera);
```

and, at the end of the loop's body, the choice, the one level shown, and the
count of objects at each level. `SetVisible` turns every level off but the one
chosen: each visible node is drawn, so two levels shown at once would be both
drawn, in the same place (Chapter 12 section 6):

```cpp
        // Section 5: the level for its height on screen, unless the panel froze them; a landmark past the last
        // line keeps its coarsest level.
        if (!settings.freezeLod)
        {
            const float pixels = settings.lodBias * asset.radius * object.scale * screenScale / std::max(distance, 0.001f);
            object.level = chooseLevel(pixels, object.level);
            if (object.level == LOD_HIDDEN && asset.landmark)
            {
                object.level = 2;
            }
        }
        for (uint32_t level = 0; level < 3; ++level)
        {
            m_scene.SetVisible(object.levels[level], level == object.level);
        }
        ++m_counts.levels[object.level];
```

`m_counts = {};` goes just before the loop, and the three parameters get their
names back. `AddObject`'s two lines that hid `LOD1` and `LOD2` go: `Update`
shows one level from the first frame. A new object starts at `LOD_HIDDEN`,
the coarsest side of every line, so it comes in at the level its size calls
for; inside a band, it takes the coarser of the two.

Two settings come with it, in `PropSettings`. **LOD bias** multiplies every
height on screen: at 2, everything takes the level it would have at half the
distance; at 0.5, at twice. It is the one knob for all assets at once, the knob
a slower GPU turns. **Freeze levels** stops the choosing, so you can fly round
an object and see the level it had. It freezes the hidden too: once section 7
plants trees, a tree planted while the levels are frozen starts at
`LOD_HIDDEN`, and stays hidden until you untick it. A tree that shrinks to
nothing while they are frozen, section 7's shrink, is not hidden either: it
keeps its level at no size, which no one can see.

### Seeing the levels

**Show levels** draws every object in its level's colour: red `LOD0`, yellow
`LOD1`, blue `LOD2`. The flat pipeline draws one colour per material, so the
view swaps materials. The colours go among the constants at the top of
`HorizonDemo.cpp`, after the views; the three materials, lit, are made in
`Setup`, right after the call to `CreatePlates`:

```cpp
// Chapter 37 section 5: each level's color in the "Show levels" view: red, yellow, blue.
constexpr std::array<glm::vec3, 3> LEVEL_COLORS{ { { 0.8f, 0.1f, 0.1f }, { 0.8f, 0.7f, 0.1f }, { 0.1f, 0.3f, 0.9f } } };
```

```cpp
    for (uint32_t level = 0; level < 3; ++level)                           // Chapter 37 section 5
    {
        m_levelMaterials[level] = AddFlatMaterial(std::format("LOD{}", level).c_str(), LEVEL_COLORS[level], true);
    }
```

In `Record`, each draw's material becomes its level's, by the mesh it draws,
which `LoadAsset` noted in `m_meshLevels`. It goes after `CollectDraws` and
before the `if (m_showPlates)` block, and the order matters: the plates' meshes
are not the props', and `m_meshLevels` has no entry for them, so after the
plates are added the loop would read past its end:

```cpp
    if (m_propSettings.showLevels)   // Chapter 37 section 5: each draw in its level's color
    {
        for (scene::DrawItem& draw : m_draws)
        {
            draw.material = m_levelMaterials[m_props.MeshLevel(draw.mesh)];
        }
    }
```

The **Objects** group shows how many objects are at each level, and the
controls, after the view buttons:

```cpp
    // Section 5: the levels, how many objects show each, and the bias.
    const PropCounts& counts = m_props.Counts();
    ImGui::Text("LOD0 %u  LOD1 %u  LOD2 %u  hidden %u", counts.levels[0], counts.levels[1], counts.levels[2],
                counts.levels[3]);
    ImGui::Checkbox("Show levels", &m_propSettings.showLevels);
    ImGui::SameLine();
    ImGui::Checkbox("Freeze levels", &m_propSettings.freezeLod);
    ImGui::SliderFloat("LOD bias", &m_propSettings.lodBias, 0.25f, 4.0f, "%.2f", ImGuiSliderFlags_Logarithmic);
```

### Landmarks

Below 4 pixels an object is hidden. A landmark is not clutter: the keep on the
skyline is how you know where the summit is from anywhere on the island, and
one silhouette there is worth more than a hundred trees in front of it. A
**landmark** keeps its coarsest level however small it gets, and costs one
draw of ten triangles for it. *Just Cause 2* kept simple models of its
landmarks loaded at all times, so they could be seen from anywhere on its
32 km map.

That is the `if` after `chooseLevel`, above, for any asset whose name begins
with `Landmark_`, as `LoadAsset` noted. In this world it is a promise more
than a rescue. The camera stays within 5 km of the origin, so the farthest it
gets from the lighthouse is 7.6 km, still above the last line in this window at
bias 1. The rule earns its place when the window is smaller or the bias lower:
at **LOD bias** 0.25 the lighthouse's last line comes in to 2.4 km, nearer than
the viewpoint is to it, 2.6 km. And the rule only keeps a landmark drawn; it
cannot make it cover a pixel. From **Far side** the keep is 7.5 km away, about 8
pixels tall on screen, its proxy 2 pixels wide: a landmark needs size as well as
the rule, which is why the keep was made 24 m square.

## Checkpoint

Run, and click **Village**. Turn on **Show levels**: the nearest houses are
yellow, `LOD1`, the far ones blue boxes, and the panel counts each. Drag the
**LOD bias** to its left end, 0.25: every house turns blue. Back to 1. Click
**Far side**: the keep stands on the skyline 7.5 km away, blue, `LOD2`. Drag
the bias to 0.25 again: it is 2 pixels by the measure now, below the last
line, and it stays, because it is a landmark. Back to 1. With **Freeze
levels** on, fly toward the village: the far houses stay boxes as they come
close.

---

# Part 3 — Trees (sections 6-7)

Part 3 grows trees round the camera: a function that says where forest grows,
then a pool of tree objects planted from it.

## 6. Where the forest grows

**This is `ForestDensity.glsl`, its copy in `Terrain.cpp`, and the Show forest
view.**

### Written once, in two languages

Two things will plant trees from the same rule: this chapter's mesh trees, on
the CPU, and Chapter 40's far forest, on the GPU, which takes over where the
mesh trees end. If the two disagreed, a billboard would stand where a mesh tree
just stood, or where none did. So the rule is a GLSL include with a copy in
C++, line for line, as Chapter 36 section 6 copied the terrain's height.

> **Jump:** section 4 copied the GPU's ground to the CPU and accepted a metre or
> two of difference, which the plinths hide. A forest cannot accept any: a tree
> is there or it is not, and a difference in the last bit can plant one on one
> side and not the other. So the rule avoids the one thing the CPU cannot copy
> bit for bit, the sampler's filtering, and reads stored texels with
> `texelFetch` instead. Keep in mind that this copy is exact, where section 4's
> was close.

Two things make the copy exact rather than nearly so:

- **The heightmap is read with `texelFetch`**: one texel of mip level 0, as
  stored, with no filtering. The sampler's blend weights are rounded on the GPU
  (Chapter 36 section 9); a stored value, divided by 65,535, is the same number
  in both languages. The texel under a point is found as `mapHeight` finds it,
  with `MAP_ORIGIN` added, so the forest lies on the island where the island
  is drawn.
- **Randomness is a hash**: `pcgHash` and Chapter 21 section 3's
  `randomFloat`, integer arithmetic that wraps the same way in GLSL's `uint` and
  C++'s `uint32_t`.

The float arithmetic after that is the same operations in the same order. A GPU
may fuse a multiply and an add, a rounding in the last bit; a tree whose random
number lands within that of its density can come out differently, about one
cell in ten million.

### What it says

Forest grows where three things agree, each a number from 0 to 1, multiplied:

- **Altitude.** Above the beach, the band just above the sea, fading in from
  4 m to 20 m, and below the tree line, fading out from 600 m to 760 m.
- **Slope.** The rise per metre across, from the texels 16 m either side, is
  gentle up to 0.45, and none grows above 0.8: cliffs and steep gullies stay
  rock.
- **Woods and clearings.** Noise a few hundred metres across, cut by a
  `smoothstep` so most places are clearly wood or clearly open.

The noise is **value noise**. It is Chapter 36 section 3's lattice with a value
at each whole point in place of a slope: a random number at every whole point
of the lattice, and between two of them a blend along `smoothstep`'s curve, of
the fraction *f* of the way from one to the next:

$$
n(x) = (1 - u)\, v_i + u\, v_{i+1}, \qquad i = \lfloor x \rfloor, \quad f = x - i, \quad u = f^2 (3 - 2f)
$$

A quarter of the way from a point whose value is 0.2 to one whose value is
0.8, *u* = 0.0625 × 2.5 = 0.156 and *n* = 0.2 + 0.156 × 0.6 = 0.29: the curve
leaves each point flat, so the blend has no corners. In two dimensions the
same blend runs along x on the square's two rows, then along z between them,
which is `valueNoise`'s two `mix`es. Two octaves, as Chapter 36 section 3
stacked them, 500 m and 190 m, weighted 0.6 and 0.4, add up to blobs of every
size; the second is turned 37 degrees, because two lattices that line up show
as a grid. Value noise is simpler than gradient noise and enough for a map of
woods, whose edges `smoothstep` sharpens anyway. The villages stand where the
density is low round them (section 3).

The cell's tree, if any, follows from a hash of the cell's two coordinates:
where it stands inside its 16 m cell, never at the rim, so neighbours never
touch; its turn; its size, from 0.8 to 1.2; whether it is a broadleaf or a
pine, pines more likely higher up; and whether it grows at all, a random number
below the density. `TREE_CELL` goes in `HorizonTypes.h`, after the `FLAT_SKY` line and
before Chapter 36's terrain flags, for both languages:

```c
/* Chapter 37 section 6: metres. One tree at most in each square of this size. */
#define TREE_CELL 16.0f
```

`ForestDensity.glsl` takes the heightmap as an argument instead of declaring
it, so any shader can include it whatever its own bindings are, and the
heightmap's three numbers as `TerrainDraw::heightmap` holds them, in its x, y
and z: the map's side in metres, the height stored as 0, and the range from
there to the height stored as 65,535 (Chapter 36 section 9):

```glsl
// Shaders/Horizon/ForestDensity.glsl - Chapter 37 section 6: where the forest grows, and the one tree each
// 16 m cell of it may hold. An include with no bindings of its own: the caller passes the heightmap, and
// `map`, TerrainDraw::heightmap's three numbers. Terrain.cpp keeps a copy on the CPU (Terrain::ForestDensity
// and Terrain::TreeInCell), from which the mesh trees are planted; Chapter 40 plants billboards from this
// one. Change one and you must change the other.
#ifndef PF_HORIZON_FOREST_DENSITY_GLSL
#define PF_HORIZON_FOREST_DENSITY_GLSL

#include "HorizonTypes.h"   // TREE_CELL
#include "Random.glsl"      // pcgHash, randomFloat (Chapter 21)

// A value in [0, 1) at a whole point: a hash of it, as Random.glsl's randomFloat turns a state into a number.
float latticeValue(ivec2 point)
{
    uint state = uint(point.x) * 7919u ^ pcgHash(uint(point.y));
    return randomFloat(state);
}

// Smooth noise from 0 to 1: Chapter 36 section 3's lattice with a value at each whole point in place of a
// slope, the values blended along smoothstep's curve (Chapter 16 section 5).
float valueNoise(vec2 p)
{
    ivec2 cell = ivec2(floor(p));
    vec2  f    = p - floor(p);
    vec2  u    = f * f * (3.0 - 2.0 * f);
    float a    = latticeValue(cell + ivec2(0, 0));
    float b    = latticeValue(cell + ivec2(1, 0));
    float c    = latticeValue(cell + ivec2(0, 1));
    float d    = latticeValue(cell + ivec2(1, 1));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// The texel of mip level 0 that xz lies in, with the map laid as mapHeight lays it: xz is at xz + MAP_ORIGIN
// on the map (Chapter 36 section 9).
ivec2 texelOf(vec2 xz, float mapSize, int texels)
{
    return ivec2(floor(((xz + MAP_ORIGIN) / mapSize + 0.5) * float(texels)));
}

// One texel of mip level 0, in metres. texelFetch reads the stored value with no filtering, so the CPU's
// copy finds exactly the same number; past the edge, the edge texel, as the sampler clamps.
float texelHeight(sampler2D heights, vec4 map, ivec2 texel)
{
    int last = textureSize(heights, 0).x - 1;
    return map.y + texelFetch(heights, clamp(texel, ivec2(0), ivec2(last)), 0).r * map.z;
}

// How much of the ground at xz is forest, from 0 to 1: none on the beach or above the tree line, none on
// the steep, and in woods a few hundred metres across with clearings between them.
float forestDensity(sampler2D heights, vec4 map, vec2 xz)
{
    float texelSize = map.x / float(textureSize(heights, 0).x);
    ivec2 texel     = texelOf(xz, map.x, textureSize(heights, 0).x);
    float height    = texelHeight(heights, map, texel);
    float dx = (texelHeight(heights, map, texel + ivec2(2, 0)) - texelHeight(heights, map, texel - ivec2(2, 0))) / (4.0 * texelSize);
    float dz = (texelHeight(heights, map, texel + ivec2(0, 2)) - texelHeight(heights, map, texel - ivec2(0, 2))) / (4.0 * texelSize);
    float slope     = sqrt(dx * dx + dz * dz);   // metres up for every metre across

    float altitude = smoothstep(4.0, 20.0, height) * (1.0 - smoothstep(600.0, 760.0, height));
    float gentle   = 1.0 - smoothstep(0.45, 0.8, slope);

    // Woods and clearings: two octaves of noise, the second turned 37 degrees so that the two lattices do
    // not line up, which would show as a grid.
    vec2  turned  = vec2(0.8 * xz.x - 0.6 * xz.y, 0.6 * xz.x + 0.8 * xz.y);
    float noise   = 0.6 * valueNoise(xz / 500.0) + 0.4 * valueNoise(turned / 190.0);
    float patches = smoothstep(0.38, 0.62, noise);
    return altitude * gentle * patches;
}

// The tree in a TREE_CELL cell, counted from the origin, if the forest has one there: where it stands, its
// turn about +Y (radians), its size (a scale around 1), and its kind (0 broadleaf, 1 pine).
bool treeInCell(sampler2D heights, vec4 map, ivec2 cell, out vec2 position, out float turn, out float scale,
                out uint kind)
{
    uint  state = uint(cell.x) * 2654435761u ^ pcgHash(uint(cell.y) + 40503u);   // the cell's own sequence
    float x     = randomFloat(state);
    float z     = randomFloat(state);
    position = (vec2(cell) + 0.1 + 0.8 * vec2(x, z)) * TREE_CELL;   // anywhere but the cell's rim
    turn     = 6.2831853 * randomFloat(state);
    scale    = 0.8 + 0.4 * randomFloat(state);
    float pines = smoothstep(150.0, 450.0, texelHeight(heights, map, texelOf(position, map.x, textureSize(heights, 0).x)));
    kind = randomFloat(state) < pines ? 1u : 0u;   // more pines higher up
    return randomFloat(state) < forestDensity(heights, map, position);
}

#endif
```

### The copy

In `Terrain.cpp`, the helpers go at file scope, after `noiseOctaves`, with
Chapter 21's `randomFloat` copied beside them. `pcgHash` is there already:
Chapter 36 section 6 copied it for the terrain's noise.

```cpp
// File scope, above the namespace block. Chapter 37 section 6: ForestDensity.glsl's helpers on the CPU, line
// for line, and Random.glsl's randomFloat (Chapter 21). Change one and you must change the other.
static float randomFloat(uint32_t& state)
{
    state = pcgHash(state);
    return static_cast<float>(state >> 8u) * (1.0f / 16777216.0f);
}

static float latticeValue(glm::ivec2 point)
{
    uint32_t state = static_cast<uint32_t>(point.x) * 7919u ^ pcgHash(static_cast<uint32_t>(point.y));
    return randomFloat(state);
}

static float valueNoise(glm::vec2 p)
{
    const glm::ivec2 cell = glm::ivec2(glm::floor(p));
    const glm::vec2  f    = p - glm::floor(p);
    const glm::vec2  u    = f * f * (3.0f - 2.0f * f);
    const float      a    = latticeValue(cell + glm::ivec2(0, 0));
    const float      b    = latticeValue(cell + glm::ivec2(1, 0));
    const float      c    = latticeValue(cell + glm::ivec2(0, 1));
    const float      d    = latticeValue(cell + glm::ivec2(1, 1));
    return glm::mix(glm::mix(a, b, u.x), glm::mix(c, d, u.x), u.y);
}
```

`texelOf` goes inside the namespace instead, after `HEIGHT_MAX`.
`HorizonTypes.h` gives C++ `using shared::vec2` inside `pf::demos::horizon`,
so `MAP_ORIGIN`'s `vec2` exists only there; `MAP_ORIGIN` is
`vec2(7300, 400)` (Chapter 36 section 9). It is Chapter 36's rule from a point
to the map, the one `mapHeight` uses, without the half-texel shift a filtered
sample needs:

```cpp
// Chapter 37 section 6: ForestDensity.glsl's texelOf, inside the namespace because MAP_ORIGIN's vec2 is this
// namespace's (HorizonTypes.h). The texel of mip level 0 under xz, with the map laid as mapHeight lays it
// (Chapter 36 section 9's rule, without the half-texel shift a filtered sample needs).
static glm::ivec2 texelOf(glm::vec2 xz, float mapSize, uint32_t texels)
{
    return glm::ivec2(glm::floor(((xz + MAP_ORIGIN) / mapSize + 0.5f) * static_cast<float>(texels)));
}
```

and the three member functions at the end of the namespace. `TexelHeight` reads
`m_heights`, and the map's size is the file's; with no heightmap, the
one-texel stand-in is the sea floor, and nothing grows:

```cpp
// Chapter 37 section 6: the shader's texelHeight. One texel of mip level 0, in metres, as it is stored: no
// filter, so the GPU's texelFetch finds the same number.
float Terrain::TexelHeight(glm::ivec2 texel) const
{
    const int last = static_cast<int>(m_heightmapSize) - 1;
    texel = glm::clamp(texel, glm::ivec2(0), glm::ivec2(last));
    const float value = static_cast<float>(m_heights[static_cast<size_t>(texel.y) * m_heightmapSize + static_cast<size_t>(texel.x)]) / 65535.0f;
    return HEIGHT_MIN + value * (HEIGHT_MAX - HEIGHT_MIN);
}

// Chapter 37 section 6: the shader's forestDensity, line for line.
float Terrain::ForestDensity(glm::vec2 xz) const
{
    const float      texelSize = MAP_SIZE / static_cast<float>(m_heightmapSize);
    const glm::ivec2 texel     = texelOf(xz, MAP_SIZE, m_heightmapSize);
    const float      height    = TexelHeight(texel);
    const float      dx = (TexelHeight(texel + glm::ivec2(2, 0)) - TexelHeight(texel - glm::ivec2(2, 0))) / (4.0f * texelSize);
    const float      dz = (TexelHeight(texel + glm::ivec2(0, 2)) - TexelHeight(texel - glm::ivec2(0, 2))) / (4.0f * texelSize);
    const float      slope     = std::sqrt(dx * dx + dz * dz);

    const float altitude = glm::smoothstep(4.0f, 20.0f, height) * (1.0f - glm::smoothstep(600.0f, 760.0f, height));
    const float gentle   = 1.0f - glm::smoothstep(0.45f, 0.8f, slope);

    const glm::vec2 turned  = glm::vec2(0.8f * xz.x - 0.6f * xz.y, 0.6f * xz.x + 0.8f * xz.y);
    const float     noise   = 0.6f * valueNoise(xz / 500.0f) + 0.4f * valueNoise(turned / 190.0f);
    const float     patches = glm::smoothstep(0.38f, 0.62f, noise);
    return altitude * gentle * patches;
}

// Chapter 37 section 6: the shader's treeInCell, line for line.
bool Terrain::TreeInCell(glm::ivec2 cell, glm::vec2& position, float& turn, float& scale, uint32_t& kind) const
{
    uint32_t    state = static_cast<uint32_t>(cell.x) * 2654435761u ^ pcgHash(static_cast<uint32_t>(cell.y) + 40503u);
    const float x     = randomFloat(state);
    const float z     = randomFloat(state);
    position = (glm::vec2(cell) + 0.1f + 0.8f * glm::vec2(x, z)) * TREE_CELL;   // anywhere but the cell's rim
    turn     = 6.2831853f * randomFloat(state);
    scale    = 0.8f + 0.4f * randomFloat(state);
    const float pines = glm::smoothstep(150.0f, 450.0f, TexelHeight(texelOf(position, MAP_SIZE, m_heightmapSize)));
    kind = randomFloat(state) < pines ? 1u : 0u;   // more pines higher up
    return randomFloat(state) < ForestDensity(position);
}
```

`Terrain.h` declares them, public, after `HeightmapSize`, and `TexelHeight`,
private, after `MapHeight`:

```cpp
    // Chapter 37 section 6: ForestDensity.glsl on the CPU. How much of the ground at xz is forest, and the
    // tree a 16 m cell holds, if it holds one. Chapter 37's mesh trees and Chapter 40's billboards are planted
    // from the same two functions.
    float ForestDensity(glm::vec2 xz) const;
    bool  TreeInCell(glm::ivec2 cell, glm::vec2& position, float& turn, float& scale, uint32_t& kind) const;

    float                TexelHeight(glm::ivec2 texel) const;                    // Chapter 37 section 6
```

### Seeing it

The GLSL copy has a use now: the terrain can show the density, which lets you
check, before a tree is planted, that the rule puts woods where you expect.
The vertex shader has the heightmap bound, so it works out the density at each
vertex, only while the view is on, and passes it on. A flag joins
`TERRAIN_SKY` in `HorizonTypes.h`:

```c
#define TERRAIN_SHOW_FOREST 16u  /* Chapter 37 section 6: the forest's density, as a tint */
```

`TerrainSettings` gains its switch, after `hazeDistance`, and `Record` sets the
flag after the rings' one:

```cpp
    bool     showForest   = false;      // Chapter 37 section 6: the forest's density, as a tint
```

```cpp
    if (settings.showForest) { flags |= TERRAIN_SHOW_FOREST; }  // Chapter 37 section 6
```

`Terrain.vert.glsl` includes the file after `TerrainHeight.glsl`, which declares
the `heightmap` it is given; declares an output with the others, after `ring`,
at the next location; and fills it in `main` after `drawn`, before the skirt
moves `xz`:

```glsl
#include "ForestDensity.glsl"   // Chapter 37 section 6: forestDensity

layout(location = 5) out float forest;          // Chapter 37 section 6: the forest's density, for its tint

    // Chapter 37 section 6: how much forest grows here, only while the panel shows it.
    forest = (terrain.flags & TERRAIN_SHOW_FOREST) != 0u ? forestDensity(heightmap, terrain.heightmap, xz) : 0.0;
```

`Terrain.frag.glsl` takes it in, after `ring` with the other inputs, and tints
in `main` right after the haze line and before the ring view, so that, like the
other debug views, it shows to the horizon unhazed:

```glsl
layout(location = 5) in float forest;   // Chapter 37 section 6

    // Chapter 37 section 6: the forest's density, as dark green.
    if ((terrain.flags & TERRAIN_SHOW_FOREST) != 0u)
    {
        color = mix(color, vec3(0.0, 0.3, 0.0), 0.8 * forest);
    }
```

and the panel gets **Show forest**, at the end of the **Objects** group (section
7 replaces this line with one that also shows a count, so keep one checkbox):

```cpp
    // Section 6: the forest.
    ImGui::Checkbox("Show forest", &m_terrainSettings.showForest);
```

From the viewpoint, **Show forest** paints the woods green: patches across the
low hills ahead with clearings between them, the nearest village's houses in
one of them, and none on the beach at the right. Turned left toward the
summit, the steep sides and the high ridges stay bare. Over **Wood** the green
lies exactly where the trees will stand.

## 7. A pool of near trees

**This is the pool's numbers in `Props.h`, its slots in `Place`, `PlantTrees`,
the trees in `Update`, and the move worth making.**

### How many, and how far

Mesh trees reach 600 m from the camera; Chapter 40 draws the forest beyond.
With one tree at most in each 16 m cell, the circle holds π × 600² / 16² =
4,418 cells, and with woods over part of the land, about one to two thousand
trees stand in it at a time. As the camera flies, cells leave the circle behind
it and others come into it ahead, and the trees must follow.

### Why a pool

The scene graph has `AddNode` and no way to remove one: nodes are indices into
an array (Chapter 12 section 2), and removing one would change every index
after it. A tree made for every cell the camera passes would make the scene
grow without end. So the trees are a fixed set of objects, made once, and each
is given a new cell when its old one leaves: a **pool**. Its cost never
changes, nothing is allocated as the camera moves, and a slot that has no tree
in its cell, a clearing, is simply hidden.

> **Jump:** a slot is not a place. Slot (*x*, *z*) holds whichever cell of the
> square round the camera has x and z equal to *x* and *z* modulo the pool's
> side, and that cell changes as the camera moves. Keep two coordinates apart
> from here on: the cell, which is where a tree stands in the world, and the
> slot, which is only where the pool keeps it.

### A pool that wraps round

The pool's numbers go in `Props.h`, after `LOD_HIDDEN`:

```cpp
// Section 7: the mesh trees reach TREE_REACH metres from the camera, and shrink to nothing over the last
// TREE_FADE of it. Chapter 40's billboards take over there. The pool is a square of TREE_SLOTS cells on a
// side, TREE_CELL metres each (HorizonTypes.h): 1,216 m, from 38 cells behind the camera's cell to 37 ahead
// of it, so at least 592 m reaches out from the camera every way.
inline constexpr float    TREE_REACH = 600.0f;   // metres
inline constexpr float    TREE_FADE  = 100.0f;   // metres
inline constexpr int32_t  TREE_SLOTS = 76;
```

The pool is a square of cells round the camera's cell, 76 on a side, 1,216 m.
Cell (*x*, *z*) can only ever be in slot (*x* mod 76, *z* mod 76). When the
camera crosses into the next cell, the column of cells it leaves behind is
exactly the column whose slots the cells ahead need: 76 slots are planted
again, and the other 5,700 keep their trees. With six slots in place of 76:

```text
 the camera in cell 3: the square is cells 0 to 5
     cell    0  1  2  3  4  5
     slot    0  1  2  3  4  5
 the camera crosses into cell 4: the square is cells 1 to 6
     cell       1  2  3  4  5  6
     slot       1  2  3  4  5  0      cell 6 takes slot 0, which cell 0 has left
```

Chapter 36's rings snapped to their cells for the same reason, so that nothing
moves until a whole cell has been crossed. With an even side the camera's cell
cannot be the middle one: the square runs from 38 cells before it to 37 after
it, so it reaches at least 592 m from the camera every way, and on the near
sides falls up to 8 m short of 600. Those last metres are deep in the shrink
band below, where a tree is a third of a pixel.

C++'s `%` keeps the sign of the number divided, so −3 % 76 is −3, not a slot.
The remainder that is never negative adds the divisor once more:

$$
\operatorname{wrap}(v) = ((v \bmod 76) + 76) \bmod 76, \qquad \operatorname{wrap}(-3) = (-3 + 76) \bmod 76 = 73
$$

Every slot holds one cell of the square. For slot *x*, the square runs from
`first.x` to `first.x + 75`, and the one cell in it that wraps to *x* is
`first.x + wrap(x − first.x)`. Where that is not the cell the slot holds, the
slot is planted: `TreeInCell` says whether a tree grows there, which kind, how
big, turned how far; the slot takes that kind's asset, from `m_treeAssets`,
and stands there. A new tree starts with no level, so section 5 gives it the
one its size calls for. An `Object` gains two fields, whether it is a slot of
the pool and the cell it holds, after `level`; and the class two members, at
its end:

```cpp
        bool                            tree  = false;      // section 7: a slot of the pool
        glm::ivec2                      cell{ INT32_MIN };  // section 7: the cell it holds; none at first

// At the end of the class, after m_counts:
    size_t                  m_firstSlot = 0;                         // section 7: where the slots begin
    std::array<uint32_t, 2> m_treeAssets{ { NO_ASSET, NO_ASSET } };  // section 7: by TreeInCell's kind
```

`PlantTrees` goes after `Place`:

```cpp
// Section 7: the pool follows the camera. It is a square of TREE_SLOTS x TREE_SLOTS cells round the camera's
// cell, and cell (x, z) can only ever be in slot (x mod TREE_SLOTS, z mod TREE_SLOTS). When the camera
// crosses into the next cell, the row or column of cells it leaves behind is exactly the one whose slots the
// row or column ahead needs: only those slots are planted again.
void Props::PlantTrees(const Terrain& terrain, glm::vec3 camera)
{
    const glm::ivec2 first = glm::ivec2(glm::floor(glm::vec2(camera.x, camera.z) / TREE_CELL)) - TREE_SLOTS / 2;
    auto wrap = [](int32_t value) { return ((value % TREE_SLOTS) + TREE_SLOTS) % TREE_SLOTS; };   // never negative
    for (int32_t z = 0; z < TREE_SLOTS; ++z)
    {
        for (int32_t x = 0; x < TREE_SLOTS; ++x)
        {
            // The one cell of the square that falls in slot (x, z).
            const glm::ivec2 cell = first + glm::ivec2(wrap(x - first.x), wrap(z - first.y));
            Object&          slot = m_objects[m_firstSlot + static_cast<size_t>(z * TREE_SLOTS + x)];
            if (slot.cell == cell)
            {
                continue;   // still the cell it holds
            }
            slot.cell = cell;
            glm::vec2 position;
            float     turn  = 0.0f;
            float     scale = 1.0f;
            uint32_t  kind  = 0;
            const bool grows = terrain.TreeInCell(cell, position, turn, scale, kind);
            SetAsset(slot, grows ? m_treeAssets[kind] : NO_ASSET);
            m_scene.SetVisible(slot.node, grows);
            if (grows)
            {
                slot.xz    = position;
                slot.scale = scale;
                slot.level = LOD_HIDDEN;   // a new tree: no level to keep yet
                scene::Transform& local = m_scene.EditLocal(slot.node);
                local.translation = { position.x, local.translation.y, position.y };
                local.rotation    = glm::angleAxis(turn, glm::vec3(0.0f, 1.0f, 0.0f));
            }
        }
    }
}
```

`PlantTrees` sets where the tree stands and which way it faces, and not the
node's size or height: `Update` does that in the same frame, by the test in
"Moving only what shows" below. That test leaves a new tree with the last one's
size or height only when they differ by less than a quarter of a pixel on
screen, and then no one can tell.

It needs `Horizon/HorizonTypes.h`, for `TREE_CELL`, at the top of `Props.cpp`,
after a blank line below the engine's includes. `Load` fills `m_treeAssets` at
its end, after the loop over the seven files and before the `return`, by name,
the broadleaf and the pine by `TreeInCell`'s kind:

```cpp
    m_treeAssets = { FindAsset("Broadleaf"), FindAsset("Pine") };   // section 7: by TreeInCell's kind
```

and `Place` makes the slots at its end, after the rocks round the keep: 5,776
objects, each a node and three levels, made once and hidden until planted:

```cpp
    // Section 7: the pool's slots, every one empty until Update plants it.
    m_firstSlot = m_objects.size();
    for (int32_t slot = 0; slot < TREE_SLOTS * TREE_SLOTS; ++slot)
    {
        Object& object = AddObject(NO_ASSET, glm::vec2(0.0f), 0.0f, 1.0f);
        object.tree    = true;
        m_scene.SetVisible(object.node, false);
    }
```

### No pop at the edge

A tree that appears at full size when its cell comes within reach is a pop:
13 pixels tall at 600 m in this window. Instead a tree shrinks, from its full
size at 500 m to nothing at 600 m, along `smoothstep`, so it comes in as a
speck that grows; below 1 % of its size it is hidden. Section 5's last line
would cut that short: a shrinking tree would vanish at 4 pixels, and appear
there, a smaller pop but a pop. So in the band a tree keeps its coarsest level,
as a landmark does, and the shrink alone takes it out. The distance is the
camera's to the tree's middle, in three dimensions, so from 600 m above the
ground no tree is within reach at all, and the island is bare until Chapter 40.
That last 100 m is where Chapter 40's billboards will fade in over the same
band, so the forest hands over without a seam.

### Moving only what shows

The shrunk size must reach the node, so the node's scale changes in the band as
well as its height. Until now `Update` marked every object every frame (section
3), and with 5,776 slots that is a cost: every node marked is a world matrix
recomputed, its three levels' with it, and flying, the ground under every far
tree shifts as the rings follow the camera (section 4) and every tree in the
band changes size.

A move nobody can see is not worth a matrix. Section 5's measure says how tall
something is on screen; a length *L* at distance *d* is

$$
\frac{L \cdot \text{screenScale}}{2d} \text{ pixels}
$$

the measure with *L* as the sphere's diameter. A height change moves the
object by its own length: a tree 400 m away whose ground moves 5 cm moves
0.05 × 1247 / 800 = 0.08 pixels on screen in this window. A scale change of Δ
moves the sphere's diameter, 2*r*, by 2*r*Δ: a pine, 7.9 m in radius, whose
scale shrinks by 1 % at 550 m moves its outline by 2 × 7.9 × 0.01 = 0.158 m,
0.158 × 1247 / 1100 = 0.18 pixels. So an object is moved only when one of the
two reaches
`MOVE_PIXELS`, a quarter of a pixel; less is left for later, and the error it
leaves on screen is never more than a quarter of a pixel. The number goes in
`Props.h`, after the pool's:

```cpp
// Section 7: an object is moved, and its node recomputed, only when its height or its size changes by this
// much on screen: less does not show.
inline constexpr float MOVE_PIXELS = 0.25f;   // pixels
```

### `Update`, finished

The pool is planted first, before the loop; the loop skips an empty slot,
shrinks a tree near the edge, moves an object only when the move shows, and
chooses the level from the shrunk size. The landmark's `if` keeps a shrinking
tree at `LOD2` as well, a tree shrunk below 1 % is hidden after it, and the
trees are counted. In full, `Update` now reads, in place of the version you have
from section 3 on, and with every parameter named:

```cpp
void Props::Update(const Terrain& terrain, const TerrainSettings& terrainSettings, glm::vec2 ringCenter,
                   glm::vec3 camera, float screenScale, const PropSettings& settings)
{
    if (!Loaded())
    {
        return;
    }
    PlantTrees(terrain, camera);   // section 7

    m_counts = {};
    for (Object& object : m_objects)
    {
        if (object.asset == NO_ASSET)
        {
            continue;   // an empty slot of the pool
        }
        const Asset& asset = m_assets[object.asset];

        // Section 4: on the ground as the rings draw it now, from where they are centred. Section 7: a tree
        // in the last TREE_FADE metres of the pool's reach shrinks toward nothing.
        const glm::vec3 base(object.xz.x, terrain.HeightAt(object.xz, ringCenter, terrainSettings), object.xz.y);
        const float     distance = glm::distance(base + asset.centre * object.scale, camera);
        const float     shrink   = object.tree ? 1.0f - glm::smoothstep(TREE_REACH - TREE_FADE, TREE_REACH, distance) : 1.0f;
        const float     scale    = object.scale * shrink;

        // Section 7: moved only when the move would show, MOVE_PIXELS or more on screen: EditLocal marks the
        // node, and every node marked is recomputed. A length L at distance d is L * screenScale / (2 d) pixels
        // tall, section 5's measure with L as the sphere's diameter: a height change moves the object by its
        // own length, a scale change moves the diameter by 2 r times as much.
        const scene::Transform& now    = m_scene.GetNode(object.node).local;
        const float             change = std::max(std::abs(now.translation.y - base.y),
                                                  2.0f * asset.radius * std::abs(now.scale.x - scale));
        if (change * screenScale / (2.0f * std::max(distance, 0.001f)) > MOVE_PIXELS)
        {
            scene::Transform& local = m_scene.EditLocal(object.node);
            local.translation.y = base.y;
            local.scale         = glm::vec3(scale);
        }

        // Section 5: the level for its height on screen, unless the panel froze them; a landmark past the last
        // line keeps its coarsest level. Section 7: so does a shrinking tree, which the shrink takes out instead
        // of the line, hidden only when it is almost nothing.
        if (!settings.freezeLod)
        {
            const float pixels = settings.lodBias * asset.radius * scale * screenScale / std::max(distance, 0.001f);
            object.level = chooseLevel(pixels, object.level);
            if (object.level == LOD_HIDDEN && (asset.landmark || shrink < 1.0f))
            {
                object.level = 2;
            }
            if (shrink < 0.01f)
            {
                object.level = LOD_HIDDEN;
            }
        }
        for (uint32_t level = 0; level < 3; ++level)
        {
            m_scene.SetVisible(object.levels[level], level == object.level);
        }
        ++m_counts.levels[object.level];
        m_counts.trees += object.tree ? 1u : 0u;
    }
    m_scene.UpdateWorldTransforms();
}
```

The panel shows the count beside **Show forest**. This block replaces section
6's comment and its `Checkbox` line, so that there is one checkbox, not two:

```cpp
    // Section 6: the forest. Section 7: beside it, the slots of the pool that hold a tree.
    ImGui::Checkbox("Show forest", &m_terrainSettings.showForest);
    ImGui::SameLine();
    ImGui::Text("  trees %u of %d", counts.trees, TREE_SLOTS * TREE_SLOTS);
```

Every frame `Update` looks at 5,776 slots and works out a `HeightAt` and a
level for each tree, and `UpdateWorldTransforms` walks some 23,000 nodes, the
slots and their levels' nodes, recomputing those marked. Standing still, nothing
is marked; flying low over a wood, only the objects whose move would show are,
more of them the faster you fly. Section 9's panel shows what it costs on your
machine. The demo draws no scene hierarchy or inspector (Chapter 12 section 8):
a hierarchy of 23,000 nodes, redrawn every frame, would cost more than the
props themselves.

*Horizon Zero Dawn* places its vegetation on the GPU from rules evaluated over
the world's maps, deterministic, so the same place always grows the same
plants; this pool is that idea at its smallest, a hash and one density, on the
CPU.

## Checkpoint

Run, and click **Wood**: broadleaf trees in front of you, a wood stretching
away, the nearest in full detail with a trunk and a lumpy crown, the far ones
two cones. **Show levels**: red near you, then yellow, then blue, in bands by
distance. **Show forest** paints the ground green under the trees. Click
**Edge**, then click on the scene so that the keys reach the demo (Chapter 10
section 10), and hold W: the wood ahead is at the pool's edge, and its trees
come in as specks and grow as you close. Climb with E: past about 600 m above
the ground, every tree is gone. The panel's count beside **Show forest** still
shows the slots planted, about 1,300 to 3,000 across these views and the
flights between them; they are hidden, not gone.

---

# Part 4 — Shadows, timers, and a real model (sections 8-10)

Part 4 gives the objects shadows near the camera, measures what everything
costs, and tries a model that was not made for this demo.

## 8. Shadows near the camera

**This is the shadows' own lens and settings, the casters in `CollectDraws`,
`RecordShadows` in `Record`, and `sunShadow` in `lightAt`.**

### A lens of their own

Chapter 17's cascades are fitted to the view, from the camera's near plane out
to `maxDistance` (Chapter 17 sections 2 and 11). What `ShadowMaps` reads of the
camera is its lens, the field of view, the near plane and the far plane as an
upper limit, and the view matrix. It never sees the projection the demo builds,
and Chapter 35 section 8 showed why the reversal cannot reach it.

> **Jump:** from here two depth conventions run in the same frame: the scene
> pass reversed, far at 0 and `GREATER`, and the shadow pass ordinary, far at 1
> and `LESS`, into images of its own, which `sunShadow` compares against.
> Nothing in the shadow path is reversed, and nothing in it needs to be.

So the main camera could be passed as it is: the cascades are fitted to
`min(maxDistance, farPlane)`, which is `maxDistance` either way. The demo
passes a lens of its own instead, an ordinary `scene::Camera` with the same
field of view, from 0.1 to 500 m. It is a choice, not a fix: it keeps
everything the shadow pass is given ordinary, and says where the shadows are
set up how far they reach, rather than leaving it to a lens that sees 200 km.

`maxDistance` defaults to 120 m, which covers a room or a garden. Here the
objects are trees and houses seen from tens of metres up, and 120 m ends the
shadows in the middle of the nearest wood; the demo takes 250 m. Chapter 17
section 11's split at λ = 0.8 cuts that into cascades ending at 13, 29, 66 and
250 m, the first sharp enough for a trunk's shadow. The constant goes after
`LEVEL_COLORS`:

```cpp
// Chapter 37 section 8: how far the shadows reach. Chapter 17's 120 m covers a room or a garden; here the
// objects are trees and houses, seen from tens of metres up.
constexpr float SHADOW_DISTANCE = 250.0f;   // metres
```

and the constructor sets both, at its end:

```cpp
    // Chapter 37 section 8: the same field of view, Chapter 10's standard depth from 0.1 to 500 m.
    m_shadowCamera                = scene::Camera{ .verticalFov = m_camera.verticalFov, .nearPlane = 0.1f, .farPlane = 500.0f };
    m_shadowSettings.maxDistance  = SHADOW_DISTANCE;
```

`HorizonDemo::Update` shows Chapter 17's **Shadows** window, after
`DrawPanel`, so its settings can be changed while the demo runs:

```cpp
    vulkan_graphics::drawShadowPanel(m_shadowSettings);   // Chapter 37 section 8: Chapter 17's window
```

### Who casts

A caster outside the view can still throw a shadow into it, so Chapter 17's
casters are not culled against the camera (Chapter 19 section 8 batches them
as a second list). Drawing every object shown into four cascades would be most
of the island's trees four times over. What can shade anything the cascades
cover is within roughly `maxDistance + casterReach` of the camera, 450 m with
`casterReach` at Chapter 17 section 2's 200 m. Roughly, because `maxDistance`
is a view depth (Chapter 10 section 4), measured along the view, while the
list is cut by distance from the camera: at the corners of the window the last
cascade's far edge is about 1.5 times as far as straight ahead, and a tall
tree just past 450 m there can lose its shadow.

So `CollectDraws` makes a second list, every shown object unculled, then drops
what is further than that. Its declaration in `Props.h` becomes:

```cpp
    // Section 2: what the camera sees, culled (Chapter 12 section 9). Section 8: what casts shadows, every
    // object shown within `casterReach` metres of the camera, unculled.
    void CollectDraws(const scene::Frustum& frustum, glm::vec3 camera, float casterReach,
                      std::vector<scene::DrawItem>& draws, std::vector<scene::DrawItem>& casters) const;
```

```cpp
void Props::CollectDraws(const scene::Frustum& frustum, glm::vec3 camera, float casterReach,
                         std::vector<scene::DrawItem>& draws, std::vector<scene::DrawItem>& casters) const
{
    m_scene.CollectDraws(draws, &frustum);   // Chapter 12: each shown level's mesh, culled by its box
    m_scene.CollectDraws(casters, nullptr);  // section 8: unculled, as Chapter 17's casters are
    std::erase_if(casters, [&](const scene::DrawItem& item) {
        return glm::distance(glm::vec3(item.world[3]), camera) > casterReach;
    });
}
```

`Record` passes the reach and the casters' list. This call replaces section 2's
`CollectDraws` call, which passed the frustum and `m_draws` alone. And
`PrepareDraws` takes the casters as its second list, in place of the call and
comment section 2 wrote:

```cpp
    m_props.CollectDraws(scene::frustumFromViewProjection(frameData.viewProjection), m_cameraTransform.translation,
                         m_shadowSettings.maxDistance + m_shadowSettings.casterReach, m_draws, m_casters);
```

```cpp
    // Chapter 35 section 3: the plates, sorted and batched into this slot's instance buffer, before anything
    // binds set 0. Chapter 37: the props with them, and the shadow casters.
    m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws, m_casters);
```

The levels the camera chose are the levels that cast, so a far tree's shadow
is its proxy's.

### The pass

`RecordShadows` fits the cascades, draws the casters into them, and leaves the
maps for the fragment shaders, all before the scene pass. It goes after
`PrepareDraws`, which wrote the casters' instances, and before the sky's bake.
The sun is `SUN_TRAVEL`, the same the sky and `FrameData` use:

```cpp
    // Chapter 37 section 8: the props' shadows, fitted to the shadow camera's ordinary depth, not to the
    // reversed 200 km lens, outside the scene pass.
    m_sceneRenderer.RecordShadows(commandBuffer, frame.frameIndex, m_shadowCamera, frameData.view, aspect,
                                  SUN_TRAVEL, m_shadowSettings);
```

The terrain is not a caster: its rings are drawn by its own pipeline, and
nothing puts them in the casters' list. It receives, which is what matters
here.

Two limits follow, and they show. **Shadows stop 250 m from the camera**: past
the last cascade a house stands in full sun with no shadow beside it, and a
tree's shadow fades out as the band ends. And **the land throws none at all**:
with the sun 35 degrees up, a ridge 500 m above its valley should throw a
shadow 700 m long across it, and here the valley is lit to the bottom; from
the viewpoint the far ranges are shaded by their slope alone. Both are work of
another kind, named in "Where to go from here".

### Receiving them

`lightAt` gains `sunLit`, how much of the sun reaches the surface: Chapter 17
section 9's `sunShadow` gives 1 in the light and 0 in shadow.
`HorizonShading.glsl` includes `Shadows.glsl` after its guard, which declares
set 0's bindings 3 and 4 and `sunShadow`; both pipelines' layouts are set 0's,
so the bindings are there. In `HorizonShading.glsl`, the file's top, with its
comment brought up to date and the include added, replaces section 2's top, and
`lightAt` replaces section 2's, which took the normal alone:

```glsl
// Shaders/Horizon/HorizonShading.glsl - Chapter 37 section 2: the light and the haze every surface of the
// Horizon demo shares: Chapter 36's ground and sea, and the objects that stand on them. An include: the
// including shader has included FrameBlock.glsl first. Declares set 0 bindings 3, 4 (through Shadows.glsl),
// 10 and 11.
#ifndef PF_HORIZON_SHADING_GLSL
#define PF_HORIZON_SHADING_GLSL

#include "Shadows.glsl"   // Chapter 17: sunShadow, from set 0 bindings 3 and 4
```

```glsl
// Chapter 36 section 4: Chapter 11's light, for a matte surface facing N: the sun, whose sunColor is already
// E / pi, and the light from everywhere else, which is Chapter 24's sky when it lights the scene. Chapter 37
// section 8: `sunLit` is how much of the sun reaches the surface, sunShadow's 1 lit to 0 in shadow.
vec3 lightAt(vec3 N, float sunLit)
{
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? texture(skyDiffuse, N).rgb : frame.ambientColor.rgb;
    return frame.sunColor.rgb * max(dot(N, -frame.sunDirection.xyz), 0.0) * sunLit + ambient;
}
```

In `Flat.frag.glsl`, the line `color *= lightAt(N);` becomes the two below: the
light takes the shadow, from the view depth `sunShadow` needs to pick a cascade
(Chapter 10 section 4's view space, its distance along the view):

```glsl
        float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;
        color *= lightAt(N, sunShadow(worldPosition, N, viewDepth));   // section 8: sunShadow
```

In `Terrain.frag.glsl` the water takes the shadow for its body's light and the
sun's glint, so `waterColor` gains a parameter, and its signature, with the
comment above it brought up to date, is replaced:

```glsl
// Chapter 36 section 10: water `depth` metres deep, seen along V (unit, toward the eye): the sky mirrored
// with Schlick's Fresnel, and the sun's glint (Chapter 30 section 10's lobe), over the water's body, which
// shows the sand below where it is shallow. Chapter 37 section 8: `sunLit`, the shadows on the water.
vec3 waterColor(float depth, vec3 V, float sunLit)
```

```glsl
    vec3  mirror    = skyColor(R, skyOn, terrain.sky.rgb) + PI * frame.sunColor.rgb * lobe * sunLit;   // E

    vec3 light = lightAt(N, sunLit);
```

Inside it, the glint's `lobe` is scaled by the shadow in the `mirror` line, and
the body's light takes it; the rest of the function is as it was. In `main`,
both the water and the ground pass the shadow, the water with a normal straight
up, the ground with its own. This block replaces the one that chose between
them, from its comment through the closing brace of the `else`; the `toEye`,
`range` and `V` lines above it and the haze below it stay:

```glsl
    // Chapter 36 section 4: the ground, lit; its section 10: or water, where the ground is below sea level.
    // Chapter 37 section 8: the sun's light in the objects' shadows (Chapter 17), out to the shadows' distance.
    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;
    vec3  color;
    if (groundHeight < 0.0)
    {
        color = waterColor(-groundHeight, V, sunShadow(worldPosition, vec3(0.0, 1.0, 0.0), viewDepth));
    }
    else
    {
        vec3 N = normalize(vertexNormal);
        color  = groundAlbedo(groundHeight, N.y) * lightAt(N, sunShadow(worldPosition, N, viewDepth));
    }
```

### No new barrier

The shadow maps are written by the shadow pass and read in the scene pass, and
Chapter 17 section 5's second barrier already makes them ready for every
fragment shader that samples them, with `COMPUTE_SHADER` beside
`FRAGMENT_SHADER` for Chapter 22's lighting pass; the terrain's and the flat
pipeline's fragment shaders are such readers, so nothing in this chapter adds
a barrier. The exit check proves the readers are seen, by taking
`FRAGMENT_SHADER` out of that barrier.

Run, and click **Wood**: each tree throws a shadow across the grass, away from
the sun behind you on your left, and the trunks are dark under their crowns.
The shadows end, fading, 250 m out.

## 9. What each pass costs

**This is `GpuTimestamps` in `Setup`, `Teardown` and `Record`, the props' time
on the CPU, and the times in the panel.**

The demo now draws a sky, a terrain, thousands of objects and their shadows, on
GPUs from lavapipe to an RTX. Which costs what is a measurement, not a guess:
Chapter 24 section 9's `GpuTimestamps`, five timestamps a frame, one at each
boundary, and the time between two neighbours is a pass's. `Setup` ends by
making them, and `Teardown` begins by destroying them:

```cpp
    // Chapter 37 section 9: five timestamps a frame (Chapter 24's class).
    return m_timestamps.Initialize(m_context.vulkan, 5);
```

```cpp
    m_timestamps.Shutdown();                                                     // Chapter 37 section 9
```

A single frame's time jumps about from frame to frame, too fast to read. Each
time on the panel is a running average instead: every new reading moves it a
tenth of the way there, so it follows the last ten frames or so and holds
still long enough to read. The first reading is taken as it is. `smoothed`
goes at file scope, after `stepsApart` (Chapter 35 section 6), and `<chrono>`
joins the standard headers for the CPU's clock:

```cpp
// File scope, above the namespace block. Chapter 37 section 9: a running average that follows a reading over
// about the last ten frames, so a time on the panel holds still long enough to read. The first reading is
// taken as it is.
static double smoothed(double average, double reading)
{
    return average == 0.0 ? reading : average + 0.1 * (reading - average);
}
```

`Record` has grown in four sections, so its changes are easier to place in a
listing than in fragments. Here it is in two stretches, each replacing what
sections 2, 3, 5 and 8 wrote for the same lines; only the `m_timestamps` lines,
the `std::chrono` lines and the `drawObjects` test are new.

The first stretch runs from the props to `PrepareDraws`. The CPU's share is
section 7's: `Props::Update` and `CollectDraws`, timed with
`std::chrono::steady_clock`, so both calls now sit between the two clock
readings. To see what a pass costs, compare it with the same frame without it.
The panel gets one switch for that, **Draw objects**,
`PropSettings::drawObjects`. Off, both lists are emptied after the timing, so
the shadow pass and the objects' draw have nothing to draw, and the frame is
Chapter 36's again, the sky and the terrain alone. The switch comes before the
level colours and the plates join `m_draws`, so with the objects off the plates
still show:

```cpp
    // Chapter 37: the props. The pool follows the camera, each takes its level and stands on the ground as it
    // is drawn now (sections 3, 4, 5, 7); then what the camera sees, and what casts shadows (sections 2, 8).
    const float screenScale = static_cast<float>(extent.height) / std::tan(0.5f * m_camera.verticalFov);
    const auto  propsStart  = std::chrono::steady_clock::now();   // Chapter 37 section 9: the props' CPU time
    m_props.Update(m_terrain, m_terrainSettings, m_ringCenter, m_cameraTransform.translation, screenScale,
                   m_propSettings);
    m_props.CollectDraws(scene::frustumFromViewProjection(frameData.viewProjection), m_cameraTransform.translation,
                         m_shadowSettings.maxDistance + m_shadowSettings.casterReach, m_draws, m_casters);
    const std::chrono::duration<double, std::milli> propsTime = std::chrono::steady_clock::now() - propsStart;
    m_propsMilliseconds = smoothed(m_propsMilliseconds, propsTime.count());
    if (!m_propSettings.drawObjects)   // Chapter 37 section 9: the frame as Chapter 36 left it, for the timers
    {
        m_draws.clear();
        m_casters.clear();
    }
    if (m_propSettings.showLevels)   // Chapter 37 section 5: each draw in its level's color
    {
        for (scene::DrawItem& draw : m_draws)
        {
            draw.material = m_levelMaterials[m_props.MeshLevel(draw.mesh)];
        }
    }
    if (m_showPlates)                // Chapter 36 section 1: the plates, while the panel shows them
    {
        m_draws.insert(m_draws.end(), m_plates.begin(), m_plates.end());
    }

    // Chapter 35 section 3: the plates, sorted and batched into this slot's instance buffer, before anything
    // binds set 0. Chapter 37: the props with them, and the shadow casters.
    m_sceneRenderer.PrepareDraws(frame.frameIndex, m_draws, m_casters);
```

The second stretch runs from the first timestamp to the end of the scene pass.
It first reads what this frame slot measured last time, whose fence has been
waited, so reading it never stalls; then the slot's pool is reset, and the
first timestamp written. Then come four more, one after each pass, each a line
after the call that ends it: the shadows, the sky with the clear to 0, the
terrain, and the objects, the last before `endScenePass`. Three are inside the
scene pass, which the grass's are too (Chapter 26 section 8): a timestamp may
be written inside a rendering scope. The stretch ends with the calls that end
the pass: from the `RecordShadows` call on, it replaces what you have, and the
lines that read and write the first timestamp go in above it:

```cpp
    // Chapter 37 section 9: what this slot measured last time, then this frame's first timestamp.
    if (m_timestamps.Read(frame.frameIndex))
    {
        for (uint32_t pass = 0; pass < m_timings.size(); ++pass)
        {
            m_timings[pass] = smoothed(m_timings[pass], m_timestamps.Milliseconds(pass, pass + 1));
        }
    }
    m_timestamps.Reset(commandBuffer, frame.frameIndex);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 0);

    // Chapter 37 section 8: the props' shadows, fitted to the shadow camera's ordinary depth, not to the
    // reversed 200 km lens, outside the scene pass.
    m_sceneRenderer.RecordShadows(commandBuffer, frame.frameIndex, m_shadowCamera, frameData.view, aspect,
                                  SUN_TRAVEL, m_shadowSettings);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 1);

    // Chapter 35 section 7: Chapter 23's sky, baked again only if it changed, before the scene pass. Chapter
    // 28's clouds in it need the camera and the time.
    m_sky.Update(commandBuffer, frame.frameIndex, frame.sky,
                 { .sunDirection   = SUN_TRAVEL,
                   .sunIrradiance  = glm::pi<float>() * glm::vec3(0.90f, 0.85f, 0.80f),
                   .cameraPosition = m_cameraTransform.translation,
                   .time           = m_time });

    // Chapter 35 section 1: a pale horizon blue where nothing is drawn.
    const VkClearColorValue clearColor{ { 0.45f, 0.60f, 0.80f, 1.0f } };
    beginScenePass(commandBuffer, frame.targets, &clearColor);

    // Chapter 35 section 7: the sky first, while the depth is still the 1.0 the pass cleared it to. Its vertex
    // shader puts it at depth 1.0 and it tests LESS_OR_EQUAL, so it passes at every pixel; it writes no depth.
    m_sky.Draw(commandBuffer, frameData.view, frameData.projection);

    // Chapter 35 section 6: the far plane is depth 0. One clear inside the scope, and everything drawn after it
    // is tested against 0.
    clearDepth(commandBuffer, extent, 0.0f);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 2);   // Chapter 37 section 9

    // Chapter 36 section 1: the ground, after the clear to 0, and before the plates.
    const bool skyOn = frame.sky.mode != SkyMode::Off;
    m_terrain.Record(commandBuffer, m_sceneRenderer, frame.frameIndex, m_terrainSettings, m_ringCenter, skyOn);
    m_timestamps.Write(commandBuffer, frame.frameIndex, 3);   // Chapter 37 section 9

    // Chapter 35 section 3: the plates, through Chapter 19's batches, with this demo's pipeline. Chapter 36
    // section 1: only while the panel shows them, since they would stand in the ground. Chapter 37: and the
    // props, lit, in the same batches.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_flatPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_flatLayout, frame.frameIndex);
    m_sceneRenderer.RecordBatches(commandBuffer, frame.frameIndex, DrawList::Scene,
                                  [&](VkCommandBuffer cb, const DrawRun& run) {
        vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
        const FlatDraw draw{
            .baseColor = m_materialColors[run.material],
            .sky       = glm::vec4(FALLBACK_SKY, m_terrainSettings.hazeDistance),   // Chapter 37: the terrain's
            .flags     = m_materialFlags[run.material] | (skyOn ? FLAT_SKY : 0u),
        };
        vkCmdPushConstants(cb, m_flatLayout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(draw), &draw);
    });
    m_timestamps.Write(commandBuffer, frame.frameIndex, 4);   // Chapter 37 section 9

    endScenePass(commandBuffer);
    handBackSceneTarget(commandBuffer, frame.targets);
```

The switch and the times go under a header of their own, **Times**, at the end
of the **Objects** group, closed at first; with it open, the panel is taller
than a 720-pixel window and scrolls, the **Camera** group under the scroll bar.
The four passes' sum is the demo's own work: the composite pass and ImGui after
it are the engine's, and not counted:

```cpp
    // Section 9, under a header of its own, closed at first: the frame without the objects, to compare with;
    // what the GPU spent on each pass, their sum, and what the props cost the CPU, each averaged.
    if (ImGui::CollapsingHeader("Times"))
    {
        ImGui::Checkbox("Draw objects", &m_propSettings.drawObjects);
        ImGui::Text("GPU ms  shadows %.2f  sky %.2f", m_timings[0], m_timings[1]);
        ImGui::Text("        terrain %.2f  objects %.2f", m_timings[2], m_timings[3]);
        ImGui::Text("        the four %.2f", m_timings[0] + m_timings[1] + m_timings[2] + m_timings[3]);
        ImGui::Text("CPU ms  props %.2f", m_propsMilliseconds);
    }
```

### Reading them

What they are for is the presets and the settings. On a GPU, switch **Preset**
from Full to Low and the terrain's time falls with its vertices, a quarter as
many; drag **LOD bias** up and the objects' and the shadows' times grow with
the levels the objects show; in Chapter 17's **Shadows** window, fewer cascades
shrink the shadows'. To compare one machine with another, keep everything else
the same: a Release build; `--msaa 4` or the **MSAA** window; the window at a
known size, which the **Frame** window shows as its swapchain's (1920 x 1080 is
a common mark); **Preset** at Full, where a GPU starts; the sky as every run
here has it, **Sun sky**; and the same view, from the buttons, so the same
objects stand in it. Wait a second for the averages to settle, then read the
four times, their sum, and the props' CPU time; then untick **Draw objects**
and read them again, for the same frame without this chapter's work.

The props' CPU time is the last line. In a Debug build `Props::Update` and
`CollectDraws` cost several times what they cost in Release, standing at the
viewpoint or in the wood and flying low over it with W and with Shift and W; in
Release, flying hardly moves it, because only the objects whose move would show
are recomputed (section 7). What Debug adds is unoptimized arithmetic,
`HeightAt` and glm's matrices, and two walks of the 23,000 nodes in
`CollectDraws`, one for the view and one for the shadow casters: the price of a
Debug build, not of the design, so judge frame rates in Release.
`REFERENCE.md` has what the reference build measured, in a table.

On lavapipe the times are not milliseconds to compare. It is a CPU, and it does
a rendering scope's work in batches of its own choosing, mostly as the scope
ends, so the stamps inside the scene pass do not fall between the passes they
name: unticking **Draw objects** in the wood takes most of the objects' draws
out of the terrain's time, because they were counted there. Read only the
shadows' time, a scope of its own: it grows with **LOD bias**, and falls with
**Draw objects** off to what four empty cascades cost (the Exit check gives
its sizes). Even that one moves with the terrain's preset, for a reason the
timers do not show. The sky's time holds Chapter 28's clouds, which lavapipe
marches on its CPU threads, and the sky's light whenever Chapter 24's bake runs
again.

**The target.** This demo is held to the RTX 4060 Laptop at 1920 x 1080, 4x
MSAA and 60 frames a second, 16.7 ms a frame, with the setup above. An
integrated GPU, such as a Radeon 890M, is measured and reported but not held to
it: a game would give it lower settings, and **Preset**, **LOD bias** and
Chapter 17's cascades are where those would come from. Chapters 38 and 39 each
check what they add against this budget.

## 10. A real model

**This is `ThirdPartyScenes/convert_glb.py`, and a downloaded tree in place of
the procedural broadleaf.**

### What a downloaded tree brings

The procedural trees were made for this demo: closed shapes, a few materials,
three levels. A model from a library was made for something else, and it is
worth knowing what one costs before a forest is planted from it. Kenney's free
(CC0) asset kits are a common first source. This one is the "Mini Arena" set in
his Godot starter kit for a basic scene,
<https://github.com/KenneyNL/Starter-Kit-Basic-Scene> (revision `a6927e6`),
which has a stylized tree. Three files from `sample/Mini Arena/` in that
repository are on `start`, in `ThirdPartyScenes/Kenney/source/` (these are their
paths, to fetch them again):

```text
Models/GLB format/tree.glb                 ->  ThirdPartyScenes/Kenney/source/tree.glb
Models/GLB format/Textures/colormap.png    ->  ThirdPartyScenes/Kenney/source/Textures/colormap.png
License.txt                                ->  ThirdPartyScenes/Kenney/source/License.txt
```

The `.glb` names its palette as `Textures/colormap.png`, a path relative to
itself, so the `Textures/` folder stays beside it, where the converter looks for
it. The licence is CC0, which lets the files be copied and altered; it stays
beside them anyway, and `THIRD_PARTY_NOTICES.md` has a row for the model with its
source, its licence and what was changed (Chapter 38 section 5 does the same for
the ground's photographs).

A `.glb` is glTF in one file: a JSON description and a binary buffer of
vertices and indices, with the palette texture beside it. Its tree is one mesh
of 330 triangles, coloured by that palette, `colormap.png`, from which every
triangle takes a shade,
and its material names no `alphaMode`, so it is OPAQUE, glTF's default (no
transparency, no cut-out leaves), and it says `doubleSided` true.

That last is the one that costs. A double-sided mesh is drawn with no culling
(Chapter 11 section 7), so every triangle facing away from the camera is drawn
as well, behind the one in front. The tree needs it: it has 68 **open edges**,
edges that belong to one triangle only, where its parts meet without closing,
and with back faces culled you would see through those gaps.

### Converting it

`convert_glb.py` is on `start` in `ThirdPartyScenes/` (some 320 lines; appendix B
says what is in it), and so is the tree it wrote, so running it is optional. It
is plain Python like the props script, with the standard library alone, and
needs no Blender. To write the tree again, from `ThirdPartyScenes/`, with the
tree's height in metres last:

```text
python convert_glb.py Kenney/source/tree.glb Kenney/MiniArenaTree.usda 10
```

It prints what it found, which is a check that the right file went in:

```text
material colormap: alphaMode OPAQUE, doubleSided True
35 palette colours, reduced to 4; 68 edges not shared by two triangles
```

and, last, one line saying what it wrote, with the triangles per level, 330, 106 and 8.

It reads the file's one mesh, gives each triangle the palette's colour under
the middle of its texture coordinates, and reduces the palette's 35 shades to 4
colours, because each colour is a material, and each material a run of its own
in Chapter 19's batches. It scales the tree to stand 10 m tall with half a
metre below the ground, and keeps `doubleSided`. Then the levels, the same
three a props asset has.

`LOD1` is the model simplified by **vertex clustering**, the crudest
simplifier there is. A grid of cells an eighth of the tree's height is laid
over it, every vertex moves to the average of the vertices in its cell, and a
triangle with two corners in the same cell has no area left and goes. The
grid's lines lie at whole multiples of the cell from the asset's own origin, `y`
= 0, which is half a metre above the tree's lowest point, and likewise in x and
z. For the 10 m tree the cells are 1.25 m: 0 to 1.25 m in height, 1.25 to 2.5,
and so on up to 7.5 to 8.75. If that one holds three vertices of a branch's tip,
at 7.6, 7.9 and 8.5 m, it leaves one vertex at their average, 8.0 m (x and z are
averaged the same way), and every triangle that had two of the three as corners
is gone. It keeps 106 of the 330
triangles with the silhouette mostly whole. `LOD2` is two four-sided cones
round the tree's bounds, in its average colour. The result is
`ThirdPartyScenes/Kenney/MiniArenaTree.usda`, beside the download it came from
in `Kenney/source/`.

### Planting it

The names are the whole convention (section 1): an asset is found by its
file's name, and it must have `LOD0` to `LOD2`. So planting the model needs no
code. Copy `ThirdPartyScenes/Kenney/MiniArenaTree.usda` to
`Assets/Scenes/Horizon/Broadleaf.usda`, over the procedural one (running the
props script writes that one back, and so does `git restore`), build so the
post-build step copies `Assets/` beside the executable again, and run. Every
broadleaf the forest plants is Kenney's tree now; the pines are still the script's.

### What it shows

Click **Wood**: the same wood, the same cells, Kenney's bright stylized trees,
turned and scaled as the procedural trees were. **Show levels** shows the same
bands, a little nearer, because the model's sphere is smaller than the
broadleaf's; the clustered `LOD1` holds the silhouette well enough at the
distances it is used. Its 330 triangles at `LOD0` are about
twice the broadleaf's 160, its 106 at `LOD1` 2.4 times the broadleaf's 44, and
its `LOD2` has the same 8.

What the model does not bring is just as telling. It is solid: its material is
OPAQUE, its palette opaque everywhere, and so are the procedural trees. A real
forest's trees are not: their leaves are cards with a cut-out picture of leaves
on them, where most of each card is transparent, and that is where foliage
costs, in the pixels every hidden layer of leaves is shaded again for. Chapter
39 builds such plants, and measures that cost. When you have looked, run
`make_horizon_props.py` again from `Assets/Scenes/`, or `git restore` the file,
and build, to put the procedural broadleaf back; the chapters after this one
plant it.

## Checkpoint

The finished chapter; the Exit check below walks through it. The frame, as this
chapter leaves it:

```text
 FrameData: the camera, the sun, the ambient light                    WriteFrameData
 the props: the pool, the levels, the ground under each; timed       Props::Update
 the draws and the casters; level colours if shown; the plates       CollectDraws
 sorted and batched, both lists                                       PrepareDraws
 timestamp 0; the cascades (Chapter 17); timestamp 1                  RecordShadows
 the sky's bake, if anything changed (Chapter 35 section 7)           Sky::Update
 beginScenePass: color cleared, depth cleared to 1.0                  (Chapters 10, 18)
     the sky, at depth 1.0, LESS_OR_EQUAL, writing none               Sky::Draw
     depth to 0 (Chapter 35 section 6); timestamp 2                   vkCmdClearAttachments
     the terrain (Chapter 36); timestamp 3                            Terrain::Record
     the props and the plates: flat, lit, GREATER; timestamp 4        RecordBatches
 endScenePass; the scene target to the composite (Chapter 08)         handBackSceneTarget
```

and `Props::Update`'s loop is the outline the chapter began with, every part
written.

---

## If something goes wrong

| Symptom | Cause |
| --- | --- |
| "No props" in the log, and no objects | `Assets/Scenes/Horizon/` is missing beside the executable: build from the command line, touch a source file, or Rebuild, so the post-build step copies `Assets/` again (Chapter 13 section 6) |
| Objects with the wrong shapes or colours, plates in odd places | The props' meshes and materials were registered after something else: `RegisterProps` must run first in `Setup`, before `CreatePlates`, so their indices are the scene renderer's (section 2) |
| Every object drawn three times over, flickering | Two or three levels are shown at once: `AddObject` must hide `LOD1` and `LOD2` until section 5, and from then `Update` shows exactly one (sections 2 and 5) |
| The watchtower floats over its hill from the viewpoint and settles as you come, or houses are buried a few kilometres off | `Update` asks `HeightAt` with the object's own position as the ring centre, or `HeightAt` reads mip level 0 only: the ground must be the mip level the rings read there (section 4) |
| Objects pop between levels as you hover near them | `chooseLevel`'s margin is missing or the wrong way round: going coarser must need less than the line, coming back more (section 5) |
| Objects black, or one flat colour, or brighter than the ground | The material's `FLAT_LIT` flag is missing (`RegisterProps` passes `true`), or `Flat.frag` lost its light; or the normal attribute is not described in `CreateFlatPipeline` (section 2) |
| No trees anywhere | No heightmap: the forest grows on its texels (section 6); or the camera is more than 600 m above the ground (section 7) |
| No new trees appear as you fly | **Freeze levels** is on: a tree planted while it is on starts hidden and stays so (section 5) |
| Trees standing in a clearing that **Show forest** shows bare, or the reverse | `ForestDensity.glsl` and `Terrain::ForestDensity` differ: they must match line for line (section 6) |
| Woods in the sea and on the bare summits, and none where the land is green | `texelOf` leaves out `MAP_ORIGIN`, so the forest is read from the map as if it were centred on the origin, 7.3 km from where it is drawn (section 6) |
| Trees appear at full size at the edge | The shrink in `Update` is missing (section 7) |
| Trees pop in as small cones a little inside the edge | The landmark's `if` does not keep a shrinking tree (`shrink < 1.0f`), so the 4-pixel line hides it before the shrink has taken it out (section 7) |
| Trees missing on the camera's east or south side, and none at all further east or south | `PlantTrees` uses C++'s `%` directly: east or south of the origin `x - first.x` goes negative, and those slots plant cells outside the square, too far to show (section 7) |
| No shadows | `RecordShadows` is not called, or `Shadows.glsl` is not included and `lightAt` is not given `sunShadow`; check the **Shadows** window's **Enabled** (section 8) |
| Trees cast shadows, but the grass under them has none | The ground's `lightAt` in `Terrain.frag` is not given `sunShadow`, only the water's (section 8) |
| Shadows end close to the camera | `maxDistance` is still Chapter 17's 120 m (section 8) |
| Kenney's tree does not appear | The file must be named `Broadleaf.usda` in `Assets/Scenes/Horizon/`, and copied beside the executable by a build; the log names a file without `LOD0` to `LOD2` (section 10) |
| Flying is smooth in Release and stutters in Debug | The props' CPU time in Debug (section 9); the **Times** header's **CPU ms** line says how much |

## Exit check

Run the finished demo, with the sky on unless a line says otherwise. The
tower on its hill, the levels in bands, the wood and the shadows were checked
where they were built, and the hygiene every exit check assumes is [the index's
conventions](../VulkanTutorial.md#conventions-every-chapter-uses). This list is
what those runs did not check.

- [ ] **Assets.** If you ran `make_horizon_props.py`, it printed the seven
      assets' triangles per level, as the table in section 1.
- [ ] **A landmark at 7.5 km.** **Far side**: the keep on the island's skyline,
      in the middle of the view, a grey mark about two pixels wide and eight
      tall on the ridge. Set **LOD bias** to 0.25: the keep stays, the same at
      the same pixel, and with **Show levels** on it is blue, `LOD2`.
- [ ] **No pop at the pool's edge.** **Edge**, click on the scene, and hold
      W: the wood ahead grows in from specks; no tree appears
      whole.
- [ ] **The timers.** With **Times** open, on lavapipe read only the shadows'
      time (section 9): about 12 to 15 ms in the wood at Low, 33 to 37 at **LOD
      bias** 4, 7 to 8 with **Draw objects** off. On a GPU the directions are
      section 9's. In Release the props' CPU time stays near its standing value
      while you fly with Shift and W.
- [ ] **The converter** (optional). From `ThirdPartyScenes/`, section 10's
      command prints its two lines and a last one with the triangles per level,
      330, 106 and 8.
- [ ] **A real model.** Copy `ThirdPartyScenes/Kenney/MiniArenaTree.usda` over
      `Assets/Scenes/Horizon/Broadleaf.usda`, build and run: the log says
      `Broadleaf.usda: imported 6 nodes, 3 meshes (444 triangles)`, and
      **Wood** shows Kenney's trees in the same cells. Run
      `make_horizon_props.py` (or `git restore` the file) to put the procedural
      one back.
- [ ] **No props.** Rename `Assets/Scenes/Horizon/Pine.usda` beside the
      executable and run: the log has two warnings, the importer's reason,
      "Props: Could not load" and the file's path, and then one beginning "No
      props", and the demo runs with the terrain alone. Name it back.
- [ ] **The shrink's positive control.** In `Props.h`, set `TREE_FADE` to 1,
      build, and do the **Edge** flight again: now the wood ahead pops in,
      each tree appearing whole at the pool's edge, about 17 pixels tall by
      section 5's measure. Put it back.
- [ ] **The barrier's positive control.** In `ShadowMaps::Record`
      (`Source/PillowFort/VulkanGraphics/ShadowMaps.cpp`), in the second
      `vkCmdPipelineBarrier2`, change `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT |
      VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT` to
      `VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT`, build, and run a few frames:
      synchronization validation reports `SYNC-HAZARD-READ-AFTER-WRITE` at
      `vkCmdDraw` (the terrain) and at `vkCmdDrawIndexedIndirect` (the objects),
      on binding 4 of set 0: the fragment shader reads the shadow maps, and the
      new readers, the terrain's and the objects' fragment shaders, are seen.
      Put it back.

---

## Where to go from here

Chapter 38 gives the ground its materials, and the chapters after it fill the
island in the same demo; the index lists them.

What this chapter did not build, and when it becomes worth building:

- **Shadows past 250 m, and shadows from the land.** The cascades end at
  250 m, and the terrain casts nothing, so at a low sun the far ranges look
  flat and the valleys stay lit. Two usual cures: march from each pixel of
  ground toward the sun through the heightmap, a few dozen steps, and stop at
  the first texel above the ray; or, since this sun never moves, bake that same
  march into a shadow mask beside the heightmap, in `make_island.py`, and
  sample it like the height. Either shades the far land; neither shades the
  objects, which the cascades still do near the camera.
- **A dithered cross-fade**, when a level's switch shows as a pop on a real
  display. For a few frames both levels are drawn, each discarding a pattern of
  pixels that grows as the other's shrinks. It needs a fade value per
  instance, which `InstanceData` has no room for (Chapter 19 section 3): an
  engine edit. (The grass's geomorph, Chapter 26 section 6, needs levels whose
  vertices nest, which authored levels do not.) Chapter 39's leaf cards, which
  pop harder than solid shapes, are where it starts to matter.
- **Merged far proxies (HLOD)**, when `PrepareDraws` shows up in the frame's
  time: a village's houses, far away, as one mesh, built at load time.
- **Culling on the GPU, and occlusion culling** (Chapter 26 section 9), past
  about 100,000 objects: the instances in a buffer the GPU reads, culled by a
  compute pass against the frustum and a depth pyramid, drawn with
  `drawIndirectCount`.
- **Levels made automatically**, when making `LOD1` and `LOD2` by hand for more
  than a few assets gets tedious: meshoptimizer's `meshopt_simplify` does far
  better than section 10's clustering. A new dependency, and a decision.
- **The props in a hierarchy you can edit**, when the world becomes a scene
  graph to inspect. Two things to settle first: the pool's 23,000 nodes must
  stay out of a hierarchy drawn every frame (under one closed node, or with
  ImGui's list clipper drawing only the rows in view); and a node dragged in
  the inspector must land on the ground, which it will not today, because
  `Props` keeps each object's `xz` and stands it there every frame: it would
  have to read the node's translation back instead.
- **Shadows from a coarser level than the one shown**, if the shadow pass
  grows long with many casters: `CollectDraws` would take the casters' meshes
  one level coarser.
- **Distant lights**, for night: each village's windows a small sprite, all in
  one buffer.

Next: [38 — Ground Materials](38-Ground-Materials.md)

---

## Sources

- The Khronos Group, *glTF 2.0 Specification*: the `.glb` container, accessors,
  `alphaMode` and `doubleSided`.
- Kenney, *Mini Arena* (CC0), in `sample/Mini Arena/` of
  <https://github.com/KenneyNL/Starter-Kit-Basic-Scene>: `tree.glb`,
  `Textures/colormap.png` and `License.txt`.
- Unity Technologies, *Unity Manual*, "LOD Group": levels switched by an
  object's height relative to the screen.
- The Souls modding community's Paramdex (`soulsmods/Paramdex`),
  `ER/Defs/PartsDrawParam.xml`: *Elden Ring*'s switch distances with a play
  band, `lv01_BorderDist` and `lv01_PlayDist`.
- Emil Persson, *Creating Vast Game Worlds: Experiences from Avalanche
  Studios*, SIGGRAPH 2012 (Chapter 35's source): *Just Cause 2*'s resident
  landmark models.
- Guerrilla Games, *GPU-Based Run-Time Procedural Placement in Horizon: Zero
  Dawn*,
  https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn:
  placement evaluated on the GPU from rules over the world's maps,
  deterministic.

---

## Appendix A — `make_horizon_props.py`

Reference for section 1: the script that writes the seven assets. It is on the
`start` branch at `Assets/Scenes/make_horizon_props.py` (345 lines, plain Python
3 with `math` and `os` only), beside the files it writes in
`Assets/Scenes/Horizon/`. To write them again, run `python make_horizon_props.py`
from `Assets/Scenes/`; it makes the `Horizon/` folder if it is missing and prints
the triangles per level. It is not part of the build and draws no random
numbers, so every run writes the same files. What it makes, and what each asset
tests (section 1's table has the triangles per level):

| File | What it is | What it tests |
| --- | --- | --- |
| `Pine.usda` | a pine 12 m tall: a trunk and three stacked cones; then two; then one four-sided pyramid | the pattern every asset follows (section 1); the forest's second kind, more of them higher up (section 6) |
| `Broadleaf.usda` | a tree 10 m tall: a trunk and a lumpy crown; then a coarser crown; then an octahedron | the forest's first kind (section 6); the file Kenney's tree replaces (section 10) |
| `Rock.usda` | a rock 1 m in radius, flattened, a third of it below the ground; then coarser; then an octahedron | a small asset with one material, scattered round the villages and the keep (section 3) |
| `House.usda` | 8 m by 6 m, its ridge 7 m up: a stone plinth 2 m deep, walls, a roof with eaves, a chimney, a door and windows; then walls and a plain roof; then one box | four materials in one mesh; small parts that `LOD1` drops; a plinth that covers a slope (sections 1 and 3) |
| `Landmark_Lighthouse.usda` | 52 m tall: a tapering tower in red and white bands on a stone base, a gallery, a lamp room and a roof; then fewer sides and bands; then one tapering four-sided prism | a landmark by its name (section 5), on the shore |
| `Landmark_Tower.usda` | 62 m to the tip of its roof: a round stone shaft on a foundation 8 m deep, a ring of corbels, a wooden lookout and a pointed roof; then fewer sides and no corbels; then one tapering prism | a landmark on a hilltop, which floats until section 4 |
| `Landmark_Keep.usda` | 86 m to the tip of its roof and 24 m square: a foundation 12 m deep, battlements, slit windows and a pointed roof; then the keep and its roof; then one tapering box | a landmark with size enough to cover pixels from 7.5 km (section 5) |

The file holds, in its order: `Shape` and the builders that add parts to one
(`frustum`, `diamond`, `box`, `gable`, `lumpy` and `moved`, which section 1
describes); the writers, `materialText`, `meshText` and `write`; and the seven
assets, each a few lines that build three shapes and call `write`. Section 1
prints `Shape`, `write` and the pine.

---

## Appendix B — `convert_glb.py`

Reference for section 10: the converter. It is on the `start` branch at
`ThirdPartyScenes/convert_glb.py` (325 lines, plain Python 3 with the standard
library only), beside `Kenney/MiniArenaTree.usda`, which it wrote from the three
downloaded files in `Kenney/source/`. To write the tree again, from
`ThirdPartyScenes/`:

```text
python convert_glb.py Kenney/source/tree.glb Kenney/MiniArenaTree.usda 10
```

It prints what section 10 lists and writes the same file, byte for byte. It
reads the first mesh of the first scene of a glTF binary that has one mesh on one
node with no transform, which is what Kenney's kits export; anything else stops
with a message. What it holds, in its order:

| Function | What it does |
| --- | --- |
| `fail` | stops with a message |
| `readGlb`, `accessor` | take the container apart, a chunk of JSON and a chunk of bytes, and read typed values out of the second |
| `readPng`, `toLinear` | read the palette, only the kind of PNG this one is (8 bits a channel, RGB or RGBA, not interlaced), and turn a texel from sRGB to linear |
| `area` | a triangle's area |
| `cluster` | `LOD1` by vertex clustering (section 10) |
| `reduce` | the palette's shades reduced to four colours by k-means weighted by area, started from the colour with the most area and then each time the one furthest from those chosen |
| `edges` | counts the edges not shared by exactly two triangles, after joining corners at the same place: 0 for a closed surface |
| `main` | strings them together: scales the tree to the height given with its lowest point half a metre below y = 0, makes `LOD2` from two cones round its bounds, and writes the USD text, in the shape of file the props script writes |
