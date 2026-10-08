/*
 * @author   Tutorial harness
 * @brief    LD_PRELOAD interposer on vkQueuePresentKHR. After the Nth present
 *           listed in PF_HOOK_FRAMES it pauses the application and tells the
 *           harness, which takes a screenshot or sends input, then lets it go.
 *           This is how screenshots land on exact frames without changing a
 *           line of the program under test.
 * @copyright 2026 Gary Yang
 *
 * Environment:
 *   PF_HOOK_FRAMES  comma list of present numbers (1-based), e.g. "30,120"
 *   PF_HOOK_REQ     FIFO the hook writes "<frame> <present result>\n" to
 *   PF_HOOK_ACK     FIFO the harness answers on (any line)
 *   PF_HOOK_SETTLE  milliseconds to wait after the present before asking (default 150),
 *                   so a presentation thread in the driver has put the image on screen
 *
 * It only waits; it never calls Vulkan itself, so it cannot add synchronization
 * that would hide a hazard from the validation layer.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vulkan/vulkan.h>

static PFN_vkQueuePresentKHR g_real;
static unsigned long g_frames[512];
static int g_frameCount = -1;
static unsigned long g_present;
static FILE* g_req;
static FILE* g_ack;

static void parseFrames(void)
{
    g_frameCount = 0;
    const char* list = getenv("PF_HOOK_FRAMES");
    if (!list) { return; }
    char* copy = strdup(list);
    for (char* token = strtok(copy, ","); token && g_frameCount < 512; token = strtok(NULL, ","))
    {
        g_frames[g_frameCount++] = strtoul(token, NULL, 10);
    }
    free(copy);
}

static int isHooked(unsigned long frame)
{
    for (int i = 0; i < g_frameCount; ++i) { if (g_frames[i] == frame) { return 1; } }
    return 0;
}

VKAPI_ATTR VkResult VKAPI_CALL vkQueuePresentKHR(VkQueue queue, const VkPresentInfoKHR* presentInfo)
{
    if (!g_real)
    {
        g_real = (PFN_vkQueuePresentKHR)dlsym(RTLD_NEXT, "vkQueuePresentKHR");
        if (!g_real) { fprintf(stderr, "pf_framehook: no next vkQueuePresentKHR\n"); abort(); }
    }
    if (g_frameCount < 0) { parseFrames(); }

    const VkResult result = g_real(queue, presentInfo);
    ++g_present;

    if (isHooked(g_present))
    {
        const char* settle = getenv("PF_HOOK_SETTLE");
        const long ms = settle ? atol(settle) : 150;
        struct timespec pause = { ms / 1000, (ms % 1000) * 1000000L };
        nanosleep(&pause, NULL);

        if (!g_req) { g_req = fopen(getenv("PF_HOOK_REQ"), "w"); }
        if (!g_ack) { g_ack = fopen(getenv("PF_HOOK_ACK"), "r"); }
        if (g_req && g_ack)
        {
            fprintf(g_req, "%lu %d\n", g_present, (int)result);
            fflush(g_req);
            char line[64];
            if (!fgets(line, sizeof(line), g_ack)) { fprintf(stderr, "pf_framehook: harness went away\n"); }
        }
    }
    return result;
}
