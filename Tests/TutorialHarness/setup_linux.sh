#!/usr/bin/env bash
# @author   Tutorial harness (Linux stand-in for the Windows SDK)
# @brief    Builds a VULKAN_SDK-shaped directory from Khronos git tags, plus the
#           X11/xvfb tooling the tutorial harness runs under. Idempotent: every
#           step leaves a stamp keyed by its version and is skipped next time.
# @copyright 2026 Gary Yang
#
# This is a doc-verification tool. premake5.lua and GenerateProjects.bat never
# reference it, and it is not a build layer for the engine.
#
# Usage:  Tests/TutorialHarness/setup_linux.sh [--force] [step ...]
# Steps:  apt clone headers utility loader volk glm vma glslc vvl submodules check
#         (default: all, in that order). PF_JOBS, PF_VULKAN_SDK, PF_SDK_CACHE
#         override the defaults below.
set -euo pipefail

SDK_TAG=${PF_SDK_TAG:-vulkan-sdk-1.4.363.0}   # newest vulkan-sdk-1.4.* tag on Vulkan-Headers, 2026-10
GLM_TAG=1.0.3                                  # latest GLM release; the SDK's own pick is not checkable offline
VMA_TAG=v3.4.0                                 # latest VMA release; same caveat
SHADERC_TAG=v2026.4                            # pins the same glslang/SPIRV-Tools commits as $SDK_TAG

PREFIX=${PF_VULKAN_SDK:-/opt/pf-vulkan-sdk}
CACHE=${PF_SDK_CACHE:-$HOME/.cache/pf-vulkan-sdk}
JOBS=${PF_JOBS:-$(nproc)}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$HERE/../.." && pwd)
SRC=$CACHE/src
BLD=$CACHE/build
STAMPS=$CACHE/stamps
FORCE=0

log()  { printf '\n[setup] %s\n' "$*"; }
die()  { printf '\n[setup] ERROR: %s\n' "$*" >&2; exit 1; }
done_already() { [[ $FORCE == 0 && -f $STAMPS/$1 ]]; }
stamp() { mkdir -p "$STAMPS"; date -u +%FT%TZ > "$STAMPS/$1"; }

# Clone one repo at one tag, shallow. Re-clones if the checkout is at another tag.
clone_at() {  # url dir tag
    local url=$1 dir=$SRC/$2 tag=$3
    if [[ -d $dir/.git ]]; then
        local have; have=$(git -C "$dir" describe --tags --exact-match 2>/dev/null || true)
        [[ $have == "$tag" ]] && return 0
        if git -C "$dir" -c advice.detachedHead=false fetch -q --depth 1 origin tag "$tag" 2>/dev/null; then
            git -C "$dir" -c advice.detachedHead=false checkout -q "$tag"; return 0
        fi
        rm -rf "$dir"
    fi
    git -c advice.detachedHead=false clone -q --depth 1 --branch "$tag" "$url" "$dir"
}

cmake_build() {  # name srcdir [cmake args...]
    local name=$1 src=$2; shift 2
    cmake -S "$src" -B "$BLD/$name" -G Ninja -D CMAKE_BUILD_TYPE=Release "$@" > "$BLD/$name.configure.log" 2>&1 \
        || { tail -40 "$BLD/$name.configure.log"; die "configure $name failed (log: $BLD/$name.configure.log)"; }
    cmake --build "$BLD/$name" -j "$JOBS" > "$BLD/$name.build.log" 2>&1 \
        || { tail -40 "$BLD/$name.build.log"; die "build $name failed (log: $BLD/$name.build.log)"; }
}

step_apt() {
    done_already apt-v4 && return 0
    log "apt: compilers, X11 dev headers, Xvfb, ImageMagick, xdotool, lavapipe"
    export DEBIAN_FRONTEND=noninteractive
    local SUDO=""; [[ $(id -u) == 0 ]] || SUDO=sudo
    $SUDO apt-get update -q || true
    $SUDO apt-get install -y -q \
        git cmake ninja-build python3 g++ clang pkg-config \
        libgl-dev libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libxext-dev \
        libxcb1-dev libx11-xcb-dev libxkbcommon-dev libwayland-dev \
        xvfb xauth x11-apps x11-utils xdotool imagemagick libclang-rt-18-dev \
        mesa-vulkan-drivers vulkan-tools
    stamp apt-v4
}

step_clone() {
    done_already "clone-$SDK_TAG-$SHADERC_TAG-$GLM_TAG-$VMA_TAG" && return 0
    log "clone: Khronos repos at $SDK_TAG"
    mkdir -p "$SRC"
    local r
    for r in Vulkan-Headers Vulkan-Utility-Libraries Vulkan-Loader Vulkan-ValidationLayers \
             SPIRV-Headers SPIRV-Tools glslang; do
        clone_at "https://github.com/KhronosGroup/$r.git" "$r" "$SDK_TAG"
    done
    clone_at https://github.com/zeux/volk.git volk "$SDK_TAG"
    clone_at https://github.com/g-truc/glm.git glm "$GLM_TAG"
    clone_at https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator.git VulkanMemoryAllocator "$VMA_TAG"
    clone_at https://github.com/google/shaderc.git shaderc "$SHADERC_TAG"
    stamp "clone-$SDK_TAG-$SHADERC_TAG-$GLM_TAG-$VMA_TAG"
}

step_headers() {
    done_already "headers-$SDK_TAG" && return 0
    log "Vulkan-Headers -> $PREFIX/Include/{vulkan,vk_video}"
    mkdir -p "$PREFIX"
    cmake_build Vulkan-Headers "$SRC/Vulkan-Headers" \
        -D CMAKE_INSTALL_PREFIX="$PREFIX" -D CMAKE_INSTALL_INCLUDEDIR=Include -D VULKAN_HEADERS_ENABLE_MODULE=OFF
    cmake --install "$BLD/Vulkan-Headers" > /dev/null
    stamp "headers-$SDK_TAG"
}

step_utility() {
    done_already "utility-$SDK_TAG" && return 0
    log "Vulkan-Utility-Libraries -> vk_enum_string_helper.h, vulkan/utility, layer settings"
    cmake_build Vulkan-Utility-Libraries "$SRC/Vulkan-Utility-Libraries" \
        -D CMAKE_INSTALL_PREFIX="$PREFIX" -D CMAKE_INSTALL_INCLUDEDIR=Include -D CMAKE_INSTALL_LIBDIR=Lib \
        -D CMAKE_PREFIX_PATH="$PREFIX" -D UPDATE_DEPS=OFF -D BUILD_TESTS=OFF
    cmake --install "$BLD/Vulkan-Utility-Libraries" > /dev/null
    stamp "utility-$SDK_TAG"
}

step_loader() {
    done_already "loader-$SDK_TAG" && return 0
    log "Vulkan-Loader -> $PREFIX/Lib/libvulkan.so"
    cmake_build Vulkan-Loader "$SRC/Vulkan-Loader" \
        -D CMAKE_INSTALL_PREFIX="$PREFIX" -D CMAKE_INSTALL_LIBDIR=Lib \
        -D CMAKE_PREFIX_PATH="$PREFIX" -D UPDATE_DEPS=OFF -D BUILD_TESTS=OFF
    cmake --install "$BLD/Vulkan-Loader" > /dev/null
    stamp "loader-$SDK_TAG"
}

step_volk() {
    done_already "volk-$SDK_TAG" && return 0
    log "volk -> $PREFIX/Include/Volk"
    mkdir -p "$PREFIX/Include/Volk"
    cp "$SRC/volk/volk.h" "$SRC/volk/volk.c" "$PREFIX/Include/Volk/"
    stamp "volk-$SDK_TAG"
}

step_glm() {
    done_already "glm-$GLM_TAG" && return 0
    log "GLM $GLM_TAG -> $PREFIX/Include/glm"
    rm -rf "$PREFIX/Include/glm"
    cp -r "$SRC/glm/glm" "$PREFIX/Include/glm"
    find "$PREFIX/Include/glm" \( -name CMakeLists.txt -o -name '*.cpp' \) -delete
    stamp "glm-$GLM_TAG"
}

step_vma() {
    done_already "vma-$VMA_TAG" && return 0
    log "VMA $VMA_TAG -> $PREFIX/Include/vma"
    mkdir -p "$PREFIX/Include/vma"
    cp "$SRC/VulkanMemoryAllocator/include/vk_mem_alloc.h" "$PREFIX/Include/vma/"
    stamp "vma-$VMA_TAG"
}

step_glslc() {
    done_already "glslc-$SHADERC_TAG-$SDK_TAG" && return 0
    log "shaderc $SHADERC_TAG + glslang/SPIRV-Tools/SPIRV-Headers $SDK_TAG -> $PREFIX/Bin (several minutes)"
    cmake_build shaderc "$SRC/shaderc" \
        -D CMAKE_INSTALL_PREFIX="$CACHE/stage/shaderc" \
        -D SHADERC_GLSLANG_DIR="$SRC/glslang" -D SHADERC_SPIRV_TOOLS_DIR="$SRC/SPIRV-Tools" \
        -D SHADERC_SPIRV_HEADERS_DIR="$SRC/SPIRV-Headers" \
        -D SHADERC_SKIP_TESTS=ON -D SHADERC_SKIP_EXAMPLES=ON -D SHADERC_SKIP_COPYRIGHT_CHECK=ON \
        -D SPIRV_SKIP_TESTS=ON -D SPIRV_WERROR=OFF -D ENABLE_GLSLANG_BINARIES=ON -D GLSLANG_TESTS=OFF
    cmake --install "$BLD/shaderc" > /dev/null
    mkdir -p "$PREFIX/Bin"
    local b
    for b in glslc glslang glslangValidator spirv-val spirv-dis spirv-opt spirv-cross; do
        [[ -e $CACHE/stage/shaderc/bin/$b ]] && cp -L "$CACHE/stage/shaderc/bin/$b" "$PREFIX/Bin/$b"
    done
    [[ -x $PREFIX/Bin/glslc ]] || die "glslc did not build"
    stamp "glslc-$SHADERC_TAG-$SDK_TAG"
}

step_vvl() {
    done_already "vvl-$SDK_TAG" && return 0
    log "Vulkan-ValidationLayers $SDK_TAG (UPDATE_DEPS fetches its known_good deps by git; 20-60 min)"
    cmake_build Vulkan-ValidationLayers "$SRC/Vulkan-ValidationLayers" \
        -D CMAKE_INSTALL_PREFIX="$CACHE/stage/vvl" -D CMAKE_INSTALL_LIBDIR=lib \
        -D UPDATE_DEPS=ON -D UPDATE_DEPS_DIR="$BLD/vvl-deps" -D BUILD_WERROR=OFF -D BUILD_TESTS=OFF
    cmake --install "$BLD/Vulkan-ValidationLayers" > /dev/null
    mkdir -p "$PREFIX/Lib" "$PREFIX/share/vulkan/explicit_layer.d"
    cp "$CACHE/stage/vvl/lib/libVkLayer_khronos_validation.so" "$PREFIX/Lib/"
    # Absolute library_path so the manifest works whatever LD_LIBRARY_PATH says.
    python3 - "$CACHE/stage/vvl/share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json" \
              "$PREFIX/share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json" \
              "$PREFIX/Lib/libVkLayer_khronos_validation.so" <<'EOF'
import json, sys
src, dst, lib = sys.argv[1:]
data = json.load(open(src))
data["layer"]["library_path"] = lib
json.dump(data, open(dst, "w"), indent=4)
EOF
    stamp "vvl-$SDK_TAG"
}

step_submodules() {
    log "submodules (pins unchanged)"
    git -C "$REPO_ROOT" submodule update --init --recursive
}

step_check() {
    log "check"
    # shellcheck source=env.sh
    source "$HERE/env.sh"
    cp "$HERE/env.sh" "$PREFIX/setup-env.sh"
    local f missing=0
    for f in Include/vulkan/vulkan.h Include/vk_video/vulkan_video_codecs_common.h \
             Include/vulkan/vk_enum_string_helper.h Include/glm/glm.hpp Include/vma/vk_mem_alloc.h \
             Include/Volk/volk.h Include/Volk/volk.c Bin/glslc Lib/libvulkan.so \
             Lib/libVkLayer_khronos_validation.so share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json; do
        if [[ -e $PREFIX/$f ]]; then echo "  ok   $f"; else echo "  MISSING $f"; missing=1; fi
    done
    "$PREFIX/Bin/glslc" --version | head -1 || true
    grep -q VK_EXT_layer_settings "$PREFIX/share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json" \
        && echo "  ok   validation layer advertises VK_EXT_layer_settings" \
        || { echo "  MISSING VK_EXT_layer_settings in layer manifest"; missing=1; }
    vulkaninfo --summary 2>/dev/null | grep -E "deviceName|apiVersion|driverName" | head -6 || true
    [[ $missing == 0 ]] || die "SDK incomplete"
}

ALL=(apt clone headers utility loader volk glm vma glslc vvl submodules check)
STEPS=()
for a in "$@"; do
    case $a in
        --force) FORCE=1 ;;
        -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
        *) STEPS+=("$a") ;;
    esac
done
[[ ${#STEPS[@]} == 0 ]] && STEPS=("${ALL[@]}")
mkdir -p "$SRC" "$BLD" "$STAMPS"
for s in "${STEPS[@]}"; do "step_$s"; done
log "done: VULKAN_SDK=$PREFIX   (source $HERE/env.sh)"
