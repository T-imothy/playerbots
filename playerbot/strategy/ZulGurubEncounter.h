#pragma once

// Native engagement, independent of a damage marker or a cached attack list.
// Only already engaged creatures in this group's map/instance are admitted.
namespace ai
{
    inline bool ZulGurubGroupMember(Player* bot, Unit* unit)
    {
        if (!bot || !bot->GetGroup() || !unit || !unit->IsPlayer() || !unit->IsInWorld() ||
            !unit->IsAlive() || unit->HasCharmer() || !bot->IsInMap(unit)) return false;
        Player* member = static_cast<Player*>(unit);
        return member->GetGroup() == bot->GetGroup() && !member->IsBeingTeleported();
    }

    inline bool ZulGurubGroupEngaged(Player* bot, Unit* enemy)
    {
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            bot->HasCharmer() || bot->GetMapId() != 309 || !bot->GetGroup() || !enemy ||
            !enemy->IsInWorld() || !enemy->IsAlive() || !enemy->IsInCombat() ||
            enemy->HasCharmer() || !bot->IsInMap(enemy)) return false;
        Unit* victim = enemy->GetVictim();
        if (ZulGurubGroupMember(bot, victim)) return true;
        if (victim && victim->IsInWorld() && bot->IsInMap(victim) &&
            ZulGurubGroupMember(bot, victim->GetMaster())) return true;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (ZulGurubGroupMember(bot, member) &&
                (member->GetVictim() == enemy || enemy->getAttackers().count(member))) return true;
        }
        return false;
    }
}
