
#include "playerbot/playerbot.h"
#include "MoltenCoreDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/ServerFacade.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::MoltenCoreImpPack(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer() || ai->IsHeal(bot)) return false;
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    if (!target || !target->IsInWorld() || !bot->IsInMap(target) || !target->IsAlive() ||
        !target->IsInCombat() || target->GetEntry() != 11669) return false;
    unsigned imps = 0;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !bot->IsInMap(enemy) || !enemy->IsAlive() ||
            sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        if (enemy->GetDistance(target) > 15 && enemy->GetDistance(bot) > 15) continue;
        if (!enemy->IsInCombat() || enemy->HasCharmer() ||
            PossibleAttackTargetsValue::HasBreakableCC(enemy, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot)) return false;
        if (enemy->GetEntry() == 11669 && enemy->GetDistance(target) <= 8)
        {
            Unit* victim = enemy->GetVictim();
            if (!victim || !victim->IsPlayer() || !ai->IsTank(static_cast<Player*>(victim)) ||
                static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) return false;
            ++imps;
        }
    }
    return imps >= 3 && ai->GetCombatStartTime() && time(0) - ai->GetCombatStartTime() >= 2;
}

bool ai::PlanMoltenCoreTrash(PlayerbotAI* ai, EncounterPosition& plan)
{
    plan = EncounterPosition();
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    Unit* selected = nullptr;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() ||
            !unit->IsInCombat() || unit->HasCharmer() || sServerFacade.IsFriendlyTo(bot, unit) ||
            (unit->GetEntry() != 12101 && unit->GetEntry() != 11673)) continue;
        Unit* victim = unit->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsAlive() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        // Keep the current victim's tank assignment. Choose one stable nearby
        // source; do not alternate between multiple trash mobs every tick.
        if (!selected || (unit->GetVictim() == bot && selected->GetVictim() != bot) ||
            (unit->GetVictim() != bot && selected->GetVictim() != bot &&
             unit->GetObjectGuid() < selected->GetObjectGuid())) selected = unit;
    }
    if (!selected) return false;
    Unit* victim = selected->GetVictim();
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = selected->GetObjectGuid();
    if (selected->GetEntry() == 12101)
    {
        // Hold the established tank in place; everyone else joins its position.
        // This cannot prevent charges at human players who remain spread out.
        if (victim == bot) { plan.active = false; return false; }
        plan.spell = 19196;
        plan.destination = {victim->GetPositionX(), victim->GetPositionY(), victim->GetPositionZ()};
        if (bot->GetDistance(victim) <= 3)
            plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    }
    else
    {
        plan.spell = 19272;
        float angle = selected->GetOrientation() + float(M_PI);
        float distance = std::max(2.0f, selected->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        if (victim == bot)
        {
            // The hound faces its victim. Move the tank to the opposite side
            // of the raid, rather than merely turning the player's model.
            float x = 0, y = 0; unsigned count = 0;
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = ref->getSource();
                if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
                    !bot->IsInMap(member) || member->IsBeingTeleported() || ai->IsTank(member) ||
                    member->GetDistance(selected) > 40) continue;
                x += member->GetPositionX(); y += member->GetPositionY(); ++count;
            }
            if (!count) { plan.active = false; return false; }
            x = x / count - selected->GetPositionX(); y = y / count - selected->GetPositionY();
            if (x*x + y*y < 4) { plan.active = false; return false; }
            angle = std::atan2(y, x) + float(M_PI);
            // A wide safe rear sector avoids rotating for tiny centroid shifts.
            if (std::cos(selected->GetAngle(bot) - angle) > 0.86f)
                plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            else plan.destination = {selected->GetPositionX() + std::cos(angle)*distance,
                selected->GetPositionY() + std::sin(angle)*distance, selected->GetPositionZ()};
        }
        else
        {
            if (ai->IsTank(bot)) { plan.active = false; return false; }
            if (ai->IsRanged(bot) || ai->IsHeal(bot)) distance = std::min(25.0f, std::max(distance, bot->GetDistance(selected)));
            if (std::cos(selected->GetAngle(bot) - selected->GetOrientation()) < -0.25f)
                plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            else plan.destination = {selected->GetPositionX() + std::cos(angle)*distance,
                selected->GetPositionY() + std::sin(angle)*distance, selected->GetPositionZ()};
        }
    }
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false;
    return false;
}

namespace
{
    bool RaidMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
            !member->HasCharmer() && bot->IsInMap(member) && member->GetGroup() == bot->GetGroup();
    }

    bool RaidEnemy(Player* bot, Unit* unit)
    {
        return unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() &&
            !unit->HasCharmer() && bot->IsInMap(unit) && !sServerFacade.IsFriendlyTo(bot, unit);
    }

    bool MoltenCoreBoss(uint32 entry)
    {
        switch (entry)
        {
            case 12118: case 11982: case 12259: case 12057: case 12056:
            case 12264: case 12098: case 11988: case 12018: case 11502: return true;
            default: return false;
        }
    }

    Unit* RaidBoss(PlayerbotAI* ai)
    {
        Unit* result = nullptr;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!RaidEnemy(ai->GetBot(), unit) || !MoltenCoreBoss(unit->GetEntry())) continue;
            if (result && result != unit) return nullptr; // Do not invent assignments on multi-boss pulls.
            result = unit;
        }
        return result;
    }

    uint32 RaidAdd(uint32 boss)
    {
        switch (boss)
        {
            case 12118: return 12119;
            case 12259: return 11661;
            case 12057: return 12099;
            case 12098: return 11662;
            case 11988: return 11672;
            case 12018: return 11664;
            case 11502: return 12143;
            default: return 0;
        }
    }

    std::vector<Unit*> RaidAdds(PlayerbotAI* ai, Unit* boss, uint32 entry)
    {
        std::vector<Unit*> result;
        if (!boss || !entry) return result;
        std::list<Unit*> nearby;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, entry, 100.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby, check);
        Cell::VisitAllObjects(boss, searcher, 100.0f);
        for (Unit* unit : nearby)
            if (RaidEnemy(ai->GetBot(), unit)) result.push_back(unit);
        std::sort(result.begin(), result.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return result;
    }

    unsigned MoltenCoreTargetPriority(uint32 boss, uint32 target)
    {
        // These entries and native mechanics match all three CMaNGOS scripts.
        switch (boss)
        {
            case 12118: return target == 12119 ? 1 : 0; // Lucifron's protectors
            case 12259: return target == 11661 ? 1 : 0; // Gehennas's flamewakers
            case 12057: return target == 12099 ? 1 : 0; // Uncontrolled Firesworn; banishes are filtered below.
            case 12098: return target == 11662 ? 1 : 0; // Sulfuron's healing priests
            case 12018: // Majordomo ends on add deaths; the boss has death prevention.
                return target == 11663 ? 2 : (target == 11664 ? 1 : 0);
            case 11988: return target == 11988 ? 1 : 0; // Core Ragers cannot die while Golemagg lives.
            case 11502: return target == 12143 ? 1 : 0; // Ragnaros's native Sons of Flame.
            default: return 0;
        }
    }
}

Unit* MoltenCorePriorityTargetAction::GetTarget()
{
    if (Unit* assigned = MoltenCoreAssignedTankTarget(ai)) return assigned;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;

    Unit* boss = nullptr;
    bool ragSons = false;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() || !unit->IsInCombat()) continue;
        const uint32 entry = unit->GetEntry();
        if (entry == 12143) ragSons = true;
        if (entry != 12118 && entry != 12259 && entry != 12057 && entry != 12098 && entry != 12018 && entry != 11988 && entry != 11502) continue;
        // Ambiguous multi-boss pulls should retain ordinary player/assist policy.
        if (boss && boss != unit) return nullptr;
        boss = unit;
    }
    if (boss && (boss->GetVictim() == bot || (ragSons && boss->GetEntry() != 11502))) return nullptr;
    // Submerged Ragnaros is correctly absent from attackable-target values.
    // His live, engaged sons identify the add wave without bypassing the
    // native submerged flag, guessing a phase timer or scanning the world.
    const uint32 bossEntry = boss ? boss->GetEntry() : (ragSons ? 11502 : 0);

    auto valid = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && unit->IsInCombat() &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    // Manual attack commands and configured raid marks remain authoritative.
    Unit* commanded = ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"));
    if (valid(commanded)) return nullptr;
    Unit* marked = ai->GetUnit(AI_VALUE(ObjectGuid, "rti target"));
    if (valid(marked) && (bossEntry || marked->GetEntry() != 11671)) return nullptr;

    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    if (!bossEntry)
    {
        // Balance the engaged small Core Hounds, not Ancient Core Hounds or
        // Golemagg's Core Ragers. Raid marks on this pack are advisory; direct
        // attack commands above remain an explicit human override.
        std::vector<Unit*> hounds;
        Unit* anchor = valid(current) && current->GetEntry() == 11671 ? current : nullptr;
        for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
        {
            Unit* unit = ai->GetUnit(guid);
            if (!valid(unit) || unit->GetEntry() != 11671) continue;
            hounds.push_back(unit);
        }
        if (hounds.empty()) return nullptr;
        if (!anchor) anchor = *std::min_element(hounds.begin(), hounds.end(), [this](Unit* a, Unit* b) {
            return bot->GetDistance(a) < bot->GetDistance(b);
        });
        float highest = 0;
        for (Unit* hound : hounds)
            if (hound->GetDistance(anchor) <= 30) highest = std::max(highest, hound->GetHealthPercent());
        // Five percentage points of tolerance avoids switching on every hit.
        // Keep damage distributed amongst the highest-health band instead of
        // sending the entire raid onto the same nearly-dead marked hound.
        std::vector<Unit*> band;
        for (Unit* hound : hounds)
            if (hound->GetDistance(anchor) <= 30 && hound->GetHealthPercent() + 5.0f >= highest) band.push_back(hound);
        if (band.empty()) return nullptr;
        if (std::find(band.begin(), band.end(), current) != band.end()) return current;
        std::sort(band.begin(), band.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return band[bot->GetGUIDLow() % band.size()];
    }
    Unit* selected = nullptr;
    unsigned priority = 0;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit) continue;
        const unsigned candidatePriority = MoltenCoreTargetPriority(bossEntry, unit->GetEntry());
        if (!candidatePriority || !valid(unit)) continue;
        if (!selected || candidatePriority > priority || (candidatePriority == priority &&
            (unit == current || (selected != current && bot->GetDistance(unit) < bot->GetDistance(selected)))))
        {
            selected = unit;
            priority = candidatePriority;
        }
    }
    return selected;
}

bool MoltenCorePriorityTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
}

bool MoltenCorePositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    if (plan.spell == 20475 && !plan.source.IsEmpty())
    {
        Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
        if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !bot->IsInMap(carrier) ||
            !carrier->IsAlive() || !carrier->HasAura(20475) || carrier->HasCharmer()) return false;
        Player* member = static_cast<Player*>(carrier);
        return !member->IsBeingTeleported() && member->GetGroup() && member->GetGroup() == bot->GetGroup();
    }
    Unit* boss = ai->GetUnit(plan.boss);
    return boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && boss->IsInCombat();
}

bool MoltenCorePositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f ||
        !bot->IsStopped() || bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool MoltenCorePositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool MoltenCorePositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove()) return false;
    if (plan.spell == 19196 || plan.spell == 19272)
    {
        if (MoltenCoreThreats(ai, current, threats) || !PlanMoltenCoreTrash(ai, current)) return false;
        plan = current;
    }
    else if (!MoltenCoreThreats(ai, current, threats)) return false;
    if (
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

Unit* ai::MoltenCoreAssignedTankTarget(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || !ai->IsTank(bot) || ai->IsRealPlayer()) return nullptr;
    // Direct commands remain available for a human-led alternative tactic.
    if (RaidEnemy(bot, ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("attack target")->Get()))) return nullptr;
    Unit* boss = RaidBoss(ai);
    if (!boss) return nullptr;
    std::vector<Player*> tanks;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (RaidMember(bot, member) && ai->IsTank(member) && member->GetDistance(boss) <= 100) tanks.push_back(member);
    }
    std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    // Preserve the established main tank (including a human), rather than
    // changing ownership every time an off-tank acquires an add.
    auto main = std::find(tanks.begin(), tanks.end(), boss->GetVictim());
    if (main != tanks.end()) std::rotate(tanks.begin(), main, main + 1);
    auto own = std::find(tanks.begin(), tanks.end(), bot);
    if (own == tanks.end()) return nullptr;
    const size_t slot = std::distance(tanks.begin(), own);
    auto valid = [bot](Unit* unit) {
        return RaidEnemy(bot, unit) &&
            PossibleAttackTargetsValue::IsValid(unit, bot, 100.0f, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    if (slot == 0) return valid(boss) ? boss : nullptr;
    std::vector<Unit*> adds = RaidAdds(ai, boss, RaidAdd(boss->GetEntry()));
    if (boss->GetEntry() == 12018)
    {
        auto healers = RaidAdds(ai, boss, 11663);
        adds.insert(adds.end(), healers.begin(), healers.end());
    }
    // Keep CC targets in the allocation so banish/sheep does not reshuffle
    // every other tank. A tank's assigned CC target is never attacked.
    const size_t offTanks = tanks.size() - 1;
    Unit* selected = nullptr;
    for (size_t i = slot - 1; i < adds.size(); i += offTanks)
    {
        Unit* add = adds[i];
        if (!valid(add)) continue;
        if (!selected || (selected->GetVictim() == bot && add->GetVictim() != bot)) selected = add;
    }
    return selected; // No add assignment means ordinary tank behavior can resume.
}

bool MoltenCoreSupportAction::Select(std::string& spell, Unit*& target)
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    Unit* boss = RaidBoss(ai);
    if (!boss) return false;
    const auto ready = [&](const char* name, Unit* unit) {
        if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
        spell = name; target = unit; return true;
    };
    // Dominate Mind makes the raid member hostile: ordinary friendly-party
    // dispel selection deliberately excludes that player. Offensive Dispel
    // Magic can remove the verified aura; native eligibility still decides.
    if (boss->GetEntry() == 12118)
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
                !member->IsBeingTeleported() && member->GetGroup() == bot->GetGroup() &&
                member->HasAura(20604) && ready("dispel magic", member)) return true;
        }
    // Magmadar's actual Frenzy aura; do not shoot merely because the boss exists.
    if (boss->GetEntry() == 11982 && boss->HasAura(19451) && ready("tranquilizing shot", boss)) return true;
    // Counter an active priest heal, including a priest other than our DPS target.
    if (boss->GetEntry() == 12098)
        for (Unit* priest : RaidAdds(ai, boss, 11662))
        {
            Spell* cast = priest->GetCurrentSpell(CURRENT_GENERIC_SPELL);
            if (!cast || !cast->m_spellInfo || cast->getState() != SPELL_STATE_CASTING || cast->m_spellInfo->Id != 19775 ||
                !cast->CanBeInterrupted()) continue;
            for (const char* name : {"pummel", "shield bash", "kick", "counterspell", "silence",
#ifdef MANGOSBOT_TWO
                "wind shear", "mind freeze"
#else
                "earth shock"
#endif
            })
                if (ready(name, priest)) return true;
        }
    // Dispel priority is tied to actual live auras, not guesses about boss timers.
    // No blanket dispels of beneficial/other encounter effects.
    for (uint32 aura : {19702u, 19716u, 19659u, 19703u, 19713u})
    {
        std::vector<Player*> afflicted;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (RaidMember(bot, member) && member->HasAura(aura)) afflicted.push_back(member);
        }
        std::sort(afflicted.begin(), afflicted.end(), [this](Player* a, Player* b) {
            if (ai->IsTank(a) != ai->IsTank(b)) return ai->IsTank(a);
            if (a->GetHealthPercent() != b->GetHealthPercent()) return a->GetHealthPercent() < b->GetHealthPercent();
            return a->GetObjectGuid() < b->GetObjectGuid();
        });
        for (Player* member : afflicted)
        {
            if (aura == 19702 || aura == 19659)
            {
                for (const char* name : {"dispel magic", "cleanse"}) if (ready(name, member)) return true;
            }
            else
                for (const char* name : {"remove lesser curse", "remove curse", "cleanse spirit"}) if (ready(name, member)) return true;
        }
    }
    if (boss->GetEntry() == 12264 && boss->HasAura(19714))
        for (const char* name : {"purge", "dispel magic", "spellsteal"}) if (ready(name, boss)) return true;
    // Pre-emptive protection for the current Magmadar tank when actually learned.
    if (boss->GetEntry() == 11982 && boss->GetVictim() && boss->GetVictim()->IsPlayer())
    {
        Player* tank = static_cast<Player*>(boss->GetVictim());
        if (RaidMember(bot, tank) && !ai->HasAura("fear ward", tank) && ready("fear ward", tank)) return true;
    }
    if (boss->GetEntry() == 12018 && bot->getClass() == CLASS_MAGE)
    {
        std::vector<Player*> mages;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (RaidMember(bot, member) && member->getClass() == CLASS_MAGE && member->GetDistance(boss) <= 100 &&
                member->GetPlayerbotAI() && !member->GetPlayerbotAI()->IsRealPlayer() &&
                member->GetPlayerbotAI()->HasSpell("polymorph")) mages.push_back(member);
        }
        std::sort(mages.begin(), mages.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        auto own = std::find(mages.begin(), mages.end(), bot);
        auto healers = RaidAdds(ai, boss, 11663);
        const ObjectGuid skull = bot->GetGroup()->GetTargetIcon(7);
        const bool markedHealer = std::any_of(healers.begin(), healers.end(), [skull](Unit* unit) {
            return unit->GetObjectGuid() == skull;
        });
        healers.erase(std::remove_if(healers.begin(), healers.end(), [skull](Unit* unit) {
            return unit->GetObjectGuid() == skull;
        }), healers.end());
        // Keep one unmarked healer available to kill. Stable boss-centred lists
        // retain sheeped units, so successful CC does not shuffle assignments.
        if (own != mages.end())
        {
            const size_t slot = std::distance(mages.begin(), own) + (markedHealer ? 0 : 1);
            if (slot < healers.size())
            {
                Unit* healer = healers[slot];
                if (!healer->HasAura(21087) && !PossibleAttackTargetsValue::HasBreakableCC(healer, bot) &&
                    !PossibleAttackTargetsValue::HasUnBreakableCC(healer, bot) && ready("polymorph", healer)) return true;
            }
        }
    }
    return false;
}

bool MoltenCoreSupportAction::isUseful()
{
    std::string spell; Unit* target = nullptr;
    return Select(spell, target);
}

bool MoltenCoreSupportAction::Execute(Event& event)
{
    std::string spell; Unit* target = nullptr;
    if (!Select(spell, target)) return false; // Recheck on execution; never retain raw unit pointers.
    uint32 duration = sPlayerbotAIConfig.globalCoolDown;
    if (!ai->CastSpell(spell, target, nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}
