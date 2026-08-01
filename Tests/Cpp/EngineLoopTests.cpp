#include "PillowFort/EngineLoop/EngineLoop.hpp"

#include <cstdio>
#include <cstdint>

namespace
{
    bool StopsAfterRequestedFrame()
    {
        constexpr std::uint64_t expected_frame_count = 3;

        pf::engine_loop::EngineLoop engine_loop;
        std::uint64_t observed_frame_count = 0;
        double previous_elapsed_seconds = 0.0;
        bool frame_data_is_valid = true;

        engine_loop.Run(
            [&](const pf::engine_loop::FrameInfo& frame_info)
            {
                frame_data_is_valid =
                    frame_data_is_valid &&
                    frame_info.frame_number == observed_frame_count &&
                    frame_info.delta_seconds >= 0.0 &&
                    frame_info.elapsed_seconds >= previous_elapsed_seconds;

                previous_elapsed_seconds = frame_info.elapsed_seconds;
                ++observed_frame_count;

                if (observed_frame_count == expected_frame_count)
                {
                    engine_loop.RequestStop();
                }
            });

        return frame_data_is_valid &&
            observed_frame_count == expected_frame_count;
    }

    bool CanRunAgainAfterStopping()
    {
        pf::engine_loop::EngineLoop engine_loop;

        const auto run_once = [&engine_loop]()
        {
            bool began_at_frame_zero = false;

            engine_loop.Run(
                [&](const pf::engine_loop::FrameInfo& frame_info)
                {
                    began_at_frame_zero = frame_info.frame_number == 0;
                    engine_loop.RequestStop();
                });

            return began_at_frame_zero;
        };

        return run_once() && run_once();
    }
}

int main()
{
    if (!StopsAfterRequestedFrame())
    {
        std::fputs(
            "FAIL: EngineLoop did not produce the expected frames.\n",
            stderr);
        return 1;
    }

    if (!CanRunAgainAfterStopping())
    {
        std::fputs("FAIL: EngineLoop did not reset between runs.\n", stderr);
        return 1;
    }

    std::fputs("PASS: EngineLoop tests\n", stdout);
    return 0;
}
