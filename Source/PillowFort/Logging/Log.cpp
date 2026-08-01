#include "PillowFort/ErrorReporting/Log.hpp"

#include <iostream>

namespace pf::error_reporting
{
    void WriteLine(const char* message) {
        printf("%s\n", message);
    }

    void WriteLine(const std::string& message) {
        WriteLine(message.c_str());
    }

    void WriteLine(const std::string_view message) {
        WriteLine(std::string(message).c_str());
    }
}

