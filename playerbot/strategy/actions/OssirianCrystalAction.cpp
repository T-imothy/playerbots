#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool OssirianCrystalAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 509 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("ossirian crystal position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 25192) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    GameObject* crystal = ai->GetGameObject(plan.source);
    return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() &&
        !boss->HasCharmer() && bot->IsInMap(boss) && boss->GetEntry() == 15339 && IsOssirianCrystal(bot, crystal) &&
        ((boss->GetVictim() == bot && ai->IsTank(bot)) || OssirianCrystalUser(ai, boss, crystal) == bot);
}

bool OssirianCrystalAction::isUseful()
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan)) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    return bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE ||
        (boss->GetVictim() != bot && OssirianNeedsCrystal(boss));
}

bool OssirianCrystalAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f ||
        OssirianNeedsCrystal(ai->GetUnit(plan.boss)));
}

bool OssirianCrystalAction::Execute(Event& event)
{
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f)
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    ai->StopMoving();
    Unit* boss = ai->GetUnit(plan.boss);
    GameObject* crystal = ai->GetGameObject(plan.source);
    if (!boss || boss->GetVictim() == bot || !OssirianNeedsCrystal(boss)) { SetDuration(100); return true; }
    const float radius = NativeEncounterSpellRadius(25177);
    Unit* trigger = FindOssirianCrystalTrigger(bot, crystal);
    const bool inRange = crystal &&
#ifdef MANGOSBOT_ZERO
        crystal->IsWithinDistInMap(bot, crystal->GetInteractionDistance());
#else
        crystal->IsAtInteractDistance(bot);
#endif
    if (!trigger || !std::isfinite(radius) || radius <= 2 || radius > 60 ||
        boss->GetDistance(trigger) >= radius - 2 || !boss->IsWithinLOSInMap(trigger, true) ||
        OssirianCrystalUser(ai, boss, crystal) != bot || !inRange ||
        !bot->IsWithinLOSInMap(crystal)) { SetDuration(1000); return false; }
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << crystal->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(1000); // Native handler and boss SpellHit decide whether it succeeded.
    return true;
}
