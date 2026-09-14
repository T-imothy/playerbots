#pragma once
#include <cstdint>

namespace ai { namespace chat {
// Synchronous broadcast metadata only. No player pointer or classification is
// retained after the native Say call returns. Nested sends restore their caller.
class BroadcastSenderScope
{
public:
    BroadcastSenderScope(std::uint64_t guid, bool freeBot)
        : previous_(current_), guid_(guid), freeBot_(freeBot) { current_ = this; }
    ~BroadcastSenderScope() { current_ = previous_; }
    BroadcastSenderScope(BroadcastSenderScope const&) = delete;
    BroadcastSenderScope& operator=(BroadcastSenderScope const&) = delete;
    static bool TryGet(std::uint64_t guid, bool& freeBot)
    {
        if (!current_ || current_->guid_ != guid) return false;
        freeBot = current_->freeBot_;
        return true;
    }
private:
    inline static thread_local BroadcastSenderScope const* current_ = nullptr;
    BroadcastSenderScope const* previous_;
    std::uint64_t guid_;
    bool freeBot_;
};
}}
