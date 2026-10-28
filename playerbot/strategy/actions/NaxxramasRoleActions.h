#pragma once
#include <string>

class PlayerbotAI;
class Unit;
namespace ai
{
    class Action;
    struct ClassicRaidPlan;
    bool NaxxramasRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan);
    bool NaxxramasRoleSupport(PlayerbotAI* ai, std::string& spell, Unit*& target);
    float NaxxramasRoleMultiplier(PlayerbotAI* ai, Action* action);
}
