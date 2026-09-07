#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Server/SQLStorages.h"
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
    return !threats.empty() && !safeFloor.empty();
}

EncounterPosition HeiganPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 533 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return plan;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() || !bot->IsInMap(unit) ||
            unit->HasCharmer() || unit->GetEntry() != 15936 || bot->GetDistance(unit) > 100) continue;
        if (boss && boss != unit) return plan;
        boss = unit;
    }
    if (!boss) return plan;
    std::list<Unit*> controllers;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, 17293, 100.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(controllers, check);
    Cell::VisitAllObjects(boss, searcher, 100.0f);
    Unit* controller = nullptr;
    for (Unit* unit : controllers)
        if (bot->IsInMap(unit) && HeiganUpcomingWave(boss, unit))
        {
            if (controller && controller != unit) return plan;
            controller = unit;
        }
    if (!controller) return plan;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.source = controller->GetObjectGuid(); plan.spell = HeiganUpcomingWave(boss, controller);
    std::vector<encounter::Circle> threats;
    std::vector<encounter::Point> safeFloor;
    if (!HeiganFloorThreats(ai, plan, threats, safeFloor)) return plan;
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
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
