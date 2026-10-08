-- Editor settings only: this does not alter the projects or the Linux harness.
newoption {
    trigger = "linux-harness",
    description = "Match the Linux TutorialHarness shims and Debug define (vscode only)"
}
newoption {
    trigger = "linux-harness-dir",
    value = "path",
    description = "Use a root-relative or absolute external TutorialHarness directory (vscode only)"
}

local harnessMode = _OPTIONS["linux-harness"] or _OPTIONS["linux-harness-dir"]
if harnessMode and (_ACTION ~= "vscode" or os.target() ~= "linux") then
    error("--linux-harness requires the vscode action targeting Linux.")
end

local architectures = { x86_64 = "x64", x86 = "x86", ARM = "arm", AARCH64 = "arm64" }
local compilerCache = {}

local function find_msvc_compiler(cfg)
    local vswhere = path.join(os.getenv("ProgramFiles(x86)") or "",
        "Microsoft Visual Studio/Installer/vswhere.exe")
    if not os.isfile(vswhere) then return nil end
    local output = os.outputof('""' .. vswhere ..
        '" -latest -version "[17.0,18.0)" -products *' ..
        ' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64' ..
        ' -property installationPath"') or ""
    local installation = output:match("([^\r\n]+)")
    if not installation then return nil end
    local versionFile = io.open(path.join(installation,
        "VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt"), "r")
    if not versionFile then return nil end
    local version = (versionFile:read("*l") or ""):match("^%s*(.-)%s*$")
    versionFile:close()
    local candidate = path.join(installation,
        "VC/Tools/MSVC/" .. version .. "/bin/Hostx64/" .. architectures[cfg.architecture] .. "/cl.exe")
    if version ~= "" and os.isfile(candidate) then
        return path.translate(candidate, "/")
    end
end

local function find_compiler(cfg, tools, language)
    local name = tools.gettoolname(cfg, language)
    if os.host() ~= cfg.system then return name end
    local key = cfg.system .. "/" .. cfg.architecture .. "/" .. name
    if compilerCache[key] then return compilerCache[key] end
    if tools == premake.tools.msc then
        compilerCache[key] = find_msvc_compiler(cfg) or name
        return compilerCache[key]
    end
    local executable = name
    if cfg.system == "windows" and path.getextension(executable) ~= ".exe" then
        executable = executable .. ".exe"
    end
    local directory = os.pathsearch(executable, os.getenv("PATH") or "")
    if directory and directory ~= "" then
        compilerCache[key] = path.translate(path.join(directory, executable), "/")
    else
        compilerCache[key] = name
    end
    return compilerCache[key]
end

local function is_vendor(cfg)
    if cfg.warnings == "Off" then return true end
    for _, node in ipairs(cfg.project._.files) do
        if not path.getrelative(cfg.workspace.basedir, node.abspath):match("^Vendor/") then
            return false
        end
    end
    return true
end

local function settings(cfg, harnessDir, isC)
    local tools, version = premake.tools.canonical(cfg.toolset)
    local kind = tools == premake.tools.msc and "msvc"
        or tools == premake.tools.gcc and "gcc" or tools == premake.tools.clang and "clang"
    local architecture = architectures[cfg.architecture]
    if (cfg.system ~= "windows" and cfg.system ~= "linux") or not architecture
        or not kind or (kind == "msvc" and (cfg.system ~= "windows" or (version and version ~= "v143"))) then
        error("Unsupported VS Code target: " .. tostring(cfg.system) .. "/" ..
            tostring(cfg.architecture) .. "/" .. tostring(cfg.toolset))
    end
    local defs = table.arraycopy(cfg.defines)
    local includes = table.arraycopy(cfg.includedirs)
    local flags = table.join(isC and tools.getcflags(cfg) or tools.getcxxflags(cfg), cfg.buildoptions)
    if kind == "msvc" then
        local runtime = premake.config.getruntime(cfg)
        if (runtime and runtime:find("Debug$")) or table.contains(flags, "/MDd") or table.contains(flags, "/MTd") then
            table.insert(defs, "_DEBUG")
        end
        if cfg.characterset == "Unicode" or cfg.characterset == "Default" then
            table.insert(defs, "UNICODE")
            table.insert(defs, "_UNICODE")
        elseif cfg.characterset == "MBCS" then
            table.insert(defs, "_MBCS")
        end
    end
    if harnessDir and not is_vendor(cfg) then
        table.insert(includes, path.join(harnessDir, "shims"))
        if cfg.buildcfg == "Debug" then table.insert(defs, "_DEBUG") end
    end
    return { compiler = find_compiler(cfg, tools, isC and "cc" or "cxx"), flags = flags,
        defines = defs, includes = includes, mode = cfg.system .. "-" .. kind .. "-" .. architecture,
        msvc = kind == "msvc" }
end

-- Premake file configurations contain only per-file settings; merge them over
-- the baked project configuration, preserving each project's own include list.
local function file_settings(cfg, filecfg)
    return setmetatable({}, { __index = function(_, key)
        local value = filecfg[key]
        if value == nil then return cfg[key] end
        local field = premake.field.get(key)
        if field and premake.field.merges(field) then
            return premake.field.merge(field, table.deepcopy(cfg[key] or {}), value)
        end
        return value
    end })
end

local function arguments(cfg, source, state)
    local args = table.join({ state.compiler }, state.flags)
    local function add(flag, values)
        for _, value in ipairs(values) do table.insert(args, flag); table.insert(args, value) end
    end
    add(state.msvc and "/D" or "-D", state.defines)
    add(state.msvc and "/U" or "-U", cfg.undefines)
    add(state.msvc and "/I" or "-I", state.includes)
    add(state.msvc and "/external:I" or "-isystem", cfg.externalincludedirs)
    add(state.msvc and "/FI" or "-include", cfg.forceincludes)
    if not state.msvc then add("-idirafter", cfg.includedirsafter) end
    table.insert(args, state.msvc and "/c" or "-c")
    table.insert(args, source)
    return args
end

local function write_json(filename, value)
    os.mkdir(path.getdirectory(filename))
    local file, message = io.open(filename, "w")
    if not file then error(message) end
    file:write(json.encode_pretty(value), "\n")
    file:close()
end

local function generate_vscode_settings(wks)
    local harnessDir
    if harnessMode then
        harnessDir = path.getabsolute(_OPTIONS["linux-harness-dir"] or "Tests/TutorialHarness", wks.basedir)
        if not os.isfile(path.join(harnessDir, "shims/windows.h")) then
            error("Linux harness directory is missing shims/windows.h: " .. harnessDir)
        end
    end
    local fallback = premake.workspace.findproject(wks, "PillowFortEngine")
    if not fallback then error("VS Code settings require the PillowFortEngine project.") end
    local configurations, databases = {}, {}
    for cfg in premake.project.eachconfig(fallback) do
        local state = settings(cfg, harnessDir, false)
        local filename = path.join(wks.basedir, "Build/IntelliSense", cfg.buildcfg, "compile_commands.json")
        databases[cfg.buildcfg] = { filename = filename, entries = {} }
        table.insert(configurations, { name = cfg.buildcfg, compilerPath = state.compiler,
            compilerArgs = state.flags, intelliSenseMode = state.mode, cppStandard = cfg.cppdialect:lower(),
            includePath = table.join(state.includes, cfg.externalincludedirs), defines = state.defines,
            compileCommands = "${workspaceFolder}/Build/IntelliSense/" .. cfg.buildcfg .. "/compile_commands.json" })
    end
    for prj in premake.workspace.eachproject(wks) do
        if prj.language == "C" or prj.language == "C++" then
            for cfg in premake.project.eachconfig(prj) do
                local database = databases[cfg.buildcfg]
                if database and not (harnessDir and prj.name == "GLFW") then
                    for _, node in ipairs(prj._.files) do
                        local ext = path.getextension(node.abspath):lower()
                        local fcfg = premake.fileconfig.getconfig(node, cfg)
                        if (ext == ".c" or ext == ".cpp" or ext == ".cc" or ext == ".cxx") and fcfg
                            and not fcfg.excludefrombuild and fcfg.buildaction ~= "None"
                            and fcfg.buildaction ~= "Copy" and not premake.fileconfig.hasCustomBuildRule(fcfg) then
                            local effective = file_settings(cfg, fcfg)
                            local isC = effective.compileas == "C" or (effective.compileas ~= "C++" and ext == ".c")
                            local state = settings(effective, harnessDir, isC)
                            table.insert(database.entries, { file = node.abspath, directory = wks.basedir,
                                arguments = arguments(effective, node.abspath, state) })
                        end
                    end
                end
            end
        end
    end
    -- Resolve and validate every configuration before replacing generated files.
    for _, database in pairs(databases) do
        table.sort(database.entries, function(a, b) return a.file < b.file end)
        write_json(database.filename, #database.entries > 0 and database.entries or json.decode("[]"))
    end
    write_json(path.join(wks.basedir, ".vscode/c_cpp_properties.json"), { configurations = configurations, version = 4 })
    print("Generated VS Code settings and Debug, Release, Dist compilation databases")
end

newaction {
    trigger = "vscode",
    description = "Generate VS Code C/C++ IntelliSense settings only",
    valid_kinds = { "StaticLib", "ConsoleApp" },
    valid_languages = { "C", "C++" },
    valid_tools = { cc = { "gcc", "clang", "msc" } },
    toolset = os.target() == "windows" and "msc-v143" or "gcc",
    onWorkspace = generate_vscode_settings
}

if _ACTION == "vs2022" then
    premake.override(premake.action.get("vs2022"), "onWorkspace", function(base, wks)
        base(wks)
        generate_vscode_settings(wks)
    end)
end
