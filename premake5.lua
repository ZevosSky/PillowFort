workspace "PillowFort"
    architecture "x86_64"
    location "Build/Projects"
    startproject "SandboxGame"
    configurations
    {
        "Debug",
        "Release",
        "Dist"
    }

outputdir = "%{cfg.buildcfg}-%{cfg.system}-%{cfg.architecture}"

/*

*/
local function apply_common_cpp_settings()
    language "C++"
    cppdialect "C++20"
    staticruntime "Off"
    warnings "Extra"

    targetdir ("Build/Artifacts/%{cfg.buildcfg}/%{prj.name}")
    objdir ("Build/Intermediate/" .. outputdir .. "/%{prj.name}")

    includedirs
    {
        "Source"
    }

    filter "system:windows"
        systemversion "latest"
        defines
        {
            "NOMINMAX",
            "WIN32_LEAN_AND_MEAN"
        }

    filter "configurations:Debug"
        defines "PF_DEBUG"
        symbols "On"

    filter "configurations:Release"
        defines "PF_RELEASE"
        optimize "Speed"

    filter {}
end

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

    links
    {
        "PillowFortEngine"
    }
