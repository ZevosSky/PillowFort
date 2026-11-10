///==========================================================================
/// \file VulkanInstance.cpp
/// \brief vulkan test stuff
/// \author Gary Yang
/// \copyright Copyright (c) 2026 Gary Yang
///==========================================================================


#include "PillowFort/VulkanGraphics/VulkanInstance.h"
#include "PillowFort/ErrorReporting/Log.h"

#include <vulkan/vulkan.h>
#include <GLFW/glfw3.h>

#include <vector>
#include <cstring>
#include <format>

/// @brief Checks if a Vulkan layer is available on the system.
/// @param name The name of the Vulkan layer to check.
/// @return True if the layer is available, false otherwise.
static bool isLayerAvailable(const char* name) {
    uint32_t layerCount = 0;
    vkEnumerateInstanceLayerProperties(&layerCount, nullptr);
    std::vector<VkLayerProperties> availableLayers(layerCount);
    vkEnumerateInstanceLayerProperties(&layerCount, availableLayers.data());

    for (const auto& layer : availableLayers) {
        if (strcmp(layer.layerName, name) == 0) {
            return true;
        }
    }
    return false;

}

namespace pf::vulkan_graphics
{
    /// @brief Initializes the Vulkan instance.
    /// @param enableValidation Whether to enable Vulkan validation layers.
    /// @return The result of the initialization, indicating success or failure.
    InitializationResult  VulkanInstance::CreateInstance(bool enableValidation) {
        const VkApplicationInfo appInfo{
            .sType              = VK_STRUCTURE_TYPE_APPLICATION_INFO,
            .pApplicationName   = "SandboxGame",
            .applicationVersion = VK_MAKE_VERSION(0, 1, 0),
            .pEngineName        = "PillowFort",
            .engineVersion      = VK_MAKE_VERSION(0, 1, 0),
            .apiVersion         = VK_API_VERSION_1_3
        };

        // glfw knows which surface exstentions this platform requires
        // Windows requires the VK_KHR_surface + VK_KHR_win32_surface extensions
        uint32_t glfwExtensionCount = 0;
        const char** glfwExtensions = glfwGetRequiredInstanceExtensions(&glfwExtensionCount);
        if (glfwExtensions == nullptr) {
            return InitializationResult::failure(
                "GLFW reports no Vulkan surface extensions. "
                "The loader is present but no ICD supports presentation.");
        }


        std::vector<const char*> instanceExtensions(glfwExtensions,
                                                    glfwExtensions + glfwExtensionCount);
        std::vector<const char*> validationLayers;


        // Check for validation layer availability and enable if requested 
        // (makes sure this app will not crash if used on a machine without the SDK)
        if (enableValidation && isLayerAvailable("VK_LAYER_KHRONOS_validation")) {
            instanceExtensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
            instanceExtensions.push_back(VK_EXT_VALIDATION_FEATURES_EXTENSION_NAME);
            validationLayers.push_back("VK_LAYER_KHRONOS_validation");
            LOG_INFO("Validation layer VK_LAYER_KHRONOS_validation is available and enabled.");
        } else if (enableValidation) {
            LOG_WARNING("Validation layer VK_LAYER_KHRONOS_validation is not available. "
                        "Continuing without validation..." );
        }

        // messenger setup 
        VkDebugUtilsMessengerCreateInfoEXT messengerInfo{
            .sType           = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
            .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT
                             | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
            .messageType     = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT
                             | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT
                             | VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT,
            .pfnUserCallback = &debugCallback,
            .pUserData = nullptr,
        };
     
        return InitializationResult::success();
    }

    

    

} // namespace pf::vulkan_graphics
