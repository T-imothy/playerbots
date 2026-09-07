#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool ArchimondeTearsAction::isUseful()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 534 ||
        !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer() ||
        !bot->HasItemCount(24494, 1) || bot->HasAuraType(SPELL_AURA_FEATHER_FALL) ||
        !bot->HasMovementFlag(MOVEFLAG_FALLING) || !ai->IsJumping()) return false;
    // Playerbot knockback handling holds its simulated apex until the native
    // landing deadline. Using its existing deadline avoids inferring descent
    // from a position that intentionally does not advance every frame.
    const int32 remaining = int32(ai->GetJumpTime() - sWorld.GetCurrentMSTime());
    if (remaining <= 0 || remaining > 1500) return false;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() &&
            bot->IsInMap(boss) && boss->GetEntry() == 17968 && bot->GetDistance(boss) <= 150)
            return UseItemIdAction::isUseful();
    }
#endif
    return false;
}

bool ArchimondeTearsAction::Execute(Event& event)
{
    // Ordinary inventory/cooldown/native item spell handling; no aura or
    // fall-information edits to manufacture a successful landing.
    return isUseful() && UseItemIdAction::Execute(event);
}
