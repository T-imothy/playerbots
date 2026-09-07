#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool ai::IsBossEscapeMap(uint32 map)
{
    if (map == 531) return true;
#ifndef MANGOSBOT_ZERO
    if (map == 532 || map == 542 || map == 550 || map == 552 || map == 553 || map == 555) return true;
#endif
#ifdef MANGOSBOT_TWO
    if (map == 602 || map == 603 || map == 604 || map == 624 || map == 658) return true;
#endif
    return false;
}

uint32 ai::NativeBossEscapeSpell(uint32 map, uint32 entry, uint32 cast, bool regular)
{
    if (map == 531 && entry == 15516 && cast == 26083) return 26084;
    if (map == 531 && entry == 15984 && cast == 26038) return 26686;
    // These are verified caster-centred escape mechanics, not an assumption
    // that every damaging AoE should be fled. All other casts retain normal AI.
#ifndef MANGOSBOT_ZERO
    if (map == 532 && entry == 16524 && cast == 29973) return cast; // Aran
    if (map == 542 && entry == 17377 && cast == 30940) return regular ? 33775 : 37371; // Keli'dan warning aura
    if (map == 552 && entry == 20885 && cast == 36142) return cast; // Dalliah: native periodic trigger carries radius.
    if (map == 550 && entry == 19516 && cast == 34162) return 34164; // Void Reaver Pounding channel
    if (map == 553 && entry == 17978) // Thorngrin: channel ticks carry the damage radius.
    {
        if (cast == 34659) return 34660;
        if (cast == 39131) return 39132;
    }
    if (map == 555 && entry == 18708) // Murmur: native SpellEffects dummy dispatch
    {
        if (cast == 33923) return 33666;
        if (cast == 38796) return 38795;
    }
#endif
#ifdef MANGOSBOT_TWO
    if (map == 602 && entry == 28923 && (cast == 52960 || cast == 59835)) return cast; // Loken
    if (map == 603 && entry == 33432 && cast == 63631) return cast; // Leviathan Mk II
    if (map == 604 && entry == 29304 && (cast == 55081 || cast == 59842)) return cast; // Slad'ran
    if (map == 624 && entry == 33993 && (cast == 64216 || cast == 65279)) return cast; // Emalon: native 10/25-player Lightning Nova.
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

uint32 ai::CurrentBossEscapeSpell(Player* bot, Unit* boss)
{
    if (!bot || !boss) return 0;
    if (bot->GetMapId() == 531)
    {
        const uint32 aura = boss->GetEntry() == 15516 ? 26083 : boss->GetEntry() == 15984 ? 26038 : 0;
        return aura && boss->GetSpellAuraHolder(aura, boss->GetObjectGuid()) ? aura : 0;
    }
#ifndef MANGOSBOT_ZERO
    // Burning Nova is triggered instantly. Its warning aura gates the native
    // Fire Nova action, so watching only an active spell misses the escape window.
    if (bot->GetMapId() == 542 && boss->GetEntry() == 17377 && boss->HasAura(30940)) return 30940;
    if (bot->GetMapId() == 552 && boss->GetEntry() == 20885 && boss->HasAura(36142)) return 36142;
#endif
    const Spell* spell = CurrentBossEscapeCast(bot, boss);
    return spell ? spell->m_spellInfo->Id : 0;
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
    if (bot->GetMapId() == 531)
    {
        std::vector<encounter::Circle> threats;
        if (!AQWhirlwindThreats(ai, plan, threats)) return plan;
        unsigned checked = 0;
        for (const auto& point : encounter::EscapeCircles(here, threats))
        {
            if (++checked > 8) break;
            plan.destination = point;
            if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
        }
        plan.active = false;
        return plan;
    }
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* boss = ai->GetUnit(guid);
        if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || boss->HasCharmer() ||
            !bot->IsInMap(boss) || bot->GetDistance(boss) > 100 ||
            std::fabs(boss->GetPositionZ() - here.z) > 8) continue;
        const uint32 spell = CurrentBossEscapeSpell(bot, boss);
        if (!spell)
        {
            if (PlanLokenClosePosition(ai, boss, plan)) return plan;
            continue;
        }
        bool regular = true;
#ifndef MANGOSBOT_ZERO
        regular = bot->GetMap()->IsRegularDifficulty();
#endif
        const uint32 damage = NativeBossEscapeSpell(bot->GetMapId(), boss->GetEntry(), spell, regular);
        if (!damage) continue;
        const float radius = NativeEncounterSpellRadius(damage);
        if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
        const std::vector<encounter::Circle> threats{{
            {boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()}, radius + 2}};
        plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
        plan.boss = boss->GetObjectGuid(); plan.spell = spell;
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
