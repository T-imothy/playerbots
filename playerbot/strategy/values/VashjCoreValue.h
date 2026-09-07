#pragma once
#include "EncounterPositionValue.h"

namespace ai
{
    enum class VashjCoreTask { None, Collect, Receive, Deliver };
    struct VashjCorePlan
    {
        VashjCoreTask task = VashjCoreTask::None;
        EncounterPosition position;
        ObjectGuid carrier, receiver, generator, corpse;
    };

    Unit* FindVashjCorePhase(PlayerbotAI* ai);
    bool IsVashjGenerator(Player* bot, GameObject* object);
    bool CanReceiveVashjCore(PlayerbotAI* ai, Player* member);
    bool CanLootVashjCore(Player* player, Creature* corpse, Unit* boss);
    bool CanPassVashjCore(Player* carrier, Player* receiver, GameObject* generator);

    class VashjCoreValue : public CalculatedValue<VashjCorePlan>
    {
    public:
        VashjCoreValue(PlayerbotAI* ai) : CalculatedValue(ai, "vashj core plan", 2) {}
        VashjCorePlan Calculate() override;
    };
}
