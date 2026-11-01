#pragma once
class PlayerbotAI;
class Unit;
struct SpellEntry;
namespace ai
{
    struct ClassicRaidPlan;
    bool CthunRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan);
    bool CthunPlanCurrent(PlayerbotAI* ai, const ClassicRaidPlan& plan);
    bool CthunOffenseAllowed(PlayerbotAI* ai, const SpellEntry* spell, Unit* target);
    bool CthunApproachAllowed(PlayerbotAI* ai, Unit* target);
    bool CthunStomachExit(PlayerbotAI* ai, bool execute);
    bool CthunFleshTarget(PlayerbotAI* ai, Unit* target);
}
