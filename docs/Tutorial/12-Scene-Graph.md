# 12 — The Scene Graph

**Goal:** a small solar system — a sun, an orbiting planet, its moon, a camera
riding along — held in a tree of nodes, edited live from an ImGui hierarchy and
inspector, seen through any of its cameras, and culled against the view.

**ROADMAP:** step 13.

**Module:** `Scene` (`Source/PillowFort/Scene/`, `pf::scene`) gains the scene
graph itself — `Scene`, `Node`, and the meshes and cameras that hang on nodes —
plus bounding boxes and frusta (`Bounds`) and the two editing panels
(`ScenePanels`). Nothing in `VulkanGraphics` changes: `SceneRenderer` draws
whatever `DrawItem` list it is given, exactly as in Chapter 11. The test subject
is a demo, `Source/PillowFort/Demos/SceneGraph/` (`pf::demos::scene_graph`).

**Prerequisites:**

- Chapter 07 sections 4 and 9: the ImGui input filter, and panels as free
  functions beside the data they edit.
- Chapter 09 sections 2, 3, and 9: what lives from `Setup` to `Teardown` and
  what survives it, `Resize` receiving the targets, and `Update` before the
  fence wait.
- Chapter 10 section 1 (what a matrix does to a point: its columns are where
  the axes land), section 2 (clip space, its `w`, and Vulkan's depth range
  `[0, 1]`; the projection read by rows; GLM indexes `[column][row]`), section
  3 (`Transform`, and why a
  quaternion), section 4 (`viewMatrix`, and why it uses only the rigid part of
  a matrix), section 6 (controllers hold input, never the pose; yaw and
  pitch), and section 8's box (the cross product and the right-hand rule).
- Chapter 11 section 3 (`MeshData` and submeshes), section 11 (`Material`,
  `DrawItem`, `SceneRenderer::AddMesh`, `AddMaterial`, `RecordDraws`), and
  section 12 (a demo that builds its `DrawItem` list by hand).

Chapter 11's demo built its list of draws by hand: five objects, five
hand-placed `Transform`s, rebuilt every frame. That stops
working the moment one object should move *with* another — a moon around a
planet around a sun — and it cannot hold a scene that comes from a file
(Chapter 14). A scene graph is the structure that both of those need.

### What changes, and where

```text
Source/PillowFort/
  Scene/
    Scene.h, .cpp                       sections 2-7: the graph
    Bounds.h, .cpp                      section 2: boxes; section 9: frusta and culling
    ScenePanels.h, .cpp                 section 8: the hierarchy and the inspector
    Transform.h, .cpp                   section 5: transformFromMatrix
    Camera.h, .cpp                      section 5: the transform moves out
  Demos/
    SceneGraph/SceneGraphDemo.h, .cpp   section 10: the demo
    Cubes/CubesDemo.h, .cpp             section 5: keep the camera's transform beside it
    Meshes/MeshesDemo.h, .cpp           section 5: the same
Source/SandboxGame/Main.cpp             section 10: one line
```

Files are added, so **rerun `GenerateProjects.bat`**.

---

## 1. What a scene graph is for

The engine has one: an **engine-owned node tree** that USD files
import into (Chapter 14) and an ImGui hierarchy and inspector edit while the
program runs. Two things it deliberately is not: nothing in it is ever saved,
and there is no reflection system describing its types — the inspector is
written by hand for the few things a node has. The index states the whole
design in four sentences:

- `Scene` owns a vector of nodes and arrays of meshes, cameras, and materials
  (lights from Chapter 16); nodes refer to their parent, children, and
  components **by index, never by pointer**.
- World transforms are recomputed **top-down, once per frame**, only below
  nodes whose local transform changed.
- **The renderer never walks the tree**: each frame the scene produces a flat
  list of draws — mesh, material, world matrix — and that list is all the GPU
  side sees.
- **The active camera is just a node index**, and a controller moves a camera by
  writing that node's transform.

Every section below is one of those sentences, made into code.

**Why a tree.** Each node has a transform *relative to its parent*. The planet's
transform says "five metres along the orbit's X axis"; the orbit's says "turned
this far around the sun"; the sun's says "two and a half metres up". The
planet's place in the world is all three, multiplied — so turning the orbit
moves the planet, the moon, and the camera riding on the planet, without
touching any of them. That is the whole point: motion is described where it
happens, once, and everything attached follows.

---

## 2. Nodes, and why they are indices

**This is the top of `Source/PillowFort/Scene/Scene.h`:**

```cpp
// Source/PillowFort/Scene/Scene.h
#pragma once

#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/Scene/Camera.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Material.h"
#include "PillowFort/Scene/MeshData.h"
#include "PillowFort/Scene/Transform.h"

#include <glm/glm.hpp>

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace pf::scene {

// Nodes and components are referred to by index into the Scene's arrays.
using NodeIndex = uint32_t;
inline constexpr NodeIndex INVALID_NODE = UINT32_MAX;
inline constexpr NodeIndex ROOT_NODE    = 0;            // every scene has it; it has no parent
inline constexpr uint32_t  NO_COMPONENT = UINT32_MAX;

struct Node
{
    std::string            name;
    NodeIndex              parent = INVALID_NODE;   // INVALID_NODE only for the root
    std::vector<NodeIndex> children;
    Transform              local;                   // relative to the parent
    glm::mat4              world{ 1.0f };           // local -> world; valid after UpdateWorldTransforms
    bool                   localChanged = true;     // world is stale for this node and everything below
    bool                   visible      = true;     // false hides the node and its whole subtree
    uint32_t               mesh   = NO_COMPONENT;   // index into the scene's meshes
    uint32_t               camera = NO_COMPONENT;   // index into the scene's cameras
};
```

**A node is mostly references.** Its parent and children, and which mesh and
camera hang on it — "components", in the usual word — are all `uint32_t`
indices into arrays the `Scene` owns. A node with no mesh has
`mesh == NO_COMPONENT`. Lights join in Chapter 16 the same way, as one more
index.

**Why indices, not pointers.** The nodes live in a `std::vector<Node>`, and a
vector moves its elements when it grows. A `Node* parent` stored in a child
becomes a dangling pointer the moment `AddNode` reallocates — not on the next
node, but on whichever one happens to cross the vector's capacity, which makes
it the kind of bug that appears only in bigger scenes. Indices survive
reallocation, survive copying the whole `Scene`, are half the size of a
pointer, and can be handed to ImGui as an ID or, in a later chapter, to a shader
as a plain number. The cost is an extra indirection — `scene.GetNode(i)` instead
of `node->` — and the obligation below.

**What index stability costs: nodes are never deleted.** An index is only a
stable name as long as nothing shifts. Erasing node 5 from the vector would move
every node after it down one, and every stored index above 5 — in parents,
children, the active camera, the inspector's selection — would silently point
at the wrong node. Supporting deletion means either leaving a hole (a "dead"
flag, and a free list to reuse it, and every loop learning to skip the dead) or
compacting and rewriting every stored index. Both are real designs, and both
are work this tutorial does not need: chapters 12 through 19 build scenes and
edit them, but never remove a node. So **`Scene` has no delete**. To make
something go away, hide it: `visible = false` removes a node and its whole
subtree from what is drawn (section 6). If a later need for deletion appears,
the free-list version is the one to add.

**Two flags.** `localChanged` is the dirty flag of section 4: it says the
node's `world` matrix is out of date. `visible` hides a subtree.

**A mesh, as the scene keeps it**, is the CPU data plus its bounding box:

```cpp
// A mesh as the scene keeps it: the data, and the box around it.
struct Mesh
{
    std::string name;
    MeshData    data;     // kept after upload: the bounds and submesh ranges come from it
    Aabb        bounds;   // in the mesh's own space
};
```

The `MeshData` stays on the CPU after it is uploaded. The bounds are computed
from it (below), and the submesh ranges are needed to build draws — and for
the scenes this tutorial loads, a CPU copy of the geometry is a few megabytes. A
scene of hundreds of megabytes would keep only the bounds and ranges.

### A box around a mesh: `Bounds.h`

`Mesh` needs `Aabb`, and `AddMesh` (section 3) computes one, so the box comes
first. **This is `Source/PillowFort/Scene/Bounds.h`**, whole: the box, and the
frustum that section 9 tests boxes against. The frustum's declarations are here
so the header is written once, and so that `Scene.cpp` compiles from this
section on; section 9 explains them and defines them.

```cpp
// Source/PillowFort/Scene/Bounds.h
#pragma once

#include "PillowFort/Scene/MeshData.h"

#include <glm/glm.hpp>

#include <array>
#include <limits>

namespace pf::scene {

// An axis-aligned bounding box. The defaults are an "empty" box - min above
// max - that growing by any point turns into that point.
struct Aabb
{
    glm::vec3 min{ std::numeric_limits<float>::max() };
    glm::vec3 max{ std::numeric_limits<float>::lowest() };
};

Aabb computeBounds(const MeshData& mesh);                           // around every vertex
Aabb transformBounds(const Aabb& local, const glm::mat4& world);    // a box around the moved box

// Six planes, each (normal, distance) with the normal pointing INTO the
// frustum: a point p is inside a plane when dot(normal, p) + distance >= 0.
struct Frustum
{
    std::array<glm::vec4, 6> planes;   // left, right, top, bottom, near, far (Vulkan's y points down)
};

Frustum frustumFromViewProjection(const glm::mat4& viewProjection);   // world-space planes
bool    intersects(const Frustum& frustum, const Aabb& box);          // false only if surely outside

} // namespace pf::scene
```

**This is `Bounds.cpp`**, which includes `Bounds.h` and `<cmath>`. Its first two
functions are boxes:

```cpp
Aabb computeBounds(const MeshData& mesh)
{
    Aabb box;
    for (const Vertex& vertex : mesh.vertices)
    {
        box.min = glm::min(box.min, vertex.position);
        box.max = glm::max(box.max, vertex.position);
    }
    return box;
}
```

An axis-aligned bounding box (AABB) is the smallest box with sides parallel to
the axes that holds every vertex — computed once, when the mesh is added
(`Scene::AddMesh`, section 3), in the mesh's own space.

Culling (section 9) tests boxes in world space, so a box has to follow its
node's world matrix. Transforming its eight corners and boxing them works; the
same answer comes cheaper by treating the box as a centre and a half-size:

```cpp
Aabb transformBounds(const Aabb& local, const glm::mat4& world)
{
    // Centre and half-size: the centre moves like a point, the half-size by the axes' absolute values.
    const glm::vec3 centre  = 0.5f * (local.min + local.max);
    const glm::vec3 extents = 0.5f * (local.max - local.min);

    const glm::vec3 worldCentre = glm::vec3(world * glm::vec4(centre, 1.0f));
    const glm::mat3 axes(world);
    const glm::vec3 worldExtents = glm::abs(axes[0]) * extents.x
                                 + glm::abs(axes[1]) * extents.y
                                 + glm::abs(axes[2]) * extents.z;
    return Aabb{ .min = worldCentre - worldExtents, .max = worldCentre + worldExtents };
}
```

The centre is a point and moves like one. The half-size along world X is how
far the box's three half-axes — the matrix's axis columns (Chapter 10 section
1) scaled by the half-size — reach along X: each one's X component, *made
positive*, because a box reaches out on both sides. With numbers: a box of
half-size (2, 1) turned 45° about Z has axis columns `(0.707, 0.707, 0)` and
`(-0.707, 0.707, 0)`, so it reaches `|0.707|·2 + |-0.707|·1 = 2.12` along X,
and the same along Y. Its new box is 4.24 metres square, around a box that was
4 by 2:

```text
   +---------+
   |   / \   |     a box turned 45°, and the
   |  /   \  |     axis-aligned box around it
   |  \   /  |
   |   \ /   |
   +---------+
```

The result is the exact box around the moved box. It can be larger than a box
fitted to the moved mesh itself — turn a long, thin mesh 45° and its new box
must hold the old box's corners, not just the mesh — which only makes culling
conservative: something may be drawn that is outside, never skipped while
inside.

---

## 3. The class map

**This is the rest of `Scene.h`:**

```cpp
struct DrawListStats
{
    uint32_t considered = 0;   // submeshes of visible nodes
    uint32_t culled     = 0;   // of those, outside the frustum
};

class Scene
{
public:
    Scene();   // the root node and the default material

    // Building. Each returns the new thing's index.
    NodeIndex AddNode(std::string name, NodeIndex parent = ROOT_NODE, const Transform& local = {});
    uint32_t  AddMesh(std::string name, MeshData data);
    uint32_t  AddCamera(const Camera& camera);
    uint32_t  AddMaterial(const Material& material);

    // Nodes.
    std::size_t NodeCount() const { return m_nodes.size(); }
    const Node& GetNode(NodeIndex node) const;
    Transform&  EditLocal(NodeIndex node);                          // marks it changed
    void        SetMesh(NodeIndex node, uint32_t mesh);
    void        SetCamera(NodeIndex node, uint32_t camera);
    void        SetVisible(NodeIndex node, bool visible);
    void        SetName(NodeIndex node, std::string name);
    bool        Reparent(NodeIndex node, NodeIndex newParent);       // keeps its place in the world
    Transform   WorldTransform(NodeIndex node) const;               // as of the last update
    void        SetWorldTransform(NodeIndex node, const Transform& world);

    // Components.
    std::size_t     MeshCount() const     { return m_meshes.size(); }
    std::size_t     CameraCount() const   { return m_cameras.size(); }
    std::size_t     MaterialCount() const { return m_materials.size(); }
    const Mesh&     GetMesh(uint32_t mesh) const;
    Camera&         GetCamera(uint32_t camera);
    const Camera&   GetCamera(uint32_t camera) const;
    Material&       GetMaterial(uint32_t material);
    const Material& GetMaterial(uint32_t material) const;

    // The camera the scene is seen through: a node with a camera component.
    NodeIndex ActiveCamera() const { return m_activeCamera; }
    void      SetActiveCamera(NodeIndex node);

    // Once per frame, in this order.
    void          UpdateWorldTransforms();
    DrawListStats CollectDraws(std::vector<DrawItem>& out, const Frustum* frustum) const;

private:
    void UpdateSubtree(NodeIndex node, const glm::mat4& parentWorld, bool parentChanged);
    void CollectSubtree(NodeIndex node, std::vector<DrawItem>& out, const Frustum* frustum,
                        DrawListStats& stats) const;
    bool IsInSubtree(NodeIndex node, NodeIndex subtreeRoot) const;

    std::vector<Node>     m_nodes;
    std::vector<Mesh>     m_meshes;
    std::vector<Camera>   m_cameras;
    std::vector<Material> m_materials;
    NodeIndex             m_activeCamera = INVALID_NODE;
};

} // namespace pf::scene
```

Read it as four groups: **building** (each `Add` returns the new thing's
index), **nodes**, **components**, and the **two calls made once per frame**,
in that order — `UpdateWorldTransforms`, then `CollectDraws`.

`GetNode` returns a `const Node&`, and the only ways to change a node are
functions: `EditLocal` for its transform, `SetMesh`, `SetVisible`, `Reparent`,
and the rest. That is not ceremony. Each of those has a rule to keep — editing a
transform must mark the node changed, reparenting must update two children
lists and keep the world position — and a public `Node&` would let any caller
break the rule by accident.

**This is `Scene.cpp`.** It includes `Scene.h`, `<algorithm>`, `<cassert>`, and
`<utility>`, and has no file-scope helpers: everything it does needs the node
array. In order:

```text
Scene.cpp
  Scene::Scene                                         this section
  AddNode, AddMesh, AddCamera, AddMaterial             this section
  GetNode, EditLocal, SetMesh, SetCamera,
    SetVisible, SetName, Get*, SetActiveCamera         this section and section 5
  UpdateWorldTransforms, UpdateSubtree                 section 4
  CollectDraws, CollectSubtree                         section 6
  WorldTransform, SetWorldTransform                    section 5
  IsInSubtree, Reparent                                section 7
```

The **constructor** makes the two things every scene has — the root node, and
the default material that Chapter 11 reserved index 0 for:

```cpp
Scene::Scene()
{
    m_nodes.push_back(Node{ .name = "Root" });                       // ROOT_NODE
    m_materials.push_back(Material{ .name = "Default" });            // DEFAULT_MATERIAL
}
```

There is exactly one root, at index 0, with no parent. Every other node has a
parent, so the tree has one top, and "reparent to the root" is how a node is
detached from everything else. The constructor touches no GPU and cannot fail,
so it is a constructor (the project's rule is only that *fallible GPU* work is
not).

**Adding a node:**

```cpp
NodeIndex Scene::AddNode(std::string name, NodeIndex parent, const Transform& local)
{
    assert(parent < m_nodes.size() && "AddNode: no such parent");

    const NodeIndex index = static_cast<NodeIndex>(m_nodes.size());
    m_nodes.push_back(Node{ .name = std::move(name), .parent = parent, .local = local });
    m_nodes[parent].children.push_back(index);   // after the push_back: it may have moved m_nodes
    return index;
}
```

The comment on the last line is the index argument from section 2, in its
smallest form. `m_nodes[parent]` is looked up *after* the `push_back`; taking a
`Node& parentNode = m_nodes[parent]` before it and using it after would write
into the vector's old, freed storage whenever the push reallocated. An invalid
parent is a programmer mistake, so it is an `assert` (the project's convention),
not a reported failure.

**Components** are added the same way, each returning its index. `AddMesh`
takes the `MeshData` by value and moves it in: the caller usually has just
generated or imported it and has no further use for it.

```cpp
uint32_t Scene::AddMesh(std::string name, MeshData data)
{
    const Aabb bounds = computeBounds(data);
    m_meshes.push_back(Mesh{ .name = std::move(name), .data = std::move(data), .bounds = bounds });
    return static_cast<uint32_t>(m_meshes.size() - 1);
}

uint32_t Scene::AddCamera(const Camera& camera)
{
    m_cameras.push_back(camera);
    return static_cast<uint32_t>(m_cameras.size() - 1);
}

uint32_t Scene::AddMaterial(const Material& material)
{
    m_materials.push_back(material);
    return static_cast<uint32_t>(m_materials.size() - 1);
}
```

**Reading and editing nodes.** Each function asserts that the index is a real
node (and, for a component, a real component or `NO_COMPONENT`), then reads or
assigns. `EditLocal` is the one with a rule in it: it marks the node changed
and hands back its transform to change — `scene.EditLocal(node).translation.x
+= 1.0f`. Marking before the change is safe, because nothing reads the flag
until section 4's update, after the caller is done.

```cpp
const Node& Scene::GetNode(NodeIndex node) const
{
    assert(node < m_nodes.size());
    return m_nodes[node];
}

Transform& Scene::EditLocal(NodeIndex node)
{
    assert(node < m_nodes.size());
    m_nodes[node].localChanged = true;   // the caller is about to change it
    return m_nodes[node].local;
}

void Scene::SetMesh(NodeIndex node, uint32_t mesh)
{
    assert(node < m_nodes.size() && (mesh == NO_COMPONENT || mesh < m_meshes.size()));
    m_nodes[node].mesh = mesh;
}

void Scene::SetCamera(NodeIndex node, uint32_t camera)
{
    assert(node < m_nodes.size() && (camera == NO_COMPONENT || camera < m_cameras.size()));
    m_nodes[node].camera = camera;
}

void Scene::SetVisible(NodeIndex node, bool visible)
{
    assert(node < m_nodes.size());
    m_nodes[node].visible = visible;
}

void Scene::SetName(NodeIndex node, std::string name)
{
    assert(node < m_nodes.size());
    m_nodes[node].name = std::move(name);
}

const Mesh&     Scene::GetMesh(uint32_t mesh) const              { return m_meshes.at(mesh); }
Camera&         Scene::GetCamera(uint32_t camera)                { return m_cameras.at(camera); }
const Camera&   Scene::GetCamera(uint32_t camera) const          { return m_cameras.at(camera); }
Material&       Scene::GetMaterial(uint32_t material)            { return m_materials.at(material); }
const Material& Scene::GetMaterial(uint32_t material) const      { return m_materials.at(material); }
```

---

## 4. World transforms, top-down

A node's `world` matrix is its parent's world matrix times its own local one:
`world = parent.world * local.Matrix()`. That definition has an order built in —
**a parent's world matrix must be up to date before any child's is computed** —
and a cost: a change to a node near the top invalidates everything below it.

**This is `UpdateWorldTransforms`**, called once per frame after everything
that moves nodes has moved them:

```cpp
void Scene::UpdateWorldTransforms()
{
    UpdateSubtree(ROOT_NODE, glm::mat4(1.0f), false);
}
```

```cpp
void Scene::UpdateSubtree(NodeIndex index, const glm::mat4& parentWorld, bool parentChanged)
{
    Node& node = m_nodes[index];

    // A world matrix is stale if this node's local transform changed, or any
    // ancestor's did - parentChanged carries the second down the tree.
    const bool changed = node.localChanged || parentChanged;
    if (changed)
    {
        node.world        = parentWorld * node.local.Matrix();
        node.localChanged = false;
    }

    // Parents before children: a child's world needs its parent's, this frame's.
    for (const NodeIndex child : node.children)
    {
        UpdateSubtree(child, node.world, changed);
    }
}
```

**The order** comes from the recursion: a node is computed, then its children
are visited with its fresh matrix. Walking from the root down gives every child
a parent that is already done. (A flat loop over the vector would work only if
every parent's index were smaller than its children's. `AddNode` creates them
that way, but section 7's reparenting can break it — move node 3 under node 20,
and 3 now comes before its parent.)

**The dirty-propagation rule** is in one line: a node's world matrix is stale if
*its own* local transform changed, **or any ancestor's did**. The first is
`localChanged`; the second arrives as `parentChanged`, passed down the
recursion. So a frame where only the moon's orbit turns recomputes the orbit and
the moon and skips the sun, the planet, the ground, and the sixteen boxes. In a
scene where most things stand still — which is most scenes — most of the matrix
work disappears. The recursion still *visits* every node, which is cheap; making
it skip unchanged subtrees entirely would need a per-node "something below me
changed" flag, which is the next step if a profile ever asks for it.

**Once per frame, and only once.** Every edit — a controller, an animation, the
inspector — writes local transforms and sets flags. None of them touches
`world`. The single update after all of them is what keeps the cost
proportional to what changed, rather than to how many times things changed.
The flip side is that `world` is **last frame's** until the update runs, which
matters to the two functions in section 5 that read it.

---

## 5. The camera becomes a node

> **Jump:** In Chapters 10 and 11 a `Camera` held its own `Transform`, and the
> controllers wrote it. From here the camera is two pieces: a **camera
> component** — the lens, `verticalFov`, `nearPlane`, `farPlane` — in the
> scene's camera array, and the **node** that holds it, whose transform is the
> camera's place in the world. The active camera is a `NodeIndex`. The view
> matrix comes from that node's `world` matrix, so a camera can be parented
> like anything else: the planet camera below rides along with the planet
> because it is the planet's child, with no code saying so. Keep in mind which
> transform a controller now writes: the node's, through its *world* pose,
> because the node may have a parent that is turning.

**This is `Source/PillowFort/Scene/Camera.h`**, losing its transform:

```cpp
// Chapter 12: a lens only. Where the camera is belongs to the scene node that
// holds it; the Cubes and Meshes demos keep a Transform beside theirs.
struct Camera
{
    float verticalFov = glm::radians(60.0f);   // the whole vertical angle, in radians
    float nearPlane   = 0.1f;                  // metres, in world space; must be > 0
    float farPlane    = 500.0f;                // metres, in world space

    // View space to Vulkan's clip space: Y down, depth [0, 1]. aspect is width / height.
    glm::mat4 Projection(float aspect) const;
};
```

Its include of `Transform.h` goes too. `Projection` and `viewMatrix` are
unchanged — `viewMatrix` already took a world matrix rather than a `Camera`,
for exactly this chapter. Near and far are in world metres: the importer
(Chapter 14) converts from the file's units.

**The Cubes and Meshes demos** keep a `Transform` beside their camera instead —
in both headers, after `m_camera`:

```cpp
scene::Transform      m_cameraTransform;   // Chapter 12: beside the camera, not in it
```

and every `m_camera.transform` in their `.cpp` files becomes `m_cameraTransform`.
Nothing else in them changes; they have no scene to put a camera in.

### Driving a camera node

A controller works on a pose in the world (Chapter 10 section 6: yaw about the
*world's* up). A camera node's local transform is relative to its parent, which
may be rotated or scaled — Chapter 14's imported files routinely put everything
under a rotated, scaled root. So the scene offers the node's transform in world
terms, and takes one back:

```cpp
Transform Scene::WorldTransform(NodeIndex node) const
{
    return transformFromMatrix(GetNode(node).world);
}
```

```cpp
void Scene::SetWorldTransform(NodeIndex node, const Transform& world)
{
    // The local transform that puts the node there, given where its parent is.
    const NodeIndex parent      = GetNode(node).parent;
    const glm::mat4 parentWorld = parent == INVALID_NODE ? glm::mat4(1.0f) : m_nodes[parent].world;
    EditLocal(node) = transformFromMatrix(glm::inverse(parentWorld) * world.Matrix());
}
```

`SetWorldTransform` solves `parentWorld · local = world` for `local`: multiply
both sides **on the left** by `inverse(parentWorld)`, which cancels it, since
`inverse(P) · P · L = L`. The side matters: matrix products do not commute, and
`P · L · inverse(P)` is a different matrix. Both functions read `world`
matrices as of the last update, which is what a controller wants — it continues
from where the camera was drawn last frame.

Both need to turn a matrix back into a `Transform`: a translation, a rotation,
and a scale. That builds on two of Chapter 10's ideas — a matrix's columns, and
the cross product — and adds what is new here: a column's length, handedness,
and the determinant. Later chapters point back to this passage for them.

### Reading a matrix: axes, cross products, and the determinant

**A column's length is the scale.** Chapter 10 section 1 read a matrix by its
columns: column *i* is where axis *i* lands, and column 3 is where the origin
lands — which is why Chapter 10 section 4 could read a camera's eye from column
3. What is new here is that a column has a length as well as a direction, and
the length is how much that axis was stretched. A worked example: scale by 2
along X, then turn 90° about +Y.

```text
               column 0   column 1   column 2   column 3
               X lands    Y lands    Z lands    origin lands
row 0  x   [      0          0          1          0     ]
row 1  y   [      0          1          0          0     ]
row 2  z   [     -2          0          0          0     ]
row 3  w   [      0          0          0          1     ]
```

Column 0 is `(0, 0, -2)`: length 2, which is the scale, pointing along −Z,
which is where a quarter turn about +Y sends X. Reading a transform back out of
a matrix is reading its columns: their lengths are the scale, and their
directions are the rotation.

**The cross product, in components.** Chapter 10 section 8's box gave the
cross product as an arrow at right angles to both inputs, with the right-hand
rule for its direction. Taking a matrix apart needs it computed, from the
components:

```text
cross(a, b) = (a.y·b.z - a.z·b.y,   a.z·b.x - a.x·b.z,   a.x·b.y - a.y·b.x)
```

With the world's own axes,
`cross((1,0,0), (0,1,0)) = (0·0 - 0·1, 0·0 - 1·0, 1·1 - 0·0) = (0, 0, 1)`:
X cross Y is Z. That is what **right-handed** means for a set of axes, and why
Chapter 10 calls the world right-handed. (The cross product's length is the
area of the parallelogram `a` and `b` span, so it is zero for parallel vectors.)

**Handedness, and a mirror.** Take a matrix's three axis columns `x`, `y`, and
`z`, and ask whether `cross(x, y)` points the same way as `z`. The **dot
product** answers that: `dot(a, b) = a.x·b.x + a.y·b.y + a.z·b.z`, which is
Chapter 11's `cos θ` multiplied by both lengths — positive when two vectors
point the same general way, negative when they point apart. Rotations and
positive scales keep the axes right-handed, so `dot(cross(x, y), z) > 0`. A
mirror reverses one axis. Scale X by −1, so `x = (-1, 0, 0)`: then
`cross(x, y) = (0, 0, -1)`, and its dot with `z = (0, 0, 1)` is −1. The axes
are now **left-handed** — your left hand's rule fits them — and no rotation
can produce that, just as turning a right hand never makes it a left one.

**That number is the determinant.** `dot(cross(x, y), z)` of a 3×3 matrix's
columns is the matrix's **determinant**, which `glm::determinant` computes.
Its size is how much the matrix scales volumes — 2 for the example above,
which stretched one axis by 2 — and its **sign says whether the matrix
mirrors**: negative exactly when it does. Chapter 14 tests that sign to find
mirrored USD prims, Chapters 15 and 19 to keep surface tangents right under a
mirror, and Chapter 25 builds a grass blade's sideways axis with a cross
product.

**This is the end of `Transform.h`**:

```cpp
// Chapter 12: the TRS that a matrix is, as closely as a Transform can say it.
// Exact for anything built from Transforms whose scales are uniform; any shear
// is dropped, and a mirror becomes a negative X scale.
Transform transformFromMatrix(const glm::mat4& matrix);
```

**and of `Transform.cpp`:**

```cpp
Transform transformFromMatrix(const glm::mat4& matrix)
{
    // The upper 3x3's columns are the transformed X, Y, and Z axes: their
    // lengths are the scale, their directions the rotation. Column 3 is the
    // translation.
    glm::vec3 x(matrix[0]);
    glm::vec3 y(matrix[1]);
    glm::vec3 z(matrix[2]);

    Transform result;
    result.translation = glm::vec3(matrix[3]);
    result.scale       = { glm::length(x), glm::length(y), glm::length(z) };

    // A left-handed set of axes is a mirror, which no rotation can produce.
    // Put the flip in the scale instead.
    if (glm::dot(glm::cross(x, y), z) < 0.0f)
    {
        result.scale.x = -result.scale.x;
        x = -x;
    }

    // Make the axes exactly perpendicular and unit length (Gram-Schmidt), so
    // they are a rotation even when the matrix had shear; the shear is lost.
    x = glm::normalize(x);
    y = glm::normalize(y - glm::dot(y, x) * x);
    z = glm::cross(x, y);
    result.rotation = glm::quat_cast(glm::mat3(x, y, z));
    return result;
}
```

For a translate-rotate-scale matrix the three axis columns are perpendicular,
so reading them back is exact. Two cases need care:

- **A mirror.** The determinant's sign finds it. The flip is moved into
  `scale.x` and out of the axes, so that what is left is a rotation. This is
  the convention Chapter 14's importer relies on.
- **Shear.** A parent scaled unevenly *and* rotated relative to its child gives
  the child a world matrix whose axes are no longer perpendicular:

```text
 the child's axes, turned 45°:          after the parent's scale of 2 along X:
 90° apart                              127° apart

      y       x                          y                         x
       \     /                            '-.                   .-'
        \   /                                '-.             .-'
         \ /                                    '-.       .-'
          o                                        '-. .-'
                                                      o
```

Translation, rotation, and scale cannot express that. Making the axes
perpendicular again gives the nearest rotation and drops the shear. The method
is **Gram-Schmidt**, and it rests on one more use of the dot product: with `x`
unit length, `dot(y, x)` is how far `y` reaches along `x`, so subtracting
`dot(y, x) · x` from `y` leaves only the part of `y` at right angles to `x`.
Keep X, remove X's part from Y and normalize, and take Z as their cross
product — the three lines at the end of `transformFromMatrix`. That is a
real loss, and it is why a scene graph that stores TRS works best with
**uniform scale on anything that has children** — the sun here is sized by its
mesh, not by its node, for this reason. It is also why reparenting under an
unevenly scaled parent cannot always keep a node exactly where it was (section
7): the local transform it would need has shear, and the shear is dropped.

### The active camera

```cpp
void Scene::SetActiveCamera(NodeIndex node)
{
    assert(node < m_nodes.size() && m_nodes[node].camera != NO_COMPONENT && "not a camera node");
    m_activeCamera = node;
}
```

Asserted, because pointing the active camera at a node with no camera is a bug
in the caller — the demo then has no lens to project with.

---

## 6. The flat draw list

**The renderer never walks the tree.** `SceneRenderer::RecordDraws` from Chapter
11 takes a `span` of `DrawItem`s and knows nothing of nodes. The scene turns
itself into that list once per frame, after the world update:

```cpp
DrawListStats Scene::CollectDraws(std::vector<DrawItem>& out, const Frustum* frustum) const
{
    out.clear();
    DrawListStats stats;
    CollectSubtree(ROOT_NODE, out, frustum, stats);
    return stats;
}
```

```cpp
void Scene::CollectSubtree(NodeIndex index, std::vector<DrawItem>& out, const Frustum* frustum,
                           DrawListStats& stats) const
{
    const Node& node = m_nodes[index];
    if (!node.visible) { return; }   // and nothing below it either

    if (node.mesh != NO_COMPONENT)
    {
        const Mesh&    mesh  = m_meshes[node.mesh];
        const uint32_t parts = static_cast<uint32_t>(mesh.data.submeshes.size());
        stats.considered += parts;

        // Culled as a whole: the bounds are the mesh's, not each submesh's.
        if (frustum != nullptr && !intersects(*frustum, transformBounds(mesh.bounds, node.world)))
        {
            stats.culled += parts;
        }
        else
        {
            for (uint32_t submesh = 0; submesh < parts; ++submesh)
            {
                out.push_back(DrawItem{ .world    = node.world,
                                        .mesh     = node.mesh,
                                        .submesh  = submesh,
                                        .material = mesh.data.submeshes[submesh].materialIndex });
            }
        }
    }

    for (const NodeIndex child : node.children)
    {
        CollectSubtree(child, out, frustum, stats);
    }
}
```

One `DrawItem` per submesh of every visible mesh node, carrying the node's
world matrix and the submesh's material. A hidden node returns before its
children are visited, which is what makes `visible` hide a subtree. The frustum
test is section 9's; pass `nullptr` and nothing is culled.

**Why a list in between**, rather than having `SceneRenderer` take the `Scene`?
Two reasons, each of which a later chapter cashes in:

- **The two sides change independently.** Chapter 14 fills the scene from a
  file without touching `SceneRenderer`, and the renderer's later growth —
  descriptor sets for materials (Chapter 15), shadow passes (Chapter 17) — does
  not change how the scene walks its tree. The list is the whole interface.
- **A list can be kept, reused, and rearranged.** Chapter 17 collects a second,
  unculled list for the shadow pass, and Chapter 19 groups items with the same
  mesh and material into instanced draws — neither is possible on a tree walk
  that draws as it goes. And the vector keeps its capacity from frame to frame,
  so after the first frame building it allocates nothing.

`CollectDraws` clears the output first, because a draw list is a result, not
something to append to; the stats report how many submeshes were considered and
how many culled, for the panel.

---

## 7. Reparenting without moving

Dragging a node onto another in the hierarchy (section 8) makes it that node's
child. What should happen to the node's position? Keeping its *local* transform
would make it jump: "two metres to the right" means somewhere else under a new
parent. Users expect it to stay where it is in the world and only change what it
moves with. So `Reparent` keeps the world matrix and solves for the new local
transform — section 5's equation, with the new parent:

```cpp
bool Scene::Reparent(NodeIndex node, NodeIndex newParent)
{
    assert(node < m_nodes.size() && newParent < m_nodes.size());

    // The root has no parent to change, and a node cannot go under itself or
    // its own descendant: that would make a loop, which is not a tree.
    if (node == ROOT_NODE || IsInSubtree(newParent, node)) { return false; }
    const NodeIndex oldParent = m_nodes[node].parent;
    if (oldParent == newParent) { return true; }

    // Stay where it is in the world: compute the local transform that, under
    // the new parent, gives the same world matrix. Uses the world matrices of
    // the last UpdateWorldTransforms.
    const glm::mat4 local = glm::inverse(m_nodes[newParent].world) * m_nodes[node].world;

    std::vector<NodeIndex>& siblings = m_nodes[oldParent].children;
    siblings.erase(std::find(siblings.begin(), siblings.end(), node));
    m_nodes[newParent].children.push_back(node);
    m_nodes[node].parent = newParent;
    EditLocal(node)      = transformFromMatrix(local);
    return true;
}
```

```cpp
bool Scene::IsInSubtree(NodeIndex node, NodeIndex subtreeRoot) const
{
    // Walk up from `node`: if we pass subtreeRoot, node is below it.
    for (NodeIndex at = node; at != INVALID_NODE; at = m_nodes[at].parent)
    {
        if (at == subtreeRoot) { return true; }
    }
    return false;
}
```

**The loop check.** A node cannot become a child of itself or of anything below
it: the tree would become a cycle, `UpdateSubtree` would recurse forever, and
nothing would have the root as an ancestor. `IsInSubtree` walks *up* from the
proposed parent — parents are one index each, so this is short — and refuses if
it meets the node. The root cannot be reparented at all.

**The order of the edits** keeps the tree valid at every step: compute the new
local transform from the old world matrices first, then move the index from the
old parent's children to the new one's, then set the parent and the transform.
The node is marked changed, so the next update recomputes its world matrix —
which comes out the same as before, which is the point.

---

## Checkpoint

The scene graph itself is complete: nodes, world transforms, the flat draw
list, and cameras as nodes. Sections 8 and 9 add the panels that edit it and
the culling that trims its list, and section 10's demo uses all of it. You can
watch the tree move before either. Type section 10 now, leaving out the four
lines that need section 8:

- in `SceneGraphDemo.h`, the `ScenePanels.h` include and the `m_editor`
  member;
- in `Update`, the two lines that draw the Scene and Inspector panels.

And give `Bounds.cpp` first versions of section 9's two functions, which cull
nothing, so the program links:

```cpp
// First versions, until section 9 replaces both: a frustum with no planes, and
// every box inside it. Nothing is culled.
Frustum frustumFromViewProjection(const glm::mat4& /*viewProjection*/) { return Frustum{}; }
bool    intersects(const Frustum& /*frustum*/, const Aabb& /*box*/)    { return true; }
```

Build and run `SandboxGame --demo Scene`. You should see:

- the sun, the planet orbiting it, the moon orbiting the planet, a ring of
  sixteen red boxes, and the ground, lit as in Chapter 11;
- the orbit and fly controllers working as in Chapters 10 and 11;
- under "Look through", **PlanetCamera**: the view rides along with the planet
  as it orbits, because the camera node is the planet's child and nothing else
  says so. **MainCamera** brings you back where you were;
- the "Scene graph" panel's "Culled" count at 0 whatever you look at: section 9
  has not been written.

Then carry on with section 8.

---

## 8. Editing it live

The hierarchy shows the tree and lets you pick and rearrange nodes; the
inspector edits the picked node. Both are free functions over a `Scene&`, for
Chapter 07 section 9's reasons, and the little state they share between frames
is a struct the demo owns. **This is `Source/PillowFort/Scene/ScenePanels.h`:**

```cpp
// Source/PillowFort/Scene/ScenePanels.h
#pragma once

#include "PillowFort/Scene/Scene.h"

#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>

namespace pf::scene {

// What the two panels remember between frames. The demo owns it.
struct SceneEditorState
{
    NodeIndex selected = INVALID_NODE;

    // The inspector shows rotation as three angles, but the node stores a
    // quaternion. These are the angles last shown, and the quaternion they were
    // shown for - Chapter 12 section 8 says why both are kept.
    glm::vec3 eulerDegrees{ 0.0f };
    glm::quat eulerSource{ 0.0f, 0.0f, 0.0f, 0.0f };   // matches no real rotation: "nothing shown yet"
    NodeIndex eulerNode = INVALID_NODE;
};

void drawSceneHierarchy(Scene& scene, SceneEditorState& state);   // "Scene": the tree; drag to reparent
void drawNodeInspector(Scene& scene, SceneEditorState& state);    // "Inspector": the selected node

} // namespace pf::scene
```

### The hierarchy

**This is `ScenePanels.cpp`**, which includes `<imgui.h>`, `<array>`,
`<cstdio>`, and `<cstring>`. One row per node, drawn recursively:

```cpp
// File scope, above the namespace block. One row of the tree, and its children
// below it. Reparenting is only *requested* here, in `reparent`: the tree is
// being walked through the very children lists a reparent would change.
static void drawNodeRow(pf::scene::Scene& scene, pf::scene::SceneEditorState& state,
                        pf::scene::NodeIndex index, std::array<pf::scene::NodeIndex, 2>& reparent)
{
    using namespace pf::scene;
    const Node& node = scene.GetNode(index);

    ImGuiTreeNodeFlags flags = ImGuiTreeNodeFlags_OpenOnArrow | ImGuiTreeNodeFlags_DefaultOpen
                             | ImGuiTreeNodeFlags_SpanAvailWidth;
    if (node.children.empty())    { flags |= ImGuiTreeNodeFlags_Leaf; }
    if (index == state.selected)  { flags |= ImGuiTreeNodeFlags_Selected; }

    // The label says what hangs on the node; the ID is the index, so two nodes
    // with the same name are still two rows.
    const char* tag = node.camera == NO_COMPONENT ? (node.mesh == NO_COMPONENT ? "" : "  [mesh]")
                    : (index == scene.ActiveCamera() ? "  [camera, active]" : "  [camera]");
    ImGui::PushID(static_cast<int>(index));
    const bool open = ImGui::TreeNodeEx("node", flags, "%s%s%s", node.name.c_str(), tag,
                                        node.visible ? "" : "  (hidden)");
    if (ImGui::IsItemClicked() && !ImGui::IsItemToggledOpen()) { state.selected = index; }

    // Drag a row onto another to make it that row's child.
    if (index != ROOT_NODE && ImGui::BeginDragDropSource())
    {
        ImGui::SetDragDropPayload("PF_NODE", &index, sizeof(index));
        ImGui::Text("Move %s", node.name.c_str());
        ImGui::EndDragDropSource();
    }
    if (ImGui::BeginDragDropTarget())
    {
        if (const ImGuiPayload* payload = ImGui::AcceptDragDropPayload("PF_NODE"))
        {
            NodeIndex dragged = INVALID_NODE;
            std::memcpy(&dragged, payload->Data, sizeof(dragged));
            reparent = { dragged, index };
        }
        ImGui::EndDragDropTarget();
    }

    if (open)
    {
        // Safe to walk while drawing: nothing in this panel changes the tree
        // until the walk is over.
        for (const NodeIndex child : node.children)
        {
            drawNodeRow(scene, state, child, reparent);
        }
        ImGui::TreePop();
    }
    ImGui::PopID();
}
```

- **IDs.** ImGui identifies widgets by their label unless told otherwise, and
  two nodes can share a name. `PushID(index)` makes every row's ID its node
  index — another place where indices pay off.
- **Selection** is the node index in `state.selected`. Clicking the arrow opens
  or closes a row without selecting it.
- **Drag and drop**: a row is a drag source carrying its node index, and every
  row is a drop target. The drop does **not** reparent on the spot. The rows
  are being drawn by walking the very `children` vectors a reparent would edit,
  and erasing from a vector that a loop above is iterating is undefined
  behaviour. So the drop records `{ node, new parent }`, and the panel applies
  it after the walk:

```cpp
void drawSceneHierarchy(Scene& scene, SceneEditorState& state)
{
    // Right-hand side, below Chapter 09's demo picker, which grows by a row with every demo.
    ImGui::SetNextWindowPos(ImVec2(ImGui::GetIO().DisplaySize.x - 330.0f, 280.0f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(320.0f, 220.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Scene"))
    {
        std::array<NodeIndex, 2> reparent{ INVALID_NODE, INVALID_NODE };   // { node, new parent }
        drawNodeRow(scene, state, ROOT_NODE, reparent);

        // Now that nothing is walking the tree, change it.
        if (reparent[0] != INVALID_NODE)
        {
            scene.Reparent(reparent[0], reparent[1]);   // false (and nothing happens) for a loop
        }
    }
    ImGui::End();
}
```

`Reparent` refuses a drop that would make a loop, so dragging a node onto its
own child simply does nothing.

### The inspector, and angles over a quaternion

```cpp
void drawNodeInspector(Scene& scene, SceneEditorState& state)
{
    ImGui::SetNextWindowPos(ImVec2(ImGui::GetIO().DisplaySize.x - 330.0f, 510.0f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(320.0f, 200.0f), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Inspector"))
    {
        if (state.selected == INVALID_NODE || state.selected >= scene.NodeCount())
        {
            ImGui::TextUnformatted("Select a node in the Scene panel.");
        }
        else
        {
            const NodeIndex index = state.selected;
            const Node&     node  = scene.GetNode(index);

            // Name. ImGui edits a fixed buffer, not a std::string.
            char name[128];
            std::snprintf(name, sizeof(name), "%s", node.name.c_str());
            if (ImGui::InputText("Name", name, sizeof(name))) { scene.SetName(index, name); }

            bool visible = node.visible;
            if (ImGui::Checkbox("Visible", &visible)) { scene.SetVisible(index, visible); }

            // Translation and scale edit the local transform directly. EditLocal
            // only when something changed, so an untouched node is not marked dirty.
            ImGui::SeparatorText("Local transform");
            Transform local = node.local;
            bool      edited = false;
            edited |= ImGui::DragFloat3("Translation", &local.translation.x, 0.05f);

            // Rotation: angles in the UI, a quaternion in the node. Re-derive the
            // angles only when the quaternion changed from outside - another
            // node selected, an animation, a controller - never from our own
            // edit, so the numbers being dragged stay the numbers shown.
            if (state.eulerNode != index || state.eulerSource != node.local.rotation)
            {
                state.eulerDegrees = glm::degrees(glm::eulerAngles(node.local.rotation));
                state.eulerSource  = node.local.rotation;
                state.eulerNode    = index;
            }
            if (ImGui::DragFloat3("Rotation (deg)", &state.eulerDegrees.x, 0.5f))
            {
                local.rotation    = glm::quat(glm::radians(state.eulerDegrees));
                state.eulerSource = local.rotation;
                edited = true;
            }

            if (ImGui::DragFloat3("Scale", &local.scale.x, 0.01f))
            {
                // Never exactly 0, which a drag reaches by rounding to "%.3f": a node scaled to
                // nothing has no inverse, and Reparent, SetWorldTransform, and the normal matrix
                // all take one. 0.001 is the smallest the field shows. A negative scale, a
                // mirror, is fine.
                for (int axis = 0; axis < 3; ++axis)
                {
                    if (local.scale[axis] > -0.001f && local.scale[axis] < 0.001f)
                    {
                        local.scale[axis] = local.scale[axis] < 0.0f ? -0.001f : 0.001f;
                    }
                }
                edited = true;
            }
            if (edited) { scene.EditLocal(index) = local; }

            if (node.mesh != NO_COMPONENT)
            {
                const Mesh& mesh = scene.GetMesh(node.mesh);
                ImGui::SeparatorText("Mesh");
                ImGui::Text("%s: %zu vertices, %zu submesh(es)", mesh.name.c_str(),
                            mesh.data.vertices.size(), mesh.data.submeshes.size());
            }

            if (node.camera != NO_COMPONENT)
            {
                Camera& camera = scene.GetCamera(node.camera);
                ImGui::SeparatorText("Camera");
                float fovDegrees = glm::degrees(camera.verticalFov);
                if (ImGui::SliderFloat("Vertical FOV", &fovDegrees, 20.0f, 120.0f, "%.0f deg"))
                {
                    camera.verticalFov = glm::radians(fovDegrees);
                }
                if (index != scene.ActiveCamera() && ImGui::Button("Look through this camera"))
                {
                    scene.SetActiveCamera(index);
                }
            }
        }
    }
    ImGui::End();
}
```

Translation and scale are edited on a copy, written back through `EditLocal`
only if something changed — so selecting a node does not mark it dirty and cost
its subtree a recompute every frame.

**Scale never reaches 0.** A node scaled to nothing has no inverse, and three
things invert one: section 7's `Reparent` (the new parent's world matrix),
section 5's `SetWorldTransform` (the camera's parent's), and Chapter 11
section 13's normal matrix (the node's own). Each divides by zero and hands
back NaN — floating point's "not a number" — and a node dropped onto a parent
scaled to 0 keeps the NaN in its local transform even after the scale comes
back. ImGui rounds a dragged value to the `%.3f` it shows, so a drag through 0
lands on it exactly. The inspector therefore moves a component within 0.001 of
0 to 0.001, the smallest the field shows, or to −0.001 if it was negative: a
negative scale is a mirror (section 5), which `transformFromMatrix` keeps, and
it stays legal.

**Rotation is the hard one.** The node stores a quaternion (Chapter 10 section
3), and nobody can type one. The inspector shows three Euler angles, in degrees,
and converts. The obvious way — convert the quaternion to angles every frame,
let ImGui edit them, convert back — fails in two ways you will see:

- **The same rotation has more than one set of angles.** A turn of 94° about Y
  can come back from `glm::eulerAngles` as `(180, 86, 180)`: the same
  orientation, written differently. Reparent the moon under the sun in this
  chapter's demo and its inspector shows exactly that. Converting every frame,
  the fields can jump from one form to the other in the middle of a drag.
- **Near ±90° of pitch, angles lose a degree of freedom** (gimbal lock). Yaw and
  roll then turn about the same axis, a drag on one moves the other, and the
  round trip through the quaternion can snap the values.

The fix is to **remember what was shown**. `state.eulerDegrees` holds the angles
the user is looking at, and `state.eulerSource` the quaternion they were made
from. While the node's rotation still equals `eulerSource`, the inspector keeps
showing the remembered angles — so the numbers being dragged are exactly the
numbers on screen, and are only ever converted *to* a quaternion. Only when the
rotation changed from somewhere else — another node selected, an animation, a
controller turning a camera — are the angles derived afresh. That is the whole
trick, and it is why the state struct has three fields for one widget.

**Cameras** get their field of view and a button that makes them the active
camera, so any camera node can be looked through.

---

## 9. Culling on the CPU

Everything in `CollectDraws` so far is drawn whether the camera can see it or
not. **Frustum culling** skips a mesh whose bounding box lies completely outside
the camera's view volume — the *frustum*, a pyramid with its top cut off at the
near plane. It is the cheapest large saving a renderer has: turn around in a
scene, and most of it is behind you. This section does it on the CPU, one box
per mesh node. Chapter 19 leans on this same per-node test for thousands of
instanced trees, and the grass chapters (25-27) move the idea to the GPU, in a
compute shader, where there are far too many blades to test one by one on the
CPU.

**This is the rest of `Bounds.cpp`**: the frustum's two functions, which
section 2's `Bounds.h` declared, and which use section 2's boxes.

### Six planes from one matrix

> **Jump:** until now a matrix has been something a point is multiplied by, to
> move it. Here its **rows** are read on their own, and each one is a *plane*.
> Two ideas make that work, both below: a plane can be written as four
> numbers, and multiplying by a matrix is one dot product per row, which
> Chapter 10 section 2 used to read the projection. Keep both in mind through
> `frustumFromViewProjection`.

**A plane as four numbers.** A plane is a flat wall through space. Write it as
`(a, b, c, d)`: `(a, b, c)` is its **normal**, the direction it faces, and for
a point `p` the value `a·p.x + b·p.y + c·p.z + d` — that is,
`dot(normal, p) + d` — is zero on the wall, positive on the side the normal
faces, and negative behind it. For example, `(1, 0, 0, -2)` is the wall
`x = 2`, facing +X:

```text
            behind (< 0)   |   in front (>= 0)
                           |
       (1, 0, 0)  •        |        •  (3, 0, 0)
       1·1 - 2 = -1        |        1·3 - 2 = 1
                           |---> normal (1, 0, 0)
                         x = 2
```

The point (3, 0, 0) gives `1·3 − 2 = 1`: in front of the wall, by one metre.
The point (1, 0, 0) gives −1: behind it. The value is a true distance only when
the normal has length 1 — divide all four numbers by the normal's length to
make it so. A frustum is six such walls with their normals pointing inward, and
a point is inside it when it is in front of all six.

**Rows as planes.** Chapter 10 section 2 read the projection by rows: output
*i* is row *i* dotted with `(p, 1)`, so clip `x` is `dot(row0, p)`, `y` is
`dot(row1, p)`, `z` is `dot(row2, p)`, and `w` is `dot(row3, p)`. A row is four
numbers dotted with `(p, 1)` — exactly how a plane is evaluated. So every row
of a matrix, and every sum or difference of rows, is a plane.

Now the frustum. After the divide, a point is on screen when
`-1 <= x/w <= 1` (Chapter 10 section 2), and the same for `y`. `w` is the
distance in front of the camera, so it is positive for anything in front, and
multiplying through by it gives `-w <= x <= w`: the same test, without the
divide, which is the form the planes need. So a world point `p` is visible when
its clip position `c = M p`, with `M` the view-projection matrix, satisfies

```text
-w <= x <= w        -w <= y <= w        0 <= z <= w
```

— the last is Vulkan's depth range, from Chapter 10 section 2. Each of the six
inequalities is one wall. `x >= -w`, for instance, is
`dot(row0, p) >= -dot(row3, p)`, which is `dot(row3 + row0, p) >= 0`: the plane
`row3 + row0`, with everything visible in front of it. Reading the six planes
out of the view-projection matrix this way is the Gribb-Hartmann method. All
six:

```cpp
Frustum frustumFromViewProjection(const glm::mat4& viewProjection)
{
    // Each plane is a sum or difference of rows of M (section 9). GLM stores
    // columns, so row i is (M[0][i], M[1][i], M[2][i], M[3][i]).
    const auto row = [&](int i) {
        return glm::vec4(viewProjection[0][i], viewProjection[1][i], viewProjection[2][i], viewProjection[3][i]);
    };

    Frustum frustum{ .planes = {
        row(3) + row(0),   // left:   x >= -w
        row(3) - row(0),   // right:  x <=  w
        row(3) + row(1),   // y >= -w (the top of the screen: Vulkan's y points down)
        row(3) - row(1),   // y <=  w
        row(2),            // near:   z >= 0 - not row3 + row2, which is OpenGL's z >= -w
        row(3) - row(2),   // far:    z <= w
    } };

    // Unit normals, so dot(normal, p) + distance is a real distance in metres.
    for (glm::vec4& plane : frustum.planes)
    {
        plane /= glm::length(glm::vec3(plane));
    }
    return frustum;
}
```

Two details that are easy to get wrong:

- **The near plane is `row2` alone**, because Vulkan's depth starts at 0. OpenGL
  tutorials use `row3 + row2`, from OpenGL's `z >= -w`; with this projection
  that puts the near plane behind the camera, and nothing very close is ever
  culled — wrong in the safe direction, which is why it survives unnoticed.
- **GLM indexes `[column][row]`**, so row `i` is gathered from the four columns.

The planes are normalized so that `dot(normal, p) + plane.w` — the fourth
number, `d` above — is a distance in metres. The box test does not need that,
but anything that culls by a radius — a bounding sphere, say — does.

### Box against frustum

```cpp
bool intersects(const Frustum& frustum, const Aabb& box)
{
    const glm::vec3 centre  = 0.5f * (box.min + box.max);
    const glm::vec3 extents = 0.5f * (box.max - box.min);
    for (const glm::vec4& plane : frustum.planes)
    {
        // How far the box reaches towards the plane's normal, and where its
        // centre is. If even the nearest corner is behind the plane, the whole
        // box is outside the frustum.
        const glm::vec3 normal(plane);
        const float     reach    = glm::dot(glm::abs(normal), extents);
        const float     distance = glm::dot(normal, centre) + plane.w;
        if (distance + reach < 0.0f)
        {
            return false;
        }
    }
    return true;   // inside or crossing every plane: possibly visible
}
```

For each plane, the question is whether even the box's corner *furthest along
the plane's normal* is behind it. That corner's distance is the centre's
distance plus the box's reach toward the normal — the same absolute-value trick
as `transformBounds` (section 2). If it is behind any one plane, the whole box
is outside and the mesh is culled. If not, it is drawn.

This test is **conservative**: a box near a corner of the frustum can be outside
the frustum while in front of every single plane, and is then drawn
needlessly. It never culls something visible, and the needless draws are few.
Exact tests exist and are rarely worth their cost.

`CollectSubtree` (section 6) calls `transformBounds` on the mesh's bounds with
the node's world matrix, then `intersects`. A culled node's children are still
visited: a child's box is not inside its parent's.

---

## 10. The test scene

**This is the Scene graph demo**: a sun with a planet orbiting it, a moon
orbiting the planet, a camera riding the planet, a ring of boxes, a ground, and
a main camera. If you typed it at section 7's checkpoint, two things remain:
the four lines you left out for section 8, and section 9's `Bounds.cpp` in
place of the two first versions. Read on for why each part has its shape.

**This is `Source/PillowFort/Demos/SceneGraph/SceneGraphDemo.h`:**

```cpp
// Source/PillowFort/Demos/SceneGraph/SceneGraphDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Scene.h"
#include "PillowFort/Scene/ScenePanels.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"

#include <vector>

namespace pf::demos::scene_graph {

class SceneGraphDemo final : public Demo
{
public:
    SceneGraphDemo();   // builds the whole scene - CPU only

    const char*          Name() const override { return "Scene graph"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    void                 Record(const RecordContext& frame) override;
    void                 Teardown() override;
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    void BuildScene();
    void DrawPanel();

    // GPU objects: Setup to Teardown.
    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;

    // CPU state: survives Teardown, so every edit is still there after a switch.
    scene::Scene                  m_scene;
    scene::SceneEditorState       m_editor;
    scene::CameraControls         m_controls;
    scene::NodeIndex              m_controlledCamera = scene::INVALID_NODE;   // whose pose the controllers hold input for
    scene::NodeIndex              m_planetOrbit = scene::INVALID_NODE;        // the pivots the animation turns
    scene::NodeIndex              m_moonOrbit   = scene::INVALID_NODE;
    std::vector<scene::DrawItem>  m_draws;
    scene::DrawListStats          m_stats;
    scene::Frustum                m_frustum{};
    VkExtent2D                    m_extent{ 1, 1 };    // from Resize: the aspect ratio for culling
    bool                          m_animate       = true;
    bool                          m_culling       = true;
    bool                          m_freezeFrustum = false;
    float                         m_planetAngle   = 0.0f;
    float                         m_moonAngle     = 0.0f;
    float                         m_time          = 0.0f;
    float                         m_deltaTime     = 0.0f;
};

} // namespace pf::demos::scene_graph
```

This time **almost everything is CPU state** that survives `Teardown`: the whole
`Scene`, the editor's selection, the controllers. A switch to another demo and
back finds every edit where it was left. Only the `SceneRenderer` is made and
destroyed with the GPU.

**This is `SceneGraphDemo.cpp`.** It includes `DemoPanel.h`, `MeshGenerators.h`,
`<imgui.h>`, `<cmath>`, and `<string>`. The generators make every mesh with material 0, so a
small helper above the namespace gives one another:

```cpp
// File scope, above the namespace block. A generated mesh is one submesh with
// material 0; this gives it another.
static pf::scene::MeshData withMaterial(pf::scene::MeshData mesh, uint32_t material)
{
    for (pf::scene::Submesh& submesh : mesh.submeshes)
    {
        submesh.materialIndex = material;
    }
    return mesh;
}
```

The **constructor** builds the scene — CPU work only:

```cpp
SceneGraphDemo::SceneGraphDemo()
{
    BuildScene();
}
```

```cpp
void SceneGraphDemo::BuildScene()
{
    using scene::Transform;
    const glm::vec3 up(0.0f, 1.0f, 0.0f);

    // Materials, after the scene's own default at index 0. All linear.
    const uint32_t groundColor = m_scene.AddMaterial({ .name = "Ground", .baseColor = { 0.35f, 0.35f, 0.35f, 1.0f } });
    const uint32_t sunColor    = m_scene.AddMaterial({ .name = "Sun",    .baseColor = { 0.95f, 0.55f, 0.08f, 1.0f } });
    const uint32_t planetColor = m_scene.AddMaterial({ .name = "Planet", .baseColor = { 0.10f, 0.30f, 0.85f, 1.0f } });
    const uint32_t moonColor   = m_scene.AddMaterial({ .name = "Moon",   .baseColor = { 0.55f, 0.55f, 0.55f, 1.0f } });
    const uint32_t boxColor    = m_scene.AddMaterial({ .name = "Box",    .baseColor = { 0.80f, 0.15f, 0.10f, 1.0f } });

    // Meshes. Each sphere is its own mesh because each has its own size and
    // color; all sixteen boxes share one.
    const uint32_t groundMesh = m_scene.AddMesh("Ground", withMaterial(scene::makePlane(40.0f, 40.0f, 1), groundColor));
    const uint32_t sunMesh    = m_scene.AddMesh("Sun",    withMaterial(scene::makeUvSphere(1.5f, 48, 24), sunColor));
    const uint32_t planetMesh = m_scene.AddMesh("Planet", withMaterial(scene::makeUvSphere(0.6f, 32, 16), planetColor));
    const uint32_t moonMesh   = m_scene.AddMesh("Moon",   withMaterial(scene::makeUvSphere(0.25f, 24, 12), moonColor));
    const uint32_t boxMesh    = m_scene.AddMesh("Box",    withMaterial(scene::makeCube(1.0f), boxColor));

    const scene::NodeIndex ground = m_scene.AddNode("Ground");
    m_scene.SetMesh(ground, groundMesh);

    // The solar system. The sun's size is in its mesh, not its node's scale,
    // so it does not scale everything that orbits it. The orbits are empty
    // nodes at their parent's centre: turning one swings its children round.
    const scene::NodeIndex sun = m_scene.AddNode("Sun", scene::ROOT_NODE, { .translation = { 0.0f, 2.5f, 0.0f } });
    m_scene.SetMesh(sun, sunMesh);
    m_planetOrbit = m_scene.AddNode("PlanetOrbit", sun);
    const scene::NodeIndex planet = m_scene.AddNode("Planet", m_planetOrbit, { .translation = { 5.0f, 0.0f, 0.0f } });
    m_scene.SetMesh(planet, planetMesh);
    m_moonOrbit = m_scene.AddNode("MoonOrbit", planet);
    const scene::NodeIndex moon = m_scene.AddNode("Moon", m_moonOrbit, { .translation = { 1.4f, 0.0f, 0.0f } });
    m_scene.SetMesh(moon, moonMesh);

    // A camera that rides along with the planet, looking back at it.
    const scene::NodeIndex planetCamera = m_scene.AddNode("PlanetCamera", planet, Transform{
        .translation = { 0.0f, 1.2f, 3.5f },
        .rotation    = scene::rotationFromYawPitch({ .yaw = 0.0f, .pitch = std::atan2(-1.2f, 3.5f) }),
    });
    m_scene.SetCamera(planetCamera, m_scene.AddCamera({}));

    // A ring of boxes around everything, to have something to cull.
    const scene::NodeIndex boxes = m_scene.AddNode("Boxes");
    for (int i = 0; i < 16; ++i)
    {
        const float angle = static_cast<float>(i) * glm::radians(360.0f / 16.0f);
        const scene::NodeIndex box = m_scene.AddNode("Box " + std::to_string(i + 1), boxes, Transform{
            .translation = { 12.0f * std::cos(angle), 0.5f, 12.0f * std::sin(angle) },
            .rotation    = glm::angleAxis(-angle, up),
        });
        m_scene.SetMesh(box, boxMesh);
    }

    // The main camera, active, where the orbit controller would put it.
    m_controls.active         = scene::ControllerKind::Orbit;
    m_controls.orbit.target   = glm::vec3(0.0f, 1.5f, 0.0f);
    m_controls.orbit.distance = 22.0f;
    Transform view;
    view.rotation    = scene::rotationFromYawPitch({ .yaw = glm::radians(25.0f), .pitch = glm::radians(-25.0f) });
    view.translation = m_controls.orbit.target - view.Forward() * m_controls.orbit.distance;
    const scene::NodeIndex mainCamera = m_scene.AddNode("MainCamera", scene::ROOT_NODE, view);
    m_scene.SetCamera(mainCamera, m_scene.AddCamera({}));
    m_scene.SetActiveCamera(mainCamera);
    m_controlledCamera = mainCamera;

    m_scene.UpdateWorldTransforms();   // so the first frame's world matrices exist
}
```

The parts worth noticing:

- **The orbits are empty nodes.** `PlanetOrbit` sits at the sun's centre with no
  mesh; turning it swings the planet, five metres along its X axis, around the
  sun. The planet's own transform never changes. `MoonOrbit` does the same one
  level down. This "pivot node" is the standard way to orbit with a scene graph.
- **Sixteen boxes, one mesh.** Every box node names mesh `boxMesh`; the
  geometry is uploaded once. (The three spheres are separate meshes only
  because each has its own size and color.)
- **The planet camera is the planet's child**, 1.2 m up and 3.5 m back, pitched
  to look at it. It moves because the planet moves.
- **The last line** computes the world matrices once, so that the first frame's
  controller has a camera pose to start from.

**`Setup`** uploads the scene into the scene renderer — **in index order**, so
that mesh `i` and material `i` mean the same thing on both sides, and a
`DrawItem` from the scene can be handed to the renderer unchanged:

```cpp
InitializationResult SceneGraphDemo::Setup(const DemoContext& context)
{
    m_context = context;
    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }

    // In index order, so that a DrawItem's mesh and material indices mean the
    // same thing to the scene renderer as they do to the scene.
    for (uint32_t mesh = 0; mesh < m_scene.MeshCount(); ++mesh)
    {
        m_sceneRenderer.AddMesh(m_scene.GetMesh(mesh).data);
    }
    for (uint32_t material = 0; material < m_scene.MaterialCount(); ++material)
    {
        m_sceneRenderer.AddMaterial(m_scene.GetMaterial(material));
    }
    return InitializationResult::success();
}
```

**`Resize`** keeps the extent, because culling happens in `Update`, which needs
the aspect ratio and is not handed the targets:

```cpp
InitializationResult SceneGraphDemo::Resize(const vulkan_graphics::SceneTargets& targets)
{
    m_extent = targets.extent;   // Update builds the culling frustum before Record sees the targets
    return InitializationResult::success();
}
```

**`Update`** is where the scene graph earns its keep. Its order is the order of
section 4 — everything that moves nodes, then one update, then the list:

```cpp
void SceneGraphDemo::Update(const FrameInput& input)
{
    // 1. The controllers move the active camera's node. They work on its pose
    //    in the world, so they behave the same under any parent.
    const scene::NodeIndex cameraNode = m_scene.ActiveCamera();
    if (cameraNode != m_controlledCamera)
    {
        // Another camera became active: forget what was held, and orbit around
        // whatever the new one is looking at.
        m_controls.fly.ReleaseAll();
        m_controls.orbit.ReleaseAll();
        m_controls.orbit.Retarget(m_scene.WorldTransform(cameraNode));
        m_controlledCamera = cameraNode;
    }
    for (const window::Event& event : input.events)
    {
        m_controls.HandleEvent(event);
    }
    scene::Transform pose = m_scene.WorldTransform(cameraNode);
    if (m_controls.Update(input.deltaSeconds, pose))
    {
        m_scene.SetWorldTransform(cameraNode, pose);
    }

    // 2. The animation turns the two orbit pivots, nothing else.
    if (m_animate)
    {
        m_planetAngle += 0.35f * input.deltaSeconds;
        m_moonAngle   += 1.60f * input.deltaSeconds;
        m_scene.EditLocal(m_planetOrbit).rotation = glm::angleAxis(m_planetAngle, glm::vec3(0.0f, 1.0f, 0.0f));
        m_scene.EditLocal(m_moonOrbit).rotation   = glm::angleAxis(m_moonAngle, glm::vec3(0.0f, 1.0f, 0.0f));
    }

    // 3. The panels, which may edit any node.
    scene::drawCameraPanel(m_scene.GetCamera(m_scene.GetNode(cameraNode).camera), m_controls, pose);
    scene::drawSceneHierarchy(m_scene, m_editor);
    scene::drawNodeInspector(m_scene, m_editor);

    // 4. Everything has moved that is going to: world matrices, once, then the
    //    draw list, culled against what the active camera can see.
    m_scene.UpdateWorldTransforms();

    const scene::Node&   viewer = m_scene.GetNode(m_scene.ActiveCamera());
    const scene::Camera& camera = m_scene.GetCamera(viewer.camera);
    const float          aspect = static_cast<float>(m_extent.width) / static_cast<float>(m_extent.height);
    if (!m_freezeFrustum)
    {
        m_frustum = scene::frustumFromViewProjection(camera.Projection(aspect) * scene::viewMatrix(viewer.world));
    }
    m_stats = m_scene.CollectDraws(m_draws, m_culling ? &m_frustum : nullptr);

    DrawPanel();
    m_time      = input.elapsedSeconds;
    m_deltaTime = input.deltaSeconds;
}
```

When the active camera changes, step 1 forgets held input and re-centres the
orbit on what the new camera is looking at, as Chapter 10's `Select` does for a
controller switch. In step 4, "Freeze frustum" keeps the last frustum while the
camera moves on, which is the clearest way to *see* culling: freeze it, turn
around, and only what the frozen view could see is drawn.

The demo's own panel comes last, so its statistics are this frame's:

```cpp
void SceneGraphDemo::DrawPanel()
{
    if (debug_panels::beginDemoPanel("Scene graph", debug_panels::DemoPanelSlot::BelowCamera))
    {
        ImGui::Checkbox("Animate", &m_animate);
        ImGui::Checkbox("Frustum culling", &m_culling);
        ImGui::Checkbox("Freeze frustum", &m_freezeFrustum);
        ImGui::Text("Nodes: %zu   draws: %zu", m_scene.NodeCount(), m_draws.size());
        ImGui::Text("Culled: %u of %u", m_stats.culled, m_stats.considered);

        // Any node with a camera can be the one the scene is seen through.
        ImGui::SeparatorText("Look through");
        for (scene::NodeIndex node = 0; node < m_scene.NodeCount(); ++node)
        {
            if (m_scene.GetNode(node).camera == scene::NO_COMPONENT) { continue; }
            if (ImGui::RadioButton(m_scene.GetNode(node).name.c_str(), m_scene.ActiveCamera() == node))
            {
                m_scene.SetActiveCamera(node);
            }
        }
    }
    ImGui::End();
}
```

**`Record`** reads the active camera node and writes the frame data, then draws
the list — exactly Chapter 11's `Record`, with the camera coming from a node:

```cpp
void SceneGraphDemo::Record(const RecordContext& frame)
{
    const VkCommandBuffer commandBuffer = frame.commandBuffer;
    const VkExtent2D      extent        = frame.targets.extent;
    const float           aspect        = static_cast<float>(extent.width) / static_cast<float>(extent.height);

    // The camera is a node: its view comes from the node's world matrix, its
    // lens from the camera component.
    const scene::Node&   viewer = m_scene.GetNode(m_scene.ActiveCamera());
    const scene::Camera& camera = m_scene.GetCamera(viewer.camera);

    // Chapter 11's sun: high, and to the right of the starting camera.
    const glm::vec3 toSun = glm::normalize(glm::vec3(0.4f, 1.0f, 0.3f));

    shared::FrameData frameData{};
    frameData.view           = scene::viewMatrix(viewer.world);
    frameData.projection     = camera.Projection(aspect);
    frameData.viewProjection = frameData.projection * frameData.view;
    frameData.cameraPosition = glm::vec4(glm::vec3(viewer.world[3]), 1.0f);
    frameData.time           = m_time;
    frameData.deltaTime      = m_deltaTime;
    frameData.sunDirection   = glm::vec4(-toSun, 0.0f);
    frameData.sunColor       = glm::vec4(0.90f, 0.85f, 0.80f, 0.0f);
    frameData.ambientColor   = glm::vec4(0.08f, 0.09f, 0.12f, 0.0f);
    m_sceneRenderer.WriteFrameData(frame.frameIndex, frameData);

    const VkClearColorValue clearColor{ { 0.02f, 0.02f, 0.03f, 1.0f } };
    vulkan_graphics::beginScenePass(commandBuffer, frame.targets, &clearColor);
    m_sceneRenderer.RecordDraws(commandBuffer, frame.frameIndex, m_draws);
    vulkan_graphics::endScenePass(commandBuffer);
    vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
}
```

```cpp
// GPU objects only. The scene, the camera, and every edit stay in m_scene.
void SceneGraphDemo::Teardown()
{
    m_sceneRenderer.Shutdown();
}
```

### Registering it

**This is `Source/SandboxGame/Main.cpp`**, after the meshes' line,

```cpp
demoList.push_back(std::make_unique<demos::scene_graph::SceneGraphDemo>());   // Chapter 12
```

and `#include "PillowFort/Demos/SceneGraph/SceneGraphDemo.h"` beside the other
demos'. `SandboxGame --demo Scene` starts on it.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| A crash or garbage after adding many nodes, never with few | A `Node&` or `Node*` held across `AddNode`, which reallocated the vector (section 3) |
| Children lag one frame behind their parent | The world update ran before something moved the parent, or a child was computed before its parent (a flat loop after a reparent) |
| An edit in the inspector does nothing | The transform was changed without `EditLocal`, so the node was never marked changed |
| A reparented node jumps | `Reparent` kept the local transform instead of solving for it; or the world matrices were stale |
| The program hangs after a drag in the hierarchy | A reparent made a loop: the check in `IsInSubtree` is missing |
| Crash or "vector iterators incompatible" when dropping a node | The reparent ran inside the tree walk instead of after it (section 8) |
| The rotation fields jump while dragging | The Euler angles are re-derived from the quaternion every frame instead of remembered (section 8) |
| A camera under a scaled parent sees the world too small or too large | The view is `glm::inverse(world)` instead of `viewMatrix(world)` (Chapter 10 section 4) |
| Controllers fight an animated or rotated parent | They wrote the local transform as if it were the world pose (section 5) |
| Objects vanish at the edges of the screen while still partly visible | `transformBounds` dropped the absolute values, or a plane's sign is flipped |
| Nothing very close to the camera is ever culled | The near plane is `row3 + row2` — OpenGL's — instead of `row2` |
| Draws reference the wrong mesh or color | Meshes or materials uploaded to the scene renderer in a different order than the scene's indices |

---

## Exit check

- [ ] The demo shows the sun, the orbiting planet and moon, the ring of boxes,
      and the ground; the Scene panel shows the tree.
- [ ] **Moving a parent moves its children**: select Sun, drag its Translation
      X in the inspector, and the planet, the moon, and the planet camera go
      with it. Scale the Sun node to 2: the whole system doubles.
- [ ] **Any camera node can be active**: pick PlanetCamera under "Look through"
      (or "Look through this camera" in its inspector). The view rides along
      with the planet as it orbits; the controllers move that camera, and
      switching back to MainCamera finds it where it was.
- [ ] **Inspector edits show immediately**, the same frame, for translation,
      rotation, scale, visibility (hiding Boxes hides all sixteen), and a
      camera's field of view.
- [ ] **Reparenting keeps the world position**: drag Moon onto Sun in the
      hierarchy. It stays where it was, stops following the planet, and its
      local transform in the inspector changes to say so. Dragging Sun onto
      Moon (its own descendant) does nothing.
- [ ] **The culled count drops when looking away**: in Fly mode, turn away from
      the system — the Scene graph panel's "Culled" count rises to most of the
      meshes, and falls back to 0 when you look back. With "Freeze frustum"
      ticked, turning back shows only what the frozen view could see.
- [ ] Switching to other demos and back keeps every edit; resizing and closing
      are validation-clean, with synchronization validation proven on, and
      `vmaDestroyAllocator` does not assert.

Next: [13 — Adding a Library: TinyUSDZ](13-Adding-TinyUSDZ.md)
