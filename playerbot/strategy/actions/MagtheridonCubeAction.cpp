#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

Unit* MagtheridonCubeAction::GetBoss(PlayerbotAI* ai)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 544 || !bot->GetGroup() || !bot->IsInCombat()) return nullptr;
    const EncounterPosition plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("magtheridon cube position")->Get();
    if (plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 30410) return nullptr;
    Unit* boss = ai->GetUnit(plan.boss);
    return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() &&
        boss->GetEntry() == 17257 && bot->IsInMap(boss) && !boss->HasAura(30205) ? boss : nullptr;
#else
    return nullptr;
#endif
}

bool MagtheridonCubeAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
#ifndef MANGOSBOT_ZERO
    Unit* boss = GetBoss(ai);
    Player* bot = ai->GetBot();
    if (!IsMagtheridonCubeUser(ai, bot, boss) || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("magtheridon cube position")->Get();
    if (!plan.active || (!ai->IsRanged(bot) && !IsMagtheridonNova(boss))) return false;
    GameObject* cube = ai->GetGameObject(plan.source);
    Unit* trigger = FindMagtheridonCubeTrigger(bot, cube);
    if (!trigger || trigger->HasAura(30410) || cube->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_IN_USE)) return false;
    const float reach = cube->GetInteractionDistance();
    return std::isfinite(reach) && reach >= 1 && reach <= 10 &&
        std::isfinite(plan.destination.x) && std::isfinite(plan.destination.y) && std::isfinite(plan.destination.z) &&
        cube->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) < reach;
#else
    return false;
#endif
}

bool MagtheridonCubeAction::isUseful()
{
    if (HasMagtheridonChannel(bot)) return !IsMagtheridonNova(GetBoss(ai));
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return false;
    return IsMagtheridonNova(GetBoss(ai)) || bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE;
}

bool MagtheridonCubeAction::isPossible()
{
    return HasMagtheridonChannel(bot) || ai->CanMove();
}

bool MagtheridonCubeAction::ShouldReactionInterruptCast() const
{
    // Do not let selecting the reaction cancel the very cube channel it is
    // meant to preserve. Ordinary class casts yield only to a live Blast Nova.
    if (HasMagtheridonChannel(bot)) return false;
    EncounterPosition plan;
    return GetPlan(ai, plan) && IsMagtheridonNova(GetBoss(ai));
}

bool MagtheridonCubeAction::Execute(Event& event)
{
#ifndef MANGOSBOT_ZERO
    if (HasMagtheridonChannel(bot))
    {
        if (IsMagtheridonNova(GetBoss(ai))) return false;
        // Native channel cancellation removes the beams and applies Mind
        // Exhaustion. Do not remove auras, clear cooldowns or create the cage.
        bot->InterruptSpell(CURRENT_CHANNELED_SPELL);
        SetDuration(100);
        return true;
    }
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    GameObject* cube = ai->GetGameObject(plan.source);
    Unit* trigger = FindMagtheridonCubeTrigger(bot, cube);
    if (!trigger || trigger->HasAura(30410) || cube->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_IN_USE) ||
        cube->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) >= cube->GetInteractionDistance()) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    if (!IsMagtheridonNova(GetBoss(ai))) { SetDuration(100); return true; }
    if (!cube->IsAtInteractDistance(bot) || !bot->IsWithinLOSInMap(cube) ||
        !IsMagtheridonCubeUser(ai, bot, GetBoss(ai))) return false;
    // Same handler as a player's click: native range, GO flags, cube owner,
    // spell admission, beam effects and exhaustion remain authoritative.
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << cube->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(1000); // Bound rejected-click retries; submission is not success.
    return true;
#else
    return false;
#endif
}
