#include "LivingActivityMailbox.h"
#include <cassert>
#include <thread>
#include <set>

using namespace LivingActivity;
int main() {
    BoundedMailbox<uint64_t> empty(0);
    assert(!empty.TryPush(1) && empty.Rejected() == 1 && empty.Drain(10).empty());
    BoundedMailbox<uint64_t> mailbox(32);
    for (unsigned i = 0; i < 32; ++i) assert(mailbox.TryPush(i));
    assert(!mailbox.TryPush(32));
    auto values = mailbox.Drain(10); assert(values.size() == 10 && values.front() == 0 && values.back() == 9);
    assert(mailbox.Drain(0).empty());
    values = mailbox.Drain(100); assert(values.size() == 22 && values.front() == 10 && values.back() == 31);
    std::vector<std::thread> producers;
    for (unsigned p = 0; p < 4; ++p) producers.emplace_back([&, p] {
        for (unsigned i = 0; i < 1000; ++i)
            while (!mailbox.TryPush(uint64_t(p) * 1000 + i)) std::this_thread::yield();
    });
    std::set<uint64_t> received;
    while (received.size() < 4000) {
        for (auto id : mailbox.Drain(16)) assert(received.insert(id).second);
        std::this_thread::yield();
    }
    for (auto& worker : producers) worker.join();
    assert(mailbox.Drain(32).empty() && received.size() == 4000);
}
