#ifndef LIVING_ACTIVITY_CODEC_H
#define LIVING_ACTIVITY_CODEC_H
#include "LivingActivity.h"
#include <boost/property_tree/json_parser.hpp>
#include <sstream>

namespace LivingActivity {
    // Shared by the live loader and native MariaDB integration tests. Error
    // codes are bounded facts; never put raw checkpoint/player text in logs.
    inline bool DecodeTaskProjection(const std::string& payload, Task& task, std::string& error) {
        error = "invalid_task_projection";
        try {
            boost::property_tree::ptree p; std::istringstream in(payload);
            boost::property_tree::read_json(in, p);
            task.id = p.get<std::string>("id"); task.actor = p.get<uint32_t>("actor");
            task.context.actor = task.actor;
            task.source = p.get<std::string>("source"); task.sourceKey = p.get<std::string>("source_key");
            task.root = p.get<std::string>("root"); task.parent = p.get<std::string>("parent");
            if (!ParseKind(p.get<std::string>("kind"), task.kind)) { error = "unsupported_task_kind"; return false; }
            if (!ParsePhase(p.get<std::string>("phase"), task.phase)) { error = "unsupported_task_phase"; return false; }
            const std::string mode = p.get<std::string>("mode");
            if (mode != "observe" && mode != "active") { error = "unsupported_task_mode"; return false; }
            task.mode = mode == "observe" ? Mode::Observe : Mode::Active;
            const unsigned priority = p.get<unsigned>("priority"), accepted = p.get<unsigned>("accepted");
            if (priority > 255 || accepted > 1) { error = "invalid_task_priority_or_acceptance"; return false; }
            task.priority = Priority(priority); task.accepted = accepted != 0;
            task.revision = p.get<uint64_t>("revision"); task.ownerGeneration = p.get<uint64_t>("generation");
            task.context.session = p.get<std::string>("session"); task.context.sessionRevision = p.get<uint64_t>("session_revision");
            task.context.policyRevision = p.get<uint64_t>("policy_revision");
            task.context.map = p.get<uint32_t>("map"); task.context.instance = p.get<uint32_t>("instance");
            task.checkpoint.version = p.get<uint32_t>("checkpoint_version");
            task.checkpoint.step = p.get<std::string>("step"); task.checkpoint.data = p.get<std::string>("checkpoint");
            // A nested object here indicates a broken row projection. Do not
            // silently turn it into an empty checkpoint and invent continuation.
            if (task.checkpoint.data.empty()) { error = "checkpoint_text_not_preserved"; return false; }
            task.checkpoint.blocker = p.get<std::string>("blocker");
            task.checkpoint.activeElapsedMs = p.get<uint64_t>("active_ms");
            task.checkpoint.lastProgressAtMs = p.get<uint64_t>("progress_at");
            task.dueAtMs = p.get<uint64_t>("due_at"); task.retryAtMs = p.get<uint64_t>("retry_at");
            task.createdAtMs = p.get<uint64_t>("created_at"); task.updatedAtMs = p.get<uint64_t>("updated_at");
            return Validate(task, error);
        } catch (const std::exception&) { return false; }
    }
}
#endif
