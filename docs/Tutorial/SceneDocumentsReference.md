# Scene Documents: Setup, Design Choices And Build Reference

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

This is a support reference for [Chapter 45](45-Scene-Documents-And-Properties.md),
not another numbered chapter. Chapter 45 teaches the binding, checked-edit,
hierarchy and publication mechanisms. Use this page when placing its code,
comparing reflection approaches or building the completed listings.
Numbered section references on this page refer to Chapter 45.

- [Property implementation layout](#cpp-layout)
- [Reflection design choices](#reflection-choices)
- [CPU environment data](#environment-data)
- [Build the listings](#build-the-listings)
- [Run the inspector](#inspector-run)
- [Run the document viewer](#viewer-run)

<a id="cpp-layout"></a>

## Property implementation layout

Return to [Chapter 45 section 2](45-Scene-Documents-And-Properties.md#ch45-property-bindings)
for the complete binding implementation, and section 3 for checked edits.

### What changes, and where

```text
Source/PillowFort/Scene/
  SceneProperties.h, .cpp       sections 1-3: bindings, typed edits and validation
  ScenePanels.h, .cpp           section 4: generated property controls
  SceneDocument.h, .cpp         sections 5-6: versioned CPU data and transactions
  Scene.h                      section 5: narrowly scoped document access
Source/PillowFort/Demos/UsdViewer/
  UsdViewerDemo.h, .cpp         section 7: save/load and safe GPU reconstruction
Tests/TutorialHarness/
  SceneDocumentTests.cpp       sections 5–6: full-format and rejection checks
premake5.lua                   private JSON include and optional CPU test target
```

Files are added, so **rerun `GenerateProjects.bat`**. Premake is the build
authority. The JSON implementation comes from the header already pinned in
TinyUSDZ; JSON types remain private to `SceneDocument.cpp`.

**Start `SceneProperties.cpp` with this file skeleton.** Paste section 2's
private helpers and tables at the first marked location, section 3's validation
helpers at the second, and its public functions after the anonymous namespace.
The comments identify insertion points; they do not stand in for undisclosed
functions:

```cpp
#include "PillowFort/Scene/SceneProperties.h"

#include <array>
#include <cmath>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace {
using namespace pf::scene;

// Section 2: PropertyBinding through findProperty, in the listed order.
// Section 3: finite helpers, validation overloads and requireIndex.
} // namespace

namespace pf::scene {
// Section 3: SceneProperties, ValidateSceneProperties, ReadSceneProperty,
// and WriteSceneProperty, in the listed order.
} // namespace pf::scene
```

There is no global registration constructor. `constexpr` constructs the tables
and allows compile-time checks of their keys and declared types. Looking up a
key, reading or writing a value, and validating an edited owner all happen at
runtime. Uniform callbacks erase the individual member path, while each
`PropertyBinding<Owner>` still takes that specific owner type.


<a id="reflection-choices"></a>

## Reflection design choices

Return to [Chapter 45 section 1](45-Scene-Documents-And-Properties.md#1-choose-what-reflection-means-here)
for the public interface. The choice here concerns how that interface obtains
its selected native fields.

There are several reasonable ways to build that bridge. Judge them against
this engine's size and learning goal:

| Approach | What it buys | Work it introduces here |
| --- | --- | --- |
| A handwritten widget and field switch for every consumer | A direct first implementation | Each new consumer duplicates field knowledge; separate descriptor and access lists can drift |
| One explicit typed binding table per owner | One registration supplies field access and its descriptor type | New component types still need registration, validation and commit behavior |
| X-macro or declaration macro | Can generate the same typed bindings with less repeated syntax | Still needs an explicit field selection and engine-specific invariants; macro expansion adds another representation to debug |
| Generated bindings from annotated source | Can reduce registration work across many types | A generator, its input rules and build dependencies must become part of this project |
| A general runtime object/type registry | Can support arbitrary tools, references and plugins | Ownership, identity, lifetime and mutation rules still need an engine-specific design |

We use the explicit typed binding table. It keeps the C++20 build and makes the important mechanism
visible. It is a foundation for selected scene properties, not discovery of
every C++ object or a plugin component system. `std::variant` deliberately
limits which value types the interface accepts.

Keeping descriptor arrays and field visitors separately makes assignments
type-safe but still allows one list to say `Float` while the other visits a
vector. We remove that duplication: **register the actual
member once and derive its descriptor type from that member**. Validation
remains explicit, because `nearPlane` and `farPlane` have a relationship that
the word `Float` cannot express.

Language choice and reflection mechanism are separate decisions. Python's
[`inspect`](https://docs.python.org/3/library/inspect.html) describes Python
objects; a native C++ object still needs exposure such as pybind11's explicit
[attribute/property bindings](https://pybind11.readthedocs.io/en/stable/classes.html).
[.NET reflection](https://learn.microsoft.com/en-us/dotnet/fundamentals/reflection/overview)
describes managed type metadata. Embedding either runtime would not, by itself,
register this engine's native fields or define their mutation rules.

A **build-time generator** written in Python or C# is a different option: it
can consume annotated C++ or a schema and emit native bindings, leaving no
language runtime in the application. Clang's
[tooling interfaces](https://clang.llvm.org/docs/Tooling.html) provide ways to
work with C++ declarations; [.NET ClangSharp](https://github.com/dotnet/ClangSharp)
also includes a C# binding generator. These are examples of generation tools,
not a requirement to embed their implementation language in the engine. Macros and generation can also compose; Qt's
[`moc`](https://doc.qt.io/qt-6/moc.html) is one concrete example. A generator here
would be a new source-processing step, separate from the removed Python build
orchestration layer. We would judge that step on its own costs.

For this implementation's 31 properties across four owner types, one native
binding table per type keeps the interface small and the build direct. If
registration expands across many components and consumers, generating those
same bindings becomes a reasonable next step. The consumer API need not
change when the producer of the tables changes.


<a id="environment-data"></a>

## CPU environment data

Use this bridge before compiling the bounded hierarchy checkpoint and later
the full document format in
[Chapter 45 section 5](45-Scene-Documents-And-Properties.md#ch45-document-round-trip).


The assembled format retains dome-light images. That CPU data model is normally
introduced in [Chapter 23 section 10](23-The-Sky.md#10-the-usd-viewer-a-domes-image-and-the-deferred-path),
so a reader arriving directly from 01-19 needs the following bounded bridge.
It does not require sky shaders, compute baking, deferred rendering or IBL.
If these declarations already exist, use them once rather than adding copies.

**In `Light.h`, add `<string>` and `<vector>` and put these declarations before
`Light`, inside `namespace pf::scene`:**

```cpp
struct EnvironmentImage
{
    std::string name;
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<float> pixels;   // linear RGBA, width * height * 4, top row first
};
inline constexpr uint32_t NO_ENVIRONMENT = UINT32_MAX;
```

**In `Light`, retain Chapter 16's `domeTextureAverage` and add `environment`
after it, before `range`:**

```cpp
glm::vec3 domeTextureAverage{ 1.0f };
uint32_t environment = NO_ENVIRONMENT;
```

The white average preserves a dome light without an image; `NO_ENVIRONMENT`
records that absence. Chapter 16 already uses the average for ambient light.
The document retains both the average and any decoded image, independently of
whether this viewer currently renders a sky from it.

**In `Scene.h`, add these public accessors and private storage:**

```cpp
uint32_t AddEnvironment(EnvironmentImage image);
const EnvironmentImage& GetEnvironment(uint32_t environment) const;
```

```cpp
std::vector<EnvironmentImage> m_environments;
```

**In `Scene.cpp`, inside `namespace pf::scene`, after texture accessors:**

```cpp
uint32_t Scene::AddEnvironment(EnvironmentImage image)
{
    m_environments.push_back(std::move(image));
    return static_cast<uint32_t>(m_environments.size() - 1);
}

const EnvironmentImage& Scene::GetEnvironment(uint32_t environment) const
{
    return m_environments.at(environment);
}
```

`Scene.cpp` already uses `<utility>` for moved arrays. A small CPU check is to
add a 1-by-1 image with four floats and read those same floats through the
returned index. The final document suite checks this bridge in its embedded
environment fixture. Rendering that image as a sky remains Chapter 23's work.


<a id="build-the-listings"></a>

## Build the listings

The [CPU checkpoint runner](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
provides sealed Starter/Solution exports for `ch45-bindings`, `ch45-hierarchy`
and `ch45-documents`. The instructions below instead assemble the chapter's
complete listings in the working repository. Run each stage when its sources
are complete; an early property check does not require the document code.

| Completed source | Target | Build stage |
| --- | --- | --- |
| `Chapter45Bindings.cpp` from section 2 | `TutorialChapter45Bindings` | [One typed binding](#binding-build) |
| `Chapter45Edits.cpp` below, with sections 1-3 implemented | `TutorialChapter45Edits` | [Checked scene edits](#checked-edit-build) |
| `Chapter45Hierarchy.cpp` from section 5 | `TutorialChapter45Hierarchy` | [Bounded hierarchy](#hierarchy-build) |
| `Chapter45Checks.cpp` from sections 3 and 5 | `TutorialChapter45Checks` | [Complete documents](#document-build) |

### Register only completed fixture sources

The 01–19 route has not introduced optional test projects. In `premake5.lua`,
add this option after the workspace settings and before the shared settings
functions. If the option already exists, keep its one declaration:

```lua
newoption { trigger = "tutorial-tests", description = "Generate focused tutorial regression targets" }
```

Put the following conditional and project-generation loop at the end of that
same file, after `apply_common_cpp_settings` is defined and after the existing
vendor, engine and SandboxGame project definitions. This keeps the local
settings function in scope and prevents the new settings from being added to
the preceding project. If `if _OPTIONS["tutorial-tests"] then` already exists,
insert only the loop inside it; do not add a second wrapper or duplicate targets.

**The list below shows the final four rows. Initially retain only the
`TutorialChapter45Bindings` row.** Add the
`TutorialChapter45Edits` row after creating its source and completing section 3;
add the hierarchy and complete-document rows only when their sources exist
and their implementations are complete. Keep the loop body unchanged. This
avoids generating projects for fixtures you have not written yet.

```lua
if _OPTIONS["tutorial-tests"] then
    for _, checkpoint in ipairs {
        { name = "TutorialChapter45Bindings", source = "Chapter45Bindings.cpp" },
        { name = "TutorialChapter45Edits", source = "Chapter45Edits.cpp", properties = true },
        { name = "TutorialChapter45Hierarchy", source = "Chapter45Hierarchy.cpp", properties = true },
        { name = "TutorialChapter45Checks", source = "Chapter45Checks.cpp", properties = true, documents = true }
    } do
        project(checkpoint.name)
            kind "ConsoleApp"
            apply_common_cpp_settings()
            files { "Tests/TutorialHarness/" .. checkpoint.source }
            externalincludedirs { "Vendor/TinyUSDZ/src" }
            externalwarnings "Off"
            removelinks { "vulkan-1" }
            if checkpoint.properties then
                files {
                    "Source/PillowFort/Scene/SceneProperties.cpp",
                    "Source/PillowFort/Scene/Scene.cpp",
                    "Source/PillowFort/Scene/Bounds.cpp",
                    "Source/PillowFort/Scene/Transform.cpp",
                    "Source/PillowFort/Scene/Camera.cpp",
                    "Source/PillowFort/Scene/Light.cpp"
                }
            end
            if checkpoint.documents then
                files { "Source/PillowFort/Scene/SceneDocument.cpp" }
            end
    end
end
```

The binding target contains section 2's private kernel and does not link the
public implementation. The checked-edit target links scene storage and
`SceneProperties.cpp`, with no document implementation or JSON dependency.
The hierarchy target adds its bounded codec and deliberately omits production
`SceneDocument.cpp`; its private-access owner is the bounded one. The final
checks target links the complete production codec and supplies only its
public-API test fixtures. These boundaries prevent duplicate definitions.

### Common generation and build settings

Use PowerShell 7 from the repository root **after registering the completed
sources for your current stage**. The supplied
[NativeGuard.ps1](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/NativeGuard.ps1) provides
`Invoke-CheckpointNative`. If an independently assembled learning tree lacks
that file, copy it unchanged from this reference to
`Tests/TutorialHarness/Checkpoints/NativeGuard.ps1` before this setup. Reuse an
existing copy. This support script does not require a sealed checkpoint export.

The guard requires 4100 MiB available before launch, monitors a 3072 MiB floor,
and refuses to overlap a native build, test or SandboxGame preview. Its timeout
is 900 seconds, and it records stdout, stderr and a `.run.json` result for each
owned process. A memory or overlap failure stops the recipe; inspect the
diagnostic and retry when the resource constraint is resolved. The MSBuild
arguments below use one worker and disable reusable build nodes so they do not
remain active for the next guarded phase.

```powershell
$chapterRoot = (Get-Location).Path
$chapterLogs = Join-Path $chapterRoot ("Build/Chapter45Logs/" + (Get-Date -Format "yyyyMMdd-HHmmss-fff"))
New-Item -ItemType Directory -Path $chapterLogs -Force | Out-Null
. (Join-Path $chapterRoot "Tests/TutorialHarness/Checkpoints/NativeGuard.ps1")

function Invoke-Chapter45Native([string]$Name, [string]$Executable, [string[]]$Arguments = @())
{
    if (![IO.Path]::IsPathRooted($Executable)) { $Executable = Join-Path $chapterRoot $Executable }
    $log = Join-Path $chapterLogs "$Name.log"
    $result = Invoke-CheckpointNative $Executable $Arguments $chapterRoot $log
    Get-Content -LiteralPath $log
    Get-Content -LiteralPath "$log.stderr"
    if ($result -ne 0) { throw "Chapter 45 phase '$Name' failed with exit code $result. Inspect $log." }
}

$chapterMsbuild = "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
$chapterBuildArgs = @(
    "/m:1", "/nr:false", "/p:CL_MPCount=1", "/p:UseMultiToolTask=true",
    "/p:MultiProcMaxCount=1", "/p:EnforceProcessCountAcrossBuilds=true",
    "/p:Configuration=Debug", "/p:Platform=x64"
)
Invoke-Chapter45Native generate .\Vendor\premake5\premake5.exe @("vs2022", "--tutorial-tests")
```

The last line invokes the same Premake generation as
`GenerateProjects.bat --tutorial-tests`, through the guard. Rerun that line
after adding a fixture or implementation file; Premake remains the build
authority. The commands below use this helper and build only their named target.
Stop at a failed command before running the next one. CPU stages establish
data/state behavior; the inspector and document viewer have separate attended
launch commands below. The setup and CPU stages launch no graphics application.

<a id="binding-build"></a>

### Build one typed binding

Complete section 2's `Chapter45Bindings.cpp`, retain its one Premake row and
run the common setup above. No checked-edit, hierarchy or document fixture is
needed for this stage.

```powershell
Invoke-Chapter45Native binding-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:TutorialChapter45Bindings") + $chapterBuildArgs)
Invoke-Chapter45Native binding-run .\Build\Artifacts\Debug\TutorialChapter45Bindings\TutorialChapter45Bindings.exe
```

Expect exit zero and `Camera binding checkpoint passed.` Then return to
[section 3](45-Scene-Documents-And-Properties.md#ch45-typed-properties).

<a id="checked-edit-build"></a>

### Build checked scene edits without document code

Create `Tests/TutorialHarness/Chapter45Edits.cpp` with this complete fixture,
also shown in [section 3](45-Scene-Documents-And-Properties.md#ch45-typed-properties).
It checks the public property API, descendant transforms and rejected edits:

```cpp
#include "PillowFort/Scene/SceneProperties.h"
#include "PillowFort/Scene/Scene.h"

#include <stdexcept>
#include <string>
#include <variant>

void CheckTypedSceneEdit()
{
    using namespace pf::scene;
    const auto require = [](bool value, const std::string& message)
    {
        if (!value) { throw std::runtime_error(message); }
    };

    Scene scene;
    const NodeIndex parent = scene.AddNode("Parent");
    const NodeIndex child = scene.AddNode("Child", parent,
        Transform{ .translation = { 0.0f, 1.0f, 0.0f } });
    scene.UpdateWorldTransforms();

    std::string error;
    const glm::vec3 expected(3.0f, 4.0f, 5.0f);
    require(WriteSceneProperty(scene, PropertyTarget::Node, parent,
        "translation", PropertyValue{ expected }, error), error);
    scene.UpdateWorldTransforms();
    require(glm::length(glm::vec3(scene.GetNode(child).world[3])
        - (expected + glm::vec3(0.0f, 1.0f, 0.0f))) < 1e-5f,
        "typed edit did not dirty the world transform");

    require(!WriteSceneProperty(scene, PropertyTarget::Node, parent,
        "translation", PropertyValue{ std::string("three") }, error),
        "wrong property type was accepted");
    require(!WriteSceneProperty(scene, PropertyTarget::Node, parent,
        "missing", PropertyValue{ 1.0f }, error), "unknown key was accepted");
    require(!WriteSceneProperty(scene, PropertyTarget::Node,
        static_cast<uint32_t>(scene.NodeCount()), "visible", PropertyValue{ false }, error),
        "out-of-range target was accepted");
    const glm::vec3 previousScale = scene.GetNode(parent).local.scale;
    require(!WriteSceneProperty(scene, PropertyTarget::Node, parent,
        "scale", PropertyValue{ glm::vec3(0.0f) }, error), "zero scale was accepted");
    require(scene.GetNode(parent).local.scale == previousScale, "rejected scale changed state");

    const uint32_t camera = scene.AddCamera(Camera{});
    const Camera previousCamera = scene.GetCamera(camera);
    require(!WriteSceneProperty(scene, PropertyTarget::Camera, camera,
        "farPlane", PropertyValue{ previousCamera.nearPlane * 0.5f }, error),
        "far plane inside the near plane was accepted");
    require(scene.GetCamera(camera).nearPlane == previousCamera.nearPlane
        && scene.GetCamera(camera).farPlane == previousCamera.farPlane,
        "rejected coupled camera edit changed state");
    PropertyValue actual;
    require(ReadSceneProperty(scene, PropertyTarget::Node, parent,
        "translation", actual, error), error);
    require(std::holds_alternative<glm::vec3>(actual), "wrong read type");
    require(glm::length(std::get<glm::vec3>(actual) - expected) < 1e-5f,
        "rejected edit changed the property");
}
```

Append this complete entry point to the same file:

```cpp
#include <iostream>

int main()
{
    try
    {
        CheckTypedSceneEdit();
        std::cout << "Checked scene edit checkpoint passed.\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
```

Complete sections 1-3's `SceneProperties.h` and `.cpp`, then add only the
`TutorialChapter45Edits` row to the rows already completed. Rerun the common
generation/setup recipe and run:

```powershell
Invoke-Chapter45Native edit-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:TutorialChapter45Edits") + $chapterBuildArgs)
Invoke-Chapter45Native edit-run .\Build\Artifacts\Debug\TutorialChapter45Edits\TutorialChapter45Edits.exe
```

Expect exit zero and `Checked scene edit checkpoint passed.` This stage
requires neither `SceneDocument.cpp` nor the section 5 round-trip fixture.
Continue with [section 4's inspector](45-Scene-Documents-And-Properties.md#ch45-generated-inspector).

<a id="inspector-run"></a>

### Run the property inspector before adding documents

After the binding and checked-edit CPU checks pass, complete section 4's
inspector integration. Keep `SceneEditorState::editMaterials` at its default
`false`: the material Apply boundary belongs to Part 3. Build SandboxGame using
the common guarded helper:

```powershell
Invoke-Chapter45Native inspector-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:SandboxGame") + $chapterBuildArgs)
```

Then, while attending the machine, run this separate viewer command. The same
4100/3072 MiB and no-overlap guard applies. Finish the UI checkpoint and close
the viewer before the guard's 900-second timeout; an already open preview
blocks this launch and remains its user's process to close.

```powershell
Invoke-Chapter45Native inspector-viewer .\Build\Artifacts\Debug\SandboxGame\SandboxGame.exe @("--demo", "USD viewer", "--scene", "Assets/Scenes/CornellBox.usda")
```

Use [section 4's UI checkpoint](45-Scene-Documents-And-Properties.md#ch45-generated-inspector)
to check node/camera/light edits, validation errors and widget identity. Keep
builds and GPU checks serial with the repository's memory guards. Full material
Apply and document reopening are deferred until Part 3's activation boundary;
this inspector stage needs no `.pfscene` file or document implementation.

<a id="hierarchy-build"></a>

### Build the bounded hierarchy codec

Create section 5's complete `Chapter45Hierarchy.cpp` after adding the CPU
environment-data bridge it uses. Add its Premake row and rerun the common
setup; keep any still-unwritten document fixture out of the row list.

```powershell
Invoke-Chapter45Native hierarchy-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:TutorialChapter45Hierarchy") + $chapterBuildArgs)
Invoke-Chapter45Native hierarchy-run .\Build\Artifacts\Debug\TutorialChapter45Hierarchy\TutorialChapter45Hierarchy.exe
```

Expect exit zero and `Hierarchy codec checkpoint passed: world position
(2,1,0).` This bounded in-memory projection is not a complete `.pfscene` file.
Return to [section 5](45-Scene-Documents-And-Properties.md#ch45-document-round-trip)
to assemble the full format before running the next stage.

<a id="document-build"></a>

### Build the complete document checks

After assembling the full document implementation from sections 5-6, create
`Tests/TutorialHarness/Chapter45Checks.cpp`. Put the two complete fixture
functions `CheckTypedSceneEdit` and `CheckSceneDocumentRoundTrip` from sections
3 and 5 before this driver, and include `<iostream>` above them:

```cpp
int main(int argc, char** argv)
{
    try
    {
        const std::filesystem::path output = argc > 1 ? std::filesystem::path(argv[1])
            : std::filesystem::current_path() / "Build" / "Chapter45Checks";
        std::filesystem::create_directories(output);
        CheckTypedSceneEdit();
        CheckSceneDocumentRoundTrip(output / "RoundTrip.pfscene");
        std::cout << "Checked scene edits and document round trip passed.\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
```

Add the `TutorialChapter45Checks` row. The broader production suite is supplied
in [SceneDocumentTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/SceneDocumentTests.cpp).
If it is absent from your learning tree, copy that complete source unchanged
to `Tests/TutorialHarness/SceneDocumentTests.cpp`. It is a second test driver,
so give it its own executable instead of adding it to `Chapter45Checks.cpp`.

**At this full-format stage**, add the following target inside the same
`if _OPTIONS["tutorial-tests"] then` block, after the four-target loop and before
the conditional's closing `end`. Reuse the target if it already exists. These
are all of its CPU implementation dependencies; it does not link the engine
library, importer or renderer:

```lua
project "TutorialSceneDocumentTests"
    kind "ConsoleApp"
    apply_common_cpp_settings()
    files {
        "Tests/TutorialHarness/SceneDocumentTests.cpp",
        "Source/PillowFort/Scene/SceneDocument.cpp",
        "Source/PillowFort/Scene/SceneProperties.cpp",
        "Source/PillowFort/Scene/Scene.cpp",
        "Source/PillowFort/Scene/Bounds.cpp",
        "Source/PillowFort/Scene/Transform.cpp",
        "Source/PillowFort/Scene/Camera.cpp",
        "Source/PillowFort/Scene/Light.cpp"
    }
    externalincludedirs { "Vendor/TinyUSDZ/src" }
    externalwarnings "Off"
    removelinks { "vulkan-1" }
```

Rerun the common guarded generation command, then build and run both CPU suites
serially:

```powershell
Invoke-Chapter45Native document-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:TutorialChapter45Checks") + $chapterBuildArgs)
Invoke-Chapter45Native document-run .\Build\Artifacts\Debug\TutorialChapter45Checks\TutorialChapter45Checks.exe @(".\Build\Chapter45Checks")
Invoke-Chapter45Native production-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:TutorialSceneDocumentTests") + $chapterBuildArgs)
Invoke-Chapter45Native production-run .\Build\Artifacts\Debug\TutorialSceneDocumentTests\TutorialSceneDocumentTests.exe @(".\Build\Chapter45ProductionTests")
```

Expect exit zero and `Checked scene edits and document round trip passed.`
The production suite additionally covers full material/image round
trips and malformed inputs. Its retained `RoundTrip.pfscene` can be used for
the viewer check. Return to [section 6](45-Scene-Documents-And-Properties.md#ch45-transactional-load)
for the load/save failure contract and its rejection checks.

<a id="viewer-run"></a>

## Run the document viewer

Complete the full document CPU stage above and Part 3's activation
implementation first. The commands use the common setup's guarded helper,
`$chapterMsbuild` and `$chapterBuildArgs`. Return to
[section 7](45-Scene-Documents-And-Properties.md#ch45-gpu-activation)
for the activation implementation and attended viewer checkpoint.

Build SandboxGame only after the CPU checks:

```powershell
Invoke-Chapter45Native viewer-build $chapterMsbuild (@(".\Build\Projects\PillowFort.sln", "/t:SandboxGame") + $chapterBuildArgs)
```

Run this separate command only for the attended viewer checkpoint, with no
other GPU test, build or preview in progress. The common guard enforces the
4100 MiB launch gate and 3072 MiB runtime floor. Complete the check and close
the viewer within its 900-second bounded session:

```powershell
Invoke-Chapter45Native document-viewer .\Build\Artifacts\Debug\SandboxGame\SandboxGame.exe @("--demo", "USD viewer", "--scene", ".\Build\Chapter45Checks\RoundTrip.pfscene")
```

The retained CPU fixture has camera/light nodes but no mesh. It proves that an
empty authored hierarchy can reopen. For visible material edits, open
`Assets/Scenes/CornellBox.usda`, save a document and follow section 7's workflow.
Record the configuration, document and actual result. Publishing this chapter
is not a claim that its intermediate sources or a particular GPU were tested;
the reference evidence records checks that actually ran.
