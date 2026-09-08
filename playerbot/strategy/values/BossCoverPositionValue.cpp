#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#ifdef MANGOSBOT_TWO
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#endif

using namespace ai;

bool ai::IsBossCoverMap(uint32 map)
{
    if (map == 469 || map == 533) return true;
#ifndef MANGOSBOT_ZERO
    if (map == 556) return true;
#endif
#ifdef MANGOSBOT_TWO
    if (map == 658 || map == 631) return true;
#endif
    return false;
}

uint32 ai::BossCoverMechanic(PlayerbotAI* ai, Unit* boss, bool keepCover)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        ai->IsRealPlayer() || !boss || !boss->IsInWorld() || !boss->IsAlive() ||
        boss->HasCharmer() || !bot->IsInMap(boss) || bot->GetDistance(boss) > 100 ||
        std::fabs(bot->GetPositionZ() - boss->GetPositionZ()) > 8) return 0;
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 631)
    {
        if (bot->HasAura(70157) || bot->HasAura(70126)) return 0;
        if (boss->GetEntry() == 36853 && CurrentBossEscapeSpell(bot, boss)) return 0;
        if (boss->GetEntry() == 37186 && boss->HasAura(70022))
        {
            // Markers need not be in combat. Only a live encounter owner's
            // actual warning marker supplies the origin of the incoming bomb.
            Unit* owner = ai->GetUnit(boss->GetSpawnerGuid());
            return owner && owner->GetEntry() == 36853 && owner->IsInWorld() && owner->IsAlive() &&
                owner->IsInCombat() && !owner->HasCharmer() && bot->IsInMap(owner) ? 69845 : 0;
        }
        if (boss->GetEntry() == 36853 && boss->IsInCombat() && boss->GetVictim() != bot)
            for (uint32 spell : {70127u, 72528u, 72529u, 72530u})
                if (const SpellAuraHolder* buffet = bot->GetSpellAuraHolder(spell, boss->GetObjectGuid()))
                    if (keepCover || buffet->GetStackAmount() >= 5) return spell;
        return 0;
    }
#endif
    if (!boss->IsInCombat()) return 0;
    // Native Sapphiron has different breath timing between eras. Air-phase
    // hover and an actual blocking Ice Block give warning even when the
    // Wrath payload has no interruptible cast bar.
    if (bot->GetMapId() == 533 && boss->GetEntry() == 15989)
        return boss->HasAura(18430) && !bot->HasAura(28522) && !bot->HasAura(31800) ? 28524 : 0;
    if (bot->GetMapId() == 469)
    {
        // The native current tank keeps the dragon anchored for the raid.
        if (boss->GetVictim() == bot) return 0;
        if (boss->GetEntry() == 11983)
        {
            const SpellAuraHolder* buffet = bot->GetSpellAuraHolder(23341, boss->GetObjectGuid());
            return buffet && (keepCover || buffet->GetStackAmount() >= 5) ? 23341 : 0;
        }
        if (boss->GetEntry() != 14020) return 0;
        const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (!cast || !cast->m_spellInfo || cast->getState() != SPELL_STATE_CASTING) return 0;
        switch (cast->m_spellInfo->Id)
        {
            // Both native left/right variants of each chosen breath.
            case 23187: case 23189: case 23308: case 23309: case 23310:
            case 23312: case 23313: case 23314: case 23315: case 23316:
                return cast->m_spellInfo->Id;
            default: return 0;
        }
    }
#ifndef MANGOSBOT_ZERO
    if (bot->GetMapId() == 556 && boss->GetEntry() == 18473)
    {
        // Ikiss stays scripted in place during his post-Blink explosion. His
        // tank also needs actual cover; a radial run cannot substitute for it.
        const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (cast && cast->m_spellInfo && cast->getState() == SPELL_STATE_CASTING &&
            (cast->m_spellInfo->Id == 38197 || cast->m_spellInfo->Id == 40425)) return cast->m_spellInfo->Id;
    }
#endif
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 658 && boss->GetEntry() == 36494)
    {
        const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        const bool forging = cast && cast->m_spellInfo && cast->getState() == SPELL_STATE_CASTING &&
            (cast->m_spellInfo->Id == 68774 || cast->m_spellInfo->Id == 68785);
        // The active tank uses the scripted forge pause to reset. Otherwise
        // dragging Garfrost around a rock also drags the source of Permafrost.
        if (boss->GetVictim() == bot && !forging) return 0;
        for (uint32 spell : {68786u, 70336u})
            if (const SpellAuraHolder* aura = bot->GetSpellAuraHolder(spell, boss->GetObjectGuid()))
                if (keepCover || forging || aura->GetStackAmount() >= 5) return spell;
    }
#endif
    return 0;
}

bool ai::IsBossCoverPosition(PlayerbotAI* ai, Unit* boss, const encounter::Point& point)
{
    Player* bot = ai->GetBot();
    // Match Spell::CheckTarget's spell LOS rather than movement visibility:
    // decorative static M2 objects cannot be treated as spell-blocking cover.
    bool ignoreM2 = true;
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 631 && boss && (boss->GetEntry() == 36853 || boss->GetEntry() == 37186))
    {
        ignoreM2 = false; // Match the encounter's explicit Ice Block model check.
        EncounterPosition separation;
        std::vector<encounter::Circle> threats;
        if (GruulShatterThreats(ai, separation, threats) && !encounter::OutsideCircles(point, threats)) return false;
    }
#endif
    if (!boss || boss->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), ignoreM2)) return false;
    if (bot->GetMapId() == 469 && boss->GetEntry() == 11983 && ai->IsHeal(bot))
    {
        // A healer must retain a line to the current tank while dropping
        // Firemaw stacks, rather than hiding where it cannot support the tank.
        Unit* tank = boss->GetVictim();
        return tank && tank->IsInWorld() && tank->IsAlive() && bot->IsInMap(tank) &&
            tank->GetDistance(point.x, point.y, point.z) <= std::min(40.0f, ai->GetRange("spell")) &&
            tank->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true);
    }
    return true;
}

EncounterPosition BossCoverPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !IsBossCoverMap(bot->GetMapId()) || !ai->CanMove())
    {
        shelterBoss.Clear();
        return plan;
    }
    Unit* source = nullptr;
    std::list<ObjectGuid> sources = AI_VALUE(std::list<ObjectGuid>, "attackers");
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 631 && bot->IsAlive() && bot->IsInCombat())
    {
        std::list<Unit*> markers;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, 37186, 100.0f);
        MaNGOS::UnitListSearcher<decltype(check)> searcher(markers, check);
        Cell::VisitAllObjects(bot, searcher, 100.0f);
        for (Unit* marker : markers)
            if (BossCoverMechanic(ai, marker, false)) sources.push_back(marker->GetObjectGuid());
    }
#endif
    for (const auto& guid : sources)
    {
        Unit* boss = ai->GetUnit(guid);
        const uint32 mechanic = BossCoverMechanic(ai, boss, boss && boss->GetObjectGuid() == shelterBoss);
        if (!mechanic) continue;
        if (source && source != boss) { shelterBoss.Clear(); return EncounterPosition{}; }
        source = boss;
        plan.spell = mechanic;
    }
    if (!source) { shelterBoss.Clear(); return plan; }
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId(); plan.boss = source->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    auto covered = [&](const encounter::Point& point)
    {
        return IsBossCoverPosition(ai, source, point);
    };
    plan.destination = here;
    if (covered(here) && ValidateEncounterDestination(ai, plan)) { shelterBoss = plan.boss; return plan; }
    unsigned paths = 0;
    uint32 coverEntry = 0;
    if (bot->GetMapId() == 533 && source->GetEntry() == 15989) coverEntry = 181247;
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() == 658 && source->GetEntry() == 36494) coverEntry = 196485;
    if (bot->GetMapId() == 631 && (source->GetEntry() == 36853 || source->GetEntry() == 37186)) coverEntry = 201722;
#endif
    if (coverEntry)
    {
        // Aim behind live native cover before coarse ring samples. The actual
        // spell LOS still decides whether a block is tall/wide enough.
        std::vector<GameObject*> objects;
        for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "nearest game objects no los"))
        {
            GameObject* object = ai->GetGameObject(guid);
            if (object && object->IsInWorld() && object->IsSpawned() && bot->IsInMap(object) &&
                object->GetEntry() == coverEntry && std::fabs(object->GetPositionZ() - here.z) <= 8 &&
                bot->GetDistance(object) <= 40) objects.push_back(object);
        }
        std::sort(objects.begin(), objects.end(), [this](GameObject* a, GameObject* b)
        {
            return bot->GetDistance(a) < bot->GetDistance(b);
        });
        for (GameObject* object : objects)
        {
            const float dx = object->GetPositionX() - source->GetPositionX();
            const float dy = object->GetPositionY() - source->GetPositionY();
            const float length = std::hypot(dx, dy);
            if (length < 1.0f) continue;
            // Eight yards leaves space around players newly struck by Icebolt.
            for (float behind : {8.0f, 5.0f, 3.0f})
            {
                plan.destination = {object->GetPositionX() + behind * dx / length,
                    object->GetPositionY() + behind * dy / length, here.z};
                bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
                if (!std::isfinite(plan.destination.z) || std::fabs(plan.destination.z - here.z) > 8 || !covered(plan.destination)) continue;
                if (++paths > 8) { shelterBoss.Clear(); plan.active = false; return plan; }
                if (ValidateEncounterDestination(ai, plan) && covered(plan.destination)) { shelterBoss = plan.boss; return plan; }
            }
        }
    }
    for (float distance : {8.0f, 16.0f, 24.0f, 32.0f})
        for (unsigned step = 0; step < 16; ++step)
        {
            const float angle = step * (2.0f * M_PI_F / 16.0f);
            plan.destination = {here.x + distance * std::cos(angle), here.y + distance * std::sin(angle), here.z};
            bot->UpdateAllowedPositionZ(plan.destination.x, plan.destination.y, plan.destination.z);
            if (!std::isfinite(plan.destination.z) || std::fabs(plan.destination.z - here.z) > 8 || !covered(plan.destination)) continue;
            if (++paths > 8) { plan.active = false; shelterBoss.Clear(); return plan; }
            if (ValidateEncounterDestination(ai, plan) && covered(plan.destination)) { shelterBoss = plan.boss; return plan; }
        }
    shelterBoss.Clear(); plan.active = false;
    return plan;
}
