#include "PillowFort/Logging/Log.hpp"

#include <cstdio>

namespace pf::logging
{
    void WriteLine(const std::string_view message)
    {
        if (!message.empty())
        {
            std::fwrite(message.data(), sizeof(char), message.size(), stdout);
        }

        std::fputc('\n', stdout);
    }
}
