#include "playerbot/playerbot.h"
#include "BotPartyCommands.h"
#include "ServerFacade.h"
#include "strategy/actions/BotCommandAccess.h"
#include "strategy/actions/PullDiagnostics.h"
#include "strategy/generic/PullStrategy.h"
#include <array>
#include <mutex>

using namespace ai;
namespace
{
enum class Kind { Interrupt, Control, Pull };
struct Request
{
    uint64 id = 0;
    ObjectGuid owner, target;
    uint32 started = 0, map = 0, instance = 0;
    Kind kind = Kind::Interrupt;
    bool claimed = false;
};
std::mutex requestMutex;
std::array<Request, 64> requests{};
uint64 sequence = 0;
const char* Name(Kind kind)
{
    return kind == Kind::Interrupt ? "interrupt" : kind == Kind::Control ? "cc" : "pull";
}
void Reply(PlayerbotAI* ai, Player* owner, const Request& request, const std::string& result)
{
    ai->TellPlayerNoFacing(owner, std::string("Party ") + Name(request.kind) + ": " + result,
        PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, true, false, true, true);
}
}

bool BotPartyCommands::Queue(Player* owner, const std::string& original, unsigned type)
{
    if (!sPlayerbotAIConfig.partyCommandCoordinator || !owner || !owner->isRealPlayer() ||
        (type != CHAT_MSG_PARTY && type != CHAT_MSG_RAID && type != CHAT_MSG_WHISPER)) return false;
    std::string text = original;
    const auto& prefix = sPlayerbotAIConfig.commandPrefix;
    if (!prefix.empty())
    {
        if (text.compare(0, prefix.size(), prefix)) return false;
        text.erase(0, prefix.size());
    }
    Kind kind;
    if (text == "party interrupt") kind = Kind::Interrupt;
    else if (text == "party cc") kind = Kind::Control;
    else if (text == "party pull") kind = Kind::Pull;
    else return false;
    // One outstanding request per owner. The target is snapshotted here;
    // selecting another enemy later must not redirect a delayed interrupt.
    if (!owner->GetGroup() || !owner->GetSelectionGuid()) return true;
    const uint32 now = WorldTimer::getMSTime();
    std::lock_guard<std::mutex> lock(requestMutex);
    Request* slot = nullptr;
    for (auto& request : requests)
    {
        if (request.id && request.owner == owner->GetObjectGuid())
        {
            if (request.claimed || uint32(now - request.started) < 1000) return true;
            slot = &request; break;
        }
        if (!request.id || uint32(now - request.started) > 10000) slot = &request;
    }
    if (slot) *slot = {++sequence, owner->GetObjectGuid(), owner->GetSelectionGuid(), now,
        owner->GetMapId(), owner->GetInstanceId(), kind, false};
    return true;
}

bool BotPartyCommands::Update(PlayerbotAI* ai)
{
    if (!sPlayerbotAIConfig.partyCommandCoordinator) return false;
    Player* bot = ai->GetBot();
    Player* owner = ai->GetMaster();
    if (!owner || !owner->isRealPlayer() || !bot->IsInWorld() || bot->IsBeingTeleported() ||
        !bot->IsInMap(owner) || !bot->GetGroup() || bot->GetGroup() != owner->GetGroup() ||
        !CanManageBotCommands(ai, owner)) return false;
    Request request;
    const uint32 now = WorldTimer::getMSTime();
    bool expired = false;
    {
        std::lock_guard<std::mutex> lock(requestMutex);
        for (auto& current : requests)
            if (current.id && !current.claimed && current.owner == owner->GetObjectGuid())
            {
                request = current;
                if (uint32(now - current.started) >= 3000)
                { current = {}; expired = true; }
                break;
            }
    }
    if (!request.id) return false;
    if (expired) { Reply(ai, owner, request, "no available bot accepted the command."); return false; }
    if (request.map != bot->GetMapId() || request.instance != bot->GetInstanceId() ||
        !bot->IsAlive() || bot->HasCharmer() || bot->IsNonMeleeSpellCasted(true)) return false;
    Unit* target = ai->GetUnit(request.target);
    if (!target || !target->IsAlive() || !target->IsInWorld() || !bot->IsInMap(target) ||
        sServerFacade.IsFriendlyTo(bot, target)) return false;

    const char* spell = nullptr;
    if (request.kind == Kind::Pull)
    {
        // Prefer an available tank briefly, then allow another equipped
        // puller. The explicit individual command remains the body-pull path.
        if (owner->GetSelectionGuid() != request.target ||
            (!ai->IsTank(bot) && uint32(now - request.started) < 500) ||
            GetPullReadiness(ai, target) != PullFailure::None) return false;
    }
    else
    {
        if (request.kind == Kind::Interrupt && !target->IsNonMeleeSpellCasted(true)) return false;
        if (request.kind == Kind::Control && target->GetTypeId() != TYPEID_UNIT) return false;
        const char* interrupts[] = {"kick", "pummel", "shield bash", "counterspell",
#ifdef MANGOSBOT_TWO
            "wind shear", "mind freeze",
#else
            "earth shock",
#endif
            "silence"};
        const char* controls[] = {"polymorph", "shackle undead", "hibernate", "banish"};
        auto consider = [&](const char* name) {
            if (!spell && ai->CanCastSpell(name, target, 0) && !ai->HasAura(name, target)) spell = name;
        };
        if (request.kind == Kind::Interrupt) for (const char* name : interrupts) consider(name);
        else for (const char* name : controls) consider(name);
        if (!spell) return false;
    }
    {
        std::lock_guard<std::mutex> lock(requestMutex);
        bool claimed = false;
        for (auto& current : requests)
            if (current.id == request.id && !current.claimed)
            { current.claimed = true; claimed = true; break; }
        if (!claimed) return false;
    }
    bool accepted;
    if (request.kind == Kind::Pull)
    {
        Event event("pull", "", owner);
        accepted = ai->DoSpecificAction("pull my target", event, true);
    }
    else accepted = ai->CastSpell(spell, target);
    {
        std::lock_guard<std::mutex> lock(requestMutex);
        for (auto& current : requests)
            if (current.id == request.id)
            {
                if (accepted) current = {};
                else current.claimed = false; // Another capable bot may try.
                break;
            }
    }
    if (accepted) Reply(ai, owner, request, std::string(bot->GetName()) + " accepted" +
        (spell ? std::string(" (") + spell + ")." : "."));
    // Acceptance means the cast/pull was started, not that a spell landed.
    return accepted;
}
