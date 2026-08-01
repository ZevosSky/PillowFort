#pragma once

#include <cstdint>
#include <functional>

namespace pf::engine_loop
{
    struct FrameInfo final
    {
        std::uint64_t frame_number;
        double delta_seconds;
        double elapsed_seconds;
    };

    using FrameCallback = std::function<void(const FrameInfo&)>;

    class EngineLoop final
    {
    public:
        // Runs until RequestStop() is called. The callback owns the work for
        // one frame; window polling and graphics will plug in there later.
        void Run(const FrameCallback& frame_callback);

        // A frame callback may request a clean stop. The current callback is
        // allowed to finish before Run() returns.
        void RequestStop() noexcept;

    private:
        bool stop_requested_ = false;
        
    };
}
