#include "playerbot/playerbot.h"
#include "MoltenCoreLavaTrashActions.h"
#include "MoltenCoreGarrActions.h"
#include "MovementPathSafety.h"
#include "playerbot/strategy/values/LavaTrashControlValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/strategy/CasterCombatPolicy.h"
#include "Combat/ThreatManager.h"
#include "Util/Timer.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;
namespace
{
    bool Member(Player* bot, Player* player, bool living = true)
    {
        return player && player->IsInWorld() && (!living || player->IsAlive()) &&
            !player->IsBeingTeleported() && !player->HasCharmer() && bot->IsInMap(player) &&
            player->GetGroup() == bot->GetGroup();
    }
    bool Belongs(PlayerbotAI* ai, Unit* unit)
    {
        if (!unit) return false;
        if (!unit->IsPlayer()) unit = unit->GetOwner();
        return unit && unit->IsPlayer() && Member(ai->GetBot(), static_cast<Player*>(unit), false);
    }
    bool Engaged(PlayerbotAI* ai, Unit* unit)
    {
        Player* bot = ai->GetBot();
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() ||
            unit->HasCharmer() || !bot->IsInMap(unit) || sServerFacade.IsFriendlyTo(bot, unit)) return false;
        if (Belongs(ai, unit->GetVictim())) return true;
        for (const auto* reference : unit->getThreatManager().getThreatList())
            if (reference && (bot->GetGroup()->IsMember(reference->getUnitGuid()) ||
                Belongs(ai, ai->GetUnit(reference->getUnitGuid())))) return true;
        for (uint32 spell : {710u, 18647u})
            if (SpellAuraHolder* aura = unit->GetSpellAuraHolder(spell))
                if (bot->GetGroup()->IsMember(aura->GetCasterGuid())) return true;
        return false;
    }
    struct Trash
    {
        LavaTrashControl control;
        std::vector<Unit*> elementals, priorities;
    };
    Trash Read(PlayerbotAI* ai)
    {
        Trash result;
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsRealPlayer() || !ai->HasRealPlayerMaster() || GarrEncounterActive(ai)) return result;
        std::vector<PlayerbotAI*> contexts;
        std::vector<uint32_t> locks;
        bool combat = false;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!Member(bot, member, false)) continue;
            combat = combat || member->IsInCombat();
            PlayerbotAI* other = member->GetPlayerbotAI();
            if (!other || other->IsRealPlayer() || !other->HasRealPlayerMaster()) continue;
            contexts.push_back(other);
            if (member->IsAlive() && member->getClass() == CLASS_WARLOCK && other->HasSpell("banish"))
                locks.push_back(member->GetGUIDLow());
        }
        std::sort(contexts.begin(), contexts.end(), [](PlayerbotAI* a, PlayerbotAI* b) { return a->GetBot()->GetObjectGuid() < b->GetBot()->GetObjectGuid(); });
        const uint32 groupId = bot->GetGroup()->GetId();
        if (!contexts.empty()) result.control = contexts.front()->GetAiObjectContext()->GetValue<LavaTrashControl>("lava trash control")->Get();
        const auto original = result.control;
        if (!combat || result.control.groupId != groupId || result.control.map != bot->GetMapId() || result.control.instance != bot->GetInstanceId())
            result.control = LavaTrashControl();
        result.control.groupId = groupId; result.control.map = bot->GetMapId(); result.control.instance = bot->GetInstanceId();
        // Recover a mirrored ledger if the former controller disappeared or reset.
        if (combat) for (PlayerbotAI* other : contexts)
        {
            const auto previous = other->GetAiObjectContext()->GetValue<LavaTrashControl>("lava trash control")->Get();
            if (previous.groupId != groupId || previous.map != bot->GetMapId() || previous.instance != bot->GetInstanceId()) continue;
            result.control.allocation.released.insert(previous.allocation.released.begin(), previous.allocation.released.end());
            if (!result.control.allocation.focus) result.control.allocation.focus = previous.allocation.focus;
            for (const auto& assignment : previous.allocation.banishes)
                result.control.allocation.banishes.emplace(assignment);
        }
        std::vector<uint32_t> ids;
        std::map<uint32_t, uint32_t> native;
        const uint32 now = WorldTimer::getMSTime();
        if (combat && (!result.control.observedAt || WorldTimer::getMSTimeDiff(result.control.observedAt, now) >= 200))
        {
          result.control.observedElementals.clear(); result.control.observedPriorities.clear();
          for (uint32 entry : {12076u, 12100u, 11666u, 11667u})
          {
            // Scan actual native group combat, including CC targets omitted
            // from attackable values. No proximity-only target recruitment.
            std::list<Unit*> nearby;
            MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, entry, 100.0f);
            MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby, check);
            Cell::VisitAllObjects(bot, searcher, 100.0f);
            for (Unit* unit : nearby)
            {
                if (!Engaged(ai, unit)) continue;
                ((entry == 12076 || entry == 12100) ? result.control.observedElementals : result.control.observedPriorities).push_back(unit->GetObjectGuid());
            }
          }
          result.control.observedAt = now;
        }
        // Cache identities, never raw Unit pointers. Death, aura ownership and
        // native engagement are rechecked on every decision/actual cast.
        for (ObjectGuid guid : result.control.observedPriorities)
            if (Unit* unit = ai->GetUnit(guid)) if (Engaged(ai, unit)) result.priorities.push_back(unit);
        for (ObjectGuid guid : result.control.observedElementals)
            if (Unit* unit = ai->GetUnit(guid)) if (Engaged(ai, unit))
            {
                result.elementals.push_back(unit); ids.push_back(unit->GetGUIDLow());
                for (uint32 spell : {710u, 18647u})
                    if (SpellAuraHolder* aura = unit->GetSpellAuraHolder(spell)) native[unit->GetGUIDLow()] = aura->GetCasterGuid().GetCounter();
            }
        std::sort(ids.begin(), ids.end()); std::sort(locks.begin(), locks.end());
        result.control.allocation.Reconcile(locks, ids, native, !result.priorities.empty());
        if (original.groupId != result.control.groupId || original.map != result.control.map || original.instance != result.control.instance ||
            original.observedAt != result.control.observedAt || original.allocation.banishes != result.control.allocation.banishes ||
            original.allocation.released != result.control.allocation.released || original.allocation.focus != result.control.allocation.focus)
            for (PlayerbotAI* other : contexts) other->GetAiObjectContext()->GetValue<LavaTrashControl>("lava trash control")->Set(result.control);
        return result;
    }
}

bool ai::LavaTrashCombatActive(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 409 || !bot->GetGroup() ||
        bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->HasRealPlayerMaster()) return false;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        if (Member(bot, ref->getSource()) && ref->getSource()->IsInCombat() && ref->getSource()->GetDistance(bot) <= 100) return true;
    return false;
}

Unit* ai::LavaTrashBanishTarget(PlayerbotAI* ai)
{
    auto trash = Read(ai);
    const auto own = trash.control.allocation.banishes.find(ai->GetBot()->GetGUIDLow());
    if (own == trash.control.allocation.banishes.end()) return nullptr;
    for (Unit* target : trash.elementals)
        if (target->GetGUIDLow() == own->second && !trash.control.allocation.released.count(own->second) &&
            !target->HasAura(710) && !target->HasAura(18647) &&
            !PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot()) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(target, ai->GetBot())) return target;
    return nullptr; // Never recast on an active native Banish.
}

Unit* ai::LavaTrashFocusTarget(PlayerbotAI* ai)
{
    auto trash = Read(ai);
    if (!trash.priorities.empty())
    {
        Unit* selected = nullptr;
        const ObjectGuid skull = ai->GetBot()->GetGroup()->GetTargetIcon(7);
        for (Unit* target : trash.priorities)
        {
            if (PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot()) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(target, ai->GetBot())) continue;
            if (target->GetObjectGuid() == skull) return target;
            if (!selected || target->GetObjectGuid() < selected->GetObjectGuid()) selected = target;
        }
        return selected;
    }
    for (Unit* target : trash.elementals)
        if (target->GetGUIDLow() == trash.control.allocation.focus && !target->HasAura(710) && !target->HasAura(18647) &&
            !PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot()) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(target, ai->GetBot())) return target;
    return nullptr;
}

bool ai::LavaTrashReservedTarget(PlayerbotAI* ai, Unit* target)
{
    if (!target || (target->GetEntry() != 12076 && target->GetEntry() != 12100) || ai->GetBot()->GetMapId() != 409) return false;
    return Read(ai).control.allocation.Reserved(target->GetGUIDLow());
}

bool ai::PlanLavaTrashBanish(PlayerbotAI* ai, EncounterPosition& plan)
{
    Unit* target = LavaTrashBanishTarget(ai);
    if (!target) return false;
    Player* bot = ai->GetBot();
    float range = 0;
    if (!ai->GetSpellRange("banish", &range) || range <= 5) return false;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = target->GetObjectGuid(); plan.spell = 18647;
    if (bot->GetDistance(target) <= range - 2 && bot->IsWithinLOSInMap(target))
    {
        plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
        if (ValidateEncounterDestination(ai, plan)) return true;
    }
    const float angle = target->GetAngle(bot);
    for (float offset : {0.0f, 0.25f, -0.25f, 0.5f, -0.5f})
    {
        plan.destination = {target->GetPositionX() + std::cos(angle + offset) * (range - 3),
            target->GetPositionY() + std::sin(angle + offset) * (range - 3), target->GetPositionZ()};
        if (ValidateEncounterDestination(ai, plan)) return true;
    }
    plan.active = false; return false;
}

bool ai::LavaTrashSpellAllowed(PlayerbotAI* ai, const std::string& name, Unit* target, const SpellEntry* spell)
{
    if (ai->GetBot()->GetMapId() != 409) return true;
    if (name == "banish" || name == "banish on cc") return target && target == LavaTrashBanishTarget(ai);
    auto trash = Read(ai);
    if (trash.elementals.empty() && trash.priorities.empty()) return true;
    // Fear scattering is unnecessary while raid tanks and assigned Banish hold
    // these native mobs. Forced fear/stun on players is never cancelled here.
    if (name == "fear" || name == "fear on cc" || name == "howl of terror" || name == "death coil" || name == "death coil on snare target") return false;
    if (!ai->IsTank(ai->GetBot()) && !trash.control.allocation.banishes.empty() &&
        (CasterSpellArea(name) != CasterArea::None || name == "cleave" || name == "whirlwind" ||
         name == "blade flurry" || name == "multi-shot")) return false;
    if (!spell) return true;
    bool damage = CasterDamageSpell(spell);
    for (uint32 effect : spell->Effect)
        damage = damage || effect == SPELL_EFFECT_WEAPON_DAMAGE || effect == SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL ||
            effect == SPELL_EFFECT_NORMALIZED_WEAPON_DMG || effect == SPELL_EFFECT_WEAPON_PERCENT_DAMAGE;
    if (!damage || !target || sServerFacade.IsFriendlyTo(ai->GetBot(), target)) return true;
    if (trash.control.allocation.Reserved(target->GetGUIDLow()) && (target->GetEntry() == 12076 || target->GetEntry() == 12100)) return false;
    if (!ai->IsTank(ai->GetBot()))
    {
        Unit* focus = LavaTrashFocusTarget(ai);
        if (focus && (target->GetEntry() == 12076 || target->GetEntry() == 12100 || target->GetEntry() == 11666 || target->GetEntry() == 11667) && target != focus) return false;
    }
    return true;
}

bool ai::MoltenCoreGroupEnemy(PlayerbotAI* ai, Unit* target)
{
    return ai->GetBot()->GetGroup() && Engaged(ai, target);
}

bool ai::MoltenCoreRecoveryTrash(uint32 entry)
{
    // Bosses and their encounter adds retain their dedicated positioning.
    // Ordinary raid trash uses native group engagement, not a short whitelist.
    switch (entry)
    {
        case 12118: case 11982: case 12259: case 12057: case 12056:
        case 12264: case 12098: case 11988: case 12018: case 11502:
        case 12119: case 11661: case 12099: case 11662: case 11672:
        case 11663: case 11664: case 12143: return false;
        default: return true;
    }
}

Unit* ai::MoltenCoreTrashAggroTarget(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsTank(bot) || !ai->HasRealPlayerMaster()) return nullptr;
    Unit* pursuer = nullptr;
    // The native attacker set updates on victim changes; do not wait for a
    // cached possible-target snapshot when a giant changes victims.
    for (Unit* enemy : bot->getAttackers())
        if (Engaged(ai, enemy) && enemy->GetVictim() == bot && MoltenCoreRecoveryTrash(enemy->GetEntry()) &&
            !enemy->HasAura(19951) && !LavaTrashReservedTarget(ai, enemy) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot) &&
            (!pursuer || enemy->GetObjectGuid() < pursuer->GetObjectGuid())) pursuer = enemy;
    return pursuer;
}

bool ai::PlanLavaTrashCarrier(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    Unit* pursuer = MoltenCoreTrashAggroTarget(ai);
    if (!pursuer) return false;
    Player* tank = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!Member(bot, member) || !ai->IsTank(member) || !member->CanReactInCombat() || member->GetDistance(bot) > 60) continue;
        if (!tank || member->GetDistance(bot) < tank->GetDistance(bot) ||
            (member->GetDistance(bot) == tank->GetDistance(bot) && member->GetObjectGuid() < tank->GetObjectGuid())) tank = member;
    }
    if (!tank) return false;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = pursuer->GetObjectGuid(); plan.source = tank->GetObjectGuid(); plan.spell = 19771;
    plan.destination = {tank->GetPositionX(), tank->GetPositionY(), tank->GetPositionZ()};
    if (bot->GetDistance(tank) <= 3) plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false; return false;
}

bool ai::LavaTrashRouteSafe(PlayerbotAI* ai, const std::vector<WorldPosition>& path)
{
    Player* bot = ai->GetBot();
    if (!LavaTrashCombatActive(ai)) return true;
    if (path.empty()) return false;
    struct Unpulled
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(Unit* unit) const
        {
            return unit && unit->GetTypeId() == TYPEID_UNIT && unit->IsInWorld() && unit->IsAlive() &&
                bot->IsInMap(unit) && !unit->IsInCombat() && !unit->HasCharmer() &&
                unit->CanInitiateAttack() && unit->CanAttackOnSight(bot);
        }
    } check{bot};
    std::list<Unit*> units;
    MaNGOS::UnitListSearcher<Unpulled> searcher(units, check);
    Cell::VisitAllObjects(bot, searcher, 90.0f);
    std::list<HazardPosition> aggro;
    for (Unit* unit : units)
    {
        const float distance = unit->GetAttackDistance(bot);
        if (distance > 0 && distance < 60)
            aggro.emplace_back(WorldPosition(unit), distance + unit->GetCombatReach() + bot->GetCombatReach() + 1);
    }
    WorldPosition previous(bot);
    for (const WorldPosition& waypoint : path)
    {
        if (!IsHazardSafeSegment(previous, waypoint, aggro)) return false;
        previous = waypoint;
    }
    return true;
}
