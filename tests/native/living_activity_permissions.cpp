#include "LivingActivityPermissions.h"
#include <atomic>
#include <cassert>
#include <thread>
#include <vector>

using namespace LivingActivity;
int main() {
    Task task; task.id = task.root = "637bd562-36d2-5b01-bc01-e2d831c49f38";
    task.source = "profession"; task.sourceKey = "1"; task.actor = task.context.actor = 497;
    task.context.boot = "ff2efbdf-f0ec-4539-b840-299847970c00";
    task.context.actorGeneration = task.context.mapGeneration = task.context.policyRevision = 1;
    task.createdAtMs = task.updatedAtMs = 1; task.mode = Mode::Active; task.phase = Phase::Traveling;
    ExecutionAuthority authority;
    authority.Observe(task.context, 0);
    auto lease = authority.Acquire(task, Mask(Effect::Movement), 100, 1000);
    assert(lease.Granted()); task.ownerGeneration = lease.lease.generation;
    PermissionPublisher publisher; const auto reader = publisher.Reader();
    const Effects movement{Mask(Effect::Movement), Lane::Managed, true};
    assert(reader.Check(movement, task.context, 200) == AuthorityCode::NoOwner);
    publisher.Publish(authority.Read(task.actor));
    assert(reader.Check(movement, task.context, 200) == AuthorityCode::StaleLease); // Not implicitly borrowed by autonomous work.
    ActionContext action; action.task = action.rootTask = task.id; action.world = task.context;
    action.revision = task.revision; action.ownerGeneration = lease.lease.generation;
    action.origin = "service_adapter"; action.permittedEffects = Mask(Effect::Movement);
    assert(reader.Check(movement, task.context, 200, &task, &action) == AuthorityCode::Allowed);
    auto revokedPolicy = task.context; ++revokedPolicy.policyRevision;
    assert(reader.Check(movement, revokedPolicy, 200, &task, &action) == AuthorityCode::StaleContext);
    assert(reader.Check(movement, task.context, 200, &task, &action, nullptr, uint32_t(Safety::Combat)) == AuthorityCode::SafetyPaused);
    assert(reader.Check(movement, task.context, 200, &task, &action, nullptr, uint32_t(Safety::Taxi)) == AuthorityCode::SafetyPaused);
    const auto heldOldView = reader.Inspect();
    auto human = task; human.id = human.root = "9411eb6c-d355-4618-b323-1c8e0b0daaa2";
    human.priority = Priority::Human;
    assert(authority.Acquire(human, Mask(Effect::Movement), 200, 1000).Granted());
    publisher.Publish(authority.Read(task.actor));
    assert(reader.Check(movement, task.context, 200, &task, &action) == AuthorityCode::StaleLease);
    assert(heldOldView->lease.rootTask == task.id); // Immutable, but not current authorization.
    publisher.Revoke();
    assert(reader.Check(movement, task.context, 200, &task, &action) == AuthorityCode::NoOwner);
    // Stress whole-snapshot publication. Readers cannot see torn context, root
    // revision, generation or effect masks while another thread publishes.
    std::atomic<bool> stop{false};
    std::vector<std::thread> workers;
    for (unsigned n = 0; n < 4; ++n) workers.emplace_back([&] {
        while (!stop.load(std::memory_order_acquire)) {
            if (const auto view = reader.Inspect()) {
                assert(view->current.policyRevision == view->root.revision);
                assert(view->root.revision == view->lease.generation);
                assert(view->lease.context.policyRevision == view->root.revision);
            }
        }
    });
    for (uint64_t revision = 1; revision < 10001; ++revision) {
        AuthoritySnapshot view;
        view.current.policyRevision = view.root.revision = view.lease.generation = revision;
        view.lease.context.policyRevision = revision;
        publisher.Publish(view);
    }
    stop.store(true, std::memory_order_release);
    for (auto& worker : workers) worker.join();
}
