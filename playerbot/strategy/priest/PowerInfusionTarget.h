#pragma once
#include "playerbot/strategy/actions/HealerSupportActions.h"

namespace ai
{
    inline Unit* SelectPowerInfusionTarget(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            !bot->IsInCombat() || !ai->HasSpell("power infusion") ||
            HasHealingPressure(ai, sPlayerbotAIConfig.lowHealth)) return nullptr;

        const auto eligible = [&](Unit* unit) {
            return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) &&
                bot->IsInGroup(unit) && ai->IsSafe(unit) && sServerFacade.IsFriendlyTo(bot, unit) &&
                !ai->HasAura("power infusion", unit) && ai->CanCastSpell("power infusion", unit, 0);
        };
        // An explicit player assignment takes precedence over automatic ranking.
        const auto assigned = ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("boost targets")->Get();
        if (!assigned.empty())
        {
            for (ObjectGuid guid : assigned)
                if (Unit* unit = ai->GetUnit(guid))
                    if (eligible(unit)) return unit;
            return nullptr;
        }
        Group* group = bot->GetGroup();
        if (!group || (!group->IsRaidGroup() && !bot->GetMap()->IsRaid()))
            return eligible(bot) ? bot : nullptr;

        Player* best = nullptr;
        int bestRank = 3;
        for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || !member->IsInWorld() || member->IsBeingTeleported() ||
                !member->IsInCombat() || !eligible(member) || ai->IsHeal(member) || ai->IsTank(member) ||
                !ai->IsRanged(member) || !member->GetMaxPower(POWER_MANA) ||
                uint64(member->GetPower(POWER_MANA)) * 100 < uint64(member->GetMaxPower(POWER_MANA)) * 10)
                continue;
            const uint8 cls = member->getClass();
            if (cls != CLASS_MAGE && cls != CLASS_WARLOCK && cls != CLASS_PRIEST &&
                cls != CLASS_DRUID && cls != CLASS_SHAMAN) continue;
#ifndef MANGOSBOT_ZERO
            // The native haste effects cannot benefit a target already using these.
            if (ai->HasAura("bloodlust", member) || ai->HasAura("heroism", member)) continue;
#endif
            const int rank = (cls == CLASS_MAGE || cls == CLASS_WARLOCK) ? 0 : 1;
            if (!best || rank < bestRank || (rank == bestRank && member->GetObjectGuid() < best->GetObjectGuid()))
            {
                best = member;
                bestRank = rank;
            }
        }
        // A healing priest does not spend this offensive cooldown on itself
        // merely because every suitable DPS target is unavailable.
        return best;
    }
}
