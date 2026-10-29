#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellMgr.h"
#ifdef MANGOSBOT_ZERO
#include "playerbot/strategy/OnyxiaFormation.h"
#include "playerbot/strategy/mage/MageCombatPolicy.h"
#endif

using namespace ai;

Unit* ai::FindOnyxiaBoss(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 249 || !bot->IsInCombat()) return nullptr;
    // Raid marks constrain damage orders, never the perception of mechanics.
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && !unit->HasCharmer() &&
            unit->GetEntry() == 10184 && unit->IsInCombat()) return unit;
    }
    return nullptr;
}

bool ai::OnyxiaBreathThreats(uint32 spellId, std::vector<encounter::Circle>& threats)
{
    std::vector<encounter::Circle> native;
    std::set<uint32> seen;
    // Native deep breaths chain ground-centred SCHOOL_DAMAGE spells. Their
    // actual footprints are 30-yard circles in Classic/TBC and 18 in Wrath;
    // the database centres need not follow the first row's orientation.
    while (spellId)
    {
        if (seen.size() >= 32 || !seen.insert(spellId).second) return false;
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(spellId);
        const SpellTargetPosition* position = sSpellMgr.GetSpellTargetPosition(spellId);
        if (!spell || !position || position->target_mapId != 249 ||
            !std::isfinite(position->target_X) || !std::isfinite(position->target_Y) || !std::isfinite(position->target_Z)) return false;
        float radius = 0;
        uint32 next = 0;
        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        {
            if (spell->Effect[effect] == SPELL_EFFECT_SCHOOL_DAMAGE &&
                spell->EffectImplicitTargetA[effect] == TARGET_LOCATION_DATABASE &&
                spell->EffectImplicitTargetB[effect] == TARGET_ENUM_UNITS_ENEMY_AOE_AT_DEST_LOC)
                radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[effect])));
            if (spell->Effect[effect] == SPELL_EFFECT_TRIGGER_SPELL)
            {
                if (next && next != spell->EffectTriggerSpell[effect]) return false;
                next = spell->EffectTriggerSpell[effect];
            }
        }
        if (!std::isfinite(radius) || radius <= 0 || radius > 40) return false;
        native.push_back({{position->target_X, position->target_Y, position->target_Z}, radius + 2.0f});
        spellId = next;
    }
    if (native.empty()) return false;
    threats.insert(threats.end(), native.begin(), native.end());
    return true;
}

#ifdef MANGOSBOT_ZERO
bool ai::OnyxiaMeleeAirAdd(PlayerbotAI* ai, Unit* boss)
{
    Player* bot = ai->GetBot();
    if (ai->IsRanged(bot) || ai->IsHeal(bot)) return false;
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    return target && target != boss && target->IsInWorld() && bot->IsInMap(target) &&
        target->IsAlive() && target->IsInCombat() && !target->HasCharmer() && target->GetEntry() == 11262;
}

namespace
{
    const char* OnyxiaRangeSpell(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (ai->IsHeal(bot)) return bot->getClass() == CLASS_PALADIN ? "flash of light" :
            bot->getClass() == CLASS_SHAMAN ? "healing wave" : bot->getClass() == CLASS_DRUID ? "healing touch" : "flash heal";
        switch (bot->getClass())
        {
            case CLASS_HUNTER: return "auto shot";
            case CLASS_WARLOCK: return "shadow bolt";
            case CLASS_PRIEST: return "mind blast";
            case CLASS_SHAMAN: return "lightning bolt";
            case CLASS_DRUID: return "wrath";
            default: return MagePrimaryDamageSpell(ai);
        }
    }

    bool PlanOnyxiaFlight(PlayerbotAI* ai, Unit* boss, EncounterPosition& result,
        const std::vector<encounter::Circle>& danger, bool targeted, encounter::Point& station, time_t& until)
    {
        Player* bot = ai->GetBot();
        if (danger.empty() && !targeted && OnyxiaMeleeAirAdd(ai, boss)) { until = 0; return false; }
        const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
        std::vector<Player*> members;
        if (bot->GetGroup())
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = ref->getSource();
                if (member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
                    bot->IsInMap(member)) members.push_back(member);
            }
        if (std::find(members.begin(), members.end(), bot) == members.end()) members.push_back(bot);
        std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        const unsigned slot = unsigned(std::distance(members.begin(), std::find(members.begin(), members.end(), bot)));
        float splash = NativeEncounterSpellRadius(18392);
        if (!std::isfinite(splash) || splash <= 0 || splash > 20) return false;
        std::vector<encounter::Circle> neighbors;
        std::vector<encounter::Point> positions;
        for (Player* member : members)
        {
            positions.push_back({member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()});
            if (member != bot) neighbors.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, splash + 2});
        }

        Unit* patient = nullptr;
        float range = 0;
        if (ai->IsHeal(bot))
        {
            // Real patients, rather than the flying boss, determine healing reach.
            for (Player* member : members)
                if (member != bot && (!patient || member->GetHealthPercent() < patient->GetHealthPercent() ||
                    (member->GetHealthPercent() == patient->GetHealthPercent() && bot->GetDistance(member) < bot->GetDistance(patient)))) patient = member;
        }
        else if (ai->IsRanged(bot))
        {
            patient = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
            if (!patient || !patient->IsInWorld() || !bot->IsInMap(patient) || !patient->IsAlive() || !patient->IsInCombat()) patient = boss;
        }
        if (patient && (!ai->GetSpellRange(OnyxiaRangeSpell(ai), &range) || !std::isfinite(range) || range <= 5)) return false;
        const auto usableRange = [&](encounter::Point point) {
            if (!patient || !danger.empty() || targeted) return true; // Escape takes precedence over DPS/healing reach.
            const float legal = range + bot->GetCombatReach() + patient->GetCombatReach() - 2;
            const float dx = point.x - patient->GetPositionX(), dy = point.y - patient->GetPositionY(), dz = point.z - patient->GetPositionZ();
            return dx * dx + dy * dy + dz * dz <= legal * legal &&
                patient->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true);
        };
        const auto admit = [&](encounter::Point point) {
            result.active = true;
            result.destination = point;
            return onyxia::InRoom(point) && encounter::OutsideCircles(point, danger) && usableRange(point) &&
                ValidateEncounterDestination(ai, result) && usableRange(result.destination) && encounter::OutsideCircles(result.destination, danger);
        };
        result.exclusive = true;
        if (!result.spell) result.spell = 18392; // Phase-checked air station, not an instruction to cast Fireball.
        if (targeted) result.source = bot->GetObjectGuid();
        // Commit to a short route instead of changing direction every sample as
        // neighbors run. A new breath immediately invalidates an unsafe station.
        if (time(nullptr) < until && encounter::Distance2d(here, station) > 1.5f &&
            (!targeted || encounter::SpreadOverlap(station, neighbors) <= 1.0f) && admit(station)) return true;
        if (danger.empty() && !targeted && !onyxia::YieldSpacing(here, slot, positions, splash + 2) && admit(here))
        { station = here; until = 0; return true; }
        if (encounter::SpreadOverlap(here, neighbors) <= 1.0f && admit(here)) { station = here; until = 0; return true; }
        unsigned checked = 0;
        for (const auto& point : onyxia::Candidates(here, slot, neighbors, danger))
        {
            if (!usableRange(point)) continue;
            if (++checked > 16) break;
            if (admit(point)) { station = result.destination; until = time(nullptr) + 3; return true; }
        }
        result.active = false;
        until = 0;
        return false;
    }
}
#endif

EncounterPosition OnyxiaPositionValue::Calculate()
{
    EncounterPosition result;
    const auto clear = [&]() {
        breath = 0; breathUntil = 0; fireballUntil = 0; owner.Clear();
#ifdef MANGOSBOT_ZERO
        flightUntil = 0;
#endif
    };
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 249 || !bot->IsInCombat())
    { clear(); return result; }
    Unit* boss = FindOnyxiaBoss(ai);
    if (!boss) { clear(); return result; }
    if (owner != boss->GetObjectGuid() || instance != bot->GetInstanceId())
    { clear(); owner = boss->GetObjectGuid(); instance = bot->GetInstanceId(); }
    result.map = bot->GetMapId();
    result.instance = bot->GetInstanceId();
    result.boss = boss->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const auto choose = [&](encounter::Point first, encounter::Point second) {
        result.active = true;
        if (encounter::Distance2d(here, second) < encounter::Distance2d(here, first)) std::swap(first, second);
        result.destination = first;
        if (!ValidateEncounterDestination(ai, result))
        {
            result.destination = second;
            result.active = ValidateEncounterDestination(ai, result);
        }
        return result;
    };
    const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
    const uint32 spell = cast && cast->m_spellInfo && cast->getState() != SPELL_STATE_FINISHED ? cast->m_spellInfo->Id : 0;
    switch (spell)
    {
        case 17086: case 18351: case 18576: case 18609:
        case 18564: case 18584: case 18596: case 18617:
            breath = spell;
            // Keep clear while the triggered breath sweeps after the cast.
            breathUntil = time(nullptr) + 8;
            break;
        default: break;
    }
    std::vector<encounter::Circle> threats;
    if (breath && time(nullptr) < breathUntil)
    {
        if (!OnyxiaBreathThreats(breath, threats)) return result;
        result.spell = breath;
    }
#ifdef MANGOSBOT_TWO
    // A guard's Nova and a deep breath can overlap. Solve them together rather
    // than allowing two movement actions to pull the bot in opposite directions.
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* guard = ai->GetUnit(guid);
        if (!guard || !guard->IsInWorld() || !bot->IsInMap(guard) || !guard->IsAlive() ||
            !guard->IsInCombat() || guard->HasCharmer() || guard->GetEntry() != 36561) continue;
        const Spell* nova = guard->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (!nova || !nova->m_spellInfo || nova->getState() == SPELL_STATE_FINISHED || nova->m_spellInfo->Id != 68958) continue;
        const float radius = NativeEncounterSpellRadius(68958);
        if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
        threats.push_back({{guard->GetPositionX(), guard->GetPositionY(), guard->GetPositionZ()}, radius + 2});
        if (!result.spell) { result.spell = 68958; result.source = guard->GetObjectGuid(); }
    }
#endif
    const bool airborne = boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10;
    bool fireball = spell == 18392;
#ifdef MANGOSBOT_TWO
    fireball = fireball || spell == 68926; // Wrath 25-player fireball only.
#endif
    if (airborne && fireball && cast->m_targets.getUnitTarget() == bot) fireballUntil = time(nullptr) + 2;
#ifdef MANGOSBOT_ZERO
    if (airborne)
    {
        PlanOnyxiaFlight(ai, boss, result, threats, time(nullptr) < fireballUntil, flightStation, flightUntil);
        return result;
    }
    flightUntil = 0;
    fireballUntil = 0;
#endif
    if (time(nullptr) < fireballUntil && bot->GetGroup())
    {
        std::vector<encounter::Point> neighbors;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member != bot && member->IsInWorld() && !member->IsBeingTeleported() && bot->IsInMap(member) && member->IsAlive())
                neighbors.push_back({member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()});
        }
        const float radius = NativeEncounterSpellRadius(18392);
        if (std::isfinite(radius) && radius > 0 && radius <= 20)
            for (const auto& position : neighbors) threats.push_back({position, radius + 2});
        if (!result.spell) result.spell = 18392;
    }
    // Ignore only circles on wholly incompatible floors; keep their native
    // horizontal radius conservatively rather than projecting an airborne boss.
    threats.erase(std::remove_if(threats.begin(), threats.end(), [here](const encounter::Circle& threat) {
        return std::fabs(here.z - threat.center.z) > threat.radius + 8;
    }), threats.end());
    if (!threats.empty())
    {
        unsigned checked = 0;
        for (const auto& point : encounter::EscapeCircles(here, threats))
        {
            if (++checked > 12) break;
            result.active = true;
            result.destination = point;
            if (ValidateEncounterDestination(ai, result) && encounter::OutsideCircles(result.destination, threats)) return result;
        }
        result.active = false;
        return result;
    }
    if (airborne || boss->GetVictim() == bot) return result;
#ifndef MANGOSBOT_ZERO
    if (bot->GetDistance(boss) > 30) return result;
#endif
    // Avoid both the frontal breath/cleave and tail cone. Do not reposition
    // the active tank or impose Wrath add rules on the old encounter.
    const float facing = boss->GetOrientation();
    result.exclusive = false;
    if (std::fabs(std::cos(boss->GetAngle(bot) - facing)) < 0.70710678f)
        return choose(here, here); // Already at a safe flank: don't chase an arbitrary spot.
    const float radius = ai->IsRanged(bot) || ai->IsHeal(bot) ? 25.0f :
        std::max(3.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1.0f);
    const encounter::Point left{boss->GetPositionX() - radius * std::sin(facing),
        boss->GetPositionY() + radius * std::cos(facing), here.z};
    const encounter::Point right{boss->GetPositionX() + radius * std::sin(facing),
        boss->GetPositionY() - radius * std::cos(facing), here.z};
    return choose(left, right);
}
