
#include "playerbot/playerbot.h"
#include "WarriorActions.h"

using namespace ai;

#ifdef MANGOSBOT_TWO
Unit* CastVigilanceAction::GetTarget()
{
    // Native Vigilance redirects the recipient's threat TO this warrior. It is
    // not Misdirection and must not be scheduled as an outgoing tank transfer.
    if (!bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || bot->IsInCombat() ||
        !ai->IsTank(bot) || !bot->HasSpell(50720)) return nullptr;
    Player* candidate = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld()) continue;
        // Preserve an existing assignment even if its recipient moved away.
        // Never repeatedly remove this warrior's aura to put it on someone else.
        if (ai->HasAura("vigilance", member, false, true)) return nullptr;
        if (!member->IsAlive() || member->HasCharmer() || member->IsBeingTeleported() ||
            member->GetMap() != bot->GetMap() || ai->IsTank(member) || ai->IsHeal(member) ||
            ai->HasAura("vigilance", member) || !ai->CanCastSpell(50720, member, 0)) continue;
        // Stable, not random on every update; don't claim an optimal DPS target.
        if (!candidate || member->GetObjectGuid() < candidate->GetObjectGuid()) candidate = member;
    }
    return candidate;
}

bool CastVigilanceAction::isUseful()
{
    return GetTarget() && CastBuffSpellAction::isUseful();
}
#endif

