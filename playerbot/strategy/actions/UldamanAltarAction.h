#pragma once
#include "MovementActions.h"
#include "playerbot/strategy/values/UldamanAltarValue.h"

namespace ai
{
    class AssistUldamanAltarAction : public MovementAction
    {
    public:
        AssistUldamanAltarAction(PlayerbotAI* ai) : MovementAction(ai, "assist uldaman altar") {}
        static bool Start(PlayerbotAI* ai, Player* requester, ObjectGuid altarGuid);
        GameObject* GetAltar();
        bool isUseful() override { return GetAltar() != nullptr; }
        bool isPossible() override;
        bool Execute(Event& event) override;
    };
}
