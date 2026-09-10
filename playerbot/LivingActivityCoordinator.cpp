#include "botpch.h"
#include "Database/DatabaseImpl.h"
#include "LivingActivityCoordinator.h"
#include "LivingActivity.h"
#include "PlayerbotRendezvousManager.h"
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/uuid/name_generator.hpp>
#include <boost/uuid/random_generator.hpp>
#include <boost/uuid/string_generator.hpp>
#include <boost/uuid/uuid_io.hpp>
#include <chrono>
#include <deque>
#include <fstream>
#include <map>
#include <set>
#include <sstream>

using namespace LivingActivity;
namespace {
    uint64_t NowMs() {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }
    std::string NewId() { return boost::uuids::to_string(boost::uuids::random_generator()()); }
    std::string SourceId(const std::string& source, const std::string& key) {
        static const auto ns = boost::uuids::string_generator()("a6dfc222-b146-5f9a-9c85-21519e5e2436");
        // Source keys include the authoritative actor and native record. The
        // character database is the identity scope, including restored copies.
        return boost::uuids::to_string(boost::uuids::name_generator(ns)(source + ':' + key));
    }
    std::string Json(const boost::property_tree::ptree& value) {
        std::ostringstream out; boost::property_tree::write_json(out, value, false); return out.str();
    }
    bool ReadTask(const std::string& payload, Task& task) {
        try {
            boost::property_tree::ptree p; std::istringstream in(payload);
            boost::property_tree::read_json(in, p);
            task.id = p.get<std::string>("id"); task.actor = p.get<uint32_t>("actor");
            task.context.actor = task.actor;
            task.source = p.get<std::string>("source"); task.sourceKey = p.get<std::string>("source_key");
            task.root = p.get<std::string>("root"); task.parent = p.get<std::string>("parent");
            if (!ParseKind(p.get<std::string>("kind"), task.kind) ||
                !ParsePhase(p.get<std::string>("phase"), task.phase)) return false;
            const std::string mode = p.get<std::string>("mode");
            if (mode != "observe" && mode != "active") return false;
            task.mode = mode == "observe" ? Mode::Observe : Mode::Active;
            task.priority = Priority(p.get<unsigned>("priority")); task.accepted = p.get<unsigned>("accepted") != 0;
            task.revision = p.get<uint64_t>("revision"); task.ownerGeneration = p.get<uint64_t>("generation");
            task.context.session = p.get<std::string>("session"); task.context.sessionRevision = p.get<uint64_t>("session_revision");
            task.context.policyRevision = p.get<uint64_t>("policy_revision");
            task.context.map = p.get<uint32_t>("map"); task.context.instance = p.get<uint32_t>("instance");
            task.checkpoint.version = p.get<uint32_t>("checkpoint_version");
            task.checkpoint.step = p.get<std::string>("step"); task.checkpoint.data = p.get<std::string>("checkpoint");
            task.checkpoint.blocker = p.get<std::string>("blocker");
            task.checkpoint.activeElapsedMs = p.get<uint64_t>("active_ms");
            task.checkpoint.lastProgressAtMs = p.get<uint64_t>("progress_at");
            task.dueAtMs = p.get<uint64_t>("due_at"); task.retryAtMs = p.get<uint64_t>("retry_at");
            task.createdAtMs = p.get<uint64_t>("created_at"); task.updatedAtMs = p.get<uint64_t>("updated_at");
            std::string error; return Validate(task, error);
        } catch (const std::exception&) { return false; }
    }
    // Only identifiers and typed source facts enter checkpoints. Do not import
    // arbitrary legacy payloads, user event descriptions or private dialogue.
    std::string ImportQuery(unsigned family, unsigned limit) {
        std::string select, where, order;
        if (family == 0) {
            select = "SELECT 'economy_goal' source,CAST(g.goal_id AS CHAR) source_key,g.character_guid actor,"
                "JSON_OBJECT('goal_id',g.goal_id,'goal_type',g.goal_type,'capability_ref',COALESCE(g.capability_ref,''),"
                "'legacy_phase',g.state,'legacy_expires_at',COALESCE(UNIX_TIMESTAMP(g.expires_at),0)) checkpoint "
                "FROM organic_economy_goal g JOIN characters c ON c.guid=g.character_guid "
                "JOIN tbcrealmd.account a ON a.id=c.account ";
            where = "g.state='active'"; order = "g.goal_id";
        } else if (family == 1) {
            select = "SELECT 'guild_delivery' source,CAST(g.delivery_id AS CHAR) source_key,g.carrier_guid actor,"
                "JSON_OBJECT('delivery_id',g.delivery_id,'guild_id',g.guild_id,'goal_id',g.goal_id,"
                "'item_guid',g.item_guid,'item_entry',g.item_entry,'quantity',g.quantity,'mail_id',g.mail_id,"
                "'legacy_phase',g.phase) checkpoint FROM guild_society_supply_delivery g "
                "JOIN characters c ON c.guid=g.carrier_guid JOIN tbcrealmd.account a ON a.id=c.account ";
            where = "g.phase NOT IN ('completed','cancelled','failed','deposited')"; order = "g.delivery_id";
        } else if (family == 2) {
            select = "SELECT 'commission' source,g.commission_id source_key,g.bot_guid actor,"
                "JSON_OBJECT('commission_id',g.commission_id,'recipe_spell_id',g.recipe_spell_id,"
                "'output_item_entry',g.output_item_entry,'quantity',g.quantity,'legacy_phase',g.state) checkpoint "
                "FROM organic_economy_commission g JOIN characters c ON c.guid=g.bot_guid "
                "JOIN tbcrealmd.account a ON a.id=c.account ";
            where = "g.state IN ('awaiting_materials','materials_received','traveling','crafting','ready')"; order = "g.commission_id";
        } else {
            select = "SELECT 'guild_event' source,CONCAT(g.event_id,':',r.character_guid) source_key,r.character_guid actor,"
                "JSON_OBJECT('event_id',g.event_id,'event_revision',g.revision,'accepted_revision',r.accepted_revision,"
                "'guild_id',g.guild_id,'target_id',g.target_id,'event_type',g.event_type,'scheduled_at',g.scheduled_at,"
                "'legacy_phase',g.state) checkpoint FROM guild_society_event g "
                "JOIN guild_society_rsvp r ON r.event_id=g.event_id JOIN characters c ON c.guid=r.character_guid "
                "JOIN tbcrealmd.account a ON a.id=c.account ";
            where = "r.response='accepted' AND g.state NOT IN ('completed','cancelled','failed','expired','draft')";
            order = "g.event_id,r.character_guid";
        }
        // Sentinel distinguishes a healthy empty result from an SQL failure.
        return "SELECT * FROM (SELECT * FROM (" + select + "WHERE " + where +
            " AND a.username LIKE 'RNDBOT%' ORDER BY " + order + ") candidates WHERE NOT EXISTS "
            "(SELECT 1 FROM living_activity_task t WHERE t.source=candidates.source AND t.source_key=candidates.source_key) LIMIT " +
            std::to_string(limit) + ") bounded UNION ALL SELECT '','',0,'{}'";
    }
}

struct LivingActivityCoordinator::State {
    Mode effective = Mode::Off;
    std::string desired = "off", blocker = "not_enabled", loadCursor;
    uint64_t policyRevision = 0, epoch = 0, nextPolicy = 0, nextWork = 0, nextLog = 0;
    unsigned batch = 32, loadBatch = 64, maxCache = 20000;
    bool ioPending = false, schemaReady = false, loaded = false;
    unsigned importFamily = 0;
    uint64_t acknowledged = 0, persistenceFailures = 0, invalidRecords = 0, transitionCount = 0;
    uint64_t maximumDispatchUs = 0, overBudgetUpdates = 0;
    struct Pending { Task task; WritePlan plan; };
    struct Incoming {
        bool restored = false;
        unsigned family = 0;
        uint32_t actor = 0;
        std::string id, source, key, payload;
    };
    std::deque<Pending> pending;
    std::deque<Incoming> incoming;
    std::map<std::string, Task> cache;
    std::map<uint32_t, std::string> preferred;

    void Policy(uint64_t now) {
        if (now < nextPolicy) return;
        nextPolicy = now + 60000;
        Mode next = Mode::Off; std::string why = "not_enabled"; uint64_t revision = 0;
        try {
            std::ifstream input("/srv/living-wow/config/activities.json");
            if (input) {
                boost::property_tree::ptree p; boost::property_tree::read_json(input, p);
                desired = p.get<std::string>("mode", "off"); revision = p.get<uint64_t>("policyRevision", 0);
                if (p.get<unsigned>("schemaVersion", 0) != 1 || !revision) throw std::invalid_argument("version");
                // Stage 2 cannot accidentally become an executor through config.
                bool execution = false;
                for (const char* flag : {"activityOwnership", "serviceExecution", "resourceClaims", "operationJournal", "socialOutbox"})
                    execution |= p.get<bool>(std::string("features.") + flag, false);
                if (desired != "off" && desired != "observe" && desired != "active") throw std::invalid_argument("mode");
                if (desired == "active" || execution) why = "execution_not_implemented_stage2";
                else if (desired == "observe" && p.get<bool>("features.durableTasks", false)) {
                    batch = p.get<unsigned>("limits.persistenceBatch", 32);
                    loadBatch = p.get<unsigned>("limits.loadBatch", 64);
                    maxCache = p.get<unsigned>("limits.cachedTasks", 20000);
                    if (!batch || batch > 32 || !loadBatch || loadBatch > 64 || maxCache < 64 || maxCache > 20000)
                        throw std::invalid_argument("limits");
                    next = Mode::Observe; why.clear();
                }
            } else desired = "off";
        } catch (const std::exception&) { why = "invalid_activity_configuration"; }
        // Do not invalidate a committed journal acknowledgement on config reload.
        // Its receipts still matter, but no gameplay action is ever dispatched here.
        effective = next; policyRevision = revision;
        if (effective == Mode::Off) blocker = why;
        else if (!schemaReady) blocker = "schema_verification_pending";
    }
    void Remember(const Task& task) {
        cache[task.id] = task;
        const auto existing = preferred.find(task.actor);
        if (existing == preferred.end() || Before(task, cache.at(existing->second))) preferred[task.actor] = task.id;
    }
    void Queue(Task task, uint64_t expected, const std::string& code) {
        if (cache.size() + pending.size() >= maxCache) { blocker = "task_cache_backpressure"; return; }
        auto plan = TaskWrite(task, expected, NewId(), code);
        pending.push_back({std::move(task), std::move(plan)});
    }
    void Flush() {
        const unsigned maximum = std::min<unsigned>(batch, pending.size());
        if (!maximum || !CharacterDatabase.BeginTransaction()) return;
        const auto started = std::chrono::steady_clock::now();
        unsigned count = 0;
        std::string query;
        for (; count < maximum;) {
            for (const auto& sql : pending[count].plan.statements) CharacterDatabase.Execute(sql.c_str());
            if (!query.empty()) query += " UNION ALL ";
            query += pending[count].plan.receiptQuery;
            ++count;
            if (std::chrono::steady_clock::now() - started >= std::chrono::milliseconds(2)) break;
        }
        // One ordered native DB transaction followed by its receipt query. No
        // synchronous DB query or extra worker on the world thread.
        if (!CharacterDatabase.CommitTransaction()) { CharacterDatabase.RollbackTransaction(); return; }
        ioPending = true;
        const auto token = epoch;
        if (!CharacterDatabase.AsyncQuery([this, count, token](QueryResult* result) {
            if (token != epoch) return;
            ioPending = false;
            std::set<std::pair<std::string, uint64_t>> receipts;
            if (result) do { auto* f = result->Fetch(); receipts.emplace(f[0].GetCppString(), f[1].GetUInt64()); }
                while (result->NextRow());
            unsigned accepted = 0;
            // Whole batch is atomic; require every receipt before acknowledging.
            for (unsigned i = 0; i < count; ++i)
                accepted += receipts.count({pending[i].plan.task, pending[i].plan.revision}) != 0;
            if (accepted != count) {
                ++persistenceFailures; blocker = "journal_receipt_not_verified"; nextWork = NowMs() + 5000; return;
            }
            for (unsigned i = 0; i < count; ++i) { Remember(pending.front().task); pending.pop_front(); ++acknowledged; ++transitionCount; }
            blocker.clear();
        }, query.c_str())) { ioPending = false; blocker = "journal_ack_queue_unavailable"; nextWork = NowMs() + 5000; }
    }
    void Probe() {
        ioPending = true;
        // Explicit required columns plus version; querying a version row alone
        // would accept a partially applied schema. The empty task table is valid.
        const std::string sql = "SELECT version,(SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND ((table_name='living_activity_task' AND column_name IN "
            "('task_id','source','source_key','revision','owner_generation','checkpoint','last_receipt_id')) OR "
            "(table_name='living_activity_transition' AND column_name IN ('sequence_id','transition_id','request_hash')) OR "
            "(table_name='living_activity_operation' AND column_name IN ('operation_id','state')) OR "
            "(table_name='living_activity_claim' AND column_name IN ('claim_id','task_id')))),"
            "(SELECT COUNT(*) FROM living_activity_transition) FROM living_activity_schema WHERE version=1";
        if (!CharacterDatabase.AsyncQuery([this](QueryResult* result) {
            ioPending = false;
            schemaReady = result && result->Fetch()[0].GetUInt32() == 1 && result->Fetch()[1].GetUInt32() == 14;
            if (schemaReady) transitionCount = result->Fetch()[2].GetUInt64();
            blocker = schemaReady ? "startup_reconciliation" : "activity_schema_unavailable";
            nextWork = NowMs() + (schemaReady ? 1000 : 60000);
        }, sql.c_str())) { ioPending = false; nextWork = NowMs() + 60000; }
    }
    void Load() {
        const std::string projection = "JSON_OBJECT('id',task_id,'actor',actor_guid,'source',source,'source_key',source_key,"
            "'root',root_task_id,'parent',parent_task_id,'kind',kind,'mode',mode,'phase',phase,'priority',priority,"
            "'accepted',accepted,'revision',revision,'generation',owner_generation,'session',session_id,"
            "'session_revision',session_revision,'policy_revision',policy_revision,'map',map_id,'instance',instance_id,"
            "'checkpoint_version',checkpoint_version,'step',step,'checkpoint',checkpoint,'blocker',blocker,"
            "'active_ms',active_elapsed_ms,'progress_at',last_progress_at_ms,'due_at',due_at_ms,'retry_at',retry_at_ms,"
            "'created_at',created_at_ms,'updated_at',updated_at_ms)";
        const std::string sql = "SELECT * FROM (SELECT task_id," + projection + " payload FROM living_activity_task "
            "WHERE phase NOT IN ('completed','cancelled','failed') AND task_id>" + SqlValue(loadCursor) +
            " ORDER BY task_id LIMIT " + std::to_string(loadBatch) + ") records UNION ALL SELECT '','{}'";
        ioPending = true;
        if (!CharacterDatabase.AsyncQuery([this](QueryResult* result) {
            ioPending = false;
            if (!result) { blocker = "task_load_query_failed"; nextWork = NowMs() + 5000; return; }
            unsigned count = 0;
            do {
                auto* f = result->Fetch(); const std::string id = f[0].GetCppString(); if (id.empty()) continue;
                incoming.push_back({true, 0, 0, id, "", "", f[1].GetCppString()}); ++count;
            } while (result->NextRow());
            if (count < loadBatch) loaded = true;
        }, sql.c_str())) { ioPending = false; nextWork = NowMs() + 5000; }
    }
    void Import() {
        const unsigned family = importFamily;
        const auto query = ImportQuery(family, batch);
        ioPending = true;
        if (!CharacterDatabase.AsyncQuery([this, family](QueryResult* result) {
            ioPending = false;
            if (!result) { blocker = "legacy_import_query_failed"; nextWork = NowMs() + 60000; return; }
            unsigned count = 0;
            do {
                auto* f = result->Fetch(); std::string source = f[0].GetCppString(); if (source.empty()) continue;
                incoming.push_back({false, family, f[2].GetUInt32(), "", source,
                    f[1].GetCppString(), f[3].GetCppString()}); ++count;
            } while (result->NextRow());
            // One domain cannot monopolize admission. A full rotation pauses
            // one minute only when there is no backlog in the observed domain.
            importFamily = (family + 1) % 4;
            if (importFamily == 0 && count == 0) nextWork = NowMs() + 60000;
        }, query.c_str())) { ioPending = false; nextWork = NowMs() + 5000; }
    }
    void DecodeIncoming() {
        const auto started = std::chrono::steady_clock::now();
        do {
            if (cache.size() + pending.size() >= maxCache) {
                blocker = "task_cache_backpressure"; nextWork = NowMs() + 60000; return;
            }
            const auto& row = incoming.front(); Task task;
            if (row.restored) {
                if (!ReadTask(row.payload, task)) {
                    ++invalidRecords; blocker = "invalid_persisted_task"; nextWork = NowMs() + 60000; return;
                }
                // Active tasks are never downgraded or executed by this observer.
                if (task.mode == Mode::Active) { Remember(task); blocker = "active_task_requires_executor"; }
                else Queue(AfterRestart(task, NowMs()), task.revision, "restart_revalidation");
                loadCursor = row.id;
            } else {
                task.source = row.source; task.sourceKey = row.key;
                task.id = task.root = SourceId(task.source, task.sourceKey);
                task.actor = task.context.actor = row.actor;
                task.kind = row.family == 0 ? Kind::CollectionReconciliation : row.family == 1 ? Kind::GuildDelivery :
                    row.family == 2 ? Kind::Commission : Kind::GuildEvent;
                if (row.family == 0) {
                    boost::property_tree::ptree p; std::istringstream in(row.payload);
                    boost::property_tree::read_json(in, p);
                    const auto type = p.get<std::string>("goal_type", "");
                    if (type == "profession_skill_up") task.kind = Kind::Profession;
                    else if (type == "storage_pressure" || type == "maintain_supplies") task.kind = Kind::Maintenance;
                    else if (type == "gear_upgrade") task.kind = Kind::Progression;
                }
                task.priority = row.family == 3 ? Priority::Scheduled : Priority::Delivery;
                task.context.policyRevision = policyRevision;
                task.createdAtMs = task.updatedAtMs = NowMs();
                task.checkpoint.data = row.payload;
                task.checkpoint.blocker = "legacy_work_requires_native_reconciliation";
                Queue(std::move(task), 0, "legacy_observed");
            }
            incoming.pop_front();
        } while (!incoming.empty() && std::chrono::steady_clock::now() - started < std::chrono::milliseconds(2));
    }
};

LivingActivityCoordinator& LivingActivityCoordinator::instance() {
    static LivingActivityCoordinator singleton; return singleton;
}
LivingActivityCoordinator::LivingActivityCoordinator() : state(new State) {}
LivingActivityCoordinator::~LivingActivityCoordinator() = default;
void LivingActivityCoordinator::Update() {
    const auto started = std::chrono::steady_clock::now();
    struct Measure {
        State& state; std::chrono::steady_clock::time_point start;
        ~Measure() {
            const auto us = uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::steady_clock::now() - start).count());
            state.maximumDispatchUs = std::max(state.maximumDispatchUs, us);
            if (us > 2000) ++state.overBudgetUpdates;
        }
    } measure{*state, started};
    const uint64_t now = NowMs();
    state->Policy(now);
    if (state->effective == Mode::Off || state->ioPending) return;
    if (!state->incoming.empty()) {
        if (now < state->nextWork) return;
        try { state->DecodeIncoming(); }
        catch (const std::exception&) { ++state->invalidRecords; state->blocker = "invalid_source_record"; state->nextWork = now + 60000; }
        return;
    }
    if (now < state->nextWork) return;
    state->nextWork = now + 1000;
    if (!state->schemaReady) state->Probe();
    else if (state->transitionCount + state->pending.size() >= 200000) state->blocker = "transition_outbox_backpressure";
    else if (!state->pending.empty()) state->Flush();
    else if (!state->loaded) state->Load();
    else if (state->cache.size() < state->maxCache) state->Import();
    else state->blocker = "task_cache_backpressure";
    if (now >= state->nextLog) {
        state->nextLog = now + 60000;
        sLog.outString("Living activity shadow: %s", StatusJson().c_str());
    }
}
std::string LivingActivityCoordinator::StatusJson() const {
    boost::property_tree::ptree p;
    p.put("contract_version", 1); p.put("desired_mode", state->desired); p.put("effective_mode", Name(state->effective));
    p.put("policy_revision", state->policyRevision); p.put("blocker", state->blocker);
    p.put("cached_tasks", state->cache.size()); p.put("pending_writes", state->pending.size());
    p.put("receipt_count", state->acknowledged); p.put("persistence_failures", state->persistenceFailures);
    p.put("retained_transitions", state->transitionCount);
    p.put("pending_decode", state->incoming.size()); p.put("maximum_dispatch_us", state->maximumDispatchUs);
    p.put("over_budget_updates", state->overBudgetUpdates); p.put("next_import_family", state->importFamily);
    p.put("invalid_records", state->invalidRecords); p.put("gameplay_mutations", 0);
    p.put("snapshot_at_ms", NowMs()); return Json(p);
}
std::string LivingActivityCoordinator::ActorJson(uint32_t guid) const {
    boost::property_tree::ptree p;
    p.put("actor_guid", guid); p.put("effective_mode", Name(state->effective));
    p.put("execution_owner", PlayerbotRendezvousManager::PartyActivityOwnerName(
        PlayerbotRendezvousManager::instance().GetPartyActivityOwner(guid)));
    auto selected = state->preferred.find(guid);
    if (selected != state->preferred.end()) {
        const Task& task = state->cache.at(selected->second);
        p.put("shadow_task_id", task.id); p.put("task_revision", task.revision);
        p.put("phase", Name(task.phase)); p.put("step", task.checkpoint.step);
        p.put("blocker", task.checkpoint.blocker); p.put("active_elapsed_ms", task.checkpoint.activeElapsedMs);
        p.put("source", task.source); p.put("last_progress_at_ms", task.checkpoint.lastProgressAtMs);
    }
    return Json(p);
}
