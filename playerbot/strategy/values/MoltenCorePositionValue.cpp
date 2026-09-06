#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Spells/SpellMgr.h"

using namespace ai;

namespace
{
    float NativeRadius(uint32 id, unsigned depth = 0)
    {
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
        if (!spell) return 0;
        float radius = 0;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        {
            radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[effect])));
            if (depth < 2 && spell->EffectTriggerSpell[effect] && spell->EffectTriggerSpell[effect] != id)
                radius = std::max(radius, NativeRadius(spell->EffectTriggerSpell[effect], depth + 1));
        }
        return radius;
    }

    bool Casting(Unit* unit, uint32 id)
    {
        for (CurrentSpellTypes type : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        {
            const Spell* spell = unit->GetCurrentSpell(type);
            if (spell && spell->m_spellInfo->Id == id && spell->getState() != SPELL_STATE_FINISHED) return true;
        }
        return false;
    }
}

EncounterPosition MoltenCorePositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat()) return plan;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && unit->GetMap() == bot->GetMap() && unit->IsAlive() && unit->IsInCombat() &&
            (unit->GetEntry() == 12056 || unit->GetEntry() == 12264)) { boss = unit; break; }
    }
    if (!boss) return plan;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId(); plan.boss = boss->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    std::vector<encounter::Circle> threats;
    const auto add = [&](Unit* center, float radius) {
        if (radius > 0 && radius <= 45 && std::fabs(center->GetPositionZ() - here.z) < 8)
            threats.push_back({{center->GetPositionX(), center->GetPositionY(), center->GetPositionZ()}, radius + 2});
    };
    if (boss->GetEntry() == 12056)
    {
        // Inferno's damage is a native script-triggered spell (19698), not the
        // radius-zero channel. Living Bomb's explosion comes from its DBC trigger.
        if (boss->HasAura(19695) || Casting(boss, 19695)) add(boss, NativeRadius(19698));
        if (boss->HasAura(20478) || Casting(boss, 20478)) add(boss, NativeRadius(20478));
        const float bombRadius = NativeRadius(20475);
        const bool carryingBomb = bot->HasAura(20475);
        if (bot->GetGroup())
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = ref->getSource();
                if (member && member != bot && member->IsInWorld() && member->GetMap() == bot->GetMap() &&
                    member->IsAlive() && (carryingBomb || member->HasAura(20475))) add(member, bombRadius);
            }
    }
    else if ((ai->IsRanged(bot) || ai->IsHeal(bot)) && boss->GetVictim() != bot)
        add(boss, NativeRadius(19712)); // Ranged/healers stay outside Shazzrah's native explosion.
    if (threats.empty()) return plan;
    // Do not freeze an unrelated bot on the other side of the room. Within the
    // danger/approach band, hold the safe position so ordinary chasing cannot undo it.
    bool relevant = bot->HasAura(20475);
    for (const auto& circle : threats)
        relevant = relevant || encounter::Distance2d(here, circle.center) < circle.radius + 8;
    if (!relevant) return plan;
    const auto candidates = encounter::EscapeCircles(here, threats);
    unsigned checked = 0;
    for (const auto& point : candidates)
    {
        if (++checked > 8) break; // Bound native path queries per cached decision.
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan)) return plan;
    }
    plan.active = false;
    return plan;
}
