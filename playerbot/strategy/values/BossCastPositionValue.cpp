#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool ai::IsBossEscapeMap(uint32 map)
{
#ifndef MANGOSBOT_ZERO
    if (map == 532 || map == 550 || map == 555) return true;
#endif
#ifdef MANGOSBOT_TWO
    if (map == 602 || map == 603 || map == 658) return true;
#endif
    return false;
}

uint32 ai::NativeBossEscapeSpell(uint32 map, uint32 entry, uint32 cast)
{
    // These are verified caster-centred escape mechanics, not an assumption
    // that every damaging AoE should be fled. All other casts retain normal AI.
#ifndef MANGOSBOT_ZERO
    if (map == 532 && entry == 16524 && cast == 29973) return cast; // Aran
    if (map == 550 && entry == 19516 && cast == 34162) return 34164; // Void Reaver Pounding channel
    if (map == 555 && entry == 18708) // Murmur: native SpellEffects dummy dispatch
    {
        if (cast == 33923) return 33666;
        if (cast == 38796) return 38795;
    }
#endif
#ifdef MANGOSBOT_TWO
    if (map == 602 && entry == 28923 && (cast == 52960 || cast == 59835)) return cast; // Loken
    if (map == 603 && entry == 33432 && cast == 63631) return cast; // Leviathan Mk II
    if (map == 658 && entry == 36476 && cast == 68989) return cast; // Ick
#endif
    return 0;
}

const Spell* ai::CurrentBossEscapeCast(Player* bot, Unit* boss)
{
    if (!bot || !boss) return nullptr;
    // Keep the active tank planted during Pounding; other melee can leave its
    // native radius without dragging the boss or synthesizing a taunt.
    if (bot->GetMapId() == 550 && boss->GetEntry() == 19516 && boss->GetVictim() == bot) return nullptr;
    for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
    {
        const Spell* spell = boss->GetCurrentSpell(slot);
        if (spell && spell->m_spellInfo && spell->getState() != SPELL_STATE_FINISHED &&
            NativeBossEscapeSpell(bot->GetMapId(), boss->GetEntry(), spell->m_spellInfo->Id)) return spell;
    }
    return nullptr;
}

EncounterPosition BossCastPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !bot->IsInCombat() || !IsBossEscapeMap(bot->GetMapId())) return plan;
    // Flame Wreath's native movement restriction takes precedence if mechanics
    // overlap. This never removes its aura or moves a player through the ring.
    if (bot->GetMapId() == 532 && AI_VALUE(bool, "aran flame wreath")) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* boss = ai->GetUnit(guid);
        if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || boss->HasCharmer() ||
            !bot->IsInMap(boss) || bot->GetDistance(boss) > 100 ||
            std::fabs(boss->GetPositionZ() - here.z) > 8) continue;
        const Spell* spell = CurrentBossEscapeCast(bot, boss);
        if (!spell) continue;
        const uint32 damage = NativeBossEscapeSpell(bot->GetMapId(), boss->GetEntry(), spell->m_spellInfo->Id);
        if (!damage) continue;
        const float radius = NativeEncounterSpellRadius(damage);
        if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
        const std::vector<encounter::Circle> threats{{
            {boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()}, radius + 2}};
        plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
        plan.boss = boss->GetObjectGuid(); plan.spell = spell->m_spellInfo->Id;
        unsigned checked = 0;
        for (const auto& point : encounter::EscapeCircles(here, threats))
        {
            if (++checked > 8) break;
            plan.active = true; plan.destination = point;
            if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
        }
        // Never invent a safe point or prevent ordinary AI when none is reachable.
        plan.active = false;
        return plan;
    }
    return plan;
}
