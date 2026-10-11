
#include "playerbot/playerbot.h"
#include "AoeValues.h"
#include "playerbot/strategy/MoltenCoreTrashPolicy.h"

#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include <algorithm>
using namespace ai;

namespace
{
    bool IsCurrentAoeTarget(Player* bot, Unit* unit)
    {
        // The shared target value may outlive a death, despawn or map/phase
        // transition. Never use coordinates from that stale membership.
        return bot && bot->IsInWorld() && unit && unit->IsInWorld() &&
            unit->IsAlive() && bot->IsInMap(unit);
    }
}

bool ai::ControlledRaidAoe(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !bot->IsInCombat() || !bot->GetGroup() || !bot->GetMap()->IsRaid() || ai->IsRealPlayer() ||
        ai->IsHeal(bot) || !ai->GetCombatStartTime() || time(0) - ai->GetCombatStartTime() < 2) return false;
    if (!ai->IsTank(bot) && (MoltenCoreNukeTarget(ai) || MoltenCoreBossBurn(ai))) return false;
    const WorldLocation center = ai->GetAiObjectContext()->GetValue<WorldLocation>("aoe position")->Get();
    // Validate the same centre the ground-targeted action will cast at. A
    // separate density scan can select a different, farther cluster.
    const float range = std::min(40.0f, ai->GetRange("spell"));
    if (!std::isfinite(center.coord_x) || !std::isfinite(center.coord_y) || !std::isfinite(center.coord_z) ||
        std::hypot(center.coord_x - bot->GetPositionX(), center.coord_y - bot->GetPositionY()) > range) return false;
    unsigned controlled = 0;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
            sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        const float dx = enemy->GetPositionX() - center.coord_x;
        const float dy = enemy->GetPositionY() - center.coord_y;
        const float dz = enemy->GetPositionZ() - center.coord_z;
        const float clearance = 12.0f + enemy->GetCombatReach();
        if (dx*dx + dy*dy + dz*dz > clearance*clearance) continue;
        // Inspect the unfiltered neighbours too: sheeped or unpulled mobs must
        // not disappear from the safety decision merely because they cannot be selected.
        if (!enemy->IsInCombat() || enemy->HasCharmer() ||
            PossibleAttackTargetsValue::HasBreakableCC(enemy, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot)) return false;
        if (dx*dx + dy*dy > 8.0f*8.0f || std::fabs(dz) > 5.0f) continue;
        Unit* victim = enemy->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            !bot->IsInMap(victim)) return false;
        Player* tank = static_cast<Player*>(victim);
        if (tank->IsBeingTeleported() || tank->HasCharmer() || tank->GetGroup() != bot->GetGroup() ||
            !ai->IsTank(tank)) return false;
        ++controlled;
    }
    return controlled >= 3;
}

std::list<ObjectGuid> AoeCountValue::FindMaxDensity(Player* bot, float range)
{
    size_t maxCount = 0;
    ObjectGuid maxGroup;
    std::map<ObjectGuid, std::list<ObjectGuid> > groups;
    if (bot && bot->IsInWorld())
    {
        std::list<ObjectGuid> units = *bot->GetPlayerbotAI()->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible attack targets");
        
        for (std::list<ObjectGuid>::iterator i = units.begin(); i != units.end(); ++i)
        {
            Unit* unit = bot->GetPlayerbotAI()->GetUnit(*i);
            if (IsCurrentAoeTarget(bot, unit))
            {
                float distanceToPlayer = sServerFacade.GetDistance2d(unit, bot);
                if (sServerFacade.IsDistanceLessOrEqualThan(distanceToPlayer, range))
                {
                    for (std::list<ObjectGuid>::iterator j = units.begin(); j != units.end(); ++j)
                    {
                        Unit* other = bot->GetPlayerbotAI()->GetUnit(*j);
                        if (IsCurrentAoeTarget(bot, other))
                        {
                            float d = sServerFacade.GetDistance2d(unit, other);
                            if (sServerFacade.IsDistanceLessOrEqualThan(d, sPlayerbotAIConfig.aoeRadius * 2.0f))
                            {
                                groups[*i].push_back(*j);
                            }
                        }
                    }

                    if (maxCount < groups[*i].size())
                    {
                        maxCount = groups[*i].size();
                        maxGroup = *i;
                    }
                }
            }
        }
    }

    if (!maxCount)
    {
        return std::list<ObjectGuid>();
    }

    return groups[maxGroup];
}

WorldLocation AoePositionValue::Calculate()
{
    std::list<ObjectGuid> group = AoeCountValue::FindMaxDensity(bot);
    if (group.empty())
        return WorldLocation();

    // A previously selected GUID can disappear before this second resolution.
    // Initialize bounds from the first still-valid unit, not the first GUID.
    bool havePosition = false;
    float x1 = 0.0f, y1 = 0.0f, x2 = 0.0f, y2 = 0.0f;
    for (std::list<ObjectGuid>::iterator i = group.begin(); i != group.end(); ++i)
    {
        Unit* unit = bot->GetPlayerbotAI()->GetUnit(*i);
        if (!IsCurrentAoeTarget(bot, unit))
            continue;

        if (!havePosition || x1 > unit->GetPositionX())
            x1 = unit->GetPositionX();
        if (!havePosition || x2 < unit->GetPositionX())
            x2 = unit->GetPositionX();
        if (!havePosition || y1 > unit->GetPositionY())
            y1 = unit->GetPositionY();
        if (!havePosition || y2 < unit->GetPositionY())
            y2 = unit->GetPositionY();
        havePosition = true;
    }
    if (!havePosition)
        return WorldLocation();
    float x = (x1 + x2) / 2;
    float y = (y1 + y2) / 2;
    float z = bot->GetPositionZ() + CONTACT_DISTANCE;
    bot->UpdateAllowedPositionZ(x, y, z);
    return WorldLocation(bot->GetMapId(), x, y, z, 0);
}

uint8 AoeCountValue::Calculate()
{
    // A crowded pull must not wrap 256 targets to zero in the uint8 value.
    return static_cast<uint8>(std::min<size_t>(FindMaxDensity(bot).size(), 255));
}

bool HasAreaDebuffValue::Calculate()
{
    if (!GetTarget())
        return false;

    Unit* checkTarget = GetTarget();
    if (!checkTarget)
        return false;

    std::list<ObjectGuid> nearestDynObjects = *context->GetValue<std::list<ObjectGuid> >("nearest dynamic objects no los");
    if (nearestDynObjects.empty())
        return false;

    for (std::list<ObjectGuid>::iterator i = nearestDynObjects.begin(); i != nearestDynObjects.end(); ++i)
    {
        DynamicObject* go = checkTarget->GetMap()->GetDynamicObject(*i);
        if (!go)
            continue;

        SpellEntry const* spellProto = sSpellTemplate.LookupEntry<SpellEntry>(go->GetSpellId());
        if (!spellProto)
            continue;

        if (IsPositiveEffect(spellProto, go->GetEffIndex()))
            continue;

        if (go->IsAffecting(checkTarget))
            return true;
    }

    return false;
}
