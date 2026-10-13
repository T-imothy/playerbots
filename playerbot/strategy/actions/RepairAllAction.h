#pragma once
#include "GenericActions.h"
#include "MovementActions.h"

namespace ai
{
    class RaidRepairAction : public MovementAction
    {
    public:
        RaidRepairAction(PlayerbotAI* ai) : MovementAction(ai,"raid repair") {}
        bool isUseful() override;
        bool Execute(Event& event) override;
    private:
        Creature* GetRepairNpc();
    };

    class RepairAllAction : public ChatCommandAction
    {
    public:
        RepairAllAction(PlayerbotAI* ai) : ChatCommandAction(ai, "repair") {}
        virtual bool Execute(Event& event) override;
    };
}