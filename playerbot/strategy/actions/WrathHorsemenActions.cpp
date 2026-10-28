#include "playerbot/playerbot.h"
#include "WrathHorsemenActions.h"
#include "ClassicRaidActions.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#ifdef MANGOSBOT_TWO
#include "Spells/SpellTargets.h"
#endif

using namespace ai;

#ifdef MANGOSBOT_TWO
namespace
{
    bool FrontHorseman(Unit* boss) { return boss && (boss->GetEntry() == 16064 || boss->GetEntry() == 30549); }
    bool RearHorseman(Unit* boss) { return boss && (boss->GetEntry() == 16065 || boss->GetEntry() == 16063); }
    bool HorsemanMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && !member->HasCharmer() &&
            !member->IsBeingTeleported() && bot->IsInMap(member) && member->GetGroup() == bot->GetGroup();
    }
    bool Automated(Player* member)
    {
        return member->GetPlayerbotAI() && !member->GetPlayerbotAI()->IsRealPlayer();
    }
    unsigned HorsemanStacks(Player* member, Unit* boss)
    {
        const SpellAuraHolder* aura = member->GetSpellAuraHolder(classicraid::HorsemanMark(boss->GetEntry()));
        return aura ? aura->GetStackAmount() : 0;
    }
    encounter::Point HorsemanPoint(Unit* unit)
    {
        return {unit->GetPositionX(), unit->GetPositionY(), unit->GetPositionZ()};
    }
    encounter::Point WrathCorner(Unit* boss)
    {
        // Native boss_four_horsemen.cpp aHorseMenMoveCoords. Front bosses can
        // subsequently follow their real tanks; the two rear casters stay here.
        switch (boss->GetEntry())
        {
            case 16065: return {2469.4f, -2947.6f, 241.28f};
            case 30549: return {2583.9f, -2971.67f, 241.35f};
            case 16064: return {2542.9f, -3015.0f, 241.35f};
            default: return {2517.8f, -2896.6f, 241.28f};
        }
    }
    std::vector<Player*> HorsemanMembers(PlayerbotAI* ai)
    {
        std::vector<Player*> result;
        Player* bot = ai->GetBot();
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            if (HorsemanMember(bot, ref->getSource())) result.push_back(ref->getSource());
        std::sort(result.begin(), result.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return result;
    }
    Player* HorsemanVictim(Player* bot, Unit* boss)
    {
        Unit* victim = boss->GetVictim();
        return victim && victim->IsPlayer() && HorsemanMember(bot, static_cast<Player*>(victim)) ? static_cast<Player*>(victim) : nullptr;
    }
    unsigned HeldFronts(Player* tank, const std::vector<Unit*>& front)
    {
        return unsigned(std::count_if(front.begin(), front.end(), [tank](Unit* boss) { return boss->GetVictim() == tank; }));
    }
    Player* CleanRelief(PlayerbotAI* ai, Unit* boss, const std::vector<Unit*>& front, const std::vector<Player*>& members)
    {
        std::vector<Player*> reserved;
        for (Unit* source : front)
        {
            Player* victim = HorsemanVictim(ai->GetBot(), source);
            if (victim && ai->IsTank(victim) && HeldFronts(victim, front) == 1 && HorsemanStacks(victim, source) < 3) continue;
            Player* selected = nullptr;
            for (Player* member : members)
                if (Automated(member) && ai->IsTank(member) && member->GetDistance(source) <= 120 && !HeldFronts(member, front) && !HorsemanStacks(member, source) &&
                    std::find(reserved.begin(), reserved.end(), member) == reserved.end() &&
                    (!selected || member->GetDistance(source) < selected->GetDistance(source) ||
                        (member->GetDistance(source) == selected->GetDistance(source) && member->GetObjectGuid() < selected->GetObjectGuid()))) selected = member;
            if (source == boss) return selected;
            if (selected) reserved.push_back(selected);
        }
        return nullptr;
    }
    Unit* FrontAssignment(PlayerbotAI* ai, Player* tank, const std::vector<Unit*>& front, const std::vector<Player*>& members)
    {
        Unit* held = nullptr;
        for (Unit* boss : front)
            if (boss->GetVictim() == tank && (!held || HorsemanStacks(tank, boss) < HorsemanStacks(tank, held))) held = boss;
        // A failed/missed taunt leaves native ownership intact. A third clean
        // tank relieves the marked holder without moving the other front boss.
        if (held && HeldFronts(tank, front) > 1) return held;
        if (held)
        {
            for (Unit* other : front)
            {
                Player* otherTank = HorsemanVictim(ai->GetBot(), other);
                if (other == held || !otherTank || !ai->IsTank(otherTank) || !Automated(otherTank) ||
                    HorsemanStacks(tank, other) || HorsemanStacks(otherTank, held)) continue;
                if ((HorsemanStacks(tank, held) >= 3 || HorsemanStacks(otherTank, other) >= 3) &&
                    !CleanRelief(ai, held, front, members) && !CleanRelief(ai, other, front, members)) return other;
            }
            return held;
        }
        for (Unit* boss : front)
        {
            Player* victim = HorsemanVictim(ai->GetBot(), boss);
            const bool needsRelief = !victim || !ai->IsTank(victim) || HeldFronts(victim, front) > 1 || HorsemanStacks(victim, boss) >= 3;
            if (needsRelief && CleanRelief(ai, boss, front, members) == tank) return boss;
        }
        return nullptr;
    }
    float RearRange(PlayerbotAI* ai, Unit* boss)
    {
        const bool regular = ai->GetBot()->GetMap()->IsRegularDifficulty();
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(boss->GetEntry() == 16065 ?
            (regular ? 57374 : 57464) : (regular ? 57376 : 57465));
        const SpellRangeEntry* range = spell ? sSpellRangeStore.LookupEntry(spell->rangeIndex) : nullptr;
        return range ? GetSpellMaxRange(range) : 0.0f;
    }
    bool RearEligible(PlayerbotAI* ai, Player* member, Unit* boss, bool frontAlive)
    {
        if (member->GetDistance(boss) > 120 || (ai->IsTank(member) && frontAlive) ||
            (!ai->IsTank(member) && !ai->IsHeal(member) && !ai->IsRanged(member))) return false;
        // Never count a human as a commanded volunteer. An actual human holder
        // already in native bolt range remains a valid occupant.
        return Automated(member) || (boss->GetVictim() == member && member->GetDistance(boss) < RearRange(ai, boss));
    }
    std::vector<Player*> RearAssignments(PlayerbotAI* ai, const std::vector<Unit*>& rear, const std::vector<Player*>& members, bool frontAlive)
    {
        std::vector<Player*> result(rear.size(), nullptr);
        if (rear.empty()) return result;
        unsigned eligible = 0;
        for (Player* member : members)
            if (std::any_of(rear.begin(), rear.end(), [&](Unit* boss) { return RearEligible(ai, member, boss, frontAlive); })) ++eligible;
        const bool understaffed = eligible < rear.size();
        auto cost = [ai, frontAlive, understaffed](Player* member, Unit* boss)
        {
            if (!member) return 1.0e8f; // Keep a distinct remaining holder when understaffed.
            if (!RearEligible(ai, member, boss, frontAlive)) return 1.0e9f;
            const unsigned stacks = HorsemanStacks(member, boss);
            return member->GetDistance(boss) + (stacks >= 3 ? 100000.0f + stacks * 1000.0f : 0.0f) +
                (boss->GetVictim() == member ? (understaffed ? -10000000.0f : stacks < 3 ? -1000.0f : 0.0f) : 0.0f) + (ai->IsHeal(member) ? 10.0f : 0.0f) -
                (!frontAlive && ai->IsTank(member) ? 2000.0f : 0.0f);
        };
        float best = 1.0e10f;
        std::vector<Player*> candidates = members;
        candidates.push_back(nullptr);
        for (Player* first : candidates)
            for (Player* second : candidates)
            {
                if (rear.size() == 1 && second) continue;
                if (first && first == second) continue;
                const float score = cost(first, rear[0]) + (rear.size() == 2 ? cost(second, rear[1]) : 0.0f);
                if (score < best) { best = score; result[0] = first; if (rear.size() == 2) result[1] = second; }
            }
        return result;
    }
    bool HorsemanPosition(PlayerbotAI* ai, Unit* boss, encounter::Point destination, ClassicRaidPlan& plan)
    {
        Player* bot = ai->GetBot();
        const auto here = HorsemanPoint(bot);
        const float distance = encounter::Distance2d(here, destination);
        if (distance > 55)
        {
            destination.x = here.x + (destination.x - here.x) * 55 / distance;
            destination.y = here.y + (destination.y - here.y) * 55 / distance;
            destination.z = here.z;
        }
        EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
        p.boss = boss->GetObjectGuid(); p.spell = classicraid::HorsemanMark(boss->GetEntry()); p.destination = destination;
        if (!ValidateEncounterDestination(ai, p)) return false;
        plan.position = p;
        return true;
    }
    void HorsemanWait(PlayerbotAI* ai, Unit* boss, const std::vector<Unit*>& avoid, ClassicRaidPlan& plan)
    {
        plan.boss = boss->GetObjectGuid(); plan.holdDamage = true;
        std::vector<encounter::Circle> marks;
        for (Unit* source : avoid)
        {
            const float radius = NativeEncounterSpellRadius(classicraid::HorsemanMark(source->GetEntry()));
            if (radius > 0 && radius <= 60) marks.push_back({HorsemanPoint(source), radius + 2});
        }
        const auto here = HorsemanPoint(ai->GetBot());
        if (encounter::OutsideCircles(here, marks) && HorsemanPosition(ai, boss, here, plan)) return;
        unsigned checks = 0;
        for (auto point : encounter::EscapeCircles(here, marks))
        {
            if (++checks > 12) break;
            if (encounter::OutsideCircles(point, marks) && HorsemanPosition(ai, boss, point, plan))
            { plan.emergency = true; return; }
        }
        // No verified path: hold attacks and ordinary pursuit in place; the
        // independent emergency ground-hazard action may still evacuate it.
        plan.position.active = true; plan.position.map = 533; plan.position.instance = ai->GetBot()->GetInstanceId();
        plan.position.boss = plan.boss; plan.position.spell = classicraid::HorsemanMark(boss->GetEntry()); plan.position.destination = here;
    }
    bool ClearSpentMarks(Player* bot, Unit* assigned, const encounter::Point& point, const std::vector<Unit*>& live)
    {
        for (Unit* source : live)
        {
            if (source == assigned || HorsemanStacks(bot, source) < 3) continue;
            const float radius = NativeEncounterSpellRadius(classicraid::HorsemanMark(source->GetEntry()));
            if (radius <= 0 || radius > 60 || encounter::Distance2d(point, HorsemanPoint(source)) < radius + 2) return false;
        }
        return true;
    }
    bool HorsemanRing(PlayerbotAI* ai, Unit* boss, float radius, float spacing,
        const std::vector<Player*>& members, const std::vector<Unit*>& live, ClassicRaidPlan& plan)
    {
        Player* bot = ai->GetBot();
        const auto center = HorsemanPoint(boss);
        const float base = std::atan2(-2955.0f - center.y, 2525.0f - center.x);
        auto separated = [&](const encounter::Point& point)
        {
            if (!ClearSpentMarks(bot, boss, point, live)) return false;
            for (Player* member : members)
                if (member != bot && (!Automated(member) || member->GetObjectGuid() < bot->GetObjectGuid()) &&
                    encounter::Distance2d(point, HorsemanPoint(member)) < spacing) return false;
            return true;
        };
        const auto here = HorsemanPoint(bot);
        if (std::fabs(encounter::Distance2d(here, center) - radius) < 2 && separated(here) &&
            boss->IsWithinLOS(here.x, here.y, here.z + bot->GetCollisionHeight(), true) && HorsemanPosition(ai, boss, here, plan)) return true;
        for (unsigned i = 0; i < 24; ++i)
        {
            const float angle = base + i * 6.2831853f / 24;
            encounter::Point point{center.x + radius * std::cos(angle), center.y + radius * std::sin(angle), center.z};
            if (separated(point) && boss->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true) && HorsemanPosition(ai, boss, point, plan)) return true;
        }
        return false;
    }
}
#endif

bool ai::BuildWrathHorsemenPlan(PlayerbotAI* ai, const std::vector<Unit*>& horsemen,
    ObjectGuid& previousHorseman, ClassicRaidPlan& plan)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !bot->GetGroup() || bot->GetMapId() != 533 || ai->IsRealPlayer()) return false;
    std::vector<Unit*> front, rear, live;
    for (Unit* boss : horsemen)
        if ((FrontHorseman(boss) || RearHorseman(boss)) && NaxxramasEncounterEngaged(bot, boss) &&
            std::find(live.begin(), live.end(), boss) == live.end())
        { live.push_back(boss); (FrontHorseman(boss) ? front : rear).push_back(boss); }
    if (live.empty()) { previousHorseman.Clear(); return false; }
    if (front.size() > 2 || rear.size() > 2) return false;
    auto order = [](Unit* a, Unit* b) { return a->GetEntry() < b->GetEntry(); };
    std::sort(front.begin(), front.end(), order); std::sort(rear.begin(), rear.end(), order); std::sort(live.begin(), live.end(), order);
    const auto members = HorsemanMembers(ai);
    if (ai->IsTank(bot) && !front.empty())
    {
        Unit* assigned = FrontAssignment(ai, bot, front, members);
        if (!assigned) { HorsemanWait(ai, front.front(), front, plan); return true; }
        Unit* held = nullptr;
        for (Unit* boss : front) if (boss->GetVictim() == bot && boss != assigned) held = boss;
        plan.boss = (held ? held : assigned)->GetObjectGuid(); plan.target = assigned->GetObjectGuid();
        if (assigned->GetVictim() == bot)
        {
            previousHorseman = assigned->GetObjectGuid();
            if (HeldFronts(bot, front) > 1) HorsemanPosition(ai, assigned, HorsemanPoint(bot), plan);
            else HorsemanPosition(ai, assigned, WrathCorner(assigned), plan);
        }
        else if (held)
        {
            // Both real owners walk to a front-only bridge. Their bosses follow
            // natively; neither ownership nor threat is changed by this planner.
            const auto a = WrathCorner(held), b = WrathCorner(assigned);
            encounter::Point bridge{(a.x+b.x)/2, (a.y+b.y)/2, (a.z+b.z)/2};
            HorsemanPosition(ai, held, bridge, plan); plan.emergency = HorsemanStacks(bot, held) >= 3;
        }
        else HorsemanRing(ai, assigned, 3.0f, 0, members, live, plan);
        if (!plan.position.active) HorsemanWait(ai, held ? held : assigned, {}, plan);
        return true;
    }
    const auto holders = RearAssignments(ai, rear, members, !front.empty());
    Unit* assigned = nullptr;
    bool retiringHolder = false;
    for (unsigned i = 0; i < rear.size(); ++i) if (holders[i] == bot) assigned = rear[i];
    if (!assigned)
        for (unsigned i = 0; i < rear.size(); ++i)
            if (rear[i]->GetVictim() == bot && holders[i] && holders[i]->GetDistance(rear[i]) >= bot->GetDistance(rear[i]))
            { assigned = rear[i]; retiringHolder = true; break; } // Keep the old holder until native replacement is actually nearer.
    if (assigned)
    {
        plan.boss = assigned->GetObjectGuid(); previousHorseman = plan.boss;
        if (!ai->IsHeal(bot)) plan.target = plan.boss;
        const float range = RearRange(ai, assigned);
        // A relief holder goes closer than the retiring one. Equal-radius
        // positions can retain the old native closest-player victim forever.
        const float radius = ai->IsTank(bot) ? 2.0f : std::min(retiringHolder ? 18.0f : 12.0f, range - 3.0f);
        plan.emergency = HorsemanStacks(bot, assigned) >= 3;
        if (range < 8 || !HorsemanRing(ai, assigned, radius, 0, members, live, plan)) HorsemanWait(ai, assigned, {}, plan);
        return true;
    }
    // Damage stays on the two front bosses first. Healers use distinct live
    // corners and their native heals rather than taking a melee tank's slot.
    auto pool = front.empty() ? rear : front;
    if (ai->IsHeal(bot))
    {
        std::vector<Player*> healers;
        for (Player* member : members) if (ai->IsHeal(member)) healers.push_back(member);
        const auto self = std::find(healers.begin(), healers.end(), bot);
        const size_t index = self == healers.end() ? 0 : size_t(self - healers.begin());
        pool = live; std::rotate(pool.begin(), pool.begin() + index % pool.size(), pool.end());
    }
    for (Unit* boss : pool) if (HorsemanStacks(bot, boss) < 3) { assigned = boss; break; }
    if (!assigned) { HorsemanWait(ai, live.front(), live, plan); return true; }
    plan.boss = assigned->GetObjectGuid();
    if (!ai->IsHeal(bot)) plan.target = plan.boss;
    if (assigned->GetEntry() == 16064)
    {
        Player* tank = HorsemanVictim(bot, assigned);
        const float meteor = NativeEncounterSpellRadius(bot->GetMap()->IsRegularDifficulty() ? 28884 : 57467);
        // Native Meteor splits at its actual victim, including during a swap.
        if (tank && meteor > 2 && ClearSpentMarks(bot, assigned, HorsemanPoint(tank), live) &&
            HorsemanPosition(ai, assigned, HorsemanPoint(tank), plan)) return true;
    }
    float radius = ai->IsRanged(bot) || ai->IsHeal(bot) ? 24.0f : 3.0f;
    if (RearHorseman(assigned)) radius = ai->IsRanged(bot) || ai->IsHeal(bot) ? std::max(radius, 18.0f) :
        std::max(3.0f, assigned->GetCombatReach() + bot->GetCombatReach() - 0.5f);
    const float spacing = assigned->GetEntry() == 16063 ? SpellTargetMgr::GetJumpRadius(bot->GetMap()->IsRegularDifficulty() ? 28883 : 57466) + 1 : 0;
    if (!HorsemanRing(ai, assigned, radius, spacing, members, live, plan)) HorsemanWait(ai, assigned, {}, plan);
    return true;
#else
    return false;
#endif
}

Unit* ai::WrathHorsemanReliefTarget(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    if (!bot || !bot->GetGroup() || bot->GetMapId() != 533 || !HorsemanMember(bot, bot) ||
        !ai->IsTank(bot) || ai->IsRealPlayer()) return nullptr;
    std::vector<Unit*> front;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (FrontHorseman(boss) && NaxxramasEncounterEngaged(bot, boss)) front.push_back(boss);
    }
    if (front.empty() || front.size() > 2) return nullptr;
    std::sort(front.begin(), front.end(), [](Unit* a, Unit* b) { return a->GetEntry() < b->GetEntry(); });
    const auto members = HorsemanMembers(ai);
    Unit* target = FrontAssignment(ai, bot, front, members);
    if (!target || target->GetVictim() == bot || HorsemanStacks(bot, target) || bot->GetVictim() != target) return nullptr;
    return target; // Caller rechecks native CanCast/cooldown/range; misses retain native owners.
#else
    return nullptr;
#endif
}
