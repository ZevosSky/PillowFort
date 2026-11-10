# @author   Tutorial harness
# @brief    `source` me: points the shell at the Linux stand-in Vulkan SDK built by
#           setup_linux.sh and forces Mesa lavapipe as the only Vulkan driver.
# @copyright 2026 Gary Yang
#
# Safe to source repeatedly; it does not stack duplicate PATH entries.

export VULKAN_SDK="${PF_VULKAN_SDK:-/opt/pf-vulkan-sdk}"

_pf_prepend() {  # var dir
    local cur="${!1:-}"
    case ":$cur:" in *":$2:"*) ;; *) export "$1=$2${cur:+:$cur}" ;; esac
}
_pf_prepend PATH "$VULKAN_SDK/Bin"
_pf_prepend LD_LIBRARY_PATH "$VULKAN_SDK/Lib"
unset -f _pf_prepend

# The Khronos validation layer built at the same tag as the headers and loader.
export VK_ADD_LAYER_PATH="$VULKAN_SDK/share/vulkan/explicit_layer.d"

# Lavapipe only. VK_DRIVER_FILES is the current loader's name for it,
# VK_ICD_FILENAMES the older one; set both so either loader obeys.
_pf_lvp=""
for _pf_d in /usr/share/vulkan/icd.d /usr/local/share/vulkan/icd.d /etc/vulkan/icd.d; do
    if [ -f "$_pf_d/lvp_icd.json" ]; then _pf_lvp="$_pf_d/lvp_icd.json"; break; fi
    if [ -f "$_pf_d/lvp_icd.x86_64.json" ]; then _pf_lvp="$_pf_d/lvp_icd.x86_64.json"; break; fi
done
if [ -n "$_pf_lvp" ]; then
    export VK_DRIVER_FILES="$_pf_lvp"
    export VK_ICD_FILENAMES="$_pf_lvp"
else
    echo "env.sh: lavapipe ICD manifest not found (apt-get install mesa-vulkan-drivers)" >&2
fi
unset _pf_lvp _pf_d

# Lavapipe warns that it is not a conformant implementation on every instance.
export LP_NUM_THREADS="${LP_NUM_THREADS:-4}"
