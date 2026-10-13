# 39 — Plants

**Goal:** trees made of leaves. One Python script grows five plants after
EZ-Tree, branch on branch from a seed: an oak, a pine, a bush, a fern and a
flower, each in three levels of detail, and writes them as USD files beside
Chapter 37's props. Their leaves are cards cut out of a picture's alpha, sharp
at one sample and soft-edged under MSAA; a scale per mip level keeps distant
leaves from thinning away, measured first on walls of leaves; their shadows
have holes in them near the camera, and far trees cast their solid stand-ins
instead. An overdraw view counts what all those layers cost. Then the ground
grows an understory: ferns, flowers and bushes, planted from nothing every
frame by a compute pass that reads Chapter 38's material map, and drawn with
instance-rate vertex attributes and indirect draws.

**ROADMAP:** step 21+ — the `Horizon` demo grows. The script is
`Assets/Scenes/make_horizon_plants.py` ([the
appendix](#appendix--the-plants-script)), on the `start` branch with what it
writes into `Assets/Scenes/Horizon/Plants/`; a class of its own, `Understory`,
in `Source/PillowFort/Demos/Horizon/`; four shaders in `Shaders/Horizon/`.

**Module:** `pf::demos::horizon` (`Understory`, new; `Props`, `Terrain` and
`HorizonDemo` grow). One change goes outside the demo: two read-only
accessors on `SceneRenderer`, so that the demo's own pipelines can bind the
engine's material sets.

**Math:** taught where it is first used, and listed in the index's [The math,
chapter by chapter](../VulkanTutorial.md#the-math-chapter-by-chapter): a ring of
points round a turning axis and Rodrigues' rotation (section 1); a crown's
normal, and keeping the leaves' area with fewer cards (section 2); a texel's
size against a card's (section 4); a quantile and the scale that restores a
share (section 6); a count read through the sRGB curve (section 7); an edge as
4w(1 − w), a slope from a central difference, and chances from weights (section
8); the cells a circle holds (section 9); a turn about +Y written out (section
10); a budget from measured times (section 11). It reuses Chapter 10's cross
product, Chapter 16 section 5's `smoothstep`, Chapter 18 section 8's coverage,
and Chapter 26's generate and append.

**Prerequisites:**

- Builds on Chapters 37 and 38, built and running. From 37: the props, their
  scene and `RegisterProps`, the flat pipeline, `FlatDraw` and `lightAt` (section
  2); the views and `GoTo` (section 3); levels chosen by size on screen, with
  hysteresis (section 5); `forestDensity` and `treeInCell`, and their kinds
  (section 6); the pool of near trees, its slots, reach and fade (section 7);
  `m_casters`, the shadow camera's standard-depth lens, `sunShadow` (section 8);
  the **Times** header, its timestamps and **Draw objects** (section 9);
  Kenney's tree copied over `Broadleaf.usda` (section 10). From 38, the chapter
  just read: the material map's weights, the island's set plan (set 0 the
  frame, set 1 the island, set 2 a pass's own, with `TerrainDraw` pushed first by
  every pass that reads the island), **Show materials**, and reading textures
  before any branch, each named again where this chapter uses it.
- Chapter 36 sections 2 (`float(1u << level)` and why exactness matters), 8 (an
  image read once at load) and 9 (`MAP_ORIGIN`, `terrainHeight` as the rings
  draw it); Chapter 35 sections 2 (the test plates), 6 (reversed depth: every
  pipeline at GREATER, the sky first) and 7 (the sky).
- Chapter 15 sections 4 (the importer's materials), 5 (mip chains made by
  blits, and how the sampler picks a level), 7 (a set per material, its
  samplers at bindings 1 to 7), 11 (specialization constants) and 13 (the test
  scenes); Chapter 14 section 12 (the importer stores `1 − v`).
- Chapter 17 sections 4 (the cut-out caster, which binds the material's set), 8
  (the shadow filter's nine taps) and 11 (cascades and their splits); Chapter
  18 section 8 (alpha to coverage); Chapter 19 sections 2 (instance-rate
  attributes), 4 (`memoryBarrier`), 5 (batches) and 6 (indirect draws, and the
  `drawIndirectFirstInstance` feature the engine turns on); Chapter 20 sections
  2 (`createComputePipeline`), 3 (`groupCount`), 4 (`createDescriptorSets`), 8
  (atomics) and 9 (reading back without stalling); Chapter 08 section 2
  (`createBuffer`, `uploadToBuffer`); Chapter 21 sections 1 (a set's writes),
  3 (`pcgHash` and `randomFloat` in `Random.glsl`) and 5
  (additive blending); Chapter 24 section 9 (`GpuTimestamps`); Chapter 26
  sections 3 and 4 (a generation pass, culling against six planes, appending).
- Chapter 10 sections 1 (a matrix times a vector), 6 (`rotationFromYawPitch`)
  and 8 (the cross product); Chapter 11 section 7 (which side is the front);
  Chapter 16 section 6 (**Raw**, the tone curve that clamps); Chapter 04
  section 5 (the three questions a barrier answers); Chapter 02 section 2 (the
  shader-access setting of synchronization validation); Chapter 05 section 3
  (`--present` on the command line); Chapter 09 sections 5 (a failed `Setup`
  detaches the demo) and 6 (`beginDemoPanel`).

---

## Where this is going

Chapter 37's trees are cones and balls of solid colour, and from 150 m that is
enough. Walk into the wood and they are what they are: shapes, not trees. This
chapter grows real ones, and the plants under them, in four parts:

- **Part 1, "Trees from a script"** (sections 1-4): a script grows branches on
  branches, and the first new picture is a winter wood, bare oaks and pines
  across the island; leaves go on as cards, square at first; a pipeline of the
  demo's own cuts them out of their picture, with shadows that have holes; and
  far trees cast their solid stand-ins, which the far shadow cascade can hold.
- **Part 2, "Leaves at a distance"** (sections 5-7): the cut edge as coverage
  under MSAA; a scale per mip level that keeps far leaves from thinning,
  measured on walls of leaf cards; and a view that counts the layers each
  pixel draws.
- **Part 3, "The understory"** (sections 8-10): a fern, a flower and a bush,
  and where on the island each may grow, seen first in false colours; a
  compute pass that plants them every frame round the camera and counts them;
  and the draws that read those counts.
- **Part 4, "The bill"** (section 11): what all of it costs, against a budget.

> **Jump:** until now every object in `Horizon` went through one pipeline
> that knows only a colour. Plants bring their own: a vertex shader that
> carries the texture coordinate, a fragment shader that reads the material's
> picture, and a layout that binds the engine's own material set at a number
> of the demo's choosing. Keep in mind which runs go where: Chapter 37's props
> stay on the flat pipeline, byte for byte; everything from a plant file goes
> through the leaf pipelines.

### What you are actually writing

Every frame of `HorizonDemo::Record`, with the section that adds each part:

```text
 the pool's trees: leaf-card trees, or Chapter 37's                       section 1
 the props' levels (Chapter 37), or one level forced for a comparison     section 3
 the casters: far plants as their LOD2 stand-ins                          section 4
 the leaf plates, while they show; triangles counted                      sections 6, 4, 11
 the shadows (Chapter 37)
 the understory's compute: every small plant within reach, planted        section 9
 the sky, the depth clear, the terrain (Chapters 35-38)
 the overdraw view's clear to black                                       section 7
 the objects: Chapter 37's on the flat pipeline, plants on the leaf ones  section 3
 the understory, drawn indirectly                                         section 10
 seven timestamps between them                                            section 11
```

And in the leaf pipelines' fragment shader, `Leaf.frag.glsl`:

```text
 the picture, read first; its mip level beside it                         sections 3, 6
 alpha, scaled for its mip level                                          section 6
 the overdraw view: count, and stop                                       section 7
 the cut: a step at one sample, coverage under MSAA, discard at 0         sections 3, 5
 the colour: picture, tint, the plant's own tint; the crown's normal; lit  section 3
```

### Where everything lands

```text
Assets/Scenes/
  make_horizon_plants.py    the plants script (on start)                sections 1, 2, 8, appendix
  Horizon/Plants/
    OakTree.usda, PineTree.usda                                         sections 1, 2
    Bush.usda, Fern.usda, Flower.usda                                   section 8
    Textures/oak.png, pine.png, ash.png, LICENSE.txt   EZ-Tree's        section 2
    Textures/fern.png, flower.png        drawn by the script            section 8
Source/PillowFort/VulkanGraphics/
  SceneRenderer.h           two accessors, at the end of the public part  section 3
Source/PillowFort/Demos/Horizon/
  Props.h, .cpp             PLANT_FILES, LoadPlants, SetLeafCards       section 1
                            IsPlantMaterial, forceLevel                 section 3
                            PlantShadows, ShapeCasters                  section 4
                            PlantMeshes                                 section 9
  Terrain.h, .cpp           IslandSetLayout                             section 3
                            showUnderstory                              section 8
                            IslandSet, DrawConstants                    section 9
  Understory.h, .cpp        the understory, a class                     sections 9, 10
  HorizonDemo.h, .cpp       PlantSettings; the Plants header; the leaf
                            pipelines and their runs; the plates; the
                            understory's place in the frame             sections 1-11
Shaders/Horizon/
  HorizonTypes.h            FLAT_LEAF, FLAT_PETALS, LeafDraw            section 3
                            FLAT_COVERAGE, FLAT_MIP_FIX                 sections 5, 6
                            TERRAIN_SHOW_UNDERSTORY                     section 8
  Leaf.vert.glsl            Flat.vert.glsl with a uv                    section 3
  Leaf.frag.glsl            every plant's colour                        sections 3, 5, 6, 7
  Understory.glsl           where the small plants grow, an include     section 8
  Terrain.frag.glsl         the Show understory view                    section 8
  UnderstoryTypes.h         the understory's C++/GLSL twins             section 9
  UnderstoryGenerate.comp.glsl                                          section 9
  Understory.vert.glsl                                                  section 10
```

Sections 3, 9 and 10 add shader and source files: regenerate
(`GenerateProjects.bat`), then build. Each section says where its functions go
in `HorizonDemo.cpp`.

---

# Part 1 — Trees from a script (sections 1-4)

Part 1 makes the trees and puts them in Chapter 37's pool, where its cones
stood: branches only at first, then leaves as cards, then cut out of their
pictures, then which level of each tree casts its shadow.

> **Before the first run.** Every run in this chapter is with the engine's sky
> on and the Tone mapping window collapsed, as in Chapters 36 to 38 (Chapter 35
> section 7 says where to set **Sun sky**), except some measurements in
> sections 4, 6 and 7, which say when to turn it off. The panel's new **Plants**
> header is the last one, below **Camera**; at 1280 x 720 it sits at the
> panel's bottom edge, so scroll the panel down to reach it (`beginDemoPanel`
> scrolls by design).

## 1. A tree is branches on branches

**This is `make_horizon_plants.py`, its growth.** A tree is a trunk that
carries branches, which carry smaller branches, down to twigs that carry
leaves. Each branch is a bent, tapering tube, grown a section at a time from
its base. Call how far a branch is from the trunk its **order**: the trunk is
order 0, its limbs order 1, their branches order 2, and so on. Everything that
makes one oak differ from the next is a handful of numbers per order, and a
random seed. The script keeps those numbers in a list it calls `levels`, one
dictionary per order; they are not the levels of detail of section 2.

### The script

The script follows EZ-Tree by Daniel Greenheck (MIT licence,
<https://github.com/dgreenheck/ez-tree>), a tree generator for the web, whose
`src/lib/tree.js` this chapter's growth is written from. It is a separate file
from Chapter 37's props script for three reasons: the licence notice and the
credit sit in the one file that carries EZ-Tree's ideas; Chapter 37's script
and its outputs stay exactly as they were; and 37's `Pine.usda` and
`Broadleaf.usda` stay, as the trees shown when **Leaf-card trees** is off.

It is plain Python with the standard library only, as Chapters 36 and 37's
scripts are, and it is on the `start` branch at
`Assets/Scenes/make_horizon_plants.py` (705 lines), beside the plants it
writes; [the appendix](#appendix--the-plants-script) says what the file holds.
Running it is optional, because what it writes is on `start` too; the excerpts
below are cut from it and explain it a part at a time. The oak's, the pine's
and the bush's numbers are EZ-Tree's presets `oak_medium`, `pine_medium` and
`bush_1`, cut down where noted, so the text says "after EZ-Tree": no plant here
is EZ-Tree's tree seed for seed, because the random numbers are drawn
differently.

### A frame that turns

A branch grows along a direction, and has to know which ways are across it:
the ring of a tube is drawn across it, and a child branch leaves at an angle
from it. So a branch carries a **frame**: three unit vectors at right angles,
`axis` along the branch, and `side` and `front` across it. Bending a branch
turns its frame, all three vectors together, about some axis. That is
Rodrigues' rotation. Chapter 10 wrote a rotation about an axis as a matrix;
this is the same rotation written with vectors, which the script needs because
it turns three vectors about an axis that changes at every step:

$$
\mathbf{v}' = \mathbf{v}\cos\theta + (\mathbf{k}\times\mathbf{v})\sin\theta + \mathbf{k}\,(\mathbf{k}\cdot\mathbf{v})(1-\cos\theta)
$$

for a vector **v** turned by θ about the unit axis **k**. Worked: (1, 0, 0)
turned by 90 degrees about +Y gives (0, 0, −1): cos θ = 0, sin θ = 1, and
**k** × **v** = (0, 1, 0) × (1, 0, 0) = (0, 0, −1). Three vectors turned by the
same rotation stay at right angles to each other, so a frame never needs
repairing. In the script, `rotate` is this formula, and the class `Frame`
holds the three vectors, with `turned` (all three by one rotation) and
`toward` (the axis toward a target by at most an angle, never past it).

### Growing

`grow` is the whole of the growth. One branch is grown section by section:
each step moves along the frame's axis by the section's length, then turns
the frame three ways:

- **gnarl**, a random turn about `side` and about `front`, larger on a thin
  branch: `g = gnarl · max(1, 1/√r)`;
- **twist**, a fixed turn about the branch's own axis;
- **force**, a turn toward up, +Y, of `force / r` radians at most, so thin
  branches bend more. Negative, it droops. Worked: the oak's force is 0.02,
  so a twig of radius 0.1 bends 0.02 / 0.1 = 0.2 radians, 11.5 degrees, each
  section; its trunk, of radius 1.41, barely 0.8 degrees.

The radius tapers along the branch: a broadleaf's falls by `taper` of it from
base to tip, so the oak's trunk, radius 1.41 with taper 0.73, keeps
1.41 × (1 − 0.73) = 0.38 at its top, eight sections up; an evergreen's tapers
to a point. Then the branch carries the next order's branches, or, at the last
order, its leaves; a broadleaf's branch also carries on from its tip as one
more branch of the next order, as a real oak's limbs fork rather than stop:

```python
def grow(plant, level, origin, frame, length, radius, rng, out, shape=None):
    """One branch, section by section, into out.branches; then the branches it carries, or its leaves. Its
    sections and segments are its level's, or `shape`'s: a tip carrying on takes its parent's."""
    p = plant["levels"][level]
    n, segments = shape or (p["sections"], p["segments"])
    sections = []
    for i in range(n + 1):
        r = radius * (1.0 - i / n) if plant["evergreen"] else radius * (1.0 - p["taper"] * i / n)
        sections.append((origin, frame, r))
        origin = add(origin, scale(frame.axis, length / n))
        g = p["gnarl"] * max(1.0, 1.0 / math.sqrt(max(r, 1e-4)))   # a thin branch wanders more
        frame = frame.turned(frame.side, rng.uniform(-g, g))
        frame = frame.turned(frame.front, rng.uniform(-g, g))
        frame = frame.turned(frame.axis, p["twist"])
        frame = frame.toward(UP, plant["force"] / max(r, 1e-4))   # toward the light, more where thin
    out.branches.append((level, sections, segments))
    tip, tip_frame, tip_radius = sections[-1]
    if level + 1 < len(plant["levels"]):
        children(plant, level + 1, sections, rng, out)
        if plant["tips"]:                                   # a broadleaf's branch carries on from its tip
            grow(plant, level + 1, tip, tip_frame, plant["levels"][level + 1]["length"], tip_radius, rng, out,
                 (n, segments))
    elif "leaves" in plant:
        leaves(plant, sections, rng, out)
        if plant["tips"]:
            out.leaves.append((tip, tip_frame, leaf_size(plant, rng)))
```

Where the children leave their parent is `spread`'s: `count` of them, one in
each of `count` equal stretches from `start` to the tip, at a random point in
its stretch. The oak's six limbs leave the trunk from 0.49 of its length on, so
each has a stretch of (1 − 0.49) / 6 = 0.085 of the trunk. Round the parent
they turn by the **golden angle**, 137.5 degrees, π(3 − √5), the angle that
puts each new leaf of a real plant over the biggest gap left by those before
it, so no two children line up. An evergreen's children shorten toward its
top, by (1 − t), so a pine grows into a cone. The script has `spread`,
`children` and `leaves`.

### Rings

A branch becomes a tube: a ring of `segments` points round each section,
across the frame, joined to the next ring by quads. Ring point k sits at the
angle 2πk / segments. The first point is repeated at the end of the ring, so
that the texture's u can run from 0 to 1 round it; at that seam two points
share a position. `tube` lists each quad's corners counter-clockwise seen from
outside (a, a + one ring, its neighbour, a + 1), which is the engine's front
face (Chapter 11 section 7).

### Same seed, same tree

Every random number comes from `random.Random(plant["seed"])`, through only
`random()` and `uniform()`, and the whole skeleton is grown once, before any
mesh is made: a `Skeleton`, the script's record of every branch's sections and
every leaf's place, frame and size. So the three levels of a plant are three
meshings of the same branches, and every run of the script makes the same
plants. To see the winter wood, run it from `Assets/Scenes/` with `--bare`,
which leaves the leaves off and writes the leafless plants over the finished
ones on `start` (section 2's run writes them back):

```text
python make_horizon_plants.py --bare
```

It prints a line for each plant, with its triangles and cards at each level,
which is the check that you grew the same plants; a last line, `cards: base t =
0`, which checks which way up the cards' pictures are and which section 2
explains; then a SHA-256 for each file it wrote, which depends on the C
library's `sin` and so is no check (Chapter 36 section 7 says the same of the
island). With `--bare` the oak, the pine and the bush print:

```text
OakTree: LOD0 3166 triangles, 0 cards; LOD1 1278 triangles, 0 cards; LOD2 56 triangles, 0 cards; far colour (0.07, 0.15, 0.03)
PineTree: LOD0 2652 triangles, 0 cards; LOD1 1572 triangles, 0 cards; LOD2 20 triangles, 0 cards; far colour (0.04, 0.11, 0.04)
Bush: LOD0 666 triangles, 0 cards; LOD1 276 triangles, 0 cards; LOD2 24 triangles, 0 cards; far colour (0.1, 0.17, 0.04)
```

and the fern's and the flower's lines are the same as in section 2's full run.
LOD2, the stand-in, comes from section 2's leaves, which `--bare` leaves out,
so its ball is fitted to the branches' tips instead.

### Into the demo

The plants load into Chapter 37's scene, after its props, through the same
`LoadAsset`: each file is a hidden prototype with three levels. `Props.h`
(which already includes `<array>`, for `m_treeAssets`) names the files after
`PropSettings`:

```cpp
// Chapter 39 section 1: the plants make_horizon_plants.py writes, in Assets/Scenes/Horizon/Plants/.
inline constexpr std::array<const char*, 5> PLANT_FILES{
    "OakTree.usda", "PineTree.usda", "Bush.usda", "Fern.usda", "Flower.usda",
};
```

and gains three public functions after `Counts`:

```cpp
    // Chapter 39 section 1: the five plants, after Load, into the same scene. A missing file is reported:
    // the pool keeps Chapter 37's trees, and there is no understory.
    InitializationResult LoadPlants(const std::filesystem::path& folder);
    bool                 PlantsLoaded() const { return m_firstPlant < m_assets.size(); }

    // Chapter 39 section 1: which trees the pool plants: the plants' leaf-card trees, or Chapter 37's. A
    // change plants every slot again, in the same cells.
    void SetLeafCards(bool leafCards);
```

and two members at the end, after `m_treeAssets`:

```cpp
    size_t                  m_firstPlant         = SIZE_MAX;   // Chapter 39 section 1: the plants' first asset,
    uint32_t                m_firstPlantMaterial = 0;          // and first material: every one after is a plant's
```

Everything `LoadPlants` appends comes after every prop's: an asset at or past
`m_firstPlant` is a plant, and a material at or past `m_firstPlantMaterial` is
a plant's. That one fact is how the rest of the chapter tells plants from
props. If a file is missing, `LoadPlants` forgets the plants again and the
pool keeps Chapter 37's trees. It never empties Chapter 37's props, as a
failed `Load` would. It goes at the end of `Props.cpp`, with `SetLeafCards`:

```cpp
// Chapter 39 section 1: the five plants, appended to the scene as Load appended Chapter 37's assets, each a
// hidden prototype with three levels. A plant's materials and meshes come after every prop's, so a material
// at or past the first plant's is a plant's. If one is missing, the plants are forgotten again and the pool
// keeps Chapter 37's trees; their meshes stay in the scene, unused.
InitializationResult Props::LoadPlants(const std::filesystem::path& folder)
{
    const size_t   firstAsset    = m_assets.size();
    const uint32_t firstMaterial = static_cast<uint32_t>(m_scene.MaterialCount());
    for (const char* file : PLANT_FILES)
    {
        const uint32_t asset = LoadAsset(folder / file);
        if (asset == NO_ASSET)
        {
            m_assets.resize(firstAsset);
            return InitializationResult::failure(std::format("{} is missing, or has no LOD0 to LOD2.", file));
        }
    }
    m_firstPlant         = firstAsset;
    m_firstPlantMaterial = firstMaterial;
    SetLeafCards(true);
    return InitializationResult::success();
}

// Chapter 39 section 1: the pool's trees by TreeInCell's kind, 0 broadleaf and 1 pine. Every slot forgets its
// cell, so the next PlantTrees plants all of them again, in the same cells with the same turn and size.
void Props::SetLeafCards(bool leafCards)
{
    const bool cards = leafCards && PlantsLoaded();
    const std::array<uint32_t, 2> assets = cards ? std::array{ FindAsset("OakTree"), FindAsset("PineTree") }
                                                 : std::array{ FindAsset("Broadleaf"), FindAsset("Pine") };
    if (assets == m_treeAssets || m_objects.empty())
    {
        m_treeAssets = assets;
        return;
    }
    m_treeAssets = assets;
    for (size_t slot = m_firstSlot; slot < m_objects.size(); ++slot)
    {
        m_objects[slot].cell = glm::ivec2(INT32_MIN);
    }
}
```

`SetLeafCards` swaps the two tree assets the pool plants by `treeInCell`'s
kind (Chapter 37 section 7), and makes every slot forget its cell. The next
`PlantTrees` then plants all of them again, in the same cells with the same
turn and size, now as the other trees. The names are `OakTree` and
`PineTree` because `Pine` is already Chapter 37's.

`HorizonDemo.h` gets the plants' settings, a struct above the class
`HorizonDemo`, as `TerrainSettings` sits above `Terrain` and `PropSettings`
above `Props`. Each section that adds a switch adds its field here, one line
after the last; section 1's is the switch between the trees:

```cpp
// Chapter 39: what the Plants header changes. The demo keeps it, so it survives Teardown.
struct PlantSettings
{
    bool         leafCards       = true;    // section 1: off, Chapter 37's trees
};
```

The demo keeps one, after `m_propsMilliseconds`, and declares the panel's
function after `DrawGroundControls`:

```cpp
    // Chapter 39 section 1: the plants' settings.
    PlantSettings m_plantSettings;

    void                 DrawPlantControls();                                  // Chapter 39: section 1
```

In `Setup`, the plants load inside Chapter 37's `if (!m_props.Loaded())`
block, as an `else if` after the props' `Load`: so they load only if the props
did, once per demo object, and survive `Teardown` with the props. The first
four lines of the block below are Chapter 37's own, the `if` that calls `Load`
and its warning, shown to place the new `else if`:

```cpp
        if (auto result = m_props.Load(folder); !result)
        {
            Log::warning(std::format("No props: {}", result.message()).c_str());
        }
        // Chapter 39 section 1: the plants, after the props, into the same scene.
        else if (auto plants = m_props.LoadPlants(folder / "Plants"); !plants)
        {
            Log::warning(std::format("No plants: {} The pool keeps Chapter 37's trees, and there is no understory.",
                                     plants.message()).c_str());
        }
```

`Record` tells the props which trees to plant, just before Chapter 37's
`m_props.Update`, so a change shows the same frame:

```cpp
    m_props.SetLeafCards(m_plantSettings.leafCards);              // Chapter 39 section 1
```

`DrawPanel` calls the new header after `DrawCameraControls`, so nothing
Chapters 35 to 38 put on the panel moves:

```cpp
        DrawCameraControls();    // Chapter 35 sections 1, 4
        DrawPlantControls();     // Chapter 39 section 1
```

and the header itself is a new function at the end of `HorizonDemo.cpp`, after
`DrawGroundControls`, closed at first. Each later section adds its lines at the
end of it, after a separator where a new group begins:

```cpp
// Chapter 39: the plants' group, a header of its own after the camera's, closed at first, so that nothing
// above it moves. Inside it, a separator before each later group: the shadows (section 4), the leaves at a
// distance (Part 2) and the understory (Part 3).
void HorizonDemo::DrawPlantControls()
{
    if (!ImGui::CollapsingHeader("Plants"))
    {
        return;
    }
    // Section 1: what was loaded, PLANT_FILES' five or none, over two lines to keep the panel narrow; and the
    // trees the pool plants.
    if (m_props.PlantsLoaded())
    {
        ImGui::TextUnformatted("Plants: OakTree, PineTree, Bush,");
        ImGui::TextUnformatted("        Fern, Flower");
    }
    else
    {
        ImGui::TextUnformatted("Plants: none; Chapter 37's trees");
    }
    ImGui::Checkbox("Leaf-card trees", &m_plantSettings.leafCards);
}
```

### Run

Run the demo on the leafless plants (the `--bare` run above), and press
**Wood**. A winter wood: across the meadow, oaks of bare, forking limbs, reddish
brown in the sun, and on the grass the thin crossed shadows of their branches.
Past a few hundred metres the trees are green balls on short trunks: LOD2, the
stand-in, which section 2 fits to the leaves and which `--bare` fits to the
branches' tips. Untick **Leaf-card trees**: Chapter 37's cones and balls come
back, in the same places. With Kenney's tree copied over `Broadleaf.usda`
(Chapter 37 section 10), the broadleaves are Kenney's.

## 2. Leaves are cards

**This is `make_horizon_plants.py`, its leaves and levels.** A leaf here is
not modelled. A **card** is a flat quad with a picture of a sprig on it, a few
leaves on a stem; the picture's alpha says where the leaves are. A tree is
some thousands of cards along its last branches. Section 3 cuts them out; this
section makes them, the three levels of detail, and the USD files.

### A card

A card stands on its branch: the middle of its base on the branch, rising
along the leaf's frame (which `spread` tilted away from the branch by the
order's `angle`). EZ-Tree crosses each card with a second at right angles
through the same axis, so a crown looks full from every side; that is 4
triangles a leaf:

```python
def card(mesh, material, point, frame, size, crossed, crop):
    """A leaf card: `size` metres tall, its base's middle on the branch, rising along the frame's axis, and as
    wide as the columns of the picture that hold any leaf, u0 to u1 of it (`crop`). Crossed: a second card
    through the same axis, at a right angle to the first."""
    u0, u1 = (0.0, 1.0) if NO_CROP or crop is None else crop
    for across in ([frame.side, frame.front] if crossed else [frame.side]):
        corners = []
        for u, t in ((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)):
            p = add(add(point, scale(across, (u - 0.5) * size)), scale(frame.axis, t * size))
            corners.append(mesh.vertex(p, frame.front, (u, 1.0 - t if FLIP_V else t)))
        mesh.quad(material, *corners)
        mesh.bases += corners[:2]
    mesh.cards += 1
```

Three things in it are choices.

**The crop.** The sprig fills only the middle of its square picture, 1,024
texels across: in `oak.png` the columns 177 to 845 hold any leaf at all, 0.653
of the width; in `pine.png` 111 to 912, 0.783. So the card is only as wide as
those columns,
and its u runs over the same columns. That is 35 % (oak) and 22 % (pine)
fewer pixels drawn for nothing, and no extra triangle. Call the share of a
picture's texels whose alpha reaches the cutoff, 0.5, its **kept share**: the
leaf that section 3 keeps. The oak's rises from 0.256 of the square to 0.392
of the card (0.256 / 0.653), the pine's from 0.229 to 0.292 (0.229 / 0.783).
`--no-crop` is the control: whole squares. The script's counts, "N cards", count
each `card` call: a crossed pair is one card, of two quads.

**Which way up.** The sprigs' stems are at the bottom of the PNGs. The
importer stores `1 − v` (Chapter 14 section 12): USD's t runs up from an
image's bottom row, the engine's v down from its top. So the script writes
USD t = 0 at a card's base, and the engine's `uv.y` is 1 at the base and 0 at
the tip, on every card of every level. `--flip-v` writes the opposite, and
every sprig hangs from its tip. The script checks itself: its line "cards:
base t = 0" lists every t it wrote at a card's base. One value, 0, is right; a
card written upside down would add a 1 to the list.

**The normal.** A card's own normal would light a crown as thousands of
facets, each bright or dark by which way it happens to face. Instead every
leaf vertex gets the **crown normal**, pointing away from the middle of the
crown: `normalize(p − c)`, with c the middle of the leaves' box from 3 % to
97 % of them along each axis (the odd leaf that sticks out does not move it). The
crown then lights like a ball, the sunlit side bright and the far side dark,
and its normal must be the same from either face: flipped for the back face,
as Chapter 37's shader does with `gl_FrontFacing`, it would point into the
crown on every card seen from behind, half of them, and the sunlit side would
go dark (section 3 keeps it unflipped). Worked: a leaf 3 m out from the
middle and 1 m above it has the normal (3, 1, 0) / √10 = (0.95, 0.32, 0).
`crowned` sets it on every vertex of a card or frond as it is made.

### Three levels of detail

The same skeleton is meshed three times, by `mesh_level` (in the script) with
a dictionary of detail per level:

- **LOD0**: every section, every card.
- **LOD1**: every `stride`th section, fewer sides, and one card in `every`,
  each `grow` times larger. Keeping the leaves' area would grow each card by
  √n for 1 card in n: √4 = 2 for the oak. But overlapping leaves already hide
  each other, so keeping the area over-fills the crown; the scales here were
  measured instead, with every tree forced to one level (section 3) in the
  overdraw view (section 7): the oak keeps 1 card in 4 at 1.6 times the size,
  the pine 1 in 3 at 1.35, the bush 1 in 2 at 1.41.
- **LOD2**: a solid **stand-in** fitted to the crown's box: a ball on a trunk
  for the oak, two cones on a trunk for the pine, a ball for the bush, in the
  plant's `Far` material. Its size is the box's times `proxy_grow`, again
  measured so that it covers as much of the screen as LOD1 does where one
  takes over from the other: 1.2 for the oak and the bush, whose cards stick
  out past the box, 0.42 for the pine, whose box the long lower branches
  overstate (`proxy`).

### The colour from afar

From 150 m the leaves are a few pixels, and what shows is their average.
Chapter 37 chose the far forest's colours: (0.07, 0.15, 0.03) for broadleaf
leaves, (0.04, 0.11, 0.04) for needles. EZ-Tree's pictures are brighter. So
each leaf material scales its picture's colour by a **tint**, the texture
node's `inputs:scale`, chosen so that the kept texels' mean (those with alpha
of 0.5 or more, in linear light) times the tint is 37's colour: `oak.png`'s
leaves average (0.127, 0.226, 0.044), so the oak's tint is (0.07 / 0.127,
0.15 / 0.226, 0.03 / 0.044) = (0.551, 0.664, 0.682). The pine's is (0.339,
0.611, 1.290). The bush uses `oak.png` too, toward a lighter, yellower green.
The stand-in's `Far` colour is the same green, so the far wood keeps the
colour Chapter 37 gave it. Each tint sits in the script's plant table with the
mean it was worked out from beside it.

### The USD

Each plant is a file as Chapter 37's props are: an `Xform` named for the
plant, a `Scope "Materials"`, and three `Mesh` children `LOD0` to `LOD2`, with
`normal3f[] normals` and `texCoord2f[] primvars:st`, both per vertex, and one
`GeomSubset` per material. LOD0 and LOD1 are `doubleSided`: a card is seen
from both sides, and the bark is double-sided with it, because the flag
belongs to the whole mesh and `Props` takes one mesh a level. LOD2 is not. The
leaf material follows Chapter 15's `MaterialTest.usda`: one `UsdUVTexture` in
sRGB feeding both `diffuseColor` (its rgb) and `opacity` (its alpha), so the
importer uploads the picture once, `opacityThreshold` 0.5, clamp wraps, and
the tint as `inputs:scale` (`material_text`, in the script).

No colour is written beside the `diffuseColor` connection. TinyUSDZ, given
both a value and a connection, keeps the value and drops the connection, and
the leaves come out untextured. The next run shows what that looks like.

> **The plant-space contract.** Every plant file, and every later chapter that
> reads one (40 bakes them, 42 bends them in the wind), holds to this:
>
> 1. The base is at the origin, y = 0 is the ground, and the trunk or stem
>    leaves it along +Y at x = z = 0; a tree's trunk reaches 1 m below, so it
>    stands in a slope.
> 2. The height is LOD0's top; the crown is LOD2's stand-in.
> 3. Every card and frond has the engine's `uv.y` = 1 at its base and 0 at its
>    tip, and `uv.x` across the cropped picture.
> 4. Leaf normals are crown normals: nothing in a plant's look depends on the
>    view.
> 5. Subsets come in the same order at every level: `<Plant>Bark` first where
>    the plant has one (the fern has none), then `<Plant>Leaf`, `<Plant>Head`
>    or `<Plant>Far`. The materials carry those names (`OakTreeBark`,
>    `OakTreeLeaf`, `BushLeaf`, `FernLeaf`, `FlowerHead` and so on), and the
>    demo finds them by name.

### Get the pictures

The three leaf pictures are EZ-Tree's, unchanged: `oak.png`, `pine.png` and
`ash.png` from its `src/app/public/textures/leaves/`, at commit
`dcf309bd86bd521083d9c70f01f2de45fdc7c457`, with EZ-Tree's `LICENSE` beside
them as `LICENSE.txt` (Chapter 38 section 5's routine for third-party files).
They are on `start`, in `Assets/Scenes/Horizon/Plants/Textures/`. To fetch them
yourself: EZ-Tree keeps them in Git LFS, so the plain "raw" link of each file
gives a 131-byte text file, a pointer that names the picture, not the picture.
Take them from GitHub's LFS host instead:

```text
https://media.githubusercontent.com/media/dgreenheck/ez-tree/dcf309bd86bd521083d9c70f01f2de45fdc7c457/src/app/public/textures/leaves/oak.png
```

and the same with `pine.png` and `ash.png`; or clone EZ-Tree with Git LFS
installed and run `git lfs pull`. The licence is a plain text file, 1,073
bytes, which the "raw" link gives as it is:
`https://raw.githubusercontent.com/dgreenheck/ez-tree/dcf309bd86bd521083d9c70f01f2de45fdc7c457/LICENSE`.
Check the pictures: 238,115, 303,684 and 181,423 bytes, with these SHA-256s
(`sha256sum`, or `certutil -hashfile oak.png SHA256` on Windows):

```text
24451223cf396d22910a4932b8bb996a7274e63d81e24128c96a430ab67822b1  oak.png
88be36a2387554ac4b7c7d1549eae454a37ad896e8e33a7d6ae5956bd169ab08  pine.png
5ec987db3829a839856c32c79b18a33a78f209e911cad55c65abfb77f30e2d29  ash.png
```

Run the script again without `--bare`, which writes the finished plants, the
ones on `start`. It does not read the pictures: their crops and tints are
numbers in its tables, measured from them once.

```text
OakTree: LOD0 13806 triangles, 2660 cards; LOD1 3938 triangles, 665 cards; LOD2 56 triangles, 0 cards; far colour (0.07, 0.15, 0.03)
PineTree: LOD0 12492 triangles, 2460 cards; LOD1 4852 triangles, 820 cards; LOD2 20 triangles, 0 cards; far colour (0.04, 0.11, 0.04)
Bush: LOD0 1674 triangles, 252 cards; LOD1 780 triangles, 126 cards; LOD2 24 triangles, 0 cards; far colour (0.1, 0.17, 0.04)
Fern: LOD0 90 triangles, 0 cards; LOD1 20 triangles, 0 cards; LOD2 20 triangles, 0 cards
Flower: LOD0 34 triangles, 2 cards; LOD1 10 triangles, 1 cards; LOD2 10 triangles, 1 cards
cards: base t = 0
```

A SHA-256 for each file follows these lines. Another C library's `sin` may
change a last digit somewhere in a file, and so its hash, so the triangle counts
are the check that you grew the same plants (the reference run's hashes, Python
3.13 with glibc 2.39, are in `REFERENCE.md`). The oak's LOD0 is 2,660 crossed
cards, 10,640 triangles, on 3,166 triangles of bark.

### Run

Nothing in the demo changes: build, which copies the new files beside the
executable (Chapter 13 section 6), run the demo, and press **Wood**.
The same wood, every crown a heap of blue-grey squares: each card drawn whole
by Chapter 37's flat pipeline, in its material's colour. The leaf material's
colour comes only from the picture, which that pipeline does not read, so it is
UsdPreviewSurface's default `diffuseColor`, a 0.18 grey, lit by the sky. The
shadows are solid blots. Far off, the stand-ins are green, in their own colour.

## 3. Cutting them out

**This is `Leaf.frag.glsl`, and the pipelines that run it.** The flat pipeline
cannot cut a leaf out: it has no texture coordinate, reads no texture, and
never discards. Plants need pipelines of their own, and those need the
material's picture. The engine uploads it, and builds Chapter 15's material
set for it (the picture at binding 1, the parameters at binding 0), when a
material is registered whole; this section's `RegisterProps` starts doing
that.

### The engine's material set, at a number of the demo's

`SceneRenderer` builds a set per material and binds it at set 1 in its own
pipelines. In `Horizon`, set 1 is the island's (Chapter 38 section 2). But a
set is not tied to a number: the number belongs to the pipeline layout. The
leaf pipelines' layout is {set 0 the frame, set 1 the island, set 2 the
material}, and the same set the engine binds at 1 is bound here at 2. Set 1 is
in the layout and never bound: no leaf shader reads it, and only sets a
shader uses must be bound.

> **Jump:** a descriptor set is made from a set layout, and binds to whatever
> number a pipeline layout gives that set layout. Keep in mind that the leaf
> layout borrows two set layouts it did not make: the island's from `Terrain`,
> and the material's from `SceneRenderer`, which is why they are created after
> both.

So the engine gains its one change in this chapter, two read-only accessors at
the end of `SceneRenderer`'s public section:

```cpp
    // Chapter 39: a demo's own pipeline can bind a material's set (Chapter 15 section 7) at a number of its own.
    VkDescriptorSetLayout MaterialSetLayout() const { return m_materialSetLayout; }
    VkDescriptorSet       MaterialSet(uint32_t material) const { return m_gpuMaterials[material].set; }
```

and `Terrain.h` hands out its set's layout, after `Materials()`:

```cpp
    // Chapter 39 section 3: the island set's layout, which every pipeline of the demo holds at set 1.
    VkDescriptorSetLayout IslandSetLayout() const { return m_setLayout; }
```

### What a run pushes

The fragment shader needs Chapter 37's `FlatDraw` (the colour, the sky, the
flags) and, from section 6, a table per material. The cutoff and the tint it
reads from the material's own buffer, as Chapter 15's mesh shader does. Its
push block is `FlatDraw` then `LeafDraw`, 96 of the 128 bytes every GPU
offers, which leaves 32 for Chapter 42. `HorizonTypes.h` gains two flags the
leaf pipelines read, after `FLAT_SKY`, and `LeafDraw` after them. Section 6
fills `LeafDraw`'s table and is the first to read it; sections 5 and 6 add a
flag each here:

```c
/* Chapter 39: more bits of FlatDraw::flags, which only the leaf pipelines read. */
#define FLAT_LEAF      4u    /* section 3: foliage: the crown's normal, the same from either face */
#define FLAT_PETALS    8u    /* section 3: a flower's head, in one of three petal colours */

/* Chapter 39 section 3: what a leaf pipeline's run pushes after FlatDraw. Section 6: k for mip levels 0 to
   11, four to a vec4: the scale that keeps a cut-out's share of kept texels at every level. */
struct LeafDraw
{
    vec4 mipScale[3];   /*  0 */
};
```

with its size checked in the file's C++ branch, the `#ifdef __cplusplus` block
where Chapter 37 put `FlatDraw`'s `static_assert`:

```c
    static_assert(sizeof(LeafDraw) == 48, "LeafDraw layout drifted.");
```

and `HorizonDemo.cpp` names the pair, after the views:

```cpp
// Chapter 39 section 3: what a leaf pipeline's run pushes, FlatDraw then LeafDraw: 96 of the 128 bytes
// every GPU offers.
struct LeafPush
{
    FlatDraw flat;
    LeafDraw leaf;
};
static_assert(sizeof(LeafPush) == 96, "LeafPush layout drifted.");
```

### Fifteen samplers

A pipeline layout counts its samplers per stage from its set layouts, not
from what the shaders read: set 0 has four the fragment stage can see
(bindings 4, 10, 11 and 12), the island four, and the material set seven, its
bindings 1 to 7 (Chapter 15 section 7). That is 15, and Vulkan promises only
16. A combined image sampler counts against both
`maxPerStageDescriptorSamplers` and `maxPerStageDescriptorSampledImages`, so
`CreateLeafPipelines` checks both and fails `Setup` with a message if either
is short, as Chapter 30's sea checks its own limit. Lavapipe, the CPU Vulkan
driver this guide's runs are checked on, allows a million.

### The pipelines

`CreateLeafPipelines` is a new member function of `HorizonDemo`. It goes after
`DrawGroundControls`, before `DrawPlantControls`, with the two that follow it
in this section, `BindLeafRun` and (in section 6) `CreateLeafPlates`. It makes
the layout and a small table of pipelines: plant
opaque (bark, stand-ins) and plant cut out (leaves), with `Leaf.frag.glsl`'s
`CUTOUT` a specialization constant (Chapter 15 section 11). Every one compares
depth with GREATER, as every pipeline in `Horizon` does (Chapter 35 section 6),
and takes its cull mode per run, as the flat pipeline does. Under MSAA the cut
out one has alpha to coverage on: at one sample the fragment's alpha is the
whole decision; section 5 says what it does with more:

```cpp
// Chapter 39 section 3: the pipelines that draw plants, in one table, [understory][mode]: a row with
// Leaf.vert.glsl, to which section 10 adds the understory's; opaque, or cut out, to which section 7 adds a
// mode. Their layout is Chapter 38's set plan: set 0 the frame's, set 1 the island's, which no leaf shader
// reads, and set 2 the run's material, the engine's own set for it. FlatDraw and then LeafDraw are pushed to
// the fragment shader.
InitializationResult HorizonDemo::CreateLeafPipelines()
{
    // Samplers in the fragment stage, counted by the layout, not by what the shaders read: set 0's four, the
    // island's four and the material's seven. Vulkan promises 16 of each kind; a GPU may offer more.
    constexpr uint32_t SAMPLERS = 15;
    VkPhysicalDeviceProperties device{};
    vkGetPhysicalDeviceProperties(m_context.vulkan.physicalDevice, &device);
    if (device.limits.maxPerStageDescriptorSamplers < SAMPLERS || device.limits.maxPerStageDescriptorSampledImages < SAMPLERS)
    {
        return InitializationResult::failure(std::format(
            "The leaf pipelines need {} samplers in one stage; this GPU allows {} samplers and {} sampled images.",
            SAMPLERS, device.limits.maxPerStageDescriptorSamplers, device.limits.maxPerStageDescriptorSampledImages));
    }

    const std::array<VkDescriptorSetLayout, 3> setLayouts{ m_sceneRenderer.FrameSetLayout(), m_terrain.IslandSetLayout(),
                                                           m_sceneRenderer.MaterialSetLayout() };
    const VkPushConstantRange pushRange{ .stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT, .offset = 0, .size = sizeof(LeafPush) };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = static_cast<uint32_t>(setLayouts.size()),
        .pSetLayouts            = setLayouts.data(),
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.vulkan.device, &layoutInfo, nullptr, &m_leafLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the leaf pipelines.");
    }

    // A plant's vertices: Chapter 11's Vertex, with its uv now.
    const VkVertexInputBindingDescription binding{
        .binding   = 0,
        .stride    = sizeof(scene::Vertex),
        .inputRate = VK_VERTEX_INPUT_RATE_VERTEX,
    };
    const std::array<VkVertexInputAttributeDescription, 3> attributes{ {
        { .location = 0, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, position) },
        { .location = 1, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, normal) },
        { .location = 2, .binding = 0, .format = VK_FORMAT_R32G32_SFLOAT, .offset = offsetof(scene::Vertex, uv) },
    } };

    // Leaf.frag.glsl's constant CUTOUT (Chapter 15 section 11's way).
    struct Constants
    {
        VkBool32 cutout;
    };
    const std::array<VkSpecializationMapEntry, 1> entries{ {
        { .constantID = 0, .offset = offsetof(Constants, cutout), .size = sizeof(VkBool32) },
    } };
    const VkDynamicState dynamicStates[] = { VK_DYNAMIC_STATE_CULL_MODE };
    const bool multisampled = m_context.formats.samples != VK_SAMPLE_COUNT_1_BIT;
    for (uint32_t understory = 0; understory < 1; ++understory)   // section 10 adds the second row
    {
        for (uint32_t mode = 0; mode < 2; ++mode)   // 0 opaque, 1 cut out; section 7 adds 2
        {
            const Constants            values{ mode == 1 ? VK_TRUE : VK_FALSE };
            const VkSpecializationInfo specialization{
                .mapEntryCount = static_cast<uint32_t>(entries.size()),
                .pMapEntries   = entries.data(),
                .dataSize      = sizeof(values),
                .pData         = &values,
            };
            const GraphicsPipelineDesc desc{
                .vertexShader           = "Horizon/Leaf.vert.spv",
                .fragmentShader         = "Horizon/Leaf.frag.spv",
                .vertexBindings         = { &binding, 1 },
                .vertexAttributes       = attributes,
                .colorFormats           = { &m_context.formats.color, 1 },
                .depthFormat            = m_context.formats.depth,
                .depthTest              = true,
                .depthWrite             = true,
                .depthCompare           = VK_COMPARE_OP_GREATER,   // Chapter 35 section 6: reversed, as every pipeline here
                .frontFace              = VK_FRONT_FACE_COUNTER_CLOCKWISE,
                .dynamicStates          = dynamicStates,
                .fragmentSpecialization = &specialization,
                .layout                 = m_leafLayout,
                .samples                = m_context.formats.samples,
                .alphaToCoverage        = mode == 1 && multisampled,   // Chapter 18 section 8's toCoverage
            };
            m_leafPipelines[understory][mode] = createGraphicsPipeline(m_context.vulkan.device, m_context.pipelineCache, desc);
            if (m_leafPipelines[understory][mode] == VK_NULL_HANDLE)
            {
                return InitializationResult::failure("Creating the leaf pipelines failed.");
            }
        }
    }
    return InitializationResult::success();
}
```

The table is `[understory][mode]` from the start, with one row filled; section 7
adds a mode and section 10 the second row. `HorizonDemo.h` declares the table
with the rest of section 3's members, after `m_plantSettings`:

```cpp
    // Chapter 39 section 3: by material, what the leaf pipelines need; the pipelines, [understory][mode]
    // (sections 3, 7, 10); and which layout set 0 was last bound with.
    struct LeafMaterial
    {
        bool plant  = false;   // drawn by the leaf pipelines
        bool cutout = false;   // its alpha is tested
    };
    std::vector<LeafMaterial>                m_leafMaterials;
    VkPipelineLayout                         m_leafLayout  = VK_NULL_HANDLE;
    std::array<std::array<VkPipeline, 3>, 2> m_leafPipelines{};
    VkPipelineLayout                         m_boundLayout = VK_NULL_HANDLE;
```

and three functions after `DrawPlantControls`:

```cpp
    InitializationResult CreateLeafPipelines();                                // Chapter 39: section 3
    void                 BindLeafRun(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t material,
                                     bool understory, bool skyOn);              // Chapter 39: section 3
    void                 DescribeMaterial(uint32_t material, const scene::Material& source,
                                          bool plant);                         // Chapter 39: section 3
```

`Setup` creates them right after the terrain, whose set layout they need, and
sizes the per-material table to every material registered so far. By then
`RegisterProps` has run: Chapter 37's `Setup` calls it right after the props
load, before the plates, the level colours and the ground, so the scene's
material indices are still the renderer's. The materials added since, the
plates' and the level colours', are not plants' (`DescribeMaterial` sizes the
table for the materials it describes; this resize covers the ones after them):

```cpp
    // Chapter 39 section 3: the plants' pipelines, whose layout holds the island's set, so after the terrain.
    if (auto result = CreateLeafPipelines(); !result) { return result; }
    m_leafMaterials.resize(m_sceneRenderer.MaterialCount());   // every material added since: not a plant's
```

and `Teardown` destroys them after the timestamps, before the sky and the
terrain:

```cpp
    for (const std::array<VkPipeline, 3>& pipelines : m_leafPipelines)           // Chapter 39 section 3
    {
        for (VkPipeline pipeline : pipelines)
        {
            vkDestroyPipeline(m_context.vulkan.device, pipeline, nullptr);
        }
    }
    vkDestroyPipelineLayout(m_context.vulkan.device, m_leafLayout, nullptr);
    m_leafPipelines = {};
    m_leafLayout    = VK_NULL_HANDLE;
    m_leafMaterials.clear();
```

### `Leaf.vert.glsl`

The vertex shader is `Flat.vert.glsl` (Chapters 35 and 37) copied as
`Leaf.vert.glsl`, with the texture coordinate passed on, and where the plant
stands, for a tint per plant. Its header comment names it:

```glsl
// Shaders/Horizon/Leaf.vert.glsl - Chapter 39 section 3: Flat.vert.glsl, with the texture coordinates the
// leaf cards are cut out by, and where the plant stands, for its tint.
```

Chapter 11's `Vertex` carries the texture coordinate after the normal, so the
inputs are one line more, under one comment, in place of `Flat.vert.glsl`'s two:

```glsl
// Chapter 11's 48-byte Vertex: position, normal and uv; its tangent, at offset 32, no plant shader reads.
layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
```

the outputs two more, in place of its two (the whole file is this chapter's, so
the "Chapter 37" notes go):

```glsl
layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec3 worldNormal;
layout(location = 2) out vec2 uv;
layout(location = 3) flat out vec2 plantBase;   // the plant's own origin, x and z: the same for all of it
```

and `main` fills them, in place of the `worldNormal` line:

```glsl
    worldNormal   = instance.normalMatrix * inNormal;
    uv            = inUv;
    plantBase     = instance.model[3].xz;
```

`model[3]` is the model matrix's last column, its translation: where the plant
stands. It is passed `flat`, not interpolated, since it is the same at every
vertex of the plant.

### `Leaf.frag.glsl`

The fragment shader reads the picture first, while every pixel of the 2 x 2
quad still runs (Chapter 38 section 6): a discard or a branch before it would
leave the derivatives that choose the mip level undefined. Then it takes
alpha as Chapter 15's `materialOpacity` does, cuts at the material's
threshold, and only then lights what is left. A leaf costs most where it is
clear, and six or seven in ten of a card's pixels are (the oak's kept share is
0.392 of its card, the pine's 0.292): discarding them before the lighting
means the nine shadow taps (Chapter 17 section 8's filter), the sky reads and
the haze run only on the leaf. The material block's type, `MaterialParameters`
(Chapter 15 section 6), is not in the include list because it comes with
`HorizonTypes.h`, which includes `Include/SharedShaderTypes.h`:

```glsl
// Shaders/Horizon/Leaf.frag.glsl - Chapter 39 section 3: everything a plant is made of: its bark, its leaf
// cards cut out by their picture's alpha, its stand-in, all lit, shadowed and hazed as Flat.frag.glsl lights
// the objects round it.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // the camera, the sun, the ambient light
#include "HorizonTypes.h"    // FlatDraw, LeafDraw, FLAT_*
#include "Random.glsl"       // pcgHash, randomFloat (Chapter 21)

layout(push_constant) uniform LeafBlock
{
    FlatDraw draw;   // 0: Chapter 37's, as the flat pipeline has it
    LeafDraw leaf;   // 48
};

#include "HorizonShading.glsl"   // Chapter 37: lightAt, sunShadow, hazed

// Set 2: the run's material, Chapter 15's set, which the engine binds at set 1 in its own pipelines. This
// pipeline's set 1 is the island's (Chapter 38 section 2), which these shaders do not read.
layout(std140, set = 2, binding = 0) uniform MaterialBlock { MaterialParameters material; };
layout(set = 2, binding = 1) uniform sampler2D baseColorTexture;   // colour and alpha: one picture (section 2)

layout(constant_id = 0) const bool CUTOUT   = false;   // section 3: the material's alpha is tested

layout(location = 0) in vec3 worldPosition;
layout(location = 1) in vec3 worldNormal;
layout(location = 2) in vec2 uv;
layout(location = 3) flat in vec2 plantBase;

layout(location = 0) out vec4 outColor;

// Section 3: three petal colours, linear: white, yellow and violet.
const vec3 PETALS[3] = vec3[](vec3(1.0, 1.0, 1.0), vec3(1.0, 0.75, 0.15), vec3(0.55, 0.35, 0.95));

// Section 3: each plant a little lighter or darker and yellower or greener than the next, from a hash of
// where it stands, to a quarter of a metre; a flower's head in one of three colours.
vec3 plantTint(vec2 base, bool petals)
{
    ivec2 spot  = ivec2(floor(base * 4.0));
    uint  state = uint(spot.x) * 2654435761u ^ pcgHash(uint(spot.y) + 39u);
    float light = 0.85 + 0.3 * randomFloat(state);
    float warm  = randomFloat(state);
    if (petals)
    {
        return PETALS[min(uint(3.0 * warm), 2u)];
    }
    return light * mix(vec3(1.0), vec3(1.08, 1.0, 0.8), warm);
}

void main()
{
    // Read first, while every pixel of the 2 x 2 quad still runs (Chapter 38 section 6): the picture.
    vec4 texel = texture(baseColorTexture, uv);

    // The material's opacity, as Chapter 15's materialOpacity takes it, through the opacity map's scale and
    // channel. Chapter 15 reads the opacity picture at binding 7; a plant's opacity picture is its colour
    // picture (section 2), so binding 1's texel serves both.
    float alpha = material.opacity * dot(texel * material.opacityMap.scale + material.opacityMap.bias,
                                         material.opacityMap.channel);

    float cutoff = material.opacityThreshold;

    // The cut: below the cutoff, thrown away before it is lit.
    float coverage = 1.0;
    if (CUTOUT)
    {
        coverage = step(cutoff, alpha);
        if (coverage <= 0.0)
        {
            discard;
        }
    }

    // The picture times its tint (the material's) times this plant's.
    vec3 albedo = (texel * material.baseColorMap.scale + material.baseColorMap.bias).rgb * material.baseColor.rgb
                * plantTint(plantBase, (draw.flags & FLAT_PETALS) != 0u);

    // Lit as the objects are (Chapter 37 section 2). A leaf's normal is the crown's (section 2), the same from
    // both faces; anything else faces the side being drawn.
    vec3 N = normalize(worldNormal);
    if ((draw.flags & FLAT_LEAF) == 0u)
    {
        N *= gl_FrontFacing ? 1.0 : -1.0;
    }
    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;
    vec3  color     = albedo * lightAt(N, sunShadow(worldPosition, N, viewDepth));
    vec3  toEye     = frame.cameraPosition.xyz - worldPosition;
    float range     = length(toEye);
    color = hazed(color, toEye / range, range, (draw.flags & FLAT_SKY) != 0u, draw.sky);

    // Under MSAA, alpha to coverage keeps the share of the pixel's samples that alpha says (Chapter 18
    // section 8): all of them, here; section 5 changes this comment.
    outColor = vec4(color, coverage);
}
```

`plantTint` makes each plant a little lighter or darker, warmer or greener,
than its neighbour, from a hash of where it stands, so no two trees in a wood
are the same green. `randomFloat` (Chapter 21 section 3) moves `state` on each
time it is called, so its second call gives a second number. `FLAT_LEAF`
keeps the crown normal unflipped on the back face; bark and stand-ins flip
theirs as the flat pipeline does.

### Registering the props whole

Until now `RegisterProps` registered each prop material as a flat colour.
Plants need the engine to own their pictures and build their sets, so it now
adds every scene texture before the materials, in index order (so a material's
texture index means the same in both), then every material whole with
`AddMaterial`. This replaces Chapter 37 section 2's `RegisterProps`. Sections 4
and 6 change two parts of it again (the mesh loop, the call's arguments), and
say so:

```cpp
// Chapter 37 section 2: the props' meshes and materials, in index order, as the USD viewer registers its scene
// (Chapter 14 section 9): a DrawItem from the props' scene then means the same mesh and material here.
// Chapter 39 section 3: the scene's pictures before its materials, so that a material's texture index is the
// renderer's; then every material whole, with its set, which the leaf pipelines bind.
void HorizonDemo::RegisterProps()
{
    const scene::Scene& world = m_props.World();
    for (uint32_t mesh = 0; mesh < world.MeshCount(); ++mesh)
    {
        m_sceneRenderer.AddMesh(world.GetMesh(mesh).data);
    }
    for (uint32_t texture = 0; texture < world.TextureCount(); ++texture)
    {
        m_sceneRenderer.AddTexture(world.GetTexture(texture));
    }
    for (uint32_t material = 0; material < world.MaterialCount(); ++material)
    {
        const scene::Material& source = world.GetMaterial(material);
        DescribeMaterial(m_sceneRenderer.AddMaterial(source), source, m_props.IsPlantMaterial(material));
    }
}
```

`DescribeMaterial` is a new function, right after it, which keeps what the demo
needs of each material: the colour the flat pipeline pushes (for a picture, its
tint), its flags, and whether it is a plant's and cut out. Chapter 37's props
come out exactly as before: `FLAT_LIT` and their base colour. This is its first
version; section 6 gives it a fourth parameter, a picture, and adds to its end:

```cpp
// Chapter 39 section 3: what the demo keeps of a material it registered whole: the colour the flat pipeline
// pushes, which for a picture is its tint; how it is lit: a leaf (or a flower's head) with the crown's
// normal, a head in its petal colour; and for the leaf pipelines, whether it is a plant's and whether it is
// cut out.
void HorizonDemo::DescribeMaterial(uint32_t material, const scene::Material& source, bool plant)
{
    m_materialColors.resize(std::max<std::size_t>(m_materialColors.size(), material + 1));
    m_materialFlags.resize(m_materialColors.size());
    m_leafMaterials.resize(m_materialColors.size());
    const bool textured = source.baseColorTexture.image != scene::NO_TEXTURE;
    m_materialColors[material] = textured ? glm::vec4(glm::vec3(source.baseColorTexture.scale), 1.0f) : source.baseColor;
    m_materialFlags[material]  = FLAT_LIT | (source.name.ends_with("Leaf") ? FLAT_LEAF : 0u)
                               | (source.name.ends_with("Head") ? FLAT_LEAF | FLAT_PETALS : 0u);
    LeafMaterial& leaf = m_leafMaterials[material];
    leaf.plant  = plant;
    leaf.cutout = source.opacityThreshold > 0.0f;
}
```

`Props.h` answers which materials are plants', in the public part after
`SetLeafCards`:

```cpp
    // Chapter 39 section 3: whether a material is a plant's, which the leaf pipelines draw.
    bool IsPlantMaterial(uint32_t material) const { return PlantsLoaded() && material >= m_firstPlantMaterial; }
```

Every material from a plant file goes through the leaf pipelines, bark and
stand-ins included, so a plant's tint holds across its three levels and LOD2
does not change colour when it takes over.

### The objects, through two families of pipelines

Chapter 37's batch lambda grows a branch. A plant's run goes to `BindLeafRun`;
any other run rebinds the flat pipeline if the last run was a plant's. Set 0
must be bound again on every switch. Two pipeline layouts are compatible for
set 0 only if they were made with the same set 0 layout and the same
push-constant ranges; the flat layout pushes 48 bytes to the fragment stage
and the leaf layout 96, so a set 0 bound with one is not kept for the other.
`PrepareDraws` sorts by material, so there are a few switches a frame, not one
per run. In `Record`, right after the flat pipeline is bound for the scene's
batches (`vkCmdBindPipeline` with `m_flatPipeline`, and `BindFrameSet` with
`m_flatLayout`), the demo notes which layout set 0 is bound with:

```cpp
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_flatPipeline);
    m_sceneRenderer.BindFrameSet(commandBuffer, m_flatLayout, frame.frameIndex);
    m_boundLayout = m_flatLayout;   // Chapter 39 section 3: which layout set 0 is bound with
```

and the lambda passed to `RecordBatches`, Chapter 37's, grows a branch; the
call and the lambda's first lines become:

```cpp
    m_sceneRenderer.RecordBatches(commandBuffer, frame.frameIndex, DrawList::Scene,
                                  [&](VkCommandBuffer cb, const DrawRun& run) {
        vkCmdSetCullMode(cb, run.doubleSided ? VK_CULL_MODE_NONE : VK_CULL_MODE_BACK_BIT);
        // Chapter 39 section 3: a plant's run through the leaf pipelines, not the understory's.
        if (m_leafMaterials[run.material].plant)
        {
            BindLeafRun(cb, frame.frameIndex, run.material, false, skyOn);
            return;
        }
        if (m_boundLayout != m_flatLayout)
        {
            vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, m_flatPipeline);
            m_sceneRenderer.BindFrameSet(cb, m_flatLayout, frame.frameIndex);
            m_boundLayout = m_flatLayout;
        }
```

`BindLeafRun` binds the run's pipeline, set 0 if needed, the material's set at
2, and pushes. It takes `understory` from the start: section 10 draws the
understory through this same function, from the table's second row and with
culling off. Until then every call passes `false`:

```cpp
// Chapter 39 section 3: one run of a plant: its pipeline, from the table's first row, or from the second for
// section 10's understory, whose plants are seen from every side; set 0 again if the last run used the flat
// layout, whose push range differs, so its set 0 does not carry over; the material's own set at set 2; and
// what it pushes.
void HorizonDemo::BindLeafRun(VkCommandBuffer commandBuffer, uint32_t frameIndex, uint32_t material, bool understory,
                              bool skyOn)
{
    const LeafMaterial& leaf = m_leafMaterials[material];
    const uint32_t      mode = leaf.cutout ? 1u : 0u;
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_leafPipelines[understory ? 1 : 0][mode]);
    if (m_boundLayout != m_leafLayout)
    {
        m_sceneRenderer.BindFrameSet(commandBuffer, m_leafLayout, frameIndex);
        m_boundLayout = m_leafLayout;
    }
    if (understory)
    {
        vkCmdSetCullMode(commandBuffer, VK_CULL_MODE_NONE);   // every small plant is drawn from both sides
    }
    const VkDescriptorSet set = m_sceneRenderer.MaterialSet(material);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_leafLayout, 2, 1, &set, 0, nullptr);

    const uint32_t flags = m_materialFlags[material] | (skyOn ? FLAT_SKY : 0u);
    const LeafPush push{
        .flat = { .baseColor = m_materialColors[material],
                  .sky       = glm::vec4(FALLBACK_SKY, m_terrainSettings.hazeDistance),
                  .flags     = flags },
    };
    vkCmdPushConstants(commandBuffer, m_leafLayout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
}
```

### Shadows with holes, for free

Chapter 37 section 8's casters already go through Chapter 17 section 4's
cut-out caster, which binds the material's set and discards below the
threshold. The leaves now have a picture and a threshold, so their shadows
come out with holes, and nothing in the shadow pass changes.

### Places to look from, and one level for all

The rest of the chapter compares the trees' levels and looks at woods from
set places, so this section adds both. `PropSettings` gains a field that
forces every object to one level:

```cpp
    int32_t forceLevel = -1;     // Chapter 39 section 3: every object at this level; -1, by its size
```

which `Props::Update`'s level line (Chapter 37 section 5) reads. The line sits
inside the `if (!settings.freezeLod)` block, so with **Freeze levels** on
(Chapter 37) the levels stay as they were frozen, forced or not:

```cpp
            object.level = settings.forceLevel >= 0 ? static_cast<uint32_t>(settings.forceLevel)   // Chapter 39 section 3
                                                    : chooseLevel(pixels, object.level);
```

Three places to look from join the views, after `GROUND_VIEWS`: an oak wood
100 to 400 m ahead, where far trees cast their stand-ins (section 4) and the
leaves are read at mip levels 7 to 9 (section 6); a pine wood the same, high
in the west where the pines grow; and the densest wood, from inside. Each is a
`View` as Chapter 37 section 3 wrote it: label, position (x, z), height, yaw
and pitch:

```cpp
// Chapter 39 section 3: places to look at the plants from: an oak wood 100 to 400 m ahead, where far trees
// cast their stand-ins (section 4) and leaves thin (section 6); a pine wood the same, high in the west, where
// the pines grow; and the densest wood, from inside, where plants cost the most.
constexpr std::array<View, 3> PLANT_VIEWS{ {
    { "Treeline", { 1620.0f, 20.0f }, 12.0f, 270.0f, -2.0f },
    { "Pines", { -4080.0f, -360.0f }, 12.0f, 120.0f, -2.0f },
    { "Forest floor", { -400.0f, 700.0f }, 2.0f, 0.0f, -8.0f },
} };
```

The Plants header shows both, after **Leaf-card trees**, the level as radio
buttons:

```cpp
    // Section 3: every object at one level, or each by its size; and places to look at the plants from.
    ImGui::TextUnformatted("Level");
    for (int32_t level = -1; level < 3; ++level)
    {
        ImGui::SameLine();
        ImGui::RadioButton(level < 0 ? "by size" : std::format("{}", level).c_str(), &m_propSettings.forceLevel, level);
    }
    for (const View& view : PLANT_VIEWS)
    {
        if (ImGui::Button(view.label)) { GoTo(view.xz, view.height, view.yaw, view.pitch); }
        ImGui::SameLine();
    }
    ImGui::NewLine();
```

### Run

**Wood** again. The crowns are leaves now: green and full, ragged against the
sky and the grass, with the bark showing inside them. Their shadows are lighter
and ragged, with holes where the sun passes between leaves, where section 2's
were solid blots. The stand-ins far off are the same green as the near crowns.
For the control, set the threshold to 0 in the script's `material_text` and run
the script again: square leaves and square shadows.

## 4. Far trees cast their stand-ins

**This is `Props::ShapeCasters`.** A wood of leaf-card trees is a lot of shadow
triangles. Chapter 37 cast every object shown within 450 m into all four
cascades; for solid cones that was cheap. An oak at LOD0 is 13,806 triangles,
and the cascades see it four times. And far off, cut-out leaves cast nothing
a shadow map can hold.

### Far leaves vanish from the shadow map

The cascades' splits are at 13.1, 29.0, 65.8 and 250 m. A shadow map texel
covers about 0.015, 0.033, 0.076 and **0.287 m** of ground in them. An oak's
card is about 0.42 m across: in the last cascade it covers 1.5 texels, so the
shadow pass reads its picture at mip 9 or 10, where the picture is 2 x 2 or a
single texel and not one texel of it reaches 0.5. Far leaf shadows do not thin,
they vanish, and leave a tree's trunk alone on lit ground. So a plant farther
than **Stand-ins from** (66 m, cascade 2's far split) casts its LOD2 stand-in
instead: a solid ball, which the far cascade can hold. Nearer plants cast
cut-out leaves. Measured from **Treeline** (section 3's view), an oak wood 100
to 400 m off, at the Full preset with the sky off: with **Stand-ins from** at
250 m, the shadows' whole reach, so that no tree casts its stand-in, the far
trees' shadows are faint, a few specks and their trunks; with the stand-ins
from 66 m each tree past it has a solid oval. Over the band where the wood
stands, about 9 % of the pixels are more than 15 % darker with the stand-ins
than with cards to 250 m (the Exit check).

**LOD0 casts LOD1**, off by default, is a cheaper choice for the near ones.
Both only ever point a plant's caster at another of its own levels: the
subsets come in the same order at every level (the contract), so the caster
keeps its submesh index and takes the new level's material.

`Props.h` gains the settings, after `PLANT_FILES`:

```cpp
// Chapter 39 section 4: which of its levels a plant casts its shadow with.
struct PlantShadows
{
    float proxiesFrom = 66.0f;   // metres: a plant farther than this casts its LOD2 stand-in
    bool  coarse      = false;   // a plant at LOD0 casts its LOD1
};
```

the function, at the end of the public part, after `IsPlantMaterial`:

```cpp
    // Chapter 39 section 4: after CollectDraws. Points the casters of plants farther than `proxiesFrom` from
    // `camera` at their LOD2 stand-in, and with `coarse` those at LOD0 at their LOD1.
    void ShapeCasters(glm::vec3 camera, const PlantShadows& shadows, std::vector<scene::DrawItem>& casters) const;
```

and a table from mesh to asset, after `m_meshLevels`:

```cpp
    std::vector<uint32_t>   m_meshAssets;   // Chapter 39 section 4: by mesh index, the asset it belongs to
```

`LoadAsset` fills the table beside `m_meshLevels`, a line each: the first beside
the line that sizes `m_meshLevels`, the second inside the loop over the asset's
levels, beside the line that sets `m_meshLevels[...]`. The second must run
before `LoadAsset` appends the asset to `m_assets` at its end: `m_assets.size()`
is then the new asset's index.

```cpp
    m_meshAssets.resize(m_scene.MeshCount(), NO_ASSET);   // Chapter 39 section 4

        m_meshAssets[asset.meshes[level]] = static_cast<uint32_t>(m_assets.size());   // Chapter 39 section 4
```

and `ShapeCasters` goes at the end of `Props.cpp`, after `SetLeafCards`. It
runs after `CollectDraws`, so Chapter 37's function is untouched, and it
changes only the casters of plants; the houses, rocks, landmarks and Chapter
37's trees cast exactly as before:

```cpp
// Chapter 39 section 4: a plant farther than `proxiesFrom` casts its LOD2 stand-in, and with `coarse` a plant
// at LOD0 casts its LOD1. Each submesh keeps its place (Bark first where the plant has one, then Leaf or Far,
// at every level: the plant-space contract) and takes that level's material. Chapter 37's props, every asset
// before the first plant, cast as they always have.
void Props::ShapeCasters(glm::vec3 camera, const PlantShadows& shadows, std::vector<scene::DrawItem>& casters) const
{
    for (scene::DrawItem& item : casters)
    {
        const uint32_t asset = m_meshAssets[item.mesh];
        if (asset == NO_ASSET || asset < m_firstPlant)
        {
            continue;
        }
        const uint32_t level = m_meshLevels[item.mesh];
        uint32_t       to    = shadows.coarse && level == 0 ? 1u : level;
        if (glm::distance(glm::vec3(item.world[3]), camera) > shadows.proxiesFrom)
        {
            to = 2;
        }
        const std::vector<scene::Submesh>& submeshes = m_scene.GetMesh(m_assets[asset].meshes[to]).data.submeshes;
        if (to != level && item.submesh < submeshes.size())
        {
            item.mesh     = m_assets[asset].meshes[to];
            item.material = submeshes[item.submesh].materialIndex;
        }
    }
}
```

In `Record` it runs inside the props' CPU timing, right after
`CollectDraws`:

```cpp
    m_props.ShapeCasters(m_cameraTransform.translation, m_plantSettings.shadows, m_casters);   // Chapter 39 section 4
```

`PlantSettings` gains the two settings, after `leafCards`:

```cpp
    PlantShadows shadows;                   // section 4: which level each plant casts with
```

### Counting what they cost

The panel shows how many casters there are and how many triangles, the cost
lavapipe can show truthfully. `RegisterProps` keeps each submesh's triangle
count as it adds the meshes (this is its final form; replace its mesh loop's
body):

```cpp
        const scene::MeshData& data = world.GetMesh(mesh).data;
        m_sceneRenderer.AddMesh(data);
        std::vector<uint32_t>& triangles = m_meshTriangles.emplace_back();   // section 4
        for (const scene::Submesh& submesh : data.submeshes)
        {
            triangles.push_back(submesh.indexCount / 3);
        }
```

into two members after the leaf pipelines' (`HorizonDemo.h`):

```cpp
    // Chapter 39 section 4: each submesh's triangles, by mesh, and the casters' this frame.
    std::vector<std::vector<uint32_t>> m_meshTriangles;
    uint64_t                           m_casterTriangles = 0;
```

cleared in `Teardown` (`m_meshTriangles.clear();`, after
`m_leafMaterials.clear();`), and `Record` sums them after the `if
(m_showPlates)` block that adds Chapter 36's plates to `m_draws`. The casters do
not need to wait for the plates, but section 11 sums the camera's draws in
the same place:

```cpp
    // Chapter 39 section 4: how many triangles the casters are, from each submesh's count.
    auto triangles = [&](const std::vector<scene::DrawItem>& items) {
        uint64_t sum = 0;
        for (const scene::DrawItem& item : items)
        {
            if (item.mesh < m_meshTriangles.size() && item.submesh < m_meshTriangles[item.mesh].size())
            {
                sum += m_meshTriangles[item.mesh][item.submesh];
            }
        }
        return sum;
    };
    m_casterTriangles = triangles(m_casters);
```

The Plants header shows them under a separator of their own, with the
switches, after the views:

```cpp
    // Section 4: the casters, how many triangles they are, and which level each plant casts with.
    ImGui::SeparatorText("Shadows");
    ImGui::Text("Casters %zu: %.2f M triangles x %d", m_casters.size(), 1e-6 * static_cast<double>(m_casterTriangles),
                m_shadowSettings.cascadeCount);
    ImGui::Checkbox("LOD0 casts LOD1", &m_plantSettings.shadows.coarse);
    ImGui::SetNextItemWidth(140.0f);   // the panel's width: its longest line, label and all
    ImGui::SliderFloat("Stand-ins from (m)", &m_plantSettings.shadows.proxiesFrom, 0.0f, 250.0f, "%.0f");
```

### Run

**Wood**, and open the Plants header. Near the camera the picture is section
3's. Past 66 m each tree's shadow is a solid oval, its stand-in's, where
section 3's were faint and ragged. Under **Shadows** the header reads **Casters
1316: 0.08 M triangles x 4**, at the Low preset and at Full alike.

The count is of draw items, one per submesh, so a tree is two: its bark and its
leaves. `ShapeCasters` changes which level each plant casts with, never how
many casters there are. On the reference run, the triangles under **Shadows**
were read a few frames after each change, at the terrain's **Full** preset
(chosen in the Terrain header), and each is drawn into four cascades. The
stand-ins take Wood's casters from 0.96 M triangles to 0.08
M, and the Forest floor's, with near trees all round, from 3.30 M to 0.82 M;
there **LOD0 casts LOD1** takes another 0.50 M off. From the viewpoint, 1,000 m
up and above all the island's ground, no object stands within the shadows'
reach, so nothing is cast.

## Checkpoint

**Wood** at one sample: a wood of leaf-card oaks and pines with dappled
shadows near the camera and solid ones past 66 m. Untick **Leaf-card trees**:
Chapter 37's wood comes back, with its shadows. Drag **Stand-ins from** to
250: the casters' triangles grow about twelvefold and the far trees' shadows
fade to their trunks.

---

# Part 2 — Leaves at a distance (sections 5-7)

Part 1's trees look right up close at one sample. Part 2 is about what a
cut-out does as it gets smaller: its edge under MSAA, its leaves as the mip
levels average them away, and what the layers cost. Run it at `--msaa 4` from
section 5 on, and at one sample where a section says so.

## 5. Alpha to coverage

**This is `leafCoverage`.** At one sample a pixel is leaf or not leaf: the
cut is a hard stair-step, and a far crown sparkles as the camera turns, its
leaves a pixel wide, in one frame and out the next. Chapter 18 section 8
solved this for a cut-out under MSAA, and its formula carries over unchanged:
the shader turns alpha's distance from the cutoff into a distance in pixels,
`(α − t) / fwidth(α) + ½`, clamped to 0 to 1, and alpha to coverage keeps that
share of the pixel's samples, so an edge is one pixel wide at any distance.
Section 3's pipeline already has `alphaToCoverage` on under MSAA, but the
shader still writes a step, 0 or 1, so every edge is all or nothing. The
shader gains Chapter 18's formula, above `plantTint`:

```glsl
// Section 5: Chapter 18 section 8's coverage: alpha's distance from the cutoff, in pixels, so that the edge
// is one pixel wide at any distance.
float leafCoverage(float alpha, float cutoff)
{
    return clamp((alpha - cutoff) / max(fwidth(alpha), 1e-4) + 0.5, 0.0, 1.0);
}
```

and the cut uses it when the flag is set (this replaces section 3's cut):

```glsl
    // Sections 3 and 5: the cut. A fragment that covers no sample is thrown away before it is lit.
    float coverage = 1.0;
    if (CUTOUT)
    {
        coverage = (draw.flags & FLAT_COVERAGE) != 0u ? leafCoverage(alpha, cutoff) : step(cutoff, alpha);
        if (coverage <= 0.0)
        {
            discard;
        }
    }
```

The fragment still discards at coverage 0, before the lighting: alpha to
coverage keeps no sample there either, and the discard saves the shading.
Section 3's last line, `outColor = vec4(color, coverage);`, now carries a
share, not just 0 or 1, and the comment above it changes to say so:

```glsl
    // Section 5: with alpha to coverage, the coverage goes out as alpha, and the GPU keeps that share of the
    // pixel's samples.
    outColor = vec4(color, coverage);
```

With many layers the hardware's masks repeat. Two cards at coverage 0.5 over
one pixel: the GPU turns 0.5 into the same pattern for both, say samples 0
and 1 of 4, so the pixel ends half covered, where two independent halves would
cover three of four samples on average. With the sharp formula most pixels
are 0 or 1, so that matters only at edges.

The comparison is a push flag, not another pipeline. `HorizonTypes.h` gains
it after `FLAT_PETALS`:

```c
#define FLAT_COVERAGE 16u    /* section 5: under MSAA, the cut-out's edge as coverage; off, all or nothing */
```

and `BindLeafRun` sets it when the switch is on and there is more than one
sample. Its `const uint32_t flags` line becomes:

```cpp
    uint32_t flags = m_materialFlags[material] | (skyOn ? FLAT_SKY : 0u);
    if (m_plantSettings.alphaToCoverage && m_context.formats.samples != VK_SAMPLE_COUNT_1_BIT)
    {
        flags |= FLAT_COVERAGE;   // section 5
    }
```

`PlantSettings` gains the switch, after `shadows`:

```cpp
    bool         alphaToCoverage = true;    // section 5: under MSAA; greyed at 1x
```

and the Plants header starts Part 2's group after the shadows' slider, with
the switch greyed at one sample, where there is no coverage to give:

```cpp
    // Section 5: greyed at one sample, where there is no coverage to give.
    ImGui::SeparatorText("Leaves at a distance");
    ImGui::BeginDisabled(m_context.formats.samples == VK_SAMPLE_COUNT_1_BIT);
    ImGui::Checkbox("Alpha to coverage", &m_plantSettings.alphaToCoverage);
    ImGui::EndDisabled();
```

### Run

Run with `--msaa 4` and press **Wood**. The leaves' edges are soft now, and the
crowns' outlines against the grass and the sky are smooth. Untick **Alpha to
coverage**: every leaf edge is a stair-step of whole pixels again, at four
samples as at one, because the test keeps or drops all four samples of a pixel
together.

## 6. Leaves that thin out

**This is `coverageScales`.** Walk back from a tree and it gets thinner than
it should: not smaller, sparser, until a far wood is a lattice of twigs. The
leaves have not gone anywhere; measure it before fixing it.

### Walls of leaves

Chapter 35 measured depth on plates set up in front of the viewpoint. This
section does the same for leaves: **leaf plates**, walls of cards facing
`VIEWPOINT`, each wall at one distance, so a card's mip level is set by its
distance alone. A wall d metres away is n x n cards of 1 m with n = d / 12.5,
so every wall is 4.6 degrees and 50 pixels wide at 720p while its cards
shrink: a 1 m card is 12.5, 6.2, 3.1 and 1.6 pixels at 50, 100, 200 and 400 m.
The sampler reads a picture at the mip level where one texel is about one
pixel: log₂ of the texels per pixel (Chapter 15 section 5). The pictures are
1,024 texels across, so a card 12.5 pixels wide is read at level
log₂(1024 / 12.5) = 6.4, and the others at 7.4, 8.4 and 9.4. One row of walls
is the oak's leaves, one the pine's, and one an ash's, a picture of EZ-Tree's
no plant here uses, because it thins the most. The plates are uncropped, so a
wall should be covered by its picture's own kept share.

The constants go after `PLANT_VIEWS` (`HorizonDemo.cpp`):

```cpp
// Chapter 39 section 6: the leaf plates. A row of four walls per picture, standing against the sky seen from
// VIEWPOINT, one at each distance: a wall d metres away is n x n cards of 1 m, n = d / 12.5, so every wall is
// 4.6 degrees wide (50 pixels at 720p) while its cards shrink from 12.5 to 1.6 pixels. The ash's picture is
// no plant's: it is here because it thins the most.
struct LeafRow
{
    const char* material;
    float       elevation;   // degrees above the level, seen from VIEWPOINT
};
constexpr std::array<LeafRow, 3> LEAF_ROWS{ { { "AshLeaf", 16.0f }, { "OakTreeLeaf", 10.0f }, { "PineTreeLeaf", 4.0f } } };
constexpr std::array<float, 4>   LEAF_AZIMUTHS{ -12.0f, -4.0f, 4.0f, 12.0f };       // degrees, as PlatePair's
constexpr std::array<float, 4>   LEAF_DISTANCES{ 50.0f, 100.0f, 200.0f, 400.0f };   // metres, by azimuth
constexpr float                  LEAF_PITCH = glm::radians(10.0f);   // looking at the oak's row from VIEWPOINT
```

`CreateLeafPlates` reads the ash's picture with Chapter 38's
`ImportRgbaImage8` (`#include "PillowFort/UsdImport/UsdImport.h"` joins the
file's `PillowFort/` includes, after `Scene/MeshGenerators.h`), registers it as
a material of the demo's own and describes
it with `DescribeMaterial`, passing the picture: the fourth parameter that
"Scaling it back", below, gives `DescribeMaterial`. Then it finds the trees'
leaf materials by name, and builds the walls of Chapter 35's plate mesh, a
1 m square drawn from both sides. It goes after `BindLeafRun`:

```cpp
// Chapter 39 section 6: the leaf plates. Like Chapter 35's plates, walls that face VIEWPOINT, so a leaf's
// mip level is set by its distance alone: a row of four walls for the ash, the oak and the pine, each wall
// as wide on screen as the others, of cards of 1 m that shrink with distance. The oak's and the pine's are
// the trees' own materials; the ash's picture is read here, as Chapter 38 reads the ground's photographs.
void HorizonDemo::CreateLeafPlates()
{
    m_leafPlates.clear();
    const std::filesystem::path file = executableDirectory() / "Assets" / "Scenes" / "Horizon" / "Plants" / "Textures" / "ash.png";
    usd_import::RgbaImage8 ash;
    if (auto result = usd_import::ImportRgbaImage8(file, ash); !result)
    {
        Log::warning(std::format("No leaf plates: {}", result.message()).c_str());
        return;
    }
    const scene::TextureImage picture{ .name = "ash.png", .width = ash.width, .height = ash.height, .srgb = true,
                                       .pixels = std::move(ash.texels) };
    const uint32_t     texture = m_sceneRenderer.AddTexture(picture);
    const scene::Material material{
        .name             = "AshLeaf",
        .opacityThreshold = 0.5f,
        .baseColorTexture = { .image = texture, .wrapS = scene::TextureWrap::Clamp, .wrapT = scene::TextureWrap::Clamp },
        .opacityTexture   = { .image = texture, .wrapS = scene::TextureWrap::Clamp, .wrapT = scene::TextureWrap::Clamp,
                              .channel = { 0.0f, 0.0f, 0.0f, 1.0f } },
    };
    const uint32_t ashMaterial = m_sceneRenderer.AddMaterial(material);
    DescribeMaterial(ashMaterial, material, &picture, true);

    // Each row's material: the ash's, and the trees' leaves, found by name in the props' scene.
    std::array<uint32_t, LEAF_ROWS.size()> materials{ ashMaterial, UINT32_MAX, UINT32_MAX };
    const scene::Scene& world = m_props.World();
    for (uint32_t i = 0; i < world.MaterialCount(); ++i)
    {
        for (size_t row = 1; row < LEAF_ROWS.size(); ++row)
        {
            if (world.GetMaterial(i).name == LEAF_ROWS[row].material)
            {
                materials[row] = i;
            }
        }
    }
    if (materials[1] == UINT32_MAX || materials[2] == UINT32_MAX)
    {
        Log::warning("No leaf plates: the trees' leaves are not loaded.");
        return;
    }

    // One card, 1 m square, drawn from both sides: Chapter 35's plate, with the whole picture on it.
    scene::MeshData square = scene::makePlane(1.0f, 1.0f, 1);
    square.doubleSided     = true;
    const uint32_t mesh    = m_sceneRenderer.AddMesh(square);
    for (size_t row = 0; row < LEAF_ROWS.size(); ++row)
    {
        const float elevation = glm::radians(LEAF_ROWS[row].elevation);
        for (size_t wall = 0; wall < LEAF_AZIMUTHS.size(); ++wall)
        {
            const float     azimuth = glm::radians(LEAF_AZIMUTHS[wall]);
            const glm::vec3 toward  = { std::cos(elevation) * std::sin(azimuth), std::sin(elevation),
                                        -std::cos(elevation) * std::cos(azimuth) };
            const glm::vec3 right   = glm::normalize(glm::cross(toward, glm::vec3(0.0f, 1.0f, 0.0f)));
            const glm::vec3 up      = glm::cross(right, toward);
            // makePlane lies in XZ facing +Y, with v down the picture along +Z: its x goes right, its normal
            // back toward VIEWPOINT, and its z down the wall, so every picture stands the right way up.
            const glm::mat4 facing(glm::vec4(right, 0.0f), glm::vec4(-toward, 0.0f), glm::vec4(-up, 0.0f),
                                   glm::vec4(0.0f, 0.0f, 0.0f, 1.0f));
            const float distance = LEAF_DISTANCES[wall];
            const int   cards    = static_cast<int>(distance / 12.5f);
            for (int y = 0; y < cards; ++y)
            {
                for (int x = 0; x < cards; ++x)
                {
                    const glm::vec3 centre = VIEWPOINT + toward * distance
                                           + right * (static_cast<float>(x) - 0.5f * static_cast<float>(cards) + 0.5f)
                                           + up * (static_cast<float>(y) - 0.5f * static_cast<float>(cards) + 0.5f);
                    m_leafPlates.push_back({ .world = glm::translate(glm::mat4(1.0f), centre) * facing,
                                             .mesh = mesh, .material = materials[row] });
                }
            }
        }
    }
}
```

A wall's direction is its azimuth, in degrees from straight ahead (−Z, where
`VIEWPOINT` looks) toward +X, and its row's elevation above the level. The
matrix `facing` is written as its columns, and each column is where a local
axis of the plate goes in the world: the plate's x to the wall's right, its
normal, y, back toward the viewpoint, and its z down the wall. `HorizonDemo.h`
declares the function after `BindLeafRun`:

```cpp
    void                 CreateLeafPlates();                                   // Chapter 39: section 6
```

`Setup` calls it right after `CreateLeafPipelines`, before the per-material
table is sized, so the ash's material is in it. It comes after `RegisterProps`
too, so the ash's index follows every scene material:

```cpp
    CreateLeafPlates();                                         // section 6: and the ash's material
```

`Teardown` clears them (`m_leafPlates.clear();`, after
`m_meshTriangles.clear();`), and `Record` adds them to the draws while they
show, right after the `if (m_showPlates)` block, which itself follows Chapter
37's level colours (37 section 5's trap: the level colours index
`m_meshLevels`, which has no plate entries):

```cpp
    if (m_plantSettings.showLeafPlates)   // Chapter 39 section 6: the leaf plates, after the level colours too
    {
        m_draws.insert(m_draws.end(), m_leafPlates.begin(), m_leafPlates.end());
    }
```

`showLeafPlates` is a `PlantSettings` field that this section adds below, with
**Mip fix**; until you have added it, this block does not compile.

`HorizonDemo.h` keeps them after the triangle counts:

```cpp
    // Chapter 39 section 6: the leaf plates.
    std::vector<scene::DrawItem> m_leafPlates;
```

The panel gets **Show leaf plates**, and **Look at them**, which puts the
camera at `VIEWPOINT` looking up at the oak's row (below, with the rest of
this section's controls).

### Measured

With the sky's **Mode** at **Off**, so the walls stand on one flat colour, at
one sample, and **Look at them**: the share of each wall's rectangle that is
leaf, against its picture's kept share at level 0.

| Picture, share at level 0 | 50 m | 100 m | 200 m | 400 m |
| --- | --- | --- | --- | --- |
| ash, 0.157 | 0.152 | 0.078 | 0.000 | 0.000 |

The oak's and the pine's go the same way, later: at 200 m the pine's wall is
nearly gone, and every 400 m wall is. Why: a mip level averages its texels 2 x
2, and an average of leaf and gap is usually a gap. Of four texels, two leaf and
two gap average to 0.5, which still passes; one leaf and three gaps average to
0.25, which does not. Box mips keep the picture's **mean** alpha; they do not
keep the share that is above 0.5, and that share is what the test cuts.

### Scaling it back

The fix scales alpha per mip level by the k that makes the level keep its
level-0 share again. Sort the level's alphas from the most opaque down; the
share s of them (0.157 for the ash) reaches some alpha q. Since alpha × k
reaches 0.5 exactly when alpha reaches q = 0.5 / k, scaling by k = 0.5 / q
keeps exactly that share. q is the **quantile** of the level at 1 − s.

One more thing decides the level's alphas: the sampler does not read texels,
it reads between them, blending the four nearest. At level 8 the oak's 4 x 4
texels pass at 0.375, more than its level 0's 0.256, so a count of texels
says the leaves grew denser; read the way the sampler reads, at points spread
across the level, only 0.179 of it passes. So `coverageScales` reads each
level at 127 x 127 points, blended from the four texels round each point, and
takes the quantile of those readings. Worked: the ash at level 7, 8 x 8 texels:
the top 15.7 % of the readings reach 0.403, so k = 0.5 / 0.403 = 1.24.

> **Jump:** a quantile is the value a given share of a list lies above; the
> median is the quantile at a half. Keep in mind what k is: not a brightening,
> but a choice of how much of a smeared picture to call leaf, made so that the
> answer's share is the original's.

It builds the levels as the GPU's blits do, each texel the rounded average of
the 2 x 2 above it in 8 bits (Chapter 15 section 5), and finds the quantile
with `std::nth_element`, which places the n-th largest without sorting the
rest. Level 0 keeps k = 1: the picture as drawn. A level too small for the
share to hold one texel (the ash's 1 x 1, level 10) keeps the level above's k,
and every k is held between 0.25 and 4, so that a level with almost nothing
left is not blown up into blocks. It is a file-scope function above the
namespace block, after Chapter 35's `stepsApart` and before Chapter 37's
`smoothed` (section 7's `clearColorAttachment` goes in the same place, ahead of
it), and it uses `std::greater<>`, so `<functional>` joins the standard
includes, after `<format>`:

```cpp
// File scope, above the namespace block. Chapter 39 section 6: why a cut-out's leaves thin with distance,
// and the scale that keeps them. At level 0 a share of the picture's texels, `share`, have an alpha at the
// cutoff or above. Each mip level below averages the 2 x 2 texels above it, rounded to 8 bits as the blits
// round, and an average of leaf and gap is usually a gap, so a smaller share passes. The sampler reads a
// level between its texels, so the level is read here as the sampler reads it: at 127 x 127 points across
// it, each blended from the four texels round it (127 is odd, so the points land at every offset between
// texels, and not only halfway). Sorted from the most opaque down, those readings reach some alpha q at the
// level-0 share: scaled by k = cutoff / q, that share passes again. A level too small for the share to hold
// one texel keeps the level above's k. Twelve entries, for mip levels 0 to 11.
static std::array<float, 12> coverageScales(const pf::scene::TextureImage& image, float cutoff, float& share)
{
    uint32_t             width  = image.width;
    uint32_t             height = image.height;
    std::vector<uint8_t> alpha(static_cast<size_t>(width) * height);
    for (size_t i = 0; i < alpha.size(); ++i)
    {
        alpha[i] = image.pixels[4 * i + 3];
    }
    const auto passes = std::count_if(alpha.begin(), alpha.end(), [&](uint8_t a) { return a >= cutoff * 255.0f; });
    share = static_cast<float>(passes) / static_cast<float>(alpha.size());

    std::array<float, 12> scales{};
    for (uint32_t level = 0; level < scales.size(); ++level)
    {
        const size_t kept = static_cast<size_t>(std::lround(share * static_cast<float>(alpha.size())));
        if (level == 0)
        {
            scales[level] = 1.0f;   // the picture as it was drawn
        }
        else if (kept >= 1)
        {
            // The level as the sampler reads it, clamped at the picture's edges, as the leaves' sampler is.
            constexpr uint32_t POINTS = 127;
            const auto texel = [&](float x, float y) {
                const auto tx = static_cast<uint32_t>(std::clamp(x, 0.0f, static_cast<float>(width - 1)));
                const auto ty = static_cast<uint32_t>(std::clamp(y, 0.0f, static_cast<float>(height - 1)));
                return static_cast<float>(alpha[static_cast<size_t>(ty) * width + tx]) / 255.0f;
            };
            std::vector<float> readings;
            readings.reserve(POINTS * POINTS);
            for (uint32_t j = 0; j < POINTS; ++j)
            {
                for (uint32_t i = 0; i < POINTS; ++i)
                {
                    const float x  = (static_cast<float>(i) + 0.5f) / POINTS * static_cast<float>(width) - 0.5f;
                    const float y  = (static_cast<float>(j) + 0.5f) / POINTS * static_cast<float>(height) - 0.5f;
                    const float x0 = std::floor(x);
                    const float y0 = std::floor(y);
                    readings.push_back(glm::mix(glm::mix(texel(x0, y0), texel(x0 + 1.0f, y0), x - x0),
                                                glm::mix(texel(x0, y0 + 1.0f), texel(x0 + 1.0f, y0 + 1.0f), x - x0), y - y0));
                }
            }
            const size_t n = std::max<size_t>(static_cast<size_t>(std::lround(share * POINTS * POINTS)), 1);
            std::nth_element(readings.begin(), readings.begin() + static_cast<std::ptrdiff_t>(n - 1), readings.end(),
                             std::greater<>());
            scales[level] = std::clamp(cutoff / std::max(readings[n - 1], 1e-6f), 0.25f, 4.0f);
        }
        else
        {
            scales[level] = level > 0 ? scales[level - 1] : 1.0f;
        }

        // The next level: each texel the rounded average of the ones above it, 2 x 2, or 2 x 1 once a side is 1.
        const uint32_t nextWidth  = std::max(width / 2, 1u);
        const uint32_t nextHeight = std::max(height / 2, 1u);
        std::vector<uint8_t> next(static_cast<size_t>(nextWidth) * nextHeight);
        for (uint32_t y = 0; y < nextHeight; ++y)
        {
            for (uint32_t x = 0; x < nextWidth; ++x)
            {
                uint32_t sum   = 0;
                uint32_t count = 0;
                for (uint32_t dy = 0; dy < std::min(height, 2u); ++dy)
                {
                    for (uint32_t dx = 0; dx < std::min(width, 2u); ++dx)
                    {
                        sum += alpha[static_cast<size_t>(std::min(2 * y + dy, height - 1)) * width + std::min(2 * x + dx, width - 1)];
                        ++count;
                    }
                }
                next[static_cast<size_t>(y) * nextWidth + x] = static_cast<uint8_t>((sum + count / 2) / count);
            }
        }
        alpha  = std::move(next);
        width  = nextWidth;
        height = nextHeight;
    }
    return scales;
}
```

`DescribeMaterial` calls it for every cut-out with a picture, keeps the table
in the material's `LeafMaterial`, and logs a line: the kept share at level 0
and k by level. It takes the picture as a fourth parameter. Replace its
declaration in `HorizonDemo.h`:

```cpp
    void                 DescribeMaterial(uint32_t material, const scene::Material& source,
                                          const scene::TextureImage* picture, bool plant);   // Chapter 39: sections 3, 6
```

In the definition, the last line of section 3's comment gains a sentence and the
signature the parameter:

```cpp
// cut out. Section 6: a cut-out's k for every mip level, from its picture, with a line in the log.
void HorizonDemo::DescribeMaterial(uint32_t material, const scene::Material& source, const scene::TextureImage* picture,
                                   bool plant)
```

The body is section 3's as it was; after its last line,
`leaf.cutout = source.opacityThreshold > 0.0f;`, and before the closing brace,
comes the rest of the function:

```cpp
    if (!leaf.cutout || picture == nullptr)
    {
        return;
    }

    // Section 6: k per level, and in the log the share of texels kept at level 0 and k by level.
    float share = 0.0f;
    const std::array<float, 12> scales = coverageScales(*picture, source.opacityThreshold, share);
    std::string table;
    for (uint32_t level = 0; level < scales.size(); ++level)
    {
        leaf.mipScale[level / 4][level % 4] = scales[level];
        table += std::format(" {:.2f}", scales[level]);
    }
    Log::info(std::format("{}: {:.1f} % of texels kept at level 0; k by level{}", source.name, 100.0f * share, table).c_str());
```

`RegisterProps` passes the material's opacity picture; the body of its
material loop, section 3's, becomes (the mesh loop, section 4's, stays):

```cpp
        const scene::Material& source  = world.GetMaterial(material);
        const uint32_t         picture = source.opacityTexture.image;
        DescribeMaterial(m_sceneRenderer.AddMaterial(source), source,
                         picture != scene::NO_TEXTURE ? &world.GetTexture(picture) : nullptr,
                         m_props.IsPlantMaterial(material));
```

`LeafMaterial` keeps the table, one more field after `cutout`:

```cpp
        std::array<glm::vec4, 3> mipScale{ glm::vec4(1.0f), glm::vec4(1.0f), glm::vec4(1.0f) };   // section 6
```

`HorizonTypes.h` gains the flag after `FLAT_COVERAGE`:

```c
#define FLAT_MIP_FIX  32u    /* section 6: alpha scaled for the mip level the leaf is read at */
```

and `BindLeafRun` sets it while the switch is on, after section 5's
`FLAT_COVERAGE`, and pushes the table in `LeafDraw`; its `push` becomes:

```cpp
    if (m_plantSettings.mipFix)
    {
        flags |= FLAT_MIP_FIX;    // section 6
    }

    const LeafPush push{
        .flat = { .baseColor = m_materialColors[material],
                  .sky       = glm::vec4(FALLBACK_SKY, m_terrainSettings.hazeDistance),
                  .flags     = flags },
        .leaf = { .mipScale = { leaf.mipScale[0], leaf.mipScale[1], leaf.mipScale[2] } },
    };
```

The log, with the plants loaded:

```text
OakTreeLeaf: 25.6 % of texels kept at level 0; k by level 1.00 0.97 0.92 0.92 0.92 0.94 0.98 1.05 1.16 1.76 1.76 1.76
PineTreeLeaf: 22.9 % of texels kept at level 0; k by level 1.00 0.93 0.91 0.93 0.95 0.95 1.00 1.12 1.34 1.65 1.65 1.65
BushLeaf: 25.6 % of texels kept at level 0; k by level 1.00 0.97 0.92 0.92 0.92 0.94 0.98 1.05 1.16 1.76 1.76 1.76
FernLeaf: 14.4 % of texels kept at level 0; k by level 1.00 1.03 1.01 1.12 1.33 1.40 1.60 2.07 2.31 2.31 2.31 2.31
FlowerHead: 40.5 % of texels kept at level 0; k by level 1.00 1.01 1.00 0.99 0.96 0.98 1.11 1.18 1.18 1.18 1.18 1.18
AshLeaf: 15.7 % of texels kept at level 0; k by level 1.00 1.00 0.98 0.93 0.92 0.93 1.04 1.24 1.48 2.28 2.28 2.28
```

### In the shader

`Leaf.frag.glsl` asks the sampler which level it reads, beside the read,
before anything can branch. The read becomes:

```glsl
    // Read first, while every pixel of the 2 x 2 quad still runs (Chapter 38 section 6): the picture, and the
    // mip level the sampler reads it at.
    vec4  texel = texture(baseColorTexture, uv);
    float level = textureQueryLod(baseColorTexture, uv).x;
```

and the shader scales alpha by the table, read between its two nearest whole
levels as the sampler blends two levels. `mipScale` goes above `leafCoverage`:

```glsl
// Section 6: k for this mip level: LeafDraw's table, read between its two nearest whole levels, as the
// sampler reads between two mip levels.
float mipScale(float level)
{
    float l = clamp(level, 0.0, 11.0);
    uint  i = uint(l);
    uint  j = min(i + 1u, 11u);
    return mix(leaf.mipScale[i / 4u][i % 4u], leaf.mipScale[j / 4u][j % 4u], l - float(i));
}
```

and the scale right after the line that takes `alpha`, before
`float cutoff`:

```glsl
    if ((draw.flags & FLAT_MIP_FIX) != 0u)
    {
        alpha *= mipScale(level);
    }
```

Under alpha to coverage the scaled alpha feeds `leafCoverage`, so the fix
holds at four samples too. The shadow pass reads the pictures through the
engine's caster shader, which has no such scale; section 4's stand-ins are
why it does not need one past 66 m.

`PlantSettings` gains the switches, after `alphaToCoverage`:

```cpp
    bool         mipFix          = true;    // section 6: alpha scaled per mip level
    bool         showLeafPlates  = false;   // section 6: the walls of cards that measure it
```

and the Plants header, after **Alpha to coverage**: **Mip fix** on the same line,
then the plates and the button that looks at them (the first two lines are
section 5's, shown to place the rest; `rotationFromYawPitch` is Chapter 10
section 6's, as Chapter 36's viewpoint uses it):

```cpp
    ImGui::Checkbox("Alpha to coverage", &m_plantSettings.alphaToCoverage);
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::Checkbox("Mip fix", &m_plantSettings.mipFix);
    ImGui::Checkbox("Show leaf plates", &m_plantSettings.showLeafPlates);
    ImGui::SameLine();
    if (ImGui::Button("Look at them"))
    {
        m_cameraTransform.translation = VIEWPOINT;
        m_cameraTransform.rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = LEAF_PITCH });
    }
```

### Run

Set the sky's **Mode** to **Off**, run at one sample (no `--msaa`), open the
Plants header, tick **Show leaf plates** and press **Look at them**. Three rows
of four walls, ash at the top, then oak, then pine, at 50, 100, 200 and 400 m
from left to right, each as wide on screen as the others. With **Mip fix** on,
each row holds its density from the 50 m wall to the 200 m one; the 400 m walls
are sparse, the oak's about half as dense as its 50 m wall and the pine's about
a quarter, and the ash's is gone. Untick **Mip fix**: the walls thin as they
go, the 200 m oak and pine walls to a scatter of dots (the pine's a few) and
the ash's to nothing, and every 400 m wall is gone. Measured as before, with
the fix:

| Picture, share at level 0 | 50 m | 100 m | 200 m | 400 m |
| --- | --- | --- | --- | --- |
| ash, 0.157 | 0.175 | 0.174 | 0.151 | 0.000 |

The oak's and the pine's walls hold too: the 50 to 200 m walls of all three are
within 15 % of their picture's share, from 13 % under (the pine's 200 m wall) to
14 % over (its 50 m wall). At 400 m a card is about 1.6 pixels wide and is read
at levels 9 and 10, where the picture is 2 x 2 texels or a single one: the
leaves are averaged into four values or one, and no scale can bring the leaves'
share back out of an average that coarse. That is where a plant must stop being
cards (Chapter 40). Set the sky back and press **Treeline**. An oak wood from
100 to 400 m ahead, the sea beyond it: the crowns keep their mass all the way
back, with no lattice of twigs, and the far ones are the same green as the near.

## 7. Counting layers

**This is the overdraw view.** A crown is cards over cards. Every card a pixel
sees is a fragment the GPU starts, and most are thrown away: a fragment shader
runs for each before the discard. The cost of a wood is how many layers each
pixel draws, and how many it keeps. Count them.

The count is another mode of the same pipelines, with three differences from
the cut-out mode: no depth write, so that a counted layer does not hide the
next; additive blending (Chapter 21 section 5), so that each layer adds to the
pixel; and no alpha to coverage, which would scale the count (the pipeline's
`mode == 1` test already leaves it off for the new mode). It keeps the same
GREATER test, so a hill still hides what stands behind it. `Leaf.frag.glsl`
gains the constant `OVERDRAW`, after `CUTOUT`, and `LAYER` after the
`outColor` declaration:

```glsl
layout(constant_id = 1) const bool OVERDRAW = false;   // section 7: count layers instead of shading them

// Section 7: what one layer adds to the overdraw view's red (drawn) and green (kept).
const float LAYER = 1.0 / 64.0;
```

In the overdraw mode the shader returns early with one layer's worth of
colour, red for every layer drawn and green as well for every layer the cut
would keep, tested on the scaled alpha as the cut tests it. The block goes in
place of the line `float cutoff = material.opacityThreshold;`, which it
carries:

```glsl
    // Section 7: one layer drawn in red; in green too if it would be kept, below the test, as the shading.
    float cutoff = material.opacityThreshold;
    if (OVERDRAW)
    {
        bool kept = cutoff <= 0.0 || alpha >= cutoff;
        outColor  = vec4(LAYER, kept ? LAYER : 0.0, 0.0, 1.0);
        return;
    }
```

`CreateLeafPipelines` makes the third mode. Its constants become two, in place
of section 3's `Constants` and `entries`:

```cpp
    // Leaf.frag.glsl's two constants, CUTOUT and OVERDRAW (Chapter 15 section 11's way).
    struct Constants
    {
        VkBool32 cutout;
        VkBool32 overdraw;
    };
    const std::array<VkSpecializationMapEntry, 2> entries{ {
        { .constantID = 0, .offset = offsetof(Constants, cutout), .size = sizeof(VkBool32) },
        { .constantID = 1, .offset = offsetof(Constants, overdraw), .size = sizeof(VkBool32) },
    } };
```

the mode loop runs to 3, and its first line sets both:

```cpp
        for (uint32_t mode = 0; mode < 3; ++mode)   // 0 opaque, 1 cut out, 2 overdraw
        {
            const Constants            values{ mode == 1 ? VK_TRUE : VK_FALSE, mode == 2 ? VK_TRUE : VK_FALSE };
```

and in the pipeline's description, `.depthWrite` becomes the first difference,
and the second is a `.blend` line, right after `.dynamicStates` and before
`.fragmentSpecialization` (the description's fields go in the order
`GraphicsPipelineDesc` declares them):

```cpp
                .depthWrite             = mode != 2,   // section 7: counting hides nothing behind it

                .dynamicStates          = dynamicStates,
                .blend                  = mode == 2 ? BlendMode::Additive : BlendMode::Opaque,
```

In the overdraw view every run counts, flat ones included, so the batch
lambda sends every run to `BindLeafRun`, and `BindLeafRun` picks mode 2. The
lambda's test and `BindLeafRun`'s `mode` line become:

```cpp
        // Chapter 39 section 3: a plant's run through the leaf pipelines, not the understory's; section 7: every
        // run, to count.
        if (m_leafMaterials[run.material].plant || m_plantSettings.overdraw)

    const uint32_t      mode = m_plantSettings.overdraw ? 2u : leaf.cutout ? 1u : 0u;
```

The count starts from black. The terrain is drawn first, for its depth, so
that the ground still hides what stands behind a hill; then its colour is
wiped to black, inside the scene pass. A clear inside a rendering scope is
`vkCmdClearAttachments`, as Chapter 35 section 6 cleared depth, and needs no
barrier: clears and draws in one scope happen in rasterization order. The
clear is a file-scope function above the namespace block, after `stepsApart`
and so before section 6's `coverageScales`:

```cpp
// File scope, above the namespace block. Chapter 39 section 7: the colour attachment set to one colour
// everywhere, from inside the rendering scope, as clearDepth sets the depth.
static void clearColorAttachment(VkCommandBuffer commandBuffer, VkExtent2D extent, const VkClearColorValue& color)
{
    const VkClearAttachment attachment{
        .aspectMask      = VK_IMAGE_ASPECT_COLOR_BIT,
        .colorAttachment = 0,
        .clearValue      = { .color = color },
    };
    const VkClearRect rect{ .rect = { { 0, 0 }, extent }, .baseArrayLayer = 0, .layerCount = 1 };
    vkCmdClearAttachments(commandBuffer, 1, &attachment, 1, &rect);
}
```

and `Record` calls it after the terrain's timestamp:

```cpp
    // Chapter 39 section 7: the overdraw view counts into black: what the terrain hides is still hidden, by
    // its depth, which stays.
    if (m_plantSettings.overdraw)
    {
        clearColorAttachment(commandBuffer, extent, VkClearColorValue{ { 0.0f, 0.0f, 0.0f, 1.0f } });
    }
```

### Reading it

One layer adds 1/64 to red; the tone curve **Raw** (Chapter 16 section 6)
clamps, and the composite encodes sRGB, so a count reads through the sRGB
curve. Worked: 4 layers are 4/64 = 0.0625, and 1.055 × 0.0625^(1/2.4) − 0.055
= 0.277, which is 71 of 255. One layer reads 34, 16 read 137, 64 read 255.
The panel prints the key while the view is on, after **Look at them**:

```cpp
    ImGui::Checkbox("Overdraw", &m_plantSettings.overdraw);
    if (m_plantSettings.overdraw)
    {
        ImGui::TextUnformatted("Red drawn, green kept, 1/64 a layer");
        ImGui::TextUnformatted("Raw (clamp): 1 34, 4 71, 16 137, 64 255");
    }
```

`PlantSettings` gains the switch, after `showLeafPlates`:

```cpp
    bool         overdraw        = false;   // section 7: layers drawn and kept, in place of the picture
```

Red counts every card fragment in front of the ground, as if nothing hid
anything: an upper bound on what the real pass shades. With depth writes on,
the GPU may test a fragment's depth before running its shader, the **early
depth test**, and skip the shader of a fragment behind a leaf already written.
A shader that can discard still gets that test; only its own depth write
waits until the shader has decided to keep the fragment.

### Run

**Wood**, at one sample, with **Overdraw** on. The frame is black but for the
plants: crowns from orange to yellow, brightest where crowns overlap at the
wood's far edge, many layers drawn and fewer kept; trunks a dim olive, one
layer drawn and kept, so red and green alike; and the stand-ins far off olive
too.

Measured on screenshots, at one sample, Low, 720p, with **Understory** off, so
that only the trees are counted, over the pixels with a layer drawn, in
**Wood** and on the **Forest floor** (the boxes and the table are in
`REFERENCE.md`'s row for this chapter): a leaf-card crown draws five to nine
times the layers of a solid one, and keeps about two in five of them; a solid
tree keeps every layer it draws. The crop saves 29 % of the layers drawn in
**Wood** (the uncropped cards draw 40 % more) and 30 % on the Forest floor, and
changes almost nothing that is kept. A count reaching 64 shows as full red, so
the means are a little low.

## Checkpoint

At `--msaa 4`: **Wood** with soft leaf edges, and with **Alpha to coverage**
off, hard ones. **Show leaf plates** and **Look at them**: the walls hold to
200 m with **Mip fix**, and thin without it. **Overdraw** in **Wood** and in
**Forest floor**: the crowns orange and yellow, the ground black.

---

# Part 3 — The understory (sections 8-10)

The trees stand in Chapter 37's pool. The plants under them are far more
numerous and far smaller, and live only near the camera: Part 3 grows three of
them, decides from Chapter 38's map where each may grow, lets the GPU plant
them every frame and count them, and draws what it counted.

## 8. Three small plants, and where they grow

**This is `Understory.glsl`.** First the plants, from the same script; then
the rule for where each grows, seen in false colours on the terrain before
anything is planted.

### A fern, a flower and a bush

- **The fern** is nine fronds from one point, at 40 to 70 degrees, drooping by
  a negative force. The stub they leave from is grown, so that the fronds have
  a place and a frame to start from, but it is not drawn: its order has no
  shape (`shape=None`, which `mesh_level` skips), so the fern is the one plant
  with no bark. A frond is not a tube but a **ribbon**: a flat strip along the
  branch, a quad a section, with one picture of a whole frond on it, 0.25 m
  wide and narrowing to its tip; 0.9 m tall. LOD1 keeps every second frond
  through every third section; its LOD2 is LOD1 again, since a fern far away
  is not drawn at all.
- **The flower** is a stem, a thin tube of 3 sections and 4 sides, with two
  blades (ribbons in the stem's colour) and a head of two cards: a crossed
  pair and, at LOD0, a flat one tilted 25 degrees, three quads (the script's
  counts, section 2's "cards", count a crossed pair once: two at LOD0, one
  at LOD1); 0.4 m tall.
  `FLAT_PETALS` gives each flower one of three petal colours (section 3's
  `plantTint`).
- **The bush** is EZ-Tree's `bush_1`, cut down: eight stems of three twigs,
  crossed cards of `oak.png` with a lighter, yellower tint, 1.4 m tall.

`ribbon` meshes a frond or a blade: two points across each section, `width`
apart along the frame's side, narrowing toward the tip, facing the frame's
front, with t = 0 at its base as a card's.

The fern's frond and the flower's head are pictures the script draws itself:
`fern.png`, 256 x 1024, a stem and 24 pairs of leaflets that lengthen to a
third of the way up and shorten to the tip; `flower.png`, 256 x 256, five
white petals round a golden middle. Each is painted from strokes, its alpha
falling from 1 to 0 over two texels across every edge, so that no mip level
sees a hard step, and written by a PNG writer of ten lines (`write_png`:
`zlib` and `struct`, in the script).

**Colour under transparency.** A clear texel still has a colour, and the mip
levels average it in. Worked: a mip texel over two clear black texels and two
leaf texels of (66, 108, 44), picture bytes in sRGB, averages in linear light,
as the GPU's blits average an sRGB picture, to (46, 77, 29): a third darker,
and that darkened texel sits on the leaf's edge, where alpha is around the
cutoff. So the script fills every clear texel with the mean colour of the
leaf, and the edges keep their colour at every level (the last lines of
`paint`). EZ-Tree's pictures do the same with one green, (71, 112, 76), under
every clear texel.

`--black-fill` is the control: black under the clear texels, and dark rims on
the ferns from 20 m on.

The demo needs nothing new to load them: `PLANT_FILES` named all five in
section 1, and their materials are plants' and cut out like the trees'.

### Where they grow

Each kind has a **chance** on every patch of ground: the share of the cells
there that grow it. It comes from what the ground is made of (Chapter 38's
six weights, w), how much forest stands on it (f, Chapter 37's
`forestDensity`, 0 to 1) and how steep it is. Three helpers first:

- **rootable** = w_grass + w_soil + w_scree, at most 1: nothing roots on sand,
  rock or snow, and everything below is scaled by it or by a weight that is
  part of it.
- **edge(w)** = 4w(1 − w): 1 where a weight is a half, falling to 0 where it
  is all of the ground and where it is none. Worked: at w = 0.9 it is
  4 × 0.9 × 0.1 = 0.36.
- **smoothstep(a, b, x)** (Chapter 16 section 5): 0 up to a, 1 from b on, an
  S-shaped rise between.

Then the three rules:

$$
\begin{aligned}
\text{fern} &= 0.5\,\max\!\big(w_\text{soil},\ 0.6\,\operatorname{smoothstep}(0.3, 0.7, f)\,\text{rootable}\big)\\
\text{flower} &= 0.4\,w_\text{grass}\,(1 - f)\,\text{drift}\\
\text{bush} &= 0.35\,\max\!\big(\operatorname{edge}(w_\text{scree}),\ \operatorname{edge}(f)\,\text{rootable}\big)
\end{aligned}
$$

where **drift**, the meadows that flower, is smoothstep(0.45, 0.7, n) of value
noise n at 25 m (Chapter 37's `valueNoise`, shifted off the forest's
lattice). Ferns are plants of damp soil and of shade, so the fern takes the
soil itself, or the forest once it is well established; flowers want open
grass, so the forest takes them away as it thickens. A bush grows where two
grounds meet: at the scree's edge and at the forest's. That is why the bush
takes `edge` and the others do not: a fern in the deep wood and a flower in
the open meadow grow best where their ground is purest, a bush where its
ground is half one thing and half another. Worked, one number a kind:

- a fern by a stream, soil 0.8 and no forest: 0.5 × max(0.8, 0) = 0.4, two
  cells in five; on the forest floor, f = 1 on grass, rootable 1:
  0.5 × max(0, 0.6 × 1 × 1) = 0.3;
- a flower in a drift on open grass, grass 0.95, f = 0, drift 1:
  0.4 × 0.95 × 1 × 1 = 0.38;
- a bush at the scree's edge, scree 0.5: 0.35 × edge(0.5) = 0.35 × 1 = 0.35;
  at the forest's edge on grass, f = 0.5: 0.35 × edge(0.5) × 1 = 0.35; deep
  in the wood, f = 1: edge(1) = 0, no bush.

Last, the slope. `groundSlope` reads the heightmap's level 0 two texels either
side of the place, along x and along z, as `forestDensity` does: a **central
difference**, dx = (h(x + 2 texels) − h(x − 2 texels)) / (4 texels), and dz
the same; the slope s = √(dx² + dz²) is metres up per metre across. Worked:
the ground 8 m higher 16 m east than 16 m west, and level north to south:
dx = 8 / 32 = 0.25, dz = 0, s = 0.25, about 14 degrees. All three chances are
multiplied by **gentle** = 1 − smoothstep(0.6, 1.0, s): unchanged up to
s = 0.6 (31 degrees), half at s = 0.8, and nothing past s = 1 (45 degrees).
The material map alone does not keep plants off the steep: on 9 % of the
island's land the slope passes 0.6, and most of that is still grass, soil or
scree on the map.

If the three chances add up to more than 1 they are scaled down to 1: section
9 lays them end to end from 0 and picks a kind by where a random number falls
among them. They are returned, and the kinds numbered, in one order: 0 a fern,
1 a flower, 2 a bush. It is an include with no bindings, as
`ForestDensity.glsl` is, because two shaders use it: the terrain's view below,
and section 9's pass. Its includer must have included `GroundMaterials.glsl`
first: that file gives it the six materials' order (`GRASS`, `SOIL`, `SCREE`)
and, through its own include of `ForestDensity.glsl`, `valueNoise`, `texelOf`
and `texelHeight`:

```glsl
// Shaders/Horizon/Understory.glsl - Chapter 39 section 8: where the small plants grow: the chance of a fern,
// a flower and a bush on a patch of ground, from what it is made of (Chapter 38), how much forest stands on
// it (Chapter 37 section 6) and how steep it is. An include with no bindings, as ForestDensity.glsl: the
// terrain's Show understory view reads it, and section 9's generate pass plants by it. The includer has
// included GroundMaterials.glsl first, for the materials' order, and through it ForestDensity.glsl's
// valueNoise, texelOf and texelHeight.
#ifndef PF_HORIZON_UNDERSTORY_GLSL
#define PF_HORIZON_UNDERSTORY_GLSL

// The most each kind may have on any one patch of ground.
const float FERN_CHANCE   = 0.5;    // by the streams, and in the forest's shade
const float FLOWER_CHANCE = 0.4;    // in drifts, on open grass
const float BUSH_CHANCE   = 0.35;   // along the scree's edge, and the forest's

// The flowers' drifts: patches about this many metres across, from value noise shifted so that its lattice
// is not the forest's.
const float DRIFT_SIZE = 25.0;

// The plants' false colours in Show understory, linear: the fern's teal, so that it does not read as grass.
const vec3 FERN_FALSE   = vec3(0.05, 0.45, 0.6);
const vec3 FLOWER_FALSE = vec3(0.9, 0.8, 0.1);
const vec3 BUSH_FALSE   = vec3(0.6, 0.3, 0.1);

// How steep the ground is at xz, metres up for every metre across: forestDensity's four texels, two either
// side, from level 0 of the heightmap (Chapter 37 section 6).
float groundSlope(sampler2D heights, vec4 map, vec2 xz)
{
    float texelSize = map.x / float(textureSize(heights, 0).x);
    ivec2 texel     = texelOf(xz, map.x, textureSize(heights, 0).x);
    float dx = (texelHeight(heights, map, texel + ivec2(2, 0)) - texelHeight(heights, map, texel - ivec2(2, 0))) / (4.0 * texelSize);
    float dz = (texelHeight(heights, map, texel + ivec2(0, 2)) - texelHeight(heights, map, texel - ivec2(0, 2))) / (4.0 * texelSize);
    return sqrt(dx * dx + dz * dz);
}

// The strength of an edge: 4w(1 - w) is 1 where a material's weight is a half, and falls to 0 both where it
// is all of the ground and where it is none of it.
float edge(float w)
{
    return 4.0 * w * (1.0 - w);
}

// The chance of a fern (x), a flower (y) and a bush (z) where the ground has the weights w, `forest` of
// forest, and the slope `slope`. Nothing roots on sand, rock or snow; nothing grows on the steep; and if the
// three would add up to more than 1, they are scaled down to 1.
vec3 understoryChance(float w[6], float forest, float slope, vec2 xz)
{
    float rootable = clamp(w[GRASS] + w[SOIL] + w[SCREE], 0.0, 1.0);
    float gentle   = 1.0 - smoothstep(0.6, 1.0, slope);
    float drift    = smoothstep(0.45, 0.7, valueNoise(xz / DRIFT_SIZE + vec2(31.7, -12.3)));
    float fern     = FERN_CHANCE * max(w[SOIL], 0.6 * smoothstep(0.3, 0.7, forest) * rootable);
    float flower   = FLOWER_CHANCE * w[GRASS] * (1.0 - forest) * drift;
    float bush     = BUSH_CHANCE * max(edge(w[SCREE]), edge(forest) * rootable);
    vec3  chance   = gentle * vec3(fern, flower, bush);
    float total    = chance.x + chance.y + chance.z;
    return total > 1.0 ? chance / total : chance;
}

// Show understory: each kind's false colour by its chance, over the ground as it was, stronger where more
// grows; where nothing can grow, the ground unchanged.
vec3 understoryFalseColor(vec3 color, vec3 chance)
{
    float total = chance.x + chance.y + chance.z;
    if (total <= 0.0)
    {
        return color;
    }
    vec3 kinds = (chance.x * FERN_FALSE + chance.y * FLOWER_FALSE + chance.z * BUSH_FALSE) / total;
    return mix(color, kinds, min(2.0 * total, 1.0));
}

#endif
```

### Show understory

The terrain draws the chances as false colours over the ground, as **Show
materials** draws the weights: fern teal, flower yellow, bush brown, mixed by
their chances and stronger where more grows, the ground unchanged where
nothing can. The fern is teal, not green, so that it does not read as grass.
`HorizonTypes.h` takes the next free bit of the terrain's flags, bit 9 (512):

```c
#define TERRAIN_SHOW_UNDERSTORY 512u   /* Chapter 39 section 8: where the small plants may grow, in false colours */
```

`Terrain.frag.glsl` includes the file after `GroundMaterials.glsl`, which it
needs (the include list's last line):

```glsl
#include "Understory.glsl"        // Chapter 39 section 8: where the small plants grow
```

and paints it on land only, after the **Show materials** block and before the
**Show reads** one:

```glsl
    // Chapter 39 section 8: where the small plants may grow, by the chances the understory plants with.
    if ((terrain.flags & TERRAIN_SHOW_UNDERSTORY) != 0u && groundHeight >= 0.0)
    {
        float forestHere = forestDensity(heightmap, terrain.heightmap, worldPosition.xz);
        float slope      = groundSlope(heightmap, terrain.heightmap, worldPosition.xz);
        color = understoryFalseColor(color, understoryChance(w, forestHere, slope, worldPosition.xz));
    }
```

`TerrainSettings` gains the switch, after `showReads`:

```cpp
    bool showUnderstory = false;    // Chapter 39 section 8: where the small plants may grow, in false colours
```

`Terrain::Record` sets the flag among its flags, after Chapter 38's `showReads`
line (section 9 moves these lines, with the rest of `Record`'s push constants,
into a function of their own):

```cpp
    if (ground && settings.showUnderstory) { flags |= TERRAIN_SHOW_UNDERSTORY; }   // Chapter 39 section 8
```

The switch is a terrain setting, but it belongs with the plants, so the Plants
header shows it, in a group of Part 3's after the overdraw view, with its key
while it is on:

```cpp
    // Section 8: where the small plants may grow, painted by the terrain, and its key.
    ImGui::SeparatorText("Understory");
    ImGui::Checkbox("Show understory", &m_terrainSettings.showUnderstory);
    if (m_terrainSettings.showUnderstory)
    {
        ImGui::TextUnformatted("Fern teal, flower yellow, bush brown");
    }
```

### Run

Open the **Ground** header and press **Stream**; open Plants and tick **Show
understory**. In false colours: a band of teal follows the stream across the
view and away into the hills; the ground under the camera, part grass and part
soil, is a pale mix of yellow and teal, and drifts of yellow lie on the slopes
beyond. Press **Meadow**: broad yellow drifts on the open grass, with plain
grass between. **Cliff**: brown along the foot of the cliff, where scree meets
grass, and the rock above it untinted. **Shore**: the sand stays sand; nothing
grows on it.

## 9. Planted by the GPU

**This is `Understory`, and its generate pass.** Cut the ground round the
camera into squares of 2 m, **cells**. The square of cells that holds a circle
of 80 m round the camera is 160 m a side, 80 x 80 cells, 6,400 of them, and the
circle itself, 40 cells in radius, holds about π × 40² ≈ 5,027. Each cell may
hold one small plant. Storing them would be easy and pointless: a plant's
place, kind, turn and size follow from its cell's own random numbers and the
ground under it, so a compute pass can work them out from nothing every frame,
keep the ones in view, and count them for the draws. Nothing is stored, nothing
pops in when the camera turns, and the cost is the same everywhere. This
section plants and counts; section 10 draws.

> **Jump:** this is Chapter 26's grass pass (a field is a function of
> position; generate, cull, append), here reading Chapter 38's island from
> compute for the first time, and feeding its draw through Chapter 19 section
> 2's other way of sending per-instance data, instance-rate vertex attributes
> (section 10). Keep in mind the two buffers it writes and who reads each: the
> instances (section 10's vertex input) and the commands (section 10's
> indirect draws, and a copy for the CPU).

### A plant from its cell

The camera's cell and the cells round it make a square, 80 x 80 at 80 m
(Low: 40 m, 40 x 40). One invocation runs per cell, in 8 x 8 workgroups, a
dispatch in two dimensions. Each:

1. draws its cell's numbers, `treeInCell`'s pattern with another salt: a place
   in the middle 80 % of the cell, its x and its z each from a `randomFloat` of
   its own (each call moves the state on, and GLSL does not say in which order
   two calls in one expression run), a turn, a size from 0.8 to 1.2, a roll
   for its kind, and where its level line falls;
2. stops if the place is beyond the reach, and shrinks the plant to nothing
   over the reach's last quarter: Chapter 37 section 7's fade, the same shape
   over a different length (Chapter 37 fades over a fixed 100 m);
3. reads the island there, takes section 8's chances, and turns the roll into
   a kind: under the fern's chance a fern, under the fern's and the flower's a
   flower, under all three a bush; above them, nothing;
4. stops inside a clearing (90 m round a village's middle, 25 m round a
   landmark, from the same tables Chapter 37 placed them by), or nearer than
   1.5 times the tree's scale, in metres, to the tree `treeInCell` puts in
   that 16 m cell (only that cell's tree is looked at, so a plant just across
   a cell's edge from a tree can stand nearer to it than that: a rare plant
   by a trunk, accepted in place of a second lookup for every plant);
5. stands on the ground as the rings draw it this frame, `terrainHeight`
   (Chapter 37 section 4's lesson: the drawn ground, not the map), sunk 5 cm;
6. stops if its sphere is outside the view (Chapter 26 section 3's six
   planes);
7. picks LOD0 or LOD1 by how wide its sphere is on screen: its radius times
   Chapter 37 section 5's `screenScale` over its distance, in pixels, against
   60. At 720p with the 60 degree lens `screenScale` is 1,247, and a fern's
   sphere has a radius of 1.96 m (half the diagonal of its 2.7 x 0.9 x 2.7 m
   box), so a fern is 60 pixels wide at 1.96 × 1247 / 60 = 41 m, and LOD0
   inside that; a flower's (0.28 m) is at 6 m, a bush's (1.34 m) at 28 m. A
   pass that starts from nothing has no last frame to keep a level by, so
   there is no hysteresis; instead each plant's line is moved by up to 10 % by
   its own number, and the change from one level to the other is a ragged
   band, not a line;
8. appends itself to its kind and level.

**The append cannot overflow.** A kind and level has a region of the instance
buffer that holds one instance per cell, 6,400, so even if every cell planted
that kind at that level it would fit. Six regions of 6,400 instances of 32
bytes are 1.17 MiB. Chapter 26 section 4's list could overflow and needed a
check; this one is sized by what can exist, not by a guess.

### The island from compute

The pass reads the material map through set 1, as the terrain does, with
Chapter 38's own `groundWeights`. In a fragment shader its `texture()` picks a
mip level from how fast the coordinate changes between neighbouring pixels; a
compute shader has no neighbouring pixels, and GLSL then reads level 0 (the
GLSL specification's rule for an implicit level of detail outside a fragment
shader, in the Sources), the map as stored, blended between its four nearest
texels by the map's linear sampler. That is the level the understory wants, so
the function is used unchanged.

### The twins

`UnderstoryTypes.h` holds what C++ and GLSL share: the instance, the pass's
parameters, and the commands. `UnderstoryParams::kinds` packs four numbers a
kind into one `vec4`, since std140 lays out an array of `vec4`s with no
padding:

```c
/* Shaders/Horizon/UnderstoryTypes.h - Chapter 39 section 9: the understory's C++/GLSL twins. GLSL includes it
   as "UnderstoryTypes.h", C++ as "Horizon/UnderstoryTypes.h". */
#ifndef PF_HORIZON_UNDERSTORY_TYPES_H
#define PF_HORIZON_UNDERSTORY_TYPES_H

#include "SharedShaderTypes.h"   /* DrawIndexedIndirectCommand, for both sides; on the C++ side, the vec4 and uint aliases */

#ifdef __cplusplus
    namespace pf::demos::horizon {
    using shared::vec4;
    using shared::uint;
    using shared::DrawIndexedIndirectCommand;
#endif

#define UNDERSTORY_CELL     2.0f   /* metres: one small plant at most in each square of this size */
#define UNDERSTORY_KINDS    3u     /* 0 a fern, 1 a flower, 2 a bush: understoryChance's order */
#define UNDERSTORY_COMMANDS 10u    /* one per kind, level and part: (1 + 2 + 2) parts, at LOD0 and LOD1 */
#define UNDERSTORY_GROUP    8u     /* the generate pass's workgroups: 8 x 8 cells */

/* One plant, as the draw reads it: two instance-rate vertex attributes (Chapter 19 section 2). */
struct PlantInstance
{
    vec4 place;   /*  0  xyz: where it stands; w: its size, 1 as the plant file has it */
    vec4 turn;    /* 16  x, y: the cosine and sine of its turn about +Y; zw unused */
};                /* 32 */

/* What the generate pass reads. std140, one buffer per frame in flight. */
struct UnderstoryParams
{
    vec4  camera;            /*   0  xyz: the camera; w: the reach (m), past which nothing grows */
    vec4  frustumPlanes[6];  /*  16  Chapter 26 section 3's culling planes: xyz inward unit normal, w distance */
    vec4  clearings[8];      /* 112  xy: the middle of a place where nothing grows; z: its radius (m) */
    vec4  kinds[3];          /* 240  per kind, four numbers in one vec4: x its sphere's radius at size 1,
                                     y its middle's height (m), z its first command, w its parts (commands
                                     per level) */
    float fade;              /* 288  metres: a plant shrinks to nothing over the reach's last `fade` */
    float screenScale;       /* 292  Chapter 37 section 5's: viewport height / tan(fov / 2), times the LOD bias */
    float lodPixels;         /* 296  a plant whose sphere is this many pixels wide or more is LOD0, else LOD1 */
    uint  capacity;          /* 300  instances a region of the instance buffer holds: one per cell */
    int   firstCellX;        /* 304  the square of cells round the camera: its first cell, counted from the */
    int   firstCellZ;        /* 308  origin, and its side */
    uint  cellsPerSide;      /* 312 */
    uint  padding0;          /* 316 */
};                           /* 320 */

/* The draws, which the generate pass counts into with atomicAdd, and which are read back for the panel. */
struct UnderstoryCommands
{
    DrawIndexedIndirectCommand commands[UNDERSTORY_COMMANDS];   /*   0 */
};                                                               /* 200 */

#ifdef __cplusplus
    static_assert(sizeof(PlantInstance) == 32, "PlantInstance layout drifted.");
    static_assert(sizeof(UnderstoryParams) == 320, "UnderstoryParams layout drifted.");
    static_assert(offsetof(UnderstoryParams, fade) == 288, "UnderstoryParams alignment drifted.");
    static_assert(sizeof(UnderstoryCommands) == 200, "UnderstoryCommands layout drifted.");
    }
#endif

#endif
```

### The class

**This is `Understory.h`.** One instance, owned by the demo; `Initialize` in
`Setup`, after the props are registered and the terrain has its set;
`RecordCompute` before the scene pass, and from section 10 `Draw` inside it.
Its includes, the constants and counts above the class, and its public part:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 39: the understory, bushes, ferns and flowers planted by the GPU every frame
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Understory.h
#pragma once

#include "PillowFort/Demos/Horizon/Props.h"
#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include "Horizon/HorizonTypes.h"      // TerrainDraw
#include "Horizon/UnderstoryTypes.h"   // UnderstoryParams, UnderstoryCommands

#include <glm/glm.hpp>
#include <vulkan/vulkan.h>

#include <array>
#include <cstdint>
#include <functional>
#include <vector>

namespace pf::demos::horizon {

// Section 9: the farthest the understory ever reaches, and so the most cells it ever plants per side: a
// region of the instance buffer holds one plant per cell of that square, so it cannot overflow.
inline constexpr float    UNDERSTORY_MAX_REACH = 80.0f;   // metres
inline constexpr uint32_t UNDERSTORY_MAX_CELLS = 80;      // per side: 6,400 cells

// Section 9: a small plant whose sphere is at least this many pixels wide on screen is LOD0, else LOD1.
inline constexpr float UNDERSTORY_LOD_PIXELS = 60.0f;

// Section 9: the three kinds, in understoryChance's order (section 8), which is the kind numbers' too.
inline constexpr std::array<const char*, UNDERSTORY_KINDS> UNDERSTORY_PLANTS{ "Fern", "Flower", "Bush" };

// Section 9: what the last frame planted, read back two frames later (Chapter 20 section 9).
struct UnderstoryCounts
{
    std::array<std::array<uint32_t, 2>, UNDERSTORY_KINDS> planted{};   // by kind, then by level
    bool                                                  valid = false;
};

// The bushes, ferns and flowers within reach of the camera, placed from nothing every frame by a compute
// pass and drawn by indirect draws. A demo owns one: Initialize in Setup, after the props are registered and
// the terrain has its island set; RecordCompute before the scene pass, Draw inside it.
class Understory
{
public:
    // Section 9: the three plants' LOD0 and LOD1 meshes, copied from the props' scene into buffers of its
    // own; the instances and the commands; the generate pass and its sets.
    InitializationResult Initialize(const vulkan_graphics::VulkanContext& context, VkPipelineCache pipelineCache,
                                    const Props& props, VkDescriptorSetLayout frameSetLayout,
                                    VkDescriptorSetLayout islandSetLayout);
    void Shutdown();   // the host has idled the device; safe after a partial Initialize
    bool Ready() const { return m_pipeline != VK_NULL_HANDLE; }

    // Section 9. In Record, after the fence wait: what this slot planted last time.
    void ReadCounts(uint32_t frameIndex);

    // Section 9. Outside the scene pass: this frame's plants, within `reach` metres of `camera` and in `view`,
    // on the island as `terrain` draws it.
    void RecordCompute(VkCommandBuffer commandBuffer, uint32_t frameIndex, glm::vec3 camera, const scene::Frustum& view,
                       float reach, float screenScale, const TerrainDraw& terrain, VkDescriptorSet islandSet);

    const UnderstoryCounts& Counts() const { return m_counts; }
```

The private part, which finishes the class, declares the three functions
`Initialize` calls (below); copies of the borrowed handles, a `VulkanContext`
and the pipeline cache; the CPU's copy of the plants' vertices and indices, the
commands as they start each frame (`m_template`, every count 0), each command's
material and the kinds' four numbers; the buffers, and per frame in flight the
parameters, the readback and `m_pending`, which says a readback holds a copy to
read; and the pass's objects, each `VK_NULL_HANDLE` until made:

```cpp
private:
    InitializationResult CopyMeshes(const Props& props);                        // section 9
    InitializationResult CreateBuffers();                                       // section 9
    InitializationResult CreatePass(VkDescriptorSetLayout frameSetLayout,
                                    VkDescriptorSetLayout islandSetLayout);     // section 9

    vulkan_graphics::VulkanContext m_context;                          // copies of borrowed handles
    VkPipelineCache                m_pipelineCache = VK_NULL_HANDLE;   // borrowed

    // The plants' vertices and indices, and what the draws start from: every instance count 0.
    std::vector<scene::Vertex>                m_vertexData;
    std::vector<uint32_t>                     m_indexData;
    UnderstoryCommands                        m_template{};
    std::array<uint32_t, UNDERSTORY_COMMANDS> m_materials{};   // each command's material
    std::array<glm::vec4, UNDERSTORY_KINDS>   m_kinds{};       // UnderstoryParams::kinds

    // The buffers: the plants' vertices and indices, the six regions of instances and the commands, and per
    // frame in flight the parameters, the readback of the commands, and whether the readback holds a copy.
    vulkan_graphics::AllocatedBuffer m_vertices;
    vulkan_graphics::AllocatedBuffer m_indices;
    vulkan_graphics::AllocatedBuffer m_instances;   // 6 regions
    vulkan_graphics::AllocatedBuffer m_commands;
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_params;
    std::array<vulkan_graphics::AllocatedBuffer, vulkan_graphics::FRAMES_IN_FLIGHT> m_readback;
    std::array<bool, vulkan_graphics::FRAMES_IN_FLIGHT>                             m_pending{};
    UnderstoryCounts                                                                m_counts;

    // The generate pass: its set layout, the pool its sets come from, a set per frame in flight, its pipeline
    // layout and its pipeline.
    VkDescriptorSetLayout                                          m_setLayout = VK_NULL_HANDLE;
    VkDescriptorPool                                               m_pool      = VK_NULL_HANDLE;
    std::array<VkDescriptorSet, vulkan_graphics::FRAMES_IN_FLIGHT> m_sets{};
    VkPipelineLayout                                               m_layout    = VK_NULL_HANDLE;
    VkPipeline                                                     m_pipeline  = VK_NULL_HANDLE;
};
```

`Understory.cpp` begins with its includes, the clearings' radii, and
`Initialize`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 39: the understory, bushes, ferns and flowers planted by the GPU every frame
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/Understory.cpp
#include "PillowFort/Demos/Horizon/Understory.h"

#include "PillowFort/VulkanGraphics/GraphicsPipeline.h"
#include "PillowFort/VulkanGraphics/VulkanBarriers.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <format>

namespace pf::demos::horizon {

using namespace vulkan_graphics;

static_assert(sizeof(DrawIndexedIndirectCommand) == sizeof(VkDrawIndexedIndirectCommand), "The command twins drifted.");

// The clearings, where nothing grows, as many as UnderstoryParams::clearings holds: every village, for 90 m
// round its middle, where its houses stand; and every landmark, for 25 m.
constexpr float VILLAGE_CLEARING  = 90.0f;   // metres
constexpr float LANDMARK_CLEARING = 25.0f;   // metres
static_assert(VILLAGES.size() + LANDMARKS.size() == 8, "UnderstoryParams::clearings holds eight.");

InitializationResult Understory::Initialize(const VulkanContext& context, VkPipelineCache pipelineCache,
                                            const Props& props, VkDescriptorSetLayout frameSetLayout,
                                            VkDescriptorSetLayout islandSetLayout)
{
    m_context       = context;
    m_pipelineCache = pipelineCache;
    if (auto result = CopyMeshes(props); !result) { return result; }
    if (auto result = CreateBuffers(); !result)   { return result; }
    return CreatePass(frameSetLayout, islandSetLayout);
}
```

`Shutdown` destroys everything `Initialize` made, in reverse, and resets the
object to its defaults, so it is safe after a partial `Initialize` (it does
nothing if `Initialize` never ran: the device is the context's, and null).
It goes after `Initialize`, and `CopyMeshes`, `CreateBuffers`, `CreatePass`,
`RecordCompute` and `ReadCounts` after it, in the order they are written
below:

```cpp
void Understory::Shutdown()
{
    const VkDevice device = m_context.device;
    if (device == VK_NULL_HANDLE)
    {
        return;   // Initialize never ran
    }
    vkDestroyPipeline(device, m_pipeline, nullptr);
    vkDestroyPipelineLayout(device, m_layout, nullptr);
    vkDestroyDescriptorPool(device, m_pool, nullptr);   // frees the sets with it
    vkDestroyDescriptorSetLayout(device, m_setLayout, nullptr);
    for (uint32_t frame = 0; frame < FRAMES_IN_FLIGHT; ++frame)
    {
        destroyBuffer(m_context, m_params[frame]);
        destroyBuffer(m_context, m_readback[frame]);
    }
    destroyBuffer(m_context, m_commands);
    destroyBuffer(m_context, m_instances);
    destroyBuffer(m_context, m_indices);
    destroyBuffer(m_context, m_vertices);
    *this = Understory{};
}
```

`CopyMeshes` copies the fern's, the flower's and the bush's LOD0 and LOD1 into
one small vertex and index buffer of the understory's own, about 0.2 MB, and
writes a command for every submesh of each. The props' scene gives the meshes
through one more accessor, `Props::PlantMeshes`:

```cpp
// Section 9: each plant's LOD0 and LOD1, one after the other in one small vertex and index buffer of the
// understory's own, and a command for each of their submeshes: (kind, level, part), the parts of a kind's
// two levels alike (the plant-space contract, section 2): the fern's frond; the flower's stem and head; the
// bush's bark and leaves. Every command of a kind and level draws the same instances, from the start of
// their region: firstInstance.
InitializationResult Understory::CopyMeshes(const Props& props)
{
    const scene::Scene& world = props.World();
    uint32_t command = 0;
    for (uint32_t kind = 0; kind < UNDERSTORY_KINDS; ++kind)
    {
        std::array<uint32_t, 3> meshes{};
        if (!props.PlantMeshes(UNDERSTORY_PLANTS[kind], meshes))
        {
            return InitializationResult::failure(std::format("{} was not loaded.", UNDERSTORY_PLANTS[kind]));
        }
        const uint32_t parts = static_cast<uint32_t>(world.GetMesh(meshes[0]).data.submeshes.size());
        if (world.GetMesh(meshes[1]).data.submeshes.size() != parts || command + 2 * parts > UNDERSTORY_COMMANDS)
        {
            return InitializationResult::failure(std::format("{}'s levels do not match.", UNDERSTORY_PLANTS[kind]));
        }

        // The sphere round LOD0, as Chapter 37 section 5 measures it: its radius, and its middle's height.
        const scene::Aabb& box = world.GetMesh(meshes[0]).bounds;
        m_kinds[kind] = glm::vec4(0.5f * glm::length(box.max - box.min), 0.5f * (box.min.y + box.max.y),
                                  static_cast<float>(command), static_cast<float>(parts));

        for (uint32_t level = 0; level < 2; ++level)
        {
            const scene::MeshData& data        = world.GetMesh(meshes[level]).data;
            const int32_t          firstVertex = static_cast<int32_t>(m_vertexData.size());
            const uint32_t         firstIndex  = static_cast<uint32_t>(m_indexData.size());
            m_vertexData.insert(m_vertexData.end(), data.vertices.begin(), data.vertices.end());
            m_indexData.insert(m_indexData.end(), data.indices.begin(), data.indices.end());
            for (const scene::Submesh& submesh : data.submeshes)
            {
                m_template.commands[command] = {
                    .indexCount    = submesh.indexCount,
                    .instanceCount = 0,
                    .firstIndex    = firstIndex + submesh.firstIndex,
                    .vertexOffset  = firstVertex,
                    .firstInstance = (2 * kind + level) * UNDERSTORY_MAX_CELLS * UNDERSTORY_MAX_CELLS,
                };
                m_materials[command] = submesh.materialIndex;   // the scene's, which RegisterProps kept
                ++command;
            }
        }
    }
    if (command != UNDERSTORY_COMMANDS)
    {
        return InitializationResult::failure("The understory's plants do not have the parts it expects.");
    }
    return InitializationResult::success();
}
```

It writes ten commands, each with the submesh's index count, where its
level's vertices start in the shared buffer, and 0 instances until the pass
counts. Every command of a kind and level draws the same instances, from the
start of their region, `firstInstance` (Chapter 19 section 6's
`drawIndirectFirstInstance`, a device feature the engine turns on in
`VulkanInstance`):

| Command | Kind, level | Part (material) | `firstInstance` |
| --- | --- | --- | --- |
| 0 | fern, LOD0 | frond (`FernLeaf`) | 0 |
| 1 | fern, LOD1 | frond (`FernLeaf`) | 6,400 |
| 2 | flower, LOD0 | stem and blades (`FlowerBark`) | 12,800 |
| 3 | flower, LOD0 | head (`FlowerHead`) | 12,800 |
| 4 | flower, LOD1 | stem (`FlowerBark`) | 19,200 |
| 5 | flower, LOD1 | head (`FlowerHead`) | 19,200 |
| 6 | bush, LOD0 | bark (`BushBark`) | 25,600 |
| 7 | bush, LOD0 | leaves (`BushLeaf`) | 25,600 |
| 8 | bush, LOD1 | bark (`BushBark`) | 32,000 |
| 9 | bush, LOD1 | leaves (`BushLeaf`) | 32,000 |

`PlantMeshes` goes in `Props.cpp` after `SetLeafCards` and before
`ShapeCasters`, section 4's, which is still at the end:

```cpp
// Chapter 39 section 9: a plant's three levels' meshes, for a pass that draws them itself.
bool Props::PlantMeshes(const std::string& name, std::array<uint32_t, 3>& meshes) const
{
    const uint32_t asset = FindAsset(name);
    if (asset == NO_ASSET || asset < m_firstPlant)
    {
        return false;
    }
    meshes = m_assets[asset].meshes;
    return true;
}
```

declared in `Props.h` after `IsPlantMaterial` and before `ShapeCasters`:

```cpp
    // Chapter 39 section 9: a plant's three levels' meshes, for the understory, which draws them itself.
    bool PlantMeshes(const std::string& name, std::array<uint32_t, 3>& meshes) const;
```

`CreateBuffers` makes the buffers, with the helpers of Chapters 08 and 20:
`createBuffer`'s last argument is `hostVisible`, true for the per-frame
parameters, which the CPU writes; `createReadbackBuffer` is Chapter 20 section
9's. The instances are both a storage buffer (the pass writes them) and a
vertex buffer (section 10's vertex input reads them); the commands are a
storage buffer, an indirect buffer, and the source and destination of
transfers:

```cpp
InitializationResult Understory::CreateBuffers()
{
    const VkDeviceSize vertexBytes   = m_vertexData.size() * sizeof(scene::Vertex);
    const VkDeviceSize indexBytes    = m_indexData.size() * sizeof(uint32_t);
    const VkDeviceSize instanceBytes = 2 * UNDERSTORY_KINDS * UNDERSTORY_MAX_CELLS * UNDERSTORY_MAX_CELLS * sizeof(PlantInstance);
    m_vertices  = createBuffer(m_context, vertexBytes, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    m_indices   = createBuffer(m_context, indexBytes, VK_BUFFER_USAGE_INDEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    m_instances = createBuffer(m_context, instanceBytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_VERTEX_BUFFER_BIT, false);
    m_commands  = createBuffer(m_context, sizeof(UnderstoryCommands),
                               VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT
                               | VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, false);
    bool ok = m_vertices.buffer != VK_NULL_HANDLE && m_indices.buffer != VK_NULL_HANDLE &&
              m_instances.buffer != VK_NULL_HANDLE && m_commands.buffer != VK_NULL_HANDLE;
    for (uint32_t frame = 0; frame < FRAMES_IN_FLIGHT; ++frame)
    {
        m_params[frame]   = createBuffer(m_context, sizeof(UnderstoryParams), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
        m_readback[frame] = createReadbackBuffer(m_context, sizeof(UnderstoryCommands));
        ok = ok && m_params[frame].buffer != VK_NULL_HANDLE && m_readback[frame].buffer != VK_NULL_HANDLE;
    }
    if (!ok)
    {
        return InitializationResult::failure("Creating the understory's buffers failed.");
    }
    uploadToBuffer(m_context, m_vertices, m_vertexData.data(), vertexBytes);
    uploadToBuffer(m_context, m_indices, m_indexData.data(), indexBytes);
    return InitializationResult::success();
}
```

`CreatePass` makes the pass's own set: three buffers the compute stage sees,
and a set per frame in flight, since the parameters change every frame. Chapter
20 section 4's `createDescriptorSets` makes the layout, a pool counted from it
(one uniform buffer and two storage buffers a set, for two sets) and the sets:

```cpp
// Section 9: the generate pass. Its layout is the island's plan (Chapter 38 section 2): set 0 the frame's,
// which no compute shader can see but holds the number; set 1 the island; set 2 its own: the parameters, one
// buffer per frame in flight, the instances and the commands. Its push constants are the terrain's.
InitializationResult Understory::CreatePass(VkDescriptorSetLayout frameSetLayout, VkDescriptorSetLayout islandSetLayout)
{
    const std::array<VkDescriptorSetLayoutBinding, 3> bindings{ {
        { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
        { .binding = 2, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .descriptorCount = 1,
          .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT },
    } };
    // A set per frame in flight.
    if (!createDescriptorSets(m_context, bindings, m_setLayout, m_pool, m_sets))
    {
        return InitializationResult::failure("Creating the understory's descriptor sets failed.");
    }
```

then each set is written with its frame's parameter buffer, the instances and
the commands, bindings 0 to 2:

```cpp
    for (uint32_t frame = 0; frame < FRAMES_IN_FLIGHT; ++frame)
    {
        const std::array<VkDescriptorBufferInfo, 3> buffers{ {
            { m_params[frame].buffer, 0, sizeof(UnderstoryParams) },
            { m_instances.buffer, 0, VK_WHOLE_SIZE },
            { m_commands.buffer, 0, VK_WHOLE_SIZE },
        } };
        std::array<VkWriteDescriptorSet, 3> writes{};
        for (uint32_t binding = 0; binding < writes.size(); ++binding)
        {
            writes[binding] = {
                .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                .dstSet          = m_sets[frame],
                .dstBinding      = binding,
                .descriptorCount = 1,
                .descriptorType  = bindings[binding].descriptorType,
                .pBufferInfo     = &buffers[binding],
            };
        }
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    }
```

Last, the pipeline's layout, Chapter 38's plan: set 0 the frame's (no compute
shader can see it, but it holds the number), set 1 the island's, set 2 its
own, and the terrain's push constants:

```cpp
    const std::array<VkDescriptorSetLayout, 3> layouts{ frameSetLayout, islandSetLayout, m_setLayout };
    const VkPushConstantRange pushRange{ .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT, .offset = 0, .size = sizeof(TerrainDraw) };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = static_cast<uint32_t>(layouts.size()),
        .pSetLayouts            = layouts.data(),
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &pushRange,
    };
    if (vkCreatePipelineLayout(m_context.device, &layoutInfo, nullptr, &m_layout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreatePipelineLayout failed for the understory.");
    }
    m_pipeline = createComputePipeline(m_context.device, m_pipelineCache, "Horizon/UnderstoryGenerate.comp.spv", m_layout);
    if (m_pipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the understory's generate pipeline failed.");
    }
    return InitializationResult::success();
}
```

### The pass

**This is `UnderstoryGenerate.comp.glsl`.** It pushes `TerrainDraw` first, as
every pass that reads the island does (Chapter 38 section 2), so that
`TerrainHeight.glsl` finds its `terrain`:

```glsl
// Shaders/Horizon/UnderstoryGenerate.comp.glsl - Chapter 39 section 9: the understory, planted from nothing
// every frame. One invocation per 2 m cell of the square round the camera: the cell's own random numbers
// say where in it a plant would stand, which kind, its turn and its size; the island says whether it grows
// there (section 8's chances); and a plant that grows, is near enough, outside every clearing and in view is
// appended to its kind and level's region, and counted into that region's draws, which section 10 draws.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "HorizonTypes.h"      // TerrainDraw, TREE_CELL
#include "UnderstoryTypes.h"   // UnderstoryParams, PlantInstance, UnderstoryCommands

layout(local_size_x = UNDERSTORY_GROUP, local_size_y = UNDERSTORY_GROUP) in;

// The terrain's push constants, first, as every pass that reads the island declares them (Chapter 38 section
// 2): TerrainHeight.glsl's functions read `terrain`.
layout(push_constant) uniform TerrainBlock
{
    TerrainDraw terrain;
};

#include "TerrainHeight.glsl"     // set 1, the island; terrainHeight, as the rings draw it this frame
#include "GroundMaterials.glsl"   // Chapter 38's groundWeights; through it forestDensity, treeInCell
#include "Understory.glsl"        // section 8: understoryChance

// Set 2: the understory's own.
layout(std140, set = 2, binding = 0) uniform ParamsBlock { UnderstoryParams params; };
layout(std430, set = 2, binding = 1) writeonly buffer InstanceBlock { PlantInstance plants[]; };
layout(std430, set = 2, binding = 2) buffer CommandBlock { UnderstoryCommands draws; };

// How far below the ground a plant's origin is sunk, so that it does not stand on a slope's high side only.
const float SINK = 0.05;   // metres

// Section 9: a LOD line jittered by each plant's own number, by this share either way.
const float LINE_JITTER = 0.1;

bool inView(vec3 centre, float radius)
{
    for (int i = 0; i < 6; ++i)
    {
        if (dot(params.frustumPlanes[i].xyz, centre) + params.frustumPlanes[i].w < -radius)
        {
            return false;
        }
    }
    return true;
}

void main()
{
    if (gl_GlobalInvocationID.x >= params.cellsPerSide || gl_GlobalInvocationID.y >= params.cellsPerSide)
    {
        return;   // the last workgroups run past the square's edge
    }

    // The cell's own numbers, in the same order every frame: Chapter 37's treeInCell, with another salt. Each
    // randomFloat moves `state` on, so each is a statement of its own: GLSL does not say in which order two
    // calls in one expression run.
    ivec2 cell  = ivec2(params.firstCellX, params.firstCellZ) + ivec2(gl_GlobalInvocationID.xy);
    uint  state = uint(cell.x) * 2654435761u ^ pcgHash(uint(cell.y) + 39u);
    float x     = randomFloat(state);
    float z     = randomFloat(state);
    vec2  xz    = (vec2(cell) + 0.1 + 0.8 * vec2(x, z)) * UNDERSTORY_CELL;
    float angle = 6.2831853 * randomFloat(state);
    float size  = 0.8 + 0.4 * randomFloat(state);
    float roll  = randomFloat(state);   // which kind, if any
    float line  = randomFloat(state);   // where this plant's LOD line falls

    // Near enough: the reach, with the last `fade` metres shrinking it to nothing (Chapter 37 section 7).
    float across = distance(xz, params.camera.xz);
    if (across > params.camera.w)
    {
        return;
    }
    size *= 1.0 - smoothstep(params.camera.w - params.fade, params.camera.w, across);
    if (size < 0.01)
    {
        return;
    }

    // Section 8: which kind grows here, if any. Chapter 38's groundWeights reads the map with texture(), which
    // in a compute shader reads level 0: there are no neighbouring pixels to choose another by. The roll is
    // a kind by where it falls: under the fern's chance a fern (0), under the fern's and the flower's a flower
    // (1), under all three a bush (2); above them, nothing.
    float w[6];
    groundWeights(groundMap, groundMapUv(xz, terrain.heightmap.x), w);
    vec3 chance = understoryChance(w, forestDensity(heightmap, terrain.heightmap, xz),
                                   groundSlope(heightmap, terrain.heightmap, xz), xz);
    uint kind = roll < chance.x ? 0u : roll < chance.x + chance.y ? 1u : roll < chance.x + chance.y + chance.z ? 2u : 3u;
    if (kind == 3u)
    {
        return;
    }

    // Not in a clearing, a village or round a landmark, nor at the foot of a tree.
    for (int i = 0; i < 8; ++i)
    {
        if (distance(xz, params.clearings[i].xy) < params.clearings[i].z)
        {
            return;
        }
    }
    vec2  treePosition;
    float treeTurn;
    float treeScale;
    uint  treeKind;
    if (treeInCell(heightmap, terrain.heightmap, ivec2(floor(xz / TREE_CELL)), treePosition, treeTurn, treeScale, treeKind)
        && distance(xz, treePosition) < 1.5 * treeScale)
    {
        return;
    }

    // On the ground as the rings draw it this frame (Chapter 37 section 4), and in view (Chapter 26 section 3).
    vec4  kindShape = params.kinds[kind];
    float radius    = kindShape.x * size;
    vec3  base      = vec3(xz.x, terrainHeight(xz) - SINK, xz.y);
    vec3  centre    = base + vec3(0.0, kindShape.y * size, 0.0);
    if (!inView(centre, radius))
    {
        return;
    }

    // LOD0 while the plant's sphere is lodPixels wide on screen or more, each plant's line moved by up to
    // LINE_JITTER of it: with no memory of last frame's level, a plant cannot keep it, so the lines are spread
    // instead.
    float pixels = radius * params.screenScale / max(distance(centre, params.camera.xyz), 0.001);
    uint  level  = pixels >= params.lodPixels * (1.0 + LINE_JITTER * (2.0 * line - 1.0)) ? 0u : 1u;

    // Appended: one more instance of every part of this kind at this level, all reading the same slot.
    uint first = uint(kindShape.z) + level * uint(kindShape.w);
    uint slot  = atomicAdd(draws.commands[first].instanceCount, 1u);
    for (uint part = 1u; part < uint(kindShape.w); ++part)
    {
        atomicAdd(draws.commands[first + part].instanceCount, 1u);
    }
    uint region = 2u * kind + level;
    plants[region * params.capacity + slot] = PlantInstance(vec4(base, size), vec4(cos(angle), sin(angle), 0.0, 0.0));
}
```

`atomicAdd` returns the count before it added, so the first part's count is
the new plant's slot; the kind's other parts count up too, so every command of
the kind draws the same instances.

### Recording it

`RecordCompute` holds the reach to what the buffers were sized for, fills the
parameters, then records six steps, (a) to (f), with two helpers
(`memoryBarrier` takes the stages and accesses before and after, Chapter 19
section 4; `groupCount` rounds a count up to whole workgroups, Chapter 20
section 3):

```cpp
void Understory::RecordCompute(VkCommandBuffer commandBuffer, uint32_t frameIndex, glm::vec3 camera,
                               const scene::Frustum& view, float reach, float screenScale, const TerrainDraw& terrain,
                               VkDescriptorSet islandSet)
{
    // The square of cells round the camera's cell that reaches `reach` every way. A reach typed into the
    // panel is held to what the instance buffer was sized for, and never below 0, before it becomes a count.
    reach = std::clamp(reach, 0.0f, UNDERSTORY_MAX_REACH);
    const uint32_t  side  = std::min(2 * static_cast<uint32_t>(std::ceil(reach / UNDERSTORY_CELL)), UNDERSTORY_MAX_CELLS);
    const glm::ivec2 first = glm::ivec2(glm::floor(glm::vec2(camera.x, camera.z) / UNDERSTORY_CELL)) - static_cast<int32_t>(side / 2);
    UnderstoryParams params{
        .camera       = glm::vec4(camera, reach),
        .fade         = 0.25f * reach,   // section 9: the reach's last quarter
        .screenScale  = screenScale,
        .lodPixels    = UNDERSTORY_LOD_PIXELS,
        .capacity     = UNDERSTORY_MAX_CELLS * UNDERSTORY_MAX_CELLS,
        .firstCellX   = first.x,
        .firstCellZ   = first.y,
        .cellsPerSide = side,
    };
    std::copy(view.planes.begin(), view.planes.end(), params.frustumPlanes);
    for (size_t i = 0; i < VILLAGES.size(); ++i)
    {
        params.clearings[i] = glm::vec4(VILLAGES[i].centre, VILLAGE_CLEARING, 0.0f);
    }
    for (size_t i = 0; i < LANDMARKS.size(); ++i)
    {
        params.clearings[VILLAGES.size() + i] = glm::vec4(LANDMARKS[i].position, LANDMARK_CLEARING, 0.0f);
    }
    std::copy(m_kinds.begin(), m_kinds.end(), params.kinds);
    std::memcpy(m_params[frameIndex].mapped, &params, sizeof(params));
    vmaFlushAllocation(m_context.allocator, m_params[frameIndex].allocation, 0, VK_WHOLE_SIZE);

    // (a) Last frame's draws read the commands and the instances, and its copy read the commands: done with
    //     them before this frame's update and generate pass write them. A write after reads: an execution
    //     dependency, no memory to make visible.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_NONE,
                  VK_PIPELINE_STAGE_2_CLEAR_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_NONE);

    // (b) Every draw back to no instances: a copy from the command buffer itself, which vkCmdUpdateBuffer
    //     carries (up to 64 KB), so there is no staging buffer. It is one of the spec's clear commands.
    vkCmdUpdateBuffer(commandBuffer, m_commands.buffer, 0, sizeof(UnderstoryCommands), &m_template);

    // (c) What the update wrote, before the generate pass's atomics read and write it.
    memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    // (d) One invocation a cell, in 8 x 8 workgroups: a dispatch in two dimensions.
    const std::array<VkDescriptorSet, 2> sets{ islandSet, m_sets[frameIndex] };
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_pipeline);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_layout, 1, 2, sets.data(), 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(terrain), &terrain);
    vkCmdDispatch(commandBuffer, groupCount(side, UNDERSTORY_GROUP), groupCount(side, UNDERSTORY_GROUP), 1);

    // (e) What the pass wrote, before the three that read it: section 10's indirect draws read the commands,
    //     its vertex input reads the instances, before any shader runs, and the copy reads the commands.
    memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT | VK_ACCESS_2_VERTEX_ATTRIBUTE_READ_BIT | VK_ACCESS_2_TRANSFER_READ_BIT);

    // (f) The counts, copied for the CPU to read when this slot comes round again (Chapter 20 section 9).
    const VkBufferCopy region{ .srcOffset = 0, .dstOffset = 0, .size = sizeof(UnderstoryCommands) };
    vkCmdCopyBuffer(commandBuffer, m_commands.buffer, m_readback[frameIndex].buffer, 1, &region);
    memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_pending[frameIndex] = true;
}
```

Step (b) is a command this guide has not used before. `vkCmdUpdateBuffer`
writes a few bytes into a buffer from data carried in the command buffer
itself, up to 64 KB, recorded like any other command: here every count back to
0, with no staging buffer. The specification files it with the clear commands,
and synchronization2 puts its write in the `CLEAR` stage, the narrowest stage
that covers it (`TRANSFER` would also be correct).

Each barrier's comment answers Chapter 04 section 5's three questions.

Two choices in (e) are worth a sentence each. The instances are read by
**vertex input, before any shader runs**: naming `VERTEX_SHADER` in (e), as
Chapters 21 and 26 did for their storage buffers, would be the classic slip in
another form. And the indirect draw reads its commands at `DRAW_INDIRECT`,
its own stage, which no shader stage covers.

The validation layer checks most of this with the program's own settings
(Chapter 02's shader-access setting is on), and the Exit check's controls fire
it. Its two on (e), without `DRAW_INDIRECT` and without `COPY`, name
`vkCmdUpdateBuffer` as the writer, not the pass: the layer records an atomic as
a read (Chapter 20 section 5's table), so the last write it knows of is the
update's, which (c) carries to the compute stage and (e) on to the readers it
names. (c) also finishes a chain: last frame's pass wrote the instances, (e) and
(a) carry that to this frame's pass without a memory access of their own, and
(c), whose second half names the pass's writes, is what closes it. The part the
layer cannot check is vertex input: taking `VERTEX_ATTRIBUTE_INPUT` out of (e)
is silent, even with synchronization validation forced, because it does not yet
track what vertex input reads for an indirect draw or through an instance-rate
binding. That part of the barrier is argued from the three questions, not from a
quiet layer.

`ReadCounts` reads a slot's copy when the slot comes round again, after the
frame's fence wait, so the copy is complete:

```cpp
// Section 9: two frames after a slot recorded its pass, its fence has been waited, so its copy is final.
void Understory::ReadCounts(uint32_t frameIndex)
{
    if (!m_pending[frameIndex])
    {
        return;
    }
    m_pending[frameIndex] = false;
    UnderstoryCommands read{};
    readBuffer(m_context, m_readback[frameIndex], &read, sizeof(read));
    for (uint32_t kind = 0; kind < UNDERSTORY_KINDS; ++kind)
    {
        const uint32_t first = static_cast<uint32_t>(m_kinds[kind].z);
        const uint32_t parts = static_cast<uint32_t>(m_kinds[kind].w);
        m_counts.planted[kind] = { read.commands[first].instanceCount, read.commands[first + parts].instanceCount };
    }
    m_counts.valid = true;
}
```

### The terrain's side

The pass reads the island as the rings draw it this frame, so it needs the
island's set and the very push constants the terrain pushes. `Terrain::Record`
built those inline; they move into a function of their own, which `Record`
now calls, for this second user. In Chapter 38's `Record`, everything from
`uint32_t flags = 0;` through the `const TerrainDraw draw{ ... };` it fills
moves into `DrawConstants`, which returns the struct; `Record` keeps
its `preset` line (the draw below it uses it) and `draw` becomes a call. The new
function goes just before `Record`. It opens with its signature and the
`preset` line the draw below it needs, which `Record` keeps too:

```cpp
// Chapter 39 section 9: the push constants Record pushes, for any pass that reads the island as the rings
// draw it this frame: Record's own block until Chapter 39, which moved it here for its second user. Its
// comments name the chapters that added each part.
TerrainDraw Terrain::DrawConstants(const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
```

Record's own block follows, moved: every line from `uint32_t flags = 0;` to the
end of the struct, section 8's `TERRAIN_SHOW_UNDERSTORY` line among them. Two
things change on the way. Chapter 36's seven comments in it, which say only
`// section 1`, `// section 2` and so on, gain the chapter's name
(`// Chapter 36 section 1`, `// Chapter 36 sections 10, 11`), as the comment
above says they do; and the struct's first line now returns it:

```cpp
    return TerrainDraw{
```

and the function ends with the closing brace after the struct's `};`.

`Record`'s new start, the rest of `Record` being Chapter 38's, unchanged:

```cpp
void Terrain::Record(VkCommandBuffer commandBuffer, const SceneRenderer& sceneRenderer, uint32_t frameIndex,
                     const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn) const
{
    const TerrainPreset& preset = TERRAIN_PRESETS[settings.preset];
    const TerrainDraw    draw   = DrawConstants(settings, ringCenter, skyOn);   // Chapter 39 section 9
```

`Terrain.h` gains `HorizonTypes.h`, in a group of its own after the
`PillowFort/` includes (`Horizon/HorizonTypes.h` is reached through the
`Shaders/` include path, as in `HorizonDemo.cpp`), for `TerrainDraw`, and the
two declarations beside `IslandSetLayout`:

```cpp
#include "Horizon/HorizonTypes.h"   // Chapter 39: TerrainDraw, which DrawConstants returns

    // Chapter 39 section 3: the island set's layout, which every pipeline of the demo holds at set 1. Section
    // 9: and what a pass that reads the island needs: the set, and the push constants its shaders read
    // (TerrainHeight.glsl's `terrain`), as Record pushes them this frame.
    VkDescriptorSetLayout IslandSetLayout() const { return m_setLayout; }
    VkDescriptorSet       IslandSet() const { return m_set; }
    TerrainDraw           DrawConstants(const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn) const;
```

### The demo's side

`HorizonDemo.h` includes `Understory.h`, after `Terrain.h`, and owns one, last:

```cpp
    // Chapter 39 section 9: the understory.
    Understory m_understory;
```

`PlantSettings` gains the switch and the reach, after `overdraw`:

```cpp
    bool         understory      = true;    // section 9: the ferns, flowers and bushes
    float        reach           = 80.0f;   // section 9: metres
```

`Setup` initializes it after the leaf pipelines, the plates and the
per-material table's resize, and before the props are placed, if the plants
loaded; a failure leaves the demo running without it. `m_context.vulkan` is the
demo's `VulkanContext`; `Initialize` keeps a copy as the understory's own
`m_context`:

```cpp
    // Chapter 39 section 9: the understory, which copies the small plants' meshes and reads the island; if it
    // cannot, the demo runs on without it.
    if (m_props.PlantsLoaded())
    {
        if (auto result = m_understory.Initialize(m_context.vulkan, m_context.pipelineCache, m_props,
                                                  m_sceneRenderer.FrameSetLayout(), m_terrain.IslandSetLayout());
            !result)
        {
            Log::warning(std::format("No understory: {}", result.message()).c_str());
            m_understory.Shutdown();
        }
    }
```

`Teardown` shuts it down as its second line, right after the timestamps and
before the leaf pipelines (`m_understory.Shutdown();`). `Record` reads last
time's counts after `PrepareDraws`:

```cpp
    // Chapter 39 section 9: what the understory planted when this slot last ran.
    m_understory.ReadCounts(frame.frameIndex);
```

and records the pass after the shadows and before the sky's update, outside
the scene pass, and not with **Draw objects** off (Chapter 37 section 9's
frame without objects):

```cpp
    // Chapter 39 section 9: the understory, planted for this frame outside the scene pass, on the ground as
    // the terrain draws it; not with the objects off (Chapter 37 section 9).
    const bool understory = m_understory.Ready() && m_plantSettings.understory && m_propSettings.drawObjects;
    if (understory)
    {
        m_understory.RecordCompute(commandBuffer, frame.frameIndex, m_cameraTransform.translation,
                                   scene::frustumFromViewProjection(frameData.viewProjection), m_plantSettings.reach,
                                   screenScale * m_propSettings.lodBias,
                                   m_terrain.DrawConstants(m_terrainSettings, m_ringCenter, frame.sky.mode != SkyMode::Off),
                                   m_terrain.IslandSet());
    }
```

The Plants header's Part 3 group grows. Here it is whole, in its final form;
it replaces section 8's group (the separator, the **Show understory** box and
the key): the new **Understory** switch sits on **Show understory**'s line and
before it, then come the reach and what was planted at each level, and
section 8's key stays last:

```cpp
    // Section 8: where the small plants may grow, painted by the terrain, and its key. Section 9: the
    // understory, its reach, and what it planted, at each level.
    ImGui::SeparatorText("Understory");
    ImGui::Checkbox("Understory", &m_plantSettings.understory);
    ImGui::SameLine();
    ImGui::Checkbox("Show understory", &m_terrainSettings.showUnderstory);
    ImGui::SetNextItemWidth(140.0f);
    ImGui::SliderFloat("Reach (m)", &m_plantSettings.reach, 20.0f, UNDERSTORY_MAX_REACH, "%.0f");
    const UnderstoryCounts& counts = m_understory.Counts();
    if (m_understory.Ready() && counts.valid)
    {
        ImGui::Text("LOD0+LOD1  fern %u+%u  flower %u+%u", counts.planted[0][0], counts.planted[0][1],
                    counts.planted[1][0], counts.planted[1][1]);
        ImGui::Text("           bush %u+%u", counts.planted[2][0], counts.planted[2][1]);
    }
    if (m_terrainSettings.showUnderstory)
    {
        ImGui::TextUnformatted("Fern teal, flower yellow, bush brown");
    }
```

### Run

Run `GenerateProjects.bat` for the new files. **Stream**, as in section 8, with
**Show understory** off. Nothing new on the ground: the pass plants, and
nothing draws yet. The panel counts what it planted, at **Reach** 80 m: **fern
105+275**, **flower 1+62** and **bush 0+0** (LOD0+LOD1), ferns on the stream's
soil, a few flowers in the grass, and no scree for a bush.

## 10. Drawn from the counts

**This is `Understory.vert.glsl`, and `Understory::Draw`.** The counts are on
the GPU, in the commands buffer, and the plants in the instance buffer. The
draws read both where they are: an indirect draw takes its counts from the
buffer, and the vertex shader takes each plant from the instances.

### Instances as vertex attributes

The trees draw through `SceneRenderer`'s instance buffer, read by the vertex
shader at `gl_InstanceIndex` (Chapter 19 section 3). The understory has its
own instances, and feeds them the other way Chapter 19 section 2 named: as
**instance-rate vertex attributes**. The two new things are a second vertex
binding, binding 1, with stride 32 and `VK_VERTEX_INPUT_RATE_INSTANCE`, and
locations 3 and 4, which read where the plant stands with its size, and the
cosine and sine of its turn. That keeps set 2 the material's, so the
understory draws through the leaf pipelines' layout unchanged. The vertex
shader turns the plant about +Y with a rotation written out (Chapter 10 section
1): a quarter turn, c = 0 and s = 1, takes (1, 0, 0) to (0, 0, −1), as
Rodrigues did in section 1.

```glsl
// Shaders/Horizon/Understory.vert.glsl - Chapter 39 section 10: Leaf.vert.glsl for the understory, whose
// plants the GPU placed. Each comes as two instance-rate vertex attributes, not a model matrix: where it
// stands with its size, and the cosine and sine of its turn about +Y.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "FrameBlock.glsl"   // set 0 binding 0: frame.viewProjection

layout(location = 0) in vec3 inPosition;   // binding 0: the plant's own vertices, as Leaf.vert reads them
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 place;        // binding 1, once per instance: PlantInstance::place
layout(location = 4) in vec4 turn;         // and PlantInstance::turn

layout(location = 0) out vec3 worldPosition;
layout(location = 1) out vec3 worldNormal;
layout(location = 2) out vec2 uv;
layout(location = 3) flat out vec2 plantBase;

// A turn about +Y by the angle whose cosine and sine are c and s, written out (Chapter 10 section 1): x and z
// mix, y stays.
vec3 turned(vec3 v, float c, float s)
{
    return vec3(c * v.x + s * v.z, v.y, -s * v.x + c * v.z);
}

void main()
{
    worldPosition = place.xyz + place.w * turned(inPosition, turn.x, turn.y);
    worldNormal   = turned(inNormal, turn.x, turn.y);   // a turn and one size for all axes: no normal matrix
    uv            = inUv;
    plantBase     = place.xz;
    gl_Position   = frame.viewProjection * vec4(worldPosition, 1.0);
}
```

### The second row of pipelines

The leaf pipelines' table gets its second row: `Understory.vert.glsl`, with
the instances at binding 1. `CreateLeafPipelines` now describes both bindings
and all five attributes once, and the first row takes the first binding and
three attributes. Four edits to the function as sections 3 and 7 left it.
First, its comment describes the table as built, in place of section 3's, which
looked ahead to section 7's mode and this row:

```cpp
// Chapter 39 section 3: the pipelines that draw plants, in one table, [understory][mode]: a row with
// Leaf.vert.glsl, and section 10's with Understory.vert.glsl and the instances at binding 1; opaque, cut out
// (section 3), or counting layers (section 7). Their layout is Chapter 38's set plan: set 0 the frame's, set
// 1 the island's, which no leaf shader reads, and set 2 the run's material, the engine's own set for it.
// FlatDraw and then LeafDraw are pushed to the fragment shader.
```

Second, section 3's `binding` constant and its three-attribute `attributes`
array, with the comment above them, become these two arrays:

```cpp
    // Binding 0: a plant's vertices, Chapter 11's Vertex with its uv now. Section 10: binding 1, a
    // PlantInstance per instance, not per vertex.
    const std::array<VkVertexInputBindingDescription, 2> bindings{ {
        { .binding = 0, .stride = sizeof(scene::Vertex), .inputRate = VK_VERTEX_INPUT_RATE_VERTEX },
        { .binding = 1, .stride = sizeof(PlantInstance), .inputRate = VK_VERTEX_INPUT_RATE_INSTANCE },
    } };
    const std::array<VkVertexInputAttributeDescription, 5> attributes{ {
        { .location = 0, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, position) },
        { .location = 1, .binding = 0, .format = VK_FORMAT_R32G32B32_SFLOAT, .offset = offsetof(scene::Vertex, normal) },
        { .location = 2, .binding = 0, .format = VK_FORMAT_R32G32_SFLOAT, .offset = offsetof(scene::Vertex, uv) },
        { .location = 3, .binding = 1, .format = VK_FORMAT_R32G32B32A32_SFLOAT, .offset = offsetof(PlantInstance, place) },
        { .location = 4, .binding = 1, .format = VK_FORMAT_R32G32B32A32_SFLOAT, .offset = offsetof(PlantInstance, turn) },
    } };
```

Third, the loop over the rows runs to 2, in place of the line that ended with
the comment `// section 10 adds the second row`:

```cpp
    for (uint32_t understory = 0; understory < 2; ++understory)
```

Fourth, in the pipeline's description the row chooses the shader, the bindings
and the attributes, in place of the `.vertexShader`, `.fragmentShader`,
`.vertexBindings` and `.vertexAttributes` lines (the `.fragmentShader` line is
unchanged):

```cpp
                .vertexShader           = understory ? "Horizon/Understory.vert.spv" : "Horizon/Leaf.vert.spv",
                .fragmentShader         = "Horizon/Leaf.frag.spv",
                .vertexBindings         = { bindings.data(), understory ? 2u : 1u },
                .vertexAttributes       = { attributes.data(), understory ? 5u : 3u },
```

The rest of the function, section 7's `Constants` and mode loop included,
stays.

### `Draw`

`Draw` binds the two vertex buffers and the index buffer, then draws each
command from the buffer the pass counted into, after `bindRun` binds its
pipeline and material. It goes at the end of `Understory.cpp`:

```cpp
// Section 10: the plant's vertices at binding 0, a vertex at a time; the instances at binding 1, an instance
// at a time; and each command drawn from the buffer the generate pass counted into.
void Understory::Draw(VkCommandBuffer commandBuffer, const std::function<void(VkCommandBuffer, uint32_t)>& bindRun) const
{
    const std::array<VkBuffer, 2>     buffers{ m_vertices.buffer, m_instances.buffer };
    const std::array<VkDeviceSize, 2> offsets{ 0, 0 };
    vkCmdBindVertexBuffers(commandBuffer, 0, 2, buffers.data(), offsets.data());
    vkCmdBindIndexBuffer(commandBuffer, m_indices.buffer, 0, VK_INDEX_TYPE_UINT32);
    for (uint32_t command = 0; command < UNDERSTORY_COMMANDS; ++command)
    {
        bindRun(commandBuffer, m_materials[command]);
        vkCmdDrawIndexedIndirect(commandBuffer, m_commands.buffer, command * sizeof(DrawIndexedIndirectCommand), 1,
                                 sizeof(DrawIndexedIndirectCommand));
    }
}
```

declared after `RecordCompute`:

```cpp
    // Section 10. Inside the scene pass: every command, after `bindRun` binds its pipeline and its material.
    void Draw(VkCommandBuffer commandBuffer, const std::function<void(VkCommandBuffer, uint32_t)>& bindRun) const;
```

`Record` draws the understory after the objects, inside the scene pass, through
section 3's `BindLeafRun`, which has taken `understory` from the start; this
call passes `true`:

```cpp
    // Chapter 39 section 10: the understory, drawn from the counts, through the leaf pipelines' second row.
    if (understory)
    {
        m_understory.Draw(commandBuffer, [&](VkCommandBuffer cb, uint32_t material) {
            BindLeafRun(cb, frame.frameIndex, material, true, skyOn);
        });
    }
```

### Run

Run `GenerateProjects.bat` for the new shader. **Stream**, as before. Ferns
along the stream's soil, the nearest a broad crown of fronds with its leaflets
clear against the ground, the farther ones smaller and sparser, at LOD1;
flowers dotted over the grass, white, yellow and violet, few and far between.
The counts are section 9's: drawing changes nothing that is planted. Press
**Forest floor**. Under oaks and pines, ferns all round the camera on dappled
ground, and no flowers: the forest's shade. The panel reads **fern 109+258**
and **flower 0+0**.

Planted at each view, LOD0 + LOD1 added, at a reach of 40 m and of 80 m
(lavapipe, 720p, the final code on the Low preset, which starts at 40 m,
section 11; 80 m is **Reach** dragged to its end). Each cell is "at 40 m / at
80 m":

| View | Ferns (at 40 m / at 80 m) | Flowers (at 40 m / at 80 m) | Bushes (at 40 m / at 80 m) |
| --- | --- | --- | --- |
| Stream | 91 / 380 | 34 / 63 | 0 / 0 |
| Meadow | 0 / 0 | 0 / 17 | 0 / 6 |
| Cliff | 0 / 0 | 0 / 0 | 15 / 15 |
| Shore | 0 / 0 | 0 / 0 | 0 / 0 |
| Village | 39 / 315 | 0 / 53 | 0 / 0 |
| Wood | 0 / 128 | 23 / 170 | 16 / 227 |
| Edge | 0 / 0 | 57 / 260 | 1 / 13 |
| Forest floor | 104 / 367 | 0 / 0 | 0 / 0 |

The Meadow view stands 25 m up, looking down past the ground within 40 m. The
split between the levels is step 7's lines at work (section 9): at Stream the
panel reads **fern 105+275** and **flower 1+62** at 80 m, where a fern is LOD0
only out to about 41 m, and a flower's sphere is 60 pixels wide at only 6 m.
Drag **Reach** down to its start, 20 m, to see it from the other side: **fern
19+2** and **flower 1+11**, the ferns almost all LOD0 and the flowers still
LOD1.

Two runs at Stream give the same frames, pixel for pixel, which proves little
on lavapipe, whose atomics run in the same order every frame (Chapter 26
section 9). On a GPU the slot each plant takes changes, and the picture does
not: every slot is drawn, and the plants are opaque and depth-tested, except
where two of them meet at exactly the same depth.

## Checkpoint

**Stream** with **Show understory**: teal, yellow and brown where each kind
may grow. Off: ferns along the stream and flowers in the grass, and the panel
counting them. **Forest floor**: ferns all round, no flowers. Untick
**Understory**: the plants go, and the counts stop changing.

---

# Part 4 — The bill (section 11)

Everything is on screen. Part 4 reads what it costs: the passes the plants add,
timed; the triangles, which lavapipe can count truthfully; and a budget a real
GPU must meet, with the switches that bring a frame back under it.

## 11. What plants cost

**This is the bill.** Lavapipe is a CPU: its times say which pass is large
against which, not what a GPU would take. So this section reads what a GPU
would measure, the cost that carries over (triangles), and works out the
budget a real GPU must meet.

### Seven timestamps

Chapter 37 section 9 timed four intervals with five timestamps. The plants
add two passes, so seven timestamps: 0 at the start, 1 after the shadows,
**2 after the understory's planting**, 3 after the sky and the depth clear, 4
after the terrain, 5 after the objects, **6 after the understory's draw**.
Every one is written every frame, outside any condition, whether the
understory ran or not: `GpuTimestamps::Read` returns nothing for a frame with
a slot left unwritten (Chapter 24 section 9). `Setup`'s last line, Chapter 37's
`return m_timestamps.Initialize(...)` with a 5, asks for seven:

```cpp
    // Chapter 37 section 9: timestamps a frame (Chapter 24's class): Chapter 39 section 11, seven.
    return m_timestamps.Initialize(m_context.vulkan, 7);
```

`m_timings` holds six. Chapter 37's loop that fills it, which reads
`Milliseconds(pass, pass + 1)` for every `pass` below `m_timings.size()`,
needs no edit: with six entries it reads the six intervals between seven
stamps.

```cpp
    std::array<double, 6>           m_timings{};               // milliseconds: shadows, planting, sky, terrain,
                                                               // objects, understory draw (Chapter 39 section 11)
```

The new stamps sit right after the understory's compute block and its draw
block, and the clear's, the terrain's and the objects' stamps (Chapter 37's 2,
3 and 4) become 3, 4 and 5:

```cpp
    m_timestamps.Write(commandBuffer, frame.frameIndex, 2);   // section 11: written whether it ran or not

    m_timestamps.Write(commandBuffer, frame.frameIndex, 6);   // section 11
```

The **Times** header reads them, in place of Chapter 37's lines after **Draw
objects**. "The four" is still Chapter 37's sum (shadows, sky, terrain, objects),
so a reading compares with Chapter 37's; "the six" adds **planting** and
**understory draw**. Below them, the triangles the camera's draws send, which
lavapipe can show truthfully; the casters' are in the Plants header (section
4):

```cpp
        // Chapter 39 section 11: six passes; "the four" are Chapter 37's. The casters' triangles are in the
        // Plants header (section 4).
        const double four = m_timings[0] + m_timings[2] + m_timings[3] + m_timings[4];
        ImGui::Text("GPU ms  shadows %.2f  planting %.2f", m_timings[0], m_timings[1]);
        ImGui::Text("        sky %.2f  terrain %.2f", m_timings[2], m_timings[3]);
        ImGui::Text("        objects %.2f", m_timings[4]);
        ImGui::Text("        understory draw %.2f", m_timings[5]);
        ImGui::Text("        the four %.2f  the six %.2f", four, four + m_timings[1] + m_timings[5]);
        ImGui::Text("CPU ms  props %.2f", m_propsMilliseconds);
        ImGui::Text("Triangles  objects %.2f M", 1e-6 * static_cast<double>(m_drawTriangles));
```

The objects' triangles are summed beside the casters' in `Record`
(`m_drawTriangles = triangles(m_draws);`, after `m_casterTriangles`), into a
member after `m_casterTriangles` (`uint64_t m_drawTriangles = 0;`).

### Where Low starts

Chapter 36 starts a CPU device on the **Low** preset. The plants follow it:
on Low, the understory's reach starts at 40 m and **LOD0 casts LOD1** starts
on; Full keeps `PlantSettings` as it is. Two constants after
`PlantSettings`:

```cpp
// Chapter 39 section 11: what the Low preset (a CPU device: lavapipe) changes of PlantSettings when Setup
// chooses it: a shorter reach, and LOD0 casting LOD1. The Full preset keeps PlantSettings as it is.
inline constexpr float LOW_PLANT_REACH    = 40.0f;   // metres
inline constexpr bool  LOW_COARSE_CASTERS = true;
```

set once, inside Chapter 36's `if (!m_presetChosen)` block in `Setup`, after
the line `m_presetChosen = true;` (Chapter 36's preset 1 is Low, 0 is Full):

```cpp
        if (m_terrainSettings.preset == 1)   // Chapter 39 section 11: Low starts the plants lighter
        {
            m_plantSettings.reach          = LOW_PLANT_REACH;
            m_plantSettings.shadows.coarse = LOW_COARSE_CASTERS;
        }
```

Until this section every device started the plants at 80 m with **LOD0 casts
LOD1** off, and the readings in sections 4, 9 and 10 say which settings they
were taken with.

### What lavapipe says

The reference run read the six intervals with **Draw objects** on and then off,
at the Low preset, 720p and the Sun sky, in each view, after the readings
settled. What that is good for is proportion: which pass grows where. A CPU's
times move with the load on the machine, so a run of yours will differ in every
figure and agree in the proportions (`REFERENCE.md`'s row for this chapter has
the reference run's table for the viewpoint, Village, Wood, Edge and Forest
floor). With **Draw objects** off, planting and the understory's draw read 0.1
to 0.4 ms, the cost of their timestamps on lavapipe, since neither runs. On a
CPU the sky, Chapter 28's clouds marched per pixel, is most of every frame. Of
the plants, the leaf cards (the objects) and their shadows are almost all of the
cost, and both grow with the trees in view: least at the viewpoint and the
Village, more in **Wood**, most on the Forest floor, where the shadows alone
cost more than the sky. The understory's two passes together are under 1 % of
any frame. (On lavapipe the terrain's interval also holds part of the objects'
work, as Chapter 37 found.) A GPU has none of these proportions: it rasterizes
the cards and their discards in hardware, and on an RTX 5070 desktop Chapter
37's "the four", the sky included, reads 0.36 to 0.40 ms (REFERENCE.md's row
37).

### The budget

The target is Chapter 37 section 9's: the RTX 4060 Laptop at 1920 x 1080, 4x
MSAA, 60 frames a second, so T = 16.7 ms a frame. The Radeon 890M is measured
and reported, not held to it; the Low preset and the cut list below are where a
game would find its lower settings.

Everything standing on the island, plants and Chapter 37's objects and all
their shadows, shares one budget:

$$
B = \min\big(5.5,\ T - X - F_\text{off} - R\big)
$$

- **F_off** is "the four" with **Draw objects** off: the island alone;
- **X** is the frame's time the timers do not see (the composite, the
  resolve, the UI), read as the **Frame** window's ms at `--present
  immediate` minus "the four", or 1.5 ms if it cannot be read;
- **R** = 4.2 ms is kept for Chapters 40-42 (billboards 1.5, grass 2.5,
  wind 0.2);
- 5.5 ms caps it: 3.0 for objects and plants, 2.5 for their shadows.

Until the timing pass measures the 4060, the budget can be worked out without
it, because whatever F_off is there, it is far below the 5.5 ms that would
bring B under its cap. On an RTX 5070 desktop "the four" with **Draw objects**
off reads 0.36 to 0.38 ms (REFERENCE.md's row 37, at 1080p, 4x, Sun sky, Full),
and the 4060 Laptop is slower than that by a small factor, not by fifteen. With
X at 1.5 ms:

$$
B = \min(5.5,\ 16.7 - 1.5 - F_\text{off} - 4.2) = 5.5 \text{ ms whenever } F_\text{off} \le 5.5 \text{ ms}
$$

So B = 5.5 ms, an estimate that a timing run on the 4060 replaces with
readings. The 4060 passes if, at the viewpoint, **Village**, **Wood**,
**Edge** and **Forest floor**, "the six" with Draw objects on minus off is at
most B. If it is over, apply the list below in order, reading again after each
step.

### Over budget: what to cut first

Ordered by time saved for look lost. Each step is a switch or a slider; read
"the six" again after each, and keep a step only if its own interval moved:

1. **Stand-ins from** 66 → 45 → 30 m: the shadows' interval.
2. **LOD0 casts LOD1**: the shadows' interval; the near dapple coarser.
3. The shadow filter's radius 1 → 0 in Chapter 17's Shadows window: nine
   taps become one, everywhere.
4. **Reach** 80 → 40 m: planting and the understory's draw.
5. **LOD bias** 1.0 → 0.8 → 0.65 (Chapter 37's slider): every object a level
   coarser sooner; the objects' interval.
6. Shadow distance 250 → 150 m, cascades 4 → 3 (the Shadows window).
7. **Alpha to coverage** off: last, because soft leaves are the point.

Past these, the cards themselves: fewer, larger cards at LOD1 (`every` and
`grow` in the script's `lod` table), measured again as section 2's were.

### Run

**Times** open, at the viewpoint, **Wood** and **Forest floor**. The six
intervals, then "the four" and "the six", the props' CPU time, and **Triangles
objects**: 0.72 M in **Wood**, 0.98 M on the **Forest floor**.

## Checkpoint

**Forest floor** at `--msaa 4`: leaf-card trees overhead, ferns round the
camera, dappled shadows on both. **Times**: six intervals and the objects'
triangles. Untick **Draw objects**: planting and the understory's draw fall to
almost nothing, and the frame is Chapter 38's.

---

## If something goes wrong

| What you see | Why, and where |
| --- | --- |
| "No plants: OakTree.usda is missing, or has no LOD0 to LOD2." and Chapter 37's trees, and "No leaf plates: the trees' leaves are not loaded." | The plant files are not in `Assets/Scenes/Horizon/Plants/` (they are on `start`; a run of the script from `Assets/Scenes/` writes them), or `Assets/` beside the executable is stale (Chapter 13 section 6) |
| "No leaf plates: ... ash.png not found." but the plants load, or with the whole `Plants/` folder missing, this line and "No plants: ..." | `Plants/Textures/ash.png` is missing: only the plates need it (section 2's "Get the pictures") |
| Trees of blue-grey squares | The leaves have no picture: a colour written beside `diffuseColor.connect` (section 2), or the pictures missing from `Plants/Textures/` (the importer logs each missing texture) |
| A file of 131 bytes where a picture should be | A Git LFS pointer, from the plain raw link: fetch the picture from GitHub's LFS host (section 2) |
| Crowns dark and flat, with no sunlit side | The crown normal flipped on back faces: `FLAT_LEAF` not set on `*Leaf` materials (section 3) |
| Plants vanish, their sunk roots show through the ground, no message | A leaf pipeline compares with LESS: every pipeline in `Horizon` is GREATER (section 3, Chapter 35 section 6) |
| "The leaf pipelines need 15 samplers in one stage ..." and no demo | The GPU's per-stage limit; the leaf layout holds 15 (section 3) |
| Validation: set 0 not bound, or a layout mismatch, after a plant | Set 0 not rebound on a switch between the flat and leaf layouts (section 3) |
| Far trees' shadows are bare trunks | **Stand-ins from** above the shadows' reach, or `ShapeCasters` not called after `CollectDraws` (section 4) |
| Overdraw view: everything red or white | Depth write on in the overdraw mode, or the colour clear missing (section 7) |
| Flowers on the beach | The material map is missing: its stand-in is all grass, so the understory plants grass's flowers everywhere, sand included (Chapter 38's "No material map: ..." line in the log) |
| No understory, and "No understory: ..." | The small plants were not loaded, or their levels' parts differ (section 9) |
| The counts stay at 0 | The pass is not recorded (the **Understory** switch, or **Draw objects** off), or `ReadCounts` is not called after the fence wait (section 9) |
| Understory plants float or sink on hills | `RecordCompute` pushed constants other than `DrawConstants` for this frame (section 9) |
| Ferns blink as the camera turns | The pass's camera, frustum or reach is not this frame's (section 9) |
| The **Times** rows never move, or stay at 0 | `GpuTimestamps::Read` returns false while a slot is left unwritten: all seven are written every frame, whether the understory ran or not (section 11) |

## Exit check

Most of it is seen. The items marked [H] were measured on lavapipe with the
harness (1280 x 720, only the program's own validation settings, the Low
preset, unless a line says otherwise), with a few lines of Python over its
screenshots; REFERENCE.md's row for this chapter holds every number, box and
threshold.

- [ ] **The script** (optional). `python make_horizon_plants.py` prints section
      2's counts (OakTree LOD0 13806 triangles, 2660 cards; LOD1 3938, 665; LOD2
      56; and so on) and "cards: base t = 0"; `--bare` prints section 1's. The
      counts are the check; the hashes depend on the C library.
- [ ] **The pictures.** `oak.png`, `pine.png` and `ash.png` are 238,115,
      303,684 and 181,423 bytes, with section 2's SHA-256s; none is a 131-byte
      pointer.
- [ ] **Loaded.** The Plants header reads "Plants: OakTree, PineTree, Bush,"
      and "Fern, Flower", and the log has section 6's six lines, with kept
      shares of 25.6, 22.9, 25.6, 14.4, 40.5 and 15.7 %.
- [ ] **The trees, by eye.** In **Wood** with the Sun sky: bare branches with
      `--bare`; blue-grey squares and solid shadows before section 3; after it,
      leaves with the sky through their edges, dappled shadows near the camera,
      and past 66 m a solid oval under each tree. With the leaves' threshold at
      0 in the script: square leaves and square shadows.
- [ ] **Leaves at one sample.** [H] In the overdraw view at **Wood**, one
      sample, **Understory** off, inside the near oak's crown, the share of
      pixels that keep no layer is about twice the share with the leaves'
      threshold at 0 (12.7 % against 6.4 %), and the 6.4 % are the pixels no
      card reaches at all.
- [ ] **Shadows with holes.** By eye, the near oak's shadow is dappled, and
      solid with the threshold at 0. [H] Under it, where the threshold-0 trees'
      shadow is solid, more than a tenth of the pixels are lit through holes
      with the leaves cut out (20.7 %).
- [ ] **Far shadows.** By eye, at **Treeline**: solid ovals under the far trees
      with **Stand-ins from** at 66, faint specks at 250. [H] About 9 % of the
      band where the wood stands is more than 15 % darker with the stand-ins,
      and under 1 % lighter.
- [ ] **Alpha to coverage.** At `--msaa 4` in **Wood**: soft leaf edges against
      the sky and the grass; with **Alpha to coverage** off, stair-steps; at
      one sample the box is greyed. [H] On the leaf plates, the pixels between
      the sky and a leaf are several times as many with it on as off, and none
      at one sample.
- [ ] **Thinning.** **Show leaf plates**, **Look at them**, sky off, one
      sample: with **Mip fix** the 50 to 200 m walls hold their density;
      without it the ash's 200 m wall is gone. [H] Section 6's tables: with the
      fix, the 50 to 200 m walls within 15 % of their picture's share; at
      `--msaa 4` the walls' mean coverage, a different measure from the tables'
      shares, holds too with the fix and falls without it.
- [ ] **Overdraw.** In **Wood**: the crowns orange to yellow on black; with
      **Leaf-card trees** off, Chapter 37's trees a dim olive. [H] Section 7's
      conclusion: leaf cards draw five to nine times the layers of the solid
      trees, and `--no-crop` about 40 % more while keeping the same. With the
      kept count moved above the scale and the test, green equals red
      everywhere.
- [ ] **Levels hold their mass.** [H] With **Level** forced, in the overdraw
      view, at **Treeline** and at **Pines**: LOD1 keeps within 15 % of LOD0's
      kept pixels (under 150 m), and LOD2 within 15 % of LOD1's (250 to 350 m).
- [ ] **The understory.** **Show understory**: teal along the soil at
      **Stream**, yellow drifts at **Meadow**, brown along the foot of the
      **Cliff**, the beach at **Shore** unchanged. With it off: ferns along the
      stream and flowers in the grass; on the **Forest floor** ferns all round
      and no flowers; nothing on the beach. The panel counts as section 10's
      table does, at the same reach. [H] At **Shore** the bottom 200 rows are
      identical with the view on and off; two runs at **Stream** are identical,
      pixel for pixel.
- [ ] **Chapter 38 untouched.** [H] With **Leaf-card trees** and **Understory**
      off, the viewpoint and **Wood** are pixel for pixel Chapter 38's (sky
      off, the panel left out).
- [ ] **Depth.** Every new pipeline compares with GREATER. Control: with
      `.depthCompare` at LESS in `CreateLeafPipelines`, every plant is gone
      with no message, and its sunk roots show through the ground.
- [ ] **Times.** **Times** shows six intervals, "the four" and "the six", and
      the objects' triangles: 0.72 M in **Wood**, 0.98 M on the Forest floor.
      **Draw objects** off takes planting and the understory's draw to a few
      tenths of a millisecond on lavapipe, their timestamps alone, and the
      frame to Chapter 38's.
- [ ] **Validation and robustness.** [H] Silent with only the program's own
      settings, and with synchronization validation and the shader-access
      setting forced, at one sample and at four, through a resize to 1000 x
      600. With the plant files missing the demo runs on: "No plants:
      OakTree.usda is missing, or has no LOD0 to LOD2. The pool keeps Chapter
      37's trees, and there is no understory." and "No leaf plates: the trees'
      leaves are not loaded."; with only `ash.png` missing, "No leaf plates: ...
      ash.png not found."; with `fern.png` missing, the importer's "Texture
      Textures/fern.png not found.". Clean under AddressSanitizer and UBSan.
- [ ] **Positive controls.** Each is a one-line edit, run with only the
      program's own settings, at **Wood**:
  - In `RecordCompute`'s barrier (e), drop `DRAW_INDIRECT` and
    `INDIRECT_COMMAND_READ`: 10 × `SYNC-HAZARD-READ-AFTER-WRITE` at
    `vkCmdDrawIndexedIndirect`, "previously written by vkCmdUpdateBuffer",
    which "must allow VK_ACCESS_2_INDIRECT_COMMAND_READ_BIT accesses at
    VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT".
  - In (e), drop `COPY` and `TRANSFER_READ`: 10 ×
    `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdCopyBuffer`, the same writer.
  - Delete barrier (c): 10 × `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`,
    the update's `TRANSFER_WRITE` at `VK_PIPELINE_STAGE_2_CLEAR_BIT`, and 10 ×
    `SYNC-HAZARD-WRITE-AFTER-WRITE` at `vkQueueSubmit2`, the instances
    "previously written by another vkCmdDispatch".
  - In (c), `COPY` in place of `CLEAR` as the source stage: 10 ×
    `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`, the same writer: the
    update's write is in the `CLEAR` stage.
  - In `CreatePass`, binding 1's `stageFlags` set to `VERTEX` alone:
    `VUID-VkComputePipelineCreateInfo-layout-07988`, "uses descriptor [Set 2,
    Binding 1, variable "InstanceBlock"] ... stageFlags was
    VK_SHADER_STAGE_VERTEX_BIT".
  - In `CreateLeafPipelines`, `SAMPLERS` set to 1000001: "The leaf pipelines
    need 1000001 samplers in one stage; this GPU allows 1000000 samplers and
    1000000 sampled images.", and the demo is detached (Chapter 09 section 5).
  - In (e), drop `VERTEX_ATTRIBUTE_INPUT` and `VERTEX_ATTRIBUTE_READ`: silent,
    even with synchronization validation forced (section 9 says why).

## Where to go from here

- **Light through leaves.** A leaf lit from behind glows (Chapter 27 section
  7's translucency). Needed when the camera looks toward the sun through a
  wood; it depends on the view, which is why Chapter 40 could not bake it,
  and why it is left out here.
- **The mip fix in the shadow pass**, so leaf shadows hold to 66 m without
  the stand-ins' help nearer in. Needed when the near cascades' dapple thins
  where it should not.
- **Understory shadows**, through Chapter 17's `extraCasters`. Needed when
  the camera walks low, where a fern's shadow is a large part of the view.
- **Per-cascade caster lists**: each cascade gets only what can fall in its
  slice (an engine change). Needed when the shadows' interval leads the bill.
- **A depth pre-pass for leaves**: draw the cut-outs once into depth with the
  test, then shade with EQUAL, so a pixel shades one leaf, not three. Needed
  when the objects' interval is mostly overdraw, as section 7 counts it.
- **Hashed alpha testing**: a stable noise threshold in place of 0.5, which
  keeps far leaves without a per-level table. Needed with temporal
  anti-aliasing, which averages its noise away.
- **Bark textures and normals**, and **more seeds per kind**. Needed when the
  near trees, not the far wood, are what a scene is about.
- **Seasons**: an autumn picture, and the oak's tint moved through the year.
- **GPU culling of the tree pool**, as the understory is culled. Needed when
  the pool's slots, not their triangles, are the CPU's cost.
- **Octahedral impostors** after Chapter 40's billboards. Needed when the far
  wood is seen from many heights.
- **Falling leaves** (Chapter 21) and **plants that bend round the camera**
  (Chapter 27's push sphere).

Next: [40 — Forests to the Horizon](40-Forests-To-The-Horizon.md)

---

## Sources

- Daniel Greenheck, *EZ-Tree*, <https://github.com/dgreenheck/ez-tree>, commit
  `dcf309bd86bd521083d9c70f01f2de45fdc7c457`, MIT licence: the growth, the
  leaf cards and their levels (`src/lib/tree.js`, `options.js`), the oak, pine
  and bush presets, and the oak, pine and ash leaf pictures.
- *Vulkan 1.4 specification*: "Clear Commands" (`vkCmdUpdateBuffer`),
  "Synchronization" (`VK_PIPELINE_STAGE_2_CLEAR_BIT`,
  `VK_PIPELINE_STAGE_2_VERTEX_ATTRIBUTE_INPUT_BIT`), "Fixed-Function Vertex
  Processing" (`VK_VERTEX_INPUT_RATE_INSTANCE`), and "Multisample Coverage"
  (alpha to coverage).
- *The OpenGL Shading Language 4.50*, section 8.9 "Texture Functions": outside
  a fragment shader, an implicit level of detail is level 0.
- Olinde Rodrigues, 1840, for the rotation about an axis; Chapter 10 has it as
  a matrix.

## Appendix — the plants script

Reference for sections 1, 2 and 8: the script that grows the five plants and
draws the fern's and the flower's pictures. It is on the `start` branch at
`Assets/Scenes/make_horizon_plants.py` (705 lines, plain Python 3 with the
standard library only), beside what it writes in `Assets/Scenes/Horizon/Plants/`.
Its header carries EZ-Tree's MIT notice, which the credit asks for, and the
pictures `oak.png`, `pine.png` and `ash.png` in `Plants/Textures/` are
EZ-Tree's own, with its `LICENSE.txt` (section 2). To write the plants again,
run it from `Assets/Scenes/`; it makes the folders if they are missing and
prints each plant's triangles and cards per level:

```text
python make_horizon_plants.py [--bare] [--no-crop] [--flip-v] [--black-fill]
```

It is not part of the build: what it writes is on `start` too. It does not read
the three leaf pictures, whose crops and tints are numbers in its tables; the
demo does. The four flags are the controls of sections 1, 2 and 8:

| Flag | Section | What it does |
| --- | --- | --- |
| `--bare` | 1 | the branches only, with no leaves |
| `--no-crop` | 2 | every card the picture's whole square |
| `--flip-v` | 2 | every picture upside down on its card |
| `--black-fill` | 8 | black under the drawn pictures' clear texels |

What it makes:

| File | What it is | Section |
| --- | --- | --- |
| `Horizon/Plants/OakTree.usda`, `PineTree.usda`, `Bush.usda` | the broadleaf, the evergreen and the bush: bark and leaf cards at three levels, LOD2 a solid stand-in | 1, 2, 8 |
| `Horizon/Plants/Fern.usda` | nine ribbon fronds, with no bark; LOD2 is LOD1 again | 8 |
| `Horizon/Plants/Flower.usda` | a stem with two blades, and a head of cards | 8 |
| `Horizon/Plants/Textures/fern.png`, `flower.png` | the two pictures the script draws itself, 256 x 1024 and 256 x 256 | 8 |

And what the file holds, in its order. Section 1 prints `grow` and section 2
`card`; the rest is described where it matters:

| Part | Functions | What they do | Section |
| --- | --- | --- | --- |
| Vectors, and a frame that turns | `add`, `sub`, `scale`, `dot`, `cross`, `mix`, `normalize`, `rotate`, `Frame` | the vector helpers; Rodrigues' rotation; a branch's three unit vectors, and their turns | 1 |
| Growing | `Skeleton`, `grow`, `along`, `spread`, `children`, `leaf_size`, `leaves` | every random number is drawn here, so all three levels of a plant share one skeleton; a point part-way along a branch; where children and leaves leave a branch, turned by the golden angle | 1 |
| Meshing | `Mesh`, `kept`, `tube`, `ribbon`, `card`, `ellipsoid`, `cone` | the mesh a level is made of; every `stride`th section; a branch as a ring of points a section; a frond or a blade; a leaf card; the stand-ins' ball and cones | 1, 2, 8 |
| Levels | `percentile`, `crown_box`, `crowned`, `mesh_level`, `proxy`, `build` | the crown's box and its normal; LOD0 and LOD1 from a level's detail; LOD2, the stand-in; the whole of one plant | 2 |
| Pictures | `write_png`, `segment_distance`, `paint`, `fern_picture`, `flower_picture` | the PNG writer; the fern's frond and the flower's head painted from strokes, alpha falling to 0 over two texels, every clear texel filled with the leaf's mean colour | 8 |
| Writing | `number`, `material_text`, `mesh_text`, `write` | the USD text: materials with their picture and tint, meshes with normals and texture coordinates, one subset per material | 2 |
| The plants | `OAK`, `PINE`, `BUSH`, `FERN`, `FLOWER`, `PLANTS` | the tables of numbers for each plant: its levels of branches, leaves, crop, tint, far colour, stand-in and detail per level, EZ-Tree's presets cut down where noted | 1, 2, 8 |
| `main` | `sha256`, `main` | grows and writes each plant, draws the two pictures, checks that every card's t is 0 at its base, and prints a SHA-256 for each file | 2 |
