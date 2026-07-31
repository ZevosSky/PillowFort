#include "PillowFort/EngineLoop/EngineLoop.hpp"
#include "PillowFort/ErrorReporting/Log.hpp"

#include <cstdint>

int main()
{
    using pf::engine_loop::EngineLoop;
    using pf::engine_loop::FrameInfo;
    using pf::error_reporting::WriteLine;

    constexpr std::uint64_t demonstration_frame_count = 3;

    WriteLine("PillowFort starting.");

    EngineLoop engine_loop;
    std::uint64_t completed_frame_count = 0;

    engine_loop.Run(
        [&engine_loop, &completed_frame_count](const FrameInfo& frame_info)
        {
            completed_frame_count = frame_info.frame_number + 1;

            if (completed_frame_count >= demonstration_frame_count)
            {
                engine_loop.RequestStop();
            }
        });

    if (completed_frame_count != demonstration_frame_count)
    {
        WriteLine("PillowFort stopped after an unexpected number of frames.");
        return 1;
    }

    WriteLine("PillowFort completed three frames and stopped cleanly.");
    return 0;
}
