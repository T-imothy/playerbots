#pragma once
class PlayerbotAI;
class Unit;
namespace ai
{
    struct ClassicRaidPlan;
    bool BroodlordFormationPlan(PlayerbotAI* ai, Unit* boss, Unit* target, ClassicRaidPlan& plan);
}
