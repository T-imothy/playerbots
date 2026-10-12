#include "playerbot/playerbot.h"
#include "MoltenCoreGarrActions.h"
#include "playerbot/strategy/values/GarrControlValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/strategy/CasterCombatPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;
namespace
{
    struct GarrEncounter
    {
        Unit* boss = nullptr;
        GarrControl control;
        std::vector<Unit*> adds;
        std::vector<Player*> tanks;
        Unit* focus = nullptr;
    };
    bool Banish(Unit* unit) { return unit->HasAura(710) || unit->HasAura(18647); }
    bool Member(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            !member->IsBeingTeleported() && !member->HasCharmer() && member->GetGroup() == bot->GetGroup();
    }
    GarrEncounter Encounter(PlayerbotAI* ai)
    {
        GarrEncounter result;
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 409 ||
            !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer()) return result;
        auto* state = ai->GetAiObjectContext()->GetValue<GarrControl>("garr control");
        result.control = state->Get();
        Unit* boss = ai->GetUnit(result.control.boss);
        if (!boss || !boss->IsInWorld() || !bot->IsInMap(boss) || boss->GetEntry() != 12057 ||
            boss->HasCharmer() || (boss->IsAlive() && !boss->IsInCombat()))
        {
            result.control = GarrControl(); boss = nullptr;
            for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
            {
                Unit* unit = ai->GetUnit(guid);
                if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->GetEntry() == 12057 &&
                    unit->IsAlive() && unit->IsInCombat() && !unit->HasCharmer()) { boss = unit; break; }
            }
            if (boss) { result.control.boss = boss->GetObjectGuid(); result.control.laneAngle = boss->GetOrientation() + float(M_PI)*0.5f; }
        }
        if (!boss) { state->Set(result.control); return result; }
        result.boss = boss;
        std::list<Unit*> nearby;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, 12099, 100.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby, check);
        Cell::VisitAllObjects(boss, searcher, 100.0f);
        std::vector<uint32_t> adds, locks;
        std::map<uint32_t, uint32_t> native;
        for (Unit* add : nearby)
        {
            if (!add->IsInWorld() || !add->IsAlive() || !bot->IsInMap(add) || !add->IsInCombat() ||
                add->HasCharmer() || sServerFacade.IsFriendlyTo(bot, add)) continue;
            result.adds.push_back(add); adds.push_back(add->GetGUIDLow());
            for (uint32 spell : {710u, 18647u})
                if (SpellAuraHolder* holder = add->GetSpellAuraHolder(spell)) native[add->GetGUIDLow()] = holder->GetCasterGuid().GetCounter();
        }
        std::sort(result.adds.begin(), result.adds.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        std::sort(adds.begin(), adds.end());
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!Member(bot, member) || member->GetDistance(boss) > 100) continue;
            if (ai->IsTank(member)) result.tanks.push_back(member);
            PlayerbotAI* other = member->GetPlayerbotAI();
            if (member->getClass() == CLASS_WARLOCK && other && !other->IsRealPlayer() && other->HasSpell("banish")) locks.push_back(member->GetGUIDLow());
        }
        std::sort(locks.begin(), locks.end());
        std::sort(result.tanks.begin(), result.tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        auto* owner = ai->GetAiObjectContext()->GetValue<int32>("manual int", "garr main " + std::to_string(boss->GetInstanceId()) + " " + std::to_string(boss->GetGUIDLow()));
        auto main = std::find_if(result.tanks.begin(), result.tanks.end(), [&](Player* tank) { return tank->GetGUIDLow() == uint32(owner->Get()); });
        if (main == result.tanks.end())
        {
            main = std::find(result.tanks.begin(), result.tanks.end(), boss->GetVictim());
            if (main == result.tanks.end() && !result.tanks.empty()) main = result.tanks.begin();
            if (main != result.tanks.end()) owner->Set(int32((*main)->GetGUIDLow()));
        }
        if (main != result.tanks.end()) std::rotate(result.tanks.begin(), main, main + 1);
        result.control.allocation.Reconcile(locks, adds, native, boss->IsAlive());
        for (Unit* add : result.adds) if (add->GetGUIDLow() == result.control.allocation.focus) result.focus = add;
        state->Set(result.control);
        return result;
    }
    bool Reserved(const GarrEncounter& encounter, Unit* add)
    {
        if (Banish(add)) return true;
        if (encounter.boss->IsAlive() || add->GetGUIDLow() != encounter.control.allocation.focus)
            for (const auto& [owner, target] : encounter.control.allocation.banishes)
                if (add->GetGUIDLow() == target) return true;
        return false;
    }
    Unit* TankTarget(PlayerbotAI* ai, const GarrEncounter& encounter)
    {
        auto own = std::find(encounter.tanks.begin(), encounter.tanks.end(), ai->GetBot());
        if (own == encounter.tanks.end()) return nullptr;
        size_t slot = std::distance(encounter.tanks.begin(), own);
        if (encounter.boss->IsAlive() && slot == 0) return encounter.boss;
        const size_t killSlot = encounter.boss->IsAlive() ? 1 : 0;
        if (slot == killSlot || encounter.tanks.size() <= killSlot + 1) return encounter.focus;
        std::vector<Unit*> parking;
        for (Unit* add : encounter.adds) if (add != encounter.focus && !Reserved(encounter, add)) parking.push_back(add);
        Unit* held = nullptr;
        for (size_t i = slot - killSlot - 1; i < parking.size(); i += encounter.tanks.size() - killSlot - 1)
        {
            Unit* victim = parking[i]->GetVictim();
            if (victim != ai->GetBot()) return parking[i];
            held = parking[i];
        }
        return held;
    }
    bool Isolated(const GarrEncounter& encounter)
    {
        if (!encounter.focus) return true;
        const float clearance = std::max(15.0f, NativeEncounterSpellRadius(19497)) + 2;
        for (Unit* add : encounter.adds)
            if (add != encounter.focus && !Banish(add) && add->GetDistance(encounter.focus) < clearance) return false;
        return true;
    }
}

Unit* ai::GarrBanishTarget(PlayerbotAI* ai)
{
    auto encounter = Encounter(ai);
    if (!encounter.boss) return nullptr;
    auto own = encounter.control.allocation.banishes.find(ai->GetBot()->GetGUIDLow());
    if (own == encounter.control.allocation.banishes.end()) return nullptr;
    for (Unit* add : encounter.adds)
        if (add->GetGUIDLow() == own->second && !Banish(add) &&
            (encounter.boss->IsAlive() || own->second != encounter.control.allocation.focus)) return add;
    return nullptr; // Recasting on an active native banish can cancel it.
}

Unit* ai::GarrFocusTarget(PlayerbotAI* ai)
{
    auto encounter = Encounter(ai);
    if (!encounter.boss) return nullptr;
    if (encounter.focus)
        return !Banish(encounter.focus) && !PossibleAttackTargetsValue::HasBreakableCC(encounter.focus, ai->GetBot()) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(encounter.focus, ai->GetBot()) ? encounter.focus : nullptr;
    return encounter.boss->IsAlive() ? encounter.boss : nullptr;
}

Unit* ai::GarrTankTarget(PlayerbotAI* ai)
{
    auto encounter = Encounter(ai);
    return encounter.boss ? TankTarget(ai, encounter) : nullptr;
}

bool ai::GarrTankHandoff(PlayerbotAI* ai, Unit* target)
{
    auto encounter = Encounter(ai);
    if (!encounter.boss || !target || target == encounter.focus || target->GetEntry() != 12099 ||
        target != TankTarget(ai, encounter)) return false;
    const size_t killSlot = encounter.boss->IsAlive() ? 1 : 0;
    return encounter.tanks.size() > killSlot && target->GetVictim() == encounter.tanks[killSlot];
}

bool ai::PlanGarrPosition(PlayerbotAI* ai, EncounterPosition& plan)
{
    auto encounter = Encounter(ai);
    if (!encounter.boss || encounter.adds.empty()) return false;
    Player* bot = ai->GetBot();
    Unit* target = ai->IsTank(bot) ? TankTarget(ai, encounter) : encounter.focus;
    if (ai->IsTank(bot) && (!target || target == encounter.boss || target->GetVictim() != bot)) return false;
    const float angle = encounter.control.laneAngle;
    float x, y, z = encounter.boss->GetPositionZ();
    if (ai->IsTank(bot))
    {
        const float direction = target == encounter.focus ? angle : angle + float(M_PI);
        // Both stations remain well inside native 100-yard Separation Anxiety.
        x = encounter.boss->GetPositionX() + std::cos(direction)*24;
        y = encounter.boss->GetPositionY() + std::sin(direction)*24;
        if (std::hypot(bot->GetPositionX()-x, bot->GetPositionY()-y) <= 3) return false;
    }
    else
    {
        // A banisher must retain legal range to its own add even while the DPS
        // kill station moves away. Stand on the parking side of that add, away
        // from the kill station, rather than following the ranged DPS cluster.
        auto own = encounter.control.allocation.banishes.find(bot->GetGUIDLow());
        if (own != encounter.control.allocation.banishes.end() &&
            (encounter.boss->IsAlive() || own->second != encounter.control.allocation.focus))
        {
            for (Unit* add : encounter.adds) if (add->GetGUIDLow() == own->second) target = add;
            float range = 0;
            if (!target || !ai->GetSpellRange("banish", &range) || range <= 5) return false;
            const float distance = std::min(20.0f, range - 3);
            x = target->GetPositionX() - std::cos(angle)*distance;
            y = target->GetPositionY() - std::sin(angle)*distance;
            z = target->GetPositionZ();
            plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
            plan.boss = encounter.boss->GetObjectGuid(); plan.spell = 19771;
            plan.destination = {x,y,z};
            if (ValidateEncounterDestination(ai, plan)) return true;
            plan.active = false; return false;
        }
        if (!target) target = encounter.boss;
        const bool retreat = !ai->IsRanged(bot) && !ai->IsHeal(bot) && target->GetEntry() == 12099 &&
            (target->GetHealthPercent() <= 25 || !Isolated(encounter));
        if (!retreat && !ai->IsRanged(bot) && !ai->IsHeal(bot)) return false;
        // Ranged finish a separated low-health add; melee never chase through
        // its death eruption. Healing admission and native hazard paths remain.
        const float distance = retreat ? std::max(15.0f, NativeEncounterSpellRadius(19497)) + 3 : 28;
        x = target->GetPositionX() + std::cos(angle)*distance;
        y = target->GetPositionY() + std::sin(angle)*distance;
        z = target->GetPositionZ();
        if (bot->GetDistance(target) >= distance - 2 && bot->GetDistance(target) <= distance + 6 &&
            std::cos(target->GetAngle(bot) - angle) > 0.5f)
        { x = bot->GetPositionX(); y = bot->GetPositionY(); z = bot->GetPositionZ(); }
    }
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = encounter.boss->GetObjectGuid(); plan.spell = 19771;
    plan.destination = {x,y,z};
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false; return false;
}

bool ai::GarrSpellAllowed(PlayerbotAI* ai, const std::string& name, Unit* target, const SpellEntry* spell)
{
    if (ai->GetBot()->GetMapId() != 409) return true;
    auto encounter = Encounter(ai);
    if (name == "banish" || name == "banish on cc")
        return encounter.boss && target && target->GetEntry() == 12099 && target == GarrBanishTarget(ai);
    if (!encounter.boss || encounter.adds.empty()) return true;
    bool damage = CasterDamageSpell(spell);
    if (spell) for (uint32 effect : spell->Effect)
        damage = damage || effect == SPELL_EFFECT_WEAPON_DAMAGE || effect == SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL ||
            effect == SPELL_EFFECT_NORMALIZED_WEAPON_DMG || effect == SPELL_EFFECT_WEAPON_PERCENT_DAMAGE;
    const bool area = CasterSpellArea(name) != CasterArea::None || name == "cleave" || name == "whirlwind" ||
        name == "thunder clap" || name == "consecration" || name == "swipe" || name == "blade flurry" ||
        name == "multi-shot" || name == "divine storm" || name == "hammer of the righteous" || name == "fire nova" ||
        name == "fire nova totem" || name == "magma totem" || name == "explosive trap" || name == "immolation trap";
    if (area) return false; // Includes next-swing/pet/ground damage supplements.
    if (!damage || !target || sServerFacade.IsFriendlyTo(ai->GetBot(), target)) return true;
    if (target->GetEntry() == 12099 && (Reserved(encounter, target) ||
        PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot()) ||
        PossibleAttackTargetsValue::HasUnBreakableCC(target, ai->GetBot()))) return false;
    if (ai->IsTank(ai->GetBot())) return true;
    if (encounter.focus && target != encounter.focus) return false;
    if (encounter.focus && !Isolated(encounter) && encounter.focus->GetHealthPercent() <= 30) return false;
    if (target->GetEntry() == 12099 && !ai->IsRanged(ai->GetBot()) && target->GetHealthPercent() <= 25) return false;
    return true;
}
