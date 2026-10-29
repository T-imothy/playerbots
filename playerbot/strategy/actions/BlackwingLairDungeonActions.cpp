#include "playerbot/playerbot.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "MotionGenerators/PathFinder.h"
#include "Movement/MoveSpline.h"
#include "BlackwingLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

#include "playerbot/ServerFacade.h"

#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/strategy/values/SuppressionDutyValue.h"
#include "MovementPathSafety.h"
#include "Combat/ThreatManager.h"

#include "AI/ScriptDevAI/include/sc_instance.h"

using namespace ai;

bool ai::SuppressionDutyOwnsMovement(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer()) return false;
    const auto state = ai->GetAiObjectContext()->GetValue<SuppressionDuty>("suppression duty")->Get();
    return state.routeOwned && state.instance == bot->GetInstanceId() &&
        state.generation == ai->GetTransitionGeneration() && bot->movespline &&
        !bot->movespline->Finalized() && bot->movespline->GetId() == state.splineId;
}

GameObject* ai::AssignedSuppressionDevice(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        bot->IsBeingTeleported() || bot->HasCharmer() || !bot->GetGroup() ||
        ai->IsRealPlayer() || bot->getClass() != CLASS_ROGUE || !bot->HasSpell(SPELL_DISARM_TRAP)) return nullptr;

    if (InstanceData* instance = bot->GetMap()->GetInstanceData())
        if (instance->GetData(2) == IN_PROGRESS || instance->GetData(2) == DONE) return nullptr;

    // Use one common raid anchor, rather than each rogue's sight list. This
    // prevents duplicate assignments. The 40-yard look-ahead still requires
    // a full native route of at most 45 yards, checked against every nearby pack.
    Player* anchor = nullptr;
    std::vector<Player*> rogues;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->IsBeingTeleported() || member->HasCharmer()) continue;
        if (member->GetObjectGuid() == bot->GetGroup()->GetLeaderGuid()) anchor = member;
        PlayerbotAI* memberAI = member->GetPlayerbotAI();
        const SpellEntry* disarm = sServerFacade.LookupSpellInfo(SPELL_DISARM_TRAP);
        if (!disarm) continue;
        if ((disarm->Attributes & SPELL_ATTR_ONLY_STEALTHED) && member->IsInCombat() &&
            !member->HasAuraType(SPELL_AURA_MOD_STEALTH) &&
            (!memberAI || !memberAI->CanCastSpell("vanish", member, 0))) continue;
        if (memberAI && !memberAI->IsRealPlayer() && member->getClass() == CLASS_ROGUE &&
            member->HasSpell(SPELL_DISARM_TRAP) && memberAI->CanMove()) rogues.push_back(member);
    }
    if (!anchor) return nullptr;
    std::list<GameObject*> found;
    MaNGOS::GameObjectEntryInPosRangeCheck check(*anchor, 179784,
        anchor->GetPositionX(), anchor->GetPositionY(), anchor->GetPositionZ(), 40.0f);
    MaNGOS::GameObjectListSearcher<MaNGOS::GameObjectEntryInPosRangeCheck> searcher(found, check);
    Cell::VisitAllObjects(anchor, searcher, 40.0f);
    std::vector<GameObject*> devices;
    for (GameObject* go : found)
        if (go && go->IsInWorld() && anchor->IsInMap(go) && sServerFacade.isSpawned(go) &&
            go->GetLootState() == GO_READY &&
            !go->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_IN_USE | GO_FLAG_NO_INTERACT) &&
            std::fabs(go->GetPositionZ() - anchor->GetPositionZ()) <= 8.0f)
            devices.push_back(go);
    std::sort(rogues.begin(), rogues.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    const uint32 now = WorldTimer::getMSTime();
    std::map<Player*, SuppressionDuty> duties;
    for (Player* rogue : rogues)
    {
        PlayerbotAI* owner = rogue->GetPlayerbotAI();
        auto state = owner->GetAiObjectContext()->GetValue<SuppressionDuty>("suppression duty")->Get();
        if (state.instance != rogue->GetInstanceId() ||
            state.generation != owner->GetTransitionGeneration()) state = SuppressionDuty{};
        else if (state.anchor != anchor->GetObjectGuid())
        {
            // A new raid leader invalidates claims, but cannot erase ownership
            // of an already running native spline before it can be retired.
            state.device.Clear(); state.rejected.clear();
            if (state.routeOwned) { state.returning = true; state.recoveryAt = now; }
        }
        state.anchor = anchor->GetObjectGuid(); state.instance = rogue->GetInstanceId();
        state.generation = owner->GetTransitionGeneration();
        for (auto it = state.rejected.begin(); it != state.rejected.end();)
            if (WorldTimer::getMSTimeDiff(it->second, now) >= 10000) it = state.rejected.erase(it);
            else ++it;
        duties[rogue] = state;
    }
    auto eligible = [&](Player* rogue, GameObject* go) {
        return !duties[rogue].returning &&
            !(duties[rogue].routeOwned && duties[rogue].routeStealthed && !rogue->HasAuraType(SPELL_AURA_MOD_STEALTH)) &&
            rogue->GetDistance(anchor) <= 40.0f && rogue->GetDistance(go) <= 40.0f &&
            std::fabs(go->GetPositionZ() - rogue->GetPositionZ()) <= 8.0f &&
            rogue->IsWithinLOSInMap(go) && !duties[rogue].rejected.count(go->GetObjectGuid());
    };
    std::map<Player*, GameObject*> assignments;
    // Keep valid in-progress claims before allocating new work. Completing one
    // trap must not redirect this rogue onto another rogue's unfinished trap.
    for (Player* rogue : rogues)
    {
        auto& state = duties[rogue];
        for (GameObject* go : devices)
            if (go->GetObjectGuid() == state.device && eligible(rogue, go))
            {
                const float distance = rogue->GetDistance(go);
                if (distance + 0.5f < state.distance)
                { state.distance = distance; state.progressAt = now; }
                if (WorldTimer::getMSTimeDiff(state.progressAt, now) >= 10000)
                { state.rejected[state.device] = now; state.device.Clear(); }
                else assignments[rogue] = go;
                break;
            }
        if (assignments.count(rogue))
            devices.erase(std::remove(devices.begin(), devices.end(), assignments[rogue]), devices.end());
    }
    for (Player* rogue : rogues)
    {
        auto& state = duties[rogue];
        GameObject* selected = assignments.count(rogue) ? assignments[rogue] : nullptr;
        if (!selected)
        {
            float distance = 40.0f;
            for (GameObject* go : devices)
            {
                if (!eligible(rogue, go)) continue;
                const float candidate = rogue->GetDistance(go);
                if (!selected || candidate < distance ||
                    (candidate == distance && go->GetObjectGuid() < selected->GetObjectGuid()))
                { selected = go; distance = candidate; }
            }
            if (selected)
            { state.device = selected->GetObjectGuid(); state.distance = distance; state.progressAt = now; }
            else state.device.Clear();
        }
        if (rogue == bot)
        {
            ai->GetAiObjectContext()->GetValue<SuppressionDuty>("suppression duty")->Set(state);
            return selected;
        }
        if (selected) devices.erase(std::remove(devices.begin(), devices.end(), selected), devices.end());
    }
    return nullptr;
}

bool ai::SuppressionDeviceInCastRange(PlayerbotAI* ai, GameObject* device)
{
    Player* bot = ai->GetBot();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(SPELL_DISARM_TRAP);
    if (!device || !spell || !bot->IsInWorld() || !device->IsInWorld() || !bot->IsInMap(device)) return false;
    const float range = GetSpellMaxRange(sSpellRangeStore.LookupEntry(spell->rangeIndex));
    return range > 0 && bot->GetDistance(device) <= std::max(0.5f, range - 0.5f) && bot->IsWithinLOSInMap(device);
}

bool MoveToSuppressionDeviceAction::isUseful()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer()) return false;
    GameObject* go = AssignedSuppressionDevice(ai);
    const auto state = ai->GetAiObjectContext()->GetValue<SuppressionDuty>("suppression duty")->Get();
    if (state.routeOwned || state.returning) return true; // Also retire an interrupted native spline.
    return go && !SuppressionDeviceInCastRange(ai, go) && !bot->IsNonMeleeSpellCasted(true);
}

bool MoveToSuppressionDeviceAction::Execute(Event& event)
{
    GameObject* go = AssignedSuppressionDevice(ai);
    auto* value = ai->GetAiObjectContext()->GetValue<SuppressionDuty>("suppression duty");
    auto state = value->Get();
    // Transfers, death, encounter transitions and explicit replacement movement
    // relinquish ownership. Never stop a newer escape, follow or combat spline.
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        state.instance != bot->GetInstanceId() || state.generation != ai->GetTransitionGeneration())
    {
        state.routeOwned = state.returning = false; value->Set(state); return false;
    }
    const bool ownSpline = SuppressionDutyOwnsMovement(ai);
    InstanceData* instance = bot->GetMap()->GetInstanceData();
    if (!bot->GetGroup() || (instance && (instance->GetData(2) == IN_PROGRESS || instance->GetData(2) == DONE)))
    {
        if (ownSpline) ai->StopMoving();
        state.device.Clear(); state.routeOwned = state.returning = false; value->Set(state);
        return false;
    }
    if (state.routeOwned && bot->movespline && !bot->movespline->Finalized() && !ownSpline)
    {
        state.rejected[state.movingDevice] = WorldTimer::getMSTime();
        state.device.Clear(); state.routeOwned = state.returning = false; value->Set(state);
        return false;
    }
    if (state.returning && ownSpline)
    {
        const auto end = bot->movespline->FinalDestination();
        if (WorldPosition(bot->GetMapId(), state.originX, state.originY, state.originZ).distance(
            WorldPosition(bot->GetMapId(), end.x, end.y, end.z)) > 1.0f)
        {
            // An anchor change can request return before this action runs.
            // Retire its old outbound leg before yielding to a current cast.
            ai->StopMoving(); state.routeOwned = false; value->Set(state);
        }
    }
    const bool interrupted = state.routeOwned && !state.returning &&
        (!go || go->GetObjectGuid() != state.movingDevice ||
            (state.routeStealthed && !bot->HasAuraType(SPELL_AURA_MOD_STEALTH)));
    if (interrupted)
    {
        if (ownSpline) ai->StopMoving();
        state.rejected[state.movingDevice] = WorldTimer::getMSTime();
        state.device.Clear(); state.routeOwned = false; state.returning = true;
        state.recoveryAt = WorldTimer::getMSTime(); value->Set(state);
        go = nullptr;
    }
    auto reject = [&]() {
        if (go) state.rejected[go->GetObjectGuid()] = WorldTimer::getMSTime();
        state.device.Clear(); state.routeOwned = state.returning = false; value->Set(state);
        if (ownSpline) ai->StopMoving();
        return false;
    };
    if (state.returning && (WorldTimer::getMSTimeDiff(state.recoveryAt, WorldTimer::getMSTime()) >= 8000 ||
        bot->GetDistance(state.originX, state.originY, state.originZ) <= 2.0f)) return reject();
    // Do not cancel a cast or fight native crowd control to service a trap.
    if (bot->IsNonMeleeSpellCasted(true) || !ai->CanMove()) return false;
    if (!state.returning && (!go || SuppressionDeviceInCastRange(ai, go))) return false;
    const WorldPosition destination = state.returning ?
        WorldPosition(bot->GetMapId(), state.originX, state.originY, state.originZ) : WorldPosition(go);
    PathFinder path(bot);
    if (!path.calculate(destination.getX(), destination.getY(), destination.getZ(), false) ||
        path.getPathType() != PATHFIND_NORMAL || path.getPath().size() < 2 || path.getPath().size() > 256) return reject();
    auto hazards = AI_VALUE(std::list<HazardPosition>, "hazards");
    AppendBlackwingGroundHazards(ai, hazards);
    // Generic enemy path clipping is disabled in combat. Device duty must not
    // cross an untouched pack even while whelps already keep the raid in combat.
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
            enemy->HasCharmer() || !enemy->CanAttackOnSight(bot)) continue;
        if (enemy->IsInCombat())
        {
            // Native Growing Flames (22442) pulses around engaged Hatchers.
            // Stealth does not prevent its damage from revealing a duty rogue.
            if (enemy->GetEntry() == 12468) hazards.emplace_back(WorldPosition(enemy), 17.0f);
            continue;
        }
        float detection = enemy->GetAttackDistance(bot);
        bool stealth = bot->HasAuraType(SPELL_AURA_MOD_STEALTH) && bot->getAttackers().empty() &&
            !bot->HasAuraTypeWithCaster(SPELL_AURA_MOD_STALKED, enemy->GetObjectGuid());
#ifndef MANGOSBOT_ZERO
        stealth = stealth && !enemy->HasAuraType(SPELL_AURA_DETECT_STEALTH);
#endif
        if (stealth)
        {
            // Use this core's level/talent/detection calculation. Ordinary
            // aggro radius would make stealth trap duty impossible in dense
            // rooms. Keep a conservative circle even behind the creature.
            const float hiddenRange = bot->GetVisibilityData().GetStealthVisibilityDistance(enemy,
                bot->HasFlag(UNIT_FIELD_FLAGS, UNIT_FLAG_PLAYER_CONTROLLED));
            if (std::isfinite(hiddenRange)) detection = std::min(detection, std::max(0.0f, hiddenRange));
        }
        hazards.emplace_back(WorldPosition(enemy), detection + 2.0f);
    }
    WorldPosition previous(bot);
    float length = 0;
    for (const auto& point : path.getPath())
    {
        WorldPosition next(bot->GetMapId(), point.x, point.y, point.z);
        length += previous.distance(next);
        if (length > 45 || !IsHazardSafeSegment(previous, next, hazards)) return reject();
        previous = next;
    }
    for (const auto& hazard : hazards)
        if (previous.distance(hazard.first) <= hazard.second) return reject();
    if (previous.distance(destination) > 2.0f) return reject();
    // Dispatch precisely the checked native route. Returning uses the same
    // current detection/hazard checks, not a blind reversal through a fresh pack.
    if (ownSpline && bot->movespline && !bot->movespline->Finalized())
    {
        const auto end = bot->movespline->FinalDestination();
        if (destination.distance(WorldPosition(bot->GetMapId(), end.x, end.y, end.z)) <= 1.0f) return true;
    }
    if (!state.routeOwned && !state.returning)
    {
        state.originX = bot->GetPositionX(); state.originY = bot->GetPositionY(); state.originZ = bot->GetPositionZ();
        state.movingDevice = go->GetObjectGuid();
    }
    ai->StopMoving();
    bot->SetStandState(UNIT_STAND_STATE_STAND);
#ifndef MANGOSBOT_TWO
    bot->GetMotionMaster()->MovePath(path.getPath(), FORCED_MOVEMENT_RUN, false, false);
#else
    bot->GetMotionMaster()->MovePath(path.getPath(), FORCED_MOVEMENT_RUN, false);
#endif
    state.routeOwned = true;
    state.routeStealthed = bot->HasAuraType(SPELL_AURA_MOD_STEALTH);
    state.splineId = bot->movespline->GetId();
    value->Set(state);
    SetDuration(250);
    return true;
}

bool StealthForSuppressionDeviceAction::isUseful()
{
    if (bot->HasAuraType(SPELL_AURA_MOD_STEALTH) || !AssignedSuppressionDevice(ai)) return false;
    const SpellEntry* disarm = sServerFacade.LookupSpellInfo(SPELL_DISARM_TRAP);
    return !bot->IsInCombat() || (disarm && (disarm->Attributes & SPELL_ATTR_ONLY_STEALTHED) &&
        ai->CanCastSpell("vanish", bot, 0));
}

bool StealthForSuppressionDeviceAction::Execute(Event& event)
{
    return isUseful() && ai->CastSpell(bot->IsInCombat() ? "vanish" : "stealth", bot);
}

bool DisarmSuppressionDeviceAction::isUseful()
{
    const SpellEntry* disarm = sServerFacade.LookupSpellInfo(SPELL_DISARM_TRAP);
    if (!disarm || ((disarm->Attributes & SPELL_ATTR_ONLY_STEALTHED) && !bot->HasAuraType(SPELL_AURA_MOD_STEALTH))) return false;
    return !bot->IsNonMeleeSpellCasted(true) && bot->IsSpellReady(SPELL_DISARM_TRAP) &&
        SuppressionDeviceInCastRange(ai, AssignedSuppressionDevice(ai));
}

bool DisarmSuppressionDeviceAction::Execute(Event& event)
{
    if (!isUseful()) return false;
    GameObject* go = AssignedSuppressionDevice(ai);
    if (bot->IsNonMeleeSpellCasted(true) || !bot->IsSpellReady(SPELL_DISARM_TRAP) ||
        !SuppressionDeviceInCastRange(ai, go)) return false;
    // Native spell validation and loot-state transition own the result and rearm timer.
    return ai->CastSpell(SPELL_DISARM_TRAP, go);
}

bool HourglassSandAction::isUseful()
{
    return bot->IsInWorld() && bot->IsAlive() && bot->GetMapId() == 469 && !bot->HasCharmer() &&
        !bot->IsBeingTeleported() && !ai->IsRealPlayer() && bot->HasAura(23170) && bot->HasItemCount(19183, 1) &&
        UseItemIdAction::isUseful();
}

bool HourglassSandAction::Execute(Event& event)
{
    // The native item spell removes Bronze; never directly remove an aura or
    // invent an item. Recheck because another effect may have cured it already.
    return isUseful() && UseItemIdAction::Execute(event);
}

bool BlackwingLairPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 469 || !bot->GetGroup()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("blackwing lair position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    if (plan.spell == 23331)
    {
        Unit* boss = ai->GetUnit(plan.boss);
        return (ai->IsRanged(bot) || ai->IsHeal(bot)) && boss && boss->IsInWorld() && boss->IsAlive() &&
            bot->IsInMap(boss) && boss->IsInCombat() && !boss->HasCharmer() &&
            boss->GetEntry() == 12017 && boss->GetVictim() != bot;
    }
    if (plan.spell != 18173 && plan.spell != 23620) return false;
    if (Unit* boss = ai->GetUnit(plan.boss))
        if (boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() &&
            boss->IsInCombat() && boss->GetEntry() == 13020 && boss->GetVictim() == bot) return false;
    Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
    if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !carrier->IsAlive() ||
        !bot->IsInMap(carrier) || !carrier->HasAura(plan.spell) || carrier->HasCharmer()) return false;
    Player* player = static_cast<Player*>(carrier);
    return !player->IsBeingTeleported() && player->GetGroup() == bot->GetGroup();
}

bool BlackwingLairPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && EncounterMovementRequired(bot, plan.destination, 1.5f);
}

bool BlackwingLairPositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool BlackwingLairPositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !BlackwingLairBurstThreats(ai, current, threats) ||
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

namespace
{
    Unit* RazorgoreCreature(WorldObject* center, uint32 entry);
    bool RazorgoreEggPhase(PlayerbotAI* ai);

    bool BwlReady(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        return bot->IsInWorld() && bot->IsAlive() && bot->GetMapId() == 469 &&
            bot->IsInCombat() && bot->GetGroup() && !bot->IsBeingTeleported() &&
            !bot->HasCharmer() && !ai->IsRealPlayer();
    }

    bool BwlMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            member->GetGroup() == bot->GetGroup() && !member->HasCharmer() && !member->IsBeingTeleported();
    }

    bool BwlGroupEngaged(PlayerbotAI* ai, Unit* enemy)
    {
        Player* bot=ai->GetBot();
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) || !enemy->IsInCombat()) return false;
        const auto member=[bot](Unit* unit) {
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit)) return false;
            if (!unit->IsPlayer()) unit=unit->GetMaster();
            return BwlMember(bot,dynamic_cast<Player*>(unit));
        };
        if (member(enemy->GetVictim())) return true;
        for (Unit* attacker:enemy->getAttackers()) if (member(attacker)) return true;
        for (const auto* threat:enemy->getThreatManager().getThreatList())
            if (threat && member(ai->GetUnit(threat->getUnitGuid()))) return true;
        return false;
    }

    unsigned BwlAfflictions(Unit* member)
    {
        unsigned count = member->HasAura(22438) ? 8 : 0;
        for (uint32 spell : {23153u, 23154u, 23155u, 23169u, 23170u}) count += member->HasAura(spell) ? 1 : 0;
        return count;
    }

    unsigned BwlAddPriority(uint32 entry)
    {
        switch (entry)
        {
            case 12557: return 4; // Grethok, while engaged; never initiate the event.
            case 12420: return 3; // Razorgore: Blackwing mages.
            case 12416: case 14456: return 2;
            case 12422: return 1;
            case 12468: return 5; // Growing Flames/Flamestrike threat; whelps respawn independently.
            case 12457: return 6; // Spellbinders: physical DPS handles their native magic immunity.
            case 12461: return 4; // Death Talon Overseer.
            case 12459: return 4; // Blackwing Warlock.
            case 13996: return 3; // Goblin technician packs.
            case 12458: return 2; // Blackwing Taskmaster.
            case 12460: case 12463: case 12464: case 12465: case 12467: return 1;
            case 14022: case 14023: case 14024: case 14025: return 1;
            case 14668: return 3; // Nefarian's hostile infernals.
            case 14101: return 3; // Warlock portal guardians.
            case 14662: case 14663: case 14664: case 14666: case 14667: return 7; // Hostile class-call totems.
            case 14605: return 3; // Nefarian's raised bone constructs.
            case 14261: case 14262: case 14263: case 14264: case 14265: case 14302: return 2;
            default: return 0;
        }
    }
}

bool ai::IsProtectedBlackwingTarget(Player* bot, Unit* target)
{
    if (!bot || !target || !bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        !target->IsInWorld() || !bot->IsInMap(target) || !bot->GetPlayerbotAI() ||
        bot->GetPlayerbotAI()->IsRealPlayer()) return false;
    if (target->GetEntry() == 10162) return target->HasAura(22663); // Native immunity barrier.
    if (target->GetEntry() != 12435) return false;
    // Native instance marks TYPE_RAZORGORE (0) SPECIAL only after the last egg.
    // Read phase state; never change the instance, eggs, charm or boss script.
    InstanceData* instance = bot->GetMap()->GetInstanceData();
    return instance && instance->GetData(0) != SPECIAL;
}

Unit* BlackwingLairPriorityTargetAction::GetTarget()
{
    if (!BwlReady(ai) || ai->IsHeal(bot)) return nullptr;
    auto valid = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() &&
            !unit->HasCharmer() && bot->IsInMap(unit) && BwlGroupEngaged(ai, unit) && !sServerFacade.IsFriendlyTo(bot, unit) &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    bool broodlordActive = false;
    for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (valid(unit) && unit->GetEntry() == 12017) { broodlordActive = true; break; }
    }
    // Damage marks are not multi-tank assignments. Keep the native boss holder
    // anchored, and distribute engaged adds before applying the DPS kill order.
    if (ai->IsTank(bot))
    {
        std::vector<Unit*> enemies;
        for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
        {
            Unit* unit = ai->GetUnit(guid);
            if (!valid(unit)) continue;
            const uint32 entry = unit->GetEntry();
            const bool boss = entry == 12435 || entry == 13020 || entry == 12017 || entry == 11983 ||
                entry == 14601 || entry == 11981 || entry == 14020 || entry == 11583;
            if (boss && unit->GetVictim() == bot) return unit;
            if (BwlAddPriority(entry) && !(broodlordActive && entry >= 14022 && entry <= 14025)) enemies.push_back(unit);
        }
        std::sort(enemies.begin(), enemies.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        std::vector<Player*> tanks;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* tank = ref->getSource();
            if (!BwlMember(bot, tank) || !ai->IsTank(tank) || tank->GetDistance(bot) > 80.0f ||
                !tank->GetPlayerbotAI() || tank->GetPlayerbotAI()->IsRealPlayer()) continue;
            // A tank holding any raid boss cannot volunteer for an add.
            Unit* victim = tank->GetVictim();
            if (victim && victim->GetVictim() == tank)
            {
                const uint32 entry = victim->GetEntry();
                if (entry == 12435 || entry == 13020 || entry == 12017 || entry == 11983 ||
                    entry == 14601 || entry == 11981 || entry == 14020 || entry == 11583) continue;
            }
            tanks.push_back(tank);
        }
        std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        std::map<Player*, unsigned> load;
        Unit* held = nullptr;
        for (Unit* enemy : enemies)
        {
            Player* holder = dynamic_cast<Player*>(enemy->GetVictim());
            if (BwlMember(bot, holder) && ai->IsTank(holder))
            {
                ++load[holder];
                if (holder == bot && !held) held = enemy;
            }
        }
        Unit* rescue = nullptr;
        for (Unit* enemy : enemies)
        {
            Player* holder = dynamic_cast<Player*>(enemy->GetVictim());
            if (BwlMember(bot, holder) && ai->IsTank(holder)) continue;
            Player* owner = nullptr;
            for (Player* tank : tanks)
                if (!owner || load[tank] < load[owner]) owner = tank;
            if (!owner) break;
            ++load[owner];
            if (owner == bot && !rescue) rescue = enemy;
        }
        if (rescue || held) return rescue ? rescue : held;
        return nullptr;
    }
    if (valid(ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"))) ||
        valid(ai->GetUnit(AI_VALUE(ObjectGuid, "rti target")))) return nullptr;
    // Preserve boss ownership. Off-tanks can acquire loose adds; the active
    // boss tank must not abandon its dragon for a higher-priority add.
    for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && unit->GetVictim() == bot &&
            ((unit->GetEntry() == 12435 && !IsProtectedBlackwingTarget(bot, unit)) || unit->GetEntry() == 11583)) return nullptr;
    }
    Unit* controlledDragon = RazorgoreEggPhase(ai) ? RazorgoreCreature(bot, 12435) : nullptr;
    Unit* controller = controlledDragon ? controlledDragon->GetCharmer() : nullptr;
    if (!controller || !controller->IsPlayer() || !BwlMember(bot, static_cast<Player*>(controller)))
    { controlledDragon = nullptr; controller = nullptr; }
    Unit* selected = nullptr;
    unsigned priority = 0;
    for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!valid(unit)) continue;
        unsigned rank = BwlAddPriority(unit->GetEntry());
        if (broodlordActive && unit->GetEntry() >= 14022 && unit->GetEntry() <= 14025) continue;
        if (unit->GetEntry() == 12457 && ai->IsRanged(bot) && bot->getClass() != CLASS_HUNTER) continue;
        if (!rank) continue;
        // Split already-engaged mixed trash by damage role. This does not
        // acquire the next pack, override a player's kill mark/order, or
        // redistribute the separately elected tanks.
        if ((!ai->IsRanged(bot) && unit->GetEntry()==12459) ||
            (ai->IsRanged(bot) && unit->GetEntry()==13996)) rank=8;
        if (controller && (unit->GetVictim() == controller || unit->GetVictim() == controlledDragon)) rank += 10;
        if (!selected || rank > priority || (rank == priority &&
            unit->GetObjectGuid() < selected->GetObjectGuid()))
        { selected = unit; priority = rank; }
    }
    return selected;
}

bool BlackwingLairPriorityTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
}

bool BlackwingLairSupportAction::Select(std::string& spell, Unit*& target)
{
    if (!BwlReady(ai) || bot->IsNonMeleeSpellCasted(true)) return false;
    const auto ready = [&](const char* name, Unit* unit) {
        if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
        spell = name; target = unit; return true;
    };
    if (ai->IsTank(bot))
    {
        BlackwingLairPriorityTargetAction assignment(ai);
        Unit* assigned = assignment.GetTarget();
        Unit* victim = assigned ? assigned->GetVictim() : nullptr;
        Player* holder = dynamic_cast<Player*>(victim);
        if (assigned && victim != bot && !(BwlMember(bot, holder) && ai->IsTank(holder)))
            for (const char* name : {"taunt", "growl", "hand of reckoning", "righteous defense", "dark command"})
                if (ready(name, assigned)) return true;
    }
    std::vector<Unit*> demons;
    bool otherEnemy = false;
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !enemy->IsInCombat() ||
            !bot->IsInMap(enemy) || enemy->HasCharmer() || sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        if (enemy->GetEntry() == 14101 || enemy->GetEntry() == 14668) demons.push_back(enemy);
        else if (!IsProtectedBlackwingTarget(bot, enemy) &&
            PossibleAttackTargetsValue::IsValid(enemy, bot, sPlayerbotAIConfig.sightDistance, false, true)) otherEnemy = true;
        if (((enemy->GetEntry() == 11981 && enemy->HasAura(23342)) ||
             (enemy->GetEntry() == 14020 && enemy->HasAura(23128)) ||
             (enemy->GetEntry() == 12464 && enemy->HasAura(22428))) && ready("tranquilizing shot", enemy)) return true;
        // Native casts, not guessed encounter timers. Recheck admission at
        // dispatch so a second interrupter cannot spend an ability on a completed cast.
        for (CurrentSpellTypes slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        {
            const Spell* cast = enemy->GetCurrentSpell(slot);
            if (!cast || !cast->m_spellInfo || cast->getState() == SPELL_STATE_FINISHED) continue;
            switch (cast->m_spellInfo->Id)
            {
                case 22458: case 22372: case 22425: case 22275: case 22274:
                case 17290: case 22272: case 22336:
                    for (const char* name : {"kick", "pummel", "shield bash", "counterspell", "earth shock", "wind shear", "mind freeze", "spell lock"})
                        if (ready(name, enemy)) return true;
                    break;
            }
        }
        if (enemy->GetEntry() == 11583 && enemy->GetVictim() && enemy->GetVictim()->IsPlayer())
        {
            Player* tank = static_cast<Player*>(enemy->GetVictim());
            if (BwlMember(bot, tank) && !ai->HasAura("fear ward", tank) && ready("fear ward", tank)) return true;
        }
    }
    if (bot->getClass() == CLASS_WARLOCK && !demons.empty())
    {
        std::sort(demons.begin(), demons.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        // Native Banish is unbreakable. Keep assignments through its aura, and
        // release one demon at a time once the rest of the engaged pack is dead.
        if (!otherEnemy) demons.erase(demons.begin());
        std::vector<Player*> controllers;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (BwlMember(bot, member) && member->getClass() == CLASS_WARLOCK && member->GetPlayerbotAI() &&
                !member->GetPlayerbotAI()->IsRealPlayer() && (member->HasSpell(710) || member->HasSpell(18647)) &&
                member->GetDistance(bot) <= 80) controllers.push_back(member);
        }
        std::sort(controllers.begin(), controllers.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        const auto self = std::find(controllers.begin(), controllers.end(), bot);
        const size_t slot = size_t(self - controllers.begin());
        if (self != controllers.end() && slot < demons.size())
        {
            Unit* demon = demons[slot];
            if (!ai->HasAura("banish", demon) && !PossibleAttackTargetsValue::HasBreakableCC(demon, bot) &&
                !PossibleAttackTargetsValue::HasUnBreakableCC(demon, bot) && ready("banish", demon)) return true;
        }
    }
    if (ai->IsHeal(bot) && RazorgoreEggPhase(ai))
    {
        Unit* dragon = RazorgoreCreature(bot, 12435);
        Unit* owner = dragon ? dragon->GetCharmer() : nullptr;
        if (dragon && dragon->GetHealthPercent() < 70.0f && owner && owner->IsPlayer() &&
            BwlMember(bot, static_cast<Player*>(owner)) && sServerFacade.IsFriendlyTo(bot, dragon))
            for (const char* name : {"flash heal", "healing wave", "healing touch", "flash of light"})
                if (ready(name, dragon)) return true;
    }
    std::vector<Player*> members;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        if (BwlMember(bot, ref->getSource())) members.push_back(ref->getSource());
    std::sort(members.begin(), members.end(), [this](Player* a, Player* b) {
        // Prevent five-affliction mutation first, then favour tanks and low health.
        if (BwlAfflictions(a) != BwlAfflictions(b)) return BwlAfflictions(a) > BwlAfflictions(b);
        if (ai->IsTank(a) != ai->IsTank(b)) return ai->IsTank(a);
        if (a->GetHealthPercent() != b->GetHealthPercent()) return a->GetHealthPercent() < b->GetHealthPercent();
        return a->GetObjectGuid() < b->GetObjectGuid();
    });
    for (Player* member : members)
        for (uint32 aura : {22438u, 22274u, 22335u, 22423u, 22687u, 23153u, 23154u, 23155u, 23169u})
        {
            if (!member->HasAura(aura)) continue;
            const SpellEntry* info = sServerFacade.LookupSpellInfo(aura);
            if (!info) continue;
            // Consult this core's spell data. Bronze is deliberately excluded:
            // existing Hourglass Sand logic must consume a real owned item.
            switch (info->Dispel)
            {
                case DISPEL_MAGIC:
                    for (const char* name : {"dispel magic", "cleanse"}) if (ready(name, member)) return true;
                    break;
                case DISPEL_CURSE:
                    for (const char* name : {"remove lesser curse", "remove curse", "cleanse spirit"}) if (ready(name, member)) return true;
                    break;
                case DISPEL_DISEASE:
                    for (const char* name : {"cure disease", "cleanse", "purify", "abolish disease"}) if (ready(name, member)) return true;
                    break;
                case DISPEL_POISON:
                    for (const char* name : {"cure poison", "cleanse", "purify", "cleanse spirit", "abolish poison"}) if (ready(name, member)) return true;
                    break;
                default: break;
            }
        }
    // Chromaggus' live shield picks a vulnerable school. This is a DPS-only
    // override after dispel/interrupt duties; never cancel an in-flight cast.
    Unit* enemy = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    if (ai->IsRanged(bot) && !ai->IsHeal(bot) && !ai->IsTank(bot) && enemy && enemy->GetEntry() == 14020 &&
        enemy->IsInWorld() && enemy->IsAlive() && enemy->IsInCombat() && bot->IsInMap(enemy))
        for (uint32 aura : {22277u, 22278u, 22279u, 22280u, 22281u})
        {
            if (!enemy->HasAura(aura)) continue;
            const SpellEntry* shield = sServerFacade.LookupSpellInfo(aura);
            if (!shield) continue;
            // Read the positive native modifier instead of assuming school IDs
            // or changing the boss's resistance/aura state.
            for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
            {
                if (shield->EffectApplyAuraName[effect] != SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN ||
                    shield->EffectBasePoints[effect] <= 0) continue;
                switch (shield->EffectMiscValue[effect])
                {
                    case SPELL_SCHOOL_MASK_FIRE:
                        for (const char* name : {"fireball", "incinerate", "searing pain"}) if (ready(name, enemy)) return true;
                        break;
                    case SPELL_SCHOOL_MASK_FROST:
                        if (ready("frostbolt", enemy)) return true;
                        break;
                    case SPELL_SCHOOL_MASK_SHADOW:
                        for (const char* name : {"shadow bolt", "mind blast", "mind flay"}) if (ready(name, enemy)) return true;
                        break;
                    case SPELL_SCHOOL_MASK_NATURE:
                        for (const char* name : {"wrath", "lightning bolt"}) if (ready(name, enemy)) return true;
                        break;
                    case SPELL_SCHOOL_MASK_ARCANE:
                        for (const char* name : {"arcane missiles", "arcane shot"}) if (ready(name, enemy)) return true;
                        break;
                }
            }
        }
    return false;
}

bool BlackwingLairSupportAction::isUseful()
{
    std::string spell; Unit* target = nullptr;
    return Select(spell, target);
}

bool BlackwingLairSupportAction::Execute(Event& event)
{
    std::string spell; Unit* target = nullptr;
    if (!Select(spell, target)) return false;
    uint32 duration = sPlayerbotAIConfig.globalCoolDown;
    if (!ai->CastSpell(spell, target, nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}


bool ai::BlackwingMeleeFlankAngle(PlayerbotAI* ai, Unit* target, float& angle)
{
    if (!BwlReady(ai) || !target || !target->IsInWorld() || !target->IsAlive() ||
        !target->IsInCombat() || !ai->GetBot()->IsInMap(target) || target->HasCharmer() ||
        (target->GetEntry() != 13020 && target->GetEntry() != 11583)) return false;
    Player* bot = ai->GetBot();
    if (target->GetVictim() == bot || ai->IsTank(bot) || ai->IsHeal(bot) || ai->IsRanged(bot)) return false;
    // Rear flanks retain the rear-facing melee benefit without aiming down
    // the native dragon's tail. Stay on the nearer side to avoid crossing it.
    const float side = std::sin(target->GetAngle(bot) - target->GetOrientation()) >= 0 ? 1.0f : -1.0f;
    angle = target->GetOrientation() + side * float(M_PI) * (2.0f / 3.0f);
    return true;
}
namespace
{
    std::vector<GameObject*> RazorgoreObjects(WorldObject* center, uint32 entry)
    {
        std::list<GameObject*> found;
        MaNGOS::GameObjectEntryInPosRangeCheck check(*center, entry,
            center->GetPositionX(), center->GetPositionY(), center->GetPositionZ(), 150.0f);
        MaNGOS::GameObjectListSearcher<MaNGOS::GameObjectEntryInPosRangeCheck> searcher(found, check);
        Cell::VisitAllObjects(center, searcher, 150.0f);
        std::vector<GameObject*> result;
        for (GameObject* object : found)
            if (object && object->IsInWorld() && center->IsInMap(object) && sServerFacade.isSpawned(object)) result.push_back(object);
        return result;
    }

    Unit* RazorgoreCreature(WorldObject* center, uint32 entry)
    {
        std::list<Unit*> found;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(center, entry, 150.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(found, check);
        Cell::VisitAllObjects(center, searcher, 150.0f);
        for (Unit* unit : found)
            if (unit && unit->IsInWorld() && unit->IsAlive() && center->IsInMap(unit)) return unit;
        return nullptr;
    }

    bool RazorgoreEggPhase(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            bot->GetMapId() != 469 || !bot->GetGroup() || ai->IsRealPlayer()) return false;
        InstanceData* instance = bot->GetMap()->GetInstanceData();
        return instance && instance->GetData(0) == IN_PROGRESS;
    }
}

GameObject* RazorgoreOrbAction::SelectOrb()
{
    if (!RazorgoreEggPhase(ai) || bot->GetCharm() || bot->HasAura(23958)) return nullptr;
    Unit* dragon = RazorgoreCreature(bot, 12435);
    // Never steal human or another bot's active control. Grethok must first die.
    if (!dragon || dragon->HasCharmer() || RazorgoreCreature(dragon, 12557)) return nullptr;
    auto orbs = RazorgoreObjects(dragon, 177808);
    if (orbs.empty()) return nullptr;
    GameObject* orb = orbs.front();
    if (orb->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT | GO_FLAG_IN_USE)) return nullptr;
    std::vector<Player*> candidates;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!BwlMember(bot, member) || !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer() ||
            member->GetCharm() || member->HasAura(23958) || member->GetDistance(orb) > 150.0f ||
            member->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) || ai->IsTank(member) || ai->IsHeal(member)) continue;
        candidates.push_back(member);
    }
    std::sort(candidates.begin(), candidates.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    if (candidates.empty()) return nullptr;
    // A bounded election lease lets another eligible DPS try if a path or click
    // fails. Successful possession, not the timer, owns control thereafter.
    const size_t slot = (WorldTimer::getMSTime() / 30000u) % candidates.size();
    return candidates[slot] == bot ? orb : nullptr;
}

bool RazorgoreOrbAction::isUseful()
{
    return SelectOrb() != nullptr;
}

bool RazorgoreOrbAction::Execute(Event& event)
{
    GameObject* orb = SelectOrb();
    if (!orb || !ai->CanMove()) return false;
#ifdef MANGOSBOT_ZERO
    const bool inRange = orb->IsWithinDistInMap(bot, orb->GetInteractionDistance());
#else
    const bool inRange = orb->IsAtInteractDistance(bot);
#endif
    if (!inRange || !bot->IsWithinLOSInMap(orb))
        return MoveTo(bot->GetMapId(), orb->GetPositionX(), orb->GetPositionY(), orb->GetPositionZ(),
            false, false, false, true);
    ai->StopMoving();
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << orb->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(1000); // A submitted click is not proof of possession.
    return true;
}

bool RazorgoreOrbAction::UpdateControl()
{
    Unit* dragon = bot->IsInWorld() ? bot->GetCharm() : nullptr;
    if (!RazorgoreEggPhase(ai) || !dragon || dragon->GetEntry() != 12435 ||
        !dragon->IsInWorld() || !dragon->IsAlive() || !bot->IsInMap(dragon) ||
        !dragon->HasCharmer(bot->GetObjectGuid()))
    {
        lastControlUpdate = 0; controlledGuid.Clear(); movingToEgg.Clear(); castEgg.Clear(); castAttempts = 0; failedEggs.clear();
        return false;
    }
    // Suppress only this controller's ordinary AI while it possesses the boss.
    // Movement/casting affect the charmed unit, never teleport or mutate eggs.
    const uint32 now = WorldTimer::getMSTime();
    if (lastControlUpdate && WorldTimer::getMSTimeDiff(lastControlUpdate, now) < 500) return true;
    lastControlUpdate = now;
    if (controlledGuid != dragon->GetObjectGuid())
    { controlledGuid = dragon->GetObjectGuid(); movingToEgg.Clear(); castEgg.Clear(); castAttempts = 0; failedEggs.clear(); }
    // Possession is expected here; LOST_CONTROL includes POSSESSED and would
    // prevent every egg cast. Native stuns/fear still block the controller.
    if (dragon->IsNonMeleeSpellCasted(true) || dragon->hasUnitState(UNIT_STAT_CAN_NOT_REACT)) return true;
    const SpellEntry* destroy = sServerFacade.LookupSpellInfo(19873);
    if (!destroy || !dragon->HasSpell(19873)) return true;
    const float range = GetSpellMaxRange(sSpellRangeStore.LookupEntry(destroy->rangeIndex));
    if (!std::isfinite(range) || range <= 0 || range > 100) return true;
    auto eggs = RazorgoreObjects(dragon, 177807);
    std::sort(eggs.begin(), eggs.end(), [dragon](GameObject* a, GameObject* b) {
        if (dragon->GetDistance(a) != dragon->GetDistance(b)) return dragon->GetDistance(a) < dragon->GetDistance(b);
        return a->GetObjectGuid() < b->GetObjectGuid();
    });
    unsigned pathChecks = 0;
    for (GameObject* egg : eggs)
    {
        // EffectActivateObject(DESTROY) changes the native GO state. Do not
        // count a packet attempt or repeatedly submit an already-used egg.
        if (egg->GetGoState() != GO_STATE_READY || egg->GetLootState() != GO_READY) continue;
        auto rejected = failedEggs.find(egg->GetObjectGuid());
        if (rejected != failedEggs.end() && WorldTimer::getMSTimeDiff(rejected->second, now) < 15000) continue;
        if (dragon->IsWithinDistInMap(egg, std::max(1.0f, range - 1.0f)) && dragon->IsWithinLOSInMap(egg))
        {
            dragon->StopMoving(); movingToEgg.Clear();
            if (!dragon->IsSpellReady(*destroy)) return true;
            if (castEgg != egg->GetObjectGuid()) { castEgg = egg->GetObjectGuid(); castAttempts = 0; }
            if (++castAttempts > 3)
            { failedEggs[egg->GetObjectGuid()] = now; castAttempts = 0; continue; }
            dragon->SetFacingToObject(egg);
            SpellCastTargets targets;
            targets.setGOTarget(egg);
            WorldPacket packet(CMSG_PET_CAST_SPELL);
            packet << dragon->GetObjectGuid();
#ifdef MANGOSBOT_TWO
            packet << uint8(0) << uint32(19873) << uint8(0);
#else
            packet << uint32(19873);
#endif
            packet << targets;
            // Native handler checks ownership, learned spell, cooldown, targets
            // and cast admission. The native spell script records egg progress.
            bot->GetSession()->HandlePetCastSpellOpcode(packet);
            return true;
        }
        if (movingToEgg == egg->GetObjectGuid())
        {
            if (WorldTimer::getMSTimeDiff(eggMoveStarted, now) >= 30000)
            {
                dragon->StopMoving(); movingToEgg.Clear(); failedEggs[egg->GetObjectGuid()] = now;
                continue;
            }
            if (!dragon->IsStopped()) return true;
        }
        if (++pathChecks > 4) break;
        PathFinder path(dragon);
        if (!path.calculate(egg->GetPositionX(), egg->GetPositionY(), egg->GetPositionZ(), false) ||
            path.getPathType() != PATHFIND_NORMAL || path.getPath().size() < 2)
        { failedEggs[egg->GetObjectGuid()] = now; continue; }
        if (movingToEgg != egg->GetObjectGuid()) eggMoveStarted = now;
        movingToEgg = egg->GetObjectGuid();
        dragon->GetMotionMaster()->MovePoint(19873, egg->GetPositionX(), egg->GetPositionY(), egg->GetPositionZ(),
            FORCED_MOVEMENT_RUN, true);
        return true;
    }
    return true; // Keep possession intact while native cooldowns/paths recover.
}
