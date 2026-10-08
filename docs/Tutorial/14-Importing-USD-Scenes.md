# 14 — Importing USD Scenes

**Goal:** USD files — hand-written ones and Blender's — import into Chapter
12's scene graph and render with the right scale, orientation, and facing,
and the hierarchy panel shows what came in.

**ROADMAP:** step 15.

**Module:** `UsdImport`, namespace `pf::usd_import`, grows `ImportUsdFile`. A
new demo, `Source/PillowFort/Demos/UsdViewer/` (`pf::demos::usd_viewer`).
Small changes to `Source/SandboxGame/Main.cpp`, and four test scenes in
`Assets/Scenes/`.

**Math:** taught here — how USD's row-vector matrices and GLM's column-vector
ones store the same transform (section 3); a field of view from a lens's focal
length and film height (section 6); how far back a camera must stand for a
sphere to fill its view (section 9); a polygon's normal from Newell's method
(section 12). Assumed: Chapter 12 section 5's reading of a matrix and its
determinant, the cross product, and `tan`, `atan`, `sin`.

**Prerequisites:**

- Chapter 13, all of it — especially section 9 (primvars and their
  interpolation; xformOps and their order), section 10 (`upAxis`,
  `metersPerUnit`, the default time), section 11 (what `LoadUSDFromFile` does
  not compose), and section 13 (`loadStage`, `toUtf8`, the file layout of
  `UsdImport.cpp`).
- Chapter 12's `Scene`: `AddNode`, `AddMesh`, `AddCamera`, `SetMesh`,
  `SetCamera`, `SetActiveCamera`, `ROOT_NODE`, `INVALID_NODE`, and
  `transformFromMatrix`; section 5's reading of a matrix (columns are where
  the axes go; the determinant's sign says whether it mirrors); section 7's
  `Reparent`; its rule that nodes refer to everything by index; its hierarchy
  and inspector panels; and its demo, which this chapter's viewer follows
  closely.
- Chapter 11's `MeshData`, `Vertex`, and `Submesh`; its winding contract
  (counter-clockwise front faces, `cullMode = BACK`, culling off for
  `doubleSided`); `makeCube` and `makeUvSphere`; and the Meshes demo's
  `SetFrontFaceFlipped` and Normals view, which are this chapter's facing
  tests.
- Chapter 10's `Camera` (`verticalFov`, `nearPlane`, `farPlane` in metres) and
  `viewMatrix`, which uses only the rigid part of a camera's world matrix.
- Chapter 09 section 4 (what every `Record` owes the scene target), section 5
  (`switchDemo`'s order, which section 10 repeats from inside a demo), and
  section 7 (`LaunchSettings`, `--demo`, registering a demo).

Chapter 13 read a file and printed it. This chapter turns what it reads into
the engine's own data, and nearly every line is a **conversion** between two
sets of conventions that disagree. The disagreements, all of them, in one
table:

| Question | USD (and Blender's export) | The engine (the index) | Converted in |
| --- | --- | --- | --- |
| Which way is up | `upAxis`: Y or Z (Blender: Z) | +Y | section 2 |
| How long is one unit | `metersPerUnit` (Blender: 1, Maya: 0.01) | one metre | section 2 |
| How a transform is stored | xformOps, row vectors | `Transform` (TRS), column vectors | section 3 |
| Which side is the front | counter-clockwise, unless `orientation = "leftHanded"` — and a mirror flips it | counter-clockwise, always | section 4 |
| How a camera's lens is described | focal length and film aperture | vertical field of view | section 6 |
| What a face is | a polygon with any number of corners | a triangle | section 11 |
| How many values per attribute | per prim, face, point, or corner (interpolation) | per vertex | section 12 |
| Where texture coordinate (0, 0) is | bottom-left | top-left (Vulkan's image origin) | section 12 |
| Material assignment within a mesh | GeomSubsets | `Submesh` index ranges | section 13 |

The chapter is in two parts, split where the table splits. **Part 1 (sections
1-10) is the hierarchy**: axes and units, transforms, mirrors, USD's built-in
cubes and spheres, cameras, the walk over the stage, and a viewer to see the
result. It ends with a working viewer on two hand-written scenes made only of
cubes and spheres; polygon meshes are skipped until then, and the log counts
them. **Part 2 (sections 11-15) is the polygons**: triangulation, per-corner
data, materials per face, and a scene exported from Blender.

### What changes, and where

```text
Source/PillowFort/UsdImport/
  UsdImport.h                           section 7: ImportUsdFile joins LogUsdPrimTree
  UsdImport.cpp                         sections 2-7: the hierarchy; sections 11-13: meshes
Source/PillowFort/Demos/UsdViewer/
  UsdViewerDemo.h, .cpp                 sections 9-10: new, the viewer
Source/SandboxGame/Main.cpp             section 9: --scene, one registration line; Chapter 13's startup call goes
Assets/Scenes/
  Basics.usda, Basics_ZUpCm.usda        section 8: hand-written, cubes and spheres only
  Facing.usda                           section 14: hand-written polygon meshes
  BlenderScene.usdc                     section 15: exported from Blender
```

Files are added, so **rerun `GenerateProjects.bat`**.

### Where everything lands in `UsdImport.cpp`

Everything new is file-scope, above the namespace block, in the order each
needs the one before it. Only `ImportUsdFile` is public:

```text
UsdImport.cpp
  includes                                                          section 7
  static toUtf8, loadStage, logPrim                                 Chapter 13
  struct ImportContext                                              section 2
  static stageToEngine(metas, metersPerUnit)                        section 2
  static toGlm(matrix)                                              section 3
  static usdLocalMatrix(xformable, parentUsdWorld, path)            section 3
  static nodeTransform(usdLocal, path)                              section 3
  struct Corner                                                     section 11
  static triangulate(counts, indices, pointCount, faceStart, problem)   section 11
  static elementFor(interpolation, corner)                          section 12
  static expectedLength(interpolation, faces, points, faceVertices) section 12
  static readUvs(mesh, uvs, interpolation, name)                    section 12
  static addMesh(context, prim, data, reverseWinding, node)         section 4
  static importMesh(context, prim, mesh, mirrored, node, path)      sections 11-13
  static importShape(context, prim, gprim, shape, mirrored, node)   section 5
  static importCamera(context, camera, node, path)                  section 6
  static asXformable(prim)                                          section 7
  static importPrim(context, prim, parent, parentUsdWorld)          section 7
  namespace pf::usd_import {
      LogUsdPrimTree(file)                                          Chapter 13
      ImportUsdFile(file, scene)                                    section 7
  }
```

Part 2's functions slot in where the layout shows them; the order only has to
put each function before its first use.

The call graph is short: `ImportUsdFile` loads the stage, makes one node for
the file, and calls `importPrim` on each root prim; `importPrim` makes a node,
hands cubes and spheres to `importShape`, cameras to `importCamera`, and — from
Part 2 — meshes to `importMesh`, and recurses.

---

# Part 1 — The hierarchy (sections 1-10)

By the end of this part, a USD file of cubes, spheres, and cameras, in any up
axis and unit, imports into the scene graph and draws through its own camera,
and the viewer can switch files while it runs.

## 1. Walk the stage yourself, or let Tydra convert it

**This is the one design decision of the chapter, made before any code.**
TinyUSDZ ships a converter, Tydra's `RenderSceneConverter`, that turns a whole
stage into a `tinyusdz::tydra::RenderScene`: flat arrays of meshes, materials,
textures, cameras, and lights, plus a node tree with local matrices. At this
pin it does a lot: it triangulates (correctly even for the concave polygons
section 11's simpler method gets wrong), merges vertices, resolves materials
and decodes their textures, and computes tangents.

And it leaves alone exactly the things this chapter is about. It records the
stage's `upAxis` and `metersPerUnit` in `RenderScene::meta` but converts
nothing; it records a mesh's `orientation` in `RenderMesh::is_rightHanded`
but does not fix the winding; its texture coordinates keep USD's bottom-left
origin. A renderer built on it still writes the axis, unit, winding, and UV
conversions — and in addition converts a second complete scene representation,
`RenderScene`, into Chapter 12's `Scene`, owning two copies of everything
while it does.

So this chapter **walks the stage itself**: prims to nodes, one at a time,
writing each conversion where you can see it. That is also the tutorial's
point — what `faceVarying` means is easier to understand from the twenty lines
that handle it than from a flag. Tydra is used for the pieces that teach
nothing: `GetGeomSubsetChildren` here, which finds a mesh's GeomSubsets, and
material-binding lookup in Chapter 15. If you later want Tydra's
triangulation, its *earcut* is in TinyUSDZ's tree
(`src/external/mapbox/earcut/earcut.hpp`), and section 11 says where it would
go.

---

## 2. One conversion for the whole file

**This is `ImportContext` and `stageToEngine`** — how a Z-up, centimetre file
becomes +Y up and metres.

The index's rule is that a stage in other conventions "is converted once, at
import". The conversion itself is one matrix: for a Z-up stage, a quarter
turn about +X that takes USD's +Z (up) to the engine's +Y; then a uniform
scale by `metersPerUnit`. The question is *where* to apply it, and there are
two candidates.

**Put it in one node.** Give the file a node of its own, under `ROOT_NODE`,
whose `Transform` *is* the conversion, and import every prim beneath it
exactly as authored. World matrices come out in the engine's conventions,
because every one of them is the conversion times the file's own world matrix.

**Or bake it into the data.** Rewrite every point and every transform in the
file into Y-up metres, so that no extra node exists.

Baking looks tidier, and it is wrong in a way that is easy to miss: rewriting
a transform into new axes re-expresses each node's *own* axes as well as its
parent's. Some prims give their own axes a meaning — **a USD camera looks
down its local −Z, and so does every UsdLux light**. After baking, a Z-up
file's camera looks down what is now its local −Y, while the engine's
`viewMatrix` (Chapter 10) still looks down local −Z: Blender's camera, aimed
at the scene, ends up looking at the sky. Fixing it means special cases for
every prim type with a meaningful axis — cameras now, lights in Chapter 16.
The conversion node needs none: a camera's local −Z stays its local −Z, and
the node above it turns the whole file at once.

What the conversion node costs is that **world matrices now carry a rotation
and a scale you did not author**, and downstream code must not assume
otherwise. Chapters 10 and 12 were written for this: `viewMatrix` builds the
view from the rigid part of the camera's world matrix only, the controllers
work on the camera's world pose and write back `local = inverse(parentWorld)
· world`, and the mesh shader normalizes its transformed normals. The
inspector shows each imported node's local transform in the file's own axes
and units — exactly what the `.usda` says — and the file's node shows the
conversion, which you can select and look at.

> **Jump:** until now, every node's transform was one you set, in metres,
> Y up. From this chapter, a node's local values are in *its file's*
> conventions, and only world matrices are guaranteed to be the engine's.
> When you read a local translation in the inspector, ask which file it came
> from; when you need a position, direction, or length in metres, take it
> from the world matrix — and normalize any direction you take from a matrix
> column, because the column carries the scale (Chapter 12 section 5).

`ImportContext` is what every step of one import needs to reach. Most
helpers take it by reference instead of a growing parameter list:

```cpp
// File scope, above the namespace block. Chapter 14 section 2: what every step of
// one import shares.
struct ImportContext
{
    pf::scene::Scene&          scene;
    const tinyusdz::Stage&     stage;                 // chapter 15 resolves material bindings through it
    std::filesystem::path      directory;             // the file's folder: chapter 15's texture paths
    double                     metersPerUnit = 1.0;   // the stage's, for camera distances
    std::map<std::string, int> skipped;               // prim type -> how many were skipped
};
```

`stage` and `directory` are not used until Chapter 15, which finds materials
through the stage and textures relative to the file. They are here because
they belong to "this import", and adding them later would change every
place that builds the struct. `skipped` collects one line per unsupported prim
type instead of one warning per prim — a scene with five hundred lights would
otherwise print five hundred lines.

`stageToEngine` builds the conversion as a `Transform`, so the file's node is
an ordinary node that Chapter 12's inspector can show and edit:

```cpp
// File scope, above the namespace block. Section 2: the one conversion, from the
// stage's up axis and units to the engine's +Y up and metres, as the transform of
// the node that holds the whole file.
static pf::scene::Transform stageToEngine(const tinyusdz::StageMetas& metas, double metersPerUnit)
{
    pf::scene::Transform conversion;
    if (metas.upAxis.get_value() == tinyusdz::Axis::Z)
    {
        // A quarter turn about +X takes USD's +Z (up) to +Y, and its +Y to -Z.
        conversion.rotation = glm::angleAxis(glm::radians(-90.0f), glm::vec3(1.0f, 0.0f, 0.0f));
    }
    else if (metas.upAxis.get_value() != tinyusdz::Axis::Y)
    {
        Log::warning("USD stage has an up axis other than Y or Z; treating it as Y.");
    }
    conversion.scale = glm::vec3(static_cast<float>(metersPerUnit));
    return conversion;
}
```

Check the direction of the turn, since a sign error here lays the whole scene
on its back: rotating by −90° about +X maps (x, y, z) to (x, z, −y). USD's up,
(0, 0, 1), becomes (0, 1, 0) — engine up. USD's +Y, which Blender calls
"forward" (into the screen in its front view), becomes −Z — away from a
default engine camera, which is also "into the screen". So a Blender scene
seen from Blender's front view looks the same from the engine's default view.

---

## 3. Transforms

**This is `toGlm`, `usdLocalMatrix`, and `nodeTransform`** — a prim's xformOps
to a node's `Transform`.

TinyUSDZ evaluates the xformOps for you. `Xformable::GetLocalMatrix` walks
`xformOpOrder`, builds each op's matrix, and multiplies them in USD's order;
it returns a `tinyusdz::value::matrix4d`, sixteen doubles. Before they go into
GLM, one thing about USD's matrices needs settling.

> **Jump:** USD and GLM write the same transform as two different-looking
> matrices, and yet the sixteen numbers copy across unchanged. GLM transforms a
> **column vector** from the right, `M · p` (Chapter 12 section 5): each *row*
> of M is dotted with p. USD transforms a **row vector** from the left,
> `p · M`: p is dotted with each *column* of M. So a matrix that does the same
> job from the other side has its rows written as columns — it is the
> *transpose* (Chapter 11 section 13) — and on paper USD's matrices are the
> transposes of GLM's. And USD stores a matrix row by row, while GLM
> stores it column by column. The two flips cancel. Here is a translate of
> (1, 2, 3) as each library stores it:
>
> ```text
>  USD matrix4d: m[i] is a row          glm::dmat4: [i] is a column
>  m[0] = (1  0  0  0)                  [0] = (1  0  0  0)
>  m[1] = (0  1  0  0)                  [1] = (0  1  0  0)
>  m[2] = (0  0  1  0)                  [2] = (0  0  1  0)
>  m[3] = (1  2  3  1)  translation     [3] = (1  2  3  1)  translation
> ```
>
> The same sixteen numbers, in the same order in memory. USD calls `m[3]` its
> last *row*, GLM calls `[3]` its last *column*, and that column is where
> `glm::translate` puts a translation — where the origin lands, in Chapter 12
> section 5's words. What does reverse is the order of a product on paper:
> USD writes a child's world matrix as `local · parentWorld`, GLM as
> `parentWorld · local`. Hold on to that wherever this chapter multiplies
> matrices: after `toGlm` they are GLM matrices, and GLM's order applies.

So `toGlm` copies element by element, with no transpose. Its loop variables
are named for GLM's side; the same two indices into `usd.m` are USD's row and
column:

```cpp
// File scope, above the namespace block. Section 3: no transpose - section 3's Jump says why.
static glm::dmat4 toGlm(const tinyusdz::value::matrix4d& usd)
{
    glm::dmat4 result(1.0);
    for (int column = 0; column < 4; ++column)
    {
        for (int row = 0; row < 4; ++row)
        {
            result[column][row] = usd.m[column][row];
        }
    }
    return result;
}
```

The matrices stay `double` (`glm::dmat4`) until they become a `Transform`.
USD's own are double, and a deep hierarchy multiplied in `float` accumulates
error; the cost is nothing at import time.

`usdLocalMatrix` asks for the local matrix at the default time (Chapter 13
section 10). It also handles `!resetXformStack!`, a prim's statement that its
ops are its *world* transform, whatever its ancestors say. Chapter 12's nodes
always have their parent's transform applied, so such a prim must be given the
local matrix that produces that world transform under its parent:
`inverse(parentWorld) · world`. That is why the function takes the parent's
world matrix, and takes it *in stage space*: the world the prim means is the
file's, and the conversion node, which sits above the stage, still applies to
it, as it should.

```cpp
// File scope, above the namespace block. Section 3: the prim's local matrix in
// stage space, from its xformOps at the default time.
static glm::dmat4 usdLocalMatrix(const tinyusdz::Xformable& xformable, const glm::dmat4& parentUsdWorld,
                                 const std::string& path)
{
    bool resetsStack = false;
    const auto local = xformable.GetLocalMatrix(tinyusdz::value::TimeCode::Default(),
                                                tinyusdz::value::TimeSampleInterpolationType::Held,
                                                &resetsStack);
    if (!local)
    {
        Log::warning(std::format("{}: cannot evaluate its xformOps ({}); using identity.",
                                 path, local.error()).c_str());
        return glm::dmat4(1.0);
    }

    // !resetXformStack! means "ignore every ancestor": the ops are the WORLD matrix.
    // The node still has a parent here, so express that matrix relative to it.
    const glm::dmat4 matrix = toGlm(local.value());
    return resetsStack ? glm::inverse(parentUsdWorld) * matrix : matrix;
}
```

`GetLocalMatrix` returns `nonstd::expected` — TinyUSDZ's stand-in for
C++23's `std::expected` — holding either the matrix or an error string. A prim
whose ops cannot be evaluated is imported with an identity transform and a
warning naming it, not dropped: its children may still be fine.

Finally the matrix becomes a `Transform`. Chapter 12's `transformFromMatrix`
reads it from the columns: their lengths are the scale, a negative
determinant puts its mirror into `scale.x`, and Gram-Schmidt squares what is
left into a rotation. A translate-rotate-scale can hold most of what USD
authors — but not all:

- **Mirrors** are fine. A negative determinant decomposes into a rotation and
  a negative scale, and `Matrix()` rebuilds the same matrix. Blender exports an
  object scaled by (−1, 1, 1) as `rotateXYZ = (180, 0, 0)` and
  `scale = (-1, -1, -1)` — the same matrix, written differently. What a mirror
  does to *facing* is section 4's problem.
- **Shear** is not. `["xformOp:scale", "xformOp:rotateZ"]` with an unequal
  scale — the order reversed from Blender's — rotates first and then stretches
  along the parent's axes, which makes the angles between the axes something
  other than 90° (Chapter 12 section 5's picture). No rotation-and-scale
  reproduces that. The closest TRS is used, and the prim is named in a
  warning.

The check is direct: rebuild the matrix from the `Transform` and compare.

```cpp
// File scope, above the namespace block. Section 3: a local matrix as a node's TRS.
static pf::scene::Transform nodeTransform(const glm::dmat4& usdLocal, const std::string& path)
{
    const glm::mat4 local(usdLocal);
    const pf::scene::Transform transform = pf::scene::transformFromMatrix(local);

    // A Transform cannot hold shear. Rebuild the matrix from the TRS and compare:
    // any real difference means the prim's xformOps sheared, and the scene shows
    // the closest TRS instead.
    const glm::mat4 rebuilt = transform.Matrix();
    float largest = 1.0f;
    float error   = 0.0f;
    for (int column = 0; column < 4; ++column)
    {
        for (int row = 0; row < 4; ++row)
        {
            largest = std::max(largest, std::abs(local[column][row]));
            error   = std::max(error, std::abs(rebuilt[column][row] - local[column][row]));
        }
    }
    if (error > 1e-4f * largest)
    {
        Log::warning(std::format("{}: its transform has shear, which a scene node cannot hold; "
                                 "using the closest translate-rotate-scale.", path).c_str());
    }
    return transform;
}
```

The tolerance is relative to the matrix's largest entry, because a
centimetre file's translations are a hundred times a metre file's and float
rounding grows with them. If shear ever matters to you — a sheared prop that
must look right — the fix is not in `Transform`, which should stay TRS so the
inspector and the controllers stay simple; it is to bake the residual into the
mesh's points on import. Exported files almost never need it.

---

## 4. Which side is the front

**This is `addMesh`** — the last step for every mesh the importer makes, and
the place that keeps Chapter 11's contract that every front face winds
counter-clockwise.

USD's default matches the engine: a face's corners wind counter-clockwise
seen from its front, and so do Chapter 11's generators, which make every mesh
in Part 1. Two things change that, and each reverses it:

- **A mirror above the mesh**: any transform with a negative determinant — a
  scale of −1 on one axis, as in Blender's "mirror an object" — turns a
  counter-clockwise triangle clockwise *as it appears in the world*, so the
  rasterizer sees its back.
- **`orientation = "leftHanded"`** on the prim: a statement that its faces
  wind clockwise seen from the front. This is USD's word for *winding*, not
  for axes — it has nothing to do with Chapter 12's left-handed axes. Some
  tools and older pipelines write it on meshes, and Part 2 meets one; any
  gprim may carry it.

Both together cancel. So the winding needs reversing exactly when one of them
holds — `leftHanded != mirrored`. `mirrored` is the sign of the determinant of
the prim's **world** matrix in the file, which `importPrim` (section 7)
computes and passes in; a mirror anywhere above counts, and two mirrors
cancel. The conversion node of section 2 is a rotation and a positive scale,
whose determinant is positive, so it never counts.

Reversing a triangle's winding is swapping two of its corners. Every mesh,
generated in Part 1 or authored in Part 2, ends in one function that does that
when asked and then hands the mesh to the scene:

```cpp
// File scope, above the namespace block. Section 4: the last step for every mesh,
// authored or generated. Fix the winding, then attach it to its node.
static void addMesh(ImportContext& context, const tinyusdz::Prim& prim, pf::scene::MeshData data,
                    bool reverseWinding, pf::scene::NodeIndex node)
{
    if (reverseWinding)
    {
        for (size_t i = 0; i + 2 < data.indices.size(); i += 3)
        {
            std::swap(data.indices[i + 1], data.indices[i + 2]);
        }
    }
    context.scene.SetMesh(node, context.scene.AddMesh(prim.element_name(), std::move(data)));
}
```

`MeshData` is taken by value and moved into the scene, so the vertex arrays
are never copied. The mesh is named after its prim, which is what the
hierarchy panel shows.

**The limit of this fix:** it is decided once, at import. Mirror a node in the
inspector afterwards — type −1 into a scale — and its meshes turn inside out,
because nothing re-decides. The general solution is to choose the front face
per draw from the sign of the world matrix's determinant, which Chapter 11's
dynamic front face makes possible. It is not done here because an imported
file is where mirrors come from in practice; if you find yourself mirroring
in the inspector, that is where to add it.

> **Note:** Blender writes `doubleSided = 1` on every mesh whose material does
> not tick *Backface Culling*, and Chapter 11 draws double-sided meshes with
> culling off and the normal flipped for back faces. Such a mesh looks right
> whichever way it winds — which is correct for a double-sided mesh, and means
> a winding bug is invisible on it. Section 15's export ticks Backface
> Culling for that reason, and Chapter 11's front-face flip toggle is the test
> that cannot be fooled.

---

## 5. Spheres and cubes

**This is `importShape`** — for the two *implicit* gprims, `Sphere` (a
`radius`, fallback 1) and `Cube` (a `size`, the edge length, fallback 2).
They have no points; they are described by their parameters, which makes them
the easiest things to write by hand — section 8's test scenes are built from
nothing else. Chapter 11's generators already build both, counter-clockwise,
with normals and texture coordinates in the engine's conventions, so the
importer only needs to call them and send the result through section 4's last
step. `orientation`, `doubleSided`, and mirroring apply to them too:

```cpp
// File scope, above the namespace block. Section 5: UsdGeomSphere and UsdGeomCube,
// built by Chapter 11's generators and then treated exactly like an authored mesh.
static void importShape(ImportContext& context, const tinyusdz::Prim& prim, const tinyusdz::GPrim& gprim,
                        pf::scene::MeshData shape, bool mirrored, pf::scene::NodeIndex node)
{
    shape.doubleSided = gprim.doubleSided.get_value();
    const bool leftHanded = gprim.orientation.get_value() == tinyusdz::Orientation::LeftHanded;
    addMesh(context, prim, std::move(shape), leftHanded != mirrored, node);
}
```

The walk (section 7) reads the radius or the size and calls the generator.
Texture coordinates from the generators are already top-left, so they skip
section 12's flip. USD defines no particular UV layout for implicit gprims, so
any consistent one is correct. (`Cylinder`, `Cone`, and `Capsule` are the same
idea with no generator yet; they are skipped with section 7's warning.)

---

## 6. Cameras

**This is `importCamera`** — a UsdGeomCamera to Chapter 10's `Camera`.

A USD camera describes a physical lens and film, not an angle: `focalLength`,
the distance from the lens to the film, and `horizontalAperture` and
`verticalAperture`, the film's width and height, all in one unit. Seen from
the side, the lens, the middle of the film, and the film's top edge make a
right triangle:

```text
   lens                 film
     o-------------------+  --+
      '-.  θ             |    |
         '-.             |    |  half the verticalAperture
            '-.          |    |
               '-.       |    |
                  '-.    |    |
                     '-. |  --+
     |<----------------->|
          focalLength
```

The angle θ at the lens is half the vertical field of view — light from the
scene crosses at the lens at the same angle — and its tangent is the far side
over the near side: `tan θ = (verticalAperture / 2) / focalLength`. So:

```text
verticalFov = 2 * atan(verticalAperture / (2 * focalLength))
```

Because it is a ratio, the unit cancels, and only the two numbers matter: a
35 mm lens over a 24 mm film is the same angle whether a file writes `35` and
`24` or `0.35` and `0.24`. Blender writes `verticalAperture` from its sensor
width and the render's aspect ratio — 36 mm × 9/16 = 20.25 mm for a 16:9
render — which is why section 15's script sets the render size. The engine
keeps the *vertical* angle and takes the aspect from the window (Chapter 10),
so in a window of a different shape than the file's film you see more or less
at the sides, never more or less at the top and bottom.

`clippingRange` gives near and far. It is in **stage units, whatever scale
sits above the camera**: USD positions the frustum with the camera's position
and orientation only, exactly as Chapter 10's `viewMatrix` does. So the
conversion is `metersPerUnit` alone. This is easy to get wrong in the other
direction — Blender's centimetre export, checked in section 15, writes
`clippingRange = (10, 10000)` under a root scaled by 100, which is 0.1 m and
100 m, the same as its metre export, and not 10 m and 10 km.

USD cameras look down their local −Z with +Y up, the engine's view-space
convention, so nothing else converts: Chapter 10's `viewMatrix(node.world)`
is right for an imported camera as it is. The first camera a file contains
becomes the scene's active camera, unless the scene already has one:

```cpp
// File scope, above the namespace block. Section 6: a UsdGeomCamera.
static void importCamera(ImportContext& context, const tinyusdz::GeomCamera& camera, pf::scene::NodeIndex node,
                         const std::string& path)
{
    // get_default reads the value authored for the default time. USD's fallbacks
    // stay when the file is silent.
    float focalLength      = 50.0f;
    float verticalAperture = 15.2908f;
    tinyusdz::value::float2 clipping{ 0.1f, 1000000.0f };
    tinyusdz::GeomCamera::Projection projection = tinyusdz::GeomCamera::Projection::Perspective;
    camera.focalLength.get_value().get_default(&focalLength);
    camera.verticalAperture.get_value().get_default(&verticalAperture);
    camera.clippingRange.get_value().get_default(&clipping);
    camera.projection.get_value().get_default(&projection);

    if (projection != tinyusdz::GeomCamera::Projection::Perspective)
    {
        Log::warning(std::format("{}: orthographic cameras are not supported; importing it as perspective.",
                                 path).c_str());
    }

    // clippingRange is in stage units, whatever scale sits above the camera (section 6).
    const pf::scene::Camera result{
        .verticalFov = static_cast<float>(2.0 * std::atan(verticalAperture / (2.0 * focalLength))),
        .nearPlane   = static_cast<float>(clipping[0] * context.metersPerUnit),
        .farPlane    = static_cast<float>(clipping[1] * context.metersPerUnit),
    };
    context.scene.SetCamera(node, context.scene.AddCamera(result));
    if (context.scene.ActiveCamera() == pf::scene::INVALID_NODE)
    {
        context.scene.SetActiveCamera(node);
    }
}
```

The local variables start at the schema's fallbacks as TinyUSDZ declares
them — 50 mm, 15.2908 mm (the height of a 35 mm Academy film frame),
0.1 to 1 000 000 — because `get_default` leaves its argument untouched when
the file has no default value, and a camera file that sets only
`focalLength` still describes a whole camera. (A far plane a million units
away gives poor depth precision, Chapter 10's lesson; a file that relies on
the fallback should get a real one, and the camera panel can change it.)

---

## 7. The walk, and the public function

**This is `asXformable`, `importPrim`, `ImportUsdFile`, and the header** — the
code that ties sections 2-6 together.

`tinyusdz::Prim` holds its schema object in a type-erased value; `prim.as<T>()`
returns a pointer to it when the prim *is* a `T`, and `nullptr` otherwise.
Several schema types are transformable, and the importer needs the shared base
class, `tinyusdz::Xformable`, to evaluate their ops. `as<T>` matches only the
exact type, so the types are asked one at a time:

```cpp
// File scope, above the namespace block. Section 7: the prim types with a transform
// that this importer understands. Chapter 16 adds the lights.
static const tinyusdz::Xformable* asXformable(const tinyusdz::Prim& prim)
{
    if (const auto* xform = prim.as<tinyusdz::Xform>())       { return xform; }
    if (const auto* sphere = prim.as<tinyusdz::GeomSphere>()) { return sphere; }
    if (const auto* cube = prim.as<tinyusdz::GeomCube>())     { return cube; }
    if (const auto* camera = prim.as<tinyusdz::GeomCamera>()) { return camera; }
    return nullptr;
}
```

`GeomMesh` is missing from the list on purpose. Part 2 adds it, in section
13, together with the code that imports a mesh; until then a `Mesh` prim is a
type the importer does not know, and is skipped like one.

`importPrim` is the walk. For each prim it decides whether to import it, makes
its node, attaches whatever the prim is, and recurses. It carries the parent's
world matrix **in stage space** alongside the scene's own nodes, because three
questions are about the file and not the engine's copy of it: `resetXformStack`
(section 3), mirroring (section 4), and — through the stage's
`metersPerUnit` — camera distances (section 6).

What it skips, and why:

- **`active = false`** prims: USD's way of deleting a prim without removing its
  text. Their subtrees go too.
- **Materials and shaders**: data, not part of the transform hierarchy.
  Chapter 15 reaches them through bindings.
- **GeomSubsets**: read with their mesh (section 13).
- **Any other type it does not know** — polygon meshes until section 13,
  lights until Chapter 16, curves, points, skeletons, `PointInstancer` until
  Chapter 19 — with everything under it, counted in `skipped` and reported once
  per type at the end. A `Scope`, or a prim with no type (TinyUSDZ reads it as
  a `Model`), is kept as a node with no transform: it groups.

```cpp
// File scope, above the namespace block. Section 7: one prim, then its children.
// parentUsdWorld is the parent's world matrix in stage space.
static void importPrim(ImportContext& context, const tinyusdz::Prim& prim, pf::scene::NodeIndex parent,
                       const glm::dmat4& parentUsdWorld)
{
    // Section 7's list: inactive prims, materials, shaders, and subsets are not nodes.
    if (!prim.IsActive() || prim.is<tinyusdz::Material>() || prim.is<tinyusdz::Shader>() ||
        prim.is<tinyusdz::GeomSubset>())
    {
        return;
    }

    const std::string               path      = prim.absolute_path().full_path_name();
    const tinyusdz::Xformable*      xformable = asXformable(prim);
    if (xformable == nullptr && !prim.is<tinyusdz::Scope>() && !prim.is<tinyusdz::Model>())
    {
        ++context.skipped[prim.prim_type_name()];   // and everything below it
        return;
    }

    // Scopes, and typeless `def` prims, group without transforming.
    const glm::dmat4 usdLocal = xformable != nullptr ? usdLocalMatrix(*xformable, parentUsdWorld, path)
                                                     : glm::dmat4(1.0);
    const glm::dmat4 usdWorld = parentUsdWorld * usdLocal;
    const pf::scene::NodeIndex node =
        context.scene.AddNode(prim.element_name(), parent, nodeTransform(usdLocal, path));

    // A mirror in the world matrix turns counter-clockwise triangles clockwise on screen.
    const bool mirrored = glm::determinant(glm::dmat3(usdWorld)) < 0.0;
    if (const auto* sphere = prim.as<tinyusdz::GeomSphere>())
    {
        double radius = 1.0;
        sphere->radius.get_value().get_default(&radius);
        importShape(context, prim, *sphere, pf::scene::makeUvSphere(static_cast<float>(radius)), mirrored, node);
    }
    else if (const auto* cube = prim.as<tinyusdz::GeomCube>())
    {
        double size = 2.0;
        cube->size.get_value().get_default(&size);
        importShape(context, prim, *cube, pf::scene::makeCube(static_cast<float>(size)), mirrored, node);
    }
    else if (const auto* camera = prim.as<tinyusdz::GeomCamera>())
    {
        importCamera(context, *camera, node, path);
    }

    for (const tinyusdz::Prim& child : prim.children())
    {
        importPrim(context, child, node, usdWorld);
    }
}
```

`usdWorld = parentUsdWorld * usdLocal` is GLM's order — parent on the left —
although the matrices came from USD: after `toGlm` they are GLM matrices
(section 3's **Jump**). `glm::determinant` of the upper 3x3 part is Chapter 12
section 5's mirror test; the translation column does not affect it.

Two things this importer leaves to later or to you. **`class` prims**,
templates that are never drawn, are not filtered; Chapter 19, which meets
them, adds the test. **`visibility = "invisible"`** is not read: Blender
exports visible objects only, and Chapter 12's per-node checkbox covers
hiding.

`ImportUsdFile` puts it together. It loads the stage with Chapter 13's
`loadStage` — so a missing or unreadable file fails before anything is added
to the scene — guards against a nonsense `metersPerUnit`, builds the context,
adds the file's node with section 2's conversion, and walks the root prims.
The counts it logs at the end are the first check of every import:

```cpp
InitializationResult ImportUsdFile(const std::filesystem::path& file, scene::Scene& scene)
{
    tinyusdz::Stage stage;
    if (auto result = loadStage(file, stage); !result) { return result; }

    double metersPerUnit = stage.metas().metersPerUnit.get_value();
    if (!(metersPerUnit > 0.0))
    {
        Log::warning(std::format("{}: metersPerUnit {} is not positive; using 1.", toUtf8(file.filename()),
                                 metersPerUnit).c_str());
        metersPerUnit = 1.0;
    }
    ImportContext context{
        .scene         = scene,
        .stage         = stage,
        .directory     = file.parent_path(),
        .metersPerUnit = metersPerUnit,
        .skipped       = {},
    };

    const std::size_t nodesBefore   = scene.NodeCount();
    const std::size_t meshesBefore  = scene.MeshCount();
    const std::size_t camerasBefore = scene.CameraCount();

    const scene::NodeIndex fileNode =
        scene.AddNode(toUtf8(file.stem()), scene::ROOT_NODE, stageToEngine(stage.metas(), metersPerUnit));
    for (const tinyusdz::Prim& root : stage.root_prims())
    {
        importPrim(context, root, fileNode, glm::dmat4(1.0));
    }

    for (const auto& [type, count] : context.skipped)
    {
        Log::warning(std::format("{}: skipped {} prim(s) of type {} and everything under them.",
                                 toUtf8(file.filename()), count, type.empty() ? "(none)" : type).c_str());
    }
    std::size_t triangles = 0;
    for (std::size_t mesh = meshesBefore; mesh < scene.MeshCount(); ++mesh)
    {
        triangles += scene.GetMesh(static_cast<uint32_t>(mesh)).data.indices.size() / 3;
    }
    Log::info(std::format("{}: imported {} nodes, {} meshes ({} triangles), {} cameras.",
                          toUtf8(file.filename()), scene.NodeCount() - nodesBefore,
                          scene.MeshCount() - meshesBefore, triangles,
                          scene.CameraCount() - camerasBefore).c_str());
    return InitializationResult::success();
}
```

A file that does not author `metersPerUnit` gets TinyUSDZ's fallback, 1
(Chapter 13 section 10), so an unlabelled centimetre file comes in a hundred
times too big; the fix belongs in the file, not here.
`!(metersPerUnit > 0.0)` rather than `metersPerUnit <= 0.0` also catches NaN,
which compares false with everything. The `stage` lives until the function
returns, which is longer than any pointer into it that the walk takes — the
GeomSubset pointers from Tydra, for one, point into the stage's prims.

The function goes inside the namespace, after Chapter 13's `LogUsdPrimTree`.
The file's includes grow to everything the new code uses — the scene's mesh
generators, Tydra's scene access, GLM, and four standard headers. Two of them,
`<tydra/scene-access.hh>` and `<array>`, are for Part 2; including them now
costs nothing:

```cpp
// Source/PillowFort/UsdImport/UsdImport.cpp
#include "PillowFort/UsdImport/UsdImport.h"

#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/Scene/MeshGenerators.h"

// MSVC's C4702, unreachable code, comes from the optimizer, which /external:W0 does not reach:
// in Release, TinyUSDZ's nonstd::expected::value() has a branch after a throw.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4702)
#endif
#include <tinyusdz.hh>             // LoadUSDFromFile, Stage, Prim, and every schema type
#include <pprint-enum.hh>          // tinyusdz::to_string(Axis)
#include <tydra/scene-access.hh>   // tinyusdz::tydra::GetGeomSubsetChildren
#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <format>
#include <map>
#include <string>
#include <vector>
```

The `#pragma warning` pair is for MSVC's Release builds. The new code calls
`.value()` on TinyUSDZ's `nonstd::expected` results, and the optimizer, once it
has inlined one, finds the expression after its `throw` unreachable: `C4702`,
reported at `nonstd/expected.hpp`. `/external:W0` (Chapter 13 section 5)
silences what the compiler finds while reading an external header; this
warning comes later, from code generation. Disabling it around the includes,
and only there, keeps it for this file's own code. Other compilers do not know
the pragma, hence `#ifdef _MSC_VER`.

**The header** gains one include and one declaration. `UsdImport.h` now
needs `scene::Scene`; that is a Scene-module header, not a TinyUSDZ one, so the
rule of Chapter 13 section 5 still holds — anything may include `UsdImport.h`.
After its `InitializationResult.h` include:

```cpp
#include "PillowFort/Scene/Scene.h"
```

and inside the namespace, after `LogUsdPrimTree`:

```cpp
// Chapter 14: append the file to `scene` as one new subtree - a node named after
// the file under ROOT_NODE, and below it one node per imported prim. Everything
// appended is already in the engine's conventions: +Y up, metres, counter-
// clockwise front faces, UV origin top-left. If the scene has no active camera,
// the file's first camera becomes it. Fails, appending nothing, when the file is
// missing or does not parse; prims it cannot import are skipped with a warning.
InitializationResult ImportUsdFile(const std::filesystem::path& file, scene::Scene& scene);
```

An import **appends**: call it twice on one scene and both files are in it,
side by side under their own nodes. Chapter 12's nodes are never deleted, so
"replace the scene" is a new `Scene`, which is what the viewer in section 10
does.

---

## 8. Two test scenes

**These are the two hand-written files Part 1 is tested with.** They are built
from `Cube` and `Sphere` prims only, so everything in them is something Part 1
imports. Save them in `Assets/Scenes/`.

### `Basics.usda` — a Y-up, metre scene

Nested transforms (a turntable whose child has a child), a camera, and a
mirror: `Mirror` scales X by −1, so the ball under it needs section 4's
winding fix, and looks like any other ball when it gets it.

```text
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "World"
{
    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 100)
        double3 xformOp:translate = (0, 1.5, 6)
        float xformOp:rotateX = -10
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }

    def Cube "Ground"
    {
        double size = 1
        double3 xformOp:translate = (0, -0.05, 0)
        float3 xformOp:scale = (10, 0.1, 10)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }

    def Xform "Turntable"
    {
        float xformOp:rotateY = 45
        uniform token[] xformOpOrder = ["xformOp:rotateY"]

        def Cube "Box"
        {
            double size = 1
            double3 xformOp:translate = (-1.2, 0.5, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }

        def Xform "Mirror"
        {
            double3 xformOp:translate = (1.2, 0, 0)
            float3 xformOp:scale = (-1, 1, 1)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

            def Sphere "Ball"
            {
                double radius = 0.6
                double3 xformOp:translate = (0, 0.6, 0)
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }
        }
    }
}
```

What the import must produce, and why:

| Thing | Expected | Because |
| --- | --- | --- |
| The log | `Basics.usda: imported 8 nodes, 3 meshes (984 triangles), 1 cameras.` | the file's node and World, Camera, Ground, Turntable, Box, Mirror, Ball; two cubes of 12 triangles and a sphere of 960 |
| Camera | `verticalFov` 53.13°, near 0.1, far 100, eye (0, 1.5, 6), looking 10° down | 2·atan(24 / 48); clipping × 1 m |
| Ball | lit like the box, not dark with a bright rim | `Mirror`'s determinant is −1, so section 4 reverses the ball's winding |

The inspector shows *local* transforms, so it reads the Box's translation as
(−1.2, 0.5, 0), not where the box is in the world. To see a world position,
use Chapter 12 section 7: drag **Box** onto **Root** in the Scene panel.
`Reparent` keeps the node where it is in the world, and Root's world matrix
is the identity, so the Box's translation now *is* its world position, in
metres: (−0.849, 0.500, 0.849), which is (−1.2, 0.5, 0) turned 45° about +Y.
Restart to undo it.

### `Basics_ZUpCm.usda` — the same scene, Z-up in centimetres

The same scene as an artist in a Z-up, centimetre tool would author it: every
length multiplied by 100, and every position and axis turned from Y-up to Z-up
— (x, y, z) becomes (x, −z, y), so the ground's thin side and the turntable's
spin move from Y to Z. **It must render identically to `Basics.usda`** — same
picture, same camera numbers — with the only visible difference in the
hierarchy: its file node shows a −90° rotation about X and a scale of 0.01.

```text
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 0.01
    upAxis = "Z"
)

def Xform "World"
{
    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (10, 10000)
        double3 xformOp:translate = (0, -600, 150)
        float xformOp:rotateX = 80
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }

    def Cube "Ground"
    {
        double size = 100
        double3 xformOp:translate = (0, 0, -5)
        float3 xformOp:scale = (10, 10, 0.1)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }

    def Xform "Turntable"
    {
        float xformOp:rotateZ = 45
        uniform token[] xformOpOrder = ["xformOp:rotateZ"]

        def Cube "Box"
        {
            double size = 100
            double3 xformOp:translate = (-120, 0, 50)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }

        def Xform "Mirror"
        {
            double3 xformOp:translate = (120, 0, 0)
            float3 xformOp:scale = (-1, 1, 1)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

            def Sphere "Ball"
            {
                double radius = 60
                double3 xformOp:translate = (0, 0, 60)
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }
        }
    }
}
```

Read it beside `Basics.usda`: the prims, their nesting, and the mirror are the
same, and only numbers and axis names changed. The camera's `rotateX = 80` is
the one line to think about: a Z-up camera with no rotation looks straight
*down* (its −Z is the world's down), so tilting it 80° up leaves it 10° below
the horizon — and the conversion node's −90° turns 80° into −10°,
`Basics.usda`'s value. The drag onto Root works here too, and gives the same
(−0.849, 0.500, 0.849) in metres; only the Box's rotation and scale still show
the file's axes, (−90, 45, 0) and 0.01.

---

## 9. The USD viewer

**This is the USD viewer demo**: open a file from `Assets/Scenes`, see it
through its own camera, walk its hierarchy in Chapter 12's panels, and test its
facing with Chapter 11's switches. It is Chapter 12's `SceneGraphDemo` with the
solar system replaced by an import, and every difference follows from that:

| | `SceneGraphDemo` (Chapter 12) | `UsdViewerDemo` |
| --- | --- | --- |
| The scene is made | in the constructor, by code that cannot fail | in `Setup`, by an import that can |
| How often | once per demo object | once per demo object too, because `Setup` imports only into an empty scene |
| The camera | built in | the file's, or one added to frame the file |
| What changes while it runs | node edits | node edits, and the whole scene when another file is picked (section 10) |

The class map, with the four helpers that sit at file scope:

```text
UsdViewerDemo
  UsdViewerDemo(startFile)    stores --scene's file name or path; nothing fallible
  Setup(context)              scene renderer; FindFiles and loadScene only into an empty scene; upload in index order
    FindFiles()               the files in Assets/Scenes, sorted, --scene's path if it names one elsewhere,
                              and which one to start on
  Resize(targets)             keeps the extent, as Chapter 12's does
  Update(input)               Chapter 12's: controllers, panels, world update, draw list
    DrawPanel()               Chapter 11's switches and sun, "Look through"; section 10 adds the file list
      SwitchToFile(index)     section 10: loadScene into a new Scene; on success wait, Teardown, swap, Setup
  Record(frame)               Chapter 11's Record with the camera from a node; section 10 adds a bare clear
  Teardown()                  the scene renderer only; m_scene and every edit survive
file scope, above the namespace block:
  scenesDirectory()           executableDirectory() / "Assets" / "Scenes"
  toUtf8(path)                a file name as UTF-8, which is what ImGui draws
  addCameraIfMissing(scene)   a camera that frames everything the file drew
  loadScene(file, scene)      ImportUsdFile, addCameraIfMissing, UpdateWorldTransforms: CPU only
```

### The class

**This is `Source/PillowFort/Demos/UsdViewer/UsdViewerDemo.h`:**

```cpp
///========================================================
/// @author Gary Yang
/// @brief  USD files from Assets/Scenes, imported into a scene graph and drawn (Chapter 14)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/UsdViewer/UsdViewerDemo.h
#pragma once

#include "PillowFort/Demos/Demo.h"
#include "PillowFort/Scene/Bounds.h"
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/DrawItem.h"
#include "PillowFort/Scene/Scene.h"
#include "PillowFort/Scene/ScenePanels.h"
#include "PillowFort/VulkanGraphics/SceneRenderer.h"

#include <glm/glm.hpp>

#include <string>
#include <vector>

namespace pf::demos::usd_viewer {

class UsdViewerDemo final : public Demo
{
public:
    // startFile: from --scene, a file name in Assets/Scenes or a path to a scene
    // anywhere; empty means the first one in Assets/Scenes. Only stored - nothing
    // fallible happens in a constructor.
    explicit UsdViewerDemo(std::string startFile);

    const char*          Name() const override { return "USD viewer"; }
    InitializationResult Setup(const DemoContext& context) override;
    InitializationResult Resize(const vulkan_graphics::SceneTargets& targets) override;
    void                 Update(const FrameInput& input) override;
    void                 Record(const RecordContext& frame) override;
    void                 Teardown() override;
    bool                 WantsCursorCaptured() const override { return m_controls.WantsCursorCaptured(); }

private:
    void FindFiles();
    void DrawPanel();

    // GPU objects: Setup to Teardown.
    DemoContext                    m_context;
    vulkan_graphics::SceneRenderer m_sceneRenderer;

    // CPU state: survives Teardown, so a demo switch or a sample-count change
    // keeps the imported scene and every edit made to it.
    std::string                   m_startFile;
    std::vector<std::string>      m_files;               // the names shown: Assets/Scenes, then --scene's path
    std::vector<std::filesystem::path> m_paths;          // where each of m_files is, to open it
    int                           m_selectedFile = -1;   // index into m_files and m_paths
    scene::Scene                  m_scene;
    scene::SceneEditorState       m_editor;
    scene::CameraControls         m_controls;
    scene::NodeIndex              m_controlledCamera = scene::INVALID_NODE;
    std::vector<scene::DrawItem>  m_draws;
    scene::DrawListStats          m_stats;
    scene::Frustum                m_frustum{};
    VkExtent2D                    m_extent{ 1, 1 };
    vulkan_graphics::ShadingMode  m_shading          = vulkan_graphics::ShadingMode::Lit;
    bool                          m_frontFaceFlipped = false;
    bool                          m_culling          = true;
    float                         m_sunAzimuth       = 53.13f;   // degrees, from +Z towards +X
    float                         m_sunElevation     = 63.43f;   // degrees above the horizon
    glm::vec3                     m_sunColor{ 0.90f, 0.85f, 0.80f };      // linear
    glm::vec3                     m_ambientColor{ 0.08f, 0.09f, 0.12f };  // linear
    float                         m_time      = 0.0f;
    float                         m_deltaTime = 0.0f;
};

} // namespace pf::demos::usd_viewer
```

The members below `m_scene` are Chapter 12's, and the shading, front-face, and
sun members are Chapter 11's Meshes demo's: a file is exactly the kind of mesh
whose facing you want to test. Four are new: `m_startFile`, what `--scene`
named; `m_files` and `m_paths`, the list it is looked up in, as the names the
panel shows and the files they open; and `m_selectedFile`, the one open. The
header gains `<filesystem>` for `m_paths`.

### Loading a file, on the CPU only

**This is the top of `Source/PillowFort/Demos/UsdViewer/UsdViewerDemo.cpp`.**
It includes `ColorSpace.h` for the sun's color pickers, as Chapter 11's demo
does, and `UsdImport.h` — the only TinyUSDZ-free door into the importer:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  USD files from Assets/Scenes, imported into a scene graph and drawn (Chapter 14)
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/UsdViewer/UsdViewerDemo.cpp
#include "PillowFort/Demos/UsdViewer/UsdViewerDemo.h"

#include "PillowFort/DebugPanels/DemoPanel.h"
#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/Scene/ColorSpace.h"
#include "PillowFort/UsdImport/UsdImport.h"
#include "PillowFort/VulkanGraphics/ExecutableFiles.h"

#include <imgui.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <format>
#include <system_error>
```

The scenes are found the way Chapter 06 finds shaders: beside the executable,
where Chapter 13 section 6's post-build step copies `Assets/`, and never
relative to the working directory, for the reasons given there. Below
`scenesDirectory` goes a conversion, because the viewer shows file names as
UTF-8, which is what ImGui draws. `toUtf8` is Chapter 13 section 13's, copied,
for the reason given there: on Windows `path::string()` converts to the ANSI
code page. In a file list that is worse than a garbled name. MSVC's `string()`
throws `std::system_error` for a name that code page cannot hold, such as a
Cyrillic one on an English-language Windows, and nothing in `Setup` catches
it; Linux's returns the bytes unchanged, so it never shows there. The files
themselves are kept as paths, so nothing has to turn a name back into one:

```cpp
// File scope, above the namespace block. Where the post-build step of Chapter 13
// puts the scenes: beside the executable, never relative to the working directory.
static std::filesystem::path scenesDirectory()
{
    return pf::vulkan_graphics::executableDirectory() / "Assets" / "Scenes";
}

// File scope, above the namespace block. A file name as UTF-8, which is what ImGui
// draws: Chapter 13's toUtf8, copied. path::string() would convert to the ANSI code
// page on Windows, and MSVC's throws for a name that page cannot hold.
static std::string toUtf8(const std::filesystem::path& path)
{
    const std::u8string utf8 = path.u8string();
    return std::string(reinterpret_cast<const char*>(utf8.c_str()), utf8.size());
}
```

**A file need not have a camera.** Many do not — an asset exported on its own
is just geometry — and the viewer still has to see it through something. So it
adds one, aimed at everything the file drew. The bounds are Chapter 12
section 9's: each mesh's box in its own space, moved into the world by
`transformBounds` and merged. A sphere of radius *r* around that box just fits
a view whose half-angle is *θ* when the edge of the view grazes it. The sight
line touches the sphere at a right angle to the radius, so the camera, the
sphere's centre, and the touching point make a right triangle:

```text
                           touching point
                      .-'|
                  .-'    |  r
              .-'        |
   camera  o-'-----------+  centre
              θ
           |<--- d ----->|      sin θ = r / d,  so  d = r / sin θ
```

With the default 60° field of view, *θ* is 30°, and *d* = *r* / sin 30° = 2*r*.
The near and far planes scale with the scene — a hundredth of *r* and a
hundred *r* — so that a 5 cm part and a 500 m city are both framed and both
have usable depth precision:

```cpp
// File scope, above the namespace block. A file without a camera still has to be
// seen through something: add one that frames everything the file drew.
static void addCameraIfMissing(pf::scene::Scene& scene)
{
    if (scene.ActiveCamera() != pf::scene::INVALID_NODE) { return; }

    scene.UpdateWorldTransforms();
    pf::scene::Aabb world;
    for (pf::scene::NodeIndex node = 0; node < scene.NodeCount(); ++node)
    {
        const pf::scene::Node& n = scene.GetNode(node);
        if (n.mesh == pf::scene::NO_COMPONENT) { continue; }
        const pf::scene::Aabb box = pf::scene::transformBounds(scene.GetMesh(n.mesh).bounds, n.world);
        world.min = glm::min(world.min, box.min);
        world.max = glm::max(world.max, box.max);
    }
    const bool      empty  = world.min.x > world.max.x;
    const glm::vec3 centre = empty ? glm::vec3(0.0f) : 0.5f * (world.min + world.max);
    const float     radius = empty ? 1.0f : std::max(0.5f * glm::length(world.max - world.min), 0.01f);

    // Back far enough that a sphere of that radius fits the default 60-degree view.
    pf::scene::Transform pose;
    pose.rotation    = pf::scene::rotationFromYawPitch({ .yaw = glm::radians(30.0f), .pitch = glm::radians(-20.0f) });
    pose.translation = centre - pose.Forward() * (radius / std::sin(glm::radians(30.0f)));

    const pf::scene::Camera camera{ .nearPlane = 0.01f * radius, .farPlane = 100.0f * radius };
    const pf::scene::NodeIndex node = scene.AddNode("Viewer camera", pf::scene::ROOT_NODE, pose);
    scene.SetCamera(node, scene.AddCamera(camera));
    scene.SetActiveCamera(node);
    Log::info("The file has no camera; added \"Viewer camera\" framing the whole scene.");
}
```

Three details. The world matrices are brought up to date first, because the
import only set local transforms. The camera is a child of `ROOT_NODE`, **not
of the file's conversion node**: its pose is computed in engine space, metres
and Y-up, and under the file node it would be turned and scaled a second time.
And a file with no meshes (`min` is still above `max`) gets a camera framing a
unit sphere at the origin, rather than one built from infinities.

`loadScene` is everything that turns a file into a scene that can be drawn:

```cpp
// File scope, above the namespace block. Everything that turns a file into a
// complete scene, on the CPU only, so it can fail without touching the GPU.
static InitializationResult loadScene(const std::filesystem::path& file, pf::scene::Scene& scene)
{
    if (auto result = pf::usd_import::ImportUsdFile(file, scene); !result) { return result; }
    addCameraIfMissing(scene);
    scene.UpdateWorldTransforms();
    return InitializationResult::success();
}
```

None of it touches the GPU, and that is the point: a file can be tried, and
walked away from if it fails, with nothing to undo.

### Importing once

The **constructor** only stores the file name, and starts in Orbit mode, which
suits looking at an object better than flying:

```cpp
UsdViewerDemo::UsdViewerDemo(std::string startFile)
    : m_startFile(std::move(startFile))
{
    m_controls.active = scene::ControllerKind::Orbit;
}
```

**`FindFiles`** lists what can be opened. The directory is read with an
`error_code`, so a missing `Assets/Scenes` is an empty list rather than an
exception; `.usd` is included because it may hold either encoding, and
TinyUSDZ tells them apart by content. The list is **sorted** because directory
order is the file system's business — NTFS happens to return names sorted,
ext4 does not — and the panel should not reorder itself between machines. A
`--scene` that names no file is treated like an unknown `--demo` in Chapter 09:
a warning, and the first one. A `--scene` with a folder in it is a path, to a
scene kept anywhere — downloaded and converted outside the repository, say —
and that file joins the end of the list and is where the viewer starts. A
relative path is relative to the working directory, as any path typed on a
command line is.

```cpp
// The scene files beside the executable, sorted, and which one to start on.
void UsdViewerDemo::FindFiles()
{
    std::vector<std::pair<std::string, std::filesystem::path>> found;   // the name shown, the file
    std::error_code error;
    for (const auto& entry : std::filesystem::directory_iterator(scenesDirectory(), error))
    {
        const std::string extension = toUtf8(entry.path().extension());
        if (entry.is_regular_file() &&
            (extension == ".usda" || extension == ".usdc" || extension == ".usdz" || extension == ".usd"))
        {
            found.emplace_back(toUtf8(entry.path().filename()), entry.path());
        }
    }
    std::sort(found.begin(), found.end());

    // --scene came from the command line in the platform's own encoding; a path reads it that way.
    // With a folder in it, it names a file anywhere - a scene kept outside the repository - which
    // joins the end of the list and is where the viewer starts.
    const std::filesystem::path startPath(m_startFile);
    std::error_code ignored;
    const bool startsElsewhere = startPath.has_parent_path() && std::filesystem::is_regular_file(startPath, ignored);
    if (startsElsewhere)
    {
        found.emplace_back(toUtf8(startPath.filename()), std::filesystem::absolute(startPath, ignored));
    }
    m_files.clear();
    m_paths.clear();
    for (const auto& [name, path] : found)
    {
        m_files.push_back(name);
        m_paths.push_back(path);
    }
    if (startsElsewhere)
    {
        m_selectedFile = static_cast<int>(m_files.size()) - 1;
        return;
    }

    const std::string startFile = toUtf8(startPath);
    const auto start = std::find(m_files.begin(), m_files.end(), startFile);
    if (!m_startFile.empty() && start == m_files.end())
    {
        Log::warning(std::format("--scene \"{}\" is not in {}; starting on the first file.",
                                 startFile, toUtf8(scenesDirectory())).c_str());
    }
    m_selectedFile = start != m_files.end() ? static_cast<int>(start - m_files.begin()) : 0;
}
```

On Windows that encoding is the ANSI code page, because `main`'s `argv` is
converted to it. A name the page holds, such as `Café.usda` on an
English-language Windows, works with `--scene`; a Cyrillic one arrives as
question marks, gets the warning, and has to be picked from the list instead.
A path is read the same way, so a scene outside `Assets/Scenes` must sit in
folders whose names the page holds.
Taking the whole command line as UTF-8 would mean `wmain` or a UTF-8 code-page
manifest, more than one flag is worth.

**`Setup`** is where the import has to go: it is fallible — a missing or
malformed file — and constructors do nothing fallible. But `Setup` does not run
once. It runs every time the demo is switched to, after the last switch away
ran `Teardown` (Chapter 09 section 5) — and, from Chapter 18, whenever the
sample count changes, which rebuilds every scene pipeline the same way.
Importing each time would parse the file again and throw away every edit made
in the inspector. So `Setup` imports only
into an **empty scene** — one holding nothing but the root — and otherwise
uploads what is already there:

```cpp
InitializationResult UsdViewerDemo::Setup(const DemoContext& context)
{
    m_context = context;
    if (auto result = m_sceneRenderer.Initialize(m_context.vulkan, m_context.pipelineCache, m_context.formats);
        !result)
    {
        return result;
    }

    // Import once per demo object, not once per Setup. A sample-count change
    // (Chapter 18) runs Teardown and Setup again; importing again would throw
    // away every edit made in the inspector and parse the file a second time.
    if (m_scene.NodeCount() == 1)   // only the root: nothing imported yet
    {
        FindFiles();
        if (m_files.empty())
        {
            return InitializationResult::failure(
                std::format("No .usda, .usdc, or .usdz files in {}", toUtf8(scenesDirectory())));
        }
        if (auto result = loadScene(m_paths[static_cast<size_t>(m_selectedFile)], m_scene); !result)
        {
            return result;
        }
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

The test is the scene itself rather than a separate `m_imported` flag, so that
the two can never disagree. It also makes a failed start retryable: an import
that fails leaves the scene empty (`ImportUsdFile` fails before it adds a
node), Chapter 09's picker shows the message, and picking the demo again after
fixing the file imports it. The upload loops are Chapter 12's.

**`Resize`** is Chapter 12's:

```cpp
InitializationResult UsdViewerDemo::Resize(const vulkan_graphics::SceneTargets& targets)
{
    m_extent = targets.extent;   // Update builds the culling frustum before Record sees the targets
    return InitializationResult::success();
}
```

### Update, the panel, and Record

**`Update`** is Chapter 12's `SceneGraphDemo::Update` (section 10), copied,
with two things taken out. There is no animation, so its step 2 goes. And
there is no "Freeze frustum" checkbox, so the frustum is rebuilt every frame:
the `m_frustum = scene::frustumFromViewProjection(...)` line loses the
`if (!m_freezeFrustum)` around it. Everything else stays, `DrawPanel()` last
included.

The controllers are already right for imported cameras. They work on the
camera's **world** pose (Chapter 12 section 5), and an imported camera always
has a parent that is not the identity — at the least, the file's conversion
node. `SetWorldTransform` solves for the local transform under it, so dragging
the view of a Z-up centimetre file writes Z-up centimetre values into the
camera's node, and the inspector shows them.

**`DrawPanel`** is Chapter 11's Meshes panel — shading, front-face flip, sun —
without its Animate checkbox, plus Chapter 12's culling checkbox, counts, and
"Look through" list:

```cpp
void UsdViewerDemo::DrawPanel()
{
    if (debug_panels::beginDemoPanel("USD viewer", debug_panels::DemoPanelSlot::BelowCamera))
    {
        int shading = static_cast<int>(m_shading);
        ImGui::RadioButton("Lit", &shading, 0);
        ImGui::SameLine();
        ImGui::RadioButton("Normals", &shading, 1);
        m_shading = static_cast<vulkan_graphics::ShadingMode>(shading);

        ImGui::Checkbox("Flip front face", &m_frontFaceFlipped);
        ImGui::Checkbox("Frustum culling", &m_culling);
        ImGui::Text("Nodes: %zu   meshes: %zu   draws: %zu", m_scene.NodeCount(), m_scene.MeshCount(), m_draws.size());
        ImGui::Text("Culled: %u of %u", m_stats.culled, m_stats.considered);

        ImGui::SeparatorText("Sun");
        ImGui::SliderFloat("Azimuth", &m_sunAzimuth, 0.0f, 360.0f, "%.0f deg");
        ImGui::SliderFloat("Elevation", &m_sunElevation, -10.0f, 90.0f, "%.0f deg");

        // The pickers show and edit sRGB; the light is linear. Convert both ways.
        glm::vec3 sunColor = scene::linearToSrgb(m_sunColor);
        if (ImGui::ColorEdit3("Sun color", &sunColor.x)) { m_sunColor = scene::srgbToLinear(sunColor); }
        glm::vec3 ambient = scene::linearToSrgb(m_ambientColor);
        if (ImGui::ColorEdit3("Ambient", &ambient.x))    { m_ambientColor = scene::srgbToLinear(ambient); }

        // A file may hold several cameras; any of them can be looked through.
        ImGui::SeparatorText("Look through");
        for (scene::NodeIndex node = 0; node < m_scene.NodeCount(); ++node)
        {
            if (m_scene.GetNode(node).camera == scene::NO_COMPONENT) { continue; }
            if (ImGui::RadioButton(std::format("{}##{}", m_scene.GetNode(node).name, node).c_str(),
                                   m_scene.ActiveCamera() == node))
            {
                m_scene.SetActiveCamera(node);
            }
        }
    }
    ImGui::End();
}
```

One thing differs from the code it was copied from: the "Look through" labels
carry `##` and the node index. ImGui identifies a widget by its label, and file
authors reuse names freely — two cameras called `Camera` under different
parents is ordinary USD — which with plain labels would be two buttons with
one identity, so clicking either could select the wrong one. Everything after
`##` is part of the identity but is not shown.

**`Record`** is Chapter 11's `MeshesDemo::Record` — the sun from the panel,
the switches applied — with the camera taken from the active camera node, as
Chapter 12's `Record` does. After the line that computes `aspect`, add:

```cpp
    const scene::Node&   viewer = m_scene.GetNode(m_scene.ActiveCamera());
    const scene::Camera& camera = m_scene.GetCamera(viewer.camera);
```

and the three frame-data lines that read `m_camera` become:

```cpp
    frameData.view           = scene::viewMatrix(viewer.world);
    frameData.projection     = camera.Projection(aspect);
    frameData.cameraPosition = glm::vec4(glm::vec3(viewer.world[3]), 1.0f);
```

The sun stays the panel's, in **engine** space: it is the same sun whatever the
file's up axis, which is exactly what makes section 2's conversion visible —
an unconverted Z-up file is lit from the side.

**`Teardown`** releases the GPU side and nothing else:

```cpp
// GPU objects only. The imported scene, the camera, and every edit stay in m_scene.
void UsdViewerDemo::Teardown()
{
    m_sceneRenderer.Shutdown();
}
```

### Registering it, and `--scene`

**This is `Source/SandboxGame/Main.cpp`.** First, Chapter 13's exit check comes
out: the startup call to `LogUsdPrimTree`, and its two includes, `UsdImport.h`
and `ExecutableFiles.h`. `LogUsdPrimTree` stays in the module — it is the
quickest way to see what TinyUSDZ read when an import looks wrong.

`LaunchSettings` gains the file to start on, as Chapter 09 section 7 planned:

```cpp
struct LaunchSettings
{
    vulkan_graphics::RendererSettings renderer;
    std::string                       demo;   // part of a demo's Name(); empty = the first one
    std::string                       scene;  // Chapter 14: a file in Assets/Scenes for the USD viewer
};
```

and `parseSettings` a branch, after `--demo`'s:

```cpp
        else if (key == "--scene")
        {
            settings.scene = value;
        }
```

The demo is registered after the scene graph's, with the file name passed to
its constructor — which only stores it:

```cpp
    demoList.push_back(std::make_unique<demos::usd_viewer::UsdViewerDemo>(settings.scene));   // Chapter 14
```

and `#include "PillowFort/Demos/UsdViewer/UsdViewerDemo.h"` beside the other
demos'.

Build, and run `SandboxGame --demo USD --scene Basics.usda`, then the same
with `--scene Basics_ZUpCm.usda`. Both must match section 8's table, and each
other. That is a complete viewer, and a good place to stop for an evening:
section 10 only makes the comparison one click instead of a restart.

---

## 10. Switching files while it runs

**This is `SwitchToFile`**, and the four small changes around it: a file list
in the panel, the panel drawn first, and a flag that lets `Record` cope with a
failed switch. With it, section 8's comparison is one click instead of a
restart.

Picking another file in the panel replaces the whole scene. The new file is
loaded **first**, into a scene of its own, on the CPU; only if that works is
anything on the GPU touched.

> **Jump:** until now, only the harness called a demo's `Setup` and
> `Teardown` (Chapter 09 section 5's `switchDemo`), and it keeps three
> promises around them:
> it waits for the device to be idle before `Teardown`; it calls `Resize` after
> every successful `Setup`; and when `Setup` fails, it stops calling `Update`
> and `Record`. `SwitchToFile` calls `Teardown` and `Setup` on its own demo,
> from inside `Update`, while the harness believes nothing has changed — so the
> demo has to keep those promises itself. Hold all three while reading it: the
> wait is explicit; `Resize` can be skipped only because this demo's `Resize`
> keeps nothing that `Setup` rebuilds; and a failed `Setup` is answered by
> `m_ready`, because the harness *will* go on calling `Record`.

The header gains the function and two members. In `UsdViewerDemo.h`,
`SwitchToFile` goes after `FindFiles`, `m_ready` after `m_sceneRenderer`, and
`m_status` after `m_selectedFile`:

```cpp
    void SwitchToFile(int index);

    bool                           m_ready = false;   // Setup finished: the scene renderer can draw

    std::string                   m_status;              // the last import's error, shown in the panel
```

`m_status` holds the last failed import's message, because a failure while
the demo runs has nowhere to go but the log and the panel. `m_ready` says that
`Setup` finished: it is the one piece of GPU state the demo must be able to ask
about. `Setup` sets it as its last step, after the upload loops:

```cpp
    m_ready = true;
    return InitializationResult::success();
```

and `Teardown` clears it first:

```cpp
// GPU objects only. The imported scene, the camera, and every edit stay in m_scene.
void UsdViewerDemo::Teardown()
{
    m_ready = false;
    m_sceneRenderer.Shutdown();
}
```

Then the function itself:

```cpp
// Replace the scene with another file's. The new file is loaded first, on the
// CPU: if it fails, the old scene stays and the panel says why. Only then are
// the GPU copies replaced, after waiting for the frames that still draw them.
void UsdViewerDemo::SwitchToFile(int index)
{
    scene::Scene loaded;
    if (auto result = loadScene(m_paths[static_cast<size_t>(index)], loaded); !result)
    {
        // All of it to the log; only the first line to the panel, because
        // TinyUSDZ follows it with a stack of its own source locations.
        Log::error(result.message());
        const std::string message = result.message();
        m_status = message.substr(0, message.find('\n'));
        return;
    }

    vkDeviceWaitIdle(m_context.vulkan.device);
    Teardown();
    m_scene            = std::move(loaded);
    m_editor           = {};
    m_controlledCamera = scene::INVALID_NODE;
    m_selectedFile     = index;
    m_status.clear();
    if (auto result = Setup(m_context); !result)
    {
        Log::error(result.message());
        m_status = result.message();
    }
}
```

In order:

- **A failed load changes nothing.** The old scene, its GPU copies, and every
  edit stay; the log gets TinyUSDZ's whole message — file, line, column, and
  the parser's stack — and the panel its first line.
- **`vkDeviceWaitIdle`**, because up to `FRAMES_IN_FLIGHT` frames already
  submitted still read the old meshes' vertex and index buffers. The harness
  does exactly this before its own `Teardown`. Waiting for the whole device is
  heavy-handed, but this is a click, not a frame.
- **`Teardown`** destroys the scene renderer's meshes and materials (Chapter 11
  section 11's `Shutdown` takes them with it), and the new scene moves in.
- **`m_editor` is reset**, because its selection is a `NodeIndex` into the old
  scene and would select an unrelated node in the new one — or one past its
  end. **`m_controlledCamera` is reset** so that the next `Update` treats the
  new file's camera as a newly active one: held keys released, the orbit
  re-aimed (Chapter 12 section 5).
- **`Setup`** uploads the new scene; it does not import, because the scene is
  no longer empty. Chapter 09 would call `Resize` next. This `Resize` only
  keeps the extent, which a file switch does not change, so there is nothing to
  redo — but a later chapter that gives the viewer window-sized resources must
  keep the `SceneTargets` and call `Resize` here as well.

`Setup` has already succeeded once with the same context, so it failing now
takes something unusual — a shader deleted while the program runs, or video
memory exhausted. When it does, the scene renderer holds nothing, `m_ready` is
false, and `Record` must cope. The panel still works, so picking another file
tries again.

**The file list** goes at the top of `DrawPanel`, right after
`if (debug_panels::beginDemoPanel("USD viewer", ...))`, with the last error under it:

```cpp
        const char* current = m_files.empty() ? "(none)" : m_files[static_cast<size_t>(m_selectedFile)].c_str();
        if (ImGui::BeginCombo("File", current))
        {
            for (int i = 0; i < static_cast<int>(m_files.size()); ++i)
            {
                if (ImGui::Selectable(m_files[static_cast<size_t>(i)].c_str(), i == m_selectedFile) &&
                    i != m_selectedFile)
                {
                    SwitchToFile(i);
                }
            }
            ImGui::EndCombo();
        }
        if (!m_status.empty())
        {
            ImGui::PushTextWrapPos(280.0f);   // a long path wraps instead of widening the panel
            ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f), "%s", m_status.c_str());
            ImGui::PopTextWrapPos();
        }
```

`SwitchToFile` runs **inside** the combo, while ImGui is still building this
frame's widgets. That is safe because ImGui's draw data does not refer to the
scene renderer, and `m_files`, which the loop walks, is changed only by
`FindFiles`, which a switch does not call. The file list is read when the
first file is imported, so a file added to `Assets/Scenes` while the program
runs appears after a restart.

**`DrawPanel` moves to the top of `Update`.** Take `DrawPanel();` from the end
of `Update` and make it the first line:

```cpp
    // 1. The viewer's own panel first: picking another file replaces m_scene,
    //    and everything below must see the new one.
    DrawPanel();
```

Chapter 12 drew its panel last, so that the statistics in it were this frame's.
Here that order would be a bug: a file picked in a panel drawn last would
replace `m_scene` **after** `m_draws` was collected from the old one, and
`Record` would hand the scene renderer a list of the old file's mesh indices
for the new file's meshes — out of range, or the wrong meshes. Drawn first, a
switch happens before anything reads the scene. The price is that the panel's
draw and culling counts are one frame old, which nobody can see.

**`Record` gets a first branch**, for the one state a failed switch can leave.
Move its `clearColor` line from just before `beginScenePass` to the top, after
`commandBuffer`, and add the branch below it:

```cpp
    const VkCommandBuffer   commandBuffer = frame.commandBuffer;
    const VkClearColorValue clearColor{ { 0.02f, 0.02f, 0.03f, 1.0f } };

    // Only after a failed switch (section 10): the scene renderer holds nothing,
    // not even a mapped frame buffer, but the scene target must still be cleared
    // and handed back, as Chapter 09 asks of every Record.
    if (!m_ready)
    {
        vulkan_graphics::beginScenePass(commandBuffer, frame.targets, &clearColor);
        vulkan_graphics::endScenePass(commandBuffer);
        vulkan_graphics::handBackSceneTarget(commandBuffer, frame.targets);
        return;
    }
```

The branch is not optional politeness. Chapter 09 section 4 asks every
active demo's `Record` to write every pixel of the scene target and leave it
ready for the composite. A `Record` that simply returned would leave the old
file's last frame frozen behind the panels — or, after a resize, a new target
still in `UNDEFINED` layout, which validation reports as soon as the composite
samples it. And `WriteFrameData` after a failed `Setup` would `memcpy` into a
buffer that was never mapped. So the branch does the least that is correct: an
empty pass, which clears, and the hand-back.

## Checkpoint

Part 1 is complete. Run the viewer and you can see:

- `--scene Basics.usda`: the box, turned 45°, left of centre and the ball to
  its right, on a pale ground, through the file's own camera; the Scene panel
  shows Root ▸ Basics ▸ World and the file's tree under it.
- Pick `Basics_ZUpCm.usda` in the File list (or, before section 10, start
  with `--scene Basics_ZUpCm.usda`): the picture and the Camera panel's
  numbers do not change. Only the file node's transform does.
- Pick `FirstStage.usda`, Chapter 13's file: its transforms and camera import,
  its tabletop does not, and the log says
  `FirstStage.usda: skipped 1 prim(s) of type Mesh and everything under them.`
  Part 2 imports it.

---

# Part 2 — The polygons (sections 11-15)

Part 1 imported every prim but `Mesh`. This part imports polygon meshes: their
faces become triangles (section 11), their per-point and per-corner data
becomes vertices (section 12), and their GeomSubsets become submeshes (section
13), where `importMesh` is finished and joins the walk. Section 14 tests it on
hand-written meshes, and section 15 on a scene exported from Blender.

## 11. Polygons to triangles

**This is `Corner`, `triangulate`, and the first part of `importMesh`.**

A USD mesh's topology is two arrays: `faceVertexCounts`, how many corners each
face has, and `faceVertexIndices`, the point index of each corner, face after
face. A cube is `counts = [4, 4, 4, 4, 4, 4]` and 24 indices. The GPU wants
triangles.

A **fan** triangulates a polygon (v₀, v₁, …, vₙ₋₁) into (v₀, v₁, v₂),
(v₀, v₂, v₃), …, (v₀, vₙ₋₂, vₙ₋₁): *n* − 2 triangles, each keeping the
polygon's winding. It is exact for convex polygons — every quad Blender
writes for a cube or a sphere, and the 16-sided cap of a cone. For a concave
polygon (an L-shaped face, a star) some fan triangles lie outside the polygon
and overlap others, and the shape comes out wrong. Two remedies, neither
needed by this chapter's files: tick *Triangulate Meshes* in Blender's export
(section 15), which hands you triangles; or replace the inner loop below with
earcut, which TinyUSDZ bundles. The importer logs a note for any mesh with
faces of more than four sides, so a mis-shaped prop can be traced to it.

Triangulating is also the moment to keep what later steps need. Section 12
reads attributes by **face** (uniform), by **point** (vertex), or by
**face-vertex** (faceVarying), so each triangle corner remembers all three:

```cpp
// File scope, above the namespace block. Section 11: one entry per triangle corner,
// remembering the three numbers that USD's interpolation modes index by.
struct Corner
{
    uint32_t face;         // which polygon: uniform data, GeomSubsets
    uint32_t faceVertex;   // position in faceVertexIndices: faceVarying data
    uint32_t point;        // faceVertexIndices[faceVertex]: vertex data, positions
};
```

`triangulate` produces the corners, three per triangle, and `faceStart[f]`,
the first corner of face *f* — section 13 uses it to pull out one face's
triangles. It also checks the topology, because a file that lies about it
(counts that add up to more indices than exist, an index past the last point)
would otherwise send the importer reading past the end of an array. A broken
mesh is reported and skipped:

```cpp
// File scope, above the namespace block. Section 11: fan triangulation. Polygon
// (v0, v1, ..., vn-1) becomes (v0, v1, v2), (v0, v2, v3), ... - exact for convex
// polygons. faceStart[f] is face f's first corner; faces with fewer than three
// vertices produce none. An empty result with `problem` set means the topology
// is invalid and the mesh must be skipped.
static std::vector<Corner> triangulate(const std::vector<int32_t>& counts, const std::vector<int32_t>& indices,
                                       size_t pointCount, std::vector<uint32_t>& faceStart, std::string& problem)
{
    std::vector<Corner> corners;
    faceStart.assign(counts.size() + 1, 0);

    size_t offset = 0;
    for (size_t face = 0; face < counts.size(); ++face)
    {
        faceStart[face] = static_cast<uint32_t>(corners.size());
        const size_t count = static_cast<size_t>(std::max(counts[face], 0));
        if (offset + count > indices.size())
        {
            problem = "faceVertexCounts adds up to more than faceVertexIndices holds";
            return {};
        }
        for (size_t i = offset; i < offset + count; ++i)
        {
            if (indices[i] < 0 || static_cast<size_t>(indices[i]) >= pointCount)
            {
                problem = std::format("faceVertexIndices[{}] = {} is not a point", i, indices[i]);
                return {};
            }
        }
        for (size_t i = 1; i + 1 < count; ++i)
        {
            for (const size_t faceVertex : { offset, offset + i, offset + i + 1 })
            {
                corners.push_back({ .face       = static_cast<uint32_t>(face),
                                    .faceVertex = static_cast<uint32_t>(faceVertex),
                                    .point      = static_cast<uint32_t>(indices[faceVertex]) });
            }
        }
        offset += count;
    }
    faceStart[counts.size()] = static_cast<uint32_t>(corners.size());
    return corners;
}
```

`faceStart` has one more entry than there are faces, so `faceStart[f + 1]` is
always the end of face *f*, even for the last one. Faces with fewer than three
corners (USD allows them; they draw nothing) simply contribute no triangles.

**This is `importMesh`, first part** — reading the arrays and triangulating.
`get_points`, `get_faceVertexCounts`, and `get_faceVertexIndices` take a time;
`Default` is Chapter 13's default time. A mesh whose points exist only as
time samples comes back with no points, fails the index check, and is skipped
with a warning — the import-side face of the decision to read only default
values.

```cpp
// File scope, above the namespace block. Sections 11-13: a UsdGeomMesh.
static void importMesh(ImportContext& context, const tinyusdz::Prim& prim, const tinyusdz::GeomMesh& mesh,
                       bool mirrored, pf::scene::NodeIndex node, const std::string& path)
{
    const double time = tinyusdz::value::TimeCode::Default();
    const std::vector<tinyusdz::value::point3f> points  = mesh.get_points(time);
    const std::vector<int32_t>                  counts  = mesh.get_faceVertexCounts(time);
    const std::vector<int32_t>                  indices = mesh.get_faceVertexIndices(time);

    std::vector<uint32_t>     faceStart;
    std::string               problem;
    const std::vector<Corner> corners = triangulate(counts, indices, points.size(), faceStart, problem);
    if (corners.empty())
    {
        Log::warning(std::format("{}: skipped, {}.", path, problem.empty() ? "no triangles" : problem).c_str());
        return;
    }
    if (std::any_of(counts.begin(), counts.end(), [](int32_t count) { return count > 4; }))
    {
        Log::info(std::format("{}: has polygons with more than four sides; fan triangulation is "
                              "right only if they are convex.", path).c_str());
    }

    // USD's fallback is "catmullClark": a mesh that does not say "none" asks to be
    // drawn as a subdivision surface, and its points are only the control cage.
    if (mesh.subdivisionScheme.get_value() != tinyusdz::GeomMesh::SubdivisionScheme::SubdivisionSchemeNone)
    {
        Log::warning(std::format("{}: asks for subdivision, which this importer does not do; "
                                 "drawing its control cage.", path).c_str());
    }
```

The subdivision warning is a USD trap worth knowing. `subdivisionScheme`'s
fallback is `catmullClark`, so a mesh that does not say `"none"` is, by the
spec, a *subdivision surface* (Chapter 13 section 9) whose points are only its
control cage — Pixar's viewer draws a hand-written cube without it as a
rounded blob. Blender writes `"none"` for ordinary meshes, and this chapter's
test files do too; Chapter 13's `FirstStage.usda` does not, so it gets the
warning. Subdividing is out of scope, so the cage is drawn and the warning
says so.

---

## 12. Primvars become vertex attributes

**This is the second part of `importMesh`, with `elementFor`,
`expectedLength`, and `readUvs`** — the mesh's orientation, then normals and
texture coordinates, by interpolation, into one vertex per index.

First, section 4's `leftHanded`, read from the mesh. The flat normals below
need it, and section 13 passes it on to `addMesh`:

```cpp
    const bool leftHanded = mesh.orientation.get_value() == tinyusdz::Orientation::LeftHanded;
```

Chapter 13 section 9's table gave the rule for which value a corner gets.
With `Corner` carrying all three indices, the rule is a `switch`:

```cpp
// File scope, above the namespace block. Section 12: which element of a primvar's
// array belongs to a corner. The interpolation says what the array is indexed by.
static size_t elementFor(tinyusdz::Interpolation interpolation, const Corner& corner)
{
    switch (interpolation)
    {
    case tinyusdz::Interpolation::Constant:    return 0;
    case tinyusdz::Interpolation::Uniform:     return corner.face;
    case tinyusdz::Interpolation::Vertex:
    case tinyusdz::Interpolation::Varying:     return corner.point;     // the same for a polygon mesh
    case tinyusdz::Interpolation::FaceVarying: return corner.faceVertex;
    default:                                   return SIZE_MAX;
    }
}
```

`vertex` and `varying` differ only for subdivision surfaces, which this
importer does not draw. An array whose length does not match its
interpolation is a malformed file — and reading it would run past its end —
so each array is checked once, against the length the table says it must
have:

```cpp
// File scope, above the namespace block. Section 12: how long a primvar's array must
// be for its interpolation - anything else is a malformed file.
static size_t expectedLength(tinyusdz::Interpolation interpolation, size_t faces, size_t points, size_t faceVertices)
{
    switch (interpolation)
    {
    case tinyusdz::Interpolation::Constant:    return 1;
    case tinyusdz::Interpolation::Uniform:     return faces;
    case tinyusdz::Interpolation::Vertex:
    case tinyusdz::Interpolation::Varying:     return points;
    case tinyusdz::Interpolation::FaceVarying: return faceVertices;
    default:                                   return 0;
    }
}
```

That check is what makes the unchecked `normals[elementFor(...)]` below safe:
every array that survives it is exactly as long as the largest index its
interpolation can produce.

**Normals.** `GeomMesh::get_normals` reads `primvars:normals` if it exists and
the `normals` attribute otherwise, expanding an indexed primvar;
`get_normalsInterpolation` returns its interpolation, `vertex` if unauthored.
A mesh may have no normals at all — three of section 14's four meshes have
none — and then the importer makes one per face. **Newell's method** adds up
`cross(a, b)` (Chapter 12 section 5) for every edge `a → b` of the polygon,
with `a` and `b` the corners' positions. For a triangle the sum is exactly
Chapter 11 section 4's `cross(b - a, c - a)`; for a bigger polygon every edge
adds its share, so no three "good" corners need choosing and three corners in
a row cannot zero it. The sum points along the face's normal, on the side from
which the corners wind counter-clockwise. A left-handed mesh's front is the
other side, so its computed normals are negated:

```cpp
    // Normals: authored ones if their array fits their interpolation, else one flat
    // normal per face.
    std::vector<glm::vec3> normals;
    tinyusdz::Interpolation normalInterpolation = mesh.get_normalsInterpolation();
    for (const auto& n : mesh.get_normals(time)) { normals.emplace_back(n.x, n.y, n.z); }
    if (!normals.empty() &&
        normals.size() != expectedLength(normalInterpolation, counts.size(), points.size(), indices.size()))
    {
        Log::warning(std::format("{}: {} normals do not match their interpolation; computing flat normals.",
                                 path, normals.size()).c_str());
        normals.clear();
    }
    if (normals.empty())
    {
        // Newell's method: the sum of cross products around the polygon is a vector
        // along its normal, pointing the way its vertices wind counter-clockwise.
        // A left-handed mesh's front is the other side.
        normalInterpolation = tinyusdz::Interpolation::Uniform;
        normals.assign(counts.size(), glm::vec3(0.0f));
        size_t offset = 0;
        for (size_t face = 0; face < counts.size(); ++face)
        {
            const size_t count = static_cast<size_t>(std::max(counts[face], 0));
            glm::vec3 sum(0.0f);
            for (size_t i = 0; i < count; ++i)
            {
                const auto& a = points[static_cast<size_t>(indices[offset + i])];
                const auto& b = points[static_cast<size_t>(indices[offset + (i + 1) % count])];
                sum += glm::cross(glm::vec3(a.x, a.y, a.z), glm::vec3(b.x, b.y, b.z));
            }
            const float length = glm::length(sum);
            normals[face] = (length > 0.0f ? sum / length : glm::vec3(0.0f, 1.0f, 0.0f)) * (leftHanded ? -1.0f : 1.0f);
            offset += count;
        }
    }
```

Normals stay in the mesh's local space, as positions do; Chapter 11's normal
matrix (the inverse transpose of the model matrix) carries both into the
world, mirror and conversion node included.

**Texture coordinates.** USD's convention is a `texCoord2f[]` primvar named
`st`. Exporters vary: Blender before 4.x named it after the UV map
(`primvars:UVMap`), and 4.x writes `st` only while *Rename UV Maps* is ticked.
So `readUvs` asks for `st` and otherwise takes the first primvar of type
`texCoord2f[]`. `flatten_with_indices` expands an indexed primvar (Chapter 13
section 9) into one value per element, so the indices never reach the code
after it. A file may also store texture coordinates as plain `float2[]`, which
is the second branch:

```cpp
// File scope, above the namespace block. Section 12: the texture coordinates. USD's
// name for them is `st`; Blender wrote the UV map's own name (`UVMap`) before 4.x,
// so fall back to the first texCoord2f[] primvar there is.
static bool readUvs(const tinyusdz::GeomMesh& mesh, std::vector<glm::vec2>& uvs,
                    tinyusdz::Interpolation& interpolation, std::string& name)
{
    tinyusdz::GeomPrimvar primvar;
    bool found = mesh.get_primvar("st", &primvar);
    if (!found)
    {
        for (const tinyusdz::GeomPrimvar& candidate : mesh.get_primvars())
        {
            if (candidate.type_name() == "texCoord2f[]")
            {
                primvar = candidate;
                found   = true;
                break;
            }
        }
    }
    if (!found)
    {
        return false;
    }

    // flatten_with_indices expands an indexed primvar (values + indices) into one
    // value per element, so the code below never sees the indices.
    std::vector<tinyusdz::value::texcoord2f> texcoords;
    std::vector<tinyusdz::value::float2>     float2s;
    uvs.clear();
    if (primvar.flatten_with_indices(&texcoords))
    {
        for (const auto& t : texcoords) { uvs.emplace_back(t.s, t.t); }
    }
    else if (primvar.flatten_with_indices(&float2s))
    {
        for (const auto& t : float2s) { uvs.emplace_back(t[0], t[1]); }
    }
    else
    {
        return false;
    }
    interpolation = primvar.get_interpolation();
    name          = primvar.name();
    return true;
}
```

In `importMesh`, a texture-coordinate array of the wrong length is dropped
with a warning, and the mesh imports without texture coordinates:

```cpp
    std::vector<glm::vec2>  uvs;
    tinyusdz::Interpolation uvInterpolation = tinyusdz::Interpolation::Constant;
    std::string             uvName;
    if (readUvs(mesh, uvs, uvInterpolation, uvName) &&
        uvs.size() != expectedLength(uvInterpolation, counts.size(), points.size(), indices.size()))
    {
        Log::warning(std::format("{}: primvars:{} does not match its interpolation; ignoring it.",
                                 path, uvName).c_str());
        uvs.clear();
    }
```

**One vertex per distinct corner.** Now each triangle corner has a position,
a normal, and a texture coordinate, each looked up by its own interpolation.
Chapter 11's vertex buffer wants one `Vertex` per index, so corners that agree
on all three may share a vertex, and corners that differ in any one must not.
A map from the three values to a vertex index does exactly that:

> **Jump:** Chapter 11 built meshes whose vertices you chose, so "a vertex"
> and "a point" were the same thing. In USD they are not. A *point* is a
> position; a GPU *vertex* is a position **plus everything else interpolated
> with it**. One point at a cube's corner is three vertices (three normals);
> one point on a UV seam is two (two texture coordinates). The vertex count of
> an imported mesh is therefore decided by its attributes, not by its points —
> a Blender cube is 8 points and 24 vertices — and the same point can sit in
> the index buffer under several vertex numbers. Nothing downstream needs to
> know; it is why the map below exists.

```cpp
    // One vertex per distinct (position, normal, uv): corners that agree on all
    // three share a vertex, corners that differ in any one get their own. That is
    // what turns USD's per-corner (faceVarying) data into one index buffer.
    pf::scene::MeshData                         data;
    std::vector<uint32_t>                       cornerVertex(corners.size());
    std::map<std::array<float, 8>, uint32_t>    vertexOf;   // position, normal, uv -> vertex
    for (size_t c = 0; c < corners.size(); ++c)
    {
        const Corner&          corner = corners[c];
        const auto&            p      = points[corner.point];
        const glm::vec2        uv     = uvs.empty() ? glm::vec2(0.0f) : uvs[elementFor(uvInterpolation, corner)];
        const pf::scene::Vertex vertex{
            .position = glm::vec3(p.x, p.y, p.z),
            .normal   = normals[elementFor(normalInterpolation, corner)],
            .uv       = glm::vec2(uv.x, 1.0f - uv.y),   // USD's v runs up from the bottom; Vulkan's down from the top
            .tangent  = glm::vec4(0.0f),                // chapter 15
        };
        const std::array<float, 8> key{ vertex.position.x, vertex.position.y, vertex.position.z,
                                        vertex.normal.x, vertex.normal.y, vertex.normal.z,
                                        vertex.uv.x, vertex.uv.y };
        const auto [it, inserted] = vertexOf.try_emplace(key, static_cast<uint32_t>(data.vertices.size()));
        if (inserted)
        {
            data.vertices.push_back(vertex);
        }
        cornerVertex[c] = it->second;
    }
```

Three details in it:

- **The V flip.** USD puts texture coordinate (0, 0) at the image's
  **bottom**-left, as OpenGL does; Vulkan's image origin, and so Chapter 08's
  and Chapter 15's sampling, is the **top**-left. `1 - v` here, once, means no
  shader and no texture loader ever flips anything. Do not "fix" an
  upside-down texture in Chapter 15 anywhere but here.
- **The key compares exact floats.** Two corners merge only when their values
  are bit-for-bit equal — which they are whenever they came from the same
  array element, the only case that matters. A tolerance would merge corners
  the author meant to keep apart.
- **`std::map`, not a hash map.** It is simple and fast enough for a scene
  you import once at startup — Blender's 528-triangle sphere is
  instantaneous. A mesh of millions of corners would want an
  `std::unordered_map` with a hash of the eight floats.

`cornerVertex[c]` is the vertex number of corner *c*; section 13 turns those
into the index buffer, grouped by GeomSubset.

---

## 13. GeomSubsets become submeshes, and meshes join the walk

**This is the third and last part of `importMesh`, and the two lines that
hook it into section 7's walk.**

A **GeomSubset** is a child prim of a mesh that names some of its faces. The
ones that matter here have `familyName = "materialBind"`: each binds a
material to its faces, which is how one mesh carries several materials —
Blender writes one subset per material slot that has faces. Chapter 11's
`MeshData` already has the matching idea: `submeshes`, contiguous ranges of
the index buffer, each with a material index, drawn as separate draws. So:
one submesh per subset, in the order the file lists them, with the faces no
subset claims gathered into one more. A mesh with no subsets has exactly one
submesh, the whole mesh.

`tydra::GetGeomSubsetChildren` finds the subsets of a family. Each subset's
`indices` are face numbers, and `faceStart` from section 11 maps a face to its
triangles' corners. A face named by two subsets is a malformed file
(`materialBind` is a non-overlapping family); the first claim wins, so the
index buffer never holds a face twice:

```cpp
    // GeomSubsets: each materialBind subset becomes one submesh, a contiguous range
    // of the index buffer, in the order the file lists them; faces no subset claims
    // form one more. Chapter 15 gives each its material; until then all use the default.
    std::vector<const tinyusdz::GeomSubset*> sources =
        tinyusdz::tydra::GetGeomSubsetChildren(prim, tinyusdz::value::token("materialBind"));
    std::vector<std::vector<uint32_t>> facesOf(sources.size());
    std::vector<bool>                  claimed(counts.size(), false);
    for (size_t s = 0; s < sources.size(); ++s)
    {
        std::vector<int32_t> subsetFaces;
        if (const auto value = sources[s]->indices.get_value())
        {
            value.value().get_default(&subsetFaces);
        }
        for (const int32_t face : subsetFaces)
        {
            if (face >= 0 && static_cast<size_t>(face) < counts.size() && !claimed[static_cast<size_t>(face)])
            {
                claimed[static_cast<size_t>(face)] = true;
                facesOf[s].push_back(static_cast<uint32_t>(face));
            }
        }
    }
    std::vector<uint32_t> unclaimed;
    for (size_t face = 0; face < counts.size(); ++face)
    {
        if (!claimed[face]) { unclaimed.push_back(static_cast<uint32_t>(face)); }
    }
    if (sources.empty() || !unclaimed.empty())
    {
        sources.push_back(nullptr);   // the faces no subset claims (or the whole mesh)
        facesOf.push_back(std::move(unclaimed));
    }
```

`sources` now lists, for each submesh to come, the subset it came from —
`nullptr` for "the rest". It stays parallel to `data.submeshes`, and it is
the hook Chapter 15 uses to look up each submesh's material binding. A
subset's `indices` attribute is read with `get_default`: the default-time
value, as everywhere in this importer.

Then the index buffer is written subset by subset, so each subset's faces are
contiguous, and each range becomes a `Submesh`:

```cpp
    std::string subsetNames;
    for (size_t s = 0; s < sources.size(); ++s)
    {
        const uint32_t first = static_cast<uint32_t>(data.indices.size());
        for (const uint32_t face : facesOf[s])
        {
            for (uint32_t c = faceStart[face]; c < faceStart[face + 1]; ++c)
            {
                data.indices.push_back(cornerVertex[c]);
            }
        }
        data.submeshes.push_back({ .firstIndex    = first,
                                   .indexCount    = static_cast<uint32_t>(data.indices.size()) - first,
                                   .materialIndex = pf::scene::DEFAULT_MATERIAL });
        subsetNames += sources[s] != nullptr ? " " + sources[s]->name : " (rest)";
    }
    if (sources.size() > 1)
    {
        Log::info(std::format("{}: {} submeshes:{}", path, sources.size(), subsetNames).c_str());
    }

    data.doubleSided = mesh.doubleSided.get_value();
    addMesh(context, prim, std::move(data), leftHanded != mirrored, node);
}
```

Every submesh uses `DEFAULT_MATERIAL` until Chapter 15, so a mesh with three
subsets draws as three grey draws. The log line is how you see them now;
Chapter 15 makes them visible. The last two lines finish the mesh: USD's
`doubleSided` goes straight into `MeshData`, and section 4's `addMesh` fixes
the winding — `leftHanded != mirrored` — and attaches the mesh to its node.

### Meshes join the walk

`importMesh` is complete, so the walk can call it. Two changes to section 7's
code. In `asXformable`, `GeomMesh` joins the list, after `Xform`:

```cpp
    if (const auto* mesh = prim.as<tinyusdz::GeomMesh>())     { return mesh; }
```

And in `importPrim`, the dispatch gains a first branch, so the sphere's `if`
becomes an `else if`; the rest of the dispatch is unchanged:

```cpp
    if (const auto* mesh = prim.as<tinyusdz::GeomMesh>())
    {
        importMesh(context, prim, *mesh, mirrored, node, path);
    }
    else if (const auto* sphere = prim.as<tinyusdz::GeomSphere>())
    {
        double radius = 1.0;
        sphere->radius.get_value().get_default(&radius);
        importShape(context, prim, *sphere, pf::scene::makeUvSphere(static_cast<float>(radius)), mirrored, node);
    }
```

From here a `Mesh` prim is a node with a mesh, and the `skipped … type Mesh`
line is gone from the log. `FirstStage.usda` now shows its tabletop, at
(1, 0.5, 0), where Chapter 13 section 9 put it.

---

## 14. A polygon test scene: `Facing.usda`

**This is the hand-written file Part 2 is tested with.** Its full text is in
this chapter's **Appendix A**; save it as `Assets/Scenes/Facing.usda`. Every
mesh in it says `subdivisionScheme = "none"`, and it holds:

- **Three cubes that must look identical.** `RightHanded` is an ordinary cube.
  `LeftHanded` lists each face's corners in reverse — its first face is
  `[3, 2, 1, 0]` where `RightHanded`'s is `[0, 1, 2, 3]` — and says so with
  `uniform token orientation = "leftHanded"`. `Mirrored` is an ordinary cube
  under a parent scaled by (−1, 1, 1). None has authored normals, so the
  importer computes flat ones and must get their side right too; and none is
  `doubleSided`, so culling is on and a cube whose winding is wrong shows its
  inside.
- **Two GeomSubsets** on `RightHanded` that leave one face unclaimed: `Caps`
  (faces 4 and 5) and `Sides` (faces 0, 1, and 2).
- **A gem**, an octahedron above the cubes, whose normals are per point
  (`vertex`) and whose texture coordinates are per corner (`faceVarying`) and
  indexed, three values reused by all eight faces:

```text
texCoord2f[] primvars:st = [(0, 0), (1, 0), (0.5, 1)] (
    interpolation = "faceVarying"
)
int[] primvars:st:indices = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]
```

What the import must produce, and why:

| Thing | Expected | Because |
| --- | --- | --- |
| The log | `/World/RightHanded: 3 submeshes: Caps Sides (rest)` and `Facing.usda: imported 8 nodes, 4 meshes (44 triangles), 1 cameras.` | three cubes of 12 triangles and a gem of 8 |
| The inspector, `RightHanded` | `RightHanded: 24 vertices, 3 submesh(es)` | flat normals: each face's four corners have their own; two subsets and the rest |
| The inspector, `Gem` | `Gem: 10 vertices, 1 submesh(es)` | 6 points, but each of the 4 round its middle takes two texture coordinates |
| The picture | three identical cubes, all facing outward, and a smoothly shaded gem | section 4's `leftHanded != mirrored`; per-point normals interpolate across each face |

If a mesh of your own renders inside out and you cannot see why, check it the
way Chapter 11 section 4 checked the generators: for every triangle,
`cross(b - a, c - a)` in world space must point the same way as its normals.

---

## 15. Scenes from Blender

**This is what Blender writes, and the export settings that make it
importable.** Blender 4.5 LTS was used; earlier 4.x versions have the same
exporter with fewer options.

### The test scene

A small scene with each thing worth checking: a ground plane; an empty
("Rig") rotated 30° about Blender's up axis, with a cube parented to it that
has two materials (top and bottom one, sides another — two GeomSubsets); a
smooth-shaded UV sphere scaled to 0.6; a cone mirrored with a scale of −1;
and a camera aimed at the middle. Build it by hand if you like Blender, or run
the script in this chapter's **Appendix B** in Blender's *Scripting*
workspace, with `EXPORT_PATH` set to your checkout's
`Assets/Scenes/BlenderScene.usdc`.

### The export settings, and why

For a scene of your own, *File ▸ Export ▸ Universal Scene Description*, with:

| Setting (panel) | Value | Why |
| --- | --- | --- |
| Selection Only, Visible Only (General) | off, on | Everything you can see. |
| Animation (General) | **off** | The importer reads the default time; with animation on, Blender writes time samples and the default value may be missing (Chapter 13 section 10). |
| Convert Orientation (General) | **off** | Leave the file honestly Z-up; the importer converts. (On, Blender adds a −90° X rotation to its own root prim and writes `upAxis = "Y"` — that imports correctly too, which is a good check of section 2.) |
| Units (General) | Meters | Centimetres also imports correctly (section 6's camera check); metres keeps the inspector's numbers equal to Blender's. |
| Normals, UV Maps, Rename UV Maps (Geometry) | on | `primvars:st`, and authored normals with Blender's smoothing. |
| Subdivision (Geometry) | **Tessellate** | Applies Subdivision Surface modifiers, so you get the mesh Blender shows. *Best Match* exports the unsubdivided cage with `subdivisionScheme = "catmullClark"`, which the importer warns about and draws as the cage. |
| Triangulate Meshes (Geometry) | off, unless a mesh has concave faces | Fan triangulation is exact for convex faces (section 11). |
| Instancing (Experimental) | **off** | Linked duplicates are then written as plain copies. On, collection instances become `instanceable` references to prims under a `class` — Chapter 19's subject; this importer would draw the hidden prototypes too. |
| Materials (Materials) | on, *USD Preview Surface* | Chapter 15 reads `UsdPreviewSurface`. |
| *Backface Culling* on every material (Material Properties ▸ Settings) | **on** | Otherwise every mesh is written `doubleSided = 1`, and culling, and so the facing test, are off for it (section 4's note). |

### What Blender writes

Reading the `.usda` version of the export (the same script with a `.usda`
path) shows every convention of this chapter in one file:

- **`upAxis = "Z"`** and **`metersPerUnit = 1`**; the conversion node turns it.
- A **`root`** Xform holding everything (Blender's *Root Prim* setting), with
  a `customData` dictionary the importer ignores.
- Each object as an **Xform** with `["xformOp:translate", "xformOp:rotateXYZ",
  "xformOp:scale"]` — *T · R · S*, rotation in degrees — and its data (mesh,
  camera, light) as a **child prim** named after the data block: `/root/Ball`
  is the transform, `/root/Ball/Sphere` the mesh. That is why every Blender
  object shows up as two nodes.
- The mirrored cone as `rotateXYZ = (180, -0, -0)` and `scale = (-1, -1, -1)`
  — a mirror written another way; its determinant is still −1.
- **Normals** as `faceVarying`, even on the smooth sphere, where neighbouring
  corners agree — the vertex merge of section 12 joins them again
  (266 points, 323 vertices: the poles and the UV seam split).
- **`primvars:st`**, `faceVarying`.
- Materials under **`/root/_materials`**, a Scope, bound with
  `rel material:binding` on the mesh and on each GeomSubset. The importer
  keeps `_materials` as an empty node; Chapter 15 reads what is in it.
- **`subdivisionScheme = "none"`** on every mesh.

The camera checks section 6 against real numbers: Blender writes its 35 mm lens
and 20.25 mm film height as `focalLength = 0.35` and
`verticalAperture = 0.2025` (USD's convention for lens values is tenths of a
scene unit); since only their ratio matters, they give 32.27°, Blender's own
vertical angle for that lens at 16:9. And `clippingRange = (0.1, 100)`.
Exported in centimetres the same camera says `focalLength = 35`,
`verticalAperture = 20.25`, and `clippingRange = (10, 10000)` under a root
scaled by 100 — and must import to the same 32.27°, 0.1 m, and 100 m.

What the import must produce, in every variant (`.usda`, `.usdc`, `.usdz`;
metres or centimetres; *Convert Orientation* on or off; *Rename UV Maps* off,
which writes `primvars:UVMap`). World positions are read with section 8's
trick — drag the node onto Root:

| Thing | Expected |
| --- | --- |
| The log | `imported 14 nodes, 4 meshes (572 triangles), 1 cameras`; the crate `2 submeshes`; the cone's sixteen-sided cap noted |
| Crate | world position (1.299, 0.5, −0.75): Blender's (1.5, 0, 0.5) under the rig's 30°, turned Y-up |
| Ball | world position (−1.5, 0.6, 0), radius 0.6; 528 triangles, 323 vertices |
| Cone | base on the ground at (0, 0, −2); front faces outward although mirrored |
| Camera | eye (0, 3, 7), looking at the crate's height through (0, −0.336, −0.942), `verticalFov` 32.27°, near 0.1, far 100 |

## Checkpoint

Part 2 is complete. In the viewer you can now see `Facing.usda`'s three cubes
and gem, `FirstStage.usda`'s tabletop, and `BlenderScene.usdc` as Blender's
camera shows it; every polygon mesh faces outward, mirrored or not. The exit
check below goes through all of it.

---

## If something goes wrong

| Symptom | Likely cause |
| --- | --- |
| `C4702: unreachable code` from `nonstd/expected.hpp`, in Release and Dist only | The `#pragma warning` pair around `UsdImport.cpp`'s TinyUSDZ includes is missing; `/external:W0` does not reach a warning from the optimizer (section 7) |
| A Blender scene is lying on its back, or seen from below | The conversion node's rotation has the wrong sign; section 2's check |
| A centimetre file is a hundred times too big, or tiny | `metersPerUnit` not applied — the file node's scale should read 0.01 |
| An imported camera looks at the sky | Its axes were converted (baked) instead of its parent turned (section 2) |
| Near-plane clipping eats a centimetre scene, or depth fights everywhere | `clippingRange` multiplied by the camera's world scale as well as `metersPerUnit` (section 6) |
| A mirrored ball or mesh is dark with a bright rim: you see its far inner faces | Winding: `leftHanded != mirrored` not applied, or the node is mirrored in the inspector after import (section 4) |
| `skipped N prim(s) of type Mesh` | Expected in Part 1; section 13 adds `GeomMesh` to `asXformable` and the dispatch |
| Every textured surface is upside down (Chapter 15) | The `1 - v` in section 12 is missing — or was added a second time somewhere else |
| A Blender mesh looks right with the front-face flip on *and* off | It is `doubleSided`; tick Backface Culling on its material and export again |
| A hand-written mesh imports with a warning about subdivision | The file does not say `uniform token subdivisionScheme = "none"` (section 11) |
| `skipped N prim(s) of type SphereLight` (or `DistantLight`, `RectLight`) | Expected until Chapter 16 |
| `skipped N prim(s) of type PointInstancer`, or an `instanceable` prim imports empty | Expected until Chapter 19; export with Instancing off |
| An imported object is missing; its prim is in Chapter 13's prim-tree log | It is a type the importer skips (the warning lists it), or `active = false` |
| A referenced asset is missing | `LoadUSDFromFile` does not compose (Chapter 13 section 11); a referencing prim arrives empty |
| Facets on a smooth Blender mesh | Exported with normals off, so the importer computed flat normals |
| A concave face draws as a wrong shape | Fan triangulation (section 11); export with Triangulate Meshes on |
| The viewer will not start, and the demo picker says `Could not load …` | The starting file is broken. Fix it and pick the demo again, or start with `--scene` naming another file |
| A file just added to `Assets/Scenes` is not in the File list | The list is read once, at the first import: restart. And the post-build step copies `Assets/` only when the project builds (Chapter 13 section 6) |
| A crash, or the wrong meshes, right after picking another file | The panel is drawn after the draw list was collected, so `Record` used the old file's list (section 10); or `Teardown` ran without `vkDeviceWaitIdle` |
| After a file switch, the inspector shows a node you never selected | `m_editor` was not reset; its selection is an index into the old scene |
| Coming back to the viewer from another demo re-imports the file and loses every edit | `Setup` imports unconditionally instead of only into an empty scene |
| Two cameras with the same name both highlight in "Look through" | The `##` and node index are missing from the label: ImGui sees one widget |
| A crash on the frame after a failed switch | `Record` reached `WriteFrameData` with `m_ready` false |

---

## Exit check

Run with validation on, and synchronization validation proven on, as in
Chapter 05.

- [ ] **The build.** Debug, Release, and Dist build with no warnings. Only
      Release and Dist test section 7's `#pragma warning` pair, because
      TinyUSDZ's `C4702` comes from the optimizer.
- [ ] **Basics.** `SandboxGame --demo USD --scene Basics.usda` logs
      `Basics.usda: imported 8 nodes, 3 meshes (984 triangles), 1 cameras.`
      Through the file's camera, the box, turned 45°, stands left of centre
      and the ball to its right, over a pale ground; the ball is lit like the
      box, not dark with a bright rim. The Camera panel reads 53°, 0.100 m,
      100 m, and position (0, 1.50, 6.00); the Scene panel shows Root ▸ Basics
      ▸ World ▸ Camera *[camera, active]*, Ground, Turntable ▸ Box, Mirror ▸
      Ball. Dragging Box onto Root leaves it where it is, and its translation
      reads (−0.849, 0.500, 0.849).
- [ ] **The same scene, Z-up in centimetres.** Pick `Basics_ZUpCm.usda`. The
      picture does not change, and neither do the Camera panel's numbers.
      Select the `Basics_ZUpCm` node: the inspector shows rotation (−90, 0, 0)
      and scale 0.01 — the whole of section 2 in one node. Now type 0 into that
      rotation's X. The view hardly moves, because the camera is inside the
      file and tips with it; but the lighting goes wrong, since the engine's
      sun still shines down +Y and the scene's up is now +Z, and the Camera
      panel's position reads (0, −6.00, 1.50) — the file's own axes, in metres
      because the scale is still there.
- [ ] **Facing.** `Facing.usda` logs `/World/RightHanded: 3 submeshes: Caps
      Sides (rest)` and `imported 8 nodes, 4 meshes (44 triangles), 1
      cameras.` Its three cubes look identical, and the gem above them is
      shaded smoothly; the inspector reads `24 vertices, 3 submesh(es)` for
      RightHanded and `10 vertices, 1 submesh(es)` for Gem. In **Normals** the
      cubes show the same colours face for face. Tick **Flip front face**: all
      four turn inside out together. A mesh that looks right only with the
      flip on has its winding backwards (section 4).
- [ ] **Blender.** `BlenderScene.usdc` (section 15) logs the cone's
      sixteen-sided cap, `/root/Rig/Crate/Cube: 2 submeshes: Blue Red`, and
      `imported 14 nodes, 4 meshes (572 triangles), 1 cameras.` The view
      matches Blender's camera view (Numpad 0): the ball on the left, the cone
      further back in the middle, the crate on the right. The Camera panel
      reads 32°, 0.100 m, 100 m, and position (0, 3.00, 7.00). Every Blender
      object is two nodes, `Ball` and its `Sphere`. With **Flip front face**
      everything turns inside out — the mirrored cone included — and the
      single-sided ground disappears; in **Normals** the cone's left flank is
      blue-green (−X) and its right flank pink (+X), as they would be on a cone
      that was never mirrored.
- [ ] **A file with no camera.** Copy `Basics.usda` to `NoCamera.usda`, delete
      its `def Camera "Camera"` block, and restart (the file list is read
      once). Picking it logs `imported 7 nodes, 3 meshes (984 triangles), 0
      cameras.` and `The file has no camera; added "Viewer camera" framing the
      whole scene.` The whole ground is in view, from above and to one side;
      `Viewer camera` is a child of Root, not of the file node; and the Camera
      panel reads 60°, 0.071 m, 710 m: the bounding sphere's radius is
      about 7.1 m.
- [ ] **A broken file.** Save a copy of any scene with one `]` deleted as
      `Broken.usda`, restart, and pick it. The log has TinyUSDZ's message with
      a line and column; the panel shows its first line in red; the previous
      scene stays, and stays editable. Picking a good file clears the message.
- [ ] **A `--scene` that names nothing.** `--scene Nope.usda` logs
      `--scene "Nope.usda" is not in …; starting on the first file.` and
      starts on `Basics.usda`.
- [ ] **A scene anywhere.** Copy `Basics.usda` into a folder outside the
      checkout and start with `--scene` and its full path: the file list ends
      with `Basics.usda` a second time, selected, and it imports exactly as the
      first does. Picking the other `Basics.usda` and back switches between
      them.
- [ ] **Edits survive a demo switch, not a file switch.** Move a node in the
      inspector, switch to *Scene graph* and back: it is still moved, and the
      log shows no second import. Pick another file and come back: the edit is
      gone, because a file pick is a fresh import.
- [ ] **Optional, the failure path.** While the viewer runs, rename
      `Shaders/Scene` beside the executable and pick another file. The log
      says the shaders are missing, the scene area clears to the background,
      and the panel reads `Creating a mesh pipeline failed.`; name the folder
      back and pick a file, and the viewer recovers. That is the `m_ready`
      branch of `Record` (section 10) — validation stays clean throughout.
- [ ] Switching files, switching demos, resizing, and closing are all
      validation-clean, and `vmaDestroyAllocator` does not assert at exit.

---

## Appendix A: `Facing.usda`

Reference for section 14: the complete file. Save it as
`Assets/Scenes/Facing.usda`.

```text
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "World"
{
    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 100)
        double3 xformOp:translate = (0, 2.5, 5)
        float xformOp:rotateX = -25
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }

    def Mesh "RightHanded"
    {
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 1, 2, 3, 5, 4, 7, 6, 1, 5, 6, 2, 4, 0, 3, 7, 3, 2, 6, 7, 4, 5, 1, 0]
        point3f[] points = [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)]
        uniform token subdivisionScheme = "none"
        double3 xformOp:translate = (-2, 0.5, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]

        uniform token subsetFamily:materialBind:familyType = "nonOverlapping"

        def GeomSubset "Caps"
        {
            uniform token elementType = "face"
            uniform token familyName = "materialBind"
            int[] indices = [4, 5]
        }

        def GeomSubset "Sides"
        {
            uniform token elementType = "face"
            uniform token familyName = "materialBind"
            int[] indices = [0, 1, 2]
        }
    }

    def Mesh "LeftHanded"
    {
        uniform token orientation = "leftHanded"
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [3, 2, 1, 0, 6, 7, 4, 5, 2, 6, 5, 1, 7, 3, 0, 4, 7, 6, 2, 3, 0, 1, 5, 4]
        point3f[] points = [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)]
        uniform token subdivisionScheme = "none"
        double3 xformOp:translate = (0, 0.5, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }

    def Xform "Mirror"
    {
        double3 xformOp:translate = (2, 0.5, 0)
        float3 xformOp:scale = (-1, 1, 1)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Mesh "Mirrored"
        {
            int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
            int[] faceVertexIndices = [0, 1, 2, 3, 5, 4, 7, 6, 1, 5, 6, 2, 4, 0, 3, 7, 3, 2, 6, 7, 4, 5, 1, 0]
            point3f[] points = [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5)]
            uniform token subdivisionScheme = "none"
        }
    }

    def Mesh "Gem"
    {
        int[] faceVertexCounts = [3, 3, 3, 3, 3, 3, 3, 3]
        int[] faceVertexIndices = [0, 3, 2, 0, 2, 5, 0, 5, 4, 0, 4, 3, 1, 2, 3, 1, 5, 2, 1, 4, 5, 1, 3, 4]
        point3f[] points = [(0, 1, 0), (0, -1, 0), (1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1)]
        normal3f[] normals = [(0, 1, 0), (0, -1, 0), (1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1)] (
            interpolation = "vertex"
        )
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (0.5, 1)] (
            interpolation = "faceVarying"
        )
        int[] primvars:st:indices = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]
        uniform token subdivisionScheme = "none"
        double3 xformOp:translate = (0, 1.8, -1.5)
        float3 xformOp:scale = (0.6, 0.6, 0.6)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }
}
```

## Appendix B: the Blender test scene's script

Reference for section 15. Paste it into Blender's *Scripting* workspace (New,
paste), set `EXPORT_PATH` to your checkout's `Assets/Scenes/BlenderScene.usdc`,
and run it. It builds the scene from an empty file and exports it with the
settings of section 15's table.

```python
# Builds chapter 14's Blender test scene and exports it as USD.
# Blender: Scripting workspace, New, paste, set EXPORT_PATH, Run Script.
import math
import bpy
from mathutils import Vector

EXPORT_PATH = "C:/PillowFort/Assets/Scenes/BlenderScene.usdc"   # change to your checkout

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1280, 720   # the camera's aperture follows this aspect

def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1.0)
    m.use_backface_culling = True          # exported as doubleSided = 0
    return m

bpy.ops.mesh.primitive_plane_add(size=10)
ground = bpy.context.object
ground.name = "Ground"
ground.data.materials.append(material("Grey", (0.5, 0.5, 0.5)))

rig = bpy.data.objects.new("Rig", None)          # an empty: a transform with no geometry
scene.collection.objects.link(rig)
rig.rotation_euler = (0, 0, math.radians(30))

bpy.ops.mesh.primitive_cube_add(size=1)
crate = bpy.context.object
crate.name = "Crate"
crate.parent = rig
crate.location = (1.5, 0, 0.5)
crate.data.materials.append(material("Red", (0.8, 0.05, 0.05)))
crate.data.materials.append(material("Blue", (0.05, 0.1, 0.8)))
for polygon in crate.data.polygons:              # top and bottom blue, sides red: two GeomSubsets
    polygon.material_index = 1 if abs(polygon.normal.z) > 0.5 else 0

bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(-1.5, 0, 0.6))
ball = bpy.context.object
ball.name = "Ball"
ball.scale = (0.6, 0.6, 0.6)
bpy.ops.object.shade_smooth()
ball.data.materials.append(material("Yellow", (0.8, 0.6, 0.05)))

bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.5, depth=1.0, location=(0, 2, 0.5))
cone = bpy.context.object
cone.name = "MirroredCone"
cone.scale = (-1, 1, 1)                          # a mirror: the importer must reverse its winding
cone.data.materials.append(material("Green", (0.1, 0.6, 0.1)))

camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("CameraData"))
camera.data.lens = 35
camera.data.clip_start, camera.data.clip_end = 0.1, 100
scene.collection.objects.link(camera)
camera.location = (0, -7, 3)
camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = camera

bpy.ops.wm.usd_export(
    filepath=EXPORT_PATH,
    selected_objects_only=False, visible_objects_only=True,
    export_animation=False,          # default-time values only
    export_meshes=True, export_cameras=True, export_lights=True,
    export_normals=True, export_uvmaps=True, rename_uvmaps=True,   # primvars:st
    export_materials=True, generate_preview_surface=True,
    export_subdivision='TESSELLATE', triangulate_meshes=False,
    use_instancing=False, convert_orientation=False,
    convert_scene_units='METERS')
```

---

Next: [15 — Materials and Textures](15-Materials-And-Textures.md)
