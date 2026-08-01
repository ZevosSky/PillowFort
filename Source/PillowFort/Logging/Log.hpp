#pragma once

#include <string_view>

namespace pf::logging
{
    // Writes one complete line to the process console.
    void WriteLine(std::string_view message);
}

// Trace calls are present in Debug and completely omitted from Release. The
// disabled form does not evaluate message.
#if defined(PF_DEBUG)
    #define PF_TRACE(message) ::pf::logging::WriteLine(message)
#else
    #define PF_TRACE(message) static_cast<void>(0)
#endif
