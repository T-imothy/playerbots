#include "playerbot/playerbot.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "MotionGenerators/PathFinder.h"
#include "BlackwingLairDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

#include "playerbot/ServerFacade.h"

#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

#include "AI/ScriptDevAI/include/sc_instance.h"

using namespace ai;

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
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
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

    unsigned BwlAfflictions(Unit* member)
    {
        unsigned count = 0;
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
            !unit->HasCharmer() && bot->IsInMap(unit) && !sServerFacade.IsFriendlyTo(bot, unit) &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
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
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    Unit* selected = nullptr;
    unsigned priority = 0;
    for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!valid(unit)) continue;
        unsigned rank = BwlAddPriority(unit->GetEntry());
        if (!rank) continue;
        if (controller && (unit->GetVictim() == controller || unit->GetVictim() == controlledDragon)) rank += 10;
        if (!selected || rank > priority || (rank == priority &&
            (unit == current || (selected != current && bot->GetDistance(unit) < bot->GetDistance(selected)))))
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
    if (!BwlReady(ai)) return false;
    const auto ready = [&](const char* name, Unit* unit) {
        if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
        spell = name; target = unit; return true;
    };
    for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible targets no los"))
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !enemy->IsInCombat() ||
            !bot->IsInMap(enemy) || enemy->HasCharmer() || sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        if (((enemy->GetEntry() == 11981 && enemy->HasAura(23342)) ||
             (enemy->GetEntry() == 14020 && enemy->HasAura(23128))) && ready("tranquilizing shot", enemy)) return true;
        if (enemy->GetEntry() == 11583 && enemy->GetVictim() && enemy->GetVictim()->IsPlayer())
        {
            Player* tank = static_cast<Player*>(enemy->GetVictim());
            if (BwlMember(bot, tank) && !ai->HasAura("fear ward", tank) && ready("fear ward", tank)) return true;
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
        for (uint32 aura : {22687u, 23153u, 23154u, 23155u, 23169u})
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
    if (!orb->IsAtInteractDistance(bot) || !bot->IsWithinLOSInMap(orb))
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
        dragon->GetCharmerGuid() != bot->GetObjectGuid())
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
