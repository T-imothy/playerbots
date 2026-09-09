#pragma once

#include "playerbot/PlayerbotAI.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/TargetValue.h"

namespace ai
{
    // Reuse group CC marks, including marks selected by other bots.
    class MeleeCcCheck : public FindNonCcTargetStrategy
    {
    public:
        explicit MeleeCcCheck(PlayerbotAI* ai) : FindNonCcTargetStrategy(ai) {}
        void CheckAttacker(Unit*, ThreatManager*) override {}
        bool Protected(Unit* target)
        {
            return target->HasBreakableByDamageCrowdControlAura() || IsCcTarget(target);
        }
    };

    inline bool MeleeCombatTarget(PlayerbotAI* ai, Unit* target)
    {
        Player* bot = ai->GetBot();
        return target && bot->IsInWorld() && target->IsInWorld() && target->IsAlive() &&
            bot->IsInMap(target) && ai->IsSafe(target) && bot->CanAttack(target) &&
            !MeleeCcCheck(ai).Protected(target);
    }

    // A self-centred melee area is not a ranged cluster. Inspect all nearby
    // hostiles for protected CC, then count only eligible attack targets in 3D.
    inline unsigned SafeMeleeTargetCount(PlayerbotAI* ai, float radius, Unit* centre = nullptr)
    {
        Player* bot = ai->GetBot();
        if (!centre) centre = bot;
        if (!bot->IsInWorld() || !centre->IsInWorld() || !bot->IsInMap(centre)) return 0;
        MeleeCcCheck cc(ai);
        auto context = ai->GetAiObjectContext();
        for (ObjectGuid guid : context->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (unit && unit->IsInWorld() && unit->IsAlive() && centre->IsInMap(unit) &&
                centre->IsWithinDistInMap(unit, radius) && centre->IsWithinLOSInMap(unit) && cc.Protected(unit))
                return 0;
        }
        unsigned count = 0;
        for (ObjectGuid guid : context->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (MeleeCombatTarget(ai, unit) && centre->IsWithinDistInMap(unit, radius) &&
                centre->IsWithinLOSInMap(unit)) ++count;
        }
        return count;
    }

    inline bool MeleeOpportunity(PlayerbotAI* ai)
    {
        Unit* target = ai->GetAiObjectContext()->GetValue<Unit*>("current target")->Get();
        return ai->IsStateActive(BotState::BOT_STATE_COMBAT) && MeleeCombatTarget(ai, target) &&
            ai->GetBot()->CanReachWithMeleeAttack(target);
    }
}
