#include "PillowFort/EngineLoop/EngineLoop.hpp"

#include <cassert>
#include <chrono>

namespace pf::engine_loop
{
    void EngineLoop::Run(const FrameCallback& frame_callback)
    {
        assert(frame_callback);

        using Clock = std::chrono::steady_clock;

        stop_requested_ = false;

        const auto start_time = Clock::now();
        auto previous_frame_time = start_time;
        std::uint64_t frame_number = 0;

        while (!stop_requested_)
        {
            const auto frame_time = Clock::now();
            const std::chrono::duration<double> delta_time =
                frame_time - previous_frame_time;
            const std::chrono::duration<double> elapsed_time =
                frame_time - start_time;

            const FrameInfo frame_info
            {
                .frame_number = frame_number,
                .delta_seconds = delta_time.count(),
                .elapsed_seconds = elapsed_time.count()
            };

            frame_callback(frame_info);

            previous_frame_time = frame_time;
            ++frame_number;
        }
    }

    void EngineLoop::RequestStop() noexcept
    {
        stop_requested_ = true;
    }
}
