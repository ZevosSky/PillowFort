#pragma once

#include <string_view>

namespace pf::error_reporting
{
    // Keep the first logging surface small. Severity, formatting, files, and
    // callbacks should be added only when a real caller requires them.
    void WriteLine(const char* message);
    void WriteLine(const std::string& message); 
    void WriteLine(const std::string_view message);
}
