#include "playerbot/playerbot.h"
#include "PartyCombatSupport.h"
#include "playerbot/ServerFacade.h"

Player* ai::GetPartyCombatAnchor(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    Group* group = bot->GetGroup();
    if (!group || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported())
        return nullptr;

    Player* best = nullptr;
    bool bestIsTank = false;
    for (const auto& slot : group->GetMemberSlots())
    {
        Player* member = sObjectMgr.GetPlayer(slot.guid);
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
            member->IsBeingTeleported() || !bot->IsInMap(member) || !ai->IsSafe(member) ||
            member->duel || !sServerFacade.IsFriendlyTo(bot, member) || !member->IsInCombat() ||
            !bot->IsWithinDistInMap(member, sPlayerbotAIConfig.sightDistance))
            continue;
#ifdef MANGOSBOT_TWO
        if (!(bot->GetPhaseMask() & member->GetPhaseMask())) continue;
#endif

        const bool tank = ai->IsTank(member);
        if (!best || (tank && !bestIsTank) ||
            (tank == bestIsTank && member->GetObjectGuid() < best->GetObjectGuid()))
        {
            best = member;
            bestIsTank = tank;
        }
    }
    return best;
}

bool ai::NeedsPartyCombatSupport(PlayerbotAI* ai)
{
    return ai->IsHeal(ai->GetBot()) && GetPartyCombatAnchor(ai);
}
