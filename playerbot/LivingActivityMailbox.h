#ifndef LIVING_ACTIVITY_MAILBOX_H
#define LIVING_ACTIVITY_MAILBOX_H
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <deque>
#include <mutex>
#include <vector>
#include <utility>

namespace LivingActivity {
    // Bounded value-only multi-producer handoff. Producers must check TryPush.
    // Optional diagnostics may count a rejection. A durable operation MUST NOT
    // execute merely hoping its result will fit later; admission is separate.
    template<class Message>
    class BoundedMailbox {
    public:
        explicit BoundedMailbox(size_t capacity) : limit(capacity) {}
        bool TryPush(Message message) {
            std::lock_guard<std::mutex> hold(mutex);
            if (queue.size() >= limit) { ++rejected; return false; }
            queue.push_back(std::move(message)); return true;
        }
        std::vector<Message> Drain(size_t maximum) {
            std::lock_guard<std::mutex> hold(mutex);
            std::vector<Message> result;
            result.reserve(std::min(maximum, queue.size()));
            while (!queue.empty() && result.size() < maximum) {
                result.push_back(std::move(queue.front())); queue.pop_front();
            }
            return result;
        }
        uint64_t Rejected() const { return rejected.load(std::memory_order_relaxed); }
    private:
        const size_t limit;
        mutable std::mutex mutex;
        std::deque<Message> queue;
        std::atomic<uint64_t> rejected{0};
    };
}
#endif
