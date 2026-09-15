#include "playerbot/playerbot.h"
#include "BotReliabilityValue.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

namespace
{
bool CanTemporarilyIgnore(PlayerbotAI* ai, Unit* target)
{
    Player* bot = ai->GetBot();
    if (!target || !target->IsAlive() || !target->IsInWorld() || !bot->IsInMap(target) ||
        target->GetTypeId() != TYPEID_UNIT || target->HasCharmer() || target->GetOwnerGuid() ||
        sServerFacade.IsFriendlyTo(bot, target) || bot->IsWithinLOSInMap(target, true)) return false;
    // Do not abandon opponents fighting us, our party or its pets. Protect the
    // master's explicit selection too, even before that enemy enters combat.
    Unit* victim = target->GetVictim();
    if (victim && (victim == bot || bot->IsInGroup(victim) ||
        victim == bot->GetPet() || victim == ai->GetMaster())) return false;
    if (Player* master = ai->GetMaster())
        if (master->GetSelectionGuid() == target->GetObjectGuid()) return false;
    AiObjectContext* context = ai->GetAiObjectContext();
    return AI_VALUE(ObjectGuid, "attack target") != target->GetObjectGuid() &&
        AI_VALUE(Unit*, "pull target") != target;
}
}

bool ai::ObserveUnreachableTarget(PlayerbotAI* ai, Unit* target)
{
    if (!sPlayerbotAIConfig.unreachableTargetRecovery) return false;
    Player* bot = ai->GetBot();
    AiObjectContext* context = ai->GetAiObjectContext();
    auto& state = AI_VALUE(BotReliabilityState&, "bot reliability");
    const uint32 now = WorldTimer::getMSTime();
    if (!state.pursuit.Observe(target->GetObjectGuid().GetRawValue(), bot->GetMapId(), bot->GetInstanceId(),
        now, bot->GetDistance(target), bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ(),
        CanTemporarilyIgnore(ai, target))) return false;
    state.unreachable.Add(target->GetObjectGuid().GetRawValue(), bot->GetMapId(), bot->GetInstanceId(), now);
    state.pursuit.Reset();
    state.incidents.unreachableTarget = target->GetObjectGuid().GetRawValue();
    BotIncidentHistory::Unreachable(ai);
    // The normal invalid-target decision will reselect from the same bounded
    // exclusion list. Stop this bot's obsolete chase, never the creature's AI.
    ai->StopMoving();
    return true;
}

bool ai::IsUnreachableTarget(PlayerbotAI* ai, Unit* target)
{
    if (!sPlayerbotAIConfig.unreachableTargetRecovery || !CanTemporarilyIgnore(ai, target)) return false;
    AiObjectContext* context = ai->GetAiObjectContext();
    Player* bot = ai->GetBot();
    return AI_VALUE(BotReliabilityState&, "bot reliability").unreachable.Contains(
        target->GetObjectGuid().GetRawValue(), bot->GetMapId(), bot->GetInstanceId(), WorldTimer::getMSTime());
}
