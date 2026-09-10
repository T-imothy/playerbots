#ifndef LIVING_ACTIVITY_SCOPE_H
#define LIVING_ACTIVITY_SCOPE_H
#include "LivingActivityPermissions.h"
#include <optional>

namespace LivingActivity {
    // Synchronous, explicitly supplied executor attribution. This is NOT a
    // grant: every boundary checks the world's latest immutable permission view.
    // Never infer this scope from the current owner or from an action name.
    // Value-only contents; no native pointers or references to the task cache.
    class ExecutionScope {
    public:
        ExecutionScope(Task task, ActionContext action);
        explicit ExecutionScope(NativePermit permit);
        ~ExecutionScope();
        ExecutionScope(const ExecutionScope&) = delete;
        ExecutionScope& operator=(const ExecutionScope&) = delete;
        static AuthorityCode Check(const PermissionReader& reader, const Effects& effects,
            const WorldContext& current, uint64_t now);
        static std::string Origin(uint32_t actor);
    private:
        static thread_local ExecutionScope* head;
        ExecutionScope* previous;
        unsigned depth;
        uint32_t actor;
        std::optional<Task> task;
        std::optional<ActionContext> action;
        std::optional<NativePermit> permit;
    };
}
#endif
