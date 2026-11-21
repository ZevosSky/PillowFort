///==========================================================================
/// \file VulkanInstance.h
/// \brief Owns the VkInstance and the objects created directly from it
/// \author Gary Yang
/// \copyright Copyright (c) 2026 Gary Yang
///==========================================================================


#pragma once


#include "PillowFort/ErrorReporting/InitializationResult.h"

#include <vulkan/vulkan.h>


namespace pf::vulkan_graphics
{

    class VulkanInstance
    {
    public:

        /// @brief Initializes the Vulkan instance.
        /// @param enableValidation Whether to enable Vulkan validation layers.
        /// @return The result of the initialization, indicating success or failure.
        InitializationResult CreateInstance(bool enableValidation);

    private:
        VkInstance m_instance = VK_NULL_HANDLE;
    };

}
