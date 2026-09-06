#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Spells/SpellMgr.h"

using namespace ai;

EncounterPosition OnyxiaPositionValue::Calculate()
{
    EncounterPosition result;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetMapId() != 249 || !bot->IsInCombat())
    { breath = 0; breathUntil = 0; return result; }
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() &&
            unit->GetEntry() == 10184 && unit->IsInCombat()) { boss = unit; break; }
    }
    if (!boss) { breath = 0; breathUntil = 0; return result; }
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
    if (breath && time(nullptr) < breathUntil)
    {
        // These are the coordinates used by this core's spell target table,
        // not donor safe spots or the airborne creature's height.
        const SpellTargetPosition* position = sSpellMgr.GetSpellTargetPosition(breath);
        if (position && position->target_mapId == 249)
        {
            const encounter::Point origin{position->target_X, position->target_Y, position->target_Z};
            const float clearance = 22.0f;
            if (encounter::LineDistance(here, origin, position->target_Orientation) >= clearance)
            {
                result.active = true;
                result.destination = here; // Hold clear until the sweep ends.
                result.active = ValidateEncounterDestination(ai, result);
                return result;
            }
            const auto left = encounter::OutsideLine(here, origin, position->target_Orientation, clearance + 1, 1);
            const auto right = encounter::OutsideLine(here, origin, position->target_Orientation, clearance + 1, -1);
            return choose(left, right);
        }
        return result; // Missing native spell data must not invent a safe destination.
    }
    const bool airborne = boss->IsLevitating() || boss->GetPositionZ() - bot->GetPositionZ() > 10;
    bool fireball = spell == 18392;
#ifdef MANGOSBOT_TWO
    fireball = fireball || spell == 68926; // Wrath 25-player fireball only.
#endif
    if (airborne && fireball && cast->m_targets.getUnitTarget() == bot && bot->GetGroup())
    {
        std::vector<encounter::Point> neighbors;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member != bot && member->IsInWorld() && !member->IsBeingTeleported() && bot->IsInMap(member) && member->IsAlive())
                neighbors.push_back({member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()});
        }
        float nearest = 1000;
        for (const auto& position : neighbors) nearest = std::min(nearest, encounter::Distance2d(here, position));
        if (nearest >= 10)
        {
            result.active = true;
            result.destination = here;
            result.active = ValidateEncounterDestination(ai, result);
            return result; // Do not let ordinary follow immediately rejoin the stack.
        }
        for (unsigned i = 0; i < 8; ++i)
        {
            const float angle = i * M_PI_F / 4;
            encounter::Point point{here.x + 10 * std::cos(angle), here.y + 10 * std::sin(angle), here.z};
            float separation = 1000;
            for (const auto& position : neighbors) separation = std::min(separation, encounter::Distance2d(point, position));
            if (separation > nearest)
            {
                EncounterPosition candidate = result;
                candidate.active = true;
                candidate.destination = point;
                if (ValidateEncounterDestination(ai, candidate)) { nearest = separation; result = candidate; }
            }
        }
        return result;
    }
    if (airborne || boss->GetVictim() == bot || bot->GetDistance(boss) > 30) return result;
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
