# 45 — Scene Documents And Typed Properties

**Goal:** describe the scene's editable properties, use the same checked edits
from tools and ImGui, and reopen those edits from an engine-owned document.

**Module:** `Scene` owns properties, validation and CPU documents. `ScenePanels`
presents them; the USD viewer owns GPU reconstruction after a load.

**ROADMAP:** step 21+ — the scene viewer gains saved documents.

Chapter 12's inspector knows each field and when to call `EditLocal`. A console
or another inspector would have to repeat that knowledge. We give tools three
operations: enumerate properties, read a typed value, and submit a checked edit.
The binding machinery stays private in `SceneProperties.cpp`.

For a selected node, the everyday edit looks like this:

```cpp
std::string error;
const bool accepted = WriteSceneProperty(scene, PropertyTarget::Node, selected,
    "translation", PropertyValue{ glm::vec3(2.0f, 0.0f, 0.0f) }, error);
```

`true` means accepted, including a successful no-op. Section 1 declares the
types; section 3 implements validation and commit.

**Prerequisites:** take this detour after Chapter 19. These are the earlier
sections the implementation uses:

| Earlier sections | What we use |
| --- | --- |
| Chapter 12, sections [3](12-Scene-Graph.md#3-the-class-map), [4](12-Scene-Graph.md#4-world-transforms-top-down) and [9](12-Scene-Graph.md#9-editing-it-live) | Indexed scene access, `EditLocal`, dirty propagation and the inspector |
| Chapter 14, sections [9](14-Importing-USD-Scenes.md#9-the-usd-viewer)–[10](14-Importing-USD-Scenes.md#10-switching-files-while-it-runs) | CPU import and the viewer's scene-switching boundary |
| Chapter 15, sections [3](15-Materials-And-Textures.md#3-materials-as-plain-data) and [5](15-Materials-And-Textures.md#5-textures-on-the-gpu)–[7](15-Materials-And-Textures.md#7-set-1-one-descriptor-set-per-material) | CPU materials/images and their separately owned GPU resources |
| Chapter 16, sections [2](16-Lights.md#2-light-units-and-lights-as-scene-data), [4](16-Lights.md#4-the-light-buffer) and [7](16-Lights.md#7-editing-lights) | Light components, uploads and specialized controls |
| Chapter 9, sections [2](09-Demo-Harness.md#2-the-demo-interface), [5](09-Demo-Harness.md#5-the-renderers-side) and [9](09-Demo-Harness.md#9-what-runs-when) | Demo lifetime, frame fences, `Update` and `Record` |

The document code also uses Chapter 23's CPU environment-image declarations.
The [bounded setup bridge](SceneDocumentsReference.md#environment-data) supplies
them before you compile the hierarchy checkpoint in section 5.

### Three Parts, Three Stopping Points

| Part | Observable result | Check |
| --- | --- | --- |
| 1: properties, sections 1–4 | One binding, checked scene edits, then an inspector | CPU binding/edit checks; UI separately |
| 2: documents, sections 5–6 | Hierarchy round trip, then validated load and atomic save | CPU hierarchy/document checks |
| 3: viewer, sections 7–8 | Load or apply edits while respecting GPU resource lifetime | Attended viewer check after the CPU checks |

Work through one part at a time. Each attempt has three hints and a complete
answer. Keep them closed until needed. The [CPU checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
provides `ch45-bindings`, `ch45-hierarchy` and `ch45-documents` Starter/Solution
pairs with protected oracles. Those are selected current-reference exercises;
the manual listings are a separate assembly path.

### What Changes, And Where

```text
Source/PillowFort/Scene/
  SceneProperties.h, .cpp       sections 1–3: bindings, checked edits and validation
  ScenePanels.h, .cpp           section 4: generated controls
  SceneDocument.h, .cpp         sections 5–6: CPU format and transactions
  Scene.h                      section 5: private document access
Source/PillowFort/Demos/UsdViewer/
  UsdViewerDemo.h, .cpp         section 7: save/load and GPU reconstruction
```

The [setup and build reference](SceneDocumentsReference.md#cpp-layout) gives
the exact file skeleton, includes and test targets. Rerun `GenerateProjects.bat`
after adding files; Premake remains the build authority.

# Part 1 — Properties that tools can discover

## 1. Choose What Reflection Means Here

Here reflection means discovering selected authored properties and reading or
changing them through a checked interface. We select that list explicitly:
local translation is editable; a cached world matrix is rebuilt from it.

**This is the interface in `SceneProperties.h`, inside `namespace pf::scene`.**
Include `Scene.h`, `<span>`, `<string>`, `<string_view>` and `<variant>`:

```cpp
enum class PropertyTarget { Node, Camera, Light, Material };
enum class PropertyType { Boolean, Float, String, Vec3, Quaternion, Vec4 };
using PropertyValue = std::variant<bool, float, std::string,
                                  glm::vec3, glm::quat, glm::vec4>;

struct PropertyDescriptor
{
    std::string_view key;
    std::string_view label;
    PropertyType type;
};

std::span<const PropertyDescriptor> SceneProperties(PropertyTarget target);
bool ReadSceneProperty(const Scene& scene, PropertyTarget target,
                       uint32_t index, std::string_view key,
                       PropertyValue& value, std::string& error);
bool WriteSceneProperty(Scene& scene, PropertyTarget target,
                        uint32_t index, std::string_view key,
                        const PropertyValue& value, std::string& error);
bool ValidateSceneProperties(const Scene& scene, std::string& error);
```

`target` chooses an owner array and `index` selects its element. A node's camera
index selects a `Camera`; it is not the node index again. The stable `key` is
for tools, while `label` is display text. Renaming “Near plane” should preserve
a command that uses `nearPlane`.

> **Jump:** `std::variant` holds one of its listed C++ types. A returned
> `glm::vec3` stays a vector. `std::get_if<glm::vec3>(&value)` gives a pointer
> only for that active alternative, connecting runtime selection to a checked
> C++ assignment.

We use one typed binding table per owner. Registering the actual member once
derives its descriptor type and accessors, so separate metadata and access lists
cannot disagree. Validation stays explicit: two `float` clip planes still have
to satisfy `0 < near < far`.

For 31 properties on four owner types, this keeps the C++20 build direct.
The [design comparison](SceneDocumentsReference.md#reflection-choices) covers
macros, Python/C# runtimes and native code generation. A later generator could
produce these same tables without changing the consumer interface.

## 2. Bind A Name To A Real Member

Put the binding helpers and tables in `SceneProperties.cpp`'s anonymous
namespace; public functions belong in `namespace pf::scene` after it. The
[file skeleton](SceneDocumentsReference.md#cpp-layout) fixes their order and
includes before you start.

A raw byte offset would ask every consumer to cast memory correctly. A typed
pointer-to-member already tells the compiler both its owner and its field
type. We use one for `Camera::nearPlane` and a path of two for
`Node::local` followed by `Transform::translation`.

> **Jump:** `&Camera::nearPlane` is a pointer-to-member: it identifies the
> `nearPlane` field of a `Camera`, not one particular camera's address. If
> `member` holds that pointer and `camera` is an object, `camera.*member` means
> that object's selected field. `&camera.nearPlane` would instead point at one
> existing object's storage. Keeping the owner and member types lets C++ check
> that we never apply a camera member to a light.

The template syntax has a small set of jobs:

- `auto Member` is a **non-type template parameter**: the compile-time argument
  is the member pointer itself, rather than a type. `Nested` optionally selects
  the second field in `Node::local`.
- `decltype(auto)` preserves the field reference from `propertyField`, including
  constness. Returning a plain `auto` would copy the field; assigning it would
  no longer edit the candidate.
- `std::declval<Owner&>()` is used only inside `decltype`. It asks what type that
  expression would have without constructing an owner or evaluating access.
  `remove_cvref_t` gives the value type used by the variant.
- A captureless lambda can convert to the ordinary function-pointer type stored
  in the binding. Its template instantiation already knows `Member` and `Type`,
  so there is no captured state or allocation.
- `unsupportedProperty<Type>` makes the failing `static_assert` depend on the
  template argument. An unsupported field type diagnoses the bad instantiation;
  supported alternatives do not take that branch.

For a concrete trace, select `&Camera::nearPlane`. The compiler knows the
owner is `Camera` and the field is `float`: applying that member gives a
`float&`, and removing the reference gives the variant alternative `float`.
The binding can therefore report `PropertyType::Float` and supply checked
reader/writer functions. At runtime the key selects that binding, then its
callback reads or writes the particular camera passed to it. The callback
signature is uniform; its generated code still knows the selected member.

<a id="ch45-property-bindings"></a>

### Attempt CH45-property-bindings: register the field once

Build a binding for a camera's near plane and a node's nested translation.
Make its descriptor type, reader and writer come from the selected member.
Then enumerate the node's name, visibility, translation, rotation and scale
without writing a separate type list or key switch.

**Acceptance:** Each key occurs once per owner. The returned variant agrees
with the descriptor type for every registered field. A wrong value type is
rejected before assigning. Renaming a display label does not change lookup.
A supported member-type change derives the new descriptor type; an unsupported
member type fails compilation instead of obtaining a guessed cast.

**Transfer:** Register `Material::roughness` using the same binding helper.
Explain why this removes an access-list edit but does not define a valid
roughness range, an undo command or a document-version migration.

**Run before opening the answer:** use `ch45-bindings` from the
[checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md). It checks
the actual camera member, inferred type and wrong-type rejection. An untouched
Starter uses `Check -ExpectIncomplete`; after repairing its declared omission,
use `Check` without that flag. For your own listing, the
[binding recipe](SceneDocumentsReference.md#binding-build) gives the test
fixture, so you need not open the answer first; the built test must print
`Camera binding checkpoint passed.` and exit zero.

<details>
<summary>Hint 1: retain the member type until the last boundary</summary>

An `auto` non-type template parameter can hold `&Camera::nearPlane` without
turning it into an integer offset. Apply the member to an owner, then inspect
the resulting reference type with `std::remove_cvref_t`.

</details>

<details>
<summary>Hint 2: give readers and writers one call signature</summary>

Every binding for one owner can expose the same reader/writer function-pointer
signatures. Instantiate those functions while the concrete member type is
still known; the writer uses `std::get_if<Field>`.

</details>

<details>
<summary>Hint 3: nested members are a path</summary>

Apply the first member pointer to the current object, then apply the next to
that result. Return with `decltype(auto)` so the last field remains a reference,
including constness when the owner is const.

</details>

<details>
<summary>Worked solution: derive access and metadata from one binding table</summary>

**These are file-scope helpers in `SceneProperties.cpp`, inside its anonymous
namespace, above the property tables.** The implementation needs `<array>`,
`<type_traits>` and `<utility>` in addition to the public header.
The binding stores a descriptor plus ordinary function pointers. Each function
pointer points at an instantiation whose member type the compiler checked.

```cpp
template<typename Owner>
struct PropertyBinding
{
    PropertyDescriptor descriptor;
    PropertyValue (*read)(const Owner&);
    bool (*write)(Owner&, const PropertyValue&, std::string& error);
};

template<typename> inline constexpr bool unsupportedProperty = false;

template<typename Type>
constexpr PropertyType propertyType()
{
    if constexpr (std::is_same_v<Type, bool>) { return PropertyType::Boolean; }
    else if constexpr (std::is_same_v<Type, float>) { return PropertyType::Float; }
    else if constexpr (std::is_same_v<Type, std::string>) { return PropertyType::String; }
    else if constexpr (std::is_same_v<Type, glm::vec3>) { return PropertyType::Vec3; }
    else if constexpr (std::is_same_v<Type, glm::quat>) { return PropertyType::Quaternion; }
    else if constexpr (std::is_same_v<Type, glm::vec4>) { return PropertyType::Vec4; }
    else { static_assert(unsupportedProperty<Type>, "Unsupported scene property type."); }
}

// A pointer-to-member is checked by C++; it is not a byte offset. The optional
// second member reaches Node::local's TRS fields and preserves const access.
template<auto Member, auto Nested = nullptr, typename Owner>
decltype(auto) propertyField(Owner& owner)
{
    if constexpr (std::is_same_v<decltype(Nested), std::nullptr_t>) { return (owner.*Member); }
    else { return ((owner.*Member).*Nested); }
}

template<typename Owner, auto Member, auto Nested = nullptr>
constexpr PropertyBinding<Owner> makeProperty(std::string_view key, std::string_view label)
{
    using Type = std::remove_cvref_t<decltype(propertyField<Member, Nested>(std::declval<Owner&>()))>;
    return {
        { key, label, propertyType<Type>() },
        [](const Owner& owner) -> PropertyValue { return propertyField<Member, Nested>(owner); },
        [](Owner& owner, const PropertyValue& value, std::string& error) {
            const auto* typed = std::get_if<Type>(&value);
            if (typed == nullptr)
            {
                error = "Scene property value has the wrong type.";
                return false;
            }
            propertyField<Member, Nested>(owner) = *typed;
            return true;
        }
    };
}

// Each editable field is declared once. Keys remain explicit so renaming a C++
// member need not rename a property used by editor commands or a document.
constexpr std::array nodeBindings = {
    makeProperty<Node, &Node::name>("name", "Name"),
    makeProperty<Node, &Node::visible>("visible", "Visible"),
    makeProperty<Node, &Node::local, &Transform::translation>("translation", "Translation"),
    makeProperty<Node, &Node::local, &Transform::rotation>("rotation", "Rotation (quaternion)"),
    makeProperty<Node, &Node::local, &Transform::scale>("scale", "Scale"),
};
constexpr std::array cameraBindings = {
    makeProperty<Camera, &Camera::verticalFov>("verticalFov", "Vertical FOV (radians)"),
    makeProperty<Camera, &Camera::nearPlane>("nearPlane", "Near plane"),
    makeProperty<Camera, &Camera::farPlane>("farPlane", "Far plane"),
};
constexpr std::array lightBindings = {
    makeProperty<Light, &Light::color>("color", "Color (linear)"),
    makeProperty<Light, &Light::intensity>("intensity", "Intensity"),
    makeProperty<Light, &Light::exposure>("exposure", "Exposure (stops)"),
    makeProperty<Light, &Light::normalize>("normalize", "Normalize"),
    makeProperty<Light, &Light::enableColorTemperature>("enableColorTemperature", "Color temperature"),
    makeProperty<Light, &Light::colorTemperature>("colorTemperature", "Kelvin"),
    makeProperty<Light, &Light::angle>("angle", "Angle (degrees)"),
    makeProperty<Light, &Light::radius>("radius", "Radius"),
    makeProperty<Light, &Light::width>("width", "Width"),
    makeProperty<Light, &Light::height>("height", "Height"),
    makeProperty<Light, &Light::shaping>("shaping", "Cone (spot)"),
    makeProperty<Light, &Light::coneAngle>("coneAngle", "Cone angle (degrees)"),
    makeProperty<Light, &Light::coneSoftness>("coneSoftness", "Cone softness"),
    makeProperty<Light, &Light::range>("range", "Range (0 = automatic)"),
};
constexpr std::array materialBindings = {
    makeProperty<Material, &Material::name>("name", "Name"),
    makeProperty<Material, &Material::baseColor>("baseColor", "Base color (linear)"),
    makeProperty<Material, &Material::emissiveColor>("emissiveColor", "Emissive color (linear)"),
    makeProperty<Material, &Material::metallic>("metallic", "Metallic"),
    makeProperty<Material, &Material::roughness>("roughness", "Roughness"),
    makeProperty<Material, &Material::occlusion>("occlusion", "Occlusion"),
    makeProperty<Material, &Material::opacity>("opacity", "Opacity"),
    makeProperty<Material, &Material::opacityThreshold>("opacityThreshold", "Opacity threshold"),
    makeProperty<Material, &Material::ior>("ior", "Index of refraction"),
};

template<typename Owner, std::size_t Count>
constexpr bool uniquePropertyKeys(const std::array<PropertyBinding<Owner>, Count>& bindings)
{
    for (std::size_t i = 0; i < Count; ++i)
    {
        if (bindings[i].descriptor.key.empty()) { return false; }
        for (std::size_t j = 0; j < i; ++j)
        {
            if (bindings[i].descriptor.key == bindings[j].descriptor.key) { return false; }
        }
    }
    return true;
}
static_assert(uniquePropertyKeys(nodeBindings) && uniquePropertyKeys(cameraBindings)
    && uniquePropertyKeys(lightBindings) && uniquePropertyKeys(materialBindings), "Duplicate or empty scene property key.");

template<typename Owner, std::size_t Count>
constexpr auto describeProperties(const std::array<PropertyBinding<Owner>, Count>& bindings)
{
    std::array<PropertyDescriptor, Count> descriptors{};
    for (std::size_t i = 0; i < Count; ++i) { descriptors[i] = bindings[i].descriptor; }
    return descriptors;
}
constexpr auto nodeProperties = describeProperties(nodeBindings);
constexpr auto cameraProperties = describeProperties(cameraBindings);
constexpr auto lightProperties = describeProperties(lightBindings);
constexpr auto materialProperties = describeProperties(materialBindings);

template<typename Owner, std::size_t Count>
const PropertyBinding<Owner>* findProperty(const std::array<PropertyBinding<Owner>, Count>& bindings, std::string_view key)
{
    for (const auto& binding : bindings)
    {
        if (binding.descriptor.key == key) { return &binding; }
    }
    return nullptr;
}
```

`makeProperty` derives `PropertyType` from the field, rather than taking a
separately typed enum argument. Constexpr table creation does not turn the
callback invocation into compile-time reflection of arbitrary runtime objects.

The node table demonstrates both direct and nested properties. Camera, light
and material tables use the same helper for their direct members. Descriptor
arrays are derived from those bindings because the public API returns a
contiguous span of descriptors; it cannot return a span of one member inside
larger binding records. Those arrays are derived copies of the registration
information; the returned `std::span` is the non-owning view. There is still
only one handwritten field list.

Lookup is a linear search in a small table. There are five node properties and
fourteen light properties; a dynamic hash registry would add machinery without
changing these operations' purpose. Registration tables live for the program's
lifetime, so descriptor string views and returned spans remain valid.

### First CPU Checkpoint: One Camera Binding

This checkpoint deliberately stops **below** the public `Scene` API. Create
`Tests/TutorialHarness/Chapter45Bindings.cpp` with the implementation skeleton's
includes and `using namespace pf::scene` in its anonymous namespace. Paste
only `PropertyBinding`, `unsupportedProperty`, `propertyType`, `propertyField`
and `makeProperty` there, followed by this function. This fixture declares its
own camera binding; it needs none of the owner registration tables or public
scene functions:

```cpp
void CheckCameraBinding()
{
    Camera camera;
    const auto binding = makeProperty<Camera, &Camera::nearPlane>("nearPlane", "Near plane");
    if (binding.descriptor.type != PropertyType::Float)
    {
        throw std::runtime_error("Camera binding described the wrong type.");
    }
    std::string error;
    if (!binding.write(camera, PropertyValue{ 0.2f }, error))
    {
        throw std::runtime_error(error);
    }
    const PropertyValue read = binding.read(camera);
    if (!std::holds_alternative<float>(read) || std::get<float>(read) != 0.2f)
    {
        throw std::runtime_error("Camera binding did not write and read the same float.");
    }
    const bool rejected = !binding.write(camera, PropertyValue{ std::string("near") }, error);
    if (!rejected || error != "Scene property value has the wrong type." || camera.nearPlane != 0.2f)
    {
        throw std::runtime_error("Wrong-type write changed the camera.");
    }
}
```

This small test uses exceptions to report a failed assertion to its entry point;
the binding itself returns a result for ordinary rejected input. Include
`<stdexcept>` for that test helper. Close its anonymous namespace, include
`<iostream>`, and add the entry point:

```cpp
int main()
{
    try
    {
        CheckCameraBinding();
        std::cout << "Camera binding checkpoint passed.\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
```

The [binding build recipe](SceneDocumentsReference.md#binding-build) repeats
this fixture and supplies the exact `TutorialChapter45Bindings` target and command. Running its executable must print `Camera binding checkpoint
passed.` and exit zero. This proves member binding and type rejection; it
does not yet prove owner validation, dirty transforms or document persistence.
The production tables and dispatch are in
[SceneProperties.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneProperties.cpp).

</details>

## 3. An Edit Is A State Transition

A correctly typed edit can still be invalid. `farPlane = 0.001f` is a float,
but a camera with `nearPlane = 0.1f` cannot use it. Checking after assigning the
live camera would leave an invalid scene even if the function returned false.

The API needs a clear failure contract: an invalid tool request returns an
error and leaves the previous authored state usable. UI limits alone cannot
enforce that contract when a console or test submits the same value directly.

<a id="ch45-typed-properties"></a>

### Attempt CH45-typed-properties: reject an edit without changing the scene

Implement checked reads and writes over the bindings. Move a parent through
the interface, update world transforms, and verify that its child follows.
Then submit a string as translation, an unknown key, an invalid index and a
zero scale. For a camera, submit a far plane inside its near plane.

**Acceptance:** Successful reads return the registered type. A valid transform
write propagates to descendants. Rejected writes retain the previous value
and return a diagnostic. Validation checks the candidate owner before any
scene mutation. A valid edit survives the document round trip in section 5.

**Transfer:** Change a camera's two clip planes in an order where one
intermediate pair would be invalid. Explain why this single-property API
rejects that intermediate state and why a future multi-property command would
need one candidate and one commit for the entire edit.

**Checkpoint:** the public-API fixture below must leave the child's world
position at `(3,5,5)` after rejected edits. The
[checked-edit recipe](SceneDocumentsReference.md#checked-edit-build) runs it
without the document implementation; its fixture is available there too.
The supplied `ch45-documents` pair separately exercises the real `EditLocal`
commit and persistence path; its declared omission is transform invalidation.

<details>
<summary>Hint 1: check the scene index before using its accessors</summary>

The reflection API accepts input from tools. An out-of-range node is a
reported error here, even though `Scene::GetNode` treats one as a programmer
mistake. Check the appropriate array count at this boundary.

</details>

<details>
<summary>Hint 2: validate the candidate owner</summary>

The binding writer should only assign a correctly typed field. The surrounding
write operation validates the completed candidate. Do not let a callback return
a reference that a caller can retain and edit after validation.

</details>

<details>
<summary>Hint 3: commit through the scene's mutation rules</summary>

Assigning `candidate.local` back through `EditLocal(index)` marks the node
dirty. Assigning directly to storage would update the saved number while its
world matrix could remain stale. A failed operation must not call `EditLocal`.

</details>

<details>
<summary>Worked solution: copy, type-check, validate, then commit</summary>

Find the binding, copy authored owner state, apply the typed write to that
copy, validate it, then commit. Node commits use `SetName`, `SetVisible` or
`EditLocal`; unrelated children arrays need not be copied. The validator checks
the candidate owner before those scene hooks are called.

**These are the validation and index helpers in `SceneProperties.cpp`, inside
its anonymous namespace, after the binding helpers and tables.** Camera
validation shows why the owner, rather than an isolated float, is the right
validation unit. The other overloads keep their own physical and numerical
constraints explicit:

```cpp
bool finite(glm::vec3 v)
{
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
}
bool finite(glm::vec4 v)
{
    return finite(glm::vec3(v)) && std::isfinite(v.w);
}
bool unitInterval(float value) { return std::isfinite(value) && value >= 0 && value <= 1; }
bool nonnegative(glm::vec3 value) { return finite(value) && value.x >= 0 && value.y >= 0 && value.z >= 0; }

bool validate(const Node& node, std::string& error)
{
    const auto& t = node.local;
    const auto q = t.rotation;
    if (node.name.size() > 1024 * 1024 || !finite(t.translation) || !finite(t.scale)
        || std::abs(t.scale.x) < 1e-6f || std::abs(t.scale.y) < 1e-6f || std::abs(t.scale.z) < 1e-6f
        || !finite(glm::vec4(q.x, q.y, q.z, q.w)) || std::abs(glm::dot(q, q) - 1.0f) > 1e-3f)
    {
        error = "Node edit needs finite TRS values, nonzero scale, and a unit quaternion.";
        return false;
    }
    return true;
}
bool validate(const Camera& camera, std::string& error)
{
    if (!std::isfinite(camera.verticalFov) || camera.verticalFov <= 0 || camera.verticalFov >= glm::radians(180.0f)
        || !std::isfinite(camera.nearPlane) || !std::isfinite(camera.farPlane)
        || camera.nearPlane <= 0 || camera.farPlane <= camera.nearPlane)
    {
        error = "Camera edit needs 0 < FOV < pi and 0 < near < far.";
        return false;
    }
    return true;
}
bool validate(const Light& light, std::string& error)
{
    const float values[] = { light.intensity, light.exposure, light.colorTemperature, light.angle,
        light.radius, light.width, light.height, light.coneAngle, light.coneSoftness, light.range };
    for (float value : values)
    {
        if (!std::isfinite(value)) { error = "Light values must be finite."; return false; }
    }
    if (!nonnegative(light.color) || light.intensity < 0 || std::abs(light.exposure) > 120
        || light.colorTemperature <= 0 || light.angle < 0 || light.angle > 180
        || light.radius < 0 || light.width < 0 || light.height < 0
        || light.coneAngle < 0 || light.coneAngle > 180 || !unitInterval(light.coneSoftness) || light.range < 0)
    {
        error = "Light edit is outside the supported physical ranges.";
        return false;
    }
    return true;
}
bool validate(const Material& material, std::string& error)
{
    if (material.name.size() > 1024 * 1024 || !finite(material.baseColor)
        || !nonnegative(glm::vec3(material.baseColor)) || !unitInterval(material.baseColor.a)
        || !nonnegative(material.emissiveColor) || !unitInterval(material.metallic)
        || !unitInterval(material.roughness) || !unitInterval(material.occlusion)
        || !unitInterval(material.opacity) || !unitInterval(material.opacityThreshold)
        || !std::isfinite(material.ior) || material.ior <= 0)
    {
        error = "Material edit needs finite colors, [0, 1] surface factors, and positive IOR.";
        return false;
    }
    return true;
}

bool requireIndex(const Scene& scene, PropertyTarget target, uint32_t index, std::string& error)
{
    const std::size_t count = target == PropertyTarget::Node ? scene.NodeCount()
        : target == PropertyTarget::Camera ? scene.CameraCount()
        : target == PropertyTarget::Light ? scene.LightCount()
        : target == PropertyTarget::Material ? scene.MaterialCount() : 0;
    if (index >= count) { error = "Scene property target index is out of range."; return false; }
    return true;
}
```

Negative scale is a valid mirror. The node validator rejects axes whose
absolute scale is below `1e-6f`; it does not turn every negative scale positive.
The exact supported ranges are a project policy, not something the field's
C++ type can infer.

**These are the public functions in `namespace pf::scene`, after closing the
anonymous namespace.** They use the tables and helpers already defined above.
Ordinary type, key, index and range failures return `false` with a diagnostic.
Each write validates a candidate before committing it, so rejection leaves the
live scene unchanged. Helpers use the same result convention as the public API:

```cpp
std::span<const PropertyDescriptor> SceneProperties(PropertyTarget target)
{
    switch (target)
    {
    case PropertyTarget::Node: return nodeProperties;
    case PropertyTarget::Camera: return cameraProperties;
    case PropertyTarget::Light: return lightProperties;
    case PropertyTarget::Material: return materialProperties;
    }
    return {};
}

bool ValidateSceneProperties(const Scene& scene, std::string& error)
{
    error.clear();
    for (uint32_t i = 0; i < scene.NodeCount(); ++i) { if (!validate(scene.GetNode(i), error)) { return false; } }
    for (uint32_t i = 0; i < scene.CameraCount(); ++i) { if (!validate(scene.GetCamera(i), error)) { return false; } }
    for (uint32_t i = 0; i < scene.LightCount(); ++i) { if (!validate(scene.GetLight(i), error)) { return false; } }
    for (uint32_t i = 0; i < scene.MaterialCount(); ++i) { if (!validate(scene.GetMaterial(i), error)) { return false; } }
    return true;
}

bool ReadSceneProperty(const Scene& scene, PropertyTarget target, uint32_t index,
                       std::string_view key, PropertyValue& value, std::string& error)
{
    error.clear();
    if (!requireIndex(scene, target, index, error)) { return false; }
    const auto read = [&](const auto& owner, const auto& bindings) {
        const auto* binding = findProperty(bindings, key);
        if (binding == nullptr) { error = "Unknown scene property key."; return false; }
        value = binding->read(owner);
        return true;
    };
    switch (target)
    {
    case PropertyTarget::Node: return read(scene.GetNode(index), nodeBindings);
    case PropertyTarget::Camera: return read(scene.GetCamera(index), cameraBindings);
    case PropertyTarget::Light: return read(scene.GetLight(index), lightBindings);
    case PropertyTarget::Material: return read(scene.GetMaterial(index), materialBindings);
    }
    error = "Scene property target index is out of range.";
    return false;
}

bool WriteSceneProperty(Scene& scene, PropertyTarget target, uint32_t index,
                        std::string_view key, const PropertyValue& value, std::string& error)
{
    error.clear();
    if (!requireIndex(scene, target, index, error)) { return false; }
    const auto write = [&](auto& candidate, const auto& bindings) {
        const auto* binding = findProperty(bindings, key);
        if (binding == nullptr) { error = "Unknown scene property key."; return false; }
        if (!binding->write(candidate, value, error)) { return false; }
        return validate(candidate, error);
    };
    switch (target)
    {
    case PropertyTarget::Node:
    {
        const Node& node = scene.GetNode(index);
        // Copy editable state only; large children arrays remain with the scene.
        Node candidate{ .name = node.name, .local = node.local, .visible = node.visible };
        if (!write(candidate, nodeBindings)) { return false; }
        if (key == "name") { scene.SetName(index, std::move(candidate.name)); }
        else if (key == "visible") { scene.SetVisible(index, candidate.visible); }
        else { scene.EditLocal(index) = candidate.local; }
        return true;
    }
    case PropertyTarget::Camera:
    {
        Camera candidate = scene.GetCamera(index);
        if (!write(candidate, cameraBindings)) { return false; }
        scene.GetCamera(index) = candidate;
        return true;
    }
    case PropertyTarget::Light:
    {
        Light candidate = scene.GetLight(index);
        if (!write(candidate, lightBindings)) { return false; }
        scene.GetLight(index) = candidate;
        return true;
    }
    case PropertyTarget::Material:
    {
        Material candidate = scene.GetMaterial(index);
        if (!write(candidate, materialBindings)) { return false; }
        scene.GetMaterial(index) = std::move(candidate);
        return true;
    }
    }
    error = "Scene property target index is out of range.";
    return false;
}
```

The public descriptor, read and write operations all use the same binding
tables. The commit switch is still explicit: editing a node transform requires
different scene bookkeeping from editing a camera lens. Hiding that distinction
in a raw member write would lose the invariant this chapter is meant to keep.

`ValidateSceneProperties` runs these owner checks over all nodes, cameras,
lights and materials, and is shared with the document validator. It checks
authored properties, not every graph/reference/world-matrix invariant. Section
6 adds those whole-document checks. The specialized inspector controls now
submit through the same checked write API. Direct scene accessors remain
available to engine code, so reflection does not retroactively make every
write in the engine pass through this API.

The complete test below changes a node through this public boundary and
checks rejection without directly editing its storage:

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


### Second CPU Checkpoint: A Checked Scene Edit

This fixture calls the **public scene-property API**, unlike the binding-only
checkpoint. Put it in `Chapter45Edits.cpp`, outside the property implementation;
the [checked-edit recipe](SceneDocumentsReference.md#checked-edit-build) gives
its driver and target. Calling `CheckTypedSceneEdit()` must
leave the child's world position at `(3,5,5)`, retain that translation after
all rejected writes, retain a unit scale and leave the original clip planes.
The driver prints its success only after these assertions return normally.


</details>

## 4. Generate Controls From The Described Values

The property layer has no dependency on ImGui. The inspector asks for a target's
descriptors, reads a value, edits a local variant, and submits it back through
`WriteSceneProperty`. Its job is presentation and interaction; validation still
belongs to the layer below.

Use the target, component index and property key in the ImGui ID stack. Two materials can
have the same display name, and multiple components can each have an
`Intensity` label. Their identity comes from the selected owner, not that text.

<a id="ch45-generated-inspector"></a>

### Attempt CH45-generated-inspector: add controls without another field list

Write one panel function that iterates descriptors and edits each supported
variant alternative. Keep a rejected edit's diagnostic visible. Add quaternion
editing without treating its four components as four Euler angles. Show a
shared mesh material only once when several submeshes refer to it.

**Acceptance:** Name, visibility, vector, scalar and quaternion properties are
editable through the same loop. Two owners with identical labels keep distinct
widget IDs. Rejected changes leave the scene intact. An edited nonzero finite
quaternion is normalized before submission. Materials mark an explicit pending
GPU update rather than silently overwriting shared GPU buffers.

**Transfer:** Change a property label, then select another material with that
same label. Which values determine widget identity? Explain why a linear RGB
vector and a translation can share a storage type while benefiting from
different specialized controls later.

**UI checkpoint:** after [building the inspector stage](SceneDocumentsReference.md#inspector-run),
edit a parent translation and observe its child, reject zero scale, and select
owners with identical labels. Errors must stay visible and controls distinct.
Material publication is completed in Part 3; the CPU pairs do not check widgets.

<details>
<summary>Hint 1: edit the returned value, not the scene storage</summary>

Read a `PropertyValue`, use `get_if` to select a widget, and pass the edited
variant to the checked write. A rejected value then disappears on the next
read while its diagnostic remains available.

</details>

<details>
<summary>Hint 2: strings and quaternions need small adapters</summary>

ImGui's text input needs writable character storage. Give it a terminated
temporary buffer and copy accepted text into the string. For quaternions,
normalize only after an edit and only when the finite length is nonzero;
leave impossible values for validation to reject.

</details>

<details>
<summary>Hint 3: CPU changes and GPU publication have different owners</summary>

The generic loop returns whether a checked write succeeded. Its caller can
then mark `materialsChanged`. The property helper cannot know whether another
frame is still reading the renderer's material buffer.

</details>

<details>
<summary>Worked solution: a typed widget loop with checked submission</summary>

**Add this declaration to `ScenePanels.h` in `namespace pf::scene`, and the
following function to `ScenePanels.cpp` in that namespace, above
`drawNodeInspector`.** This listing uses the direct ImGui controls taught in
Chapter 7. The assembled reference routes three controls through its optional
[control-workspace wrappers](09-Demo-Harness.md#control-workspace-transfer);
those are not a prerequisite for this path.
The source also includes `<algorithm>`,
`<cmath>`, `<cstring>`, `<string>`, `<variant>` and `<vector>`.

```cpp
bool drawReflectedProperties(Scene& scene, PropertyTarget target,
                             uint32_t index, std::string& error);
```

```cpp
bool drawReflectedProperties(Scene& scene, PropertyTarget target, uint32_t index, std::string& error)
{
    bool changed = false;
    ImGui::PushID(static_cast<int>(target));
    ImGui::PushID(static_cast<int>(index));
    for (const PropertyDescriptor& property : SceneProperties(target))
    {
        PropertyValue value;
        std::string readError;
        if (!ReadSceneProperty(scene, target, index, property.key, value, readError))
        {
            error = readError;
            continue;
        }
        ImGui::PushID(property.key.data(), property.key.data() + property.key.size());
        bool edited = false;
        // The key owns widget identity; changing a display label preserves focus.
        const std::string label = std::string(property.label) + "###value";
        if (auto* boolean = std::get_if<bool>(&value))
        {
            edited = ImGui::Checkbox(label.c_str(), boolean);
        }
        else if (auto* number = std::get_if<float>(&value))
        {
            edited = ImGui::DragFloat(label.c_str(), number, 0.01f);
        }
        else if (auto* vector3 = std::get_if<glm::vec3>(&value))
        {
            edited = ImGui::DragFloat3(label.c_str(), &vector3->x, 0.01f);
        }
        else if (auto* vector4 = std::get_if<glm::vec4>(&value))
        {
            edited = ImGui::DragFloat4(label.c_str(), &vector4->x, 0.01f);
        }
        else if (auto* rotation = std::get_if<glm::quat>(&value))
        {
            edited = ImGui::DragFloat4(label.c_str(), &rotation->x, 0.01f);
            const float length = glm::length(*rotation);
            if (edited && std::isfinite(length) && length > 1e-6f) { *rotation /= length; }
        }
        else if (auto* text = std::get_if<std::string>(&value))
        {
            std::vector<char> buffer(std::max<std::size_t>(text->size() + 256, 1024), '\0');
            std::memcpy(buffer.data(), text->data(), text->size());
            edited = ImGui::InputText(label.c_str(), buffer.data(), buffer.size());
            if (edited) { *text = buffer.data(); }
        }
        if (edited)
        {
            std::string writeError;
            if (WriteSceneProperty(scene, target, index, property.key, value, writeError))
            {
                changed = true;
                error.clear();
            }
            else { error = writeError; }
        }
        ImGui::PopID();
    }
    ImGui::PopID();
    ImGui::PopID();
    return changed;
}
```

The current UI dispatches on the variant's active type. The binding-derived
descriptor agrees with it, but the widget never reinterprets a value merely
because metadata names a type. Quaternion storage order is the order of its
members (`x,y,z,w`) here; section 5's document explicitly chooses another
representation and converts it deliberately.

### Connect The Generated Controls

**`ScenePanels.h` must include both `Scene.h` and `SceneProperties.h`.** Its
existing `SceneEditorState` becomes the following, inside `namespace pf::scene`;
keep the existing panel declarations and the new function declaration below it:

```cpp
struct SceneEditorState
{
    NodeIndex selected = INVALID_NODE;
    std::string transformError;
    bool editMaterials = false;     // owning demo must safely rebuild GPU material resources
    bool materialsChanged = false;
    std::string propertyError;

    // The inspector shows rotation as three angles, but the node stores a
    // quaternion. These are the angles last shown, and the quaternion they were
    // shown for - Chapter 12 section 9 says why both are kept.
    glm::vec3 eulerDegrees{ 0.0f };
    glm::quat eulerSource{ 0.0f, 0.0f, 0.0f, 0.0f };   // matches no real rotation: "nothing shown yet"
    NodeIndex eulerNode = INVALID_NODE;
};
```
**In `drawNodeInspector`, inside the existing valid-selection branch**, keep
`const NodeIndex index = state.selected;` and `const Node& node = scene.GetNode(index);`.
After the specialized camera/light controls, insert this complete call site:

```cpp
if (ImGui::TreeNode("Reflected properties"))
{
    drawReflectedProperties(scene, PropertyTarget::Node, index, state.propertyError);
    if (node.camera != NO_COMPONENT && ImGui::TreeNode("Camera properties"))
    {
        drawReflectedProperties(scene, PropertyTarget::Camera, node.camera, state.propertyError);
        ImGui::TreePop();
    }
    if (node.light != NO_COMPONENT && ImGui::TreeNode("Light properties"))
    {
        drawReflectedProperties(scene, PropertyTarget::Light, node.light, state.propertyError);
        ImGui::TreePop();
    }
    if (state.editMaterials && node.mesh != NO_COMPONENT)
    {
        std::vector<uint32_t> shown;
        for (const Submesh& submesh : scene.GetMesh(node.mesh).data.submeshes)
        {
            const uint32_t material = submesh.materialIndex;
            if (std::find(shown.begin(), shown.end(), material) != shown.end()) { continue; }
            shown.push_back(material);
            ImGui::PushID(static_cast<int>(material));
            if (ImGui::TreeNode("Material", "%s", scene.GetMaterial(material).name.c_str()))
            {
                state.materialsChanged |= drawReflectedProperties(scene,
                    PropertyTarget::Material, material, state.propertyError);
                ImGui::TreePop();
            }
            ImGui::PopID();
        }
    }
    ImGui::TreePop();
}
if (!state.propertyError.empty()) { ImGui::TextWrapped("%s", state.propertyError.c_str()); }
```
The material loop uses the mesh's actual material indices, not its submesh
number. A shared material appears only once and one accepted write marks a
pending GPU update. `editMaterials` defaults to false, so a demo has to supply
the activation boundary before enabling those controls.

That index identifies a shared scene material. Applying its pending update
changes every submesh that refers to it. Position and scale remain per-node
transform edits.

Specialized controls share the same write boundary. **For example, replace
the inspector's direct translation mutation with this block**, after defining
`index` and `node` as above:

```cpp
glm::vec3 translation = node.local.translation;
if (ImGui::DragFloat3("Translation", &translation.x, 0.05f))
{
    WriteSceneProperty(scene, PropertyTarget::Node, index,
        "translation", PropertyValue{ translation }, state.propertyError);
}
```

Finish migrating the old inspector rather than keeping a second commit path:

- Remove Chapter 12's aggregate `edited` flag and its final
  `scene.EditLocal(index) = local` assignment. Each accepted control now commits
  through `WriteSceneProperty`; an invalid scale or rotation must reach it too.
- Replace direct name/visibility setters with checked writes for `name`
  (`std::string`) and `visible` (`bool`). Scale submits a `glm::vec3`; Euler
  controls convert their degrees to a unit quaternion for `rotation`.
- Camera controls use `PropertyTarget::Camera` and `node.camera`. The light
  helper takes `Scene&`, the light component index and the shared error string;
  call `drawLightInspector(scene, node.light, state.propertyError)`. Each lens
  or light value is a local candidate, submitted with its registered key.
- The light-colour swatch converts sRGB to linear RGB before submitting
  `color`. Presentation conversions do not write the live component directly.

The complete named adapters are `drawNodeInspector` and the file-scope
`drawLightInspector` in [ScenePanels.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/ScenePanels.cpp).
Use them to compare the finished migration. On the direct ImGui path, replace
the optional `debug_panels` control calls with their corresponding ImGui calls,
as the generic loop above does.

**The caller is Chapter 14's `UsdViewerDemo::Update`.** Keep its existing
hierarchy and inspector calls, before the world-transform update:

```cpp
scene::drawSceneHierarchy(m_scene, m_editor);
scene::drawNodeInspector(m_scene, m_editor);
m_scene.UpdateWorldTransforms();
```

`m_scene` and `m_editor` are the viewer's existing CPU members. Keep
`m_editor.editMaterials` false for this first inspector check. After completing
section 7's GPU rebuild boundary, set it true at the end of a successful viewer
`Setup` to enable material edits.
The generic implementation needs no new call from `SandboxGame::main`: the
demo harness already invokes this viewer's `Update` and `Record`.

### UI Checkpoint: One Interface, Two Presentations

In the USD viewer, select a node with a child and edit its translation under
**Reflected properties**. The child follows on the next frame. Try zero scale;
the value is rejected and the error remains visible after collapsing that
tree. Make a valid edit through the specialized control to clear the error.
Select two owners with identical display names: their controls stay distinct.
Once Part 3 enables material controls, edit a textured mesh's material and
expect the pending message; section 7's
**Apply material changes** publishes it. Run this attended UI check separately
from the CPU build using the [inspector command](SceneDocumentsReference.md#inspector-run). A CPU pass does
not prove widget identity, readable errors or rendered material updates.

Each generic widget pushes the stable property key and uses the `###value`
label suffix. ImGui displays the label before `###` but uses the suffix for
its local ID; combined with the key/owner stack, changing display text preserves
widget identity. The inspector draws `propertyError` after the reflected tree,
so collapsing it does not hide a diagnostic from a specialized control.

The complete integration is in
[ScenePanels.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/ScenePanels.cpp). The existing
Euler controls and sRGB light-color swatch remain useful: they convert their
presentation values and call `WriteSceneProperty`, just as the generic controls
do. A generic quaternion editor is mechanically correct but less convenient
for many human edits. Storage reflection supplies a default inspector; it does
not eliminate presentation choices.

</details>

# Part 2 — A document that survives the process

## 5. Save Authored Data, Rebuild Derived Data

The binding table describes editable values. A document has a separate,
versioned schema: it also stores hierarchy, meshes, material texture inputs,
decoded images, cameras, lights and the active camera. Adding an editor control
therefore needs a separate decision about persistence.

Store authored inputs and rebuild the device-dependent or cached results:

| Stored input | Reconstructed result |
| --- | --- |
| Parent and ordered children, local translation/rotation/scale | Validated hierarchy and recomputed world transforms |
| CPU vertex/index data and submesh assignments | Mesh bounds and GPU vertex/index buffers |
| Decoded images and material texture inputs | GPU images, views, samplers and descriptors |
| Camera lens plus the camera node | View/projection for the current target aspect |
| Authored lights plus their nodes | Resolved world-space lighting |

Version 1 preserves array indices and child order within one document. Those
indices express local relationships; persistent cross-document identity needs
its own contract. Self-contained mesh/image data makes reopening independent
of the source USD file, at the cost of larger files.

> **Jump:** JSON represents named values as objects and ordered values as
> arrays. `{"name":"Lamp","children":[]}` is an illustrative record, not a
> complete document. Encoding turns scene inputs into these values; decoding
> builds a candidate scene. Validation comes before publishing that candidate.

Before compiling the hierarchy codec below, add the
[CPU environment-data bridge](SceneDocumentsReference.md#environment-data)
if you arrived from Chapters 1–19. The bounded validator checks that these
arrays are empty, so it still needs their declarations. The complete format
later retains their images; rendering an environment remains Chapter 23's work.

**Place JSON helpers in `SceneDocument.cpp`'s anonymous namespace.** Keep JSON
types private. `SceneDocument.h` exposes `SaveSceneDocument` and
`LoadSceneDocument`; the friend `SceneDocumentAccess` owns whole-scene
encode/decode/validation in the implementation.

Private array access lets the decoder restore saved local transforms, shared
references and child order exactly. Replaying world-preserving `Reparent`
would answer a different question. Section 6 validates the completed arrays
before moving the candidate into the caller.

For the first hierarchy build, **create `SceneDocument.h` now from the
[complete public header](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneDocument.h)**.
It supplies `SCENE_DOCUMENT_VERSION`, the size limit and public declarations.
The bounded checkpoint needs this header, but does not link `SceneDocument.cpp`.

A **schema** is the agreement about required keys, value types and meanings.
For the bounded projection the top-level keys are:

| Required keys | Meaning |
| --- | --- |
| `format`, `version` | Identify this representation and its supported version |
| `activeCamera` | Node index, or `INVALID_NODE` for no active camera |
| `nodes` | Ordered records: name, parent/children, local TRS, visibility and component indices |
| `cameras`, `lights` | Component arrays referenced by those node indices |

The complete file later adds mesh/material/image arrays. This table describes
the bounded projection only. Indices refer to array positions, so decoding
must retain their order before validating the links.

The JSON library is a container API over those named values. With
`using Json = nlohmann::json`, a small illustrative record is:

```cpp
Json item{ { "name", "Lamp" }, { "children", Json::array() } };
item["children"].push_back(2);
const std::string label = item.at("name").get<std::string>();
```

Each `{ "key", value }` pair creates one object member. Encoding with
`operator[]` can create a key; decoding with `.at` requires it and throws when
missing. `.push_back` appends in order. The codec's scalar/array helpers check
types, bounds and shapes before converting with `.get<T>()`. Do not use
`operator[]` to silently invent missing required input.

<a id="ch45-document-round-trip"></a>

### Attempt CH45-document-round-trip: reopen the scene you edited

First implement an in-memory hierarchy codec: ordered nodes, local TRS,
visibility and camera/light references, with their component arrays. Make a
parent translated by two metres, put a light one metre above it, and add an
active camera. Predict the light's world position after decode. Then integrate
the supplied material/mesh/image codecs into the complete version-1 document,
save it, change the parent in memory, and reload. Extend the full-format
fixture with one textured mesh and a dome environment.

**Acceptance:** The loaded hierarchy and local transforms reproduce the
saved scene. The hierarchy checkpoint preserves camera/light references and
child order; after full-format integration, material assignments and decoded
assets survive too. An active camera is either `INVALID_NODE` or a node with
a valid camera component. The document can represent a scene without a camera;
the viewer adds a framing camera when needed. Invalid versions, broken references,
malformed data and failed file operations produce an error. A failed load
leaves the caller's current scene usable. Loading never restores Vulkan
handles from disk.

**Transfer:** Move the saved document away from its source USD asset, then
load it into a fresh process. Explain why self-contained image and mesh data
permit this. Now imagine a water simulation that owns elapsed time outside
`Scene`: which additional state and reset/resume policy would saving it need?

**CPU checkpoint:** run `ch45-hierarchy` using the
[checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md). The
decoded light must be at `(2,1,0)`, with its component links intact.
For your own listing use the [hierarchy recipe](SceneDocumentsReference.md#hierarchy-build),
including the two-sibling order control below. The packaged pair's declared
omission tests translation restoration; its one-child fixture alone cannot
demonstrate resistance to sibling sorting.
Then run the full-format fixture with the
[document recipe](SceneDocumentsReference.md#document-build); a hierarchy
projection alone is not a valid version-1 `.pfscene` file.

<details>
<summary>Hint 1: a document is a set of inputs</summary>

Persist local transforms and component data. Recompute world matrices and
rendering resources from those inputs. Saving only the inspector's current
selection or an import filename loses edited state.

</details>

<details>
<summary>Hint 2: parse before publishing</summary>

Build a candidate scene and validate its references before replacing the
caller's scene. A malformed late material must not leave half a newly loaded
hierarchy attached to the old one.

</details>

<details>
<summary>Hint 3: compare both data and derived behavior</summary>

Check local values and relationships, then call `UpdateWorldTransforms` and
check the light's world position. Include texture bytes and active-camera
selection; equal node counts alone miss both kinds of loss.

</details>

<details>
<summary>Worked solution: round-trip CPU state through the document API</summary>

### Implement The Hierarchy Before The Asset Codecs

The following is a complete **in-memory hierarchy checkpoint**, using the
version-1 keys and transform representation. It deliberately excludes mesh,
texture and environment arrays and retains the scene's default material. Its
JSON projection is **not a complete `.pfscene` file** and must not be passed to
`LoadSceneDocument`. The final file implementation below retains the existing
public API and full version-1 schema.

For this standalone checkpoint, create
`Tests/TutorialHarness/Chapter45Hierarchy.cpp`. **Start with these complete
includes, private conversion helpers and limits:**

```cpp
#include "PillowFort/Scene/SceneDocument.h"
#include "PillowFort/Scene/SceneProperties.h"
#include <external/jsonhpp/nlohmann/json.hpp>

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace {
using Json = nlohmann::json;
using namespace pf::scene;
constexpr std::size_t MAX_NODES = 100000;
constexpr std::size_t MAX_COMPONENTS = 100000;
constexpr std::size_t MAX_HIERARCHY_DEPTH = 512;
constexpr std::size_t MAX_STRING = 1024 * 1024;

void require(bool condition, const char* message)
{
    if (!condition) { throw std::runtime_error(message); }
}

const Json& array(const Json& value, std::size_t limit)
{
    require(value.is_array() && value.size() <= limit, "Scene array has the wrong type or exceeds its count limit.");
    return value;
}
uint32_t integer(const Json& value)
{
    require(value.is_number_integer(), "Scene index/dimension must be an integer.");
    if (value.is_number_unsigned())
    {
        const uint64_t number = value.get<uint64_t>();
        require(number <= UINT32_MAX, "Scene integer is outside the uint32 range.");
        return static_cast<uint32_t>(number);
    }
    const int64_t number = value.get<int64_t>();
    require(number >= 0 && number <= UINT32_MAX, "Scene integer is outside the uint32 range.");
    return static_cast<uint32_t>(number);
}
float scalar(const Json& value)
{
    require(value.is_number(), "Scene scalar must be a number.");
    const double number = value.get<double>();
    require(std::isfinite(number) && std::abs(number) <= std::numeric_limits<float>::max(),
            "Scene scalar must be a finite float.");
    return static_cast<float>(number);
}
bool boolean(const Json& value)
{
    require(value.is_boolean(), "Scene flag must be a boolean.");
    return value.get<bool>();
}
std::string string(const Json& value)
{
    require(value.is_string(), "Scene name must be a string.");
    const auto& result = value.get_ref<const std::string&>();
    require(result.size() <= MAX_STRING, "Scene name exceeds its size limit.");
    return result;
}
glm::vec2 vec2(const Json& value)
{
    require(array(value, 2).size() == 2, "Scene vec2 must contain two numbers.");
    return { scalar(value[0]), scalar(value[1]) };
}
glm::vec3 vec3(const Json& value)
{
    require(array(value, 3).size() == 3, "Scene vec3 must contain three numbers.");
    return { scalar(value[0]), scalar(value[1]), scalar(value[2]) };
}
glm::vec4 vec4(const Json& value)
{
    require(array(value, 4).size() == 4, "Scene vec4 must contain four numbers.");
    return { scalar(value[0]), scalar(value[1]), scalar(value[2]), scalar(value[3]) };
}
Json encode(glm::vec2 value) { return Json::array({ value.x, value.y }); }
Json encode(glm::vec3 value) { return Json::array({ value.x, value.y, value.z }); }
Json encode(glm::vec4 value) { return Json::array({ value.x, value.y, value.z, value.w }); }
Json encode(const Transform& value)
{
    const auto q = value.rotation;
    return { { "translation", encode(value.translation) }, { "rotation", Json::array({ q.w, q.x, q.y, q.z }) },
             { "scale", encode(value.scale) } };
}
Transform transform(const Json& value)
{
    const glm::vec4 q = vec4(value.at("rotation"));
    return { .translation = vec3(value.at("translation")), .rotation = glm::quat(q.x, q.y, q.z, q.w),
             .scale = vec3(value.at("scale")) };
}

bool finite(glm::vec2 value) { return std::isfinite(value.x) && std::isfinite(value.y); }
bool finite(glm::vec3 value) { return finite(glm::vec2(value)) && std::isfinite(value.z); }
bool finite(glm::vec4 value) { return finite(glm::vec3(value)) && std::isfinite(value.w); }
bool finite(const glm::mat4& value)
{
    for (int column = 0; column < 4; ++column) { if (!finite(value[column])) { return false; } }
    return true;
}
} // namespace
```
The transform helper explicitly saves quaternion order `[w,x,y,z]`.
`vec4` names its returned components `x,y,z,w`, so its local `q.x` contains the
saved quaternion `w`; the `glm::quat(w,x,y,z)` constructor restores it deliberately.
The inspector's memory order is a different representation.

**Add `friend struct SceneDocumentAccess;` to the private section of `Scene`
in `Scene.h`.** In the checkpoint source, append this complete private-access
owner and its three functions. This preserves indices and child order directly;
replaying world-preserving `Reparent` would change the saved local transforms.

```cpp
namespace pf::scene {

// These bounded checkpoint helpers are not the complete .pfscene file codec.
struct SceneDocumentAccess
{
    static void ValidateHierarchy(const Scene& scene);
    static Json EncodeHierarchy(const Scene& scene);
    static Scene DecodeHierarchy(const Json& document);
};

void SceneDocumentAccess::ValidateHierarchy(const Scene& scene)
{
    require(!scene.m_nodes.empty() && scene.m_nodes.size() <= MAX_NODES, "Scene needs a root and at most 100000 nodes.");
    require(!scene.m_materials.empty(), "Scene needs its default material at index zero.");
    for (const std::size_t size : { scene.m_meshes.size(), scene.m_cameras.size(), scene.m_materials.size(),
                                   scene.m_lights.size(), scene.m_textures.size(), scene.m_environments.size() })
    {
        require(size <= MAX_COMPONENTS, "Scene component array exceeds its count limit.");
    }
    std::string propertyError;
    if (!ValidateSceneProperties(scene, propertyError)) { throw std::runtime_error(propertyError); }
    const auto valid = [](uint32_t index, std::size_t count) { return index == NO_COMPONENT || index < count; };
    require(scene.m_nodes[ROOT_NODE].parent == INVALID_NODE, "Scene root must have no parent.");
    std::vector<uint32_t> incoming(scene.m_nodes.size(), 0);
    for (NodeIndex i = 0; i < scene.m_nodes.size(); ++i)
    {
        const Node& node = scene.m_nodes[i];
        require(i == ROOT_NODE || node.parent < scene.m_nodes.size(), "Scene node has an invalid parent.");
        require(valid(node.mesh, scene.m_meshes.size()) && valid(node.camera, scene.m_cameras.size())
                && valid(node.light, scene.m_lights.size()), "Scene node refers to a missing component.");
        for (NodeIndex child : node.children)
        {
            require(child != ROOT_NODE && child < scene.m_nodes.size(), "Scene child index is invalid.");
            require(scene.m_nodes[child].parent == i && ++incoming[child] == 1,
                    "Scene parent/child links disagree or contain duplicate children.");
        }
    }
    for (NodeIndex i = 1; i < incoming.size(); ++i)
    {
        require(incoming[i] == 1, "Every scene node must appear exactly once in its parent's children.");
    }
    struct Visit { NodeIndex node; std::size_t depth; glm::mat4 parent; };
    std::vector<Visit> stack{ { ROOT_NODE, 0, glm::mat4(1) } };
    std::size_t visited = 0;
    while (!stack.empty())
    {
        const Visit visit = stack.back();
        stack.pop_back();
        require(visit.depth <= MAX_HIERARCHY_DEPTH && ++visited <= scene.m_nodes.size(),
                "Scene hierarchy is cyclic or exceeds its depth limit.");
        const Node& node = scene.m_nodes[visit.node];
        const glm::mat4 world = visit.parent * node.local.Matrix();
        require(finite(world) && finite(glm::inverse(world)), "Scene world transform is singular or non-finite.");
        for (NodeIndex child : node.children) { stack.push_back({ child, visit.depth + 1, world }); }
    }
    require(visited == scene.m_nodes.size(), "Scene hierarchy has a cycle or disconnected nodes.");
    require(scene.m_activeCamera == INVALID_NODE || (scene.m_activeCamera < scene.m_nodes.size()
        && scene.m_nodes[scene.m_activeCamera].camera != NO_COMPONENT), "Active camera must name a camera node.");

    require(scene.m_meshes.empty() && scene.m_textures.empty() && scene.m_environments.empty()
        && scene.m_materials.size() == 1, "Hierarchy checkpoint excludes meshes and asset arrays.");
    for (const Light& light : scene.m_lights)
    {
        require(static_cast<uint32_t>(light.type) <= static_cast<uint32_t>(LightType::Dome)
            && light.environment == NO_ENVIRONMENT && finite(light.domeTextureAverage),
            "Hierarchy checkpoint light has an invalid type or environment reference.");
    }
}

Json SceneDocumentAccess::EncodeHierarchy(const Scene& scene)
{
    ValidateHierarchy(scene);
    Json document{ { "format", "PillowFort.Scene" }, { "version", SCENE_DOCUMENT_VERSION },
        { "activeCamera", scene.m_activeCamera }, { "nodes", Json::array() },
        { "cameras", Json::array() }, { "lights", Json::array() } };
    for (const Node& node : scene.m_nodes)
    {
        document["nodes"].push_back({ { "name", node.name }, { "parent", node.parent }, { "children", node.children },
            { "local", encode(node.local) }, { "visible", node.visible }, { "mesh", node.mesh },
            { "camera", node.camera }, { "light", node.light } });
    }
    for (const Camera& camera : scene.m_cameras)
    {
        document["cameras"].push_back({ { "verticalFov", camera.verticalFov }, { "nearPlane", camera.nearPlane },
            { "farPlane", camera.farPlane } });
    }
    for (const Light& light : scene.m_lights)
    {
        document["lights"].push_back({ { "type", static_cast<uint32_t>(light.type) }, { "color", encode(light.color) },
            { "intensity", light.intensity }, { "exposure", light.exposure }, { "normalize", light.normalize },
            { "enableColorTemperature", light.enableColorTemperature }, { "colorTemperature", light.colorTemperature },
            { "angle", light.angle }, { "radius", light.radius }, { "width", light.width }, { "height", light.height },
            { "shaping", light.shaping }, { "coneAngle", light.coneAngle }, { "coneSoftness", light.coneSoftness },
            { "domeTextureAverage", encode(light.domeTextureAverage) }, { "environment", light.environment }, { "range", light.range } });
    }
    return document;
}

Scene SceneDocumentAccess::DecodeHierarchy(const Json& document)
{
    require(document.is_object() && string(document.at("format")) == "PillowFort.Scene", "Not a PillowFort hierarchy projection.");
    require(integer(document.at("version")) == SCENE_DOCUMENT_VERSION, "Unsupported scene document version.");
    Scene scene;
    scene.m_nodes.clear();
    scene.m_activeCamera = integer(document.at("activeCamera"));
    for (const auto& item : array(document.at("nodes"), MAX_NODES))
    {
        Node node{ .name = string(item.at("name")), .parent = integer(item.at("parent")),
            .local = transform(item.at("local")), .visible = boolean(item.at("visible")),
            .mesh = integer(item.at("mesh")), .camera = integer(item.at("camera")), .light = integer(item.at("light")) };
        for (const auto& child : array(item.at("children"), MAX_NODES)) { node.children.push_back(integer(child)); }
        scene.m_nodes.push_back(std::move(node));
    }
    for (const auto& item : array(document.at("cameras"), MAX_COMPONENTS))
    {
        scene.m_cameras.push_back({ .verticalFov = scalar(item.at("verticalFov")),
            .nearPlane = scalar(item.at("nearPlane")), .farPlane = scalar(item.at("farPlane")) });
    }
    for (const auto& item : array(document.at("lights"), MAX_COMPONENTS))
    {
        scene.m_lights.push_back({ .type = static_cast<LightType>(integer(item.at("type"))), .color = vec3(item.at("color")),
            .intensity = scalar(item.at("intensity")), .exposure = scalar(item.at("exposure")),
            .normalize = boolean(item.at("normalize")), .enableColorTemperature = boolean(item.at("enableColorTemperature")),
            .colorTemperature = scalar(item.at("colorTemperature")), .angle = scalar(item.at("angle")),
            .radius = scalar(item.at("radius")), .width = scalar(item.at("width")), .height = scalar(item.at("height")),
            .shaping = boolean(item.at("shaping")), .coneAngle = scalar(item.at("coneAngle")),
            .coneSoftness = scalar(item.at("coneSoftness")), .domeTextureAverage = vec3(item.at("domeTextureAverage")),
            .environment = integer(item.at("environment")), .range = scalar(item.at("range")) });
    }
    ValidateHierarchy(scene);
    scene.UpdateWorldTransforms();
    return scene;
}

} // namespace pf::scene
```
The topology checks prove both matching local links and complete rooted
reachability. A disconnected cycle may have one incoming link per node, but
the root traversal will visit fewer nodes than the scene owns. Component
references are checked before dereferencing. `INVALID_NODE` is valid for the
active camera; any other value must address a node with a camera component.

**Append this entry point to that checkpoint file:**

```cpp
int main()
{
    using namespace pf::scene;
    try
    {
        Scene original;
        const NodeIndex parent = original.AddNode("Parent", ROOT_NODE,
            Transform{ .translation = { 2.0f, 0.0f, 0.0f } });
        const NodeIndex lamp = original.AddNode("Lamp", parent,
            Transform{ .translation = { 0.0f, 1.0f, 0.0f } });
        const uint32_t light = original.AddLight(Light{});
        original.SetLight(lamp, light);
        const NodeIndex eye = original.AddNode("Camera");
        original.SetCamera(eye, original.AddCamera(Camera{}));
        original.SetActiveCamera(eye);
        const Json encoded = SceneDocumentAccess::EncodeHierarchy(original);
        original.EditLocal(parent).translation.x = 100.0f;
        Scene loaded = SceneDocumentAccess::DecodeHierarchy(encoded);
        require(loaded.GetNode(lamp).parent == parent && loaded.GetNode(lamp).light == light,
            "Hierarchy references changed.");
        require(loaded.GetNode(parent).children == original.GetNode(parent).children,
            "Child links changed.");
        require(loaded.GetNode(ROOT_NODE).children == original.GetNode(ROOT_NODE).children,
            "Original sibling order changed.");
        // Root has two children. Reverse their encoded order without changing
        // parent links; a decoder that sorts by index must fail this control.
        Json reordered = encoded;
        reordered["nodes"][ROOT_NODE]["children"] = Json::array({ eye, parent });
        Scene reorderedScene = SceneDocumentAccess::DecodeHierarchy(reordered);
        const std::vector<NodeIndex> expectedOrder{ eye, parent };
        require(reorderedScene.GetNode(ROOT_NODE).children == expectedOrder,
            "Ordered siblings were sorted or reversed during decode.");
        require(SceneDocumentAccess::EncodeHierarchy(reorderedScene)["nodes"][ROOT_NODE]["children"]
                == reordered["nodes"][ROOT_NODE]["children"], "Encoding changed the reordered siblings.");
        require(loaded.ActiveCamera() == eye, "Active camera changed.");
        require(glm::length(glm::vec3(loaded.GetNode(lamp).world[3]) - glm::vec3(2, 1, 0)) < 1e-5f,
            "Local transforms did not reproduce the light's world position.");

        Json noActive = encoded;
        noActive["activeCamera"] = INVALID_NODE;
        require(SceneDocumentAccess::DecodeHierarchy(noActive).ActiveCamera() == INVALID_NODE,
            "A valid scene without an active camera was rejected.");

        Json cycle = encoded;
        cycle["nodes"][ROOT_NODE]["children"] = Json::array({ eye });
        cycle["nodes"][parent]["parent"] = lamp;
        cycle["nodes"][lamp]["children"] = Json::array({ parent });
        bool rejected = false;
        try { (void)SceneDocumentAccess::DecodeHierarchy(cycle); }
        catch (const std::exception&) { rejected = true; }
        require(rejected, "Disconnected hierarchy cycle was accepted.");
        std::cout << "Hierarchy codec checkpoint passed: world position (2,1,0).\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
```
Build and run `TutorialChapter45Hierarchy` using the
[hierarchy build recipe](SceneDocumentsReference.md#hierarchy-build) and its
commands. Expect exit zero and `Hierarchy codec checkpoint passed: world
position (2,1,0).` The test also checks child order, component references,
an absent active camera and a disconnected cycle. It uses no filesystem or GPU.
This source defines its own bounded `SceneDocumentAccess`; do not link it with
the production `SceneDocument.cpp` in the same executable.

### Integrate The Complete Version-1 Format

The [environment data and accessors](SceneDocumentsReference.md#environment-data)
added before the hierarchy checkpoint now let the complete format retain dome
images as well.

The hierarchy checkpoint is now understood and independently runnable. The
remaining repetitive mesh/material/image conversions are supplied reference
plumbing, required before the full document APIs below can work. **Use
[SceneDocument.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneDocument.h) unchanged for
the public API, and assemble `SceneDocument.cpp` in this exact order from the
[complete source](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneDocument.cpp):**

1. Its include block, platform includes, JSON alias and all `MAX_*` limits.
2. Private `require`, primitive/vector conversions and transform codec shown
   above; then `encode(TextureInput)`, `textureInput`, `hex`, `unhex`,
   `imageBytes`, and the `finite` overloads. These are the contiguous helpers
   before `replaceFile`. They validate texture inputs, byte shapes and budgets.
3. `replaceFile`, shown completely in section 6; then close the anonymous
   namespace.
4. Inside `namespace pf::scene`, use the production `SceneDocumentAccess`
   declarations `Validate`, `Encode` and `Decode`. Replace the bounded
   `*Hierarchy` checkpoint helpers with those full-format functions.
   Section 6 shows the complete production validator. `Encode` and `Decode`
   retain the hierarchy mechanism and add the supplied mesh, material,
   texture-input, RGBA8-hex and HDR-float loops. No GPU handles enter them.
5. Append section 6's public `SaveSceneDocument` and `LoadSceneDocument`, then
   close `namespace pf::scene`.

The supplied asset codecs are not additional reflection exercise solutions.
They are necessary implementation supplied in full by the linked source;
the chapter's complete hierarchy and transaction mechanisms explain how that
plumbing is owned and published. Do not write the bounded projection as a
version-1 file with missing arrays. The final encoder emits all seven arrays,
including the default material, and the final decoder validates all references.

The next fixture checks this **complete assembled format**, not the bounded
projection. Its two-function public boundary reports failures explicitly:

```cpp
bool SaveSceneDocument(const std::filesystem::path& path,
                       const Scene& scene, std::string& error);
bool LoadSceneDocument(const std::filesystem::path& path,
                       Scene& scene, std::string& error);
```

This complete fixture exercises the hierarchy and camera/light path. Put it
in a CPU test source, with `SceneDocument.cpp` and the scene module linked by
Premake. To finish the textured-mesh/environment extension, use the complete
`fixture()` constructor in [SceneDocumentTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/SceneDocumentTests.cpp):
it builds embedded RGBA bytes, an HDR environment, a textured triangle and two
nodes sharing its mesh. Its `main` reserializes the loaded scene and compares
the entire saved payload, then explicitly compares texture bytes/colour space,
environment floats and rebuilt world transforms. Reproduce those comparisons;
equal node counts alone do not complete that extension.

```cpp
#include "PillowFort/Scene/SceneDocument.h"
#include "PillowFort/Scene/Scene.h"

#include <cmath>
#include <filesystem>
#include <stdexcept>
#include <string>

void CheckSceneDocumentRoundTrip(const std::filesystem::path& path)
{
    using namespace pf::scene;
    const auto require = [](bool value, const std::string& message)
    {
        if (!value) { throw std::runtime_error(message); }
    };

    Scene original;
    const NodeIndex parent = original.AddNode("Parent", ROOT_NODE,
        Transform{ .translation = { 2.0f, 0.0f, 0.0f } });
    const NodeIndex lamp = original.AddNode("Lamp", parent,
        Transform{ .translation = { 0.0f, 1.0f, 0.0f } });
    const uint32_t light = original.AddLight(Light{});
    original.SetLight(lamp, light);
    const NodeIndex eye = original.AddNode("Camera");
    original.SetCamera(eye, original.AddCamera(Camera{}));
    original.SetActiveCamera(eye);
    original.UpdateWorldTransforms();

    std::string error;
    require(SaveSceneDocument(path, original, error), error);
    original.EditLocal(parent).translation.x = 100.0f;

    Scene loaded;
    require(LoadSceneDocument(path, loaded, error), error);
    require(loaded.NodeCount() == original.NodeCount(), "node count changed");
    require(loaded.GetNode(lamp).parent == parent, "light lost its parent");
    require(loaded.GetNode(lamp).light == light, "light assignment changed");
    require(loaded.ActiveCamera() == eye, "active camera changed");
    loaded.UpdateWorldTransforms();
    const glm::vec3 position(loaded.GetNode(lamp).world[3]);
    require(glm::length(position - glm::vec3(2.0f, 1.0f, 0.0f)) < 1e-5f,
        "saved local transforms did not reproduce the world position");
}
```

Give the fixture a path in an existing writable test directory. It intentionally
lets the production API report an unavailable directory or write failure.
The complete document encoder/decoder is in
[SceneDocument.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneDocument.cpp); copying
only this fixture would not implement serialization. Its separation matters:
the serializer owns the format, while the test asks whether authored behavior
survives the format.

</details>


## 6. Publish A Loaded Scene Only After Validation

A valid JSON object can still be an invalid scene: a child may name a missing
parent, two parents may list the same child, or a material may reference a
missing image. Parsing and scene validation are separate gates.

> **Jump:** Transactional loading means retaining the old state until a new
> candidate is complete and valid, then publishing it in one move. It trades
> memory for a clear failure guarantee. The old scene, parsed JSON and candidate
> can coexist; a 256 MiB file limit is not a 256 MiB peak-process-memory cap.

Saving has its own publication point: finish writing a sibling temporary file,
then replace the destination. A failure before replacement leaves the previous
file in place. “Publish” therefore names a concrete commit, not every step of
the work: move a valid CPU candidate into `Scene`, replace a file path, or
activate a finished GPU resource set.

<a id="ch45-transactional-load"></a>

### Attempt CH45-transactional-load: keep the previous usable result

Save a valid fixture. Corrupt a late material reference, duplicate a JSON key,
and make a disconnected cycle in the node graph. Try each load while an
existing scene contains a recognizable sentinel node. Then attempt a save
whose temporary file or replacement cannot be completed.

**Acceptance:** Each malformed document returns a diagnostic, with the previous
CPU scene unchanged. For duplicate keys, insert a repeated key textually
into an otherwise valid saved document and require
`Scene JSON contains a duplicate object key.` Assigning a JSON object key
twice before encoding merely overwrites it. For nesting, add a deeply nested
extra field to that valid payload and require
`Scene JSON exceeds its nesting limit.` These diagnostics prove the intended
parser guards ran; a malformed payload failing an unrelated schema check does
not. Whole-scene checks reject broken references and disconnected cycles. A failed
save preserves the previous destination file; writing directly over it is not
an acceptable failure path. Counts and image arithmetic are checked before
allocating their decoded data.

**Transfer:** A rooted traversal visits no cycle when that cycle is disconnected
from the root. Which additional count/link checks catch it? Explain why a file
rename transaction and a GPU resource activation transaction are separate.

**Checkpoint:** extend the full-format fixture with the corruptions above;
the sentinel and previous saved file must survive. The
[document recipe](SceneDocumentsReference.md#document-build) also runs the
production rejection suite. `ch45-documents` supplies runnable edit/round-trip
and failed-operation checks, not an omission exercise for every schema rule.

<details>
<summary>Hint 1: do not decode into the caller's arrays</summary>

Make `Scene candidate` locally. Decode all arrays into it, validate the graph
and assets, update its derived transforms, then move it into the caller. Error
handling before that move must not modify the caller.

</details>

<details>
<summary>Hint 2: prove both local links and global reachability</summary>

Count incoming child links and compare them against each node's parent. Traverse
from root with a bounded depth, check finite/invertible world transforms, then
require that the visited count equals the complete node count.

</details>

<details>
<summary>Hint 3: make the file publication a separate final step</summary>

Encode and validate before opening an output file. Create a unique sibling
temporary exclusively, write all bytes, flush and close it, then replace the
destination. On failure, clean up that temporary; do not truncate the previous
document first.

</details>

<details>
<summary>Worked solution: bounded parsing, candidate validation and atomic save</summary>

**This is `LoadSceneDocument` in `SceneDocument.cpp`, in `namespace pf::scene`.**
Its private `require` helper throws `std::runtime_error` on a failed condition;
`SceneDocumentAccess::Decode` performs the scene checks and world-transform
update before returning. The function includes the bounded file read and JSON
duplicate-key handling, so parsing cannot silently accept the last duplicate
value:

```cpp
bool LoadSceneDocument(const std::filesystem::path& path, Scene& scene, std::string& error)
{
    error.clear();
    try
    {
        const uint64_t bytes = std::filesystem::file_size(path);
        require(bytes > 0 && bytes <= SCENE_DOCUMENT_MAX_BYTES, "Scene document is empty or exceeds the 256 MiB file limit.");
        std::ifstream input(path, std::ios::binary);
        require(input.is_open(), "Opening scene document failed.");
        std::string payload(static_cast<std::size_t>(bytes), '\0');
        input.read(payload.data(), static_cast<std::streamsize>(payload.size()));
        require(input.gcount() == static_cast<std::streamsize>(payload.size()) && input.peek() == std::char_traits<char>::eof(),
                "Scene document changed or could not be read completely.");
        // Bound JSON nesting before it can exhaust the call stack, and reject
        // duplicate keys instead of silently accepting last-value-wins edits.
        std::vector<std::unordered_set<std::string>> keys;
        auto callback = [&](int depth, Json::parse_event_t event, Json& parsed) {
            require(depth <= 32, "Scene JSON exceeds its nesting limit.");
            if (event == Json::parse_event_t::object_start) { keys.emplace_back(); }
            else if (event == Json::parse_event_t::object_end) { keys.pop_back(); }
            else if (event == Json::parse_event_t::key)
            {
                require(!keys.empty() && keys.back().insert(parsed.get<std::string>()).second,
                        "Scene JSON contains a duplicate object key.");
            }
            return true;
        };
        Scene candidate;
        {
            Json parsed = Json::parse(payload, callback);
            // Do not retain the bounded input buffer while allocating decoded
            // geometry/images. The old scene stays intact until validation ends.
            std::string().swap(payload);
            candidate = SceneDocumentAccess::Decode(parsed);
        }
        scene = std::move(candidate);
        return true;
    }
    catch (const std::exception& exception) { error = exception.what(); return false; }
}
```

**This is the complete production `SceneDocumentAccess::Validate`.** Place it
after that struct's declarations and before `Encode`. It extends the bounded
hierarchy checks with every component and asset relationship; it is the shared
gate for both save and decode:

```cpp
void SceneDocumentAccess::Validate(const Scene& scene)
{
    require(!scene.m_nodes.empty() && scene.m_nodes.size() <= MAX_NODES, "Scene needs a root and at most 100000 nodes.");
    require(!scene.m_materials.empty(), "Scene needs its default material at index zero.");
    for (const std::size_t size : { scene.m_meshes.size(), scene.m_cameras.size(), scene.m_materials.size(),
                                   scene.m_lights.size(), scene.m_textures.size(), scene.m_environments.size() })
    {
        require(size <= MAX_COMPONENTS, "Scene component array exceeds its count limit.");
    }
    std::string propertyError;
    if (!ValidateSceneProperties(scene, propertyError)) { throw std::runtime_error(propertyError); }
    const auto valid = [](uint32_t index, std::size_t count) { return index == NO_COMPONENT || index < count; };
    require(scene.m_nodes[ROOT_NODE].parent == INVALID_NODE, "Scene root must have no parent.");
    std::vector<uint32_t> incoming(scene.m_nodes.size(), 0);
    for (NodeIndex i = 0; i < scene.m_nodes.size(); ++i)
    {
        const Node& node = scene.m_nodes[i];
        require(i == ROOT_NODE || node.parent < scene.m_nodes.size(), "Scene node has an invalid parent.");
        require(valid(node.mesh, scene.m_meshes.size()) && valid(node.camera, scene.m_cameras.size())
                && valid(node.light, scene.m_lights.size()), "Scene node refers to a missing component.");
        for (NodeIndex child : node.children)
        {
            require(child != ROOT_NODE && child < scene.m_nodes.size(), "Scene child index is invalid.");
            require(scene.m_nodes[child].parent == i && ++incoming[child] == 1,
                    "Scene parent/child links disagree or contain duplicate children.");
        }
    }
    for (NodeIndex i = 1; i < incoming.size(); ++i)
    {
        require(incoming[i] == 1, "Every scene node must appear exactly once in its parent's children.");
    }
    struct Visit { NodeIndex node; std::size_t depth; glm::mat4 parent; };
    std::vector<Visit> stack{ { ROOT_NODE, 0, glm::mat4(1) } };
    std::size_t visited = 0;
    while (!stack.empty())
    {
        const Visit visit = stack.back();
        stack.pop_back();
        require(visit.depth <= MAX_HIERARCHY_DEPTH && ++visited <= scene.m_nodes.size(),
                "Scene hierarchy is cyclic or exceeds its depth limit.");
        const Node& node = scene.m_nodes[visit.node];
        const glm::mat4 world = visit.parent * node.local.Matrix();
        require(finite(world) && finite(glm::inverse(world)), "Scene world transform is singular or non-finite.");
        for (NodeIndex child : node.children) { stack.push_back({ child, visit.depth + 1, world }); }
    }
    require(visited == scene.m_nodes.size(), "Scene hierarchy has a cycle or disconnected nodes.");
    require(scene.m_activeCamera == INVALID_NODE || (scene.m_activeCamera < scene.m_nodes.size()
        && scene.m_nodes[scene.m_activeCamera].camera != NO_COMPONENT), "Active camera must name a camera node.");

    std::size_t vertices = 0, indices = 0;
    for (const Mesh& mesh : scene.m_meshes)
    {
        require(mesh.name.size() <= MAX_STRING && !mesh.data.vertices.empty() && !mesh.data.indices.empty()
                && !mesh.data.submeshes.empty(), "Scene mesh is empty or has an oversized name.");
        vertices += mesh.data.vertices.size();
        indices += mesh.data.indices.size();
        require(vertices <= MAX_VERTICES && indices <= MAX_INDICES, "Scene geometry exceeds its total count budget.");
        for (const Vertex& vertex : mesh.data.vertices)
        {
            require(finite(vertex.position) && finite(vertex.normal) && finite(vertex.uv) && finite(vertex.tangent),
                    "Scene mesh vertex is non-finite.");
        }
        for (uint32_t index : mesh.data.indices) { require(index < mesh.data.vertices.size(), "Mesh index refers to a missing vertex."); }
        uint64_t covered = 0;
        for (const Submesh& submesh : mesh.data.submeshes)
        {
            require(submesh.firstIndex == covered && submesh.indexCount > 0 && submesh.indexCount % 3 == 0
                    && covered + submesh.indexCount <= mesh.data.indices.size()
                    && submesh.materialIndex < scene.m_materials.size(), "Submesh range/material is invalid.");
            covered += submesh.indexCount;
        }
        require(covered == mesh.data.indices.size(), "Submeshes must cover every triangle index exactly once.");
    }
    uint64_t decodedBytes = 0;
    for (const TextureImage& image : scene.m_textures)
    {
        const uint64_t expected = imageBytes(image.width, image.height, 1);
        decodedBytes += expected;
        require(image.name.size() <= MAX_STRING && image.pixels.size() == expected, "Texture dimensions/byte count are invalid.");
    }
    for (const EnvironmentImage& image : scene.m_environments)
    {
        const uint64_t expected = imageBytes(image.width, image.height, sizeof(float));
        decodedBytes += expected;
        require(image.name.size() <= MAX_STRING && uint64_t(image.pixels.size()) * sizeof(float) == expected,
                "Environment dimensions/float count are invalid.");
        for (float value : image.pixels) { require(std::isfinite(value), "Environment image contains non-finite values."); }
    }
    require(decodedBytes <= MAX_IMAGE_BYTES, "Combined decoded images exceed the 256 MiB budget.");
    for (const Material& material : scene.m_materials)
    {
        for (const TextureInput* input : { &material.baseColorTexture, &material.emissiveTexture, &material.normalTexture,
            &material.metallicTexture, &material.roughnessTexture, &material.occlusionTexture, &material.opacityTexture })
        {
            require(valid(input->image, scene.m_textures.size()) && static_cast<uint32_t>(input->wrapS) < 4
                    && static_cast<uint32_t>(input->wrapT) < 4 && finite(input->scale) && finite(input->bias)
                    && finite(input->channel), "Material texture input is invalid.");
        }
    }
    for (const Light& light : scene.m_lights)
    {
        require(static_cast<uint32_t>(light.type) <= static_cast<uint32_t>(LightType::Dome)
                && valid(light.environment, scene.m_environments.size()) && finite(light.domeTextureAverage),
                "Light type or environment reference is invalid.");
    }
}
```
Array limits, finite authored values and graph consistency are separate
checks. Image byte arithmetic uses `uint64_t` before allocation; a large pair
of 32-bit dimensions must not wrap into an apparently small budget.

**This is the complete private `replaceFile` helper**, before closing the
anonymous namespace. Use the production include block: `<algorithm>`,
`<atomic>`, `<cerrno>`, `<chrono>`, `<system_error>` and `<utility>`, plus
`<windows.h>` on Windows or `<fcntl.h>` and `<unistd.h>` elsewhere. Its
`require` helper is already defined above it:

```cpp
void replaceFile(const std::filesystem::path& path, const std::string& payload)
{
    static std::atomic<uint64_t> sequence{ 0 };
    std::filesystem::path temporary;
#ifdef _WIN32
    HANDLE file = INVALID_HANDLE_VALUE;
#else
    int file = -1;
#endif
    // Exclusive creation prevents two saves, or a pre-existing sibling, from
    // sharing a temporary file. Rename remains on the destination filesystem.
    for (int attempt = 0; attempt < 16; ++attempt)
    {
        temporary = path;
        const auto tick = std::chrono::steady_clock::now().time_since_epoch().count();
        temporary += ".tmp." + std::to_string(tick) + "." + std::to_string(sequence.fetch_add(1));
#ifdef _WIN32
        file = CreateFileW(temporary.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file != INVALID_HANDLE_VALUE) { break; }
        const DWORD code = GetLastError();
        if (code != ERROR_FILE_EXISTS && code != ERROR_ALREADY_EXISTS)
        {
            throw std::system_error(static_cast<int>(code), std::system_category(), "Creating scene temporary file");
        }
#else
        file = ::open(temporary.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (file >= 0) { break; }
        if (errno != EEXIST) { throw std::system_error(errno, std::generic_category(), "Creating scene temporary file"); }
#endif
    }
#ifdef _WIN32
    require(file != INVALID_HANDLE_VALUE, "Could not allocate a unique scene temporary file.");
#else
    require(file >= 0, "Could not allocate a unique scene temporary file.");
#endif
    try
    {
        std::size_t written = 0;
        while (written < payload.size())
        {
#ifdef _WIN32
            DWORD count = 0;
            const DWORD chunk = static_cast<DWORD>(std::min<std::size_t>(payload.size() - written, 1024 * 1024));
            if (!WriteFile(file, payload.data() + written, chunk, &count, nullptr) || count == 0)
            {
                throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), "Writing scene temporary file");
            }
#else
            const auto count = ::write(file, payload.data() + written, payload.size() - written);
            if (count < 0 && errno == EINTR) { continue; }
            if (count <= 0) { throw std::system_error(errno, std::generic_category(), "Writing scene temporary file"); }
#endif
            written += static_cast<std::size_t>(count);
        }
#ifdef _WIN32
        if (!FlushFileBuffers(file))
        {
            throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), "Flushing scene temporary file");
        }
        const BOOL closed = CloseHandle(file);
        file = INVALID_HANDLE_VALUE;
        if (!closed) { throw std::runtime_error("Closing scene temporary file failed."); }
        if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        {
            throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), "Replacing scene file");
        }
#else
        if (::fsync(file) != 0) { throw std::system_error(errno, std::generic_category(), "Flushing scene temporary file"); }
        const int closed = ::close(file);
        file = -1;
        if (closed != 0) { throw std::runtime_error("Closing scene temporary file failed."); }
        std::filesystem::rename(temporary, path);
#endif
    }
    catch (...)
    {
#ifdef _WIN32
        if (file != INVALID_HANDLE_VALUE) { CloseHandle(file); }
#else
        if (file >= 0) { ::close(file); }
#endif
        std::error_code ignored;
        std::filesystem::remove(temporary, ignored);
        throw;
    }
}
```

**This is the public save operation**, after those helpers:

```cpp
bool SaveSceneDocument(const std::filesystem::path& path, const Scene& scene, std::string& error)
{
    error.clear();
    try
    {
        require(!path.empty() && path.has_filename(), "Scene document path needs a filename.");
        SceneDocumentAccess::Validate(scene);
        const std::string payload = SceneDocumentAccess::Encode(scene).dump(2) + '\n';
        require(payload.size() <= SCENE_DOCUMENT_MAX_BYTES, "Scene document exceeds the 256 MiB file limit.");
        replaceFile(path, payload);
        return true;
    }
    catch (const std::exception& exception) { error = exception.what(); return false; }
}
```

`replaceFile` owns the platform-specific file transaction. On Windows it uses
exclusive `CreateFileW(..., CREATE_NEW, ...)`, loops over partial writes,
checks `FlushFileBuffers` and `CloseHandle`, then calls `MoveFileExW` with
`MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH`. Its exception cleanup
closes an open handle and removes only its own temporary. The temporary is a
sibling of the destination so replacement stays on that filesystem. This
protects the previous file on the function's failure paths; it is not a claim
of power-loss durability on every filesystem or storage device.

The full graph/asset checks, primitive conversions, encoder, decoder and
cross-platform replacement helper are in
[SceneDocument.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Scene/SceneDocument.cpp). They are
part of the solution: the chapter has shown the mechanisms and their exact
placement without reproducing the entire multi-component format listing.
[SceneDocumentTests.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/SceneDocumentTests.cpp)
checks those production functions with valid and deliberately malformed data.

</details>

# Part 3 — Bring The Edited Scene Back To The Viewer

The CPU stopping point is a document that round-trips and preserves the old
scene or file on failure. Run those checks before adding renderer lifetime
management. This part connects that tested CPU boundary to the viewer.

## 7. Replace The Renderer At A Safe Boundary

CPU properties and GPU resources have different lifetimes. A changed transform,
camera or light follows its normal per-frame path. A material has persistent
GPU copies, while loading a different scene can replace meshes, images and
descriptors together. The viewer owns that activation boundary.

<a id="ch45-gpu-activation"></a>

### Attempt CH45-gpu-activation: activate an edited or loaded scene safely

Add **Scene document** controls to the USD viewer. Save an imported scene,
change a translation and material, and reload. Make the pending material change
visible before choosing **Apply material changes**. Also open an invalid
document while the current scene is usable. Decide which resources must stop
being read before rebuilding them and what CPU state survives failure.

**Acceptance:** A failed CPU load retains the current scene. A valid load
rebuilds from the new CPU data after all shared GPU users are finished. A
material edit is saved even while its GPU update is pending; Apply updates the
rendered material. Setup after MSAA changes does not reimport over edits.
`INVALID_NODE` as the document's active camera is valid and the viewer adds a
framing camera. Failed **scene replacement** attempts to restore the previous
CPU scene's resources. Failed **material Apply** retains the edited CPU scene
and reports the rebuild error; it does not restore older material values.
An unsuccessful rebuild or recovery can leave a clear-only view.

**Transfer:** Why does waiting for only the current frame's fence fail to
protect a material buffer shared with another frame slot? What ownership and
retirement changes would be needed before asynchronous replacement could avoid
a whole-device wait?

**Attended checkpoint:** use the [viewer recipe](SceneDocumentsReference.md#viewer-run)
after CPU checks pass. Save a small scene, edit it, load the saved copy, then
try malformed input; that CPU-load failure must retain the previous usable
view. Check material Apply and scene-replacement recovery separately using
their acceptance contracts above. Run this separately from CPU builds.

<details>
<summary>Hint 1: separate CPU loading from activation</summary>

Load into a local scene first. Preserve the current CPU scene while attempting
to activate its replacement. The format loader does not know about Vulkan.

</details>

<details>
<summary>Hint 2: protect every frame that can read shared resources</summary>

Material buffers and descriptors are shared across frame slots. A controlled
device-idle boundary is sufficient here; a single slot's fence is not. Reuse
the viewer's existing Teardown/Setup lifecycle after that boundary.

</details>

<details>
<summary>Hint 3: retain the state needed to reconstruct either view</summary>

Keep the previous CPU scene and latest target description. Rebuild the selected
scene, including Resize, and if that fails restore the previous CPU scene and
try again. Prevent Setup from reimporting just because a valid document has no
geometry. Keep document status and editor state on the CPU side of Teardown.

</details>

<details>
<summary>Worked solution: load, rebuild and recover through one viewer boundary</summary>

**In `UsdViewerDemo.h`, inside the existing class's private section, add these
method declarations and members.** The header gains `<array>` if not already
present. `SceneTargets` comes from Chapter 9's existing demo headers:

```cpp
bool ReplaceScene(scene::Scene loaded);
bool RebuildSceneResources();
void DrawDocumentPanel();

std::array<char, 1024> m_documentPath{};
std::string m_documentStatus;
bool m_imported = false;
vulkan_graphics::SceneTargets m_targets{};
scene::NodeIndex m_domeNode = scene::INVALID_NODE;
```

Reuse existing `m_scene`, `m_editor`, `m_context`, `m_ready`, `m_status`,
`m_controls`, `m_controlledCamera`, `m_selectedFile` and the file/path arrays;
do not add duplicates. The assembled viewer already has the target cache and
dome marker from Chapters 22/23. A reader arriving from 19 adds them here.
The marker is just a CPU node index in this chapter; sky GPU resources remain
outside this bridge.

**`UsdViewerDemo.cpp` gains `SceneDocument.h` and `VulkanResources.h`.** The
three methods below also use its existing logging, `InitializationResult`,
`toUtf8`, `addCameraIfMissing`, ImGui, `<filesystem>`, `<string_view>` and
`<utility>`. `requireSafeDeviceIdle` is Chapter 8's resource-lifetime helper;
include its declaring header directly rather than relying on a transitive one.
Keep Chapter 14's file-scope `toUtf8` and `addCameraIfMissing` above the namespace.

Initialize the path in the constructor; it still performs no fallible work:

```cpp
UsdViewerDemo::UsdViewerDemo(std::string startFile)
    : m_startFile(std::move(startFile))
{
    m_controls.active = scene::ControllerKind::Orbit;
    std::snprintf(m_documentPath.data(), m_documentPath.size(), "%s", "scene.pfscene");
}
```
**Replace Setup's scene-size-based import condition with this explicit import
flag block.** Keep the renderer initialization before it and the existing
mesh/texture/material uploads after it. A valid empty document must not trigger
another USD import during resource reconstruction:

```cpp
    if (!m_imported)
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
        m_imported = true;
    }
```
At the successful end of `Setup`, set `m_editor.editMaterials = true` and
`m_ready = true` before returning success. **At the start of the existing
`Resize`, assign `m_targets = targets`**, then retain that chapter's existing
resize behavior. Rebuild needs the latest borrowed target description. In
`Teardown`, clear `m_ready` and `m_domeNode`; retain the CPU scene, import flag,
document path/status and authored edits.

**Add these three complete methods inside `namespace pf::demos::usd_viewer`,
after `SwitchToFile` and before `Update`:**

```cpp
bool UsdViewerDemo::RebuildSceneResources()
{
    // Material buffers/descriptors are shared by both frame slots. Wait for both
    // before replacing any resource; a single frame fence is insufficient.
    if (vulkan_graphics::requireSafeDeviceIdle(m_context.vulkan.device, "rebuilding scene resources") != VK_SUCCESS)
    {
        m_status = "Cannot safely rebuild scene resources; the device did not become idle.";
        Log::error(m_status.c_str());
        m_ready = false;
        m_domeNode = scene::INVALID_NODE;
        return false;
    }
    Teardown();
    InitializationResult result = Setup(m_context);
    if (result) { result = Resize(m_targets); }
    if (!result)
    {
        Log::error(result.message());
        m_status = result.message();
        m_ready  = false;   // Record then only clears, as after a failed Setup
    }
    return static_cast<bool>(result);
}

bool UsdViewerDemo::ReplaceScene(scene::Scene loaded)
{
    addCameraIfMissing(loaded);
    loaded.UpdateWorldTransforms();
    scene::Scene previous = std::move(m_scene);
    m_scene = std::move(loaded);
    m_imported = true;
    m_controls.ReleaseAll();
    m_controlledCamera = scene::INVALID_NODE;
    m_editor = {};
    m_status.clear();
    if (RebuildSceneResources()) { return true; }

    const std::string failure = m_status;
    m_scene = std::move(previous);
    // Keep the authored CPU document even when GPU allocation fails. Recover
    // the old uploads when the device still permits it, otherwise Record clears.
    const bool recovered = RebuildSceneResources();
    m_status = "Scene load failed: " + failure + (recovered ? " Previous scene restored." : " GPU recovery also failed.");
    return false;
}

void UsdViewerDemo::DrawDocumentPanel()
{
    ImGui::SetNextItemOpen(true, ImGuiCond_Once);
    if (!ImGui::CollapsingHeader("Scene document")) { return; }
    ImGui::InputText("Document path", m_documentPath.data(), m_documentPath.size());
    ImGui::TextWrapped("Self-contained .pfscene file. Relative paths use the working directory.");
    const std::string_view pathText(m_documentPath.data());
    const std::filesystem::path path(std::u8string(pathText.begin(), pathText.end()));
    if (ImGui::Button("Save scene"))
    {
        std::string error;
        m_documentStatus = scene::SaveSceneDocument(path, m_scene, error)
            ? "Scene saved to " + toUtf8(path) : error;
    }
    if (ImGui::Button("Load scene"))
    {
        scene::Scene loaded;
        std::string error;
        if (!scene::LoadSceneDocument(path, loaded, error)) { m_documentStatus = error; }
        else if (ReplaceScene(std::move(loaded)))
        {
            m_selectedFile = -1;
            m_documentStatus = "Scene loaded.";
        }
        else { m_documentStatus = m_status; }
    }
    if (ImGui::Button("Apply material changes"))
    {
        m_documentStatus = RebuildSceneResources() ? "Material resources updated." : m_status;
        m_editor.materialsChanged = !m_ready;
    }
    if (m_editor.materialsChanged) { ImGui::TextWrapped("Material edits are pending. Apply to update the rendered scene."); }
    if (!m_documentStatus.empty()) { ImGui::TextWrapped("%s", m_documentStatus.c_str()); }
}
```
A single frame's fence does not protect resources shared by both slots. This
implementation waits for the whole device before Teardown. It is deliberately
coarse; incremental uploads would require explicit replacement and retirement
ownership. If recovery also fails, the CPU document remains available while
`m_ready == false` makes `Record` clear instead of issuing invalid draws.

**Replace Chapter 14's `SwitchToFile` body with this same activation path:**

```cpp
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

    if (ReplaceScene(std::move(loaded))) { m_selectedFile = index; }
}
```
**At the beginning of the existing `DrawPanel` panel body**, immediately after
its successful `beginDemoPanel`, insert:

```cpp
DrawDocumentPanel();
```

The loaded document is not necessarily in the scanned file list, so use the
following guarded label for that existing File combo instead of indexing `-1`:

```cpp
const char* current = m_selectedFile >= 0 && static_cast<size_t>(m_selectedFile) < m_files.size()
    ? m_files[static_cast<size_t>(m_selectedFile)].c_str() : "(scene document)";
```

For command-line reopening and the File picker, **extend `FindFiles`' existing
extension filter to include `.pfscene`**, alongside its USD extensions:

```cpp
if (entry.is_regular_file() &&
    (extension == ".usda" || extension == ".usdc" || extension == ".usdz" ||
     extension == ".usd" || extension == ".pfscene"))
{
    found.emplace_back(toUtf8(entry.path().filename()), entry.path());
}
```

**Replace the file-scope `loadScene` helper**, above the namespace, with this
document-aware version. Camera framing stays in the viewer rather than becoming
a document-format requirement:

```cpp
static InitializationResult loadScene(const std::filesystem::path& file, pf::scene::Scene& scene)
{
    if (file.extension() == ".pfscene")
    {
        std::string error;
        if (!pf::scene::LoadSceneDocument(file, scene, error)) { return InitializationResult::failure(error); }
    }
    else if (auto result = pf::usd_import::ImportUsdFile(file, scene); !result) { return result; }
    addCameraIfMissing(scene);
    scene.UpdateWorldTransforms();
    return InitializationResult::success();
}
```
### Attended Viewer Checkpoint

After a successful build, open the USD viewer using the
[viewer command](SceneDocumentsReference.md#viewer-run) and
choose Cornell Box or another small scene with a material. Select a node,
save under **Scene document**, then edit its translation through **Reflected
properties**. Its child follows. Edit a nested material: the pending message
appears; **Apply material changes** updates the image and clears the pending
state. Saving before Apply still retains the CPU material edit.

Use **Load scene** to recover the saved values, then try a malformed copy.
Expect a diagnostic and the previous usable scene. Change MSAA, then verify
that edits survive resource reconstruction. Reopen the `.pfscene` through
`--scene` and verify that a document without an active camera receives a
viewer camera. Run builds and GPU checks serially with the repository's memory
guards; an existing interactive preview stays open until its user closes it.

The path is relative to the working directory, and its parent must exist when
saving. This is an engine-owned project file; it does not write edits back to
the source USD stage. No shoreline GPU history, FFT state or procedural island
configuration is implied by the saved scene.

</details>

## 8. Exit Check

Use the [checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md)
for supplied Starter/Solution sources, or the
[complete build reference](SceneDocumentsReference.md#build-the-listings)
for listings you assemble yourself. Keep their results separate:

| Check | What must pass |
| --- | --- |
| Binding | Real member read/write and wrong-type rejection |
| Checked scene edit | Validated commit, descendant transforms and rejected edits unchanged |
| Hierarchy codec | Ordered references and rebuilt world position `(2,1,0)` |
| Complete document | Authored data round trip, malformed-input rejection and failed-operation preservation |
| Attended viewer | Widget behavior, material publication, saved-scene activation and recovery |

CPU success establishes data/state behavior. The
[viewer recipe](SceneDocumentsReference.md#viewer-run) is a separate attended
check with the same serial builds and resource guards. Record the configuration,
fixture and actual result; the reference evidence covers only checks that ran.

Before calling the feature complete, explain these decisions without looking
at the implementation:

- Which one registration determines a reflected field's key, value type and
  read/write access? Why is validation still owner-specific?
- Why does a successful node transform commit go through `EditLocal`, and why
  must a rejected commit avoid it?
- Which scene values belong in the versioned file but are absent from the
  reflected scalar property set? Which derived values are rebuilt?
- What are the separate publication points for a CPU load, a file save and
  GPU activation? What previous state survives each failure?

Persistent cross-document IDs, undo/redo, collection/reference editors, custom
component registration and schema migrations remain subsequent design work.
The next useful extension is driven by a concrete consumer of those contracts,
not by making every runtime field appear in the default inspector.


### Maintaining The Interface

Keep the work needed for new capabilities explicit:

| Change | Required maintenance |
| --- | --- |
| Another editable field on an existing owner | Add one binding; update owner validation and decide explicitly whether the versioned document encodes/decodes it |
| Another value type | Extend `PropertyValue`, `PropertyType`/its type mapping and widget support; provide document codecs if persisted |
| Another owner/component type | Extend `PropertyTarget`, target-count and read/write dispatch, commit rules and validation; then define its document/reference ownership |

One registration removes duplicate field metadata and access lists. It does
not make a new value type, owner, undo transaction or persistent identity a
one-line feature. A generator could produce the same tables later while
preserving this checked consumer interface.

Next on the graphics route: return to [20 — Compute Fundamentals](20-Compute-Fundamentals.md),
or choose another path in the [series routes](../VulkanTutorial.md#routes).
[Chapter 46](46-Capturing-Grass-Clumps.md) continues the separate grass route
after 27 and 41; it does not follow from scene documents.
