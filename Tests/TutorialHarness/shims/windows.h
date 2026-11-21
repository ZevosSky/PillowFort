/*
 * @author   Tutorial harness
 * @brief    Category (a) PLATFORM SHIM. Linux stand-ins for the handful of Win32
 *           calls the tutorial's code makes, so that code compiles verbatim:
 *             - IsDebuggerPresent / __debugbreak   (Chapter 02 section 3, DebugBreak.h)
 *             - GetModuleFileNameW, MAX_PATH, DWORD (Chapter 06 section 1, ExecutableFiles.cpp)
 *           On the include path only for the Linux harness. Never part of the engine.
 * @copyright 2026 Gary Yang
 */
#pragma once

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <unistd.h>

using DWORD = unsigned long;
using BOOL  = int;
#ifndef MAX_PATH
#define MAX_PATH 260
#endif

// TracerPid in /proc/self/status is non-zero under gdb/lldb.
inline BOOL IsDebuggerPresent()
{
    FILE* status = std::fopen("/proc/self/status", "r");
    if (status == nullptr) { return 0; }
    char line[256];
    BOOL traced = 0;
    while (std::fgets(line, sizeof(line), status) != nullptr)
    {
        if (std::strncmp(line, "TracerPid:", 10) == 0) { traced = std::atoi(line + 10) != 0; break; }
    }
    std::fclose(status);
    return traced;
}

#define __debugbreak() std::raise(SIGTRAP)

// Only the hModule == nullptr form (this executable) is supported.
inline DWORD GetModuleFileNameW(void* /*module*/, wchar_t* buffer, DWORD size)
{
    char narrow[4096];
    const ssize_t length = readlink("/proc/self/exe", narrow, sizeof(narrow) - 1);
    if (length <= 0 || size == 0) { return 0; }
    narrow[length] = '\0';
    const size_t converted = std::mbstowcs(buffer, narrow, size);
    if (converted == static_cast<size_t>(-1)) { return 0; }
    if (converted >= size) { buffer[size - 1] = L'\0'; return size; }
    return static_cast<DWORD>(converted);
}
