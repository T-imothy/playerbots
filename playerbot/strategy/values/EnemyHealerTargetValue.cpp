
#include "playerbot/playerbot.h"
#include "EnemyHealerTargetValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

ObjectGuid EnemyHealerTargetValue::Calculate()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer())
        return ObjectGuid();

    const std::string interrupt = qualifier;
    const bool raid = bot->GetMap()->IsRaid();
    ObjectGuid offensiveCaster;

    std::list<ObjectGuid> attackers = ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get();
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    for (std::list<ObjectGuid>::iterator i = attackers.begin(); i != attackers.end(); ++i)
    {
        Unit* unit = ai->GetUnit(*i);
        if (!unit || unit == target)
            continue;

        if (sServerFacade.GetDistance2d(bot, unit) > ai->GetRange("spell"))
            continue;

        if (!ai->IsInterruptableSpellCasting(unit, interrupt))
            continue;

        // Raid interrupts also cover dangerous casts by an engaged off-target
        // enemy. Require native cast admission here: do not leave an assigned
        // position chasing a caster, or let an unavailable interrupt mask a
        // reachable one. This includes the pet's own range/cooldown checks.
        if (raid && !ai->CanCastSpell(interrupt, unit, 0))
            continue;

        for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        {
            const Spell* cast = unit->GetCurrentSpell(slot);
            if (!cast || !cast->m_spellInfo || cast->getState() == SPELL_STATE_FINISHED)
                continue;
            if (IsPositiveSpell(cast->m_spellInfo))
                return unit->GetObjectGuid();
            if (raid && offensiveCaster.IsEmpty())
                offensiveCaster = unit->GetObjectGuid();
        }
    }

    // Keep healing/buff casts ahead of the additional damaging-cast fallback.
    // Outside raids, retain the existing enemy-healer selection policy.
    return offensiveCaster;
}
