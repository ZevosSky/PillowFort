workspace "PillowFort"
    architecture "x86_64"
    location "Build/Projects"
    startproject "SandboxGame"
    configurations { "Debug", "Release", "Dist" }

outputdir = "%{cfg.buildcfg}-%{cfg.system}-%{cfg.architecture}"

local vulkanSDK = os.getenv("VULKAN_SDK")
if not vulkanSDK then
    error("VULKAN_SDK is not set. Install the Vulkan SDK and open a new shell.")
end

-- Settings shared by every target we write ourselves.
local function apply_common_cpp_settings()
    language "C++"
    cppdialect "C++20"
    staticruntime "Off"
    warnings "Extra"

    targetdir ("Build/Artifacts/%{cfg.buildcfg}/%{prj.name}")
    objdir ("Build/Intermediate/" .. outputdir .. "/%{prj.name}")

    includedirs
    {
        "Source",
        "Shaders/Include",               -- headers shared with GLSL (tutorial chapter 08)
        vulkanSDK .. "/Include"          -- vulkan/, vma/, glm/ all live here
    }

    libdirs { vulkanSDK .. "/Lib" }
    links   { "vulkan-1" }

    -- Every GLM switch lives here, once, and never as a #define above an
    -- include: GLM's templates and even its vector layouts change with these,
    -- so two files that disagree produce two definitions of one function or type
    -- and the linker silently keeps one (tutorial chapter 06 section 2).
    -- GLM_ENABLE_EXPERIMENTAL: glm/gtx/* hard-errors without it. Camera uses the
    -- single-argument glm::translate/rotate, which live only in gtx/transform.
    -- GLM_FORCE_DEPTH_ZERO_TO_ONE: Vulkan's [0, 1] depth for glm::perspective.
    defines { "GLM_ENABLE_EXPERIMENTAL", "GLM_FORCE_DEPTH_ZERO_TO_ONE" }

    filter "system:windows"
        systemversion "latest"
        defines { "NOMINMAX", "WIN32_LEAN_AND_MEAN" }

    filter "configurations:Debug"
        defines { "PF_DEBUG", "PF_VULKAN_VALIDATION" }
        symbols "On"

    filter "configurations:Release"
        defines "PF_RELEASE"
        optimize "Speed"

    filter "configurations:Dist"
        defines "PF_DIST"
        optimize "Speed"
        symbols "Off"

    filter {}
end

-- Vendor code is not ours to warn about.
local function apply_vendor_settings()
    warnings "Off"
    targetdir ("Build/Artifacts/%{cfg.buildcfg}/%{prj.name}")
    objdir ("Build/Intermediate/" .. outputdir .. "/%{prj.name}")

    filter "system:windows"
        systemversion "latest"
    filter "configurations:Debug"
        symbols "On"
    filter "configurations:Release"
        optimize "Speed"
    filter {}
end

-- Every Name.vert.glsl, Name.frag.glsl, and Name.comp.glsl under Shaders/ is
-- compiled to a mirrored .spv beside the executable (ROADMAP step 7, tutorial
-- chapter 06). The stage comes from the name and is passed explicitly, because
-- glslc cannot infer it from .glsl. Any other .glsl is an include. Like the C++
-- globs, this runs at generation time: rerun GenerateProjects.bat after adding
-- a shader.
local shaderStages = { vert = "vertex", frag = "fragment", comp = "compute" }

-- Builds the prebuild command list for one set of glslc flags.
local function shaderCommands(flags)
    local commands = {}
    for _, file in ipairs(os.matchfiles("Shaders/**.glsl")) do
        local path  = file:match("^Shaders/(.*)%.glsl$")      -- "Triangle/Triangle.vert"
        local stage = shaderStages[path:match("%.(%a+)$")]    -- "vertex"
        if stage then
            local folder = path:match("^(.*)/") or "."
            table.insert(commands, '{MKDIR} "%{cfg.targetdir}/Shaders/' .. folder .. '"')
            table.insert(commands,
                '"$(VULKAN_SDK)/Bin/glslc.exe" -fshader-stage=' .. stage ..
                ' --target-env=vulkan1.3 ' .. flags ..
                ' -I "%{wks.location}/../../Shaders/Include"' ..
                ' "%{wks.location}/../../Shaders/' .. path .. '.glsl"' ..
                ' -o "%{cfg.targetdir}/Shaders/' .. path .. '.spv"')
        end
    end
    return commands
end

project "GLFW"
    kind "StaticLib"
    language "C"
    cdialect "C11"
    apply_vendor_settings()

    files
    {
        "Vendor/GLFW/include/GLFW/glfw3.h",
        "Vendor/GLFW/include/GLFW/glfw3native.h",
        "Vendor/GLFW/src/internal.h",
        "Vendor/GLFW/src/platform.h",
        "Vendor/GLFW/src/mappings.h",
        "Vendor/GLFW/src/context.c",
        "Vendor/GLFW/src/init.c",
        "Vendor/GLFW/src/input.c",
        "Vendor/GLFW/src/monitor.c",
        "Vendor/GLFW/src/platform.c",
        "Vendor/GLFW/src/vulkan.c",
        "Vendor/GLFW/src/window.c",
        "Vendor/GLFW/src/egl_context.c",
        "Vendor/GLFW/src/osmesa_context.c",
        "Vendor/GLFW/src/null_init.c",
        "Vendor/GLFW/src/null_monitor.c",
        "Vendor/GLFW/src/null_window.c",
        "Vendor/GLFW/src/null_joystick.c"
    }

    filter "system:windows"
        files
        {
            "Vendor/GLFW/src/win32_init.c",
            "Vendor/GLFW/src/win32_module.c",
            "Vendor/GLFW/src/win32_joystick.c",
            "Vendor/GLFW/src/win32_monitor.c",
            "Vendor/GLFW/src/win32_time.c",
            "Vendor/GLFW/src/win32_thread.c",
            "Vendor/GLFW/src/win32_window.c",
            "Vendor/GLFW/src/wgl_context.c"
        }
        defines { "_GLFW_WIN32", "_CRT_SECURE_NO_WARNINGS" }
    filter {}

project "ImGui"
    kind "StaticLib"
    language "C++"
    cppdialect "C++20"
    apply_vendor_settings()

    files
    {
        "Vendor/ImGui/imgui.cpp",
        "Vendor/ImGui/imgui_draw.cpp",
        "Vendor/ImGui/imgui_tables.cpp",
        "Vendor/ImGui/imgui_widgets.cpp",
        "Vendor/ImGui/imgui_demo.cpp",
        "Vendor/ImGui/backends/imgui_impl_glfw.cpp",
        "Vendor/ImGui/backends/imgui_impl_vulkan.cpp"
    }

    includedirs
    {
        "Vendor/ImGui",
        "Vendor/ImGui/backends",
        "Vendor/GLFW/include",
        vulkanSDK .. "/Include"
    }

project "PillowFortEngine"
    kind "StaticLib"
    apply_common_cpp_settings()

    files
    {
        "Source/PillowFort/**.h",
        "Source/PillowFort/**.hpp",
        "Source/PillowFort/**.c",
        "Source/PillowFort/**.cpp"
    }

    includedirs
    {
        "Vendor/GLFW/include",
        "Vendor/ImGui",
        "Vendor/ImGui/backends"
    }

project "SandboxGame"
    kind "ConsoleApp"
    apply_common_cpp_settings()

    files
    {
        "Source/SandboxGame/**.h",
        "Source/SandboxGame/**.hpp",
        "Source/SandboxGame/**.c",
        "Source/SandboxGame/**.cpp"
    }

    -- main() includes engine headers that include GLFW, and once ImGui is up it
    -- calls ImGui and its GLFW backend directly. Linking the libraries is not
    -- enough; the compiler needs their headers too.
    includedirs
    {
        "Vendor/GLFW/include",
        "Vendor/ImGui",
        "Vendor/ImGui/backends"
    }

    links { "PillowFortEngine", "GLFW", "ImGui" }

    filter "configurations:Debug"
        prebuildcommands(shaderCommands("-g -O0"))   -- readable GLSL in RenderDoc
    filter "configurations:not Debug"
        prebuildcommands(shaderCommands("-O"))
    filter {}

-- Editor export is separate from the build definition and follows the target OS.
dofile("Scripts/VSCode.lua")
