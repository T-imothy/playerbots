#include "playerbot/playerbot.h"
#include "playerbot/RaidLabTrace.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Server/SQLStorages.h"
#include "Spells/SpellMgr.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

uint32 ai::HeiganNextWave(Unit* controller)
{
    if (!controller || !controller->IsInWorld() || !controller->IsAlive() || controller->HasCharmer() ||
        controller->GetMapId() != 533 || controller->GetEntry() != 17293) return 0;
    const Aura* slow = controller->GetAura(29351, EFFECT_INDEX_0);
    const Aura* fast = controller->GetAura(30114, EFFECT_INDEX_0);
    if (bool(slow) == bool(fast)) return 0;
    const Aura* aura = fast ? fast : slow;
    if (aura->GetCasterGuid() != controller->GetObjectGuid()) return 0;
    // GetAuraTicks includes the most recently dispatched tick. The native
    // periodic handler subtracts one while dispatching that tick.
    const uint32 sequence[] = {30116, 30117, 30118, 30119, 30118, 30117};
    return sequence[aura->GetAuraTicks() % 6];
}

bool ai::HeiganManaBurnSafe(PlayerbotAI* ai, Unit* boss, const encounter::Point& point)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (boss && !boss->HasAura(29350) && !ai->IsTank(bot) && (ai->IsHeal(bot) || ai->IsRanged(bot)))
    {
        const float radius=NativeEncounterSpellRadius(29310);
        return std::isfinite(radius) && radius>0 && radius<=40 &&
            encounter::Distance2d(point,{boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ()}) >=
                radius+boss->GetCombatReach()+bot->GetCombatReach()+1;
    }
#endif
    return true;
}

bool ai::HeiganCloudSafe(Player* bot, Unit* boss, const encounter::Point& point)
{
    if (!boss || !boss->HasAura(29350)) return true;
    const float radius = NativeEncounterSpellRadius(30122);
    if (!std::isfinite(radius) || radius <= 0 || radius > 40) return false;
    return encounter::Distance2d(point, {boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()}) >=
        radius + boss->GetCombatReach() + bot->GetCombatReach() + 1;
}

uint32 ai::HeiganUpcomingWave(Unit* boss, Unit* controller)
{
    if (!controller || !controller->IsInWorld() || !controller->IsAlive() || controller->HasCharmer() ||
        controller->GetMapId() != 533 || controller->GetEntry() != 17293) return 0;
    const uint32 next = HeiganNextWave(controller);
    if (next) return next;
#ifdef MANGOSBOT_ZERO
    // Native Aggro starts the slow controller after five seconds. Its first
    // wave is already known; protect the raid during that opening instead of
    // letting ordinary formation walk casters into Mana Burn before it starts.
    // Native phase transitions also restart at the first wave. Never infer a
    // wave from contradictory or foreign controller auras, or an idle boss.
    if (boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() &&
        !boss->HasCharmer() && boss->GetMapId()==533 && boss->GetEntry()==15936 &&
        !controller->HasAura(29351) && !controller->HasAura(30114)) return 30116;
#endif
    // The native platform transition channels its cloud before starting the
    // fast controller. Its first wave is always 30116; leave the platform now.
    return boss && boss->HasAura(29350) && !controller->HasAura(29351) && !controller->HasAura(30114) ? 30116 : 0;
}

namespace
{
    std::set<uint32> HeiganFissureEntries(uint32 wave)
    {
        std::set<uint32> entries;
        const SpellEntry* spell = sSpellTemplate.LookupEntry<SpellEntry>(wave);
        if (!spell) return entries;
        auto bounds = sSpellScriptTargetStorage.getBounds<SpellTargetEntry>(wave);
        for (auto row = bounds.first; row != bounds.second; ++row)
        {
            if (row->type != SPELL_TARGET_TYPE_GAMEOBJECT) continue;
            for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
                if (spell->Effect[effect] == SPELL_EFFECT_ACTIVATE_OBJECT &&
                    (spell->EffectMiscValue[effect] == uint32(GameObjectActions::DISTURB) ||
                        spell->EffectMiscValue[effect] == uint32(GameObjectActions::OPEN)) &&
                    !row->CanNotHitWithSpellEffect(SpellEffectIndex(effect))) entries.insert(row->targetEntry);
        }
        return entries;
    }
}

bool ai::HeiganFloorThreats(PlayerbotAI* ai, const EncounterPosition& plan,
    std::vector<encounter::Circle>& threats, std::vector<encounter::Point>& safeFloor)
{
    Player* bot = ai->GetBot();
    Unit* controller = ai->GetUnit(plan.source);
    Unit* boss = ai->GetUnit(plan.boss);
    if (!boss || !controller || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
        boss->HasCharmer() || boss->GetEntry() != 15936 || !bot->IsInMap(boss) || !bot->IsInMap(controller) ||
        HeiganUpcomingWave(boss, controller) != plan.spell) return false;
    const auto dangerous = HeiganFissureEntries(plan.spell);
    if (dangerous.empty()) return false;
    std::set<uint32> floorEntries;
    for (uint32 wave : {30116u, 30117u, 30118u, 30119u})
    {
        auto entries = HeiganFissureEntries(wave);
        if (entries.empty()) return false;
        floorEntries.insert(entries.begin(), entries.end());
    }
    struct FissureCheck
    {
        Player* bot;
        const std::set<uint32>& entries;
        Player const& GetFocusObject() const { return *bot; }
        bool operator()(GameObject* go) const
        {
            return go && go->IsInWorld() && bot->IsInMap(go) && go->IsSpawned() && entries.count(go->GetEntry()) &&
                go->GetGOInfo() && go->GetGoType() == GAMEOBJECT_TYPE_TRAP && go->GetGOInfo()->trap.spellId == 29371;
        }
    } check{bot, floorEntries};
    std::list<GameObject*> fissures;
    MaNGOS::GameObjectListSearcher<FissureCheck> searcher(fissures, check);
    Cell::VisitAllObjects(controller, searcher, 100.0f);
    if (fissures.empty() || fissures.size() > 256) return false;
    const float eruption = NativeEncounterSpellRadius(29371);
    if (!std::isfinite(eruption) || eruption <= 0 || eruption > 20) return false;
    for (GameObject* fissure : fissures)
    {
        if (!check(fissure)) continue;
        const encounter::Point point{fissure->GetPositionX(), fissure->GetPositionY(), fissure->GetPositionZ()};
        if (dangerous.count(fissure->GetEntry()))
            threats.push_back({point, eruption + fissure->GetCombatReach() + bot->GetCombatReach() + 1});
        else safeFloor.push_back(point);
    }
    if (boss->HasAura(29350))
    {
        const float radius = NativeEncounterSpellRadius(30122);
        if (!std::isfinite(radius) || radius <= 0 || radius > 40) return false;
        threats.push_back({{boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()},
            radius + boss->GetCombatReach() + bot->GetCombatReach() + 1});
    }
#ifdef MANGOSBOT_ZERO
    else if (!ai->IsTank(bot) && (ai->IsHeal(bot) || ai->IsRanged(bot)))
    {
        // A tile safe from the next eruption can still be inside Mana Burn.
        // Preserve the native radius, and do not send healers/casters onto
        // that tile while the boss follows the tank through the slow dance.
        const float radius=NativeEncounterSpellRadius(29310);
        if (!std::isfinite(radius) || radius<=0 || radius>40) return false;
        threats.push_back({{boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ()},
            radius+boss->GetCombatReach()+bot->GetCombatReach()+1});
    }
#endif
    return !threats.empty() && !safeFloor.empty();
}

namespace {
float HeiganRoleSpellRange(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    const bool healer = ai->IsHeal(bot);
    const char* spell = nullptr;
    switch (bot->getClass())
    {
        case CLASS_PRIEST: spell = healer ? "flash heal" : "mind blast"; break;
        case CLASS_DRUID: spell = healer ? "healing touch" : "wrath"; break;
        case CLASS_SHAMAN: spell = healer ? "healing wave" : "lightning bolt"; break;
        case CLASS_PALADIN: spell = "flash of light"; break;
        case CLASS_MAGE: spell = "frostbolt"; break;
        case CLASS_WARLOCK: spell = "shadow bolt"; break;
        case CLASS_HUNTER: spell = "auto shot"; break;
    }
    float range = ai->GetRange("spell");
    if (spell) ai->GetSpellRange(spell, &range);
    return std::isfinite(range) ? std::min(38.0f, range - 2.0f) : 0;
}
bool HeiganTankFloor(PlayerbotAI* ai, Unit* boss, Unit* controller, EncounterPosition& plan,
    const std::vector<encounter::Circle>& threats, const std::vector<encounter::Point>& safeFloor)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (!ai->IsTank(bot) || boss->HasAura(29350) || controller->HasAura(30114)) return false;
    const SpellTargetPosition* native=sSpellMgr.GetSpellTargetPosition(30211);
    const float burn=NativeEncounterSpellRadius(29310);
    if (!native || native->target_mapId!=533 || !std::isfinite(native->target_X) ||
        !std::isfinite(native->target_Y) || !std::isfinite(native->target_Z) ||
        !std::isfinite(burn) || burn<=0 || burn>40) return false;
    const encounter::Point platform{native->target_X,native->target_Y,native->target_Z};
    const encounter::Point here{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
    // Nearest safe fissure alone leaves Heigan close enough to burn the
    // platform. Give his melee pursuit room while keeping platform healers
    // within their normal range. Eruption and complete-path admission remain
    // mandatory; if no station works the ordinary dance escape still runs.
    const float minimum=burn+boss->GetCombatReach()+bot->GetCombatReach()+6;
    const float maximum=minimum+9;
    const auto admitted=[&](const encounter::Point& p) {
        const float radius=encounter::Distance2d(p,platform);
        return radius>=minimum && radius<=maximum && encounter::OutsideCircles(p,threats);
    };
    std::vector<encounter::Point> candidates;
    if (admitted(here)) candidates.push_back(here);
    for (const auto& anchor:safeFloor)
        for (float dx:{-6.0f,0.0f,6.0f}) for (float dy:{-6.0f,0.0f,6.0f})
        {
            encounter::Point point{anchor.x+dx,anchor.y+dy,anchor.z};
            if (admitted(point)) candidates.push_back(point);
        }
    std::sort(candidates.begin(),candidates.end(),[&](const encounter::Point& a,const encounter::Point& b){
        return encounter::Distance2d(here,a)<encounter::Distance2d(here,b);
    });
    unsigned checked=0;
    for (const auto& point:candidates)
    {
        if (++checked>8) break;
        plan.active=true;plan.destination=point;
        if (ValidateEncounterDestination(ai,plan) && admitted(plan.destination)) return true;
    }
    plan.active=false;
#endif
    return false;
}

bool HeiganCasterPlatform(PlayerbotAI* ai, Unit* boss, Unit* controller,
    EncounterPosition& plan, const std::vector<encounter::Circle>& threats)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (ai->IsTank(bot) || !(ai->IsHeal(bot) || ai->IsRanged(bot)) || boss->HasAura(29350) ||
        !boss->IsInCombat() || controller->HasAura(30114) ||
        (!controller->HasAura(29351) && HeiganUpcomingWave(boss,controller)!=30116)) return false;
    const SpellTargetPosition* native=sSpellMgr.GetSpellTargetPosition(30211);
    const float burn=NativeEncounterSpellRadius(29310);
    // The generic movement default is 26yd. It is not the priest/druid/etc.
    // heal range and made every platform candidate fail against 25yd burn.
    const float maximum=HeiganRoleSpellRange(ai);
#ifdef MANTECH_RAID_LAB
    // Bounded per-second aggregates expose the native inputs when an otherwise
    // legal platform disappears from the plan. Values are centimetres.
    RaidLab::Count(bot,"heigan_platform_input",1,int32(maximum*100),plan.spell);
    RaidLab::Count(bot,"heigan_platform_input",2,int32(boss->GetCombatReach()*100),plan.spell);
    RaidLab::Count(bot,"heigan_platform_input",3,int32(bot->GetCombatReach()*100),plan.spell);
    RaidLab::Count(bot,"heigan_platform_input",4,int32(burn*100),plan.spell);
#endif
    if (!native || native->target_mapId!=533 || !std::isfinite(native->target_X) ||
        !std::isfinite(native->target_Y) || !std::isfinite(native->target_Z) ||
        !std::isfinite(burn) || burn<=0 || burn>40 || !std::isfinite(maximum) || maximum<=burn+2) return false;
    const encounter::Point anchor{native->target_X,native->target_Y,native->target_Z};
    const encounter::Point here{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
    std::vector<encounter::Point> candidates;
    if (encounter::Distance2d(here,anchor)<=6 && std::fabs(here.z-anchor.z)<2) candidates.push_back(here);
    candidates.push_back(anchor);
    for (float dx:{-4.0f,0.0f,4.0f}) for (float dy:{-4.0f,0.0f,4.0f})
        candidates.push_back({anchor.x+dx,anchor.y+dy,anchor.z});
    for (const auto& point:candidates)
    {
        // The platform only helps after the tank takes Heigan away from it.
        // Preserve normal spell-range approach when no safe platform station
        // can reach the boss. Fast phase always returns to floor-wave logic.
        const float distance=boss->GetDistance(point.x,point.y,point.z);
        const uint32 rejection=distance<burn+bot->GetCombatReach()+1 ? 1 : distance>maximum ? 2 :
            !encounter::OutsideCircles(point,threats) ? 3 : 0;
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"heigan_platform_candidate",rejection,int32(distance*100),plan.spell);
#endif
        if (rejection) continue;
        plan.active=true;plan.destination=point;
        if (ValidateEncounterDestination(ai,plan) && encounter::OutsideCircles(plan.destination,threats)) return true;
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"heigan_platform_candidate",4,0,plan.spell);
#endif
    }
    plan.active=false;
#endif
    return false;
}
}

EncounterPosition HeiganPositionValue::Calculate()
{
    EncounterPosition plan;
    auto result = [&](uint32 reason) {
#ifdef MANTECH_RAID_LAB
        // Count aggregates by reason and wave; the lab flushes once/second.
        // No production logging or forced planner refresh.
        if (bot->IsInWorld() && bot->GetMapId()==533)
            RaidLab::Count(bot,"heigan_plan",reason,plan.active?1:0,plan.spell);
#endif
        return plan;
    };
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 533 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return result(1);
    Unit* boss = nullptr;
    // Safety perception must survive a skull on an add or no skull at all.
    for (const auto& guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() || !bot->IsInMap(unit) ||
            unit->HasCharmer() || unit->GetEntry() != 15936 || bot->GetDistance(unit) > 100 ||
            !NaxxramasEncounterEngaged(bot, unit)) continue;
        if (boss && boss != unit) return result(3);
        boss = unit;
    }
    if (!boss) return result(2);
    std::list<Unit*> controllers;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, 17293, 100.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(controllers, check);
    Cell::VisitAllObjects(boss, searcher, 100.0f);
    Unit* controller = nullptr;
    for (Unit* unit : controllers)
        if (bot->IsInMap(unit) && HeiganUpcomingWave(boss, unit))
        {
            if (controller && controller != unit) return result(5);
            controller = unit;
        }
    if (!controller) return result(4);
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.source = controller->GetObjectGuid(); plan.spell = HeiganUpcomingWave(boss, controller);
    std::vector<encounter::Circle> threats;
    std::vector<encounter::Point> safeFloor;
    if (!HeiganFloorThreats(ai, plan, threats, safeFloor)) return result(6);
    if (HeiganTankFloor(ai,boss,controller,plan,threats,safeFloor)) return result(10);
#ifdef MANGOSBOT_ZERO
    // If the moving tank brings Mana Burn onto a caster, leave by the nearest
    // admitted outward route first. A platform on the opposite side of the
    // boss is a later destination, not a reason to run through his aura.
    const encounter::Point current{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
    if (!HeiganManaBurnSafe(ai,boss,current))
    {
        unsigned checked=0;
        for (const auto& point:encounter::EscapeCircles(current,threats))
        {
            if (++checked>16) break;
            plan.active=true;plan.destination=point;
            if (ValidateEncounterDestination(ai,plan) && encounter::OutsideCircles(plan.destination,threats)) return result(11);
        }
        plan.active=false;
    }
#endif
    if (HeiganCasterPlatform(ai,boss,controller,plan,threats)) return result(7);
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    std::vector<encounter::Point> candidates;
    if (encounter::OutsideCircles(here, threats)) candidates.push_back(here);
    std::sort(safeFloor.begin(), safeFloor.end(), [here](const encounter::Point& a, const encounter::Point& b) {
        return encounter::Distance2d(here, a) < encounter::Distance2d(here, b);
    });
    candidates.insert(candidates.end(), safeFloor.begin(), safeFloor.end());
    unsigned checked = 0;
    for (const auto& point : candidates)
    {
        if (!encounter::OutsideCircles(point, threats)) continue;
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return result(8);
    }
#ifdef MANGOSBOT_ZERO
    // Fissures describe the eruption geometry, not the only places a player
    // can stand. During the fourth slow wave the tank can make every safe
    // fissure centre fail Mana Burn clearance, although open floor beside
    // those centres satisfies both hazards. Search a bounded local ring
    // before giving ordinary spell-range movement control back.
    candidates.clear();
    for (const auto& anchor : safeFloor)
        for (float dx : {-6.0f, 0.0f, 6.0f})
            for (float dy : {-6.0f, 0.0f, 6.0f})
            {
                if (!dx && !dy) continue;
                encounter::Point point{anchor.x + dx, anchor.y + dy, anchor.z};
                if (encounter::OutsideCircles(point, threats)) candidates.push_back(point);
            }
    std::sort(candidates.begin(), candidates.end(), [here](const encounter::Point& a, const encounter::Point& b) {
        return encounter::Distance2d(here, a) < encounter::Distance2d(here, b);
    });
    checked = 0;
    for (const auto& point : candidates)
    {
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        // Keep native ground/path admission and recheck after Z projection.
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return result(8);
    }
#endif
    plan.active = false;
    return result(9);
}
