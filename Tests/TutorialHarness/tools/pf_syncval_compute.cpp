// @author   Tutorial harness
// @brief    Positive control for synchronization validation of SHADER accesses made
//           through descriptors. One command buffer, no barriers anywhere:
//             1. dispatch writes storage buffer A        -> vkCmdCopyBuffer reads A
//             2. dispatch writes storage buffer B        -> dispatch reads B (descriptor)
//           Both are read-after-write hazards. VVL 1.4.363 sees them only when
//           syncval_shader_accesses_heuristic is on; with it off the run is silent,
//           which is exactly why the harness turns it on.
//
//           Two builds of this file:
//             * a standalone program (`pf_syncval_compute writer.spv reader.spv`) with its
//               own instance - tests the layer + environment alone;
//             * PF_INTERPOSE: an LD_PRELOAD library that hooks vkCreateDevice in the
//               program under test and records the same hazards on THAT program's device,
//               right after it is created. Validation is then configured exactly as the
//               program configures it (its VK_EXT_layer_settings plus the harness
//               environment), and no line of the program changes. Shader paths come from
//               PF_SYNCVAL_WRITER / PF_SYNCVAL_READER.
//           Neither asks for sync validation or the heuristic itself.
// @copyright 2026 Gary Yang
#include <vulkan/vulkan.h>

#ifdef PF_INTERPOSE
#include <dlfcn.h>
#endif
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>

#define CHECK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
    std::fprintf(stderr, "[ERROR] %s failed: %d\n", #call, r_); std::exit(1); } } while (0)

#ifndef PF_INTERPOSE
static VKAPI_ATTR VkBool32 VKAPI_CALL callback(VkDebugUtilsMessageSeverityFlagBitsEXT severity,
                                               VkDebugUtilsMessageTypeFlagsEXT,
                                               const VkDebugUtilsMessengerCallbackDataEXT* data, void*)
{
    const bool error = (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) != 0;
    std::printf("[%s] Vulkan: [%s] %s\n", error ? "ERROR" : "WARNING",
                data->pMessageIdName ? data->pMessageIdName : "", data->pMessage);
    return VK_FALSE;
}
#endif

static std::vector<uint32_t> readSpirv(const char* path)
{
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) { std::fprintf(stderr, "[ERROR] cannot open %s\n", path); std::exit(1); }
    const std::streamsize bytes = file.tellg();
    std::vector<uint32_t> words(static_cast<size_t>(bytes) / 4);
    file.seekg(0);
    file.read(reinterpret_cast<char*>(words.data()), bytes);
    return words;
}

struct Buffer { VkBuffer buffer; VkDeviceMemory memory; };

// Records and submits both hazards on `device`, waits, and destroys everything it made.
static void recordHazards(VkPhysicalDevice physical, VkDevice device, uint32_t family,
                          const char* writerPath, const char* readerPath)
{
    VkQueue queue;
    vkGetDeviceQueue(device, family, 0, &queue);
    VkPhysicalDeviceMemoryProperties memoryProperties;
    vkGetPhysicalDeviceMemoryProperties(physical, &memoryProperties);
    auto makeBuffer = [&](VkBufferUsageFlags usage) {
        Buffer b{};
        VkBufferCreateInfo info{};
        info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        info.size = 256 * sizeof(uint32_t);
        info.usage = usage;
        CHECK(vkCreateBuffer(device, &info, nullptr, &b.buffer));
        VkMemoryRequirements requirements;
        vkGetBufferMemoryRequirements(device, b.buffer, &requirements);
        uint32_t type = 0;
        while (!(requirements.memoryTypeBits & (1u << type))) { ++type; }
        VkMemoryAllocateInfo allocate{};
        allocate.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = type;
        CHECK(vkAllocateMemory(device, &allocate, nullptr, &b.memory));
        CHECK(vkBindBufferMemory(device, b.buffer, b.memory, 0));
        return b;
    };
    const VkBufferUsageFlags storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                                       VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    Buffer a = makeBuffer(storage), b = makeBuffer(storage), copyTarget = makeBuffer(storage), out = makeBuffer(storage);

    VkDescriptorSetLayoutBinding bindings[2]{};
    for (uint32_t i = 0; i < 2; ++i)
    {
        bindings[i].binding = i;
        bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[i].descriptorCount = 1;
        bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    VkDescriptorSetLayoutCreateInfo setLayoutInfo{};
    setLayoutInfo.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    setLayoutInfo.bindingCount = 2;
    setLayoutInfo.pBindings = bindings;
    VkDescriptorSetLayout setLayout;
    CHECK(vkCreateDescriptorSetLayout(device, &setLayoutInfo, nullptr, &setLayout));
    VkPipelineLayoutCreateInfo layoutInfo{};
    layoutInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    layoutInfo.setLayoutCount = 1;
    layoutInfo.pSetLayouts = &setLayout;
    VkPipelineLayout layout;
    CHECK(vkCreatePipelineLayout(device, &layoutInfo, nullptr, &layout));

    auto makePipeline = [&](const char* path) {
        const std::vector<uint32_t> code = readSpirv(path);
        VkShaderModuleCreateInfo moduleInfo{};
        moduleInfo.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        moduleInfo.codeSize = code.size() * 4;
        moduleInfo.pCode = code.data();
        VkShaderModule module;
        CHECK(vkCreateShaderModule(device, &moduleInfo, nullptr, &module));
        VkComputePipelineCreateInfo info{};
        info.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
        info.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        info.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        info.stage.module = module;
        info.stage.pName = "main";
        info.layout = layout;
        VkPipeline pipeline;
        CHECK(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &info, nullptr, &pipeline));
        vkDestroyShaderModule(device, module, nullptr);
        return pipeline;
    };
    VkPipeline writer = makePipeline(writerPath);   // binding 1 <- index
    VkPipeline reader = makePipeline(readerPath);   // binding 1 <- binding 0 + 1

    VkDescriptorPoolSize poolSize{ VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 6 };
    VkDescriptorPoolCreateInfo poolInfo{};
    poolInfo.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    poolInfo.maxSets = 3;
    poolInfo.poolSizeCount = 1;
    poolInfo.pPoolSizes = &poolSize;
    VkDescriptorPool pool;
    CHECK(vkCreateDescriptorPool(device, &poolInfo, nullptr, &pool));
    VkDescriptorSetLayout layouts[3] = { setLayout, setLayout, setLayout };
    VkDescriptorSetAllocateInfo allocateInfo{};
    allocateInfo.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    allocateInfo.descriptorPool = pool;
    allocateInfo.descriptorSetCount = 3;
    allocateInfo.pSetLayouts = layouts;
    VkDescriptorSet sets[3];
    CHECK(vkAllocateDescriptorSets(device, &allocateInfo, sets));
    auto write = [&](VkDescriptorSet set, VkBuffer binding0, VkBuffer binding1) {
        VkDescriptorBufferInfo infos[2] = { { binding0, 0, VK_WHOLE_SIZE }, { binding1, 0, VK_WHOLE_SIZE } };
        VkWriteDescriptorSet writes[2]{};
        for (uint32_t i = 0; i < 2; ++i)
        {
            writes[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
            writes[i].dstSet = set;
            writes[i].dstBinding = i;
            writes[i].descriptorCount = 1;
            writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[i].pBufferInfo = &infos[i];
        }
        vkUpdateDescriptorSets(device, 2, writes, 0, nullptr);
    };
    write(sets[0], out.buffer, a.buffer);   // writer -> A
    write(sets[1], out.buffer, b.buffer);   // writer -> B
    write(sets[2], b.buffer, out.buffer);   // reader: B -> out

    VkCommandPoolCreateInfo commandPoolInfo{};
    commandPoolInfo.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    commandPoolInfo.queueFamilyIndex = family;
    VkCommandPool commandPool;
    CHECK(vkCreateCommandPool(device, &commandPoolInfo, nullptr, &commandPool));
    VkCommandBufferAllocateInfo commandInfo{};
    commandInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    commandInfo.commandPool = commandPool;
    commandInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    commandInfo.commandBufferCount = 1;
    VkCommandBuffer cmd;
    CHECK(vkAllocateCommandBuffers(device, &commandInfo, &cmd));

    VkCommandBufferBeginInfo begin{};
    begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    CHECK(vkBeginCommandBuffer(cmd, &begin));
    // Case 1: shader write through a descriptor, then a transfer read. No barrier.
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, writer);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &sets[0], 0, nullptr);
    vkCmdDispatch(cmd, 4, 1, 1);
    const VkBufferCopy region{ 0, 0, 256 * sizeof(uint32_t) };
    vkCmdCopyBuffer(cmd, a.buffer, copyTarget.buffer, 1, &region);
    std::printf("[INFO] case 1 recorded: dispatch writes A, vkCmdCopyBuffer reads A, no barrier\n");
    // Case 2: shader write, then shader read, both through descriptors. No barrier.
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &sets[1], 0, nullptr);
    vkCmdDispatch(cmd, 4, 1, 1);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, reader);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &sets[2], 0, nullptr);
    vkCmdDispatch(cmd, 4, 1, 1);
    std::printf("[INFO] case 2 recorded: dispatch writes B, dispatch reads B, no barrier\n");
    CHECK(vkEndCommandBuffer(cmd));

    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &cmd;
    CHECK(vkQueueSubmit(queue, 1, &submit, VK_NULL_HANDLE));
    CHECK(vkQueueWaitIdle(queue));

    vkDestroyCommandPool(device, commandPool, nullptr);
    vkDestroyDescriptorPool(device, pool, nullptr);
    vkDestroyPipeline(device, writer, nullptr);
    vkDestroyPipeline(device, reader, nullptr);
    vkDestroyPipelineLayout(device, layout, nullptr);
    vkDestroyDescriptorSetLayout(device, setLayout, nullptr);
    for (Buffer* buffer : { &a, &b, &copyTarget, &out })
    {
        vkDestroyBuffer(device, buffer->buffer, nullptr);
        vkFreeMemory(device, buffer->memory, nullptr);
    }
}

#ifndef PF_INTERPOSE
int main(int argc, char** argv)
{
    if (argc != 3) { std::fprintf(stderr, "usage: %s writer.spv reader.spv\n", argv[0]); return 2; }

    const char* layers[] = { "VK_LAYER_KHRONOS_validation" };
    const char* extensions[] = { VK_EXT_DEBUG_UTILS_EXTENSION_NAME };
    VkDebugUtilsMessengerCreateInfoEXT messengerInfo{};
    messengerInfo.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
    messengerInfo.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                                    VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
    messengerInfo.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                                VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT;
    messengerInfo.pfnUserCallback = &callback;

    VkApplicationInfo app{};
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.apiVersion = VK_API_VERSION_1_3;
    VkInstanceCreateInfo instanceInfo{};
    instanceInfo.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instanceInfo.pNext = &messengerInfo;
    instanceInfo.pApplicationInfo = &app;
    instanceInfo.enabledLayerCount = 1;
    instanceInfo.ppEnabledLayerNames = layers;
    instanceInfo.enabledExtensionCount = 1;
    instanceInfo.ppEnabledExtensionNames = extensions;
    VkInstance instance;
    CHECK(vkCreateInstance(&instanceInfo, nullptr, &instance));

    uint32_t count = 1;
    VkPhysicalDevice physical;
    vkEnumeratePhysicalDevices(instance, &count, &physical);
    if (count == 0) { std::fprintf(stderr, "[ERROR] no device\n"); return 1; }

    uint32_t familyCount = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &familyCount, nullptr);
    std::vector<VkQueueFamilyProperties> families(familyCount);
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &familyCount, families.data());
    uint32_t family = 0;
    while (family < familyCount && !(families[family].queueFlags & VK_QUEUE_COMPUTE_BIT)) { ++family; }

    const float priority = 1.0f;
    VkDeviceQueueCreateInfo queueInfo{};
    queueInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queueInfo.queueFamilyIndex = family;
    queueInfo.queueCount = 1;
    queueInfo.pQueuePriorities = &priority;
    VkDeviceCreateInfo deviceInfo{};
    deviceInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    deviceInfo.queueCreateInfoCount = 1;
    deviceInfo.pQueueCreateInfos = &queueInfo;
    VkDevice device;
    CHECK(vkCreateDevice(physical, &deviceInfo, nullptr, &device));

    recordHazards(physical, device, family, argv[1], argv[2]);
    vkDestroyDevice(device, nullptr);
    vkDestroyInstance(instance, nullptr);
    return 0;
}
#endif

#ifdef PF_INTERPOSE
// Runs once, inside the program's own vkCreateDevice, on the device it just created.
extern "C" VKAPI_ATTR VkResult VKAPI_CALL vkCreateDevice(VkPhysicalDevice physical,
                                                        const VkDeviceCreateInfo* info,
                                                        const VkAllocationCallbacks* allocator,
                                                        VkDevice* device)
{
    static auto real = reinterpret_cast<PFN_vkCreateDevice>(dlsym(RTLD_NEXT, "vkCreateDevice"));
    const VkResult result = real(physical, info, allocator, device);
    static bool done = false;
    const char* writer = std::getenv("PF_SYNCVAL_WRITER");
    const char* reader = std::getenv("PF_SYNCVAL_READER");
    if (result == VK_SUCCESS && !done && writer && reader && info->queueCreateInfoCount > 0)
    {
        done = true;
        std::printf("[INFO] pf_syncval_compute: recording the compute hazards on the program's device\n");
        std::fflush(stdout);
        recordHazards(physical, *device, info->pQueueCreateInfos[0].queueFamilyIndex, writer, reader);
    }
    return result;
}
#endif
